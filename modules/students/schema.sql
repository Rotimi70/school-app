-- Optional login for a student (username = matric number). Removed automatically if the student is deleted.
CREATE TABLE IF NOT EXISTS student_accounts (
    student_id    INTEGER PRIMARY KEY REFERENCES students(id) ON DELETE CASCADE,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
