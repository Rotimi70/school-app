from werkzeug.security import generate_password_hash


def seed(db, config):
    if not config.get("DEMO_MODE"):
        return
    row = db.execute("SELECT id FROM students ORDER BY id LIMIT 1").fetchone()
    if row:
        # One demo student login (matric number SCH/2026/001).
        db.execute("INSERT INTO student_accounts (student_id, password_hash) VALUES (?,?)",
                   (row[0], generate_password_hash("student123")))
