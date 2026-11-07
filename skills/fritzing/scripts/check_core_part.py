#!/usr/bin/env python3
"""Check that a Fritzing core part has all the image files its .fzp file names.

A part whose image file is missing from your Fritzing install draws blank in that view.
Run this before you use a part in a generated sketch.

Usage:
    python check_core_part.py <fritzing-parts folder> <part.fzp file name or part of the title> [...]
    python check_core_part.py <fritzing-parts folder> --all [search text]

Examples (Windows):
    python check_core_part.py "C:\\Program Files\\Fritzing\\fritzing-parts" resistor.fzp
    python check_core_part.py "C:\\Program Files\\Fritzing\\fritzing-parts" --all battery

For each part it prints OK or MISSING, the number of connectors, and the module id.
Exit code 0 means every checked part is complete. Exit code 1 means at least one image is missing.
Standard library only.
"""
import glob, os, sys
import xml.etree.ElementTree as ET


def check(parts, fzp_path):
    """Return (title, module_id, connector_count, [missing image paths])."""
    root = ET.parse(fzp_path).getroot()
    missing = []
    for layers in root.findall(".//views/*/layers"):
        image = layers.get("image")
        if image and not os.path.exists(os.path.join(parts, "svg", "core", image)):
            missing.append(image)
    return (root.findtext("title") or "", root.get("moduleId"),
            len(root.findall(".//connectors/connector")), missing)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    sys.stdout.reconfigure(errors="replace")     # part titles can hold characters a Windows console cannot show
    parts = sys.argv[1]
    core = os.path.join(parts, "core")
    if not os.path.isdir(core):
        print("No 'core' folder in", parts)
        return 2
    if sys.argv[2] == "--all":
        needle = sys.argv[3].lower() if len(sys.argv) > 3 else ""
        files = sorted(glob.glob(os.path.join(core, "*.fzp")))
    else:
        needle = ""
        files = []
        for name in sys.argv[2:]:
            exact = os.path.join(core, name)
            if os.path.exists(exact):
                files.append(exact)
            else:
                files += [f for f in sorted(glob.glob(os.path.join(core, "*.fzp"))) if name.lower() in os.path.basename(f).lower()]
    bad = 0
    for f in files:
        try:
            title, module_id, n, missing = check(parts, f)
        except ET.ParseError:
            continue
        if needle and needle not in (title + " " + os.path.basename(f)).lower():
            continue
        print("%-8s %2d connectors  %s | %s | %s" % ("MISSING" if missing else "OK", n, os.path.basename(f), title, module_id))
        for m in missing:
            print("           missing image:", m)
        bad += bool(missing)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
