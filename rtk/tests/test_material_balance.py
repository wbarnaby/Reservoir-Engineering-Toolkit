"""Tests for rtk.core.material_balance."""

import numpy as np
import pytest

from rtk.core.constants import BG_FT3, BG_RB, FT3_PER_BBL
from rtk.core.material_balance import gas_fvf, p_over_z
from rtk.core.units import convert

T_RES = 659.67  # 200 degF in degR


@pytest.fixture
def gas_data():
    """Worked example from the derivation (Section 12)."""
    gp = np.array([0.0, 10.0, 20.0, 30.0, 40.0])
    p = np.array([4400.0, 3915.0, 3480.0, 3080.0, 2670.0])
    z = np.array([0.88, 0.87, 0.87, 0.88, 0.89])
    return gp, p, z


# ---------- constants ----------


def test_ft3_per_bbl():
    assert FT3_PER_BBL == pytest.approx(5.614583, rel=1e-6)


def test_bg_constants_match_textbook():
    assert BG_FT3 == pytest.approx(0.02828, rel=1e-3)
    assert BG_RB == pytest.approx(0.005037, rel=1e-3)


def test_bg_constants_agree_with_units_module():
    assert convert(BG_FT3, "ft3/scf", "rb/scf") == pytest.approx(BG_RB)


# ---------- p_over_z ----------


def test_p_over_z_array(gas_data):
    _gp, p, z = gas_data
    expected = [5000.0, 4500.0, 4000.0, 3500.0, 3000.0]
    assert p_over_z(p, z) == pytest.approx(expected)


def test_p_over_z_scalar():
    assert p_over_z(4400, 0.88) == pytest.approx(5000.0)


def test_p_over_z_accepts_lists():
    assert p_over_z([4400, 3915], [0.88, 0.87]) == pytest.approx(
        [5000.0, 4500.0]
    )


@pytest.mark.parametrize(
    "p, z, message",
    [
        ([4400, 3915], [0.88], "shape"),
        ([4400], [0.0], "z must be positive"),
        ([4400], [-0.9], "z must be positive"),
        ([-100], [0.9], "p must be positive"),
    ],
)
def test_p_over_z_errors(p, z, message):
    with pytest.raises(ValueError, match=message):
        p_over_z(p, z)


# ---------- gas_fvf ----------


def test_gas_fvf_hand_value():
    # hand calculation: 0.02828 * 0.88 * 659.67 / 4400
    assert gas_fvf(4400, 0.88, T_RES) == pytest.approx(0.0037310, rel=1e-4)


def test_gas_fvf_increases_as_pressure_falls(gas_data):
    _gp, p, z = gas_data
    bg = gas_fvf(p, z, T_RES)
    assert np.all(np.diff(bg) > 0)


def test_bg_ratio_equals_pz_ratio(gas_data):
    # Bgi / Bg = (p/z) / (pi/zi), derivation Section 8
    _gp, p, z = gas_data
    bg = gas_fvf(p, z, T_RES)
    pz = p_over_z(p, z)
    assert bg[0] / bg == pytest.approx(pz / pz[0])


def test_gas_fvf_rb_via_units(gas_data):
    _gp, p, z = gas_data
    bg_ft3 = gas_fvf(p, z, T_RES)
    bg_rb = convert(bg_ft3, "ft3/scf", "rb/scf")
    assert bg_rb == pytest.approx(BG_RB * z * T_RES / p)


def test_gas_fvf_rejects_fahrenheit():
    with pytest.raises(ValueError, match="degF"):
        gas_fvf(4400, 0.88, 200)
