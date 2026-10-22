"""Generated unique identifiers."""
import re


def next_number(db, table, column, prefix):
    """Next running number for identifiers like PREFIX0001.

    `table` and `column` are fixed names written in our own code, never user input.
    """
    nums = []
    for (value,) in db.execute(f"SELECT {column} FROM {table} WHERE {column} LIKE ?", (prefix + "%",)):
        m = re.fullmatch(re.escape(prefix) + r"(\d+)", value or "")
        if m:
            nums.append(int(m.group(1)))
    return max(nums, default=0) + 1
