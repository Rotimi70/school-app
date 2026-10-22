CREATE TABLE IF NOT EXISTS grades (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    subject    TEXT NOT NULL,
    term       TEXT NOT NULL,
    score      REAL NOT NULL CHECK (score >= 0 AND score <= 100),
    UNIQUE (student_id, subject, term)
);

CREATE INDEX IF NOT EXISTS idx_grades_student ON grades(student_id);
