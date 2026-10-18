# Driver per 3 servomotori: progetto KiCad, due varianti

> Nel repository c'è anche la **scheda di test con Arduino Nano** (progetto 3): è nella cartella [`Scheda_Test_Arduino/`](Scheda_Test_Arduino/README.md), che ha il suo README.

Il circuito prende l'alimentazione da una batteria LiPo 2S (7.4 V), la abbassa a 5 V per i servo e porta i tre segnali PWM del microcontrollore da 3.3 V a livello 5 V con un LM324. Tutti i componenti sono a foro passante (THT).

| Cartella | Regolatore | File |
|---|---|---|
| `Variante_A_LDO/` | lineare LM7805 (TO-220) + diodo di protezione 1N4007 | schema `Servo_Driver_A_LDO.kicad_sch`, PCB `Servo_Driver_A_LDO.kicad_pcb`, anteprime `Servo_Driver_A_LDO.pdf` e `Servo_Driver_A_LDO_PCB.pdf` |
| `Variante_B_Buck/` | switching LM2596T-5.0 (TO-220-5) con componenti discreti | schema `Servo_Driver_B_Buck.kicad_sch`, PCB `Servo_Driver_B_Buck.kicad_pcb`, anteprime `Servo_Driver_B_Buck.pdf` e `Servo_Driver_B_Buck_PCB.pdf` |

Ogni cartella è un progetto KiCad autonomo: si apre con il file `.kicad_pro`. I file sono stati creati con KiCad 7 e si aprono in KiCad 9, che li converte al nuovo formato al primo salvataggio. Al primo salvataggio KiCad 9 può avvisare che il file viene aggiornato: va bene.

## Il PCB

- **Scheda**: 80 × 60 mm, 2 strati, 4 fori di fissaggio M3 negli angoli.
- **Massa**: un piano di massa (GND) su entrambe le facce collega tutti i pin di massa.
- **Piste di potenza**: +BATT, +5V verso i servo e, nella variante B, il nodo di commutazione SW sono tracciate a mano, larghe 1.5 mm.
- **Segnali**: sbrogliati con l'autorouter Freerouting. Le piste sono larghe 0.4 mm e il resto della +5V 0.8 mm, con distanze minime di 0.3 mm.
- **Classi di net**: sono nel `.kicad_pro`. La classe `Power` comprende GND, +BATT, +5V e SW.
- **Disposizione**:
  - in alto, la batteria (J1) a sinistra e lo stadio di alimentazione;
  - in basso a sinistra, l'ingresso PWM (J2) con le resistenze;
  - al centro, l'LM324 su zoccolo DIP-14;
  - a destra, le tre uscite servo (J3–J5).
- **Serigrafia**: polarità della batteria (+/−), pin del connettore PWM (G, 1, 2, 3) e pin di ogni servo (G, +, S).
- **DRC**: senza errori e senza pad scollegati.

Il file `.kicad_dru` contiene una sola regola: accetta un solo raggio di collegamento termico per faccia, perché i pad di massa sono collegati al piano su tutte e due le facce. Senza questa regola il DRC segnala un pad di R5.

**Prima di mandare la scheda in produzione:**
1. In KiCad 9 lanciare il controllo regole elettriche (ERC) sullo schema e il controllo regole di progettazione (DRC) sul PCB, con la verifica di coerenza tra schema e PCB attiva.
2. Controllare le impronte di L1 e dei condensatori elettrolitici sui componenti acquistati (diametro e passo dei piedini).
3. Nella variante A lasciare spazio al dissipatore dietro la linguetta di U1, verso il bordo superiore.
4. Se il PCB è stato modificato, rigenerare i Gerber (vedi sotto).

Per modificare il PCB a mano conviene ricaricare le zone di massa con il tasto **B** dopo ogni modifica.

## File per ordinare le schede

Nella cartella `produzione/` ci sono:

| File | Contenuto |
|---|---|
| `Gerber_Servo_Driver_A_LDO.zip` | Gerber e forature della variante A, da caricare così com'è sul sito del produttore |
| `Gerber_Servo_Driver_B_Buck.zip` | Gerber e forature della variante B |
| `Progetto_KiCad_Driver_3_Servo.zip` | progetto KiCad completo delle due varianti (schemi, PCB, regole, PDF, Gerber, README) |
| `Gerber_Scheda_Test_Arduino.zip` | Gerber e forature della scheda di test con Arduino Nano |
| `Progetto_KiCad_Scheda_Test_Arduino.zip` | progetto KiCad completo della scheda di test, con lo sketch di prova |

Ogni zip Gerber contiene:
- rame lato componenti e lato saldature (`.gtl`, `.gbl`);
- maschera di saldatura (`.gts`, `.gbs`);
- serigrafia (`.gto`, `.gbo`);
- contorno della scheda (`.gm1`);
- forature metallizzate e non metallizzate (`-PTH.drl`, `-NPTH.drl`, Excellon in mm);
- il file di job (`.gbrjob`).

**Dati da inserire nell'ordine** (JLCPCB, PCBWay e simili):

| Parametro | Valore |
|---|---|
| Strati | 2 |
| Dimensioni | 80 × 60 mm |
| Spessore | 1.6 mm |
| Rame | 1 oz |
| Pista minima / distanza minima | 0.4 mm / 0.3 mm |
| Foro minimo | 0.4 mm (via) |
| Finitura | HASL |
| Colore | a piacere |

Questi valori rientrano nelle opzioni standard di tutti i produttori economici.

**Per rigenerare i Gerber dopo una modifica**, in KiCad 9 dall'editor PCB:
1. Usare **File → Fabbricazione → Gerber**. Strati da includere: F.Cu, B.Cu, F.Silkscreen, B.Silkscreen, F.Mask, B.Mask, Edge.Cuts.
2. Nella stessa finestra usare **Genera file di foratura**: Excellon, millimetri, PTH e NPTH separati.
3. Comprimere i file in uno zip.

Da riga di comando:

```sh
kicad-cli pcb export gerbers -o gerber/ --layers F.Cu,B.Cu,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts \
    --exclude-value --subtract-soldermask Servo_Driver_A_LDO.kicad_pcb
kicad-cli pcb export drill -o gerber/ --format excellon --excellon-units mm --excellon-separate-th \
    Servo_Driver_A_LDO.kicad_pcb
```

## Parte comune alle due varianti

| Rif. | Valore | Impronta | Funzione |
|---|---|---|---|
| J1 | JST-PH 2 pin | `JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical` | ingresso batteria (1 = +, 2 = GND) |
| C1 | 100 µF 16 V elettrolitico | `CP_Radial_D6.3mm_P2.50mm` | filtro in parallelo all'ingresso |
| J2 | header 1x4 2.54 mm | `PinHeader_1x04_P2.54mm_Vertical` | dal microcontrollore: 1 = GND, 2/3/4 = PWM1/2/3 a 3.3 V |
| U2 | LM324 | `DIP-14_W7.62mm` | 3 comparatori (U2A, U2B, U2C) come level shifter |
| R1 | 22 kΩ | `R_Axial_DIN0207…` | partitore di riferimento (lato +5 V) |
| R2 | 10 kΩ | `R_Axial_DIN0207…` | partitore di riferimento (lato GND) |
| C2 | 100 nF | `C_Disc_D5.0mm…` | filtro sulla tensione di riferimento VREF |
| R3, R4, R5 | 100 kΩ | `R_Axial_DIN0207…` | pull-down sugli ingressi PWM |
| C3 | 100 nF | `C_Disc_D5.0mm…` | disaccoppiamento alimentazione LM324 (vicino al pin 4) |
| J3, J4, J5 | header 1x3 2.54 mm | `PinHeader_1x03_P2.54mm_Vertical` | uscite servo: 1 = GND, 2 = +5 V, 3 = PWM 5 V |
| H1–H4 | foro M3 | `MountingHole_3.2mm_M3` | fissaggio della scheda |

**Come funziona il level shifter.** Il partitore R1/R2 genera VREF = 5 V × 10k / (22k + 10k) ≈ 1.56 V, collegata agli ingressi invertenti (−) di U2A, U2B e U2C. Ogni PWM a 3.3 V entra nell'ingresso non invertente (+). Con il PWM a 3.3 V (sopra la soglia) l'uscita va alta, con il PWM a 0 V va bassa. La quarta sezione, U2D, non è usata: è collegata come inseguitore con IN+ a massa, così non oscilla.

## Variante A: regolatore lineare LDO

| Rif. | Valore | Impronta | Funzione |
|---|---|---|---|
| U1 | LM7805 | `TO-220-3_Vertical` | regolatore 5 V (1 = IN, 2 = GND, 3 = OUT) |
| D1 | 1N4007 | `D_DO-41_SOD81_P10.16mm_Horizontal` | antiparallelo: catodo su IN, anodo su OUT |
| C4 | 330 nF | `C_Disc_D5.0mm…` | condensatore d'ingresso consigliato dal datasheet del 7805 |
| C5 | 100 nF | `C_Disc_D5.0mm…` | condensatore d'uscita consigliato dal datasheet |
| C6 | 100 µF 10 V elettrolitico | `CP_Radial_D6.3mm_P2.50mm` | riserva per i picchi di corrente dei servo |

## Variante B: buck converter LM2596-5.0

| Rif. | Valore | Impronta | Funzione |
|---|---|---|---|
| U1 | LM2596T-5.0 | `TO-220-5_P3.4x3.7mm_StaggerOdd_Lead3.8mm_Vertical` | 1 = VIN, 2 = OUT, 3 = GND, 4 = FEEDBACK, 5 = ON/OFF |
| C4 | 100 µF 16 V elettrolitico | `CP_Radial_D8.0mm_P3.50mm` | condensatore d'ingresso sul pin VIN |
| D1 | 1N5822 (Schottky 3 A) | `D_DO-201AD_P15.24mm_Horizontal` | tra OUT (catodo) e GND (anodo) |
| L1 | 33 µH, ≥ 3 A | `L_Radial_D12.0mm_P5.00mm_Fastron_11P` | induttore sulla linea d'uscita |
| C5 | 220 µF 10 V low-ESR | `CP_Radial_D8.0mm_P3.50mm` | condensatore d'uscita sui 5 V |

La specifica chiede l'**LM2596S**-5.0, che esiste solo in contenitore SMD (TO-263). Visto che la scheda è tutta a foro passante, ho usato l'**LM2596T**-5.0: è lo stesso integrato in contenitore TO-220-5, con gli stessi pin. Va comprata la versione con i piedini sfalsati per il montaggio verticale. Se il professore vuole proprio la versione "S", basta cambiare simbolo e impronta di U1.

Il pin FEEDBACK (4) è collegato ai 5 V dopo l'induttore. Sul PCB la pista passa sul lato inferiore fino al pin 2 di L1. Il pin ON/OFF (5) va a GND, altrimenti il regolatore resta spento: la specifica non lo nomina, ma è necessario.

## Cose da sapere (da riportare anche nella relazione)

1. **L'LM324 a 5 V non arriva a 5 V in uscita.** Non è rail-to-rail: con alimentazione a 5 V l'uscita alta arriva a circa 3.5–3.8 V. Ai servo basta (accettano già segnali da 3.3 V), ma non sono 5 V pieni. Per averli si può montare un **MCP6004** o un **LMV324** nello stesso zoccolo DIP-14: hanno lo stesso pinout, quindi schema e PCB non cambiano.
2. **LM7805 e batteria 2S.** Il 7805 ha bisogno di circa 2 V di margine, quindi sotto ~7 V di batteria l'uscita scende sotto 5 V, e una LiPo 2S va da 8.4 V (carica) a ~6.4 V (scarica). L'**LM2940-5.0** ha lo stesso pinout TO-220 e un dropout di circa 0.5 V.
3. **Calore nella variante A.** Il regolatore lineare dissipa (Vin − 5 V) × I: con 7.4 V e 1 A sono circa 2.4 W, quindi serve un dissipatore sul TO-220. Il 7805 eroga al massimo ~1.5 A. Tre servo che si muovono insieme possono superarlo (ogni SG90 in stallo assorbe ~0.7 A, i servo più grandi anche 2 A). La variante B arriva a 3 A con molto meno calore.
4. **Layout della variante B.** L'anello C4 → U1 → D1 → L1 → C5 è tenuto corto, con il piano di massa sotto. L'impronta di L1 è indicativa: va controllata sul componente acquistato.
5. **Polarità della batteria.** Su J1 il pin 1 è il + e il pin 2 è la massa, come indicato sulla serigrafia. I connettori JST-PH delle LiPo non hanno tutti la stessa polarità: va controllata prima del primo collegamento. Non è prevista una protezione contro l'inversione di polarità.
6. **Aggiunte rispetto alla specifica.** R3–R5 (pull-down), C2 (filtro di VREF), C3 (disaccoppiamento), i fori di fissaggio e, nella variante A, C4–C6 non sono richiesti dalla specifica. Sono pratica comune e si possono togliere senza cambiare il funzionamento base.

## Rigenerare i file

Gli schemi e i PCB sono stati generati dagli script in `tools/`, che servono solo a ricrearli da zero. Per modificarli basta lavorare direttamente in KiCad. Rigenerando, le modifiche fatte a mano vanno perse.

```sh
python3 tools/genera_schemi.py      # schemi (.kicad_sch)
kicad-cli sch export netlist --format kicadxml -o A.xml Variante_A_LDO/Servo_Driver_A_LDO.kicad_sch
python3 tools/verifica_netlist.py A A.xml   # confronta i collegamenti con la specifica
FREEROUTING_JAR=freerouting-2.4.1-executable.jar JAVA=java-25 python3 tools/genera_pcb.py   # PCB
```

`genera_pcb.py` usa il modulo Python `pcbnew` di KiCad 7 e [Freerouting](https://freerouting.app) 2.4.1, che richiede Java 25.
