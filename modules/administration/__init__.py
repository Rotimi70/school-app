"""Administration: teacher accounts and classes (admin only)."""
from .routes import bp

MODULE = {
    "label": "Administration",
    "blueprint": bp,
    "nav": [
        {"label": "Teachers", "endpoint": "administration.teachers", "icon": "briefcase",
         "roles": ("admin",), "group": "Administration", "prefix": "administration.teacher"},
        {"label": "Classes", "endpoint": "administration.classes", "icon": "layers",
         "roles": ("admin",), "group": "Administration", "prefix": "administration.class"},
    ],
}
