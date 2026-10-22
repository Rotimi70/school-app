"""Records: personal details, family contacts and identifiers for each student.

Adds two sections to the student page and a register export. It only reads the core
students table; nothing else depends on it.
"""
import os

from .panels import family_contacts_panel, personal_details_panel
from .routes import bp
from .seed import seed

MODULE = {
    "label": "Records",
    "blueprint": bp,
    "schema": os.path.join(os.path.dirname(__file__), "schema.sql"),
    "seed": seed,
    "student_panels": [personal_details_panel, family_contacts_panel],
    "nav": [],
}
