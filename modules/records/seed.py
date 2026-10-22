import random

STATES = ["Borno", "Gombe", "Adamawa", "Yobe", "Bauchi"]
GUARDIANS = [("Mr. {}", "Father"), ("Mrs. {}", "Mother")]


def seed(db, config):
    rnd = random.Random(17)
    for sid, name in db.execute("SELECT id, name FROM students ORDER BY id").fetchall():
        surname = name.split()[-1]
        db.execute(
            "INSERT INTO student_profiles (student_id, date_of_birth, gender, nationality, state_of_origin, "
            "home_address, phone, admission_date) VALUES (?,?,?,?,?,?,?,?)",
            (sid, f"{rnd.randint(2008, 2013)}-{rnd.randint(1, 12):02d}-{rnd.randint(1, 28):02d}",
             rnd.choice(["male", "female"]), "Nigerian", rnd.choice(STATES),
             f"{rnd.randint(1, 60)} Demo Street, Biu", f"080{rnd.randint(10000000, 99999999)}", "2026-09-07"))
        title, relation = rnd.choice(GUARDIANS)
        db.execute(
            "INSERT INTO family_contacts (student_id, full_name, relationship, phone, is_primary, is_emergency) "
            "VALUES (?,?,?,?,1,1)",
            (sid, title.format(surname), relation, f"081{rnd.randint(10000000, 99999999)}"))
