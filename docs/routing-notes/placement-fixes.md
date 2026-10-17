# Placement fixes for routing (2026-10-03)

These changes answer the placement requests in `hs_usbc.md`, `hs_hub.md` and `power.md`. They live in the layout
scripts (`hardware/odock-10/layout/*.py`) and have been applied to `odock-10.kicad_pcb`.

**Board check after `tools/apply_layout.py`:**
- 0 courtyard overlaps.
- No OUTSIDE REGION or MOVED NON-OWNED warnings.

**DRC (`--severity-error`):** apart from unconnected items, there are 163 `[clearance]` errors.
- All 163 are pad-to-pad pairs inside a single IC footprint (U304, U303, U206, U109, ...).
- They come from the HV/PWR_HC netclass rules in the uncommitted `.kicad_pro`. The board as it was before these
  moves shows the same errors.
- No new violations.

Coordinates are footprint origins in mm. "rot" is the KiCad orientation. T = top, B = bottom.

## Changes your scripts must follow

| Script | What changed |
|---|---|
| `c_hs_usbc` | U501 and U504 moved; C611/C612 swapped (the P5 TX polarity detour can go, use `pleft=True`); TP1206 moved out of the lanes |
| `d_hs_hub` | C603–C608 rotated; C609/C610 moved 2 mm east; C835/C836 rotated; R908 moved; L1001 group nudged |
| `e_hs_eth_sd` | R908 moved, so the CLK detour must be shortened |
| `b_power` | C220 now on the bottom; C114/R122 moved off R137.2; R312.2 top side cleared; TP1202 moved; U206 unchanged |

The routers check pad nets, so the stubs they stopped short should now connect once they re-run.

## hubrails (`hubrails.py`)

| Ref | Old | New | Why |
|---|---|---|---|
| C611 (P5 TXP) | 172.35, 88.2 r90 T | **173.6, 88.2** r90 T | P/N order now matches hub pins 83 (P, x 173.0) and 84 (N, x 172.6). Pad 1 is still south (y 88.68) |
| C612 (P5 TXN) | 173.6, 88.2 r90 T | **172.35, 88.2** r90 T | swapped with C611 |
| C603 / C604 (P1 TX) | 160.55 / 161.8, 101.0 r90 | same xy, **r270** | pad 1 (HUB_P1_TX*_IC) now faces north, at y 100.52 |
| C605 / C606 (P2 TX) | 162.3 / 163.55, 105.4 r90 | same xy, **r270** | pad 1 now north, at y 104.92 |
| C607 / C608 (P3 TX) | 166.8 / 168.05, 106.55 r90 | same xy, **r270** | pad 1 now north, at y 106.07 |
| C609 (P4 TXP) | 175.4, 105.5 r0 T | **177.4, 105.5** r0 T | pad 1 (HUB_P4_TXP_IC) at 176.92, 105.5 |
| C610 (P4 TXN) | 175.4, 106.75 r0 T | **177.4, 106.75** r0 T | pad 1 at 176.92, 106.75. This frees the pocket under pins 43–48 (+3V3 / PF3–PF7) for escape vias |
| C613 (+3V3, B) | 169.0, 90.6 | **166.8, 90.6** | swapped with C626 |
| C626 (+1V15, B) | 166.8, 90.6 | **169.0, 90.6** | swapped with C613 |
| D602 | 158.15, 81.5 r0 T | **158.9, 81.4** r0 T | pads: +3V3 at 157.85, HUB_VBUS_SNS at 159.95 |
| C641 | 157.3, 83.25 r0 T | **156.6, 81.4 r90** T | pad 1 (+3V3) at 156.6, 81.88 |
| U603 | 158.15, 86.1 r90 T | **158.15, 84.55** r90 T | pins 1–3 at y 85.69; pins 4/5 at y 83.41 |
| R626 | 158.75, 89.3 r0 T | **159.75, 88.6 r270** T | pad 1 (VBUS_SNS) at 159.75, 87.78; pad 2 (GND) at 159.75, 89.42 |

**Hub pin 99 (+3V3, 166.6, 92.16).** The pad behind its toe is now C613 pad 1 (+3V3, 166.32, 90.60). The pin 99
via can land on or next to that cap pad. Pin 93 (+1V15) now has C626 pad 1 (+1V15, 168.52, 90.60) behind it,
not a +3V3 pad.

**R312.2 (+5V, B, 157.2, 87.36).** The VBUS-detect group has moved toward y 80–86.6 and x ≥ 159. The top side
over x 155.3–158.9, y 86.7–88.4 now has no pads, so the whole R312 pad 2 is free for L4 vias. The U301 pads and the
U303 pads (bottom, y 89.64) still bound the area.

## right (`right.py`)

| Ref | Old | New | Why |
|---|---|---|---|
| C835 (ETH TXP) | 191.4, 61.15 r0 | same xy, **r180** | pad 1 (ETH_TXP_IC) now east, at 191.88, 61.15, toward U801 pin 43 |
| C836 (ETH TXN) | 191.4, 62.4 r0 | same xy, **r180** | pad 1 (ETH_TXN_IC) at 191.88, 62.40, toward pin 44 |
| L1001 | 226.4, 71.35 | **226.4, 71.2** | the whole Pico 2 regulator group moved 0.15 mm north, with its geometry unchanged |
| C1002 | 223.9, 71.4 | **223.9, 71.25** | same group |
| C1001 | 226.4, 69.4 | **226.4, 69.25** | same group |
| C1003 | 228.95, 71.45 | **228.95, 71.3** | same group |

**RP2350 USB pins 66/67 (toes at y 73.01).** A 0.45/0.2 via with 0.15 clearance now fits anywhere in the band
**y 72.40–72.60** between the L1001 / C1002 pads and the pin toes. The band was 0.05 mm wide before.
- Suggested vias: USB_DP_IC at **(224.85, 72.55)** and USB_DM_IC at **(226.10, 72.55)**.
- Each via lands on the IC-side pad 1 of R1007 / R1008 (bottom, y 72.76). On the bottom the stub is then just the
  via-in-pad.

## usbc (`usbc.py`)

| Ref | Old | New | Notes |
|---|---|---|---|
| U501 (TPD4S480, B) | 150.7, 63.05 | **150.7, 65.05** | Pins 1–5 (SBU1, SBU2, VBIAS, CC1, CC2) at y 63.65, x 149.9–151.5. Pins 11/12 (LAPTOP_CC2/CC1) at 151.5 / 151.1, y 66.45. Pins 14/15 (UP_SBU2/1) at 150.3 / 149.9, y 66.45. Pin 20 (VBUS_LAPTOP) at 149.3, 64.25 |
| R512 R513 R510 R511 R508 R509 | grid y 66.85 / 68.1 / 69.35 | grid **y 67.65 / 68.9 / 70.15** | x unchanged (151.75 / 153.9) |
| U504 (TPD6S300, B) | 171.0, 63.4 | **174.2, 63.4** | Pins 1–5 (DS_C_SBU1 … DS_C_CC2) at y 62.0, x 173.4–175.0. Pins 19/20 (HUB_DSC_DN/DP) at 172.8, y 63.0 / 62.6. Pins 11/12 (DS_CC2/CC1) at 175.0 / 174.6, y 64.8. Pins 14/15 (DS_SBU2/1) at 173.8 / 173.4, y 64.8. Pin 9 (FLT) at 175.6, 63.8. Pin 10 (+3V3) at 175.6, 64.2 |
| C537 (VBIAS, B) | 174.0, 63.4 r90 | **177.08, 62.72 r270** | pad 1 (DS_TPD_VBIAS) at 177.08, 61.95 |
| C538 (+3V3, B) | 175.55, 63.0 | **176.85, 65.3** r90 | pad 1 (+3V3) at 176.85, 65.78 |
| R541 (FLT pull-up, B) | 176.8, 63.0 | **177.95, 65.3** r90 | pad 1 (FLT) at 177.95, 65.81 |
| R531 / R532 (DS_EQ0) | 169.95 / 172.1, 66.15 r0 | **169.5 / 170.6, 66.55 r90** | the right-edge straps are now two vertical columns, all west of x 171.11 |
| R529 / R530 (DS_EQ1) | 169.95 / 172.1, 67.4 r0 | **169.5 / 170.6, 68.6 r90** | |
| R523 / R524 (DS_CAD_SNK) | 169.95 / 172.1, 68.65 r0 | **169.5 / 170.6, 70.65 r90** | |
| R410 / R411 / R412 (MUX_DS CTL0 / CTL1 / FLIP) | row at y 71.2 | **173.7, 66.6 / 67.85 / 69.1** r0 | moved under the TX1/RX1 lane copper, where no through via fits anyway |
| R522 (DS_HPD) | 169.95, 69.9 | **173.7, 70.35** r0 | same place as R410–R412 |

**New through-via room** (checked against the current `c_hs_usbc` copper):
- **Laptop side.** The D502/D503 gap above U501 is now free on every layer at **x 149.6–150.8, y 60.6–62.8**. That is
  room for 4–6 staggered 0.45 mm vias for A8 SBU1, A7/A6 D−/D+ and A5 CC1. The B row is THT, so CC2/SBU2/D± can go
  straight down on L6.
  - LAPTOP_CC1/2 now leave U501 at y 66.45, 2 mm lower than before.
- **Downstream side.** The column under the D507/D506 gap, **x 171.3–172.2, y 61.2–69.2**, is now free on every
  layer (it was blocked only by U504 and the strap grid). That is about 12 via positions at 0.6 mm pitch.
  - Suggested use: J502 CC1/CC2/SBU1/SBU2/D+/D− vias at the top (y 61.7–65.0). U504's DP/DN pins (172.8) face the
    column. CC/SBU reach pins 1–5 along y ≈ 61.4 on the bottom.
  - The lower part (y 66–69) is for DS_SBU1/2 (U504 pins 14/15 → R542/R543 → U503 pins 26/27) and for
    HUB_DSC_DP/DN.
- **Bottom corridor.** The bottom strip **x 168.1–168.9** (west of the vertical straps, east of C525) runs from
  y 61.2 down to y 72. It also reaches the free via area **x 168.8–171, y 72–74.4**.
- **DS_CC vias.** For DS_CC1/2 → PMG1, the area **x 164.4–167.8, y 59.8–61.2** (west of J502, above R533/R534) was
  already free.
- U503 decaps C525–C529 are unchanged. C537/C538/R541 are within about 1.5–3 mm of their U504 pins; VBIAS takes the
  longest path.

**TP1206** (`zz_integration.py`): 150.7, 67.55 → **143.7, 64.84** T. It now sits between C501 and TP403, left of D503
and next to the J501 VBUS / D501 side. It is out of the lane fan-in and blocks nothing the lanes use.

## power (`power.py`)

| Ref | Old | New | Notes |
|---|---|---|---|
| C220 (HB2 bootstrap) | 113.9, 80.45 r90 **T** | **115.5, 85.45 r90 B** | pad 1 (BB_HB2) at 115.50, 86.22, under pin 26; pad 2 (BB_SW2) at 115.50, 84.67 |
| C224 (BB_COMP) | 115.45, 85.2 r90 B | **118.6, 84.6 r0** B | under the package above the EP, toward pin 18; pad 1 at 118.12, 84.60 |
| C213 | 115.15, 83.2 B | **115.15, 83.1** B | 0.1 mm nudge for C220 |
| C217 | 114.9, 88.7 B | **114.9, 88.8** B | 0.1 mm nudge for C220 |
| C114 (PD_DVDT) | 113.95, 77.05 r90 **T** | **110.0, 81.5 r0 B** | pad 1 (PD_DVDT) at 109.22, 81.5; pad 2 (GND) at 110.78, 81.5 |
| R122 (PD_OV) | 112.45, 76.45 r90 **T** | **110.3, 80.0 r180 B** | pad 1 (PD_OV) at 110.81, 80.0, toward R121.2; pad 2 (GND) at 109.79, 80.0 |
| TP1202 (`zz_integration.py`) | 106.3, 80.6 B (under Q204) | **108.1, 84.45 B** | still under L201, but clear of Q204's courtyard (y ≤ 82.39), so the Q204 EP can take thermal vias |

**U201.** C220 no longer sits above pins 20–23, and the whole toe column north of the pins (x 113.1–115.1, y 78–82)
is free on top. The R202 Kelvin pair can leave pins 22/23 northward in the normal way, and the vias under the
package are no longer needed.
- HB2/SW2 can drop through 0.4 mm vias at the inner ends of pins 26 and 25, at about (116.05, 86.25) and
  (116.05, 85.6). These lie between the pin ends (x 115.9) and the EP (x ≥ 116.6). The HB2 via overlaps C220 pad 1.
- C121 (+3V3, at the toes of pins 23–26) is unchanged.

**R137.2 (VIN).** The R122/C114 pads no longer sit over R137 pad 2 (x 112.0–115.5, y 75.7–77.2). The whole pad, plus
the strip down to y 77.6, is now free on top for VIN vias. Before, only a single column at x 115.0 was free.

C114, R122 and TP1202 now sit on the bottom inside the `P_BB_SW2` area, where KO_BB_SW2 forbids vias on L3/L4.
- Take their GND pads out on L6 to a via outside that area. For C114/R122, go north into the GND via box at
  y < 79.3. For TP1202, go south of y 85.7.
- The PD_DVDT and PD_OV traces also leave on L6.

**Not changed (small nudges did not help):**
- **U206 +5V sink vias.** The spot is boxed in by C211's GND pad (top, to x 131.4), R246 (top) and C239 (bottom,
  SNK_DVDT at pin 7). There is no free spot nearby for R246 or C239 without crowding U206's other pins. This needs a
  real rework of the sink cluster.
- **J502 A9 VBUS_DS and R415.1 +5V vias.** These are routing-level fixes, as already suggested in `hs_usbc.md`. Tie
  A9–B4 / A4–B9 between the J502 rows, and put the +5V vias inside or north of R415 pad 1 (y 78.3–79.4).

## zz_integration (`zz_integration.py`)

A target can now be an absolute point as well as a footprint:
- `("@", (x, y), side)` searches for the nearest free spot around (x, y).
- `("=", (x, y), side)` places the part exactly at (x, y).

**R908** (µSD CLK series R): 129.1, 107.25 B → **119.4, 114.9 B (r0)**.
- Pad 1 (CR_USD_CLK) is at 118.89, 114.90 and pad 2 (CR_USD_CLK_S) at 119.91, 114.90.
- It sits just west of the U901 escape via row (y 114.3, CLK via at x 123.2), so the 11 mm CLK detour goes away.
- It is placed with `=` because the free-spot search treats the J901 socket outline as blocking the whole area.
