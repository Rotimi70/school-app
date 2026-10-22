-- One row of personal details per student (the core students table stays untouched).
CREATE TABLE IF NOT EXISTS student_profiles (
    student_id      INTEGER PRIMARY KEY REFERENCES students(id) ON DELETE CASCADE,
    date_of_birth   TEXT,
    gender          TEXT CHECK (gender IN ('male', 'female', 'other') OR gender IS NULL),
    nationality     TEXT,
    state_of_origin TEXT,
    home_address    TEXT,
    phone           TEXT,
    national_id     TEXT,
    admission_date  TEXT,
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- A national / birth-certificate number, when given, can belong to only one student.
CREATE UNIQUE INDEX IF NOT EXISTS idx_profile_national_id
    ON student_profiles(national_id) WHERE national_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS family_contacts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id   INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    full_name    TEXT NOT NULL,
    relationship TEXT NOT NULL,
    phone        TEXT,
    email        TEXT,
    address      TEXT,
    is_primary   INTEGER NOT NULL DEFAULT 0,
    is_emergency INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_contacts_student ON family_contacts(student_id);
