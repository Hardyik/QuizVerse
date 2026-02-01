import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import mysql
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ----------------- CONFIG -----------------
# MySQL Configuration
# Format: mysql+pymysql://username:password@host:port/database_name
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URI', 
    'mysql+pymysql://root:hardik%401310@localhost:3306/QVDB'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-here')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=8)

db = SQLAlchemy(app)
jwt = JWTManager(app)

# ----------------- MODELS -----------------
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    level = db.Column(db.Integer, default=1)
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
    
    category = db.relationship('Category', backref=db.backref('questions', lazy=True))


class Option(db.Model):
    __tablename__ = 'options'
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    
    question = db.relationship('Question', backref=db.backref('options', lazy=True))


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


# ------------- DB INITIALIZATION -------------
def init_db():
    with app.app_context():
        db.create_all()
        
        # Create default admin
        admin_user = os.getenv('ADMIN_USER', 'admin')
        admin_pass = os.getenv('ADMIN_PASS', 'QVAdmin@123')
        admin_email = os.getenv('ADMIN_EMAIL', 'admin@quizverse.com')
        
        existing = User.query.filter_by(username=admin_user).first()
        if not existing:
            admin = User(username=admin_user, email=admin_email, is_admin=True)
            admin.set_password(admin_pass)
            db.session.add(admin)
            db.session.commit()
            print(f"[INIT] Admin created -> {admin_user} / {admin_pass}")
        else:
            print("[INIT] Admin already exists")


# ------------- HELPER FUNCTIONS -------------
def admin_required(fn):
    @jwt_required()
    def wrapper(*args, **kwargs):
        identity = get_jwt_identity()
        user = User.query.filter_by(username=identity).first()
        if not user or not user.is_admin:
            return jsonify({"msg": "Admin privileges required"}), 403
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper


# ------------- MAIN PAGE ROUTES -------------
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login')
def login_page():
    return render_template('login.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/categories')
def categories_page():
    return render_template('categories.html')


@app.route('/demo')
def play():
    return render_template('demo.html')


@app.route('/admin')
def admin_panel():
    # Check if user is logged in via session
    if 'user_id' not in session:
        return redirect('/login')
    
    user = User.query.get(session['user_id'])
    if not user or not user.is_admin:
        return redirect('/login')
    
    return render_template('Admin.html')


@app.route('/user_dashboard')
def user_dashboard():
    return render_template('user_dashboard.html')


@app.route('/signup')
def signup():

    return render_template('signup.html')

@app.route('/playquiz')
def playquiz():
    return render_template('playquiz.html')

@app.route('/faq')
def faq():
       return render_template('faq.html')



# ------------- AUTH ENDPOINTS -------------
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()
    
    if not user or not user.check_password(password):
        return jsonify({"msg": "Invalid email or password"}), 401

    token = create_access_token(identity=user.username)
    
    # ADD THESE TWO LINES:
    session['user_id'] = user.id
    session['username'] = user.username
    
    return jsonify({
        "access_token": token,
        "username": user.username,
        "email": user.email,
        "is_admin": user.is_admin,
        "level": user.level
    }), 200


@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not password or not email:
        return jsonify({"msg": "username, email and password required"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"msg": "username taken"}), 409
    
    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "email already registered"}), 409

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    return jsonify({"msg": "registered successfully"}), 201

# ------------- QUIZ API ENDPOINTS -------------
@app.route('/api/categories', methods=['GET'])
def list_categories():
    cats = Category.query.all()
    return jsonify([
        {
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "icon": c.icon,
            "quiz_count": len(c.questions)
        }
        for c in cats
    ])


@app.route('/api/categories/<int:cat_id>/questions', methods=['GET'])
def get_questions(cat_id):
    limit = int(request.args.get('limit', 10))
    difficulty = request.args.get('difficulty', None)
    
    query = Question.query.filter_by(category_id=cat_id)
    if difficulty:
        query = query.filter_by(difficulty=difficulty)
    
    questions = query.limit(limit).all()

    result = []
    for q in questions:
        result.append({
            "id": q.id,
            "text": q.text,
            "difficulty": q.difficulty,
            "time_limit": q.time_limit,
            "options": [{"id": o.id, "text": o.text} for o in q.options]
        })
    return jsonify(result)


@app.route('/api/submit', methods=['POST'])
def submit_quiz():
    data = request.get_json() or {}
    answers = data.get('answers', [])
    username = data.get('username') or "Anonymous"
    category_id = data.get('category_id')
    time_taken = data.get('time_taken', 0)

    if not isinstance(answers, list) or not answers:
        return jsonify({"msg": "answers required"}), 400

    total = len(answers)
    correct = 0

    for a in answers:
        qid = a.get('question_id')
        oid = a.get('option_id')
        if not qid or not oid:
            continue
        opt = Option.query.filter_by(id=oid, question_id=qid).first()
        if opt and opt.is_correct:
            correct += 1

    # Get user if logged in
    user_id = None
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        try:
            from flask_jwt_extended import decode_token
            decoded = decode_token(token)
            user = User.query.filter_by(username=decoded['sub']).first()
            if user:
                user_id = user.id
                username = user.username
        except:
            pass

    result = Result(
        user_id=user_id,
        username=username,
        category_id=category_id,
        score=correct,
        total=total,
        time_taken=time_taken
    )
    db.session.add(result)
    db.session.commit()

    return jsonify({
        "score": correct,
        "total": total,
        "percentage": round((correct / total) * 100, 2),
        "result_id": result.id
    })


@app.route('/api/leaderboard', methods=['GET'])
def leaderboard():
    cat_id = request.args.get('category_id')
    limit = int(request.args.get('limit', 10))
    
    query = Result.query
    if cat_id:
        query = query.filter_by(category_id=int(cat_id))
    
    top = query.order_by(Result.score.desc(), Result.taken_at.asc()).limit(limit).all()

    return jsonify([
        {
            "username": r.username,
            "score": r.score,
            "total": r.total,
            "percentage": round((r.score / r.total) * 100, 2),
            "time_taken": r.time_taken,
            "taken_at": r.taken_at.isoformat()
        } for r in top
    ])


# ------------- ADMIN ENDPOINTS -------------
@app.route('/api/admin/category', methods=['POST'])
@admin_required
def create_category():
    data = request.get_json() or {}
    name = data.get('name')
    desc = data.get('description')
    icon = data.get('icon', 'fas fa-question-circle')

    if not name:
        return jsonify({"msg": "name required"}), 400

    if Category.query.filter_by(name=name).first():
        return jsonify({"msg": "category already exists"}), 409

    cat = Category(name=name, description=desc, icon=icon)
    db.session.add(cat)
    db.session.commit()
    return jsonify({"id": cat.id, "name": cat.name}), 201


@app.route('/api/admin/question', methods=['POST'])
@admin_required
def create_question():
    data = request.get_json() or {}
    cat_id = data.get('category_id')
    text = data.get('text')
    options = data.get('options', [])
    difficulty = data.get('difficulty', 'medium')
    time_limit = data.get('time_limit', 30)

    if not cat_id or not text or not options:
        return jsonify({"msg": "category_id, text and options required"}), 400

    q = Question(
        category_id=cat_id,
        text=text,
        difficulty=difficulty,
        time_limit=time_limit
    )
    db.session.add(q)
    db.session.flush()

    for opt in options:
        o = Option(
            question_id=q.id,
            text=opt.get('text'),
            is_correct=bool(opt.get('is_correct'))
        )
        db.session.add(o)

    db.session.commit()
    return jsonify({"id": q.id, "msg": "question created"}), 201


@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def admin_stats():
    total_users = User.query.count()
    total_quizzes = Question.query.count()
    total_attempts = Result.query.count()
    total_categories = Category.query.count()
    
    return jsonify({
        "total_users": total_users,
        "total_quizzes": total_quizzes,
        "total_attempts": total_attempts,
        "total_categories": total_categories
    })


# ------------- USER ENDPOINTS -------------
@app.route('/api/user/profile', methods=['GET'])
@jwt_required()
def user_profile():
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()
    
    if not user:
        return jsonify({"msg": "User not found"}), 404
    
    # Get user stats
    total_quizzes = Result.query.filter_by(user_id=user.id).count()
    recent_results = Result.query.filter_by(user_id=user.id)\
        .order_by(Result.taken_at.desc())\
        .limit(5)\
        .all()
    
    avg_score = 0
    if total_quizzes > 0:
        scores = [r.score / r.total * 100 for r in user.results]
        avg_score = sum(scores) / len(scores)
    
    return jsonify({
        "username": user.username,
        "email": user.email,
        "level": user.level,
        "total_quizzes": total_quizzes,
        "avg_score": round(avg_score, 2),
        "recent_results": [
            {
                "quiz": r.category.name if r.category else "General",
                "score": r.score,
                "total": r.total,
                "date": r.taken_at.isoformat()
            }
            for r in recent_results
        ]
    })


# ------------- HEALTH CHECK -------------
@app.route('/health', methods=['GET'])
def health():
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return jsonify({
        "status": "ok",
        "database": db_status,
        "time": datetime.utcnow().isoformat()
    })


# ------------- ERROR HANDLERS -------------
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
