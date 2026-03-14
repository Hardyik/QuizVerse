from flask import Blueprint, request, jsonify, session
from flask_jwt_extended import create_access_token
from models import User, OTP, db # UPDATED: Added OTP
from extensions import db, jwt, mail, limiter
from flask_mail import Message
import random, string, threading
from datetime import datetime, timedelta
from flask import current_app

auth_bp = Blueprint('auth', __name__)

# ... (login/register/logout routes remain unchanged) ...

@auth_bp.route('/api/login', methods=['POST'])
@limiter.limit("10 per minute")
def api_login():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')
    is_admin_login = data.get('is_admin_login', False)
    remember_me = data.get('remember_me', False)

    user = User.query.filter_by(email=email).first()
    
    if not user or not user.check_password(password):
        return jsonify({"msg": "Invalid email or password"}), 401

    # ─── Role-mode enforcement ────────────────────────────────────────────
    if is_admin_login and not user.is_admin:
        return jsonify({"msg": "You don't have admin privileges. Please switch to User login."}), 403

    if not is_admin_login and user.is_admin:
        return jsonify({"msg": "This account has admin access. Please switch to Admin login."}), 403

    token = create_access_token(identity=user.username)
    
    # ─── Auth Session (namespaced with auth_ prefix) ─────────────────────
    session.clear()  # Clear any stale session data first
    
    if remember_me:
        session.permanent = True   # Uses PERMANENT_SESSION_LIFETIME (7 days)
    else:
        session.permanent = False  # Session cookie — dies when browser closes
    
    session['auth_user_id']  = user.id
    session['auth_username'] = user.username
    session['auth_is_admin'] = user.is_admin
    session['auth_login_at'] = datetime.utcnow().isoformat()
    
    return jsonify({
        "access_token": token,
        "username": user.username,
        "email": user.email,
        "is_admin": user.is_admin,
        "level": user.level
    }), 200

@auth_bp.route('/api/register', methods=['POST'])
@limiter.limit("5 per minute")
def register():
    data = request.get_json() or {}
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not password or not email:
        return jsonify({"msg": "username, email and password required"}), 400

    # Strong password validation
    import re
    if len(password) < 8:
        return jsonify({"msg": "Password must be at least 8 characters"}), 400
    if not re.search(r'[A-Z]', password):
        return jsonify({"msg": "Password must contain at least one uppercase letter"}), 400
    if not re.search(r'[a-z]', password):
        return jsonify({"msg": "Password must contain at least one lowercase letter"}), 400
    if not re.search(r'[0-9]', password):
        return jsonify({"msg": "Password must contain at least one number"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"msg": "username taken"}), 409
    
    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "email already registered"}), 409

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    return jsonify({"msg": "registered successfully"}), 201

@auth_bp.route('/logout')
def logout():
    session.clear()
    # Serve a tiny interstitial that clears the JWT from localStorage
    # before redirecting to /login.  Without this the login page's
    # auto-redirect script would find the old token and send the user
    # straight back in.
    return '''<!DOCTYPE html><html><head><title>Logging out…</title></head>
<body><script>
localStorage.removeItem('access_token');
window.location.replace('/login');
</script><noscript><meta http-equiv="refresh" content="0;url=/login"></noscript>
</body></html>''', 200

# ─── Forgot Password (OTP flow) ───────────────────────────────────────────────

def _generate_otp(length=6) -> str:
    return ''.join(random.choices(string.digits, k=length))

def _send_async_email(app, msg):
    with app.app_context():
        try:
            print(f"[MAIL] Attempting to send email to {msg.recipients}...")
            mail.send(msg)
            print(f"[MAIL] Email sent successfully to {msg.recipients}")
        except Exception as e:
            print(f"[MAIL] Async send failed for {msg.recipients}: {e}")
            import traceback
            traceback.print_exc()

def _send_otp_email(to_email: str, otp: str) -> bool:
    """Send OTP via Flask-Mail asynchronously."""
    try:
        sender = current_app.config.get('MAIL_DEFAULT_SENDER')
        print(f"[MAIL] Preparing OTP email for {to_email} (Sender: {sender})")
        
        msg = Message(
            subject="Your QuizVerse Password Reset OTP",
            recipients=[to_email],
            body=f"Your QuizVerse OTP is: {otp}. Valid for 10 minutes.", # Plain text fallback
            html=f"""
            <div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;padding:20px;border:1px solid #eee;border-radius:10px;">
                <h2 style="color:#4361ee;text-align:center;">QuizVerse</h2>
                <p style="font-size:16px;">Your one-time password (OTP) for password reset is:</p>
                <div style="background:#f8f9fa;padding:20px;text-align:center;border-radius:8px;margin:20px 0;">
                    <h1 style="letter-spacing:8px;color:#3a0ca3;font-size:36px;margin:0;">{otp}</h1>
                </div>
                <p style="color:#666;font-size:14px;">Valid for <strong>10 minutes</strong>. Do not share this with anyone.</p>
                <hr style="border:0;border-top:1px solid #eee;margin:20px 0;">
                <p style="font-size:12px;color:#aaa;text-align:center;">If you did not request this, please ignore this email.</p>
            </div>"""
        )
        
        # Get the underlying Flask app object from the proxy
        app = current_app._get_current_object()
        
        # For debugging on Render: Log the start of the thread
        print(f"[MAIL] Starting background thread for {to_email}")
        thread = threading.Thread(target=_send_async_email, args=(app, msg))
        thread.daemon = True # Ensure it doesn't block exit
        thread.start()
        
        return True
    except Exception as e:
        print(f"[MAIL] Could not prepare OTP email for {to_email}: {e}")
        return False


@auth_bp.route('/api/forgot-password', methods=['POST'])
@limiter.limit("3 per minute")
def forgot_password():
    data  = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()

    if not email:
        return jsonify({"msg": "Email is required"}), 400

    user = User.query.filter_by(email=email).first()
    # Always return 200 to avoid email enumeration
    if not user:
        return jsonify({"msg": "If that email exists, an OTP has been sent."}), 200

    # Clear any old OTPs for this email AND clean up any expired ones globally
    OTP.query.filter((OTP.email == email) | (OTP.expires_at < datetime.utcnow())).delete()
    db.session.commit()

    otp_code = _generate_otp()
    new_otp = OTP(
        email=email,
        otp=otp_code,
        expires_at=datetime.utcnow() + timedelta(minutes=10)
    )
    db.session.add(new_otp)
    db.session.commit()

    _send_otp_email(email, otp_code)

    return jsonify({"msg": "If that email exists, an OTP has been sent."}), 200


@auth_bp.route('/api/verify-otp', methods=['POST'])
@limiter.limit("5 per minute")
def verify_otp():
    data  = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    otp   = (data.get('otp')   or '').strip()

    if not email or not otp:
        return jsonify({"msg": "Email and OTP are required"}), 400

    record = OTP.query.filter_by(email=email, otp=otp).first()
    if not record:
        return jsonify({"msg": "Invalid OTP or incorrect email"}), 400

    if datetime.utcnow() > record.expires_at:
        db.session.delete(record)
        db.session.commit()
        return jsonify({"msg": "OTP has expired. Request a new one."}), 400

    # Mark OTP as verified
    record.is_verified = True
    db.session.commit()
    return jsonify({"msg": "OTP verified"}), 200


@auth_bp.route('/api/reset-password', methods=['POST'])
def reset_password():
    data        = request.get_json() or {}
    email       = (data.get('email')    or '').strip().lower()
    new_password = data.get('new_password') or ''
    otp         = (data.get('otp')      or '').strip()

    if not email or not new_password or not otp:
        return jsonify({"msg": "Email, OTP and new_password are required"}), 400

    record = OTP.query.filter_by(email=email, otp=otp).first()
    
    if not record or not record.is_verified:
        return jsonify({"msg": "OTP not verified or expired. Start over."}), 400

    if datetime.utcnow() > record.expires_at:
        db.session.delete(record)
        db.session.commit()
        return jsonify({"msg": "OTP expired. Request a new one."}), 400

    if len(new_password) < 8:
        return jsonify({"msg": "Password must be at least 8 characters"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"msg": "User not found"}), 404

    user.set_password(new_password)
    db.session.delete(record) # Clear the used OTP
    db.session.commit()

    return jsonify({"msg": "Password reset successfully"}), 200
