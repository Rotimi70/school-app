# School Manager

Flask + SQLite school management app: login, Admin/Teacher roles, student CRUD with search, attendance, grades and a dashboard. Runs on free hosting with no paid services.

## Run it locally

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000. The first start creates `school.db` with demo data.

| Role    | Email                  | Password   |
|---------|------------------------|------------|
| Admin   | admin@school.test      | admin123   |
| Teacher | teacher1@school.test   | teacher123 |
| Teacher | teacher2@school.test   | teacher123 |

Teachers only see the classes assigned to them. Admins see everything and manage teachers and classes.

## Project structure

```
school-app/
├── app.py            routes, auth, roles, CSRF, queries, seed data
├── schema.sql        users, classes, students, attendance, grades
├── requirements.txt
├── templates/        Jinja pages
└── static/           style.css, app.js
```

## Push to GitHub

```bash
git init
git add .
git commit -m "School Manager"
git branch -M main
git remote add origin https://github.com/<your-username>/school-app.git
git push -u origin main
```

`.gitignore` keeps `school.db` and secrets out of the repo.

## Deploy free on PythonAnywhere

Free-tier limits change, so check their current terms.

1. Sign up at pythonanywhere.com and open a **Bash console**.
2. `git clone https://github.com/<your-username>/school-app.git`
3. `cd school-app && pip install --user -r requirements.txt`
4. **Web** tab → **Add a new web app** → **Flask** → point it at `~/school-app/app.py`. If it asks for a Python version, pick the same one you installed with.
5. In the **WSGI configuration file**, make sure it imports the app, e.g. `from app import app as application`, and that the project folder is on `sys.path`.
6. Still in the Web tab, add environment variables in the WSGI file **above** the import:
   ```python
   import os
   os.environ["SECRET_KEY"] = "paste-a-long-random-string"
   os.environ["DEMO_MODE"] = "0"
   ```
   Generate a key with `python -c "import secrets; print(secrets.token_hex(32))"`.
7. Press **Reload**. Your link is `https://<username>.pythonanywhere.com`.

## Before you share the public link

- Sign in as admin and **change the demo passwords** (Teachers page for teachers; for the admin, see below).
- Set `DEMO_MODE=0` so the demo credentials box is hidden on the login page.
- Set a real `SECRET_KEY`.

Change the admin password from a Python shell in the project folder:

```bash
python -c "
import sqlite3
from werkzeug.security import generate_password_hash
db = sqlite3.connect('school.db')
db.execute(\"UPDATE users SET password_hash=? WHERE email='admin@school.test'\", (generate_password_hash('YourNewStrongPassword'),))
db.commit()
"
```

## Known limits

- SQLite suits a demo or a small school, not heavy traffic.
- No email password reset: an admin resets teacher passwords.
- No login rate limiting yet.

## Next up

- Student logins (read-only view of their own attendance and grades)
- CSV export for students, attendance and grades
