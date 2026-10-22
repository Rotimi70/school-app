import sqlite3

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash

from core.db import execute, query
from core.security import admin_required

bp = Blueprint("administration", __name__, template_folder="templates")


# --------------------------------------------------------------------------
# Teachers
# --------------------------------------------------------------------------
@bp.route("/teachers")
@admin_required
def teachers():
    rows = query(
        "SELECT u.*, (SELECT GROUP_CONCAT(name, ', ') FROM classes WHERE teacher_id=u.id) AS class_names "
        "FROM users u WHERE u.role='teacher' ORDER BY u.name")
    return render_template("administration/teachers.html", teachers=rows)


@bp.route("/teachers/new", defaults={"tid": None}, methods=["GET", "POST"])
@bp.route("/teachers/<int:tid>/edit", methods=["GET", "POST"])
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
                return redirect(url_for("administration.teachers"))
            except sqlite3.IntegrityError:
                errors.append("That email is already registered.")
        for e in errors:
            flash(e, "error")
    return render_template("administration/teacher_form.html", form=form, tid=tid)


@bp.route("/teachers/<int:tid>/delete", methods=["POST"])
@admin_required
def teacher_delete(tid):
    execute("DELETE FROM users WHERE id=? AND role='teacher'", (tid,))
    flash("Teacher deleted. Their classes are now unassigned.", "success")
    return redirect(url_for("administration.teachers"))


# --------------------------------------------------------------------------
# Classes
# --------------------------------------------------------------------------
@bp.route("/classes")
@admin_required
def classes():
    rows = query(
        "SELECT c.*, u.name AS teacher, (SELECT COUNT(*) FROM students s WHERE s.class_id=c.id) AS n_students "
        "FROM classes c LEFT JOIN users u ON u.id=c.teacher_id ORDER BY c.name")
    return render_template("administration/classes.html", classes=rows)


@bp.route("/classes/new", defaults={"cid": None}, methods=["GET", "POST"])
@bp.route("/classes/<int:cid>/edit", methods=["GET", "POST"])
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
                return redirect(url_for("administration.classes"))
            except sqlite3.IntegrityError:
                flash("A class with that name already exists.", "error")
    return render_template("administration/class_form.html", form=form, cid=cid, teachers=teachers_list)


@bp.route("/classes/<int:cid>/delete", methods=["POST"])
@admin_required
def class_delete(cid):
    n = query("SELECT COUNT(*) AS n FROM students WHERE class_id=?", (cid,), one=True)["n"]
    if n:
        flash("Move or delete the students in this class first.", "error")
    else:
        execute("DELETE FROM classes WHERE id=?", (cid,))
        flash("Class deleted.", "success")
    return redirect(url_for("administration.classes"))
