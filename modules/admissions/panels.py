from flask import g, render_template
from markupsafe import Markup

from core.db import query

OPEN_STATUSES_SQL = "('applied','review','offered','accepted')"


def admission_panel(student):
    """Shows how this student was admitted (admins only, and only if they came through Admissions)."""
    if g.user["role"] != "admin":
        return None
    row = query("SELECT * FROM applications WHERE student_id=?", (student["id"],), one=True)
    if row is None:
        return None
    return Markup(render_template("admissions/panel_admission.html", row=row))


admission_panel.title = "Admission record"


def open_applications_card():
    if g.user["role"] != "admin":
        return None
    n = query(f"SELECT COUNT(*) AS n FROM applications WHERE status IN {OPEN_STATUSES_SQL}", one=True)["n"]
    return {"label": "Open applications", "value": n, "icon": "clipboard", "tone": "sky"}
