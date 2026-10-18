# Scheda di test con Arduino Nano

Scheda con un Arduino Nano come controllo, collegato a:
- un modulo BME280 (temperatura, umidità, pressione);
- un buzzer;
- un servomotore.

Un interruttore accende tutta la scheda e un LED si accende quando l'interruttore è su ON. Tutti i componenti sono a foro passante.

| File | Contenuto |
|---|---|
| `Scheda_Test_Arduino.kicad_pro` | progetto KiCad da aprire |
| `Scheda_Test_Arduino.kicad_sch` / `.pdf` | schema |
| `Scheda_Test_Arduino.kicad_pcb` / `_PCB.pdf` | circuito stampato |
| `gerber/` | Gerber e forature per ordinare la scheda |
| `firmware/test_scheda/test_scheda.ino` | sketch di prova |

Come per il driver servo, i file sono in formato KiCad 7 e si aprono in KiCad 9.

## Come funziona

- **Alimentazione:** la batteria (7–12 V, per esempio la stessa LiPo 2S da 7.4 V) entra dal connettore JST J1. Passa dall'interruttore SW1 e arriva al pin VIN dell'Arduino. Il regolatore dell'Arduino genera i 5 V per servo e buzzer e i 3.3 V per il sensore. C1 filtra la tensione dopo l'interruttore.
- **LED di accensione:** D1 con R1 da 1 kΩ è collegato dopo l'interruttore, quindi si accende solo con l'interruttore su ON. Assorbe circa 5 mA a 7.4 V.
- **BME280:** si collega via I2C con SDA su A4 e SCL su A5. È alimentato a 3.3 V, che va bene sia per i moduli solo 3.3 V sia per quelli con regolatore a 5 V.
- **Servo:** il segnale arriva da D9, l'alimentazione dai 5 V dell'Arduino. C2 da 220 µF assorbe i picchi di corrente del motore.
- **Buzzer:** è pilotato da D8 tramite il transistor Q1 (BC547), perché un buzzer può assorbire più corrente di quella che un pin dell'Arduino regge bene.
  - R2 limita la corrente di base.
  - R3 tiene il transistor spento durante il reset.
  - D2 protegge Q1 dalle sovratensioni dei buzzer magnetici.

  Funziona sia con buzzer attivi sia passivi da 5 V.

| Pin Arduino | Collegato a |
|---|---|
| VIN | batteria dopo l'interruttore |
| 5V | servo (+), buzzer (+) |
| 3V3 | BME280 VCC |
| A4 / A5 | BME280 SDA / SCL |
| D8 | buzzer (base di Q1 tramite R2) |
| D9 | segnale del servo |

## Componenti

| Rif. | Valore | Impronta | Note |
|---|---|---|---|
| U1 | Arduino Nano | `Module:Arduino_Nano` | montato su due strip femmina 1x15, con la USB verso il bordo |
| J1 | JST-PH 2 pin | `JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical` | batteria: 1 = +, 2 = GND |
| SW1 | interruttore a slitta SPDT | `SW_Slide_SPDT_Straight_CK_OS102011MS2Q` | 3 pin a passo 2 mm |
| D1 | LED rosso 5 mm | `LED_D5.0mm` | spia di accensione |
| R1 | 1 kΩ | `R_Axial_DIN0207…` | resistenza del LED |
| C1 | 100 µF 16 V elettrolitico | `CP_Radial_D6.3mm_P2.50mm` | filtro dopo l'interruttore |
| J2 | strip femmina 1x4 | `PinSocket_1x04_P2.54mm_Vertical` | BME280: 1 = VCC, 2 = GND, 3 = SCL, 4 = SDA |
| J3 | strip maschio 1x3 | `PinHeader_1x03_P2.54mm_Vertical` | servo: 1 = GND, 2 = +5 V, 3 = segnale |
| C2 | 220 µF 10 V elettrolitico | `CP_Radial_D8.0mm_P3.50mm` | riserva per il servo |
| BZ1 | buzzer 5 V Ø12 mm | `Buzzer_12x9.5RM7.6` | piedini a passo 7.6 mm |
| Q1 | BC547 | `TO-92_Inline_Wide` | piedini a passo 2.54 mm, più facili da saldare |
| R2 | 1 kΩ | `R_Axial_DIN0207…` | base di Q1 |
| R3 | 10 kΩ | `R_Axial_DIN0207…` | tiene Q1 spento durante il reset |
| D2 | 1N4148 | `D_DO-35_SOD27_P7.62mm_Horizontal` | diodo di protezione sul buzzer |
| H1–H4 | foro M3 | `MountingHole_3.2mm_M3` | fissaggio |

## Il PCB

- **Scheda:** 80 × 58 mm, 2 strati, 4 fori M3 negli angoli.
- **Massa:** un piano di rame su tutte e due le facce.
- **Piste:** le alimentazioni (batteria, VIN, +5V) sono larghe 0.8 mm, i segnali 0.4 mm.
- **Disposizione:**
  - a sinistra, batteria, interruttore e LED;
  - al centro, l'Arduino, con la USB raggiungibile dal bordo destro;
  - in alto, lo zoccolo del BME280;
  - in basso, buzzer, transistor e connettore del servo.
- **Serigrafia:** polarità della batteria, nomi dei pin del BME280 (3V3, GND, SCL, SDA) e del servo (G, +, S).

Il DRC è pulito: 0 errori, 0 pad scollegati. Ho controllato i Gerber con un visualizzatore.

**Dati per l'ordine:**

| Parametro | Valore |
|---|---|
| Strati | 2 |
| Dimensioni | 80 × 58 mm |
| Spessore | 1.6 mm |
| Rame | 1 oz |
| Finitura | HASL |
| Pista minima | 0.4 mm |
| Distanza minima | 0.2 mm |
| Foro minimo | 0.75 mm |

La distanza minima è 0.2 mm invece di 0.3 mm per un solo motivo: nell'impronta dell'interruttore le linguette di fissaggio distano 0.25 mm dai pin. È comunque ampiamente nei limiti dei produttori economici, che arrivano a 0.1 mm.

## Cose da sapere

1. **Corrente del servo.** Il servo prende i 5 V dal regolatore dell'Arduino, che regge circa 0.5 A. Va bene un micro servo (SG90, MG90S). Un servo più grande va alimentato a parte, per esempio con il driver del progetto 1.
2. **Interruttore.** Molti interruttori a slitta piccoli sono dati per 0.1–0.5 A. Conviene sceglierne uno da almeno 0.5 A, con 3 pin a passo 2 mm.
3. **Ordine dei pin del BME280.** Lo zoccolo J2 segue l'ordine più comune dei moduli GY-BME280 a 4 pin: VCC, GND, SCL, SDA. Va controllato sul proprio modulo. I moduli a 6 pin (VCC, GND, SCL, SDA, CSB, SDO) entrano con i primi 4 pin, lasciando fuori CSB e SDO.
4. **Livelli I2C.** Il modulo porta SDA e SCL a 3.3 V, che l'Arduino a 5 V legge come livello alto. È il collegamento usato normalmente con questi moduli.
5. **USB.** Con il cavo USB collegato l'Arduino resta acceso anche con l'interruttore su OFF. Il LED invece resta spento, perché è sul lato batteria.
6. **Batteria.** Non c'è protezione contro l'inversione di polarità: va controllata la polarità del connettore prima di collegarlo (pin 1 = +, come indicato sulla serigrafia).

## Sketch di prova

`firmware/test_scheda/test_scheda.ino` fa tre cose:
- all'accensione suona un beep;
- ogni ciclo stampa temperatura, umidità e pressione sul monitor seriale (9600 baud);
- muove il servo tra 0°, 90° e 180°.

Richiede la libreria **Adafruit BME280 Library** (dal gestore librerie dell'IDE). La libreria Servo è già inclusa nell'IDE.

L'ho compilato per Arduino Nano (ATmega328) senza errori né avvisi. Non avendo qui le librerie Servo e Adafruit, ho usato interfacce con le stesse firme: va ricompilato una volta nell'IDE con le librerie vere.

## Rigenerare i file

```sh
FREEROUTING_JAR=freerouting-2.4.1-executable.jar JAVA=java-25 python3 tools/genera_scheda_arduino.py
```

Lo script si lancia dalla cartella principale del repository. Rigenerando, le modifiche fatte a mano in KiCad vanno perse.
