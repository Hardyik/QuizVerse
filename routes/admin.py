from flask import Blueprint, render_template, redirect, session, jsonify, request
from models import User, Category, Question, Option, Result, db
from flask_jwt_extended import jwt_required, get_jwt_identity

admin_bp = Blueprint('admin', __name__)

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
    if 'user_id' not in session:
        return redirect('/login')
    
    user = User.query.get(session['user_id'])
    if not user or not user.is_admin:
        return redirect('/login')
    
    total_users = User.query.count()
    return render_template('Admin.html', total_users=total_users)

@admin_bp.route('/admin/users')
def list_users():
    if 'user_id' not in session:
        return redirect('/login')
    
    user = User.query.get(session['user_id'])
    if not user or not user.is_admin:
        return redirect('/login')
    
    users = User.query.filter(User.id != user.id).all()
    return render_template('admin_users.html', users=users)

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

@admin_bp.route('/api/admin/stats', methods=['GET'])
@admin_required_decorator
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
