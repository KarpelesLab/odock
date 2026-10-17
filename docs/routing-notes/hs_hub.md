# Routing notes: hub downstream links, Ethernet MDI, SD / microSD (hs_hub)

Scripts:
- `hardware/odock-10/routing/d_hs_hub.py`: hub ports P1 (card reader), P2 (USB-A 1), P3 (USB-A 2), P4 (Ethernet), P6 (RP2350), and the hub crystal.
- `hardware/odock-10/routing/e_hs_eth_sd.py`: Ethernet MDI, PHY crystal, SD slot 1 and microSD slot 2.
- `hardware/odock-10/routing/_hs_lib.py`: shared helpers (pair offsetting, length tuning). The leading `_` keeps
  `apply_routing.py` from running it as a script.

Neither script owns any zones. Both print their length table and warnings when applied.

## Update after placement fixes (commit 61e4dc2)

- **Previously blocked legs now connect.** All TX cap legs connect: P1/P2/P3 through C603–C608, P4 through
  C609/C610 at x 177.4, and U801 pins 43/44 through C835/C836. Pad positions are recomputed from the board.
- **microSD.** CLK now goes U901 → L3 over the D0/D1 vias → R908 (119.4, 114.9) → CLK_S on B.Cu → via (118.45,
  119.75) → its L3 lane. All six lines are matched to 116.02 mm (was 138.06).
- **RP2350 USB stubs.** Done: vias at (224.85 / 226.10, 72.55) on R1007/R1008 pad 1, then L1 to pins 67/66.
- **Escape room.** These spots are kept clear and pass DRC with test vias (`KEEP_TEST=1`):

  | Pin | Via position |
  |---|---|
  | Hub pin 99 (+3V3) | (166.45, 91.15) |
  | Hub pin 100 (RBIAS) | (165.75, 91.4) |
  | Hub pins 9 / 18 (+1V15) | (164.15, 96.55) / (164.3, 100.12) |
  | U901 pins 1/2 (CDZ / WP) | (137.15, 114.65 / 115.35) |

  To make room:
  - XI was lowered to y 90.67.
  - CR_DP/DN was moved to x 137.72.
- **Card-reader L6 lanes.** Re-spaced to y 108.05 / 108.95 / 109.85 for the 0.3 mm USB_90 rule. The P2 lanes moved to
  y 111.2 / 111.9.
- **GND return vias added:**
  - (160.75, 110.55) at the CR TX L1→L6 change;
  - two at the P4 RX L3→L1 change, at (189.9, 61.775) and (189.0, 60.5).

  There is still no room in the hub pocket around (171–174, 107.5): MCU L6 and RX L3 run at the only free spots.
  There is also no room at the MDI pair vias or the CR RX L3 vias.
- **Remaining DRC (my nets).** The only errors left are 18 "hs pair spacing" hits between the two halves of the
  same `*_TX?_IC` pair (HUB_P1/P2/P4_TX?_IC, ETH_TX?_IC).
  - KiCad does not see `..._TXP_IC` / `..._TXN_IC` as a diff pair (the name doesn't end in P/N), so
    `isCoupledDiffPair()` is false.
  - Fix in `.kicad_dru`: add `&& !(A.NetName ~ '*TX?_IC' && B.NetName ~ '*TX?_IC')` to that rule.
  - The legs are a proper 0.10 / 0.18 coupled pair.
- **Unchanged.** P4 TX still threads C610's pad gap, because the hub-pin and cap P/N order is still crossed.
  Swapping C609 and C610 would remove that.

## Status (original pass)

- **DRC.** With only these two scripts applied (`--only d_hs_hub,e_hs_eth_sd`), DRC has 0 clearance, short,
  width or hole errors on track or via items. The rest of the report is unconnected items.
  - It stays at 0 with the four test vias from `TOE_VIAS` added (`KEEP_TEST=1`). These are the toe vias the
    power/plane scripts need between my pairs: +1V15 at pins 9 and 18, and RBIAS at pin 100.
- **Conflicts with the other agents' scripts (2026-10-03 snapshot).** Running all scripts together shows these:
  1. `a_planes.py` places GND stitching vias on a 4 mm grid without checking for tracks. Several land on my routes:
     - the P4 column at x 180.4, y 80.8–103.2;
     - (180.8, 68.8), which sits in the only L1 path through the C536/C808 pinch;
     - (112, 124), (120, 120) and (127.2, 119.6), under the microSD lanes;
     - (113.7, 107.7), (127.6, 107.6) and (136, 108), where they sit on SD vias or tracks;
     - (172.8, 124.8).

     KiCad then re-assigns some of them to my nets. The stitching pass should skip copper of other nets, or run
     after the signal scripts.
  2. In `b_power.py`, CR_SD_VCC (C914 → J901.4 on B.Cu) crosses the SD1 bus, which is on B.Cu. Its via at
     (122.82, 109.7) also clips the microSD CLK on L3. Hop that net on L3 between y 108.3 and 110 instead.

## Impedance / geometry used

These values are estimates. **Confirm them in JLC's impedance calculator for JLC061611-1080A before fab.**

| Use | L1 / L6 (microstrip over L2 / L5) | L3 (stripline) |
|---|---|---|
| USB SS and USB2, 90 Ω diff | w 0.10 / gap 0.18 | w 0.16 / gap 0.20 |
| Ethernet MDI, 100 Ω diff | w 0.09 / gap 0.20 | — |
| SD / microSD, 50 Ω SE | w 0.12 | w 0.20 |

Other geometry rules:
- Corners are 45° only.
- Intra-pair matching uses small 45° bumps (USB) or chamfered accordions (MDI, SD) on the short line.
- At least 0.3 mm between different pairs, except in a few fan-outs. The DRC "hs pair spacing" rule is met.

## What is routed

### P1: U601 → U901 GL3224 (card reader, 5 Gb/s)

- **TX.** U601 pins 7/8 run on L1 west, then south at x 161.2 to C603/C604. From the caps they go down to swap
  vias at (161.95, 109.0) and (161.4, 109.75), then L6 west on lane y 109.45. They turn south at x 141.5, then west
  into U901 pins 10/11.
- **RX.** U601 pins 10/11 go to stacked vias at x 162.9, in the free bottom column between R624 and R607. From
  there:
  - L3 west, then south at x 160.6;
  - swap vias at (160.95, 107.85) and (160.35, 108.55);
  - L6 west on lane y 108.75;
  - south at x 139.98 into the bottom caps C918/C917. GL TX → caps is on B.Cu.
- **USB2 (CR_DP/DN).** L1 west lane at x 159.3, then swap vias at (159.6, 106.5) and (159.16, 107.2). From there:
  - L6 west on lane y 108.05;
  - south at x 137.27 into U901 pins 4/5.
- **Swap vias.** Every pair needs one P/N swap between the hub order and the GL3224 order. It is done
  geometrically at the via pair, with no crossing.

### P2: U601 → J701 (USB-A 1)

- **TX.** U601 pins 16/17 run on L1 down x 162.9 through C605/C606, then west on y 110.6. They go south at x 150.75
  into D701 (flow-through), then fan out to the J701 THT pins.
- **RX.** U601 pins 19/20 go down x 163.8, jogging to x 164.25 east of the caps. They run west on y 111.3, then
  south at x 152.25.
- **USB2.** Toe vias at (164.3, 98.25) and (164.3, 98.85) take USBA1_DP/DN to L3. From there:
  - L3 down x 163.6, then diagonally to D702;
  - D702 flow-through on L1;
  - DP to pin 3 on L3, DN to pin 2 on L6.

### P3: U601 → J702 (USB-A 2)

- **TX and RX.** Straight down on L1 through C607/C608, D703 and the fan-out. The pairs jog east at y 109–112,
  above the TPS2553 U704.
- **USB2.** Vias at (165.75, 108.25) and (166.35, 107.75), then:
  - L3 on y 109.67 to x 174.5;
  - D704;
  - DP to pin 3 on L3, DN to pin 2 on L6.

### P4: U601 → U801 RTL8156BG (10 Gb/s)

- **TX.** U601 pins 36/37 dive to y 108.1 and come back up into C609/C610. The polarity is crossed between pins
  and caps: TXP threads the 0.4 mm gap between C610's pads (0.09 mm trace) up to C609.
  - North of the caps: L1 at x 180.2 to y 63.1, then east into U801 pins 46/47.
  - The 2.87 mm hub-side skew is cancelled on the cap→U801 leg. The total U601→U801 skew is 0.
- **RX.** U601 pins 39/40 go to vias at (171.25 / 171.95, 107.5). From there:
  - L3: through the via field, then a column at x 180.0 up to y 61.8;
  - vias at (189.4, 61.15) and (189.4, 62.4), with 2 GND return vias;
  - L1 toward C835/C836.
- **ETH USB2.** L1 outer lane on y 108.8 and x 181.2. It hops to L6 at (180.9 / 181.6, 71.9) around the
  C536/C808 pinch, comes back to L1 at stacked vias at (181.6, 63.75 / 64.45), and runs into pins 49/50.

### P6: U601 → RP2350 (MCU_USB, full speed)

The route goes:
1. pins 41/42 on L1;
2. vias at (172.7 / 173.4, 107.5);
3. L6 east on y 107.9–108.25, then north at x 182.6;
4. L3 at y 72.9 / 73.26, clear of the J801 pins and the PHY crystal vias;
5. vias at (222.9, 71.0 / 71.75);
6. B.Cu into R1007/R1008 pad 2. DN passes between R1007's pads.

The RP2350-side stubs (USB_DP/DM_IC, R pad 1 → pins 66/67) are **not** routed. There is no room for two vias
between L1001 and the pin row; this needs the right-block owner.

### Hub crystal (Y601 → U601 pins 98/97, L1, 0.12 mm)

- XO is the outer loop: north of C328, down x 164.5, into pad 3 from the east.
- XI runs inside it and threads between the crystal's pad rows into pad 1.
- C638 and C637 (bottom) hang off one via each, at (164.5, 91.5) and (165.0, 92.0).
- The toe of pin 100 (RBIAS) is kept free for its via at (166.05, 91.3).

### Ethernet MDI (L1 / L6, 100 Ω)

Decision: no MDI-swap eFuse.
- **MDI0 and MDI1 on L1.** They pass under the GND shell pin (y 66.15 and 65.47). The P line lands on the
  upper-row pin. The N line continues and drops between pins to the lower row. MDI1 rises to y 63.8 after the
  shell pin to make room for its tuning.
- **MDI2 and MDI3 on L6, through pair vias.**
  - MDI2's vias are at x 202.1, in the slot between the bottom cap column and the shell pin. On L6 it runs under the
    shell at y 65.45.
  - MDI3's vias are at x 202.9, north of the shell pin. On L6 it threads the 0.89 mm gap between the shell pin and
    the peg hole, then runs at y 63.0.
- **Stagger skew.** The jack's staggered rows make N about 3.8 mm longer. Accordions on P cancel it.
- **Return vias.** No GND return vias at the MDI pair vias (no room). The signal is 2.5GBASE-T, at about 200 MHz.

### PHY crystal

- XO drops at the Y801 centre via (197.6, 71.1) and runs east between the pad rows to R804.
- XI goes around the south of that via to its own via at (195.45, 71.1), then to Y801.1 and C833.
- XO_X: R804 → Y801.3, and R804 → C834.
- Both vias are tented and sit in the FPC loop zone. Check the mask there.

### SD slot 1 (B.Cu, 50 Ω)

- This deviates from the layout note, which asked for L3. The bottom is free under the socket, so the U901 pins
  need no escape vias.
- The six lines are nested. Each gets one via just north of its contact (y 107.85), then a short L1 stub.
- All six lines are matched to 23.38 mm (target = D1), using accordions in the free bottom area.
- CLK has 0.42 mm meander spacing and at least 0.6 mm to its neighbours. There is no separate GND guard trace.

### microSD slot 2

- **U901 end.** Bottom stubs run west between C912 and C910, then north into a via row at y 114.3. The CLK via is at
  x 123.2.
- **L3 lanes.** They fan out west under the SD socket (tuning accordions there), then turn east into the band
  y 129.7–132.4.
- **J902 end.** The lanes go north at x 179.0–181.7, then east on y 120.2–122.9, and drop into one via per contact
  (y 123.4, north of the contact row).
- **CLK.** CLK has to visit R908, which sits at (129.1, 107.25), 11 mm north of pin 29. It detours on L3 to vias at
  (128.59 / 129.61, 106.5) and comes back as CLK_S.
- All six lines are matched to 138.06 mm, set by CLK. The design note expected about 90 mm (see blocking items).
- The band uses 0.5 mm pitch, with 0.6 mm around CLK.
- CDZ and VCC are not mine. Room is left for their vias at x 183.2, 186.35 (GND) and 188.55 in the contact via row.

## Length / skew (mm, P / N, measured pad to pad or to the stopping point)

| Link | Layer(s) | P | N | Skew |
|---|---|---|---|---|
| P1 HUB_P1_TX_IC (U601→cap) | L1 | 8.97 | 8.97 | 0 |
| P1 CR_SS_TX (cap→U901) | L1 → L6 | 42.55 | 42.55 | 0 |
| P1 CR_SS_RX (U601→C917/8) | L1 → L3 → L6 | 41.20 | 41.20 | 0 |
| P1 CR_TX_IC (U901→caps) | L6 | 7.31 | 7.31 | 0 |
| P1 CR_DP/DN | L1 → L6 | 49.76 | 49.76 | 0 |
| P2 HUB_P2_TX_IC | L1 | 7.90 | 7.90 | 0 |
| P2 USBA1_SS_TX (cap→J701) | L1 | 31.23 | 31.23 | 0 |
| P2 USBA1_SS_RX | L1 | 37.63 | 37.63 | 0 |
| P3 USBA2_SS_TX (cap→J702) | L1 | 19.41 | 19.41 | 0 |
| P3 USBA2_SS_RX | L1 | 22.92 | 22.92 | 0 |
| P3 USBA2_DP/DN | L1 / L3 / L6 | 23.00 | 22.85 | 0.15 |
| P4 TX total U601→U801 | L1 | 73.80 | 73.80 | 0 (hub leg +2.87, cap leg −2.87) |
| P4 ETH_SS_RX (U601→caps) | L1 → L3 → L1 | 69.75 | 69.75 | 0 |
| P4 ETH_DP/DN | L1 / L6 / L1 | 73.34 | 73.35 | 0.01 |
| P6 MCU_USB_DP/DN (full speed) | L1 / L6 / L3 / L6 | 94.62 | 97.17 | 2.5 (FS USB, not tuned) |
| MDI0 / MDI1 | L1 | 11.80 / 17.61 | same | 0 |
| MDI2 / MDI3 | L1 → L6 | 21.81 / 25.44 | same | 0 |
| SD1 D0–D3, CMD, CLK | L6 + L1 stub | 23.38 (all six) | | 0 |
| µSD D0–D3, CMD, CLK (pin→R908→J902) | L6 stub + L3 + L1 stub | 138.06 (all six) | | 0 |

## Blocking items for the lead (placement)

1. **C603/C604, C605/C606 and C607/C608 must be rotated 180°.** These are the hub TX AC caps for P1, P2 and P3.
   - Their IC-side pad (pad 1) faces away from U601. The legs can't pass straight through, and the 0.63 mm gap
     between the caps is too narrow to wrap around them.
   - For now the six legs stop 0.75 mm short of the caps. Rerunning the script after the rotation connects them,
     because the code checks the pad nets.
2. **C835/C836 must be rotated 180°.** These are the RTL TX caps, and the same problem applies.
   - The RX legs stop short.
   - ETH_TXP_IC / ETH_TXN_IC (U801 pins 43/44 → caps) are routed automatically once the caps are rotated.
3. **R908 (microSD CLK series R) is at (129.1, 107.25), 11 mm from U901 pin 29.** Move it within about 3 mm of the
   pin-29 escape, for example on the bottom west of the via row at about (119.5, 115). That cuts about 25 mm from
   all six microSD lines. The code then needs its CLK detour shortened.
4. **C609/C610 sit under pins 46–50.**
   - P4 TX has to loop under pins 38–48. The PF3–PF7 strap pins and the +3V3 pin 43 can only escape through
     vias in the pocket around y 107.5, which my RX and MCU vias already use.
   - Moving C609/C610 about 2 mm east (x ≈ 177.5) frees the pocket.
5. **Hub pin 99 (VDD33) has no free toe via spot once XI/XO are routed.** C626's +1V15 pad sits right behind it.
   Options: move C626, or use via-in-pad.
6. **U901 pins 1/2 (SD1_CDZ / WP) can't escape east on B.Cu past the CR_DP/DN pair.** They need toe vias.
7. **Missing GND return vias.**
   - None at the P4 RX L1→L3 change in the hub pocket (no space; there are 2 at the RTL end).
   - None at the 5G card-reader transitions.
   - The stitching agent can add them once the pocket frees up (see item 4).

## Remaining

- Everything in the blocking items.
- The RP2350 USB_DP/DM_IC stubs.
- GND guard traces and stitching along the SD/microSD buses and the P4 column. These belong to the plane agent.
  Keep the stitching off the tracks.
