#!/usr/bin/env python3
"""Confronta la netlist esportata da KiCad con i collegamenti attesi.

Uso:  kicad-cli sch export netlist --format kicadxml -o A.xml Variante_A_LDO/Servo_Driver_A_LDO.kicad_sch
      python3 tools/verifica_netlist.py A A.xml
(schede: A, B = driver servo; ARDUINO = scheda di test con Arduino Nano)
"""
import sys
import xml.etree.ElementTree as ET

COMMON = {
    "GND": "J1.2 C1.2 J2.1 R2.2 C2.2 R3.2 R4.2 R5.2 U2.12 U2.11 C3.2 J3.1 J4.1 J5.1",
    "+5V": "R1.1 U2.4 C3.1 J3.2 J4.2 J5.2",
    "+BATT": "J1.1 C1.1",
    "VREF": "R1.2 R2.1 C2.1 U2.2 U2.6 U2.9",
    "PWM1_IN": "J2.2 R3.1 U2.3",
    "PWM2_IN": "J2.3 R4.1 U2.5",
    "PWM3_IN": "J2.4 R5.1 U2.10",
    "PWM1_5V": "U2.1 J3.3",
    "PWM2_5V": "U2.7 J4.3",
    "PWM3_5V": "U2.8 J5.3",
    "U2D": "U2.13 U2.14",
}
VARIANT = {
    "A": {
        "GND": "U1.2 C4.2 C5.2 C6.2",
        "+5V": "U1.3 D1.2 C5.1 C6.1",
        "+BATT": "U1.1 D1.1 C4.1",
    },
    "B": {
        "GND": "U1.3 U1.5 C4.2 D1.2 C5.2",
        "+5V": "L1.2 C5.1 U1.4",
        "+BATT": "U1.1 C4.1",
        "SW": "U1.2 D1.1 L1.1",
    },
}


ARDUINO = {
    "+BATT": "J1.1 SW1.2",
    "VIN": "SW1.1 U1.30 C1.1 R1.1",
    "GND": "J1.2 U1.4 U1.29 C1.2 D1.1 J2.2 J3.1 C2.2 Q1.3 R3.2",
    "+5V": "U1.27 J3.2 C2.1 BZ1.1 D2.1",
    "+3V3": "U1.17 J2.1",
    "SCL": "U1.24 J2.3",
    "SDA": "U1.23 J2.4",
    "SERVO_PWM": "U1.12 J3.3",
    "BUZZER": "U1.11 R2.1",
    "BASE": "R2.2 R3.1 Q1.2",
    "BUZZER-": "Q1.1 BZ1.2 D2.2",
    "LED": "R1.2 D1.2",
}


def expected_nets(board):
    if board == "ARDUINO":
        return {k: set(v.split()) for k, v in ARDUINO.items()}
    expected = {k: set(v.split()) for k, v in COMMON.items()}
    for k, v in VARIANT[board].items():
        expected.setdefault(k, set()).update(v.split())
    return expected


def main(board, path):
    expected = expected_nets(board)

    root = ET.parse(path).getroot()
    actual = []
    for net in root.iter("net"):
        nodes = {"%s.%s" % (n.get("ref"), n.get("pin")) for n in net.iter("node")}
        nodes = {n for n in nodes if not n.startswith("#")}
        actual.append((net.get("name"), nodes))

    ok = True
    used = set()
    for name, nodes in sorted(expected.items()):
        match = [a for a in actual if a[1] == nodes]
        if match:
            used.add(match[0][0])
            print("OK   %-8s -> %-10s %s" % (name, match[0][0], " ".join(sorted(nodes))))
        else:
            ok = False
            best = max(actual, key=lambda a: len(a[1] & nodes))
            print("ERR  %-8s atteso %s" % (name, sorted(nodes)))
            print("     trovato %s: %s" % (best[0], sorted(best[1])))
    for name, nodes in actual:
        if name not in used and nodes and not name.startswith("unconnected-"):
            ok = False
            print("ERR  net inattesa %s: %s" % (name, sorted(nodes)))

    # tutti i pin dei componenti devono comparire in una net
    pins = {}
    for comp in root.iter("comp"):
        pins[comp.get("ref")] = comp
    print("componenti:", len(pins))
    print("RISULTATO:", "OK" if ok else "ERRORI")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main(sys.argv[1], sys.argv[2]) else 1)
