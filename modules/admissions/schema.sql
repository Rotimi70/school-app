CREATE TABLE IF NOT EXISTS applications (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    application_no  TEXT NOT NULL UNIQUE,            -- e.g. APP/2026/0001
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    date_of_birth   TEXT,
    gender          TEXT CHECK (gender IN ('male', 'female', 'other') OR gender IS NULL),
    nationality     TEXT,
    state_of_origin TEXT,
    home_address    TEXT,
    phone           TEXT,
    email           TEXT,
    previous_school TEXT,
    national_id     TEXT,
    class_id        INTEGER REFERENCES classes(id) ON DELETE SET NULL,   -- class applied for
    academic_year   TEXT NOT NULL,                   -- e.g. 2026/2027
    status          TEXT NOT NULL DEFAULT 'applied'
                    CHECK (status IN ('applied', 'review', 'offered', 'accepted', 'enrolled', 'rejected', 'withdrawn')),
    notes           TEXT,
    student_id      INTEGER REFERENCES students(id) ON DELETE SET NULL,  -- set when enrolled
    applied_on      TEXT NOT NULL DEFAULT (date('now')),
    decided_on      TEXT,
    enrolled_on     TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS application_guardians (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    full_name      TEXT NOT NULL,
    relationship   TEXT NOT NULL,
    phone          TEXT,
    email          TEXT,
    address        TEXT,
    is_primary     INTEGER NOT NULL DEFAULT 0,
    is_emergency   INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_guardians_application ON application_guardians(application_id);
