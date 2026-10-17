"""odock-10 region routing, phase g: power block (Power input + Laptop power out), region (100,50)-(138,108).

Routes every still-unrouted connection of the nets LOCAL to the power region (all pads inside it; list in
build/partition.json "local"/"power") after a_planes .. f_fanout, and ties the unconnected pads of the shared supply
nets inside the region (GND, VIN, VBUS_LAPTOP, VBUS_LSW, +5V to their existing copper / planes; the isolated +3V3
pads into one local tree). Signal nets that leave the region (I2C, VBB_*, LAPTOP_*, PG_5V, ...) are left to
Freerouting.

How: a small maze router on a 0.05 mm grid over the region (L1 F.Cu, L3 In2.Cu, L6 B.Cu, through vias 0.45/0.25).
Obstacles are rasterised from the real board copper (pads of every layer, tracks, vias, filled pours on the routing
layers except the general GND_L1/GND_L6 pours, rule areas incl. the switch-node keep-outs on L3) inflated by
half-width + clearance (0.15 mm, 0.3 mm across the HV boundary except the HV-rated fine-pitch parts exempted by the
.kicad_dru "high voltage" rule). Each grid cell remembers the net that blocks it, so same-net copper is free. A
connection is a multi-source A* from one copper cluster of a net to the already-connected cluster(s) (or, for plane
nets, to a via spot inside the net's inner-layer fill). Paths are 8-direction (45 deg), 90 deg corners chamfered.
- Other-net power pours may get a shallow notch (<= NOTCH deep, only where the pour is >= 2*NOTCH wide, high cost);
  never a via inside them, never through switch-node / hot-loop copper.
- Fine-pitch IC pins get a reserved straight escape for their own net (reserve_escapes), so neither local nor
  interblock pins are boxed in by other routes.
- Last resort per connection: a 0.35/0.15 via, which may sit inside the pad (filled + capped, the process the U401
  BGA fan-out already needs), never in D101/D102.
- Nets are routed in PRIORITY order, then the rest by pad count; a second pass with fresh connectivity retries.
Env (debug): G_ONLY=net,net  G_ITER=n (re-runs with failed nets first, prints the best order)  G_DEBUG=dir.
NETS = [] / GROUPED: everything drawn goes into group "route:g_power", which apply_routing.py replaces on re-run.
Notes: docs/routing-notes/g_power.md.
"""
import os
import sys
import math
import heapq
from array import array
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew  # noqa: E402
import _pwrlib as L  # noqa: E402

NETS = []
GROUPED = True

mm, MM = pcbnew.FromMM, pcbnew.ToMM

# ---------------------------------------------------------------------------------------------- parameters
REGION = [(100.0, 50.0, 138.0, 108.0), (100.0, 49.5, 138.0, 64.0)]
X0, Y0, X1, Y1 = 99.5, 49.5, 138.6, 108.6       # raster bounds
CU_X0, CU_Y0, CU_X1, CU_Y1 = 100.3, 50.3, 138.3, 108.3   # copper must stay inside (board edge 0.3 / region + 0.3)
S = 0.05                                         # grid step
CLR = 0.15 + 0.02                                # DRC 0.15 + raster margin
HVCLR = 0.30 + 0.02
HOLE_CLR = 0.20 + 0.02
VIA = (0.45, 0.25)
VR = VIA[0] / 2
NO_VIP_REFS = {"D101", "D102"}
VIA_SMALL = (0.35, 0.15)      # last resort only (brief: 0.35/0.15 where unavoidable)
LAYERS = (pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)
LNAME = ("F.Cu", "In2.Cu", "B.Cu")
ALL6 = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu)
INNER_PLANES = (pcbnew.In1_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu)
HARD_POUR_NETS = {"BB_SW1", "BB_SW2", "BB_LS", "5V_SW"}   # switch-node copper: never cut
SKIP_ZONES = {"GND_L1", "GND_L6"}                # dropped for the autorouter, re-added later: neither obstacle nor tie
HV_EXEMPT_PREFIX = ("U10", "U20", "Q20")
HV_EXEMPT_REFS = {"J101", "J501"}
VIA_COST = 50.0          # in grid steps (2.5 mm of track)
LAYER_COST = (1.0, 1.25, 1.0)
NOTCH = 0.7              # max depth of a notch cut into an other-net pour (only where the pour is >= 1.4 mm wide)
SOFT_COST = 8.0          # per step inside an other-net pour (the pour gets a notch)
TURN_COST = {0: 0.0, 1: 0.4, 2: 2.0, 3: 12.0, 4: 1e9}
MAXERR = mm(0.003)

# Net widths (bare names). Everything else 0.15 mm.
WIDE = {"+3V3": 0.2, "PD_LDO_3V3": 0.2, "BB_VCC": 0.25, "BB_BIAS": 0.25, "PD_LDO_1V5": 0.2, "SNK_VCAP": 0.2,
        "VIN": 0.25, "VBUS_LAPTOP": 0.25, "VBUS_LSW": 0.25, "+5V": 0.3, "GND": 0.25,
        "VBAR": 0.2, "VBB_OUT": 0.2, "VBUS_PDIN": 0.2, "VIN_OR": 0.2}
# not routed here: the BB_SW1 switch node is split in b_power's P_BB_SW1 fill (Q201 gate pad cuts the pour at
# x 107.1-108.1); a 0.15 mm track would hide that, b_power must bridge the pour (see docs/routing-notes/g_power.md)
SKIP_NETS = {"BB_SW1"}
# shared supply nets whose unconnected pads inside the region are tied to the existing copper / planes
SUPPLY = ["GND", "VIN", "VBUS_LAPTOP", "VBUS_LSW", "+5V"]
# isolated +3V3 pads of the region: joined into one local tree (the feed from the usbc / right blocks is left to
# the autorouter, which then only needs one connection into the region)
LOCAL_TREE = ["+3V3"]


def short(n):
    return str(n).split("/")[-1]


def in_region(x, y):
    return any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in REGION)


# ---------------------------------------------------------------------------------------------- raster helpers
W = int(round((X1 - X0) / S)) + 1
H = int(round((Y1 - Y0) / S)) + 1
N = W * H


def rings_of(sps):
    """SHAPE_POLY_SET -> list of rings [(x, y), ...] in mm (outlines and holes; even-odd fill)."""
    out = []
    for i in range(sps.OutlineCount()):
        chains = [sps.Outline(i)] + [sps.Hole(i, h) for h in range(sps.HoleCount(i))]
        for ch in chains:
            n = ch.PointCount()
            pts = []
            for k in range(n):
                p = ch.CPoint(k)
                pts.append((p.x / 1e6, p.y / 1e6))
            if len(pts) >= 3:
                out.append(pts)
    return out


def spans(rings, i0=0, j0=0, i1=W - 1, j1=H - 1):
    """Yield (j, ia, ib) grid spans (inclusive) whose cell centres are inside the rings (even-odd)."""
    rows = defaultdict(list)
    for ring in rings:
        n = len(ring)
        for k in range(n):
            xa, ya = ring[k]
            xb, yb = ring[(k + 1) % n]
            if ya == yb:
                continue
            lo, hi = (ya, yb) if ya < yb else (yb, ya)
            ja = max(j0, int(math.ceil((lo - Y0) / S - 1e-9)))
            jb = min(j1, int(math.ceil((hi - Y0) / S - 1e-9)) - 1)
            if ja > jb:
                continue
            dx = (xb - xa) / (yb - ya)
            for j in range(ja, jb + 1):
                y = Y0 + j * S
                rows[j].append(xa + (y - ya) * dx)
    for j, xs in rows.items():
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            ia = max(i0, int(math.ceil((xs[k] - X0) / S - 1e-9)))
            ib = min(i1, int(math.floor((xs[k + 1] - X0) / S + 1e-9)))
            if ia <= ib:
                yield j, ia, ib


def circle_rings(x, y, r, n=24):
    r = r / math.cos(math.pi / n)      # circumscribed polygon (errs outside)
    return [[(x + r * math.cos(2 * math.pi * k / n), y + r * math.sin(2 * math.pi * k / n)) for k in range(n)]]


def capsule_rings(a, b, r, n=12):
    """Segment a-b inflated by r (polygon errs outside)."""
    r = r / math.cos(math.pi / (2 * n))
    dx, dy = b[0] - a[0], b[1] - a[1]
    ang = math.atan2(dy, dx)
    pts = []
    for k in range(n + 1):
        t = ang + math.pi / 2 + math.pi * k / n
        pts.append((a[0] + r * math.cos(t), a[1] + r * math.sin(t)))
    for k in range(n + 1):
        t = ang - math.pi / 2 + math.pi * k / n
        pts.append((b[0] + r * math.cos(t), b[1] + r * math.sin(t)))
    return [pts]


def mark(arr, rings, owner):
    for j, ia, ib in spans(rings):
        base = j * W
        for k in range(base + ia, base + ib + 1):
            v = arr[k]
            if v == 0:
                arr[k] = owner
            elif v != owner:
                arr[k] = -1


def mark_hard(arr, rings):
    for j, ia, ib in spans(rings):
        base = j * W
        for k in range(base + ia, base + ib + 1):
            arr[k] = -1


# ---------------------------------------------------------------------------------------------- obstacles
class Item:
    """One piece of copper (pad / track / via / zone fill) with what is needed to rasterise it."""
    __slots__ = ("kind", "obj", "net", "hv", "exempt", "layers", "hole", "geo", "parts")

    def __init__(self, kind, obj, net, hv, exempt, layers, hole=None, geo=None):
        self.kind, self.obj, self.net, self.hv, self.exempt = kind, obj, net, hv, exempt
        self.layers, self.hole, self.geo = layers, hole, geo
        self.parts = {}

    def zone_part_rings(self, layer, infl, soft):
        """Pour split for notching: soft = band of depth NOTCH along the edge of the wide parts of the fill,
        hard = the rest (interior and every neck narrower than 2 * NOTCH)."""
        if layer not in self.parts:
            fill = pcbnew.SHAPE_POLY_SET(self.geo[layer])
            deep = pcbnew.SHAPE_POLY_SET(fill)
            deep.Deflate(mm(NOTCH), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MAXERR)
            opened = pcbnew.SHAPE_POLY_SET(deep)
            opened.Inflate(mm(NOTCH), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MAXERR)
            band = pcbnew.SHAPE_POLY_SET(opened)
            band.BooleanSubtract(deep)
            hard = pcbnew.SHAPE_POLY_SET(fill)
            hard.BooleanSubtract(band)
            self.parts[layer] = (hard, band)
        sps = pcbnew.SHAPE_POLY_SET(self.parts[layer][1 if soft else 0])
        if sps.OutlineCount() == 0:
            return []
        sps.Inflate(mm(infl), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MAXERR)
        return rings_of(sps)

    def rings(self, layer, infl):
        """Copper of this item on `layer` inflated by `infl` mm."""
        if self.kind == "via":
            x, y, r = self.geo
            return circle_rings(x, y, r + infl)
        if self.kind == "seg":
            a, b, w = self.geo
            return capsule_rings(a, b, w / 2 + infl)
        if self.kind == "zone":
            sps = pcbnew.SHAPE_POLY_SET(self.geo[layer])
            if infl > 0:
                sps.Inflate(mm(infl), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MAXERR)
            elif infl < 0:
                sps.Deflate(mm(-infl), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MAXERR)
            return rings_of(sps)
        sps = pcbnew.SHAPE_POLY_SET()
        self.obj.TransformShapeToPolygon(sps, layer, mm(max(infl, 0)), MAXERR, pcbnew.ERROR_OUTSIDE)
        return rings_of(sps)

    def bbox(self):
        if self.kind == "via":
            x, y, r = self.geo
            return (x - r, y - r, x + r, y + r)
        if self.kind == "seg":
            a, b, w = self.geo
            return (min(a[0], b[0]) - w / 2, min(a[1], b[1]) - w / 2, max(a[0], b[0]) + w / 2, max(a[1], b[1]) + w / 2)
        if self.kind == "zone":
            bb = None
            for sps in self.geo.values():
                b = sps.BBox()
                q = (MM(b.GetLeft()), MM(b.GetTop()), MM(b.GetRight()), MM(b.GetBottom()))
                bb = q if bb is None else (min(bb[0], q[0]), min(bb[1], q[1]), max(bb[2], q[2]), max(bb[3], q[3]))
            return bb
        b = self.obj.GetBoundingBox()
        return (MM(b.GetLeft()), MM(b.GetTop()), MM(b.GetRight()), MM(b.GetBottom()))


def _near_region(bb, m=1.0):
    return not (bb[2] < X0 - m or bb[0] > X1 + m or bb[3] < Y0 - m or bb[1] > Y1 + m)


class World:
    def __init__(self, board, r):
        self.board, self.r = board, r
        self.items = []                    # every copper item near the region
        self.rule_areas = []               # (rings, track layers (indices), blocks vias)
        self.holes = []                    # (x, y, radius) drilled holes (pads, vias)
        self.maps = {}                     # (hw, hv) -> [arr L1, arr L3, arr L6]; ('v', hv) -> arr
        self.soft = {}                     # same keys: other-net pours (soft obstacles)
        self.netcode = {}
        self.by_code = {}
        for name, ni in board.GetNetsByName().items():
            c = ni.GetNetCode()
            if c > 0:
                self.netcode[short(name)] = c   # NB: bare names are unique for the nets used here
                self.by_code[c] = ni

    # --- inventory
    def collect(self):
        b = self.board
        for fp in b.GetFootprints():
            ref = fp.GetReference()
            ex = ref.startswith(HV_EXEMPT_PREFIX) or ref in HV_EXEMPT_REFS
            for p in fp.Pads():
                bb = p.GetBoundingBox()
                q = (MM(bb.GetLeft()), MM(bb.GetTop()), MM(bb.GetRight()), MM(bb.GetBottom()))
                if not _near_region(q):
                    continue
                ls = [l for l in ALL6 if p.IsOnLayer(l)]
                hole = None
                if p.GetDrillSizeX() > 0:
                    pos = p.GetPosition()
                    hole = (MM(pos.x), MM(pos.y), MM(max(p.GetDrillSizeX(), p.GetDrillSizeY())) / 2)
                    self.holes.append(hole)
                n = p.GetNetCode()
                self.items.append(Item("pad", p, n if n > 0 else -1, short(p.GetNetname()) in L.HV_NETS, ex, ls,
                                       hole))
            for z in fp.Zones():
                self._rule_area(z)
        for t in b.GetTracks():
            self.add_board_track(t)
        for z in b.Zones():
            if z.GetIsRuleArea():
                self._rule_area(z)
                continue
            if z.GetZoneName() in SKIP_ZONES:
                continue
            # one Item per fill island and layer: a zone whose fill is split must not join its islands
            for l in ALL6:
                if not (z.IsOnLayer(l) and z.HasFilledPolysForLayer(l)):
                    continue
                fill = z.GetFilledPolysList(l)
                for i in range(fill.OutlineCount()):
                    sub = pcbnew.SHAPE_POLY_SET()
                    sub.AddOutline(fill.COutline(i))
                    for h in range(fill.HoleCount(i)):
                        sub.AddHole(fill.CHole(i, h))
                    it = Item("zone", z, z.GetNetCode(), short(z.GetNetname()) in L.HV_NETS, False, [l],
                              geo={l: sub})
                    if _near_region(it.bbox()):
                        self.items.append(it)

    def add_board_track(self, t):
        n = t.GetNetCode()
        hv = short(t.GetNetname()) in L.HV_NETS
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition()
            x, y = MM(p.x), MM(p.y)
            if not (X0 - 1 < x < X1 + 1 and Y0 - 1 < y < Y1 + 1):
                return None
            top, bot = t.TopLayer(), t.BottomLayer()
            ls = [l for l in ALL6 if t.IsOnLayer(l)]
            it = Item("via", t, n, hv, False, ls, (x, y, MM(t.GetDrillValue()) / 2),
                      (x, y, MM(t.GetWidth(top)) / 2))
            self.holes.append(it.hole)
        else:
            a, c = t.GetStart(), t.GetEnd()
            if t.GetClass() == "PCB_ARC":
                it = Item("pad", t, n, hv, False, [t.GetLayer()])      # rasterised through TransformShapeToPolygon
            else:
                it = Item("seg", t, n, hv, False, [t.GetLayer()],
                          geo=((MM(a.x), MM(a.y)), (MM(c.x), MM(c.y)), MM(t.GetWidth())))
            if not _near_region(it.bbox()):
                return None
        self.items.append(it)
        return it

    def _rule_area(self, z):
        if not z.GetIsRuleArea():
            return
        ol = z.Outline()
        bb = ol.BBox()
        q = (MM(bb.GetLeft()), MM(bb.GetTop()), MM(bb.GetRight()), MM(bb.GetBottom()))
        if not _near_region(q):
            return
        tl = [i for i, l in enumerate(LAYERS) if z.IsOnLayer(l)] if z.GetDoNotAllowTracks() else []
        bv = z.GetDoNotAllowVias() and any(z.IsOnLayer(l) for l in ALL6)
        if tl or bv:
            self.rule_areas.append((pcbnew.SHAPE_POLY_SET(ol), tl, bv))

    # --- maps
    @staticmethod
    def clr_for(hv, it):
        if it.net == -1:
            return CLR
        if hv != it.hv and not it.exempt:
            return HVCLR
        return CLR

    def is_soft(self, it):
        """Other-net pours: a track may cut a notch into them (they refill around it) at a high cost."""
        if it.kind != "zone":
            return False
        nm = it.obj.GetZoneName()
        return not (nm.startswith("P_GND_HOT") or short(it.obj.GetNetname()) in HARD_POUR_NETS)

    def tmaps(self, hw, hv):
        key = (round(hw, 4), hv)
        if key not in self.maps:
            arrs = [array("i", [0]) * N for _ in LAYERS]
            soft = [array("i", [0]) * N for _ in LAYERS]
            for it in self.items:
                if self.is_soft(it):
                    c = self.clr_for(hv, it)
                    for li, l in enumerate(LAYERS):
                        if l in it.layers:
                            mark(arrs[li], it.zone_part_rings(l, hw + c, False), it.net)
                            mark(soft[li], it.zone_part_rings(l, hw + c, True), it.net)
                else:
                    self._mark_track_maps(arrs, it, hw, hv)
            for sps, tl, bv in self.rule_areas:
                if tl:
                    q = pcbnew.SHAPE_POLY_SET(sps)
                    q.Inflate(mm(hw + 0.01), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MAXERR)
                    rg = rings_of(q)
                    for li in tl:
                        mark_hard(arrs[li], rg)
            for (x, y, rr) in self.holes:
                for li in range(3):
                    mark_hard(arrs[li], circle_rings(x, y, rr + HOLE_CLR + hw))
            self.maps[key] = arrs
            self.soft[key] = soft
        return self.maps[key], self.soft[key]

    def vmap(self, hv, via=VIA):
        VR, VD = via[0] / 2, via[1]
        key = ("v", hv, via)
        if key not in self.maps:
            arr = array("i", [0]) * N
            soft = array("i", [0]) * N
            for it in self.items:
                if self.is_soft(it):
                    c = self.clr_for(hv, it)
                    for l in it.layers:
                        if l in LAYERS:
                            # no via in an other-net pour (a via hole cuts every layer's copper)
                            mark(arr, it.rings(l, VR + c), it.net)
                else:
                    self._mark_via_map(arr, it, hv, VR)
            for sps, tl, bv in self.rule_areas:
                if bv:
                    q = pcbnew.SHAPE_POLY_SET(sps)
                    q.Inflate(mm(VR + 0.01), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MAXERR)
                    mark_hard(arr, rings_of(q))
            for (x, y, rr) in self.holes:
                mark_hard(arr, circle_rings(x, y, rr + max(HOLE_CLR + VR, 0.2 + 0.02 + VD / 2)))
            self.maps[key] = arr
            self.soft[key] = soft
        return self.maps[key], self.soft[key]

    def _mark_track_maps(self, arrs, it, hw, hv):
        c = self.clr_for(hv, it)
        for li, l in enumerate(LAYERS):
            if l in it.layers:
                mark(arrs[li], it.rings(l, hw + c), it.net)

    def _mark_via_map(self, arr, it, hv, VR):
        c = self.clr_for(hv, it)
        if it.kind in ("via", "seg"):
            mark(arr, it.rings(it.layers[0], VR + c), it.net)
            return
        if it.kind == "zone":
            for l in it.layers:
                if l in LAYERS:       # inner plane fills refill around a via: not an obstacle
                    mark(arr, it.rings(l, VR + c), it.net)
            return
        done = set()
        for l in it.layers:
            rg = it.rings(l, VR + c)
            key = tuple(tuple(p) for p in rg[0][:4]) if rg else None
            if key in done:
                continue
            done.add(key)
            mark(arr, rg, it.net)
        if it.kind == "pad" and it.obj.GetClass() == "PAD" and \
                (VR >= VIA[0] / 2 or it.obj.GetParentFootprint().GetReference() in NO_VIP_REFS):
            # no via inside a pad with the normal via; the 0.35/0.15 last-resort via may sit in a pad (filled and
            # capped, as the U401 BGA fan-out already requires), never in D101/D102 (FETs underneath)
            for l in it.layers:
                mark_hard(arr, it.rings(l, VR - 0.05))
                break

    def add_item(self, it):
        """New copper drawn by this script: update every map built so far."""
        self.items.append(it)
        if it.hole:
            self.holes.append(it.hole)
        for key, m in self.maps.items():
            if key[0] == "v":
                self._mark_via_map(m, it, key[1], key[2][0] / 2)
                if it.hole:
                    x, y, rr = it.hole
                    mark_hard(m, circle_rings(x, y, rr + max(HOLE_CLR + key[2][0] / 2, 0.2 + 0.02 + key[2][1] / 2)))
            else:
                self._mark_track_maps(m, it, key[0], key[1])


# ---------------------------------------------------------------------------------------------- routing
DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]


class Router:
    def __init__(self, world):
        self.w = world
        self.board = world.board
        self.r = world.r
        self.log = []

    # cluster copper cells (uninflated) on the routing layers, clipped to a window
    def copper_cells(self, items, win, layers=(0, 1, 2)):
        i0, j0, i1, j1 = win
        out = [set() for _ in LAYERS]
        for it in items:
            bb = it.bbox()
            if bb[2] < X0 + i0 * S - 0.5 or bb[0] > X0 + i1 * S + 0.5 or bb[3] < Y0 + j0 * S - 0.5 or \
                    bb[1] > Y0 + j1 * S + 0.5:
                continue
            for li in layers:
                l = LAYERS[li]
                if l not in it.layers:
                    continue
                infl = -0.02 if it.kind == "zone" else 0.0
                for j, ia, ib in spans(it.rings(l, infl), i0, j0, i1, j1):
                    for i in range(ia, ib + 1):
                        out[li].add(j * W + i)
        return out

    def plane_cells(self, items, win):
        """Via spots inside an inner-layer fill of the cluster (plane nets)."""
        i0, j0, i1, j1 = win
        out = set()
        for it in items:
            if it.kind != "zone":
                continue
            for l in it.layers:
                if l not in INNER_PLANES:
                    continue
                for j, ia, ib in spans(it.rings(l, -(VIA[0] / 2 + 0.1)), i0, j0, i1, j1):
                    for i in range(ia, ib + 1):
                        out.add(j * W + i)
        return out

    def route(self, net, src_items, dst_items, width, margin=3.0, vias=True, layers=(0, 1, 2), plane=True,
              via=VIA):
        VR = via[0] / 2
        """Connect the copper of src_items to the copper of dst_items. Returns the list of new Items or None."""
        w = self.w
        code = w.netcode[net]
        hv = net in L.HV_NETS
        hw = width / 2
        tm, tsoft = w.tmaps(hw, hv)
        vm, vsoft = w.vmap(hv, via) if vias else (None, None)
        # window: source bbox + nearest destination point
        sb = None
        for it in src_items:
            q = it.bbox()
            sb = q if sb is None else (min(sb[0], q[0]), min(sb[1], q[1]), max(sb[2], q[2]), max(sb[3], q[3]))
        cx, cy = (sb[0] + sb[2]) / 2, (sb[1] + sb[3]) / 2
        best = None
        for it in dst_items:
            q = it.bbox()
            dx = max(q[0] - cx, 0, cx - q[2])
            dy = max(q[1] - cy, 0, cy - q[3])
            d = math.hypot(dx, dy)
            if best is None or d < best[0]:
                best = (d, (min(max(cx, q[0]), q[2]), min(max(cy, q[1]), q[3])))
        if best is None:
            return None
        bx0, by0 = min(sb[0], best[1][0]) - margin, min(sb[1], best[1][1]) - margin
        bx1, by1 = max(sb[2], best[1][0]) + margin, max(sb[3], best[1][1]) + margin
        lim = (max(bx0, CU_X0 + hw), max(by0, CU_Y0 + hw), min(bx1, CU_X1 - hw), min(by1, CU_Y1 - hw))
        i0 = max(1, int(math.ceil((lim[0] - X0) / S)))
        j0 = max(1, int(math.ceil((lim[1] - Y0) / S)))
        i1 = min(W - 2, int(math.floor((lim[2] - X0) / S)))
        j1 = min(H - 2, int(math.floor((lim[3] - Y0) / S)))
        if i1 <= i0 or j1 <= j0:
            return None
        win = (i0, j0, i1, j1)
        # local grid with a blocked border
        lw, lh = i1 - i0 + 3, j1 - j0 + 3
        ln = lw * lh
        pt = [bytearray(ln) for _ in LAYERS]
        pv = bytearray(ln)
        for li in layers:
            arr, sft = tm[li], tsoft[li]
            p = pt[li]
            for j in range(j0, j1 + 1):
                gb = j * W
                lb = (j - j0 + 1) * lw + 1 - i0
                for i in range(i0, i1 + 1):
                    v = arr[gb + i]
                    if v == 0 or v == code:
                        u = sft[gb + i]
                        p[lb + i] = 1 if (u == 0 or u == code) else 2
        if vias:
            p0, p1, p2 = pt
            vx0, vy0 = int(math.ceil((CU_X0 + VR - X0) / S)), int(math.ceil((CU_Y0 + VR - Y0) / S))
            vx1, vy1 = int(math.floor((CU_X1 - VR - X0) / S)), int(math.floor((CU_Y1 - VR - Y0) / S))
            for j in range(j0, j1 + 1):
                gb = j * W
                lb = (j - j0 + 1) * lw + 1 - i0
                for i in range(i0, i1 + 1):
                    v = vm[gb + i]
                    k = lb + i
                    if (v == 0 or v == code) and p0[k] and p2[k] and (p1[k] or 1 not in layers) and \
                            vx0 <= i <= vx1 and vy0 <= j <= vy1:
                        u = vsoft[gb + i]
                        pv[k] = 1 if ((u == 0 or u == code) and p0[k] == 1 and p2[k] == 1 and p1[k] < 2) else 2

        def loc(k):
            j, i = divmod(k, W)
            return (j - j0 + 1) * lw + (i - i0 + 1)
        src = self.copper_cells(src_items, win, layers)
        dst = self.copper_cells(dst_items, win, layers)
        goal = [bytearray(ln) for _ in LAYERS]
        gx = []
        for li in layers:
            for k in dst[li]:
                lk = loc(k)
                if pt[li][lk]:
                    goal[li][lk] = 1
                    gx.append(lk)
        pgoal = bytearray(ln)
        if vias and plane:
            for k in self.plane_cells(dst_items, win):
                lk = loc(k)
                if pv[lk]:
                    pgoal[lk] = 1
                    gx.append(lk)
        if not gx:
            return None
        gi = [k % lw for k in gx]
        gj = [k // lw for k in gx]
        ga, gb_, gc, gd = min(gi), max(gi), min(gj), max(gj)

        def h(k):
            i, j = k % lw, k // lw
            dx = ga - i if i < ga else (i - gb_ if i > gb_ else 0)
            dy = gc - j if j < gc else (j - gd if j > gd else 0)
            if dx < dy:
                dx, dy = dy, dx
            return dx + 0.4142 * dy
        INF = 1e18
        g = [array("d", [INF]) * ln for _ in LAYERS]
        prev = [array("i", [-1]) * ln for _ in LAYERS]
        pdir = [bytearray(b"\x08") * ln for _ in LAYERS]
        openq = []
        for li in layers:
            for k in src[li]:
                lk = loc(k)
                if pt[li][lk]:
                    g[li][lk] = 0.0
                    heapq.heappush(openq, (h(lk), 0.0, li, lk))
        offs = [dx + dy * lw for dx, dy in DIRS]
        steps = [1.0 if (dx == 0 or dy == 0) else 1.41421356 for dx, dy in DIRS]
        end = None
        pops = 0
        while openq:
            f, gc_, li, k = heapq.heappop(openq)
            if gc_ > g[li][k]:
                continue
            pops += 1
            if goal[li][k]:
                end = (li, k, False)
                break
            if pgoal[k]:
                end = (li, k, True)
                break
            pd = pdir[li][k]
            lc = LAYER_COST[li]
            p = pt[li]
            for d in range(8):
                nk = k + offs[d]
                pk = p[nk]
                if not pk:
                    continue
                if pd < 8:
                    t = abs(d - pd)
                    if t > 4:
                        t = 8 - t
                    tc = TURN_COST[t]
                    if tc >= 1e9:
                        continue
                else:
                    tc = 0.0
                ng = gc_ + steps[d] * (lc if pk == 1 else lc * SOFT_COST) + tc
                if ng < g[li][nk]:
                    g[li][nk] = ng
                    prev[li][nk] = li * ln + k
                    pdir[li][nk] = d
                    heapq.heappush(openq, (ng + h(nk), ng, li, nk))
            if vias and pv[k]:
                for l2 in layers:
                    if l2 == li or not pt[l2][k]:
                        continue
                    ng = gc_ + (VIA_COST if pv[k] == 1 else VIA_COST * 3)
                    if ng < g[l2][k]:
                        g[l2][k] = ng
                        prev[l2][k] = li * ln + k
                        pdir[l2][k] = 8
                        heapq.heappush(openq, (ng + h(k), ng, l2, k))
        if end is None:
            dd = os.environ.get("G_DEBUG")
            if dd and margin >= 7.0:
                tag = "%s_%d_%d_w%d" % (net.replace("+", "p"), int(cx * 10), int(cy * 10), int(width * 100))
                srcset = [set(loc(k) for k in src[li]) for li in range(3)]
                for li in range(3):
                    with open(os.path.join(dd, "%s_L%d.pgm" % (tag, li)), "wb") as fh:
                        fh.write(b"P5 %d %d 255\n" % (lw, lh))
                        fh.write(bytes((60 if k in srcset[li] else 160 if goal[li][k] else
                                        (255 if pt[li][k] and pv[k] else 200 if pt[li][k] else 0))
                                       for k in range(ln)))
            return None
        # walk back
        li, k, pv_end = end
        path = [(li, k)]
        while prev[path[-1][0]][path[-1][1]] != -1:
            q = prev[path[-1][0]][path[-1][1]]
            path.append(divmod(q, ln))
        path.reverse()
        if goal[path[0][0]][path[0][1]] and len(path) == 1 and not pv_end:
            return []                        # already touching
        def xy(lk):
            j, i = divmod(lk, lw)
            return (round(X0 + (i - 1 + i0) * S, 4), round(Y0 + (j - 1 + j0) * S, 4))
        # split per layer
        runs = []
        cur = [path[0]]
        for st in path[1:]:
            if st[0] != cur[-1][0]:
                runs.append(cur)
                cur = [st]
            else:
                cur.append(st)
        runs.append(cur)
        new = []
        for ri, run in enumerate(runs):
            li = run[0][0]
            ks = [k for _, k in run]
            pts = self._simplify(ks, lw)
            pts = self._chamfer(pts, lw, pt[li])
            xys = [xy(k) for k in pts]
            for a, b in zip(xys, xys[1:]):
                new.append(self._track(net, a, b, width, li))
            if ri < len(runs) - 1:
                x, y = xy(run[-1][1])
                new.append(self._via(net, x, y, via))
        if pv_end:
            x, y = xy(path[-1][1])
            new.append(self._via(net, x, y, via))
        return new

    @staticmethod
    def _simplify(ks, lw):
        if len(ks) <= 2:
            return ks
        out = [ks[0]]
        for a, b, c in zip(ks, ks[1:], ks[2:]):
            if b - a != c - b:
                out.append(b)
        out.append(ks[-1])
        return out

    @staticmethod
    def _chamfer(pts, lw, passable):
        """Replace 90 deg corners by a 45 deg cut (up to 0.4 mm legs) where the cut stays on free cells."""
        if len(pts) < 3:
            return pts
        def ij(k):
            return (k % lw, k // lw)
        out = [pts[0]]
        i = 1
        while i < len(pts) - 1:
            a, b, c = ij(out[-1]), ij(pts[i]), ij(pts[i + 1])
            d1 = (b[0] - a[0], b[1] - a[1])
            d2 = (c[0] - b[0], c[1] - b[1])
            l1 = max(abs(d1[0]), abs(d1[1]))
            l2 = max(abs(d2[0]), abs(d2[1]))
            u1 = (d1[0] // l1 if l1 else 0, d1[1] // l1 if l1 else 0)
            u2 = (d2[0] // l2 if l2 else 0, d2[1] // l2 if l2 else 0)
            dot = u1[0] * u2[0] + u1[1] * u2[1]
            orth = (u1[0] == 0 or u1[1] == 0) and (u2[0] == 0 or u2[1] == 0) and dot == 0
            done = False
            if orth:
                nmax = min(8, l1 // 2 if i > 1 else l1, l2 // 2 if i < len(pts) - 2 else l2)
                for n in range(nmax, 0, -1):
                    p = (b[0] - u1[0] * n, b[1] - u1[1] * n)
                    q = (b[0] + u2[0] * n, b[1] + u2[1] * n)
                    ok = True
                    for t in range(n + 1):
                        cx, cy = p[0] + (u1[0] + u2[0]) * t, p[1] + (u1[1] + u2[1]) * t
                        if not passable[cy * lw + cx]:
                            ok = False
                            break
                    if ok:
                        out.append(p[1] * lw + p[0])
                        out.append(q[1] * lw + q[0])
                        done = True
                        break
            if not done:
                out.append(pts[i])
            i += 1
        out.append(pts[-1])
        # drop zero-length / duplicate points
        res = [out[0]]
        for k in out[1:]:
            if k != res[-1]:
                res.append(k)
        return res

    def _track(self, net, a, b, width, li):
        t = pcbnew.PCB_TRACK(self.board)
        t.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1])))
        t.SetEnd(pcbnew.VECTOR2I(mm(b[0]), mm(b[1])))
        t.SetWidth(mm(width))
        t.SetLayer(LAYERS[li])
        t.SetNet(self.w.by_code[self.w.netcode[net]])
        self.r._add(t)
        it = Item("seg", t, self.w.netcode[net], net in L.HV_NETS, False, [LAYERS[li]], geo=(a, b, width))
        self.w.add_item(it)
        return it

    def _via(self, net, x, y, via=VIA):
        v = pcbnew.PCB_VIA(self.board)
        v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        v.SetWidth(mm(via[0]))
        v.SetDrill(mm(via[1]))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(self.w.by_code[self.w.netcode[net]])
        self.r._add(v)
        it = Item("via", v, self.w.netcode[net], net in L.HV_NETS, False, list(ALL6), (x, y, via[1] / 2),
                  (x, y, via[0] / 2))
        self.w.add_item(it)
        return it


# ---------------------------------------------------------------------------------------------- escapes
def reserve_escapes(board, world):
    """Fine-pitch IC pins (pitch < 0.7 mm): reserve a straight 0.15 mm escape out of the pin end for the pin's own
    net (a virtual track: blocks every other net, draws nothing). Keeps the pins of local AND interblock nets
    reachable whatever is routed first."""
    n = 0
    for fp in board.GetFootprints():
        pads = [p for p in fp.Pads() if p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD]
        if len(pads) < 6:
            continue
        pos = fp.GetPosition()
        fx, fy = MM(pos.x), MM(pos.y)
        if not in_region(fx, fy):
            continue
        xy = [_pad_xy(p) for p in pads]
        areas = [MM(p.GetBoundingBox().GetWidth()) * MM(p.GetBoundingBox().GetHeight()) for p in pads]
        amed = sorted(areas)[len(areas) // 2]
        for p, (x, y), a in zip(pads, xy, areas):
            if p.GetNetCode() <= 0 or a > 3 * amed:
                continue
            d = min((math.hypot(x - u, y - v) for (u, v) in xy if (u, v) != (x, y)), default=9)
            if d >= 0.7:
                continue
            bb = p.GetBoundingBox()
            wdt, hgt = MM(bb.GetWidth()), MM(bb.GetHeight())
            if wdt > hgt:      # long axis x
                sx = 1 if x > fx else -1
                a0, a1 = (x, y), (x + sx * (wdt / 2 + 0.35), y)
            else:
                sy = 1 if y > fy else -1
                a0, a1 = (x, y), (x, y + sy * (hgt / 2 + 0.35))
            ls = [l for l in LAYERS if p.IsOnLayer(l)]
            if not ls:
                continue
            world.items.append(Item("seg", None, p.GetNetCode(), short(p.GetNetname()) in L.HV_NETS, True, ls[:1],
                                    geo=(a0, a1, 0.15)))
            n += 1
    return n


# ---------------------------------------------------------------------------------------------- clusters
def _anchor_points(it):
    """(x, y, layers) points of a non-zone item that lie inside any pour island it is connected to."""
    if it.kind == "via":
        return [(it.geo[0], it.geo[1], it.layers)]
    if it.kind == "seg":
        return [(it.geo[0][0], it.geo[0][1], it.layers), (it.geo[1][0], it.geo[1][1], it.layers)]
    if it.obj is not None and it.obj.GetClass() == "PAD":
        v = it.obj.GetPosition()
        return [(MM(v.x), MM(v.y), it.layers)]
    return []


def clusters_of(board, conn, world, net_full):
    """Copper clusters of a net (KiCad connectivity) as lists of world Items + their pads. KiCad reports zones,
    not fill islands: an island joins the cluster that has a pad / via / track end in (or within 0.6 mm of, for
    thermal reliefs) it."""
    by_obj = {}
    islands = defaultdict(list)
    for it in world.items:
        if it.obj is None:
            continue
        if it.kind == "zone":
            islands[it.obj.m_Uuid.AsString()].append(it)
        else:
            by_obj[it.obj.m_Uuid.AsString()] = it
    pads = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() == net_full:
                pads.append(p)
    seen = {}
    taken = set()
    out = []
    for p in pads:
        u = p.m_Uuid.AsString()
        if u in seen:
            continue
        ci = len(out)
        items = []
        padl = []
        zones = []
        for q in [p] + list(conn.GetConnectedItems(p)):
            uq = q.m_Uuid.AsString()
            if uq in islands:
                zones.append(uq)
                continue
            if uq in seen:
                continue
            seen[uq] = ci
            it = by_obj.get(uq)
            if it is not None:
                items.append(it)
            if q.GetClass() == "PAD":
                padl.append(q)
        pts = [a for it in items for a in _anchor_points(it)]
        for uz in zones:
            for isl in islands[uz]:
                if id(isl) in taken:
                    continue
                l = isl.layers[0]
                sps = isl.geo[l]
                if any(l in ls and sps.Collide(pcbnew.VECTOR2I(mm(x), mm(y)), mm(0.6)) for x, y, ls in pts):
                    items.append(isl)
                    taken.add(id(isl))
        out.append({"items": items, "pads": padl})
    return out


def _pad_xy(p):
    v = p.GetPosition()
    return (MM(v.x), MM(v.y))


# ---------------------------------------------------------------------------------------------- main
# nets routed first (G_ITER=6 run: failed nets moved ahead each time; this order gave the fewest failures)
PRIORITY = ['BB_SLOPE', 'BB_SS', 'BB_VS1D', 'SNK_ILM', 'SNK_ITIMER', 'SRC_CAP', 'SRC_OVT', 'BAR_SW', 'PD_CAP',
            'PD_GPIO11', 'PD_GPIO3', 'PD_GPIO4', 'PD_GPIO5', 'PD_GPIO6', 'PD_GPIO7', 'PD_LDO_1V5', 'PD_OV_TOP',
            'PD_PP_EN_HV', 'SNK_OVLO', 'SRC_OV', 'BAR_HGATE', 'BAR_OV', 'PDIN_CC1', 'PDIN_C_CC1', 'PDIN_C_CC2',
            'PDIN_EPR_EN', 'PDIN_PRES_L', 'PD_ADCIN1', 'PD_ADCIN2', 'PD_OV', 'SRC_ON', 'BAR_OK', 'PDIN_VBUS_LV',
            'PD_I2CC_SDA', 'BB_FBM', 'BB_VCC', 'VBAR', 'VIN_OR', 'BAR_MID', 'PD_LDO_3V3', 'PD_MID', 'VBUS_PDIN',
            'VBB_OUT', 'VBUS_LSW', 'VBUS_LAPTOP', 'VIN', 'GND', '+3V3']


def route(board, r):
    import time
    t0 = time.time()
    to_fill = [z for z in board.Zones() if not z.GetIsRuleArea() and z.GetZoneName() not in SKIP_ZONES]
    pcbnew.ZONE_FILLER(board).Fill(to_fill)
    netpads = defaultdict(list)
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetNetCode() > 0:
                netpads[p.GetNetname()].append(p)
    local, supply, tree = [], [], []
    for full, pl in netpads.items():
        inside = [in_region(*_pad_xy(p)) for p in pl]
        n = short(full)
        if n in SKIP_NETS:
            continue
        if all(inside):
            local.append(full)
        elif any(inside) and n in SUPPLY:
            supply.append(full)
        elif any(inside) and n in LOCAL_TREE:
            tree.append(full)
    only = set(x for x in os.environ.get("G_ONLY", "").split(",") if x)

    def run(prio):
        board.BuildConnectivity()
        world = World(board, r)
        world.collect()
        n_res = reserve_escapes(board, world)
        rt = Router(world)
        state = {"conn": board.GetConnectivity()}
        stats = defaultdict(int)
        failed = []

        def pads_of(c):
            return [p.GetParentFootprint().GetReference() + "." + p.GetNumber() for p in c["pads"]]

        def centre(it):
            q = it.bbox()
            return ((q[0] + q[2]) / 2, (q[1] + q[3]) / 2)

        def attempt(n, src, dst, width, final=False):
            if not final:
                tries = [(width, 3.0, VIA), (width, 7.0, VIA)]
                if width > 0.15:
                    tries += [(0.15, 3.0, VIA), (0.15, 7.0, VIA)]
            else:       # second pass: what failed before gets a bigger window, then the small (in-pad) via
                tries = [(0.15, 7.0, VIA), (0.15, 11.0, VIA), (0.15, 4.0, VIA_SMALL)]
            for wd, mg, via in tries:
                res = rt.route(n, src, dst, wd, margin=mg, via=via)
                if res is not None:
                    return res
            return None

        def connect(full, mode, final=False):
            """Join the clusters of a net. Returns the clusters that could not be joined."""
            n = short(full)
            cl = clusters_of(board, state["conn"], world, full)
            if mode != "local":
                cl = [c for c in cl if c["items"]]
            if len(cl) <= 1:
                return []
            width = WIDE.get(n, 0.15)
            cl.sort(key=lambda c: (-sum(1 for it in c["items"] if it.kind == "zone"), -len(c["pads"])))
            if mode == "supply":
                # every in-region cluster -> the main cluster (planes / pours); nothing else is joined
                main = cl[0]
                bad = []
                for c in [c for c in cl[1:] if any(in_region(*_pad_xy(p)) for p in c["pads"])]:
                    res = attempt(n, c["items"], main["items"], width, final)
                    if res is None:
                        bad.append(c)
                        continue
                    main["items"] += c["items"] + res
                    stats["supply ties"] += 1
                return bad
            if mode == "tree":
                cl = [c for c in cl if any(in_region(*_pad_xy(p)) for p in c["pads"])]
                if len(cl) <= 1:
                    return []
            # Prim from the biggest cluster; a cluster that cannot reach the tree is retried against all the rest
            tree_items = list(cl[0]["items"])
            rest = cl[1:]
            pending = []
            while rest:
                tp = [centre(it) for it in tree_items if it.kind == "pad"] or [centre(it) for it in tree_items]

                def dist(c):
                    return min(math.hypot(a[0] - b[0], a[1] - b[1]) for a in [_pad_xy(p) for p in c["pads"]]
                               for b in tp)
                rest.sort(key=dist)
                c = rest.pop(0)
                res = attempt(n, c["items"], tree_items, width, final)
                if res is None:
                    pending.append(c)
                    continue
                tree_items += c["items"] + res
                stats["connections"] += 1
            bad = []
            for c in pending:
                others = tree_items + [it for o in pending if o is not c for it in o["items"]]
                res = attempt(n, c["items"], others, width, final)
                if res is None:
                    bad.append(c)
                    continue
                c["items"] += res
                stats["connections"] += 1
            return bad

        rank = {n: i for i, n in enumerate(prio)}
        jobs = [(f, "local") for f in local] + [(f, "supply") for f in supply] + [(f, "tree") for f in tree]
        order = {"local": 0, "supply": 1, "tree": 2}
        jobs.sort(key=lambda j: (rank.get(short(j[0]), 1e6), order[j[1]], len(netpads[j[0]]), j[0]))
        if only:
            jobs = [j for j in jobs if short(j[0]) in only]
        for full, mode in jobs:
            connect(full, mode)
        # second pass with the real connectivity (catches pending clusters joined through others)
        board.BuildConnectivity()
        state["conn"] = board.GetConnectivity()
        for full, mode in jobs:
            for c in connect(full, mode, final=True):
                failed.append((short(full), pads_of(c)))
        return failed, stats, n_res

    def rip_all():
        n = 0
        g = r.group
        items = list(g.GetItems())
        g.RemoveAll()
        for it in items:
            board.Remove(it)
            n += 1
        return n

    prio = list(PRIORITY)
    iters = int(os.environ.get("G_ITER", "1"))
    best = None
    for it_ in range(iters):
        failed, stats, n_res = run(prio)
        nf = len(failed)
        print("g_power: run %d: %s; %d failed clusters; %d escape reservations; %.0fs" %
              (it_, dict(stats), nf, n_res, time.time() - t0))
        if best is None or nf < best[0]:
            best = (nf, list(prio), failed, stats)
        if it_ == iters - 1 or nf == 0:
            break
        # failed nets go first next time (ahead of the previous priority list)
        fn = []
        for n, _p in failed:
            if n not in fn:
                fn.append(n)
        prio = fn + [n for n in prio if n not in fn]
        rip_all()
    if iters > 1 and best[1] != prio:
        rip_all()
        failed, stats, n_res = run(best[1])
        prio = best[1]
    if iters > 1:
        print("g_power: PRIORITY =", prio)
    for z in to_fill:
        z.UnFill()
    print("g_power: %s; %d failed clusters; %.0fs" % (dict(stats), len(failed), time.time() - t0))
    for n, pads in failed:
        print("   FAILED", n, " ".join(pads))
