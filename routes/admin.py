from flask import Blueprint, render_template, redirect, session, jsonify, request, current_app
from models import User, Category, Question, Option, Result, SystemSetting, db
from flask_jwt_extended import jwt_required, get_jwt_identity, decode_token
from datetime import datetime, timedelta
from sqlalchemy import func, text
import sys

admin_bp = Blueprint('admin', __name__)


def _admin_login_or_restore():
    """Check if the current session belongs to an admin.
    If the session is empty but a valid JWT exists in localStorage,
    serve a restore interstitial page instead of redirecting to login."""
    user_id = session.get('auth_user_id')
    if user_id:
        user = User.query.get(user_id)
        if user and user.is_admin:
            return None  # Session OK, user is admin
        return redirect('/login')  # Session exists but not admin

    # No session — try header-based restore (covers fetch calls)
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        try:
            token = auth_header.split(' ', 1)[1]
            decoded = decode_token(token)
            username = decoded.get('sub')
            if username:
                user = User.query.filter_by(username=username).first()
                if user and user.is_admin:
                    session.permanent = True
                    session['auth_user_id']  = user.id
                    session['auth_username'] = user.username
                    session['auth_is_admin'] = user.is_admin
                    session['auth_login_at'] = datetime.utcnow().isoformat()
                    return None
        except Exception:
            pass

    # For browser navigation, serve a restore page
    next_url = request.path
    if request.query_string:
        next_url += '?' + request.query_string.decode()
    return _admin_restore_page(next_url)


def _admin_restore_page(next_url):
    """Serve a small interstitial that tries to restore the admin session
    from the JWT in localStorage before redirecting to login."""
    return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Restoring session…</title>
<style>
body {{ display:flex;align-items:center;justify-content:center;
       height:100vh;margin:0;font-family:sans-serif;
       background:linear-gradient(135deg,#667eea,#764ba2);color:#fff; }}
.loader {{ text-align:center }}
.spinner {{ width:40px;height:40px;border:4px solid rgba(255,255,255,.3);
           border-top-color:#fff;border-radius:50%;
           animation:spin .8s linear infinite;margin:0 auto 16px }}
@keyframes spin {{ to {{ transform:rotate(360deg) }} }}
</style></head>
<body><div class="loader"><div class="spinner"></div><p>Restoring session…</p></div>
<script>
(async()=>{{
  const token=localStorage.getItem("access_token");
  if(!token){{ window.location.href="/login?next={next_url}"; return; }}
  try{{
    const r=await fetch("/api/auth/session-check",{{
      headers:{{"Authorization":"Bearer "+token}}
    }});
    const d=await r.json();
    if(d.logged_in && d.is_admin){{ window.location.replace("{next_url}"); return; }}
  }}catch(e){{}}
  localStorage.removeItem("access_token");
  window.location.href="/login?next={next_url}";
}})();
</script></body></html>''', 200

def admin_required_decorator(fn):
    @jwt_required()
    def wrapper(*args, **kwargs):
        identity = get_jwt_identity()
        user = User.query.filter_by(username=identity).first()
        if not user or not user.is_admin:
            return jsonify({"msg": "Admin privileges required"}), 403
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper

@admin_bp.route('/admin')
def admin_panel():
    guard = _admin_login_or_restore()
    if guard:
        return guard
    total_users = User.query.count()
    return render_template('includes/Admin.html', total_users=total_users)

@admin_bp.route('/admin/users')
def list_users():
    guard = _admin_login_or_restore()
    if guard:
        return guard
    user = User.query.get(session['auth_user_id'])
    users = User.query.filter(User.id != user.id).all()
    return render_template('includes/admin_users.html', users=users)

@admin_bp.route('/admin/quizzes')
def quiz_management():
    guard = _admin_login_or_restore()
    if guard:
        return guard
    return render_template('includes/admin_quiz.html')

@admin_bp.route('/admin/settings')
def admin_settings():
    guard = _admin_login_or_restore()
    if guard:
        return guard
    return render_template('includes/admin_settings.html')

@admin_bp.route('/admin/analytics')
def admin_analytics_page():
    guard = _admin_login_or_restore()
    if guard:
        return guard
    return render_template('includes/admin_analytics.html')

@admin_bp.route('/api/admin/analytics/categories', methods=['GET'])
@admin_required_decorator
def admin_analytics_categories():
    # Fetch all results
    results = Result.query.all()
    
    # Process attempts per category
    category_counts = {}
    for r in results:
        cat_name = r.category.name if r.category else "Unknown"
        if cat_name not in category_counts:
            category_counts[cat_name] = 0
        category_counts[cat_name] += 1
        
    # Format into a sorted list
    stats_list = []
    for cat, count in category_counts.items():
        stats_list.append({
            "category": cat,
            "attempts": count
        })
        
    # Sort descending by attempts
    stats_list.sort(key=lambda x: x['attempts'], reverse=True)
    
    return jsonify({
        "total_categories_attempted": len(category_counts),
        "most_viewed": stats_list[0] if stats_list else None,
        "category_stats": stats_list
    })

@admin_bp.route('/api/admin/user/<int:user_id>', methods=['DELETE'])
@admin_required_decorator
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404
        
    if user.is_admin:
         return jsonify({"msg": "Cannot delete admin"}), 403

    db.session.delete(user)
    db.session.commit()
    return jsonify({"msg": "User deleted"}), 200

@admin_bp.route('/api/admin/user/<int:user_id>/toggle-admin', methods=['POST'])
@admin_required_decorator
def toggle_admin(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404
        
    # Prevent self-demotion for safety (optional but good)
    identity = get_jwt_identity()
    if user.username == identity:
        return jsonify({"msg": "Cannot demote yourself"}), 400

    user.is_admin = not user.is_admin
    db.session.commit()
    return jsonify({"msg": f"User {'promoted to' if user.is_admin else 'demoted from'} admin"}), 200

@admin_bp.route('/api/admin/users', methods=['GET'])
@admin_required_decorator
def api_list_users():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    search = request.args.get('search', '').strip()
    
    query = User.query
    if search:
        query = query.filter(User.username.ilike(f'%{search}%') | User.email.ilike(f'%{search}%'))
        
    pagination = query.order_by(User.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "is_admin": u.is_admin,
                "level": u.level,
                "created_at": u.created_at.strftime('%Y-%m-%d') if u.created_at else 'N/A'
            }
            for u in pagination.items
        ],
        "total": pagination.total,
        "pages": pagination.pages,
        "current_page": pagination.page
    })

@admin_bp.route('/api/admin/category', methods=['POST'])
@admin_required_decorator
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

@admin_bp.route('/api/admin/category/<int:cat_id>', methods=['PATCH'])
@admin_required_decorator
def update_category(cat_id):
    cat = Category.query.get(cat_id)
    if not cat:
        return jsonify({"msg": "Category not found"}), 404
        
    data = request.get_json() or {}
    if 'name' in data:
        cat.name = data['name']
    if 'description' in data:
        cat.description = data['description']
    if 'icon' in data:
        cat.icon = data['icon']
        
    db.session.commit()
    return jsonify({"msg": "Category updated"}), 200

@admin_bp.route('/api/admin/category/<int:cat_id>', methods=['DELETE'])
@admin_required_decorator
def delete_category(cat_id):
    cat = Category.query.get(cat_id)
    if not cat:
        return jsonify({"msg": "Category not found"}), 404
    
    db.session.delete(cat)
    db.session.commit()
    return jsonify({"msg": "Category deleted"}), 200

@admin_bp.route('/api/admin/question', methods=['POST'])
@admin_required_decorator
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

@admin_bp.route('/api/admin/question/<int:q_id>', methods=['PATCH'])
@admin_required_decorator
def update_question(q_id):
    q = Question.query.get(q_id)
    if not q:
        return jsonify({"msg": "Question not found"}), 404
        
    data = request.get_json() or {}
    if 'text' in data:
        q.text = data['text']
    if 'difficulty' in data:
        q.difficulty = data['difficulty']
    if 'time_limit' in data:
        q.time_limit = data['time_limit']
    if 'category_id' in data:
        q.category_id = data['category_id']
        
    if 'options' in data:
        # Simplest way: delete old options and add new ones
        Option.query.filter_by(question_id=q_id).delete()
        for opt in data['options']:
            o = Option(
                question_id=q.id,
                text=opt.get('text'),
                is_correct=bool(opt.get('is_correct'))
            )
            db.session.add(o)
            
    db.session.commit()
    return jsonify({"msg": "Question updated"}), 200

@admin_bp.route('/api/admin/questions', methods=['GET'])
@admin_required_decorator
def list_questions():
    cat_id = request.args.get('category_id')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    search = request.args.get('search', '').strip()
    
    query = Question.query
    if cat_id:
        query = query.filter_by(category_id=cat_id)
    if search:
        query = query.filter(Question.text.ilike(f'%{search}%'))
        
    pagination = query.order_by(Question.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        "questions": [
            {
                "id": q.id,
                "text": q.text,
                "category_id": q.category_id,
                "category_name": q.category.name if q.category else "Unknown",
                "difficulty": q.difficulty,
                "time_limit": q.time_limit,
                "options": [{"text": o.text, "is_correct": o.is_correct} for o in q.options]
            }
            for q in pagination.items
        ],
        "total": pagination.total,
        "pages": pagination.pages,
        "current_page": pagination.page
    })
 
@admin_bp.route('/api/admin/question/<int:q_id>', methods=['DELETE'])
@admin_required_decorator
def delete_question(q_id):
    q = Question.query.get(q_id)
    if not q:
        return jsonify({"msg": "Question not found"}), 404
    
    db.session.delete(q)
    db.session.commit()
    return jsonify({"msg": "Question deleted"}), 200

@admin_bp.route('/api/admin/stats', methods=['GET'])
@admin_required_decorator
def admin_stats():
    total_users = User.query.count()
    total_quizzes = Question.query.count()
    total_attempts = Result.query.count()
    total_categories = Category.query.count()
    
    # Get recent activity (last 10 items)
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_results = Result.query.order_by(Result.taken_at.desc()).limit(5).all()
    
    activity = []
    for u in recent_users:
        activity.append({
            "type": "user",
            "message": f"New user joined: {u.username}",
            "time": u.created_at.isoformat() + "Z",
            "icon": "user-plus",
            "color": "blue"
        })
    for r in recent_results:
        activity.append({
            "type": "quiz",
            "message": f"{r.username} completed {r.category.name if r.category else 'General'} quiz: {r.score}/{r.total}",
            "time": r.taken_at.isoformat() + "Z",
            "icon": "award",
            "color": "purple"
        })
    
    # Sort activity by time
    activity.sort(key=lambda x: x['time'], reverse=True)
    activity = activity[:15] # Final 15 items
    
    # Get Chart Data (attempts per day for last 7 days)
    chart_data = []
    today = datetime.utcnow().date()
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = Result.query.filter(func.date(Result.taken_at) == day).count()
        chart_data.append({
            "date": day.strftime("%b %d"),
            "count": count
        })

    return jsonify({
        "total_users": total_users,
        "total_quizzes": total_quizzes,
        "total_attempts": total_attempts,
        "total_categories": total_categories,
        "activity": activity,
        "chart_data": chart_data
    })

@admin_bp.route('/api/admin/settings', methods=['GET'])
@admin_required_decorator
def get_settings():
    maintenance = SystemSetting.get_val('maintenance_mode', 'false')
    admin_only_quiz = SystemSetting.get_val('admin_only_quiz', 'true')
    email_notifications = SystemSetting.get_val('email_notifications', 'false')
    
    # Dynamic System Info
    db_status = "Connected"
    try:
        db.session.execute(text('SELECT 1'))
    except Exception:
        db_status = "Disconnected"

    return jsonify({
        "settings": {
            "maintenance_mode": maintenance == 'true',
            "admin_only_quiz": admin_only_quiz == 'true',
            "email_notifications": email_notifications == 'true'
        },
        "system_info": {
            "version": current_app.config.get('APP_VERSION', '1.0.0'),
            "environment": "Development" if current_app.debug else "Production",
            "db_status": db_status,
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "db_type": "MySQL" # Could be dynamic if needed
        }
    })

@admin_bp.route('/api/admin/settings', methods=['PATCH'])
@admin_required_decorator
def update_settings():
    data = request.get_json() or {}
    
    if 'maintenance_mode' in data:
        SystemSetting.set_val('maintenance_mode', 'true' if data['maintenance_mode'] else 'false')
    
    if 'admin_only_quiz' in data:
        SystemSetting.set_val('admin_only_quiz', 'true' if data['admin_only_quiz'] else 'false')

    if 'email_notifications' in data:
        SystemSetting.set_val('email_notifications', 'true' if data['email_notifications'] else 'false')
        
    return jsonify({"msg": "Settings updated"}), 200
