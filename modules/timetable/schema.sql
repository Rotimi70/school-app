CREATE TABLE IF NOT EXISTS schedule_slots (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id   INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    weekday    INTEGER NOT NULL CHECK (weekday BETWEEN 1 AND 5),   -- 1 = Monday ... 5 = Friday
    start_time TEXT NOT NULL,                                       -- HH:MM
    end_time   TEXT NOT NULL,
    subject    TEXT NOT NULL,
    teacher_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    room       TEXT
);

CREATE INDEX IF NOT EXISTS idx_slots_class ON schedule_slots(class_id, weekday, start_time);
