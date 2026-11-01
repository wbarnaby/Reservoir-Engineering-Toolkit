"""Tests for rtk.core.fitting."""

import numpy as np
import pytest

from rtk.core.fitting import fit_line, fit_origin, fit_stats


@pytest.fixture
def hand_data():
    """Small data set solved by hand: x=[1,2,3], y=[1,2,2]."""
    x = np.array([1.0, 2.0, 3.0])
    y = np.array([1.0, 2.0, 2.0])
    return x, y


def test_fit_line_hand(hand_data):
    x, y = hand_data
    b0, b1 = fit_line(x, y)
    assert b0 == pytest.approx(2 / 3)
    assert b1 == pytest.approx(0.5)


def test_fit_stats_hand(hand_data):
    x, y = hand_data
    b0, b1 = fit_line(x, y)
    stats = fit_stats(y, b0 + b1 * x)
    assert stats["r2"] == pytest.approx(0.75)
    assert stats["l1"] == pytest.approx(2 / 3)
    assert stats["l2"] == pytest.approx(np.sqrt(1 / 6))
    assert stats["rmse"] == pytest.approx(np.sqrt(1 / 18))


def test_residual_properties(hand_data):
    x, y = hand_data
    b0, b1 = fit_line(x, y)
    r = fit_stats(y, b0 + b1 * x)["residuals"]
    assert np.sum(r) == pytest.approx(0.0, abs=1e-12)
    assert np.sum(x * r) == pytest.approx(0.0, abs=1e-12)


def test_fit_origin_hand(hand_data):
    x, y = hand_data
    assert fit_origin(x, y) == pytest.approx(11 / 14)


def test_pz_line():
    gp = np.array([0, 10, 20, 30, 40])
    p_z = np.array([5000, 4500, 4000, 3500, 3000])
    b0, b1 = fit_line(gp, p_z)
    assert b0 == pytest.approx(5000.0)
    assert b1 == pytest.approx(-50.0)
    assert -b0 / b1 == pytest.approx(100.0)


def test_matches_polyfit():
    x = np.array([1, 2, 3, 4, 5])
    y = np.array([2.1, 3.9, 6.2, 7.8, 10.1])
    slope, intercept = np.polyfit(x, y, 1)
    assert fit_line(x, y) == pytest.approx((intercept, slope))


@pytest.mark.parametrize(
    "func, x, y, message",
    [
        (fit_line, [3, 3, 3], [1, 2, 3], "Singular"),
        (fit_line, [1, 2], [1, 2, 3], "does not match"),
        (fit_origin, [], [], "Fewer points"),
        (fit_line, [[1, 2], [3, 4]], [1, 2], "must be 1-D"),
    ],
)
def test_fit_errors(func, x, y, message):
    with pytest.raises(ValueError, match=message):
        func(x, y)


def test_r2_undefined_for_flat_y():
    stats = fit_stats([2, 2, 2], [2, 2, 2])
    assert np.isnan(stats["r2"])
