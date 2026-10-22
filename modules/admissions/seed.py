from datetime import date

DEMO = [
    ("Aisha", "Mohammed", "applied", "Mrs. Mohammed", "Mother"),
    ("Samuel", "Yakubu", "review", "Mr. Yakubu", "Father"),
    ("Hauwa", "Garba", "offered", "Mrs. Garba", "Mother"),
    ("Peter", "Danladi", "accepted", "Mr. Danladi", "Father"),
    ("Mariam", "Usman", "rejected", "Mr. Usman", "Father"),
    ("Ibrahim", "Suleiman", "applied", "Mrs. Suleiman", "Mother"),
]


def seed(db, config):
    today = date.today()
    year = f"{today.year}/{today.year + 1}" if today.month >= 8 else f"{today.year - 1}/{today.year}"
    class_row = db.execute("SELECT id FROM classes ORDER BY name LIMIT 1").fetchone()
    class_id = class_row[0] if class_row else None
    for n, (first, last, status, guardian, relation) in enumerate(DEMO, start=1):
        cur = db.execute(
            "INSERT INTO applications (application_no, first_name, last_name, gender, nationality, class_id, "
            "academic_year, status) VALUES (?,?,?,?,?,?,?,?)",
            (f"APP/{today.year}/{n:04d}", first, last, "female" if first[-1] == "a" else "male", "Nigerian",
             class_id, year, status))
        db.execute(
            "INSERT INTO application_guardians (application_id, full_name, relationship, phone, is_primary, is_emergency) "
            "VALUES (?,?,?,?,1,1)", (cur.lastrowid, guardian, relation, f"080{12345670 + n}"))
