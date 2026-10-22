SUBJECTS = ["Mathematics", "English", "Science"]
# Start times differ between classes that share a teacher, so the demo has no clashes.
STARTS = [(8, 0), (8, 0), (11, 0)]


def seed(db, config):
    classes = db.execute("SELECT id, teacher_id FROM classes ORDER BY id").fetchall()
    for index, (class_id, teacher_id) in enumerate(classes):
        hour, minute = STARTS[index % len(STARTS)]
        for weekday in range(1, 6):
            for period in range(3):
                start = hour * 60 + minute + period * 60
                end = start + 50
                subject = SUBJECTS[(period + weekday) % len(SUBJECTS)]
                db.execute(
                    "INSERT INTO schedule_slots (class_id, weekday, start_time, end_time, subject, teacher_id, room) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (class_id, weekday, f"{start // 60:02d}:{start % 60:02d}", f"{end // 60:02d}:{end % 60:02d}",
                     subject, teacher_id, f"Room {index + 1}"))
