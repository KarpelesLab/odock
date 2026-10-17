# odock-10 layout notes: power block (Power input + Laptop power out)

Script: `hardware/odock-10/layout/power.py`, 226 refs: every 1xx/2xx footprint plus U1201, C1201, TH1201, TP1201.
Region (100,50)–(138,108). A second REGION rectangle (y 49.5–64) only covers J101/J102, whose courtyards stick
0.5 mm past the back edge because their mating faces sit flush with it.
How it was made: I placed the connectors, TVS diodes, power stages and source switch by hand. Each small part
was then put by an anchor packer (nearest free spot to the pin or part it serves, 0.2 mm courtyard gap), and the
result is stored as explicit coordinates. Checked with `apply_layout.py --only power`: no OUTSIDE REGION, no
MOVED NON-OWNED, and no overlap between two power refs. Top: 99 parts, bottom: 127.

## Map (top side; B = the part is on the bottom)

```
x:100      108          119.4 120.4         131.8  138
y=50 (H1)  [ J102 barrel  ]   [ J101 PD-in C  ]  U101 TPD4S480
           [  x=113.70    ]   [  x=126.10     ]  U102 TPS26750   (+PD passives, B)
     D102  [              ]   [ D101 TVS (y 61-67)]  C233
     TVS   Q101-103 / ideal-diode passives     Q213 | Q214   R243 -> VBUS_LAPTOP exits x=138, y 66-70
 y=63 B: Q106 | Q107 || Q105 | Q104  (input ideal-diode row on the bottom, y 63.4-69.2)
 y=71  C205/C206 PSO caps   R202 (8 mOhm)   C211 polymer      Q217 sink FET (B: U205/U206)
       Q204 | Q203 (boost)  C209/C210        C212 polymer      sink/PD passives
 y=82  L201 XAL1010   |gate| U201 LM51770   (analog pins face +x)
 y=93  R201 (4 mOhm)  TH1201                 C215..          C122 47u/100V alu (VIN exits x=138, y 88-101)
 y=97  Q202 | Q201 (buck) U1201 TMP1075, TP1201   logic / OVP latch / source-sink logic
 y=104 C201  C203  (C202/C204 under them, B)
```

## Main decisions

- **Connectors.** J102 is at x = 113.70, not 108. At 108 its courtyard (11.3 mm wide) would cover the H1 hole
  centre (104,54), and the rule needs 4 mm from hole centres. J101 is therefore at 126.10, which leaves 1.06 mm
  between the two courtyards. Both use rot 180 with the courtyard 0.5 mm past the edge, as in the rough placement.
- **LM51770 stage: one vertical column at x 100.6–112.3.** The boost leg is on top, L201 in the middle and the
  buck leg at the bottom. U201 is rotated 90°, so its power pins face the column (HO2/LO2/SW2/HB2 at the top,
  HO1/LO1/SW1/HB1/CSA/CSB at the bottom) and its analog pins face +x, away from the switch nodes. The hottest
  parts (Q201/Q202/L201/R201) sit at x ≤ 112.3, more than 25 mm from the hubrails region (x ≥ 138), so the
  ≥ 15 mm rule to the LM5148 holds for any LM5148 position there.
  - Buck hot loop: C201 (top) bridges the Q202 source row (GND, y 103.4) and the Q201 drain/EP (VIN, y 101–103.5).
    C203 sits next to it on Q201's VIN side. C202 and C204 are directly underneath on the bottom. SW1 is the shared
    top edge of Q202 (drain) and Q201 (source row) at y 97.6–99.8, which goes to R201 pad 1 (101.5, 94.8). R201
    pad 2 (BB_LS) goes to L201 pad 1 (106.3, 90.9).
  - Boost hot loop: C205 and C206 (top, rot 0) bridge the Q204 drain (PSO, y 78.7–79.9) and the Q203 source row
    (GND, y 78.7). C208 is top-left, C207 is underneath on the bottom. SW2 is the shared bottom edge of Q204/Q203
    (y 80.6–81.8), which goes to L201 pad 2 (106.3, 84.3).
  - Output: the PSO pour runs from the Q204 drain to R202 pad 1 (113.0, 73.2). R202 pad 2 is VBB_OUT (118.9,
    73.2), with C209/C210 just below it, polymer caps C211/C212 at x 122–132, and Q213's VBB_OUT source pins at
    x 120.8, so the source switch input is 2 mm from the shunt.
- **Input ideal diodes on the bottom.** Q106|Q107 and Q105|Q104 form one row at y 63.4–69.2, each pair
  common-drain with the drains facing each other. The VIN_OR sources of Q107 (x 115.0) and Q105 (x 116.6) face
  each other, which makes the OR node at about (115.8, 66). U105 and U104 are just below the row. R137
  (2 mΩ, bottom, rot 270) has its VIN_OR pad at (113.8, 70.5) at the OR node and its VIN pad at (113.8, 76.5);
  INA237 U109 is beside it. Dissipation is ≤ 0.15 W per FET, so no thermal vias are needed. Thermal vias there
  would land in the top-side pads of D101/D102, so **do not put vias in the Q104–Q107 drain pads under D101/D102.**
- **TVS at the connectors.** D102 (rot 270) has its VBAR pad at (103.8, 60.7) on the H1-free strip.
  D101 (rot 180) sits right under J101, VBUS_PDIN pad (129.8, 64.2). C101 (2.2 µF) and C102 are under Q104/D101
  on the bottom.
- **Source switch, top right.** Q213 (rot 270) and Q214 (rot 90) are common-drain, SRC_MID in the middle. U202 is
  on the bottom under the drain junction (DGATE pin (126.0, 76.8), HGATE pin (128.8, 74.8)); the gate pins are at
  (120.8, 72.4) and (134.0, 68.6). Q214's VBUS_LSW row (x 134) goes to R243 pad 1 (136.2, 71.4). R243 pad 2 and
  C233 are VBUS_LAPTOP: **it exits at x = 138, y ≈ 65–70** toward J501. INA226 U204 is on the bottom (Kelvin
  pins at y 79).
- **Sink path** (VBUS_LSW → +5V) right below: Q217 on top (VBUS_LSW pins at x 137), with U205 and U206 on the
  bottom under it. **+5V leaves from U206 pin 6 (132.4, 79.7, bottom) to the right at x = 138, y ≈ 78–82.**
- **PD-in controller** in the 6 mm strip right of J101: U101 at (134.4, 53) and U102 at (135.1, 61), passives on the
  bottom. PDIN_C_CC1/2 run from J101 A5/B5 (x ≈ 125–127, y 57.6–59.6) right along y ≈ 60.8, between the J101
  pads and the D101 pads, to U101 pins 4/5 (134.7–135.1, 54.4). EEPROM U103 and test pads TP101/TP102 are on
  the bottom at about (126, 81).
- **Thermal sensors.** U1201 TMP1075 is at (114.1, 98.5), against the Q201 edge, between the buck FETs and the
  L201/R201 copper. TP1201 is under it. TH1201 is at (110.4, 94.0), against R201's BB_LS pad, i.e. on the
  inductor-pad copper of L201 pad 1 (route the BB_LS pour up to TH1201 pad 2's GND keep-clear).
- **Bottom side:** passives, SOT-23, WSON/VQFN, SOIC-8 (U103), TDSON (input FETs), 2512 (R137, R235). There are
  no bottom parts under J101/J102, under the Q201–Q204/Q213/Q214 courtyards (thermal vias go there) or under the
  U201 exposed pad. The 4.7 µF/100 V and 10 µF/50 V 1210 caps on the bottom (C202, C204, C207, C101) can be about
  2.5 mm thick: check the part heights if the bottom must stay ≤ 2 mm.

## Routing intent

Layers: L1 sig/power, L2 GND (0.069 mm under L1), L3 sig, L4 power, L5 GND, L6 sig/power.

- **Hot loops (top, L1 + L2):** keep the C201/C203–Q201–Q202 and C205/C206/C208–Q204–Q203 copper on L1, with
  GND returns through ≥ 6 vias per cap and FET source into L2 right at the pads. The bottom caps (C202, C204,
  C207) get their own via pairs right at their pads. Keep L2 solid under the whole column: no slots, no traces
  on L3 under the switch nodes.
- **Switch nodes BB_SW1 / BB_SW2:** small top-only copper shapes, with no copper on L3/L4/L6 directly below. Put a
  GND pour on L3 under them if anything has to be there. 0 Ω gate resistors R203–R206 sit in the 1.7 mm gap
  between L201 and U201 (R205/R206) and next to R201 (R203/R204). The Q201 gate pin (107.5, 97.7) sits inside the
  SW1 row: take it out with a via to L3 and route HO1 together with SW1 (return) as a pair to U201 pins 34/36.
  HO2/SW2 and LO1/LO2 likewise run as pairs over L2, ≤ 15 mm, 0.3 mm wide.
- **Thermal copper:** a Q201 drain = VIN pour on L1 + L4 with a via array in the EP. Q202/Q203 sources go to GND
  with a via array to L2/L5. The Q204 drain = BB_PSO pour on L1 from the Q204 drain to R202, with vias to an L4
  island. L201 pads get wide L1 copper. Q213/Q214 SRC_MID pour on L1 with an EP via array to an L4/L6 island
  (allowed: nothing on the bottom under them). Use 2 oz if the stack-up allows, otherwise duplicate the pours on
  L4/L6.
- **Kelvin pairs (L3, routed together, 0.15 mm):** R201 → CSA/CSB through R210/R211 (filter R's and C221 at the
  U201 end, pins 37/38). R202 → U201 pins 23 (PSO) and 20/22 (VBB_OUT). R137 → U109 pins 10/9 (bottom, L6).
  R243 → U204 pins 10/8 (bottom, L6). Take each pair from the inner edges of the shunt pads.
- **Quiet analog (U201 pins 1–19, the +x side):** COMP/FB/SS/RT/IMON parts are at U201's right edge and on the
  bottom under its right half. Keep BB_FB/BB_FBM short and away from the SW nodes, with the L5 GND plane in
  between when they are on L6. The VSEL FB-switch FETs Q205–Q207 are on the bottom around (105–115, 85–95).
  Keep the switching traces out of that zone on L6. Use a local AGND tie at the U201 EP (pin 39) with a via
  array to L2.
- **Power nets and pours:**
  - VIN_OR: L6 pour around the bottom OR node (Q107/Q105 sources ↔ R137 pad 1), ≥ 6 mm wide.
  - VIN: from R137 pad 2 (bottom) down to L4. **On L4, the VIN pour runs down the left side (x 100–112, y 76–88) and then across the whole width (x 100–138, y 88–108).** It feeds the Q201
    drain/C201–C204 (via arrays), U201 pin 3 (via C215), C122 (132.55, 90.6) and **exits at x = 138, y 85–105**
    to the hubrails 5 V buck (hubrails should take it on L4). HV clearance is 0.3 mm.
  - VBAR / VBUS_PDIN: J102 pin 1 (113.7, 50.85) and J101 VBUS pins go to the TVS pads and down to the bottom FET
    sources on L3/L4 under the jack, ≥ 3 mm wide, with ≥ 4 vias at each layer change.
  - VBB_OUT: L1 from R202 → C209/C210 → Q213 sources, plus an L4 island under C211/C212 (x 112–132, y 72–88).
    The split from the VIN pour runs along x = 112 and y = 88.
  - VBUS_LSW: L1 from the Q214 source row → R243, and down to Q217 (x 137, y 75–81), 3 mm.
  - VBUS_LAPTOP: L1/L4, ≥ 3 mm (5 A), from R243 pad 2/C233 to the right edge at y 65–70, then the usbc block
    takes it to J501 VBUS.
  - +5V (sink output, ≤ 3.3 A): U206 pin 6 → L6/L4 → right edge y 78–82, toward the hubrails +5V rail.
- **Gate drives of the ideal-diode controllers** (bottom, L6): U105/U104 sit right below their FET pairs, so the
  gate traces are ≤ 6 mm. U202 DGATE/HGATE: ≤ 8 mm on L6. DGATE needs fast turn-off, so keep it short and direct.
- **Logic and I2C (out of the block):** VBB_EN, VBB_VSEL0..2, VBB_PG, LAPTOP_SRC_EN, LAPTOP_SNK_EN, LAPTOP_OVP_N
  and EXT_PWR_PRESENT come from or go to U401 (PMG1, usbc block). Their parts are bottom-right (x 120–138,
  y 85–108). Leave the block at x = 138, y 85–100 on L3/L6. I2C_PD (U102 pins 8/9 at (136.4–137.0, 62–63)),
  PDIN_INT_N and PDIN_PRESENT leave at x = 138, y 60–64 toward PMG1/RP2350. I2C_SYS (U109, U204, U1201),
  TEMP_ALERT_N and NTC_ADC0 (TH1201) go to RP2350/U1003 in the right block: run them on L3 along y ≈ 96–100
  toward x = 138. PG_5V comes in from hubrails at x = 138, y ≈ 100 (to R251/D204 near (131, 103)).
- **Keep-outs:** no vias inside the D101/D102 pads (bottom FETs below them). A 4 mm copper keep-out around H1.
  No signal traces under the barrel-jack pins.

## Open issues / for other blocks

1. **SD socket J901 (front block).** Its courtyard is 31.2 mm deep (SD-SMD_SD-111). Even flush with the front edge
   (y 135.6) it reaches **y ≈ 104.4**, which is 3.6 mm into this region over x 104–136. My top parts in y 104.4–108
   (buck input caps C201/C203, C227, Q220, D205, R256, C244 …) would collide with it. The front block must let J901
   overhang the front edge by ≥ 3.6 mm (or move the floorplan line), otherwise I lose about 120 mm² of top area.
   The power column has no slack in y. The bottom side is not affected, because J901 is SMD.
2. J102 and J101 positions are moved from the floorplan values: x = 113.70 (not 108) to clear H1, and x = 126.10
   (not 124) for the 1 mm gap. The usbc block sees J101's courtyard right edge at x = 131.77, so this block uses
   the strip up to x = 138.
3. The PJ-063BH footprint pin positions still need checking against the datasheet (power_input.md open item 6).
   Rot 180 follows the rough placement and the 3D model (opening at the back edge).
4. C122 (47 µF aluminium electrolytic) is at x 127–138, y 88–101, near the hubrails boundary. Keep the LM5148
   switching parts ≥ 10 mm from it to protect the capacitor's lifetime.
