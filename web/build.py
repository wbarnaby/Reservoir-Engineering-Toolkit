"""Build the browser version of RTK into dist/.

Run from the project root:   python web/build.py

Runs textual-wasm, then fixes Windows path separators in the output.
textual-wasm 0.2.1 records file paths with str(), which on Windows gives
backslashes (core\\units.py). The browser's file system only understands
forward slashes, so those files land as oddly named files instead of in
subfolders and every subpackage import fails. Once textual-wasm fixes
this upstream, the fix step finds nothing to change and does no harm.
"""

import json
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

from packaging.version import Version

ENTRY = "rtk.ui.app:ToolkitApp"
PACKAGE = "rtk"
OUTPUT = Path("dist")
TITLE = "Reservoir Toolkit"
REQUIREMENTS = [
    "numpy",
    "textual-plotext",
    "textual-fspicker",
    "textual-image",
    "matplotlib",
    "pillow",
]

# xterm.js draws box-drawing characters with the font by default, and
# most fonts leave gaps between rows. Its WebGL renderer draws them as
# shapes instead. Version must match the xterm 6.0.0 textual-wasm loads.
WEBGL_ADDON_URL = "https://cdn.jsdelivr.net/npm/@xterm/addon-webgl@0.19.0/lib/addon-webgl.mjs"
WEBGL_ANCHOR = "  terminal.open(container);\n"
WEBGL_MARKER = "// web/build.py: WebGL renderer"
WEBGL_PATCH = f"""{WEBGL_ANCHOR}  {WEBGL_MARKER}
  import("{WEBGL_ADDON_URL}")
    .then(({{ WebglAddon }}) => {{
      const webgl = new WebglAddon();
      webgl.onContextLoss(() => webgl.dispose());
      terminal.loadAddon(webgl);
    }})
    .catch((error) => console.warn("WebGL unavailable, using default", error));
"""

# textual-wasm pins each dependency to the version installed on this
# machine, so a newer local version ships to the browser. These are
# versions known to crash there: (package, first bad version, reason).
BROWSER_INCOMPATIBLE = [
    ("platformdirs", "4.14.0", "imports os.geteuid, which Pyodide lacks"),
]


def check_environment():
    """Stop before building if an installed version will crash in Pyodide."""
    problems = []
    for package, first_bad, reason in BROWSER_INCOMPATIBLE:
        installed = version(package)
        if Version(installed) >= Version(first_bad):
            problems.append(
                f"{package} {installed} {reason}.\n"
                f'  fix: python -m pip install "{package}<{first_bad}"'
            )
    if problems:
        print("Build stopped:\n" + "\n".join(problems))
        sys.exit(1)


def build():
    """Run textual-wasm build; stop the script if it fails."""
    command = [sys.executable, "-m", "textual_wasm", "build", ENTRY, PACKAGE]
    command += ["-o", str(OUTPUT), "--title", TITLE]
    for requirement in REQUIREMENTS:
        command += ["-r", requirement]
    subprocess.run(command, check=True)


def fix_separators(sources_file):
    """Rewrite backslashes in bundled file paths. Returns how many changed."""
    data = json.loads(sources_file.read_text(encoding="utf-8"))
    changed = 0
    fixed = {}
    for package, files in data.items():
        fixed[package] = {}
        for name, contents in files.items():
            if "\\" in name:
                changed += 1
            fixed[package][name.replace("\\", "/")] = contents
    sources_file.write_text(json.dumps(fixed), encoding="utf-8")
    return changed


def enable_webgl(main_file):
    """Insert the WebGL renderer right after the terminal is opened."""
    script = main_file.read_text(encoding="utf-8")
    if WEBGL_MARKER in script:
        return
    if WEBGL_ANCHOR not in script:
        sys.exit(
            f"Could not find where to enable WebGL in {main_file}; "
            "textual-wasm's page code changed. Check WEBGL_ANCHOR."
        )
    script = script.replace(WEBGL_ANCHOR, WEBGL_PATCH, 1)
    main_file.write_text(script, encoding="utf-8")


if __name__ == "__main__":
    check_environment()
    build()
    count = fix_separators(OUTPUT / "sources.json")
    print(f"fixed {count} Windows paths in {OUTPUT / 'sources.json'}")
    enable_webgl(OUTPUT / "main.mjs")
    print("enabled WebGL renderer")
