from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__)

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
def random():
    return render_template('random.html')

@main_bp.route('/faq')
def faq():
       return render_template('faq.html')
