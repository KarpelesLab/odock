# Routing notes: `g_usbc` (usbc region, phase g)

Script: `hardware/odeck-10/routing/g_usbc.py` (`NETS = []`, `GROUPED = True`: everything it draws is in group
`route:g_usbc`, and only that group is replaced on a re-run). It runs after a_planes, b_power, c_hs_usbc, d_hs_hub,
e_hs_eth_sd and f_fanout, and before z_stitch / Freerouting.

**Status: partial.** DRC is clean (no clearance, short, hole, width or annular errors from this script), but a
large part of the usbc local nets cannot be finished with the current rules and the current HS / fan-out copper.
Numbers and the blockers are listed below. Each blocker comes with the change that would unblock it.

## How it works

Everything is automatic. The only hard-coded parts are the policy tables at the top of the script.

1. **Snapshot.** Zones are filled, except `GND_L1` / `GND_L6`, which are unfilled first because the autoroute step
   removes them. KiCad connectivity then gives the copper clusters of every net in the region.
2. **Grid router.**
   - 0.05 mm grid on F.Cu / In2.Cu / B.Cu, 8 directions with only 45° turns, through vias.
   - Obstacles are rebuilt for each window from every pad, track, via, hole and other-net `P_*` pour.
   - Clearances are applied per net pair:
     - 0.15 mm (netclass);
     - 0.30 mm across the HV boundary. The exempt footprints are read from the `.kicad_dru` "high voltage" rule;
     - 0.30 mm track-to-track from USB_90 / HS_85 tracks;
     - 0.20 mm copper-to-hole (NPTH included) and 0.25 mm hole-to-hole;
     - 0.30 mm to the board edge.
   - Copper stays inside the usbc rectangles + 0.5 mm.
   - No through vias in the hs_usbc keep-outs: the L3 hub-SS corridor x 159.75–163.4 / y 63–79, the L3 laptop USB2
     run, and the hub-link transitions. The bottom CC channels are existing copper, so they are respected.
3. **(A) PMG1 BGA escapes.** These use PathFinder-style negotiation, all balls together.
   - Same-net neighbour balls are joined on L1 first (VDDD B8–D8–D6–F6, +5V L14–L15 / L1–L2).
   - Inner balls (rings 2+) take a 0.35/0.15 via-in-pad and leave the ball field on L3/L6.
   - Outer-ring balls are left to phase B, which reaches them on L1. Interblock balls of the side columns get a
     stub that ends on a via.
4. **(B) Local nets.** The clusters of each local net form a minimum spanning tree, giving 2-point requests. Every
   request, plus the stray supply pads of GND / +3V3 / VBUS_LAPTOP, is negotiated together:
   - occupancy is the exact clearance footprints on the fine grid;
   - conflicts are found geometrically (segment/via distances), with history costs;
   - up to 30 passes.
   - Each conflict-free path is then re-checked against the copper emitted before it. If that check fails, a greedy
     A* takes over, with a 0.10 mm neck-down as the last resort.
5. **(C) Supply drops.** Every stray pad of +5V, PMG1_VDDD, +3V3, GND, VBUS_DS or VBUS_LAPTOP in the region is tied
   to the nearest same-net copper: a plane via, a pour or a track.
   - IC and ESD-array supply pins (U\*, D\*) may take a via-in-pad straight into the plane.
   - The PMG1 +5V group may use a long trunk to the L4 +5V island (window up to 26 mm).

Widths: signals 0.15 mm; GND / +3V3 / VDDD / VBUS_DS drops 0.20 mm, falling back to 0.15; +5V 0.30 → 0.20 → 0.15.
Vias: 0.45/0.25 by default, 0.35/0.15 where 0.45 does not fit, and 0.35/0.15 for via-in-pad. The board minimum
annular ring is 0.10 mm, so there are no 0.30 vias.

Re-run:
```
GUSBC_DEBUG=1 apply_routing.py <scratch>/odeck-10 --only a_planes,b_power,c_hs_usbc,d_hs_hub,e_hs_eth_sd,f_fanout,g_usbc,z_stitch --drc
```
- The script takes about 13 min in KiCad's Python.
- `GUSBC_PHASES=AB` skips the supply phase. `GUSBC_NEG_ITERS` sets the number of negotiation passes.

## Result (full pipeline a–f + g_usbc + z_stitch, current rules, `--drc`)

- **DRC errors: 0.** Only unconnected items are reported (capped at 499 board-wide). There is no clearance, hole,
  edge, annular or width error anywhere.
- Drawn by g_usbc: 687 mm of track, 61 vias of 0.45/0.25 and 43 vias of 0.35/0.15 (via-in-pad included).

| Unconnected connections in the region (KiCad connectivity, filled zones) | before g | after g |
|---|---|---|
| Local nets (45 nets, partition.json "local"/"usbc") | 96 | **34** |
| +3V3 pads | 30 | 11 |
| GND pads | 12 | 4 |
| +5V pads | 7 | 4 |
| VBUS_LAPTOP pads | 4 | 4 |

Local connections still open:
- **Straps.** UP: EQ0, I2C_EN, SSEQ0, SSEQ1, DPEQ0, DPEQ1, HPDIN. DS: EQ0, I2C_EN, SSEQ0, SSEQ1, DPEQ0, DPEQ1. In
  each case the mux pin is cut off from its resistor pair.
- **Protector pins.** UP_TPD_VBIAS, DS_TPD_VBIAS, UP/DS_CCPROT_FLT_N.
- **Mux control.** MUX_UP_CTL0 (×2), CTL1, FLIP; MUX_DS_CTL0, CTL1 (×2), FLIP (×2). These are the mux pins 21–23
  and some BGA balls.
- **HPD.** DS_HPD (M10), HPD1_OUT (G14 → R413).
- **Other PMG1 nets.** P3V3_SNS (A9), PMG1_UART_TX (A3 → TP404), DS_SRC (C14/R2 → R415), DS_GOUT (P1 → Q402).
- **VBUS_DS.** J502.A9 and U401.H14.

Supply pads still open:
- +3V3: U502.6/20, U503.1/6/28, U401.B14, U1205.5/8 + C1205, R513.2, R532.2, U504.10.
- GND: R507.2, D506.3/8, R527.2 + R539.2, R516.2.
- +5V: U401.C15, L1/L2, L14/L15, C412.1.
- VBUS_LAPTOP: U401.A15, H15, C414.1, U501.20.

With the two rule changes proposed below (U401 HV exemption, "via in pad" 0.12 mm), a test run drops the
script's failure count from 67 to 53. Most of the straps, CTL pins and protector pins then close.

Impedance: g_usbc draws no controlled-impedance nets.

## Blockers (not fixable inside g_usbc; each needs one of the changes below)

Checked "in isolation": each of these connections fails even on the a–f board with nothing else of g_usbc drawn.

1. **HV rule vs the PMG1 VBUS balls.**
   - U401 is not in the exemption list of the `.kicad_dru` "high voltage" rule. H15 / A15 (VBUS_LAPTOP) and B15
     (VBUS_LSW) therefore need 0.3 mm to the neighbouring balls.
   - Consequences:
     - H15 has no legal exit at all.
     - H14 (VBUS_DS), B14 (+3V3) and G15 (EXT_PWR_PRESENT) cannot take a via-in-pad: 0.205 mm < 0.3 mm to H15/B15.
   - **Fix:** add `A.memberOfFootprint('U401')` / `B.memberOfFootprint('U401')` to the pad exemptions. This is the
     same reasoning already used for U10\*/U20\*. The script reads the rule, so a re-run picks it up.
2. **Via-in-pad on the 0.4 mm-pitch USB-C parts.** This affects U502/U503 straps (pins 2, 3, 11, 14, 17, 32, 35, 38),
   CTL/FLIP pins 21–23, +3V3 pins 1/6/20/28, and U501/U504 VBIAS/FLT.
   - A 0.35/0.15 via (the 0.10 mm annular ring is the minimum) leaves 0.125 mm to the neighbour pads. That is less
     than the 0.15 mm netclass clearance.
   - The c_hs_usbc lanes and the SBU/AUX tracks at the toes leave no other exit (hs_usbc.md says "use
     via-in-pad").
   - **Fix:** add a DRU rule
     ```
     (rule "via in pad"
       (condition "A.Type == 'Via' && B.Type == 'Pad' && (B.memberOfFootprint('U501') || B.memberOfFootprint('U502') || B.memberOfFootprint('U503') || B.memberOfFootprint('U504'))")
       (constraint clearance (min 0.12mm)))
     ```
     JLC 6-layer handles 0.09 mm. The script parses a rule named "via in pad" and uses its clearance for via-in-pad.
     Rules 1 and 2 together cut the failures from 67 to 53 in a test run.
3. **LAPTOP_CC1 on B.Cu under the BGA (c_hs_usbc).** It runs along y 52.8, x 157.95–164.0, so no via-in-pad is
   possible in ball rows L/M/N.
   - Unreachable as a result: the **PMG1 VCONN supply balls +5V L1/L2/L14/L15** and DS_HPD M10. The L1 exits are
     closed by the CC1/CC2 L1 tracks and vias at the side columns, and C15 too.
   - **Fix:** take CC1 under the BGA on L3, or north of the ball field (y ≤ 50.9).
4. **U401.D12 (I2C_PD_SDA) is boxed in.** Around it sit E14/C14 via-in-pads (needed for XRES / DS_SRC), the B-row
   vias, the D10 via, and the f_fanout GND via-in-pad in F12.
   - **Fix:** a BGA-area rule allowing 0.1 mm tracks and 0.1 mm clearance inside the U401 courtyard. Or f_fanout
     joins F12 to F10 on L1 instead of a via in F12. Even then the channel is marginal.
5. **U504.3 (DS VBIAS → C537) and U504.9 (FLT → R541).** They are closed in by the hs_usbc CC/SBU L6 fan-out into
   pins 1/2/4/5 and by the f_fanout GND dog-bones of pins 6–8.
   - **Fix:** move C537 / R541 next to those pins on the F side, or route the GND of pins 6–8 through the EP.
6. **J502.A9 (VBUS_DS).** DS_C_TX2_N runs on L3 right under the pad, so no via-in-pad fits. The B-row TX2 hop vias
   block the A9–B4 tie between the rows.
   - **Fix:** in c_hs_usbc, move the TX2_N L3 segment 0.25 mm off A9.
7. **U502.3 (UP_SSEQ1) and U503.21 / R412.1 (MUX_DS_FLIP).** Hub-SS / DS_AUX copper at the pins (c_hs_usbc).
8. **Capacity.** The rest of the failures are congestion, not single blockers. The strap grids under/next to the
   muxes, the BGA→mux CTL lines, and the long PMG1 debug lines all compete for the same space:
   - SWD to TP401/TP402 at x 140 and to JP402/JP403 at x 178;
   - UART to TP404/TP405;
   - XRES to TP403 and Q401;
   - DS_SRC, DS_GIN/GOUT to Q402/R415.

   The negotiation ends with about 15–40 conflicting requests and the greedy pass does not recover them all.
   - Fixing 1–3 frees most of the BGA side.
   - Moving the probe pads TP401–TP406 closer to the PMG1 (they are at x 139–144) would remove about 60 mm of
     long routing from the busiest band.

## Not done / left for others
- Every connection named in the result table as unconnected.
- The interblock nets (I2C_PD_\*, VBB_\*, LAPTOP_\*, EXT_PWR_PRESENT, PDIN_PRESENT, VBUS_LSW, TEMP_ALERT_N,
  I2C_SYS_\*) are left to Freerouting.
  - BGA balls of rings 2+ have via-in-pad escapes out of the ball field.
  - The side-column balls end on a via.
  - Row-A interblock balls (A14, A7, A5, A2) are on the outer ring, with L1 access to the south.
- +3V3 / GND of U1205 (x 139–141, inside the VBUS_LAPTOP copper) have no same-net copper within reach.
  b_power / hubrails should bring +3V3 there.
