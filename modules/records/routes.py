import sqlite3
from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from core.csvutil import csv_response
from core.db import execute, get_db, placeholders, query
from core.security import get_student_or_404, login_required, my_class_ids

bp = Blueprint("records", __name__, template_folder="templates")

GENDERS = ("male", "female", "other")
RELATIONSHIPS = ("Father", "Mother", "Guardian", "Grandparent", "Sibling", "Uncle/Aunt", "Other")


def clean(name, limit=200):
    return request.form.get(name, "").strip()[:limit]


def parse_date(raw, label, errors, allow_future=False):
    if not raw:
        return None
    try:
        d = date.fromisoformat(raw)
    except ValueError:
        errors.append(f"{label} is not a valid date.")
        return None
    if d > date.today() and not allow_future:
        errors.append(f"{label} can't be in the future.")
        return None
    return d.isoformat()


@bp.context_processor
def helpers():
    return {"GENDERS": GENDERS, "RELATIONSHIPS": RELATIONSHIPS}


# --------------------------------------------------------------------------
# Personal details
# --------------------------------------------------------------------------
@bp.route("/students/<int:sid>/profile", methods=["GET", "POST"])
@login_required
def profile_edit(sid):
    student = get_student_or_404(sid)
    existing = query("SELECT * FROM student_profiles WHERE student_id=?", (sid,), one=True)
    form = dict(existing) if existing else {"nationality": "Nigerian"}
    if request.method == "POST":
        errors = []
        form = {
            "date_of_birth": parse_date(clean("date_of_birth"), "Date of birth", errors),
            "gender": clean("gender") if clean("gender") in GENDERS else None,
            "nationality": clean("nationality", 60) or None,
            "state_of_origin": clean("state_of_origin", 60) or None,
            "home_address": clean("home_address", 300) or None,
            "phone": clean("phone", 30) or None,
            "national_id": clean("national_id", 40) or None,
            "admission_date": parse_date(clean("admission_date"), "Admission date", errors),
        }
        if not errors:
            try:
                execute(
                    "INSERT INTO student_profiles (student_id, date_of_birth, gender, nationality, state_of_origin, "
                    "home_address, phone, national_id, admission_date) VALUES (?,?,?,?,?,?,?,?,?) "
                    "ON CONFLICT(student_id) DO UPDATE SET date_of_birth=excluded.date_of_birth, "
                    "gender=excluded.gender, nationality=excluded.nationality, "
                    "state_of_origin=excluded.state_of_origin, home_address=excluded.home_address, "
                    "phone=excluded.phone, national_id=excluded.national_id, "
                    "admission_date=excluded.admission_date, updated_at=datetime('now')",
                    (sid, form["date_of_birth"], form["gender"], form["nationality"], form["state_of_origin"],
                     form["home_address"], form["phone"], form["national_id"], form["admission_date"]))
                flash("Personal details saved.", "success")
                return redirect(url_for("students.student_detail", sid=sid))
            except sqlite3.IntegrityError:
                errors.append("That national ID number is already recorded for another student.")
        for e in errors:
            flash(e, "error")
    return render_template("records/profile_form.html", student=student, form=form)


# --------------------------------------------------------------------------
# Family contacts
# --------------------------------------------------------------------------
def get_contact_or_404(sid, cid):
    contact = query("SELECT * FROM family_contacts WHERE id=? AND student_id=?", (cid, sid), one=True)
    if contact is None:
        abort(404)
    return contact


@bp.route("/students/<int:sid>/contacts/new", defaults={"cid": None}, methods=["GET", "POST"])
@bp.route("/students/<int:sid>/contacts/<int:cid>/edit", methods=["GET", "POST"])
@login_required
def contact_form(sid, cid):
    student = get_student_or_404(sid)
    contact = get_contact_or_404(sid, cid) if cid else None
    form = dict(contact) if contact else {"relationship": "Father", "is_primary": 0, "is_emergency": 0}
    if request.method == "POST":
        form = {
            "full_name": clean("full_name", 120),
            "relationship": clean("relationship", 40),
            "phone": clean("phone", 30) or None,
            "email": clean("email", 120).lower() or None,
            "address": clean("address", 300) or None,
            "is_primary": 1 if request.form.get("is_primary") else 0,
            "is_emergency": 1 if request.form.get("is_emergency") else 0,
        }
        errors = []
        if not form["full_name"]:
            errors.append("Name is required.")
        if form["relationship"] not in RELATIONSHIPS:
            errors.append("Choose a relationship.")
        if not form["phone"] and not form["email"]:
            errors.append("Give at least a phone number or an email address.")
        if form["email"] and ("@" not in form["email"] or "." not in form["email"]):
            errors.append("Enter a valid email address or leave it blank.")
        if not errors:
            db = get_db()
            if contact:
                db.execute(
                    "UPDATE family_contacts SET full_name=?, relationship=?, phone=?, email=?, address=?, "
                    "is_primary=?, is_emergency=? WHERE id=?",
                    (form["full_name"], form["relationship"], form["phone"], form["email"], form["address"],
                     form["is_primary"], form["is_emergency"], cid))
                new_id = cid
            else:
                has_any = db.execute("SELECT 1 FROM family_contacts WHERE student_id=?", (sid,)).fetchone()
                if not has_any:
                    form["is_primary"] = 1  # the first contact is the primary one
                cur = db.execute(
                    "INSERT INTO family_contacts (student_id, full_name, relationship, phone, email, address, "
                    "is_primary, is_emergency) VALUES (?,?,?,?,?,?,?,?)",
                    (sid, form["full_name"], form["relationship"], form["phone"], form["email"],
                     form["address"], form["is_primary"], form["is_emergency"]))
                new_id = cur.lastrowid
            if form["is_primary"]:
                db.execute("UPDATE family_contacts SET is_primary=0 WHERE student_id=? AND id!=?", (sid, new_id))
            db.commit()
            flash("Contact saved.", "success")
            return redirect(url_for("students.student_detail", sid=sid))
        for e in errors:
            flash(e, "error")
    return render_template("records/contact_form.html", student=student, form=form, cid=cid)


@bp.route("/students/<int:sid>/contacts/<int:cid>/delete", methods=["POST"])
@login_required
def contact_delete(sid, cid):
    get_student_or_404(sid)
    get_contact_or_404(sid, cid)
    execute("DELETE FROM family_contacts WHERE id=?", (cid,))
    flash("Contact removed.", "success")
    return redirect(url_for("students.student_detail", sid=sid))


# --------------------------------------------------------------------------
# Student register export (identifiers, personal details and the main guardian)
# --------------------------------------------------------------------------
@bp.route("/records/export.csv")
@login_required
def register_export():
    ids = my_class_ids()
    rows = []
    if ids:
        rows = query(
            "SELECT s.matric_no, s.name, c.name AS class_name, p.date_of_birth, p.gender, p.nationality, "
            "p.state_of_origin, p.phone, p.home_address, p.national_id, p.admission_date, "
            "(SELECT full_name FROM family_contacts f WHERE f.student_id=s.id ORDER BY is_primary DESC, id LIMIT 1) AS g_name, "
            "(SELECT relationship FROM family_contacts f WHERE f.student_id=s.id ORDER BY is_primary DESC, id LIMIT 1) AS g_rel, "
            "(SELECT phone FROM family_contacts f WHERE f.student_id=s.id ORDER BY is_primary DESC, id LIMIT 1) AS g_phone, "
            "(SELECT email FROM family_contacts f WHERE f.student_id=s.id ORDER BY is_primary DESC, id LIMIT 1) AS g_email "
            "FROM students s JOIN classes c ON c.id = s.class_id "
            "LEFT JOIN student_profiles p ON p.student_id = s.id "
            f"WHERE s.class_id IN ({placeholders(len(ids))}) ORDER BY c.name, s.name", ids)
    header = ["Matric No", "Name", "Class", "Date of Birth", "Gender", "Nationality", "State of Origin",
              "Phone", "Home Address", "National ID", "Admission Date",
              "Main Contact", "Relationship", "Contact Phone", "Contact Email"]
    return csv_response("student-register.csv", header, [tuple(r) for r in rows])
