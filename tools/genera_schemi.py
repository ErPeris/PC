#!/usr/bin/env python3
"""Genera gli schemi KiCad delle due varianti del driver per 3 servomotori.

Uso:  python3 tools/genera_schemi.py [cartella_librerie_simboli]

Le librerie di simboli standard di KiCad servono solo in fase di generazione:
i simboli vengono incorporati nel file .kicad_sch, quindi il progetto si apre
anche senza questo script.
"""
import copy
import json
import math
import os
import sys
import uuid

SYMDIR = sys.argv[1] if len(sys.argv) > 1 else "/usr/share/kicad/symbols"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATE = "2026-10-18"


# ---------------------------------------------------------------- S-expression
class Sym(str):
    """Atomo non quotato (parola chiave o numero)."""


def parse_sexpr(text):
    pos, n = 0, len(text)
    stack, cur = [], []
    while pos < n:
        c = text[pos]
        if c in " \t\r\n":
            pos += 1
        elif c == "(":
            stack.append(cur)
            cur = []
            pos += 1
        elif c == ")":
            done = cur
            cur = stack.pop()
            cur.append(done)
            pos += 1
        elif c == '"':
            pos += 1
            buf = []
            while text[pos] != '"':
                if text[pos] == "\\":
                    buf.append(text[pos:pos + 2])
                    pos += 2
                else:
                    buf.append(text[pos])
                    pos += 1
            pos += 1
            cur.append("".join(buf))
        else:
            start = pos
            while pos < n and text[pos] not in ' \t\r\n()"':
                pos += 1
            cur.append(Sym(text[start:pos]))
    return cur[0]


def fmt_num(v):
    v = round(v, 4)
    if v == int(v):
        return str(int(v))
    return ("%.4f" % v).rstrip("0").rstrip(".")


def dump(node, indent=0):
    if isinstance(node, Sym):
        return str(node)
    if isinstance(node, str):
        return '"' + node + '"'
    if isinstance(node, bool):
        return "yes" if node else "no"
    if isinstance(node, (int, float)):
        return fmt_num(node)
    out = "(" + dump(node[0], indent)
    for x in node[1:]:
        if isinstance(x, list) and any(isinstance(y, list) for y in x):
            out += "\n" + "  " * (indent + 1) + dump(x, indent + 1)
        else:
            out += " " + dump(x, indent + 1)
    return out + ")"


def S(*items):
    return [Sym(items[0])] + list(items[1:])


def uid():
    return Sym(str(uuid.uuid4()))


# ---------------------------------------------------------------- librerie
_libs = {}


def load_lib(lib):
    if lib not in _libs:
        tree = parse_sexpr(open(os.path.join(SYMDIR, lib + ".kicad_sym")).read())
        _libs[lib] = {x[1]: x for x in tree if isinstance(x, list) and x[0] == "symbol"}
    return _libs[lib]


def flat_symbol(lib, name):
    """Simbolo di libreria con l'eventuale 'extends' risolto."""
    node = copy.deepcopy(load_lib(lib)[name])
    ext = [x for x in node if isinstance(x, list) and x[0] == "extends"]
    if not ext:
        return node
    parent_name = ext[0][1]
    parent = flat_symbol(lib, parent_name)
    child_props = [x for x in node if isinstance(x, list) and x[0] == "property"]
    out = [Sym("symbol"), name]
    for x in parent[2:]:
        if isinstance(x, list) and x[0] == "property":
            continue
        if isinstance(x, list) and x[0] == "symbol":
            x = copy.deepcopy(x)
            x[1] = name + x[1][len(parent_name):]
            out.extend(child_props)
            child_props = []
        out.append(x)
    out.extend(child_props)
    return out


def lib_pins(symnode):
    """{numero: (x, y, angolo, unit)} in coordinate di libreria (Y verso l'alto)."""
    pins = {}
    for sub in symnode:
        if not (isinstance(sub, list) and sub[0] == "symbol"):
            continue
        unit = int(sub[1].split("_")[-2])
        for p in sub:
            if isinstance(p, list) and p[0] == "pin":
                at = [x for x in p if isinstance(x, list) and x[0] == "at"][0]
                num = [x for x in p if isinstance(x, list) and x[0] == "number"][0][1]
                pins[num] = (float(at[1]), float(at[2]), float(at[3]), unit)
    return pins


# ---------------------------------------------------------------- schema
def rnd(p):
    return (round(p[0], 3), round(p[1], 3))


class Part:
    def __init__(self, sch, lib_id, ref, value, at, rot=0, mirror=False, unit=1,
                 footprint="", fields=None, extra=None):
        self.sch, self.lib_id, self.ref, self.value = sch, lib_id, ref, value
        self.x, self.y = at
        self.rot, self.mirror, self.unit = rot, mirror, unit
        self.footprint = footprint
        self.fields = fields or {}
        self.extra = extra or {}
        lib, name = lib_id.split(":")
        self.libsym = flat_symbol(lib, name)
        self.pins = lib_pins(self.libsym)
        self.power = any(isinstance(x, list) and x[0] == "power" for x in self.libsym)
        sch.add_lib_symbol(lib_id, self.libsym)

    def xform(self, px, py):
        x, y = px, -py
        if self.mirror:
            x = -x
        a = math.radians(self.rot)
        c, s = round(math.cos(a)), round(math.sin(a))
        return (x * c + y * s, -x * s + y * c)

    def pin(self, num):
        px, py, _, _ = self.pins[str(num)]
        dx, dy = self.xform(px, py)
        return rnd((self.x + dx, self.y + dy))

    def unit_pins(self):
        return [n for n, p in self.pins.items() if p[3] in (0, self.unit)]

    def sexpr(self, project, root_uuid):
        node = S("symbol", S("lib_id", self.lib_id), S("at", self.x, self.y, self.rot))
        if self.mirror:
            node.append(S("mirror", Sym("y")))
        node += [S("unit", self.unit), S("in_bom", Sym("yes")), S("on_board", Sym("yes")),
                 S("dnp", Sym("no")), S("uuid", uid())]
        txt_angle = 90 if self.rot in (90, 270) else 0
        values = {"Reference": self.ref, "Value": self.value,
                  "Footprint": self.footprint, "Datasheet": "~"}
        for k, v in self.extra.items():
            values[k] = v
        for name, val in values.items():
            dx, dy, just, hide = self.fields.get(name, (0, 0, None, True))
            eff = S("effects", S("font", S("size", 1.27, 1.27)))
            if just:
                eff.append(S("justify", Sym(just)))
            if hide:
                eff.append(Sym("hide"))
            node.append(S("property", name, val, S("at", self.x + dx, self.y + dy, txt_angle), eff))
        for n in self.unit_pins():
            node.append(S("pin", n, S("uuid", uid())))
        node.append(S("instances", S("project", project,
                                     S("path", "/" + root_uuid, S("reference", self.ref), S("unit", self.unit)))))
        return node


class Schematic:
    def __init__(self, title, comments):
        self.title, self.comments = title, comments
        self.lib_symbols = {}
        self.parts, self.wires, self.labels, self.texts, self.noconn = [], [], [], [], []
        self.pwr_count = 0

    def add_lib_symbol(self, lib_id, node):
        if lib_id not in self.lib_symbols:
            n = copy.deepcopy(node)
            n[1] = lib_id
            self.lib_symbols[lib_id] = n

    def part(self, *a, **k):
        p = Part(self, *a, **k)
        self.parts.append(p)
        return p

    def power(self, name, at, rot=0, lib="power"):
        """Simbolo di alimentazione (GND, +5V, +BATT, PWR_FLAG)."""
        self.pwr_count += 1
        ref = ("#FLG%02d" if name == "PWR_FLAG" else "#PWR%02d") % self.pwr_count
        up = name != "GND"  # il corpo è sopra il pin (tranne GND)
        d = 3.81 if name == "GND" else -3.81
        if rot == 0:
            off = (0, d)
        elif rot == 180:
            off = (0, -d)
        else:
            # simbolo ruotato: corpo verso sinistra (+5V rot 90, GND rot 270)
            # o verso destra (+5V rot 270, GND rot 90)
            left = (rot == 90) == up
            off = (-5.08 if left else 5.08, 0)
        fields = {"Value": (off[0], off[1], None, False)}
        return self.part("%s:%s" % (lib, name), ref, name, at, rot=rot, fields=fields)

    def wire(self, *pts):
        pts = [rnd(p) for p in pts]
        for a, b in zip(pts, pts[1:]):
            assert a[0] == b[0] or a[1] == b[1], ("filo non ortogonale", a, b)
            self.wires.append((a, b))

    def label(self, name, at, angle=0):
        self.labels.append((name, rnd(at), angle))

    def text(self, txt, at, size=1.27, bold=False):
        self.texts.append((txt, at, size, bold))

    def no_connect(self, at):
        self.noconn.append(rnd(at))

    # --- connessioni
    def _pin_points(self):
        pts = []
        for p in self.parts:
            for n in p.unit_pins():
                pts.append(p.pin(n))
        return pts

    def _split_wires(self):
        """Spezza i fili nei punti dove termina qualcosa (pin, fili, etichette)."""
        stops = set(self._pin_points()) | {l[1] for l in self.labels}
        for a, b in self.wires:
            stops.add(a)
            stops.add(b)
        out = []
        for a, b in self.wires:
            inner = [s for s in stops if s not in (a, b) and on_segment(s, a, b)]
            seq = sorted([a, b] + inner, key=lambda q: (q[0] - a[0]) ** 2 + (q[1] - a[1]) ** 2)
            out += list(zip(seq, seq[1:]))
        self.wires = out

    def _junctions(self):
        count = {}
        for a, b in self.wires:
            for q in (a, b):
                count[q] = count.get(q, 0) + 1
        for q in self._pin_points():
            if q in count:
                count[q] += 1
        return sorted(q for q, c in count.items() if c >= 3)

    def save(self, path, project):
        self._split_wires()
        root_uuid = str(uuid.uuid4())
        tb = S("title_block", S("title", self.title), S("date", DATE), S("rev", "1.0"),
               S("company", ""))
        for i, c in enumerate(self.comments, 1):
            tb.append(S("comment", i, c))
        out = S("kicad_sch", S("version", 20230121), S("generator", Sym("eeschema")),
                S("uuid", Sym(root_uuid)), S("paper", "A4"), tb)
        out.append(S("lib_symbols", *self.lib_symbols.values()))
        for q in self._junctions():
            out.append(S("junction", S("at", *q), S("diameter", 0), S("color", 0, 0, 0, 0), S("uuid", uid())))
        for q in self.noconn:
            out.append(S("no_connect", S("at", *q), S("uuid", uid())))
        for a, b in self.wires:
            out.append(S("wire", S("pts", S("xy", *a), S("xy", *b)),
                         S("stroke", S("width", 0), S("type", Sym("default"))), S("uuid", uid())))
        for name, at, ang in self.labels:
            just = "left" if ang == 0 else "right"
            out.append(S("label", name, S("at", at[0], at[1], ang),
                         S("effects", S("font", S("size", 1.27, 1.27)), S("justify", Sym(just), Sym("bottom"))),
                         S("uuid", uid())))
        for txt, at, size, bold in self.texts:
            font = S("font", S("size", size, size))
            if bold:
                font.append(Sym("bold"))
            txt = txt.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            out.append(S("text", txt, S("at", at[0], at[1], 0),
                         S("effects", font, S("justify", Sym("left"), Sym("bottom"))), S("uuid", uid())))
        for p in self.parts:
            out.append(p.sexpr(project, root_uuid))
        out.append(S("sheet_instances", S("path", "/", S("page", "1"))))
        with open(path, "w") as f:
            f.write(dump(out) + "\n")


def on_segment(q, a, b):
    if a[0] == b[0] == q[0]:
        return min(a[1], b[1]) < q[1] < max(a[1], b[1])
    if a[1] == b[1] == q[1]:
        return min(a[0], b[0]) < q[0] < max(a[0], b[0])
    return False


# ---------------------------------------------------------------- footprint
FP = {
    "jst2": "Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical",
    "hdr4": "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
    "hdr3": "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
    "dip14": "Package_DIP:DIP-14_W7.62mm",
    "to220": "Package_TO_SOT_THT:TO-220-3_Vertical",
    "to263": "Package_TO_SOT_SMD:TO-263-5_TabPin3",
    "r": "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
    "c": "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm",
    "cp6": "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm",
    "cp8": "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm",
    "do41": "Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal",
    "do201": "Diode_THT:D_DO-201AD_P15.24mm_Horizontal",
    "l": "Inductor_THT:L_Radial_D12.0mm_P5.00mm_Fastron_11P",
}

# posizioni dei campi Reference/Value: (dx, dy, justify, nascosto)
F_RIGHT = {"Reference": (2.54, -1.27, "left", False), "Value": (2.54, 1.27, "left", False)}
F_LEFT = {"Reference": (-2.54, -1.27, "right", False), "Value": (-2.54, 1.27, "right", False)}


def vpart(sch, lib_id, ref, value, at, fp, side="right"):
    """Componente a 2 pin verticale (pin 1 in alto)."""
    return sch.part(lib_id, ref, value, at, footprint=fp, fields=F_RIGHT if side == "right" else F_LEFT)


# ---------------------------------------------------------------- blocchi
RAIL = 50.8  # quota della linea di alimentazione di ingresso


def input_block(sch):
    """J1 batteria, C1 filtro d'ingresso, simboli +BATT e PWR_FLAG."""
    j1 = sch.part("Connector_Generic:Conn_01x02", "J1", "BATT 7.4V (JST-PH)", (30.48, RAIL), mirror=True,
                  footprint=FP["jst2"], fields={"Reference": (0, -5.08, None, False),
                                                 "Value": (-2.54, 6.35, None, False)})
    p1, p2 = j1.pin(1), j1.pin(2)
    sch.power("+BATT", (40.64, RAIL))
    c1 = vpart(sch, "Device:C_Polarized", "C1", "100uF 16V", (45.72, RAIL + 3.81), FP["cp6"])
    sch.power("GND", c1.pin(2))
    sch.wire(p2, (38.1, p2[1]), (38.1, p2[1] + 5.08))
    sch.power("GND", (38.1, p2[1] + 5.08))
    sch.power("PWR_FLAG", (53.34, RAIL))
    # PWR_FLAG sulla massa
    sch.power("PWR_FLAG", (25.4, 68.58))
    sch.power("GND", (25.4, 68.58))
    sch.text("Ingresso LiPo 2S\n(6.0 ... 8.4 V)", (17.78, 41.91))
    return p1


def signal_block(sch):
    """Header ingresso PWM, partitore di riferimento, LM324, uscite servo."""
    # --- header ingresso J2
    j2 = sch.part("Connector_Generic:Conn_01x04", "J2", "PWM IN 3.3V", (30.48, 99.06), mirror=True,
                  footprint=FP["hdr4"], fields={"Reference": (0, -5.08, None, False),
                                                 "Value": (-2.54, 10.16, None, False)})
    g = j2.pin(1)
    sch.wire(g, (g[0] + 5.08, g[1]))
    sch.power("GND", (g[0] + 5.08, g[1]), rot=90)
    for i in range(3):
        p = j2.pin(i + 2)
        sch.wire(p, (p[0] + 12.7, p[1]))
        sch.label("PWM%d_IN" % (i + 1), (p[0] + 12.7, p[1]))
    sch.text("Dal microcontrollore:\n1 = GND\n2 = PWM1  3 = PWM2  4 = PWM3", (17.78, 87.63))

    # --- partitore di riferimento VREF
    x0 = 50.8
    r1 = vpart(sch, "Device:R", "R1", "22k", (x0, 125.73), FP["r"])
    r2 = vpart(sch, "Device:R", "R2", "10k", (x0, 133.35), FP["r"], side="left")
    c2 = vpart(sch, "Device:C", "C2", "100nF", (x0 + 7.62, 133.35), FP["c"])
    sch.power("+5V", r1.pin(1))
    sch.power("GND", r2.pin(2))
    sch.power("GND", c2.pin(2))
    node = r1.pin(2)
    sch.wire(node, c2.pin(1), (x0 + 15.24, node[1]))
    sch.label("VREF", (x0 + 15.24, node[1]))
    sch.text("VREF = 5V x 10k / (22k + 10k)\n       = 1.56 V (soglia)", (25.4, 147.32))

    # --- LM324: unità A, B, C come comparatori
    X = 111.76
    out_pins = []
    for i, (u, Y) in enumerate([(1, 96.52), (2, 116.84), (3, 137.16)]):
        n = i + 1
        ua = sch.part("Amplifier_Operational:LM324", "U2", "LM324", (X, Y), unit=u, footprint=FP["dip14"],
                      fields={"Reference": (1.27, -8.89, "left", False), "Value": (1.27, -6.35, "left", False)})
        pin_p, pin_m, pin_o = [ua.pin(k) for k in {1: (3, 2, 1), 2: (5, 6, 7), 3: (10, 9, 8)}[u]]
        # ingresso non invertente: segnale PWM a 3.3 V con pull-down
        rpd = sch.part("Device:R", "R%d" % (n + 2), "100k", (X - 20.32, Y + 1.27), footprint=FP["r"],
                       fields=F_LEFT)
        sch.label("PWM%d_IN" % n, (X - 27.94, pin_p[1]), angle=180)
        sch.wire((X - 27.94, pin_p[1]), rpd.pin(1), pin_p)
        sch.power("GND", rpd.pin(2))
        # ingresso invertente: soglia VREF
        sch.label("VREF", (X - 10.16, pin_m[1]), angle=180)
        sch.wire((X - 10.16, pin_m[1]), pin_m)
        out_pins.append((n, pin_o, Y))

    # --- uscite verso i servo
    XJ = 170.18
    for k, (n, po, Y) in enumerate(out_pins):
        j = sch.part("Connector_Generic:Conn_01x03", "J%d" % (n + 2), "SERVO %d" % n, (XJ, Y), footprint=FP["hdr3"],
                     fields={"Reference": (2.54, -2.54, "left", False), "Value": (2.54, 0, "left", False)})
        sig = j.pin(3)
        sch.wire(po, (147.32, po[1]), (147.32, sig[1]), sig)
        sch.label("PWM%d_5V" % n, (po[0] + 5.08, po[1]))
        gnd, vcc = j.pin(1), j.pin(2)
        sch.wire(gnd, (gnd[0] - 5.08, gnd[1]))
        sch.power("GND", (gnd[0] - 5.08, gnd[1]), rot=270)
        sch.wire(vcc, (vcc[0] - 5.08, vcc[1]))
        sch.power("+5V", (vcc[0] - 5.08, vcc[1]), rot=90)
    sch.text("Servo: 1 = GND, 2 = +5V, 3 = PWM 5V", (152.4, 87.63))

    # --- unità D non usata: inseguitore con IN+ a massa
    Y = 157.48
    ud = sch.part("Amplifier_Operational:LM324", "U2", "LM324", (X, Y), unit=4, footprint=FP["dip14"],
                  fields={"Reference": (1.27, -8.89, "left", False), "Value": (1.27, -6.35, "left", False)})
    pp, pm, po = ud.pin(12), ud.pin(13), ud.pin(14)
    sch.wire(pp, (pp[0] - 5.08, pp[1]))
    sch.power("GND", (pp[0] - 5.08, pp[1]))
    sch.wire(pm, (pm[0] - 2.54, pm[1]), (pm[0] - 2.54, Y + 7.62), (po[0] + 2.54, Y + 7.62),
             (po[0] + 2.54, po[1]), po)
    sch.text("U2D non usata:\nIN+ a GND, uscita\nretroazionata su IN-", (68.58, 154.94))

    # --- alimentazione LM324 + disaccoppiamento
    ue = sch.part("Amplifier_Operational:LM324", "U2", "LM324", (139.7, Y), unit=5, footprint=FP["dip14"],
                  fields={"Reference": (1.27, -1.27, "left", False), "Value": (1.27, 1.27, "left", False)})
    sch.power("+5V", ue.pin(4))
    sch.power("GND", ue.pin(11))
    c3 = vpart(sch, "Device:C", "C3", "100nF", (152.4, Y), FP["c"])
    sch.power("+5V", c3.pin(1))
    sch.power("GND", c3.pin(2))

    sch.text("LEVEL SHIFTER 3.3V -> 5V  (LM324, comparatori non invertenti: IN+ = PWM, IN- = VREF)",
             (68.58, 85.09), size=1.524, bold=True)


def variant_a():
    sch = Schematic("Driver 3 servo - Variante A (LDO)",
                    ["Batteria LiPo 2S 7.4V -> 5V con regolatore lineare LM7805",
                     "Level shifter PWM 3.3V -> 5V con LM324"])
    sch.text("ALIMENTAZIONE - Variante A: regolatore lineare LM7805", (17.78, 30.48), size=1.524, bold=True)
    vin = input_block(sch)
    u1 = sch.part("Regulator_Linear:LM7805_TO220", "U1", "LM7805", (81.28, RAIL), footprint=FP["to220"],
                  fields={"Reference": (3.81, 7.62, "left", False), "Value": (3.81, 10.16, "left", False)})
    c4 = vpart(sch, "Device:C", "C4", "330nF", (63.5, RAIL + 3.81), FP["c"])
    c5 = vpart(sch, "Device:C", "C5", "100nF", (99.06, RAIL + 3.81), FP["c"])
    c6 = vpart(sch, "Device:C_Polarized", "C6", "100uF 10V", (111.76, RAIL + 3.81), FP["cp6"])
    d1 = sch.part("Diode:1N4007", "D1", "1N4007", (81.28, RAIL - 7.62), footprint=FP["do41"],
                  fields={"Reference": (0, -5.08, None, False), "Value": (0, -2.54, None, False)})
    for c in (c4, c5, c6):
        sch.power("GND", c.pin(2))
    sch.power("GND", u1.pin(2))
    sch.wire(vin, u1.pin(1))
    sch.wire(u1.pin(3), (121.92, RAIL))
    sch.power("+5V", (121.92, RAIL))
    # D1 in antiparallelo: catodo su IN, anodo su OUT
    sch.wire((71.12, RAIL), (71.12, d1.pin(1)[1]), d1.pin(1))
    sch.wire(d1.pin(2), (91.44, d1.pin(2)[1]), (91.44, RAIL))
    sch.text("D1: protezione da correnti inverse\n(catodo su IN, anodo su OUT)", (96.52, 40.64))
    signal_block(sch)
    notes(sch, [
        "NOTE",
        "- U1 dissipa (Vin - 5V) x I: con 7.4V e 1A sono circa 2.4W -> serve un dissipatore sul TO-220.",
        "- Il 7805 richiede circa 2V di caduta: sotto ~7V di batteria l'uscita scende sotto 5V.",
        "  Alternativa a basso dropout con lo stesso pinout TO-220: LM2940-5.0.",
    ])
    return sch


def variant_b():
    sch = Schematic("Driver 3 servo - Variante B (Buck)",
                    ["Batteria LiPo 2S 7.4V -> 5V con regolatore switching LM2596S-5.0",
                     "Level shifter PWM 3.3V -> 5V con LM324"])
    sch.text("ALIMENTAZIONE - Variante B: regolatore switching LM2596S-5.0", (17.78, 30.48), size=1.524, bold=True)
    vin = input_block(sch)
    u1 = sch.part("Regulator_Switching:LM2596S-5", "U1", "LM2596S-5.0", (99.06, RAIL + 2.54), footprint=FP["to263"],
                  fields={"Reference": (0, -10.16, None, False), "Value": (0, -7.62, None, False)})
    cin = vpart(sch, "Device:C_Polarized", "C4", "100uF 16V", (68.58, RAIL + 3.81), FP["cp8"])
    sch.power("GND", cin.pin(2))
    sch.wire(vin, u1.pin(1))
    sch.power("GND", u1.pin(3))
    on = u1.pin(5)
    sch.wire(on, (on[0] - 2.54, on[1]), (on[0] - 2.54, on[1] + 2.54))
    sch.power("GND", (on[0] - 2.54, on[1] + 2.54))
    sw = u1.pin(2)
    xs = sw[0] + 5.08
    d1 = sch.part("Diode:1N5822", "D1", "1N5822", (xs, sw[1] + 3.81), rot=270, footprint=FP["do201"],
                  fields={"Reference": (-2.54, 3.81, "right", False), "Value": (-2.54, 6.35, "right", False)})
    l1 = sch.part("Device:L", "L1", "33uH 3A", (xs + 7.62, sw[1]), rot=90, footprint=FP["l"],
                  fields={"Reference": (0, 3.81, None, False), "Value": (0, 6.35, None, False)})
    xo = xs + 15.24
    cout = vpart(sch, "Device:C_Polarized", "C5", "220uF 10V low ESR", (xo, sw[1] + 3.81), FP["cp8"])
    sch.power("GND", d1.pin(2))
    sch.power("GND", cout.pin(2))
    sch.wire(sw, d1.pin(1), l1.pin(1))
    sch.wire(l1.pin(2), (xo, sw[1]), (xo + 17.78, sw[1]))
    sch.power("PWR_FLAG", (xo + 5.08, sw[1]))
    sch.power("+5V", (xo + 17.78, sw[1]))
    fb = u1.pin(4)
    sch.wire(fb, (xo, fb[1]), (xo, sw[1]))
    sch.text("FB collegato ai 5V dopo l'induttore", (xo - 15.24, fb[1] - 2.54))
    sch.text("ON/OFF a GND = sempre acceso", (66.04, 71.12))
    signal_block(sch)
    notes(sch, [
        "NOTE",
        "- Anello di potenza (C4, U1 pin VIN/OUT/GND, D1, L1, C5) il più corto possibile, con piano di massa.",
        "- L1: induttore di potenza da almeno 3A di saturazione; verificare l'impronta col componente acquistato.",
        "- Con batteria scarica (~6.4V) il LM2596 lavora vicino al limite di dropout.",
    ])
    return sch


def notes(sch, lines):
    common = [
        "- LM324 alimentato a 5V: l'uscita alta arriva a ~3.5-3.8V (non rail-to-rail). Ai servo basta;",
        "  per avere 5V pieni montare MCP6004 o LMV324 nello stesso zoccolo DIP-14 (stesso pinout).",
        "- R3-R5 (pull-down) tengono basse le uscite se il microcontrollore e' scollegato.",
    ]
    sch.text("\n".join(lines + common), (17.78, 193.04))


def project_file(path, name):
    with open("/usr/share/kicad/template/kicad.kicad_pro") as f:
        pro = json.load(f)
    pro["meta"]["filename"] = name + ".kicad_pro"
    with open(path, "w") as f:
        json.dump(pro, f, indent=2)
        f.write("\n")


def main():
    for folder, name, build in [("Variante_A_LDO", "Servo_Driver_A_LDO", variant_a),
                                ("Variante_B_Buck", "Servo_Driver_B_Buck", variant_b)]:
        d = os.path.join(ROOT, folder)
        os.makedirs(d, exist_ok=True)
        build().save(os.path.join(d, name + ".kicad_sch"), name)
        project_file(os.path.join(d, name + ".kicad_pro"), name)
        print("scritto", os.path.join(folder, name + ".kicad_sch"))


if __name__ == "__main__":
    main()
