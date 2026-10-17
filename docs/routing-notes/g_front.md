# odeck-10 routing, phase g: front region (`g_front.py`)

Script: `hardware/odeck-10/routing/g_front.py`.
- `NETS = []` and `GROUPED = True`. Everything it draws lives in group `route:g_front`, and only that group is
  replaced on re-run.
- Region: `layout/front.py` `REGION`. That is the card-reader column, the USB-A block and the microSD corner.

## Check

Full pipeline, run on a scratch copy:

```
apply_routing.py <scratch>/odeck-10 --only a_planes,b_power,c_hs_usbc,d_hs_hub,e_hs_eth_sd,f_fanout,g_front,z_stitch --drc
```

- **0 DRC errors** anywhere on the board. That covers clearance, short, hole, width, edge and mask. Only
  unconnected items remain.
- **Local nets:** 25 nets / about 47 connections at the start. **2 connections remain**: U901.16 (CR_RTERM) and
  U901.25 (CR_3V3). Section 3 says why.
- **Supply pads in the region:** all +3V3, +5V and CR_3V3 drops are connected, except U901.25. Two GND pads remain:
  C914.2 and J902.13 (section 3).
- **Size:** 92 route entries, 71 vias (69 at 0.45/0.25, 2 at 0.35/0.15).
- **Copper length:** about 515 mm in total: B.Cu 270 mm, In2.Cu (L3) 143 mm, F.Cu 101 mm.

## How the geometry was made

- The coordinates are frozen output of a grid A* router. It ran against the board after `a_planes`…`f_fanout`.
- **Grid:** 0.025 mm, or 0.0125 mm in tight spots.
- **Clearances:** 0.15 mm plus a raster margin. 0.3 mm to USB_90/HS_85 tracks and HV copper. 0.2 mm hole clearance.
- **Limits:** routes stay inside the region rectangles + 0.5 mm. Rule-area keep-outs are respected.
- **Corners:** 45° only, no acute angles. 90° corners are chamfered where there is room.
- **P_\* power pours** are hard obstacles for tracks. Vias may punch through them, and the pour refills around the
  hole. This applies to:
  - about a dozen vias in the +5V_USBAx F.Cu output pours;
  - the INA180 GND via, in the SW_IN L1/L3 strips.
- The router tooling is in the session scratchpad, not in the repo (`route_g_front/tools/grid.py` and
  `drive.py`). Re-running `g_front.py` simply redraws the frozen copper. If an earlier script changes, the geometry
  must be regenerated.

## 1. Card reader (U901 GL3224, bottom)

### Pins to their caps (B.Cu)

| Pins | Caps / net |
|---|---|
| 6, 15, 34, 44 | CR_3V3 to C905, C906, C907, C908 |
| 9, 26 | CR_1V2 to C909, C910 |
| 33, 43 | VUHS2 / VUHS1 to C912 / C911 |
| 3 | GND to the EP |

- **Track widths:**
  - CR_3V3 / CR_1V2: 0.2 mm, necked to 0.12 mm where the pin field requires it (pins 15 and 34);
  - VUHS2: 0.12 mm, under C912.2.
- **Joins:**
  - The CR_3V3 groups (C903 / C904 / C905 / C906 / C907 / C908 / R902) are joined on B.Cu, with short L3 hops.
  - CR_1V2 runs C910 → C909: B, then F.Cu under the SD socket, then B.
  - CR_3V3 and CR_1V2 stay local nets, never joined to +3V3.

### Crystal (B.Cu only)

- XI: pin 13 → Y901.1 → C919.
- XO: pin 14 → Y901.3 → C920.
- Each is under 4 mm. Nothing high-speed runs under Y901.

### SD slot 1 detect / WP

- CDZ and WP use d_hs_hub's reserved toe vias, at (137.15, 114.65) and (137.15, 115.35).
- From there they run on L3 under the socket and finish with a short F.Cu stub to J901.10 / J901.11.
- R904.1 joins CDZ through a channel via (see the strap rows below).

### microSD slot 2

- **CR_USD_CDZ:**
  - Pins 35 and 36 are tied. A via in the free corner above pin 36 (129.55, 114.15) leads to F.Cu, then to R905.1.
  - From R905.1, F.Cu runs south of the USB-A shell tabs (y ≈ 129–130) to J902.9.
  - It never enters the L3 band.
- **CR_USD_VCC:**
  - 0.4 mm, about 79 mm long.
  - Route: J902.4, then a via next to the pad, then B.Cu. On B it runs south-west to y ≈ 135.3, west under the
    USB-A bodies, and north at x 125.45 to b_power's U901.24–C916 trace.
  - It stays clear of the J901 peg hole.

### Bottom-row straps and LED

- **Escape vias.** Pins 21, 19 and 17 escape through vias placed between b_power's +5V via (131.39, 121.61) and
  f_fanout's C906.2 GND via (134.3, 121.72):
  - LED_IC: (132.45, 121.66), 0.35/0.15;
  - SPI_CK: (133.0, 121.66), 0.35/0.15;
  - SPI_MISO: (133.62, 121.65), 0.45/0.25.
- **Why 0.35 vias.** NC pins 18 and 20 sit above and C902 below. That leaves no 0.45 slot for pins 21 and 19, so
  0.35 is the "unavoidable" case.
- **Routing to the resistors.** From those vias the signals go on L3/F to R906 / R903 / R902.
- **Strap rows.** R902/R903/R906 and R907/R904/R905 sit over the L3 microSD band. Vias only go in the 0.86 mm channel
  between the two rows, at y 129.2:
  - R907.1 (LED_IC, joined to R906.1);
  - R904.1 (SD CDZ);
  - R905.1 (uSD CDZ).
- **CR_LED_A:** R907.2 → D901.2 on B.

## 2. USB-A ports (both ports, same scheme)

| Net | Route |
|---|---|
| SW_IN | C704/C712 bulk → via → 0.6 mm L3 → the L3 SW_IN strip. C705/C713 HF → 0.5 mm L3 up the west side to C704's via. |
| +3V3 | U702.5 / C706 / C707 / U703.5 joined (0.2 mm). Feed is 0.3 mm on B.Cu along y ≈ 121–123. Port 1 feeds port 2; port 2 drops through a via at (180.45, 119.1) into the right block's L4 +3V3 plane (outline x ≥ 180.3, y ≤ 119.3). That via is the only copper outside the main rectangle, inside the +0.5 mm margin. |
| ILIM | TPS pin 5 → via → L3 → R701/R706. Kept out of the INA180 pin field. |
| EN | U702.4 → R703 (pull-down) → TPS pin 3 (via, L3, via). |
| ISNS | U703.1 → R705 (filter R). Crosses under the SS channel on L3 only, never B.Cu in the channel. |
| INA180 GND (U703.2 / U706.2) | Own via. The signal routes cut its B.Cu pour feed. The via sits in the SW_IN pour margin, and the strip refills around it. |
| VBUS clamp D702.5 / D704.5 | 0.3 mm. F stub, via, L3 under the SS channel, via, into the +5V_USBAx F pour. |

## Interblock escapes (left to Freerouting)

Each escape is a B.Cu stub plus a 0.45 via.

| Net | Via |
|---|---|
| CR_LED (R906.2) | (135.16, 128.5) |
| CR_CD_USD_N (R905.2) | (135.12, 129.2) |
| CR_CD_SD_N (R904.2) | (135.85, 129.2) |
| USBA1_PWR_EN (U702.1) | (144.15, 116.86) |
| USBA1_FORCE_EN (U702.2) | (143.2, 116.86) |
| USBA1_FORCE_EN (R702.1) | (146.22, 120.53) |
| USBA1_ISENSE (R705.2 / C708.1, joined) | (155.84, 113.43) |
| USBA1_OCS_N (U701.4, F) | (144.6, 114.25) |
| Port 2 | Same pattern: U705.1 (163.15, 116.86), U705.2 (162.2, 116.86), R707.1 (165.22, 120.53), R710.2 (175.51, 113.78), U704.4 (162.7, 116.3) |

Keep L3 above the band (y < 129.4) east of x 135 free for the card-reader detect / LED lines.

## 3. Not done, and what would fix it

1. **U901.16 (CR_RTERM → R901) and U901.25 (CR_3V3 LDO output → C903) are boxed in by f_fanout GND dog-bone vias.**
   - **U901.16:** C906.2's via at (134.3, 121.72) sits 0.19 mm under pin 16.
   - **U901.25:** C910.2's via at (128.7, 120.3) sits in the only pocket left of pin 25. b_power's U901.24 → C916
     CR_USD_VCC trace runs under it.
   - **These must be fixed before fab.** Without RTERM the USB PHY has no reference. Without pin 25 the 3.3 V LDO
     output is not connected to its 10 µF cap or to the other CR_3V3 pins.
   - **Fix (f_fanout):** give C906.2 and C910.2 a 0.351/0.15 via-in-pad (add them to `VIP_PADS`) instead of the
     dog-bone.
   - `g_front.py` already holds the routes for that case (`COND`):
     - RTERM: 0.35 via at (134.3, 121.64), then F.Cu to R901.1;
     - pin 25: 0.35 via at (128.8, 120.3), then an L3 hop to C903.1.
   - Those routes are drawn automatically once no GND via sits at the two blocking points. That case was verified
     by simulating the f_fanout change on the scratch board: **0 DRC errors and 0 unconnected local nets.**
2. **C914.2 (GND, SD VCC cap) cannot be connected.**
   - It is boxed by the SD1 bus (B.Cu, y 112.0 / 113.2) and by C914.1 / b_power's CR_SD_VCC via at (124.45, 112.6).
   - b_power's CR_SD_VCC L3 hop runs right under the pad, so a via-in-pad would short it. f_fanout had already
     failed on this pad.
   - **Fix (b_power):** move the CR_SD_VCC hop / via so a VIP fits in C914.2.
3. **J902.13 (GND shell tab) is outside the board edge** (y 138.9–140.8 vs edge 139). No legal copper can reach it.
   - It is the same metal shell as J902.10/11/12/14, which are connected, so it is electrically fine.
   - It shows as one unconnected item. A footprint net-tie, or a DRC exclusion, would silence it.
4. **Deviations from the layout notes:**
   - The microSD VCC runs on B.Cu, not with the L3 bus, because the band is full.
   - SD CDZ / WP run on L3/F.
   - The +3V3 feed comes from the right block's L4 plane at x 180.45, inside the +0.5 mm margin. The notes had it
     arriving "eastward on L3/L6 at y 113–125".
