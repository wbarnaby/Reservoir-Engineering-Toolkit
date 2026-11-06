"""Split assistant replies into text and LaTeX, and render LaTeX to images.

Display math is written between $$ and $$ on its own lines. Rendering
uses matplotlib's mathtext, so no TeX installation is needed. mathtext
supports most equation syntax (fractions, roots, sub/superscripts,
Greek letters, integrals) but not environments like //begin{aligned}.
"""

import io

import matplotlib

matplotlib.use("Agg")  # draw to memory, never open a window

from matplotlib import mathtext
from matplotlib.figure import Figure
from PIL import Image


def split_math(text):
    """Split text into ("text", ...) and ("math", ...) segments.

    A math segment is anything between a pair of $$ markers. An
    unclosed $$ is treated as plain text, so a half-finished reply
    never crashes the renderer.
    """
    segments = []
    parts = text.split("$$")
    for i, part in enumerate(parts):
        is_math = i % 2 == 1 and i < len(parts) - 1
        if is_math:
            segments.append(("math", part.strip()))
        elif part:
            segments.append(("text", part))
    if len(parts) % 2 == 0:  # odd number of $$: last one never closed
        segments[-1] = ("text", "$$" + parts[-1])
    return segments


def is_valid_latex(expr):
    # True if mathtext can parse expr.
    try:
        mathtext.MathTextParser("path").parse(f"${expr}$")
    except ValueError:
        return False
    return True


def render_latex(expr, color="#33ff33", background="#000000", size=15):
    """Render one LaTeX expression to a PIL image, cropped tight.

    Raises ValueError if mathtext cannot parse the expression.
    """
    expr = display_style(expr)
    if not is_valid_latex(expr):
        raise ValueError(f"Cannot render LaTeX: {expr}")

    fig = Figure(figsize=(0.01, 0.01), facecolor=background)
    fig.text(0, 0, f"${expr}$", fontsize=size, color=color)

    buffer = io.BytesIO()
    fig.savefig(
        buffer,
        format="png",
        dpi=150,
        facecolor=background,
        bbox_inches="tight",
        pad_inches=0.08,
    )
    buffer.seek(0)
    return Image.open(buffer).convert("RGB")


def display_style(expr):
    r"""Use full-size fractions: \frac renders small in mathtext."""
    return expr.replace(r"\frac", r"\dfrac")


class MathStreamer:
    """Turn streamed reply lines into ("text"/"math", ...) segments.

    Feed complete lines in order. A $$ block may span several lines;
    its segment is only released once the closing $$ arrives.
    """

    def __init__(self):
        self.in_math = False
        self.math_lines = []

    def feed(self, line):
        """Process one complete line; return the segments it finishes."""
        if not self.in_math:
            if line.count("$$") % 2 == 0:
                return split_math(line) if "$$" in line else [("text", line)]
            before, after = line.split("$$", 1)
            self.in_math = True
            self.math_lines = [after]
            return [("text", before)] if before.strip() else []

        if "$$" not in line:
            self.math_lines.append(line)
            return []

        inside, rest = line.split("$$", 1)
        self.math_lines.append(inside)
        self.in_math = False
        body = " ".join(line.strip() for line in self.math_lines)
        segments = [("math", body.strip())]
        if rest.strip():
            segments += self.feed(rest)
        return segments

    def finish(self):
        """Flush anything left when the reply ends (an unclosed $$)."""
        if not self.in_math:
            return []
        self.in_math = False
        body = " ".join(line.strip() for line in self.math_lines)
        return [("text", "$$ " + body)]
