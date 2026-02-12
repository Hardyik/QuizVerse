import os
from flask import Flask, render_template, jsonify
from datetime import datetime
from extensions import db, jwt
from config import Config
from routes.auth import auth_bp
from routes.main import main_bp
from routes.admin import admin_bp
from routes.api import api_bp
from models import User

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize Extensions
    db.init_app(app)
    jwt.init_app(app)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # Initialize DB (and Admin)
    with app.app_context():
        try:
            db.create_all()
            create_admin_if_not_exists()
        except Exception as e:
            print(f"[ERROR] Database connection failed: {e}")
            # On Vercel, we can't crash here or the whole function fails.
            pass

    # Error Handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error"}), 500
        
    @app.route('/health')
    def health():
        try:
            db.session.execute('SELECT 1')
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

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
