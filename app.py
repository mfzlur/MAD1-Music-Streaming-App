import os
from flask import Flask, render_template, request, url_for, flash, redirect, session
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from datetime import datetime, date
from werkzeug.utils import secure_filename
from flask_migrate import Migrate




UPLOAD_FOLDER ='song-files'
ALLOWED_EXTENSIONS = {'mp3'}
app = Flask(__name__) #application instance
app.config['SECRET_KEY'] = 'my-secret-key'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///myDB.db' 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False #to supress warning
db = SQLAlchemy(app) #database instance
migrate = Migrate(app, db)
bootstrap = Bootstrap(app)

######################      Models      ##################################
##########################################################################


class User(db.Model):
    __tablename__= 'user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(512), nullable=False)
    name = db.Column(db.String(80), nullable=True)
    type = db.Column(db.String(32), nullable=False, default='general')
    flagged = db.Column(db.Boolean, default=False, nullable=False)
    blacklisted = db.Column(db.Boolean, default=False, nullable=False)

    artist_id = db.Column(db.Integer, db.ForeignKey('artist.id'), nullable=True)
    artist = db.relationship('Artist', uselist=False, back_populates='user')

    def check_password(self,password):
        return self.password==password
    
    
songs = db.Table('songs',
    db.Column('song_id', db.Integer, db.ForeignKey('song.id'), primary_key=True),
    db.Column('playlist_id', db.Integer, db.ForeignKey('playlist.id'), primary_key=True)
)

class Song(db.Model):
    __tablename__= 'song'
    id = db.Column(db.Integer,autoincrement=True, primary_key=True)
    title = db.Column(db.String(200))
    release_date = db.Column(db.Date, nullable=True)
    lyrics = db.Column(db.Text())
    song_file_name = db.Column(db.String(500), nullable=True)
    singer = db.Column(db.String(200))
    genre = db.Column(db.String(80), default='genre1', nullable=True)
    song_rating = db.Column(db.Float, nullable=True)
    lyrics_rating = db.Column(db.Float, nullable=True)

    artist_id = db.Column(db.Integer, db.ForeignKey('artist.id'), nullable=True)

    album_id = db.Column(db.Integer, db.ForeignKey('album.id'), nullable=True)


class Artist(db.Model):

    id = db.Column(db.Integer, autoincrement=True, primary_key=True)

    user = db.relationship('User', backref='artist', uselist=False)

    # One-to-many relationship with Song, album
    songs = db.relationship('Song', backref='artist', lazy=True)
    albums = db.relationship('Album', back_populates='artist', lazy=True)

class Album(db.Model):
    __tablename__= 'album'
    id = db.Column(db.Integer,autoincrement=True, primary_key=True)
    name = db.Column(db.String(200))
    genre = db.Column(db.String(200))

    artist_id = db.Column(db.Integer, db.ForeignKey('artist.id'), nullable=True)
    songs = db.relationship('Song', backref='album', lazy=True)


class Playlist(db.Model):
    __tablename__= 'playlist'
    id = db.Column(db.Integer,autoincrement=True, primary_key=True)
    name = db.Column(db.String(80))

    songs = db.relationship('Song', secondary=songs, lazy='subquery',
        backref=db.backref('playlists', lazy=True))
    



#########################   Normal  User  ######################################
#########################                 ######################################


@app.route('/search', methods=['GET'])
def search():

    album_search = request.args.get('albumSearch', '')
    song_search = request.args.get('songSearch', '')

    albums = Album.query.filter(Album.name.ilike(f'%{album_search}%')).all()

    if not albums:
        albums = Album.query.filter(Album.genre.ilike(f'%{album_search}%')).all()
    
    if not albums:
        flash('No albums or genre found please try again')
        return redirect(url_for('user_dashboard'))
    
    # Search for songs by title (case-insensitive)
    songs = Song.query.filter(Song.title.ilike(f'%{song_search}%')).all()

    if not songs:
        try:
            rating = int(song_search)
            # Search for songs by rating
            songs = Song.query.filter_by(song_rating=rating).all()
        except ValueError:
            pass  # Ignore ValueError, as it means the search term is not a valid integer rating

    if not songs:
        flash('No songs found matching the search critea!! try again')
        return redirect(url_for('user_dashboard'))

    return render_template('search.html', albums=albums, songs=songs)

@app.route('/')
def index():
    user_type = "Normal User's Home Page"
    return render_template('index.html', user_type=user_type)

@app.route('/dashboard')
def user_dashboard():
    songs = db.session.query(Song).all()
    playlists = db.session.query(Playlist).all()
    genre_value='genre1'
    genre = Song.query.filter_by(genre=genre_value).all()

    return render_template('user-dashboard.html', songs=songs, playlists=playlists, genre=genre, genre_value=genre_value)


@app.route('/login', methods=['GET', 'POST'])
def user_login():

    if request.method == 'GET':
        return render_template('user-login.html')

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username=='' or  password=='':
            flash('username or password cannot be empty')
            return redirect(url_for('user_login'))


        user = User.query.filter_by(username=username).first()
        if not user:
            flash('User does not exists kindly try again')
            return redirect(url_for('user_login'))
        
        
        elif not user.check_password(password):
            flash('Incorrect Password.')
            return redirect(url_for('user_login'))
        
        session['user_id'] = user.id
        session['username'] = user.username
        session['artist_id'] = user.artist_id
    
        return redirect(url_for('user_dashboard'))
        


@app.route('/register', methods=['GET', 'POST'])
def user_register():
    if request.method == 'GET':
        return render_template('user-register.html')

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')

        if username=='' or  password=='':
            flash('username or password cannot be empty')
            return redirect(url_for('user_login'))

        if User.query.filter_by(username=username).first():
            flash('user with the username already exists. Please choose some other username')
            return redirect(url_for('user_register'))
        
        user = User(username=username, password=password, name=name)
        db.session.add(user)
        db.session.commit()
        flash('User successfully registered')
        
        return redirect(url_for('user_login'))

@app.route('/song/<int:song_id>/update_rating', methods=['POST'])
def update_song_rating(song_id):
    rating = int(request.form.get('rating'))

    song = Song.query.get(song_id)
    if song:
        song.song_rating = rating
        db.session.commit()

    return redirect(url_for('song', song_id=song_id))

@app.route('/lyrics/<int:song_id>/update_rating', methods=['POST'])
def update_lyrics_rating(song_id):
    rating = int(request.form.get('rating'))

    song = Song.query.get(song_id)
    if song:
        song.lyrics_rating = rating
        db.session.commit()

    return redirect(url_for('song', song_id=song_id))

@app.route('/song/<int:song_id>')
def song(song_id):
    song = Song.query.filter_by(id=song_id).first()
    song_name = song.title
    artist_id = song.artist_id
    song_id = song.id
    artist = User.query.filter_by(artist_id=artist_id).first()
    if artist:
        artist_name=artist.name
    else:
        artist_name = 'Artist not found'
    
    lyrics = song.lyrics

    return render_template('song.html', song_name=song_name, artist_name=artist_name, lyrics=lyrics, song_id=song_id)


    
app.route('/edit-song/<int:song_id>', methods=['GET','POST'])
def edit_song(song_id):

    if request.method == 'GET':
        song_details = db.session.query(Song).filter_by(id=song_id).first()
        artist_id = song_details.artist_id
        artist = db.session.query(Artist).filter_by(id=artist_id).first()
        artist_name=artist.name
        return render_template('edit-song.html', song_title=song_details.title, lyrics=song_details.lyrics, artis_name=artist_name)
                               

    if request.method == 'POST':
        song_title = request.form['song_title']
        lyrics = request.form['lyrics']


        update_song = db.session.query(
            Song).filter_by(id=song_id).first()

        # Update Values in SQL
        update_song.title = song_title
        update_song.lyrics = lyrics

        db.session.commit()

        return redirect(url_for('creator_dashboard'))

app.route('/delete-song/<int:song_id>', methods=['GET'])
def delete_song(song_id):
    delete_song = db.session.query(Song).filter_by(id=song_id).first()
    db.session.delete(delete_song)
    db.session.commit()

    return redirect(url_for('creator_dashboard'))


@app.route('/all-songs')
def all_songs():
    songs= Song.query.all()
    return render_template('all-songs.html', songs=songs)

@app.route('/all-albums')
def all_albums():
    albums= Album.query.all()
    return render_template('all-albums.html', albums=albums)

@app.route('/create-playlist', methods=['GET','POST'])
def create_playlist():
    all_songs = Song.query.all()

    if request.method == 'GET':
        return render_template('create-playlist.html', songs=all_songs)
    
    if request.method == 'POST':
        # Get the playlist name and selected songs from the form data
        playlist_name = request.form.get('playlist_name')
        selected_songs = request.form.getlist('selected_songs')

        new_playlist = Playlist(name=playlist_name)
        for song_id in selected_songs:
            song = Song.query.get(song_id)
            new_playlist.songs.append(song)
        db.session.add(new_playlist)
        db.session.commit()
        flash('Playlist Created Successfully')

        return redirect(url_for('user_dashboard'))

@app.route('/playlist-songs/<int:playlist_id>')
def playlist_songs(playlist_id):
    playlist = Playlist.query.filter_by(id=playlist_id).first()
    songs = playlist.songs
    return render_template('playlist-songs.html', songs=songs)


@app.route('/logout')
def logout():
    session.clear()
    return render_template('user-login.html')


#########################   Admin   User  ######################################
#########################                 ######################################



@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():

    if request.method == 'GET':
        return render_template('admin-login.html')

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username=='' or  password=='':
            flash('username or password cannot be empty')
            return redirect(url_for('admin_login'))


        user = User.query.filter_by(username=username).first()
        if not user:
            flash('User does not exists kindly try again')
            return redirect(url_for('admin_login'))
        
        
        elif not user.check_password(password):
            flash('Incorrect Password.')
            return redirect(url_for('admin_login'))
        
        elif not user.type == 'admin':
            flash('User is not an admin kindly log in as a normal user')
            return redirect(url_for('admin_login'))
        
        all_users = User.query.all()

        # Filter users by user type
        normal_users = len([user for user in all_users if user.type == 'normal'])
        print(normal_users)
        creator_users = len([user for user in all_users if user.type == 'creator'])

        songs = Song.query.all()
        tracks = len(songs)
        
        albums = Album.query.all()
        total_albums = len(albums)
        genres = []
        for album in albums:
            if album.genre not in genres:
                genres.append(album.genre)
        total_genres = len(genres)


        return render_template('admin-dashboard.html', total_normal_users=normal_users, total_creators=creator_users, total_songs=tracks, total_albums=total_albums, total_genres=total_genres)
        


@app.route('/admin-register', methods=['GET', 'POST'])
def admin_register():
    if request.method == 'GET':
        return render_template('admin-register.html')

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')

        if username=='' or  password=='':
            flash('username or password cannot be empty')
            return redirect(url_for('admin_login'))
        
        user = User.query.filter_by(username=username).first()

        if user:
            if user.type != 'admin':
                flash(f'User {user.username} is admin user now')
                user.type = 'admin'
                db.session.commit()
                return redirect(url_for('admin_login'))
            
            elif user.type == 'admin':
                flash('user with the username already exists. Please choose some other username')
                return redirect(url_for('admin_register'))
        
        user = User(username=username, password=password, name=name, type='admin')
        db.session.add(user)
        db.session.commit()
        flash('User successfully registered')
        
        return redirect(url_for('admin_login'))

@app.route('/admin-dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    users = User.query.all()
    songs = Song.query.all()
    albums = Album.query.all()
    genres = []
    creators = []
    admins = []
    for user in users:
        if user.type == 'creator':
            creators.append(user)
        elif user.type == 'admin':
            admins.append(user)

    for song in songs:
        if song.genre not in genres:
            genres.append(song.genre)

    total_normal_users = len(users) - len(creators) -len(admins)
    total_albums = len(albums)
    total_songs = len(songs)
    total_genres = len(genres)
    total_creators = len(creators)

    return render_template('admin-dashboard.html', total_albums=total_albums, total_creators=total_creators,total_songs=total_songs, total_genres=total_genres, total_normal_users=total_normal_users)


#########################   Creator  User  #####################################
#########################                  #####################################


    
@app.route('/register-as-creator', methods=['GET', 'POST'])
def creator_register():
    if request.method == 'GET':
        return render_template('creator-register.html')

    if request.method == 'POST':
        # Retrieve user_id from the session
        user_id = session.get('user_id')


        normal_user = User.query.get(user_id)
        #print(normal_user.name)

        if normal_user.type != 'creator':
            flash(f'User {normal_user.username} is a creator now')
            normal_user.type = 'creator'
            artist = Artist()
            normal_user.artist_id = artist.id
            db.session.commit()
            return render_template('creator-dashboard.html')

        elif normal_user.type == 'creator':
            flash('You are already a creator. Redirecting you to the creator dashboard.')
            return render_template('creator-dashboard.html')

        else:
            flash('Something went wrong. Kindly retry.')
            return redirect(url_for('creator_dashboard'))


@app.route('/creator-dashboard', methods=['GET', 'POST'])
def creator_dashboard():
    artist_id = session.get('user_id')
    user = User.query.filter_by(id=artist_id).first()
    

    if user.type != 'artist':
        return redirect(url_for('creator_register'))
    
    songs = Song.query.filter_by(artist_id=artist_id).all()
    print(songs)
    total_songs = len(songs)

    if total_songs == 0:
        return render_template('creator-dashboard-start.html')


    albums = Album.query.filter_by(artist_id=artist_id).all()
    total_albums = len(albums)

    total_rating = 0
    for song in songs:
        if song.song_rating is not None:
            total_rating += int(song.song_rating)
    avg_rating = total_rating/total_songs

    return render_template('creator-dashboard.html', total_songs=total_songs, total_albums=total_albums, avg_rating=avg_rating)


@app.route('/song-upload', methods=['GET', 'POST'])
def upload_song():
    if request.method == 'GET':
        return render_template('upload-song.html')

    if request.method == 'POST':
        title = request.form.get('title')
        song_file = request.files.get('song-file-name')
        release_date_str = request.form.get('release-date')
        lyrics = request.form.get('lyrics')
        song_file_name = ''

        release_date = datetime.strptime(release_date_str, "%Y-%m-%d")
        artist_id = session.get('artist_id')

        if title=='':
            flash('Title cannot be empty')
            return redirect(url_for('upload_song'))
        
        if song_file and allowed_file(song_file.filename):
            filename = secure_filename(song_file.filename)
            song_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            song_file_name = filename

        
        song = Song(title=title, artist_id=artist_id, release_date=release_date, lyrics=lyrics, song_file_name=song_file_name)
        

        db.session.add(song)
        db.session.commit()
        flash('Song Added Successfully')
        
        return redirect(url_for('creator_dashboard'))
        
@app.route('/play-song')
def play_song():
    # Provide the URL to the MP3 file
    mp3_url = url_for('static', filename='song-files/' + 'song1.mp3')
    return render_template('play-song.html', mp3_url=mp3_url)
    
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
    