"""odock-10 GND stitching vias + board-edge via fence, and GND on the mounting-hole pads. Runs LAST (after the
high-speed scripts and the autorouter output), so every via is checked against the copper that is really there.

- A via is placed only where it clears every pad, track and via of another net on all layers by the DRC clearance
  (0.2 mm, 0.3 mm to HV-class copper), every rule-area keep-out that forbids vias, all courtyards, the HS corridors
  named in docs/routing-notes/hs_usbc.md / hs_hub.md, the power stages and the power pours of b_power.py.
- Idempotent: NETS is empty (GND belongs to other scripts too); the vias of the previous run are recognised by
  their tag size (0.46/0.25 mm GND vias, a size no other script uses) and deleted before placing new ones.
"""
import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew  # noqa: E402
import _pwrlib as L  # noqa: E402

NETS = []
ZONES = []
PITCH = 4.0          # stitching grid
FENCE_PITCH = 2.5    # edge fence
FENCE_INSET = 1.4
VIA = (0.46, 0.25)    # the 0.46 mm diameter tags these vias (see _clear_previous)

# High-speed corridors / channels and dense areas where the signal owners place their own GND return vias.
EXCLUDE = [
    L.rect(138.0, 50.0, 180.5, 80.5),      # usbc block (BGA fan-out, lanes, CC channels, U504 EP)
    L.rect(159.75, 63.0, 163.4, 79.0),     # L3 hub SS corridor (no through vias)
    L.rect(166.6, 76.9, 174.4, 80.4),      # L1/L3 transitions of the hub links
    L.rect(145.8, 79.3, 171.0, 80.6),      # L3 laptop USB2
    L.rect(159.0, 80.0, 164.8, 112.5),     # hub SS escape + P1/P2 channel
    L.rect(166.8, 78.0, 174.5, 92.0),      # UP/P5 corridor
    L.rect(165.5, 103.5, 181.0, 108.6),    # P3 / P4 run, hub pocket
    L.rect(136.8, 107.8, 165.0, 112.6),    # CR SS + hub->front hand-off band
    L.rect(149.0, 104.0, 154.0, 124.5),    # USB-A port 1 channel
    L.rect(168.0, 104.0, 173.0, 124.5),    # USB-A port 2 channel
    L.rect(107.0, 103.5, 138.5, 129.5),    # card reader: SD bus, microSD escape, CR USB2
    L.rect(126.5, 128.6, 182.0, 133.4),    # microSD band
    L.rect(178.5, 119.5, 193.0, 133.4),    # microSD rise + J902 row
    L.rect(177.5, 58.5, 194.0, 109.0),     # Ethernet USB corridor + pairs along x = 180
    L.rect(198.5, 63.5, 220.0, 73.0),      # MDI bundle
    L.rect(193.5, 69.0, 202.5, 92.0),      # LCD FPC tail / J1103
    L.rect(100.0, 62.0, 116.5, 108.5),     # LM51770 column + input FETs (own via arrays in b_power)
    L.rect(138.0, 78.0, 158.5, 108.5),     # LM5148 stage (own via arrays in b_power)
]


def _clear_previous(board):
    """Delete this script's vias from a previous run: GND vias with the tag size VIA (0.46/0.25, used by no one else)."""
    for t in list(board.GetTracks()):
        if t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND" and \
                abs(L.MM(t.GetWidth(pcbnew.F_Cu)) - VIA[0]) < 1e-4 and abs(L.MM(t.GetDrillValue()) - VIA[1]) < 1e-4:
            board.Delete(t)     # Delete, not Remove: Remove leaves the SWIG proxies in a broken state


def route(board, r):
    _clear_previous(board)
    # mounting holes H1-H4: plated pad + ring vias -> GND
    gnd = board.FindNet("GND")
    for ref in ("H1", "H2", "H3", "H4"):
        fp = r.fps.get(ref)
        if fp:
            for p in fp.Pads():
                p.SetNet(gnd)

    import a_planes
    import b_power
    excl = list(EXCLUDE) + [poly for (_n, _net, _l, poly, _p) in b_power.POURS] + \
        [poly for _n, poly in a_planes.SW_KO] + [poly for _n, poly in a_planes.L3_KO]
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref in ("U1101", "J901", "J701", "J702", "J801") or ref.startswith("H"):
            continue
        cy = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd)
        if cy.OutlineCount():
            bb = cy.BBox()
            excl.append(L.rect(L.MM(bb.GetLeft()), L.MM(bb.GetTop()), L.MM(bb.GetRight()), L.MM(bb.GetBottom())))
    # every rule area on the board that forbids vias (whoever owns it)
    for z in board.Zones():
        if z.GetIsRuleArea() and z.GetDoNotAllowVias():
            o = z.Outline().Outline(0)
            excl.append([(L.MM(o.CPoint(i).x), L.MM(o.CPoint(i).y)) for i in range(o.PointCount())])

    L.ViaPlacer.ghost_tracks, L.ViaPlacer.ghost_vias = [], []
    placed = []

    class _R:   # records every via the placers drop
        def via(self, net, x, y, size, drill, *a):
            r.via(net, x, y, size, drill)
            placed.append((round(x, 4), round(y, 4)))
    rr = _R()
    vp = L.ViaPlacer(board, keepouts=excl, clearance=0.2)
    n_grid = vp.grid(rr, "GND", L.rect(101.0, 51.0, 229.0, 138.0), PITCH, size=VIA[0], drill=VIA[1])
    # the edge fence may run through the HS areas (it only takes spots that are free), not through the usbc block
    fence = L.ViaPlacer(board, keepouts=[EXCLUDE[0]] + excl[len(EXCLUDE):], clearance=0.2)
    n_f = 0
    e = FENCE_INSET
    for (ax, ay, bx, by) in ((100 + e, 50 + e, 230 - e, 50 + e), (230 - e, 50 + e, 230 - e, 139 - e),
                             (230 - e, 139 - e, 100 + e, 139 - e), (100 + e, 139 - e, 100 + e, 50 + e)):
        n = int(math.hypot(bx - ax, by - ay) / FENCE_PITCH)
        for k in range(n + 1):
            x, y = ax + (bx - ax) * k / n, ay + (by - ay) * k / n
            for d in (0.0, 0.5, -0.5, 1.0, -1.0):
                dx, dy = (d, 0) if ay == by else (0, d)
                if fence.place(rr, "GND", x + dx, y + dy, VIA[0], VIA[1]):
                    n_f += 1
                    break
    print("z_stitch: %d stitching vias, %d fence vias, mounting holes -> GND" % (n_grid, n_f))
