#!/usr/bin/env python3
"""Load a Fritzing sketch headlessly and export its three views as SVG files.

Usage:
    python3 fritzing_export.py <Fritzing executable or AppImage> <sketch.fzz> [output folder]

What it does:
    - copies the sketch into a fresh folder (Fritzing exports every .fzz in the folder it is given)
    - runs:  <Fritzing> -svg <folder>
    - prints the files written, and any log lines that look like load errors

The output files are <name>_breadboard.svg, <name>_schematic.svg and <name>_pcb.svg.
A part that Fritzing could not draw is missing from the SVG file. Look for it there.
On Linux the script sets QT_QPA_PLATFORM=xcb when it is not set (the AppImage has no wayland plugin).
Standard library only. Tested with Fritzing 1.0.x on Windows 11 (November 2026). The Linux and macOS lines are not tested.
"""
import os, shutil, subprocess, sys, tempfile

def main():
    if len(sys.argv) < 3:
        print(__doc__); return 2
    exe, sketch = sys.argv[1], os.path.abspath(sys.argv[2])
    out = os.path.abspath(sys.argv[3]) if len(sys.argv) > 3 else tempfile.mkdtemp(prefix="fritzing_export_")
    os.makedirs(out, exist_ok=True)
    if os.listdir(out):
        print("Output folder is not empty: %s. Use a new empty folder." % out); return 2
    shutil.copy(sketch, out)
    env = dict(os.environ)
    if sys.platform.startswith("linux"):
        env.setdefault("QT_QPA_PLATFORM", "xcb")
    r = subprocess.run([exe, "-svg", out], env=env, capture_output=True, text=True, timeout=300)
    log = (r.stdout or "") + (r.stderr or "")
    noise = ("removing folder", "svgidlayer fail", "Bin location", "registering font", "missing expected terminal")
    for line in log.splitlines():
        low = line.lower()
        if any(n in line for n in noise):
            continue
        if any(k in low for k in ("error", "fail", "cannot", "could not", "invalid")):
            print("LOG:", line[:300])
    missing = sum(1 for l in log.splitlines() if "missing expected terminal" in l)
    if missing:
        print("LOG: %d 'missing expected terminal' lines (a schematic SVG lacks a connectorNterminal element)" % missing)
    print("exit code:", r.returncode)
    for f in sorted(os.listdir(out)):
        print("%-60s %8d bytes" % (f, os.path.getsize(os.path.join(out, f))))
    return 0

if __name__ == "__main__":
    sys.exit(main())
