import re
import sqlite3
from datetime import date

from flask import (Blueprint, abort, current_app, flash, redirect, render_template, request,
                   url_for)

from core.csvutil import csv_response
from core.db import execute, get_db, query
from core.security import admin_required
from core.ui import safe_url

from .ids import next_number

bp = Blueprint("admissions", __name__, template_folder="templates")

STATUSES = ("applied", "review", "offered", "accepted", "enrolled", "rejected", "withdrawn")
STATUS_LABELS = {
    "applied": "Applied", "review": "Under review", "offered": "Offered a place",
    "accepted": "Offer accepted", "enrolled": "Enrolled", "rejected": "Rejected", "withdrawn": "Withdrawn",
}
STATUS_BADGE = {
    "applied": "gray", "review": "amber", "offered": "indigo", "accepted": "green",
    "enrolled": "green", "rejected": "red", "withdrawn": "gray",
}
# Which status can follow which. "enrolled" is only reached through the Enrol button.
NEXT_STATUSES = {
    "applied": ("review", "offered", "rejected", "withdrawn"),
    "review": ("offered", "rejected", "withdrawn"),
    "offered": ("accepted", "rejected", "withdrawn"),
    "accepted": ("withdrawn",),
    "rejected": ("review",),
    "withdrawn": ("review",),
    "enrolled": (),
}
ACTION_LABELS = {
    "review": "Start review", "offered": "Offer a place", "accepted": "Mark offer accepted",
    "rejected": "Reject", "withdrawn": "Withdraw",
}
ACTION_STYLE = {"rejected": "danger", "withdrawn": "danger"}
GENDERS = ("male", "female", "other")
RELATIONSHIPS = ("Father", "Mother", "Guardian", "Grandparent", "Sibling", "Uncle/Aunt", "Other")


@bp.context_processor
def helpers():
    return {"STATUS_LABELS": STATUS_LABELS, "STATUS_BADGE": STATUS_BADGE, "GENDERS": GENDERS,
            "RELATIONSHIPS": RELATIONSHIPS, "ACTION_LABELS": ACTION_LABELS, "ACTION_STYLE": ACTION_STYLE}


def default_academic_year():
    t = date.today()
    start = t.year if t.month >= 8 else t.year - 1
    return f"{start}/{start + 1}"


def clean(name, limit=200):
    return request.form.get(name, "").strip()[:limit]


def get_application_or_404(aid):
    row = query(
        "SELECT a.*, c.name AS class_name FROM applications a LEFT JOIN classes c ON c.id=a.class_id "
        "WHERE a.id=?", (aid,), one=True)
    if row is None:
        abort(404)
    return row


# --------------------------------------------------------------------------
# List, search, export
# --------------------------------------------------------------------------
def filtered_applications():
    status = request.args.get("status", "")
    if status not in STATUSES:
        status = ""
    q = request.args.get("q", "").strip()
    where, args = [], []
    if status:
        where.append("a.status=?")
        args.append(status)
    if q:
        where.append("(a.application_no LIKE ? OR a.first_name LIKE ? OR a.last_name LIKE ? "
                     "OR a.phone LIKE ? OR a.email LIKE ?)")
        args += [f"%{q}%"] * 5
    sql = "SELECT a.*, c.name AS class_name FROM applications a LEFT JOIN classes c ON c.id=a.class_id"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY a.id DESC"
    return status, q, query(sql, args)


@bp.route("/admissions")
@admin_required
def applications():
    status, q, rows = filtered_applications()
    counts = {r["status"]: r["n"] for r in query("SELECT status, COUNT(*) AS n FROM applications GROUP BY status")}
    return render_template("admissions/list.html", rows=rows, status=status, q=q, counts=counts,
                           total=sum(counts.values()), statuses=STATUSES)


@bp.route("/admissions/export.csv")
@admin_required
def applications_export():
    _status, _q, rows = filtered_applications()
    header = ["Application No", "First Name", "Last Name", "Class Applied", "Academic Year", "Status",
              "Applied On", "Date of Birth", "Gender", "Phone", "Email", "Previous School", "Matric No"]
    out = []
    for r in rows:
        matric = None
        if r["student_id"]:
            s = query("SELECT matric_no FROM students WHERE id=?", (r["student_id"],), one=True)
            matric = s["matric_no"] if s else None
        out.append((r["application_no"], r["first_name"], r["last_name"], r["class_name"], r["academic_year"],
                    STATUS_LABELS[r["status"]], r["applied_on"], r["date_of_birth"], r["gender"], r["phone"],
                    r["email"], r["previous_school"], matric))
    return csv_response("applications.csv", header, out)


# --------------------------------------------------------------------------
# Create / edit
# --------------------------------------------------------------------------
def parse_application_form(class_ids):
    errors = []
    data = {
        "first_name": clean("first_name", 80),
        "last_name": clean("last_name", 80),
        "date_of_birth": None,
        "gender": clean("gender") if clean("gender") in GENDERS else None,
        "nationality": clean("nationality", 60) or None,
        "state_of_origin": clean("state_of_origin", 60) or None,
        "home_address": clean("home_address", 300) or None,
        "phone": clean("phone", 30) or None,
        "email": clean("email", 120).lower() or None,
        "previous_school": clean("previous_school", 150) or None,
        "national_id": clean("national_id", 40) or None,
        "class_id": request.form.get("class_id", type=int),
        "academic_year": clean("academic_year", 9),
        "notes": clean("notes", 1000) or None,
    }
    if not data["first_name"] or not data["last_name"]:
        errors.append("First name and last name are required.")
    raw_dob = clean("date_of_birth")
    if raw_dob:
        try:
            dob = date.fromisoformat(raw_dob)
            if dob > date.today():
                errors.append("Date of birth can't be in the future.")
            else:
                data["date_of_birth"] = dob.isoformat()
        except ValueError:
            errors.append("Date of birth is not a valid date.")
    if data["email"] and ("@" not in data["email"] or "." not in data["email"]):
        errors.append("Enter a valid email address or leave it blank.")
    if not re.fullmatch(r"\d{4}/\d{4}", data["academic_year"] or ""):
        errors.append("Academic year should look like 2026/2027.")
    if data["class_id"] not in class_ids:
        data["class_id"] = None
    return data, errors


def parse_guardian_form(prefix=""):
    g_ = {
        "full_name": clean(prefix + "name", 120),
        "relationship": clean(prefix + "relationship", 40),
        "phone": clean(prefix + "phone", 30) or None,
        "email": clean(prefix + "email", 120).lower() or None,
    }
    errors = []
    if g_["full_name"]:
        if g_["relationship"] not in RELATIONSHIPS:
            errors.append("Choose the guardian's relationship.")
        if not g_["phone"] and not g_["email"]:
            errors.append("Give the guardian's phone number or email.")
        if g_["email"] and ("@" not in g_["email"] or "." not in g_["email"]):
            errors.append("Enter a valid guardian email address or leave it blank.")
    return g_, errors


FIELDS = ("first_name", "last_name", "date_of_birth", "gender", "nationality", "state_of_origin", "home_address",
          "phone", "email", "previous_school", "national_id", "class_id", "academic_year", "notes")


def create_application(data, guardian):
    db = get_db()
    year = date.today().year
    prefix = f"APP/{year}/"
    for _ in range(3):
        number = f"{prefix}{next_number(db, 'applications', 'application_no', prefix):04d}"
        try:
            cur = db.execute(
                f"INSERT INTO applications (application_no, {', '.join(FIELDS)}) "
                f"VALUES (?, {', '.join('?' * len(FIELDS))})", (number, *[data[f] for f in FIELDS]))
            aid = cur.lastrowid
            if guardian["full_name"]:
                db.execute(
                    "INSERT INTO application_guardians (application_id, full_name, relationship, phone, email, "
                    "is_primary, is_emergency) VALUES (?,?,?,?,?,1,1)",
                    (aid, guardian["full_name"], guardian["relationship"], guardian["phone"], guardian["email"]))
            db.commit()
            return aid
        except sqlite3.IntegrityError:
            db.rollback()
    return None


@bp.route("/admissions/new", methods=["GET", "POST"])
@admin_required
def application_new():
    classes = query("SELECT id, name FROM classes ORDER BY name")
    form = {"academic_year": default_academic_year(), "nationality": "Nigerian", "guardian_relationship": "Father"}
    if request.method == "POST":
        data, errors = parse_application_form([c["id"] for c in classes])
        guardian, g_errors = parse_guardian_form("guardian_")
        errors += g_errors
        form = dict(data, **{"guardian_" + k: v for k, v in guardian.items()})
        form["date_of_birth"] = clean("date_of_birth")
        if not errors:
            aid = create_application(data, guardian)
            if aid:
                flash("Application recorded.", "success")
                return redirect(url_for("admissions.application_detail", aid=aid))
            errors.append("Couldn't generate an application number. Please try again.")
        for e in errors:
            flash(e, "error")
    return render_template("admissions/form.html", form=form, classes=classes, aid=None)


@bp.route("/admissions/<int:aid>/edit", methods=["GET", "POST"])
@admin_required
def application_edit(aid):
    row = get_application_or_404(aid)
    if row["status"] == "enrolled":
        flash("This applicant is already enrolled. Edit the student's record instead.", "error")
        return redirect(url_for("admissions.application_detail", aid=aid))
    classes = query("SELECT id, name FROM classes ORDER BY name")
    form = dict(row)
    if request.method == "POST":
        data, errors = parse_application_form([c["id"] for c in classes])
        form = dict(data)
        form["date_of_birth"] = clean("date_of_birth")
        if not errors:
            execute(f"UPDATE applications SET {', '.join(f + '=?' for f in FIELDS)} WHERE id=?",
                    (*[data[f] for f in FIELDS], aid))
            flash("Application updated.", "success")
            return redirect(url_for("admissions.application_detail", aid=aid))
        for e in errors:
            flash(e, "error")
    return render_template("admissions/form.html", form=form, classes=classes, aid=aid, application=row)


@bp.route("/admissions/<int:aid>/delete", methods=["POST"])
@admin_required
def application_delete(aid):
    row = get_application_or_404(aid)
    if row["status"] == "enrolled":
        flash("An enrolled applicant's record can't be deleted. It's the admission record of a student.", "error")
        return redirect(url_for("admissions.application_detail", aid=aid))
    execute("DELETE FROM applications WHERE id=?", (aid,))
    flash("Application deleted.", "success")
    return redirect(url_for("admissions.applications"))


# --------------------------------------------------------------------------
# One application: details, guardians, status changes, enrolment
# --------------------------------------------------------------------------
@bp.route("/admissions/<int:aid>")
@admin_required
def application_detail(aid):
    row = get_application_or_404(aid)
    guardians = query(
        "SELECT * FROM application_guardians WHERE application_id=? ORDER BY is_primary DESC, id", (aid,))
    classes = query("SELECT id, name FROM classes ORDER BY name")
    student_url = safe_url("students.student_detail", sid=row["student_id"]) if row["student_id"] else ""
    return render_template("admissions/detail.html", a=row, guardians=guardians, classes=classes,
                           next_statuses=NEXT_STATUSES[row["status"]], student_url=student_url)


@bp.route("/admissions/<int:aid>/status", methods=["POST"])
@admin_required
def application_status(aid):
    row = get_application_or_404(aid)
    new = request.form.get("status", "")
    if new not in NEXT_STATUSES[row["status"]]:
        flash(f"An application that is \"{STATUS_LABELS[row['status']]}\" can't be moved to that status.", "error")
    else:
        decided = date.today().isoformat() if new in ("offered", "accepted", "rejected") else None
        execute("UPDATE applications SET status=?, decided_on=COALESCE(?, decided_on) WHERE id=?",
                (new, decided, aid))
        flash(f"Status changed to \"{STATUS_LABELS[new]}\".", "success")
    return redirect(url_for("admissions.application_detail", aid=aid))


@bp.route("/admissions/<int:aid>/guardians", methods=["POST"])
@admin_required
def guardian_add(aid):
    row = get_application_or_404(aid)
    guardian, errors = parse_guardian_form("")
    if not guardian["full_name"]:
        errors.append("Enter the guardian's name.")
    if errors:
        for e in errors:
            flash(e, "error")
    else:
        db = get_db()
        has_primary = db.execute("SELECT 1 FROM application_guardians WHERE application_id=? AND is_primary=1",
                                 (aid,)).fetchone()
        db.execute(
            "INSERT INTO application_guardians (application_id, full_name, relationship, phone, email, "
            "is_primary, is_emergency) VALUES (?,?,?,?,?,?,?)",
            (aid, guardian["full_name"], guardian["relationship"], guardian["phone"], guardian["email"],
             0 if has_primary else 1, 1 if request.form.get("is_emergency") else 0))
        db.commit()
        flash("Guardian added.", "success")
    return redirect(url_for("admissions.application_detail", aid=row["id"]))


@bp.route("/admissions/<int:aid>/guardians/<int:gid>/delete", methods=["POST"])
@admin_required
def guardian_delete(aid, gid):
    get_application_or_404(aid)
    execute("DELETE FROM application_guardians WHERE id=? AND application_id=?", (gid, aid))
    flash("Guardian removed.", "success")
    return redirect(url_for("admissions.application_detail", aid=aid))


@bp.route("/admissions/<int:aid>/enrol", methods=["POST"])
@admin_required
def application_enrol(aid):
    """Turn an accepted applicant into a student with a generated matric number."""
    row = get_application_or_404(aid)
    back = redirect(url_for("admissions.application_detail", aid=aid))
    if row["status"] != "accepted":
        flash("Only applicants who have accepted an offer can be enrolled.", "error")
        return back
    class_id = request.form.get("class_id", type=int) or row["class_id"]
    if not class_id or not query("SELECT 1 FROM classes WHERE id=?", (class_id,), one=True):
        flash("Choose the class to enrol this student into.", "error")
        return back

    db = get_db()
    prefix = f"{current_app.config['SCHOOL_CODE']}/{date.today().year}/"
    student_id = matric = None
    for _ in range(3):
        matric = f"{prefix}{next_number(db, 'students', 'matric_no', prefix):03d}"
        try:
            cur = db.execute(
                "INSERT INTO students (name, matric_no, email, class_id) VALUES (?,?,?,?)",
                (f"{row['first_name']} {row['last_name']}", matric, row["email"], class_id))
            student_id = cur.lastrowid
            db.execute(
                "UPDATE applications SET status='enrolled', student_id=?, class_id=?, enrolled_on=date('now') "
                "WHERE id=?", (student_id, class_id, aid))
            db.commit()
            break
        except sqlite3.IntegrityError:
            db.rollback()
            student_id = None
    if not student_id:
        flash("Couldn't create the student record. Please try again.", "error")
        return back

    # The student now exists. Copying details into the Records module is best-effort:
    # if that module has a problem, the enrolment still stands.
    missing = []
    try:
        try:
            db.execute(
                "INSERT INTO student_profiles (student_id, date_of_birth, gender, nationality, state_of_origin, "
                "home_address, phone, national_id, admission_date) VALUES (?,?,?,?,?,?,?,?, date('now'))",
                (student_id, row["date_of_birth"], row["gender"], row["nationality"], row["state_of_origin"],
                 row["home_address"], row["phone"], row["national_id"]))
        except sqlite3.IntegrityError:
            db.rollback()
            db.execute(
                "INSERT INTO student_profiles (student_id, date_of_birth, gender, nationality, state_of_origin, "
                "home_address, phone, national_id, admission_date) VALUES (?,?,?,?,?,?,?,NULL, date('now'))",
                (student_id, row["date_of_birth"], row["gender"], row["nationality"], row["state_of_origin"],
                 row["home_address"], row["phone"]))
            missing.append("the national ID (it is already recorded for another student)")
        db.commit()
    except sqlite3.Error:
        db.rollback()
        current_app.logger.exception("Could not copy personal details to the Records module")
        missing.append("personal details")
    try:
        db.execute(
            "INSERT INTO family_contacts (student_id, full_name, relationship, phone, email, address, "
            "is_primary, is_emergency) SELECT ?, full_name, relationship, phone, email, address, is_primary, "
            "is_emergency FROM application_guardians WHERE application_id=?", (student_id, aid))
        db.commit()
    except sqlite3.Error:
        db.rollback()
        current_app.logger.exception("Could not copy guardians to the Records module")
        missing.append("family contacts")

    if missing:
        flash(f"Enrolled as {matric}, but these could not be copied automatically: {', '.join(missing)}. "
              "Please add them on the student's page.", "error")
    else:
        flash(f"Enrolled. The new matric number is {matric}.", "success")
    return redirect(url_for("admissions.application_detail", aid=aid))
