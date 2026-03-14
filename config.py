import os
from datetime import timedelta

# Load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not required; set envvars manually or via system

class Config:
    APP_VERSION = '1.0.0'
    # ─── Database ─────────────────────────────────────────────────────────────
    # Reads from env; falls back to local dev default if not set.
    # We check multiple common names (DATABASE_URI, DATABASE_URL, SQLALCHEMY_DATABASE_URI)
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI') or \
                              os.getenv('DATABASE_URL') or \
                              os.getenv('SQLALCHEMY_DATABASE_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ─── Security ─────────────────────────────────────────────────────────────
    SECRET_KEY          = os.getenv('SECRET_KEY',     'change-me-in-production')
    JWT_SECRET_KEY      = os.getenv('JWT_SECRET_KEY', 'change-jwt-secret-too')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)

    # ─── Session Configuration ────────────────────────────────────────────────
    SESSION_COOKIE_NAME     = 'quizverse_session'
    SESSION_COOKIE_HTTPONLY = True                          # JS can't read the cookie
    SESSION_COOKIE_SAMESITE = 'Lax'                        # CSRF protection
    SESSION_COOKIE_SECURE   = os.getenv('FLASK_ENV') == 'production'  # HTTPS only in prod
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)         # "Remember me" sessions last 7 days

    # ─── Admin bootstrap credentials ──────────────────────────────────────────
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_EMAIL    = os.getenv('ADMIN_EMAIL',    'admin@quizverse.com')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'Admin@1234')

    # ─── Flask-Mail (forgot-password OTP) ─────────────────────────────────────
    MAIL_SERVER         = os.getenv('MAIL_SERVER',   'smtp.gmail.com')
    MAIL_PORT           = int(os.getenv('MAIL_PORT', '587'))
    MAIL_USE_SSL        = os.getenv('MAIL_USE_SSL',  'False').lower() == 'true'
    MAIL_USE_TLS        = os.getenv('MAIL_USE_TLS',  'True' if not MAIL_USE_SSL else 'False').lower() == 'true'
    MAIL_USERNAME       = os.getenv('MAIL_USERNAME',  '')
    MAIL_PASSWORD       = os.getenv('MAIL_PASSWORD',  '')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER') or os.getenv('MAIL_USERNAME') or 'QuizVerse <no-reply@quizverse.com>'
