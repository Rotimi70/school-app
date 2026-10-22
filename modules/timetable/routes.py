import re

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from core.db import execute, query
from core.security import admin_required, any_login_required, is_admin, my_classes

bp = Blueprint("timetable", __name__, template_folder="templates")

DAYS = {1: "Monday", 2: "Tuesday", 3: "Wednesday", 4: "Thursday", 5: "Friday"}
TIME_RE = re.compile(r"([01]\d|2[0-3]):[0-5]\d")


@bp.context_processor
def helpers():
    return {"DAYS": DAYS}


def build_grid(slots):
    """Rows of (start, end) with the lessons for each weekday."""
    times = sorted({(s["start_time"], s["end_time"]) for s in slots})
    return [{
        "start": start, "end": end,
        "cells": {d: [s for s in slots if s["weekday"] == d and s["start_time"] == start and s["end_time"] == end]
                  for d in DAYS},
    } for start, end in times]


def visible_classes():
    """Admins see every class, teachers their own, students only their own class."""
    if g.user["role"] == "student":
        row = query("SELECT c.id, c.name FROM students s JOIN classes c ON c.id=s.class_id WHERE s.id=?",
                    (g.user["student_id"],), one=True)
        return [row] if row else []
    if is_admin():
        return query("SELECT id, name FROM classes ORDER BY name")
    return my_classes()


@bp.route("/timetable")
@any_login_required
def timetable():
    classes = visible_classes()
    ids = [c["id"] for c in classes]
    class_id = request.args.get("class_id", type=int)
    if class_id is not None and class_id not in ids:
        abort(403, "That class timetable isn't available to you.")
    class_id = class_id or (ids[0] if ids else None)
    slots = []
    if class_id:
        slots = query(
            "SELECT s.*, u.name AS teacher_name FROM schedule_slots s LEFT JOIN users u ON u.id=s.teacher_id "
            "WHERE s.class_id=? ORDER BY s.start_time, s.weekday", (class_id,))
    return render_template("timetable/timetable.html", classes=classes, class_id=class_id,
                           grid=build_grid(slots), count=len(slots))


# --------------------------------------------------------------------------
# Editing (admins only)
# --------------------------------------------------------------------------
def find_conflicts(class_id, weekday, start, end, teacher_id, exclude_id=None):
    """Lessons that overlap this one in the same class, or with the same teacher elsewhere."""
    rows = query(
        "SELECT s.*, c.name AS class_name FROM schedule_slots s JOIN classes c ON c.id=s.class_id "
        "WHERE s.weekday=? AND s.start_time < ? AND ? < s.end_time AND s.id != ?",
        (weekday, end, start, exclude_id or -1))
    messages = []
    for r in rows:
        when = f"{r['start_time']}–{r['end_time']}"
        if r["class_id"] == class_id:
            messages.append(f"{r['class_name']} already has {r['subject']} at {when} that day.")
        elif teacher_id and r["teacher_id"] == teacher_id:
            messages.append(f"That teacher is already teaching {r['class_name']} ({r['subject']}) at {when}.")
    return messages


def parse_slot_form(class_ids, teacher_ids, exclude_id=None):
    form = {
        "class_id": request.form.get("class_id", type=int),
        "weekday": request.form.get("weekday", type=int),
        "start_time": request.form.get("start_time", "").strip(),
        "end_time": request.form.get("end_time", "").strip(),
        "subject": request.form.get("subject", "").strip()[:80],
        "teacher_id": request.form.get("teacher_id", type=int),
        "room": request.form.get("room", "").strip()[:40] or None,
    }
    errors = []
    if form["class_id"] not in class_ids:
        errors.append("Choose a class.")
    if form["weekday"] not in DAYS:
        errors.append("Choose a day, Monday to Friday.")
    if not (TIME_RE.fullmatch(form["start_time"]) and TIME_RE.fullmatch(form["end_time"])):
        errors.append("Enter the start and end times.")
    elif form["start_time"] >= form["end_time"]:
        errors.append("The lesson must end after it starts.")
    if not form["subject"]:
        errors.append("Enter the subject.")
    if form["teacher_id"] not in teacher_ids:
        form["teacher_id"] = None
    if not errors:
        errors += find_conflicts(form["class_id"], form["weekday"], form["start_time"], form["end_time"],
                                 form["teacher_id"], exclude_id)
    return form, errors


@bp.route("/timetable/slots/new", defaults={"slot_id": None}, methods=["GET", "POST"])
@bp.route("/timetable/slots/<int:slot_id>/edit", methods=["GET", "POST"])
@admin_required
def slot_form(slot_id):
    slot = None
    if slot_id:
        slot = query("SELECT * FROM schedule_slots WHERE id=?", (slot_id,), one=True)
        if slot is None:
            abort(404)
    classes = query("SELECT id, name FROM classes ORDER BY name")
    teachers = query("SELECT id, name FROM users WHERE role='teacher' ORDER BY name")
    form = dict(slot) if slot else {"class_id": request.args.get("class_id", type=int), "weekday": 1}
    if request.method == "POST":
        form, errors = parse_slot_form([c["id"] for c in classes], [t["id"] for t in teachers], slot_id)
        if not errors:
            values = (form["class_id"], form["weekday"], form["start_time"], form["end_time"], form["subject"],
                      form["teacher_id"], form["room"])
            if slot:
                execute("UPDATE schedule_slots SET class_id=?, weekday=?, start_time=?, end_time=?, subject=?, "
                        "teacher_id=?, room=? WHERE id=?", (*values, slot_id))
                flash("Lesson updated.", "success")
            else:
                execute("INSERT INTO schedule_slots (class_id, weekday, start_time, end_time, subject, teacher_id, "
                        "room) VALUES (?,?,?,?,?,?,?)", values)
                flash("Lesson added.", "success")
            return redirect(url_for("timetable.timetable", class_id=form["class_id"]))
        for e in errors:
            flash(e, "error")
    return render_template("timetable/slot_form.html", form=form, classes=classes, teachers=teachers,
                           slot_id=slot_id)


@bp.route("/timetable/slots/<int:slot_id>/delete", methods=["POST"])
@admin_required
def slot_delete(slot_id):
    slot = query("SELECT * FROM schedule_slots WHERE id=?", (slot_id,), one=True)
    if slot is None:
        abort(404)
    execute("DELETE FROM schedule_slots WHERE id=?", (slot_id,))
    flash("Lesson removed.", "success")
    return redirect(url_for("timetable.timetable", class_id=slot["class_id"]))
