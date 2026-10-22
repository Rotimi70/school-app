import sqlite3

from flask import (Blueprint, current_app, flash, g, redirect, render_template, request, url_for)
from werkzeug.security import generate_password_hash

from core.csvutil import csv_response
from core.db import execute, placeholders, query
from core.panels import render_student_panels
from core.security import (admin_required, get_student_or_404, login_required, my_classes,
                           student_required)

bp = Blueprint("students", __name__, template_folder="templates")


def filtered_students():
    """Students the current user may see, narrowed by ?q= and ?class_id=."""
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
    return q, classes, class_id, rows


@bp.route("/students")
@login_required
def students():
    q, classes, class_id, rows = filtered_students()
    return render_template("students/students.html", students=rows, classes=classes, q=q, class_id=class_id)


@bp.route("/students/export.csv")
@login_required
def students_export():
    _q, _classes, _class_id, rows = filtered_students()
    return csv_response(
        "students.csv", ["Matric No", "Name", "Email", "Class", "Added"],
        [(r["matric_no"], r["name"], r["email"], r["class_name"], r["created_at"][:10]) for r in rows])


def student_summary(sid):
    """Attendance and grade figures for one student (used by staff and student pages).

    Those tables belong to other modules, so if one is unavailable we show empty figures.
    """
    summary = {"counts": {}, "rate": None, "recent": [], "grades": [], "avg": None}
    try:
        counts = {r["status"]: r["n"] for r in query(
            "SELECT status, COUNT(*) AS n FROM attendance WHERE student_id=? GROUP BY status", (sid,))}
        total = sum(counts.values())
        attended = counts.get("present", 0) + counts.get("late", 0)
        summary["counts"] = counts
        summary["rate"] = round(100 * attended / total, 1) if total else None
        summary["recent"] = query(
            "SELECT date, status FROM attendance WHERE student_id=? ORDER BY date DESC LIMIT 10", (sid,))
    except sqlite3.Error:
        current_app.logger.exception("Attendance figures unavailable")
    try:
        grades = query("SELECT subject, term, score FROM grades WHERE student_id=? ORDER BY term, subject", (sid,))
        summary["grades"] = grades
        summary["avg"] = round(sum(g_["score"] for g_ in grades) / len(grades), 1) if grades else None
    except sqlite3.Error:
        current_app.logger.exception("Grade figures unavailable")
    return summary


@bp.route("/students/<int:sid>")
@login_required
def student_detail(sid):
    student = get_student_or_404(sid)
    has_account = query("SELECT 1 FROM student_accounts WHERE student_id=?", (sid,), one=True) is not None
    return render_template("students/student_detail.html", student=student, has_account=has_account,
                           panels=render_student_panels(student), **student_summary(sid))


# --------------------------------------------------------------------------
# Student portal: a student sees only their own profile
# --------------------------------------------------------------------------
@bp.route("/me")
@student_required
def me():
    student = query(
        "SELECT s.*, c.name AS class_name FROM students s "
        "JOIN classes c ON c.id = s.class_id WHERE s.id=?", (g.user["student_id"],), one=True)
    return render_template("students/student_portal.html", student=student, **student_summary(student["id"]))


@bp.route("/students/<int:sid>/account", methods=["POST"])
@login_required
def student_account_set(sid):
    """Create or reset a student's login. Teachers: own classes only; admins: any."""
    student = get_student_or_404(sid)
    password = request.form.get("password", "")
    if len(password) < 8:
        flash("The password must be at least 8 characters.", "error")
    else:
        execute(
            "INSERT INTO student_accounts (student_id, password_hash) VALUES (?,?) "
            "ON CONFLICT(student_id) DO UPDATE SET password_hash=excluded.password_hash",
            (sid, generate_password_hash(password)))
        flash(f"Login saved. {student['name']} signs in with matric number {student['matric_no']}.", "success")
    return redirect(url_for("students.student_detail", sid=sid))


@bp.route("/students/<int:sid>/account/delete", methods=["POST"])
@login_required
def student_account_delete(sid):
    student = get_student_or_404(sid)
    execute("DELETE FROM student_accounts WHERE student_id=?", (sid,))
    flash(f"{student['name']} can no longer sign in.", "success")
    return redirect(url_for("students.student_detail", sid=sid))


# --------------------------------------------------------------------------
# Create / edit / delete
# --------------------------------------------------------------------------
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


@bp.route("/students/new", defaults={"sid": None}, methods=["GET", "POST"])
@bp.route("/students/<int:sid>/edit", methods=["GET", "POST"])
@login_required
def student_form(sid):
    student = get_student_or_404(sid) if sid else None
    classes = my_classes()
    allowed = [c["id"] for c in classes]
    if not allowed:
        flash("No classes are assigned to you yet. Ask an administrator.", "error")
        return redirect(url_for("students.students"))

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
                return redirect(url_for("students.students"))
            except sqlite3.IntegrityError:
                errors.append("That matric number is already in use.")
        for e in errors:
            flash(e, "error")
    return render_template("students/student_form.html", form=form, sid=sid, classes=classes)


@bp.route("/students/<int:sid>/delete", methods=["POST"])
@admin_required
def student_delete(sid):
    get_student_or_404(sid)
    execute("DELETE FROM students WHERE id=?", (sid,))
    flash("Student deleted.", "success")
    return redirect(url_for("students.students"))
