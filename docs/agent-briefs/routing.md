# Routing brief (common to all routing agents) — odock-10

Board: hardware/odock-10/odock-10.kicad_pcb (KiCad 10), 130×89 mm, placed and DRC-clean (only unrouted items).
Stack-up JLC061611-1080A (1 oz all layers): L1 F.Cu sig · 0.069 mm 1080 · L2 In1.Cu GND · 0.40 core · L3 In2.Cu sig ·
0.49 prepreg · L4 In3.Cu power · 0.40 core · L5 In4.Cu GND · 0.069 · L6 B.Cu sig. Parts on both sides.
Read: docs/floorplan.md, docs/layout-notes/*.md (ROUTING INTENT per block), docs/routing-notes/*.md, docs/odock-10.md,
docs/design/*.md for your nets, tools/apply_routing.py (Router API: track, via, pair, pair_via, zone, pad, pad_of_net;
GROUPED scripts), hardware/odock-10/odock-10.kicad_dru and the net classes in hardware/odock-10/odock-10.kicad_pro.

Impedance (estimates; confirm in JLC's calculator before fab):
- L1/L6 microstrip over 0.069 mm: 90 Ω diff w 0.10 / gap 0.18; 85 Ω diff w 0.10 / gap 0.12; 100 Ω diff (Ethernet MDI)
  w 0.09 / gap 0.20; 50 Ω single-ended w 0.12.
- L3 stripline (0.40 to L2 GND, 0.49 to L4): 90 Ω w 0.16 / gap 0.20; 85 Ω w 0.18 / gap 0.18; 50 Ω SE w 0.20. Only use L3
  for high-speed where L4 directly underneath is solid; prefer L1/L6.
- Every layer change of a 10 Gbps / DP pair: r.pair_via(..., gnd_vias=True). Intra-pair skew ≤ 0.15 mm, no stubs, 45°.

Scripts: hardware/odock-10/routing/<name>.py with NETS (nets whose tracks are deleted before route()) or
GROUPED = True + NETS = [] (only the script's own group "route:<name>" is replaced on re-run — use this when sharing
nets), optional ZONES, and route(board, r). Notes in docs/routing-notes/<name>.md. Never modify footprints, placement or
schematics; report needed changes instead.

WORKFLOW (never write the real board — others may work in parallel):
  S=/private/tmp/claude-501/-Users-magicaltux-projects-odeck/95ecabdd-1f69-468e-8be9-3295b795520e/scratchpad/route_<name>
  rm -rf $S && mkdir -p $S && cp -r /Users/magicaltux/projects/odeck/hardware/odock-10 /Users/magicaltux/projects/odeck/hardware/lib $S/
  P=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
  $P /Users/magicaltux/projects/odeck/tools/apply_routing.py $S/odock-10 --only <scripts> --drc
  → zero clearance/short/hole/width errors (unconnected items of other nets are expected).
  Connectivity per net: board.GetConnectivity().GetConnectedItems(pad) returns a pad's whole copper cluster after
  ZONE_FILLER fill + BuildConnectivity (see tools/net_partition.py); kicad-cli DRC caps unconnected items at 499.
  Visual check: kicad-cli pcb export svg / pcb render, then view the PNG with the Read tool.
Parts lookup: python3 tools/jlc_search.py <keyword>. Do not commit.
