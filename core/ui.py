"""Icons, navigation menu and error pages shared by every module."""
from flask import current_app, g, render_template, request, url_for
from markupsafe import Markup
from werkzeug.exceptions import HTTPException
from werkzeug.routing import BuildError

# Feather-style icons as inline SVG so there are no external dependencies.
ICONS = {
    "home": '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
    "users": '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "check": '<polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>',
    "award": '<circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/>',
    "briefcase": '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
    "layers": '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
    "logout": '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
    "menu": '<line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/>',
    "search": '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
    "plus": '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
    "percent": '<line x1="19" y1="5" x2="5" y2="19"/><circle cx="6.5" cy="6.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/>',
    "calendar": '<rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>',
    "clipboard": '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/>',
    "user-plus": '<path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/>',
    "alert": '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
    "activity": '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
}


def icon(name):
    return Markup(
        '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true">%s</svg>' % ICONS.get(name, ICONS["layers"])
    )


def safe_url(endpoint, **values):
    """url_for that returns '' instead of crashing when that module isn't loaded."""
    try:
        return url_for(endpoint, **values)
    except BuildError:
        return ""


# Order of the sidebar groups. "main" has no heading.
NAV_GROUPS = ["main", "Admissions", "Finance", "Reports", "Administration"]


def build_nav():
    user = g.get("user")
    if not user:
        return []
    groups = {}
    for item in current_app.config.get("NAV_ITEMS", []):
        if user["role"] in item["roles"]:
            groups.setdefault(item.get("group", "main"), []).append(item)
    ordered = [(name, groups[name]) for name in NAV_GROUPS if name in groups]
    ordered += [(name, items) for name, items in groups.items() if name not in NAV_GROUPS]
    return ordered


def nav_active(item):
    return bool(request.endpoint) and request.endpoint.startswith(item["prefix"])


def http_error(err):
    return render_template("error.html", code=err.code, message=err.description), err.code


def unexpected_error(err):
    """A crash inside one module shows a friendly page; everything else keeps working."""
    if isinstance(err, HTTPException):
        return err
    current_app.logger.exception("Unhandled error on %s (module: %s)", request.path, request.blueprint)
    label = None
    for entry in current_app.config.get("MODULE_STATUS", []):
        if entry["name"] == request.blueprint:
            label = entry["label"]
    return render_template("module_error.html", module=label), 500


def init_ui(app):
    app.jinja_env.globals.update(icon=icon, safe_url=safe_url, nav_active=nav_active)

    @app.context_processor
    def inject_layout():
        failed = [m for m in app.config.get("MODULE_STATUS", []) if m["error"]]
        return {"nav_groups": build_nav(), "failed_modules": failed}

    for code in (400, 403, 404, 405):
        app.register_error_handler(code, http_error)
    app.register_error_handler(Exception, unexpected_error)
