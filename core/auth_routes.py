"""Login, logout, the plain home page and the system-status page."""
from flask import (Blueprint, current_app, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash

from .db import query
from .security import (admin_required, any_login_required, clear_failures, home_url,
                       record_failure, too_many_failures)

core_bp = Blueprint("core", __name__)


@core_bp.route("/")
def index():
    return redirect(home_url(g.user) if g.user else url_for("core.login"))


@core_bp.route("/home")
@any_login_required
def home():
    """Landing page used when the dashboard module isn't available."""
    return render_template("home.html")


@core_bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(home_url(g.user))
    if request.method == "POST":
        # Staff sign in with their email, students with their matric number.
        ident = request.form.get("email", "").strip().lower()[:100]
        password = request.form.get("password", "")
        if too_many_failures(ident):
            flash("Too many failed attempts. Please wait 10 minutes and try again.", "error")
            return render_template("login.html"), 429
        user = query("SELECT * FROM users WHERE email=?", (ident,), one=True)
        if user and check_password_hash(user["password_hash"], password):
            clear_failures(ident)
            session.clear()
            session["uid"] = user["id"]
            return redirect(home_url(user))
        acct = query(
            "SELECT s.id, a.password_hash FROM students s "
            "JOIN student_accounts a ON a.student_id = s.id WHERE s.matric_no=?",
            (ident.upper(),), one=True) if _student_logins_available() else None
        if acct and check_password_hash(acct["password_hash"], password):
            clear_failures(ident)
            session.clear()
            session["sid"] = acct["id"]
            return redirect(home_url({"role": "student"}))
        record_failure(ident)
        flash("Incorrect email, matric number or password.", "error")
    return render_template("login.html")


def _student_logins_available():
    """Staff can still sign in even if the student-login table has a problem."""
    try:
        query("SELECT 1 FROM student_accounts LIMIT 1")
        return True
    except Exception:
        current_app.logger.exception("student_accounts table unavailable")
        return False


@core_bp.route("/logout", methods=["POST"])
@any_login_required
def logout():
    session.clear()
    return redirect(url_for("core.login"))


@core_bp.route("/system")
@admin_required
def system_status():
    return render_template("system_status.html", modules=current_app.config.get("MODULE_STATUS", []))
