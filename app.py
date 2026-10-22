"""School Manager: Flask + SQLite.

A small core (login, permissions, layout, database helpers) plus separate feature
modules in modules/. Every module has its own pages, templates and database tables
and is loaded independently, so a problem in one cannot take the others down.

Roles
  admin   - manages teachers, classes, admissions and every student
  teacher - works only with the classes assigned to them
  student - sees only their own profile, attendance and grades
"""
import logging
import os

from flask import Flask

from core import db, security, ui
from core.auth_routes import core_bp
from core.seed import seed_core
from modules import load_modules

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _setup_core_database(app):
    """Create the core tables. Returns True if the database is brand new."""
    conn = db.setup_connection(app)
    try:
        db.run_script(conn, os.path.join(BASE_DIR, "core", "schema.sql"))
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
    finally:
        conn.close()


def _seed_demo_data(app, loaded):
    conn = db.setup_connection(app)
    try:
        seed_core(conn)
        conn.commit()
        for meta in loaded:
            seed = meta.get("seed")
            if not seed:
                continue
            try:
                seed(conn, app.config)
                conn.commit()
            except Exception:
                conn.rollback()
                app.logger.exception("Demo data for module %r failed", meta.get("label"))
    finally:
        conn.close()


def create_app(overrides=None, module_names=None):
    app = Flask(__name__)
    disabled = {n.strip() for n in os.environ.get("DISABLED_MODULES", "").split(",") if n.strip()}
    app.config.update(
        # Set SECRET_KEY as an environment variable on your host. The fallback is for local use only.
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        DEMO_MODE=os.environ.get("DEMO_MODE", "1") == "1",
        DATABASE=os.environ.get("DATABASE", os.path.join(BASE_DIR, "school.db")),
        SCHOOL_CODE=os.environ.get("SCHOOL_CODE", "SCH"),
        DISABLED_MODULES=disabled,
    )
    if overrides:
        app.config.update(overrides)
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO)

    db.init_app(app)
    security.init_security(app)
    ui.init_ui(app)
    app.register_blueprint(core_bp)

    fresh = _setup_core_database(app)
    loaded = load_modules(app, module_names)
    if fresh:
        _seed_demo_data(app, loaded)

    app.config["NAV_ITEMS"] = app.config["NAV_ITEMS"] + [{
        "label": "System status", "endpoint": "core.system_status", "icon": "activity",
        "roles": ("admin",), "group": "Administration", "prefix": "core.system",
    }]
    return app


# Create the app on import (also works under WSGI hosts such as PythonAnywhere).
app = create_app()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
