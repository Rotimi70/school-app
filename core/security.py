"""Login sessions, CSRF protection, permissions and a simple brute-force brake."""
import hmac
import secrets
import sqlite3
import threading
import time
from functools import wraps

from flask import abort, g, redirect, request, session, url_for
from werkzeug.routing import BuildError

from .db import query


# --------------------------------------------------------------------------
# Who is signed in?
# --------------------------------------------------------------------------
def load_user():
    g.user = None
    uid = session.get("uid")
    sid = session.get("sid")
    if uid:
        g.user = query("SELECT id, name, email, role FROM users WHERE id=?", (uid,), one=True)
        if g.user is None:
            session.clear()
    elif sid:
        try:
            row = query(
                "SELECT s.id, s.name, s.matric_no FROM students s "
                "JOIN student_accounts a ON a.student_id = s.id WHERE s.id=?", (sid,), one=True)
        except sqlite3.Error:
            row = None  # student logins unavailable: treat as signed out, staff are unaffected
        if row is None:
            session.clear()
        else:
            g.user = {"id": row["id"], "name": row["name"], "email": row["matric_no"],
                      "role": "student", "student_id": row["id"]}


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


def init_security(app):
    app.before_request(load_user)
    app.before_request(csrf_protect)
    app.jinja_env.globals["csrf_token"] = csrf_token


def home_url(user):
    """Where a signed-in user lands. Falls back to a plain page if that module is unavailable."""
    target = "students.me" if user["role"] == "student" else "dashboard.dashboard"
    try:
        return url_for(target)
    except BuildError:
        return url_for("core.home")


# --------------------------------------------------------------------------
# Access decorators
# --------------------------------------------------------------------------
def login_required(view):
    """Staff only (admin or teacher). Students are sent to their own page."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("core.login"))
        if g.user["role"] == "student":
            return redirect(home_url(g.user))
        return view(*args, **kwargs)
    return wrapped


def any_login_required(view):
    """Any signed-in user, including students."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("core.login"))
        return view(*args, **kwargs)
    return wrapped


def student_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("core.login"))
        if g.user["role"] != "student":
            return redirect(home_url(g.user))
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


# --------------------------------------------------------------------------
# What may this staff member see?
# --------------------------------------------------------------------------
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


def pick_class(classes):
    ids = [c["id"] for c in classes]
    class_id = request.values.get("class_id", type=int)
    if class_id is not None and class_id not in ids:
        abort(403, "That class is not assigned to you.")
    return class_id or (ids[0] if ids else None)


# --------------------------------------------------------------------------
# Brake on password guessing: 5 failures per login name per 10 minutes.
# Kept in memory, so it resets whenever the app reloads.
# --------------------------------------------------------------------------
MAX_FAILS = 5
FAIL_WINDOW = 600  # seconds
_failed = {}
_failed_lock = threading.Lock()


def too_many_failures(ident):
    now = time.time()
    with _failed_lock:
        for key in [k for k, v in _failed.items() if not v or now - v[-1] > FAIL_WINDOW]:
            del _failed[key]
        recent = [t for t in _failed.get(ident, []) if now - t < FAIL_WINDOW]
        return len(recent) >= MAX_FAILS


def record_failure(ident):
    with _failed_lock:
        _failed.setdefault(ident, []).append(time.time())


def clear_failures(ident):
    with _failed_lock:
        _failed.pop(ident, None)
