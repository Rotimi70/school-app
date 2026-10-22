# School Manager (v3, modular)

A small school management web app: Flask + SQLite, no paid services.

## Modules
Each module lives in `modules/<name>/` with its own routes, templates, database tables (`schema.sql`) and optional demo data. The shared **core** (`core/`) only handles login, security, the database connection and navigation.

| Module | What it does |
|---|---|
| dashboard | Overview cards |
| students | Student list, search, CSV export, student logins, `/me` portal |
| attendance | Daily attendance + export |
| grades | Scores per subject/term + export |
| timetable | Weekly class schedule, with clash detection |
| records | Personal details, national ID, family contacts, register export |
| admissions | Applications -> review -> offer -> accept -> enrol (creates the student and a matric number) |
| administration | Teachers and classes |

### If one module breaks
- A module that fails to load is skipped; the rest of the app keeps running and admins see a banner.
- A crash inside one module shows a friendly "this part is unavailable" page.
- Sections on the student page (personal details, contacts, admission record) fail on their own.
- Admins can open **System status** (`/system`) to see what is loaded.
- Switch modules off with an environment variable, e.g. `DISABLED_MODULES=timetable,admissions`.

Honest limit: all modules share one SQLite file and the core, so a broken core or a corrupt database still affects everything. Truly separate services would need separate hosting.

## Run locally
```
pip install -r requirements.txt
python app.py
```
Demo logins (demo mode only): admin@school.test / admin123, teacher1@school.test / teacher123, student SCH/2026/001 / student123.

## Settings (environment variables)
`SECRET_KEY`, `DEMO_MODE` (1/0), `DATABASE`, `SCHOOL_CODE` (matric prefix, default SCH), `DISABLED_MODULES`.

## Upgrading from v2
1. Copy the v3 files over your project. **Delete the old `schema.sql` in the project root** (each module now has its own).
2. `git add .`, `git commit -m "v3 modules"`, `git push`.
3. On the server: `git pull`, then Reload the web app.

New tables are created automatically; existing data is kept.

## Adding a module
Create `modules/<name>/` with `__init__.py` exposing a `MODULE` dict, then add the name to `MODULE_NAMES` in `modules/__init__.py`.
