import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from twilio.rest import Client
import datetime

load_dotenv()

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///database.db')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', False)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

db = SQLAlchemy(app)

TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
else:
    twilio_client = None

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class EmergencyContact(db.Model):
    __tablename__ = 'emergency_contacts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    contact_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120))
    relationship = db.Column(db.String(50))


@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('saved'))
    return render_template('home.html')


@app.route('/signin', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')

            if not username or not password:
                return jsonify({'success': False, 'message': 'Missing username or password'}), 400

            user = User.query.filter_by(username=username).first()

            if user and user.check_password(password):
                session['user_id'] = user.id
                session['username'] = user.username
                return jsonify({'success': True, 'message': 'Login successful', 'redirect': '/saved'}), 200
            else:
                return jsonify({'success': False, 'message': 'Invalid username or password'}), 401

        except Exception as e:
            print(f"Login error: {str(e)}")
            return jsonify({'success': False, 'message': 'Server error. Please try again.'}), 500

    return render_template('signin.html')


@app.route('/signup', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        try:
            data = request.get_json()
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')
            phone = data.get('phone')

            if not all([username, email, password]):
                return jsonify({'success': False, 'message': 'Missing required fields'}), 400

            if User.query.filter_by(username=username).first():
                return jsonify({'success': False, 'message': 'Username already exists'}), 409

            if User.query.filter_by(email=email).first():
                return jsonify({'success': False, 'message': 'Email already registered'}), 409

            user = User(username=username, email=email, phone=phone)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()

            session['user_id'] = user.id
            session['username'] = user.username

            return jsonify({'success': True, 'message': 'Account created successfully', 'redirect': '/saved'}), 201

        except Exception as e:
            db.session.rollback()
            print(f"Signin error: {str(e)}")
            return jsonify({'success': False, 'message': 'Server error. Please try again.'}), 500

    return render_template('signup.html')


@app.route('/saved')
def saved():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    contacts = EmergencyContact.query.filter_by(user_id=session['user_id']).all()
    return render_template('saved.html', user=user, contacts=contacts)


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    contacts = EmergencyContact.query.filter_by(user_id=session['user_id']).all()
    return render_template('dashboard.html', user=user, contacts=contacts)


@app.route('/home')
def user_home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    return render_template('home.html', user=user)


@app.route('/journey')
def journey():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    return render_template('journey.html', user=user)


@app.route('/reminders')
def reminders():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    return render_template('reminders.html', user=user)


@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    return render_template('history.html', user=user)


@app.route('/emergency', methods=['POST'])
def emergency_alert():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    try:
        data = request.get_json()
        latitude = data.get('latitude')
        longitude = data.get('longitude')

        user = User.query.get(session['user_id'])
        contacts = EmergencyContact.query.filter_by(user_id=session['user_id']).all()

        if not contacts:
            return jsonify({'success': False, 'message': 'No emergency contacts added'}), 400

        location_url = f"https://maps.google.com/?q={latitude},{longitude}"
        message = f"EMERGENCY: {user.username} needs help! Location: {location_url}"

        if twilio_client:
            for contact in contacts:
                try:
                    twilio_client.messages.create(
                        body=message,
                        from_=TWILIO_PHONE_NUMBER,
                        to=contact.phone_number
                    )
                except Exception as e:
                    print(f"SMS failed: {str(e)}")

        return jsonify({'success': True, 'message': 'Emergency alert sent', 'contacts_notified': len(contacts)}), 200

    except Exception as e:
        print(f"Emergency alert error: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to send alert'}), 500


@app.route('/add-contact', methods=['POST'])
def add_contact():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    try:
        data = request.get_json()
        contact = EmergencyContact(
            user_id=session['user_id'],
            contact_name=data.get('name'),
            phone_number=data.get('phone'),
            email=data.get('email'),
            relationship=data.get('relationship')
        )
        db.session.add(contact)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Contact added'}), 201

    except Exception as e:
        db.session.rollback()
        print(f"Add contact error: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to add contact'}), 500


@app.route('/delete-contact/<int:contact_id>', methods=['DELETE'])
def delete_contact(contact_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    contact = EmergencyContact.query.filter_by(id=contact_id, user_id=session['user_id']).first()
    if contact:
        db.session.delete(contact)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Contact deleted'}), 200
    return jsonify({'success': False, 'message': 'Contact not found'}), 404


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route('/privacy')
def privacy():
    return render_template('privacy.html')


@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Internal server error'}), 500


with app.app_context():
    db.create_all()
    print("✓ Database initialized")


if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_ENV') == 'development'
    if debug_mode:
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        app.run(debug=False, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
