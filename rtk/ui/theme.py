"""Retro phosphor-green theme shared by the whole UI."""

from textual.theme import Theme

GREEN = "#33ff33"
DIM_GREEN = "#1a8a1a"
AMBER = "#ffb000"
RED = "#ff4040"

PHOSPHOR = Theme(
    name="phosphor",
    primary=GREEN,
    secondary=DIM_GREEN,
    accent=AMBER,
    warning=AMBER,
    error=RED,
    success=GREEN,
    foreground=GREEN,
    background="#000000",
    surface="#030a03",
    panel="#0a1f0a",
    dark=True,
)

BANNER = r"""
 ____  _____ _  __
|  _ \|_   _| |/ /
| |_) | | | | ' /    Reservoir Toolkit
|  _ <  | | | . \    v0.1
|_| \_\ |_| |_|\_\
"""
