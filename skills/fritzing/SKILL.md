---
name: fritzing
description: Build, check, and edit Fritzing sketches (.fzz and .fz files) with code. Makes the breadboard, schematic, and PCB views from one net list, adds custom parts (.fzp and SVG files), and proves the file loads by exporting SVG files and by opening it in the real Fritzing window. Use this skill whenever the user mentions Fritzing, a .fzz, .fz, .fzp, or .fzpz file, or asks to wire up, lay out, or draw a circuit on a breadboard, as a schematic, or as a PCB in Fritzing. Also use it when a Fritzing part draws blank, is missing a pin, or when a generated sketch will not open.
---

# Fritzing sketches from code

## What this skill gives you

- A method to turn a net list (a list of which pins connect together) into one `.fzz` file with three views: breadboard, schematic, and PCB.
- Two worked generators. Copy one and change the parts and nets.
  - `scripts/build_fzz_battery_led.py` uses only parts that ship with Fritzing: a battery holder, a push button, a resistor, and an LED. Start here.
  - `scripts/build_fzz_header_led.py` shows how to write a custom part (a `.fzp` file and four SVG files) into the sketch.
- A part checker, `scripts/check_core_part.py`. It tells you if a core part has all of its image files.
- A headless checker, `scripts/fritzing_export.py`. It loads a sketch in Fritzing and writes the three views as SVG files.
- A window checker, `scripts/fritzing_gui_shot.ps1` (Windows). It takes a screenshot of the Fritzing window, so you can read the status bar.
- The file-format facts in `references/fz-file-format.md`. Read it before you write any `.fz` XML.

## What was tested

- Tested: Windows 11 with Fritzing 1.0.x, installed in `C:\Program Files\Fritzing`. Both example sketches in `examples/` build, export to SVG, open in the Fritzing window with "Routing completed" in all three views, and pass the PCB design rule check. This was checked on 2026-11-07.
- Not tested: macOS, Linux, Fritzing versions other than 1.0.x, autorouting, and circuits with more than a few parts.

## Rules for Claude

- Do not guess a part's pins. Read its `.fzp` file and list its connectors. Compare them with the net list before you build.
- Check every core part with `scripts/check_core_part.py` before you use it. A part whose image files are missing draws blank.
- Do not download a file without the user's yes, unless they gave you the link. Say the file name, the source, and the size. Put each download in its own new empty folder. Do not run anything from it.
- Do not say a sketch "works" because the generator ran. Fritzing must load it, and each view must show every part. Say what you did not check.
- The last check is a person's: they open the file in the Fritzing window and say what they see. Fix the generator, not the file by hand.
- Write the full name of each file and part every time.

## Workflow

### Find Fritzing and its parts library

- Windows (tested): Fritzing is at `C:\Program Files\Fritzing\Fritzing.exe`. The parts library is `C:\Program Files\Fritzing\fritzing-parts`. The sample sketches are in `C:\Program Files\Fritzing\sketches\core`. Read them to copy the exact XML that Fritzing writes.
- Linux (not tested for this repository): a Fritzing AppImage can be unpacked with its `--appimage-extract` option into a new empty folder. The parts library is then `squashfs-root/fritzing-parts`.
- macOS (not tested): the parts library is inside the Fritzing application. Look for a folder named `fritzing-parts`.
- The scripts read the parts library from the user's own Fritzing install. Set the environment variable `FRITZING_PARTS` to that folder.

### Check the parts

- List the parts you need and look each one up: `python scripts\check_core_part.py "C:\Program Files\Fritzing\fritzing-parts" <part name>`. Add `--all battery` to list every core part with "battery" in its title.
- It prints `OK` or `MISSING` for each part, the number of connectors, and the module id. A part that says `MISSING` draws blank in the view whose image file is gone.
- Example from the 2026-11-07 test install: the core part `screw_terminal_2_100mil` lacks its schematic and PCB images, and the core part `Battery block 9V` lacks its PCB footprint (`jumper_2_100mil_pcb.svg`). The core part `4 x AAA Battery Mount` is complete.
- If no core part fits, draw one. `scripts/build_fzz_header_led.py` has an example: one `.fzp` file and four SVG files.
- If a part from another source lacks a pin, copy the part, give it a new `moduleId`, and add the connector. Add the pin to the breadboard SVG, the schematic SVG, and the PCB SVG.

### Build

- Copy `scripts/build_fzz_battery_led.py`. Change the parts, the hole names, the coordinates, and the nets.
- Write the nets as a list of members. The script checks its own wiring against that list in all three views, and checks the PCB trace clearance.
- Choose the breadboard layout first, then the schematic, then the PCB. Use `references/fz-file-format.md` for hole names, scales, layer names, and transforms.
- For a part with bendable legs, copy the leg XML from a Fritzing sample sketch. Do not guess it (see "Things that went wrong").

### Check

- Run `python scripts\fritzing_export.py "C:\Program Files\Fritzing\Fritzing.exe" <sketch.fzz> <new empty folder>`. Read each line it prints. It writes `<name>_breadboard.svg`, `<name>_schematic.svg`, and `<name>_pcb.svg`.
- Look at the SVG files as pictures. One way on Windows: write an HTML page that holds an `<img>` of the SVG file, then run `msedge.exe --headless --window-size=W,H --screenshot=<out.png> file:///<page.html>`. Read the PNG. The export shows copper only, not the silkscreen outlines.
- For each part, check three things: it is drawn, its pins sit on the holes, and each wire end touches a pin.
- The SVG export does not draw ratsnest lines (the thin lines that show unrouted connections). So it cannot prove that Fritzing registered the connections. Open the sketch in the Fritzing window.
- Windows, in the real Fritzing window:
  - Start `Fritzing.exe "<sketch.fzz>"` with `Start-Process`. Wait 25 seconds.
  - Run `scripts\fritzing_gui_shot.ps1 -Out <png>` for the current view, then with `-Keys "^3"` for the schematic view and `-Keys "^4"` for the PCB view. Read each PNG.
  - Look for "Routing completed" in the status bar of each view, and for green connector dots.
  - For the design rule check, run the script with `-Keys "^+d" -Wait 5` in the PCB view. A clean sketch shows "Your sketch is ready for production: there are no connectors or traces that overlap or are too close together."
  - Close the dialog and run `Stop-Process -Name Fritzing`.

### Report

- Say what you checked and how. Say what you did not check. Name the files you wrote with full paths.
- Tell the user how to open the file: in Fritzing, `File` → `Open`.

## Things that went wrong before

- **A core part's image files are missing from the install.** The part draws blank. Run `scripts/check_core_part.py` before you use a part.
- **A part draws blank.** Fritzing 1.0.x draws nothing when a breadboard SVG has no `<g id="breadboard">` group. Wrap the whole content in that group.
- **A wire end looks right but is not connected.** The `.fz` file must list each connection in both items. Write one `link()` call per pair and emit both sides.
- **A part with bendable legs (LED, resistor, diode, battery holder).** In the `.fz` file, the connector `<geometry x y>` is the body-side end of the leg line in the SVG, times the scale. The `<leg>` second point is the tip, relative to that point. For the 5 mm LED the tip offset is `(0, 30.5172)`. For the battery holder it is `(6.25, 0)`. Fritzing's own sample sketches show this.
- **Wrong scale.** A scene unit is 1/90 inch. An SVG with `in` units scales by `90 × width_in / viewBox_width`. An Illustrator SVG with plain `px` units counts as 72 dpi, so multiply by 1.25.
- **A schematic terminal is not found.** Some schematic SVG files hide the terminal inside a `<g>` element, and some have no terminal at all. Read the SVG file and take the outer end of the pin line. The LED schematic `led.svg` has its terminals at (9.9005, 21.8165) for the cathode and (9.9005, 0.2165) for the anode, at 72 dpi.
- **A rotated part lands off its holes.** Use the transform formulas in the reference file. Place a part by the position of one pin, not by its corner.
- **Traces cross.** Put the two traces on different layers. Through-hole pads join both layers, so no via is needed.
- **Python.** The scripts use only the standard library. They need no installed package.

## Files in this skill

- `SKILL.md`: this file.
- `references/fz-file-format.md`: the `.fzz` and `.fz` format, with XML examples, scales, layer names, and formulas.
- `scripts/build_fzz_battery_led.py`: generator with core parts only (battery holder, push button, resistor, LED).
- `scripts/build_fzz_header_led.py`: generator that also writes a custom part (a 2-pin header).
- `scripts/check_core_part.py`: checks that a core part has all its image files.
- `scripts/fritzing_export.py`: the headless load-and-export check.
- `scripts/fritzing_gui_shot.ps1`: activates the Fritzing window, can send keys, and saves a screenshot (Windows).
- `examples/battery_led.fzz` and `examples/header_led.fzz`: the sketches that the two generators wrote, with a picture of each view.
