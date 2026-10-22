"""Grades: enter scores per class, subject and term, and export to CSV."""
import os

from .panels import grade_chart_panel
from .routes import bp
from .seed import seed

MODULE = {
    "label": "Grades",
    "blueprint": bp,
    "schema": os.path.join(os.path.dirname(__file__), "schema.sql"),
    "seed": seed,
    "student_panels": [grade_chart_panel],
    "nav": [
        {"label": "Grades", "endpoint": "grades.grades", "icon": "award",
         "roles": ("admin", "teacher"), "group": "main"},
    ],
}
