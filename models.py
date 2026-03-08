from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    level = db.Column(db.Integer, default=1)
    profile_picture = db.Column(db.String(100), default='avtar1.jpg')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.String(20), default='medium')
    time_limit = db.Column(db.Integer, default=30)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    category = db.relationship('Category', backref=db.backref('questions', cascade="all, delete-orphan", lazy=True))


class Option(db.Model):
    __tablename__ = 'options'
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    
    question = db.relationship('Question', backref=db.backref('options', cascade="all, delete-orphan", lazy=True))


class Result(db.Model):
    __tablename__ = 'results'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    username = db.Column(db.String(80), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    score = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Integer, nullable=False)
    time_taken = db.Column(db.Integer, nullable=True)  # in seconds
    taken_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('results', lazy=True))
    category = db.relationship('Category', backref=db.backref('results', lazy=True))

class OTP(db.Model):
    __tablename__ = 'otps'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    otp = db.Column(db.String(6), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
class QuizSession(db.Model):
    __tablename__ = 'quiz_sessions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    question_ids = db.Column(db.Text, nullable=False) # JSON-encoded list of IDs
    current_index = db.Column(db.Integer, default=0)
    score = db.Column(db.Integer, default=0)
    user_answers = db.Column(db.Text, nullable=True) # JSON-encoded list of answers
    last_active = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('quiz_sessions', cascade="all, delete-orphan", lazy=True))
    category = db.relationship('Category', backref=db.backref('quiz_sessions', cascade="all, delete-orphan", lazy=True))


class SystemSetting(db.Model):
    __tablename__ = 'system_settings'
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(255), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # In-memory cache to avoid database hits on every request
    _cache = {}

    @staticmethod
    def get_val(key, default=None):
        # Check cache first
        if key in SystemSetting._cache:
            return SystemSetting._cache[key]
            
        setting = SystemSetting.query.get(key)
        val = setting.value if setting else default
        
        # Store in cache
        SystemSetting._cache[key] = val
        return val

    @staticmethod
    def set_val(key, value):
        setting = SystemSetting.query.get(key)
        if not setting:
            setting = SystemSetting(key=key, value=str(value))
            db.session.add(setting)
        else:
            setting.value = str(value)
        
        db.session.commit()
        
        # Update/Invalidate cache
        SystemSetting._cache[key] = str(value)

    @staticmethod
    def clear_cache():
        SystemSetting._cache = {}
