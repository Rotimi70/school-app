"""School Manager: Flask + SQLite.

Roles
  admin   - manages teachers, classes and every student; sees all stats
  teacher - sees and manages only the classes assigned to them

Every permission is enforced here on the server, not just hidden in the UI.
"""
import hmac
import os
import random
import secrets
import sqlite3
from datetime import date, timedelta
from functools import wraps

from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   session, url_for)
from markupsafe import Markup
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.environ.get("DATABASE", os.path.join(BASE_DIR, "school.db"))

STATUSES = ("present", "late", "absent")
TERMS = ("Term 1", "Term 2", "Term 3")
DEFAULT_SUBJECTS = ("Mathematics", "English", "Science")

app = Flask(__name__)
app.config.update(
    # Set SECRET_KEY as an environment variable on your host. The fallback is for local use only.
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    DEMO_MODE=os.environ.get("DEMO_MODE", "1") == "1",
)

# --------------------------------------------------------------------------
# Icons (feather-style, inline SVG so there are no external dependencies)
# --------------------------------------------------------------------------
ICONS = {
    "home": '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
    "users": '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "check": '<polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>',
    "award": '<circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/>',
    "briefcase": '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
    "layers": '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
    "logout": '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
    "menu": '<line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/>',
    "search": '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
    "plus": '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
    "percent": '<line x1="19" y1="5" x2="5" y2="19"/><circle cx="6.5" cy="6.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/>',
}


def icon(name):
    return Markup(
        '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true">%s</svg>' % ICONS[name]
    )


app.jinja_env.globals["icon"] = icon


# --------------------------------------------------------------------------
# Database helpers
# --------------------------------------------------------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query(sql, args=(), one=False):
    rows = get_db().execute(sql, args).fetchall()
    if one:
        return rows[0] if rows else None
    return rows


def execute(sql, args=()):
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur


def placeholders(n):
    return ",".join("?" * n)


def init_db():
    db = sqlite3.connect(DATABASE)
    with open(os.path.join(BASE_DIR, "schema.sql"), encoding="utf-8") as f:
        db.executescript(f.read())
    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        seed(db)
    db.commit()
    db.close()


def seed(db):
    """Demo data so the app is useful the moment it starts."""
    rnd = random.Random(7)
    db.execute(
        "INSERT INTO users (name, email, password_hash, role) VALUES (?,?,?,?)",
        ("Admin User", "admin@school.test", generate_password_hash("admin123"), "admin"),
    )
    teacher_hash = generate_password_hash("teacher123")
    for name, email in (("Mrs. Adeyemi", "teacher1@school.test"),
                        ("Mr. Bello", "teacher2@school.test")):
        db.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?,?,?,'teacher')",
            (name, email, teacher_hash),
        )
    t1, t2 = [r[0] for r in db.execute("SELECT id FROM users WHERE role='teacher' ORDER BY id")]
    class_ids = []
    for cname, tid in (("JSS 1A", t1), ("JSS 2A", t2), ("SS 1A", t1)):
        cur = db.execute("INSERT INTO classes (name, teacher_id) VALUES (?,?)", (cname, tid))
        class_ids.append(cur.lastrowid)

    first = ["Amina", "Chinedu", "Tolu", "Ibrahim", "Ngozi", "Emeka", "Fatima", "Seun",
             "Blessing", "Musa", "Zainab", "Daniel", "Halima", "Kunle", "Grace", "Yusuf"]
    last = ["Okafor", "Bello", "Adeyemi", "Musa", "Eze", "Ibrahim", "Balogun", "Danjuma",
            "Okoro", "Lawal", "Abubakar", "Nwosu", "Garba", "Afolabi"]
    student_ids, n = [], 0
    for cid in class_ids:
        for _ in range(8):
            n += 1
            cur = db.execute(
                "INSERT INTO students (name, matric_no, email, class_id) VALUES (?,?,?,?)",
                (f"{rnd.choice(first)} {rnd.choice(last)}", f"SCH/2026/{n:03d}",
                 f"student{n}@school.test", cid),
            )
            student_ids.append(cur.lastrowid)

    days, d = [], date.today()
    while len(days) < 10:
        if d.weekday() < 5:
            days.append(d)
        d -= timedelta(days=1)
    for sid in student_ids:
        for day in days:
            status = rnd.choices(STATUSES, [85, 7, 8])[0]
            db.execute("INSERT INTO attendance (student_id, date, status) VALUES (?,?,?)",
                       (sid, day.isoformat(), status))
        for subject in DEFAULT_SUBJECTS:
            score = max(35, min(98, round(rnd.gauss(68, 14))))
            db.execute("INSERT INTO grades (student_id, subject, term, score) VALUES (?,?,?,?)",
                       (sid, subject, "Term 1", score))


# --------------------------------------------------------------------------
# Auth, sessions, CSRF
# --------------------------------------------------------------------------
@app.before_request
def load_user():
    g.user = None
    uid = session.get("uid")
    if uid:
        g.user = query("SELECT id, name, email, role FROM users WHERE id=?", (uid,), one=True)
        if g.user is None:
            session.clear()


@app.before_request
def csrf_protect():
    if request.method == "POST":
        sent = request.form.get("csrf_token", "").encode()
        expected = session.get("csrf_token", "").encode()
        if not expected or not hmac.compare_digest(sent, expected):
            abort(400, "Your session expired or the form was invalid. Please go back and try again.")


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]


app.jinja_env.globals["csrf_token"] = csrf_token


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if g.user["role"] != "admin":
            abort(403, "Only administrators can do that.")
        return view(*args, **kwargs)
    return wrapped


def is_admin():
    return g.user["role"] == "admin"


def my_classes():
    """Classes the current user is allowed to work with."""
    if is_admin():
        return query("SELECT * FROM classes ORDER BY name")
    return query("SELECT * FROM classes WHERE teacher_id=? ORDER BY name", (g.user["id"],))


def my_class_ids():
    return [c["id"] for c in my_classes()]


def get_student_or_404(sid):
    student = query(
        "SELECT s.*, c.name AS class_name FROM students s "
        "JOIN classes c ON c.id = s.class_id WHERE s.id=?", (sid,), one=True)
    if student is None:
        abort(404)
    if not is_admin() and student["class_id"] not in my_class_ids():
        abort(403, "That student is not in one of your classes.")
    return student


@app.errorhandler(400)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(405)
def http_error(err):
    return render_template("error.html", code=err.code, message=err.description), err.code


# --------------------------------------------------------------------------
# Login / logout
# --------------------------------------------------------------------------
@app.route("/")
def index():
    return redirect(url_for("dashboard" if g.user else "login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = query("SELECT * FROM users WHERE email=?", (email,), one=True)
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["uid"] = user["id"]
            return redirect(url_for("dashboard"))
        flash("Incorrect email or password.", "error")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))


# --------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    ids = my_class_ids() or [-1]
    ph = placeholders(len(ids))
    since = (date.today() - timedelta(days=30)).isoformat()

    total_students = query(f"SELECT COUNT(*) AS n FROM students WHERE class_id IN ({ph})", ids, one=True)["n"]
    att = query(
        f"SELECT COUNT(*) AS total, COALESCE(SUM(a.status IN ('present','late')),0) AS ok "
        f"FROM attendance a JOIN students s ON s.id=a.student_id "
        f"WHERE s.class_id IN ({ph}) AND a.date >= ?", ids + [since], one=True)
    att_rate = round(100 * att["ok"] / att["total"], 1) if att["total"] else None
    avg_grade = query(
        f"SELECT ROUND(AVG(g.score),1) AS avg FROM grades g JOIN students s ON s.id=g.student_id "
        f"WHERE s.class_id IN ({ph})", ids, one=True)["avg"]

    trend_rows = query(
        f"SELECT a.date, ROUND(100.0*SUM(a.status IN ('present','late'))/COUNT(*)) AS rate "
        f"FROM attendance a JOIN students s ON s.id=a.student_id "
        f"WHERE s.class_id IN ({ph}) AND a.date >= ? GROUP BY a.date ORDER BY a.date",
        ids + [(date.today() - timedelta(days=21)).isoformat()])
    trend = [{"label": date.fromisoformat(r["date"]).strftime("%a %d"), "rate": int(r["rate"])}
             for r in trend_rows][-7:]

    per_class = query(
        f"""SELECT c.id, c.name, u.name AS teacher,
              (SELECT COUNT(*) FROM students s WHERE s.class_id=c.id) AS n_students,
              (SELECT ROUND(100.0*SUM(a.status IN ('present','late'))/COUNT(*),1)
                 FROM attendance a JOIN students s ON s.id=a.student_id
                 WHERE s.class_id=c.id AND a.date >= ?) AS att_rate,
              (SELECT ROUND(AVG(g.score),1) FROM grades g JOIN students s ON s.id=g.student_id
                 WHERE s.class_id=c.id) AS avg_grade
            FROM classes c LEFT JOIN users u ON u.id=c.teacher_id
            WHERE c.id IN ({ph}) ORDER BY c.name""", [since] + ids)

    stats = {
        "students": total_students,
        "classes": len(per_class),
        "teachers": query("SELECT COUNT(*) AS n FROM users WHERE role='teacher'", one=True)["n"],
        "att_rate": att_rate,
        "avg_grade": avg_grade,
    }
    return render_template("dashboard.html", stats=stats, trend=trend, per_class=per_class)


# --------------------------------------------------------------------------
# Students: list + search, detail, create/edit, delete
# --------------------------------------------------------------------------
@app.route("/students")
@login_required
def students():
    q = request.args.get("q", "").strip()
    classes = my_classes()
    ids = [c["id"] for c in classes]
    class_id = request.args.get("class_id", type=int)
    if class_id not in ids:
        class_id = None

    target = [class_id] if class_id else ids
    rows = []
    if target:
        where = [f"s.class_id IN ({placeholders(len(target))})"]
        args = list(target)
        if q:
            where.append("(s.name LIKE ? OR s.matric_no LIKE ? OR s.email LIKE ?)")
            args += [f"%{q}%"] * 3
        rows = query(
            "SELECT s.*, c.name AS class_name FROM students s JOIN classes c ON c.id=s.class_id "
            f"WHERE {' AND '.join(where)} ORDER BY s.name", args)
    return render_template("students.html", students=rows, classes=classes, q=q, class_id=class_id)


@app.route("/students/<int:sid>")
@login_required
def student_detail(sid):
    student = get_student_or_404(sid)
    counts = {r["status"]: r["n"] for r in query(
        "SELECT status, COUNT(*) AS n FROM attendance WHERE student_id=? GROUP BY status", (sid,))}
    total = sum(counts.values())
    attended = counts.get("present", 0) + counts.get("late", 0)
    rate = round(100 * attended / total, 1) if total else None
    recent = query("SELECT date, status FROM attendance WHERE student_id=? ORDER BY date DESC LIMIT 10", (sid,))
    grades = query("SELECT subject, term, score FROM grades WHERE student_id=? ORDER BY term, subject", (sid,))
    avg = round(sum(g_["score"] for g_ in grades) / len(grades), 1) if grades else None
    return render_template("student_detail.html", student=student, counts=counts, rate=rate,
                           recent=recent, grades=grades, avg=avg)


def parse_student_form(allowed_ids):
    data = {
        "name": request.form.get("name", "").strip(),
        "matric_no": request.form.get("matric_no", "").strip().upper(),
        "email": request.form.get("email", "").strip().lower(),
        "class_id": request.form.get("class_id", type=int),
    }
    errors = []
    if not data["name"]:
        errors.append("Name is required.")
    if not data["matric_no"]:
        errors.append("Matric number is required.")
    if data["email"] and ("@" not in data["email"] or "." not in data["email"]):
        errors.append("Enter a valid email address or leave it blank.")
    if data["class_id"] not in allowed_ids:
        errors.append("Choose a valid class.")
    return data, errors


@app.route("/students/new", defaults={"sid": None}, methods=["GET", "POST"])
@app.route("/students/<int:sid>/edit", methods=["GET", "POST"])
@login_required
def student_form(sid):
    student = get_student_or_404(sid) if sid else None
    classes = my_classes()
    allowed = [c["id"] for c in classes]
    if not allowed:
        flash("No classes are assigned to you yet. Ask an administrator.", "error")
        return redirect(url_for("students"))

    form = dict(student) if student else {"name": "", "matric_no": "", "email": "", "class_id": allowed[0]}
    if request.method == "POST":
        data, errors = parse_student_form(allowed)
        form.update(data)
        if not errors:
            try:
                if sid:
                    execute("UPDATE students SET name=?, matric_no=?, email=?, class_id=? WHERE id=?",
                            (data["name"], data["matric_no"], data["email"] or None, data["class_id"], sid))
                    flash("Student updated.", "success")
                else:
                    execute("INSERT INTO students (name, matric_no, email, class_id) VALUES (?,?,?,?)",
                            (data["name"], data["matric_no"], data["email"] or None, data["class_id"]))
                    flash("Student added.", "success")
                return redirect(url_for("students"))
            except sqlite3.IntegrityError:
                errors.append("That matric number is already in use.")
        for e in errors:
            flash(e, "error")
    return render_template("student_form.html", form=form, sid=sid, classes=classes)


@app.route("/students/<int:sid>/delete", methods=["POST"])
@admin_required
def student_delete(sid):
    get_student_or_404(sid)
    execute("DELETE FROM students WHERE id=?", (sid,))
    flash("Student deleted.", "success")
    return redirect(url_for("students"))


# --------------------------------------------------------------------------
# Attendance
# --------------------------------------------------------------------------
def pick_class(classes):
    ids = [c["id"] for c in classes]
    class_id = request.values.get("class_id", type=int)
    if class_id is not None and class_id not in ids:
        abort(403, "That class is not assigned to you.")
    return class_id or (ids[0] if ids else None)


@app.route("/attendance", methods=["GET", "POST"])
@login_required
def attendance():
    classes = my_classes()
    class_id = pick_class(classes)
    try:
        day = date.fromisoformat(request.values.get("date", ""))
    except ValueError:
        day = date.today()

    roster = []
    if class_id:
        roster = query("SELECT id, name, matric_no FROM students WHERE class_id=? ORDER BY name", (class_id,))

    if request.method == "POST":
        if day > date.today():
            flash("You can't mark attendance for a future date.", "error")
        else:
            db = get_db()
            for s in roster:
                status = request.form.get(f"status_{s['id']}")
                if status in STATUSES:
                    db.execute(
                        "INSERT INTO attendance (student_id, date, status) VALUES (?,?,?) "
                        "ON CONFLICT(student_id, date) DO UPDATE SET status=excluded.status",
                        (s["id"], day.isoformat(), status))
            db.commit()
            flash(f"Attendance saved for {day.strftime('%A, %d %B %Y')}.", "success")
        return redirect(url_for("attendance", class_id=class_id, date=day.isoformat()))

    marked = {r["student_id"]: r["status"] for r in query(
        "SELECT student_id, status FROM attendance WHERE date=? AND student_id IN "
        "(SELECT id FROM students WHERE class_id=?)", (day.isoformat(), class_id))}
    rows = [{"id": s["id"], "name": s["name"], "matric_no": s["matric_no"], "status": marked.get(s["id"])}
            for s in roster]
    return render_template("attendance.html", classes=classes, class_id=class_id, day=day.isoformat(),
                           today=date.today().isoformat(), rows=rows)


# --------------------------------------------------------------------------
# Grades
# --------------------------------------------------------------------------
@app.route("/grades", methods=["GET", "POST"])
@login_required
def grades():
    classes = my_classes()
    class_id = pick_class(classes)
    subject = request.values.get("subject", "").strip()
    term = request.values.get("term", TERMS[0])
    if term not in TERMS:
        term = TERMS[0]

    roster = []
    if class_id:
        roster = query("SELECT id, name, matric_no FROM students WHERE class_id=? ORDER BY name", (class_id,))

    if request.method == "POST":
        if not subject:
            flash("Enter a subject before saving scores.", "error")
        else:
            db, bad = get_db(), []
            for s in roster:
                raw = request.form.get(f"score_{s['id']}", "").strip()
                if raw == "":
                    db.execute("DELETE FROM grades WHERE student_id=? AND subject=? AND term=?",
                               (s["id"], subject, term))
                    continue
                try:
                    score = float(raw)
                    if not 0 <= score <= 100:
                        raise ValueError
                except ValueError:
                    bad.append(s["name"])
                    continue
                db.execute(
                    "INSERT INTO grades (student_id, subject, term, score) VALUES (?,?,?,?) "
                    "ON CONFLICT(student_id, subject, term) DO UPDATE SET score=excluded.score",
                    (s["id"], subject, term, score))
            db.commit()
            if bad:
                flash("Scores must be between 0 and 100. Skipped: " + ", ".join(bad), "error")
            else:
                flash(f"{subject} ({term}) scores saved.", "success")
        return redirect(url_for("grades", class_id=class_id, subject=subject, term=term))

    scores = {}
    if subject and class_id:
        scores = {r["student_id"]: r["score"] for r in query(
            "SELECT student_id, score FROM grades WHERE subject=? AND term=? AND student_id IN "
            "(SELECT id FROM students WHERE class_id=?)", (subject, term, class_id))}
    rows = [{"id": s["id"], "name": s["name"], "matric_no": s["matric_no"], "score": scores.get(s["id"])}
            for s in roster]
    known = [r["subject"] for r in query("SELECT DISTINCT subject FROM grades ORDER BY subject")]
    subjects = sorted(set(known) | set(DEFAULT_SUBJECTS))
    return render_template("grades.html", classes=classes, class_id=class_id, subject=subject,
                           term=term, terms=TERMS, subjects=subjects, rows=rows)


# --------------------------------------------------------------------------
# Admin: teachers
# --------------------------------------------------------------------------
@app.route("/teachers")
@admin_required
def teachers():
    rows = query(
        "SELECT u.*, (SELECT GROUP_CONCAT(name, ', ') FROM classes WHERE teacher_id=u.id) AS class_names "
        "FROM users u WHERE u.role='teacher' ORDER BY u.name")
    return render_template("teachers.html", teachers=rows)


@app.route("/teachers/new", defaults={"tid": None}, methods=["GET", "POST"])
@app.route("/teachers/<int:tid>/edit", methods=["GET", "POST"])
@admin_required
def teacher_form(tid):
    teacher = None
    if tid:
        teacher = query("SELECT * FROM users WHERE id=? AND role='teacher'", (tid,), one=True)
        if teacher is None:
            abort(404)
    form = {"name": teacher["name"], "email": teacher["email"]} if teacher else {"name": "", "email": ""}
    if request.method == "POST":
        form["name"] = request.form.get("name", "").strip()
        form["email"] = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        errors = []
        if not form["name"]:
            errors.append("Name is required.")
        if "@" not in form["email"]:
            errors.append("Enter a valid email address.")
        if (not teacher or password) and len(password) < 8:
            errors.append("Password must be at least 8 characters." if not teacher
                          else "The new password must be at least 8 characters.")
        if not errors:
            try:
                if teacher:
                    execute("UPDATE users SET name=?, email=? WHERE id=?", (form["name"], form["email"], tid))
                    if password:
                        execute("UPDATE users SET password_hash=? WHERE id=?",
                                (generate_password_hash(password), tid))
                    flash("Teacher updated.", "success")
                else:
                    execute("INSERT INTO users (name, email, password_hash, role) VALUES (?,?,?,'teacher')",
                            (form["name"], form["email"], generate_password_hash(password)))
                    flash("Teacher account created.", "success")
                return redirect(url_for("teachers"))
            except sqlite3.IntegrityError:
                errors.append("That email is already registered.")
        for e in errors:
            flash(e, "error")
    return render_template("teacher_form.html", form=form, tid=tid)


@app.route("/teachers/<int:tid>/delete", methods=["POST"])
@admin_required
def teacher_delete(tid):
    execute("DELETE FROM users WHERE id=? AND role='teacher'", (tid,))
    flash("Teacher deleted. Their classes are now unassigned.", "success")
    return redirect(url_for("teachers"))


# --------------------------------------------------------------------------
# Admin: classes
# --------------------------------------------------------------------------
@app.route("/classes")
@admin_required
def classes():
    rows = query(
        "SELECT c.*, u.name AS teacher, (SELECT COUNT(*) FROM students s WHERE s.class_id=c.id) AS n_students "
        "FROM classes c LEFT JOIN users u ON u.id=c.teacher_id ORDER BY c.name")
    return render_template("classes.html", classes=rows)


@app.route("/classes/new", defaults={"cid": None}, methods=["GET", "POST"])
@app.route("/classes/<int:cid>/edit", methods=["GET", "POST"])
@admin_required
def class_form(cid):
    klass = None
    if cid:
        klass = query("SELECT * FROM classes WHERE id=?", (cid,), one=True)
        if klass is None:
            abort(404)
    form = dict(klass) if klass else {"name": "", "teacher_id": None}
    teachers_list = query("SELECT id, name FROM users WHERE role='teacher' ORDER BY name")
    if request.method == "POST":
        form["name"] = request.form.get("name", "").strip()
        form["teacher_id"] = request.form.get("teacher_id", type=int)
        valid_teachers = {t["id"] for t in teachers_list}
        if form["teacher_id"] not in valid_teachers:
            form["teacher_id"] = None
        if not form["name"]:
            flash("Class name is required.", "error")
        else:
            try:
                if klass:
                    execute("UPDATE classes SET name=?, teacher_id=? WHERE id=?",
                            (form["name"], form["teacher_id"], cid))
                    flash("Class updated.", "success")
                else:
                    execute("INSERT INTO classes (name, teacher_id) VALUES (?,?)",
                            (form["name"], form["teacher_id"]))
                    flash("Class created.", "success")
                return redirect(url_for("classes"))
            except sqlite3.IntegrityError:
                flash("A class with that name already exists.", "error")
    return render_template("class_form.html", form=form, cid=cid, teachers=teachers_list)


@app.route("/classes/<int:cid>/delete", methods=["POST"])
@admin_required
def class_delete(cid):
    n = query("SELECT COUNT(*) AS n FROM students WHERE class_id=?", (cid,), one=True)["n"]
    if n:
        flash("Move or delete the students in this class first.", "error")
    else:
        execute("DELETE FROM classes WHERE id=?", (cid,))
        flash("Class deleted.", "success")
    return redirect(url_for("classes"))


# Create the database and demo data on first start (also works under WSGI hosts).
init_db()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
