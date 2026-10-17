# hubrails block: placement notes and routing intent

Script: `hardware/odock-10/layout/hubrails.py`. Region: (138,80)–(180,108). It owns 161 footprints:
- the USB hub sheet (C601–C641, D601–D602, R601–R633, U601–U603, Y601);
- the Rails sheet (C301–C341, D301, L301–L303, Q301–Q303, R301–R321, U301–U305);
- U1202, C1202, U1203, C1203, TH1202, TP1202, TP1203.

Result of `apply_layout.py --only hubrails`: nothing outside the region, no foreign part moved, and no courtyard overlap
between two hubrails parts. Every courtyard gap within the block is at least 0.2 mm. The script also checks the "through"
case: the U601 and U301 footprints carry their EP thermal vias as PTH pads, so nothing on the bottom side sits under
either package.

## Floor plan

```
 x=138          152      160   164.3          177.7 180
 y=80 ┌──────────┬────────┬──────┬───────────────┬────┐
      │ L301     │ R303   │ L302 │corridor│ L303 │    │  <- usbc block above (TUSB1064 x~150, TUSB1046 x~168)
      │ 4.7uH    │ D602   │ +3V3 │UP + P5 │ +1V15│    │
      │ (SW pad  │ U603   │ U304 │ pairs, │ U305 │    │
      │  bottom) │ U301   │ Cin  │C601/02 │      │    │
      │          │ LM5148 │      │C611/12 │      │    │
 y~95 ├────┬─────┤ C307   │ Y601 ┌───────────────┐ dec│
VIN ->│Q301│Q302 │ C324   │ P1/P2│   USB7206C    │ caps
edge  │ HS │ LS  ├────────┤ chan-│   U601 (171,98)│ top│ -> right block (SMBus, PRT_CTL, straps)
      ├────┴──┬──┤ C323   │ nel  │               │    │
      │C301/02│C303 330uF │C603-6└───────────────┘    │
 y=108└───────┴──┴────────┴──────┴─P3──P4/P6 ─C609/10─┘ -> front block (USB-A, GL3224); P4/P6 -> right
```

### Key decisions

**Hub U601 at (171, 98), rot 0.**
- Pins 76–100 face the back edge: UP (89–95) at x 168.2–170.6 and P5 (81–87) at x 171.4–173.8. They exit straight up
  a clear corridor (x ≈ 167.5–174, y 80–91.3) to the usbc block. P5 lands right under TUSB1046 (x ≈ 168). UP turns
  left inside the usbc block toward TUSB1064 (x ≈ 150).
- P3 (27–33, x 166.6–169.0) drops straight down to J702 (x 168).
- P4 (34–40) and P6 (41/42) leave the bottom edge and turn right along y ≈ 105–107.7 to the right block.
- P1 (5–11) and P2 (14–20) leave the left edge into the P1/P2 channel (x 160–164.3), then turn down to the front
  block. P1 is the outer (left) lane and P2 the inner lane, so no lanes cross. This is the port map in
  docs/design/usb_hub.md, unchanged.
- The hub sits right of the region centre because the LM5148 stage, which carries 8 A, needs a 21 mm column on the
  left.

**Hub decoupling.**
- The PF/SPI side (pins 53, 55, 62, 67) has no pairs, so its 100 nF caps are on top, right at the pads: C620, C632,
  C616, C617, plus bulk C633 and C622.
- Every VDD33/VCORE pin that sits between pairs (9, 18, 25, 26, 31, 38, 43, 78, 79, 85, 88, 93, 99) has its 100 nF on
  the **bottom**, just outside the courtyard, ≤ 2 mm along the edge from its pin. Connect each with a via at the pad toe.
- VCORE/VDD33 bulk is in the second bottom row.
- RBIAS R601 is on the bottom at pin 100.

**Crystal Y601** is at the top-left package corner (XO pad about 4 mm from pin 97, XI pad about 6 mm from pin 98), with
C637/C638 directly under its pads on the bottom. It stays clear of both the UP corridor and the P1 channel.

**Straps.** All straps are on the bottom.
- Right side: one column of 17 resistors (SMBus, PF29, SPI_D0–D3/CE/CLK, PF19, TEST1–3, PF18, R630/R631) at
  x ≈ 179, in pin order.
- Left side: CFG1–3, PF31, RESET_N R/C and D601.
- Under the bottom edge: PF3–PF7 and the R629 pull-down.

**AC caps.** C601–C612 are in-line on top, at most 5 mm from the pins:
- UP and P5: at y ≈ 88.2 in the corridor.
- P1: in the outer channel lane at y 101.
- P2: in the inner lane at y 105.4.
- P3: at y 106.6 under the hub.
- P4: rot 0 on the rightward run at x 175.4.

**LM5148 5 V/8 A.**
- L301 (rot 90) sits top-left. Its SW pad is at the bottom (y 92–95.2). Q301 (HS, rot 90: VIN pins left, SW right) and
  Q302 (LS, SW/EP up, source down) sit directly under that SW pad. The SW copper island spans only x 142.5–150.8,
  y 92–99.
- VIN comes in at the left edge (y 96–107): Q301 drain, then C301/C302 (VIN pad left, GND pad right), C304/C306
  directly under them, and C303/C305 under Q302. C303's GND pad faces Q302's source pins.
- U301 is right of L301, with the gate-drive pins (LO 11, HO 13, SW 14, BOOT 15) pointing down at the FETs. R303 (Kelvin
  sense) is above U301: its ISNS pad is next to L301's ISNS pad and its 5V_BUCK pad is right above U301's VOUT/ISNS pins
  (20/21).
- The output side is all on the bottom under L301 and R303: 6 × 47 µF, OR-FET Q303, LM74700 U302, the 2 mΩ shunt
  R312 and INA226 U303. The 330 µF polymer C323 and 22 µF C324 are on top at the bottom-right of the column.
- The stage is in the left/bottom-left of the region. The FETs are at x 140–151, which should keep it ≥ 15 mm from the
  LM51770 stage at the top-left of the power block. Power should confirm this once its stage is placed.

**+3V3 (TPS62933F)** is in the top-left strip (L302, U304, Cin on top; Cout and feedback on the bottom under L302).
**+1V15 (TPS62933P)** is in the top-right corner beside the VCORE pin-78 corner (L303, U305, Cin on top; 4 × 22 µF,
FB, EN, PG and BST on the bottom under L303). It is about 3 mm from the hub's top-right VCORE pins.

**Sensors.**
- TH1202: on top, on Q301's drain/VIN copper.
- TP1203: bottom, 2 mm from the FETs.
- U1202 (TMP1075 "5V BUCK"): bottom, under C303 on the Q302-source / input-cap GND copper.
- U1203 (TMP1075 "HUB"): bottom, at the hub's bottom-left corner, 0.2 mm from its courtyard.
- TP1202: bottom, under L301.

**DNP parts.** U602 (SPI flash) is on the bottom under the UP/P5 corridor (pairs run on L1, so they are unaffected).
The R302/C308 snubber is on the bottom by the LS FET.

## Routing intent

### SuperSpeed (10 Gb/s) and USB2

- **Layers.** Route SS pairs on **L1** (microstrip over the solid L2 GND), 85 Ω differential. Avoid layer changes. If
  one is unavoidable, use L6 over L5 with two GND stitching vias per signal via.
- **USB2 pairs.** P1/P2 USB2 (CR_DP/DN, USBA1_DP/DN) go on **L3** to save width in the channel. The P6 pair
  (MCU_USB_DP/DN, pins 41/42) also goes on L3 under the P4 run toward the right block. That matches the design note:
  "USB2 only, layer change tolerated".
- **Corridor (x 167.5–174, y 80–91.3)** carries UP TX/RX + UP USB2 (pins 89–95) and P5 TX/RX + USB2 (81–87). No vias
  in it except GND stitching. The UP and P5 VCORE/VDD33 pins (85, 88, 93) drop to the bottom caps through vias at the
  pad toe, between the pairs.
- **P1/P2 channel (x 160–164.3, y 94.5–108).**
  - The four SS pairs run at about 1 mm pitch: P1 TX/RX outer (x ≈ 160.3–162.2), P2 TX/RX inner (x ≈ 162.4–164.2).
  - The channel holds the AC caps C603–C606 in-line. Keep the pairs symmetric around each cap, and **void L2 under the
    0402 cap pads**. Apply the same void at C601/C602 and C607–C612.
  - The bottom side of the channel has only low-speed parts.
- **P3** goes straight down at x 166.6–169.0 through C607/C608 to the front block.
- **P4 (ETH_*)** leaves pins 34–40, drops about 1 mm, and runs right along y 105–107.7 through C609/C610 to x = 180.
  It hands over to the right block at about y 105–107.5. It is the longest SS run, so check length and loss. It is
  shorter than the design note feared, because it no longer wraps around the PF side.
- **Cross-block hand-off points (y/x at the region edge):**

  | Port | Hand-off |
  |---|---|
  | UP | x 168–171 at y 80 |
  | P5 | x 171–174 at y 80 |
  | P1 | x 160–162.3 at y 108 |
  | P2 | x 162.3–164.3 at y 108 |
  | P3 | x 166.5–169 at y 108 |
  | P4 | y 105–107.7 at x 180 |
  | P6 | L3, y ≈ 104–107 at x 180 |

- **Length matching.** Match intra-pair to 0.1 mm (5 mil). No inter-pair matching is needed (USB 3.2).

### Hub low-speed

- **Crystal.** XI/XO run on L1 to pins 98/97. They are short and guarded by GND, with no other signal between Y601 and
  the corner. C637/C638 return to GND through their own vias next to Y601's GND pads.
- **RBIAS.** R601 sits on the bottom with a direct via to pin 100 and its own GND via.
- **To the right block:**
  - HUB_SMB_CLK/DAT (pins 75/76) and HUB_SMB_PU leave at the top-right corner.
  - USBA1/2_PWR_EN/OCS_N (pins 59/58 via R631/R630) and HUB_RESET_N run on L3/L6 across the strap column to x = 180.
  - USBA*_PWR_EN goes onward to the front block (usb_a) via the right block or along y ≈ 107 on L3.
- **HUB_RESET_N** (pin 1) comes from the left-column R624/C639/D601. RAILS_PG comes from U305 pin 7 (top-right) to
  D601 on L3.
- **VBUS_DET chain.**
  - VBUS_LAPTOP enters from the usbc block to R625 (bottom, 160.75/96.3) on L3/L6, with HV clearance (up to 28 V).
  - U603/D602/R626/R632 are on top at x 156.5–160, and HUB_VBUS_DET reaches pin 2 together with R633 (bottom).
- **Hub EP.** About 6 × 6 vias (already in the footprint) into L2/L5 GND. This is the hub's main heat path.

### LM5148 power stage

- **Hot loop: top layer only.**
  - VIN pour from the left edge covers Q301's drain/EP and the left pads of C301/C302.
  - GND pour links the right pads of C301/C302, C305 and C303 to Q302's source pins (y 102.3).
  - The SW island links Q301's SW pins, Q302's SW pins/EP and L301's SW pad. Keep it as small as drawn.
  - Place a dense GND via row (≥ 8 × 0.3 mm) between the cap GND pads and Q302's source into L2. The loop then closes
    vertically through L2 (0.1 mm below).
  - Do not run any signal under the SW island on L3.
- **Thermal vias.**
  - Q301: VIN drain copper, ≥ 9 vias into an L4 VIN pour and a bottom VIN pour (the bottom under Q301/Q302 is kept
    free of parts).
  - Q302: SW EP, ≥ 9 vias into a bottom SW pour sized like the top one. Do not enlarge it.
  - Q302 source: GND vias.
- **VIN feed.** Top-layer pour along y 96–108 from the left edge, plus an L4 VIN pour under the stage. Per
  power_input, VIN arrives at the power block's right edge at y ≈ 96–107.
- **Gate drive.**
  - LO: U301 pin 11 to Q302 gate (pin 4, at 149.8/102.3). Run it on top in the free strip x 150.9–152.3, 0.4 mm wide,
    with the PGND return under it on L2.
  - HO: U301 pin 13, through R301 (top, 153.2/96.75), to Q301 gate (pin 4, at 143.9/96.9). Route on **L3** with the
    SW return (pin 14) as a parallel trace, about 10 mm.
  - BOOT: C307 sits right at pins 14/15.
- **Current sense (Kelvin).**
  - ISNS: from the inner edge of R303 pad 1 (154.1/81.4) down the right side of U301 to pin 20.
  - VOUT: from R303 pad 2 (154.1/87.3) to pins 21/16.
  - Route the two traces as a pair on L1/L3, away from SW.
- **FB/COMP/RT/CNFG.**
  - R306/R307 are on the bottom just left of U301 (pins 3/4).
  - The FB divider R308/R309 and comp R310/C318/C319 are on the bottom 4–6 mm below U301.
  - Route FB/COMP on L3 between the planes, away from L301's SW pad. FB top (R308) senses 5V_BUCK at R303 pad 2.
- **5V_BUCK node.**
  - R303 pad 2 connects through ≥ 6 vias to a bottom 5V_BUCK pour.
  - That pour covers C309–C314, Q303's source row (y 87.0) and U302 ANODE (pins 3/6).
  - Use ≥ 8 A copper (bottom pour plus an L4 copy).
- **OR / +5V.**
  - Q303 drain/EP (5V_OR, top of Q303) connects to R312 pad 5V_OR (157.2/81.4).
  - R312 pad +5V (157.2/87.4) feeds the **L4 +5V plane**, which is the main +5V distribution to usb_a, the
    downstream C (usbc), GL3224 and the two bucks here. Use ≥ 10 vias at R312, C323 and C324.
  - INA226 U303 Kelvin-senses R312: IN+ = 5V_OR and IN− = +5V, taken at the inner pad edges.
  - LM74700 GATE goes to Q303 gate (150.15/87.0), short. CATHODE (5V_OR) is sensed from Q303's drain EP.
- **PG_5V.** R311 (bottom, 158.6/99.75) leaves left for power_laptop. Route it on L3 along y ≈ 100 to x = 138.

### Small bucks

- **+3V3.**
  - The U304 input loop is C328 (100 nF, right under the VIN/GND pins) plus C326/C327.
  - SW goes from pin 5 (166.7/87.3) to L302 pad 1 (166.2/83.25), short, on top.
  - +3V3 leaves L302 pad 2 (162.1/83.25), with ≥ 6 vias to the bottom Cout (C331–C333) and to the **L4 +3V3 pour**,
    which also feeds the hub VDD33 pins.
  - FB is taken at C331.
- **+1V15.**
  - The U305 input loop is C336 (right under pins 3/4) plus C334 (top) and C335 (bottom).
  - SW goes from pin 5 (176.7/87.7) to L303 pad 1 (176.95/85.55).
  - +1V15 leaves L303 pad 2 (176.95/81.45), with vias to the bottom 4 × 22 µF and an **L4 +1V15 pour under the whole
    hub**, which carries the 1.31 A to the nine VCORE pins.
  - FB (R320/R321) senses at the hub side of that pour, not at the inductor.
- **L4 layout.** L4 is split into VIN (left, under the LM5148 input), +5V (centre band), +3V3 (top-left/left of hub)
  and +1V15 (under U601). Keep the split gaps out from under any SS pair: the pairs reference L2 (L1) or L5 (L6) only.

### Sensors and analog

- **NTC_ADC1** (TH1202, 139.25/98.7): high-impedance. Route it on L3, guarded by GND, from the left edge of the stage to
  the MCU (right block), never under L301 or the SW island.
- **I2C_SYS and TEMP_ALERT_N.** Daisy-chain U303 (bottom, ~159/91.7), U1202 (bottom, 147.9/105) and U1203 (bottom,
  162.8/105.5) on L3/L6, away from SW.
- **U1202 / U1203 thermal copper.** Tie U1202's EP into the Q302-source GND copper with vias. Tie U1203's EP to the hub
  GND via field.

## Open points / for other blocks

- **TP1202 label mismatch.** On the schematic TP1202 is "TC_BB_L" (buck-boost inductor, power block) and TP1204 is
  "TC_5V_L" (LM5148 inductor), yet the floorplan gives TP1202 to hubrails and TP1204 to usbc. TP1202 is placed under
  L301, where it effectively acts as the 5 V-inductor pad. Swapping TP1202 ↔ TP1204 ownership (or the labels) would make
  the silkscreen match. TP1208 "TC_ORFET" (Q303) is owned by right. If it should sit at Q303, it belongs at about
  (152, 80.5) on top, above R303, and is currently not placed by hubrails.
- **Power block.** VIN must arrive at x = 138 between y 96 and 107, as a wide pour on top plus an L4 pour.
- **usbc block.** UP pairs in x 168–171 and P5 pairs in x 171–174 at y = 80. Keep TUSB1046's hub-facing pins near x ≈
  171–174 to avoid jogs. VBUS_LAPTOP is needed at about x 158–161, y 80 (HV clearance).
- **front block.** P1 (CR_*) at x 160–162.3, P2 (USBA1_*) at x 162.3–164.3, P3 (USBA2_*) at x 166.5–169, all at y =
  108. +5V comes from the L4 plane.
- **right block.**
  - P4 (ETH_*) along y 105–107.7 and P6 (MCU_USB) on L3 at y ≈ 104–107, both at x = 180.
  - SMBus, HUB_SMB_PU, HUB_RESET_N, USBA*_PWR_EN/OCS_N, I2C_SYS, TEMP_ALERT_N and NTC_ADC1 cross x = 180 between
    y 86 and 107 on inner layers.
