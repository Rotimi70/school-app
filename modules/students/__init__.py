"""Students: list, search, add/edit/delete, student page, student logins and CSV export."""
import os

from .routes import bp
from .seed import seed

MODULE = {
    "label": "Students",
    "blueprint": bp,
    "schema": os.path.join(os.path.dirname(__file__), "schema.sql"),
    "seed": seed,
    "nav": [
        {"label": "Students", "endpoint": "students.students", "icon": "users",
         "roles": ("admin", "teacher"), "group": "main", "prefix": "students.student"},
        {"label": "My profile", "endpoint": "students.me", "icon": "users",
         "roles": ("student",), "group": "main", "prefix": "students.me"},
    ],
}
