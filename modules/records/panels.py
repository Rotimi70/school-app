"""Sections this module adds to the student page."""
from datetime import date

from flask import render_template
from markupsafe import Markup

from core.db import query


def _age(dob):
    try:
        born = date.fromisoformat(dob)
    except (TypeError, ValueError):
        return None
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def personal_details_panel(student):
    profile = query("SELECT * FROM student_profiles WHERE student_id=?", (student["id"],), one=True)
    age = _age(profile["date_of_birth"]) if profile else None
    return Markup(render_template("records/panel_profile.html", student=student, profile=profile, age=age))


personal_details_panel.title = "Personal details"


def family_contacts_panel(student):
    contacts = query(
        "SELECT * FROM family_contacts WHERE student_id=? ORDER BY is_primary DESC, id", (student["id"],))
    return Markup(render_template("records/panel_contacts.html", student=student, contacts=contacts))


family_contacts_panel.title = "Family contacts"
