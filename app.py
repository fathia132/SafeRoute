from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import json
import random
import string

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "saferoute-secret-2024")

# --- DATABASE ---
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///saferoute.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# --- TWILIO ---
TWILIO_SID   = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_FROM  = os.environ.get("TWILIO_PHONE_NUMBER")
CALLMEBOT_KEY = os.environ.get("CALLMEBOT_API_KEY", "")

# --- MODELS ---
class User(db.Model):
    id                 = db.Column(db.Integer, primary_key=True)
    name               = db.Column(db.String(100))
    email              = db.Column(db.String(150), unique=True, nullable=False)
    password           = db.Column(db.String(200))
    oauth_provider     = db.Column(db.String(50))
    emergency_contacts = db.Column(db.Text, default="[]")
    created_at         = db.Column(db.DateTime, default=datetime.utcnow)
    reset_token        = db.Column(db.String(10))

class Reminder(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("user.id"))
    destination = db.Column(db.String(200))
    hour        = db.Column(db.Integer)
    minute      = db.Column(db.Integer)
    period      = db.Column(db.String(2))
    days        = db.Column(db.String(100))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

class JourneyHistory(db.Model):
    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey("user.id"))
    destination      = db.Column(db.String(200))
    duration_minutes = db.Column(db.Integer)
    started_at       = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at         = db.Column(db.DateTime)
    status           = db.Column(db.String(50), default="active")

with app.app_context():
    db.create_all()

# --- HELPERS ---
def current_user():
    uid = session.get("user_id")
    return User.query.get(uid) if uid else None

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user():
            return redirect(url_for("signin"))
        return f(*args, **kwargs)
    return decorated

# ================================================================
# PAGE ROUTES
# ================================================================

@app.route("/")
def index():
    return redirect(url_for("reminders")) if current_user() else render_template("landing.html")

@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route("/signin")
def signin():
    return render_template("signin.html")

@app.route("/reminders")
@login_required
def reminders():
    return render_template("reminders.html", user=current_user())

@app.route("/saved")
@login_required
def saved():
    reminder_list = Reminder.query.filter_by(user_id=session["user_id"]).all()
    return render_template("saved.html", reminders=reminder_list, user=current_user())

@app.route("/journey")
@login_required
def journey():
    return render_template("journey.html", user=current_user())

@app.route("/history")
@login_required
def history():
    logs = JourneyHistory.query.filter_by(
        user_id=session["user_id"]
    ).order_by(JourneyHistory.started_at.desc()).all()
    return render_template("history.html", logs=logs, user=current_user())

@app.route("/home")
def home():
    return render_template("home.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/api/whatsapp-alert", methods=["POST"])
@login_required
def whatsapp_alert():
    import json, requests as req
    data = request.get_json()
    user = current_user()
    contacts = json.loads(user.emergency_contacts or "[]") if user else []
    dest = data.get("destination", "unknown")
    location = data.get("last_location", "unknown")
    uname = user.name if user else "User"
    
    results = []
    for contact in contacts:
        number = contact["number"].replace("+", "").replace(" ", "")
        name = contact.get("name", "there")
        msg = (
            f"🚨 *EMERGENCY ALERT from SafeRoute* 🚨%0A%0A"
            f"Hello {name},%0A"
            f"*{uname}* may need urgent help right now!%0A%0A"
            f"📍 *Destination:* {dest}%0A"
            f"📌 *Last Location:* {location}%0A%0A"
            f"Please call them immediately or go to their location.%0A"
            f"If unreachable, contact the authorities.%0A%0A"
            f"_This is an automated alert from SafeRoute Safety App_"
        )
        try:
            api_key = os.environ.get("CALLMEBOT_API_KEY", "")
            url = f"https://api.callmebot.com/whatsapp.php?phone={number}&text={msg}&apikey={api_key}"
            resp = req.get(url, timeout=10)
            results.append({"number": number, "status": "sent"})
        except Exception as e:
            results.append({"number": number, "status": "failed", "error": str(e)})
    
    return jsonify({"success": True, "results": results})

@app.route("/forgot-password")
def forgot_password():
    return render_template("forgot_password.html")

@app.route("/api/forgot-password", methods=["POST"])
def api_forgot_password():
    data = request.get_json()
    email = data.get("email","").strip().lower()
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "Email not found"}), 404
    # Generate 6 digit code
    code = ''.join(random.choices(string.digits, k=6))
    user.reset_token = code
    db.session.commit()
    # Send via email if configured, else print to console
    print(f"RESET CODE for {email}: {code}")
    # Try send email via Twilio SendGrid or just show in console
    if TWILIO_SID and TWILIO_TOKEN and TWILIO_FROM:
        try:
            from twilio.rest import Client
            client = Client(TWILIO_SID, TWILIO_TOKEN)
            client.messages.create(
                body=f"Your SafeRoute password reset code is: {code}. Valid for 10 minutes.",
                to=email if "@" not in email else user.email,
                from_=TWILIO_FROM
            )
        except: pass
    return jsonify({"success": True})

@app.route("/api/reset-password", methods=["POST"])
def api_reset_password():
    data = request.get_json()
    email = data.get("email","").strip().lower()
    code = data.get("code","").strip()
    new_password = data.get("new_password","")
    user = User.query.filter_by(email=email).first()
    if not user or user.reset_token != code:
        return jsonify({"error": "Invalid code"}), 400
    user.password = generate_password_hash(new_password)
    user.reset_token = None
    db.session.commit()
    return jsonify({"success": True})

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("signin"))

# ================================================================
# AUTH API
# ================================================================

@app.route("/api/signup", methods=["POST"])
def api_signup():
    data     = request.get_json()
    name     = data.get("name", "").strip()
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not name or not email or not password:
        return jsonify({"error": "All fields are required"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    user = User(name=name, email=email,
                password=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    session["user_id"] = user.id
    return jsonify({"success": True, "redirect": "/reminders"})

@app.route("/api/signin", methods=["POST"])
def api_signin():
    data     = request.get_json()
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")
    user     = User.query.filter_by(email=email).first()

    if not user or not user.password or \
       not check_password_hash(user.password, password):
        return jsonify({"error": "Invalid email or password"}), 401

    session["user_id"] = user.id
    return jsonify({"success": True, "redirect": "/reminders"})

# ================================================================
# GOOGLE OAUTH  (only works if you add credentials to .env)
# ================================================================
try:
    from authlib.integrations.flask_client import OAuth
    oauth = OAuth(app)
    google = oauth.register(
        name="google",
        client_id=os.environ.get("GOOGLE_CLIENT_ID"),
        client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    facebook = oauth.register(
        name="facebook",
        client_id=os.environ.get("FACEBOOK_CLIENT_ID"),
        client_secret=os.environ.get("FACEBOOK_CLIENT_SECRET"),
        access_token_url="https://graph.facebook.com/oauth/access_token",
        authorize_url="https://www.facebook.com/dialog/oauth",
        api_base_url="https://graph.facebook.com/",
        client_kwargs={"scope": "email"},
    )

    @app.route("/auth/google")
    def google_login():
        redirect_uri = url_for("google_callback", _external=True)
        return google.authorize_redirect(redirect_uri)

    @app.route("/auth/google/callback")
    def google_callback():
        token    = google.authorize_access_token()
        userinfo = token.get("userinfo")
        email    = userinfo["email"]
        name     = userinfo.get("name", email.split("@")[0])
        user     = User.query.filter_by(email=email).first()
        if not user:
            user = User(name=name, email=email, oauth_provider="google")
            db.session.add(user)
            db.session.commit()
        session["user_id"] = user.id
        return redirect(url_for("reminders"))

    @app.route("/auth/facebook")
    def facebook_login():
        redirect_uri = url_for("facebook_callback", _external=True)
        return facebook.authorize_redirect(redirect_uri)

    @app.route("/auth/facebook/callback")
    def facebook_callback():
        token   = facebook.authorize_access_token()
        resp    = facebook.get("me?fields=id,name,email", token=token)
        profile = resp.json()
        email   = profile.get("email") or f"{profile['id']}@facebook.com"
        name    = profile.get("name", "User")
        user    = User.query.filter_by(email=email).first()
        if not user:
            user = User(name=name, email=email, oauth_provider="facebook")
            db.session.add(user)
            db.session.commit()
        session["user_id"] = user.id
        return redirect(url_for("reminders"))

except Exception as e:
    print(f"OAuth not configured: {e}")

# ================================================================
# REMINDERS API
# ================================================================

@app.route("/api/reminders", methods=["POST"])
@login_required
def save_reminder():
    data = request.get_json()
    r = Reminder(
        user_id     = session["user_id"],
        destination = data.get("destination", ""),
        hour        = data.get("hour", 12),
        minute      = data.get("minute", 0),
        period      = data.get("period", "AM"),
        days        = ",".join(data.get("days", [])),
    )
    db.session.add(r)
    db.session.commit()
    return jsonify({"success": True, "id": r.id})

@app.route("/api/reminders/<int:rid>", methods=["DELETE"])
@login_required
def delete_reminder(rid):
    r = Reminder.query.filter_by(id=rid, user_id=session["user_id"]).first_or_404()
    db.session.delete(r)
    db.session.commit()
    return jsonify({"success": True})

# ================================================================
# EMERGENCY CONTACTS API
# ================================================================

@app.route("/api/emergency-contact", methods=["POST"])
@login_required
def save_emergency_contact():
    data     = request.get_json()
    user     = current_user()
    contacts = data.get("contacts", [])
    user.emergency_contacts = json.dumps(contacts)
    db.session.commit()
    return jsonify({"success": True})

# ================================================================
# JOURNEY API
# ================================================================

@app.route("/api/journey/start", methods=["POST"])
@login_required
def start_journey():
    data = request.get_json()
    log  = JourneyHistory(
        user_id          = session["user_id"],
        destination      = data.get("destination", ""),
        duration_minutes = data.get("duration_minutes", 30),
        status           = "active",
    )
    db.session.add(log)
    db.session.commit()
    return jsonify({"success": True, "journey_id": log.id})

@app.route("/api/journey/safe", methods=["POST"])
@login_required
def mark_safe():
    data = request.get_json()
    log  = JourneyHistory.query.get(data.get("journey_id"))
    if log:
        log.ended_at = datetime.utcnow()
        log.status   = "safe"
        db.session.commit()
    return jsonify({"success": True})

@app.route("/api/journey/extend", methods=["POST"])
@login_required
def extend_journey():
    data = request.get_json()
    log  = JourneyHistory.query.get(data.get("journey_id"))
    if log:
        log.duration_minutes += data.get("extra_minutes", 10)
        log.status            = "extended"
        db.session.commit()
    return jsonify({"success": True})

@app.route("/api/journey/emergency", methods=["POST"])
@login_required
def call_emergency():
    data = request.get_json()
    log  = JourneyHistory.query.get(data.get("journey_id"))
    user = current_user()
    duress = data.get("duress", False)  # silent duress mode
    last_location = data.get("last_location", "unknown location")

    # Update journey status
    if log:
        log.ended_at = datetime.utcnow()
        log.status   = "emergency_called"
        db.session.commit()

    # Load saved contacts
    contacts = json.loads(user.emergency_contacts or "[]") if user else []

    if not contacts:
        return jsonify({"success": False, "error": "No emergency contacts saved"}), 400

    # Call every contact via Twilio
    if TWILIO_SID and TWILIO_TOKEN and TWILIO_FROM:
        try:
            from twilio.rest import Client
            client = Client(TWILIO_SID, TWILIO_TOKEN)
            dest   = log.destination if log else "an unknown destination"
            uname  = user.name if user else "Your contact"
            duress_note = "This is a silent distress signal. Act immediately and do not call back." if duress else "Please try to reach them immediately."

            for contact in contacts:
                contact_name = contact.get("name", "there")
                # Message repeats 5 times so even if they pick up late they hear it
                single_msg = (
                    f"<Say voice='alice'>"
                    f"Hello {contact_name}. This is an urgent safety alert from SafeRoute. "
                    f"{uname} started a journey and did not check in on time. "
                    f"They may need your help right now. "
                    f"Their planned destination was {dest}. "
                    f"Their last known location was {last_location}. "
                    f"Please check on {uname} immediately. "
                    f"Try calling them, go to their location, or contact the authorities if needed. "
                    f"{duress_note}"
                    f"</Say>"
                    f"<Pause length='2'/>"
                )
                # Repeat message 5 times so if they pick up late they still hear it
                twiml_msg = f"<Response>{single_msg * 5}</Response>"

                call = client.calls.create(
                    twiml=twiml_msg,
                    to=contact["number"],
                    from_=TWILIO_FROM,
                )

                # Keep calling every 30 seconds until answered (no limit)
                import threading
                def keep_calling(number, twiml, call_sid):
                    import time
                    attempt = 1
                    current_sid = call_sid
                    while True:
                        time.sleep(30)
                        try:
                            call_status = client.calls(current_sid).fetch().status
                            if call_status in ['completed', 'in-progress']:
                                print(f"Call answered after {attempt} attempts")
                                break
                            elif call_status in ['no-answer', 'busy', 'failed', 'canceled']:
                                attempt += 1
                                print(f"Retrying call attempt {attempt}")
                                new_c = client.calls.create(
                                    twiml=twiml,
                                    to=number,
                                    from_=TWILIO_FROM,
                                )
                                current_sid = new_c.sid
                        except Exception as e:
                            print(f"Retry error: {e}")
                            break

                t = threading.Thread(
                    target=keep_calling,
                    args=(contact["number"], twiml_msg, call.sid),
                    daemon=True
                )
                t.start()
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    # Also send WhatsApp message via CallMeBot (free, works for Nigerian numbers)
    CALLMEBOT_API = os.environ.get("CALLMEBOT_API_KEY", "")
    if CALLMEBOT_API:
        import urllib.request
        import urllib.parse
        for contact in contacts:
            try:
                wa_msg = (
                    f"🚨 EMERGENCY ALERT from SafeRoute 🚨\n\n"
                    f"Hello {contact.get('name', '')}!\n"
                    f"{uname} may need URGENT help right now!\n\n"
                    f"📍 Destination: {dest}\n"
                    f"📌 Last location: {last_location}\n\n"
                    f"Please call them IMMEDIATELY or go to their location.\n"
                    f"Do NOT ignore this message.\n\n"
                    f"- SafeRoute Safety App"
                )
                encoded = urllib.parse.quote(wa_msg)
                number = contact["number"].replace("+", "")
                url = f"https://api.callmebot.com/whatsapp.php?phone={number}&text={encoded}&apikey={CALLMEBOT_API}"
                urllib.request.urlopen(url, timeout=10)
            except Exception as e:
                print(f"WhatsApp error: {e}")

    called = [c["number"] for c in contacts]
    return jsonify({"success": True, "called": called, "duress": duress})


# ================================================================
# RUN
# ================================================================
if __name__ == "__main__":
    app.run(debug=True)