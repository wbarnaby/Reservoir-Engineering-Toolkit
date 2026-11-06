"""Load tabular data from CSV text into numpy arrays.

parse_columns() takes the file's text, not a path, so the same code
works on the desktop and in a browser. read_text() is the desktop-only
part that reads a file from disk.
"""

import csv
import io

import numpy as np


def read_text(path):
    # Read a text file. utf-8-sig strips the marker Excel adds.
    with open(path, encoding="utf-8-sig") as file:
        return file.read()


def _is_skippable(row):
    # True for blank rows and comment rows starting with #.
    if not row or all(cell.strip() == "" for cell in row):
        return True
    return row[0].strip().startswith("#")


def parse_columns(text, required, optional=()):
    """Parse CSV text into {column name: float array}.

    Header names are matched case-insensitively. Blank lines and lines
    starting with # are skipped. Raises ValueError naming the line and
    column of any problem.
    """
    reader = csv.reader(io.StringIO(text))

    header = None
    for row in reader:
        if not _is_skippable(row):
            header = [name.strip().lower() for name in row]
            break
    if header is None:
        raise ValueError("File is empty")

    missing = [name for name in required if name not in header]
    if missing:
        raise ValueError(
            f"Missing column(s): {', '.join(missing)}. "
            f"Found: {', '.join(header)}"
        )

    wanted = [name for name in (*required, *optional) if name in header]
    position = {name: header.index(name) for name in wanted}
    columns = {name: [] for name in wanted}

    for row in reader:
        if _is_skippable(row):
            continue
        line = reader.line_num
        if len(row) != len(header):
            raise ValueError(
                f"Line {line}: expected {len(header)} values, got {len(row)}"
            )
        for name in wanted:
            cell = row[position[name]].strip()
            try:
                columns[name].append(float(cell))
            except ValueError:
                raise ValueError(
                    f"Line {line}, column '{name}': '{cell}' is not a number"
                ) from None

    if not columns[wanted[0]]:
        raise ValueError("File has a header but no data rows")

    return {name: np.array(values) for name, values in columns.items()}
