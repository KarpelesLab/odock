# odeck-10 routing notes: g_power (power region, phase g)

Script: `hardware/odeck-10/routing/g_power.py`. It has `NETS = []` and `GROUPED = True`, so everything it draws goes
into the group `route:g_power`, and only that group is replaced when the script runs again.
Region: (100,50)–(138,108) plus the J101/J102 strip. All copper stays inside x 100.3–138.3, y 50.3–108.3.
Run time: about 6–9 min (pure-Python router).

Check command:
`apply_routing.py <scratch>/odeck-10 --only a_planes,b_power,c_hs_usbc,d_hs_hub,e_hs_eth_sd,f_fanout,g_power,z_stitch --drc`
gives **0 DRC errors**. The only items left are unconnected items. Before routing, I counted the connectivity of
every net on the a–f board. After routing, **no net has more clusters than before**: no pour was cut off and no
connection was broken.

## Method

The script contains a small maze router.
- **Grid and layers.** It works on a 0.05 mm grid over the region, on L1, L3 (In2.Cu) and L6. Through vias are
  0.45/0.25.
- **Obstacles.** Obstacles are rasterised from the real copper, inflated by half the track width plus clearance:
  - pads on all layers, tracks, vias, rule areas (including the switch-node L3 keep-outs) and holes;
  - pours on the routing layers, except the general `GND_L1`/`GND_L6`;
  - clearance is 0.15 mm, and 0.3 mm across the HV boundary. The pads of U10x/U20x/Q20x/J101/J501 are exempt from
    the 0.3 mm, as in the `.kicad_dru` rule.
- **Same-net copper.** Each grid cell stores the net that blocks it, so copper of the net being routed is free.
- **Connections.** Each connection is a multi-source A* search from one copper cluster of a net to the clusters
  already joined. Plane nets can also end on a via inside their inner-layer fill.
- **Pours split into islands.** A pour whose fill is split is handled per fill island, so two islands of the same
  zone are not counted as connected.
- **Path shape.** Paths use 45° directions only. 90° corners are chamfered. There are no acute angles (checked).
- **Other-net power pours.** A track may cut a notch into another net's power pour at a high cost. The notch is at
  most 0.7 mm deep, and only where the pour is at least 1.4 mm wide. Vias are never placed in other-net pours.
  Switch-node pours and hot-loop GND pours are never crossed.
- **Reserved pin escapes.** Every fine-pitch IC pin (pitch < 0.7 mm) gets a reserved straight escape for its own
  net. This applies to local and interblock pins alike, so later routes cannot box a pin in.
- **Last resort: 0.35/0.15 vias.** The router falls back to a 0.35/0.15 via, which may sit inside a pad (filled
  and capped; the U401 BGA fan-out already needs that process), but never in D101/D102. 9 such vias are used.
- **Routing order.** Nets in `PRIORITY` are routed first. That order came from 6 runs with `G_ITER=6`, where the nets
  that failed were moved to the front each time. All other nets follow by pad count. A second pass with fresh
  connectivity retries what is still open, using larger windows and the small via.
- **Widths.**
  - 0.15 mm by default.
  - 0.2 mm: +3V3, PD_LDO_3V3, and the HV-net sense/bias fragments.
  - 0.25 mm: VIN, VBUS_LSW and VBUS_LAPTOP ties, BB_VCC, BB_BIAS.
  - The router drops to 0.15 mm where the wider track does not fit.
- **Totals.** About 913 segments, about 1030 mm of track, 139 vias.

## Results (full preview run)

| | before (a–f) | after g_power |
|---|---|---|
| Local nets with unrouted connections | 99 nets / 204 edges | 52 nets / 56 edges |
| Supply pads in the region not tied (GND / VIN / VBUS_LSW / VBUS_LAPTOP / +5V) | 9 / 3 / 2 / 2 / 1 | 5 / 0 / 2 / 1 / 0 |
| +3V3 pads in the region (no +3V3 copper in the region) | 28 isolated | 24 in one local tree, 4 isolated |
| Board-wide unconnected (cluster count − 1) | 928 | 745 |

The +3V3 feed into the tree is left to Freerouting: it only needs one connection into the region. Interblock nets
(I2C, VBB_*, LAPTOP_*, PG_5V, EXT_PWR_PRESENT, TEMP_ALERT_N, NTC_ADC0, PDIN_INT_N/PRESENT) were not routed. Their
fine-pitch pins keep a reserved escape.

## Not done, and why (needs changes outside this script)

1. **BB_SW1 is not routed on purpose.** The fill of b_power's `P_BB_SW1` is split at x 107.1–108.1, y 96.9–98.35:
   the clearance around the Q201 gate pad cuts the pour. This leaves Q201's source row (with U201.36/C219) separate
   from Q202's drain and R201.1. A 0.15 mm track would hide a broken switch node, so **b_power must bridge the
   pour**, for example by extending `P_BB_SW1` below the gate pad to y ≈ 99, or by joining the two halves on L1/L6.
2. **LM74800 pins (U104, U105, U202, bottom, 0.5 mm pitch).** These pins are boxed in by b_power gate-drive tracks,
   f_fanout GND dog-bone vias right at the pin ends, and the HV pours. Many of the pins are HV, which needs 0.3 mm
   to those tracks.
   - **U105:** pins 2/3 (VBAR), 5 (BAR_OV), 9 (VIN_OR) and 11 (BAR_CAP).
     - The `BAR_DGATE` track runs at x 106.19, only 0.39 mm from the pin-2/3 pad ends. Moving it ≥ 0.25 mm further
       left (x ≤ 105.95) would let VBAR in.
     - The GND via at (110.75, 71.1) blocks pin 9.
   - **U104:** pins 2/3 (VBUS_PDIN), 5 (PD_OV), 7 (GND), 9 (VIN_OR) and 11 (PD_CAP).
   - **U202:** pins 2 (VBB_OUT), 3 (VBUS_LAPTOP), 4 (SRC_OVT), 5 (SRC_OV), 7 (GND), 9 (VBUS_LSW) and 11 (SRC_CAP).
   - **Related passives:** R124 (BAR_HGATE), R125, R127, C118, R238, C230, R239.
3. **PD strip (U101/U102 and their 0402 arrays, x 132–138, y 50–66).** Passives are stacked top/bottom at the same
   x/y: for example, R110.1 on top sits over R113 on the bottom. The 0402 rows have about 0.3 mm gaps, so there is
   no legal via spot, not even a via in the pad. Affected nets:
   - PD_GPIO3/4/6/7/11, PD_ADCIN1/2, PD_LDO_3V3 (U102.1, R102.1), PD_LDO_1V5 (C108);
   - PDIN_CC1/CC2, PDIN_C_CC1/C_CC2 (U101.7, J101.B5), PDIN_EPR_EN, PDIN_FLT_N, PDIN_PRES_L, PDIN_VBUS_LV (U101.19);
   - PD_I2CC_SCL/SDA/IRQ_N, PD_OV/PD_OV_TOP (R121), PD_PP_EN_HV (Q101.1), PD_PP_EN_INV, PD_MON_UV (U107.3);
   - +3V3 C106/R106.
   This area needs placement relief: unstack the top/bottom 0402s or spread the rows to ≥ 0.5 mm. f_fanout fails
   there for the same reason.
4. **Sink path U206/U204 (bottom).**
   - U206: pins 9 (SNK_ILM), 10 (SNK_ITIMER) and 8 (GND).
   - U204: pins 6 (+3V3) and 7 (GND).
   - Also R247 (SNK_UV), R244 (VBUS_LSW) and C236 (GND).
   They are hemmed in by the VBUS_LSW/SNK_MID pours and the Kelvin taps.
5. **U201 analog side:**
   - R214 (BB_CFG), R212 (BB_RT), R222 (BB_FB), R226 (BB_FBM);
   - Q206.3/R229.2 (BB_VS1D/VS2D), on the bottom under U201;
   - U1201.8 (+3V3).
   These are boxed in by the BB_VCC/PSO copper and by the vias already there. Freerouting (push-and-shove) may still
   finish some of them.

The connections that remain are shown as ratsnest. The autorouter step can try them, but items 1–3 most likely need
the changes listed above.

## Debug

- `G_ONLY=net,net` routes only those nets.
- `G_ITER=n` re-runs with the failed nets moved first and prints the best `PRIORITY`.
- `G_DEBUG=dir` dumps PGM maps of each failed search: source, goal, free cells, and cells where a via is allowed.
