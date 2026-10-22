"""Database helpers shared by every module."""
import sqlite3

from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query(sql, args=(), one=False):
    rows = get_db().execute(sql, args).fetchall()
    if one:
        return rows[0] if rows else None
    return rows


def execute(sql, args=()):
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur


def placeholders(n):
    return ",".join("?" * n)


def init_app(app):
    app.teardown_appcontext(close_db)


def setup_connection(app):
    """A separate connection used only at start-up (creating tables, demo data)."""
    db = sqlite3.connect(app.config["DATABASE"])
    db.execute("PRAGMA foreign_keys = ON")
    return db


def run_script(db, path):
    with open(path, encoding="utf-8") as f:
        db.executescript(f.read())
