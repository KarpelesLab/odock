# odock-10: front block layout notes (card reader + USB-A)

Script: `hardware/odock-10/layout/front.py`. It owns 70 refs:
- Card reader: C901–C920, D901, J901, J902, R901–R907, U901, Y901.
- USB-A: C701–C716, D701–D704, J701, J702, R701–R710, U701–U706.

The board is 130 × 89 mm and the front edge is at y = 139. Mounting hole H3 is at (104, 135), and every courtyard is at
least 4 mm from it.

## Regions and deviations (other blocks must know)

1. **Regions:**

   | Rectangle | What it is |
   |---|---|
   | (100,112)–(180,139.5) | The main front block |
   | (100,108)–(140,139.5) | The card-reader column. The SD-111 courtyard is 31.1 mm deep and reaches y 108.2. |
   | (180,121.5)–(198,139.5) | The microSD corner |

   - All three extend 0.5 mm past the edge because the edge connectors' courtyards overhang it.
   - **The corner is 2.5 mm taller than agreed** (the agreed corner started at y 124). The DM3AT courtyard is 17.15 mm
     deep, so with the card face flush at y 139 it starts at y 121.9. The right block must keep (180–198, 121.5–124)
     clear too, on top only. The bottom there is only used by C915/C916.
   - Also, the J902 contact-row vias sit just north of y 122.7, at x 183–192 (see the microSD bus).
2. **J902 (microSD) is on top in the corner, at x 189**, card face flush at y 139 (the body front line, y_local +8.71).
   Its contact row is at the back, y 122.74, x 183.2–191.85.
3. **USB-A positions:** J701 is at x 151.5 (floorplan 150) and J702 at x 170.5 (floorplan 168). The SD courtyard ends
   at x 139.8, and the shift leaves room for each port's power stage on the left of its connector, where VBUS pin 1 is.
4. **GL3224 (U901) and all card-reader passives are on the bottom**, under the SD socket. The top side there is
   entirely the socket. U901 is a QFN-48 0.85 mm, which falls under the brief's "DFN-class" bottom rule.
   - U901 stays under the SD socket. That keeps the SD bus at 6–22 mm and the hub pairs short. The microSD bus is long
     wherever U901 sits, because J902 is now 60 mm away.

## Placement summary

| Item | Position | Notes |
|---|---|---|
| J901 SD-111 | (124.0, 120.33) top, rot 0 | Card enters from +y. The body front line (y_local +18.67) is at y 139. Contact row is at y 109.23, x 110.8 (WP) to 133.3 (D2). NPTH pegs at (111.8, 133.53) and (136.0, 133.53). |
| J902 DM3AT | (189.0, 130.29) top, rot 0 | Opening faces +y (front). Contact row at y 122.74: CDZ 183.2, D1 184.15, D0 185.25, GND 186.35, CLK 187.45, VCC 188.55, CMD 189.65, D3 190.75, D2 191.85. C915/C916 are on the bottom under it. |
| U901 GL3224 | (133.0, 117.5) bottom, rot 270 | Sides listed below. |
| Y901 25 MHz | (136.85, 125.3) bottom | Just below pins 13/14. XI pad (137.7, 124.2) with C919 on its right; XO pad (136.0, 126.4) with C920 below. |
| J701 / J702 | x 151.5 / 170.5, y 125.52, top | The footprint marker "CONNECTOR EDGE = BOARD EDGE" (y_local 13.48) sits on y 139. THT pins at y 123.72 / 125.22, shell tabs at y 127.22. |
| D701 / D703 TPD4E02B04 | (jx, 120.75) top | Flow-through, directly above the SS pin row. Pad order TXP, TXN, GND, RXP, RXN matches connector pins 9, 8, 7, 6, 5. |
| D702 / D704 USBLC6 | (jx + 4, 119.75) top | Right of each SS channel. |
| Port power, top | Left of each connector | POSCAP C701/C709 at (jx − 9, 117), with the + pad at y 120.1 next to VBUS pin 1 (jx − 3.5, 125.22). TPS2553 at (jx − 4.2, 114.3): OUT pin 6 faces left toward the POSCAP, IN pin 1 faces right. C702/C703 (10u/100n VBUS) sit between the TPS and pin 1. |
| Port power, bottom | Under the TPS | 30 mΩ shunt (jx − 3.9, 113.1) directly under TPS IN, INA180 right below it (Kelvin), LVC1G32 and the 0402s. |

U901 side orientation:

| U901 side | Pins | Points toward |
|---|---|---|
| +x | USB, 1–12 | The pair channel |
| −y | SD, 37–42 | The SD contact row |
| −x | microSD, 27–32 | Via escapes to L3 (see the microSD bus) |
| +y | Power and crystal, 13–24 | The front |

## Routing intent

### Card-reader USB (hub port 1: 5 Gbps SS + USB2), no ESD (embedded link)
- U901 USB pins on the +x side, top to bottom: DN/DP at y 116.25/116.75, AVDD33 6, TXN/TXP at 117.75/118.25, AVDD12 9,
  RXN/RXP at 119.25/119.75.
- Escape to the right on B.Cu and turn up, nested so nothing crosses:
  - DP/DN innermost, going up at x ≈ 137.5;
  - TX next, through the 100 nF AC caps C918 (TXN) and C917 (TXP) at x 139.35/140.6, y 114;
  - RX outermost, at x ≈ 141.3.
- Change to **L3 stripline** with GND stitching vias at y ≈ 112.5. From there run up and right under the SD-socket and
  power-block strip into hubrails, to the USB7206C port 1 at about (155–165, 90). Keep x 137.3–141.5, y 112–120 free of
  other copper on B.Cu.
- Decaps C905 (pin 6) and C909 (pin 9) sit directly at their pins, between the pair escapes. The router may nudge them
  by ≤ 0.3 mm or neck the pin stubs. Keep the TX pair in the gap between C905 and C909, and the RX pair between C909 and
  C904.
- 90 Ω differential for USB, with intra-pair skew < 0.1 mm. Each SS pair is about 35–40 mm to the hub. CR_SS_TX* (the hub
  TX) already has its 220 nF on the hub side.

### SD bus (slot 1) and microSD bus (slot 2): SDR104, up to 208 MHz, no termination fitted
- **SD:** pins 37–42 are on U901's top edge (y 114.1, x 130.25–132.75). The pads are on F.Cu at y 109.23.
  - Run on **L3** (between the L2 GND and L4 planes): a via at each pin escape, then a via next to each SD pad.
  - Nesting: D1 (leftmost pin) goes farthest left (pad x 114.15), with the lowest horizontal. Then D0, CLK, CMD, D3, D2.
    Nothing crosses.
  - Raw lengths are about D1 21, D0 20, CLK 15, CMD 8, D3 6.5, D2 5.5 mm. **Meander CMD/D0–D3 to match CLK within
    ±1 mm, and CLK to the longest** (target about 22 mm).
- **microSD (long run, about 80–90 mm):** pins 27–32 are on U901's −x edge (x 129.6, y 116.75–119.25). J902's contacts
  are at y 122.74, x 183.2–191.85, on F.Cu.
  - Escape each pin with a via just outside the chip's −x edge, at x ≈ 128.5, between C912 and C910.
  - Run on **L3** (stripline between L2 GND and L4) south to y ≈ 130, staying at x ≤ 134 to keep off Y901.
  - Turn east in a **band at y 129.5–132.5**. That runs:
    - under the SD socket's front half;
    - north of the SD-111 peg hole at (136.0, 133.53);
    - **south of every USB-A THT pin and shell tab** (the J701/J702 pins sit at y 123.7–127.2, tabs at 127.22 ± 1).
    - The band passes under the USB-A bodies, where there are no holes.
  - Then go up north at x ≈ 180 (between J702's courtyard at 178.8 and J902's at 181.5) to y ≈ 121.5. Fan east along the
    north side of J902's contact row, with a via next to each contact.
  - CR_USD_CDZ travels with the bus. CR_USD_VCC also goes with it as a ≥ 0.4 mm trace (or an L4 strip), from pin 24 to
    J902 pin 4. C915/C916 sit on the bottom right under J902 pin 4, at (188.55, 124–125.5).
  - Nest the bus so nothing crosses: chip pin order top→bottom is D2, D3, CMD, CLK, D0, D1, and the pad order
    east→west is D2, D3, CMD, VCC, CLK, GND, D0, D1, CDZ.
  - Raw length is about 80 (D1) to 90 (D2) mm. **Length-match CLK/CMD/D0–D3 to the longest, about 90 mm, ±1 mm**
    (skew < 6 ps). 40 Ω single-ended (SDR104 practice; 50 Ω acceptable), 3W spacing (≥ 0.3 mm on L3), and keep CLK
    2W further from the DAT lines.
  - Solid L2 GND and L4 reference along the whole run. GND stitching vias every 5 mm on both sides of the band.
  - The open card_reader issue still applies: if SDR104 margins are poor on the bench, fit the CLK series resistor
    (22–33 Ω) at the U901 pin-29 escape, or limit slot 2 to SDR50.
- Keep a solid L2 GND under both buses. Optional 22–33 Ω series R on CLK (card_reader open issue 5): no footprint exists
  yet. If one is added, put it at the CLK pin escape: SD CLK pin 39 at (131.25, 114.1) and microSD CLK pin 29 at
  (129.6, 118.25). For the long microSD bus this is recommended.
- Card VCC:
  - CR_SD_VCC: U901 pin 23 → C913/C914 (bottom, at (123.3–125.5, 112.6)) → via → J901 pin 4 (123.28, 109.23).
    Trace ≥ 0.4 mm.
  - CR_USD_VCC: see the microSD bus.
- Detect and WP are slow and can go on any layer:
  - SD1_CDZ: pin 1 (USB side, top) → J901 pad 10 (126.6, 109.2).
  - SD1_WP: pin 2 → pad 11 (110.8, 109.2).
  - CR_USD_CDZ: pins 35+36 → J902 pad 9 (183.2, 122.74). It runs with the microSD bus.

### Card-reader power and clock
- +5V reaches VBUS pin 22 (C901 10u, C902 100n just below the chip) through a via from the L4 +5V plane. CR_3V3 and
  CR_1V2 are **local nets**: short B.Cu traces or a small B.Cu pour around U901, never joined to +3V3.
  - C903 (10u) sits at pin 25 and C910 at pin 26. C911/C908 sit above pins 43/44, at the NC pins 45–48. C907/C912 are at
    pins 34/33, and C906 is at pin 15.
- Thermal: up to about 1 W in U901. Put a 5×5 array of 0.3 mm vias in the 5.1 mm EP to L2/L5 GND, and a GND pour on F.Cu
  under the SD socket footprint area (away from the socket's own pads) as a heat spreader.
- Crystal: keep XI/XO (pins 13 → XI pad top-right, 14 → XO pad bottom-left) under 4 mm, guarded with GND. Nothing
  high-speed may run under Y901 on L3/L6. The USB pairs stay at x ≥ 137.3 and y ≤ 120, above the crystal.

### USB-A SS (10 Gbps) and USB2, ports on hub ports 2/3
- The pairs come down from hubrails at y ≈ 108–112 into **clear channels**: x 149.5–153.5 for port 1 and x 168.5–172.5 for
  port 2. No parts are in these channels on either side.
- Run on F.Cu straight down to the TPD4E02B04: TX on pads 1/10 and 2/9, RX on 4/7 and 5/6. Flow-through under the
  package, then fan out to the THT pins at y 123.72 (2 mm pitch). 85–90 Ω, skew < 0.1 mm, GND vias next to every layer
  change.
- No AC caps on this board for either direction. Hub TX has 220 nF on usb_hub; device TX caps are in the plug.
- USB2: hub → D702/D704 on F.Cu (pins 1/6 DP, 3/4 DN). Then via to **L3** and run to the connector's THT pins 2 (DN) and
  3 (DP) at y 125.22, entering between the SS pins on L3.

### USB-A power (each port ≤ 1.8 A)
- +5V (from hubrails/power, L4 plane) → R704/R709 shunt on B.Cu at (jx − 3.9, 113.1) → USBAx_SW_IN.
  - SW_IN reaches TPS IN pin 1 (top, directly above) through ≥ 3 vias, with C704/C705 (bottom) on the same node.
  - All of these are ≥ 1 mm traces or pours.
- **Kelvin:** INA180 IN+ (pin 3, +5V) and IN− (pin 4, SW_IN) connect to the inner pad edges of the shunt with separate
  thin traces, not through the pour.
- +5V_USBAx is a **F.Cu pour**: TPS OUT pin 6 → POSCAP + pad (jx − 9, 120.1) → C702/C703 → J pin 1 (jx − 3.5, 125.22).
  - It enters pin 1 from the left at y ≈ 125.2, between SS pin 9 and the shell tab.
  - It is also tied to D702/D704 pin 5 (VBUS clamp).
- Give TPS2553 IN/OUT copper (0.25 W each), with 4–6 thermal vias on GND pin 2.
- Slow signals, routed on L3/L6:

  | Net | From | To |
  |---|---|---|
  | USBAx_EN | U702 pin 4 | TPS pin 3 |
  | USBAx_ILIM | R701 | TPS pin 5 (≤ 5 mm) |
  | ISNS → R705/C708 → USBAx_ISENSE | — | RP2350 ADC (right block) |
  | USBAx_PWR_EN / USBAx_OCS_N | Hub PRT_CTL | U702 pin 1 and TPS pin 4 |
  | USBAx_FORCE_EN | RP2350 | U702 pin 2 |

## Cross-block exits

| Net(s) | Leaves the front block at | Goes to |
|---|---|---|
| CR_SS_TX±, CR_SS_RX±, CR_DP/DN | x 137.5–141.5, y 112 (B.Cu → L3) | Hub port 1 (hubrails) |
| USBA1_SS_*, USBA1_DP/DN | Channel x 149.5–153.5, y 112 (USB2 at x ≈ 155.5) | Hub port 2 |
| USBA2_SS_*, USBA2_DP/DN | Channel x 168.5–172.5, y 112 (USB2 at x ≈ 174.5) | Hub port 3 |
| +5V (≈ 4 A for both ports plus the card reader) | L4 plane, entering at y 108–112 over x 140–168 | Rails (hubrails) |
| USBAx_PWR_EN, USBAx_OCS_N | y 112, x ≈ 143–162 | Hub PRT_CTL2/3 |
| USBAx_FORCE_EN, USBAx_ISENSE, CR_CD_SD_N, CR_CD_USD_N, CR_LED, +3V3 | Eastward on L3/L6 at y 113–125 (keep L3 y 129.5–132.5 for the microSD bus) | MCU / TCA9534 (right block) |
