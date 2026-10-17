"""odock-10 phase g, region "usbc": local signal nets, PMG1 BGA escapes, strap/decoupling links and supply drops.

Runs after a_planes, b_power, c_hs_usbc, d_hs_hub, e_hs_eth_sd and f_fanout (before z_stitch / Freerouting).
NETS = [] and GROUPED = True: everything drawn here lives in group "route:g_usbc" and only that group is replaced
on a re-run, so the nets stay shared with the other scripts.

How it works (all automatic, nothing hard-coded except the policy tables below):
- Zones are filled (except the outer GND pours GND_L1 / GND_L6, which the autoroute step removes) and KiCad's
  connectivity gives the copper clusters of every net touching the region.
- A grid router (0.05 mm grid, layers F.Cu / In2.Cu / B.Cu, 8 directions with 45 degree turns only, through vias).
  Obstacles are built per window from every pad, track, via, hole and other-net pour (b_power P_*), with the real
  clearance per pair of nets: 0.15 mm, 0.3 mm across the HV boundary (exemptions read from the .kicad_dru "high
  voltage" rule), 0.3 mm track-to-track from USB_90 / HS_85 tracks ("hs pair spacing"), 0.2 mm copper-to-hole,
  0.25 mm hole-to-hole, 0.3 mm to the board edge.
- Copper is confined to the usbc rectangles + 0.5 mm. No through vias in the hs_usbc keep-outs (L3 hub-SS corridor
  x 159.75-163.4 / y 63-79, the laptop USB2 L3 run, the hub-link transitions) and none inside SMD pads, except
  0.35/0.15 via-in-pad (filled/capped) in PMG1 BGA balls, in the slow pins of U501-U504, in IC / ESD-array supply
  pins and in J502 A4/A9, wherever the clearances allow it (an optional .kicad_dru rule "via in pad" relaxes the
  via-to-pad clearance for those parts; see docs/routing-notes/g_usbc.md).
- Order: (A) PMG1 ball escapes, negotiated together (same-net neighbour balls joined on L1, inner balls via-in-pad
  to L3/L6); (B) all local-net connections (cluster MST) plus the stray GND / +3V3 / VBUS_LAPTOP pads, negotiated
  together (PathFinder: exact clearance footprints on the grid, geometric conflict check, history costs), then a
  greedy pass for what is left; (C) remaining supply pads to the nearest same-net copper (plane via, pour, track).
Widths: signals 0.15 (0.10 neck-down only as a last resort), supply drops 0.2 (0.3 for the +5V feed where it fits),
fallback 0.15; vias 0.45/0.25, 0.35/0.15 only where 0.45 does not fit.
Env: GUSBC_DEBUG=1 (log), GUSBC_PHASES=ABC, GUSBC_NEG_ITERS=30.
"""
import os
import sys
import math
import heapq
import time
import re
import fnmatch
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew  # noqa: E402
import _pwrlib as L  # noqa: E402

NETS = []
GROUPED = True

mm, MM = pcbnew.FromMM, pcbnew.ToMM

# ------------------------------------------------------------------------------------------------ policy
REGION = [(138.0, 50.0, 180.0, 80.0), (144.0, 49.4, 177.0, 61.2)]    # layout/usbc.py REGION
MARGIN = 0.5
S = 0.05                                     # grid step (mm)
GX0, GY0 = 137.5, 48.9                       # grid origin (multiples of S: pads on 0.05 land on grid points)
GX1, GY1 = 180.5, 80.5
CU6 = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu]
RL = [pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]          # routing layers
RLN = ["F.Cu", "In2.Cu", "B.Cu"]
LCOST = [1.2, 1.2, 1.0]                                 # L6 slightly preferred for slow signals
INNER_PLANES = (pcbnew.In1_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu)
CLR, HV_CLR, HS_CLR, HOLE_CLR, H2H, EDGE_CLR = 0.15, 0.30, 0.30, 0.20, 0.25, 0.30
M_T = 0.02                                   # track sampling margin (grid quantisation)
M_V = -1e-6                                  # via margin: vias sit exactly on grid points (exact clearances)
VIA45 = (0.45, 0.25)
VIA35 = (0.35, 0.15)
VIA_BGA = (0.35, 0.15)                       # U401 via-in-pad (JLC POFV)
VIA_STRAP = (0.35, 0.15)                     # fine-pitch via-in-pad (board minimum: 0.25 dia, 0.10 annular ring)
VIA30 = (0.30, 0.15)                         # tier kept for a relaxed rule set; unused while the annular min is 0.10
VIA30_ZONE = (0.0, 0.0, 0.0, 0.0)            # (empty: 0.30/0.15 vias violate the 0.10 mm annular-ring minimum)
VIA_COST = 26                                # in grid steps (1.3 mm)
VTIER = (0, 1.0, 1.4, 1.0, 2.0)              # cost factor per vok code (1 = 0.45, 2 = 0.35, 3 = via-in-pad, 4 = 0.30)
TURN_COST = 0.4
NEG_ITERS = int(os.environ.get("GUSBC_NEG_ITERS", "30"))
NECK = (0.1,)                                # last-resort neck-down width (board minimum 0.09)
NEG_SUPPLY = ("GND", "+3V3", "VBUS_LAPTOP")   # plane nets whose stray pads join the phase-B negotiation
EXP_LIMIT = 900000
HV_NETS = L.HV_NETS


def _hv_exempt_refs():
    """Footprints whose pads the .kicad_dru "high voltage" rule exempts (read from the rule itself, so a rule change
    is picked up on the next run)."""
    try:
        dru = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "odock-10.kicad_dru")
        txt = open(dru).read()
        m = re.search(r'\(rule "high voltage"(.*?)\(constraint', txt, re.S)
        return set(re.findall(r"memberOfFootprint\('([^']+)'\)", m.group(1))) if m else {"J501"}
    except Exception:
        return {"J501"}


HV_EXEMPT = _hv_exempt_refs()


def _vip_rule():
    """Optional .kicad_dru rule "via in pad": (footprint patterns, via-to-pad clearance) for via-in-pad on fine-pitch
    parts. Without it the netclass 0.15 mm applies and a 0.35 mm via does not fit in a 0.4 mm-pitch QFN pad."""
    try:
        dru = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "odock-10.kicad_dru")
        txt = open(dru).read()
        m = re.search(r'\(rule "via in pad"(.*?)\(constraint clearance \(min ([0-9.]+)mm\)\)', txt, re.S)
        if m:
            return set(re.findall(r"memberOfFootprint\('([^']+)'\)", m.group(1))), float(m.group(2))
    except Exception:
        pass
    return set(), CLR


VIP_RULE_REFS, VIP_RULE_CLR = _vip_rule()
HS_CLASSES = ("USB_90", "HS_85")
BGA_REF = "U401"
BGA_FIELD = (158.4, 51.55, 163.4, 56.55)     # ball centre bbox
BGA_OUT = 0.65                               # escape: leave the ball field by this much
FIELD_MULT = 3.0                             # escape: cost factor for travelling under the ball field
ESC_PULL = 0.35                              # escape end cost per grid step of distance to the destination
# fine-pitch ICs whose slow-signal / supply pins may take a 0.35/0.15 via-in-pad (JLC POFV): the TUSB1064/1046 straps
# and CTL pins sit between DP / SS lanes or have SBU / AUX tracks right at their toes (hs_usbc.md), the protectors'
# VBIAS / FLT pins are hemmed in by the CC / SBU fan-out
STRAP_VIP = ("U502", "U503", "U501", "U504")
# single pads that may take a 0.35/0.15 via-in-pad: J502 A9 VBUS_DS is boxed in by the B-row lane hop vias, a via in the
# pad lands straight in the L4 VBUS_DS island (power.md: "tie A9 between the rows" has no room left)
VIP_PADS = {("J502", "A9"), ("J502", "A4")}
VIP_SUPPLY = {"GND", "+3V3", "+5V", "PMG1_VDDD"}     # supply pins of ICs / ESD arrays: via-in-pad allowed
# no through vias (docs/routing-notes/hs_usbc.md "Keep-outs for other routers")
NO_VIA = [
    (159.75, 63.0, 163.4, 79.0),     # L3 hub SS corridor
    (145.8, 79.3, 171.0, 80.6),      # L3 laptop USB2
    (166.6, 76.9, 174.4, 80.4),      # L1/L3 transitions of the hub links
]
# where the interblock nets of the PMG1 leave the region (usbc.md routing intent)
_PWR_EXIT = (138.0, 60.0)
_RIGHT_EXIT = (180.0, 76.0)
EXIT_HINT = {n: _PWR_EXIT for n in ("VBB_EN", "VBB_VSEL0", "VBB_VSEL1", "VBB_VSEL2", "LAPTOP_SNK_EN", "LAPTOP_SRC_EN",
                                    "VBB_PG", "LAPTOP_OVP_N", "EXT_PWR_PRESENT", "PDIN_PRESENT", "VBUS_LSW")}
EXIT_HINT.update({n: _RIGHT_EXIT for n in ("I2C_PD_SCL", "I2C_PD_SDA", "I2C_PD_INT_N")})
SUPPLY_W = {"+5V": (0.3, 0.2, 0.15), "GND": (0.2, 0.15), "+3V3": (0.2, 0.15), "PMG1_VDDD": (0.2, 0.15),
            "VBUS_DS": (0.2, 0.15), "VBUS_LAPTOP": (0.15,), "VBUS_LSW": (0.15,)}
OUTER_GND_POURS = ("GND_L1", "GND_L6")
DEBUG = os.environ.get("GUSBC_DEBUG")
PHASES = os.environ.get("GUSBC_PHASES", "ABC")


def short(n):
    return str(n).split("/")[-1]


def in_region(x, y, m=0.0):
    return any(x0 - m <= x <= x1 + m and y0 - m <= y <= y1 + m for x0, y0, x1, y1 in REGION)


# ------------------------------------------------------------------------------------------------ geometry
def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def in_poly(x, y, poly):
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[j]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
        j = i
    return inside


def poly_dist(x, y, polys):
    """polys: list of point lists (outlines). -1 inside, else distance to the outline."""
    best = 1e9
    for poly in polys:
        if in_poly(x, y, poly):
            return -1.0
        n = len(poly)
        for i in range(n):
            d = seg_dist(x, y, poly[i][0], poly[i][1], poly[(i + 1) % n][0], poly[(i + 1) % n][1])
            if d < best:
                best = d
    return best


def sps_outlines(sps):
    out = []
    for i in range(sps.OutlineCount()):
        ch = sps.Outline(i)
        out.append([(MM(ch.CPoint(k).x), MM(ch.CPoint(k).y)) for k in range(ch.PointCount())])
    return out


class Item:
    """Copper (or hole) on the board. dist(x, y): distance to the copper edge (negative / -1 inside)."""
    __slots__ = ("kind", "net", "code", "layers", "bb", "dist", "hole", "smd", "hs", "hv", "ref", "num", "cx", "cy",
                 "r", "w", "uid", "pts", "exempt_hv")

    def __init__(self, kind, net, code, layers, bb, dist, hole=None, smd=False, hs=False, ref="", num="",
                 cx=0.0, cy=0.0, r=0.0, w=0.0, uid=None, pts=None):
        self.kind, self.net, self.code, self.layers, self.bb, self.dist = kind, net, code, layers, bb, dist
        self.hole, self.smd, self.hs, self.ref, self.num = hole, smd, hs, ref, num
        self.cx, self.cy, self.r, self.w, self.uid, self.pts = cx, cy, r, w, uid, pts
        self.hv = net in HV_NETS
        self.exempt_hv = bool(ref) and any(fnmatch.fnmatchcase(ref, pat) for pat in HV_EXEMPT)


def pad_item(p, fp, ncls):
    ref = fp.GetReference()
    net = short(p.GetNetname())
    layers = frozenset(l for l in CU6 if p.IsOnLayer(l))
    pos = p.GetPosition()
    cx, cy = MM(pos.x), MM(pos.y)
    b = p.GetBoundingBox()
    bb = (MM(b.GetLeft()), MM(b.GetTop()), MM(b.GetRight()), MM(b.GetBottom()))
    shp = p.GetShape()
    hole = None
    if p.GetDrillSizeX() > 0:
        hs = p.GetEffectiveHoleShape()
        try:
            sg = hs.GetSeg()
            hole = (MM(sg.A.x), MM(sg.A.y), MM(sg.B.x), MM(sg.B.y), MM(hs.GetWidth()) / 2)
        except Exception:
            r = MM(min(p.GetDrillSizeX(), p.GetDrillSizeY())) / 2
            hole = (cx, cy, cx, cy, r)
    if shp in (pcbnew.PAD_SHAPE_CIRCLE, pcbnew.PAD_SHAPE_RECTANGLE, pcbnew.PAD_SHAPE_OVAL,
               pcbnew.PAD_SHAPE_ROUNDRECT, pcbnew.PAD_SHAPE_CHAMFERED_RECT, pcbnew.PAD_SHAPE_TRAPEZOID):
        sz = p.GetSize()
        hx, hy = MM(sz.x) / 2, MM(sz.y) / 2
        if shp == pcbnew.PAD_SHAPE_CIRCLE:
            rr = hx
            hy = hx
        elif shp == pcbnew.PAD_SHAPE_OVAL:
            rr = min(hx, hy)
        elif shp == pcbnew.PAD_SHAPE_ROUNDRECT:
            try:
                rr = MM(p.GetRoundRectCornerRadius(pcbnew.F_Cu))
            except Exception:
                rr = MM(p.GetRoundRectCornerRadius())
            rr = min(rr, hx, hy)
        else:
            rr = 0.0
        a = math.radians(p.GetOrientationDegrees())
        c, s = math.cos(a), math.sin(a)
        ix, iy = hx - rr, hy - rr

        def dist(x, y, cx=cx, cy=cy, c=c, s=s, ix=ix, iy=iy, rr=rr):
            dx, dy = x - cx, y - cy
            u = abs(dx * c - dy * s) - ix      # KiCad rotation is clockwise in the y-down frame
            v = abs(dx * s + dy * c) - iy
            if u > 0:
                if v > 0:
                    return math.sqrt(u * u + v * v) - rr
                return u - rr
            if v > 0:
                return v - rr
            return (u if u > v else v) - rr
    else:
        lay = pcbnew.F_Cu if p.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
        polys = sps_outlines(p.GetEffectivePolygon(lay))

        def dist(x, y, polys=polys):
            return poly_dist(x, y, polys)
    return Item("pad", net, p.GetNetCode(), layers, bb, dist, hole=hole,
                smd=p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD, ref=ref, num=p.GetNumber(), cx=cx, cy=cy,
                uid=p.m_Uuid.AsString())


def track_item(net, code, layer, ax, ay, bx, by, w, hs, uid=None):
    hw = w / 2
    bb = (min(ax, bx) - hw, min(ay, by) - hw, max(ax, bx) + hw, max(ay, by) + hw)

    def dist(x, y):
        return seg_dist(x, y, ax, ay, bx, by) - hw
    return Item("trk", net, code, frozenset([layer]), bb, dist, hs=hs, cx=ax, cy=ay, w=w, uid=uid,
                pts=(ax, ay, bx, by))


def via_item(net, code, x, y, size, drill, uid=None, layers=None):
    r = size / 2
    bb = (x - r, y - r, x + r, y + r)

    def dist(px, py):
        return math.hypot(px - x, py - y) - r
    return Item("via", net, code, layers or frozenset(CU6), bb, dist, hole=(x, y, x, y, drill / 2), cx=x, cy=y,
                r=r, uid=uid)


class Hash:
    def __init__(self, cell=1.0):
        self.c = cell
        self.d = defaultdict(list)

    def add(self, it):
        c = self.c
        x0, y0, x1, y1 = it.bb
        for i in range(int(math.floor(x0 / c)), int(math.floor(x1 / c)) + 1):
            for j in range(int(math.floor(y0 / c)), int(math.floor(y1 / c)) + 1):
                self.d[(i, j)].append(it)

    def query(self, x0, y0, x1, y1):
        c = self.c
        seen = set()
        out = []
        for i in range(int(math.floor(x0 / c)), int(math.floor(x1 / c)) + 1):
            for j in range(int(math.floor(y0 / c)), int(math.floor(y1 / c)) + 1):
                for it in self.d.get((i, j), ()):
                    if id(it) not in seen:
                        seen.add(id(it))
                        out.append(it)
        return out


def netclass_fn(board):
    import json
    import fnmatch
    pats = []
    try:
        pro = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "odock-10.kicad_pro")
        fn = board.GetFileName()
        if fn and os.path.exists(os.path.splitext(fn)[0] + ".kicad_pro"):
            pro = os.path.splitext(fn)[0] + ".kicad_pro"
        pats = [(p["pattern"], p["netclass"]) for p in json.load(open(pro))["net_settings"]["netclass_patterns"]]
    except Exception:
        pass
    cache = {}

    def f(net):
        if net not in cache:
            cache[net] = "Default"
            for pat, cls in pats:
                if fnmatch.fnmatchcase(net, pat):
                    cache[net] = cls
                    break
        return cache[net]
    return f


def path_geom(W, path, endvia, width):
    """Segments (layer index, ax, ay, bx, by, half width), vias (x, y, r) and bbox of a grid path."""
    wn = W["wn"]
    xw0, yw0 = W["xw0"], W["yw0"]
    segs, vias = [], []
    prev = None
    run = []

    def flush(run):
        if len(run) >= 2:
            li = run[0][0]
            pts = [run[0][1]]
            for (l_, p) in run[1:]:
                pts.append(p)
            # merge collinear
            out = [pts[0]]
            for k in range(1, len(pts) - 1):
                d1 = (pts[k][0] - out[-1][0], pts[k][1] - out[-1][1])
                d2 = (pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1])
                if abs(d1[0] * d2[1] - d1[1] * d2[0]) > 1e-9:
                    out.append(pts[k])
            out.append(pts[-1])
            for a, b in zip(out, out[1:]):
                segs.append((li, a[0], a[1], b[0], b[1], width / 2))
    for li, k in path:
        p = (xw0 + (k % wn) * S, yw0 + (k // wn) * S)
        if prev is not None and prev[0] != li:
            flush(run)
            run = []
            sz = W["vsize"].get(k, VIA45 if W["vok"][k] == 1 else VIA35)[0]
            vias.append((p[0], p[1], sz / 2))
        run.append((li, p))
        prev = (li, k)
    flush(run)
    if endvia:
        k = path[-1][1]
        p = (xw0 + (k % wn) * S, yw0 + (k // wn) * S)
        sz = W["vsize"].get(k, VIA45 if W["vok"][k] == 1 else VIA35)[0]
        vias.append((p[0], p[1], sz / 2))
    xs = [s_[1] for s_ in segs] + [s_[3] for s_ in segs] + [v[0] for v in vias]
    ys = [s_[2] for s_ in segs] + [s_[4] for s_ in segs] + [v[1] for v in vias]
    if not xs:
        p = (xw0 + (path[0][1] % wn) * S, yw0 + (path[0][1] // wn) * S)
        xs, ys = [p[0]], [p[1]]
    return segs, vias, (min(xs), min(ys), max(xs), max(ys))


def seg_seg(a, b, c, d):
    """Distance between segments ab and cd."""
    def cross(o, p, q):
        return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])
    d1, d2, d3, d4 = cross(c, d, a), cross(c, d, b), cross(a, b, c), cross(a, b, d)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)) and d1 != 0 and d2 != 0:
        return 0.0
    return min(seg_dist(a[0], a[1], c[0], c[1], d[0], d[1]), seg_dist(b[0], b[1], c[0], c[1], d[0], d[1]),
               seg_dist(c[0], c[1], a[0], a[1], b[0], b[1]), seg_dist(d[0], d[1], a[0], a[1], b[0], b[1]))


def _near_pts(ax, ay, bx, by, cx, cy, dx, dy, req):
    """Sample points of segment ab closer than req to segment cd."""
    L_ = math.hypot(bx - ax, by - ay)
    n = max(1, int(L_ / 0.05))
    out = []
    for t in range(n + 1):
        x, y = ax + (bx - ax) * t / n, ay + (by - ay) * t / n
        if seg_dist(x, y, cx, cy, dx, dy) < req:
            out.append((x, y))
    return out


def geom_conflicts(gi, gj):
    """Clearance violations between two path geometries: (hits on path i, hits on path j) as lists of
    (layer index or None for all layers, x, y)."""
    hi, hj = [], []
    si, vi, _ = gi
    sj, vj, _ = gj
    for (li, ax, ay, bx, by, hw) in si:
        for (lj, cx, cy, dx, dy, hw2) in sj:
            if li != lj:
                continue
            if max(ax, bx) < min(cx, dx) - 0.5 or max(cx, dx) < min(ax, bx) - 0.5 or \
                    max(ay, by) < min(cy, dy) - 0.5 or max(cy, dy) < min(ay, by) - 0.5:
                continue
            req = hw + hw2 + CLR - 1e-6
            if seg_seg((ax, ay), (bx, by), (cx, cy), (dx, dy)) < req:
                hi += [(li, x, y) for x, y in _near_pts(ax, ay, bx, by, cx, cy, dx, dy, req)]
                hj += [(li, x, y) for x, y in _near_pts(cx, cy, dx, dy, ax, ay, bx, by, req)]
        for (x, y, r) in vj:
            req = hw + r + CLR - 1e-6
            if seg_dist(x, y, ax, ay, bx, by) < req:
                hi += [(li, px, py) for px, py in _near_pts(ax, ay, bx, by, x, y, x, y, req)]
                hj.append((None, x, y))
    for (x, y, r) in vi:
        for (lj, cx, cy, dx, dy, hw2) in sj:
            req = hw2 + r + CLR - 1e-6
            if seg_dist(x, y, cx, cy, dx, dy) < req:
                hi.append((None, x, y))
                hj += [(lj, px, py) for px, py in _near_pts(cx, cy, dx, dy, x, y, x, y, req)]
        for (x2, y2, r2) in vj:
            if math.hypot(x - x2, y - y2) < r + r2 + CLR - 1e-6:
                hi.append((None, x, y))
                hj.append((None, x2, y2))
    return (hi, hj) if (hi or hj) else None


# ------------------------------------------------------------------------------------------------ router
class Ctx:
    def __init__(self, board, r):
        self.board, self.r = board, r
        self.ncls = netclass_fn(board)
        self.h = Hash()
        self.items = []
        self.codes = {}
        self.stats = defaultdict(int)
        self.fail = []
        self.vip = {}            # (gi, gj) -> (code, size, drill)
        self.region_cells = None
        self.zones_obst = []

    # ---- board snapshot
    def load(self):
        b = self.board
        X0, Y0, X1, Y1 = GX0 - 3, GY0 - 3, GX1 + 3, GY1 + 3
        for fp in b.GetFootprints():
            for p in fp.Pads():
                if not any(p.IsOnLayer(l) for l in CU6) and p.GetDrillSizeX() == 0:
                    continue
                bbx = p.GetBoundingBox()
                if MM(bbx.GetRight()) < X0 or MM(bbx.GetLeft()) > X1 or MM(bbx.GetBottom()) < Y0 or \
                        MM(bbx.GetTop()) > Y1:
                    continue
                it = pad_item(p, fp, self.ncls)
                self.add(it)
                ref, num = it.ref, it.num
                gi, gj = self.cell_of(it.cx, it.cy)
                if ref == BGA_REF and it.code > 0:
                    self.vip[(gi, gj)] = (it.code, VIA_BGA[0], VIA_BGA[1])
                elif (ref, num) in VIP_PADS and it.code > 0:
                    w_, h_ = it.bb[2] - it.bb[0], it.bb[3] - it.bb[1]
                    ax = (1, 0) if w_ > h_ else (0, 1)
                    for off in (0.0, 0.1, -0.1, 0.15, -0.15):
                        c2 = self.cell_of(it.cx + ax[0] * off, it.cy + ax[1] * off)
                        if it.dist(GX0 + c2[0] * S, GY0 + c2[1] * S) < -0.049:
                            self.vip.setdefault(c2, (it.code, VIA_STRAP[0], VIA_STRAP[1]))
                elif ref[:1] in ("U", "D") and it.net in VIP_SUPPLY and it.smd and \
                        it.bb[2] - it.bb[0] < 0.9 and it.bb[3] - it.bb[1] < 0.9 and in_region(it.cx, it.cy):
                    # IC / ESD-array supply pins boxed in by lanes: a via in the pad straight into the plane
                    w_, h_ = it.bb[2] - it.bb[0], it.bb[3] - it.bb[1]
                    ax = (1, 0) if w_ > h_ else (0, 1)
                    for off in (0.0, 0.1, -0.1, 0.15, -0.15):
                        c2 = self.cell_of(it.cx + ax[0] * off, it.cy + ax[1] * off)
                        if it.dist(GX0 + c2[0] * S, GY0 + c2[1] * S) < -0.049:
                            self.vip.setdefault(c2, (it.code, VIA_STRAP[0], VIA_STRAP[1]))
                elif ref in STRAP_VIP and it.code > 0 and it.net != "GND" and \
                        self.ncls(it.net) not in HS_CLASSES and it.bb[2] - it.bb[0] < 0.9 and \
                        it.bb[3] - it.bb[1] < 0.9:
                    # along the pad's long axis: centre and staggered positions (neighbour pins may take one too)
                    w_, h_ = it.bb[2] - it.bb[0], it.bb[3] - it.bb[1]
                    ax = (1, 0) if w_ > h_ else (0, 1)
                    for off in (0.0, 0.1, -0.1, 0.15, -0.15):
                        c2 = self.cell_of(it.cx + ax[0] * off, it.cy + ax[1] * off)
                        if it.dist(GX0 + c2[0] * S, GY0 + c2[1] * S) < -0.049:
                            self.vip.setdefault(c2, (it.code, VIA_STRAP[0], VIA_STRAP[1]))
        for t in b.GetTracks():
            self.add_board_track(t, X0, Y0, X1, Y1)
        # other-net pours on the routing layers (b_power P_*): obstacles (never cut them)
        for z in b.Zones():
            if z.GetIsRuleArea() or not z.GetNetCode():
                continue
            if z.GetZoneName() in OUTER_GND_POURS:
                continue
            lays = [l for l in RL if z.GetLayerSet().Contains(l)]
            if not lays:
                continue
            bbx = z.GetBoundingBox()
            bb = (MM(bbx.GetLeft()), MM(bbx.GetTop()), MM(bbx.GetRight()), MM(bbx.GetBottom()))
            if bb[2] < X0 or bb[0] > X1 or bb[3] < Y0 or bb[1] > Y1:
                continue
            polys = sps_outlines(z.Outline())

            def dist(x, y, polys=polys):
                return poly_dist(x, y, polys)
            it = Item("zone", short(z.GetNetname()), z.GetNetCode(), frozenset(lays), bb, dist,
                      uid=z.m_Uuid.AsString())
            self.add(it)
        # rule areas forbidding vias / tracks
        self.rules = []
        for z in b.Zones():
            if not z.GetIsRuleArea() or not (z.GetDoNotAllowVias() or z.GetDoNotAllowTracks()):
                continue
            polys = sps_outlines(z.Outline())
            ls = set(l for l in CU6 if z.GetLayerSet().Contains(l))
            bbx = z.GetBoundingBox()
            self.rules.append((polys, (MM(bbx.GetLeft()), MM(bbx.GetTop()), MM(bbx.GetRight()), MM(bbx.GetBottom())),
                               ls, z.GetDoNotAllowTracks(), z.GetDoNotAllowVias()))

    def add_board_track(self, t, X0, Y0, X1, Y1):
        net = short(t.GetNetname())
        code = t.GetNetCode()
        uid = t.m_Uuid.AsString()
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition()
            x, y = MM(p.x), MM(p.y)
            if not (X0 < x < X1 and Y0 < y < Y1):
                return
            top, bot = t.TopLayer(), t.BottomLayer()
            lays = frozenset(l for l in CU6 if t.IsOnLayer(l))
            self.add(via_item(net, code, x, y, MM(t.GetWidth(pcbnew.F_Cu)), MM(t.GetDrillValue()), uid, lays))
            return
        hs = self.ncls(net) in HS_CLASSES
        if t.GetClass() == "PCB_ARC":
            a, m, e = t.GetStart(), t.GetMid(), t.GetEnd()
            pts = self._arc_pts((MM(a.x), MM(a.y)), (MM(m.x), MM(m.y)), (MM(e.x), MM(e.y)))
        else:
            a, e = t.GetStart(), t.GetEnd()
            pts = [(MM(a.x), MM(a.y)), (MM(e.x), MM(e.y))]
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            if max(ax, bx) < X0 or min(ax, bx) > X1 or max(ay, by) < Y0 or min(ay, by) > Y1:
                continue
            self.add(track_item(net, code, t.GetLayer(), ax, ay, bx, by, MM(t.GetWidth()), hs, uid))

    @staticmethod
    def _arc_pts(a, m, e, n=8):
        ax, ay = a
        bx, by = m
        cx_, cy_ = e
        d = 2 * (ax * (by - cy_) + bx * (cy_ - ay) + cx_ * (ay - by))
        if abs(d) < 1e-9:
            return [a, e]
        ux = ((ax * ax + ay * ay) * (by - cy_) + (bx * bx + by * by) * (cy_ - ay) + (cx_ * cx_ + cy_ * cy_) * (ay - by)) / d
        uy = ((ax * ax + ay * ay) * (cx_ - bx) + (bx * bx + by * by) * (ax - cx_) + (cx_ * cx_ + cy_ * cy_) * (bx - ax)) / d
        R = math.hypot(ax - ux, ay - uy)
        a0 = math.atan2(ay - uy, ax - ux)
        a1 = math.atan2(by - uy, bx - ux)
        a2 = math.atan2(cy_ - uy, cx_ - ux)

        def norm(t):
            return (t - a0) % (2 * math.pi)
        ccw = norm(a1) < norm(a2)
        span = norm(a2) if ccw else -((a0 - a2) % (2 * math.pi))
        return [(ux + R * math.cos(a0 + span * k / n), uy + R * math.sin(a0 + span * k / n)) for k in range(n + 1)]

    def add(self, it):
        self.items.append(it)
        self.h.add(it)

    @staticmethod
    def cell_of(x, y):
        return int(round((x - GX0) / S)), int(round((y - GY0) / S))

    # ---- window obstacle build for one net
    def build(self, code, net, win, hw, fallback):
        """Returns window W with blk[3] (track centre blocked), vok (0 / 1 = 0.45 / 2 = 0.35 / 3 = VIP) and the
        VIP sizes."""
        gi0, gj0, gi1, gj1 = win
        wn, wm = gi1 - gi0 + 1, gj1 - gj0 + 1
        N = wn * wm
        blk = [bytearray(N) for _ in RL]
        v45 = bytearray(N)
        v35 = bytearray(N)
        pv45 = bytearray(N)      # via would overlap a same-net SMD pad
        pv35 = bytearray(N)
        v30 = bytearray(N)
        pv30 = bytearray(N)
        hv = net in HV_NETS
        r45, r35 = VIA45[0] / 2, VIA35[0] / 2
        d45, d35 = VIA45[1] / 2, VIA35[1] / 2
        r30, d30 = VIA30[0] / 2, VIA30[1] / 2
        xw0, yw0 = GX0 + gi0 * S, GY0 + gj0 * S
        # region / edge
        for j in range(wm):
            y = yw0 + j * S
            for i in range(wn):
                x = xw0 + i * S
                k = j * wn + i
                if not in_region(x, y, MARGIN):
                    for li in range(3):
                        blk[li][k] = 1
                    v45[k] = v35[k] = v30[k] = 1
                    continue
                e = y - L.BY0
                if e < EDGE_CLR + hw + 0.01:
                    for li in range(3):
                        blk[li][k] = 1
                if e < EDGE_CLR + r45 + 0.01:
                    v45[k] = 1
                if e < EDGE_CLR + r35 + 0.01:
                    v35[k] = 1
                if e < EDGE_CLR + r30 + 0.01:
                    v30[k] = 1
        # no-via rectangles + rule areas
        for (x0, y0, x1, y1) in NO_VIA:
            self._mark_rect(v45, win, x0 - r45, y0 - r45, x1 + r45, y1 + r45)
            self._mark_rect(v35, win, x0 - r35, y0 - r35, x1 + r35, y1 + r35)
            self._mark_rect(v30, win, x0 - r30, y0 - r30, x1 + r30, y1 + r30)
        for polys, bb, ls, nt, nv in self.rules:
            if bb[2] < xw0 - 1 or bb[0] > xw0 + wn * S + 1 or bb[3] < yw0 - 1 or bb[1] > yw0 + wm * S + 1:
                continue
            i0, i1 = max(0, int((bb[0] - 0.5 - xw0) / S)), min(wn - 1, int((bb[2] + 0.5 - xw0) / S) + 1)
            j0, j1 = max(0, int((bb[1] - 0.5 - yw0) / S)), min(wm - 1, int((bb[3] + 0.5 - yw0) / S) + 1)
            for j in range(j0, j1 + 1):
                for i in range(i0, i1 + 1):
                    d = poly_dist(xw0 + i * S, yw0 + j * S, polys)
                    k = j * wn + i
                    if nv and d < r45 + 0.02:
                        v45[k] = 1
                    if nv and d < r35 + 0.02:
                        v35[k] = 1
                    if nv and d < r30 + 0.02:
                        v30[k] = 1
                    if nt and d < hw + 0.02:
                        for li, l in enumerate(RL):
                            if l in ls:
                                blk[li][k] = 1
        # items
        X0, Y0 = xw0 - 1, yw0 - 1
        X1, Y1 = xw0 + wn * S + 1, yw0 + wm * S + 1
        for it in self.h.query(X0, Y0, X1, Y1):
            same = it.code == code and code > 0
            if same:
                if it.kind == "pad" and it.smd:
                    self._mark_dist(it, win, [(pv45, r45 - 0.001), (pv35, r35 - 0.001), (pv30, r30 - 0.001)], [])
                if it.hole is not None:     # hole-to-hole and no stacking on same-net vias / holes
                    hx0, hy0, hx1, hy1, hr = it.hole
                    rr_ = it.r if it.kind == "via" else hr
                    self._mark_hole(win, it.hole, [(v45, max(r45 + rr_, d45 + hr + H2H) - hr),
                                                   (v35, max(r35 + rr_, d35 + hr + H2H) - hr),
                                                   (v30, max(r30 + rr_, d30 + hr + H2H) - hr)])
                continue
            c = HV_CLR if (hv != it.hv and not (it.kind == "pad" and it.exempt_hv)) else CLR
            if it.kind == "zone":
                ct = c + 0.05     # keep away from other-net pours (they would be cut)
            else:
                ct = max(c, HS_CLR) if (it.kind == "trk" and it.hs) else c
            lis = [li for li, l in enumerate(RL) if l in it.layers]
            trk_targets = [(blk[li], hw + ct + M_T) for li in lis]
            via_targets = []
            if it.kind == "zone":
                via_targets = [(v45, r45 + c + 0.05), (v35, r35 + c + 0.05), (v30, r30 + c + 0.05)]
            elif it.layers:
                via_targets = [(v45, r45 + c + M_V), (v35, r35 + c + M_V), (v30, r30 + c + M_V)]
            self._mark_dist(it, win, via_targets, trk_targets)
            if it.hole is not None:
                hr = it.hole[4]
                self._mark_hole(win, it.hole, [(v45, max(d45 + H2H, r45 + HOLE_CLR)),
                                               (v35, max(d35 + H2H, r35 + HOLE_CLR)),
                                               (v30, max(d30 + H2H, r30 + HOLE_CLR))])
                if it.kind == "pad":       # copper-to-hole 0.2 (NPTH holes may sit inside a "copper" pad shape)
                    hb = [(blk[li], hw + HOLE_CLR + M_T) for li in range(3)]
                    self._mark_hole(win, it.hole, hb)
        vok = bytearray(N)
        vsize = {}
        for k in range(N):
            if not v45[k] and not pv45[k]:
                vok[k] = 1
            elif fallback and not v35[k] and not pv35[k]:
                vok[k] = 2
            elif fallback and not v30[k] and not pv30[k]:
                x, y = xw0 + (k % wn) * S, yw0 + (k // wn) * S
                if VIA30_ZONE[0] < x < VIA30_ZONE[2] and VIA30_ZONE[1] < y < VIA30_ZONE[3]:
                    vok[k] = 4
                    vsize[k] = VIA30
        # via-in-pad cells of this net: exact check
        for (gi, gj), (vc, sz, dr) in self.vip.items():
            if vc != code or not (gi0 <= gi <= gi1 and gj0 <= gj <= gj1):
                continue
            x, y = GX0 + gi * S, GY0 + gj * S
            if self.via_legal(code, net, x, y, sz, dr):
                k = (gj - gj0) * wn + (gi - gi0)
                vok[k] = 3
                vsize[k] = (sz, dr)
        return dict(win=win, wn=wn, wm=wm, blk=blk, vok=vok, vsize=vsize, xw0=xw0, yw0=yw0)

    def via_legal(self, code, net, x, y, sz, dr):
        r = sz / 2
        hv = net in HV_NETS
        if not in_region(x, y, MARGIN - r) or y - L.BY0 < EDGE_CLR + r:
            return False
        for (x0, y0, x1, y1) in NO_VIA:
            if x0 - r < x < x1 + r and y0 - r < y < y1 + r:
                return False
        for it in self.h.query(x - 1, y - 1, x + 1, y + 1):
            if it.code == code and code > 0:
                if it.hole is not None:
                    hx0, hy0, hx1, hy1, hr = it.hole
                    dd = seg_dist(x, y, hx0, hy0, hx1, hy1)
                    if it.kind == "via" and dd < max(r + it.r, dr / 2 + hr + H2H):
                        return False
                    if it.kind == "pad" and dd < dr / 2 + hr + H2H:
                        return False
                continue
            c = HV_CLR if (hv != it.hv and not (it.kind == "pad" and it.exempt_hv)) else CLR
            if it.kind == "pad" and c == CLR and any(fnmatch.fnmatchcase(it.ref, p) for p in VIP_RULE_REFS):
                c = VIP_RULE_CLR
            if it.layers and it.dist(x, y) < r + c - 1e-6:
                return False
            if it.hole is not None:
                hx0, hy0, hx1, hy1, hr = it.hole
                if seg_dist(x, y, hx0, hy0, hx1, hy1) < max(dr / 2 + hr + H2H, r + hr + HOLE_CLR):
                    return False
        return True

    def segment_legal(self, code, net, a, b, w, layer):
        """Exact clearance check of a straight track against everything else."""
        hw = w / 2
        hv = net in HV_NETS
        x0, y0, x1, y1 = min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])
        L_ = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(2, int(L_ / 0.01) + 1)
        pts = [(a[0] + (b[0] - a[0]) * t / (n - 1), a[1] + (b[1] - a[1]) * t / (n - 1)) for t in range(n)]
        for it in self.h.query(x0 - 1, y0 - 1, x1 + 1, y1 + 1):
            if it.code == code and code > 0:
                continue
            if layer not in it.layers and not (it.kind == "pad" and it.hole is not None):
                continue
            c = HV_CLR if (hv != it.hv and not (it.kind == "pad" and it.exempt_hv)) else CLR
            if it.kind == "trk" and it.hs:
                c = max(c, HS_CLR)
            if layer in it.layers and min(it.dist(x, y) for x, y in pts) < hw + c:
                return False
            if it.hole is not None:
                hx0, hy0, hx1, hy1, hr = it.hole
                if min(seg_dist(x, y, hx0, hy0, hx1, hy1) for x, y in pts) - hr < hw + HOLE_CLR:
                    return False
        return True

    def _mark_rect(self, arr, win, x0, y0, x1, y1):
        gi0, gj0, gi1, gj1 = win
        wn = gi1 - gi0 + 1
        i0 = max(gi0, int(math.ceil((x0 - GX0) / S))) - gi0
        i1 = min(gi1, int(math.floor((x1 - GX0) / S))) - gi0
        j0 = max(gj0, int(math.ceil((y0 - GY0) / S))) - gj0
        j1 = min(gj1, int(math.floor((y1 - GY0) / S))) - gj0
        for j in range(j0, j1 + 1):
            for i in range(i0, i1 + 1):
                arr[j * wn + i] = 1

    def _mark_dist(self, it, win, via_targets, trk_targets):
        targets = via_targets + trk_targets
        if not targets:
            return
        gi0, gj0, gi1, gj1 = win
        wn = gi1 - gi0 + 1
        m = max(t for _, t in targets)
        x0, y0, x1, y1 = it.bb
        i0 = max(gi0, int(math.floor((x0 - m - GX0) / S)))
        i1 = min(gi1, int(math.ceil((x1 + m - GX0) / S)))
        j0 = max(gj0, int(math.floor((y0 - m - GY0) / S)))
        j1 = min(gj1, int(math.ceil((y1 + m - GY0) / S)))
        if i0 > i1 or j0 > j1:
            return
        dist = it.dist
        for gj in range(j0, j1 + 1):
            y = GY0 + gj * S
            row = (gj - gj0) * wn - gi0
            for gi in range(i0, i1 + 1):
                d = dist(GX0 + gi * S, y)
                if d >= m:
                    continue
                k = row + gi
                for arr, t in targets:
                    if d < t:
                        arr[k] = 1

    def _mark_hole(self, win, hole, targets):
        hx0, hy0, hx1, hy1, hr = hole
        gi0, gj0, gi1, gj1 = win
        wn = gi1 - gi0 + 1
        m = max(t for _, t in targets) + hr
        i0 = max(gi0, int(math.floor((min(hx0, hx1) - m - GX0) / S)))
        i1 = min(gi1, int(math.ceil((max(hx0, hx1) + m - GX0) / S)))
        j0 = max(gj0, int(math.floor((min(hy0, hy1) - m - GY0) / S)))
        j1 = min(gj1, int(math.ceil((max(hy0, hy1) + m - GY0) / S)))
        for gj in range(j0, j1 + 1):
            y = GY0 + gj * S
            for gi in range(i0, i1 + 1):
                d = seg_dist(GX0 + gi * S, y, hx0, hy0, hx1, hy1) - hr
                k = (gj - gj0) * wn + gi - gi0
                for arr, t in targets:
                    if d < t:
                        arr[k] = 1

    # ---- copper of a cluster as start / goal cells
    def cells_of(self, W, items, zones, want_via_goal=True, hw=0.075, near=None):
        """Returns (trk[3] dict k -> cost, viag set k) for the given same-net items (Item) and filled zones."""
        gi0, gj0, gi1, gj1 = W["win"]
        wn, wm = W["wn"], W["wm"]
        trk = [dict(), dict(), dict()]
        viag = set()
        for it in items:
            x0, y0, x1, y1 = it.bb
            i0 = max(gi0, int(math.floor((x0 - GX0) / S)))
            i1 = min(gi1, int(math.ceil((x1 - GX0) / S)))
            j0 = max(gj0, int(math.floor((y0 - GY0) / S)))
            j1 = min(gj1, int(math.ceil((y1 - GY0) / S)))
            lis = [li for li, l in enumerate(RL) if l in it.layers]
            if not lis:
                continue
            for gj in range(j0, j1 + 1):
                y = GY0 + gj * S
                for gi in range(i0, i1 + 1):
                    x = GX0 + gi * S
                    if it.kind == "pad":
                        d = it.dist(x, y)
                        if d > -0.02:
                            continue
                        cost = math.hypot(x - it.cx, y - it.cy) / S * 0.5
                    elif it.kind == "trk":
                        d = it.dist(x, y)
                        if d > -it.w * 0.25:
                            continue
                        cost = 0.0
                    elif it.kind == "via":
                        if math.hypot(x - it.cx, y - it.cy) > it.r * 0.6:
                            continue
                        cost = 0.0
                    else:
                        continue
                    k = (gj - gj0) * wn + gi - gi0
                    for li in lis:
                        if cost < trk[li].get(k, 1e9):
                            trk[li][k] = cost
        # filled zones
        xw0, yw0 = W["xw0"], W["yw0"]
        for z in zones:
            for lay in z.GetLayerSet().Seq():
                if lay not in CU6:
                    continue
                fill = z.GetFilledPolysList(lay)
                if fill.OutlineCount() == 0:
                    continue
                fill = pcbnew.SHAPE_POLY_SET(fill)
                fill.BuildBBoxCaches()
                fb = fill.BBox()
                fx0, fy0, fx1, fy1 = MM(fb.GetLeft()), MM(fb.GetTop()), MM(fb.GetRight()), MM(fb.GetBottom())
                if near is not None:
                    fx0, fy0 = max(fx0, near[0]), max(fy0, near[1])
                    fx1, fy1 = min(fx1, near[2]), min(fy1, near[3])
                i0 = max(0, int((fx0 - xw0) / S))
                i1 = min(wn - 1, int((fx1 - xw0) / S) + 1)
                j0 = max(0, int((fy0 - yw0) / S))
                j1 = min(wm - 1, int((fy1 - yw0) / S) + 1)
                if lay in RL:
                    li = RL.index(lay)
                    rad = hw + 0.03
                    for j in range(j0, j1 + 1):
                        for i in range(i0, i1 + 1):
                            k = j * wn + i
                            if W["blk"][li][k]:
                                continue
                            x, y = xw0 + i * S, yw0 + j * S
                            if all(fill.Contains(pcbnew.VECTOR2I(mm(px), mm(py)), -1, 0, True)
                                   for px, py in ((x, y), (x + rad, y), (x - rad, y), (x, y + rad), (x, y - rad))):
                                trk[li][k] = 0.0
                elif want_via_goal and lay in INNER_PLANES:
                    vok = W["vok"]
                    for j in range(j0, j1 + 1, 2):
                        for i in range(i0, i1 + 1, 2):
                            k = j * wn + i
                            if not vok[k] or k in viag:
                                continue
                            sz = W["vsize"].get(k, VIA45 if vok[k] == 1 else VIA35)[0]
                            rad = sz / 2 + 0.02
                            x, y = xw0 + i * S, yw0 + j * S
                            if all(fill.Contains(pcbnew.VECTOR2I(mm(px), mm(py)), -1, 0, True)
                                   for px, py in ((x, y), (x + rad, y), (x - rad, y), (x, y + rad), (x, y - rad))):
                                viag.add(k)
        return trk, viag

    # ---- A*
    def astar(self, W, starts, goals, viag, hgoal=None):
        wn, wm = W["wn"], W["wm"]
        N = wn * wm
        blk, vok = W["blk"], W["vok"]
        dirs = [(1, 0, 1.0), (1, 1, 1.41421), (0, 1, 1.0), (-1, 1, 1.41421), (-1, 0, 1.0), (-1, -1, 1.41421),
                (0, -1, 1.0), (1, -1, 1.41421)]
        if hgoal:
            hx0, hy0, hx1, hy1 = hgoal

            def h(k):
                i, j = k % wn, k // wn
                dx = hx0 - i if i < hx0 else (i - hx1 if i > hx1 else 0)
                dy = hy0 - j if j < hy0 else (j - hy1 if j > hy1 else 0)
                return max(dx, dy) + 0.41421 * min(dx, dy)
        else:
            def h(k):
                return 0.0
        g = {}
        came = {}
        openq = []
        for li in range(3):
            for k, c0 in starts[li].items():
                if blk[li][k] and vok[k] != 3:
                    continue
                s = li * N + k
                if c0 < g.get(s, 1e18):
                    g[s] = c0
                    came[s] = (None, -1)
                    heapq.heappush(openq, (c0 + h(k), c0, s))
        end = None
        n_exp = 0
        while openq:
            f, gc, s = heapq.heappop(openq)
            if gc > g.get(s, 1e18):
                continue
            n_exp += 1
            if n_exp > EXP_LIMIT:
                break
            li, k = divmod(s, N)
            if k in goals[li] and came[s][0] is not None:
                end = (s, False)
                break
            if k in viag and vok[k] and came[s][0] is not None:
                end = (s, True)
                break
            i, j = k % wn, k // wn
            pd = came[s][1]
            lc = LCOST[li]
            bl = blk[li]
            for d in (() if bl[k] else (range(8)) if pd < 0 else (pd, (pd + 1) % 8, (pd + 7) % 8)):
                di, dj, c = dirs[d]
                ii, jj = i + di, j + dj
                if ii < 0 or jj < 0 or ii >= wn or jj >= wm:
                    continue
                k2 = jj * wn + ii
                if bl[k2]:
                    continue
                if di and dj and (bl[j * wn + ii] and bl[jj * wn + i]):
                    continue
                ng = gc + c * lc + (TURN_COST if (pd >= 0 and d != pd) else 0.0)
                s2 = li * N + k2
                if ng < g.get(s2, 1e18):
                    g[s2] = ng
                    came[s2] = (s, d)
                    heapq.heappush(openq, (ng + h(k2), ng, s2))
            if vok[k]:
                vc = VIA_COST * VTIER[vok[k]]
                for l2 in range(3):
                    if l2 == li or (blk[l2][k] and not (vok[k] == 3 and k in goals[l2])):
                        continue
                    s2 = l2 * N + k
                    ng = gc + vc
                    if ng < g.get(s2, 1e18):
                        g[s2] = ng
                        came[s2] = (s, -1)
                        heapq.heappush(openq, (ng + h(k), ng, s2))
        self.stats["expansions"] += n_exp
        if end is None:
            return None
        s, endvia = end
        path = [s]
        while came[path[-1]][0] is not None:
            path.append(came[path[-1]][0])
        path.reverse()
        return [(st // N, st % N) for st in path], endvia

    # ---- negotiated congestion (PathFinder) for a group of connections sharing one window
    def negotiate(self, reqs, win, iters=40, label="neg"):
        """reqs: list of dict(net, code, src (items), width, goal_fn(W) -> (gl, vg), endvia, outer_vip_mult,
        bga_outer (set of grid cells where a via costs more)). All requests are routed in the same window, letting
        them overlap at a growing cost until no path sits in another one's clearance. Returns {index: items}."""
        gi0, gj0, gi1, gj1 = win
        wn, wm = gi1 - gi0 + 1, gj1 - gj0 + 1
        N = wn * wm
        occT = [[0] * N for _ in range(3)]
        occV = [[0] * N for _ in range(3)]
        hist = [[0.0] * N for _ in range(3)]
        histV = [0.0] * N
        Ws, starts, goals = [], [], []
        for q in reqs:
            W = self.build(q["code"], q["net"], win, q["width"] / 2, True)
            st, _ = self.cells_of(W, q["src"], [], False, q["width"] / 2)
            gl, vg = q["goal_fn"](W)
            for li in range(3):
                for k in [k for k in gl[li] if W["blk"][li][k] and W["vok"][k] != 3]:
                    del gl[li][k]
            Ws.append(W)
            starts.append(st)
            goals.append((gl, vg))
            if DEBUG:
                print("   %s req %s %s: starts %s goals %s/%d" % (
                    label, q.get("label"), q["net"], [sum(1 for k in st[li] if not W["blk"][li][k]) for li in range(3)],
                    [len(x) for x in gl], len(vg)))
        # footprint stencils (grid offsets)
        def disc(rad):
            n = int(rad / S) + 1
            return [(di, dj) for di in range(-n, n + 1) for dj in range(-n, n + 1) if math.hypot(di, dj) * S < rad]
        hw0 = 0.075
        R_TT = 2 * hw0 + CLR + M_T                  # track centre vs track centre
        R_TV = hw0 + CLR + VIA45[0] / 2 + M_V        # track centre vs via centre (worst via)
        st_T = disc(R_TT)
        st_TV = disc(R_TV)
        foot = [None] * len(reqs)
        paths = [None] * len(reqs)
        netocc = defaultdict(lambda: defaultdict(int))     # code -> (arr, li, k) -> count (same net never conflicts)

        def mark(i, sign):
            if foot[i] is None:
                return
            no = netocc[reqs[i]["code"]]
            for key in foot[i]:
                arr_i, li, k = key
                (occT if arr_i == 0 else occV)[li][k] += sign
                no[key] += sign

        def footprint(path, endvia, W):
            fs = set()
            vcells = []
            prev = None
            for li, k in path:
                if prev is not None and prev[0] != li:
                    vcells.append(k)
                prev = (li, k)
            if endvia:
                vcells.append(path[-1][1])
            for li, k in path:
                i, j = k % wn, k // wn
                for di, dj in st_T:
                    ii, jj = i + di, j + dj
                    if 0 <= ii < wn and 0 <= jj < wm:
                        fs.add((0, li, jj * wn + ii))
                for di, dj in st_TV:
                    ii, jj = i + di, j + dj
                    if 0 <= ii < wn and 0 <= jj < wm:
                        fs.add((1, li, jj * wn + ii))
            for k in vcells:
                sz = W["vsize"].get(k, VIA45 if W["vok"][k] == 1 else VIA35)[0]
                i, j = k % wn, k // wn
                for di, dj in disc(sz / 2 + CLR + hw0 + M_T):
                    ii, jj = i + di, j + dj
                    if 0 <= ii < wn and 0 <= jj < wm:
                        for li in range(3):
                            fs.add((0, li, jj * wn + ii))
                for di, dj in disc(sz / 2 + CLR + VIA35[0] / 2 - 0.001):
                    ii, jj = i + di, j + dj
                    if 0 <= ii < wn and 0 <= jj < wm:
                        for li in range(3):
                            fs.add((1, li, jj * wn + ii))
            return list(fs), vcells

        dirs = [(1, 0, 1.0), (1, 1, 1.41421), (0, 1, 1.0), (-1, 1, 1.41421), (-1, 0, 1.0), (-1, -1, 1.41421),
                (0, -1, 1.0), (1, -1, 1.41421)]

        def search(i, pf):
            W = Ws[i]
            blk, vok = W["blk"], W["vok"]
            gl, vg = goals[i]
            q = reqs[i]
            endvia = q.get("endvia")
            vmult = q.get("vip_mult", {})
            lay_ok = q.get("layers", (0, 1, 2))
            force_via = q.get("force_via", False)
            fmask = q.get("field_mask")
            no = netocc[q["code"]]
            g = {}
            came = {}
            openq = []
            for li in ((0,) if force_via else lay_ok):
                for k, c0 in starts[i][li].items():
                    if blk[li][k] and vok[k] != 3:
                        continue
                    s = li * N + k
                    g[s] = c0
                    came[s] = (None, -1)
                    heapq.heappush(openq, (c0, c0, s))
            n_exp = 0
            while openq:
                f, gc, s = heapq.heappop(openq)
                if gc > g.get(s, 1e18):
                    continue
                n_exp += 1
                if n_exp > 250000:
                    if DEBUG:
                        print("     search %s: expansion limit" % q.get("label"))
                    return None
                if s < 0:
                    s0, ev0 = came[s]
                    return self._unwind(came, s0, N), ev0
                li, k = divmod(s, N)
                if came[s][0] is not None:
                    tc = None
                    if not endvia and k in gl[li]:
                        tc, ev0 = gl[li][k], False
                    elif k in vg and vok[k]:
                        tc, ev0 = vg[k] if isinstance(vg, dict) else 0.0, True
                    if tc is not None:
                        e = -1 - s
                        if gc + tc < g.get(e, 1e18):
                            g[e] = gc + tc
                            came[e] = (s, ev0)
                            heapq.heappush(openq, (gc + tc, gc + tc, e))
                ii0, jj0 = k % wn, k // wn
                pd = came[s][1]
                lc = LCOST[li]
                bl = blk[li]
                oT = occT[li]
                hT = hist[li]
                tmoves = (range(8) if pd < 0 else (pd, (pd + 1) % 8, (pd + 7) % 8))
                if li not in lay_ok or (force_via and came[s][0] is None) or bl[k]:
                    tmoves = ()
                for d in tmoves:
                    di, dj, c = dirs[d]
                    ii, jj = ii0 + di, jj0 + dj
                    if ii < 0 or jj < 0 or ii >= wn or jj >= wm:
                        continue
                    k2 = jj * wn + ii
                    if bl[k2]:
                        continue
                    if di and dj and (bl[jj0 * wn + ii] and bl[jj * wn + ii0]):
                        continue
                    o = oT[k2]
                    if o:
                        o -= no.get((0, li, k2), 0)
                    cc = c * lc * (1.0 + hT[k2]) * (1.0 + pf * o) * (FIELD_MULT if fmask and fmask[k2] else 1.0)
                    ng = gc + cc + (TURN_COST if (pd >= 0 and d != pd) else 0.0)
                    s2 = li * N + k2
                    if ng < g.get(s2, 1e18):
                        g[s2] = ng
                        came[s2] = (s, d)
                        heapq.heappush(openq, (ng, ng, s2))
                if vok[k]:
                    ov = 0
                    for l3 in range(3):
                        ov += occV[l3][k] + occT[l3][k]
                    if ov:
                        for l3 in range(3):
                            ov -= no.get((1, l3, k), 0) + no.get((0, l3, k), 0)
                    vc = VIA_COST * VTIER[vok[k]] * vmult.get(k, 1.0) * (1.0 + histV[k]) * \
                        (1.0 + pf * ov)
                    for l2 in lay_ok:
                        if l2 == li or (blk[l2][k] and not (vok[k] == 3 and k in gl[l2])):
                            continue
                        s2 = l2 * N + k
                        ng = gc + vc
                        if ng < g.get(s2, 1e18):
                            g[s2] = ng
                            came[s2] = (s, -1)
                            heapq.heappush(openq, (ng, ng, s2))
            if DEBUG:
                print("     search %s: exhausted after %d (lay_ok %s fv %s)" % (q.get("label"), n_exp, lay_ok, force_via))
            return None

        pf = 0.6
        order = list(range(len(reqs)))
        for it_n in range(iters):
            for i in order:
                mark(i, -1)
                res = search(i, pf)
                if res is None:
                    foot[i], paths[i] = None, None
                    continue
                path, ev = res
                fs, vcells = footprint(path, ev, Ws[i])
                foot[i], paths[i] = fs, (path, ev, vcells)
                mark(i, +1)
            # conflicts: a path cell inside another path's footprint
            nconf = 0
            for i in order:
                if paths[i] is None:
                    continue
                no = netocc[reqs[i]["code"]]
                path, ev, vcells = paths[i]
                bad = False
                for li, k in path:
                    o = occT[li][k] - no.get((0, li, k), 0)
                    if o > 0:
                        hist[li][k] += 0.5
                        bad = True
                for k in vcells:
                    o = sum(occV[l][k] - no.get((1, l, k), 0) for l in range(3))
                    if o > 0:
                        histV[k] += 0.5
                        bad = True
                nconf += bad
            if DEBUG:
                print("   %s iter %d: %d conflicting, %d unrouted, pf %.1f" % (
                    label, it_n, nconf, sum(p is None for p in paths), pf))
            if nconf == 0:
                break
            pf *= 1.6
        out = {}
        for i, q in enumerate(reqs):
            if paths[i] is None:
                continue
            path, ev, vcells = paths[i]
            # skip paths that still conflict with an already emitted one (left for the greedy pass)
            out[i] = (path, ev)
        emitted = {}
        for i in sorted(out, key=lambda i: len(out[i][0])):
            path, ev = out[i]
            W = Ws[i]
            # final legality against what was emitted in this round: rebuild cheaply by checking clearance
            ok = True
            for j, items in emitted.items():
                for it in items:
                    for li, k in path:
                        x, y = W["xw0"] + (k % wn) * S, W["yw0"] + (k // wn) * S
                        if it.bb[0] - 0.6 < x < it.bb[2] + 0.6 and it.bb[1] - 0.6 < y < it.bb[3] + 0.6:
                            if RL[li] in it.layers and it.dist(x, y) < reqs[i]["width"] / 2 + CLR + 0.01:
                                ok = False
                                break
                    if not ok:
                        break
                if not ok:
                    break
            if not ok:
                continue
            emitted[i] = self.emit(W, reqs[i]["net"], reqs[i]["code"], path, ev, reqs[i]["width"])
        return emitted

    @staticmethod
    def _unwind(came, s, N):
        path = [s]
        while came[path[-1]][0] is not None:
            path.append(came[path[-1]][0])
        path.reverse()
        return [(st // N, st % N) for st in path]

    def path_legal(self, W, path, endvia):
        blk, vok = W["blk"], W["vok"]
        prev = None
        for li, k in path:
            if blk[li][k] and not (vok[k] == 3 and prev is not None and prev[0] != li):
                if not (vok[k] == 3 and prev is None):
                    return False
            if prev is not None and prev[0] != li and not vok[k]:
                return False
            prev = (li, k)
        if endvia and not vok[path[-1][1]]:
            return False
        return True

    # ---- region-wide negotiation on the fine grid (exact clearance footprints)
    def negotiate3(self, reqs, iters=20, label="neg3"):
        """reqs: dict(net, code, src, tgt, tzones, width, win (x0, y0, x1, y1)). Returns ({i: (W, path, endvia)},
        bad list). Occupancy = clearance footprints of the other nets' current paths on the 0.05 mm grid; requests
        of one net are routed together (they never conflict with each other)."""
        from array import array
        GW = int(round((GX1 - GX0) / S)) + 2
        GH = int(round((GY1 - GY0) / S)) + 2
        NG = GW * GH
        occT = [array("i", bytes(4 * NG)) for _ in range(3)]
        occV = array("i", bytes(4 * NG))
        hist = [array("f", bytes(4 * NG)) for _ in range(3)]
        histV = array("f", bytes(4 * NG))

        def disc(rad):
            n = int(rad / S) + 1
            return [(di, dj) for di in range(-n, n + 1) for dj in range(-n, n + 1)
                    if math.hypot(di, dj) * S < rad - 1e-6]
        hw0 = 0.075
        st_TT = disc(2 * hw0 + CLR)                       # track centre vs track centre
        st_TV = disc(hw0 + CLR + VIA35[0] / 2)            # via centre vs track centre
        st_VT = {}                                         # via of size sz: blocks track centres
        st_VV = {}

        def vt(sz):
            if sz not in st_VT:
                st_VT[sz] = disc(sz / 2 + CLR + hw0)
                st_VV[sz] = disc(sz / 2 + CLR + VIA35[0] / 2)
            return st_VT[sz], st_VV[sz]
        data = []
        t0 = time.time()
        for q in reqs:
            x0, y0, x1, y1 = q["win"]
            gi0, gj0 = self.cell_of(max(x0, GX0), max(y0, GY0))
            gi1, gj1 = self.cell_of(min(x1, GX1), min(y1, GY1))
            W = self.build(q["code"], q["net"], (gi0, gj0, gi1, gj1), q["width"] / 2, True)
            st, _ = self.cells_of(W, q["src"], [], False, q["width"] / 2)
            tin = [it for it in q["tgt"] if it.bb[2] > x0 and it.bb[0] < x1 and it.bb[3] > y0 and it.bb[1] < y1]
            gl, vg = self.cells_of(W, tin, q.get("tzones", []), True, q["width"] / 2, q.get("near"))
            for li in range(3):
                for k in [k for k in gl[li] if W["blk"][li][k] and W["vok"][k] != 3]:
                    del gl[li][k]
            wn = W["wn"]
            allk = [k for li in range(3) for k in gl[li]] + list(vg)
            hb = (min(k % wn for k in allk), min(k // wn for k in allk), max(k % wn for k in allk),
                  max(k // wn for k in allk)) if allk else None
            data.append((W, st, gl, vg, hb))
        if DEBUG:
            print("   %s: %d requests prepared (%.0fs)" % (label, len(reqs), time.time() - t0))
        paths = [None] * len(reqs)
        foots = [None] * len(reqs)

        def gidx(W, k):
            return (W["win"][1] + k // W["wn"]) * GW + W["win"][0] + k % W["wn"]

        def footprint(i):
            W = data[i][0]
            path, ev = paths[i]
            cells = set()
            vcells = []
            prev = None
            for li, k in path:
                if prev is not None and prev[0] != li:
                    vcells.append(k)
                cells.add((li, gidx(W, k)))
                prev = (li, k)
            if ev:
                vcells.append(path[-1][1])
            ft = set()
            fv = set()
            for li, g_ in cells:
                gi, gj = g_ % GW, g_ // GW
                for di, dj in st_TT:
                    ft.add((li, (gj + dj) * GW + gi + di))
                for di, dj in st_TV:
                    fv.add((gj + dj) * GW + gi + di)
            for k in vcells:
                g_ = gidx(W, k)
                gi, gj = g_ % GW, g_ // GW
                sz = W["vsize"].get(k, VIA45 if W["vok"][k] == 1 else VIA35)[0]
                a_, b_ = vt(sz)
                for di, dj in a_:
                    c_ = (gj + dj) * GW + gi + di
                    ft.add((0, c_))
                    ft.add((1, c_))
                    ft.add((2, c_))
                for di, dj in b_:
                    fv.add((gj + dj) * GW + gi + di)
            return [x for x in ft if 0 <= x[1] < NG], [x for x in fv if 0 <= x < NG]

        def mark(i, sign):
            if foots[i] is None:
                return
            ft, fv = foots[i]
            for li, c_ in ft:
                occT[li][c_] += sign
            for c_ in fv:
                occV[c_] += sign

        dirs = [(1, 0, 1.0), (1, 1, 1.41421), (0, 1, 1.0), (-1, 1, 1.41421), (-1, 0, 1.0), (-1, -1, 1.41421),
                (0, -1, 1.0), (1, -1, 1.41421)]

        def search(i, pf):
            W, st, gl, vg, hb = data[i]
            wn, wm = W["wn"], W["wm"]
            N = wn * wm
            blk, vok = W["blk"], W["vok"]
            gi0, gj0 = W["win"][0], W["win"][1]
            if hb:
                hx0, hy0, hx1, hy1 = hb

                def h(k):
                    i_, j_ = k % wn, k // wn
                    dx = hx0 - i_ if i_ < hx0 else (i_ - hx1 if i_ > hx1 else 0)
                    dy = hy0 - j_ if j_ < hy0 else (j_ - hy1 if j_ > hy1 else 0)
                    return max(dx, dy) + 0.41421 * min(dx, dy)
            else:
                def h(k):
                    return 0.0
            g = {}
            came = {}
            openq = []
            for li in range(3):
                for k, c0 in st[li].items():
                    if blk[li][k] and vok[k] != 3:
                        continue
                    s_ = li * N + k
                    g[s_] = c0
                    came[s_] = (None, -1)
                    heapq.heappush(openq, (c0 + h(k), c0, s_))
            n_exp = 0
            while openq:
                f, gc, s_ = heapq.heappop(openq)
                if gc > g.get(s_, 1e18):
                    continue
                n_exp += 1
                if n_exp > 700000:
                    return None
                li, k = divmod(s_, N)
                if came[s_][0] is not None:
                    if k in gl[li]:
                        return self._unwind(came, s_, N), False
                    if k in vg and vok[k]:
                        return self._unwind(came, s_, N), True
                i_, j_ = k % wn, k // wn
                pd = came[s_][1]
                lc = LCOST[li]
                bl = blk[li]
                oT = occT[li]
                hT = hist[li]
                tm = () if bl[k] else (range(8) if pd < 0 else (pd, (pd + 1) % 8, (pd + 7) % 8))
                for d in tm:
                    di, dj, c = dirs[d]
                    ii, jj = i_ + di, j_ + dj
                    if ii < 0 or jj < 0 or ii >= wn or jj >= wm:
                        continue
                    k2 = jj * wn + ii
                    if bl[k2]:
                        continue
                    if di and dj and (bl[j_ * wn + ii] and bl[jj * wn + i_]):
                        continue
                    g_ = (gj0 + jj) * GW + gi0 + ii
                    ng = gc + c * lc * (1.0 + hT[g_]) * (1.0 + pf * oT[g_]) + \
                        (TURN_COST if (pd >= 0 and d != pd) else 0.0)
                    s2 = li * N + k2
                    if ng < g.get(s2, 1e18):
                        g[s2] = ng
                        came[s2] = (s_, d)
                        heapq.heappush(openq, (ng + h(k2), ng, s2))
                if vok[k]:
                    g_ = (gj0 + j_) * GW + gi0 + i_
                    ov = occV[g_] + occT[0][g_] + occT[1][g_] + occT[2][g_]
                    vc = VIA_COST * VTIER[vok[k]] * (1.0 + histV[g_]) * (1.0 + pf * ov)
                    for l2 in range(3):
                        if l2 == li or (blk[l2][k] and not (vok[k] == 3 and k in gl[l2])):
                            continue
                        s2 = l2 * N + k
                        ng = gc + vc
                        if ng < g.get(s2, 1e18):
                            g[s2] = ng
                            came[s2] = (s_, -1)
                            heapq.heappush(openq, (ng + h(k), ng, s2))
            return None

        by_net = defaultdict(list)
        for i, q in enumerate(reqs):
            by_net[q["code"]].append(i)
        pf = 0.5
        bad = [True] * len(reqs)
        hist_nb = []
        for it_n in range(iters):
            t1 = time.time()
            for code, idx in by_net.items():
                if it_n > 0 and not any(bad[i] or paths[i] is None for i in idx) and it_n % 4 != 0:
                    continue
                for i in idx:
                    mark(i, -1)
                for i in idx:
                    res = search(i, pf)
                    paths[i] = res
                    foots[i] = footprint(i) if res else None
                for i in idx:
                    mark(i, +1)
            bad = [False] * len(reqs)
            geo = [None if paths[i] is None else path_geom(data[i][0], paths[i][0], paths[i][1],
                                                         reqs[i]["width"]) for i in range(len(reqs))]
            for i in range(len(reqs)):
                if geo[i] is None:
                    continue
                for j in range(i + 1, len(reqs)):
                    if geo[j] is None or reqs[j]["code"] == reqs[i]["code"]:
                        continue
                    bi, bj = geo[i][2], geo[j][2]
                    if bi[2] < bj[0] - 0.6 or bj[2] < bi[0] - 0.6 or bi[3] < bj[1] - 0.6 or bj[3] < bi[1] - 0.6:
                        continue
                    hits = geom_conflicts(geo[i], geo[j])
                    if hits:
                        bad[i] = bad[j] = True
                        cells = set()
                        for (li, x_, y_) in hits[0] + hits[1]:
                            gi, gj = int(round((x_ - GX0) / S)), int(round((y_ - GY0) / S))
                            for di in (-1, 0, 1):
                                for dj in (-1, 0, 1):
                                    for l2 in ((li,) if li is not None else range(3)):
                                        cells.add((l2, (gj + dj) * GW + gi + di))
                        for l2, c_ in cells:
                            if 0 <= c_ < NG:
                                hist[l2][c_] += 0.5
                                histV[c_] += 0.2
            nb = sum(bad)
            if DEBUG:
                print("   %s iter %d: %d conflicting, %d unrouted, pf %.1f (%.0fs)" % (
                    label, it_n, nb, sum(p is None for p in paths), pf, time.time() - t1))
            if nb == 0:
                break
            hist_nb.append(nb)
            if len(hist_nb) > 8 and min(hist_nb[-8:]) >= min(hist_nb[:-8]):
                break
            pf *= 1.4
        if DEBUG:
            print("   %s: unrouted %s" % (label, " ".join(reqs[i].get("label", "?") for i in range(len(reqs))
                                                       if paths[i] is None)))
            print("   %s: conflicting %s" % (label, " ".join(reqs[i].get("label", "?") for i in range(len(reqs))
                                                          if bad[i])))
        return {i: (data[i][0], paths[i][0], paths[i][1]) for i in range(len(reqs))
                if paths[i] is not None}, bad

    # ---- emit
    def emit(self, W, net, code, path, endvia, width):
        wn = W["wn"]
        xw0, yw0 = W["xw0"], W["yw0"]
        vok, vsize = W["vok"], W["vsize"]
        new = []

        def xy(k):
            return (round(xw0 + (k % wn) * S, 4), round(yw0 + (k // wn) * S, 4))

        placed = set()

        def put_via(k):
            if k in placed:
                return
            placed.add(k)
            if k in vsize:
                sz, dr = vsize[k]
            elif vok[k] == 1:
                sz, dr = VIA45
            else:
                sz, dr = VIA35
            x, y = xy(k)
            self.r.via(net, x, y, sz, dr)
            it = via_item(net, code, x, y, sz, dr)
            self.add(it)
            new.append(it)
            self.stats["via %.2f" % sz] += 1

        runs = []
        cur = [path[0]]
        for st in path[1:]:
            if st[0] != cur[-1][0]:
                runs.append(cur)
                put_via(st[1])
                cur = [st]
            else:
                cur.append(st)
        runs.append(cur)
        for run in runs:
            if len(run) < 2:
                continue
            li = run[0][0]
            pts = [xy(run[0][1])]
            lastd = None
            for a, b in zip(run, run[1:]):
                pa, pb = xy(a[1]), xy(b[1])
                d = (round((pb[0] - pa[0]) / S), round((pb[1] - pa[1]) / S))
                if d == lastd:
                    pts[-1] = pb
                else:
                    pts.append(pb)
                lastd = d
            self.r.track(net, pts, RLN[li], width)
            for (ax, ay), (bx, by) in zip(pts, pts[1:]):
                it = track_item(net, code, RL[li], ax, ay, bx, by, width, False)
                self.add(it)
                new.append(it)
            self.stats["track mm"] += sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))
        if endvia:
            put_via(path[-1][1])
        return new

    # ---- one connection
    def connect(self, net, code, src_items, tgt_items, tgt_zones, widths, wins, goal_fn=None, endvia_any=False,
                label="", near=None):
        """Route from the source copper to any target copper (or to cells accepted by goal_fn), inside the window
        bboxes `wins` (tried in order). Tries widths in order, first with 0.45 vias only, then with the 0.35
        fallback. Returns (new items, path) or None."""
        for (ax0, ay0, ax1, ay1) in wins:
            gi0, gj0 = self.cell_of(max(ax0, GX0), max(ay0, GY0))
            gi1, gj1 = self.cell_of(min(ax1, GX1), min(ay1, GY1))
            win = (gi0, gj0, gi1, gj1)
            for fallback in (False, True):
                for w in widths:
                    t0 = time.time()
                    W = self.build(code, net, win, w / 2, fallback)
                    st, _ = self.cells_of(W, src_items, [], False, w / 2)
                    if goal_fn is not None:
                        gl, vg = goal_fn(W)
                    else:
                        tin = [it for it in tgt_items if it.bb[2] > ax0 and it.bb[0] < ax1 and it.bb[3] > ay0 and
                               it.bb[1] < ay1]
                        gl, vg = self.cells_of(W, tin, tgt_zones, True, w / 2, near)
                    for li in range(3):      # goal cells must be free
                        for k in [k for k in gl[li] if W["blk"][li][k] and W["vok"][k] != 3]:
                            del gl[li][k]
                    if not any(gl) and not vg:
                        continue
                    hb = None
                    allk = [k for li in range(3) for k in gl[li]]
                    if allk and not vg:
                        wn_ = W["wn"]
                        hb = (min(k % wn_ for k in allk), min(k // wn_ for k in allk), max(k % wn_ for k in allk),
                              max(k // wn_ for k in allk))
                    res = self.astar(W, st, gl, vg, hb)
                    if DEBUG:
                        print("   %s %s w%.2f win%.1fx%.1f fb%d -> %s (%.1fs)" % (
                            label, net, w, ax1 - ax0, ay1 - ay0, fallback, "ok" if res else "FAIL", time.time() - t0))
                    if res:
                        path, endvia = res
                        if endvia_any and not endvia:
                            endvia = bool(W["vok"][path[-1][1]])
                        return self.emit(W, net, code, path, endvia, w), path
        return None


# ------------------------------------------------------------------------------------------------ clusters
def clusters_of(board, conn, net_code, pads_by_code):
    """Copper clusters (lists of BOARD_CONNECTED_ITEM) of a net, seeded from its pads."""
    seen = set()
    out = []
    for p in pads_by_code[net_code]:
        u = p.m_Uuid.AsString()
        if u in seen:
            continue
        items = list(conn.GetConnectedItems(p)) + [p]
        uu = set()
        cl = []
        for it in items:
            if it.GetNetCode() != net_code:
                continue
            q = it.m_Uuid.AsString()
            if q in uu:
                continue
            uu.add(q)
            cl.append(it)
        seen |= uu
        out.append((uu, cl))
    return out


def bb_union(items, m=0.0):
    return (min(it.bb[0] for it in items) - m, min(it.bb[1] for it in items) - m,
            max(it.bb[2] for it in items) + m, max(it.bb[3] for it in items) + m)


def grow(bb, m):
    return (bb[0] - m, bb[1] - m, bb[2] + m, bb[3] + m)


def route(board, r):
    t0 = time.time()
    ctx = Ctx(board, r)
    to_fill = [z for z in board.Zones() if not z.GetIsRuleArea() and z.GetZoneName() not in OUTER_GND_POURS]
    for z in board.Zones():
        if z.GetZoneName() in OUTER_GND_POURS:
            z.UnFill()          # removed for the autorouter: never count on them
    pcbnew.ZONE_FILLER(board).Fill(to_fill)
    board.BuildConnectivity()
    conn = board.GetConnectivity()
    ctx.load()
    by_uid = defaultdict(list)
    for it in ctx.items:
        if it.uid:
            by_uid[it.uid].append(it)
    pads_by_code = defaultdict(list)
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetNetCode() > 0:
                pads_by_code[p.GetNetCode()].append(p)
    code2name = {ni.GetNetCode(): str(k) for k, ni in board.GetNetsByName().items()}

    import json
    part = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build", "partition.json")
    local, inter = [], []
    try:
        pj = json.load(open(part))
        local = [x["net"] for x in pj["local"].get("usbc", [])]
        inter = [x["net"] for x in pj["interblock"] if "usbc" in x["regions"]]
    except Exception as e:
        print("g_usbc: no partition.json (%s)" % e)
    local_short = set(short(n) for n in local)
    inter_short = set(short(n) for n in inter)

    class Net:
        pass
    nets = {}

    def get_net(name):
        ni = board.FindNet(name)
        if ni is None:
            return None
        code = ni.GetNetCode()
        if code in nets:
            return nets[code]
        n = Net()
        n.name, n.code, n.short = ni.GetNetname(), code, short(ni.GetNetname())
        n.clusters = []
        for uu, cl in clusters_of(board, conn, code, pads_by_code):
            its, zs, pds = [], [], []
            for bi in cl:
                if bi.GetClass() == "ZONE":
                    if bi.GetZoneName() not in OUTER_GND_POURS:
                        zs.append(bi)
                    continue
                for it in by_uid.get(bi.m_Uuid.AsString(), ()):
                    its.append(it)
                    if it.kind == "pad":
                        pds.append(it)
            n.clusters.append(dict(items=its, zones=zs, pads=pds, plane=bool(zs)))
        nets[code] = n
        return n

    def merge(n, a, b):
        if a > b:
            a, b = b, a
        ca, cb = n.clusters[a], n.clusters[b]
        ca["items"] += cb["items"]
        ca["zones"] += cb["zones"]
        ca["pads"] += cb["pads"]
        ca["plane"] = ca["plane"] or cb["plane"]
        del n.clusters[b]
        return a

    def touches(new, c):
        """Does any new item (track end point / via) land on the copper of cluster c?"""
        pts = []
        for it in new:
            if it.kind == "via":
                pts.append((it.cx, it.cy, None))
            else:
                ax, ay, bx, by = it.pts
                lay = next(iter(it.layers))
                pts.append((ax, ay, lay))
                pts.append((bx, by, lay))
        for x, y, lay in pts:
            for it in c["items"]:
                if not (it.bb[0] - 0.3 <= x <= it.bb[2] + 0.3 and it.bb[1] - 0.3 <= y <= it.bb[3] + 0.3):
                    continue
                if lay is not None and lay not in it.layers and it.kind != "via":
                    continue
                if lay is None and not (it.layers & set(RL)):
                    continue
                if it.dist(x, y) < -0.005:
                    return True
            for z in c["zones"]:
                for l2 in z.GetLayerSet().Seq():
                    if lay is None or l2 == lay:
                        f = z.GetFilledPolysList(l2)
                        if f.OutlineCount() and f.Contains(pcbnew.VECTOR2I(mm(x), mm(y))):
                            return True
        return False

    def absorb(n, ci, new):
        """Merge every cluster touched by the new copper into cluster ci; returns ci's new index."""
        n.clusters[ci]["items"] += new
        changed = True
        while changed:
            changed = False
            for j in range(len(n.clusters)):
                if j != ci and touches(new, n.clusters[j]):
                    ci = merge(n, ci, j)
                    changed = True
                    break
        return ci

    def nearest_item(src, items):
        best, bd = None, 1e9
        sx = [(p.cx, p.cy) if p.kind != "trk" else ((p.bb[0] + p.bb[2]) / 2, (p.bb[1] + p.bb[3]) / 2)
              for p in src[:80]]
        for it in items:
            cx, cy = (it.bb[0] + it.bb[2]) / 2, (it.bb[1] + it.bb[3]) / 2
            d = min(math.hypot(cx - x, cy - y) for x, y in sx)
            if d < bd:
                best, bd = it, d
        return best, bd

    def link(n, src_ci, widths, label, supply=False, to=None):
        src = n.clusters[src_ci]
        tg = [i for i in range(len(n.clusters)) if i != src_ci and (to is None or i == to)]
        titems = [it for i in tg for it in n.clusters[i]["items"]]
        tzones = [z for i in tg for z in n.clusters[i]["zones"]]
        sbb = bb_union(src["items"])
        if supply and n.short != "+5V":
            # big shared nets: only same-net copper near the stray (and the planes) are targets
            fb = grow(sbb, 6.0)
            titems = [it for it in titems if it.bb[2] > fb[0] and it.bb[0] < fb[2] and it.bb[3] > fb[1] and
                      it.bb[1] < fb[3]]
        near, _ = nearest_item(src["items"], [it for it in titems if it.kind != "zone"])
        wins = []
        if supply:
            wins += [grow(sbb, 2.5), grow(sbb, 5.0)]
        if near is not None:
            ub = (min(sbb[0], near.bb[0]), min(sbb[1], near.bb[1]), max(sbb[2], near.bb[2]), max(sbb[3], near.bb[3]))
            if not supply or n.short == "+5V" or max(ub[2] - ub[0], ub[3] - ub[1]) < 12:
                wins += [grow(ub, 1.5), grow(ub, 4.0)]
        if supply and n.short == "+5V":
            wins.append(grow(sbb, 26.0))      # PMG1 VCONN feed: no +5V copper near the BGA
        res = ctx.connect(n.short, n.code, src["items"], titems, tzones, widths, wins, label=label,
                          near=grow(sbb, 2.5) if supply else grow(sbb, 4.0))
        if res is None:
            return None
        new, path = res
        return absorb(n, src_ci, new)

    def region_pads(c):
        return [p for p in c["pads"] if in_region(p.cx, p.cy)]

    def report_fail(net, what):
        ctx.fail.append("%s: %s" % (net, what))
        print("  g_usbc FAIL %s: %s" % (net, what))

    # ---------------------------------------------------------------- (A) BGA escapes
    bx0, by0, bx1, by1 = BGA_FIELD
    ex0, ey0, ex1, ey1 = bx0 - BGA_OUT, by0 - BGA_OUT, bx1 + BGA_OUT, by1 + BGA_OUT

    def outside_field(it):
        cx, cy = (it.bb[0] + it.bb[2]) / 2, (it.bb[1] + it.bb[3]) / 2
        return not (ex0 < cx < ex1 and ey0 < cy < ey1)

    # same-net neighbour balls: join them on L1 first (saves vias in the ball field)
    bga_balls = [it for it in ctx.items if it.kind == "pad" and it.ref == BGA_REF and it.code > 0 and
                 it.net != "GND"]
    if "A" in PHASES:
        for i1, p in enumerate(bga_balls):
            for q in bga_balls[i1 + 1:]:
                if p.code != q.code or math.hypot(p.cx - q.cx, p.cy - q.cy) > 0.95:
                    continue
                n = get_net(code2name[p.code])
                ca = next(i for i, c in enumerate(n.clusters) if any(x is p for x in c["pads"]))
                cb = next(i for i, c in enumerate(n.clusters) if any(x is q for x in c["pads"]))
                if ca == cb:
                    continue
                if not ctx.segment_legal(p.code, p.net, (p.cx, p.cy), (q.cx, q.cy), 0.15, pcbnew.F_Cu):
                    continue
                r.track(n.short, [(p.cx, p.cy), (q.cx, q.cy)], "F.Cu", 0.15)
                it = track_item(n.short, p.code, pcbnew.F_Cu, p.cx, p.cy, q.cx, q.cy, 0.15, False)
                ctx.add(it)
                absorb(n, ca, [it])
                ctx.stats["BGA L1 joins"] += 1
    todo_balls = []
    for it in ctx.items:
        if it.kind != "pad" or it.ref != BGA_REF or it.code <= 0:
            continue
        n = get_net(code2name[it.code])
        if n is None or n.short == "GND":
            continue
        if n.short not in local_short and n.short not in inter_short:
            continue
        ci = next(i for i, c in enumerate(n.clusters) if any(p is it for p in c["pads"]))
        c = n.clusters[ci]
        if len(n.clusters) == 1 and n.short not in inter_short:
            continue
        if c["plane"] or any(outside_field(it2) for it2 in c["items"]):
            continue
        todo_balls.append((it, n))
    if "A" not in PHASES:
        todo_balls = []
    # one request per ball (balls of the same net already joined count as one)
    reqs = []
    outer = set()
    for it in ctx.items:
        if it.kind == "pad" and it.ref == BGA_REF and (abs(it.cx - bx0) < 0.01 or abs(it.cx - bx1) < 0.01 or
                                                        abs(it.cy - by0) < 0.01 or abs(it.cy - by1) < 0.01):
            outer.add(ctx.cell_of(it.cx, it.cy))
    win = ctx.cell_of(ex0 - 2.2, ey0 - 1.5) + ctx.cell_of(ex1 + 2.2, ey1 + 2.2)
    seen_cl = set()
    wn_f, wm_f = win[2] - win[0] + 1, win[3] - win[1] + 1
    fmask = bytearray(wn_f * wm_f)
    for j in range(wm_f):
        for i in range(wn_f):
            x, y = GX0 + (win[0] + i) * S, GY0 + (win[1] + j) * S
            if bx0 - 0.3 < x < bx1 + 0.3 and by0 - 0.3 < y < by1 + 0.3:
                fmask[j * wn_f + i] = 1
    for ball, n in todo_balls:
        ci = next(i for i, c in enumerate(n.clusters) if any(p is ball for p in c["pads"]))
        c = n.clusters[ci]
        if id(c) in seen_cl:
            continue
        seen_cl.add(id(c))
        is_inter = n.short not in local_short and n.short not in SUPPLY_W
        # where is this net going?
        if n.short in EXIT_HINT:
            T = EXIT_HINT[n.short]
        else:
            others = [p for i2, c2 in enumerate(n.clusters) if i2 != ci for p in c2["pads"] if p.ref != BGA_REF]
            if not others:
                others = [p for i2, c2 in enumerate(n.clusters) if i2 != ci for p in c2["pads"]]
            T = min(((p.cx, p.cy) for p in others), key=lambda q: math.hypot(q[0] - ball.cx, q[1] - ball.cy)) \
                if others else (161.0, 70.0)
        tx, ty = T[0] - ball.cx, T[1] - ball.cy

        ring1 = abs(ball.cx - bx0) < 0.01 or abs(ball.cx - bx1) < 0.01 or abs(ball.cy - by0) < 0.01 or \
            abs(ball.cy - by1) < 0.01
        if ring1 and (not is_inter or abs(ball.cy - by0) < 0.01 or abs(ball.cy - by1) < 0.01):
            continue            # outer balls reach L1 directly: routed with their net in phase B / Freerouting

        def goal_fn(W, n=n, ball=ball, via_end=ring1, T=T):
            ci = next(j for j, c in enumerate(n.clusters) if any(p is ball for p in c["pads"]))
            gi0_, gj0_, gi1_, gj1_ = W["win"]
            wn_, wm_ = W["wn"], W["wm"]
            gl = [dict(), dict(), dict()]
            vg = dict()
            vx0, vy0, vx1, vy1 = bx0 - 0.35, by0 - 0.35, bx1 + 0.35, by1 + 0.35
            for j in range(wm_):
                y = GY0 + (gj0_ + j) * S
                for i in range(wn_):
                    x = GX0 + (gi0_ + i) * S
                    k = j * wn_ + i
                    tc = ESC_PULL * math.hypot(x - T[0], y - T[1]) / S
                    if via_end:
                        if not (vx0 < x < vx1 and vy0 < y < vy1) and W["vok"][k] in (1, 2):
                            vg[k] = tc
                        continue
                    if ex0 < x < ex1 and ey0 < y < ey1:
                        continue
                    for li in range(3):
                        if not W["blk"][li][k]:
                            gl[li][k] = tc
            others = [it2 for i2, c2 in enumerate(n.clusters) if i2 != ci for it2 in c2["items"]]
            g2, v2 = ctx.cells_of(W, others, [c3 for i2, c2 in enumerate(n.clusters) if i2 != ci
                                              for c3 in c2["zones"]], True)
            for li in range(3):
                gl[li].update(g2[li])
            for k in v2:
                vg[k] = 0.0
            return gl, vg
        vm = {}
        gi0, gj0 = win[0], win[1]
        wn_ = win[2] - win[0] + 1
        for (gi, gj) in outer:
            vm[(gj - gj0) * wn_ + (gi - gi0)] = 3.0
        reqs.append(dict(net=n.short, code=n.code, src=c["items"], width=0.15, goal_fn=goal_fn, endvia=False,
                         vip_mult=vm, n=n, ball=ball, label=ball.num, field_mask=fmask,
                         layers=(0,) if ring1 else (1, 2), force_via=not ring1, ring1=ring1))
    print("g_usbc: %d BGA escape requests" % len(reqs))
    if reqs:
        res = ctx.negotiate(reqs, win, iters=30, label="bga")
        # second chance for the failures: any layer, vias anywhere
        retry = [q for i, q in enumerate(reqs) if i not in res]
        for i, q in enumerate(reqs):
            n = q["n"]
            ci = next(j for j, c in enumerate(n.clusters) if any(p is q["ball"] for p in c["pads"]))
            if i in res:
                absorb(n, ci, res[i])
                ctx.stats["BGA escapes"] += 1
        for q in retry:
            q["layers"], q["force_via"] = (0, 1, 2), False
            n = q["n"]
            ci = next(j for j, c in enumerate(n.clusters) if any(p is q["ball"] for p in c["pads"]))
            q["src"] = n.clusters[ci]["items"]
        res2 = ctx.negotiate(retry, win, iters=12, label="bga2") if retry else {}
        for i, q in enumerate(retry):
            n = q["n"]
            ci = next(j for j, c in enumerate(n.clusters) if any(p is q["ball"] for p in c["pads"]))
            if i in res2:
                absorb(n, ci, res2[i])
                ctx.stats["BGA escapes"] += 1
            else:
                report_fail(n.short, "BGA escape of %s.%s" % (BGA_REF, q["label"]))
    print("g_usbc: BGA escapes done (%.0fs)" % (time.time() - t0))

    # ---------------------------------------------------------------- (B) local nets
    lnets = [n for n in (get_net(nm) for nm in local) if n is not None]

    def est_len(n):
        cs = [c for c in n.clusters if c["pads"]]
        tot = 0.0
        for c in cs[1:]:
            tot += min(math.hypot(p.cx - q.cx, p.cy - q.cy) for p in c["pads"] for q in cs[0]["pads"])
        return tot
    order = sorted([n for n in lnets if n.short not in SUPPLY_W], key=est_len) + \
        [n for n in lnets if n.short in SUPPLY_W]
    if "B" not in PHASES:
        order = []
    # MST of the clusters of every local net -> two-point requests, negotiated together
    reqs = []
    for n in order:
        cl = n.clusters
        if len(cl) < 2:
            continue
        widths = SUPPLY_W.get(n.short, (0.15,))

        def reps(c):
            return [p for p in c["pads"]] or c["items"]
        inside = {0}
        edges = []
        while len(inside) < len(cl):
            best = None
            for a_ in inside:
                for b_ in range(len(cl)):
                    if b_ in inside:
                        continue
                    for p in reps(cl[a_])[:80]:
                        for q in reps(cl[b_])[:80]:
                            d = math.hypot(p.cx - q.cx, p.cy - q.cy)
                            if best is None or d < best[0]:
                                best = (d, a_, b_, p, q)
            d, a_, b_, p, q = best
            inside.add(b_)
            edges.append((a_, b_, p, q))
        for a_, b_, p, q in edges:
            # route from the smaller cluster
            if len(cl[a_]["items"]) > len(cl[b_]["items"]):
                a_, b_, p, q = b_, a_, q, p
            m = 2.5 + 0.15 * math.hypot(p.cx - q.cx, p.cy - q.cy)
            win = (min(p.cx, q.cx) - m, min(p.cy, q.cy) - m, max(p.cx, q.cx) + m, max(p.cy, q.cy) + m)
            reqs.append(dict(net=n.short, code=n.code, src=cl[a_]["items"], tgt=cl[b_]["items"],
                             tzones=cl[b_]["zones"], width=widths[-1] if len(widths) == 1 else widths[0],
                             win=win, n=n, p=p, q=q, label="%s.%s-%s.%s" % (p.ref, p.num, q.ref, q.num)))
    # supply strays of the plane nets compete in the same negotiation (target: same-net copper nearby or a plane via)
    if "C" in PHASES and "B" in PHASES:
        for nm in NEG_SUPPLY:
            ni = board.FindNet(nm)
            if ni is None:
                continue
            n = get_net(ni.GetNetname())
            mains = [i for i, c in enumerate(n.clusters) if c["plane"]]
            if not mains:
                continue
            main = n.clusters[mains[0]]
            for ci, c in enumerate(n.clusters):
                if c["plane"] or not region_pads(c):
                    continue
                sbb = bb_union(c["items"])
                fb = grow(sbb, 5.0)
                tg = [it for it in main["items"] if it.bb[2] > fb[0] and it.bb[0] < fb[2] and it.bb[3] > fb[1] and
                      it.bb[1] < fb[3]]
                p = region_pads(c)[0]
                reqs.append(dict(net=n.short, code=n.code, src=c["items"], tgt=tg, tzones=main["zones"],
                                 width=SUPPLY_W.get(n.short, (0.2,))[0], win=grow(sbb, 3.0), near=grow(sbb, 2.5),
                                 n=n, p=p, q=None, supply=True, label="%s.%s>%s" % (p.ref, p.num, n.short)))
    if reqs:
        res, bad = ctx.negotiate3(reqs, iters=NEG_ITERS, label="loc")
        # emit in order of length: re-check each path against what was emitted before it
        todo = sorted(range(len(reqs)), key=lambda i: len(res[i][1]) if i in res else 1e9)
        for i in todo:
            q = reqs[i]
            n = q["n"]
            ci = next(j for j, c in enumerate(n.clusters) if any(x is q["p"] for x in c["pads"]))
            if q.get("supply"):
                if n.clusters[ci]["plane"]:
                    continue
                if i in res and not bad[i]:
                    W0, path, ev = res[i]
                    W2 = ctx.build(q["code"], q["net"], W0["win"], q["width"] / 2, True)
                    if ctx.path_legal(W2, path, ev):
                        new = ctx.emit(W2, q["net"], q["code"], path, ev, q["width"])
                        ctx.stats["negotiated supply links"] += 1
                        absorb(n, ci, new)
                        if ev and not n.clusters[next(j for j, c in enumerate(n.clusters)
                                                      if any(x is q["p"] for x in c["pads"]))]["plane"]:
                            # the via landed in the plane: mark the cluster as tied
                            cj2 = next(j for j, c in enumerate(n.clusters) if any(x is q["p"] for x in c["pads"]))
                            n.clusters[cj2]["plane"] = True
                continue        # failures: handled by phase C
            cj = next(j for j, c in enumerate(n.clusters) if any(x is q["q"] for x in c["pads"]))
            if ci == cj:
                continue
            new = None
            if i in res and not bad[i]:
                W0, path, ev = res[i]
                W2 = ctx.build(q["code"], q["net"], W0["win"], q["width"] / 2, True)
                if ctx.path_legal(W2, path, ev):
                    new = ctx.emit(W2, q["net"], q["code"], path, ev, q["width"])
                    ctx.stats["negotiated links"] += 1
            if new is None:
                got = link(n, ci, SUPPLY_W.get(n.short, (0.15,)) + NECK, "loc", to=cj)
                if got is not None:
                    ctx.stats["greedy links"] += 1
                continue
            absorb(n, ci, new)
    # whatever is still split: greedy, closest clusters first
    for n in order:
        widths = SUPPLY_W.get(n.short, (0.15,))
        guard = 0
        while len(n.clusters) > 1 and guard < 40:
            guard += 1
            best = None
            for a in range(len(n.clusters)):
                for b in range(a + 1, len(n.clusters)):
                    pa = n.clusters[a]["pads"] or n.clusters[a]["items"]
                    pb = n.clusters[b]["pads"] or n.clusters[b]["items"]
                    d = min(math.hypot(p.cx - q.cx, p.cy - q.cy) for p in pa[:60] for q in pb[:60])
                    sa, sb = len(n.clusters[a]["items"]), len(n.clusters[b]["items"])
                    src = a if sa <= sb else b
                    if n.clusters[src]["plane"]:
                        src = b if src == a else a
                    if best is None or d < best[0]:
                        best = (d, src)
            src = best[1]
            got = link(n, src, widths + NECK, "loc")
            if got is None:
                pads = region_pads(n.clusters[src])
                report_fail(n.short, "cluster %s" % " ".join("%s.%s" % (p.ref, p.num) for p in pads[:6]))
                del n.clusters[src]
                continue
            ctx.stats["greedy links"] += 1
    print("g_usbc: local nets done (%.0fs)" % (time.time() - t0))

    # ---------------------------------------------------------------- (C) supply / shared nets in the region
    for nm in (("+5V", "PMG1_VDDD", "+3V3", "GND", "VBUS_DS", "VBUS_LAPTOP") if "C" in PHASES else ()):
        ni = board.FindNet(nm)
        if ni is None:
            continue
        n = get_net(ni.GetNetname())
        widths = SUPPLY_W.get(n.short, (0.2, 0.15))
        dead = set()
        guard = 0
        while guard < 80:
            guard += 1
            mains = [i for i, c in enumerate(n.clusters) if c["plane"]]
            if not mains:
                mains = [max(range(len(n.clusters)), key=lambda i: len(n.clusters[i]["items"]))]
            strays = [i for i, c in enumerate(n.clusters) if i not in mains and region_pads(c) and
                      id(c) not in dead]
            if not strays:
                break
            si = strays[0]
            got = link(n, si, widths, "sup", supply=True)
            if got is None:
                pads = region_pads(n.clusters[si])
                report_fail(n.short, "pads %s" % " ".join("%s.%s" % (p.ref, p.num) for p in pads[:6]))
                dead.add(id(n.clusters[si]))
                continue
            ctx.stats["supply links"] += 1
    print("g_usbc: supply drops done (%.0fs)" % (time.time() - t0))

    for z in to_fill:
        z.UnFill()
    print("g_usbc: %s; %d failures; %.0fs" % (", ".join("%s %s" % (k, ("%.0f" % v) if isinstance(v, float) else v)
                                                        for k, v in sorted(ctx.stats.items())),
                                              len(ctx.fail), time.time() - t0))
    for f in ctx.fail:
        print("   fail:", f)
