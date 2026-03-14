# 📖 QuizVerse — Line-by-Line Code Explanation (Part 4: API & Static Files)

---

## 1. `routes/api.py` — Public & User API Blueprint

### User Profile (Lines 11–70)
```python
@api_bp.route('/api/user/profile', methods=['GET'])
@jwt_required()                            # Requires valid JWT in Authorization header
def user_profile():
    username = get_jwt_identity()           # Extract username from JWT 'sub' claim
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"msg": "User not found"}), 404

    # Fetch ALL results for this user once (efficient — avoids multiple DB queries)
    all_results = Result.query.filter_by(user_id=user.id).all()
    total_quizzes = len(all_results)

    # Sort by date descending, take latest 5 for "recent results"
    recent_results = sorted(all_results, key=lambda x: x.taken_at, reverse=True)[:5]

    avg_score = 0
    perfect_scores = 0
    if total_quizzes > 0:
        # Calculate average percentage across all quizzes
        total_pct = sum((r.score / r.total * 100) for r in all_results if r.total > 0)
        avg_score = total_pct / total_quizzes
        # Count quizzes where user scored 100%
        perfect_scores = sum(1 for r in all_results if r.score == r.total and r.total > 0)

    # ─── Badge System (Lines 35–51) ───
    # Badges are computed dynamically based on stats — not stored in DB
    badges = []
    if total_quizzes >= 1:   badges.append({"id": "first_quiz", "icon": "🎯", "name": "First Quiz", ...})
    if total_quizzes >= 10:  badges.append({"id": "veteran", "icon": "🏅", "name": "Quiz Veteran", ...})
    if total_quizzes >= 50:  badges.append({"id": "legend", "icon": "🏆", "name": "Quiz Legend", ...})
    if avg_score >= 80:      badges.append({"id": "sharpshooter", "icon": "🎖️", "name": "Sharpshooter", ...})
    if avg_score >= 95:      badges.append({"id": "ace", "icon": "💎", "name": "Ace", ...})
    if perfect_scores >= 1:  badges.append({"id": "perfect", "icon": "⭐", "name": "Perfect Score", ...})
    if user.level >= 5:      badges.append({"id": "level_up", "icon": "🚀", "name": "Level Up", ...})
    if user.level >= 10:     badges.append({"id": "master", "icon": "👑", "name": "Master", ...})

    return jsonify({
        "username": user.username, "email": user.email, "level": user.level,
        "profile_picture": user.profile_picture or 'avtar1.jpg',
        "total_quizzes": total_quizzes, "avg_score": round(avg_score, 2),
        "badges": badges, "recent_results": [...]
    })
```

### Profile Update (Lines 72–123)
```python
@api_bp.route('/api/user/profile', methods=['PATCH'])
@jwt_required()
def update_profile():
    # Validates new username (min 3 chars, alphanumeric+underscore only, unique)
    if new_username and new_username != user.username:
        if len(new_username) < 3: return 400
        if not re.match(r'^[a-zA-Z0-9_]+$', new_username): return 400
        if User.query.filter_by(username=new_username).first(): return 409

        # IMPORTANT: Update all historic Result records with the new username
        Result.query.filter_by(user_id=user.id).update({Result.username: new_username})
        user.username = new_username

    # Validates new email (format check, unique)
    if new_email and new_email != user.email:
        if not re.match(r'[^@]+@[^@]+\.[^@]+', new_email): return 400
        if User.query.filter_by(email=new_email).first(): return 409
        user.email = new_email

    # Avatar: only accepts avtar1.jpg through avtar15.jpg
    valid_avatars = [f'avtar{i}.jpg' for i in range(1, 16)]
    if new_profile_picture and new_profile_picture in valid_avatars:
        user.profile_picture = new_profile_picture

    db.session.commit()

    # If username changed → issue a NEW JWT (old one has the old username as identity)
    if user.username != username:
        new_token = create_access_token(identity=user.username)
        response_data["access_token"] = new_token
```

### Avatar & Password APIs (Lines 125–167)
```python
# PATCH /api/user/avatar → Update avatar only (validates against 15 valid filenames)
# PATCH /api/user/password → Change password (requires current_password + new_password ≥ 8 chars)
```

### Category & Question APIs (Lines 169–303)
```python
@api_bp.route('/api/categories', methods=['GET'])
def list_categories():
    # PUBLIC — no auth needed. Returns all categories with question counts.
    cats = Category.query.all()
    return jsonify([{
        "id": c.id, "name": c.name, "description": c.description,
        "icon": c.icon, "quiz_count": len(c.questions)  # Uses ORM relationship
    } for c in cats])

@api_bp.route('/api/categories/<int:cat_id>/questions', methods=['GET'])
def get_questions(cat_id):
    limit = int(request.args.get('limit', 10))       # Default: 10 questions
    difficulty = request.args.get('difficulty', None)  # Optional filter

    query = Question.query.filter_by(category_id=cat_id)
    if difficulty:
        query = query.filter_by(difficulty=difficulty)
    questions = query.limit(limit).all()

    # SECURITY: Options returned WITHOUT is_correct field
    # The client can't see which answer is correct until they submit
    return jsonify([{
        "id": q.id, "text": q.text, "difficulty": q.difficulty,
        "time_limit": q.time_limit,
        "options": [{"id": o.id, "text": o.text} for o in q.options]  # No is_correct!
    } for q in questions])
```

### Quiz Session Persistence (Lines 206–303)
```python
# POST /api/quiz/session/start → Creates a new QuizSession row
#   - Deletes any existing session for same user+category (one active quiz per category)
#   - Stores question_ids as JSON string, initializes score=0, current_index=0

# GET /api/quiz/session/<cat_id> → Returns session progress (index, score, answers)
#   - Returns null (None) if no active session exists

# PATCH /api/quiz/session/<cat_id> → Updates progress (current_index, score, user_answers)
#   - Called after each question to save progress

# DELETE /api/quiz/session/<cat_id> → Clears the session

# POST /api/questions/batch → Fetch multiple questions by IDs
#   - Used when resuming: frontend sends saved question_ids, gets full question data back
#   - Results sorted to match requested ID order using a dict lookup
```

### Answer Checking & Quiz Submission (Lines 305–415)
```python
@api_bp.route('/api/check_answer', methods=['POST'])
def check_answer():
    # Takes question_id + option_id → returns {is_correct, correct_option_id}
    correct_option = Option.query.filter_by(question_id=qid, is_correct=True).first()
    selected_option = Option.query.filter_by(id=oid, question_id=qid).first()
    # REVEALS the correct answer only AFTER the user has answered

@api_bp.route('/api/submit', methods=['POST'])
def submit_quiz():
    answers = data.get('answers', [])          # List of {question_id, option_id}
    username = data.get('username') or "Anonymous"
    category_id = data.get('category_id')
    time_taken = data.get('time_taken', 0)

    cat = Category.query.get(category_id)      # Validate category exists

    correct = 0
    for a in answers:
        # SECURITY: Verify each question belongs to the claimed category
        q = Question.query.filter_by(id=qid, category_id=category_id).first()
        if not q: return 400                   # Question doesn't belong to this category

        opt = Option.query.filter_by(id=oid, question_id=qid).first()
        if opt and opt.is_correct:
            correct += 1                       # Count correct answers

    # Try to identify user from JWT (even though endpoint doesn't require auth)
    user_id = None
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        decoded = decode_token(token)
        user_obj = User.query.filter_by(username=decoded['sub']).first()
        if user_obj: user_id = user_obj.id

    # ONLY save results for authenticated users (not anonymous/demo)
    if user_id:
        result = Result(user_id=user_id, username=username,
                       category_id=category_id, score=correct,
                       total=total, time_taken=time_taken)
        db.session.add(result)

        # Level progression: level = (quizzes_completed / 5) + 1
        quizzes_done = Result.query.filter_by(user_id=user_id).count() + 1
        calculated_level = max(1, quizzes_done // 5 + 1)
        if calculated_level != user.level:
            user.level = calculated_level      # Level up!

        db.session.commit()
        # Clean up active quiz session
        QuizSession.query.filter_by(user_id=user_id, category_id=category_id).delete()

    return jsonify({
        "score": correct, "total": total,
        "percentage": round((correct/total)*100, 2),
        "level_up": new_level                   # Non-null if user leveled up
    })
```

### Leaderboard (Lines 417–468)
```python
@api_bp.route('/api/leaderboard', methods=['GET'])
def leaderboard():
    cat_id = request.args.get('category_id')   # Optional category filter
    limit = int(request.args.get('limit', 10))

    # Join with User table to exclude admins from leaderboard
    query = Result.query.join(User).filter(Result.user_id.isnot(None), User.is_admin == False)

    # Aggregate per user: total score, total questions, total time, quiz count
    user_stats = {}
    for r in all_results:
        # Accumulate stats per user_id
        user_stats[uid]["total_score"] += r.score
        user_stats[uid]["total_questions"] += r.total
        user_stats[uid]["total_time"] += (r.time_taken or 0)
        user_stats[uid]["quizzes"] += 1

    # Calculate accuracy % and avg time for each user
    # Sort by: highest accuracy first, then lowest avg time (tiebreaker)
    ranked.sort(key=lambda x: (-x["percentage"], x["time_taken"]))
    return jsonify(ranked[:limit])
```

### User Analytics (Lines 470–519)
```python
@api_bp.route('/api/user/analytics', methods=['GET'])
@jwt_required()
def user_analytics():
    results = Result.query.filter_by(user_id=user.id).all()

    # Overall stats
    total_score = sum(r.score for r in results)
    total_possible = sum(r.total for r in results)
    overall_accuracy = round((total_score / total_possible * 100), 2)
    total_correct = total_score
    total_incorrect = total_possible - total_score
    avg_time_taken = round(average of all valid time_taken values, 2)

    # Per-category breakdown
    category_stats = {}
    for r in results:
        cat_name = r.category.name
        # Accumulate score/questions/count per category
    # Format into list of {category, accuracy, quizzes_taken}

    return jsonify({
        "total_quizzes", "overall_accuracy", "total_correct",
        "total_incorrect", "avg_time_taken", "category_performance": [...]
    })
```

---

## 2. `static/dark-mode.js` — Dark Mode Toggle Logic

```javascript
(function () {                             // IIFE — runs immediately, no global pollution
  'use strict';

  // Line 9: Read saved theme from localStorage (default: 'light')
  const savedTheme = localStorage.getItem('theme') || 'light';
  // Line 10: Apply theme IMMEDIATELY (before DOM loads → prevents flash of wrong theme)
  document.documentElement.setAttribute('data-theme', savedTheme);

  function updateAllToggles(theme) {
    // Lines 14-31: Find ALL toggle buttons on the page (desktop + mobile)
    // For each toggle: show/hide sun/moon icons based on current theme
    // Update text labels ("Dark Mode" ↔ "Light Mode")
  }

  function init() {
    updateAllToggles(currentTheme);        // Sync toggle icons on page load

    // Line 39: Delegate click handler to document (handles dynamically added toggles)
    document.addEventListener('click', function (e) {
      const toggle = e.target.closest('#darkModeToggle, ...');
      if (!toggle) return;                 // Click wasn't on a toggle → ignore

      e.preventDefault();
      // Toggle theme: dark → light, light → dark
      const newTheme = theme === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', newTheme);  // Apply CSS
      localStorage.setItem('theme', newTheme);  // Persist choice
      updateAllToggles(newTheme);                // Update icons
    });
  }

  // Lines 56-60: Run init when DOM is ready (or immediately if already loaded)
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
```

---

## 3. `static/dark-mode.css` — Dark Mode Stylesheet

```css
/* Lines 5-11: CSS Custom Properties (Light theme defaults) */
:root {
  --bg-primary: #ffffff;         /* Main background */
  --bg-secondary: #f8f9fa;       /* Card/section backgrounds */
  --text-primary: #212529;       /* Main text color */
  --text-secondary: #6c757d;     /* Muted text */
  --border-color: #dee2e6;       /* Borders, dividers */
}

/* Lines 13-19: Dark theme overrides — activated by data-theme="dark" on <html> */
[data-theme="dark"] {
  --bg-primary: #0f172a;         /* Slate 900 — deep dark blue */
  --bg-secondary: #1e293b;       /* Slate 800 */
  --text-primary: #f8fafc;       /* Slate 50 — near white */
  --text-secondary: #94a3b8;     /* Slate 400 — muted gray */
  --border-color: #334155;       /* Slate 700 */
}

/* Lines 22-190: Component-specific dark overrides */
/* Body → dark background + light text */
/* Cards, inputs, navbars, sidebars → dark backgrounds with subtle borders */
/* Quiz buttons → dark background, purple hover effect */
/* Correct answers → green tint; wrong answers → red tint */
/* Scrollbar → dark track + slate thumb */
/* Badges → indigo-tinted backgrounds */
/* All use !important to override existing inline/utility styles */
```

---

*This completes the line-by-line explanation of all QuizVerse source files.*

### 📚 Full Index

| Part | File | Document |
|---|---|---|
| **Part 1** | `extensions.py`, `config.py`, `models.py`, `app.py` | `CODE_EXPLAINED_PART1_CORE.md` |
| **Part 2** | `routes/auth.py`, `routes/main.py` | `CODE_EXPLAINED_PART2_ROUTES.md` |
| **Part 3** | `routes/admin.py` | `CODE_EXPLAINED_PART3_ADMIN.md` |
| **Part 4** | `routes/api.py`, `dark-mode.js`, `dark-mode.css` | `CODE_EXPLAINED_PART4_API_STATIC.md` |
