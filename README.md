# 🎯 QuizVerse

> **Enter the universe of quizzes — where learning meets fun.**

**QuizVerse** is a full-stack web application built with Flask that allows users to test their knowledge across various categories. It features a robust quiz engine, user authentication, score tracking, and a comprehensive admin panel for content management.

---

## 🚀 Features

### **User Features**
- **🔐 Secure Authentication:** User registration and login system with JWT support.
- **📚 Diverse Categories:** Browse and select quizzes from multiple categories.
- **⏱️ Timed Quizzes:** Challenge yourself with time-bound questions.
- **📊 Instant Results:** Get immediate feedback and scores after completing a quiz.
- **👤 User Dashboard:** View your quiz history and track your improvements.
- **📱 Responsive Design:** optimized for desktop and mobile devices.

### **Admin Capabilities**
- **🛠️ Dashboard:** Centralized control panel for administrators.
- **📝 Content Management:** Add, edit, and delete Categories, Questions, and Options.
- **👥 User Management:** Monitor and manage registered users.

### **Technological Highlights**
- **API Support:** RESTful API endpoints for external integrations.
- **Database:** robust MySQL backend with SQLAlchemy ORM.
- **Security:** Password hashing and JWT-based session management.

---

## 🛠️ Tech Stack

**Backend**
- [Python 3.x](https://www.python.org/)
- [Flask](https://flask.palletsprojects.com/) (Web Framework)
- [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/) (ORM)
- [Flask-JWT-Extended](https://flask-jwt-extended.readthedocs.io/) (Authentication)
- [PyMySQL](https://pypi.org/project/PyMySQL/) (Database Connector)

**Frontend**
- HTML5 / CSS3
- Jinja2 Templating Engine
- JavaScript (Vanilla)

**Database**
- MySQL

**Deployment**
- Configured for [Render](https://render.com/)

---

## ⚙️ Installation & Setup

Follow these steps to get QuizVerse running on your local machine.

### 1. **Clone the Repository**
```bash
git clone https://github.com/yourusername/QuizVerse.git
cd QuizVerse
```

### 2. **Create a Virtual Environment**
It's recommended to use a virtual environment to manage dependencies.
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

### 4. **Configure Environment Variables**
Create a `.env` file in the root directory and add the following configuration:
```env
# Database Configuration
SQLALCHEMY_DATABASE_URI=mysql+pymysql://<username>:<password>@<host>/<database_name>

# Security
SECRET_KEY=your_super_secret_key_here
JWT_SECRET_KEY=your_jwt_secret_key_here

# Admin Setup (Optional - for initial admin creation)
ADMIN_USER=admin
ADMIN_PASS=securepassword
ADMIN_EMAIL=admin@example.com
```

### 5. **Initialize the Database**
The application will automatically create the necessary database tables and the initial admin user (if configured) on the first run.
Ensure your MySQL server is running and the database exists.

### 6. **Run the Application**
```bash
python app.py
```
Visit `http://localhost:5000` in your browser.

---

## 📂 Project Structure

```text
QuizVerse/
├── app.py              # Application entry point
├── extensions.py       # Flask extensions initialization
├── models.py           # Database models
├── config.py           # Configuration settings
├── routes/             # Blueprint routes
│   ├── auth.py         # Authentication logic
│   ├── main.py         # Main site navigation
│   ├── admin.py        # Admin panel routes
│   └── api.py          # API endpoints
├── static/             # Static assets (CSS, JS, Images)
├── templates/          # HTML templates
└── requirements.txt    # Project dependencies
```

---

## 🤝 Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

