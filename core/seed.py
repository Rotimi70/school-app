"""Demo data for the core tables (staff, classes, students). Runs only on an empty database."""
import random

from werkzeug.security import generate_password_hash


def seed_core(db):
    rnd = random.Random(7)
    db.execute(
        "INSERT INTO users (name, email, password_hash, role) VALUES (?,?,?,?)",
        ("Admin User", "admin@school.test", generate_password_hash("admin123"), "admin"),
    )
    teacher_hash = generate_password_hash("teacher123")
    for name, email in (("Mrs. Adeyemi", "teacher1@school.test"),
                        ("Mr. Bello", "teacher2@school.test")):
        db.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?,?,?,'teacher')",
            (name, email, teacher_hash),
        )
    t1, t2 = [r[0] for r in db.execute("SELECT id FROM users WHERE role='teacher' ORDER BY id")]
    class_ids = []
    for cname, tid in (("JSS 1A", t1), ("JSS 2A", t2), ("SS 1A", t1)):
        cur = db.execute("INSERT INTO classes (name, teacher_id) VALUES (?,?)", (cname, tid))
        class_ids.append(cur.lastrowid)

    first = ["Amina", "Chinedu", "Tolu", "Ibrahim", "Ngozi", "Emeka", "Fatima", "Seun",
             "Blessing", "Musa", "Zainab", "Daniel", "Halima", "Kunle", "Grace", "Yusuf"]
    last = ["Okafor", "Bello", "Adeyemi", "Musa", "Eze", "Ibrahim", "Balogun", "Danjuma",
            "Okoro", "Lawal", "Abubakar", "Nwosu", "Garba", "Afolabi"]
    n = 0
    for cid in class_ids:
        for _ in range(8):
            n += 1
            db.execute(
                "INSERT INTO students (name, matric_no, email, class_id) VALUES (?,?,?,?)",
                (f"{rnd.choice(first)} {rnd.choice(last)}", f"SCH/2026/{n:03d}",
                 f"student{n}@school.test", cid),
            )
