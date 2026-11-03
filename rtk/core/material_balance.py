"""Gas material balance: p/z, Havlena-Odeh, Cole plot, volumetrics.

Equation numbers refer to gas_material_balance.pdf.
Every production history must start at initial conditions (Gp = 0).
"""

import numpy as np

from rtk.core.constants import BG_FT3, FT3_PER_ACRE_FT
from rtk.core.fitting import fit_line, fit_origin, fit_stats
from rtk.core.units import convert


def p_over_z(p, z):
    # Return p/z. p in psia (absolute), z dimensionless.
    p = np.asarray(p, dtype=float)
    z = np.asarray(z, dtype=float)

    if p.shape != z.shape:
        raise ValueError(f"p and z shapes differ: {p.shape} vs {z.shape}")
    if np.any(z <= 0):
        raise ValueError("z must be positive")
    if np.any(p <= 0):
        raise ValueError("p must be positive (absolute pressure, psia)")

    return p / z


def gas_fvf(p, z, t_rankine):
    """Return gas formation volume factor Bg in ft3/scf. Eq. (3).

    p in psia, t_rankine in degR. For rb/scf use
    units.convert(bg, "ft3/scf", "rb/scf")
    """

    if np.any(np.asarray(t_rankine, dtype=float) < 459.67):
        raise ValueError(
            "T below 459.67 degR (0 degF); did you pass degF instead of degR?"
        )

    pz = p_over_z(p, z)
    return BG_FT3 * t_rankine / pz


def _check_history(gp, p, z):
    """Validate a production history and return float arrays

    The leading underscore marks this as private to this module.
    """

    gp = np.asarray(gp, dtype=float)
    p = np.asarray(p, dtype=float)
    z = np.asarray(z, dtype=float)

    if gp.ndim != 1:
        raise ValueError(f"Gp must be 1-D, got {gp.ndim}-D")
    if not gp.shape == p.shape == z.shape:
        raise ValueError(
            f"Gp, p, and z lengths differ: Gp: {len(gp)}, p: {len(p)}, z: {len(z)}"
        )
    if len(gp) < 3:
        raise ValueError(f"Need at least 3 data points, got {len(gp)}")
    if gp[0] != 0:
        raise ValueError("First row must be initial conditions (Gp = 0)")
    if np.any(np.diff(gp) < 0):
        raise ValueError("Cumulative Gp must not decrease")

    return gp, p, z


def pz_analysis(gp, p, z, ce=0.0, p_abandon=None, z_abandon=None):
    """Fit the p/z line and estimate the original gas in place G.

    gp: cumulative gas, any surface unit;; G is returned in the same unit
    p: average reservoir pressure, psia
    z: gas deviation factor at each p
    ce: effective compressibility, 1/psi (0 = volumetric), Eq. (13)
    p_abandon, z_abandon: optional abandonment conditions for reserves

    Returns a dict. Eqs. (6), (7), (8), (9), (14).
    """

    gp, p, z = _check_history(gp, p, z)
    if ce < 0:
        raise ValueError("ce must not be negative")

    pz = p_over_z(p, z)
    delta_p = p[0] - p
    y = pz * (1 - ce * delta_p)  # left side of Eq. (14)

    intercept, slope = fit_line(gp, y)
    if slope >= 0:
        raise ValueError(
            "p/z does not decline with Gp, so G cannot be estimated"
        )

    g = -intercept / slope  # Eq. (7)
    y_fit = intercept + slope * gp

    result = {
        "pz": pz,
        "y": y,
        "y_fit": y_fit,
        "intercept": intercept,
        "slope": slope,
        "G": g,
        "pz_initial_measured": float(pz[0]),
        "recovery_factor": gp / g,  # Eq. (8)
        "stats": fit_stats(y, y_fit),
    }

    if p_abandon is not None and z_abandon is not None:
        pz_ab = float(p_over_z(p_abandon, z_abandon))
        y_ab = pz_ab * (1 - ce * (p[0] - p_abandon))
        gp_ab = g * (1 - y_ab / intercept)
        result["gp_abandon"] = gp_ab
        result["remaining"] = gp_ab - gp[-1]

    return result


def havlena_odeh_gas(gp_scf, p, z, t_rankine, wp=0.0, bw=1.0):
    """Fit F = G * Eg through the origin. Eqs. (10), (11).

    gp_scf: cumulative gas, scf (must be scf: F mixes gas and water)
    t_rankine: reservoir temperature, degR
    wp: cumulative water, STB (scalar or array), default 0
    bw: water FVF, rb/STB

    Returns a dict with Bg (rb/scf), F (rb), Eg (rb/scf) and G (scf)"""

    gp, p, z = _check_history(gp_scf, p, z)
    wp = np.asarray(wp, dtype=float)
    if wp.ndim != 0 and wp.shape != gp.shape:
        raise ValueError("wp must be a single value or match Gp's length")

    bg = convert(gas_fvf(p, z, t_rankine), "ft3/scf", "rb/scf")
    eg = bg - bg[0]
    f = gp * bg + wp * bw

    g = fit_origin(eg, f)

    return {
        "bg": bg,
        "F": f,
        "Eg": eg,
        "G": g,
        "stats": fit_stats(f, g * eg),
    }


def cole_values(gp, f, eg):
    """Return (gp, F/Eg) for the Cole plot, Eq. (12).

    Points with Eg <= 0 (the initial point) are dropped since
    F/Eg is 0/0 there.
    """

    gp = np.asarray(gp, dtype=float)
    f = np.asarray(f, dtype=float)
    eg = np.asarray(eg, dtype=float)

    mask = eg > 0
    return gp[mask], f[mask] / eg[mask]


def volumetric_ogip(area_acres, h_ft, phi, swi, bgi_ft3):
    """Return original gas in place from the rock, scf. Eq. (15).

    bgi_ft3 is initial Bg in ft3/scf.
    """

    if not 0 < phi <= 1:
        raise ValueError("phi must be a fraction between 0 and 1")
    if not 0 <= swi < 1:
        raise ValueError("swi must be a fraction between 0 and 1")
    if area_acres <= 0 or h_ft <= 0 or bgi_ft3 <= 0:
        raise ValueError("area, h, or Bgi must be positive")

    gas_pore_volume = FT3_PER_ACRE_FT * area_acres * h_ft * phi * (1 - swi)
    return gas_pore_volume / bgi_ft3
