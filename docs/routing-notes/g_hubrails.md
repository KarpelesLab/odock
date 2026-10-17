# Routing notes: hubrails region (phase g)

Scripts:
- `hardware/odock-10/routing/g_hubrails.py`: `NETS = []`, `GROUPED = True`. Everything it draws goes into the group
  `route:g_hubrails`, and only that group is replaced on a re-run.
- `hardware/odock-10/routing/_g_hubrails_lib.py`: a raster maze router used only by this script. The leading `_` keeps
  `apply_routing.py` from running it.

Region: (138, 80)–(180, 108). Copper stays inside the region plus 0.5 mm. Run time is about 13 min, almost all of it in
the maze router.

**Check (full pipeline):**
`apply_routing.py <scratch>/odock-10 --only a_planes,b_power,c_hs_usbc,d_hs_hub,e_hs_eth_sd,f_fanout,g_hubrails,z_stitch --drc`
- **0 DRC errors** of any kind (clearance, short, width, hole, edge). The report lists only unconnected items.
- Pours and planes stay whole. See "Pours and planes" below.

## Results

| | Total | Routed | Open |
|---|---|---|---|
| Local-net connections (`partition.json` → local → hubrails, 46 nets) | 76 | 65 | 11 |
| Supply-pad ties in the region (+3V3 34, +5V 7, GND 11, VIN 2) | 54 | 44 | 10 |
| **All** | **130** | **109** | **21** |

Numbers come from the script's own count. They match KiCad connectivity on the filled final board (see the last
section).

Track widths:
- 0.15 mm for signals.
- 0.2 mm for +3V3, +1V15, VIN and 5V_BUCK/5V_OR sense legs; 0.25 mm for GND and +5V. The script steps down to
  0.15 mm only where the wider track does not fit.
- 0.3 mm for 5V_SW / 5V_SNB (snubber) and 5V_VCC; 0.25 mm for 5V_VINC.

Vias are 0.45/0.25. The script uses 0.35/0.15 only where nothing else fits (pin pockets at U304, U305 and U301).
- Layers: L1, L3 and L6. Corners are 45°, with no turns sharper than 90°.
- L3 is never used under the switch-node keep-outs (`KO_*_SW` rule areas).
- The hub UP/P5 corridor (x 167.5–174, y < 90.8) gets no vias. The P1/P2/P3/P4/P6 channels are left alone, because
  every HS track keeps 0.3 mm to our tracks.

## How it works

1. **Clusters.** The script fills all zones except GND_L1/GND_L6, as f_fanout does (those pours are dropped for the
   autorouter). KiCad connectivity then gives the copper clusters of each net.
2. **Units.** Each unit is one of:
   - a local net, all its clusters;
   - the SPI-flash (U602, DNP) legs of a HUB_SPI net, routed after every strap;
   - one stray cluster of a supply net.

   A supply stray is routed either to the main cluster, through a via into its inner plane (L2/L5 GND, the L4
   islands), or to an already-tied stray.
3. **Router.** It works on a 0.025 mm grid with conservative rasters, so every clearance holds within about 0.02 mm.
   Clearances:
   - 0.15 mm to other copper;
   - 0.3 mm to HV copper (VIN);
   - 0.3 mm between our tracks and HS/USB tracks (the "hs pair spacing" rule);
   - 0.2 mm to holes;
   - 0.3 mm to b_power pours, so a pour never pulls back.

   Rule areas are respected: no-track areas on their layers, and no-via areas. Soft costs keep copper out from under
   the hub body (the pad-ring heel side), so the strap pins keep their escapes.
4. **Rip-up and reroute.** When a connection fails, the script soft-routes it, treating our own copper as passable at
   a cost, then rips up the units in the way. This is a transaction: it is kept only if every ripped unit routes again.
5. **Pours.** Another net may nibble a b_power pour only within 0.9 mm of a pad that sits in that pour's cut-outs.
   This lets a boxed-in pin reach a via. A via inside a pour only costs extra.
   - Switch-node, hot-loop GND and HV pours are strict.
   - After routing, the pours are refilled. A pour that lost a piece or more than 8 % of its area is hardened, and the
     units that went into it are re-routed. This happened once, to P_5V_BUCK_L6.
6. **Inner planes.** A route whose vias would cut an L4 island of another net in two is undone. It is retried with
   those via spots banned. The script checks this on a coarse raster.
   - The check runs over the whole zone, not just the region grid. An earlier version split L4_P5V: the strip that
     feeds U304/U305 VIN and R415 was cut off at x ≈ 164. The guard prevents that now.
   - After routing, every pour and plane touching the region has the same number of pieces as before.
   - Area lost to our antipads and nibbles:
     - L4_P1V15: 220 → 192 mm²;
     - L4_P5V: −28 mm² (of 2977);
     - L4_5V_BUCK: 121 → 118 mm²;
     - P_P5V_R312_L6: 16.2 → 15.0 mm².
7. **Escapes.** Every pad of a signal net that leaves the region (29 pads) is checked for an escape path to a ring
   3 mm away. If our copper boxed one in, the script reserves a corridor for it, but only if that costs no local
   connection.

## Not routed, and why (21)

Most open items are pins that other scripts' copper boxed in. These fail even when the net is routed alone on the
a–f board.

| Open connection | Blocked by | Fix (owner) |
|---|---|---|
| +1V15 **U601.85** (VCORE, between P5 TXN and DSC RXP) | The only toe-via spot is taken by f_fanout's GND dog-bone C625.2 → (172.17, 93.08) on B.Cu | f_fanout: tie C625.2 elsewhere, leaving (172.2, 91.3) free for a 0.35 via |
| **HUB_CFG2** (pin 22) → R606, **HUB_CFG3** (pin 23) → R607 | Toe side: the P2 RX pair, with its 0.3 mm rule, leaves no via room. Heel side: f_fanout's under-body vias +1V15 (166.08, 101.62) (C628.1) and GND (165.94, 102.40) (pin 24) | f_fanout: move those two vias ≥ 0.6 mm further inward (x ≥ 166.7), or put pin 24's GND via in the EP |
| U304 (TPS62933F): **3V3_EN** (pin 2) → R313/R314, **+5V U304.3** and **+5V C328.1** | North: b_power's 3V3_BST track at y 86.58 above pins 7/8, plus KO_3V3_SW (no vias). South: d_hs_hub's XO loop at y 89.48, which also cuts C328 off U304.3. Between rows: C640 (bottom) leaves one 0.35-via spot, taken by FB/SS | b_power: run 3V3_BST north of y 86.2 so pins 7/8 can exit north. d_hs_hub: take XO around the U304 input cap |
| U305 (TPS62933P): **1V15_EN** (pin 2) → R317/R318, **1V15_FB** (pin 8) → R320/R321, **+3V3 R317.1 / R319.2** (pull-ups), **+5V C334.1 / C335.1**, **GND C335.2** | b_power's 1V15_BST route runs between the pin rows (via at 177.57, 88.65) and loops round L303 on B.Cu (x 175.27 / y 83.95 / x 177.67), fencing in R317–R321 and C335. C335.2 also sits inside KO_1V15_SW (no vias). f_fanout's GND via (175.34, 88.45) is between the rows | b_power: shorter BST, e.g. a via just outside KO_1V15_SW north-west of pin 6, without the loop |
| U301 (LM5148): **5V_EN** (pin 19) → R304/R305 | Pins 17–19 sit in a pocket closed by b_power's 5V_BUCK Kelvin from pin 16 (vertical at x 157.545) and the 5V_ISNS via (157.0, 91.14). Only one 0.35 via fits; it goes to pin 18 (VDDA / PFM-SYNC strap) | b_power: route the pin-16 VOUT tap on L3, or join it at pin 21, so pins 17–19 can exit east |
| **+3V3 U303.6** (INA226 VS) | The pin sits in the +5V R312 pour's cut-out on L6. A tie would have to cross the hard part of the pour | Allow one via in the P_P5V_R312_L6 pour next to pin 6 (b_power), or reroute the sense lines |
| **HUB_SPI_D1** (U601.71 → R611 strap, and U602.2), **HUB_SPI_CE_N U602.1**, **HUB_SPI_CLK U602.6** | Right-side strap fan-out: 12 straps at 1.25 mm pitch against 0.4 mm pins, plus the top-cap GND vias at x ≈ 177.6. The flash legs must leave the no-via corridor on B.Cu. Even routed alone, 3 SPI connections fail | U602 is DNP (no SPI boot), so the flash legs are low priority. R611 (SPI_D1 strap) needs room: move C617/C633 0.5 mm east, or swap the strap order |
| **+3V3 U601.67** | Same right-side pin field; no via spot left after the straps | As above |
| **GND C638.2** (crystal load cap) | d_hs_hub's XO B.Cu track at y 91.35 fences it from every legal GND via spot | d_hs_hub: GND via beside C638.2, inside the XO loop, or reroute XO |

## Escapes for the Freerouting nets

- 25 of the 29 escape pads still have a path out. One of them, R311.2 (PG_5V), uses a reserved corridor.
- **Boxed in by this script (4):**
  - U1203.1/2/3 (I2C_SYS_SDA/SCL, TEMP_ALERT_N at the TMP1075 "HUB"). Reserving their corridors up front (option
    `PRE_RESERVE`) frees them but costs 8 local +3V3 connections around U1203, so it is off.
  - U301.17 (PG_5V): the U301 pin-17–19 pocket above has a single via spot, and VDDA has it.
- Both need the b_power or U1203 changes above. Freerouting cannot reach these pins as they are.

## Notes for the lead

- **Re-run safety.** `b_power` has GND in `NETS`. On a board that already carries our GND ties, its `clear()` deletes
  them while they are still in `route:g_hubrails`. A fresh pipeline (clean board, `route_all.sh`) is unaffected.
- **L4_P1V15 under the hub loses about 13 % of its area** (220 → 192 mm²) to the antipads of our +3V3/strap vias. It
  stays in one piece and still feeds all VCORE pins. Confirm the copper is enough for the 1.31 A, or move some +3V3
  drops to via-in-pad.
- **P_P5V_R312_L6** (the 8 A +5V pour at R312/U303) loses 1.2 mm² (7 %) to vias and nibbles next to the U303 pins. It
  stays in one piece.
- **Impedance.** No controlled-impedance nets are routed here. The XI/XO, SS and USB2 nets belong to d_hs_hub.
- **Debugging.** `LOCAL_ONLY = [...]` in the script routes only the listed nets. `G_DEBUG=<dir>` dumps the blocked
  map of every failed search as PGM files.

## Final check

Full pipeline (a–f, g_hubrails, z_stitch) on a scratch copy, filled board checked with KiCad connectivity
(GND_L1/GND_L6 filled, as DRC sees it):
- DRC: **0 errors**. The report lists only unconnected items (capped at 499 board-wide).
- Local nets of this region: **11 open connections**:
  - HUB_CFG2, HUB_CFG3;
  - HUB_SPI_D1 ×2, HUB_SPI_CE_N, HUB_SPI_CLK;
  - +1V15 U601.85;
  - 1V15_EN, 1V15_FB;
  - 3V3_EN;
  - 5V_EN.
- Supply pads in the region not tied: **10**:
  - +3V3: U601.67, R317.1, R319.2, U303.6;
  - +5V: U304.3, C328.1, C334.1, C335.1;
  - GND: C335.2, C638.2.

  This matches the script's own count.
- Pre-existing, not ours: the +3V3 network is in two parts. One is the L4_P3V3 usbc/hub band (L302 side); the other
  is the right-block plane and everything tied to it. The link between them belongs to Freerouting or the power owner.
- Every pour and L4 island in the region has the same number of pieces as before this script.
