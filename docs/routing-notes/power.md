# odock-10 routing notes: copper zones, power routing, GND stitching

Scripts (all in `hardware/odock-10/routing/`):
- `a_planes.py`: zones and keep-outs only (no tracks, `NETS = []`).
- `b_power.py`: power pours, via arrays, gate drives, Kelvin taps, card-reader VCC, and the hot-loop GND vias.
  `GND` is in its `NETS`.
- `z_stitch.py`: board-wide GND stitching, the edge fence, and GND on H1–H4. It runs last, after the HS scripts
  and the autorouter.
- Helpers in `_pwrlib.py`: zone/keep-out helpers, a via placer that checks every pad, hole, track and via already
  on the board, a small A* grid router, and `load_ghosts()`.

**`b_power.py` routes around the final HS copper.** At the start of `route()` it applies `c_hs_usbc`, `d_hs_hub`
and `e_hs_eth_sd` to a scratch copy of the board file (`load_ghosts`). Their tracks and vias then count as
obstacles for every via and track it draws. No HS copper is ever moved.

**Check (wave 2):** `apply_routing.py --only a_planes,b_power,c_hs_usbc,d_hs_hub,e_hs_eth_sd,z_stitch --drc`.
- 0 errors other than the HV fine-pitch class (item 1 in section 3). None involve HS copper.
- 45 HV errors remain. All are a track or via touching a 0.5 mm-pitch pin whose neighbour pin is on the other side
  of the HV rule: U201, U104, U105, U109, U202, U204, U205, the Q201 gate, and the J101/J501 A-row VBUS links.
- With the `.kicad_dru` clause in item 1, the full run gives **0 errors** (only unconnected items).

## 1. Zones (`ZONES` in both scripts)

| Layer | Zones | Priority |
|---|---|---|
| L2 In1.Cu | `GND_L2` whole board (0.5 mm pull-back, 4 mm keep-out around H1–H4) | 0 |
| L5 In4.Cu | `GND_L5` same | 0 |
| L4 In3.Cu | `L4_GND` everywhere + power islands (table below) | 0 / 5 |
| L1 / L6 | `GND_L1`, `GND_L6` whole board (free areas) | 0 |
| L1 / L6 / L3 | power pours `P_*` (b_power.py) | 10 |
| L1 / L6 | switch-node copper `P_BB_SW1`, `P_BB_LS`, `P_BB_SW2`, `P_5V_SW`, `P_5V_SW_L6` | 11 |
| L1 | hot-loop GND copper `P_GND_HOT_*` (buck/boost/LM5148 input caps to FET sources) | 12 |

All zones: 0.3 mm clearance (meets the 0.3 mm HV rule everywhere), solid pad connection, min width 0.25 mm,
islands removed.

L4 island map (power plane, everything else on L4 is GND):

| Island | Area | Feeds |
|---|---|---|
| `L4_VBAR` | x 100.5–118.8, y 50.5–64 (+ strip down to y 69.6 at x < 103.4) | J102 pin 1 (THT) → Q106 sources |
| `L4_VBUS_PDIN` | x 119.4–133, y 50.5–63.6 (+ x 128.6–133 to y 66) | J101 VBUS (THT B4/B9) → D101 / Q104 |
| `L4_BB_PSO` | x 100.5–114.2, y 70.4–74.3 + x 100.5–109, y 74.3–78.4 | boost output caps C205–C208, R202.1 |
| `L4_VIN` | x 109.3–115.9, y 74.6–88 (tab at R137) + x 100.5–138, y 88–107.7 + hubrails x 138–151.6, y 95–107.7 | Q201/C201–C204, U201 VIN, C122, LM5148 Q301/C301–C306 |
| `L4_VBB_OUT` | x 116.3–131, y 74.8–87.6 (+ x 116.3–121.3 from y 71.8) | R202.2, C209–C212, Q213 sources |
| `L4_SRC_MID` | x 121.7–132.8, y 66.4–74.4 | Q213/Q214 drain EPs (thermal) |
| `L4_VBUS_LAPTOP` | x 133.4–154, y 50.5–66.2 + tab x 133.4–138.6 to y 70.4 | R243.2/C233 → D501 → J501 B4/B9 (THT) |
| `L4_5V_BUCK` | x 138.5–151.5, y 80.4–90.3 | copy of the bottom 5V_BUCK pour (C309–C314) |
| `L4_P5V` | sink strip x 131.4–156.2, y 76–80.4; hub centre x 151.9–164.4, y 80.4–108; strip x 164.4–176, y 86–90.4; tab x 168.6–172.4, y 76.4–86 (R415); front x 100.5–180, y 108–138.5; J902 corner x 180–198 from y 119.6 | U206 sink output, R312.2 (LM5148 output), U304 VIN, USB-A shunts R704/R709, U901, R415 |
| `L4_P3V3` | usbc x 154.4–166.5, y 50.5–75.7; band over J502 y 50.5–56.4 to x 180.3; strip x 180.3–183.3 down to y 72; right block x 180.3–229.5, y 72–138.5 minus the J902 corner; MCU column x 222–229.5 from y 58.6; hub band x 156.5–168.3, y 75.9–85.8 | L302.2 (+3V3 buck), muxes/PMG1, RP2350, LCD, U802 |
| `L4_VBUS_DS` | x 166.8–179.7, y 56.8–75.6 + x 172.9–179.7 to y 80.3 | Q402 pin 3, J502 VBUS, D505, C536 |
| `L4_P1V15` | under U601 x 164.6–179.7, y 90.8–105.4 + column x 174.5–179.7 from y 80.6 (x ≥ 176.3 for y 86–90.8) | L303.2 / C338–C341 → hub VCORE caps |
| `L4_ETH_3V3` | x 183.6–202, y 50.5–59.3 + x 183.6–192.4 to y 64 | U802 OUT (via `P_ETH_3V3_U802`) |
| `L4_ETH_0V95` | under the RTL x 192.7–201.8, y 59.6–71.6 + x 183.6–201.8, y 64.3–71.6 | L801.2 (via `P_ETH_0V95_L801`) |

L3 hub/usbc corridors (x 159.5–164 down to y 80, and the P1/P2 channel) sit over solid `L4_P3V3` / `L4_P5V`;
the only split they cross is y ≈ 85.8 (+3V3 → +5V) if they continue on L3 below y 80. Card-reader SS on L3 should run east
along y 108–112 (all `L4_P5V`) before turning north at x ≥ 152, not north at x ≈ 139 (that is `L4_VIN`).

Keep-outs (rule areas): `KO_HOLE_1..4` (r = 4 mm, all layers); switch nodes `KO_BB_SW1_*`, `KO_BB_LS`, `KO_BB_SW2`,
`KO_5V_SW_*` (no tracks/vias/pour on L3/L4 under the SW copper; `_L6` copies forbid L6 pour under the BB nodes;
the Q302 EP keeps its thermal vias); `KO_3V3_SW`, `KO_1V15_SW`, `KO_ETH_SW`, `KO_VREG_LX` (nothing on L3);
`KO_RJ45` (no pour on L1/L4/L6 under the cable-side half of the magjack, x 202.3–221.7, y < 60; L2/L5 stay solid
because the shell is GND per ethernet.md); `VOID_<cap>_<pad>` = L2 (top caps) / L5 (bottom caps) voids under every
SS/DP AC-coupling cap pad (C509–C522, C530–C535, C601–C612, C835/C836, C917/C918).

GND stitching (`z_stitch.py`, runs last):
- **Grid:** 4 mm (≈ 190 vias). **Edge fence:** 1.4 mm in from the edge, 2.5 mm pitch (≈ 60 vias).
- **Size:** 0.46/0.25. The 0.46 mm diameter is the tag: on a re-run the script deletes exactly these vias, so it is
  idempotent with `NETS = []`.
- **Placement check:** a via goes in only where it clears every pad, track and via of another net on all layers
  (0.2 mm, or 0.3 mm to HV copper), and every via-forbidding rule area.
- **Excluded areas:**
  - all courtyards;
  - the power stages and the power pours;
  - the usbc block, including the L3 hub corridor x 159.75–163.4 / y 63–79, the CC channels and the U504 EP area;
  - the HS channels from `hs_usbc.md` / `hs_hub.md`;
  - the card-reader / microSD / Ethernet corridors.
- **Mounting holes:** H1–H4 pads are set to GND. Their 4 mm keep-out now blocks tracks and vias only, so the
  planes reach the holes.

b_power also adds the hot-loop GND via rows (8–12 per loop) and the GND escapes for C114, R122 and TP1202. These
three parts now sit on the bottom inside the SW2 area, so they leave on L6 to vias north or south of the
keep-out.

## 2. Power paths (current sizing: 1 oz, IPC-2152 ≈ 20 °C rise; vias 0.6/0.3 unless noted)

| Path | Copper | Width | Vias (layer changes) |
|---|---|---|---|
| VBAR (≤ 8 A barrel): J102.1 → Q106 sources | L4 island + L6 pour (J102 → between peg and sleeve → y 62–64 → Q106) + L1 at D102 | L6 ≥ 1.45 mm neck, L4 ≥ 8 mm | 5 at D102, 4×0.5/0.25 at Q106 |
| BAR_MID / PD_MID (FET-pair drains) | L6 pours over both EPs | 4.4 mm | none (drain pads under D101/D102, per notes) |
| VBUS_PDIN: J101 → D101 → Q104 | L4 island, A4/A9→B9/B4 links (0.25), L1 D101 pour, L6 Q104/C101 pour | 4 mm | 3 filled via-in-pad D101.1/Q104 1–3 + 1 at C101 |
| VIN_OR → R137.1 | L6 pour | 3.4 mm | – |
| VIN: R137.2 → L4 → Q201, C122, U201, hubrails | L6 pour at R137, L4 `L4_VIN`, L1 pours at Q201/C201–C203, C122, Q301/C301–C305, L6 pours under the buck caps and Q301 | L4 ≥ 3.6 mm tab, then plane | 10 at R137, 9 Q201 EP, 6 caps, 4 C122, 8 Q301 EP/drain, 6+4 LM5148 caps |
| BB_SW1 / BB_LS / BB_SW2 / 5V_SW | small L1 shapes only (5V_SW also L6 under Q302, 9 EP vias) | pad-sized | – |
| BB_PSO: Q204 → caps → R202.1 | L1 pours + L4 island + L6 at C207 | ≥ 2.7 mm | 13 + 3 thermal in the Q204 EP |
| VBB_OUT (5 A, ≤ 28 V): R202.2 → C209–C212 → Q213 | L1 pours + L4 island | plane | 14 |
| SRC_MID (Q213/Q214 drains) | L1 + L4 + L6 | EP-wide | 15 thermal (EP arrays) |
| VBUS_LSW (5 A): Q214 → R243.1 → Q217 | L1 + **L3 helper pour** x 133.4–138.6, y 69.5–81.6 (L1 is choked by R116/C232/R247/C235) | L3 5 mm | 5 + 4 |
| VBUS_LAPTOP (5 A): R243.2/C233 → D501 → J501 | L1 at both ends, L4 island ≥ 8 mm, L6 pour under J501/D501, A4/A9→B9/B4 links | plane | 8 + 8 + 1 |
| +5V sink (≤ 3.3 A): U206.6 → L4 | 0.3 mm stub + small L6 pour | – | **2** |
| 5V_ISNS (8 A): L301.2 → R303.1 | L1 pour 1.9–3.8 mm | | – |
| 5V_BUCK (8 A): R303.2 → C309–C314, Q303 | L6 pour + L4 copy | plane | 4 (R303.2 via-in-pad) + 10 |
| 5V_OR: Q303 → R312.1 | L6 pour (1 mm neck at x 154.5–155.5, under R303) | | – |
| +5V (8 A): R312.2 → L4 plane | L6 pour (to x 162.8 east of U303) | | 9 (7 via-in-pad in R312.2 + 2 east of U303); C323 5, C324 1 |
| +3V3 / +1V15 buck outputs | L4 islands | plane | 6 (L302.2) / 5 (L303.2) |
| DS_SRC / DS_FETD / VBUS_DS (3 A) | L1 pours at R415/Q402 (drain copper on the right of the SOIC), L4 island | | 3 (Q402.3, under the SOIC body) + 3 (D505/C536) + 2 (J502 B4/B9) + 1 (C422) |
| USB-A (1.8 A each): R704/R709 → SW_IN → TPS IN; TPS OUT → POSCAP → J70x.1 | +5V via L4 (3 vias each), SW_IN: L6 at the shunt → 2 vias → **L3 strip** → 2 vias → L1 at TPS IN; +5V_USBAx L1 pours | ≥ 2 mm | 3 + 2 + 2 |
| ETH_3V3 / ETH_0V95 | small L1 pours at U802 OUT / L801.2 + 3/4 vias (0.5/0.25) to the L4 islands | | |

Gate drives and local loops (grid router, 0.25–0.4 mm, L1 with L3 where needed): BB_HO1/HO2/LO1/LO2 → R203–R206 →
BB_G1–G4, HB1/HB2 and the SW1/SW2 driver returns to C219/C220; BAR_DGATE/HGATE, PD_DGATE/HGATE, SRC_DGATE/HGATE
(L6/L3), SNK_GATE; 5V_HG via R301 (L3 under the stage, outside the SW keep-out), 5V_HO, 5V_LG (0.4 mm), 5V_BOOT,
SW return U301.14 → Q302; 5V_ORG; 3V3_SW/3V3_BST, 1V15_SW/1V15_BST, ETH_SW; U305 VIN from C336 to the L4 +5V strip.

Kelvin taps (0.15 mm, separate tracks; the power pours are pulled back from the inner pad edges so the taps leave
the pad there; the router keeps them off other same-net copper): R201 → R210/R211 → C221 → U201.37/38 (CSA via-in-pad
0.35/0.15 through C221.1/U201.37); R202 → U201.22/23 (north up the toe column now that C220 is on the bottom; U201.20 joins C210
directly); HB2/SW2 reach C220 (bottom) through 0.35 mm vias next to the inner ends of pins 26/25; R137 → U109.9/10; R243 → U204.8–10; R303 → U301.20/21 (+ U301.16); R312 → U303.8–10;
R704/R709 → U703/U706 IN+/IN−. Card-reader VCC: U901.23 → C913/C914 → J901.4 (0.25 at the pin, then 0.4) and
U901.24 → C916/C915 (0.4).

## 3. Problems / for the lead (wave 2)

1. **The HV rule cannot be met at 0.5 mm-pitch pins.** The `high voltage` rule exempts only pad-to-pad, so any
   track or via entering a pin next to an HV pin of the same part is flagged. Examples are BB_SW1 pin 36 next to
   HB1/CSA, and the gate pins of U104/U105/U202 next to VBAR/VIN_OR/VBB_OUT/VBUS_LSW pins. Proposed clause,
   appended to that rule's condition (tested: the full run then has 0 DRC errors):
   ```
   && !((A.Type == 'Pad' && (A.memberOfFootprint('U10*') || A.memberOfFootprint('U20*') || A.memberOfFootprint('Q20*') || A.memberOfFootprint('J101') || A.memberOfFootprint('J501')))
     || (B.Type == 'Pad' && (B.memberOfFootprint('U10*') || B.memberOfFootprint('U20*') || B.memberOfFootprint('Q20*') || B.memberOfFootprint('J101') || B.memberOfFootprint('J501')))
     || (A.intersectsCourtyard('U201') && B.intersectsCourtyard('U201')))
   ```
   Away from these pins my copper keeps the full 0.3 mm. U201 pins are entered at the toe, or at the inner end for
   HB2/SW2, so no track runs along a pad.
2. **Via counts after the placement fixes:**

   | Spot | Vias now (was) | Status |
   |---|---|---|
   | VIN at R137 (≤ 8 A) | 10 (4) | OK |
   | +5V at R312.2 (8 A) | 9: 7 via-in-pad + 2 on the L6 extension | Close to the 10 target |
   | Q204 EP | 3 thermal vias | Now possible |
   | +5V sink at U206 | 2 | Still limited (the sink cluster rework is not done) |
   | VBAR at Q106 | L6 pour + L4, 5 vias at D102 | |

3. **HS copper makes these impossible (reported, HS copper not moved):**
   - J502 A9 → B4 VBUS link. The DS B-row 0.35 mm vias and their GND vias sit between the rows. A4 → B9 is linked,
     and B4/B9 have vias north of the B row, so A9 is reached through the plug only.
   - U305 VIN (+5V) via near U305/C336. The hub P5/UP corridor and U305's own parts fill every spot that lands on
     the L4 +5V strip, so U305.3 → C336 is drawn and the rest is left to the autorouter. The L4 +5V strip was
     widened to x 176 for it.
   - The R415.1 +5V feed now uses one 0.6/0.3 via-in-pad through R415 pad 1 and C421 pad 1. The south-edge vias are
     gone.
4. **Fixed against the HS routes:**
   - VIN via vs CR_DN, GND via at C203 vs CR_SD_D1, the J502 A4/A9 stubs and the via at (174.5, 79.1), and the R415
     south-edge vias: all handled by the obstacle-aware placement.
   - CR_SD_VCC now hops on L3 where it has to cross the SD1 bus.
   - The L6 VBUS_LAPTOP pour, which the laptop USB2/SBU/CC tracks cut, gets 14 stitching vias so every fragment
     ties to the L4 island.
   - No vias near the U502 straps.
5. **Freerouting:** remove `a_planes.GND_POURS` (`GND_L1`, `GND_L6`) before the DSN export and re-apply after.
   Ideally also remove the `P_*` pours of `b_power.ZONES`, because the DSN turns every zone into a blocking plane.
   `z_stitch.py` must run after the autorouter output.

## 4. Left for the autorouter / other owners

Small rail drops and decoupling connections on +3V3 (≈ 199 pads), +1V15 hub caps ↔ VCORE pins, +5V branches (U901,
C901/C902, C241, F1101, R1101, C412/C413/PMG1, U305 caps), ETH_3V3/ETH_0V95 to the RTL pins and decaps, VIN/VBB_OUT
sense taps (U201.3, C215, R234, R207, R209, R220, R235, D205, U202.2, R304, D301), VBUS_LAPTOP to D205/R625/U401,
VBUS_DS to U401, VBUS_PDIN to U101/R133/U104, VBAR to U105/R127/D103, SNK_MID to C238/R248/U205, C213/C115/C415/C422,
the +5V_USBAx clamps (D702/D704 pin 5), CR_USD_VCC long run to J902.4, CR_3V3/CR_1V2 (B.Cu, local), PMG1_VDDD (BGA),
U305 VIN (+5V), J502 A9, and GND pads/pour islands that still need a via (≈ 100 items).
