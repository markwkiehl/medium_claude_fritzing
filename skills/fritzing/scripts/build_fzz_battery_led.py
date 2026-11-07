#!/usr/bin/env python3
"""Build a Fritzing sketch (.fzz) of a battery, a push button, a resistor, and an LED.

Every part is a core part that ships with Fritzing. No custom part and no download is needed.
The sketch has three views: breadboard, schematic, and PCB.

Circuit: battery + -> push button -> 330 ohm resistor -> red LED -> battery -
Parts:   BT1 "4 x AAA Battery Mount"   SW1 "Pushbutton" (2 legs)   R1 330 ohm resistor   D1 red 5 mm LED

Run (Windows, standard library only):
    set FRITZING_PARTS=C:\\Program Files\\Fritzing\\fritzing-parts
    python build_fzz_battery_led.py battery_led.fzz

Before it writes the file, the script checks its own wiring in all three views against the net list
below, and checks the PCB traces for clearance. A "PASS" from the script does not prove that Fritzing
loads the file. Open the file in Fritzing (see SKILL.md) for that.

Tested with Fritzing 1.0.x on Windows 11. Not tested elsewhere.
"""
import math, os, re, sys, zipfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

PARTS = os.environ["FRITZING_PARTS"]          # the fritzing-parts folder of your Fritzing install
BB_SCALE = 1.25                               # breadboard2.svg is 72 dpi; the sketch scene is 90 dpi
out_path = sys.argv[1]
NAME = os.path.splitext(os.path.basename(out_path))[0]


def load_holes():
    """Hole centres of the full-size breadboard, in breadboard2.svg units: {'pin4D': (x, y), ...}"""
    text = open(PARTS + "/svg/core/breadboard/breadboard2.svg", encoding="utf-8").read()
    holes = {}
    for m in re.finditer(r'<g id="(pin\d+[A-Z])">(.*?)</g>', text, re.S):
        c = re.search(r'<circle[^>]*cx="([-\d.]+)"[^>]*cy="([-\d.]+)"', m.group(2))
        holes[m.group(1)] = (float(c.group(1)), float(c.group(2)))
    return holes


HOLES = load_holes()


def hole(name):
    x, y = HOLES["pin" + name]
    return (x * BB_SCALE, y * BB_SCALE)


class Inst:
    """One item of the sketch: a part, a wire, a trace, the breadboard, or the board."""
    def __init__(s, mod, path, title, layer, kind):
        s.mod, s.path, s.title, s.layer, s.kind = mod, path, title, layer, kind
        s.props = []; s.legs = {}; s.z = 2.5; s.mi = None
        s.conns = {}; s.sconns = {}; s.pconns = {}          # breadboard, schematic, PCB links
        s.pos = (0.0, 0.0); s.sch_pos = (0.0, 0.0); s.pcb_pos = (0.0, 0.0)
        s.sch_tf = None; s.pcb_tf = None; s.layer_pcb = None


insts = []


def add(i):
    i.mi = 1000 + 17 * len(insts)
    insts.append(i)
    return i


def _link(table, a, ca, b, cb):
    """Write a connection on both sides. Fritzing needs both."""
    getattr(a, table).setdefault(ca, []).append((b, cb))
    getattr(b, table).setdefault(cb, []).append((a, ca))


def link(a, ca, b, cb): _link("conns", a, ca, b, cb)
def slink(a, ca, b, cb): _link("sconns", a, ca, b, cb)
def plink(a, ca, b, cb): _link("pconns", a, ca, b, cb)


# ---------------------------------------------------------------- breadboard view
bb = add(Inst("Breadboard-RSR03MB102-ModuleID", "breadboard2.fzp", "Breadboard1", "breadboardbreadboard", "bb"))
bb.z = 1.5
bbroot = ET.parse(PARTS + "/core/breadboard2.fzp").getroot()
bus_members = [[m.get("connectorId") for m in b.iter("nodeMember")] for b in bbroot.iter("bus")]


def plug(part, cid, hole_name):
    link(part, cid, bb, "pin" + hole_name)


# Battery holder. Its two leads are legs on its right edge. connector0 is "-" (black), connector1 is "+" (red).
# Leg geometry rule (read from Fritzing's own sample sketches): the connector <geometry> is the body-side end of the
# leg line in the SVG, times the scale. The <leg> second point is the tip, relative to that point.
bt = add(Inst("c7c8e292b3beec531de0c51f2576d329", "4 x AAA Battery Mount.fzp", "BT1", "breadboard", "part"))
bt.pos = (-200.0, 60.0)
LEG0 = 6.25                                    # default leg length: 5 svg units * 1.25
bt.legs = {"connector0": (153.1 * 1.25, 102.505 * 1.25, LEG0, 0), "connector1": (153.1 * 1.25, 25.906 * 1.25, LEG0, 0)}


def leg_tip(part, cid):
    gx, gy, lx, ly = part.legs[cid]
    return (part.pos[0] + gx + lx, part.pos[1] + gy + ly)


# Push button, 2 legs, no bendable legs. Pin centres in svg units: connector1 left, connector0 right.
SW_S = 90 * 0.328 / 23.662                     # scene units per svg unit (width .328 in, viewBox 23.662)
SW_C = {"connector1": (1.834, 3.563), "connector0": (21.914, 3.563)}
sw = add(Inst("20A9BBEE34_ST-2leadbutton-horizon", "pushbutton_2_horizontal.fzp", "SW1", "breadboard", "part"))
h1, h2 = hole("3C"), hole("6C")
sw.pos = ((h1[0] + h2[0]) / 2 - (SW_C["connector1"][0] + SW_C["connector0"][0]) / 2 * SW_S, h1[1] - SW_C["connector1"][1] * SW_S)
plug(sw, "connector1", "3C"); plug(sw, "connector0", "6C")
for cid, hname in (("connector1", "3C"), ("connector0", "6C")):          # pin centre must be near the hole centre
    px, py = sw.pos[0] + SW_C[cid][0] * SW_S, sw.pos[1] + SW_C[cid][1] * SW_S
    hx, hy = hole(hname)
    assert abs(px - hx) < 2.0 and abs(py - hy) < 2.0, (cid, px, py, hx, hy)


def resistor(title, value, left, right):
    r = add(Inst("ResistorModuleID", "resistor.fzp", title, "breadboard", "part"))
    r.props = [("tolerance", "\u00b15%"), ("resistance", value), ("pin spacing", "400 mil"), ("power", "0.25W")]
    hl, hr = hole(left), hole(right)
    r.pos = ((hl[0] + hr[0]) / 2 - 19.3127, hl[1] - 4.5405)
    r.legs = {"connector0": (2.619, 4.5405, -2.2095, 0), "connector1": (36.0063, 4.5405, 2.2095, 0)}
    plug(r, "connector0", left); plug(r, "connector1", right)
    return r


r1 = resistor("R1", "330", "6B", "10B")

# Red 5 mm LED with bendable legs, pointing down. connector0 is the cathode (left leg), connector1 the anode.
d1 = add(Inst("LED-genedb611bf8177f41ac9c325217070f0c62ColorLEDModuleID", "LED-generic-5mm_6852162_005.fzp", "D1", "breadboard", "part"))
d1.props = [("color", "Red (633nm)"), ("current", "0.030A")]
LEG_L = 30.5172
d1.legs = {"connector0": (5.6583, 36.5085, 0, LEG_L), "connector1": (14.661, 36.5085, 0, LEG_L)}
hc = hole("9G")
d1.pos = (hc[0] - 5.6583, hc[1] - 36.5085 - LEG_L)
plug(d1, "connector0", "9G"); plug(d1, "connector1", "10G")
assert abs((d1.pos[0] + 14.661) - hole("10G")[0]) < 0.2, "LED leg pitch must equal hole pitch"


def wire(name, color, a, b):
    """A jumper wire. a and b are a hole name such as '3E', or a tuple (part, connector id) for a battery lead."""
    w = add(Inst("WireModuleID", "wire.fzp", name, "breadboardWire", "wire"))
    w.color, w.z = color, 3.5
    w.ends = []
    for cid, end in (("connector0", a), ("connector1", b)):
        if isinstance(end, tuple):
            part, pcid = end
            w.ends.append(leg_tip(part, pcid)); link(w, cid, part, pcid)
        else:
            w.ends.append(hole(end)); link(w, cid, bb, "pin" + end)
    return w


wires = [wire("Wire BT1 +", "#cc1414", (bt, "connector1"), "3E"),
         wire("Wire BT1 -", "#404040", (bt, "connector0"), "5A"),
         wire("Wire LED anode", "#ef6100", "10D", "10H"),
         wire("Wire LED cathode", "#47cc79", "9H", "5D")]

# ---------------------------------------------------------------- net list and the checks
pinref = {"BT1 +": (bt, "connector1"), "BT1 -": (bt, "connector0"),
          "SW1.1": (sw, "connector1"), "SW1.2": (sw, "connector0"),
          "R1.1": (r1, "connector0"), "R1.2": (r1, "connector1"),
          "D1 anode": (d1, "connector1"), "D1 cathode": (d1, "connector0")}
expected = {"BAT_PLUS": ["BT1 +", "SW1.1"], "SW_OUT": ["SW1.2", "R1.1"],
            "LED_A": ["R1.2", "D1 anode"], "GND": ["BT1 -", "D1 cathode"]}
want = sorted(sorted(v) for v in expected.values())


def make_finder():
    parent = {}
    def find(a):
        parent.setdefault(a, a)
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    def union(a, b): parent[find(a)] = find(b)
    return find, union


def netcheck(label, find):
    nets = {}
    for lab, (p, c) in pinref.items():
        nets.setdefault(find((p.title, c)), []).append(lab)
    got = sorted(sorted(v) for v in nets.values())
    print(label, "PASS" if got == want else "FAIL")
    if got != want:
        for g in got: print("  got ", g)
        for w_ in want: print("  want", w_)
        sys.exit(1)


find, union = make_finder()
for m in bus_members:                                       # holes of one breadboard strip are one net
    for x in m[1:]: union(("bb", m[0]), ("bb", x))
for w in wires: union((w.title, "connector0"), (w.title, "connector1"))
for i in insts:
    for cid, others in i.conns.items():
        for (o, oc) in others:
            union(("bb", cid) if i is bb else (i.title, cid), ("bb", oc) if o is bb else (o.title, oc))
netcheck("BREADBOARD NETLIST CHECK:", find)

# ---------------------------------------------------------------- schematic view
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
        g = lambda k: float(re.search(r"\b%s=['\"]([-\d.]+)" % k, e).group(1))
        terms[m.group(1)] = (g("x") + g("width") / 2, g("y") + g("height") / 2)
    return dict(w_in=w_in, h_in=h_in, upi=vb[2] / w_in, terms=terms)


SCH = PARTS + "/svg/core/schematic/"
INFO = {
    "bat": info_from_file(SCH + "dc_powersupply.svg"),
    "res": info_from_file(SCH + "resistor.svg"),
    # pushbutton.svg has no terminal elements and led.svg hides them in <g> elements: read by hand. 72 dpi.
    "sw": dict(w_in=6.616 / 72, h_in=29.495 / 72, upi=72.0, terms={"connector1": (4.741, 0.295), "connector0": (4.741, 29.135)}),
    "led": dict(w_in=13.68 / 72, h_in=22.031 / 72, upi=72.0, terms={"connector0": (9.9005, 21.8165), "connector1": (9.9005, 0.2165)}),
}


def rot_tf(rot, w, h):
    return {None: None, "cw": (0, 1, -1, 0, w / 2 + h / 2, h / 2 - w / 2),
            "ccw": (0, -1, 1, 0, w / 2 - h / 2, w / 2 + h / 2), "180": (-1, 0, 0, -1, w, h)}[rot]


def rot_pt(rot, u, v, w, h):
    """Where a point (u, v) inside a w by h part lands after the part is turned about its centre."""
    if rot is None: return (u, v)
    if rot == "cw": return (-v + w / 2 + h / 2, u + h / 2 - w / 2)
    if rot == "ccw": return (v + w / 2 - h / 2, -u + w / 2 + h / 2)
    return (w - u, h - v)


def sloc(inst, cid):
    inf = inst.sinfo; k = 90.0 / inf["upi"]
    return rot_pt(inst.srot, inf["terms"][cid][0] * k, inf["terms"][cid][1] * k, inf["w_in"] * 90, inf["h_in"] * 90)


def place_s(inst, key, rot, cid, target):
    """Place a part so that its connector cid lands on target (scene units)."""
    inst.sinfo, inst.srot = INFO[key], rot
    inst.sch_tf = rot_tf(rot, inst.sinfo["w_in"] * 90, inst.sinfo["h_in"] * 90)
    inst.sch_pos = (0.0, 0.0)
    lx, ly = sloc(inst, cid)
    inst.sch_pos = (target[0] - lx, target[1] - ly)


def T(inst, cid):
    lx, ly = sloc(inst, cid)
    return (round(inst.sch_pos[0] + lx, 3), round(inst.sch_pos[1] + ly, 3))


Y_TOP = 90.0
place_s(bt, "bat", "cw", "connector1", (80.0, Y_TOP))         # + on top, - below
place_s(sw, "sw", "ccw", "connector1", (120.0, Y_TOP))        # turned flat: connector1 left, connector0 right
place_s(r1, "res", None, "connector0", (200.0, Y_TOP))
place_s(d1, "led", None, "connector1", (300.0, Y_TOP))        # anode on top, cathode below
swires, sends = [], []


def swire(pts):
    for a, b in zip(pts[:-1], pts[1:]):
        w = add(Inst("WireModuleID", "wire.fzp", "Schematic wire %d" % (len(swires) + 1), "schematicTrace", "swire"))
        w.a, w.b = a, b
        swires.append(w)
        sends.append((a, "w", w, "connector0")); sends.append((b, "w", w, "connector1"))


y_back = T(d1, "connector0")[1] + 43.0
swire([T(bt, "connector1"), T(sw, "connector1")])
swire([T(sw, "connector0"), T(r1, "connector0")])
swire([T(r1, "connector1"), T(d1, "connector1")])
swire([T(d1, "connector0"), (T(d1, "connector0")[0], y_back), (T(bt, "connector0")[0], y_back), T(bt, "connector0")])
for inst in (bt, sw, r1, d1):
    for c in ("connector0", "connector1"):
        sends.append((T(inst, c), "p", inst, c))
groups = {}
for xy, kind, inst, cid in sends:
    groups.setdefault((round(xy[0], 1), round(xy[1], 1)), []).append((kind, inst, cid))
for mem in groups.values():                                   # everything at one point is joined; two part pins never are
    for a in range(len(mem)):
        for b in range(a + 1, len(mem)):
            if mem[a][0] == "p" and mem[b][0] == "p": continue
            slink(mem[a][1], mem[a][2], mem[b][1], mem[b][2])
for w in swires:
    for c in ("connector0", "connector1"):
        assert c in w.sconns, (w.title, c)

sfind, sunion = make_finder()
for i in insts:
    for cid, others in i.sconns.items():
        for (o, oc) in others: sunion((i.title, cid), (o.title, oc))
for w in swires: sunion((w.title, "connector0"), (w.title, "connector1"))
netcheck("SCHEMATIC NETLIST CHECK:", sfind)

# ---------------------------------------------------------------- PCB view (design units: mm; one scene unit is 1/90 in)
MM = 90.0 / 25.4
PCB_OX, PCB_OY = 150.0, 150.0                                  # scene position of the board corner
PCB_INFO = {
    "bat": dict(k=1.25, w=193.84, h=179.67, pads={"connector1": (9.35, 18.81), "connector0": (9.35, 54.81)}, r=0.98),
    "sw": dict(k=0.09, w=35.28, h=8.28, pads={"connector0": (46, 46), "connector1": (346, 46)}, r=1.17),
    "res": dict(k=0.09, w=42.75, h=7.74, pads={"connector0": (37.5, 43), "connector1": (437.5, 43)}, r=0.9525),
    "led": dict(k=1.0, w=21.969, h=21.969, pads={"connector0": (10.9845, 4.433), "connector1": (10.9845, 13.292)}, r=0.80),
}


def ploc(inst, cid):
    inf = inst.pinfo
    return rot_pt(inst.prot, inf["pads"][cid][0] * inf["k"], inf["pads"][cid][1] * inf["k"], inf["w"], inf["h"])


def PP(inst, cid):
    """Pad centre in mm, measured from the board corner."""
    lx, ly = ploc(inst, cid)
    return ((inst.pcb_pos[0] + lx - PCB_OX) / MM, (inst.pcb_pos[1] + ly - PCB_OY) / MM)


def pplace(inst, key, rot, cid, target_mm):
    inst.pinfo, inst.prot = PCB_INFO[key], rot
    inst.pcb_tf = rot_tf(rot, inst.pinfo["w"], inst.pinfo["h"])
    inst.pcb_pos = (0.0, 0.0)
    lx, ly = ploc(inst, cid)
    inst.pcb_pos = (PCB_OX + target_mm[0] * MM - lx, PCB_OY + target_mm[1] * MM - ly)


BOARD = dict(w=75.0, h=56.0)                                   # mm
board = add(Inst("TwoLayerRectanglePCBModuleID", "rectangle_pcb_two_layers.fzp", "PCB1", "board", "board"))
board.pcb_pos = (PCB_OX, PCB_OY)
board.props = [("layers", "2"), ("width", "%s" % BOARD["w"]), ("height", "%s" % BOARD["h"])]
pplace(bt, "bat", "180", "connector1", (53.4, 46.0))           # turned 180 degrees: its pads face the other parts
pplace(sw, "sw", "180", "connector1", (61.5, 46.0))
pplace(r1, "res", "ccw", "connector0", (69.12, 36.0))          # standing up: connector0 below, connector1 above
pplace(d1, "led", None, "connector1", (62.0, 25.84))           # cathode (square pad) 2.5 mm above the anode
pwires, pends = [], []
TOP = "copper1trace"


def ptrace(layer, pts):
    for a, b in zip(pts[:-1], pts[1:]):
        w = add(Inst("WireModuleID", "wire.fzp", "Trace %d" % (len(pwires) + 1), layer, "pwire"))
        w.a, w.b, w.layer_pcb = a, b, layer
        pwires.append(w)
        pends.append((a, w, "connector0")); pends.append((b, w, "connector1"))


gnd_x = 57.0
ptrace(TOP, [PP(bt, "connector1"), PP(sw, "connector1")])                                     # battery + -> button
ptrace(TOP, [PP(sw, "connector0"), PP(r1, "connector0")])                                     # button -> resistor
ptrace(TOP, [PP(r1, "connector1"), PP(d1, "connector1")])                                     # resistor -> LED anode
ptrace(TOP, [PP(d1, "connector0"), (gnd_x, PP(d1, "connector0")[1]), (gnd_x, PP(bt, "connector0")[1]), PP(bt, "connector0")])  # LED cathode -> battery -
for inst in (bt, sw, r1, d1):
    for c in ("connector0", "connector1"):
        pends.append((PP(inst, c), inst, c))
pgroups = {}
for xy, inst, cid in pends:
    pgroups.setdefault((round(xy[0], 2), round(xy[1], 2)), []).append((inst, cid))
for mem in pgroups.values():
    for a in range(len(mem)):
        for b in range(a + 1, len(mem)):
            if mem[a][0].kind != "pwire" and mem[b][0].kind != "pwire": continue
            plink(mem[a][0], mem[a][1], mem[b][0], mem[b][1])
for w in pwires:
    for c in ("connector0", "connector1"):
        assert c in w.pconns, (w.title, c, w.a, w.b)

pfind, punion = make_finder()
for i in insts:
    for cid, others in i.pconns.items():
        for (o, oc) in others: punion((i.title, cid), (o.title, oc))
for w in pwires: punion((w.title, "connector0"), (w.title, "connector1"))
netcheck("PCB NETLIST CHECK:", pfind)


def seg_pt(p, q, c):
    dx, dy = q[0] - p[0], q[1] - p[1]
    L = dx * dx + dy * dy
    u = 0 if L == 0 else max(0, min(1, ((c[0] - p[0]) * dx + (c[1] - p[1]) * dy) / L))
    return math.hypot(p[0] + u * dx - c[0], p[1] + u * dy - c[1])


def seg_seg(a, b, c, d):
    def cross(o, p_, q): return (p_[0] - o[0]) * (q[1] - o[1]) - (p_[1] - o[1]) * (q[0] - o[0])
    if cross(a, b, c) * cross(a, b, d) < 0 and cross(c, d, a) * cross(c, d, b) < 0: return 0.0
    return min(seg_pt(a, b, c), seg_pt(a, b, d), seg_pt(c, d, a), seg_pt(c, d, b))


HW, CLR = 24 * 0.0254 / 2, 0.254        # trace half width (24 mil) and Fritzing's default keepout (10 mil), in mm
worst, bad = 9e9, []
for w in pwires:
    nw = pfind((w.title, "connector0"))
    for inst in (bt, sw, r1, d1):
        for cid in inst.pinfo["pads"]:
            if pfind((inst.title, cid)) == nw: continue
            d = seg_pt(w.a, w.b, PP(inst, cid)) - inst.pinfo["r"] - HW
            worst = min(worst, d)
            if d < CLR: bad.append(("trace %s vs pad %s.%s" % (w.title, inst.title, cid), round(d, 3)))
    for q in (w.a, w.b):
        if not (HW <= q[0] <= BOARD["w"] - HW and HW <= q[1] <= BOARD["h"] - HW):
            bad.append(("trace %s outside the board" % w.title, q))
for a in range(len(pwires)):
    for b in range(a + 1, len(pwires)):
        if pfind((pwires[a].title, "connector0")) == pfind((pwires[b].title, "connector0")): continue
        d = seg_seg(pwires[a].a, pwires[a].b, pwires[b].a, pwires[b].b) - 2 * HW
        worst = min(worst, d)
        if d < CLR: bad.append(("trace %s vs trace %s" % (pwires[a].title, pwires[b].title), round(d, 3)))
print("PCB CLEARANCE CHECK (needs >= %.3f mm):" % CLR, "PASS, smallest gap %.2f mm" % worst if not bad else "FAIL")
for b in bad: print("  ", b)
if bad: sys.exit(1)

# ---------------------------------------------------------------- write the .fz file
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
        for (o, oc) in others:
            out += '%s    <connect connectorId="%s" modelIndex="%d" layer="%s"/>\n' % (ind, oc, o.mi, o.layer)
        out += '%s  </connects>\n%s</connector>\n' % (ind, ind)
    return out


def pconn_xml(i, ind):
    out = ""
    for cid, others in i.pconns.items():
        out += '%s<connector connectorId="%s" layer="copper0">\n%s  <geometry x="0" y="0"/>\n%s  <connects>\n' % (ind, cid, ind, ind)
        for (o, oc) in others:
            out += '%s    <connect connectorId="%s" modelIndex="%d" layer="%s"/>\n' % (ind, oc, o.mi, o.layer_pcb)
        out += '%s  </connects>\n%s</connector>\n' % (ind, ind)
    return out


def sconn_xml(i, ind):
    out = ""
    for cid, others in i.sconns.items():
        out += '%s<connector connectorId="%s" layer="schematic">\n%s  <geometry x="0" y="0"/>\n%s  <connects>\n' % (ind, cid, ind, ind)
        for (o, oc) in others:
            out += '%s    <connect connectorId="%s" modelIndex="%d" layer="%s"/>\n' % (ind, oc, o.mi, "schematicTrace" if o.kind == "swire" else "schematic")
        out += '%s  </connects>\n%s</connector>\n' % (ind, ind)
    return out


def tf_xml(t):
    if not t: return ""
    return '\n            <transform m11="%s" m12="%s" m13="0" m21="%s" m22="%s" m23="0" m31="%.4f" m32="%.4f" m33="1"/>\n          ' % t


fz = ['<?xml version="1.0" encoding="UTF-8"?>\n<module fritzingVersion="1.0.8">\n',
      '  <boards>\n    <board moduleId="TwoLayerRectanglePCBModuleID" title="Rectangular PCB - Resizable" instance="PCB1" width="%.4fcm" height="%.4fcm"/>\n  </boards>\n' % (BOARD["w"] / 10, BOARD["h"] / 10),
      '  <views>\n    <view name="breadboardView" backgroundColor="#ffffff" gridSize="0.1in" showGrid="1" alignToGrid="1" viewFromBelow="0" colorWiresByLength="0"/>\n'
      '    <view name="schematicView" backgroundColor="#ffffff" gridSize="0.1in" showGrid="1" alignToGrid="1" viewFromBelow="0"/>\n'
      '    <view name="pcbView" backgroundColor="#333333" gridSize="0.05in" showGrid="1" alignToGrid="1" viewFromBelow="0"/>\n  </views>\n  <instances>\n']
for i in insts:
    fz.append('    <instance moduleIdRef="%s" modelIndex="%d" path="%s">\n' % (i.mod, i.mi, i.path))
    for k, v in i.props:
        fz.append('      <property name="%s" value="%s"/>\n' % (k, escape(v)))
    fz.append('      <title>%s</title>\n      <views>\n' % escape(i.title))
    if i.kind == "board":
        fz.append('        <pcbView layer="board">\n          <geometry z="1.5" x="%.4f" y="%.4f"/>\n        </pcbView>\n' % i.pcb_pos)
    elif i.kind == "pwire":
        a = (PCB_OX + i.a[0] * MM, PCB_OY + i.a[1] * MM); b = (PCB_OX + i.b[0] * MM, PCB_OY + i.b[1] * MM)
        fz.append('        <pcbView layer="%s">\n          <geometry z="9.5" x="%.4f" y="%.4f" x1="0" y1="0" x2="%.4f" y2="%.4f" wireFlags="4"/>\n'
                  '          <wireExtras mils="24" color="#f2c600" opacity="1" banded="0"/>\n          <connectors>\n'
                  % (i.layer_pcb, a[0], a[1], b[0] - a[0], b[1] - a[1]))
        for cid in ("connector0", "connector1"):
            fz.append('            <connector connectorId="%s" layer="%s">\n              <geometry x="0" y="0"/>\n              <connects>\n' % (cid, i.layer_pcb))
            for (o, oc) in i.pconns[cid]:
                fz.append('                <connect connectorId="%s" modelIndex="%d" layer="%s"/>\n' % (oc, o.mi, o.layer_pcb if o.kind == "pwire" else "copper1"))
            fz.append('              </connects>\n            </connector>\n')
        fz.append('          </connectors>\n        </pcbView>\n')
    elif i.kind == "swire":
        a, b = i.a, i.b
        fz.append('        <schematicView layer="schematicTrace">\n          <geometry z="4.5" x="%.4f" y="%.4f" x1="0" y1="0" x2="%.4f" y2="%.4f" wireFlags="128"/>\n'
                  '          <wireExtras mils="9.7222" color="#404040" opacity="1" banded="0"/>\n          <connectors>\n'
                  % (a[0], a[1], b[0] - a[0], b[1] - a[1]))
        for cid in ("connector0", "connector1"):
            fz.append('            <connector connectorId="%s" layer="schematicTrace">\n              <geometry x="0" y="0"/>\n              <connects>\n' % cid)
            for (o, oc) in i.sconns[cid]:
                fz.append('                <connect connectorId="%s" modelIndex="%d" layer="%s"/>\n' % (oc, o.mi, "schematicTrace" if o.kind == "swire" else "schematic"))
            fz.append('              </connects>\n            </connector>\n')
        fz.append('          </connectors>\n        </schematicView>\n')
    elif i.kind == "wire":
        a, b = i.ends
        fz.append('        <breadboardView layer="breadboardWire">\n          <geometry z="%s" x="%.4f" y="%.4f" x1="0" y1="0" x2="%.4f" y2="%.4f" wireFlags="64"/>\n'
                  '          <wireExtras mils="22.2222" color="%s" opacity="1" banded="0"/>\n          <connectors>\n'
                  % (i.z, a[0], a[1], b[0] - a[0], b[1] - a[1], i.color))
        for cid in ("connector0", "connector1"):
            fz.append('            <connector connectorId="%s" layer="breadboardWire">\n              <geometry x="0" y="0"/>\n              <connects>\n' % cid)
            for (o, oc) in i.conns[cid]:
                fz.append('                <connect connectorId="%s" modelIndex="%d" layer="%s"/>\n' % (oc, o.mi, o.layer))
            fz.append('              </connects>\n            </connector>\n')
        fz.append('          </connectors>\n        </breadboardView>\n')
    else:
        fz.append('        <breadboardView layer="%s">\n          <geometry z="%s" x="%.4f" y="%.4f"/>\n          <connectors>\n%s          </connectors>\n        </breadboardView>\n'
                  % (i.layer, i.z, i.pos[0], i.pos[1], conn_xml(i, "            ")))
        if i.kind == "part":
            fz.append('        <schematicView layer="schematic">\n          <geometry z="2.5" x="%.4f" y="%.4f">%s</geometry>\n          <connectors>\n%s          </connectors>\n        </schematicView>\n'
                      % (i.sch_pos[0], i.sch_pos[1], tf_xml(i.sch_tf), sconn_xml(i, "            ")))
            fz.append('        <pcbView layer="copper0">\n          <geometry z="5.5" x="%.4f" y="%.4f">%s</geometry>\n          <connectors>\n%s          </connectors>\n        </pcbView>\n'
                      % (i.pcb_pos[0], i.pcb_pos[1], tf_xml(i.pcb_tf), pconn_xml(i, "            ")))
    fz.append('      </views>\n    </instance>\n')
fz.append('  </instances>\n</module>\n')

with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr(NAME + ".fz", "".join(fz))
print("wrote", out_path, "with 1 file;", len(insts), "instances (all parts are core parts)")
