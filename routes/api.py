from flask import Blueprint, jsonify, request
from models import User, Category, Question, Option, Result, QuizSession, db
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
import json

api_bp = Blueprint('api', __name__)




@api_bp.route('/api/user/profile', methods=['GET'])
@jwt_required()
def user_profile():
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()
    
    if not user:
        return jsonify({"msg": "User not found"}), 404
    
    # Get user stats
    # Get user results once for efficiency
    all_results = Result.query.filter_by(user_id=user.id).all()
    total_quizzes = len(all_results)
    
    recent_results = sorted(all_results, key=lambda x: x.taken_at, reverse=True)[:5]
    
    avg_score = 0
    perfect_scores = 0
    if total_quizzes > 0:
        total_pct = sum((r.score / r.total * 100) for r in all_results if r.total > 0)
        avg_score = total_pct / total_quizzes
        perfect_scores = sum(1 for r in all_results if r.score == r.total and r.total > 0)

    # ─── Badge System ─────────────────────────────────────────────────────
    badges = []
    if total_quizzes >= 1:
        badges.append({"id": "first_quiz",  "icon": "🎯", "name": "First Quiz",     "desc": "Completed your first quiz!"})
    if total_quizzes >= 10:
        badges.append({"id": "veteran",     "icon": "🏅", "name": "Quiz Veteran",   "desc": "Completed 10+ quizzes"})
    if total_quizzes >= 50:
        badges.append({"id": "legend",      "icon": "🏆", "name": "Quiz Legend",    "desc": "Completed 50+ quizzes"})
    if avg_score >= 80:
        badges.append({"id": "sharpshooter","icon": "🎖️", "name": "Sharpshooter",  "desc": "Avg score ≥ 80%"})
    if avg_score >= 95:
        badges.append({"id": "ace",         "icon": "💎", "name": "Ace",            "desc": "Avg score ≥ 95%"})
    if perfect_scores >= 1:
        badges.append({"id": "perfect",     "icon": "⭐", "name": "Perfect Score",  "desc": "Got 100% on a quiz"})
    if user.level >= 5:
        badges.append({"id": "level_up",    "icon": "🚀", "name": "Level Up",       "desc": "Reached Level 5"})
    if user.level >= 10:
        badges.append({"id": "master",      "icon": "👑", "name": "Master",         "desc": "Reached Level 10"})

    return jsonify({
        "username": user.username,
        "email": user.email,
        "level": user.level,
        "profile_picture": user.profile_picture or 'avtar1.jpg',
        "total_quizzes": total_quizzes,
        "avg_score": round(avg_score, 2),
        "badges": badges,
        "recent_results": [
            {
                "quiz": r.category.name if r.category else "General",
                "score": r.score,
                "total": r.total,
                "date": r.taken_at.isoformat() + "Z"
            }
            for r in recent_results
        ]
    })

@api_bp.route('/api/user/profile', methods=['PATCH'])
@jwt_required()
def update_profile():
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"msg": "User not found"}), 404
        
    data = request.get_json() or {}
    new_username = data.get('username', '').strip()
    new_email = data.get('email', '').strip()
    new_profile_picture = data.get('profile_picture', '').strip()
    
    import re
    
    if new_username and new_username != user.username:
        if len(new_username) < 3:
            return jsonify({"msg": "Username too short"}), 400
        if not re.match(r'^[a-zA-Z0-9_]+$', new_username):
            return jsonify({"msg": "Username contains invalid characters"}), 400
        if User.query.filter_by(username=new_username).first():
            return jsonify({"msg": "Username already taken"}), 409
        
        # Update all previous results with the new username to prevent stale data
        from models import Result
        Result.query.filter_by(user_id=user.id).update({Result.username: new_username})
        
        user.username = new_username
        
    if new_email and new_email != user.email:
        if not re.match(r'[^@]+@[^@]+\.[^@]+', new_email):
            return jsonify({"msg": "Invalid email format"}), 400
        if User.query.filter_by(email=new_email).first():
            return jsonify({"msg": "Email already registered"}), 409
        user.email = new_email
    
    # Update profile picture if provided
    valid_avatars = [f'avtar{i}.jpg' for i in range(1, 16)]
    if new_profile_picture and new_profile_picture in valid_avatars:
        user.profile_picture = new_profile_picture
    elif new_profile_picture:
        return jsonify({"msg": "Invalid avatar selection"}), 400
        
    db.session.commit()
    
    # If username changed, issue a new JWT with the updated identity
    response_data = {"msg": "Profile updated successfully", "username": user.username, "profile_picture": user.profile_picture}
    if user.username != username:
        new_token = create_access_token(identity=user.username)
        response_data["access_token"] = new_token
    
    return jsonify(response_data), 200

@api_bp.route('/api/user/avatar', methods=['PATCH'])
@jwt_required()
def update_avatar():
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"msg": "User not found"}), 404
    
    data = request.get_json() or {}
    avatar = data.get('profile_picture', '').strip()
    
    valid_avatars = [f'avtar{i}.jpg' for i in range(1, 16)]
    if avatar not in valid_avatars:
        return jsonify({"msg": "Invalid avatar selection"}), 400
    
    user.profile_picture = avatar
    db.session.commit()
    return jsonify({"msg": "Avatar updated", "profile_picture": avatar}), 200

@api_bp.route('/api/user/password', methods=['PATCH'])
@jwt_required()
def change_password():
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"msg": "User not found"}), 404
        
    data = request.get_json() or {}
    current_pass = data.get('current_password')
    new_pass = data.get('new_password')
    
    if not current_pass or not new_pass:
        return jsonify({"msg": "Current and new password required"}), 400
        
    if not user.check_password(current_pass):
        return jsonify({"msg": "Incorrect current password"}), 401
        
    if len(new_pass) < 8:
        return jsonify({"msg": "New password must be at least 8 characters"}), 400
        
    user.set_password(new_pass)
    db.session.commit()
    return jsonify({"msg": "Password updated successfully"}), 200

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
            "options": [{"id": o.id, "text": o.text} for o in q.options] # REPLACED: Removed is_correct
        })
    return jsonify(result)

# ─── QUIZ SESSION PERSISTENCE ────────────────────────────────────────────────
@api_bp.route('/api/quiz/session/start', methods=['POST'])
@jwt_required()
def start_quiz_session():
    data = request.get_json() or {}
    cat_id = data.get('category_id')
    q_ids = data.get('question_ids', [])
    
    if not cat_id or not q_ids:
        return jsonify({"msg": "category_id and question_ids required"}), 400
        
    user_identity = get_jwt_identity()
    user = User.query.filter_by(username=user_identity).first()
    
    # Clear any old session for this user/category
    QuizSession.query.filter_by(user_id=user.id, category_id=cat_id).delete()
    
    sess = QuizSession(
        user_id=user.id,
        category_id=cat_id,
        question_ids=json.dumps(q_ids),
        current_index=0,
        score=0,
        user_answers=json.dumps([])
    )
    db.session.add(sess)
    db.session.commit()
    return jsonify({"msg": "Session started", "session_id": sess.id}), 201

@api_bp.route('/api/quiz/session/<int:cat_id>', methods=['GET'])
@jwt_required()
def get_quiz_session(cat_id):
    user_identity = get_jwt_identity()
    user = User.query.filter_by(username=user_identity).first()
    
    sess = QuizSession.query.filter_by(user_id=user.id, category_id=cat_id).first()
    if not sess:
        return jsonify(None), 200
        
    return jsonify({
        "current_index": sess.current_index,
        "score": sess.score,
        "question_ids": json.loads(sess.question_ids),
        "user_answers": json.loads(sess.user_answers or '[]')
    })

@api_bp.route('/api/quiz/session/<int:cat_id>', methods=['PATCH'])
@jwt_required()
def update_quiz_session(cat_id):
    data = request.get_json() or {}
    user_identity = get_jwt_identity()
    user = User.query.filter_by(username=user_identity).first()
    
    sess = QuizSession.query.filter_by(user_id=user.id, category_id=cat_id).first()
    if not sess:
        return jsonify({"msg": "No active session"}), 404
        
    if 'current_index' in data:
        sess.current_index = data['current_index']
    if 'score' in data:
        sess.score = data['score']
    if 'user_answers' in data:
        sess.user_answers = json.dumps(data['user_answers'])
        
    db.session.commit()
    return jsonify({"msg": "Progress saved"}), 200

@api_bp.route('/api/quiz/session/<int:cat_id>', methods=['DELETE'])
@jwt_required()
def delete_quiz_session(cat_id):
    user_identity = get_jwt_identity()
    user = User.query.filter_by(username=user_identity).first()
    QuizSession.query.filter_by(user_id=user.id, category_id=cat_id).delete()
    db.session.commit()
    return jsonify({"msg": "Session cleared"}), 200

@api_bp.route('/api/questions/batch', methods=['POST'])
@jwt_required()
def get_questions_batch():
    data = request.get_json() or {}
    ids = data.get('ids', [])
    if not ids:
        return jsonify([])
    
    questions = Question.query.filter(Question.id.in_(ids)).all()
    # Sort to match requested order
    q_dict = {q.id: q for q in questions}
    sorted_questions = [q_dict[qid] for qid in ids if qid in q_dict]
    
    result = []
    for q in sorted_questions:
        result.append({
            "id": q.id,
            "text": q.text,
            "difficulty": q.difficulty,
            "time_limit": q.time_limit,
            "options": [{"id": o.id, "text": o.text} for o in q.options]
        })
    return jsonify(result)

@api_bp.route('/api/check_answer', methods=['POST'])
def check_answer():
    data = request.get_json() or {}
    qid = data.get('question_id')
    oid = data.get('option_id')

    if not qid or not oid:
        return jsonify({"msg": "question_id and option_id required"}), 400

    question = Question.query.get(qid)
    if not question:
        return jsonify({"msg": "Question not found"}), 404

    correct_option = Option.query.filter_by(question_id=qid, is_correct=True).first()
    selected_option = Option.query.filter_by(id=oid, question_id=qid).first()

    if not selected_option:
        return jsonify({"msg": "Option not found for this question"}), 404

    return jsonify({
        "is_correct": selected_option.is_correct,
        "correct_option_id": correct_option.id if correct_option else None
    })

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

    # Verify if category exists
    cat = Category.query.get(category_id)
    if not cat:
        return jsonify({"msg": "Invalid category"}), 400

    for a in answers:
        qid = a.get('question_id')
        oid = a.get('option_id')
        if not qid or not oid:
            continue
            
        # Security Check: Does question exist and belong to this category?
        q = Question.query.filter_by(id=qid, category_id=category_id).first()
        if not q:
            return jsonify({"msg": f"Question {qid} does not belong to category {category_id}"}), 400
            
        opt = Option.query.filter_by(id=oid, question_id=qid).first()
        if opt and opt.is_correct:
            correct += 1

    # Get user if logged in via JWT
    user_id = None
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        try:
            from flask_jwt_extended import decode_token
            decoded = decode_token(token)
            user_obj = User.query.filter_by(username=decoded['sub']).first()
            if user_obj:
                user_id = user_obj.id
                username = user_obj.username
        except:
            pass

    # Strictly only save results if we have a valid user_id
    # Demo/Anonymous users will just get the response without any DB storage
    new_level = None
    result_id = None
    if user_id:
        result = Result(
            user_id=user_id,
            username=username,
            category_id=category_id,
            score=correct,
            total=total,
            time_taken=time_taken
        )
        db.session.add(result)

        # Level progression: level up every 5 quizzes taken
        user = User.query.get(user_id)
        if user:
            quizzes_done = Result.query.filter_by(user_id=user_id).count() + 1
            calculated_level = max(1, quizzes_done // 5 + 1)
            if calculated_level != user.level:
                user.level = calculated_level
                new_level = calculated_level

        db.session.commit()
        result_id = result.id

        # Clear active quiz session after submission
        QuizSession.query.filter_by(user_id=user_id, category_id=category_id).delete()
        db.session.commit()

    return jsonify({
        "score": correct,
        "total": total,
        "percentage": round((correct / total) * 100, 2),
        "result_id": result_id,
        "level_up": new_level
    })

@api_bp.route('/api/leaderboard', methods=['GET'])
def leaderboard():
    cat_id = request.args.get('category_id')
    limit = int(request.args.get('limit', 10))
    
    query = Result.query.join(User, Result.user_id == User.id).filter(
        Result.user_id.isnot(None),
        User.is_admin == False
    )
    if cat_id:
        query = query.filter(Result.category_id == int(cat_id))
    
    all_results = query.all()

    # Aggregate per user: best overall accuracy
    user_stats = {}
    for r in all_results:
        uid = r.user_id
        if uid not in user_stats:
            user_stats[uid] = {
                "username": r.username,
                "user": r.user,
                "total_score": 0,
                "total_questions": 0,
                "total_time": 0,
                "quizzes": 0
            }
        user_stats[uid]["total_score"] += r.score
        user_stats[uid]["total_questions"] += r.total
        user_stats[uid]["total_time"] += (r.time_taken or 0)
        user_stats[uid]["quizzes"] += 1

    # Build ranked list sorted by accuracy desc, then avg time asc
    ranked = []
    for uid, s in user_stats.items():
        pct = round((s["total_score"] / s["total_questions"]) * 100, 2) if s["total_questions"] > 0 else 0
        avg_time = round(s["total_time"] / s["quizzes"]) if s["quizzes"] > 0 else 0
        profile_pic = 'avtar1.jpg'
        if s["user"]:
            profile_pic = s["user"].profile_picture or 'avtar1.jpg'
        ranked.append({
            "username": s["username"],
            "score": s["total_score"],
            "total": s["total_questions"],
            "percentage": pct,
            "time_taken": avg_time,
            "quizzes_played": s["quizzes"],
            "profile_picture": profile_pic
        })

    ranked.sort(key=lambda x: (-x["percentage"], x["time_taken"]))
    return jsonify(ranked[:limit])

@api_bp.route('/api/user/analytics', methods=['GET'])
@jwt_required()
def user_analytics():
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"msg": "User not found"}), 404

    results = Result.query.filter_by(user_id=user.id).all()
    
    total_quizzes = len(results)
    
    total_score = sum(r.score for r in results)
    total_possible = sum(r.total for r in results)
    overall_accuracy = round((total_score / total_possible * 100) if total_possible > 0 else 0, 2)
    
    total_correct = total_score
    total_incorrect = total_possible - total_score

    valid_times = [r.time_taken for r in results if r.time_taken is not None]
    avg_time_taken = round(sum(valid_times) / len(valid_times) if valid_times else 0, 2)

    category_stats = {}
    for r in results:
        cat_name = r.category.name if r.category else "Unknown"
        if cat_name not in category_stats:
            category_stats[cat_name] = {"total_score": 0, "total_questions": 0, "quizzes_taken": 0}
        
        category_stats[cat_name]["total_score"] += r.score
        category_stats[cat_name]["total_questions"] += r.total
        category_stats[cat_name]["quizzes_taken"] += 1
        
    formatted_category_stats = []
    for cat, stats in category_stats.items():
        accuracy = round((stats["total_score"] / stats["total_questions"] * 100) if stats["total_questions"] > 0 else 0, 2)
        formatted_category_stats.append({
            "category": cat,
            "accuracy": accuracy,
            "quizzes_taken": stats["quizzes_taken"]
        })

    return jsonify({
        "total_quizzes": total_quizzes,
        "overall_accuracy": overall_accuracy,
        "total_correct": total_correct,
        "total_incorrect": total_incorrect,
        "avg_time_taken": avg_time_taken,
        "category_performance": formatted_category_stats
    })
