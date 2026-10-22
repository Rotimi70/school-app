"""Admissions & Enrolment: applications from first contact to enrolled student.

Enrolling creates the student in the core students table (with a generated matric
number). It then tries to copy personal details and guardians into the Records
module; if Records isn't available the student is still enrolled and a note says
what to add by hand.
"""
import os

from .panels import admission_panel, open_applications_card
from .routes import bp
from .seed import seed

MODULE = {
    "label": "Admissions",
    "blueprint": bp,
    "schema": os.path.join(os.path.dirname(__file__), "schema.sql"),
    "seed": seed,
    "student_panels": [admission_panel],
    "dashboard_cards": [open_applications_card],
    "nav": [
        {"label": "Admissions", "endpoint": "admissions.applications", "icon": "clipboard",
         "roles": ("admin",), "group": "Admissions", "prefix": "admissions."},
    ],
}
