"""Feature modules, each loaded on its own.

A module is a folder in modules/ whose __init__.py defines a MODULE dictionary:

    label            name shown in menus and error messages
    blueprint        the Flask blueprint with its pages
    schema           path to its own schema.sql (its own database tables)
    seed             optional function(db, config) that adds demo data
    nav              menu entries: label, endpoint, icon, roles, group
    student_panels   optional functions that add sections to the student page
    dashboard_cards  optional functions that add cards to the dashboard

load_modules() imports each one inside its own try/except. If a module fails to
import, can't create its tables, or is switched off, it is simply left out and the
others keep working. Run-time crashes inside a module are caught by the error
handler in core/ui.py and only affect that request.

To switch a module off without touching code, set DISABLED_MODULES (for example
DISABLED_MODULES=timetable,admissions) in the environment.
"""
import importlib
import logging

from core import db as coredb

log = logging.getLogger("school.modules")

# Order = order in the sidebar menu and the order demo data is created.
MODULE_NAMES = [
    "dashboard",
    "students",
    "attendance",
    "grades",
    "timetable",
    "records",
    "admissions",
    "administration",
]


def load_modules(app, names=None):
    names = list(names if names is not None else MODULE_NAMES)
    disabled = set(app.config.get("DISABLED_MODULES") or ())
    status, loaded = [], []
    nav = list(app.config.get("NAV_ITEMS", []))
    panels, cards = [], []

    setup_db = coredb.setup_connection(app)
    try:
        for name in names:
            entry = {"name": name, "label": name.replace("_", " ").title(),
                     "ok": False, "disabled": name in disabled, "error": None}
            status.append(entry)
            if entry["disabled"]:
                continue
            try:
                module = importlib.import_module(f"modules.{name}")
                meta = module.MODULE
                entry["label"] = meta.get("label", entry["label"])
                if meta.get("schema"):
                    coredb.run_script(setup_db, meta["schema"])
                new_nav = [dict(item, prefix=item.get("prefix") or item["endpoint"].split(".")[0] + ".")
                           for item in meta.get("nav", [])]
                app.register_blueprint(meta["blueprint"])
                nav.extend(new_nav)
                panels.extend(meta.get("student_panels", []))
                cards.extend(meta.get("dashboard_cards", []))
                loaded.append(meta)
                entry["ok"] = True
            except Exception as exc:  # one broken module must never stop the others
                log.exception("Module %r could not be loaded", name)
                entry["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        setup_db.close()

    app.config.update(MODULE_STATUS=status, LOADED_MODULES=loaded, NAV_ITEMS=nav,
                      STUDENT_PANELS=panels, DASHBOARD_CARDS=cards)
    return loaded
