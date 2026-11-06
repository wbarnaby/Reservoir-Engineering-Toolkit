"""Tests for rtk.assistant.latex."""

import pytest

from rtk.assistant.latex import (
    MathStreamer,
    display_style,
    is_valid_latex,
    render_latex,
    split_math,
)

# ---------- split_math ----------


def test_split_plain_text():
    assert split_math("no math here") == [("text", "no math here")]


def test_split_one_equation():
    segments = split_math(r"so $$\frac{p}{z}$$ falls")
    assert segments == [
        ("text", "so "),
        ("math", r"\frac{p}{z}"),
        ("text", " falls"),
    ]


def test_split_unclosed_stays_text():
    segments = split_math(r"start $$ \frac{1}{2}")
    assert all(kind == "text" for kind, _ in segments)


# ---------- MathStreamer ----------


def feed_all(lines):
    """Feed lines through a fresh streamer and collect every segment."""
    streamer = MathStreamer()
    segments = []
    for line in lines:
        segments += streamer.feed(line)
    return segments + streamer.finish()


def test_stream_single_line_block():
    segments = feed_all(["The line:", r"$$\frac{p}{z} = a + b G_p$$", "Done."])
    assert segments == [
        ("text", "The line:"),
        ("math", r"\frac{p}{z} = a + b G_p"),
        ("text", "Done."),
    ]


def test_stream_multi_line_block():
    segments = feed_all(["$$", r"B_g = 0.02828", r"\frac{zT}{p}", "$$"])
    assert segments == [("math", r"B_g = 0.02828 \frac{zT}{p}")]


def test_stream_math_held_until_closed():
    streamer = MathStreamer()
    assert streamer.feed("$$ a = b") == []
    assert streamer.feed("+ c $$") == [("math", "a = b + c")]


def test_stream_unclosed_flushes_as_text():
    segments = feed_all(["$$ a = b", "never closed"])
    assert segments == [("text", "$$ a = b never closed")]


def test_stream_dollar_amounts_untouched():
    assert feed_all(["That costs $5."]) == [("text", "That costs $5.")]


# ---------- rendering ----------


def test_display_style_upgrades_fractions():
    assert display_style(r"\frac{a}{b}") == r"\dfrac{a}{b}"
    assert display_style(r"\dfrac{a}{b}") == r"\dfrac{a}{b}"


@pytest.mark.parametrize(
    "expr, valid",
    [
        (r"\frac{p}{z} = \frac{p_i}{z_i}", True),
        (r"c_e = \frac{c_f + c_w S_{wi}}{1 - S_{wi}}", True),
        (r"\begin{aligned} a &= b \end{aligned}", False),
        (r"\frac{a}{", False),
    ],
)
def test_is_valid_latex(expr, valid):
    assert is_valid_latex(expr) is valid


def test_render_returns_image():
    picture = render_latex(r"\frac{p}{z}")
    assert picture.width > 0 and picture.height > 0


def test_render_bad_latex_raises():
    with pytest.raises(ValueError, match="Cannot render"):
        render_latex(r"\frac{a}{")
