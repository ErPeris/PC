#!/usr/bin/env python3
"""Genera schema e PCB della scheda di test con Arduino Nano (progetto 3).

Uso:  FREEROUTING_JAR=freerouting-2.4.1-executable.jar JAVA=/percorso/java-25 \\
      python3 tools/genera_scheda_arduino.py [--solo-schema]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from genera_schemi import FP, F_LEFT, ROOT, Schematic, project_file, vpart  # noqa: E402

FOLDER, NAME = "Scheda_Test_Arduino", "Scheda_Test_Arduino"
FP_NANO = "Module:Arduino_Nano"
FP_SW = "Button_Switch_THT:SW_Slide_SPDT_Straight_CK_OS102011MS2Q"
FP_LED = "LED_THT:LED_D5.0mm"
FP_BUZ = "Buzzer_Beeper:Buzzer_12x9.5RM7.6"
FP_TO92 = "Package_TO_SOT_THT:TO-92_Inline_Wide"
FP_DO35 = "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal"
FP_SOCK4 = "Connector_PinSocket_2.54mm:PinSocket_1x04_P2.54mm_Vertical"

# pin dell'Arduino Nano non usati (numerazione del simbolo KiCad = piedini del modulo)
NANO_NC = [1, 2, 3, 5, 6, 7, 8, 9, 10, 13, 14, 15, 16, 18, 19, 20, 21, 22, 25, 26, 28]


def schematic():
    sch = Schematic("Scheda di test con Arduino Nano",
                    ["Arduino Nano + BME280 (I2C) + buzzer + servomotore",
                     "Interruttore generale con LED di accensione"])

    # --- alimentazione: batteria, interruttore, LED di accensione
    sch.text("ALIMENTAZIONE", (17.78, 30.48), size=1.524, bold=True)
    rail = 50.8
    j1 = sch.part("Connector_Generic:Conn_01x02", "J1", "BATT 7-12V (JST-PH)", (30.48, rail), mirror=True,
                  footprint=FP["jst2"], fields={"Reference": (0, -5.08, None, False),
                                                 "Value": (-2.54, 6.35, None, False)})
    p1, p2 = j1.pin(1), j1.pin(2)
    sch.wire(p2, (38.1, p2[1]), (38.1, p2[1] + 5.08))
    sch.power("GND", (38.1, p2[1] + 5.08))
    sch.power("+BATT", (38.1, rail))
    sch.power("PWR_FLAG", (45.72, rail))
    sw = sch.part("Switch:SW_SPDT", "SW1", "ON/OFF", (53.34, rail), footprint=FP_SW,
                  fields={"Reference": (0, -5.08, None, False), "Value": (0, 5.08, None, False)})
    sch.wire(p1, sw.pin(2))
    sch.no_connect(sw.pin(3))
    vin = sw.pin(1)
    r1 = vpart(sch, "Device:R", "R1", "1k", (71.12, vin[1] + 3.81), FP["r"])
    d1 = sch.part("Device:LED", "D1", "LED 5mm", (71.12, vin[1] + 11.43), rot=90, footprint=FP_LED,
                  fields={"Reference": (3.81, -1.27, None, False), "Value": (6.35, 1.27, None, False)})
    sch.power("GND", d1.pin(1))
    c1 = vpart(sch, "Device:C_Polarized", "C1", "100uF 16V", (83.82, vin[1] + 3.81), FP["cp6"])
    sch.power("GND", c1.pin(2))
    sch.wire(vin, r1.pin(1), c1.pin(1), (99.06, vin[1]))
    sch.power("PWR_FLAG", (91.44, vin[1]))
    sch.label("VIN", (99.06, vin[1]))
    sch.power("PWR_FLAG", (25.4, 68.58))
    sch.power("GND", (25.4, 68.58))
    sch.text("LED acceso = interruttore su ON", (40.64, 76.2))

    # --- Arduino Nano
    sch.text("MICROCONTROLLORE", (101.6, 71.12), size=1.524, bold=True)
    u1 = sch.part("MCU_Module:Arduino_Nano_v3.x", "U1", "Arduino Nano", (127, 110.49), footprint=FP_NANO,
                  fields={"Reference": (15.24, -22.86, "left", False), "Value": (15.24, -20.32, "left", False)})
    pv, p33, p5 = u1.pin(30), u1.pin(17), u1.pin(27)
    sch.wire(pv, (pv[0], pv[1] - 7.62), (pv[0] - 7.62, pv[1] - 7.62))
    sch.label("VIN", (pv[0] - 7.62, pv[1] - 7.62), angle=180)
    sch.wire(p33, (p33[0], p33[1] - 5.08))
    sch.power("+3V3", (p33[0], p33[1] - 5.08))
    sch.wire(p5, (p5[0], p5[1] - 2.54), (p5[0] + 7.62, p5[1] - 2.54))
    sch.power("+5V", (p5[0] + 7.62, p5[1] - 2.54))
    g1, g2 = u1.pin(4), u1.pin(29)
    sch.wire(g1, (g1[0], g1[1] + 2.54), (g2[0], g2[1] + 2.54), g2)
    sch.power("GND", (g1[0], g1[1] + 2.54))
    for pin, name in [(11, "BUZZER"), (12, "SERVO_PWM")]:
        p = u1.pin(pin)
        sch.wire(p, (p[0] - 7.62, p[1]))
        sch.label(name, (p[0] - 7.62, p[1]), angle=180)
    for pin, name in [(23, "SDA"), (24, "SCL")]:
        p = u1.pin(pin)
        sch.wire(p, (p[0] + 7.62, p[1]))
        sch.label(name, (p[0] + 7.62, p[1]))
    for pin in NANO_NC:
        sch.no_connect(u1.pin(pin))
    sch.text("D8 = buzzer, D9 = servo\nA4 = SDA, A5 = SCL", (101.6, 154.94))

    # --- modulo BME280
    sch.text("SENSORE BME280 (I2C)", (165.1, 87.63), size=1.524, bold=True)
    j2 = sch.part("Connector_Generic:Conn_01x04", "J2", "BME280", (198.12, 101.6), footprint=FP_SOCK4,
                  fields={"Reference": (2.54, -2.54, "left", False), "Value": (2.54, 0, "left", False)})
    a, b = j2.pin(1), j2.pin(2)
    sch.wire(a, (a[0] - 5.08, a[1]))
    sch.power("+3V3", (a[0] - 5.08, a[1]), rot=90)
    sch.wire(b, (b[0] - 5.08, b[1]))
    sch.power("GND", (b[0] - 5.08, b[1]), rot=270)
    for pin, name in [(3, "SCL"), (4, "SDA")]:
        p = j2.pin(pin)
        sch.wire(p, (p[0] - 17.78, p[1]))
        sch.label(name, (p[0] - 17.78, p[1]), angle=180)
    sch.text("Zoccolo 1x4: 1 = VCC (3.3V), 2 = GND,\n3 = SCL, 4 = SDA", (165.1, 115.57))

    # --- servomotore
    sch.text("SERVOMOTORE", (165.1, 123.19), size=1.524, bold=True)
    j3 = sch.part("Connector_Generic:Conn_01x03", "J3", "SERVO", (198.12, 132.08), footprint=FP["hdr3"],
                  fields={"Reference": (2.54, -2.54, "left", False), "Value": (2.54, 0, "left", False)})
    a, b, s = j3.pin(1), j3.pin(2), j3.pin(3)
    sch.wire(a, (a[0] - 5.08, a[1]))
    sch.power("GND", (a[0] - 5.08, a[1]), rot=270)
    sch.wire(b, (b[0] - 5.08, b[1]))
    sch.power("+5V", (b[0] - 5.08, b[1]), rot=90)
    sch.wire(s, (s[0] - 17.78, s[1]))
    sch.label("SERVO_PWM", (s[0] - 17.78, s[1]), angle=180)
    c2 = vpart(sch, "Device:C_Polarized", "C2", "220uF 10V", (160.02, 132.08), FP["cp8"], side="left")
    sch.power("+5V", c2.pin(1))
    sch.power("GND", c2.pin(2))
    sch.text("1 = GND, 2 = +5V, 3 = segnale (D9)", (165.1, 142.24))

    # --- buzzer pilotato da transistor
    sch.text("BUZZER", (40.64, 130.81), size=1.524, bold=True)
    q1 = sch.part("Transistor_BJT:BC547", "Q1", "BC547", (81.28, 157.48), footprint=FP_TO92,
                  fields={"Reference": (5.08, -1.27, "left", False), "Value": (5.08, 1.27, "left", False)})
    bz = sch.part("Device:Buzzer", "BZ1", "Buzzer 5V", (86.36, 144.78), footprint=FP_BUZ,
                  fields={"Reference": (5.08, -1.27, "left", False), "Value": (5.08, 1.27, "left", False)})
    d2 = sch.part("Diode:1N4148", "D2", "1N4148", (78.74, 144.78), rot=270, footprint=FP_DO35,
                  fields={"Reference": (-2.54, -1.27, "right", False), "Value": (-2.54, 1.27, "right", False)})
    c, base, e = q1.pin(1), q1.pin(2), q1.pin(3)
    sch.power("GND", e)
    top = (bz.pin(1)[0], bz.pin(1)[1] - 2.54)
    sch.wire(bz.pin(1), top)
    sch.power("+5V", top)
    sch.wire(d2.pin(1), (d2.pin(1)[0], top[1]), top)
    sch.wire(bz.pin(2), c)
    sch.wire(d2.pin(2), (d2.pin(2)[0], d2.pin(2)[1] + 1.27), (c[0], d2.pin(2)[1] + 1.27))
    r2 = sch.part("Device:R", "R2", "1k", (68.58, base[1]), rot=90, footprint=FP["r"],
                  fields={"Reference": (0, -2.54, None, False), "Value": (0, 2.54, None, False)})
    r3 = vpart(sch, "Device:R", "R3", "10k", (73.66, base[1] + 3.81), FP["r"])
    sch.power("GND", r3.pin(2))
    sch.wire(r2.pin(2), r3.pin(1), base)
    sch.wire((r2.pin(1)[0] - 7.62, base[1]), r2.pin(1))
    sch.label("BUZZER", (r2.pin(1)[0] - 7.62, base[1]), angle=180)
    sch.text("Q1 pilota il buzzer (fino a ~100 mA)\nR3 lo tiene spento durante il reset", (40.64, 175.26))

    # --- fori di fissaggio
    for i in range(4):
        sch.part("Mechanical:MountingHole", "H%d" % (i + 1), "M3", (210.82 + 12.7 * i, 50.8), footprint=FP["hole"],
                 fields={"Reference": (0, -5.08, None, False), "Value": (0, 5.08, None, False)})
    sch.text("Fori di fissaggio M3", (205.74, 40.64))

    sch.text("\n".join([
        "NOTE",
        "- Batteria 7-12V su J1 (es. LiPo 2S 7.4V): il regolatore dell'Arduino genera i 5V per servo e buzzer.",
        "- Il servo e' alimentato dai 5V dell'Arduino: va bene un micro servo (SG90/MG90S).",
        "- Con il cavo USB collegato l'Arduino resta acceso anche con l'interruttore su OFF.",
    ]), (17.78, 198.12))
    return sch


# ---------------------------------------------------------------- PCB
PCB = {
    "folder": FOLDER, "name": NAME, "w": 80.0, "h": 58.0,
    "power_nets": ["GND", "+BATT", "/VIN", "+5V"],
    # le linguette di fissaggio dell'interruttore distano 0.25 mm dai suoi pin
    "clearance": 0.2,
    # posizione del pad 1 (x, y, rotazione)
    "place": {
        "H1": (3.5, 3.5, 0), "H2": (76.5, 3.5, 0), "H3": (3.5, 54.5, 0), "H4": (76.5, 54.5, 0),
        "U1": (35, 36, 90),            # connettore USB verso il bordo destro
        "J1": (8, 14, 90), "SW1": (6, 28, 90), "C1": (16, 22, 0),
        "D1": (12, 40, 0), "R1": (12, 47, 0),
        "J2": (45, 9, 90),             # BME280: pin allineati con A5/A4
        "J3": (62, 48, 90), "C2": (72, 44, 0),
        "BZ1": (36, 49, 0), "D2": (48.5, 40.5, 0), "Q1": (50, 45, 0),
        "R2": (48.5, 50, 0), "R3": (48.5, 54, 0),
    },
    "routes": [],
    "refs": {
        "H1": None, "H2": None, "H3": None, "H4": None, "J1": None, "J2": None, "J3": None,
        "U1": (52.78, 28.4), "SW1": (11.5, 26), "C1": (17.25, 27), "D1": (18.5, 40),
        "R1": (17.08, 47), "R2": (53.58, 50), "R3": (53.58, 54), "D2": (52.31, 40.5),
        "Q1": (58.5, 45), "BZ1": (39.8, 49), "C2": (73.75, 49.8),
    },
    "silk": [
        ("+", 4.8, 14, 1.0), ("-", 4.8, 12, 1.0), ("BATT 7-12V", 10, 7.8, 1.0),
        ("PWR", 3, 18.5, 0.8), ("LED ON", 12, 35, 0.8),
        ("3V3", 45, 5.8, 0.8), ("GND", 47.54, 13, 0.8), ("SCL", 50.08, 5.8, 0.8), ("SDA", 52.62, 13, 0.8),
        ("BME280", 61, 9, 1.0),
        ("G", 62, 51.5, 1.0), ("+", 64.54, 51.5, 1.0), ("S", 67.08, 51.5, 1.0), ("SERVO", 64.54, 54.3, 1.0),
        ("SCHEDA TEST ARDUINO", 20, 55, 1.0),
    ],
}


def main():
    d = os.path.join(ROOT, FOLDER)
    os.makedirs(d, exist_ok=True)
    schematic().save(os.path.join(d, NAME + ".kicad_sch"), NAME)
    project_file(os.path.join(d, NAME + ".kicad_pro"), NAME)
    print("scritto", os.path.join(FOLDER, NAME + ".kicad_sch"))
    if "--solo-schema" not in sys.argv:
        from genera_pcb import make_pcb
        make_pcb(PCB)


if __name__ == "__main__":
    main()
