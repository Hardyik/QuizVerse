from flask import Blueprint, render_template, jsonify, request
from models import User, Category, Question, Option, Result, db
from flask_jwt_extended import jwt_required, get_jwt_identity

api_bp = Blueprint('api', __name__)

@api_bp.route('/user_dashboard')
def user_dashboard():
    return render_template('user_dashboard.html')

@api_bp.route('/api/user/profile', methods=['GET'])
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

@api_bp.route('/api/categories', methods=['GET'])
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

@api_bp.route('/api/categories/<int:cat_id>/questions', methods=['GET'])
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

@api_bp.route('/api/submit', methods=['POST'])
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

@api_bp.route('/api/leaderboard', methods=['GET'])
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
