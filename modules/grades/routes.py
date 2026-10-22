from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from core.csvutil import csv_response, slug
from core.db import get_db, query
from core.security import login_required, my_classes, pick_class

from .seed import DEFAULT_SUBJECTS

bp = Blueprint("grades", __name__, template_folder="templates")

TERMS = ("Term 1", "Term 2", "Term 3")


@bp.route("/grades", methods=["GET", "POST"])
@login_required
def grades():
    classes = my_classes()
    class_id = pick_class(classes)
    subject = request.values.get("subject", "").strip()
    term = request.values.get("term", TERMS[0])
    if term not in TERMS:
        term = TERMS[0]

    roster = []
    if class_id:
        roster = query("SELECT id, name, matric_no FROM students WHERE class_id=? ORDER BY name", (class_id,))

    if request.method == "POST":
        if not subject:
            flash("Enter a subject before saving scores.", "error")
        else:
            db, bad = get_db(), []
            for s in roster:
                raw = request.form.get(f"score_{s['id']}", "").strip()
                if raw == "":
                    db.execute("DELETE FROM grades WHERE student_id=? AND subject=? AND term=?",
                               (s["id"], subject, term))
                    continue
                try:
                    score = float(raw)
                    if not 0 <= score <= 100:
                        raise ValueError
                except ValueError:
                    bad.append(s["name"])
                    continue
                db.execute(
                    "INSERT INTO grades (student_id, subject, term, score) VALUES (?,?,?,?) "
                    "ON CONFLICT(student_id, subject, term) DO UPDATE SET score=excluded.score",
                    (s["id"], subject, term, score))
            db.commit()
            if bad:
                flash("Scores must be between 0 and 100. Skipped: " + ", ".join(bad), "error")
            else:
                flash(f"{subject} ({term}) scores saved.", "success")
        return redirect(url_for("grades.grades", class_id=class_id, subject=subject, term=term))

    scores = {}
    if subject and class_id:
        scores = {r["student_id"]: r["score"] for r in query(
            "SELECT student_id, score FROM grades WHERE subject=? AND term=? AND student_id IN "
            "(SELECT id FROM students WHERE class_id=?)", (subject, term, class_id))}
    rows = [{"id": s["id"], "name": s["name"], "matric_no": s["matric_no"], "score": scores.get(s["id"])}
            for s in roster]
    known = [r["subject"] for r in query("SELECT DISTINCT subject FROM grades ORDER BY subject")]
    subjects = sorted(set(known) | set(DEFAULT_SUBJECTS))
    return render_template("grades/grades.html", classes=classes, class_id=class_id, subject=subject,
                           term=term, terms=TERMS, subjects=subjects, rows=rows)


@bp.route("/grades/export.csv")
@login_required
def grades_export():
    class_id = pick_class(my_classes())
    if not class_id:
        abort(404)
    cname = query("SELECT name FROM classes WHERE id=?", (class_id,), one=True)["name"]
    where, args = ["s.class_id=?"], [class_id]
    term = request.args.get("term", "")
    subject = request.args.get("subject", "").strip()
    if term in TERMS:
        where.append("g.term=?")
        args.append(term)
    if subject:
        where.append("g.subject=?")
        args.append(subject)
    rows = query(
        "SELECT s.matric_no, s.name, g.subject, g.term, g.score FROM grades g "
        f"JOIN students s ON s.id = g.student_id WHERE {' AND '.join(where)} "
        "ORDER BY g.term, g.subject, s.name", args)
    return csv_response(f"grades-{slug(cname)}.csv", ["Matric No", "Name", "Subject", "Term", "Score"],
                        [(r["matric_no"], r["name"], r["subject"], r["term"], '%g' % r["score"]) for r in rows])
