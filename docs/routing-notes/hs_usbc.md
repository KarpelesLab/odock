# Routing notes: `hs_usbc` (usbc block high-speed nets, slow connector nets, links to the hub)

Script: `hardware/odock-10/routing/c_hs_usbc.py` (80 nets, no zones). Adapted to placement-fixes commit 61e4dc2:
- U501 moved 2 mm south, U504 moved 3.2 mm east, C611/C612 swapped, TP1206 moved.
- The lane nets are now in the HS_85 / USB_90 netclasses, so all pairs use the brief's nominal widths and gaps.

Check results:
- Alone (with zone fill): no DRC errors on these nets, and every net is fully connected (own connectivity
  check, `nets with issues: 0 of 80`).
- Run with `d_hs_hub` and `e_hs_eth_sd`: no DRC hits involving these nets.

Impedance widths are the brief's estimates. **Confirm them in JLC's calculator before fab.**

## Plan (usbc.md and hubrails.md reconciled)

1. **Mux end:** L1 escapes, then via pairs to L3 next to the mux hub pins and the SSRX caps.
2. **L3 corridor under the DP caps:** x 160.0–163.1, y 63–76. West to east: UP TX, UP RX, P5 RX, P5 TX.
3. **L3 east runs** at y 75.55 / 76.92 / 77.74 / 78.56.
4. **L3 → L1:** UP pairs at x 166.9–168.6, y 78–79; P5 pairs at x 172.3–174.2, y 79.5.
5. **L1 hub corridor** (hubrails intent): columns 167.95 (UP RX), 169.45 (UP TX), 171.01 (laptop USB2), 171.70 (P5 RX),
   172.97 (P5 TX) and 174.45/174.73 (downstream USB2), down to the hub pins and the TX caps.

Hub-side TX stubs:
- UP: HUB_UP_TXN_IC still crosses under C601's body (0.09 mm track between its pads), because C601/C602 are not swapped.
- P5: now straight stubs.

**Keep-outs for other routers:**
- L3 x 159.75–163.4, y 63–79: hub SS corridor. No through vias in it.
- L3 y 79.3–80.6, x 145.8–171: laptop USB2.
- L1 x 166.6–174.4, y 76.9–80.4: transitions.
- Bottom channels used by LAPTOP_CC:
  - CC2 at x 157.85, from y 66.45 north to 54.6.
  - CC1 on y 67.04 → x 159.2 → y 64.4 → x 163.75 → north to 59.95 → x 164.5 → north to 52.8 under the BGA.

## Per group

| Group | Route |
|---|---|
| DP ML0–3 | L1 straight through C515–C522 |
| DP AUX | L1. DP_AUX_N hops on L3 (forced crossing). |
| Laptop SS lanes | L1 nested L's. TX2/RX1 leave the THT B row on L3 through the B1–B4 / B9–B12 gaps; tracks keep 0.3 mm from VBUS (HV class) |
| Downstream SS lanes | L1. The B-row pairs use 0.35 mm vias between the SMD rows. U503 pin order: RX2 and TX1 hop on L3. TX1 hop vias are now at (175.75/176.4, 66.6), clear of R410. |
| Hub links + SSRX caps | See plan. L3 0.16/0.20, L1 0.10/0.18 |
| UP_SBU1/2 | U501 15/14 → L6 → staggered vias → L1 → R502/R503 → U502 24/25 |
| Laptop receptacle (UP_C_CC1/2, UP_C_SBU1/2, D±) | Four 0.35 mm vias in the freed gap above U501. D+ is A6–B6 on L1. D− runs on L6 from B7 and from the A7 via, west to D504. CC1: L6 into pin 4 plus a loop round the corner to pin 7. CC2 / SBU2 (THT B5/B8 can only exit upwards): L3 above the B row, out between the shell pads, round the shell (CC2 west at x 145.3, SBU2 east at x 156.15). CC2 drops through a via inside the CC1 loop (pins 5/6); SBU2 lands on a via above pin 2. |
| LAPTOP_CC1/2 → PMG1 | L6 along the bottom channels above, vias at (157.95, 52.8) / (157.85, 54.6), then L1 to C416/C417 and N14/N15, J14/J15. The J15 approach is 0.15 mm wide, to keep 0.3 mm from H15 (VBUS_LAPTOP). |
| DS_CC1/2 → PMG1 | Vias just south of U504 pins 12/11, L3 west at y 64.45/64.8, north at x 166.0/165.5, then L1. CC1 passes between C418 and C419 to N1/N2. CC2 runs between the J/H ball column and the cap column to J1/J2. |
| DS_SBU1/2 | L6 down the free column (x 172.25/172.55), west along y 71.8/72.25. SBU1: via → L1 → U503 27 + R542. SBU2: via between AUX-N and SBU1 → U503 26, then L3 → R543. |
| HUB_DSC_DP/DN | U504 pins 20/19 → column vias (171.45, 63.35) / (172.1, 63.4) → L3 east under U504 → south along x 177.0/177.36 → vias at y ~80 → L1 column → hub pins 81/82 |
| Downstream receptacle (DS_C_CC1/2, DS_C_SBU1/2, D±) | A-row nets go to vias between the rows; B-row nets to vias north of the B row (y 57.75). D+ is B6–A6–down the ESD gap to the DP column via (L1). D−: A7 and B7 joined on L3, down to the DN column via. SBU1/SBU2 run on L6 into pins 1/2. CC1/CC2 run on L3 north of the B row, round the east shell pad, then via at (174.35, 60.3) / (175.45, 60.75) and on L6 into pins 4/5. |
| Laptop USB2 to the hub | D504 → L6 → L3 along y 79.7 → vias at y 80.15 → L1 column |

GND return vias are placed automatically: up to 2 per HS transition, at the nearest free spot. Not every site gets them; the tightest connector hops have none.

## Lengths / intra-pair skew (mm, end to end)

| Pair | P | N | skew |
|---|---|---|---|
| UP TX1 / TX2 / RX1 / RX2 | 8.88 / 21.49 / 15.40 / 16.36 | 8.89 / 21.48 / 15.47 / 16.41 | −0.01 / +0.01 / −0.07 / −0.05 |
| DS TX1 / TX2 / RX1 / RX2 | 17.73 / 10.40 / 17.34 / 11.09 | 17.73 / 10.65 / 17.39 / 11.23 | 0.00 / **−0.25** / −0.05 / −0.14 |
| UP SS TX / RX | 47.71 / 43.32 | 47.84 / 43.30 | −0.13 / +0.02 |
| P5 SS TX / RX | 36.26 / 46.66 | 36.20 / 46.66 | +0.06 / 0.00 |
| DP ML0–3 | 4.82–4.91 | 4.87–4.94 | −0.03 to −0.05 |
| Laptop USB2 (receptacle → hub) | 64.82 | 64.43 | +0.39 |
| DP AUX (not matched, 1 Mb/s) | 10.96 | 16.54 | −5.6 |

DS TX2 is the only pair over 0.15 mm. Its P leg runs within 0.3 mm of the RX2-hop vias at U503's NE corner, so there is no room for a bump.

## Remaining / notes for others

- **Nothing is unrouted** in this script's scope.
- **Pins hemmed in by these routes:**
  - The routes leave no via room between the lanes for U502 strap pins 32/35/38 (use via-in-pad).
  - U502 pin 28 and U503 pin 28 (+3V3) are crossed just below their toes by DP_AUX_N / DS_SBU1. Escape diagonally.
  - U502/U503 pins 21–23 (CTL) have UP_SBU / DS_AUX 0.25–0.45 mm below their toes. Use staggered toe vias.
- **Under U504 on L3:** the DSC USB2 run (y 62.9/63.26) and DS_CC2 (y 64.45) pass under it. The EP thermal vias must stay
  within y 63.5–64.2, or use L6/L2 only.
- **L6 under J501:** laptop USB2, SBU and CC2 tracks cut the VBUS_LAPTOP L6 pour. B4/B9 are still reached on L1 and L4.
- **Power-agent conflicts** (VBUS_DS stubs under J502 A4/A9, R415 +5V vias) still apply. Move them off these lanes, as agreed.
