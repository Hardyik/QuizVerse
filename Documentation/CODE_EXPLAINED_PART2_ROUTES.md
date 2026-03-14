# 📖 QuizVerse — Line-by-Line Code Explanation (Part 2: Routes — auth.py & main.py)

---

## 1. `routes/auth.py` — Authentication Blueprint

### Imports & Blueprint Setup (Lines 1–9)
```python
from flask import Blueprint, request, jsonify, session
from flask_jwt_extended import create_access_token   # Creates signed JWT tokens
from models import User, OTP, db
from extensions import db, jwt, mail, limiter        # Rate limiter, mailer
from flask_mail import Message                       # Email message object
import random, string                                # For OTP generation
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__)
# Line 9: Create a Blueprint named 'auth' — groups all auth routes together
```

### Login Endpoint (Lines 13–55)
```python
@auth_bp.route('/api/login', methods=['POST'])
@limiter.limit("10 per minute")           # Max 10 login attempts per minute per IP
def api_login():
    data = request.get_json() or {}       # Parse JSON body (or empty dict if none)
    email = data.get('email')
    password = data.get('password')
    is_admin_login = data.get('is_admin_login', False)  # True if admin login toggle is on
    remember_me = data.get('remember_me', False)

    user = User.query.filter_by(email=email).first()  # Find user by email

    if not user or not user.check_password(password):
        return jsonify({"msg": "Invalid email or password"}), 401  # 401 Unauthorized

    # ─── Role-mode enforcement ───
    if is_admin_login and not user.is_admin:
        # User tried admin login but isn't admin
        return jsonify({"msg": "You don't have admin privileges..."}), 403

    if not is_admin_login and user.is_admin:
        # Admin tried user login — must use admin login mode
        return jsonify({"msg": "This account has admin access..."}), 403

    token = create_access_token(identity=user.username)
    # Line 34: Create a JWT with the username as the "sub" (subject) claim

    session.clear()                        # Wipe any stale session data

    if remember_me:
        session.permanent = True           # Cookie persists for 7 days (PERMANENT_SESSION_LIFETIME)
    else:
        session.permanent = False          # Cookie dies when browser closes

    # Store auth info in Flask server-side session
    session['auth_user_id']  = user.id
    session['auth_username'] = user.username
    session['auth_is_admin'] = user.is_admin
    session['auth_login_at'] = datetime.utcnow().isoformat()

    return jsonify({
        "access_token": token,             # JWT for API calls (stored in localStorage)
        "username": user.username,
        "email": user.email,
        "is_admin": user.is_admin,
        "level": user.level
    }), 200
```

### Registration Endpoint (Lines 57–90)
```python
@auth_bp.route('/api/register', methods=['POST'])
@limiter.limit("5 per minute")            # Max 5 registrations per minute per IP
def register():
    data = request.get_json() or {}
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not password or not email:
        return jsonify({"msg": "username, email and password required"}), 400

    # ─── Strong password validation (Lines 69–77) ───
    import re
    if len(password) < 8:                  # Minimum 8 characters
        return jsonify({"msg": "Password must be at least 8 characters"}), 400
    if not re.search(r'[A-Z]', password):  # At least one uppercase letter
        return jsonify({"msg": "...uppercase letter"}), 400
    if not re.search(r'[a-z]', password):  # At least one lowercase letter
        return jsonify({"msg": "...lowercase letter"}), 400
    if not re.search(r'[0-9]', password):  # At least one digit
        return jsonify({"msg": "...one number"}), 400

    # ─── Uniqueness checks ───
    if User.query.filter_by(username=username).first():
        return jsonify({"msg": "username taken"}), 409       # 409 Conflict

    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "email already registered"}), 409

    # Create and save user
    user = User(username=username, email=email)
    user.set_password(password)            # Hash the password
    db.session.add(user)
    db.session.commit()
    return jsonify({"msg": "registered successfully"}), 201  # 201 Created
```

### Logout (Lines 92–104)
```python
@auth_bp.route('/logout')
def logout():
    session.clear()                        # Destroy all server-side session data
    # Returns a small HTML page with JS that:
    # 1. Removes 'access_token' from localStorage (client-side JWT cleanup)
    # 2. Redirects to /login
    # <noscript> fallback: meta refresh redirect for browsers without JS
    return '''<!DOCTYPE html>...<script>
    localStorage.removeItem('access_token');
    window.location.replace('/login');
    </script>...''', 200
```

### Forgot Password — OTP Generation (Lines 108–164)
```python
def _generate_otp(length=6) -> str:
    # Line 109: Generate 6 random digits, e.g. "483921"
    return ''.join(random.choices(string.digits, k=length))

def _send_otp_email(to_email: str, otp: str) -> bool:
    # Lines 112-132: Send a styled HTML email with the OTP via Flask-Mail
    try:
        msg = Message(subject="Your QuizVerse Password Reset OTP",
                      recipients=[to_email],
                      html=f"...{otp}...")  # OTP displayed in large styled text
        mail.send(msg)                     # Send via SMTP configured in config.py
        return True
    except Exception as e:
        print(f"[MAIL] Could not send OTP email: {e}")
        print(f"[MAIL] DEV OTP for {to_email}: {otp}")  # Print OTP to console in dev
        return False

@auth_bp.route('/api/forgot-password', methods=['POST'])
@limiter.limit("3 per minute")            # Only 3 OTP requests per minute (brute-force protection)
def forgot_password():
    email = (data.get('email') or '').strip().lower()

    user = User.query.filter_by(email=email).first()
    if not user:
        # SECURITY: Return same message whether email exists or not
        # This prevents email enumeration attacks
        return jsonify({"msg": "If that email exists, an OTP has been sent."}), 200

    # Delete old OTPs for this email AND any globally expired OTPs
    OTP.query.filter((OTP.email == email) | (OTP.expires_at < datetime.utcnow())).delete()
    db.session.commit()

    otp_code = _generate_otp()
    new_otp = OTP(email=email, otp=otp_code,
                  expires_at=datetime.utcnow() + timedelta(minutes=10))  # 10-min expiry
    db.session.add(new_otp)
    db.session.commit()

    _send_otp_email(email, otp_code)       # Send the email
    return jsonify({"msg": "If that email exists, an OTP has been sent."}), 200
```

### OTP Verification & Password Reset (Lines 167–224)
```python
@auth_bp.route('/api/verify-otp', methods=['POST'])
@limiter.limit("5 per minute")
def verify_otp():
    # Find OTP record matching email + code
    record = OTP.query.filter_by(email=email, otp=otp).first()
    if not record:
        return jsonify({"msg": "Invalid OTP or incorrect email"}), 400

    if datetime.utcnow() > record.expires_at:     # Check if expired
        db.session.delete(record)
        db.session.commit()
        return jsonify({"msg": "OTP has expired. Request a new one."}), 400

    record.is_verified = True                      # Mark OTP as verified
    db.session.commit()
    return jsonify({"msg": "OTP verified"}), 200

@auth_bp.route('/api/reset-password', methods=['POST'])
def reset_password():
    # Requires: email + OTP (must be verified) + new_password
    record = OTP.query.filter_by(email=email, otp=otp).first()

    if not record or not record.is_verified:
        return jsonify({"msg": "OTP not verified or expired"}), 400

    if datetime.utcnow() > record.expires_at:      # Double-check expiry
        return jsonify({"msg": "OTP expired"}), 400

    if len(new_password) < 8:
        return jsonify({"msg": "Password must be at least 8 characters"}), 400

    user = User.query.filter_by(email=email).first()
    user.set_password(new_password)                 # Hash new password
    db.session.delete(record)                       # Delete used OTP
    db.session.commit()
    return jsonify({"msg": "Password reset successfully"}), 200
```

---

## 2. `routes/main.py` — Page Rendering Blueprint

### Helper Functions (Lines 9–82)
```python
def _try_restore_session():
    # Lines 9-30: Try to restore session from the JWT in the Authorization header
    # Used for AJAX/fetch calls that include the token in headers
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return False                               # No token present
    try:
        token = auth_header.split(' ', 1)[1]
        decoded = decode_token(token)              # Verify JWT signature & decode
        username = decoded.get('sub')
        user = User.query.filter_by(username=username).first()
        if user:
            session.permanent = True
            session['auth_user_id'] = user.id      # Populate session from JWT data
            session['auth_username'] = user.username
            session['auth_is_admin'] = user.is_admin
            return True
    except Exception:
        pass
    return False

def _login_required_or_restore():
    # Lines 33-48: Auth guard for protected pages
    if session.get('auth_user_id'):
        return None                                # Already authenticated — allow
    if _try_restore_session():
        return None                                # Restored from header — allow
    # Neither worked → serve the restore interstitial page
    return _session_restore_page(next_url)

def _session_restore_page(next_url):
    # Lines 51-82: Returns a small HTML page that:
    # 1. Shows a loading spinner ("Restoring your session…")
    # 2. Reads JWT from localStorage
    # 3. Calls /api/auth/session-check with Bearer token via fetch()
    # 4. If session restored → redirects to the original page (next_url)
    # 5. If no token → redirects to /login?next=<next_url>
    # This bridges the gap between JWT (in localStorage) and Flask session (in cookie)
```

### Public Routes — No Login Required (Lines 85–118)
```python
@main_bp.route('/')
def index():
    return render_template('index.html')           # Landing page

@main_bp.route('/login')
def login_page():
    return render_template('login.html')           # Login form

@main_bp.route('/signup')
def signup():
    return render_template('signup.html')           # Registration form

@main_bp.route('/about')
def about():
    return render_template('about.html')            # About/team page

@main_bp.route('/explore')
def categories_page():
    return render_template('explore.html')           # Browse categories

@main_bp.route('/demo')
def play():
    return render_template('demo.html')              # Demo quiz (no login needed)

@main_bp.route('/faq')
def faq():
    return render_template('faq.html')               # FAQ page

@main_bp.route('/forget_pass')
def forget_pass():
    return render_template('forget_pass.html')       # Forgot password flow

@main_bp.route('/leaderboard')
def leaderboard_page():
    return render_template('leaderboard.html')       # Public leaderboard
```

### Protected Routes — Login Required (Lines 109–162)
```python
@main_bp.route('/random')
def random_quiz():
    guard = _login_required_or_restore()   # Check auth
    if guard:
        return guard                       # Returns restore page or redirect to login
    return render_template('random.html')

@main_bp.route('/play_quiz')
def play_quiz():
    guard = _login_required_or_restore()
    if guard: return guard
    return render_template('play_quiz.html')         # Active quiz page

@main_bp.route('/profile')
def profile_page():
    guard = _login_required_or_restore()
    if guard: return guard
    return render_template('profile.html')            # User profile editor

@main_bp.route('/user_dashboard')
def user_dashboard():
    guard = _login_required_or_restore()
    if guard: return guard
    return render_template('user_dashboard.html')     # Dashboard with history

@main_bp.route('/select_quiz')
def select_quiz():
    guard = _login_required_or_restore()
    if guard: return guard
    return render_template('select_quiz.html')        # Category selection

@main_bp.route('/analytics')
def analytics_page():
    guard = _login_required_or_restore()
    if guard: return guard
    return render_template('analytics.html')          # User analytics charts
```

> **Pattern:** Every protected route calls `_login_required_or_restore()`. If it returns `None`, the user is authenticated and the template is served. If it returns a response (the restore interstitial page), that response is returned instead.

---

*Continued in Part 3 → `CODE_EXPLAINED_PART3_ADMIN_API.md`*
