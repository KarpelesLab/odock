# odock-10 layout notes: `usbc` block

Script: `hardware/odock-10/layout/usbc.py`. Region (138,50)–(180,80), with a second rectangle (144,49.4)–(177,61.2)
for the edge connectors only, because their courtyards poke about 0.5 mm past the back edge when the shell front is flush.
Refs: all of "USB-C muxes & DP" (C501–C538, D501–D507, J501, J502, R501–R544, U501–U504), all of "PD controller"
(C401–C422, JP401–JP403, Q401, Q402, R401–R415, TP401–TP406, U401), plus U1204, C1204, U1205, C1205, TP1204,
TP1205. That makes 150 refs. Board check: no "OUTSIDE REGION", no "MOVED NON-OWNED", no overlaps between two usbc
parts. Every courtyard gap between usbc parts is ≥ 0.2 mm.

Note: the U401 BGA footprint has an open (segmented) courtyard, 157.85–163.95 × 51.05–57.05, so `apply_layout.py`
does not check it. Its neighbours were checked by hand and sit ≥ 0.25 mm away.

## Floorplan inside the block (top view, back edge = y 50)

```
x 138    141.4      150.7               160.9               171.0        178.2  180
  ┌──────┬──────────────────┬───────────────────┬──────────────────┬──────┐ y 50
  │ D501 │ J501 laptop C    │ C416  U401  C418  │ J502 downstream C│ D505 │
  │ TVS  │ (DX07, r180)     │ C417 PMG1  C419   │ (Amphenol, r180) │ TVS  │
  │      │                  │ C412 BGA   C413   │                  │      │
  │      │                  │ decap rows C40x   │                  │      │ y 61
  │U1205 C501 D503  D502   │ C414 C420 R401    │  D507   D506      │      │ ESD rows y 62.5
  │      │ TX caps C511/2  C510/09  C513/14  C530/31  C534/5  C533/2 │ C536 │
  │ TP401..406   lanes ─►┌─U502─┐ C515..C522 ┌─U503─┐◄─ lanes      │      │
  │              (L1)    │TUSB  │ (DP caps)  │TUSB  │   (L1)        │ Q402 │ muxes y 66–73
  │                      │1064  │════════════│1046  │               │AO4842│
  │      R41x            └──────┘            └──────┘   R415        │      │
  │      R502/3 R506/7 C523/4 R525/6 R542/3   TP1205 TP1204  C415    │      │ y 80
  └─────────────────────────────────────────────────────────────────┴──────┘
```

Bottom side: U501 (TPD4S480), D504 (laptop USB2 ESD) and U504 (TPD6S300) sit right behind the connector pins.
Also on the bottom: all mux VCC decoupling and EQ/strap resistors, U1204 + C1204 under the PMG1 decap rows, the
JP401–JP403 + Q401 + R402 SWD/XRES cluster (bottom-right corner), C421, C422, and the mux CTL pull-downs.
**Nothing is on the bottom under J501, J502 or D501**, so that area stays free for the VBUS_LAPTOP pour and the
connector THT pins.

## Key decisions

1. **Connectors.**
   - J501 is at x 150.7 (floorplan 150). It moved +0.7 mm so the 1500 W SMC TVS D501 fits between it and x 138,
     on the VBUS_LAPTOP feed path.
   - J502 is at x 171.0 (floorplan 168, +3 mm, the allowed limit). This leaves room between the ports for the PMG1
     with a cap column on each side, and room for the two muxes side by side.
   - Both shells sit flush with the back edge: DX07 shell front at y ≈ 49.9, Amphenol fab outline at y 49.97.
     Confirm against the enclosure.
2. **Muxes rotated 270° and placed side by side** (TUSB1064 U502 at 156.85,69.55; TUSB1046 U503 at 166.3,69.55).
   - With this rotation, the DP edges of the two chips face each other, and their pin orders mirror exactly
     (ML0P…ML3N top to bottom on both). The DP main link is therefore **8 straight, parallel lines about 5.6 mm long
     (pad to pad), with no crossings**.
   - Each chip's connector edge faces outward toward its own connector. Its hub-SS edge faces up, and its
     AUX/SBU/CTL edge faces down. AUX runs straight along the row below the chips (about 9 mm).
   - "Connector-facing up" (rot 180/0) was rejected. It made the DP link a 25 mm U and AUX about 30 mm, and the hub
     SS of both chips had to cross the DP bundle anyway.
3. **Lane fan-in.** J501's lanes leave the receptacle, pass straight through D503 (TX2/RX2) and D502 (TX1/RX1), then
   the TX caps (vertical, below the ESDs). They then turn right into U502's left edge as nested L-shapes. The pair order
   matches all the way with no crossings: D502 rot 180 gives TX1P, TX1N, RX1P, RX1N top to bottom; D503 rot 0 gives
   RX2N, RX2P, TX2N, TX2P.
4. **PMG1 between the ports, at the back.**
   - Rot 180 puts the port-0 balls (LAPTOP_CC, VBUS_LAPTOP, VBUS_LSW, I2C, XRES) on the left, facing J501 and U501.
     The port-1 balls (DS_CC, gate drives, VBUS_DS, DS_SRC) are on the right, facing J502 and U504.
   - The VDDD/VCCD/VSYS balls and the VBB_*/MUX_* rows end up on the bottom side of the package. The decap block
     sits right there (3 rows below the BGA). The CC 390 pF and VCONN 1 µF caps are in the side columns, level with
     their balls (CC at y 52.5–53.5, VCONN at y 53.05).
   - CC path from protector to PMG1 is about 9 mm on each side.
5. **Protectors on the bottom, directly behind the receptacle pins.** U501 at (150.7,63.05) and U504 at (171,63.4) have
   their C_CC/C_SBU pins (1–5) facing the connector. D504 (laptop D+/D−) is at (146.9,63.05). U504 pins 19/20
   provide the downstream D+/D− ESD.
6. **Downstream VBUS switch** goes in the bottom-right corner: Q402, R415 and C415 on top, C421 and C422 on the
   bottom. +5V comes in from hubrails at y 80 (R415 pad 1 at 170.85,78.86). D505 and C536 sit at J502's right side.

## Routing intent

### Stack-up use
- L1 carries every SS/DP line, referenced to L2 GND.
- L3 is used only for the hub-SS escape (referenced to L2/L4) and slow signals.
- L4 is power: VBUS_LAPTOP island, VBUS_DS island, +3V3, +5V.
- L6 carries slow signals plus the VBUS_LAPTOP pour under J501/D501.
- L2 and L5 stay solid GND under the whole block: no splits and no slots under the lanes.

### SuperSpeed / DP (HS_85: 85 Ω, intra-pair skew < 0.1 mm)

**Laptop port (J501 → U502).**
- Route on L1, ≤ 20 mm. Order: receptacle pad → straight across D502/D503's flow-through pad pairs → TX cap (TX
  lines only: C509/C510 TX1, C511/C512 TX2) → U502 left edge. RX lines are DC here.
- The **B row is THT** on the DX07. Pick up B2/B3 and B10/B11 on L1 from the THT pins, so no extra via is needed.
- GND voids on L2 under the 0402 cap pads, about one pad width.

**Downstream port (U503 → J502).**
- L1, mirror image of the laptop port: TX caps C532–C535 under D506/D507, then turn left into U503's right edge.
- **Known pair-order mismatch.** U503's pin order (RX2P RX2N TX2P TX2N | TX1N TX1P RX1N RX1P) cannot match the
  TPD4E02B04 pinout (P N G P N) in either rotation. D507 rot 0 and D506 rot 180 keep P/N correct, but **the two
  pairs in each half swap order between ESD and chip**.
- Fix: the B-row pair of each half already needs a via, because the Amphenol B row is SMD behind the A row (TX2 on
  the left half, RX1 on the right half). Run that pair on L3 from the connector and bring it up just before the ESD.
  After the ESD, cross the A-row pair once more on L3. Alternatively, swap pairs at the TX-cap pads.
- Do not swap P/N within a pair: DP lanes are not polarity-tolerant.

**DP main link (U502 right edge → C515–C522 → U503 left edge).**
- L1, straight horizontal. P caps are in the left column (x 160.51), N caps in the right column (x 162.62), one row
  per lane pair.
- Match the 4 pairs to ±0.5 mm. They are naturally equal.
- Keep the strap stubs (SSEQ0/DPEQ0/HPDIN, I2C_EN) that leave between the pairs short. They go to vias and then to
  the bottom resistors.

**Hub SS (to hubrails).**
- Pins sit on the top edges: U502 TXP/TXN at x 155.45/155.85, SSRX at 156.65/157.05 (y 66.65); U503 at 164.85/165.25
  and 166.05/166.45.
- SSRX goes through C513/C514 (U502) and C530/C531 (U503), placed right above the pins. **One via pair per line to
  L3** right next to the caps (TX: right at the pins; the TX caps are on the hub sheet).
- On L3, route into the middle corridor x ≈ 159.5–164, under the DP caps, and straight down to **y 80, exit x ≈
  159–164** (8 lines, 4 pairs).
- Add GND stitching vias next to every signal via, for the L2/L4/L5 reference change.
- Through-via stubs: the transition sits ≤ 3 mm from the mux, as allowed by usbc_muxes.md. Keep L3 between L2/L4
  references, and keep 3W from the slow lines.

**AUX** (90 Ω, low speed). U502 AUX pins (157.45/157.85, y 72.45) → R506/R507 bias → C523/C524 → R525/R526 bias →
U503 AUX (166.05/166.45). This is one straight run along the y 73.8/75.05 row, on L1.

### USB2 (USB_90)
- LAPTOP_USB_DP/DN: J501 A6/A7 (SMD) and B6/B7 (THT) are tied at the receptacle. Go to D504 on the bottom
  (146.9,63.05), flow-through vertical. Then run down on L6/L3 along x ≈ 146–150 and **exit at y 80, x ≈ 148–150**
  toward the hub upstream port.
- HUB_DSC_DP/DN: J502 A6/A7 + B6/B7 (vias) → U504 pins 19/20 (bottom, ESD tap) → down on L3/L6 right of U503 →
  **exit at y 80, x ≈ 168–170**.

### CC / SBU / VCONN
- J501 A5/B5 (CC) and A8/B8 (SBU): short vias right under the A-row pads to U501 directly below on the bottom.
  - LAPTOP_CC1/2 (U501 pins 12/11) → PMG1 balls N14/N15, J14/J15 (left column, x 158.4–158.9, y 52.55/53.55), on
    L6/L3, about 9 mm. C416/C417 sit at the balls.
  - VCONN is up to 600 mA through the CC path: width ≥ 0.3 mm on CC between J501, U501 and the PMG1.
- UP_SBU1/2 (U501 pins 15/14) → U502 SBU pins (156.65/157.05, y 72.45), with R502/R503 (2 M) at the chip.
- Downstream is the same: J502 → U504 → DS_CC1/2 → PMG1 N1/N2, J1/J2 (right column) with C418/C419. DS_SBU →
  U503 pins 26/27 (166.85/167.25, y 72.45), with R542/R543.
- Keep CC away from VBUS copper, using `HV` clearance for LAPTOP CC near VBUS_LAPTOP.
- VBIAS caps C502 (100 V) and C537 sit at pin 3 of each protector. VPWR caps: C503 (PMG1_VDDD) and C538 (+3V3).

### Power
- **VBUS_LAPTOP (5 A, up to 28 V, `PWR_HC`/`HV`).**
  - It enters from the power block at x 138, y 50–63. Pour it on **L4 (island) + L6 (bottom pour)**, each ≥ 8 mm
    wide, under D501 and J501 into J501's THT VBUS pins B4/B9 (149.5/151.9, 58.27). Add a via cluster at A4/A9 (SMD).
  - On L1, D501 pad 1 (141.4,58.9) and C501 tie into that island with ≥ 6 vias.
  - D501 pad 2 (GND) goes to the back-edge GND / J501 shell with a via cluster.
  - U1205 (140,62.75) sits in this copper. Only its EP/GND touches the pour. Keep VBUS clearance to its pins.
  - The PMG1 VBUS_C_P0 sense (balls A15/H15, left side) is a thin tap from the island, with C414 at the ball.
  - VBUS_LSW (ball B15) is a Kelvin sense line to the power_laptop INA226 shunt. Route it as a pair with the
    VBUS_LAPTOP sense (pd_pmg1 open issue 4), on L3/L6 toward x 138.
- **VBUS_DS (3 A).** The path is +5V (y 80) → R415 → DS_SRC → Q402 pin 1 … pin 3 (173.57,75.53).
  - Run an L4 island (≥ 3 mm or a pour) up to J502's VBUS pins (A4/A9/B4/B9), with vias beside each pad.
  - D505 pad 1 (178.15,66.95), C536, C422 (bottom, at pin 3) and C415 (PMG1 VBUS_C_P1) all hang on this island.
  - Q402 common drain (pins 5–8): wide L1 copper on the right side of the SOIC, for heat.
  - CSP_P1 (+5V) and CSN_P1 (DS_SRC) are a **Kelvin pair from the R415 pads** to PMG1 C15 / C14 and R2.
  - DS_GIN and DS_GOUT come from PMG1 P2/P1 (top-right) to Q402 pins 2/4. Route them on L3/L6 under J502 (its body
    is SMD, so the inner layers are free).
- **+3V3** comes up from hubrails on L4 to the mux VCC caps (bottom, one per pin), U504 VPWR, the PMG1 VSYS caps
  C401/C402, and U1204/U1205.
- **+5V** comes up from hubrails to R415/C421, the PMG1 VCONN caps C412/C413, and C15.
- **PMG1_VDDD** is local: PMG1 balls → C403–C410, U501 VPWR (C503), R401/R403/R501.

### PMG1 BGA fanout
- 0.5 mm pitch: use via-in-pad (filled/capped, free on 6 L).
- Outer ring on L1 toward the side columns.
- Inner VDDD/VCCD/GND balls drop straight to L2/L4/L5. The decap rows sit right below the package. Keep the area
  under the BGA free of bottom parts (it already is).
- **Power-block signals** come from the bottom-left balls: VBB_EN, VBB_VSEL0–2, LAPTOP_SNK_EN (R8, top), LAPTOP_SRC_EN,
  VBB_PG, LAPTOP_OVP_N, EXT_PWR_PRESENT, PDIN_PRESENT, VBUS_LSW. Two corridors exit at x 138:
  - (a) y 59.5–61 on L3, between J501's THT rows and the protector row;
  - (b) the free bottom-left area on L6, x 138–150, y 66–80.
- **MUX_UP/DS CTL0/CTL1/FLIP** come from the bottom-right balls (A1, B1, B3, C1, C2, D4).
  - They go down to the mux bottom edges: U502 pins 21–23 at x 155.45–156.25, U503 pins 21–23 at x 164.85–165.65,
    both at y 72.45. Pull-downs: R407–R409 (bottom, below U502) and R410–R412 (bottom, right of U503).
  - The middle corridor is busy (L3 = hub SS, bottom = strap grid). Route the TUSB1064 group on L6 down the left of
    the strap grid (x ≈ 158.5–159.5), and the TUSB1046 group on L6 down x ≈ 163.7–164.3 / behind U503.
- HPD: HPD0_OUT → R414 → UP_HPD → R505 → U502 pin 32 (right edge), with R544 pull-down. HPD1_OUT → R413 → DS_HPD →
  R522 → U503 pin 32 (right edge), and back to PMG1 ball M10.
- **To the RP2350** (right block, x > 180, y > 80):
  - I2C_PD_SCL/SDA (E15/D12), I2C_PD_INT_N (B9, pull-up R403 on the bottom).
  - SWD/XRES through JP401–JP403 + Q401 (bottom-right corner, 172–180 × 71–80). The JP outer pads face x 180.
  - Probe pads TP401–TP406 are at the left (139.6–144.3, 67.6–70): stubs on the PMG1-side nets, kept short (no
    matched-length requirement).

### GND, thermal, EMI
- Stitch both receptacle shells to L2/L5 with via rows along each shell pad.
- Put a GND via fence (≈ 1.5 mm pitch) along both sides of each lane bundle, and between the hub-SS L3 corridor and
  the slow lines.
- U502/U503 EP: 3×5 via array (0.3/0.6) to L2/L5. Mux power is about 0.3 W each. U501/U504 EP: 4 vias.
- U1204 (TMP1075, bottom, 161,58.4) reads the PMG1/mux area through the GND planes. Tie its EP to GND with 4 vias.
- Q402: drain copper on L1 plus 6 thermal vias. R415: wide pads, Kelvin taps from the inner pad edges.

## Problems / for other blocks
- **hubrails**:
  - Hub SS (4 pairs) arrives on **L3 at y 80, x ≈ 159–164**. The HUB_*_SS_TX AC caps belong on the hub side.
  - LAPTOP_USB_DP/DN at y 80, x ≈ 148–150. HUB_DSC_DP/DN at y 80, x ≈ 168–170.
  - +5V for R415/C421 at (170.85, 80). +3V3 / +5V on L4.
- **power**: VBUS_LAPTOP enters at x 138, y 50–63 on L4 + L6 (≥ 8 mm). The PMG1 power-control signals and VBUS_LSW
  Kelvin also cross x 138, at y 59–61 (L3) and y 66–80 (L6).
- **right**: PMG1 I2C/INT/SWD/XRES leave around x 180, y 72–80 (JP401–JP403 sit there on the bottom).
- **TP1204 (TC_5V_L) and TP1205 (TC_HUB)** are assigned to usbc by floorplan.md, but sensors.md wants them ≤ 3 mm from
  L301 and the USB7206C, which are both in hubrails.
  - They are placed at the bottom-middle edge of this region (159.9 / 163.6, 78.3), the closest available spot.
  - **Suggest reassigning them to hubrails.**
  - Conversely, **TP1206 (TC_LAPTOP_C, "laptop USB-C VBUS pins")** belongs next to J501/D501 but is assigned to
    `right`. Recommend moving it to usbc. There is room at about (143.4, 65.0), under C501 next to the J501/D501 VBUS
    copper, if TP401–TP406 shift 0.2 mm down.
- Space is tight between the ports. If the PMG1 side columns get crowded during fanout, the VCONN caps C412/C413 can
  move to the bottom side columns (free on the right).
