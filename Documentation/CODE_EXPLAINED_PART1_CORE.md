# 📖 QuizVerse — Line-by-Line Code Explanation (Part 1: Core Files)

---

## 1. `extensions.py`

```python
from flask_sqlalchemy import SQLAlchemy          # Line 1: Import SQLAlchemy ORM for database operations
from flask_jwt_extended import JWTManager         # Line 2: Import JWT manager for token-based authentication
from flask_mail import Mail                       # Line 3: Import Mail for sending emails (OTP)
from flask_migrate import Migrate                 # Line 4: Import Migrate for database schema migrations (Alembic)
from flask_limiter import Limiter                 # Line 5: Import Limiter for rate-limiting API endpoints
from flask_limiter.util import get_remote_address # Line 6: Import helper that extracts client IP from request

db = SQLAlchemy()                                 # Line 8:  Create SQLAlchemy instance (no app bound yet)
jwt = JWTManager()                                # Line 9:  Create JWT instance (no app bound yet)
mail = Mail()                                     # Line 10: Create Mail instance (no app bound yet)
migrate = Migrate()                               # Line 11: Create Migrate instance (no app bound yet)
limiter = Limiter(key_func=get_remote_address)    # Line 12: Create Limiter; rate-limit key = client's IP address
```

> **Why this file exists:** Flask uses the "application factory" pattern. Extensions are created here *without* an app, then bound to the app later in `app.py` via `.init_app(app)`. This prevents circular imports.

---

## 2. `config.py`

```python
import os                                         # Line 1: OS module to read environment variables
from datetime import timedelta                    # Line 2: timedelta for token/session expiry durations

try:
    from dotenv import load_dotenv                # Line 6: Try to import python-dotenv
    load_dotenv()                                 # Line 7: Load variables from .env file into os.environ
except ImportError:
    pass                                          # Line 9: If dotenv isn't installed, skip silently
```

```python
class Config:                                     # Line 11: Configuration class — Flask reads from this
    APP_VERSION = '1.0.0'                         # Line 12: Application version string

    # ─── Database ───
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI')
    # Line 16: MySQL connection string from env var, e.g. "mysql+pymysql://user:pass@host/db"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Line 17: Disable SQLAlchemy event system (saves memory, removes warning)

    # ─── Security ───
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-me-in-production')
    # Line 20: Flask session signing key. Fallback is insecure — must override in production.

    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'change-jwt-secret-too')
    # Line 21: Key used to sign/verify JWT tokens. Separate from session key.

    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    # Line 22: JWT tokens expire after 8 hours

    # ─── Session ───
    SESSION_COOKIE_NAME = 'quizverse_session'     # Line 25: Custom cookie name
    SESSION_COOKIE_HTTPONLY = True                 # Line 26: JS cannot read cookie (XSS protection)
    SESSION_COOKIE_SAMESITE = 'Lax'               # Line 27: Cookie only sent with same-site requests (CSRF protection)
    SESSION_COOKIE_SECURE = os.getenv('FLASK_ENV') == 'production'
    # Line 28: Cookie only sent over HTTPS when in production

    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    # Line 29: "Remember me" sessions last 7 days

    # ─── Admin bootstrap credentials ───
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')     # Line 32: Default admin username
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@quizverse.com')  # Line 33
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'Admin@1234')     # Line 34

    # ─── Flask-Mail (SMTP for OTP emails) ───
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')  # Line 37: SMTP server
    MAIL_PORT = int(os.getenv('MAIL_PORT', '587'))            # Line 38: SMTP port (587 = TLS)
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'  # Line 39: Enable TLS
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')             # Line 40: SMTP login email
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')             # Line 41: SMTP app password
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'QuizVerse <no-reply@quizverse.com>')
    # Line 42: "From" address shown in OTP emails
```

---

## 3. `models.py`

### User Model (Lines 5–20)
```python
class User(db.Model):
    __tablename__ = 'users'                        # Maps to 'users' table in MySQL
    id = db.Column(db.Integer, primary_key=True)   # Auto-increment primary key
    username = db.Column(db.String(80), unique=True, nullable=False)   # Unique username
    email = db.Column(db.String(120), unique=True, nullable=False)     # Unique email
    password_hash = db.Column(db.String(255), nullable=False)          # Hashed password (never plain text)
    is_admin = db.Column(db.Boolean, default=False)                    # True = admin user
    level = db.Column(db.Integer, default=1)                           # Gamification level, starts at 1
    profile_picture = db.Column(db.String(100), default='avtar1.jpg')  # Avatar filename
    created_at = db.Column(db.DateTime, default=datetime.utcnow)       # Registration timestamp

    def set_password(self, password):
        # Line 17: Hash the plain-text password using Werkzeug's generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        # Line 20: Compare plain-text password against stored hash; returns True/False
        return check_password_hash(self.password_hash, password)
```

### Category Model (Lines 23–29)
```python
class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)  # e.g. "Science", "History"
    description = db.Column(db.Text, nullable=True)                # Optional description
    icon = db.Column(db.String(50), nullable=True)                 # FontAwesome icon class
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

### Question Model (Lines 32–41)
```python
class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    # FK to categories table — every question belongs to one category
    text = db.Column(db.Text, nullable=False)           # The question text
    difficulty = db.Column(db.String(20), default='medium')  # easy/medium/hard
    time_limit = db.Column(db.Integer, default=30)      # Seconds allowed per question
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    category = db.relationship('Category', backref=db.backref('questions', cascade="all, delete-orphan", lazy=True))
    # Line 41: ORM relationship — question.category gives the Category object
    # backref: category.questions gives all questions in that category
    # cascade="all, delete-orphan": deleting a category auto-deletes its questions
```

### Option Model (Lines 44–51)
```python
class Option(db.Model):
    __tablename__ = 'options'
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)       # Option text (e.g. "Paris")
    is_correct = db.Column(db.Boolean, default=False)  # True = this is the correct answer

    question = db.relationship('Question', backref=db.backref('options', cascade="all, delete-orphan", lazy=True))
    # Cascaded delete: deleting a question auto-deletes its options
```

### Result Model (Lines 54–66)
```python
class Result(db.Model):
    __tablename__ = 'results'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Nullable for anonymous
    username = db.Column(db.String(80), nullable=False)       # Stored separately for display
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    score = db.Column(db.Integer, nullable=False)             # Number of correct answers
    total = db.Column(db.Integer, nullable=False)             # Total questions attempted
    time_taken = db.Column(db.Integer, nullable=True)         # Total seconds taken
    taken_at = db.Column(db.DateTime, default=datetime.utcnow)  # When quiz was completed

    user = db.relationship('User', backref=db.backref('results', lazy=True))
    category = db.relationship('Category', backref=db.backref('results', lazy=True))
```

### OTP Model (Lines 68–75)
```python
class OTP(db.Model):
    __tablename__ = 'otps'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)     # Email the OTP was sent to
    otp = db.Column(db.String(6), nullable=False)         # 6-digit OTP code
    expires_at = db.Column(db.DateTime, nullable=False)   # Expiry timestamp (10 min after creation)
    is_verified = db.Column(db.Boolean, default=False)    # Set True after user verifies the OTP
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

### QuizSession Model (Lines 76–88)
```python
class QuizSession(db.Model):
    __tablename__ = 'quiz_sessions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    question_ids = db.Column(db.Text, nullable=False)     # JSON string: [1, 5, 12, ...]
    current_index = db.Column(db.Integer, default=0)      # Which question user is on
    score = db.Column(db.Integer, default=0)               # Score so far
    user_answers = db.Column(db.Text, nullable=True)       # JSON: list of user's answers
    last_active = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # onupdate: automatically updates timestamp whenever the row is modified
```

### SystemSetting Model (Lines 91–130)
```python
class SystemSetting(db.Model):
    __tablename__ = 'system_settings'
    key = db.Column(db.String(50), primary_key=True)      # Setting name, e.g. "maintenance_mode"
    value = db.Column(db.String(255), nullable=False)      # Setting value, e.g. "true"
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    _cache = {}   # Line 98: Class-level dict — acts as in-memory cache to avoid DB hits

    @staticmethod
    def get_val(key, default=None):
        if key in SystemSetting._cache:      # Check cache first
            return SystemSetting._cache[key]
        setting = SystemSetting.query.get(key)  # Query DB using primary key
        val = setting.value if setting else default
        SystemSetting._cache[key] = val      # Store result in cache for future calls
        return val

    @staticmethod
    def set_val(key, value):
        setting = SystemSetting.query.get(key)
        if not setting:                        # Create new setting if doesn't exist
            setting = SystemSetting(key=key, value=str(value))
            db.session.add(setting)
        else:
            setting.value = str(value)         # Update existing setting
        db.session.commit()
        SystemSetting._cache[key] = str(value) # Update cache immediately

    @staticmethod
    def clear_cache():
        SystemSetting._cache = {}              # Wipe the in-memory cache
```

---

## 4. `app.py`

### Imports (Lines 1–11)
```python
import os
from flask import Flask, render_template, jsonify, request, session
from sqlalchemy import text                       # For raw SQL in health check
from datetime import datetime
from extensions import db, jwt, mail, migrate, limiter  # Import pre-created extension instances
from config import Config                         # Import configuration class
from routes.auth import auth_bp                   # Authentication blueprint
from routes.main import main_bp                   # Page-rendering blueprint
from routes.admin import admin_bp                 # Admin panel blueprint
from routes.api import api_bp                     # API endpoints blueprint
from models import User, SystemSetting            # Models needed at app startup
```

### Application Factory (Lines 13–48)
```python
def create_app():
    app = Flask(__name__)          # Line 14: Create Flask app instance
    app.config.from_object(Config) # Line 15: Load all Config class attributes as app config

    # Lines 18–22: Bind each extension to this app instance
    db.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)      # Migrate needs both app and db
    limiter.init_app(app)

    # Lines 25–28: Register all 4 blueprints (modular route groups)
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # Lines 31–33: Inside app context, create tables & bootstrap admin
    with app.app_context():
        create_admin_if_not_exists()
```

### Session Restore Hook (Lines 35–62)
```python
    @app.before_request
    def restore_session_from_jwt():
        # Runs BEFORE every request. If session cookie is missing but
        # the request has a valid JWT Bearer token, re-populate the session.
        if session.get('auth_user_id'):
            return                          # Session already exists — skip

        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return                          # No token — skip

        try:
            from flask_jwt_extended import decode_token
            token = auth_header.split(' ', 1)[1]  # Extract token after "Bearer "
            decoded = decode_token(token)          # Decode & verify JWT signature
            username = decoded.get('sub')          # 'sub' claim = username (identity)
            if username:
                user = User.query.filter_by(username=username).first()
                if user:
                    session.permanent = True                # Use 7-day lifetime
                    session['auth_user_id']  = user.id
                    session['auth_username'] = user.username
                    session['auth_is_admin'] = user.is_admin
                    session['auth_login_at'] = datetime.utcnow().isoformat()
        except Exception:
            pass  # Token invalid or expired — silently ignore
```

### Maintenance Mode Hook (Lines 78–100)
```python
    @app.before_request
    def check_maintenance():
        # Skip maintenance check for essential routes
        if request.path.startswith('/static') or \
           request.path in ['/login', '/logout', '/api/login', '/api/logout',
                           '/api/auth/status', '/maintenance']:
            return

        # Query the system_settings table for maintenance_mode
        is_maintenance = SystemSetting.get_val('maintenance_mode', 'false') == 'true'

        if is_maintenance:
            is_admin = session.get('auth_is_admin', False)
            if not is_admin:
                # Non-admin users see the maintenance page with 503 status
                return render_template('includes/maintenance.html'), 503
```

### Error Handlers & Health (Lines 102–148)
```python
    # Lines 103-133: Custom error handlers for HTTP status codes
    # 400 → JSON "Bad Request"
    # 401 → JSON "Unauthorized"
    # 403 → JSON "Forbidden"
    # 404 → JSON for /api/ routes, HTML 404.html for page routes
    # 405 → JSON "Method Not Allowed"
    # 500 → Logs error, JSON for /api/, HTML 500.html for pages

    @app.route('/health')
    def health():
        # Lines 136-146: Health check endpoint
        try:
            db.session.execute(text('SELECT 1'))  # Quick DB ping
            db_status = "connected"
        except Exception as e:
            db_status = f"error: {str(e)}"
        return jsonify({
            "status": "ok",
            "database": db_status,
            "time": datetime.utcnow().isoformat()  # Server timestamp
        })

    return app                                     # Line 148: Return the configured app
```

### Admin Bootstrap (Lines 150–167)
```python
def create_admin_if_not_exists():
    admin_user  = current_app.config.get('ADMIN_USERNAME', 'admin')
    admin_pass  = current_app.config.get('ADMIN_PASSWORD', 'Admin@1234')
    admin_email = current_app.config.get('ADMIN_EMAIL', 'admin@quizverse.com')

    existing = User.query.filter_by(username=admin_user).first()
    if not existing:
        admin = User(username=admin_user, email=admin_email, is_admin=True)
        admin.set_password(admin_pass)             # Hash the password
        db.session.add(admin)
        db.session.commit()
        print(f"[INIT] Admin created -> {admin_user}")
    else:
        print("[INIT] Admin already exists")
```

### Entry Point (Lines 169–172)
```python
app = create_app()             # Line 169: Create the app at module level (used by gunicorn too)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
    # Line 172: Run dev server on all interfaces, port 5000, with debug mode
```

---

*Continued in Part 2 → `CODE_EXPLAINED_PART2_ROUTES.md`*
