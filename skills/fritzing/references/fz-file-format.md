# Fritzing 1.0.8 file format: what the generator relies on

Source: the files inside Fritzing 1.0.8 and 1.0.x (the parts library and the sample sketches in `sketches/core`), read in November 2026. Nothing here comes from Fritzing's own documentation. Items marked **(not checked)** are guesses.

## The .fzz file

- A `.fzz` file is a zip file.
- It holds one `.fz` XML file (the sketch) and, for each custom part, flat files:
  - `part.<name>.fzp`
  - `svg.breadboard.<name>.svg`, `svg.schematic.<name>.svg`, `svg.pcb.<name>.svg`, `svg.icon.<name>.svg`
- Inside the `.fzp` file, each view names its image as `breadboard/<name>.svg`, `schematic/<name>.svg`, and so on. The prefix `svg.<view>.` in the zip name maps to the folder `<view>/`.
- Core parts are not in the zip. The `.fz` file names them by `moduleIdRef`.

## The .fz file

```xml
<module fritzingVersion="1.0.8">
  <boards><board moduleId="TwoLayerRectanglePCBModuleID" title="Rectangular PCB - Resizable" instance="PCB1" width="5.8cm" height="5.35cm"/></boards>
  <views> ...three <view> elements: breadboardView, schematicView, pcbView... </views>
  <instances>
    <instance moduleIdRef="ResistorModuleID" modelIndex="1034" path="resistor.fzp">
      <property name="resistance" value="330"/>
      <title>R1</title>
      <views>
        <breadboardView layer="breadboard"><geometry z="2.5" x="100" y="50"/><connectors> ... </connectors></breadboardView>
        <schematicView layer="schematic"> ... </schematicView>
        <pcbView layer="copper0"> ... </pcbView>
      </views>
    </instance>
  </instances>
</module>
```

- `modelIndex` is a unique integer per instance.
- `geometry x,y` is the top-left corner of the part's SVG, in scene pixels (1/90 inch).
- Each connection is written twice: in the connector of item A, and in the connector of item B.

```xml
<connector connectorId="connector0" layer="breadboard">
  <geometry x="0" y="0"/>
  <connects><connect connectorId="pin18D" modelIndex="1000" layer="breadboardbreadboard"/></connects>
</connector>
```

### Layer names for each view

| View | Part connector `layer` | Breadboard hole or wire `layer` | Notes |
| --- | --- | --- | --- |
| Breadboard | `breadboard` | hole `breadboardbreadboard`, wire `breadboardWire` | wire geometry has `wireFlags="64"`; the wire has only a `breadboardView` |
| Schematic | `schematic` | wire `schematicTrace` | `wireFlags="128"`, `mils="9.7222"`, colour `#404040` |
| PCB top trace | part `copper0` (lists wires of both layers) | wire `copper1trace` | `wireFlags="4"`, `mils="24"`, colour `#f2c600`; the wire's connect to a part uses `copper1` |
| PCB bottom trace | part `copper0` | wire `copper0trace`, add `bottom="true"` | `wireFlags="4"`, `mils="24"`, colour `#f28a00`; the wire's connect to a part uses `copper0` |

- A wire is a straight segment. `geometry x,y` is its start. `x2,y2` is the offset to its end. `connector0` is the start. `connector1` is the end.
- To make a bend, use two wires. Write the connection between them on both. Where three or more ends meet at one point, link each pair.
- Do not link a top trace to a bottom trace.

### PCB board

```xml
<instance moduleIdRef="TwoLayerRectanglePCBModuleID" modelIndex="..." path="rectangle_pcb_two_layers.fzp">
  <property name="layers" value="2"/><property name="width" value="58"/><property name="height" value="53.5"/>
  <title>PCB1</title>
  <views><pcbView layer="board"><geometry z="1.5" x="..." y="..."/></pcbView></views>
</instance>
```

- `width` and `height` are in millimetres. The board has only a `pcbView`.

## Scales

- A scene unit is 1/90 inch. 1 mm is 3.5433 scene units.
- An SVG with `in` units and a `viewBox`: scene units per SVG unit = `90 × width_in / viewBox_width`.
- An SVG with plain `px` units from Illustrator (such as the core `breadboard2.svg`, the core diode schematic, and many parts from other makers): 72 dpi. One SVG unit is 1.25 scene units. The 0.1 inch pitch is 7.2 SVG units.
- Core footprints use 0.001 inch units: pad centres 400 mil apart are 400 units apart.

## Breadboard `breadboard2.svg` (the full-size breadboard)

- `moduleIdRef="Breadboard-RSR03MB102-ModuleID"`, `path="breadboard2.fzp"`. 63 columns.
- Hole names: `pin<column><row>`. Rows A to E are the lower half, F to J the upper half. Row A is at SVG y 115.2 and row J is at y 36.0, 7.2 units apart. Row E to row F is 21.6 units (a 0.3 inch gap).
- Column `c` is at SVG x `10.92 + 7.2 × (c − 1)`.
- Power rails: W and X below (y 144.0 and 136.8), Y and Z above (y 14.4 and 7.2). A rail hole exists for column `c` except when `c` is 8, 14, 20, 26, 32, 38, and so on (every sixth).
- The `.fzp` file lists the buses: one per column half (`bus<c>A-E`, `bus<c>F-J`) and one per rail. Read them to find which holes share a net.
- A part with two rows of pins 0.8 inch apart fits across the gap on rows that are 8 positions apart: C and I, or D and J.

## Placing parts by one pin

- A part with no rotation: `position = target − pin_offset`, where `pin_offset` is the pin's position inside the SVG, in scene units.
- Rotation is stored as a `<transform>` inside `<geometry>`. The part turns about its centre. With `w` and `h` the part's size in scene units:
  - 90 degrees clockwise: `m11=0 m12=1 m21=-1 m22=0 m31=w/2+h/2 m32=h/2-w/2`. A pin at `(u,v)` moves to `(-v + w/2+h/2, u + h/2-w/2)`.
  - 90 degrees counter-clockwise: `m11=0 m12=-1 m21=1 m22=0 m31=w/2-h/2 m32=w/2+h/2`. A pin at `(u,v)` moves to `(v + w/2-h/2, -u + w/2+h/2)`.
  - 180 degrees: `m11=-1 m22=-1 m31=w m32=h`.
- Add `m13="0" m23="0" m33="1"`.

## Parts with bendable legs (core resistor and diode)

- The breadboard connector has a `<geometry x y>` and a `<leg>` with two points. Copy these values for the 400 mil resistor: connector0 at `(2.619, 4.5405)` with leg end `-2.2095`; connector1 at `(36.0063, 4.5405)` with leg end `+2.2095`. Size 38.6 by 8.7 scene units; centre the part between the two holes.
- 1N4001 (`moduleIdRef="3254CBFC44diode"`, `path="diode_1N4001_300mil.fzp"`): connector0 is the cathode (stripe) at `(2.6175, 4.5375)` leg `-1.30875`; connector1 is the anode at `(34.7312, 4.5375)` leg `+1.30875`. Legs end about 34.7 scene units apart; the holes are 36 apart (0.4 inch). Fritzing accepts this.
- Resistor `resistance` is written `330`, `10k`, `1M`.
- PCB footprints: resistor `axial_lay_2_400mil_pcb.svg`, pads 400 mil apart. Diode `DO-41_diode_2_300mil_pcb.svg`, pads 300 mil apart, connector0 (cathode) is the square pad.

## Custom part files

- `.fzp`: `<module moduleId="...">`, `<title>`, `<views>` with an `image` for each of iconView, breadboardView, schematicView, pcbView, and `<connectors>`. Each connector has `<p svgId="connectorNpin" layer="breadboard"/>`, `<p svgId="connectorNpin" terminalId="connectorNterminal" layer="schematic"/>`, and two `<p svgId="connectorNpad" layer="copper0|copper1"/>` entries for the PCB.
- Breadboard SVG: put everything inside `<g id="breadboard">`. A male pin is a `<rect id="connectorNpin">` at the leg tip. Fritzing connects it to a breadboard hole when the centres meet.
- Schematic SVG: put everything inside `<g id="schematic">`. Each pin is a line `connectorNpin`. The terminal is a tiny `<rect id="connectorNterminal">` at the pin's outer end. Fritzing takes the terminal's centre as the point where a wire ends.
- PCB SVG: `<g id="silkscreen">`, and `<g id="copper1"><g id="copper0">` holding `<circle id="connectorNpad" r="27.5" stroke-width="20" fill="none" stroke="#F7BD13">` (0.075 inch pads).
- Internal links inside a part (two GND pins that are one net) go in `<buses><bus id="..."><nodeMember connectorId="..."/>...</bus></buses>`.

## Checks the generator runs on itself

- Netlist: union-find over holes (with the breadboard buses), wires, and part buses. The member list of each net must match the net list exactly.
- Schematic and PCB: the same union-find, using only the wires of that view.
- PCB clearance: distance from each trace segment to each pad and each other-net trace on the same layer, minus half the trace width (24 mil) must be at least 0.254 mm (10 mil, Fritzing's default keepout).

## Headless export

- `Fritzing -svg <folder>` loads every `.fzz` in the folder and writes `<name>_breadboard.svg`, `_schematic.svg`, `_pcb.svg`.
- It does not draw ratsnest lines. It does not run the design rule check.
- Log lines `svgidlayer fail ...` appear for core parts too. They did not stop a part from drawing.
- Log lines `missing expected terminal ...` mean a schematic SVG lacks a `connectorNterminal` element.

## Not checked

- Checked on 2026-11-07 on Windows 11 with Fritzing 1.0.x, by the author of this repository: `examples/header_led.fzz` and `examples/battery_led.fzz` open in the Fritzing window, each view shows "Routing completed", and the PCB design rule check finds no problem. Treat any other sketch as unchecked until a person opens it in Fritzing.
- Autorouting.
- macOS and Linux.
