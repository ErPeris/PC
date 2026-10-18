# Driver per 3 servomotori: progetto KiCad, due varianti

Il circuito prende l'alimentazione da una batteria LiPo 2S (7.4 V), la abbassa a 5 V per i servo e porta i tre segnali PWM del microcontrollore da 3.3 V a livello 5 V con un LM324.

| Cartella | Regolatore | Schema |
|---|---|---|
| `Variante_A_LDO/` | lineare LM7805 (TO-220) + diodo di protezione 1N4007 | `Servo_Driver_A_LDO.kicad_sch`, anteprima in `Servo_Driver_A_LDO.pdf` |
| `Variante_B_Buck/` | switching LM2596S-5.0 (TO-263) con componenti discreti | `Servo_Driver_B_Buck.kicad_sch`, anteprima in `Servo_Driver_B_Buck.pdf` |

Ogni cartella è un progetto KiCad autonomo: si apre con il file `.kicad_pro`. I file sono in formato KiCad 7 e si aprono anche con KiCad 8 e 9, che li convertono al primo salvataggio. I simboli sono incorporati nello schema e ogni componente ha già la sua impronta (footprint).

## Come si passa al PCB

1. Aprire il `.kicad_pro`, poi lo schema, e lanciare **Ispeziona → Controllo regole elettriche (ERC)**: non deve segnalare errori.
2. Aprire l'editor PCB e usare **Strumenti → Aggiorna PCB da schema (F8)**: arrivano tutte le impronte con le net.
3. Disegnare il contorno della scheda sul layer `Edge.Cuts`, posizionare i componenti e sbrogliare. Per le piste di potenza (+BATT, +5V, GND, e nella variante B anche SW) conviene una larghezza di almeno 1–1.5 mm.

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
| C3 | 100 nF | `C_Disc_D5.0mm…` | disaccoppiamento alimentazione LM324 (vicino ai pin 4 e 11) |
| J3, J4, J5 | header 1x3 2.54 mm | `PinHeader_1x03_P2.54mm_Vertical` | uscite servo: 1 = GND, 2 = +5 V, 3 = PWM 5 V |

**Come funziona il level shifter.** Il partitore R1/R2 genera VREF = 5 V × 10k / (22k + 10k) ≈ 1.56 V, collegata agli ingressi invertenti (−) di U2A, U2B e U2C. Ogni PWM a 3.3 V entra nell'ingresso non invertente (+). Con il PWM a 3.3 V (sopra la soglia) l'uscita va alta, con il PWM a 0 V va bassa. La quarta sezione, U2D, non è usata: è collegata come inseguitore con IN+ a massa, così non oscilla.

## Variante A: regolatore lineare LDO

| Rif. | Valore | Impronta | Funzione |
|---|---|---|---|
| U1 | LM7805 | `TO-220-3_Vertical` | regolatore 5 V (1 = IN, 2 = GND, 3 = OUT) |
| D1 | 1N4007 | `D_DO-41_SOD81_P10.16mm_Horizontal` | antiparallelo: catodo su IN, anodo su OUT |
| C4 | 330 nF | `C_Disc_D5.0mm…` | condensatore d'ingresso consigliato dal datasheet del 7805 |
| C5 | 100 nF | `C_Disc_D5.0mm…` | condensatore d'uscita consigliato dal datasheet |
| C6 | 100 µF 10 V elettrolitico | `CP_Radial_D6.3mm_P2.50mm` | riserva per i picchi di corrente dei servo |

## Variante B: buck converter LM2596S-5.0

| Rif. | Valore | Impronta | Funzione |
|---|---|---|---|
| U1 | LM2596S-5.0 | `TO-263-5_TabPin3` (SMD) | 1 = VIN, 2 = OUT, 3 = GND, 4 = FEEDBACK, 5 = ON/OFF |
| C4 | 100 µF 16 V elettrolitico | `CP_Radial_D8.0mm_P3.50mm` | condensatore d'ingresso sul pin VIN |
| D1 | 1N5822 (Schottky 3 A) | `D_DO-201AD_P15.24mm_Horizontal` | tra OUT (catodo) e GND (anodo) |
| L1 | 33 µH, ≥ 3 A | `L_Radial_D12.0mm_P5.00mm_Fastron_11P` | induttore sulla linea d'uscita |
| C5 | 220 µF 10 V low-ESR | `CP_Radial_D8.0mm_P3.50mm` | condensatore d'uscita sui 5 V |

Il pin FEEDBACK (4) è collegato ai 5 V dopo l'induttore. Il pin ON/OFF (5) va a GND, altrimenti il regolatore resta spento: la specifica non lo nomina, ma è necessario.

## Cose da sapere (da riportare anche nella relazione)

1. **L'LM324 a 5 V non arriva a 5 V in uscita.** Non è rail-to-rail: con alimentazione a 5 V l'uscita alta arriva a circa 3.5–3.8 V. Ai servo basta (accettano già segnali da 3.3 V), ma non sono 5 V pieni. Per averli si può montare un **MCP6004** o un **LMV324** nello stesso zoccolo DIP-14: hanno lo stesso pinout, quindi schema e PCB non cambiano.
2. **LM7805 e batteria 2S.** Il 7805 ha bisogno di circa 2 V di margine, quindi sotto ~7 V di batteria l'uscita scende sotto 5 V, e una LiPo 2S va da 8.4 V (carica) a ~6.4 V (scarica). L'**LM2940-5.0** ha lo stesso pinout TO-220 e un dropout di circa 0.5 V.
3. **Calore nella variante A.** Il regolatore lineare dissipa (Vin − 5 V) × I: con 7.4 V e 1 A sono circa 2.4 W, quindi serve un dissipatore sul TO-220. Il 7805 eroga al massimo ~1.5 A. Tre servo che si muovono insieme possono superarlo (ogni SG90 in stallo assorbe ~0.7 A, i servo più grandi anche 2 A). La variante B arriva a 3 A con molto meno calore.
4. **Layout della variante B.** L'anello C4 → U1 → D1 → L1 → C5 deve essere il più corto possibile, con un piano di massa. L'impronta di L1 è indicativa: va controllata sul componente acquistato.
5. **Polarità della batteria.** Su J1 il pin 1 è il + e il pin 2 è la massa. I connettori JST-PH delle LiPo non hanno tutti la stessa polarità: va controllata prima del primo collegamento e scritta sulla serigrafia. Non è prevista una protezione contro l'inversione di polarità.
6. **Aggiunte rispetto alla specifica.** R3–R5 (pull-down), C2 (filtro di VREF), C3 (disaccoppiamento) e, nella variante A, C4–C6 non sono richiesti dalla specifica. Sono pratica comune e si possono togliere senza cambiare il funzionamento base.

## Rigenerare gli schemi

Gli schemi sono stati generati da `tools/genera_schemi.py`, che serve solo a ricrearli da zero. Per modificarli basta lavorare direttamente in KiCad. `tools/verifica_netlist.py` confronta la netlist esportata con i collegamenti richiesti:

```sh
python3 tools/genera_schemi.py
kicad-cli sch export netlist --format kicadxml -o A.xml Variante_A_LDO/Servo_Driver_A_LDO.kicad_sch
python3 tools/verifica_netlist.py A A.xml
```
