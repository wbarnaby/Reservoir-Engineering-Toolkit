"""Every tool the console can open.

Format:  "command": (title, module path, panel class name)
Panels are imported only when opened (lazy import).
"""

TOOLS = {
    "units": ("Unit Converter", "rtk.ui.tools.units_panel", "UnitsPanel"),
    "pz": ("Gas p/z Material Balance", "rtk.ui.tools.pz_panel", "PzPanel"),
}
