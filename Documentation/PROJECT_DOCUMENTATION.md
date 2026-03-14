# 🎯 QuizVerse — Project Documentation

> A complete reference of every feature, file, and module in the QuizVerse codebase.

---

## 📌 Overview

**QuizVerse** is a full-stack quiz platform built with **Flask** (Python). It provides:

- A multi-category quiz engine with timed questions and difficulty levels
- User authentication with JWT + server-side sessions
- A gamification layer (levels, badges, leaderboard)
- A complete admin panel for content & user management
- OTP-based password recovery via email
- A maintenance mode toggle, rate limiting, and health checks

**Tech Stack:** Python 3 · Flask · MySQL (PyMySQL) · SQLAlchemy ORM · Flask-JWT-Extended · Flask-Mail · Flask-Migrate · Flask-Limiter · Jinja2 · Vanilla JS/CSS

---

## 🚀 Feature Summary

### User-Facing Features

| Feature | Description |
|---|---|
| **Registration & Login** | Email + password signup with strong-password validation. Login issues a JWT (stored in `localStorage`) and populates a Flask server-side session. Role-based enforcement blocks admins from logging in via the user portal and vice-versa. |
| **Remember Me** | Optional persistent session (7-day cookie) vs. browser-session-only cookie. |
| **Forgot Password** | OTP sent to email → verify OTP → reset password. Rate-limited to 3 req/min. |
| **Category Explorer** | Browse all quiz categories (name, description, icon, question count). |
| **Quiz Play** | Select a category → get questions (filterable by difficulty). Per-question timer. Answers verified server-side. Correct option ID returned only after answering. |
| **Quiz Session Persistence** | In-progress quizzes are saved to the DB so users can resume after page refresh or browser close. |
| **Demo Mode** | Unauthenticated users can try a demo quiz. Results are *not* saved to the database. |
| **Random Quiz** | Play a random quiz from any category (login required). |
| **Score & Results** | After submission the user receives score, percentage, and optional level-up notification. |
| **Leaderboard** | Global or per-category leaderboard ranked by accuracy (desc), then average time (asc). Admins are excluded. |
| **User Dashboard** | Personal quiz history, scores, and performance overview. |
| **Analytics** | Per-user analytics: overall accuracy, correct/incorrect counts, avg time, category-wise performance. |
| **Profile Management** | Update username, email, password, and avatar (15 pre-set avatars). Username changes propagate to historic results and issue a fresh JWT. |
| **Badge System** | Earned automatically: First Quiz 🎯, Veteran 🏅 (10+), Legend 🏆 (50+), Sharpshooter 🎖️ (≥80%), Ace 💎 (≥95%), Perfect Score ⭐, Level Up 🚀 (Lvl 5), Master 👑 (Lvl 10). |
| **Level Progression** | Level increases by 1 for every 5 quizzes completed. |
| **Dark Mode** | Client-side dark mode toggle with dedicated CSS + JS. |

### Admin Features

| Feature | Description |
|---|---|
| **Admin Dashboard** | Overview stats — total users, questions, attempts, categories. Daily attempts chart (7 days). Recent activity feed. |
| **User Management** | Paginated user list with search. Delete users. Promote/demote admin role (with self-demotion protection). |
| **Quiz Management** | Full CRUD for Categories (name, description, icon) and Questions (text, difficulty, time limit, options with correct flag). Paginated, searchable. |
| **Analytics** | Per-category attempt counts, most-viewed category. |
| **Settings** | Toggle maintenance mode, admin-only quiz creation, email notifications. |
| **Maintenance Mode** | When active, non-admin visitors see a `503 maintenance.html` page. Login/logout/static routes remain accessible. |

### Infrastructure & Security

| Feature | Description |
|---|---|
| **JWT + Session hybrid auth** | JWT for API calls; Flask session for page-level guards. A `before_request` hook automatically restores the session from a valid JWT when the session cookie is missing. |
| **Session Restore Interstitial** | Protected pages serve a tiny HTML page that reads the JWT from `localStorage`, calls `/api/auth/session-check`, and reloads — seamlessly handling "browser was closed" scenarios. |
| **Rate Limiting** | `Flask-Limiter` guards sensitive endpoints (login: 10/min, register: 5/min, forgot-password: 3/min, OTP verify: 5/min). |
| **Database Migrations** | `Flask-Migrate` / Alembic for schema versioning. |
| **Health Endpoint** | `GET /health` returns DB connection status and server time. |
| **Error Handlers** | Custom JSON responses for 400, 401, 403, 404, 405, 500. Custom HTML pages for 404 and 500 on non-API routes. |
| **Admin Auto-Bootstrap** | On first startup, an admin user is created from environment variables. |

---

## 📂 File-by-File Breakdown

### Root-Level Files

#### `app.py` — Application Entry Point
- **`create_app()`** — Factory function that:
  1. Creates the Flask app and loads `Config`.
  2. Initializes all extensions (`db`, `jwt`, `mail`, `migrate`, `limiter`).
  3. Registers 4 Blueprints: `auth_bp`, `main_bp`, `admin_bp`, `api_bp`.
  4. Calls `create_admin_if_not_exists()` to bootstrap the admin user.
  5. Registers `before_request` hooks:
     - **`restore_session_from_jwt()`** — re-populates `session` from the `Authorization: Bearer <token>` header when the session cookie is missing.
     - **`check_maintenance()`** — returns `maintenance.html` (503) for non-admin users when maintenance mode is active.
  6. Registers global error handlers (400, 401, 403, 404, 405, 500).
  7. Provides `GET /health` (DB connectivity check) and `GET /api/auth/session-check` (returns current auth state).
- **`create_admin_if_not_exists()`** — Reads `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_EMAIL` from config; creates the admin `User` if not present.
- Starts the dev server on `0.0.0.0:5000` when run directly.

---

#### `config.py` — Configuration
Loads `.env` via `python-dotenv` and exposes a `Config` class with:
| Setting | Purpose |
|---|---|
| `SQLALCHEMY_DATABASE_URI` | MySQL connection string from `DATABASE_URI` env var |
| `SECRET_KEY` / `JWT_SECRET_KEY` | Signing keys for sessions and JWT |
| `JWT_ACCESS_TOKEN_EXPIRES` | 8 hours |
| `SESSION_COOKIE_*` | HttpOnly, SameSite=Lax, Secure (prod only) |
| `PERMANENT_SESSION_LIFETIME` | 7 days (for "Remember Me") |
| `ADMIN_USERNAME / EMAIL / PASSWORD` | Bootstrap admin credentials |
| `MAIL_*` | SMTP settings for OTP emails (default: Gmail) |
| `APP_VERSION` | `1.0.0` |

---

#### `extensions.py` — Flask Extensions
Instantiates (without app binding) and exports:
- `db` — `SQLAlchemy`
- `jwt` — `JWTManager`
- `mail` — `Mail`
- `migrate` — `Migrate`
- `limiter` — `Limiter` (keyed by remote IP)

---

#### `models.py` — Database Models
Defines **7 SQLAlchemy models**:

| Model | Table | Key Fields | Purpose |
|---|---|---|---|
| **`User`** | `users` | `id`, `username`, `email`, `password_hash`, `is_admin`, `level`, `profile_picture`, `created_at` | Stores registered users. Methods: `set_password()`, `check_password()` (Werkzeug hashing). |
| **`Category`** | `categories` | `id`, `name`, `description`, `icon`, `created_at` | Quiz categories (e.g. "Science", "History"). |
| **`Question`** | `questions` | `id`, `category_id` (FK), `text`, `difficulty`, `time_limit`, `created_at` | Individual quiz questions. `cascade="all, delete-orphan"` ensures questions are deleted with their category. |
| **`Option`** | `options` | `id`, `question_id` (FK), `text`, `is_correct` | Answer options for each question. Cascaded delete with question. |
| **`Result`** | `results` | `id`, `user_id` (FK), `username`, `category_id` (FK), `score`, `total`, `time_taken`, `taken_at` | Stores completed quiz results for scoring and analytics. |
| **`OTP`** | `otps` | `id`, `email`, `otp`, `expires_at`, `is_verified`, `created_at` | Temporary OTPs for the forgot-password flow. |
| **`QuizSession`** | `quiz_sessions` | `id`, `user_id` (FK), `category_id` (FK), `question_ids` (JSON), `current_index`, `score`, `user_answers` (JSON), `last_active` | Persists in-progress quiz state so users can resume. |
| **`SystemSetting`** | `system_settings` | `key` (PK), `value`, `updated_at` | Key-value store for app settings (maintenance mode, etc.). Includes an in-memory `_cache` with `get_val()`, `set_val()`, `clear_cache()`. |

---

#### `requirements.txt` — Python Dependencies
```
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
Flask-JWT-Extended==4.6.0
Flask-Mail==0.10.0
PyMySQL==1.1.0
python-dotenv==1.0.0
cryptography==41.0.7
Werkzeug==3.0.1
mysql-connector-python==8.1.0
gunicorn==21.2.0
Flask-Migrate==4.0.5
Flask-Limiter==3.5.0
```

---

#### `.env.example` — Environment Template
Sample values for `DATABASE_URI`, security keys, admin credentials, SMTP settings, and Flask debug flags.

---

### `routes/` — Blueprint Modules

#### `routes/auth.py` — Authentication Blueprint (`auth_bp`)
| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/login` | POST | — | Validates email/password, enforces admin vs. user role mode, creates JWT, populates session. Rate-limited 10/min. |
| `/api/register` | POST | — | Creates a new user with strong-password validation (8+ chars, uppercase, lowercase, digit). Rate-limited 5/min. |
| `/logout` | GET | — | Clears session, serves interstitial JS page that removes `access_token` from `localStorage` and redirects to `/login`. |
| `/api/forgot-password` | POST | — | Generates 6-digit OTP, stores in DB (10 min expiry), sends via Flask-Mail. Always returns 200 (prevents email enumeration). Rate-limited 3/min. |
| `/api/verify-otp` | POST | — | Verifies OTP exists and hasn't expired; sets `is_verified = True`. Rate-limited 5/min. |
| `/api/reset-password` | POST | — | Accepts verified OTP + new password; updates the user's password hash. |

---

#### `routes/main.py` — Page Rendering Blueprint (`main_bp`)
| Route | Template | Auth Required |
|---|---|---|
| `/` | `index.html` | No |
| `/login` | `login.html` | No |
| `/signup` | `signup.html` | No |
| `/about` | `about.html` | No |
| `/explore` | `explore.html` | No |
| `/demo` | `demo.html` | No |
| `/faq` | `faq.html` | No |
| `/forget_pass` | `forget_pass.html` | No |
| `/leaderboard` | `leaderboard.html` | No |
| `/random` | `random.html` | **Yes** |
| `/play_quiz` | `play_quiz.html` | **Yes** |
| `/profile` | `profile.html` | **Yes** |
| `/user_dashboard` | `user_dashboard.html` | **Yes** |
| `/select_quiz` | `select_quiz.html` | **Yes** |
| `/analytics` | `analytics.html` | **Yes** |

**Helper functions:**
- `_try_restore_session()` — Attempts session restore from JWT in the `Authorization` header.
- `_login_required_or_restore()` — Checks session → tries header restore → serves restore interstitial HTML page.
- `_session_restore_page(next_url)` — Animated loading page that reads the JWT from `localStorage`, calls `/api/auth/session-check`, and reloads.

---

#### `routes/admin.py` — Admin Blueprint (`admin_bp`)

**Page Routes (all admin-guarded):**
| Route | Template |
|---|---|
| `/admin` | `includes/Admin.html` |
| `/admin/users` | `includes/admin_users.html` |
| `/admin/quizzes` | `includes/admin_quiz.html` |
| `/admin/settings` | `includes/admin_settings.html` |
| `/admin/analytics` | `includes/admin_analytics.html` |

**API Routes (all JWT + admin-required):**
| Endpoint | Method | Description |
|---|---|---|
| `/api/admin/stats` | GET | Dashboard stats: total users/questions/attempts/categories, recent activity feed, daily attempts chart (7 days). |
| `/api/admin/users` | GET | Paginated user list with search by username/email. |
| `/api/admin/user/<id>` | DELETE | Delete a non-admin user. |
| `/api/admin/user/<id>/toggle-admin` | POST | Promote or demote a user's admin status (self-demotion blocked). |
| `/api/admin/category` | POST | Create a new category. |
| `/api/admin/category/<id>` | PATCH | Update category name/description/icon. |
| `/api/admin/category/<id>` | DELETE | Delete a category (cascades to its questions & options). |
| `/api/admin/question` | POST | Create a question with options. |
| `/api/admin/question/<id>` | PATCH | Update question text/difficulty/time_limit/options. |
| `/api/admin/question/<id>` | DELETE | Delete a question. |
| `/api/admin/questions` | GET | Paginated question list, filterable by category + search. |
| `/api/admin/analytics/categories` | GET | Per-category attempt counts. |
| `/api/admin/settings` | GET | Get current settings + system info (version, env, DB status, Python version). |
| `/api/admin/settings` | PATCH | Toggle maintenance_mode, admin_only_quiz, email_notifications. |

---

#### `routes/api.py` — Public & User API Blueprint (`api_bp`)

**User Profile Endpoints (JWT required):**
| Endpoint | Method | Description |
|---|---|---|
| `/api/user/profile` | GET | Returns username, email, level, avatar, total quizzes, avg score, badges, recent results. |
| `/api/user/profile` | PATCH | Update username/email/avatar. Issues new JWT on username change. |
| `/api/user/avatar` | PATCH | Update avatar only (15 valid avatar options). |
| `/api/user/password` | PATCH | Change password (requires current password). |
| `/api/user/analytics` | GET | Detailed analytics: overall accuracy, correct/incorrect breakdown, avg time, category performance. |

**Quiz Endpoints:**
| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/categories` | GET | — | List all categories with question counts. |
| `/api/categories/<id>/questions` | GET | — | Get questions for a category (limit, difficulty filters). Options returned **without** `is_correct`. |
| `/api/check_answer` | POST | — | Check a single answer; returns whether correct + correct option ID. |
| `/api/submit` | POST | — | Submit full quiz; calculates score. For authenticated users: saves `Result`, handles level-up, clears `QuizSession`. Anonymous users get score but nothing is persisted. |
| `/api/leaderboard` | GET | — | Aggregated leaderboard: per-user accuracy, time, quizzes played. Filterable by category. |

**Quiz Session Persistence (JWT required):**
| Endpoint | Method | Description |
|---|---|---|
| `/api/quiz/session/start` | POST | Start a new quiz session (category + question IDs). Clears any existing session for that user/category. |
| `/api/quiz/session/<cat_id>` | GET | Get current session progress. |
| `/api/quiz/session/<cat_id>` | PATCH | Update progress (current index, score, answers). |
| `/api/quiz/session/<cat_id>` | DELETE | Clear session. |
| `/api/questions/batch` | POST | Fetch multiple questions by IDs (for session resume). |

---

### `templates/` — Jinja2 HTML Templates

| Template | Page |
|---|---|
| `index.html` | Landing / Home page |
| `login.html` | User & Admin login (toggle mode) |
| `signup.html` | User registration form |
| `about.html` | About page (team info with member photos) |
| `explore.html` | Category browser |
| `demo.html` | Demo quiz (unauthenticated) |
| `faq.html` | Frequently Asked Questions |
| `forget_pass.html` | Forgot password flow (request OTP → verify → reset) |
| `leaderboard.html` | Public leaderboard |
| `play_quiz.html` | Active quiz page (timer, options, progress bar) |
| `random.html` | Random quiz mode |
| `select_quiz.html` | Category selection for logged-in users |
| `user_dashboard.html` | User dashboard with history and stats |
| `profile.html` | User profile (edit info, avatar, password) |
| `analytics.html` | User analytics charts |

#### `templates/includes/` — Admin & Shared Partials

| Template | Purpose |
|---|---|
| `Admin.html` | Admin dashboard (stats cards, activity feed, charts) |
| `admin_users.html` | Admin user management table |
| `admin_quiz.html` | Admin quiz/category CRUD interface |
| `admin_settings.html` | Admin settings panel |
| `admin_analytics.html` | Admin analytics dashboard |
| `admin_sidebar.html` | Reusable admin sidebar navigation |
| `maintenance.html` | Maintenance mode 503 page |
| `session_guard.html` | Session restoration guard page |
| `404.html` | Custom 404 error page |
| `500.html` | Custom 500 error page |

---

### `static/` — Static Assets

| File/Folder | Purpose |
|---|---|
| `LOGO.jpg` / `logo.png` | QuizVerse branding logos |
| `dark-mode.css` | Dark mode stylesheet |
| `dark-mode.js` | Dark mode toggle logic (persisted across sessions) |
| `avatars/` | 15 user avatars (`avtar1.jpg` – `avtar15.jpg`) + `admin_av.png` |
| `quiz_page.png` | Screenshot for README/docs |
| `daund.png`, `dingorkar.jpeg`, `hardik.png`, `parth.jpeg`, `pratik.jpeg` | Team member photos (used in `about.html`) |

---

### `migrations/` — Database Migrations
Alembic migration files managed by Flask-Migrate. Run migrations with:
```bash
flask db init      # One-time setup
flask db migrate   # Generate migration
flask db upgrade   # Apply migration
```

---

## 🔐 Authentication Flow

```
┌─────────────┐    POST /api/login     ┌───────────┐
│  Login Page  │ ─────────────────────► │  Server   │
│  (login.html)│                        │           │
│              │ ◄───────────────────── │ JWT token │
│  Stores JWT  │   { access_token }     │ + Session │
│  in          │                        └───────────┘
│  localStorage│
└──────┬───────┘
       │
       │  Browser navigates to /user_dashboard
       ▼
┌──────────────┐   No session cookie?    ┌──────────────────┐
│  main.py     │ ───────────────────────►│  Restore Page    │
│  route guard │                         │  (interstitial)  │
│              │                         │                  │
│              │   Reads JWT from        │  fetch() to      │
│              │   localStorage          │  /api/auth/      │
│              │ ◄──────────────────────│  session-check   │
│  Session OK! │   Session restored      │  with Bearer JWT │
│  Serve page  │                         └──────────────────┘
└──────────────┘
```

---

## 🗃️ Database Schema (ER Diagram)

```
┌─────────────┐       ┌──────────────┐       ┌──────────────┐
│   users      │       │  categories  │       │  questions   │
├─────────────┤       ├──────────────┤       ├──────────────┤
│ id (PK)     │       │ id (PK)      │       │ id (PK)      │
│ username    │       │ name         │◄──────│ category_id  │
│ email       │       │ description  │       │ text         │
│ password_   │       │ icon         │       │ difficulty   │
│   hash      │       │ created_at   │       │ time_limit   │
│ is_admin    │       └──────────────┘       │ created_at   │
│ level       │                              └──────┬───────┘
│ profile_    │       ┌──────────────┐              │
│   picture   │       │   options    │              │
│ created_at  │       ├──────────────┤              │
└──────┬──────┘       │ id (PK)      │◄─────────────┘
       │              │ question_id  │
       │              │ text         │
       │              │ is_correct   │
       │              └──────────────┘
       │
       │         ┌──────────────┐
       ├────────►│   results    │
       │         ├──────────────┤
       │         │ id (PK)      │
       │         │ user_id (FK) │
       │         │ username     │
       │         │ category_id  │
       │         │ score        │
       │         │ total        │
       │         │ time_taken   │
       │         │ taken_at     │
       │         └──────────────┘
       │
       │         ┌────────────────┐
       ├────────►│ quiz_sessions  │
       │         ├────────────────┤
       │         │ id (PK)        │
       │         │ user_id (FK)   │
       │         │ category_id    │
       │         │ question_ids   │
       │         │ current_index  │
       │         │ score          │
       │         │ user_answers   │
       │         │ last_active    │
       │         └────────────────┘
       │
       │         ┌──────────────────┐
       │         │  system_settings │
       │         ├──────────────────┤
       │         │ key (PK)         │
       │         │ value            │
       │         │ updated_at       │
       │         └──────────────────┘
       │
       │         ┌──────────────┐
       │         │     otps     │
       │         ├──────────────┤
       │         │ id (PK)      │
       │         │ email        │
       │         │ otp          │
       │         │ expires_at   │
       │         │ is_verified  │
       │         │ created_at   │
       │         └──────────────┘
```

---

## 🏃 How to Run

```bash
# 1. Clone & enter directory
git clone <repo-url> && cd QuizVerse

# 2. Create virtual environment
python -m venv venv && venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy & fill env vars
cp .env.example .env
# Edit .env with your MySQL URI, keys, SMTP config

# 5. Initialize database (first time only)
flask db init
flask db migrate -m "initial"
flask db upgrade

# 6. Run
python app.py
# → http://localhost:5000
```

---

*Generated on 2026-03-07 for the QuizVerse project.*
