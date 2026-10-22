"""Chart on the student page: this student's score per subject next to the class average."""
from flask import render_template
from markupsafe import Markup

from core.db import query


def grade_chart_panel(student):
    rows = query(
        "SELECT g.subject, "
        "  AVG(CASE WHEN g.student_id=? THEN g.score END) AS mine, "
        "  AVG(g.score) AS class_avg "
        "FROM grades g JOIN students s ON s.id=g.student_id "
        "WHERE s.class_id=? AND g.subject IN (SELECT subject FROM grades WHERE student_id=?) "
        "GROUP BY g.subject ORDER BY g.subject",
        (student["id"], student["class_id"], student["id"]))
    bars = [{"subject": r["subject"], "mine": round(r["mine"], 1), "avg": round(r["class_avg"], 1)}
            for r in rows if r["mine"] is not None]
    return Markup(render_template("grades/panel_chart.html", bars=bars))


grade_chart_panel.title = "Grades compared with class average"
grade_chart_panel.portal = True  # also shown on the student's own page
