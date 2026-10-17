"""odeck-10 phase g, region "right" (Ethernet, RP2350 + flash, LCD / UI, sensors U1206-U1208).

Routes every still-unrouted connection of the nets LOCAL to the right region (build/partition.json -> local.right)
and ties the still-unconnected pads of the shared supply nets inside the region (+3V3, +5V, GND) to their planes /
copper.  Interblock signal nets are left to Freerouting.

Hand-placed parts of the routing (Pico-2 regulator geometry, QSPI, crystal) are expressed as per-net parameters
(layers, widths, ordering); the copper itself is drawn by a small gridded router in this file:
- 0.05 mm grid per connection (window around the terminals), layers F.Cu / In2.Cu (L3) / B.Cu, through vias
  0.45/0.25; octilinear tracks, 90-degree corners forbidden (45-degree turns only), no corner cutting.
- Obstacles: every pad, track, via of another net (0.15 mm + 0.012 margin; 0.30 to USB_90 / HS_85 tracks per the
  "hs pair spacing" rule), NPTH holes (0.2), via hole-to-hole 0.2, rule areas (keep-outs) per layer, other-net
  copper pours on the signal layers, the board edge (0.3) and the region rectangles + 0.5 mm.
- Fine-pitch pins (QFN 0.35 / 0.4 mm) get a straight escape stub along the pin axis before the grid takes over.
- Targets: any same-net copper already connected to the rest of the net (pads, tracks, vias, same-net pours on
  the signal layers) or, for plane nets, a legal via spot inside the filled plane (GND L2/L5/L4, +3V3 / +5V /
  ETH_3V3 / ETH_0V95 L4 islands).

GROUPED: everything goes into group "route:g_right"; NETS = [] (nets are shared with b_power / f_fanout / ...).
"""
import os
import sys
import math
import heapq
import json
from collections import defaultdict

import pcbnew

NETS = []
GROUPED = True

mm, MM = pcbnew.FromMM, pcbnew.ToMM
HERE = os.path.dirname(os.path.abspath(__file__))
DEBUG = os.environ.get("G_RIGHT_DEBUG")

REGION = [
    (180.0, 50.0, 230.0, 123.75),
    (198.0, 50.0, 230.0, 139.0),
    (201.5, 48.5, 222.5, 73.0),
    (198.0, 130.0, 223.0, 141.5),
]
REG_MARGIN = 0.5
BOARD = (100.0, 50.0, 230.0, 139.0)
EDGE_CLR = 0.3

STEP = 0.05
CLR = 0.15
HS_CLR = 0.30
HOLE_CLR = 0.20
MARGIN = 0.006
VIA = (0.45, 0.25)
MIN_RUN = 0                          # (run-length states disabled: corners are widened afterwards)
CHAMFER = 0.25                       # target length of the 45-degree corner segments (post-processing)

CU6 = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu]
CU6_NAME = ["F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"]
RL = [0, 2, 5]                       # routing layers (indices into CU6)
RL_NAME = [CU6_NAME[i] for i in RL]
ALL6 = 0b111111
HS_CLASSES = ("USB_90", "HS_85")
# power nets allowed to put a (filled, as elsewhere on this board) via inside a same-net decoupling-cap pad
VIP_NETS = {"ETH_0V95", "ETH_3V3", "+1V1", "+3V3", "GND", "ETH_AVDD33_PLL", "ETH_0V95_UPS", "VREG_AVDD", "ADC_AVDD"}

# plane nets: net -> inner layers (CU6 indices) whose filled zones of that net count as the plane
PLANES = {"GND": (1, 3, 4), "+3V3": (3,), "+5V": (3,), "ETH_3V3": (3,), "ETH_0V95": (3,)}

DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
SQ2 = math.sqrt(2.0)


def short(n):
    return str(n).split("/")[-1]


def log(*a):
    print("g_right:", *a)


# ----------------------------------------------------------------------------------------------- geometry
def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / L2
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def in_poly(x, y, pts):
    inside = False
    n = len(pts)
    j = n - 1
    for i in range(n):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if (yi > y) != (yj > y) and x < xi + (y - yi) * (xj - xi) / (yj - yi):
            inside = not inside
        j = i
    return inside


def poly_sdist(x, y, pts):
    d = min(seg_dist(x, y, pts[i - 1][0], pts[i - 1][1], pts[i][0], pts[i][1]) for i in range(len(pts)))
    return -d if in_poly(x, y, pts) else d


class Obs:
    """Obstacle / copper item. kind: 'rr' rounded rect (cx,cy,c,s,hx,hy,r), 'seg' (ax,ay,bx,by,hw), 'cir' (cx,cy,r),
    'poly' (pts). lmask: bit i = CU6[i]. tb/vb: blocks tracks / vias. clr: clearance my copper keeps to it."""
    __slots__ = ("kind", "net", "lmask", "g", "bb", "tb", "vb", "clr", "hole", "pad", "smd", "ref", "num", "hs",
                 "zone")

    def __init__(self, kind, net, lmask, g, bb, tb=True, vb=True, clr=CLR, hole=None, pad=None, hs=False):
        self.kind, self.net, self.lmask, self.g, self.bb = kind, net, lmask, g, bb
        self.tb, self.vb, self.clr, self.hole, self.pad, self.hs = tb, vb, clr, hole, pad, hs
        self.smd = False
        self.ref = self.num = None
        self.zone = None

    def dist(self, x, y):
        k = self.kind
        g = self.g
        if k == "rr":
            cx, cy, c, s, hx, hy, r = g
            dx, dy = x - cx, y - cy
            lx, ly = abs(dx * c + dy * s), abs(-dx * s + dy * c)
            qx, qy = lx - hx + r, ly - hy + r
            if qx > 0 and qy > 0:
                return math.hypot(qx, qy) - r
            return max(qx, qy) - r
        if k == "seg":
            return seg_dist(x, y, g[0], g[1], g[2], g[3]) - g[4]
        if k == "cir":
            return math.hypot(x - g[0], y - g[1]) - g[2]
        return poly_sdist(x, y, g)


def pad_obs(p, net):
    """Obs for a copper pad (shape of its first copper layer; custom shapes -> bounding box)."""
    lmask = 0
    for i, l in enumerate(CU6):
        if p.IsOnLayer(l):
            lmask |= 1 << i
    if not lmask:
        return None
    L = pcbnew.F_Cu if p.IsOnLayer(pcbnew.F_Cu) else (pcbnew.B_Cu if p.IsOnLayer(pcbnew.B_Cu) else CU6[2])
    shp = p.GetShape(L)
    q = p.GetPosition()
    cx, cy = MM(q.x), MM(q.y)
    sz = p.GetSize(L)
    hx, hy = MM(sz.x) / 2, MM(sz.y) / 2
    a = math.radians(-p.GetOrientationDegrees())     # KiCad: CCW positive with y down -> rotate by -angle
    c, s = math.cos(a), math.sin(a)
    if shp == pcbnew.PAD_SHAPE_CIRCLE:
        r = hx
        hy = hx
    elif shp == pcbnew.PAD_SHAPE_OVAL:
        r = min(hx, hy)
    elif shp == pcbnew.PAD_SHAPE_ROUNDRECT:
        r = MM(p.GetRoundRectCornerRadius(L))
    elif shp == pcbnew.PAD_SHAPE_RECT:
        r = 0.0
    else:
        bb = p.GetBoundingBox()
        x0, y0, x1, y1 = MM(bb.GetLeft()), MM(bb.GetTop()), MM(bb.GetRight()), MM(bb.GetBottom())
        cx, cy, hx, hy, c, s, r = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2, 1.0, 0.0, 0.0
    ext = math.hypot(hx, hy)
    hole = None
    if p.GetDrillSizeX() > 0:
        hole = max(MM(p.GetDrillSizeX()), MM(p.GetDrillSizeY())) / 2
    o = Obs("rr", net, lmask, (cx, cy, c, s, hx, hy, r), (cx - ext, cy - ext, cx + ext, cy + ext), hole=hole, pad=p)
    o.smd = p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD
    o.ref = p.GetParentFootprint().GetReference()
    o.num = p.GetNumber()
    return o


def seg_obs(net, a, b, w, lmask, hs=False):
    hw = w / 2
    return Obs("seg", net, lmask, (a[0], a[1], b[0], b[1], hw),
               (min(a[0], b[0]) - hw, min(a[1], b[1]) - hw, max(a[0], b[0]) + hw, max(a[1], b[1]) + hw),
               clr=HS_CLR if hs else CLR, hs=hs)


def via_obs(net, x, y, size, drill):
    r = size / 2
    return Obs("cir", net, ALL6, (x, y, r), (x - r, y - r, x + r, y + r), hole=drill / 2)


def poly_obs(net, pts, lmask, tb=True, vb=True, clr=0.0):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    if len(pts) >= 12:                       # circular keep-outs (mounting holes): use a circle (fast)
        cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
        rs = [math.hypot(x - cx, y - cy) for x, y in pts]
        if max(rs) - min(rs) < 0.05:
            r = max(rs)
            return Obs("cir", net, lmask, (cx, cy, r), (cx - r, cy - r, cx + r, cy + r), tb=tb, vb=vb, clr=clr)
    return Obs("poly", net, lmask, pts, (min(xs), min(ys), max(xs), max(ys)), tb=tb, vb=vb, clr=clr)


def chain_pts(sps):
    """SHAPE_LINE_CHAIN -> list of (x,y) mm."""
    return [(MM(sps.CPoint(k).x), MM(sps.CPoint(k).y)) for k in range(sps.PointCount())]


# ----------------------------------------------------------------------------------------------- world model
class World:
    BUCKET = 2.0

    def __init__(self, board, r):
        self.board = board
        self.r = r
        self.obs = []
        self.buckets = defaultdict(list)
        self.net_items = defaultdict(list)       # net -> Obs list (same-net copper, incl. pads)
        self.planes = defaultdict(list)          # net -> list of (layer index, [outline pts lists])
        self.pours = defaultdict(list)           # net -> list of (layer index, [outline pts lists]) on RL layers
        self.drawn = 0
        X0, Y0 = 175.0, 45.0
        X1, Y1 = 235.0, 145.0
        self.win = (X0, Y0, X1, Y1)
        hs_nets = set()
        for ni in board.GetNetsByName().values():
            try:
                if ni.GetNetClassName() in HS_CLASSES:
                    hs_nets.add(short(ni.GetNetname()))
            except Exception:
                pass
        self.hs_nets = hs_nets
        fps = r.fps.values() if getattr(r, "fps", None) else board.GetFootprints()
        for fp in fps:
            bb = fp.GetBoundingBox()
            if MM(bb.GetRight()) < X0 or MM(bb.GetLeft()) > X1 or MM(bb.GetBottom()) < Y0 or MM(bb.GetTop()) > Y1:
                continue
            for p in fp.Pads():
                net = short(p.GetNetname())
                o = pad_obs(p, net)
                if o is None:
                    if p.GetDrillSizeX() > 0:      # NPTH: hole only
                        q = p.GetPosition()
                        hr = max(MM(p.GetDrillSizeX()), MM(p.GetDrillSizeY())) / 2
                        h = Obs("cir", "", ALL6, (MM(q.x), MM(q.y), hr),
                                (MM(q.x) - hr, MM(q.y) - hr, MM(q.x) + hr, MM(q.y) + hr), clr=HOLE_CLR, hole=hr)
                        self.add(h)
                    continue
                if not net:
                    net = "~%s.%s" % (o.ref, o.num)    # unconnected pad: unique pseudo-net
                    o.net = net
                self.add(o)
        for t in board.GetTracks():
            self.add_track_item(t)
        for z in board.Zones():
            bb = z.GetBoundingBox()
            if MM(bb.GetRight()) < X0 or MM(bb.GetLeft()) > X1 or MM(bb.GetBottom()) < Y0 or MM(bb.GetTop()) > Y1:
                continue
            if z.GetIsRuleArea():
                tb, vb = z.GetDoNotAllowTracks(), z.GetDoNotAllowVias()
                if not (tb or vb):
                    continue
                lm = 0
                for i, l in enumerate(CU6):
                    if z.IsOnLayer(l):
                        lm |= 1 << i
                ol = z.Outline()
                for k in range(ol.OutlineCount()):
                    self.add(poly_obs(None, chain_pts(ol.Outline(k)), lm, tb=tb, vb=vb, clr=0.02))
                continue
            net = short(z.GetNetname())
            for i, l in enumerate(CU6):
                if not z.IsOnLayer(l):
                    continue
                fpl = z.GetFilledPolysList(l)
                outl = [chain_pts(fpl.Outline(k)) for k in range(fpl.OutlineCount())]
                if i in PLANES.get(net, ()):
                    self.planes[net].append((i, outl, z.GetZoneName()))
                elif i in RL:
                    if net == "GND" and z.GetAssignedPriority() < 10:
                        continue                   # GND pours on L1/L6: tracks of other nets may cross (refill)
                    self.pours[net].append((i, outl, z.GetZoneName()))
                    # other-net pour on a signal layer: obstacle (do not cut it)
                    ol = z.Outline()
                    for k in range(ol.OutlineCount()):
                        o = poly_obs(net, chain_pts(ol.Outline(k)), 1 << i, clr=CLR)
                        o.zone = z.GetZoneName()
                        self.add(o)

    def add_track_item(self, t):
        net = short(t.GetNetname())
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition()
            o = via_obs(net, MM(p.x), MM(p.y), MM(t.GetWidth(pcbnew.F_Cu)), MM(t.GetDrillValue()))
            top, bot = t.TopLayer(), t.BottomLayer()
            if (top, bot) != (pcbnew.F_Cu, pcbnew.B_Cu):
                lm = 0
                on = False
                for i, l in enumerate(CU6):
                    if l == top:
                        on = True
                    if on:
                        lm |= 1 << i
                    if l == bot:
                        on = False
                o.lmask = lm
        else:
            a, b = t.GetStart(), t.GetEnd()
            li = CU6.index(t.GetLayer()) if t.GetLayer() in CU6 else None
            if li is None:
                return
            o = seg_obs(net, (MM(a.x), MM(a.y)), (MM(b.x), MM(b.y)), MM(t.GetWidth()), 1 << li,
                        hs=net in self.hs_nets)
        self.add(o)

    def add(self, o):
        self.obs.append(o)
        B = self.BUCKET
        x0, y0, x1, y1 = o.bb
        for bx in range(int(math.floor(x0 / B)), int(math.floor(x1 / B)) + 1):
            for by in range(int(math.floor(y0 / B)), int(math.floor(y1 / B)) + 1):
                self.buckets[(bx, by)].append(o)
        if o.net:
            self.net_items[o.net].append(o)

    def query(self, x0, y0, x1, y1):
        B = self.BUCKET
        seen = set()
        out = []
        for bx in range(int(math.floor(x0 / B)), int(math.floor(x1 / B)) + 1):
            for by in range(int(math.floor(y0 / B)), int(math.floor(y1 / B)) + 1):
                for o in self.buckets.get((bx, by), ()):
                    if id(o) not in seen:
                        seen.add(id(o))
                        out.append(o)
        return out

    # ---- drawing (Router + world update)
    def draw_track(self, net, pts, li, w):
        pts = [(round(x, 4), round(y, 4)) for x, y in pts]
        clean = [pts[0]]
        for p in pts[1:]:
            if math.hypot(p[0] - clean[-1][0], p[1] - clean[-1][1]) > 1e-4:
                clean.append(p)
        if len(clean) < 2:
            return []
        self.r.track(net, clean, CU6_NAME[li], w)
        new = []
        for a, b in zip(clean, clean[1:]):
            o = seg_obs(net, a, b, w, 1 << li)
            self.add(o)
            new.append(o)
        self.drawn += len(clean) - 1
        return new

    def draw_via(self, net, x, y, size=VIA[0], drill=VIA[1]):
        x, y = round(x, 4), round(y, 4)
        self.r.via(net, x, y, size, drill)
        o = via_obs(net, x, y, size, drill)
        self.add(o)
        return o


# ----------------------------------------------------------------------------------------------- the router
class Grid:
    """Raster of one routing problem: free cells per routing layer for a track of half-width hw, via-legal cells."""

    def __init__(self, world, net, box, hw, vr, vdrill, layers):
        self.w = world
        self.net = net
        self.hw, self.vr = hw, vr
        x0, y0, x1, y1 = box
        s = STEP
        self.x0, self.y0 = x0, y0
        self.nx = nx = int(round((x1 - x0) / s)) + 1
        self.ny = ny = int(round((y1 - y0) / s)) + 1
        n = nx * ny
        self.layers = layers                                # subset of range(3) (indices into RL)
        self.blk = [bytearray(b"\x01") * n for _ in range(3)]
        self.vblk = bytearray(b"\x01") * n
        # --- allowed area: region rects + margin, board edge
        bx0, by0, bx1, by1 = BOARD
        for j in range(ny):
            y = y0 + j * s
            rowt = bytearray(nx)
            rowv = bytearray(nx)
            for (rx0, ry0, rx1, ry1) in REGION:
                for infl, row in ((hw, rowt), (vr, rowv)):
                    lo_y, hi_y = max(ry0 - REG_MARGIN, by0 + EDGE_CLR) + infl, min(ry1 + REG_MARGIN, by1 - EDGE_CLR) - infl
                    if not (lo_y <= y <= hi_y):
                        continue
                    lo_x = max(rx0 - REG_MARGIN, bx0 + EDGE_CLR) + infl
                    hi_x = min(rx1 + REG_MARGIN, bx1 - EDGE_CLR) - infl
                    i0 = max(0, int(math.ceil((lo_x - x0) / s - 1e-9)))
                    i1 = min(nx - 1, int(math.floor((hi_x - x0) / s + 1e-9)))
                    for i in range(i0, i1 + 1):
                        row[i] = 1
            base = j * nx
            for i in range(nx):
                if rowt[i]:
                    for li in layers:
                        self.blk[li][base + i] = 0
                if rowv[i]:
                    self.vblk[base + i] = 0
        # --- obstacles
        rl_bits = [1 << RL[li] for li in range(3)]
        lay_bits = 0
        for li in layers:
            lay_bits |= rl_bits[li]
        hole_r = vdrill / 2
        M = MARGIN
        for o in world.query(x0 - 2, y0 - 2, x1 + 2, y1 + 2):
            same = (o.net == net)
            hole = o.hole
            if same:
                # same-net copper is free; holes still need hole-to-hole spacing; no via inside a same-net SMD pad
                if hole:
                    self._mark(o, None, hole_r + HOLE_CLR + M, use_center_hole=True)
                if o.kind == "rr" and o.smd and not (net in VIP_NETS and o.g[4] * o.g[5] >= 0.06):
                    self._mark(o, None, vr + 0.05)
                continue
            if o.net is None:
                tthr = (hw + o.clr) if (o.tb and (o.lmask & lay_bits)) else None
                vthr = (vr + o.clr) if o.vb else None
                self._mark2(o, tthr, vthr, rl_bits)
                continue
            clr_t = o.clr
            clr_v = CLR if o.kind == "seg" else o.clr
            tthr = hw + clr_t + M if (o.lmask & lay_bits) else None
            vthr = vr + clr_v + M
            self._mark2(o, tthr, vthr, rl_bits)
            if hole:
                self._mark(o, None, hole_r + HOLE_CLR + M, use_center_hole=True)

    def apply_hot(self, rects):
        """Cells in congested escape areas (around fine-pitch pin fields): inner/bottom layers and vias cost more
        there, so that escapes leave on L1 first and do not park lanes/vias in front of neighbouring pins."""
        self.hot = bytearray(self.nx * self.ny)
        for r_ in rects:
            i0, i1, j0, j1 = self._range(r_, 0)
            for j in range(j0, j1 + 1):
                for i in range(i0, i1 + 1):
                    self.hot[j * self.nx + i] = 1

    def apply_keep(self, keep):
        s = STEP
        for (kx0, ky0, kx1, ky1, lis, allowed, vb) in keep:
            if self.net in allowed:
                continue
            for li in lis:
                if li not in self.layers:
                    continue
                infl = self.hw
                i0, i1, j0, j1 = self._range((kx0, ky0, kx1, ky1), infl)
                arr = self.blk[li]
                for j in range(j0, j1 + 1):
                    for i in range(i0, i1 + 1):
                        arr[j * self.nx + i] = 1
            if vb:
                i0, i1, j0, j1 = self._range((kx0, ky0, kx1, ky1), self.vr)
                for j in range(j0, j1 + 1):
                    for i in range(i0, i1 + 1):
                        self.vblk[j * self.nx + i] = 1

    def _range(self, bb, infl):
        s = STEP
        i0 = max(0, int(math.floor((bb[0] - infl - self.x0) / s)))
        i1 = min(self.nx - 1, int(math.ceil((bb[2] + infl - self.x0) / s)))
        j0 = max(0, int(math.floor((bb[1] - infl - self.y0) / s)))
        j1 = min(self.ny - 1, int(math.ceil((bb[3] + infl - self.y0) / s)))
        return i0, i1, j0, j1

    def _mark2(self, o, tthr, vthr, rl_bits):
        infl = max(tthr or 0, vthr or 0)
        i0, i1, j0, j1 = self._range(o.bb, infl)
        if i0 > i1 or j0 > j1:
            return
        tl = [li for li in self.layers if (o.lmask & rl_bits[li])] if tthr is not None else []
        tarrs = [self.blk[li] for li in tl]
        varr = self.vblk if vthr is not None else None
        s, x0, y0, nx = STEP, self.x0, self.y0, self.nx
        dist = o.dist
        tt = tthr if tthr is not None else -1e9
        vt = vthr if vthr is not None else -1e9
        for j in range(j0, j1 + 1):
            y = y0 + j * s
            base = j * nx
            for i in range(i0, i1 + 1):
                d = dist(x0 + i * s, y)
                if d < tt:
                    k = base + i
                    for a in tarrs:
                        a[k] = 1
                if d < vt:
                    varr[base + i] = 1

    def _mark(self, o, layers, thr, use_center_hole=False):
        """Via-block cells within thr of the obstacle's hole centre (use_center_hole) or of its copper."""
        if use_center_hole:
            cx, cy = (o.g[0], o.g[1])
            hr = o.hole
            infl = thr + hr
            bb = (cx, cy, cx, cy)
        else:
            infl = thr
            bb = o.bb
        i0, i1, j0, j1 = self._range(bb, infl)
        s, x0, y0, nx = STEP, self.x0, self.y0, self.nx
        for j in range(j0, j1 + 1):
            y = y0 + j * s
            base = j * nx
            for i in range(i0, i1 + 1):
                x = x0 + i * s
                d = (math.hypot(x - cx, y - cy) - hr) if use_center_hole else o.dist(x, y)
                if d < thr:
                    self.vblk[base + i] = 1

    def cell(self, x, y):
        return int(round((x - self.x0) / STEP)), int(round((y - self.y0) / STEP))

    def xy(self, k):
        return self.x0 + (k % self.nx) * STEP, self.y0 + (k // self.nx) * STEP

    def cells_in(self, o, inset=0.0, li_filter=None):
        """(k, li) cells inside copper item o (distance <= -inset) on routing layers, free."""
        out = []
        i0, i1, j0, j1 = self._range(o.bb, 0)
        for li in self.layers:
            if not (o.lmask & (1 << RL[li])):
                continue
            if li_filter is not None and li not in li_filter:
                continue
            arr = self.blk[li]
            for j in range(j0, j1 + 1):
                y = self.y0 + j * STEP
                for i in range(i0, i1 + 1):
                    k = j * self.nx + i
                    if arr[k]:
                        continue
                    if o.dist(self.x0 + i * STEP, y) <= -inset:
                        out.append((k, li))
        return out


def raster_poly_mask(g, polys, erode):
    """bytearray mask of cells inside the union of polygons (even-odd per outline), eroded by `erode` mm."""
    nx, ny = g.nx, g.ny
    m = bytearray(nx * ny)
    for pts in polys:
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        if max(xs) < g.x0 or min(xs) > g.x0 + nx * STEP or max(ys) < g.y0 or min(ys) > g.y0 + ny * STEP:
            continue
        n = len(pts)
        for j in range(ny):
            y = g.y0 + j * STEP
            xi = []
            for a in range(n):
                (xa, ya), (xb, yb) = pts[a - 1], pts[a]
                if (ya > y) != (yb > y):
                    xi.append(xa + (y - ya) * (xb - xa) / (yb - ya))
            xi.sort()
            for a in range(0, len(xi) - 1, 2):
                i0 = max(0, int(math.ceil((xi[a] - g.x0) / STEP)))
                i1 = min(nx - 1, int(math.floor((xi[a + 1] - g.x0) / STEP)))
                base = j * nx
                for i in range(i0, i1 + 1):
                    m[base + i] ^= 1
    if erode > 0:
        e = int(math.ceil(erode / STEP))
        out = bytearray(nx * ny)
        ed = int(round(e / SQ2))
        offs = [(e, 0), (-e, 0), (0, e), (0, -e), (ed, ed), (ed, -ed), (-ed, ed), (-ed, -ed)]
        for j in range(e, ny - e):
            base = j * nx
            for i in range(e, nx - e):
                k = base + i
                if not m[k]:
                    continue
                ok = True
                for di, dj in offs:
                    if not m[k + dj * nx + di]:
                        ok = False
                        break
                if ok:
                    out[k] = 1
        m = out
    return m


def astar(g, starts, goal_t, goal_v, via_cost, layer_cost, max_exp=1200000, wh=1.2):
    """starts: list of (k, li); goal_t[li]: bytearray (cell is target copper on li) or None; goal_v: bytearray
    (a via here reaches the plane) or None. Returns (list of (k, li) states, ended_on_plane_via)."""
    nx, ny = g.nx, g.ny
    blk, vblk = g.blk, g.vblk
    hot = getattr(g, "hot", None) or bytearray(nx * ny)
    layers = g.layers
    gx0 = gy0 = 10 ** 9
    gx1 = gy1 = -1
    arrs = [goal_t[li] for li in layers if goal_t[li] is not None] + ([goal_v] if goal_v is not None else [])
    for arr in arrs:
        k = arr.find(1)
        if k < 0:
            continue
        kl = arr.rfind(1)
        gy0 = min(gy0, k // nx)
        gy1 = max(gy1, kl // nx)
        for j in range(k // nx, kl // nx + 1):
            row = arr[j * nx:(j + 1) * nx]
            a = row.find(1)
            if a >= 0:
                gx0 = min(gx0, a)
                gx1 = max(gx1, row.rfind(1))
    if gx1 < 0:
        return None, False

    def h(k):
        i, j = k % nx, k // nx
        dx = gx0 - i if i < gx0 else (i - gx1 if i > gx1 else 0)
        dy = gy0 - j if j < gy0 else (j - gy1 if j > gy1 else 0)
        a, b = (dx, dy) if dx > dy else (dy, dx)
        return (a - b) + SQ2 * b

    Wh = wh                                    # mildly greedy (more for long connections)
    NR_ = MIN_RUN + 1                          # run-length states: a turn needs >= MIN_RUN straight cells before it
    openq = []
    gs = {}
    par = {}
    for k, li in starts:
        st = ((k * 3 + li) * 9 + 8) * NR_ + MIN_RUN
        gs[st] = 0.0
        heapq.heappush(openq, (Wh * h(k), 0.0, st))
    dnb = [(di + dj * nx, di, dj, SQ2 if di and dj else 1.0) for di, dj in DIRS]
    TURN = 0.6
    TURN_SHORT = 6.0                           # turn after a run shorter than MIN_RUN (tight spots only)
    end = None
    plane_end = False
    exp = 0
    gv = goal_v
    while openq:
        f, gc, st = heapq.heappop(openq)
        if gc > gs.get(st, 1e18):
            continue
        exp += 1
        if exp > max_exp:
            break
        run = st % NR_
        s9 = st // NR_
        d = s9 % 9
        kl = s9 // 9
        li = kl % 3
        k = kl // 3
        gt = goal_t[li]
        if gt is not None and gt[k]:
            end = st
            break
        if gv is not None and gv[k] and run >= MIN_RUN // 2:
            end = st
            plane_end = True
            break
        i, j = k % nx, k // nx
        a = blk[li]
        lc = layer_cost[li]
        if d == 8:
            dirs = range(8)
        else:
            dirs = (d, (d + 1) % 8, (d + 7) % 8)
        tpen = TURN if run >= MIN_RUN else TURN_SHORT
        for nd in dirs:
            off, di, dj, c = dnb[nd]
            ii, jj = i + di, j + dj
            if ii < 0 or jj < 0 or ii >= nx or jj >= ny:
                continue
            k2 = k + off
            if a[k2]:
                continue
            if di and dj and (a[k + di] or a[k + dj * nx]):
                continue
            if hot[k2] and li:
                c *= 3.0
            if nd == d:
                ng = gc + c * lc
                r2 = run + 1 if run < MIN_RUN else MIN_RUN
            else:
                ng = gc + c * lc + (0 if d == 8 else tpen)
                r2 = min(1, MIN_RUN) if d != 8 else MIN_RUN
            if gv is not None and gv[k2]:
                ng += via_cost * 0.5
            s2 = (((k2 * 3 + li) * 9 + nd) * NR_) + r2
            if ng < gs.get(s2, 1e18):
                gs[s2] = ng
                par[s2] = st
                heapq.heappush(openq, (ng + Wh * h(k2), ng, s2))
        if not vblk[k]:
            for l2 in layers:
                if l2 == li or blk[l2][k]:
                    continue
                s2 = (((k * 3 + l2) * 9 + 8) * NR_) + MIN_RUN
                ng = gc + (via_cost * 3 if hot[k] else via_cost)
                if ng < gs.get(s2, 1e18):
                    gs[s2] = ng
                    par[s2] = st
                    heapq.heappush(openq, (ng + Wh * h(k), ng, s2))
    if end is None:
        if DEBUG:
            log("    astar: %d expansions, %d cells x %d layers, open %d" % (exp, nx * ny, len(layers), len(openq)))
        return None, False
    path = []
    st = end
    while True:
        s9 = st // NR_
        path.append(((s9 // 9) // 3, (s9 // 9) % 3))
        if st not in par:
            break
        st = par[st]
    path.reverse()
    return path, plane_end


# ----------------------------------------------------------------------------------------------- net router
class NetRouter:
    def __init__(self, world):
        self.w = world
        self.fail = []
        self.done = []

    def window(self, pts, margin):
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return (math.floor((min(xs) - margin) / STEP) * STEP, math.floor((min(ys) - margin) / STEP) * STEP,
                math.ceil((max(xs) + margin) / STEP) * STEP, math.ceil((max(ys) + margin) / STEP) * STEP)

    def stub_for(self, o, g, w):
        """Escape stub for a fine-pitch pad without free access cells: straight along the pad's long axis away from
        the footprint centre, to 0.3 mm past the pad tip. Returns (pts, li) or None."""
        p = o.pad
        fp = p.GetParentFootprint()
        fc = fp.GetPosition()
        fcx, fcy = MM(fc.x), MM(fc.y)
        cx, cy, c, s, hx, hy, r = o.g
        # long axis in board frame
        if hx >= hy:
            ax, ay, half = c, s, hx
        else:
            ax, ay, half = -s, c, hy
        if (cx - fcx) * ax + (cy - fcy) * ay < 0:
            ax, ay = -ax, -ay
        li = 0 if (o.lmask & 1) else 2
        px, py = -ay, ax
        for sgn in (1, -1):                       # outward first, then into the pin-ring interior
            for ext in (0.3, 0.45, 0.6, 0.8):
                L = half + ext
                e = (cx + sgn * ax * L, cy + sgn * ay * L)
                if self.seg_clear(o.net, (cx, cy), e, w, RL[li]) and self.keep_ok(o.net, e, li):
                    return [(cx, cy), e], li
            # straight out of the pin row, then a 45-degree dog-leg (pins capped by a via straight ahead)
            for ext0 in (0.12, 0.2, 0.3):
                p1 = (cx + sgn * ax * (half + ext0), cy + sgn * ay * (half + ext0))
                if not self.seg_clear(o.net, (cx, cy), p1, w, RL[li]):
                    continue
                for side in (1, -1):
                    dx, dy = (sgn * ax + side * px) / SQ2, (sgn * ay + side * py) / SQ2
                    for dl in (0.35, 0.5, 0.7, 0.9):
                        e = (p1[0] + dx * dl, p1[1] + dy * dl)
                        if self.seg_clear(o.net, p1, e, w, RL[li]) and self.keep_ok(o.net, e, li):
                            return [(cx, cy), p1, e], li
        return None

    def keep_ok(self, net, e, li):
        for (kx0, ky0, kx1, ky1, lis, allowed, vb) in KEEP:
            if li in lis and net not in allowed and kx0 <= e[0] <= kx1 and ky0 <= e[1] <= ky1:
                return False
        return True

    def seg_clear(self, net, a, b, w, cu_i, extra=0.0):
        """Exact-ish clearance check of a segment (sampled every 0.02 mm) against other-net copper."""
        hw = w / 2
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(1, int(L / 0.02))
        x0, x1 = min(a[0], b[0]) - 1, max(a[0], b[0]) + 1
        y0, y1 = min(a[1], b[1]) - 1, max(a[1], b[1]) + 1
        obs = [o for o in self.w.query(x0, y0, x1, y1) if o.net != net and (o.lmask >> cu_i) & 1 and o.tb]
        for t in range(n + 1):
            x = a[0] + (b[0] - a[0]) * t / n
            y = a[1] + (b[1] - a[1]) * t / n
            for o in obs:
                if o.dist(x, y) < hw + o.clr + extra:
                    return False
        return True

    def connect(self, net, src_items, dst_items, w=0.15, layers=(0, 1, 2), plane=False, margin=2.0,
                via_cost=24.0, layer_cost=(1.0, 1.0, 1.0), stub_w=None, max_margin=8.0, extra_pts=()):
        """Route from copper `src_items` (Obs list) to `dst_items` (Obs list) or the net's plane."""
        hw = w / 2
        vr = VIA[0] / 2

        def fine(items):
            return any(o.pad is not None and o.kind == "rr" and min(o.g[4], o.g[5]) < 0.13 for o in items)
        if not plane and dst_items and fine(dst_items) and not fine(src_items):
            src_items, dst_items = dst_items, src_items      # start from the constrained (fine-pitch) end
        pts = []
        for o in list(src_items) + list(dst_items) + list(extra_pts):
            if isinstance(o, tuple):
                pts.append(o)
            else:
                pts.append(((o.bb[0] + o.bb[2]) / 2, (o.bb[1] + o.bb[3]) / 2))
        if plane and not dst_items:
            src_pts = [((o.bb[0] + o.bb[2]) / 2, (o.bb[1] + o.bb[3]) / 2) for o in src_items]
            pts = src_pts
        xs_ = [p[0] for p in pts]
        ys_ = [p[1] for p in pts]
        span = max(max(xs_) - min(xs_), max(ys_) - min(ys_))
        m = max(margin, min(0.15 * span, 4.0))
        max_margin = max(max_margin, 2 * m)
        self.wh = 1.2 if span < 8 else 1.6
        while m <= max_margin + 1e-9:
            box = self.window(pts, m)
            res = self._try(net, src_items, dst_items, box, w, layers, plane, via_cost, layer_cost, stub_w)
            if res:
                return True
            m *= 2
        return False

    def _try(self, net, src_items, dst_items, box, w, layers, plane, via_cost, layer_cost, stub_w):
        W = self.w
        hw = w / 2
        g = Grid(W, net, box, hw, VIA[0] / 2, VIA[1], layers)
        g.apply_keep(KEEP)
        g.apply_hot(HOT)
        stubs = []          # (pts, li, stub-width) to emit if used
        starts = []
        anchor = {}         # start/goal cell -> exact anchor point to prepend/append
        for o in src_items:
            cs = g.cells_in(o, inset=0.01 if o.kind == "rr" else 0.0)
            if not cs and o.kind == "rr" and o.pad is not None:
                sw = min(stub_w or w, w, 0.15 if min(o.g[4], o.g[5]) < 0.13 else 2 * min(o.g[4], o.g[5]))
                st = self.stub_for(o, g, sw)
                if st:
                    spts, li = st
                    if li in layers:
                        e = spts[-1]
                        ci, cj = g.cell(*e)
                        cands = []
                        for di in (-1, 0, 1):
                            for dj in (-1, 0, 1):
                                ii, jj = ci + di, cj + dj
                                if 0 <= ii < g.nx and 0 <= jj < g.ny:
                                    k = jj * g.nx + ii
                                    if not g.blk[li][k]:
                                        cands.append((math.hypot(g.xy(k)[0] - e[0], g.xy(k)[1] - e[1]), k))
                        if cands:
                            cands.sort()
                            k = cands[0][1]
                            starts.append((k, li))
                            anchor[(k, li)] = e
                            stubs.append((spts, li, sw, (k, li)))
            starts.extend(cs)
        if not starts:
            if DEBUG:
                log("  no start cells", net, [(o.ref, o.num) for o in src_items if o.pad])
            return False
        n = g.nx * g.ny
        goal_t = [None, None, None]
        dst_stubs = []
        for li in layers:
            goal_t[li] = bytearray(n)
        for o in dst_items:
            cs = g.cells_in(o, inset=0.01 if o.kind == "rr" else 0.0)
            if not cs and o.kind == "rr" and o.pad is not None:
                sw = min(stub_w or w, w, 0.15 if min(o.g[4], o.g[5]) < 0.13 else 2 * min(o.g[4], o.g[5]))
                st = self.stub_for(o, g, sw)
                if st:
                    spts, li = st
                    if li in layers:
                        e = spts[-1]
                        ci, cj = g.cell(*e)
                        for di in (-1, 0, 1):
                            for dj in (-1, 0, 1):
                                ii, jj = ci + di, cj + dj
                                if 0 <= ii < g.nx and 0 <= jj < g.ny:
                                    k = jj * g.nx + ii
                                    if not g.blk[li][k]:
                                        goal_t[li][k] = 1
                                        anchor[(k, li)] = e
                        dst_stubs.append((spts, li, sw))
            for k, li in cs:
                goal_t[li][k] = 1
                if o.kind == "seg":
                    ax, ay, bx, by, _ = o.g
                    x, y = g.xy(k)
                    dx, dy = bx - ax, by - ay
                    L2 = dx * dx + dy * dy
                    t = 0 if L2 == 0 else max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / L2))
                    anchor[(k, li)] = (ax + t * dx, ay + t * dy)
                elif o.kind == "cir":
                    anchor[(k, li)] = (o.g[0], o.g[1])
        # same-net pours on signal layers of the destination set
        goal_v = None
        if plane:
            polys = []
            for (ci, outl, zn) in W.planes.get(net, ()):
                polys.extend(outl)
            if polys:
                goal_v = raster_poly_mask(g, polys, VIA[0] / 2 + 0.1)
                vb = g.vblk
                for k in range(n):
                    if goal_v[k] and vb[k]:
                        goal_v[k] = 0
            for (li6, outl, zn) in W.pours.get(net, ()):
                if li6 in RL and RL.index(li6) in layers:
                    li = RL.index(li6)
                    msk = raster_poly_mask(g, outl, hw + 0.05)
                    a = goal_t[li]
                    b = g.blk[li]
                    for k in range(n):
                        if msk[k] and not b[k]:
                            a[k] = 1
        # do not end on start cells
        sset = set(starts)
        for k, li in sset:
            if goal_t[li] is not None and goal_t[li][k]:
                goal_t[li][k] = 0
        path, plane_end = astar(g, starts, goal_t, goal_v, via_cost, layer_cost, wh=getattr(self, "wh", 1.2))
        if not path:
            if DEBUG:
                log("  fail", net, "box", ["%.2f" % v for v in box], "starts", len(starts))
                dd = os.environ.get("G_RIGHT_DUMP")
                if dd:
                    sset2 = set(starts)
                    for li in layers:
                        tag = "_".join("%s.%s" % (o.ref, o.num) for o in src_items if o.pad is not None)[:40]
                        fn = os.path.join(dd, "fail_%s_%s_%d_%s.ppm" % (net.replace("+", "p"), tag, g.nx, RL_NAME[li]))
                        with open(fn, "wb") as fh:
                            fh.write(b"P6 %d %d 255\n" % (g.nx, g.ny))
                            px = bytearray()
                            for k in range(n):
                                if (k, li) in sset2:
                                    px += b"\x00\xff\x00"
                                elif goal_t[li] is not None and goal_t[li][k]:
                                    px += b"\xff\x00\x00"
                                elif goal_v is not None and goal_v[k]:
                                    px += b"\xff\x80\x00"
                                elif g.blk[li][k]:
                                    px += b"\x00\x00\x00"
                                elif g.vblk[k]:
                                    px += b"\x80\x80\x80"
                                else:
                                    px += b"\xff\xff\xff"
                            fh.write(bytes(px))
            return False
        self.emit(net, g, path, plane_end, w, anchor, stubs, dst_stubs)
        return True

    def widen_corners(self, net, pts, cu_i, w):
        """Lengthen short 45-degree corner segments (a 90-degree turn made of two 45-degree steps) to CHAMFER where
        the clearance allows; the cut stays inside the corner."""
        pts = list(pts)
        for _ in range(3):
            changed = False
            for i in range(1, len(pts) - 2):
                A, B, C, D = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
                lbc = math.hypot(C[0] - B[0], C[1] - B[1])
                if lbc >= CHAMFER - 1e-6:
                    continue
                lab = math.hypot(B[0] - A[0], B[1] - A[1])
                lcd = math.hypot(D[0] - C[0], D[1] - C[1])
                if lab < 1e-6 or lcd < 1e-6:
                    continue
                u = ((B[0] - A[0]) / lab, (B[1] - A[1]) / lab)
                v = ((D[0] - C[0]) / lcd, (D[1] - C[1]) / lcd)
                if abs(u[0] * v[0] + u[1] * v[1]) > 1e-3:
                    continue
                need = (CHAMFER - lbc) / SQ2
                for t in (need, need * 0.75, need * 0.5, need * 0.25):
                    if t <= 0.01 or t > lab - 0.02 or t > lcd - 0.02:
                        continue
                    B2 = (B[0] - u[0] * t, B[1] - u[1] * t)
                    C2 = (C[0] + v[0] * t, C[1] + v[1] * t)
                    if self.seg_clear(net, B2, C2, w, cu_i, extra=MARGIN):
                        pts[i], pts[i + 1] = B2, C2
                        changed = True
                        break
            if not changed:
                break
        return pts

    def emit(self, net, g, path, plane_end, w, anchor, stubs, dst_stubs):
        W = self.w
        # stubs used at the start / end
        k0 = path[0]
        for spts, li, sw, key in stubs:
            if key == k0:
                W.draw_track(net, spts, RL[li], sw)
        kend = path[-1]
        if kend in anchor and not plane_end:
            for spts, li, sw in dst_stubs:
                e = spts[-1]
                if math.hypot(e[0] - anchor[kend][0], e[1] - anchor[kend][1]) < 1e-6:
                    W.draw_track(net, spts, RL[li], sw)
                    break
        segs = []
        cur = [path[0]]
        for st in path[1:]:
            if st[1] != cur[-1][1]:
                segs.append(cur)
                x, y = g.xy(st[0])
                W.draw_via(net, x, y)
                cur = [st]
            else:
                cur.append(st)
        segs.append(cur)
        for si, sg in enumerate(segs):
            li = sg[0][1]
            ks = [k for k, _ in sg]
            # simplify collinear
            simp = [ks[0]]
            for a in range(1, len(ks) - 1):
                (x0, y0), (x1, y1), (x2, y2) = g.xy(simp[-1]), g.xy(ks[a]), g.xy(ks[a + 1])
                if abs((x1 - x0) * (y2 - y1) - (y1 - y0) * (x2 - x1)) > 1e-9:
                    simp.append(ks[a])
            if len(ks) > 1:
                simp.append(ks[-1])
            pts = [g.xy(k) for k in simp]
            if si == 0 and path[0] in anchor:
                pts.insert(0, anchor[path[0]])
            if si == len(segs) - 1 and path[-1] in anchor and not plane_end:
                pts.append(anchor[path[-1]])
            if len(pts) >= 2:
                pts = self.widen_corners(net, pts, RL[li], w)
                W.draw_track(net, pts, RL[li], w)
        if plane_end:
            x, y = g.xy(path[-1][0])
            W.draw_via(net, x, y)
        ex, ey = anchor[path[-1]] if (path[-1] in anchor and not plane_end) else g.xy(path[-1][0])
        self.last_end = (ex, ey, RL[path[-1][1]], plane_end)


# ----------------------------------------------------------------------------------------------- connectivity
def clusters(board, nets):
    """net -> list of clusters; cluster = dict(pads=set((ref,num)), tracks=[...], vias=[...], zones=set(names))."""
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.BuildConnectivity()
    conn = board.GetConnectivity()
    want = set(nets)
    pads = defaultdict(list)
    for fp in board.GetFootprints():
        for p in fp.Pads():
            n = short(p.GetNetname())
            if n in want:
                pads[n].append(p)
    out = {}
    for net, pl in pads.items():
        seen = {}
        cl = []
        for p in pl:
            key = (p.GetParentFootprint().GetReference(), p.GetNumber())
            if key in seen:
                continue
            c = {"pads": {key}, "zones": set(), "items": []}
            seen[key] = c
            for it in conn.GetConnectedItems(p):
                cls = it.GetClass()
                if cls == "PAD":
                    k2 = (it.GetParentFootprint().GetReference(), it.GetNumber())
                    c["pads"].add(k2)
                    seen[k2] = c
                elif cls == "ZONE":
                    c["zones"].add(it.GetZoneName())
                elif cls in ("PCB_TRACK", "PCB_VIA", "PCB_ARC"):
                    c["items"].append(it)
            cl.append(c)
        out[net] = cl
    return out


def in_region(x, y):
    return any(a <= x <= c and b <= y <= d for a, b, c, d in REGION)


# ----------------------------------------------------------------------------------------------- plan
# per-net routing parameters: width, layers (indices into RL: 0=F.Cu 1=In2.Cu 2=B.Cu), stub width, layer cost
P_DEFAULT = dict(w=0.15, layers=(0, 1, 2))
PARAMS = {
    # RP2350 regulator (Pico 2 geometry): short L1 copper
    "VREG_LX": dict(w=0.3, layers=(0,), stub_w=0.2),
    "+1V1": dict(w=0.3, layers=(0, 2), stub_w=0.2, fallback_w=0.2),
    "VREG_AVDD": dict(w=0.2, layers=(0, 2)),
    "ADC_AVDD": dict(w=0.2),
    # crystal: L1 only
    "XIN": dict(w=0.15, layers=(0,)),
    "XOUT": dict(w=0.15, layers=(0,)),
    "XTAL_O": dict(w=0.15, layers=(0,)),
    # QSPI: short, prefer L1
    "QSPI_SCLK": dict(w=0.15, layer_cost=(1.0, 1.3, 1.2)),
    "QSPI_SD0": dict(w=0.15, layer_cost=(1.0, 1.3, 1.2)),
    "QSPI_SD1": dict(w=0.15, layer_cost=(1.0, 1.3, 1.2)),
    "QSPI_SD2": dict(w=0.15, layer_cost=(1.0, 1.3, 1.2)),
    "QSPI_SD3": dict(w=0.15, layer_cost=(1.0, 1.3, 1.2)),
    "QSPI_SS": dict(w=0.15, layer_cost=(1.0, 1.3, 1.2)),
    # supplies
    "ETH_0V95": dict(w=0.3, stub_w=0.2, fallback_w=0.2, plane=True),
    "ETH_3V3": dict(w=0.3, stub_w=0.2, fallback_w=0.2, plane=True),
    "ETH_AVDD33_PLL": dict(w=0.3, fallback_w=0.2),
    "ETH_0V95_UPS": dict(w=0.2),
    "ETH_MCT": dict(w=0.3, fallback_w=0.2),
    "+3V3": dict(w=0.25, stub_w=0.2, fallback_w=0.2, plane=True),
    "+5V": dict(w=0.4, fallback_w=0.3, plane=True),
    "GND": dict(w=0.25, stub_w=0.2, fallback_w=0.2, plane=True),
    "+3V3_USR": dict(w=0.3, fallback_w=0.2),
    "+5V_USR": dict(w=0.4, fallback_w=0.3),
    "LCD_BL_A": dict(w=0.3, fallback_w=0.2),
    "LCD_BL_K": dict(w=0.3, fallback_w=0.2),
}
# routing order: critical first, then local nets by span, supply ties last
ORDER_FIRST = ["VREG_LX", "QSPI_SD1", "QSPI_SD0", "QSPI_SCLK", "QSPI_SD3", "QSPI_SD2", "QSPI_SS", "XIN", "XOUT",
               "XTAL_O", "+1V1", "VREG_AVDD", "ETH_FB", "ETH_SWR_EN", "ETH_RSET", "ETH_AVDD33_PLL",
               "ETH_0V95_UPS", "ETH_0V95", "ETH_3V3"]


# Local keep-outs for this script's copper: (x0, y0, x1, y1, routing layers (RL indices), nets allowed, block vias)
HOT = [
    (217.3, 72.3, 229.7, 84.3),     # RP2350 pin field + 1 mm
    (192.5, 59.6, 200.5, 67.6),     # RTL8156 pin field + 1 mm
]
KEEP = [
    # inside the QFN pin rings (between the pins and the EP) on the top layer: no tracks under the IC bodies
    # (exceptions: +1V1 VREG_FB pin 65 is boxed in by the USB_DM_IC fan-out, XIN/XOUT by f_fanout's vias below
    #  pins 29-31, QSPI_SCLK/SD3 by f_fanout's vias above pins 69-71 -> they escape through the ring interior)
    (219.15, 73.75, 228.25, 82.85, (0,), ("+1V1", "XIN", "XOUT", "QSPI_SCLK", "QSPI_SD3", "QSPI_SD2", "QSPI_SS",
                                                "QSPI_SD0", "QSPI_SD1"), False),  # U1001
    (193.85, 60.95, 199.15, 66.25, (0,), (), True),         # U801 RTL8156BG
    # RP2350 crystal: only XIN / XTAL_O / XOUT / GND copper on L1 / L3 under Y1001 + its caps
    (221.5, 84.75, 225.5, 88.05, (0, 1), ("XIN", "XTAL_O", "XOUT", "GND"), True),
    # VREG: nothing else under the L1001 body (between its pads) on L1
    (225.6, 70.4, 227.2, 72.0, (0,), ("VREG_LX", "+1V1"), False),
]


def local_nets():
    part = json.load(open(os.path.join(HERE, "..", "build", "partition.json")))
    return [e["net"] for e in part["local"]["right"]]


def route(board, r):
    import time
    t0 = time.time()
    loc = [short(n) for n in local_nets()]
    supply = ["+3V3", "+5V", "GND"]
    cl = clusters(board, loc + supply)          # fills the zones (plane polygons for the World)
    order = [n for n in ORDER_FIRST if n in loc] + sorted([n for n in loc if n not in ORDER_FIRST]) + supply
    if os.environ.get("G_RIGHT_ONLY"):
        only = os.environ["G_RIGHT_ONLY"].split(",")
        order = [n for n in order if n in only]

    def run_pass(order):
        W = World(board, r)
        NR = NetRouter(W)
        log("world: %d obstacles, %.1fs" % (len(W.obs), time.time() - t0))

        def obs_of_cluster(net, c):
            keys = c["pads"]
            out = [o for o in W.net_items[net] if o.pad is not None and (o.ref, o.num) in keys]
            ids = set()
            for it in c["items"]:
                if it.GetClass() == "PCB_VIA":
                    p = it.GetPosition()
                    ids.add(("v", round(MM(p.x), 3), round(MM(p.y), 3)))
                else:
                    a, b = it.GetStart(), it.GetEnd()
                    ids.add(("t", round(MM(a.x), 3), round(MM(a.y), 3), round(MM(b.x), 3), round(MM(b.y), 3)))
            for o in W.net_items[net]:
                if o.pad is not None:
                    continue
                if o.kind == "cir":
                    key = ("v", round(o.g[0], 3), round(o.g[1], 3))
                elif o.kind == "seg":
                    key = ("t", round(o.g[0], 3), round(o.g[1], 3), round(o.g[2], 3), round(o.g[3], 3))
                else:
                    continue
                if key in ids:
                    out.append(o)
            return out

        stats = {"ok": 0, "fail": 0}
        fails = []

        def cdist(A, B):
            best = 1e9
            for a in A:
                ax, ay = (a.bb[0] + a.bb[2]) / 2, (a.bb[1] + a.bb[3]) / 2
                for b in B:
                    d = math.hypot(ax - (b.bb[0] + b.bb[2]) / 2, ay - (b.bb[1] + b.bb[3]) / 2)
                    if d < best:
                        best = d
            return best

        for net in order:
            cls = cl.get(net)
            if not cls:
                continue
            prm = dict(P_DEFAULT)
            prm.update(PARAMS.get(net, {}))
            is_plane = prm.get("plane", False)
            pzones = set(z for (_, _, z) in W.planes.get(net, ()))
            groups = []
            for c in cls:
                groups.append({"items": obs_of_cluster(net, c), "main": bool(pzones & c["zones"]),
                               "pads": set(c["pads"])})
            if not is_plane:
                if len(groups) < 2:
                    continue
                max(groups, key=lambda gr: len(gr["pads"]))["main"] = True
            if net in supply:
                # only clusters with a pad inside the region are this script's job
                def gin(gr):
                    return any(o.pad is not None and in_region(o.g[0], o.g[1]) for o in gr["items"])
                groups = [gr for gr in groups if gr["main"] or gin(gr)]
            tried = set()
            while True:
                pend = [gr for gr in groups if not gr["main"] and id(gr) not in tried]
                if not pend:
                    break
                others_all = lambda gr: [o for g2 in groups if g2 is not gr for o in g2["items"]]
                pend.sort(key=lambda gr: cdist(gr["items"], others_all(gr)) if len(groups) > 1 else 0)
                gr = pend[0]
                items = gr["items"]
                dst = others_all(gr)
                if dst:
                    dd = sorted((dmin_pair(o, items), id(o), o) for o in dst)
                    lim = dd[0][0] + 6.0
                    dst = [o for d_, _, o in dd if d_ <= lim]
                before = len(W.net_items[net])
                ok = False
                for w in [prm["w"]] + ([prm["fallback_w"]] if prm.get("fallback_w") else []):
                    kw = dict(w=w, layers=prm["layers"], plane=is_plane, stub_w=prm.get("stub_w"),
                              layer_cost=prm.get("layer_cost", (1.0, 1.0, 1.0)))
                    if is_plane:
                        ok = NR.connect(net, items, [o for o in dst if dmin_pair(o, items) < 4.0], margin=1.5,
                                        max_margin=3.0, **kw)
                        if not ok:
                            ok = NR.connect(net, items, dst, margin=2.0, max_margin=4.0, **kw)
                    else:
                        ok = NR.connect(net, items, dst, **kw)
                    if ok:
                        break
                new = W.net_items[net][before:]
                if DEBUG:
                    log("%s %s %s %.1fs" % (net, "ok" if ok else "FAIL", sorted("%s.%s" % k for k in gr["pads"])[:3],
                                            time.time() - t0))
                if not ok:
                    tried.add(id(gr))
                    continue
                stats["ok"] += 1
                gr["items"] = items + new
                ex, ey, eli, pend_plane = NR.last_end
                target = None
                if pend_plane:
                    gr["main"] = True
                else:
                    pts_ = []
                    for o in new:
                        if o.kind == "seg":
                            pts_.append((o.g[0], o.g[1], o.lmask))
                            pts_.append((o.g[2], o.g[3], o.lmask))
                        elif o.kind == "cir":
                            pts_.append((o.g[0], o.g[1], o.lmask))
                    for g2 in groups:
                        if g2 is gr:
                            continue
                        for o in g2["items"]:
                            if any((o.lmask & lm_) and o.dist(px_, py_) <= 0.02 for (px_, py_, lm_) in pts_):
                                target = g2
                                break
                        if target:
                            break
                    if target is None:
                        log("  warn: %s end (%.3f,%.3f) touches no group" % (net, ex, ey))
                        gr["main"] = True
                    else:
                        target["items"] += gr["items"]
                        target["pads"] |= gr["pads"]
                        target["main"] = target["main"] or gr["main"]
                        groups.remove(gr)
                tried = set()
            for gr in groups:
                if not gr["main"]:
                    stats["fail"] += 1
                    fails.append((net, sorted("%s.%s" % k for k in gr["pads"])))
        log("connections ok %d, failed %d, %d track segments, %.1fs" % (stats["ok"], stats["fail"], W.drawn,
                                                                       time.time() - t0))
        for f in fails:
            log("  FAILED", f[0], " ".join(f[1]))
        return fails, W

    fails, W = run_pass(order)
    if fails and not os.environ.get("G_RIGHT_ONEPASS"):
        # second pass: the failed nets first (greedy routing order matters); keep the better result
        first = []
        for n, _ in fails:
            if n not in first:
                first.append(n)
        order2 = first + [n for n in order if n not in first]
        n1 = len(fails)
        clear_group(board, r)
        fails2, W2 = run_pass(order2)
        if len(fails2) > n1:
            clear_group(board, r)
            fails, W = run_pass(order)
        else:
            fails = fails2
    log("final: %d connections not routed" % len(fails))


def clear_group(board, r):
    items = list(r.group.GetItems())
    r.group.RemoveAll()
    for it in items:
        board.Remove(it)


def dmin_pair(o, items):
    ax, ay = (o.bb[0] + o.bb[2]) / 2, (o.bb[1] + o.bb[3]) / 2
    return min(math.hypot(ax - (b.bb[0] + b.bb[2]) / 2, ay - (b.bb[1] + b.bb[3]) / 2) for b in items)
