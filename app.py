import os
from flask import Flask, render_template, jsonify, request, session
from sqlalchemy import text
from datetime import datetime
from extensions import db, jwt, mail, migrate, limiter
from config import Config
from routes.auth import auth_bp
from routes.main import main_bp
from routes.admin import admin_bp
from routes.api import api_bp
from models import User, SystemSetting

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize Extensions
    db.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db) # UPDATED
    limiter.init_app(app)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # Initialize DB (and Admin)
    with app.app_context():
        # db.create_all() # Commented out in favor of migrations
        create_admin_if_not_exists()

    @app.before_request
    def restore_session_from_jwt():
        """If Flask session is empty but the request has a valid JWT,
        re-populate the auth session so page-level guards don't kick
        the user out.  This covers the case where the browser was closed
        (session cookie lost) but localStorage still has a valid token."""
        if session.get('auth_user_id'):
            return  # session already populated — nothing to do

        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return

        try:
            from flask_jwt_extended import decode_token
            token = auth_header.split(' ', 1)[1]
            decoded = decode_token(token)
            username = decoded.get('sub')
            if username:
                user = User.query.filter_by(username=username).first()
                if user:
                    session.permanent = True  # keep restored session alive
                    session['auth_user_id']  = user.id
                    session['auth_username'] = user.username
                    session['auth_is_admin'] = user.is_admin
                    session['auth_login_at'] = datetime.utcnow().isoformat()
        except Exception:
            pass  # token invalid / expired — ignore

    @app.route('/api/auth/session-check')
    def session_check():
        """Frontend calls this on page load to verify auth status.
        Returns the current auth session state."""
        user_id = session.get('auth_user_id')
        if user_id:
            return jsonify({
                "logged_in": True,
                "user_id": user_id,
                "username": session.get('auth_username'),
                "is_admin": session.get('auth_is_admin', False)
            })
        return jsonify({"logged_in": False}), 200

    @app.before_request
    def check_maintenance():
        # 1. Routes that should ALWAYS be accessible, even in maintenance mode
        if request.path.startswith('/static') or \
           request.path == '/login' or \
           request.path == '/logout' or \
           request.path == '/api/login' or \
           request.path == '/api/logout' or \
           request.path == '/api/auth/status' or \
           request.path == '/maintenance':
            return

        # 2. Check if maintenance mode is active in the database
        is_maintenance = SystemSetting.get_val('maintenance_mode', 'false') == 'true'
        
        if is_maintenance:
            # 3. If maintenance mode is active, check if the current user is an Admin
            # We check the Flask session memory since /api/login populates 'auth_is_admin'
            is_admin = session.get('auth_is_admin', False)
            
            if not is_admin:
                # 4. If they are not an Admin (or not logged in), block them
                return render_template('includes/maintenance.html'), 503

    # Global Error Handlers
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "Bad Request", "message": str(e)}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({"error": "Unauthorized", "message": "Login required"}), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({"error": "Forbidden", "message": "Access denied"}), 403

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith('/api/'):
            return jsonify({"error": "Not Found", "message": "Resource does not exist"}), 404
        return render_template('includes/404.html'), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Method Not Allowed"}), 405

    @app.errorhandler(500)
    def server_error(e):
        app.logger.error(f"Server Error: {str(e)}")
        if request.path.startswith('/api/'):
            return jsonify({
                "error": "Internal Server Error",
                "message": "An unexpected error occurred"
            }), 500
        return render_template('includes/500.html'), 500
        
    @app.route('/health')
    def health():
        try:
            db.session.execute(text('SELECT 1'))
            db_status = "connected"
        except Exception as e:
            db_status = f"error: {str(e)}"
        return jsonify({
            "status": "ok",
            "database": db_status,
            "time": datetime.utcnow().isoformat()
        })

    return app

def create_admin_if_not_exists():
    from flask import current_app
    admin_user  = current_app.config.get('ADMIN_USERNAME', 'admin')
    admin_pass  = current_app.config.get('ADMIN_PASSWORD', 'Admin@1234')
    admin_email = current_app.config.get('ADMIN_EMAIL',    'admin@quizverse.com')

    existing = User.query.filter_by(username=admin_user).first()
    if not existing:
        admin = User(username=admin_user, email=admin_email, is_admin=True)
        admin.set_password(admin_pass)
        db.session.add(admin)
        db.session.commit()
        print(f"[INIT] Admin created -> {admin_user}")
    else:
        print("[INIT] Admin already exists")
        print(f"Admin username: {admin_user}")
        print(f"Admin email: {admin_email}")
        print(f"Admin password: {admin_pass}")

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
