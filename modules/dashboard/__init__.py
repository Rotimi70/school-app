"""Dashboard: summary figures. Reads other modules' tables defensively, so it still loads
if one of them is unavailable. Other modules can add cards via "dashboard_cards"."""
from .routes import bp

MODULE = {
    "label": "Dashboard",
    "blueprint": bp,
    "nav": [
        {"label": "Dashboard", "endpoint": "dashboard.dashboard", "icon": "home",
         "roles": ("admin", "teacher"), "group": "main"},
    ],
}
