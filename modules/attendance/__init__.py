"""Attendance: mark present/late/absent per class and day, and export to CSV."""
import os

from .routes import bp
from .seed import seed

MODULE = {
    "label": "Attendance",
    "blueprint": bp,
    "schema": os.path.join(os.path.dirname(__file__), "schema.sql"),
    "seed": seed,
    "nav": [
        {"label": "Attendance", "endpoint": "attendance.attendance", "icon": "check",
         "roles": ("admin", "teacher"), "group": "main"},
    ],
}
