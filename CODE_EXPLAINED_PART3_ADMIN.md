# 📖 QuizVerse — Line-by-Line Code Explanation (Part 3: Routes — admin.py)

---

## `routes/admin.py` — Admin Panel Blueprint

### Imports & Blueprint (Lines 1–8)
```python
from flask import Blueprint, render_template, redirect, session, jsonify, request, current_app
from models import User, Category, Question, Option, Result, SystemSetting, db
from flask_jwt_extended import jwt_required, get_jwt_identity, decode_token
from datetime import datetime, timedelta
from sqlalchemy import func, text       # func for SQL aggregation, text for raw SQL
import sys                               # For Python version in system info

admin_bp = Blueprint('admin', __name__)  # Blueprint for all /admin routes
```

### Admin Auth Guard (Lines 11–89)
```python
def _admin_login_or_restore():
    # Lines 11-78: Checks if the current user is an admin
    # Step 1: Check Flask session
    user_id = session.get('auth_user_id')
    if user_id:
        user = User.query.get(user_id)           # Fetch user from DB
        if user and user.is_admin:
            return None                           # ✅ Admin session OK
        return redirect('/login')                 # Session exists but not admin → redirect

    # Step 2: No session — try restoring from JWT in Authorization header (for AJAX calls)
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        try:
            token = auth_header.split(' ', 1)[1]
            decoded = decode_token(token)          # Decode JWT
            username = decoded.get('sub')
            user = User.query.filter_by(username=username).first()
            if user and user.is_admin:
                # Populate the session from JWT data
                session.permanent = True
                session['auth_user_id']  = user.id
                session['auth_username'] = user.username
                session['auth_is_admin'] = user.is_admin
                session['auth_login_at'] = datetime.utcnow().isoformat()
                return None                        # ✅ Admin restored from JWT
        except Exception:
            pass

    # Step 3: Serve restore interstitial page (same concept as main.py)
    # JS reads JWT from localStorage → calls /api/auth/session-check
    # If admin → reloads page; otherwise → redirects to /login
    return _admin_restore_page(next_url)

def admin_required_decorator(fn):
    # Lines 80-89: Decorator for admin-only API endpoints
    @jwt_required()                               # First: require valid JWT
    def wrapper(*args, **kwargs):
        identity = get_jwt_identity()             # Get username from JWT
        user = User.query.filter_by(username=identity).first()
        if not user or not user.is_admin:
            return jsonify({"msg": "Admin privileges required"}), 403  # Not admin → 403
        return fn(*args, **kwargs)                # Admin ✅ → run the actual function
    wrapper.__name__ = fn.__name__                # Preserve function name for Flask routing
    return wrapper
```

### Admin Page Routes (Lines 91–127)
```python
@admin_bp.route('/admin')
def admin_panel():
    guard = _admin_login_or_restore()             # Admin auth check
    if guard: return guard
    total_users = User.query.count()              # Pass total users to template
    return render_template('includes/Admin.html', total_users=total_users)

@admin_bp.route('/admin/users')                   # User management page
@admin_bp.route('/admin/quizzes')                  # Quiz CRUD page
@admin_bp.route('/admin/settings')                 # Settings page
@admin_bp.route('/admin/analytics')                # Analytics page
# Each follows same pattern: guard → render template
```

### User Management APIs (Lines 160–218)
```python
@admin_bp.route('/api/admin/user/<int:user_id>', methods=['DELETE'])
@admin_required_decorator                          # JWT + admin check
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user: return jsonify({"msg": "User not found"}), 404
    if user.is_admin: return jsonify({"msg": "Cannot delete admin"}), 403  # Safety check
    db.session.delete(user)
    db.session.commit()
    return jsonify({"msg": "User deleted"}), 200

@admin_bp.route('/api/admin/user/<int:user_id>/toggle-admin', methods=['POST'])
@admin_required_decorator
def toggle_admin(user_id):
    user = User.query.get(user_id)
    identity = get_jwt_identity()
    if user.username == identity:
        return jsonify({"msg": "Cannot demote yourself"}), 400  # Self-demotion blocked
    user.is_admin = not user.is_admin              # Toggle admin flag
    db.session.commit()
    return jsonify({"msg": f"User {'promoted to' if user.is_admin else 'demoted from'} admin"}), 200

@admin_bp.route('/api/admin/users', methods=['GET'])
@admin_required_decorator
def api_list_users():
    page = int(request.args.get('page', 1))        # Pagination: current page
    per_page = int(request.args.get('per_page', 10))
    search = request.args.get('search', '').strip()

    query = User.query
    if search:
        # Search by username OR email (case-insensitive with ILIKE)
        query = query.filter(User.username.ilike(f'%{search}%') | User.email.ilike(f'%{search}%'))

    pagination = query.order_by(User.id.desc()).paginate(page=page, per_page=per_page)
    # .paginate() returns a Pagination object with .items, .total, .pages, .page

    return jsonify({
        "users": [{"id": u.id, "username": u.username, ...} for u in pagination.items],
        "total": pagination.total,
        "pages": pagination.pages,
        "current_page": pagination.page
    })
```

### Category CRUD APIs (Lines 220–266)
```python
@admin_bp.route('/api/admin/category', methods=['POST'])
@admin_required_decorator
def create_category():
    name = data.get('name')
    desc = data.get('description')
    icon = data.get('icon', 'fas fa-question-circle')  # Default icon

    if Category.query.filter_by(name=name).first():
        return jsonify({"msg": "category already exists"}), 409  # Duplicate check

    cat = Category(name=name, description=desc, icon=icon)
    db.session.add(cat)
    db.session.commit()
    return jsonify({"id": cat.id, "name": cat.name}), 201

# PATCH /api/admin/category/<id> → Update name/description/icon
# DELETE /api/admin/category/<id> → Delete category (cascades to questions & options)
```

### Question CRUD APIs (Lines 268–375)
```python
@admin_bp.route('/api/admin/question', methods=['POST'])
@admin_required_decorator
def create_question():
    cat_id = data.get('category_id')
    text = data.get('text')
    options = data.get('options', [])  # List of {text, is_correct}
    difficulty = data.get('difficulty', 'medium')
    time_limit = data.get('time_limit', 30)

    q = Question(category_id=cat_id, text=text, difficulty=difficulty, time_limit=time_limit)
    db.session.add(q)
    db.session.flush()                 # Flush to get q.id before commit (for FK in options)

    for opt in options:
        o = Option(question_id=q.id, text=opt.get('text'), is_correct=bool(opt.get('is_correct')))
        db.session.add(o)

    db.session.commit()
    return jsonify({"id": q.id, "msg": "question created"}), 201

# PATCH /api/admin/question/<id>:
#   - Updates text, difficulty, time_limit, category_id
#   - If options provided: deletes ALL old options → creates new ones (replace strategy)

# GET /api/admin/questions:
#   - Paginated list with optional category_id filter and search
#   - Returns question text, category name, difficulty, time_limit, options

# DELETE /api/admin/question/<id> → Delete question (cascades to options)
```

### Admin Stats Dashboard API (Lines 377–429)
```python
@admin_bp.route('/api/admin/stats', methods=['GET'])
@admin_required_decorator
def admin_stats():
    total_users = User.query.count()
    total_quizzes = Question.query.count()         # Total questions in system
    total_attempts = Result.query.count()           # Total quiz attempts
    total_categories = Category.query.count()

    # Recent activity feed: last 5 new users + last 5 quiz results
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_results = Result.query.order_by(Result.taken_at.desc()).limit(5).all()

    activity = []
    for u in recent_users:
        activity.append({"type": "user", "message": f"New user joined: {u.username}", ...})
    for r in recent_results:
        activity.append({"type": "quiz", "message": f"{r.username} completed...", ...})

    activity.sort(key=lambda x: x['time'], reverse=True)  # Merge & sort by time
    activity = activity[:15]                       # Keep latest 15

    # Chart data: quiz attempts per day for last 7 days
    chart_data = []
    today = datetime.utcnow().date()
    for i in range(6, -1, -1):                     # 6 days ago → today
        day = today - timedelta(days=i)
        count = Result.query.filter(func.date(Result.taken_at) == day).count()
        # func.date() extracts date from datetime column for comparison
        chart_data.append({"date": day.strftime("%b %d"), "count": count})

    return jsonify({
        "total_users": total_users, "total_quizzes": total_quizzes,
        "total_attempts": total_attempts, "total_categories": total_categories,
        "activity": activity, "chart_data": chart_data
    })
```

### Settings APIs (Lines 431–475)
```python
@admin_bp.route('/api/admin/settings', methods=['GET'])
@admin_required_decorator
def get_settings():
    # Read settings from SystemSetting key-value store
    maintenance = SystemSetting.get_val('maintenance_mode', 'false')
    admin_only_quiz = SystemSetting.get_val('admin_only_quiz', 'true')
    email_notifications = SystemSetting.get_val('email_notifications', 'false')

    # Dynamic system info
    db_status = "Connected"
    try:
        db.session.execute(text('SELECT 1'))       # Quick DB ping
    except Exception:
        db_status = "Disconnected"

    return jsonify({
        "settings": {
            "maintenance_mode": maintenance == 'true',      # Convert string → boolean
            "admin_only_quiz": admin_only_quiz == 'true',
            "email_notifications": email_notifications == 'true'
        },
        "system_info": {
            "version": current_app.config.get('APP_VERSION', '1.0.0'),
            "environment": "Development" if current_app.debug else "Production",
            "db_status": db_status,
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "db_type": "MySQL"
        }
    })

@admin_bp.route('/api/admin/settings', methods=['PATCH'])
@admin_required_decorator
def update_settings():
    data = request.get_json() or {}
    # Toggle each setting if present in the request body
    if 'maintenance_mode' in data:
        SystemSetting.set_val('maintenance_mode', 'true' if data['maintenance_mode'] else 'false')
    if 'admin_only_quiz' in data:
        SystemSetting.set_val('admin_only_quiz', 'true' if data['admin_only_quiz'] else 'false')
    if 'email_notifications' in data:
        SystemSetting.set_val('email_notifications', 'true' if data['email_notifications'] else 'false')
    return jsonify({"msg": "Settings updated"}), 200
```

---

*Continued in Part 4 → `CODE_EXPLAINED_PART4_API_STATIC.md`*
