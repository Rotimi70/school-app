"""Lets modules add sections to shared pages without depending on each other.

A module lists "student_panels" (small functions that return HTML for the student
page) or "dashboard_cards" in its MODULE dictionary. If one of them crashes, only
that section shows "temporarily unavailable"; the rest of the page still loads.
"""
from flask import current_app, render_template
from markupsafe import Markup


def render_student_panels(student, portal=False):
    """portal=True: only the sections marked safe for the student's own page."""
    out = []
    for panel in current_app.config.get("STUDENT_PANELS", []):
        if portal and not getattr(panel, "portal", False):
            continue
        try:
            html = panel(student)
        except Exception:
            title = getattr(panel, "title", "This section")
            current_app.logger.exception("Student page section %r failed", title)
            html = Markup(render_template("panel_unavailable.html", title=title))
        if html:
            out.append(html)
    return out


def collect_dashboard_cards():
    cards = []
    for card in current_app.config.get("DASHBOARD_CARDS", []):
        try:
            data = card()
        except Exception:
            current_app.logger.exception("Dashboard card %r failed", getattr(card, "__name__", card))
            continue
        if data:
            cards.append(data)
    return cards
