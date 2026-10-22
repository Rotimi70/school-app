"""Timetable: weekly class schedules. Admins edit; teachers and students can view."""
import os

from .routes import bp
from .seed import seed

MODULE = {
    "label": "Timetable",
    "blueprint": bp,
    "schema": os.path.join(os.path.dirname(__file__), "schema.sql"),
    "seed": seed,
    "nav": [
        {"label": "Timetable", "endpoint": "timetable.timetable", "icon": "calendar",
         "roles": ("admin", "teacher", "student"), "group": "main", "prefix": "timetable."},
    ],
}
