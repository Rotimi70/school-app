"""CSV download helpers shared by every module."""
import csv
import io
import re

from flask import Response


def csv_cell(value):
    """Stop spreadsheets from running text like =SUM(...) that starts with a formula character."""
    if isinstance(value, str) and value and value[0] in "=+-@\t\r":
        return "'" + value
    return "" if value is None else value


def csv_response(filename, header, rows):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    for row in rows:
        writer.writerow([csv_cell(c) for c in row])
    # The BOM makes Excel read accents and non-English names correctly.
    return Response("﻿" + buf.getvalue(), mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


def slug(text):
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower() or "export"
