from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from core.csvutil import csv_response, slug
from core.db import get_db, query
from core.security import login_required, my_classes, pick_class

bp = Blueprint("attendance", __name__, template_folder="templates")

STATUSES = ("present", "late", "absent")


@bp.route("/attendance", methods=["GET", "POST"])
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
        return redirect(url_for("attendance.attendance", class_id=class_id, date=day.isoformat()))

    marked = {r["student_id"]: r["status"] for r in query(
        "SELECT student_id, status FROM attendance WHERE date=? AND student_id IN "
        "(SELECT id FROM students WHERE class_id=?)", (day.isoformat(), class_id))}
    rows = [{"id": s["id"], "name": s["name"], "matric_no": s["matric_no"], "status": marked.get(s["id"])}
            for s in roster]
    return render_template("attendance/attendance.html", classes=classes, class_id=class_id, day=day.isoformat(),
                           today=date.today().isoformat(), rows=rows)


@bp.route("/attendance/export.csv")
@login_required
def attendance_export():
    class_id = pick_class(my_classes())
    if not class_id:
        abort(404)
    cname = query("SELECT name FROM classes WHERE id=?", (class_id,), one=True)["name"]
    rows = query(
        "SELECT s.matric_no, s.name, a.date, a.status FROM attendance a "
        "JOIN students s ON s.id = a.student_id WHERE s.class_id=? ORDER BY a.date, s.name", (class_id,))
    return csv_response(f"attendance-{slug(cname)}.csv", ["Matric No", "Name", "Date", "Status"],
                        [tuple(r) for r in rows])
