from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
import os
import pymysql
from googletrans import Translator, LANGUAGES
from werkzeug.utils import secure_filename

pymysql.install_as_MySQLdb()

app = Flask(__name__)
app.config.from_object(Config)
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size
app.secret_key = 'supersecretkey'

db = SQLAlchemy(app)
migrate = Migrate(app, db)
translator = Translator()

class P_Users(db.Model):
    __tablename__ = 'P_Users'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    profile_picture = db.Column(db.String(255), nullable=True)

class P_Languages(db.Model):
    __tablename__ = 'P_Languages'
    language_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('P_Users.user_id'), nullable=False)
    native_language = db.Column(db.String(50), nullable=False)
    fluent_language = db.Column(db.String(100), nullable=True)
    learning_language = db.Column(db.String(50), nullable=False)
    proficiency_level = db.Column(db.String(50), nullable=False)

class P_Profiles(db.Model):
    __tablename__ = 'P_Profiles'
    profile_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('P_Users.user_id'), nullable=False)
    bio = db.Column(db.Text, nullable=False)
    interests = db.Column(db.String(255), nullable=False)
    preferred_partner = db.Column(db.String(255), nullable=False)
    learning_goals = db.Column(db.Text, nullable=False)

class P_Matches(db.Model):
    __tablename__ = 'P_Matches'
    match_id = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('P_Users.user_id'), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey('P_Users.user_id'), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='pending')

class P_Messages(db.Model):
    __tablename__ = 'P_Messages'
    message_id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('P_Users.user_id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('P_Users.user_id'), nullable=False)
    message_content = db.Column(db.Text, nullable=False)
    translated_content = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)

class P_Notifications(db.Model):
    __tablename__ = 'P_Notifications'
    notification_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('P_Users.user_id'), nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)
    notification_content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)

@app.route('/')
def main():
    if 'user_id' in session:
        user = db.session.query(P_Users).get(session['user_id'])
        user_languages = db.session.query(P_Languages).filter_by(user_id=user.user_id).first()

        all_users = db.session.query(
            P_Users.user_id,
            P_Users.username,
            P_Users.profile_picture,
            P_Languages.native_language,
            P_Languages.fluent_language,
            P_Languages.learning_language,
            P_Languages.proficiency_level,
            P_Profiles.interests
        ).join(P_Languages, P_Users.user_id == P_Languages.user_id).join(P_Profiles, P_Users.user_id == P_Profiles.user_id).all()

        matched_users = []
        for u in all_users:
            u_native_languages = u.fluent_language.split(',') if u.fluent_language else []
            user_fluent_languages = user_languages.fluent_language.split(',') if user_languages.fluent_language else []
            if (
                (user_languages.learning_language in u_native_languages or user_languages.learning_language == u.native_language) and
                (u.learning_language in user_fluent_languages or u.learning_language == user_languages.native_language)
            ):
                matched_users.append(u)

        return render_template('main.html', user=user, users=matched_users)
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = P_Users.query.filter_by(email=email, password=password).first()
        if user:
            session['user_id'] = user.user_id
            return redirect(url_for('main'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        if P_Users.query.filter_by(email=email).first():
            flash('Email already registered. Please use a different email.', 'error')
            return redirect(url_for('register'))
        
        username = request.form['username']
        password = request.form['password']
        
        profile_picture = None
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                profile_picture = filename
        
        user = P_Users(
            username=username,
            email=email,
            password=password,
            profile_picture=profile_picture
        )
        db.session.add(user)
        db.session.commit()

        languages = P_Languages(
            user_id=user.user_id,
            native_language=request.form['native_language'],
            fluent_language=request.form['fluent_language'],
            learning_language=request.form['learning_language'],
            proficiency_level=request.form['proficiency_level']
        )
        db.session.add(languages)
        db.session.commit()

        profile = P_Profiles(
            user_id=user.user_id,
            bio=request.form['bio'],
            interests=request.form['interests'],
            preferred_partner=request.form['preferred_partner'],
            learning_goals=request.form['learning_goals']
        )
        db.session.add(profile)
        db.session.commit()

        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/mypage', methods=['GET', 'POST'])
def mypage():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = db.session.query(P_Users).get(session['user_id'])
    languages = db.session.query(P_Languages).filter_by(user_id=user.user_id).first()
    profile = db.session.query(P_Profiles).filter_by(user_id=user.user_id).first()
    if request.method == 'POST':
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                user.profile_picture = filename
        
        languages.native_language = request.form['native_language']
        languages.fluent_language = request.form['fluent_language']
        languages.learning_language = request.form['learning_language']
        languages.proficiency_level = request.form['proficiency_level']
        profile.bio = request.form['bio']
        profile.interests = request.form['interests']
        profile.preferred_partner = request.form['preferred_partner']
        profile.learning_goals = request.form['learning_goals']
        db.session.commit()
        return redirect(url_for('mypage'))
    return render_template('mypage.html', user=user, languages=languages, profile=profile)

@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = db.session.query(P_Users).get(user_id)

    if user:
        # Delete user's profile picture from the filesystem
        if user.profile_picture:
            profile_picture_path = os.path.join(app.config['UPLOAD_FOLDER'], user.profile_picture)
            if os.path.exists(profile_picture_path):
                os.remove(profile_picture_path)
        
        # Delete related data
        P_Languages.query.filter_by(user_id=user_id).delete()
        P_Profiles.query.filter_by(user_id=user_id).delete()
        P_Matches.query.filter(
            ((P_Matches.user1_id == user_id) | (P_Matches.user2_id == user_id))
        ).delete()
        P_Messages.query.filter(
            ((P_Messages.sender_id == user_id) | (P_Messages.receiver_id == user_id))
        ).delete()
        P_Notifications.query.filter_by(user_id=user_id).delete()

        db.session.delete(user)
        db.session.commit()

        session.pop('user_id', None)
        return redirect(url_for('login'))

@app.route('/messages')
def messages():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = db.session.query(P_Users).get(session['user_id'])
    matches = P_Matches.query.filter(
        ((P_Matches.user1_id == user.user_id) | (P_Matches.user2_id == user.user_id)) & 
        (P_Matches.status == 'accepted')
    ).all()
    pending_requests = P_Matches.query.filter_by(user2_id=user.user_id, status='pending').all()

    match_users = []
    for match in matches:
        if match.user1_id == user.user_id:
            match_user = db.session.query(P_Users).get(match.user2_id)
        else:
            match_user = db.session.query(P_Users).get(match.user1_id)
        match_users.append(match_user)

    pending_request_users = []
    for request in pending_requests:
        request_user = db.session.query(P_Users).get(request.user1_id)
        pending_request_users.append((request, request_user))

    return render_template('messages.html', user=user, match_users=match_users, pending_request_users=pending_request_users)

@app.route('/message_request/<int:user_id>', methods=['POST'])
def message_request(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    existing_match = P_Matches.query.filter_by(user1_id=session['user_id'], user2_id=user_id).first()
    
    if not existing_match:
        match = P_Matches(user1_id=session['user_id'], user2_id=user_id, status='pending')
        db.session.add(match)
        db.session.commit()
    
    return redirect(url_for('main'))

@app.route('/handle_request/<int:match_id>/<action>', methods=['POST'])
def handle_request(match_id, action):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    match = db.session.query(P_Matches).get(match_id)
    
    if match and match.user2_id == session['user_id']:
        if action == 'accept':
            match.status = 'accepted'
        elif action == 'reject':
            match.status = 'rejected'
        db.session.commit()
    
    return redirect(url_for('messages'))

@app.route('/chat/<int:user_id>', methods=['GET', 'POST'])
def chat(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = db.session.query(P_Users).get(session['user_id'])
    chat_user = db.session.query(P_Users).get(user_id)

    if request.method == 'POST':
        message_content = request.form['message_content']
        message = P_Messages(sender_id=user.user_id, receiver_id=chat_user.user_id, message_content=message_content)
        db.session.add(message)
        db.session.commit()
    
    messages = P_Messages.query.filter(
        ((P_Messages.sender_id == user.user_id) & (P_Messages.receiver_id == chat_user.user_id)) |
        ((P_Messages.sender_id == chat_user.user_id) & (P_Messages.receiver_id == user.user_id))
    ).order_by(P_Messages.timestamp).all()

    languages = LANGUAGES

    return render_template('chat.html', user=user, chat_user=chat_user, messages=messages, languages=languages)

@app.route('/translate_message', methods=['POST'])
def translate_message():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    message_id = request.form['message_id']
    target_language = request.form['target_language']

    message = db.session.query(P_Messages).get(message_id)
    if not message:
        return jsonify({'error': 'Message not found'}), 404

    translation = translator.translate(message.message_content, dest=target_language)
    translated_text = translation.text

    return jsonify({'message_id': message_id, 'translated_text': translated_text})

@app.route('/delete_chat/<int:user_id>', methods=['POST'])
def delete_chat(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = db.session.query(P_Users).get(session['user_id'])
    
    P_Matches.query.filter(
        ((P_Matches.user1_id == user.user_id) & (P_Matches.user2_id == user_id)) |
        ((P_Matches.user1_id == user_id) & (P_Matches.user2_id == user.user_id))
    ).delete()
    
    P_Messages.query.filter(
        ((P_Messages.sender_id == user.user_id) & (P_Messages.receiver_id == user_id)) |
        ((P_Messages.sender_id == user_id) & (P_Messages.receiver_id == user.user_id))
    ).delete()
    
    db.session.commit()
    return redirect(url_for('messages'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
