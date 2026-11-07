#!/usr/bin/env python3
"""Build a Fritzing sketch (.fzz): power header J1 -> 330 ohm resistor R1 -> red LED D1.
The resistor and the 5 mm LED are core parts. The 2-pin power header is a small custom part that this
script writes into the .fzz file (one .fzp file and four SVG files). Standard library only.
This example shows how a custom part is made. For core parts only, see build_fzz_battery_led.py.
Run (Windows):
    set FRITZING_PARTS=C:/Program Files/Fritzing/fritzing-parts
    python build_fzz_header_led.py header_led.fzz
Tested with Fritzing 1.0.x on Windows 11. Not tested elsewhere.
"""
import re, sys, zipfile, os, math
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

PARTS = os.environ["FRITZING_PARTS"]
BB_SCALE = 1.25
out_path = sys.argv[1]
NAME = os.path.splitext(os.path.basename(out_path))[0]

def load_holes():
    t = open(PARTS + "/svg/core/breadboard/breadboard2.svg", encoding="utf-8").read()
    holes = {}
    for m in re.finditer(r'<g id="(pin\d+[A-Z])">(.*?)</g>', t, re.S):
        c = re.search(r'<circle[^>]*cx="([-\d.]+)"[^>]*cy="([-\d.]+)"', m.group(2))
        holes[m.group(1)] = (float(c.group(1)), float(c.group(2)))
    return holes
HOLES = load_holes()
def hole(name):
    x, y = HOLES["pin" + name]; return (x * BB_SCALE, y * BB_SCALE)

class Inst:
    def __init__(s, mod, path, title, layer, kind):
        s.mod, s.path, s.title, s.layer, s.kind = mod, path, title, layer, kind
        s.mi = None; s.props = []; s.legs = {}; s.z = 2.5
        s.conns = {}; s.sconns = {}; s.pconns = {}
        s.pos = (0.0, 0.0); s.sch_pos = (0.0, 0.0); s.pcb_pos = (0.0, 0.0)
        s.sch_tf = None; s.pcb_tf = None; s.layer_pcb = None
insts = []
def add(i):
    i.mi = 1000 + 17 * len(insts); insts.append(i); return i
def _lk(d, a, ca, b, cb):
    getattr(a, d).setdefault(ca, []).append((b, cb)); getattr(b, d).setdefault(cb, []).append((a, ca))
def link(a, ca, b, cb): _lk("conns", a, ca, b, cb)
def slink(a, ca, b, cb): _lk("sconns", a, ca, b, cb)
def plink(a, ca, b, cb): _lk("pconns", a, ca, b, cb)

# ---------------------------------------------------------------- breadboard
bb = add(Inst("Breadboard-RSR03MB102-ModuleID", "breadboard2.fzp", "Breadboard1", "breadboardbreadboard", "bb"))
bb.z = 1.5
bbroot = ET.parse(PARTS + "/core/breadboard2.fzp").getroot()
bus_members = [[m.get("connectorId") for m in b.iter("nodeMember")] for b in bbroot.iter("bus")]
def plug(part, cid, hname): link(part, cid, bb, "pin" + hname)

J1_MOD = "custom_pwr2_100mil"
j1 = add(Inst(J1_MOD, "part.%s.fzp" % J1_MOD, "J1", "breadboard", "part"))
h = hole("3E"); j1.pos = (h[0] - 0.9 * 5, h[1] - 0.9 * 47)
plug(j1, "connector0", "3E"); plug(j1, "connector1", "4E")          # +5V, GND

def resistor(title, value, left, right):
    r = add(Inst("ResistorModuleID", "resistor.fzp", title, "breadboard", "part"))
    r.props = [("tolerance", "±5%"), ("resistance", value), ("pin spacing", "400 mil"), ("power", "0.25W")]
    hl, hr = hole(left), hole(right)
    r.pos = ((hl[0] + hr[0]) / 2 - 19.3127, hl[1] - 4.5405)
    r.legs = {"connector0": (2.619, 4.5405, -2.2095, 0), "connector1": (36.0063, 4.5405, 2.2095, 0)}
    plug(r, "connector0", left); plug(r, "connector1", right); return r
r1 = resistor("R1", "330", "8D", "13D")

LED_MOD = "LED-genedb611bf8177f41ac9c325217070f0c62ColorLEDModuleID"
d1 = add(Inst(LED_MOD, "LED-generic-5mm_6852162_005.fzp", "D1", "breadboard", "part"))
d1.props = [("color", "Red (633nm)"), ("current", "0.030A")]
hc = hole("12G")                                   # cathode = connector0 (left leg); anode = connector1 on 13G
LEG_L = 30.5172
d1.legs = {"connector0": (5.6583, 36.5085, 0, LEG_L), "connector1": (14.661, 36.5085, 0, LEG_L)}
d1.pos = (hc[0] - 5.6583, hc[1] - 36.5085 - LEG_L)
plug(d1, "connector0", "12G"); plug(d1, "connector1", "13G")
assert abs((d1.pos[0] + 14.661) - hole("13G")[0]) < 0.2, "LED leg pitch must equal hole pitch"

def wire(name, color, a, b):
    w = add(Inst("WireModuleID", "wire.fzp", name, "breadboardWire", "wire"))
    w.color, w.a, w.b, w.z = color, a, b, 3.5
    link(w, "connector0", bb, "pin" + a); link(w, "connector1", bb, "pin" + b); return w
wires = [wire("Wire +5V", "#cc1414", "3C", "8C"),
         wire("Wire LED anode", "#ef6100", "13B", "13H"),
         wire("Wire GND", "#404040", "4C", "12H")]

# ---------------------------------------------------------------- breadboard netlist check
parent = {}
def find(a):
    parent.setdefault(a, a)
    while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
    return a
def union(a, b): parent[find(a)] = find(b)
for m in bus_members:
    for x in m[1:]: union(("bb", m[0]), ("bb", x))
for w in wires: union((w.title, "connector0"), (w.title, "connector1"))
for i in insts:
    for cid, others in i.conns.items():
        for (o, oc) in others:
            union(("bb", cid) if i is bb else (i.title, cid), ("bb", oc) if o is bb else (o.title, oc))
pinref = {"J1.1 +5V": (j1, "connector0"), "J1.2 GND": (j1, "connector1"), "R1.1": (r1, "connector0"), "R1.2": (r1, "connector1"),
          "D1 cathode": (d1, "connector0"), "D1 anode": (d1, "connector1")}
expected = {"+5V": ["J1.1 +5V", "R1.1"], "LED_A": ["R1.2", "D1 anode"], "GND": ["J1.2 GND", "D1 cathode"]}
want = sorted(sorted(v) for v in expected.values())
def netcheck(label, finder):
    nets = {}
    for lab, (p, c) in pinref.items(): nets.setdefault(finder((p.title, c)), []).append(lab)
    got = sorted(sorted(v) for v in nets.values())
    print(label, "PASS" if got == want else "FAIL")
    if got != want:
        for g in got: print("  got ", g)
        for w_ in want: print("  want", w_)
        sys.exit(1)
netcheck("BREADBOARD NETLIST CHECK:", find)

# ---------------------------------------------------------------- custom part files (J1)
def fzp(mod, title, desc, label, conns, img):
    cs = ""
    for cid, nm, d in conns:
        cs += ('<connector id="%s" name="%s" type="male"><description>%s</description><views>'
               '<breadboardView><p svgId="%spin" layer="breadboard"/></breadboardView>'
               '<schematicView><p svgId="%spin" terminalId="%sterminal" layer="schematic"/></schematicView>'
               '<pcbView><p svgId="%spad" layer="copper0"/><p svgId="%spad" layer="copper1"/></pcbView></views></connector>\n'
               % (cid, escape(nm), escape(d), cid, cid, cid, cid, cid))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<module fritzingVersion="1.0.8" moduleId="%s">\n<version>1</version>\n'
            '<author>fritzing skill example</author>\n<title>%s</title>\n<label>%s</label>\n<date>2026-11-07</date>\n'
            '<tags><tag>custom</tag></tags>\n<properties><property name="family">Power header</property></properties>\n'
            '<description>%s</description>\n<views>\n'
            '<iconView><layers image="icon/%s_icon.svg"><layer layerId="icon"/></layers></iconView>\n'
            '<breadboardView><layers image="breadboard/%s_breadboard.svg"><layer layerId="breadboard"/></layers></breadboardView>\n'
            '<schematicView><layers image="schematic/%s_schematic.svg"><layer layerId="schematic"/></layers></schematicView>\n'
            '<pcbView><layers image="pcb/%s_pcb.svg"><layer layerId="copper1"/><layer layerId="silkscreen"/><layer layerId="copper0"/></layers></pcbView>\n'
            '</views>\n<connectors>\n%s</connectors>\n<buses/>\n</module>\n' % (mod, escape(title), label, escape(desc), img, img, img, img, cs))

def make_sch(W, H, box, pins, title_lines):
    x0, y0, x1, y1 = box
    s = ('<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="%.2fin" height="%.2fin" viewBox="0 0 %d %d">\n<g id="schematic">\n' % (W / 100, H / 100, W, H))
    s += '<rect x="%d" y="%d" width="%d" height="%d" fill="#ffffff" stroke="#000000" stroke-width="1"/>\n' % (x0, y0, x1 - x0, y1 - y0)
    term = {}
    for cid, lab, pos in pins:                      # pins on the right side only
        term[cid] = (W, pos)
        s += '<line id="%spin" x1="%d" y1="%d" x2="%d" y2="%d" stroke="#000000" stroke-width="1" stroke-linecap="round"/>\n' % (cid, x1, pos, W, pos)
        s += '<rect id="%sterminal" x="%.3f" y="%.3f" width="0.001" height="0.001" fill="none"/>\n' % (cid, W, pos)
        s += '<text x="%d" y="%d" text-anchor="end" font-family="Arial" font-size="7" fill="#000000">%s</text>\n' % (x1 - 3, pos + 2.5, escape(lab))
    for k, ln in enumerate(title_lines):
        s += '<text x="%d" y="%d" text-anchor="middle" font-family="Arial" font-size="7" fill="#333333">%s</text>\n' % ((x0 + x1) / 2 - 8, 56 + 9 * k, escape(ln))
    return s + '</g>\n</svg>\n', term

J1_BB = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="0.2in" height="0.5in" viewBox="0 0 20 50">
<g id="breadboard">
 <g stroke="#b5b5b5" stroke-width="1.6" stroke-linecap="round"><line x1="5" y1="20" x2="5" y2="47"/><line x1="15" y1="20" x2="15" y2="47"/></g>
 <rect x="1" y="4" width="18" height="16" rx="1.5" fill="#2e6b3a" stroke="#1d4526" stroke-width="0.6"/>
 <text x="2.5" y="14" font-size="4.5" font-family="Arial" fill="#ffffff">+5V GND</text>
 <rect id="connector0pin" x="3" y="45" width="4" height="4" fill="none"/><rect id="connector1pin" x="13" y="45" width="4" height="4" fill="none"/>
</g></svg>
'''
J1_PCB = ('<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="0.2in" height="0.1in" viewBox="0 0 200 100">\n'
          '<g id="silkscreen"><rect x="3" y="3" width="194" height="94" fill="none" stroke="#ffffff" stroke-width="8"/></g>\n'
          '<g id="copper1"><g id="copper0">\n'
          '<circle id="connector0pad" cx="50" cy="50" r="27.5" fill="none" stroke="#F7BD13" stroke-width="20"/>\n'
          '<circle id="connector1pad" cx="150" cy="50" r="27.5" fill="none" stroke="#F7BD13" stroke-width="20"/>\n</g></g>\n</svg>\n')
files = {}
files["part.%s.fzp" % J1_MOD] = fzp(J1_MOD, "Power header 2-pin (+5V, GND)", "2-pin 0.1 in header; pin 1 is +5V, pin 2 is GND. Made by the fritzing skill example script.",
                                    "J", [("connector0", "+5V", "Supply"), ("connector1", "GND", "Ground")], J1_MOD)
files["svg.breadboard.%s_breadboard.svg" % J1_MOD] = J1_BB
files["svg.icon.%s_icon.svg" % J1_MOD] = '<?xml version="1.0"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="0.5in" height="0.5in" viewBox="0 0 50 50"><rect x="2" y="2" width="46" height="46" fill="#ddd" stroke="#333"/><text x="8" y="28" font-size="9" font-family="Arial">J1</text></svg>\n'
J1_SVG, J1_TERM = make_sch(80, 60, (10, 10, 60, 50), [("connector0", "+5V", 20), ("connector1", "GND", 40)], ["Power", "header"])
files["svg.schematic.%s_schematic.svg" % J1_MOD] = J1_SVG
files["svg.pcb.%s_pcb.svg" % J1_MOD] = J1_PCB

# ---------------------------------------------------------------- schematic
def info_from_file(path):
    s = open(path, encoding="utf-8").read()
    root = re.search(r"<svg.*?>", s, re.S).group(0)
    def dim(k):
        m = re.search(r'\b%s=[\'"]([\d.]+)(in|px)?' % k, root)
        return float(m.group(1)) / (1 if m.group(2) == "in" else 72.0)
    w_in, h_in = dim("width"), dim("height")
    vb = [float(v) for v in re.search(r'viewBox=[\'"]([^\'"]+)', root).group(1).split()]
    terms = {}
    for m in re.finditer(r"<[^>]*id=['\"](connector\d+)terminal['\"][^>]*>", s):
        e = m.group(0)
        if "<rect" in e or "x=" in e:
            g = lambda k: float(re.search(r"\b%s=['\"]([-\d.]+)" % k, e).group(1))
            terms[m.group(1)] = (g("x") + g("width") / 2, g("y") + g("height") / 2)
    return dict(w_in=w_in, h_in=h_in, upi=vb[2] / w_in, terms=terms)
SCH_CORE = PARTS + "/svg/core/schematic/"
INFO = {"j1": dict(w_in=0.8, h_in=0.6, upi=100.0, terms=J1_TERM), "res": info_from_file(SCH_CORE + "resistor.svg"),
        # led.svg: terminals are <g id=connectorNterminal><rect/></g>, read by hand; Illustrator px = 72 dpi
        "led": dict(w_in=13.68 / 72, h_in=22.031 / 72, upi=72.0, terms={"connector0": (9.9005, 21.8165), "connector1": (9.9005, 0.2165)})}
def place_s(inst, key, cid, target):
    inf = INFO[key]; k = 90.0 / inf["upi"]
    inst.sinfo = inf
    u, v = inf["terms"][cid][0] * k, inf["terms"][cid][1] * k
    inst.sch_pos = (target[0] - u, target[1] - v)
def T(inst, cid):
    inf = inst.sinfo; k = 90.0 / inf["upi"]
    return (round(inst.sch_pos[0] + inf["terms"][cid][0] * k, 3), round(inst.sch_pos[1] + inf["terms"][cid][1] * k, 3))
place_s(j1, "j1", "connector0", (120.0, 70.0))
place_s(r1, "res", "connector0", (190.0, 70.0))
place_s(d1, "led", "connector1", (290.0, 70.0))
swires = []; sends = []
def swire(pts):
    for a, b in zip(pts[:-1], pts[1:]):
        w = add(Inst("WireModuleID", "wire.fzp", "Schematic wire %d" % (len(swires) + 1), "schematicTrace", "swire"))
        w.a, w.b = a, b; swires.append(w)
        sends.append((a, "w", w, "connector0")); sends.append((b, "w", w, "connector1"))
swire([T(j1, "connector0"), T(r1, "connector0")])
swire([T(r1, "connector1"), T(d1, "connector1")])
yg = T(d1, "connector0")[1] + 22
swire([T(d1, "connector0"), (T(d1, "connector0")[0], yg), (T(j1, "connector1")[0], yg), T(j1, "connector1")])
for inst in (j1, r1, d1):
    for c in ("connector0", "connector1"): sends.append((T(inst, c), "p", inst, c))
groups = {}
for xy, kind, inst, cid in sends: groups.setdefault((round(xy[0], 1), round(xy[1], 1)), []).append((kind, inst, cid))
for mem in groups.values():
    for a in range(len(mem)):
        for b in range(a + 1, len(mem)):
            if mem[a][0] == "p" and mem[b][0] == "p": continue
            slink(mem[a][1], mem[a][2], mem[b][1], mem[b][2])
for w in swires:
    for c in ("connector0", "connector1"): assert c in w.sconns, (w.title, c)
sp = {}
def sfind(a):
    sp.setdefault(a, a)
    while sp[a] != a: sp[a] = sp[sp[a]]; a = sp[a]
    return a
for i in insts:
    for cid, others in i.sconns.items():
        for (o, oc) in others: sp[sfind((i.title, cid))] = sfind((o.title, oc))
for w in swires: sp[sfind((w.title, "connector0"))] = sfind((w.title, "connector1"))
netcheck("SCHEMATIC NETLIST CHECK:", sfind)

# ---------------------------------------------------------------- PCB (mm relative to origin px (150,150); px = 90 dpi)
MM = 90.0 / 25.4
PCB_OX, PCB_OY = 150.0, 150.0
PCB_INFO = {"j1": dict(k=0.09, w=18.0, h=9.0, pads={"connector0": (50, 50), "connector1": (150, 50)}, r=0.9525),
            "res": dict(k=0.09, w=42.75, h=7.74, pads={"connector0": (37.5, 43), "connector1": (437.5, 43)}, r=0.9525),
            "led": dict(k=1.0, w=21.969, h=21.969, pads={"connector0": (10.9845, 4.433), "connector1": (10.9845, 13.292)}, r=0.80)}
def _ploc(inst, cid):
    inf = inst.pinfo; u, v = inf["pads"][cid][0] * inf["k"], inf["pads"][cid][1] * inf["k"]; w, h = inf["w"], inf["h"]
    if inst.prot is None: return (u, v)
    return (-v + (w / 2 + h / 2), u + (h / 2 - w / 2))            # 90 degrees clockwise (only rotation used here)
def PP(inst, cid):
    lx, ly = _ploc(inst, cid); return ((inst.pcb_pos[0] + lx - PCB_OX) / MM, (inst.pcb_pos[1] + ly - PCB_OY) / MM)
def pplace(inst, key, rot, cid, target_mm):
    inst.pinfo = PCB_INFO[key]; inst.prot = rot
    w, h = inst.pinfo["w"], inst.pinfo["h"]
    inst.pcb_tf = None if rot is None else (0, 1, -1, 0, w / 2 + h / 2, h / 2 - w / 2)
    inst.pcb_pos = (0.0, 0.0); lx, ly = _ploc(inst, cid)
    inst.pcb_pos = (PCB_OX + target_mm[0] * MM - lx, PCB_OY + target_mm[1] * MM - ly)
BOARD = dict(x0=0.0, y0=0.0, w=40.0, h=26.0)
board = add(Inst("TwoLayerRectanglePCBModuleID", "rectangle_pcb_two_layers.fzp", "PCB1", "board", "board"))
board.pcb_pos = (PCB_OX, PCB_OY)
board.props = [("layers", "2"), ("width", "%s" % BOARD["w"]), ("height", "%s" % BOARD["h"])]
pplace(j1, "j1", "cw", "connector0", (6.0, 14.0))        # rotated: +5V pad above GND pad
pplace(r1, "res", None, "connector0", (14.0, 14.0))
pplace(d1, "led", "cw", "connector1", (30.0, 14.0))      # rotated: anode left, cathode right
pwires = []; pends = []
TOP = "copper1trace"
def ptrace(layer, pts):
    for a, b in zip(pts[:-1], pts[1:]):
        w = add(Inst("WireModuleID", "wire.fzp", "Trace %d" % (len(pwires) + 1), layer, "pwire"))
        w.a, w.b = a, b; w.layer_pcb = layer; pwires.append(w)
        pends.append((a, w, "connector0")); pends.append((b, w, "connector1"))
ptrace(TOP, [PP(j1, "connector0"), PP(r1, "connector0")])
ptrace(TOP, [PP(r1, "connector1"), PP(d1, "connector1")])
g = PP(j1, "connector1"); c = PP(d1, "connector0")
ptrace(TOP, [g, (g[0], 20.0), (c[0], 20.0), c])
for inst in (j1, r1, d1):
    for cc in ("connector0", "connector1"): pends.append((PP(inst, cc), inst, cc))
pgroups = {}
for xy, inst, cid in pends: pgroups.setdefault((round(xy[0], 2), round(xy[1], 2)), []).append((inst, cid))
for mem in pgroups.values():
    for a in range(len(mem)):
        for b in range(a + 1, len(mem)):
            if mem[a][0].kind != "pwire" and mem[b][0].kind != "pwire": continue
            plink(mem[a][0], mem[a][1], mem[b][0], mem[b][1])
for w in pwires:
    for cc in ("connector0", "connector1"): assert cc in w.pconns, (w.title, cc, w.a, w.b)
pp_ = {}
def pfind(a):
    pp_.setdefault(a, a)
    while pp_[a] != a: pp_[a] = pp_[pp_[a]]; a = pp_[a]
    return a
for i in insts:
    for cid, others in i.pconns.items():
        for (o, oc) in others: pp_[pfind((i.title, cid))] = pfind((o.title, oc))
for w in pwires: pp_[pfind((w.title, "connector0"))] = pfind((w.title, "connector1"))
netcheck("PCB NETLIST CHECK:", pfind)

def seg_pt(p, q, c):
    px_, py_ = q[0] - p[0], q[1] - p[1]; L = px_ * px_ + py_ * py_
    u = 0 if L == 0 else max(0, min(1, ((c[0] - p[0]) * px_ + (c[1] - p[1]) * py_) / L))
    return math.hypot(p[0] + u * px_ - c[0], p[1] + u * py_ - c[1])
HW, CLR = 24 * 0.0254 / 2, 0.254
worst = 9e9; bad = []
for w in pwires:
    nw = pfind((w.title, "connector0"))
    for inst in (j1, r1, d1):
        for cid in inst.pinfo["pads"]:
            if pfind((inst.title, cid)) == nw: continue
            d = seg_pt(w.a, w.b, PP(inst, cid)) - inst.pinfo["r"] - HW
            worst = min(worst, d)
            if d < CLR: bad.append(("trace %s vs pad %s.%s" % (w.title, inst.title, cid), round(d, 3)))
    for q in (w.a, w.b):
        if not (HW <= q[0] <= BOARD["w"] - HW and HW <= q[1] <= BOARD["h"] - HW): bad.append(("trace %s outside board" % w.title, q))
print("PCB CLEARANCE CHECK (needs >= %.3f mm):" % CLR, "PASS, smallest gap %.2f mm" % worst if not bad else "FAIL")
for b in bad: print("  ", b)
if bad: sys.exit(1)

# ---------------------------------------------------------------- .fz
def conn_xml(i, ind):
    out = ""
    for cid, others in i.conns.items():
        out += '%s<connector connectorId="%s" layer="%s">\n' % (ind, cid, i.layer)
        if cid in i.legs:
            gx, gy, lx, ly = i.legs[cid]
            out += ('%s  <geometry x="%s" y="%s"/>\n%s  <leg>\n%s    <point x="0" y="0"/>\n%s    <bezier/>\n%s    <point x="%s" y="%s"/>\n%s    <bezier/>\n%s  </leg>\n'
                    % (ind, gx, gy, ind, ind, ind, ind, lx, ly, ind, ind))
        else:
            out += '%s  <geometry x="0" y="0"/>\n' % ind
        out += '%s  <connects>\n' % ind
        for (o, oc) in others: out += '%s    <connect connectorId="%s" modelIndex="%d" layer="%s"/>\n' % (ind, oc, o.mi, o.layer)
        out += '%s  </connects>\n%s</connector>\n' % (ind, ind)
    return out
def pconn_xml(i, ind):
    out = ""
    for cid, others in i.pconns.items():
        out += '%s<connector connectorId="%s" layer="copper0">\n%s  <geometry x="0" y="0"/>\n%s  <connects>\n' % (ind, cid, ind, ind)
        for (o, oc) in others: out += '%s    <connect connectorId="%s" modelIndex="%d" layer="%s"/>\n' % (ind, oc, o.mi, o.layer_pcb)
        out += '%s  </connects>\n%s</connector>\n' % (ind, ind)
    return out
def sconn_xml(i, ind):
    out = ""
    for cid, others in i.sconns.items():
        out += '%s<connector connectorId="%s" layer="schematic">\n%s  <geometry x="0" y="0"/>\n%s  <connects>\n' % (ind, cid, ind, ind)
        for (o, oc) in others: out += '%s    <connect connectorId="%s" modelIndex="%d" layer="%s"/>\n' % (ind, oc, o.mi, "schematicTrace" if o.kind == "swire" else "schematic")
        out += '%s  </connects>\n%s</connector>\n' % (ind, ind)
    return out
def tfx(t):
    return "" if not t else ('\n            <transform m11="%s" m12="%s" m13="0" m21="%s" m22="%s" m23="0" m31="%.4f" m32="%.4f" m33="1"/>\n          ' % t)
fz = ['<?xml version="1.0" encoding="UTF-8"?>\n<module fritzingVersion="1.0.8">\n',
      '  <boards>\n    <board moduleId="TwoLayerRectanglePCBModuleID" title="Rectangular PCB - Resizable" instance="PCB1" width="%.4fcm" height="%.4fcm"/>\n  </boards>\n' % (BOARD["w"] / 10, BOARD["h"] / 10),
      '  <views>\n    <view name="breadboardView" backgroundColor="#ffffff" gridSize="0.1in" showGrid="1" alignToGrid="1" viewFromBelow="0" colorWiresByLength="0"/>\n'
      '    <view name="schematicView" backgroundColor="#ffffff" gridSize="0.1in" showGrid="1" alignToGrid="1" viewFromBelow="0"/>\n'
      '    <view name="pcbView" backgroundColor="#333333" gridSize="0.05in" showGrid="1" alignToGrid="1" viewFromBelow="0"/>\n  </views>\n  <instances>\n']
for i in insts:
    fz.append('    <instance moduleIdRef="%s" modelIndex="%d" path="%s">\n' % (i.mod, i.mi, i.path))
    for k, v in i.props: fz.append('      <property name="%s" value="%s"/>\n' % (k, escape(v)))
    fz.append('      <title>%s</title>\n      <views>\n' % escape(i.title))
    if i.kind == "board":
        fz.append('        <pcbView layer="board">\n          <geometry z="1.5" x="%.4f" y="%.4f"/>\n        </pcbView>\n' % i.pcb_pos)
    elif i.kind == "pwire":
        a = (PCB_OX + i.a[0] * MM, PCB_OY + i.a[1] * MM); b = (PCB_OX + i.b[0] * MM, PCB_OY + i.b[1] * MM)
        fz.append('        <pcbView layer="%s">\n          <geometry z="9.5" x="%.4f" y="%.4f" x1="0" y1="0" x2="%.4f" y2="%.4f" wireFlags="4"/>\n'
                  '          <wireExtras mils="24" color="#f2c600" opacity="1" banded="0"/>\n          <connectors>\n' % (i.layer_pcb, a[0], a[1], b[0] - a[0], b[1] - a[1]))
        for cid in ("connector0", "connector1"):
            fz.append('            <connector connectorId="%s" layer="%s">\n              <geometry x="0" y="0"/>\n              <connects>\n' % (cid, i.layer_pcb))
            for (o, oc) in i.pconns[cid]:
                fz.append('                <connect connectorId="%s" modelIndex="%d" layer="%s"/>\n' % (oc, o.mi, o.layer_pcb if o.kind == "pwire" else "copper1"))
            fz.append('              </connects>\n            </connector>\n')
        fz.append('          </connectors>\n        </pcbView>\n')
    elif i.kind == "swire":
        a, b = i.a, i.b
        fz.append('        <schematicView layer="schematicTrace">\n          <geometry z="4.5" x="%.4f" y="%.4f" x1="0" y1="0" x2="%.4f" y2="%.4f" wireFlags="128"/>\n'
                  '          <wireExtras mils="9.7222" color="#404040" opacity="1" banded="0"/>\n          <connectors>\n' % (a[0], a[1], b[0] - a[0], b[1] - a[1]))
        for cid in ("connector0", "connector1"):
            fz.append('            <connector connectorId="%s" layer="schematicTrace">\n              <geometry x="0" y="0"/>\n              <connects>\n' % cid)
            for (o, oc) in i.sconns[cid]:
                fz.append('                <connect connectorId="%s" modelIndex="%d" layer="%s"/>\n' % (oc, o.mi, "schematicTrace" if o.kind == "swire" else "schematic"))
            fz.append('              </connects>\n            </connector>\n')
        fz.append('          </connectors>\n        </schematicView>\n')
    elif i.kind == "wire":
        a = hole(i.a); b = hole(i.b)
        fz.append('        <breadboardView layer="breadboardWire">\n          <geometry z="%s" x="%.4f" y="%.4f" x1="0" y1="0" x2="%.4f" y2="%.4f" wireFlags="64"/>\n'
                  '          <wireExtras mils="22.2222" color="%s" opacity="1" banded="0"/>\n          <connectors>\n' % (i.z, a[0], a[1], b[0] - a[0], b[1] - a[1], i.color))
        for cid in ("connector0", "connector1"):
            fz.append('            <connector connectorId="%s" layer="breadboardWire">\n              <geometry x="0" y="0"/>\n              <connects>\n' % cid)
            for (o, oc) in i.conns[cid]: fz.append('                <connect connectorId="%s" modelIndex="%d" layer="%s"/>\n' % (oc, o.mi, o.layer))
            fz.append('              </connects>\n            </connector>\n')
        fz.append('          </connectors>\n        </breadboardView>\n')
    else:
        fz.append('        <breadboardView layer="%s">\n          <geometry z="%s" x="%.4f" y="%.4f"/>\n          <connectors>\n%s          </connectors>\n        </breadboardView>\n'
                  % (i.layer, i.z, i.pos[0], i.pos[1], conn_xml(i, "            ")))
        if i.kind == "part":
            st = None  # no schematic rotation in this test
            fz.append('        <schematicView layer="schematic">\n          <geometry z="2.5" x="%.4f" y="%.4f"></geometry>\n          <connectors>\n%s          </connectors>\n        </schematicView>\n'
                      % (i.sch_pos[0], i.sch_pos[1], sconn_xml(i, "            ")))
            fz.append('        <pcbView layer="copper0">\n          <geometry z="5.5" x="%.4f" y="%.4f">%s</geometry>\n          <connectors>\n%s          </connectors>\n        </pcbView>\n'
                      % (i.pcb_pos[0], i.pcb_pos[1], tfx(i.pcb_tf), pconn_xml(i, "            ")))
    fz.append('      </views>\n    </instance>\n')
fz.append('  </instances>\n</module>\n')
files[NAME + ".fz"] = "".join(fz)
with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
    for n, c in files.items(): z.writestr(n, c)
print("wrote", out_path, "with", len(files), "files;", len(insts), "instances")
