from flask import Blueprint, render_template, session, redirect, request
from flask_jwt_extended import decode_token
from models import User
from datetime import datetime

main_bp = Blueprint('main', __name__)


def _try_restore_session():
    """Attempt to restore session from JWT token in Authorization header.
    Returns True if session was restored, False otherwise."""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return False
    try:
        token = auth_header.split(' ', 1)[1]
        decoded = decode_token(token)
        username = decoded.get('sub')
        if username:
            user = User.query.filter_by(username=username).first()
            if user:
                session.permanent = True
                session['auth_user_id']  = user.id
                session['auth_username'] = user.username
                session['auth_is_admin'] = user.is_admin
                session['auth_login_at'] = datetime.utcnow().isoformat()
                return True
    except Exception:
        pass
    return False


def _login_required_or_restore():
    """Check session, if empty try JWT restore, if still empty return a
    small bootstrap page that sends the stored token and reloads."""
    if session.get('auth_user_id'):
        return None  # Already authenticated

    # Try header-based restore (covers fetch/AJAX calls)
    if _try_restore_session():
        return None

    # For browser navigation, the JWT lives in localStorage, not in headers.
    # Serve a tiny HTML interstitial that sends the token via fetch and reloads.
    next_url = request.path
    if request.query_string:
        next_url += '?' + request.query_string.decode()
    return _session_restore_page(next_url)


def _session_restore_page(next_url):
    """Return a small HTML page that tries to call /api/auth/session-check
    with the JWT from localStorage to restore the Flask session, then
    navigates to the intended page. If no token exists, redirects to login."""
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
<body><div class="loader"><div class="spinner"></div><p>Restoring your session…</p></div>
<script>
(async()=>{{
  const token=localStorage.getItem("access_token");
  if(!token){{ window.location.href="/login?next={next_url}"; return; }}
  try{{
    const r=await fetch("/api/auth/session-check",{{
      headers:{{"Authorization":"Bearer "+token}}
    }});
    const d=await r.json();
    if(d.logged_in){{ window.location.replace("{next_url}"); return; }}
  }}catch(e){{}}
  localStorage.removeItem("access_token");
  window.location.href="/login?next={next_url}";
}})();
</script></body></html>''', 200


@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/login')
def login_page():
    return render_template('login.html')

@main_bp.route('/signup')
def signup():
    return render_template('signup.html')

@main_bp.route('/about')
def about():
    return render_template('about.html')

@main_bp.route('/explore')
def categories_page():
    return render_template('explore.html')

@main_bp.route('/demo')
def play():
    return render_template('demo.html')

@main_bp.route('/random')
def random_quiz():
    guard = _login_required_or_restore()
    if guard:
        return guard
    return render_template('random.html')

@main_bp.route('/faq')
def faq():
    return render_template('faq.html')

@main_bp.route('/forget_pass')
def forget_pass():
    return render_template('forget_pass.html')

@main_bp.route('/leaderboard')
def leaderboard_page():
    return render_template('leaderboard.html')

@main_bp.route('/play_quiz')
def play_quiz():
    guard = _login_required_or_restore()
    if guard:
        return guard
    return render_template('play_quiz.html')

@main_bp.route('/profile')
def profile_page():
    guard = _login_required_or_restore()
    if guard:
        return guard
    return render_template('profile.html')

@main_bp.route('/user_dashboard')
def user_dashboard():
    guard = _login_required_or_restore()
    if guard:
        return guard
    if session.get('auth_is_admin'):
        return redirect('/admin')
    return render_template('user_dashboard.html')

@main_bp.route('/select_quiz')
def select_quiz():
    guard = _login_required_or_restore()
    if guard:
        return guard
    return render_template('select_quiz.html')

@main_bp.route('/analytics')
def analytics_page():
    guard = _login_required_or_restore()
    if guard:
        return guard
    return render_template('analytics.html')
