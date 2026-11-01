"""Tests for rtk.core.units."""

import numpy as np
import pytest

from rtk.core.units import convert, units_for


@pytest.mark.parametrize(
    "value, from_unit, to_unit, expected",
    [
        (3000, "psi", "Pa", 20684271.879),
        (32, "F", "C", 0.0),
        (212, "F", "C", 100.0),
        (-40, "F", "C", -40.0),
        (200, "F", "R", 659.67),
        (1, "acre_ft", "bbl", 7758.367346938775),
        (1, "psi/ft", "kPa/m", 22.620594793307085),
        (1, "mD", "D", 0.001),
    ],
)
def test_convert(value, from_unit, to_unit, expected):
    assert convert(value, from_unit, to_unit) == pytest.approx(
        expected, rel=1e-9, abs=1e-12
    )


def test_delta_ignores_offset():
    assert convert(10, "F", "C", delta=True) == pytest.approx(50 / 9)


def test_round_trip():
    kelvin = convert(75, "F", "K")
    assert convert(kelvin, "K", "F") == pytest.approx(75.0)


def test_array_input():
    result = convert(np.array([1, 2, 3]), "ft", "m")
    assert result == pytest.approx([0.3048, 0.6096, 0.9144])


@pytest.mark.parametrize(
    "from_unit, to_unit, message",
    [
        ("psi", "ft", "Cannot convert"),
        ("STB", "rb", "Cannot convert"),
        ("psii", "Pa", "Unknown unit"),
    ],
)
def test_convert_errors(from_unit, to_unit, message):
    with pytest.raises(ValueError, match=message):
        convert(1, from_unit, to_unit)


def test_units_for_pressure():
    assert "psi" in units_for("pressure")


def test_units_for_unknown_dimension():
    with pytest.raises(ValueError, match="Unknown dimension"):
        units_for("presure")
