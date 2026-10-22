import random
from datetime import date, timedelta

STATUSES = ("present", "late", "absent")


def seed(db, config):
    rnd = random.Random(11)
    days, d = [], date.today()
    while len(days) < 10:
        if d.weekday() < 5:
            days.append(d)
        d -= timedelta(days=1)
    for (sid,) in db.execute("SELECT id FROM students ORDER BY id").fetchall():
        for day in days:
            status = rnd.choices(STATUSES, [85, 7, 8])[0]
            db.execute("INSERT INTO attendance (student_id, date, status) VALUES (?,?,?)",
                       (sid, day.isoformat(), status))
