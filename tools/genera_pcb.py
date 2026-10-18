#!/usr/bin/env python3
"""Genera il PCB (2 strati, foro passante) delle due varianti del driver servo e lo sbroglia
con Freerouting. Le funzioni sono usate anche da genera_scheda_arduino.py.

Uso:  FREEROUTING_JAR=freerouting-2.4.1-executable.jar JAVA=/percorso/java-25 \\
      python3 tools/genera_pcb.py

Richiede il modulo Python 'pcbnew' di KiCad e kicad-cli. Lo schema va generato prima
(tools/genera_schemi.py): componenti, impronte e net vengono letti dalla sua netlist.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from genera_schemi import ROOT, parse_sexpr  # noqa: E402

FPDIR = os.environ.get("KICAD_FOOTPRINT_DIR", "/usr/share/kicad/footprints")
FREEROUTING = os.environ.get("FREEROUTING_JAR", "freerouting.jar")
JAVA = os.environ.get("JAVA", "java")

OX, OY = 100.0, 100.0  # posizione della scheda nel foglio

# posizione del pad 1 (x, y, rotazione) rispetto all'angolo in alto a sinistra della scheda
COMMON = {
    "H1": (4, 4, 0), "H2": (76, 4, 0), "H3": (4, 56, 0), "H4": (76, 56, 0),
    "J2": (6, 32, 0), "R3": (12, 30, 0), "R4": (12, 34, 0), "R5": (12, 38, 0),
    "R1": (12, 44, 0), "R2": (12, 48, 0), "C2": (12, 52, 0),
    "U2": (32, 32, 0), "C3": (27, 39.62, 270),
    "J3": (74, 27, 0), "J4": (74, 36, 0), "J5": (74, 45, 0),
}
PLACE = {
    "A": dict(COMMON, **{"J1": (12, 12, 180), "C1": (20, 12, 90), "C4": (27, 12, 90), "U1": (36, 12, 0),
                         "D1": (30.92, 18, 0), "C5": (48, 12, 90), "C6": (55, 12, 90)}),
    "B": dict(COMMON, **{"J1": (12, 14, 180), "C1": (20, 14, 90), "C4": (28, 14, 90), "U1": (36, 14, 0),
                         "L1": (50, 13, 0), "D1": (46.5, 23, 0), "C5": (63.5, 13, 90)}),
}

# piste di potenza tracciate a mano: (net, strato, larghezza mm, punti)
F, B = "F.Cu", "B.Cu"
SERVO_5V = [("+5V", F, 1.5, [(66, y), (74, y)]) for y in (29.54, 38.54, 47.54)]
SERVO_5V.append(("+5V", F, 0.8, [(27, 39.62), (32, 39.62)]))  # C3 vicino al pin 4 di U2
ROUTES = {
    "A": [
        ("+BATT", F, 1.5, [(12, 12), (20, 12), (27, 12), (30.92, 12), (36, 12)]),
        ("+BATT", F, 1.0, [(30.92, 12), (30.92, 18)]),                      # D1 catodo
        ("+5V", F, 1.0, [(41.08, 18), (41.08, 12)]),                        # D1 anodo
        ("+5V", F, 1.5, [(41.08, 12), (48, 12), (55, 12), (66, 12), (66, 29.54), (66, 38.54), (66, 47.54)]),
    ] + SERVO_5V,
    "B": [
        ("+BATT", F, 1.5, [(12, 14), (20, 14), (28, 14), (36, 14)]),
        ("Net-(D1-K)", F, 1.5, [(37.7, 10.3), (37.7, 7), (46.5, 7), (46.5, 13), (46.5, 23)]),
        ("Net-(D1-K)", F, 1.5, [(46.5, 13), (50, 13)]),
        ("+5V", B, 0.6, [(41.1, 10.3), (41.1, 4), (55, 4), (55, 13)]),      # FEEDBACK
        ("+5V", F, 1.5, [(55, 13), (63.5, 13), (66, 13), (66, 29.54), (66, 38.54), (66, 47.54)]),
    ] + SERVO_5V,
}

# posizione dei riferimenti in serigrafia (None = nascosto)
REFS_COMMON = {
    "H1": None, "H2": None, "H3": None, "H4": None, "J1": None, "J2": None, "J3": None, "J4": None, "J5": None,
    "R1": (17.08, 44), "R2": (17.08, 48), "R3": (17.08, 30), "R4": (17.08, 34), "R5": (17.08, 38),
    "C2": (14.5, 52), "C3": (29.9, 42.1), "U2": (35.81, 39.62),
}
REFS = {
    "A": dict(REFS_COMMON, **{"C1": (20, 15.6), "C4": (30, 9.5), "U1": (38.54, 6.5), "D1": (36, 18),
                              "C5": (45.6, 9.5), "C6": (55, 15.6)}),
    "B": dict(REFS_COMMON, **{"C1": (20, 17.6), "C4": (28, 18.6), "U1": (40.25, 18), "D1": (54, 23),
                              "L1": (52.5, 9), "C5": (60, 17.5)}),
}


def silk_servo(variant):
    """Scritte sulla serigrafia: (testo, x, y, dimensione)."""
    yb = PLACE[variant]["J1"][1]
    out = [("+", 12, yb - 4, 1.2), ("-", 10, yb - 4, 1.2), ("BATT 7.4V (J1)", 11, yb + 4, 1.0),
           ("G", 3.2, 32, 1.0), ("1", 3.2, 34.54, 1.0), ("2", 3.2, 37.08, 1.0), ("3", 3.2, 39.62, 1.0),
           ("PWM (J2)", 6, 43, 1.0)]
    for i, y in enumerate((27, 36, 45)):
        out += [("G", 71, y, 1.0), ("+", 71, y + 2.54, 1.0), ("S", 71, y + 5.08, 1.0),
                ("SERVO%d" % (i + 1), 68.5, y - 2.5, 0.8)]
    title = {"A": "DRIVER 3 SERVO - VAR. A (LM7805)", "B": "DRIVER 3 SERVO - VAR. B (LM2596)"}[variant]
    out.append((title, 46, 57, 1.2))
    return out


def pt(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(OX + x), pcbnew.FromMM(OY + y))


def read_netlist(sch):
    xml = tempfile.mktemp(suffix=".xml")
    subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadxml", "-o", xml, sch],
                   check=True, stdout=subprocess.DEVNULL)
    root = ET.parse(xml).getroot()
    comps = {}
    for c in root.iter("comp"):
        comps[c.get("ref")] = {
            "value": c.findtext("value"),
            "footprint": c.findtext("footprint"),
            "uuid": c.findtext("tstamps").split()[0],
        }
    nets = {}
    for n in root.iter("net"):
        for node in n.iter("node"):
            nets[(node.get("ref"), node.get("pin"))] = n.get("name")
    os.unlink(xml)
    return comps, nets


def setup_rules(board, clearance):
    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(2)
    ns = ds.m_NetSettings
    dflt = ns.m_DefaultNetClass
    dflt.SetClearance(pcbnew.FromMM(clearance))
    dflt.SetTrackWidth(pcbnew.FromMM(0.4))
    dflt.SetViaDiameter(pcbnew.FromMM(0.8))
    dflt.SetViaDrill(pcbnew.FromMM(0.4))
    pwr = pcbnew.NETCLASS("Power")
    pwr.SetClearance(pcbnew.FromMM(clearance))
    pwr.SetTrackWidth(pcbnew.FromMM(0.8))
    pwr.SetViaDiameter(pcbnew.FromMM(1.0))
    pwr.SetViaDrill(pcbnew.FromMM(0.5))
    ns.m_NetClasses["Power"] = pwr
    return pwr


def servo_project(variant, folder, name):
    """Configurazione di una scheda per make_pcb()."""
    return {"folder": folder, "name": name, "w": 80.0, "h": 60.0,
            "power_nets": ["GND", "+BATT", "+5V", "Net-(D1-K)"],
            "place": PLACE[variant], "routes": ROUTES[variant], "refs": REFS[variant],
            "silk": silk_servo(variant)}


def build_board(cfg, sch):
    comps, nets = read_netlist(sch)
    board = pcbnew.BOARD()
    pwr = setup_rules(board, cfg.get("clearance", 0.3))

    netitems = {}
    for name in sorted(set(nets.values())):
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netitems[name] = ni
        if name in cfg["power_nets"]:
            ni.SetNetClass(pwr)

    sheetfile = os.path.basename(sch)
    for ref, (x, y, rot) in cfg["place"].items():
        c = comps.pop(ref)
        lib, name = c["footprint"].split(":")
        fp = pcbnew.FootprintLoad(os.path.join(FPDIR, lib + ".pretty"), name)
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.SetReference(ref)
        fp.SetValue(c["value"])
        fp.SetPath(pcbnew.KIID_PATH("/" + c["uuid"]))
        fp.SetProperty("Sheetfile", sheetfile)
        fp.SetProperty("Sheetname", "")
        fp.SetPosition(pt(x, y))
        fp.SetOrientationDegrees(rot)
        for pad in fp.Pads():
            net = nets.get((ref, pad.GetNumber()))
            if net:
                pad.SetNet(netitems[net])
        # valore sullo strato di fabbricazione, non sulla serigrafia
        fp.Value().SetLayer(pcbnew.F_Fab)
        ref_pos = cfg["refs"].get(ref, "default")
        if ref_pos is None:
            fp.Reference().SetVisible(False)
        elif ref_pos != "default":
            fp.Reference().SetPosition(pt(*ref_pos))
            fp.Reference().SetTextAngleDegrees(-rot)  # angolo relativo all'impronta: testo orizzontale
            fp.Reference().SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.0), pcbnew.FromMM(1.0)))
            fp.Reference().SetTextThickness(pcbnew.FromMM(0.15))
        board.Add(fp)
    assert not comps, "componenti senza posizione: %s" % sorted(comps)

    # contorno della scheda
    W, H = cfg["w"], cfg["h"]
    corners = [(0, 0), (W, 0), (W, H), (0, H)]
    for a, b in zip(corners, corners[1:] + corners[:1]):
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(pt(*a))
        seg.SetEnd(pt(*b))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(pcbnew.FromMM(0.1))
        board.Add(seg)

    for net, layer, width, pts in cfg["routes"]:
        for p0, p1 in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pt(*p0))
            t.SetEnd(pt(*p1))
            t.SetWidth(pcbnew.FromMM(width))
            t.SetLayer({F: pcbnew.F_Cu, B: pcbnew.B_Cu}[layer])
            t.SetNet(netitems[net])
            t.SetLocked(True)  # Freerouting non le sposta
            board.Add(t)

    for txt, x, y, size in cfg["silk"]:
        t = pcbnew.PCB_TEXT(board)
        t.SetText(txt)
        t.SetPosition(pt(x, y))
        t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size), pcbnew.FromMM(size)))
        t.SetTextThickness(pcbnew.FromMM(size * 0.15))
        board.Add(t)
    return board, netitems


def autoroute(pcb, workdir):
    dsn = os.path.join(workdir, "board.dsn")
    ses = os.path.join(workdir, "board.ses")
    # esportazione in un processo nuovo: così KiCad carica il .kicad_pro aggiornato
    # e assegna le net alle classi (larghezza delle piste di alimentazione)
    subprocess.run([sys.executable, "-c", "import pcbnew, sys; "
                    "sys.exit(not pcbnew.ExportSpecctraDSN(pcbnew.LoadBoard(sys.argv[1]), sys.argv[2]))",
                    pcb, dsn], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run([JAVA, "-jar", FREEROUTING, "-de", dsn, "-do", ses, "-mp", "100",
                    "--gui.enabled=false", "--usage_and_diagnostic_data.disable_analytics=true"],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return ses


def import_ses(board, netitems, ses):
    """Importa piste e via dalla sessione di Freerouting (Specctra .ses)."""
    tree = parse_sexpr(open(ses).read())
    routes = [x for x in tree if isinstance(x, list) and x[0] == "routes"][0]
    res = [x for x in routes if isinstance(x, list) and x[0] == "resolution"][0]
    scale = {"um": 1e-3, "mm": 1.0, "mil": 0.0254}[res[1]] / float(res[2])
    layers = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu}

    def p(x, y):  # Specctra ha l'asse Y verso l'alto
        return pcbnew.VECTOR2I(pcbnew.FromMM(float(x) * scale), pcbnew.FromMM(-float(y) * scale))

    netout = [x for x in routes if isinstance(x, list) and x[0] == "network_out"][0]
    ntrack = nvia = 0
    for net in netout[1:]:
        ni = netitems[str(net[1])]
        for item in net[2:]:
            if item[0] == "wire":
                path = item[1]
                layer, width, coords = layers[str(path[1])], float(path[2]) * scale, path[3:]
                pts = [p(coords[i], coords[i + 1]) for i in range(0, len(coords), 2)]
                for a, b in zip(pts, pts[1:]):
                    t = pcbnew.PCB_TRACK(board)
                    t.SetStart(a)
                    t.SetEnd(b)
                    t.SetWidth(pcbnew.FromMM(width))
                    t.SetLayer(layer)
                    t.SetNet(ni)
                    board.Add(t)
                    ntrack += 1
            elif item[0] == "via":
                dia, drill = re.search(r"_(\d+):(\d+)_um", item[1]).groups()
                v = pcbnew.PCB_VIA(board)
                v.SetPosition(p(item[2], item[3]))
                v.SetWidth(pcbnew.FromMM(int(dia) / 1000))
                v.SetDrill(pcbnew.FromMM(int(drill) / 1000))
                v.SetNet(ni)
                board.Add(v)
                nvia += 1
    return ntrack, nvia


def add_gnd_zones(board, gnd, W, H):
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(gnd)
        z.SetLocalClearance(pcbnew.FromMM(0.5))
        z.SetMinThickness(pcbnew.FromMM(0.3))
        z.SetThermalReliefGap(pcbnew.FromMM(0.4))
        z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.5))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        ol = z.Outline()
        ol.NewOutline()
        m = 0.5
        for x, y in [(m, m), (W - m, m), (W - m, H - m), (m, H - m)]:
            ol.Append(pt(x, y))
        board.Add(z)


DRU = """(version 1)
# I pad dei componenti a foro passante sono collegati alla massa su entrambe le facce:
# basta un raggio della connessione termica per faccia.
(rule "raggi_termici"
    (constraint min_resolved_spokes 1))
"""


def project_netclasses(pro_path, power_nets, clearance):
    """Scrive le classi di net nel .kicad_pro (KiCad le legge da lì)."""
    with open(pro_path) as f:
        pro = json.load(f)
    base = {"bus_width": 12, "clearance": clearance, "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25,
            "diff_pair_width": 0.2, "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1,
            "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)",
            "wire_width": 6}
    pro["net_settings"] = {
        "classes": [dict(base, name="Default", track_width=0.4, via_diameter=0.8, via_drill=0.4),
                    dict(base, name="Power", track_width=0.8, via_diameter=1.0, via_drill=0.5)],
        "meta": {"version": 3},
        "net_colors": None,
        "netclass_assignments": None,
        "netclass_patterns": [{"netclass": "Power", "pattern": n} for n in power_nets],
    }
    with open(pro_path, "w") as f:
        json.dump(pro, f, indent=2)
        f.write("\n")


def make_pcb(cfg):
    """Crea, sbroglia e verifica il PCB descritto da cfg (vedi servo_project)."""
    d = os.path.join(ROOT, cfg["folder"])
    sch = os.path.join(d, cfg["name"] + ".kicad_sch")
    pcb = os.path.join(d, cfg["name"] + ".kicad_pcb")
    board, _ = build_board(cfg, sch)
    board.SetFileName(pcb)
    pcbnew.SaveBoard(pcb, board)
    project_netclasses(os.path.join(d, cfg["name"] + ".kicad_pro"), cfg["power_nets"], cfg.get("clearance", 0.3))
    with open(os.path.join(d, cfg["name"] + ".kicad_dru"), "w") as f:
        f.write(DRU)

    # ricarico la scheda: così valgono le classi di net del progetto e il
    # riempimento delle zone funziona
    board = pcbnew.LoadBoard(pcb)
    board.BuildConnectivity()
    netitems = {n.GetNetname(): n for n in board.GetNetsByName().values()}
    add_gnd_zones(board, netitems["GND"], cfg["w"], cfg["h"])  # per Freerouting sono piani di massa
    pcbnew.SaveBoard(pcb, board)
    with tempfile.TemporaryDirectory() as tmp:
        ses = autoroute(pcb, tmp)
        ntrack, nvia = import_ses(board, netitems, ses)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(pcb, board)

    report = os.path.join(tempfile.gettempdir(), cfg["name"] + "-drc.txt")
    pcbnew.WriteDRCReport(pcbnew.LoadBoard(pcb), report, pcbnew.EDA_UNITS_MILLIMETRES, True)
    summary = [l.strip("* \n") for l in open(report) if l.startswith("** Found")]
    print("%s: %d segmenti e %d via dall'autorouter; DRC: %s" % (cfg["folder"], ntrack, nvia, ", ".join(summary)))


def main():
    make_pcb(servo_project("A", "Variante_A_LDO", "Servo_Driver_A_LDO"))
    make_pcb(servo_project("B", "Variante_B_Buck", "Servo_Driver_B_Buck"))


if __name__ == "__main__":
    main()
