"""Unit conventions and conversions used throughout the toolkit.

Conversion factors are stored in CONVERSION_FACTORS and applied by
convert(). Each unit converts to an SI base unit for its dimension,
except surface quantities (STB, scf), which stay in oilfield units.

Format:  "symbol": (dimension, scale, offset)
         base_value = value * scale + offset
"""

import math

CONVERSION_FACTORS = {
    # pressure (base: Pa)
    "Pa": ("pressure", 1.0, 0.0),
    "kPa": ("pressure", 1e3, 0.0),
    "MPa": ("pressure", 1e6, 0.0),
    "bar": ("pressure", 1e5, 0.0),
    "atm": ("pressure", 101325.0, 0.0),
    "psi": ("pressure", 6894.757293, 0.0),
    "psia": ("pressure", 6894.757293, 0.0),
    "psig": ("pressure", 6894.757293, 101325.0),
    "barg": ("pressure", 1e5, 101325.0),
    # temperature (base: K)
    "K": ("temperature", 1.0, 0.0),
    "C": ("temperature", 1.0, 273.15),
    "F": ("temperature", 5 / 9, 459.67 * 5 / 9),
    "R": ("temperature", 5 / 9, 0.0),
    # length (base: m)
    "m": ("length", 1.0, 0.0),
    "cm": ("length", 0.01, 0.0),
    "mm": ("length", 0.001, 0.0),
    "km": ("length", 1000.0, 0.0),
    "ft": ("length", 0.3048, 0.0),
    "in": ("length", 0.0254, 0.0),
    "mi": ("length", 1609.344, 0.0),
    # area (base: m2)
    "m2": ("area", 1.0, 0.0),
    "cm2": ("area", 1e-4, 0.0),
    "ft2": ("area", 0.3048**2, 0.0),
    "in2": ("area", 0.0254**2, 0.0),
    "acre": ("area", 4046.8564224, 0.0),
    "ha": ("area", 1e4, 0.0),
    "km2": ("area", 1e6, 0.0),
    "mi2": ("area", 1609.344**2, 0.0),
    # volume, geometric or reservoir conditions (base: m3)
    "m3": ("volume", 1.0, 0.0),
    "L": ("volume", 1e-3, 0.0),
    "cm3": ("volume", 1e-6, 0.0),
    "cc": ("volume", 1e-6, 0.0),
    "ft3": ("volume", 0.3048**3, 0.0),
    "in3": ("volume", 0.0254**3, 0.0),
    "gal": ("volume", 0.003785411784, 0.0),
    "bbl": ("volume", 0.158987294928, 0.0),
    "rb": ("volume", 0.158987294928, 0.0),
    "Mbbl": ("volume", 0.158987294928 * 1e3, 0.0),
    "MMbbl": ("volume", 0.158987294928 * 1e6, 0.0),
    "acre_ft": ("volume", 4046.8564224 * 0.3048, 0.0),
    # oil volume at surface conditions (base: STB)
    # cannot convert to rb without Bo
    "STB": ("oil_surface", 1.0, 0.0),
    "MSTB": ("oil_surface", 1e3, 0.0),
    "MMSTB": ("oil_surface", 1e6, 0.0),
    # gas volume at surface conditions (base: scf)
    # cannot convert to reservoir volume without Bg
    "scf": ("gas_surface", 1.0, 0.0),
    "Mscf": ("gas_surface", 1e3, 0.0),
    "MMscf": ("gas_surface", 1e6, 0.0),
    "Bscf": ("gas_surface", 1e9, 0.0),
    "Bcf": ("gas_surface", 1e9, 0.0),
    "Tscf": ("gas_surface", 1e12, 0.0),
    "Tcf": ("gas_surface", 1e12, 0.0),
    # liquid volumetric rate (base: m3/s)
    "m3/s": ("liquid_rate", 1.0, 0.0),
    "m3/d": ("liquid_rate", 1 / 86400, 0.0),
    "L/s": ("liquid_rate", 1e-3, 0.0),
    "cm3/s": ("liquid_rate", 1e-6, 0.0),
    "ft3/s": ("liquid_rate", 0.3048**3, 0.0),
    "ft3/d": ("liquid_rate", 0.3048**3 / 86400, 0.0),
    "bbl/d": ("liquid_rate", 0.158987294928 / 86400, 0.0),
    "gpm": ("liquid_rate", 0.003785411784 / 60, 0.0),
    # oil rate at surface conditions (base: STB/d)
    "STB/d": ("oil_rate", 1.0, 0.0),
    "MSTB/d": ("oil_rate", 1e3, 0.0),
    # gas rate at surface conditions (base: scf/d)
    "scf/d": ("gas_rate", 1.0, 0.0),
    "Mscf/d": ("gas_rate", 1e3, 0.0),
    "MMscf/d": ("gas_rate", 1e6, 0.0),
    # viscosity (base: Pa.s)
    "Pa.s": ("viscosity", 1.0, 0.0),
    "cP": ("viscosity", 1e-3, 0.0),
    "mPa.s": ("viscosity", 1e-3, 0.0),
    "P": ("viscosity", 0.1, 0.0),
    "lbm/ft.s": ("viscosity", 0.45359237 / 0.3048, 0.0),
    # permeability (base: m2)
    # no "m2" key here because area already uses it
    "um2": ("permeability", 1e-12, 0.0),
    "D": ("permeability", 9.869233e-13, 0.0),
    "mD": ("permeability", 9.869233e-16, 0.0),
    # compressibility (base: 1/Pa)
    "1/Pa": ("compressibility", 1.0, 0.0),
    "1/kPa": ("compressibility", 1e-3, 0.0),
    "1/MPa": ("compressibility", 1e-6, 0.0),
    "1/bar": ("compressibility", 1e-5, 0.0),
    "1/atm": ("compressibility", 1 / 101325.0, 0.0),
    "1/psi": ("compressibility", 1 / 6894.757293, 0.0),
    "microsip": ("compressibility", 1e-6 / 6894.757293, 0.0),
    # density (base: kg/m3)
    "kg/m3": ("density", 1.0, 0.0),
    "g/cm3": ("density", 1000.0, 0.0),
    "kg/L": ("density", 1000.0, 0.0),
    "lbm/ft3": ("density", 0.45359237 / 0.3048**3, 0.0),
    "ppg": ("density", 0.45359237 / 0.003785411784, 0.0),
    # pressure gradient (base: Pa/m)
    "Pa/m": ("pressure_gradient", 1.0, 0.0),
    "kPa/m": ("pressure_gradient", 1e3, 0.0),
    "psi/ft": ("pressure_gradient", 6894.757293 / 0.3048, 0.0),
    # velocity (base: m/s)
    "m/s": ("velocity", 1.0, 0.0),
    "cm/s": ("velocity", 0.01, 0.0),
    "ft/s": ("velocity", 0.3048, 0.0),
    "m/d": ("velocity", 1 / 86400, 0.0),
    "ft/d": ("velocity", 0.3048 / 86400, 0.0),
    # time (base: s), year = 365.25 days
    "s": ("time", 1.0, 0.0),
    "min": ("time", 60.0, 0.0),
    "hr": ("time", 3600.0, 0.0),
    "d": ("time", 86400.0, 0.0),
    "yr": ("time", 365.25 * 86400, 0.0),
    # mass (base: kg)
    "kg": ("mass", 1.0, 0.0),
    "g": ("mass", 1e-3, 0.0),
    "lbm": ("mass", 0.45359237, 0.0),
    # surface / interfacial tension (base: N/m)
    "N/m": ("surface_tension", 1.0, 0.0),
    "mN/m": ("surface_tension", 1e-3, 0.0),
    "dyne/cm": ("surface_tension", 1e-3, 0.0),
    # angle (base: rad)
    "rad": ("angle", 1.0, 0.0),
    "deg": ("angle", math.pi / 180, 0.0),
    # fraction, for porosity and saturation (base: fraction)
    "frac": ("fraction", 1.0, 0.0),
    "%": ("fraction", 0.01, 0.0),
    # gas formation volume factor Bg (base: rb/scf)
    "rb/scf": ("gas_fvf", 1.0, 0.0),
    "rb/Mscf": ("gas_fvf", 1e-3, 0.0),
    "ft3/scf": ("gas_fvf", 0.3048**3 / 0.158987294928, 0.0),
    # gas-oil ratio (base: scf/STB)
    "scf/STB": ("gor", 1.0, 0.0),
    "Mscf/STB": ("gor", 1e3, 0.0),
    "sm3/sm3": ("gor", 0.158987294928 / 0.3048**3, 0.0),
}


# convert unit types
def convert(value, from_unit, to_unit, delta=False):
    # validate that units exist
    for unit in (from_unit, to_unit):
        if unit not in CONVERSION_FACTORS:
            raise ValueError(f"Unknown unit '{unit}'")

    # retrieve and unpack conversion factors
    dim_from, scale_from, offset_from = CONVERSION_FACTORS[from_unit]
    dim_to, scale_to, offset_to = CONVERSION_FACTORS[to_unit]

    # validate that from and to dimensions are the same
    if dim_from != dim_to:
        raise ValueError(
            f"Cannot convert {from_unit} ({dim_from}) to {to_unit} ({dim_to})"
        )

    # delta values will not be correct with traditional offsets
    if delta:
        offset_from = 0.0
        offset_to = 0.0

    # convert input value to base unit and convert base unit to target unit
    base = value * scale_from + offset_from
    return (base - offset_to) / scale_to


# return a list of unit symbols belonging to a dimension
def units_for(dimension):
    units = []
    for symbol, (dim, _scale, _offset) in CONVERSION_FACTORS.items():
        if dim == dimension:
            units.append(symbol)
    if not units:
        raise ValueError(f"Unknown dimension '{dimension}'")
    return units


def all_dimensions():
    # Return a sorted list of every dimension in CONVERSION_FACTORS.
    dimensions = []
    for dim, _scale, _offset in CONVERSION_FACTORS.values():
        if dim not in dimensions:
            dimensions.append(dim)
    return sorted(dimensions)
