import random

DEFAULT_SUBJECTS = ("Mathematics", "English", "Science")


def seed(db, config):
    rnd = random.Random(13)
    for (sid,) in db.execute("SELECT id FROM students ORDER BY id").fetchall():
        for subject in DEFAULT_SUBJECTS:
            score = max(35, min(98, round(rnd.gauss(68, 14))))
            db.execute("INSERT INTO grades (student_id, subject, term, score) VALUES (?,?,?,?)",
                       (sid, subject, "Term 1", score))
