"""Oilfield constants shared across the toolkit.

Standard conditions: 14.696 psia and 60 degF (519.67 degR).
Change them here only; every derived constant follows.
"""

P_SC = 14.696  # standard pressure, psia
T_SC = 519.67  # standard temperature, degR (60 degF)
R_GAS = 10.7316  # gas constant, psia*ft3/(lb-mol*degR)

FT3_PER_BBL = 42 * 231 / 1728  # 42 gal/bbl, 231 in3/gal, 1728 in3/ft3
FT3_PER_ACRE_FT = 43560.0

BG_FT3 = P_SC / T_SC  # Bg = BG_FT3 * zT/p [ft3/scf]
BG_RB = BG_FT3 / FT3_PER_BBL
