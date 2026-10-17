"""odock-10 plane fan-out: a short escape track + through via from every SMD pad of a plane net to its plane.

Runs after a_planes / b_power / c-e (high-speed) and before the autorouter and z_stitch.py, so Freerouting only sees
the real signal connections instead of ~1700 pad-to-plane stubs.

What is fanned out
- Every SMD pad (both sides) whose net has a copper zone on an inner layer (GND: GND_L2 / GND_L5; power: the L4
  islands of a_planes and the L3 helper pours of b_power) and that is NOT already in the same copper cluster as that
  zone (cluster test: inner zones and the b_power pours filled, GND_L1 / GND_L6 left unfilled because the autoroute
  step removes them; KiCad connectivity). Pads already tied by a pour, a track or a via are skipped; THT pads reach
  every layer and are skipped.
- The via must land inside the filled copper of one of the net's inner zones (voids / keep-outs / other islands are
  respected that way).
- Exposed pads (large SMD pad at the centre of a part with >= 4 pads, or any SMD pad >= 2 mm^2) without a via yet get
  a via array inside the pad. The PMG1 BGA (U401) balls and the hub VDD33 pin U601.99 (hs_hub.md) get a 0.35/0.15
  via-in-pad. Everything else gets a dog-bone: straight track from the pad centre to a via outside the pad, at the
  cheapest legal spot (track length + a penalty for leaving towards the part body) within REACH of the pad edge.
  An existing same-net via that already reaches the plane (or one of ours, max 2 pads each) is reused when closer.

Legality (own geometric checker, KiCad pad shapes): >= 0.16 mm to every pad / track / via of another net on every
layer (0.31 mm across the HV boundary, 0.31 mm from our tracks to USB_90 / HS_85 tracks: "hs pair spacing" rule),
0.21 mm copper-to-hole, board edge, mounting holes, every rule area that forbids vias (or tracks on that layer),
the HS corridors of hs_usbc.md, KO_RJ45, the other-net power pours of b_power (vias and tracks would cut them),
the courtyards of other parts on the same side, and (except via-in-pad) the pin fields of ICs on either side.

Ownership / idempotency: NETS = [] (the nets also belong to b_power, c-e, z_stitch). Everything this script draws is
tagged by size -- tracks 0.201 / 0.251 / 0.301 / 0.401 mm, vias 0.451/0.25 and 0.351/0.15 -- sizes no other script
uses; route() first deletes exactly those items, so re-running never touches other copper.
"""
import os
import sys
import math
from collections import defaultdict, Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew  # noqa: E402
import _pwrlib as L  # noqa: E402

NETS = []
ZONES = []

mm, MM = pcbnew.FromMM, pcbnew.ToMM
VIA = (0.451, 0.25)        # dog-bone / EP vias (tag: 0.451 mm diameter)
VIA_VIP = (0.351, 0.15)    # BGA / fine-pitch via-in-pad (tag: 0.351 mm diameter)
TAG_W = (0.201, 0.251, 0.301, 0.401)
CLR = 0.16                 # DRC 0.15 + margin
HV_CLR = 0.31              # "high voltage" rule 0.3 + margin
HS_CLR = 0.31              # "hs pair spacing" rule (track-track) 0.3 + margin
HOLE_CLR = 0.21            # min_hole_clearance 0.2 + margin
# dog-bone passes: (max via distance from the pad edge, strict). strict: no via in the courtyard of another part on
# the same side nor inside an IC pin field (either side); the later passes drop that (pad clearances still apply)
PASSES = ((1.5, True), (1.5, False), (2.2, False))
VIP_REFS = {"U401"}        # PMG1 BGA: via-in-pad per usbc.md
VIP_PADS = {("U601", "99")}  # hub VDD33: no toe spot left (hs_hub.md item 5)
HS_CLASSES = ("USB_90", "HS_85")
ALL_LAYERS = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu)

# No through vias here (docs/routing-notes/hs_usbc.md "Keep-outs for other routers"); KO_RJ45 is added from a_planes.
NO_VIA = [
    L.rect(159.75, 63.0, 163.4, 79.0),     # L3 hub SS corridor
    L.rect(145.8, 79.3, 171.0, 80.6),      # L3 laptop USB2
    L.rect(166.6, 76.9, 174.4, 80.4),      # L1/L3 transitions of the hub links
]


# ------------------------------------------------------------------------------------------------ geometry
def _seg_seg(a, b, c, d):
    """Distance between segments ab and cd."""
    def orient(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    o1, o2, o3, o4 = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
    if ((o1 > 0) != (o2 > 0)) and ((o3 > 0) != (o4 > 0)) and o1 and o2 and o3 and o4:
        return 0.0
    return min(L._seg_dist(a[0], a[1], c[0], c[1], d[0], d[1]), L._seg_dist(b[0], b[1], c[0], c[1], d[0], d[1]),
               L._seg_dist(c[0], c[1], a[0], a[1], b[0], b[1]), L._seg_dist(d[0], d[1], a[0], a[1], b[0], b[1]))


def _bbox(poly):
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    return (min(xs), min(ys), max(xs), max(ys))


def _v(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


def _poly_pts(sps, i=0):
    o = sps.Outline(i)
    return [(MM(o.CPoint(k).x), MM(o.CPoint(k).y)) for k in range(o.PointCount())]


class Grid:
    """Spatial hash of obstacles (1 mm cells)."""

    def __init__(self, cell=1.0):
        self.cell = cell
        self.d = defaultdict(list)

    def add(self, item, bb):
        c = self.cell
        for i in range(int(math.floor(bb[0] / c)), int(math.floor(bb[2] / c)) + 1):
            for j in range(int(math.floor(bb[1] / c)), int(math.floor(bb[3] / c)) + 1):
                self.d[(i, j)].append(item)

    def query(self, bb):
        c = self.cell
        seen = set()
        out = []
        for i in range(int(math.floor(bb[0] / c)), int(math.floor(bb[2] / c)) + 1):
            for j in range(int(math.floor(bb[1] / c)), int(math.floor(bb[3] / c)) + 1):
                for it in self.d.get((i, j), ()):
                    if id(it) not in seen:
                        seen.add(id(it))
                        out.append(it)
        return out


class Pad:
    __slots__ = ("p", "ref", "num", "net", "layers", "bb", "hole", "shapes", "smd", "fp", "why")

    def __init__(self, p, fp):
        self.p, self.fp = p, fp
        self.ref, self.num = fp.GetReference(), p.GetNumber()
        self.net = L.short(p.GetNetname())
        self.layers = [l for l in ALL_LAYERS if p.IsOnLayer(l)]
        b = p.GetBoundingBox()
        self.bb = (MM(b.GetLeft()), MM(b.GetTop()), MM(b.GetRight()), MM(b.GetBottom()))
        self.hole = p.GetEffectiveHoleShape() if p.GetDrillSizeX() > 0 else None
        self.shapes = {}
        self.smd = p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD
        self.why = "via-in-pad blocked"

    def shape(self, layer):
        s = self.shapes.get(layer)
        if s is None:
            s = self.shapes[layer] = self.p.GetEffectiveShape(layer)
        return s


class Checker:
    def __init__(self, board, netclass):
        self.board = board
        self.ncls = netclass
        self.g = Grid()
        self.pads = []
        for fp in board.GetFootprints():
            for p in fp.Pads():
                if not any(p.IsOnLayer(l) for l in ALL_LAYERS) and p.GetDrillSizeX() == 0:
                    continue
                pd = Pad(p, fp)
                self.pads.append(pd)
                self.g.add(("pad", pd), pd.bb)
        for t in board.GetTracks():
            n = L.short(t.GetNetname())
            if t.GetClass() == "PCB_VIA":
                p = t.GetPosition()
                self.add_via(n, MM(p.x), MM(p.y), MM(t.GetWidth(pcbnew.F_Cu)), MM(t.GetDrillValue()))
            else:
                a, b = t.GetStart(), t.GetEnd()
                self.add_track(n, (MM(a.x), MM(a.y)), (MM(b.x), MM(b.y)), MM(t.GetWidth()), t.GetLayer())
        # rule areas: (poly, bbox, layers, no_tracks, no_vias)
        self.rules = []
        for z in board.Zones():
            if not z.GetIsRuleArea() or not (z.GetDoNotAllowVias() or z.GetDoNotAllowTracks()):
                continue
            poly = _poly_pts(z.Outline())
            ls = set(l for l in ALL_LAYERS if z.GetLayerSet().Contains(l))
            self.rules.append((poly, _bbox(poly), ls, z.GetDoNotAllowTracks(), z.GetDoNotAllowVias()))
        # courtyards per side: (ref, poly, bbox)
        self.crt = {pcbnew.F_Cu: [], pcbnew.B_Cu: []}
        for fp in board.GetFootprints():
            side = pcbnew.B_Cu if fp.IsFlipped() else pcbnew.F_Cu
            cy = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd)
            for i in range(cy.OutlineCount()):
                poly = _poly_pts(cy, i)
                if len(poly) >= 3:
                    self.crt[side].append((fp.GetReference(), poly, _bbox(poly)))
        # IC pin fields (vias there block the IC's own escapes), either side
        self.pinfields = []
        for fp in board.GetFootprints():
            ref = fp.GetReference()
            if not ref.startswith("U") or len(fp.Pads()) < 8 or ref == "U1101":
                continue
            bxs = [p.GetBoundingBox() for p in fp.Pads()]
            self.pinfields.append((ref, (min(MM(q.GetLeft()) for q in bxs), min(MM(q.GetTop()) for q in bxs),
                                         max(MM(q.GetRight()) for q in bxs), max(MM(q.GetBottom()) for q in bxs))))
        # other-net pours (b_power) on outer / L3 layers: (net, poly, bbox, layer)
        self.pours = []
        # no-via polygons
        self.novia = [(p, _bbox(p)) for p in NO_VIA]
        self.board_ok = L.board_poly(inset=0.0, chamfer=2.0)

    # ---- obstacle bookkeeping
    def add_via(self, net, x, y, size, drill):
        it = ("via", net, x, y, size / 2, drill)
        self.g.add(it, (x - size / 2, y - size / 2, x + size / 2, y + size / 2))
        return it

    def add_track(self, net, a, b, w, layer):
        it = ("trk", net, a, b, w, layer, self.ncls(net) in HS_CLASSES)
        self.g.add(it, (min(a[0], b[0]) - w / 2, min(a[1], b[1]) - w / 2, max(a[0], b[0]) + w / 2,
                        max(a[1], b[1]) + w / 2))
        return it

    @staticmethod
    def _clr(n1, n2):
        return HV_CLR if ((n1 in L.HV_NETS) != (n2 in L.HV_NETS)) else CLR

    # ---- tests
    def edge_ok(self, x, y, d):
        bo = self.board_ok
        return L._poly_dist(x, y, bo) == 0 and \
            min(L._seg_dist(x, y, *bo[i], *bo[(i + 1) % len(bo)]) for i in range(len(bo))) >= d

    def via_ok(self, net, x, y, size, drill, own=None, vip=False, side=None, strict=True):
        rad = size / 2
        # board edge (0.3 mm copper-to-edge) and mounting holes
        if not self.edge_ok(x, y, rad + 0.35):
            return False
        for hx, hy in L.HOLES:
            if math.hypot(x - hx, y - hy) < 4.3 + rad:
                return False
        for poly, bb in self.novia:
            if bb[0] - 1 < x < bb[2] + 1 and bb[1] - 1 < y < bb[3] + 1 and L._poly_dist(x, y, poly) < rad + 0.02:
                return False
        for poly, bb, ls, nt, nv in self.rules:
            if nv and bb[0] - 1 < x < bb[2] + 1 and bb[1] - 1 < y < bb[3] + 1 and \
                    L._poly_dist(x, y, poly) < rad + 0.02:
                return False
        for pnet, poly, bb, layer in self.pours:
            if pnet != net and bb[0] - 1 < x < bb[2] + 1 and bb[1] - 1 < y < bb[3] + 1 and \
                    L._poly_dist(x, y, poly) < rad + 0.05:
                return False
        if not vip and strict:
            for ref, (x0, y0, x1, y1) in self.pinfields:
                if x0 - rad < x < x1 + rad and y0 - rad < y < y1 + rad:
                    return False
            if side is not None:
                for ref, poly, bb in self.crt[side]:
                    if own is not None and ref == own.ref:
                        continue
                    if bb[0] < x < bb[2] and bb[1] < y < bb[3] and L._in_poly(x, y, poly):
                        return False
        v = _v(x, y)
        m = HV_CLR + rad + 0.1
        for it in self.g.query((x - m, y - m, x + m, y + m)):
            k = it[0]
            if k == "pad":
                pd = it[1]
                if pd.hole is not None and pd.hole.Collide(v, mm(rad + HOLE_CLR)):
                    return False
                same = pd.net == net
                c = self._clr(pd.net, net)
                for layer in pd.layers:
                    if same:
                        if vip and pd is own:
                            continue
                        if pd.shape(layer).Collide(v, mm(rad) - 1):      # no via (partly) inside a pad
                            return False
                    elif pd.shape(layer).Collide(v, mm(rad + c)):
                        return False
            elif k == "via":
                _, n, vx, vy, vr, vd = it
                d = math.hypot(x - vx, y - vy)
                if n == net:
                    if d < max(vr + rad + 0.05, drill / 2 + vd / 2 + 0.26):
                        return False
                elif d < vr + rad + self._clr(n, net):
                    return False
            else:
                _, n, a, b, w, layer, hs = it
                if n != net and L._seg_dist(x, y, a[0], a[1], b[0], b[1]) < rad + w / 2 + self._clr(n, net):
                    return False
        return True

    def track_ok(self, net, a, b, w, layer, own=None, trace=None):
        r = self._track_ok(net, a, b, w, layer)
        if trace is not None and r is not True:
            trace.append((a, b, w, r))
        return r is True

    def _track_ok(self, net, a, b, w, layer):
        hw = w / 2
        n_s = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 0.05) + 1)
        samples = [(a[0] + (b[0] - a[0]) * k / (n_s - 1), a[1] + (b[1] - a[1]) * k / (n_s - 1)) for k in range(n_s)]
        bb = (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))
        for poly, pb, ls, nt, nv in self.rules:
            if nt and layer in ls and not (pb[2] < bb[0] - 1 or pb[0] > bb[2] + 1 or pb[3] < bb[1] - 1 or
                                           pb[1] > bb[3] + 1):
                if any(L._poly_dist(x, y, poly) < hw + 0.02 for x, y in samples):
                    return "rule area"
        for pnet, poly, pb, pl in self.pours:
            if pnet != net and pl == layer and not (pb[2] < bb[0] - 1 or pb[0] > bb[2] + 1 or pb[3] < bb[1] - 1 or
                                                    pb[1] > bb[3] + 1):
                if any(L._poly_dist(x, y, poly) < hw + 0.05 for x, y in samples):
                    return "pour " + pnet
        seg = pcbnew.SEG(_v(*a), _v(*b))
        m = max(HV_CLR, HS_CLR) + hw + 0.1
        for it in self.g.query((bb[0] - m, bb[1] - m, bb[2] + m, bb[3] + m)):
            k = it[0]
            if k == "pad":
                pd = it[1]
                if pd.hole is not None and pd.hole.Collide(seg, mm(hw + HOLE_CLR)):
                    return "hole %s.%s" % (pd.ref, pd.num)
                if pd.net == net or layer not in pd.layers:
                    continue
                if pd.shape(layer).Collide(seg, mm(hw + self._clr(pd.net, net))):
                    return "pad %s.%s" % (pd.ref, pd.num)
            elif k == "via":
                _, n, vx, vy, vr, vd = it
                if n != net and L._seg_dist(vx, vy, a[0], a[1], b[0], b[1]) < vr + hw + self._clr(n, net):
                    return "via %s" % n
            else:
                _, n, c, d, w2, l2, hs = it
                if n == net or l2 != layer:
                    continue
                cl = max(self._clr(n, net), HS_CLR if hs else 0)
                if _seg_seg(a, b, c, d) < hw + w2 / 2 + cl:
                    return "track %s" % n
        return True


# ------------------------------------------------------------------------------------------------ helpers
def _clear_previous(board):
    tw = set(mm(w) for w in TAG_W)
    tv = {(mm(VIA[0]), mm(VIA[1])), (mm(VIA_VIP[0]), mm(VIA_VIP[1]))}
    n = 0
    for t in list(board.GetTracks()):
        if t.GetClass() == "PCB_VIA":
            if (t.GetWidth(pcbnew.F_Cu), t.GetDrillValue()) in tv:
                board.Delete(t)
                n += 1
        elif t.GetClass() == "PCB_TRACK" and t.GetWidth() in tw:
            board.Delete(t)
            n += 1
    return n


def _netclass_fn(board):
    import json
    import fnmatch
    pats = []
    try:
        pro = os.path.splitext(board.GetFileName())[0] + ".kicad_pro"
        if not os.path.exists(pro):
            pro = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "odock-10.kicad_pro")
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


def _widths(net, ncls):
    if net == "GND":
        return (0.251, 0.201)
    c = ncls(net)
    if c in ("PWR_HC", "HV"):
        return (0.401, 0.301, 0.201)
    return (0.301, 0.251, 0.201)


def _in_fill(fills, x, y, rad):
    pts = [(x, y)] + [(x + 0.6 * rad * math.cos(a), y + 0.6 * rad * math.sin(a)) for a in (0, 1.5708, 3.1416, 4.7124)]
    for f in fills:
        if all(f.Contains(_v(px, py), -1, 0, True) for px, py in pts):
            return True
    return False


def _is_ep(pd, fp):
    w, h = pd.bb[2] - pd.bb[0], pd.bb[3] - pd.bb[1]
    area = w * h
    if area >= 2.0:
        return True
    pads = list(fp.Pads())
    if len(pads) < 4 or area < 1.0:
        return False
    if max(q.GetSize().x * q.GetSize().y for q in pads) > pd.p.GetSize().x * pd.p.GetSize().y:
        return False
    xs = [MM(q.GetPosition().x) for q in pads]
    ys = [MM(q.GetPosition().y) for q in pads]
    cx, cy = (pd.bb[0] + pd.bb[2]) / 2, (pd.bb[1] + pd.bb[3]) / 2
    return abs(cx - (min(xs) + max(xs)) / 2) < 0.8 and abs(cy - (min(ys) + max(ys)) / 2) < 0.8


# ------------------------------------------------------------------------------------------------ main
def route(board, r):
    n_old = _clear_previous(board)
    ncls = _netclass_fn(board)
    import a_planes
    import b_power

    # --- plane zones per net (inner layers) and the cluster analysis
    inner = (pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu)
    gnd_outer = set(a_planes.GND_POURS)
    to_fill = [z for z in board.Zones() if not z.GetIsRuleArea() and z.GetZoneName() not in gnd_outer]
    pcbnew.ZONE_FILLER(board).Fill(to_fill)
    planes = defaultdict(list)          # net -> [zone]
    fills = defaultdict(list)           # net -> [SHAPE_POLY_SET]
    for z in to_fill:
        if z.GetLayer() in inner and z.GetNetname():
            n = L.short(z.GetNetname())
            planes[n].append(z)
            fp_ = pcbnew.SHAPE_POLY_SET(z.GetFilledPolysList(z.GetLayer()))   # copy: survives UnFill()
            fp_.BuildBBoxCaches()
            fills[n].append(fp_)
    board.BuildConnectivity()
    conn = board.GetConnectivity()
    on_plane = set()                    # uuids of items in a plane cluster
    for n, zs in planes.items():
        for z in zs:
            for it in conn.GetConnectedItems(z):
                on_plane.add(it.m_Uuid.AsString())

    ck = Checker(board, ncls)
    for name, net, layer, poly, prio in b_power.POURS:
        ck.pours.append((net, poly, _bbox(poly), L.CU[layer]))
    ck.novia.append((a_planes.RJ45_KO, _bbox(a_planes.RJ45_KO)))

    # existing same-net vias that reach a plane: reusable targets
    reuse = defaultdict(list)            # net -> [[x, y, uses_left]]
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA" and t.GetViaType() == pcbnew.VIATYPE_THROUGH and \
                t.m_Uuid.AsString() in on_plane:
            p = t.GetPosition()
            reuse[L.short(t.GetNetname())].append([MM(p.x), MM(p.y), 2])

    # pads with a via already inside them (EP arrays of b_power / HS scripts)
    def has_via_inside(pd):
        for it in ck.g.query(pd.bb):
            if it[0] == "via" and it[1] == pd.net:
                if any(pd.shape(l).Collide(_v(it[2], it[3]), 0) for l in pd.layers):
                    return True
        return False

    todo = []
    for pd in ck.pads:
        if not pd.smd or pd.net not in planes or not pd.net:
            continue
        if pd.p.m_Uuid.AsString() in on_plane:
            continue
        todo.append(pd)
    stats = Counter()
    failed = []

    def via(net, x, y, size, drill):
        r.via(net, x, y, size, drill)
        ck.add_via(net, x, y, size, drill)

    def track(net, a, b, w, layer):
        r.track(net, [a, b], _lname(layer), w)
        ck.add_track(net, a, b, w, layer)

    # --- 1. exposed / thermal pads: via arrays inside the pad
    rest = []
    for pd in todo:
        fp = pd.fp
        if pd.ref in VIP_REFS or (pd.ref, pd.num) in VIP_PADS:
            x, y = MM(pd.p.GetPosition().x), MM(pd.p.GetPosition().y)
            if _in_fill(fills[pd.net], x, y, VIA_VIP[0] / 2) and \
                    ck.via_ok(pd.net, x, y, VIA_VIP[0], VIA_VIP[1], own=pd, vip=True):
                via(pd.net, x, y, *VIA_VIP)
                stats["via-in-pad"] += 1
                continue
            rest.append(pd)
            continue
        if _is_ep(pd, fp) and not has_via_inside(pd):
            x0, y0, x1, y1 = pd.bb
            rad = VIA[0] / 2
            pitch = 1.0
            nx = max(1, min(5, int((x1 - x0 - 2 * (rad + 0.1)) / pitch) + 1))
            ny = max(1, min(5, int((y1 - y0 - 2 * (rad + 0.1)) / pitch) + 1))
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            k = 0
            for i in range(nx):
                for j in range(ny):
                    x = round(cx + (i - (nx - 1) / 2) * pitch, 3)
                    y = round(cy + (j - (ny - 1) / 2) * pitch, 3)
                    if not any(pd.shape(l).Collide(_v(x, y), 0) for l in pd.layers):
                        continue
                    if _in_fill(fills[pd.net], x, y, rad) and \
                            ck.via_ok(pd.net, x, y, VIA[0], VIA[1], own=pd, vip=True):
                        via(pd.net, x, y, *VIA)
                        k += 1
            if k:
                stats["EP arrays"] += 1
                stats["EP vias"] += k
                continue
        rest.append(pd)

    # --- 2. dog-bones
    for pass_reach, strict in PASSES:
        nxt = []
        for pd in rest:
            if not _dogbone(pd, ck, fills[pd.net], reuse[pd.net], ncls, via, track, pass_reach, strict, stats):
                nxt.append(pd)
        rest = nxt
    for pd in rest:
        failed.append(pd)
    for z in to_fill:     # refilled by apply_routing (or left unfilled with --no-fill)
        z.UnFill()
    print("f_fanout: removed %d old items; %d pads to fan out; %s; %d failed" %
          (n_old, len(todo), ", ".join("%s %d" % kv for kv in sorted(stats.items())), len(failed)))
    if failed:
        byn = Counter(pd.net for pd in failed)
        print("  failed by net:", ", ".join("%s %d" % kv for kv in byn.most_common()))
        print("  failed by reason:", ", ".join("%s %d" % kv for kv in Counter(pd.why for pd in failed).most_common()))
        if os.environ.get("FANOUT_DEBUG"):
            for pd in failed:
                print("   ", pd.ref, pd.num, pd.net, pd.why)
        print("  failed pads:", " ".join("%s.%s" % (pd.ref, pd.num) for pd in failed[:200]))


def _lname(layer):
    return {pcbnew.F_Cu: "F.Cu", pcbnew.B_Cu: "B.Cu", pcbnew.In1_Cu: "In1.Cu", pcbnew.In2_Cu: "In2.Cu",
            pcbnew.In3_Cu: "In3.Cu", pcbnew.In4_Cu: "In4.Cu"}[layer]


def _dogbone(pd, ck, fills, reuse, ncls, via, track, reach, strict, stats):
    p = pd.p
    layer = pcbnew.F_Cu if p.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
    if not p.IsOnLayer(layer):
        return False
    shp = pd.shape(layer)
    cx, cy = MM(p.GetPosition().x), MM(p.GetPosition().y)
    fp = pd.fp
    cyd = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd)
    if cyd.OutlineCount():
        bb = cyd.BBox()
        bx, by = MM(bb.Centre().x), MM(bb.Centre().y)
    else:
        bx, by = MM(fp.GetPosition().x), MM(fp.GetPosition().y)
    ox, oy = cx - bx, cy - by
    olen = math.hypot(ox, oy)
    out_ang = math.atan2(oy, ox) if olen > 0.05 else None
    rad = VIA[0] / 2
    widths = _widths(pd.net, ncls)
    cands = []
    # reuse an existing via that reaches the plane
    for rv in reuse:
        if rv[2] <= 0:
            continue
        d = math.hypot(rv[0] - cx, rv[1] - cy)
        if d < reach + 2.0:
            cands.append((d - 0.6, rv[0], rv[1], rv))
    for k in range(32):
        a = 2 * math.pi * k / 32
        ux, uy = math.cos(a), math.sin(a)
        # exit distance of the ray from the pad outline
        t = 0.0
        while shp.Collide(_v(cx + ux * t, cy + uy * t), 0) and t < 10:
            t += 0.025
        dev = 0.0 if out_ang is None else abs((a - out_ang + math.pi) % (2 * math.pi) - math.pi)
        s = t
        while s < t + reach + rad:
            x, y = round(cx + ux * s, 3), round(cy + uy * s, 3)
            s += 0.05
            if shp.Collide(_v(x, y), mm(rad) - 1):
                continue
            cost = (s - t) + 0.6 * dev
            cands.append((cost, x, y, None))
    cands.sort(key=lambda c: c[0])
    # elbows for "toe first, then turn" escapes: along the pad axes / diagonals, just past the pad outline
    elbows = []
    po = p.GetOrientation().AsRadians() if hasattr(p.GetOrientation(), "AsRadians") else 0.0
    for k in range(8):
        a = po + math.pi * k / 4
        dev = 0.0 if out_ang is None else abs((a - out_ang + math.pi) % (2 * math.pi) - math.pi)
        if dev > 1.75:
            continue
        ux, uy = math.cos(a), math.sin(a)
        t = 0.0
        while shp.Collide(_v(cx + ux * t, cy + uy * t), 0) and t < 10:
            t += 0.025
        for e in (0.12, 0.25, 0.4, 0.6, 0.85):
            elbows.append((round(cx + ux * (t + e), 3), round(cy + uy * (t + e), 3)))
    tried = 0
    n_fill = n_via = 0
    trace = [] if os.environ.get("FANOUT_TRACE") == "%s.%s" % (pd.ref, pd.num) else None
    for cost, x, y, rv in cands:
        if rv is None:
            if not ck.via_ok(pd.net, x, y, VIA[0], VIA[1], own=pd, side=layer, strict=strict):
                continue
            n_via += 1
            if not _in_fill(fills, x, y, rad):
                continue
            n_fill += 1
        tried += 1
        path = None
        for w in widths:
            st = _start(ck, shp, cx, cy, x, y, w)
            if st and ck.track_ok(pd.net, st, (x, y), w, layer, own=pd, trace=trace):
                path = [st, (x, y)]
                break
        if path is None:
            els = sorted(elbows, key=lambda q: math.hypot(q[0] - cx, q[1] - cy) + math.hypot(x - q[0], y - q[1]))
            for w in widths:
                for q in els:
                    if math.hypot(x - q[0], y - q[1]) < 0.05:
                        continue
                    st = _start(ck, shp, cx, cy, q[0], q[1], w)
                    if st and ck.track_ok(pd.net, st, q, w, layer, own=pd) and \
                            ck.track_ok(pd.net, q, (x, y), w, layer, own=pd):
                        path = [st, q, (x, y)]
                        break
                if path:
                    break
        if path:
            if rv is None:
                via(pd.net, x, y, *VIA)
                reuse.append([x, y, 1])
                stats["dog-bones"] += 1
            else:
                rv[2] -= 1
                stats["reused vias"] += 1
            for a_, b_ in zip(path, path[1:]):
                track(pd.net, a_, b_, w, layer)
            return True
        if tried > 120:
            break
    if trace is not None:
        for t_ in trace[:40]:
            print("    trace", pd.ref, pd.num, t_)
    pd.why = "no legal via spot" if not n_via and not any(c[3] for c in cands) else \
        ("no plane under the legal spots" if not n_fill and not any(c[3] for c in cands) else "track blocked")
    return False


def _start(ck, shp, cx, cy, x, y, w):
    """Track start: the pad centre, or (edge-mounted pads) the first point towards the via that is inside the pad
    and keeps the 0.3 mm copper-to-edge clearance."""
    d = math.hypot(x - cx, y - cy)
    k = 0.0
    while k < d:
        px, py = cx + (x - cx) * k / d, cy + (y - cy) * k / d
        if not shp.Collide(_v(px, py), 0):
            return None
        if ck.edge_ok(px, py, w / 2 + 0.33):
            return (round(px, 4), round(py, 4))
        k += 0.05
    return None
