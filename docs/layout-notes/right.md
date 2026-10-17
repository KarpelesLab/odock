# odock-10 layout notes — right block (Ethernet, MCU, Display & UI, sensors U1206–U1208)

Script: `hardware/odock-10/layout/right.py` (187 refs: ethernet 8xx, mcu 10xx, display_ui 11xx, U/C1206–1208,
TP1207). Board 130 × 89 mm: front edge y = 139, H4 at (226,135).
Region: (180,50)–(230,121.5) and (198,50)–(230,139). The corner (180,121.5)–(198,139.5) is kept free on top for the
microSD socket J902. Two overhang rectangles cover parts that stick out past the board edge (the J801 courtyard at
the back; the SW1101/SW1102 actuators and the J1102 courtyard at the front).

**Check status** (`apply_layout.py --only right`): no MOVED NON-OWNED and no overlap between two of my parts.
**One OUTSIDE REGION remains, U1101 (the LCD outline).** See the first open point: the panel cannot fit between the
RJ45 and the J902 corner. A stricter check also passes: courtyard gaps ≥ 0.2 mm, ≥ 4 mm from H2 and H4, ≥ 0.5 mm
from the edge, nothing on top in the J902 corner, the J902 via row (x 183–192, y 120.5–121.3) free on both sides,
and the FPC path clear.

## Floor plan (top view, back edge at top)

```
 x 180                       202        222  230
 y 50 ┌ U805 U806 Q801 R820/1 ┬── J801 RJ45 ──┬ (H2)
      │ U802 C801-3 U804 TP1207│  rot 180       │ U1002 flash (rot 270)
      │ ==USB corridor== U801  │  LED pins top  │ C1001 L1001 C1002 C1003 (VREG)
 y 64 │ L801 U803 C806 (buck)  │  MDI pins y 67–70
 y 71.6├── LCD panel U1101 (rot 180), x 180.3–216.5, y 71.6–123.4 ──┤ U1001 RP2350B (223.7, 78.3)
      │   foam window + J1103 (197.95, 87.9)          │ Y1001, TP1001–4
      │   U1207 at (198.4, 92.3)                      │ SW1001 BOOTSEL, SW1002 RESET
      │   (bottom side: display, header, MCU support) │ J1101 user header (right edge, y 105–127)
 y 121.5 (J902 corner, x<198) ┤ J1001 (y 125–128), RC parts, D1001 / D1002
                              │ SW1101 201.6 | SW1102 208.4 | U1208 213 | J1102 Qwiic 218.3 ┤ (H4 226,135)
 y 139  FRONT EDGE
```

## Key decisions

### LCD (U1101, J1103)
- **The panel is at rot 180: its FPC (tail) edge faces the back of the board.** Rot 0 is impossible because the
  unfolded-tail drawing in the outline footprint would reach 21 mm past the front edge, which fails the region check.
  It also has real benefits:
  - the fold loop (1.3–2 mm past the tail edge) lands on the board, not past the front edge;
  - the buttons and Qwiic at the front edge stay clear of it.
- **Firmware has to rotate the image 180°** (ST7789 MADCTL MX+MY) so it reads correctly from the front. IPS viewing
  angles are symmetric, so nothing else changes.
- Panel centre (198.4, 97.5). Panel edges x 180.3–216.5, y 71.6–123.4. The top edge just clears the RJ45 body
  (y 71.4); the bottom edge reaches 1.9 mm into the J902 corner (open point 1). Before that change, this was the
  largest panel position that
  leaves 12.5 mm for the MCU column at the right edge and clears the buttons at the front.
- **J1103** is at panel centre + R180·(0.43, 9.6) = (197.95, 87.9), rot 180, with its opening toward the tail edge.
  - That puts it 14.5 mm inside the tail edge, as in display_ui.md. Pad 1 is at x 195.2 and pad 12 at x 200.7,
    which keeps the panel-pin-n → contact-(13−n) mapping.
  - Foam window: x 193.5–202.7, y 71.6–90.5. Tail path: x 194.7–201.2.
  - **The FPC loop zone (x 194.3–201.4, y 69.6–71.6) and the tail path down to J1103 are empty on the top side.**
    Keep them free of silk text and exposed copper (solder mask over everything under the gold fingers).
- **Under the panel (top side)**, only these parts: J1103 (1.0 mm), U1207 (WSON 0.8 mm, just below the foam window,
  ≈ 5 mm from the panel centre), and a 0.05 mm sliver of D1104 (USON 0.55 mm).
  - Everything else under the panel is on the **bottom** side: backlight parts, LCD caps, the TCA9534, pull-ups, and
    the ADC filters.
  - Foam tape: cut a pocket for U1207, or simply let the 1.5 mm foam take the 0.8 mm part.
- **Fitting the panel:** with the panel held face-down "beyond the tail edge", it sits over the Ethernet area. The
  RJ45 (13 mm tall, x ≥ 202) is next to the tail (x 194.7–201.2). Hold the panel tilted while you insert the tail.
  Check this on a sample before freeze.
- R1101 (39 Ω, 0.19 W) is on the bottom side, so there is board between it and the panel.

### Ethernet
- **J801**, rot 180, at (212, 62.95). The edge marker is on y = 50 and the courtyard sticks out 0.54 mm.
  - Courtyard x 202.3–221.7, which is 4.3 mm from H2.
  - Pin positions: MDI P row at y 67.14 and N row at y 69.68, with pair 1/2 (MDI0) on the left (x 206.3/207.6) and
    7/8 (MDI3) on the right (x 216.4/217.7). LED pins at y 56.2/58.3. Shell pins at (204.1/219.9, 63.8), pegs at
    (206.3/217.7, 60.8).
- **U801 RTL8156BG**, rot 90, at (196.5, 63.6):
  - MDI side faces +x (the jack);
  - USB side faces −x (the hub), with pins at x 193.55, y 65.7–68.2;
  - the strap/LED/I²C side faces up;
  - pins 1–14 (XTAL, RSET, PLL, SWR_EN) face down toward the panel.
- **No room in front of the jack.** The jack's PCB side (y > 72) is where the panel is, and "nothing hot under the
  LCD" rules out the RTL there. So the RTL sits to the left of the jack, and the MDI pairs run about 7–18 mm on L1.
- **MDI pair order (router and design owner must decide):**
  - The pairs can only enter the pin field from the left/bottom. Above the pin rows, the shell pin and pegs block
    the way.
  - Entering from the bottom, the nested order would need MDI0 at the top of the bundle. The RTL's right side has
    MDI3 at the top (y 66.1) and MDI0 at the bottom (y 70.3), so the order is reversed and the pairs would cross.
  - Recommended fix, as ethernet.md suggests: **use the RTL MDI-swap option (DS 6.15) and swap the pair mapping in
    the schematic** (RTL MDI0 ↔ jack pair D 7/8, MDI1 ↔ C 4/5, MDI2 ↔ B 3/6, MDI3 ↔ A 1/2). With that, the bundle is
    fully nested on L1 with no vias.
  - Without the swap, two of the pairs need a layer change (L1 → L6, L5 GND reference, with GND stitching vias next
    to each signal via).
- **AC caps C835/C836** are in-line on the PHY TX pair (pins 43/44), right at the left side, in the USB corridor.
- **USB corridor:** x 180.5–193, y 64.5–69.5 on top is kept free of parts except C835/C836. The ETH_SS_TX±,
  ETH_SS_RX± and ETH_DP/DN pairs leave the block at **x = 180, y ≈ 61–64** toward the hub. Keep each pair's
  intra-pair skew ≤ 0.1 mm.
- **0.95 V buck** (U803, L801, C806/C807 input, C808/C809 output) is below the corridor at x 181–192, y 64.5–69.3.
  - Hot loop: C806 sits right at the VIN/GND pins, and SW is 3 mm to the L801 pad.
  - The feedback divider (R802/R803) and EN pull-down (R801) are on the bottom under U803.
  - Keep the ETH_SW node small, on L1 only.
- **Crystal Y801 (with C833/C834/R804) is on the bottom side** under the RTL's bottom edge. The top side there is the
  strip next to the panel/FPC loop.
  - XI/XO (pins 11/12 at x 197.7/198.1, y 70.95) drop through one via each, about 3 mm.
  - Keep the crystal traces and the GND guard on L6, with an L5 GND island under them.
  - RSET R805 is on the bottom at pin 14.
- **Strap resistors (R808, R810–R815, R818, R819) and the jack LED resistors (R816/R817) are on the bottom**, above
  the RTL's top pin row.
- **Decoupling.** The caps for the bottom pin row (C825, C823, C805, C810, C820) are on the bottom between the EP and
  the crystal. C837/C838
  (CT caps) right below jack pins 5/6 (x 211–213). Everything else is on the bottom: a column under the MDI-side power pins
  (C812/C821/C813/C822/C814), a row under the top pins (C817/C824/C829/C830), and a column under the USB-side power
  pins (C818/C831/C832/C819/C826). Nothing is under the 4.7 mm EP, which is for the thermal via field.
- **PLL bead FB801 and C804 (22 µF)** are on the bottom at x ≈ 187. C805 (100 nF) is on the top, right at pin 9.
- **Back strip:**
  - U802 (PHY load switch, +3V3 → ETH_3V3), U805 (EUI-48 EEPROM), U806, Q801 (I²C bridge), U804 (LED buffer).
  - R816/R817 (jack LED resistors) at x 201. The green LED pin 13 is on the far side of the jack (218.7, 56.2), so
    route that trace on L3 under the jack between the pegs.
- **U1206** (TMP1075 "ETHERNET") is on top between the RTL's top-right corner and the jack, at (200.7, 62.3).
  **TP1207** (TC_ETH) is at (200.5, 58.8).

### MCU (RP2350B)
- **U1001**, rot 0, at (223.7, 78.3), in the 12.5 mm column at the right edge. It is not under the panel, so it can
  be probed and reworked.
  - QSPI/USB/VREG edge faces up (back), the XIN/SWD/LCD edge faces down, HDR_GPIO/PD/hub-SMBus faces left, and the
    ADC/LED/button edge faces right (board edge).
- **Flash U1002**, rot 270, sits above the RP2350 at (225.85, 64.0), right of the jack and 5.3 mm from H2. Its bottom
  pin row (SD0, SCLK, SD3, VCC) faces the RP2350 in the same order as QSPI pins 70–72.
- **Regulator (copy of the Pico 2 geometry):**
  - L1001, rot 180: pad 1 (VREG_LX, un-dotted) at (227.4, 71.35) over pin 63; pad 2 (+1V1, dot) at (225.4, 71.35)
    over VREG_FB pin 65. **Check in the JLC CPL preview that the dot lands on pad 2.**
  - C1002 (C_out) is beside pad 2, C1001 (C_in, pin 64) is above L1001, and C1003 (VREG_AVDD) is at the right edge.
  - R1001 is on the bottom.
  - Route PGND (pin 62) to the C1001/C1002 grounds on L1 with a short wide trace, not only through vias.
  - Keep +1V1 off the L4 plane: local copper on L1 to DVDD pins 10/32/51 (pin 32 has C1028 under it, on the bottom).
- **USB 27 Ω resistors** R1007/R1008 are on the bottom right under pins 66/67. MCU_USB_DP/DN (full speed) run left
  under the panel on L3. They leave the block at
  **x = 180, y ≈ 74–80** toward hub port 6.
- **Crystal Y1001** is under the XIN/XOUT pins at (223.5, 86.4), with R1003 (1k XOUT) and C1020/C1021 tight against
  it. Keep the crystal and its traces on L1 over solid L2 GND, and route no other signals under it.
- **Decoupling** sits on the bottom at the pin ring, inside the pads, but not under the 3.4 mm EP (keep that clear
  for its via field). C1006 (10 µF) is on the bottom below the chip.
- **SWD pads** TP1001–TP1004 are a column at x 218.45, y 90–97 (SWCLK, SWDIO, RUN, GND). They are outside the panel,
  so a pogo clip can reach them.
- **BOOTSEL and RESET** (SW1001/SW1002) are below, top-push. R1005/R1004/R1006 are on the bottom next to them.
- **TCA9534 (U1003)** is on the bottom under the panel at (211, 76.6). Its signals are slow and come from all over
  the board.
- **Pull-ups** are a column on the bottom at x 216.6, y 72.7–82.7, left of the chip: I²C_SYS, I²C_PD, I²C_EXT,
  IOX_INT, TEMP_ALERT, ETH_RESET_N, P7.
- **ADC filters** (C1024–C1027, C1108/C1109, R1018–R1021) are a row on the bottom at y 84.5–86.8, x 212–218.4.
- **J1001** (debug UART, unpopulated) is horizontal in the front strip at (202.5–207.6, 126.5).
- **D1001** (power, green) and **D1002** (status, red) are right behind SW1101/SW1102 at y ≈ 134, so they
  can be seen from the user's side.

### Front edge and user I/O
- **SW1101/SW1102** (side-push) are at x 201.6 and 208.4, rot 0. Body front is on the edge (y = 139) and the actuator
  sticks out about 2 mm. Their RC parts are on the top side just behind them.
  - Per display_ui open issue 4, keep the ALPS keep-out between the button pads free of copper.
- **J1102 Qwiic** is at (218.3, 136.55), courtyard 4.05 mm from H4 (226,135), rot 0, body front on the edge.
  D1104 and C1107 are right behind it.
  - **Check:** the mating face of the SM04B-SRSS-TB is assumed to be on the mounting-tab side (+y), as on SparkFun
    boards.
- **U1208** (AMBIENT) is on the front edge between SW1102 and Qwiic at (213.0, 136.95), rot 90. This follows the lead's
  instruction; sensors.md still says "front-left near SD", so update that doc.
- **J1101** user header (2×8, unpopulated) is on the right edge: pin 1 at (224.95, 107.0), courtyard to y 126.6,
  8.4 mm from H4 at (226,135).
  - The top side at x 217.4–223 next to it is left empty for the silkscreen pinout.
  - ESD arrays D1101–D1103, 220 Ω R1106–R1113, R1114/R1115, F1101/F1102 and C1105/C1106 are on the bottom just left
    of the header pins. None are under the THT pins.

## Routing intent

| Net / group | Layer and path | Notes |
|---|---|---|
| ETH_MDI0–3 ± (100 Ω diff) | L1, RTL right side → jack pins from the lower left, bundle y ≈ 66–71.5 | Pair-order issue above: MDI swap (schematic) or vias on 2 pairs. Length-match within each pair ≤ 0.15 mm; no matching between pairs needed. No parts or vias between the RTL and the jack apart from GND stitching. |
| ETH_MCT | C837/C838 right below jack pins 5/6 (top side, y 72.6, x 211–213, under the panel's top edge) | Short and wide. |
| ETH_SS_TX±, ETH_SS_RX± (C835/C836 in-line), ETH_DP/DN | L1 (USB_90 class) through the corridor, leaving at x 180, y 61–64 | GND stitching vias on both sides of the corridor every ~2 mm. The AC caps sit in-line with symmetric fan-out. |
| ETH_3V3 | Pour on L4 under the Ethernet block (from U802 at the back strip to the RTL, U803 VIN, the LED/I²C parts) | 0.6 A max. |
| ETH_0V95 | Island on L4 (or L3) under the RTL, fed from the L801/C808/C809 node | Separate from ETH_3V3 on L4. 0.65 A max. Short, wide connections to pins 7/13/18/24/31/42/52/56. |
| ETH_SW | L1 only, U803 pin 2 → L801 pad 1 | Small; no plane under it on L3. |
| RTL EP | ≥ 16 thermal vias to L2/L5 GND | Thermal: ~1 W. U1206 GND/EP pour joined to the RTL GND copper on L1. |
| ETH_XI/XO | Through vias to the bottom crystal (L6), guarded | ≤ 3 mm per side. |
| +1V1 | L1 local copper: L1001 pad 2 / C1002 → VREG_FB (65) → DVDD pins 10, 32, 51 | Copy the Pico 2 layout. Never via the inductor node. |
| VREG_LX | L1, L1001 pad 1 → pin 63, < 2 mm | No other copper under L1001 on L3. |
| QSPI | L1 / L3, RP2350 top pins → flash, < 10 mm | Keep away from VREG_LX. |
| MCU_USB_DP/DN | L1 out of R1007/R1008, then L3 under the panel to the hub (exit at x 180, y ≈ 74–80) | Full speed; 90 Ω if convenient. |
| LCD_* (SCK/MOSI via R1022/R1023) | L3/L6 under the panel, RP2350 bottom-left pins → J1103 | ~25 mm. Under the FPC fingers: solder mask only. |
| HDR_GPIO0–7, HDR_ADC0/1 | RP2350 left/right pins → bottom resistors/ESD → J1101 | ESD lands right at the header pins. |
| I2C_SYS | Daisy chain: RP2350 → TCA9534 → U805/Q801 → U1206 → (other blocks) | Away from ETH_SW and VREG_LX. |
| GND | L2/L5 solid under the whole block | Stitch top/bottom GND pours around the RTL, the jack shell pins and the crystal areas. |

## Cross-block exits
- **To hubrails:** the Ethernet USB 10G + USB2 pairs at x = 180, y 61–64. MCU_USB_DP/DN at x = 180, y ≈ 74–80.
  HUB_SMB_DAT/CLK/PU and HUB_RESET_N come from the RP2350 left side under the panel and leave at x = 180,
  y ≈ 80–90.
- **To usbc (PMG1):** I2C_PD (with PD_INT and PDIN_INT), PMG1_SWCLK/SWDIO (through R1026/R1027) and PMG1_XRES_N
  leave toward the top-left of the block, at x = 180, y ≈ 75–80.
- **To front:** USBA1/2_FORCE_EN, USBA1/2_ISENSE, CR_LED, CR_CD_SD_N/CR_CD_USD_N (to the TCA9534) and NTC_ADC0/1,
  along the bottom of the panel area (x = 180, y ≈ 100–125).
- **To power:** EXT_PWR_PRESENT, LAPTOP_OVP_N, PDIN_PRESENT, TEMP_ALERT_N; slow signals on inner layers.
- **Rails in:** +3V3 (RP2350, LCD, U802), +5V (R1101 backlight, F1101).

## Open points for the lead
1. **The LCD does not fit with the J902 corner reserved down to y = 121.5.** The panel is 51.8 mm tall (52.3 mm
   outline bbox). It spans x 180.3–216.5, so it always overlaps both the RJ45 (body to y 71.4, x 202–222) and the
   reserved corner (x < 198). The space between them is 50.05 mm, about 1.9 mm short. The panel is placed at the
   lowest position that clears the jack (y 71.6–123.4, bbox to 123.66). Ways out:
   - (a) reserve the corner only from y ≥ 123.7;
   - (b) let the panel (on 1.5 mm foam) overhang the rear 1.9 mm of J902, but only if the DM3AT top is < 1.4 mm
     there;
   - (c) move J902 so its rear clears x 180.3–198 below y 123.7.
   The Ethernet top side ends at y 69.3, so the FPC loop zone (y 69.6–71.6) is clear for any of these.
2. **MDI pair order:** see the Ethernet section (schematic pair swap plus the RTL MDI-swap eFuse/strap, or vias).
3. **The LCD is rot 180**, so firmware must rotate the image. Before freeze, check with a sample panel that the tail
   can be inserted next to the RJ45.
4. **Qwiic mating face:** check the SM04B-SRSS-TB footprint orientation (opening on the tab side).
