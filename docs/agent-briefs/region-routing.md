# Region routing brief (hybrid plan, phase "g") — odock-10

Read docs/agent-briefs/routing.md first. Already routed (do NOT modify): a_planes (zones), b_power (power paths),
c_hs_usbc / d_hs_hub / e_hs_eth_sd (high-speed), f_fanout (plane-net pads to planes), z_stitch (GND stitching, last).

YOUR JOB: hardware/odock-10/routing/g_<region>.py with NETS = [], GROUPED = True, route(board, r).
Route every connection of the nets LOCAL to your region (all pads inside your region rectangles from
hardware/odock-10/layout/<block>.py REGION) that is still unrouted after a–f (recompute the list with
tools/net_partition.py on a scratch board: `$P tools/net_partition.py <board> hardware/odock-10/layout out.json`, using a
board with a–f applied). Also tie every still-unconnected pad of shared supply nets inside your region (+3V3, +5V,
GND, +1V15, +1V1, VIN, ETH_3V3, ETH_0V95, PMG1_VDDD, …) to the nearest copper of the same net. Signal nets that span
regions ("interblock") are left to Freerouting: don't route them, but don't box in their pads — keep an escape (a short
stub + via toward the region exit is welcome).
Rules: copper inside your region + 0.5 mm; signal 0.15 mm (0.2+ for power drops), vias 0.45/0.25 (0.35/0.15 only where
unavoidable), 45° corners, no tracks under switch nodes on L3/L4 (keep-out areas), respect HS corridors and 0.3 mm HV
spacing. Preview: apply_routing.py <scratch>/odock-10 --only a_planes,b_power,c_hs_usbc,d_hs_hub,e_hs_eth_sd,f_fanout,g_<region>,z_stitch --drc
→ zero errors; report remaining unconnected connections for your local nets (target 0) and supply pads in your region.
Write docs/routing-notes/g_<region>.md. If you build a grid router or other helper, put it in the repo
(hardware/odock-10/routing/_<name>_lib.py or tools/) so the routes can be regenerated later. Do not commit.
