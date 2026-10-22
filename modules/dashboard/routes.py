from datetime import date, timedelta

from flask import Blueprint, current_app, render_template

from core.db import placeholders, query
from core.panels import collect_dashboard_cards
from core.security import login_required, my_class_ids

bp = Blueprint("dashboard", __name__, template_folder="templates")


def _safe(fn, default):
    """Run one dashboard widget; if its data is unavailable, show a dash instead of failing."""
    try:
        return fn()
    except Exception:
        current_app.logger.exception("Dashboard widget failed")
        return default


@bp.route("/dashboard")
@login_required
def dashboard():
    ids = my_class_ids() or [-1]
    ph = placeholders(len(ids))
    since = (date.today() - timedelta(days=30)).isoformat()

    total_students = _safe(lambda: query(
        f"SELECT COUNT(*) AS n FROM students WHERE class_id IN ({ph})", ids, one=True)["n"], 0)

    def attendance_rate():
        att = query(
            f"SELECT COUNT(*) AS total, COALESCE(SUM(a.status IN ('present','late')),0) AS ok "
            f"FROM attendance a JOIN students s ON s.id=a.student_id "
            f"WHERE s.class_id IN ({ph}) AND a.date >= ?", ids + [since], one=True)
        return round(100 * att["ok"] / att["total"], 1) if att["total"] else None

    def average_grade():
        return query(
            f"SELECT ROUND(AVG(g.score),1) AS avg FROM grades g JOIN students s ON s.id=g.student_id "
            f"WHERE s.class_id IN ({ph})", ids, one=True)["avg"]

    def attendance_trend():
        rows = query(
            f"SELECT a.date, ROUND(100.0*SUM(a.status IN ('present','late'))/COUNT(*)) AS rate "
            f"FROM attendance a JOIN students s ON s.id=a.student_id "
            f"WHERE s.class_id IN ({ph}) AND a.date >= ? GROUP BY a.date ORDER BY a.date",
            ids + [(date.today() - timedelta(days=21)).isoformat()])
        return [{"label": date.fromisoformat(r["date"]).strftime("%a %d"), "rate": int(r["rate"])}
                for r in rows][-7:]

    def classes_full():
        return query(
            f"""SELECT c.id, c.name, u.name AS teacher,
                  (SELECT COUNT(*) FROM students s WHERE s.class_id=c.id) AS n_students,
                  (SELECT ROUND(100.0*SUM(a.status IN ('present','late'))/COUNT(*),1)
                     FROM attendance a JOIN students s ON s.id=a.student_id
                     WHERE s.class_id=c.id AND a.date >= ?) AS att_rate,
                  (SELECT ROUND(AVG(g.score),1) FROM grades g JOIN students s ON s.id=g.student_id
                     WHERE s.class_id=c.id) AS avg_grade
                FROM classes c LEFT JOIN users u ON u.id=c.teacher_id
                WHERE c.id IN ({ph}) ORDER BY c.name""", [since] + ids)

    def classes_basic():
        return query(
            f"""SELECT c.id, c.name, u.name AS teacher,
                  (SELECT COUNT(*) FROM students s WHERE s.class_id=c.id) AS n_students,
                  NULL AS att_rate, NULL AS avg_grade
                FROM classes c LEFT JOIN users u ON u.id=c.teacher_id
                WHERE c.id IN ({ph}) ORDER BY c.name""", ids)

    per_class = _safe(classes_full, None)
    if per_class is None:
        per_class = _safe(classes_basic, [])

    stats = {
        "students": total_students,
        "classes": len(per_class),
        "teachers": _safe(lambda: query("SELECT COUNT(*) AS n FROM users WHERE role='teacher'", one=True)["n"], 0),
        "att_rate": _safe(attendance_rate, None),
        "avg_grade": _safe(average_grade, None),
    }
    return render_template("dashboard/dashboard.html", stats=stats, trend=_safe(attendance_trend, []),
                           per_class=per_class, extra_cards=collect_dashboard_cards())
