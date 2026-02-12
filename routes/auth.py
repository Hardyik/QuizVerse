from flask import Blueprint, request, jsonify, session
from flask_jwt_extended import create_access_token
from models import User, db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')
    is_admin_login = data.get('is_admin_login', False)

    user = User.query.filter_by(email=email).first()
    
    if not user or not user.check_password(password):
        return jsonify({"msg": "Invalid email or password"}), 401
        
    # Enforce Admin Login Checkbox
    if user.is_admin and not is_admin_login:
        return jsonify({"msg": "Admins must use Admin Login"}), 403
    
    if not user.is_admin and is_admin_login:
         return jsonify({"msg": "Access denied: Not an administrator"}), 403

    token = create_access_token(identity=user.username)
    
    session['user_id'] = user.id
    session['username'] = user.username
    
    return jsonify({
        "access_token": token,
        "username": user.username,
        "email": user.email,
        "is_admin": user.is_admin,
        "level": user.level
    }), 200

@auth_bp.route('/api/register', methods=['POST'])
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

@auth_bp.route('/logout')
def logout():
    session.clear()
    from flask import redirect
    return redirect('/login')
