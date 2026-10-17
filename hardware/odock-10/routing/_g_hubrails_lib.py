"""Raster (bit-row) maze router for the g_hubrails region script (not a routing script: leading underscore).

Model
- A grid of STEP mm cells over a rectangle (the region + margin). Every mask is a dict row -> int (bit i = column i).
- Copper of every net is rasterised per copper layer, *inflated* by HALF_DIAG so that "cell centre outside the
  dilated mask" guarantees the real clearance (conservative). A second, *exact* raster (cell centre inside the real
  copper) is kept per connectivity cluster: a path ending on such a cell really touches that copper.
- Obstacles for a job (net N, track width w) = dilate(other-net copper, w/2 + clearance + HALF_DIAG); HV / HS
  (track-track 0.3 mm) clearances, holes, rule areas (no-track / no-via) and the allowed-area mask are added.
- Clusters come from KiCad connectivity after a zone fill (GND_L1/GND_L6 excluded, like f_fanout).
- Dijkstra over (cell, layer) on the routing layers L1/L3/L6, 8-connected (45 deg corners only, turns > 90 deg
  forbidden), vias where the via mask is free. Goals: exact copper of the target clusters on a routing layer, or a
  via landing inside the filled plane of the same net on an inner layer.
"""
import math
import heapq
from collections import defaultdict
import pcbnew

mm, MM = pcbnew.FromMM, pcbnew.ToMM
STEP = 0.025
HALF_DIAG = 0.018
CU6 = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu]
LNAME = {pcbnew.F_Cu: "F.Cu", pcbnew.In1_Cu: "In1.Cu", pcbnew.In2_Cu: "In2.Cu", pcbnew.In3_Cu: "In3.Cu",
         pcbnew.In4_Cu: "In4.Cu", pcbnew.B_Cu: "B.Cu"}
ROUTE_LAYERS = [pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
INNER_PLANES = [pcbnew.In1_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu]


def short(n):
    return str(n).split("/")[-1]


def _rings(sps):
    out = []
    for i in range(sps.OutlineCount()):
        for ch in [sps.Outline(i)] + [sps.Hole(i, h) for h in range(sps.HoleCount(i))]:
            out.append([(MM(ch.CPoint(k).x), MM(ch.CPoint(k).y)) for k in range(ch.PointCount())])
    return out


def OR(a, b):
    """a |= b (row dicts)."""
    for j, m in b.items():
        a[j] = a.get(j, 0) | m
    return a


class Grid:
    def __init__(self, x0, y0, x1, y1, step=STEP):
        self.x0, self.y0, self.s = x0, y0, step
        self.nx = int(round((x1 - x0) / step)) + 1
        self.ny = int(round((y1 - y0) / step)) + 1
        self.full = (1 << self.nx) - 1

    def X(self, i):
        return round(self.x0 + i * self.s, 4)

    def Y(self, j):
        return round(self.y0 + j * self.s, 4)

    def ci(self, x):
        return int(round((x - self.x0) / self.s))

    def cj(self, y):
        return int(round((y - self.y0) / self.s))

    # ---- rasterisers (cell centre inside -> bit set)
    def rings(self, rings, out=None):
        out = {} if out is None else out
        s, x0, y0 = self.s, self.x0, self.y0
        cross = defaultdict(list)
        for ring in rings:
            n = len(ring)
            for k in range(n):
                xa, ya = ring[k]
                xb, yb = ring[(k + 1) % n]
                if ya == yb:
                    continue
                if ya > yb:
                    xa, ya, xb, yb = xb, yb, xa, ya
                j0 = max(0, int(math.ceil((ya - y0) / s - 1e-9)))
                j1 = min(self.ny - 1, int(math.ceil((yb - y0) / s - 1e-9)) - 1)
                if j1 < j0:
                    continue
                k_ = (xb - xa) / (yb - ya)
                for j in range(j0, j1 + 1):
                    cross[j].append(xa + (y0 + j * s - ya) * k_)
        for j, xs in cross.items():
            xs.sort()
            m = 0
            for a, b in zip(xs[0::2], xs[1::2]):
                i0 = max(0, int(math.ceil((a - x0) / s - 1e-9)))
                i1 = min(self.nx - 1, int(math.floor((b - x0) / s + 1e-9)))
                if i1 >= i0:
                    m |= ((1 << (i1 - i0 + 1)) - 1) << i0
            if m:
                out[j] = out.get(j, 0) | m
        return out

    def capsule(self, ax, ay, bx, by, r, out=None):
        out = {} if out is None else out
        s, x0, y0 = self.s, self.x0, self.y0
        j0 = max(0, int(math.ceil((min(ay, by) - r - y0) / s)))
        j1 = min(self.ny - 1, int(math.floor((max(ay, by) + r - y0) / s)))
        dx, dy = bx - ax, by - ay
        L = math.hypot(dx, dy)
        for j in range(j0, j1 + 1):
            y = y0 + j * s
            lo, hi = 1e18, -1e18
            for cx, cy in ((ax, ay), (bx, by)):
                h = r * r - (y - cy) ** 2
                if h >= 0:
                    h = math.sqrt(h)
                    lo, hi = min(lo, cx - h), max(hi, cx + h)
            if L > 1e-9:
                ux, uy = dx / L, dy / L
                nx_, ny_ = -uy, ux
                # t = (x-ax)ux + (y-ay)uy in [0, L];  s = (x-ax)nx + (y-ay)ny in [-r, r]
                a_lo, a_hi = -1e18, 1e18
                ok = True
                for coef, const, lo_v, hi_v in ((ux, (y - ay) * uy, 0.0, L), (nx_, (y - ay) * ny_, -r, r)):
                    if abs(coef) < 1e-12:
                        if not (lo_v <= const <= hi_v):
                            ok = False
                        continue
                    p, q = (lo_v - const) / coef, (hi_v - const) / coef
                    if p > q:
                        p, q = q, p
                    a_lo, a_hi = max(a_lo, p), min(a_hi, q)
                if ok and a_lo <= a_hi:
                    lo, hi = min(lo, ax + a_lo), max(hi, ax + a_hi)
            if hi < lo:
                continue
            i0 = max(0, int(math.ceil((lo - x0) / s - 1e-9)))
            i1 = min(self.nx - 1, int(math.floor((hi - x0) / s + 1e-9)))
            if i1 >= i0:
                out[j] = out.get(j, 0) | (((1 << (i1 - i0 + 1)) - 1) << i0)
        return out

    def circle(self, cx, cy, r, out=None):
        return self.capsule(cx, cy, cx, cy, r, out)

    def rect(self, x0, y0, x1, y1, out=None):
        return self.rings([[(x0, y0), (x1, y0), (x1, y1), (x0, y1)]], out)

    # ---- morphology
    def hdil(self, m, d):
        k = 0
        while k < d:
            st = min(k + 1, d - k)
            m = m | (m << st) | (m >> st)
            k += st
        return m & self.full

    def dilate(self, rows, R, jlo=0, jhi=None):
        """Disc dilation (strict: cells at distance < R mm from a set cell). Only output rows jlo..jhi."""
        jhi = self.ny - 1 if jhi is None else jhi
        Rc = R / self.s
        K = int(math.ceil(Rc))
        prof = []
        for dy in range(-K, K + 1):
            v = Rc * Rc - dy * dy
            if v <= 0:
                continue
            d = int(math.ceil(math.sqrt(v))) - 1
            if d * d + dy * dy >= Rc * Rc:
                d -= 1
            if d >= 0:
                prof.append((dy, d))
        out = {}
        for j, m in rows.items():
            if j < jlo - K or j > jhi + K or not m:
                continue
            cache = {}
            for dy, d in prof:
                jj = j + dy
                if jj < jlo or jj > jhi:
                    continue
                hd = cache.get(d)
                if hd is None:
                    hd = cache[d] = self.hdil(m, d)
                out[jj] = out.get(jj, 0) | hd
        return out


def AND_NOT(a, b):
    out = {}
    for j, m in a.items():
        v = m & ~b.get(j, 0)
        if v:
            out[j] = v
    return out


def AND(a, b):
    out = {}
    for j, m in a.items():
        v = m & b.get(j, 0)
        if v:
            out[j] = v
    return out


class Item:
    __slots__ = ("kind", "net", "obj", "layers", "uuid", "ref", "num", "pos", "smd")


class BitRouter:
    """See module docstring. `allowed`: list of (x0,y0,x1,y1) rectangles where copper may go (tracks: centre-line
    kept hw inside, vias: fully inside)."""

    def __init__(self, board, r, bounds, allowed, hv_nets, hs_nets, skip_zones=(), log=print, soft_pours=True):
        self.board, self.r, self.log = board, r, log
        self.g = G = Grid(*bounds)
        self.pour_soft = {l: {} for l in CU6}
        self.pour_hard = {l: {} for l in CU6}   # pour copper: keep the zones' own 0.3 mm clearance (no pull-back)
        self.pour_strict = {l: {} for l in CU6}  # pours we had to harden: no vias of other nets either
        self.zone_band = []            # [zone name, layer, net, soft band rows, fill rows]
        self.zone_rows = {}            # zone name -> [(layer, net, fill rows)]
        self.zone_obj = {}
        self.hv_nets, self.hs_nets = set(hv_nets), set(hs_nets)
        self.allowed = allowed
        bx0, by0 = bounds[0], bounds[1]
        bx1, by1 = G.X(G.nx - 1), G.Y(G.ny - 1)

        def inb(bb):
            return not (bb[2] < bx0 - 1 or bb[0] > bx1 + 1 or bb[3] < by0 - 1 or bb[1] > by1 + 1)
        # copper (inflated) per layer: net -> rows ; aggregated any / hv / hs-tracks per layer
        self.cu = {l: defaultdict(dict) for l in CU6}
        self.holes = defaultdict(dict)           # net -> rows (hole discs, inflated)
        self.smdpads = {}                         # rows: every SMD pad on F/B (no via-in-pad)
        self.pad_rows = {l: {} for l in CU6}      # exact pad copper per layer per net
        self.pad_all = {l: {} for l in CU6}
        self.hs_tr = {l: {} for l in ROUTE_LAYERS}
        # exact copper per item (for cluster rasters): uuid -> {layer: rows}
        self.exact = {}
        self.items = {}
        self.planes = defaultdict(lambda: defaultdict(dict))   # net -> zone uuid -> rows (inner-layer fill)
        self.zone_net = {}
        for fp in board.GetFootprints():
            for p in fp.Pads():
                b = p.GetBoundingBox()
                bb = (MM(b.GetLeft()), MM(b.GetTop()), MM(b.GetRight()), MM(b.GetBottom()))
                if not inb(bb):
                    continue
                net = short(p.GetNetname()) if p.GetNetCode() > 0 else "~" + fp.GetReference() + "." + p.GetNumber()
                it = Item()
                it.kind, it.net, it.obj, it.ref, it.num = "pad", net, p, fp.GetReference(), p.GetNumber()
                it.uuid = p.m_Uuid.AsString()
                it.pos = (MM(p.GetPosition().x), MM(p.GetPosition().y))
                it.smd = p.GetAttribute() in (pcbnew.PAD_ATTRIB_SMD, pcbnew.PAD_ATTRIB_CONN)
                it.layers = [l for l in CU6 if p.IsOnLayer(l)]
                self.items[it.uuid] = it
                ex = {}
                for l in it.layers:
                    sp = pcbnew.SHAPE_POLY_SET()
                    p.TransformShapeToPolygon(sp, l, mm(HALF_DIAG), mm(0.005), pcbnew.ERROR_OUTSIDE)
                    G.rings(_rings(sp), self.cu[l][net])
                    sp = pcbnew.SHAPE_POLY_SET()
                    p.TransformShapeToPolygon(sp, l, 0, mm(0.005), pcbnew.ERROR_INSIDE)
                    ex[l] = G.rings(_rings(sp))
                    if it.smd and l in (pcbnew.F_Cu, pcbnew.B_Cu):
                        OR(self.smdpads, ex[l])
                    if l in ROUTE_LAYERS:
                        OR(self.pad_rows[l].setdefault(net, {}), ex[l])
                        OR(self.pad_all[l], ex[l])
                self.exact[it.uuid] = ex
                if p.GetDrillSizeX() > 0:
                    hs = p.GetEffectiveHoleShape()
                    a, c = hs.GetSeg().A, hs.GetSeg().B
                    G.capsule(MM(a.x), MM(a.y), MM(c.x), MM(c.y), MM(hs.GetWidth()) / 2 + HALF_DIAG,
                              self.holes[net])
        for t in board.GetTracks():
            b = t.GetBoundingBox()
            bb = (MM(b.GetLeft()), MM(b.GetTop()), MM(b.GetRight()), MM(b.GetBottom()))
            if not inb(bb):
                continue
            self._add_track_item(t)
        for z in board.Zones():
            if z.GetIsRuleArea() or z.GetZoneName() in skip_zones or not z.GetNetname():
                continue
            net = short(z.GetNetname())
            uid = z.m_Uuid.AsString()
            self.zone_net[uid] = net
            it = Item()
            it.kind, it.net, it.obj, it.uuid, it.layers = "zone", net, z, uid, []
            self.items[uid] = it
            ex = {}
            for l in CU6:
                if not z.IsOnLayer(l):
                    continue
                fl = z.GetFilledPolysList(l)
                if fl.OutlineCount() == 0:
                    continue
                bb = fl.BBox()
                if not inb((MM(bb.GetLeft()), MM(bb.GetTop()), MM(bb.GetRight()), MM(bb.GetBottom()))):
                    continue
                rows = G.rings(_rings(fl))
                self.zone_rows.setdefault(z.GetZoneName(), []).append((l, net, rows))
                self.zone_obj[z.GetZoneName()] = z
                it.layers.append(l)
                if l in ROUTE_LAYERS:
                    # pours on signal layers: other nets' tracks keep the pour's own 0.3 mm (no pull-back), except
                    # in a band within 0.9 mm of a pad of another net in the pour's cut-outs (nibbled at a cost, lets
                    # a boxed-in pin out); a via inside a pour only costs (the pour refills around the hole).
                    # Switch-node, hot-loop GND and HV pours are strict: no tracks, no vias of other nets.
                    name = z.GetZoneName()
                    if soft_pours and not ("SW" in name or "HOT" in name or net in self.hv_nets):
                        # band: pour copper within 0.6 mm of a pad of another net sitting in the pour's cut-outs
                        oth = AND_NOT(self.pad_all[l], self.pad_rows[l].get(net, {}))
                        near = G.dilate(oth, 0.3 + 0.6)
                        band = AND(rows, near)
                        OR(self.pour_hard[l].setdefault(net, {}), AND_NOT(rows, band))
                        OR(self.pour_soft[l], band)
                        self.zone_band.append([name, l, net, band, rows])
                    else:
                        OR(self.pour_hard[l].setdefault(net, {}), rows)
                        OR(self.pour_strict[l].setdefault(net, {}), rows)
                    ex[l] = rows
                else:
                    self.planes[net][uid] = rows
            self.exact[uid] = ex
        # rule areas
        self.ko_tr = {l: {} for l in ROUTE_LAYERS}
        self.ko_via = {}
        for z in board.Zones():
            if not z.GetIsRuleArea():
                continue
            rows = None
            if z.GetDoNotAllowTracks() or z.GetDoNotAllowVias():
                rows = G.rings(_rings(z.Outline()))
            if not rows:
                continue
            if z.GetDoNotAllowVias():
                OR(self.ko_via, rows)
            if z.GetDoNotAllowTracks():
                for l in ROUTE_LAYERS:
                    if z.IsOnLayer(l):
                        OR(self.ko_tr[l], rows)
        self.allowed_rows = {}
        for a in allowed:
            G.rect(*a, out=self.allowed_rows)
        self.extra_novia = {}
        self.pen_tr = {l: {} for l in ROUTE_LAYERS}   # soft-cost areas (cost PEN per cell) per layer
        self.pen_via = {}                              # soft-cost via areas (cost PEN_VIA)
        self.PEN, self.PEN_VIA = 3.0, 100.0
        self.extra_notrack = {l: {} for l in ROUTE_LAYERS}
        self.drawn = []
        self._agg()
        # snapshot of the copper that was on the board before us (hard obstacles in soft mode / rip-up rebuilds)
        self.fixed_cu = {l: {n: dict(rows) for n, rows in self.cu[l].items()} for l in CU6}
        self.fixed_holes = {n: dict(rows) for n, rows in self.holes.items()}
        self.any_fixed = {l: dict(self.any[l]) for l in CU6}
        self.holes_fixed_all = dict(self.holes_all)
        self.units = {}          # uid -> {"net", "items": [board items], "rows": {layer: rows}, "holes": rows}
        self.cur = None          # uid receiving new copper
        self.mine_any = {l: {} for l in CU6}
        self.mine_holes = {}

    # ------------------------------------------------------------------ bookkeeping
    def _add_track_item(self, t, add_obj=True):
        G = self.g
        net = short(t.GetNetname())
        it = Item()
        it.kind, it.net, it.obj, it.uuid = ("via" if t.GetClass() == "PCB_VIA" else "trk"), net, t, \
            t.m_Uuid.AsString()
        ex = {}
        if it.kind == "via":
            p = t.GetPosition()
            x, y = MM(p.x), MM(p.y)
            rad = MM(t.GetWidth(pcbnew.F_Cu)) / 2
            top, bot = t.TopLayer(), t.BottomLayer()
            it.layers = [l for l in CU6 if t.IsOnLayer(l)]
            for l in it.layers:
                G.circle(x, y, rad + HALF_DIAG, self.cu[l][net])
                ex[l] = G.circle(x, y, rad - 0.01)
            G.circle(x, y, MM(t.GetDrillValue()) / 2 + HALF_DIAG, self.holes[net])
        else:
            a, b = t.GetStart(), t.GetEnd()
            ax, ay, bx, by = MM(a.x), MM(a.y), MM(b.x), MM(b.y)
            w = MM(t.GetWidth())
            l = t.GetLayer()
            it.layers = [l]
            G.capsule(ax, ay, bx, by, w / 2 + HALF_DIAG, self.cu[l][net])
            if net in self.hs_nets and l in ROUTE_LAYERS:
                G.capsule(ax, ay, bx, by, w / 2 + HALF_DIAG, self.hs_tr[l])
            ex[l] = G.capsule(ax, ay, bx, by, w / 2 - 0.01)
        self.items[it.uuid] = it
        self.exact[it.uuid] = ex
        return it

    def _agg(self):
        self.any = {}
        self.hv = {}
        for l in CU6:
            a, h = {}, {}
            for net, rows in self.cu[l].items():
                OR(a, rows)
                if net in self.hv_nets:
                    OR(h, rows)
            self.any[l], self.hv[l] = a, h
        self.holes_all = {}
        for rows in self.holes.values():
            OR(self.holes_all, rows)

    def _unit(self):
        u = self.units.get(self.cur)
        if u is None:
            u = self.units[self.cur] = {"net": None, "items": [], "rows": defaultdict(dict), "holes": {}, "geom": []}
        return u

    def add_copper(self, net, kind, geom, layer=None):
        """Register new copper (track/via we drew) in the obstacle rasters; returns exact rows per layer."""
        G = self.g
        ex = {}
        u = self._unit()
        u["net"] = net
        if kind == "via":
            x, y, size, drill = geom
            for l in CU6:
                rows = G.circle(x, y, size / 2 + HALF_DIAG)
                OR(self.cu[l][net], rows)
                OR(self.any[l], rows)
                OR(u["rows"][l], rows)
                OR(self.mine_any[l], rows)
                if net in self.hv_nets:
                    OR(self.hv[l], rows)
                ex[l] = G.circle(x, y, size / 2 - 0.01)
            hr = G.circle(x, y, drill / 2 + HALF_DIAG)
            OR(self.holes[net], hr)
            OR(self.holes_all, hr)
            OR(u["holes"], hr)
            OR(self.mine_holes, hr)
        else:
            (ax, ay), (bx, by), w = geom
            rows = G.capsule(ax, ay, bx, by, w / 2 + HALF_DIAG)
            OR(self.cu[layer][net], rows)
            OR(self.any[layer], rows)
            OR(u["rows"][layer], rows)
            OR(self.mine_any[layer], rows)
            if net in self.hv_nets:
                OR(self.hv[layer], rows)
            ex[layer] = G.capsule(ax, ay, bx, by, w / 2 - 0.01)
        return ex

    def remove_unit(self, uid):
        """Rip up everything unit `uid` drew (board items + rasters)."""
        u = self.units.pop(uid, None)
        if u is None:
            return
        for it in u["items"]:
            if self.r.group is not None:
                self.r.group.RemoveItem(it)
            self.board.Remove(it)
        net = u["net"]
        if net is None:
            return
        same = [v for v in self.units.values() if v["net"] == net]
        for l in CU6:
            rows = dict(self.fixed_cu[l].get(net, {}))
            for v in same:
                OR(rows, v["rows"].get(l, {}))
            self.cu[l][net] = rows
        hr = dict(self.fixed_holes.get(net, {}))
        for v in same:
            OR(hr, v["holes"])
        self.holes[net] = hr
        self._agg()
        self.mine_any = {l: {} for l in CU6}
        self.mine_holes = {}
        for v in self.units.values():
            for l, rows in v["rows"].items():
                OR(self.mine_any[l], rows)
            OR(self.mine_holes, v["holes"])

    def harden(self, zone_name):
        """Make the soft edge band of a pour hard again (it got split by our copper)."""
        for l, net, rows in self.zone_rows.get(zone_name, []):
            if l in ROUTE_LAYERS:
                OR(self.pour_hard[l].setdefault(net, {}), rows)
                OR(self.pour_strict[l].setdefault(net, {}), rows)
        for e in self.zone_band:
            if e[0] == zone_name:
                e[3] = {}
        self.pour_soft = {l: {} for l in CU6}
        for e in self.zone_band:
            OR(self.pour_soft[e[1]], e[3])
        self._agg()
        self.any_fixed = {l: {} for l in CU6}
        for l in CU6:
            for rows in self.fixed_cu[l].values():
                OR(self.any_fixed[l], rows)

    # ---- inner-plane split guard (coarse raster connectivity over the whole zone, not just our grid)
    CSTEP = 0.1

    def _coarse_init(self, gnd_like=("GND",)):
        self.coarse = {}
        for name, ents in self.zone_rows.items():
            for l, net, rows in ents:
                if l in ROUTE_LAYERS or net in gnd_like:
                    continue
                fl = self.zone_obj[name].GetFilledPolysList(l)
                bb = fl.BBox()
                G2 = Grid(MM(bb.GetLeft()) - 0.2, MM(bb.GetTop()) - 0.2, MM(bb.GetRight()) + 0.2,
                          MM(bb.GetBottom()) + 0.2, self.CSTEP)
                rr = G2.rings(_rings(fl))
                W, H = G2.nx, G2.ny
                bm = bytearray(W * H)
                for j, m in rr.items():
                    if m:
                        bits = format(m, "0%db" % W)[::-1].encode()
                        bm[j * W:(j + 1) * W] = bytes(1 if c == 49 else 0 for c in bits)
                self.coarse[name] = [net, bm, W, H, None, G2]
        for name, e in self.coarse.items():
            e[4] = self._pieces(e, [])

    def _pieces(self, e, vias):
        net, bm, W, H, _, G2 = e
        b = bytearray(bm)
        s = G2.s
        for x, y, size in vias:
            r = size / 2 + 0.3 + 0.07
            ci0, ci1 = int((x - r - G2.x0) / s), int((x + r - G2.x0) / s) + 1
            cj0, cj1 = int((y - r - G2.y0) / s), int((y + r - G2.y0) / s) + 1
            for cj in range(max(0, cj0), min(H - 1, cj1) + 1):
                for ci in range(max(0, ci0), min(W - 1, ci1) + 1):
                    if (G2.x0 + ci * s - x) ** 2 + (G2.y0 + cj * s - y) ** 2 < r * r:
                        b[cj * W + ci] = 0
        seen = bytearray(W * H)
        n = 0
        N = W * H
        for k0 in range(N):
            if not b[k0] or seen[k0]:
                continue
            stack = [k0]
            seen[k0] = 1
            size = 0
            while stack:
                k = stack.pop()
                size += 1
                ci = k % W
                if ci > 0 and b[k - 1] and not seen[k - 1]:
                    seen[k - 1] = 1
                    stack.append(k - 1)
                if ci < W - 1 and b[k + 1] and not seen[k + 1]:
                    seen[k + 1] = 1
                    stack.append(k + 1)
                if k >= W and b[k - W] and not seen[k - W]:
                    seen[k - W] = 1
                    stack.append(k - W)
                if k + W < N and b[k + W] and not seen[k + W]:
                    seen[k + W] = 1
                    stack.append(k + W)
            if size >= 30:
                n += 1
        return n

    def split_check(self, net, new_vias):
        """Inner planes (other nets) that our vias, with `new_vias` added, cut into more pieces."""
        if not hasattr(self, "coarse"):
            self._coarse_init()
        bad = []
        for name, e in self.coarse.items():
            if e[0] == net:
                continue
            G2, W, H = e[5], e[2], e[3]
            touch = False
            for x, y, size in new_vias:
                ci, cj = int((x - G2.x0) / G2.s), int((y - G2.y0) / G2.s)
                for dj in (-6, 0, 6):
                    for di in (-6, 0, 6):
                        if 0 <= ci + di < W and 0 <= cj + dj < H and e[1][(cj + dj) * W + ci + di]:
                            touch = True
            if not touch:
                continue
            vias = [(g[1], g[2], g[3]) for u in self.units.values() if u["net"] != e[0]
                    for g in u["geom"] if g[0] == "via"]
            if self._pieces(e, vias) > e[4]:
                bad.append(name)
        return bad

    def units_in(self, zone_name):
        """Units (any net but the zone's) with copper inside a zone's fill."""
        out = set()
        for l, net, rows in self.zone_rows.get(zone_name, []):
            for uid, u in self.units.items():
                if u["net"] == net:
                    continue
                ur = u["rows"].get(l)
                if not ur:
                    continue
                ur = self.g.dilate(ur, 0.32)       # the zone keeps 0.3 mm from our copper
                if any(m & rows.get(j, 0) for j, m in ur.items()):
                    out.add(uid)
        return out

    def conflicts(self, net, drawn, width, via, clr=0.15):
        """Units (other nets) whose copper is within clearance of the would-be copper `drawn`."""
        G = self.g
        foot = defaultdict(dict)
        for d in drawn:
            if d[0] == "via":
                x, y = d[1]
                for l in CU6:
                    G.circle(x, y, via[0] / 2 + clr + 2 * HALF_DIAG, foot[l])
            else:
                _, l, xy = d
                for a, b in zip(xy, xy[1:]):
                    G.capsule(a[0], a[1], b[0], b[1], width / 2 + clr + 2 * HALF_DIAG, foot[l])
        out = set()
        for uid, u in self.units.items():
            if u["net"] == net:
                continue
            for l, rows in foot.items():
                ur = u["rows"].get(l)
                if ur and any(m & ur.get(j, 0) for j, m in rows.items()):
                    out.add(uid)
                    break
        return out

    # ------------------------------------------------------------------ clusters
    def clusters(self, conn, net_full, region_test):
        """Connectivity clusters of a net (list of dicts: uuids, pads, exact rows per layer, plane rows)."""
        pads = []
        for fp in self.board.GetFootprints():
            for p in fp.Pads():
                if p.GetNetname() == net_full:
                    pads.append(p)
        seen = set()
        out = []
        for p in pads:
            u = p.m_Uuid.AsString()
            if u in seen:
                continue
            members = {u}
            for it in conn.GetConnectedItems(p):
                if it.GetNetname() == net_full:
                    members.add(it.m_Uuid.AsString())
            seen |= members
            out.append(self._mk_cluster(members))
        return out

    def _mk_cluster(self, members):
        c = {"uuids": set(members), "rows": defaultdict(dict), "plane": {}, "pads": []}
        for u in members:
            it = self.items.get(u)
            if it is None:
                continue
            if it.kind == "pad":
                c["pads"].append(it)
            for l, rows in self.exact.get(u, {}).items():
                if l in ROUTE_LAYERS:
                    OR(c["rows"][l], rows)
            if it.kind == "zone":
                for zu, rows in self.planes[it.net].items():
                    if zu == u:
                        OR(c["plane"], rows)
            if it.kind == "via":   # a via reaching an inner plane counts as plane copper only via its zone
                pass
        return c

    @staticmethod
    def merge(a, b):
        a["uuids"] |= b["uuids"]
        for l, rows in b["rows"].items():
            OR(a["rows"][l], rows)
        OR(a["plane"], b["plane"])
        a["pads"] += b["pads"]
        return a

    # ------------------------------------------------------------------ routing
    def route(self, net, src, dsts, width=0.15, via=(0.45, 0.25), window=None, layers=None, via_cost=1.2,
              plane_goal=True, l3_cost=1.15, clr=0.15, max_vias=4, src_layers=None, soft=False, soft_cost=6.0,
              dry=False):
        """Route cluster `src` to any of `dsts`. window: (x0,y0,x1,y1) mm. Returns list of drawn items or None."""
        G = self.g
        layers = layers or ROUTE_LAYERS
        L = len(layers)
        hw = width / 2
        vr = via[0] / 2
        hv = net in self.hv_nets
        if window is None:
            window = (G.x0, G.y0, G.X(G.nx - 1), G.Y(G.ny - 1))
        I0, J0 = max(0, G.ci(window[0])), max(0, G.cj(window[1]))
        I1, J1 = min(G.nx - 1, G.ci(window[2])), min(G.ny - 1, G.cj(window[3]))
        W, H = I1 - I0 + 1, J1 - J0 + 1
        wmask = ((1 << W) - 1)

        def win(rows):
            """row dict -> list of bytearrays (1 = set) over the window."""
            out = []
            for j in range(J0, J1 + 1):
                m = (rows.get(j, 0) >> I0) & wmask
                if not m:
                    out.append(None)
                else:
                    out.append(bytearray(format(m, "0%db" % W)[::-1].encode()))
            return out

        def other(l):
            mine = self.cu[l].get(net, {})
            if soft:     # our own copper of other nets is passable at a cost (rip-up candidates)
                return AND_NOT(self.any_fixed[l], mine), mine
            return AND_NOT(self.any[l], mine), mine

        allowed_tr = self._erode(self.allowed_rows, hw + 0.001, J0, J1)
        allowed_v = self._erode(self.allowed_rows, vr + 0.001, J0, J1)
        blocked = []
        for l in layers:
            oth, mine = other(l)
            b = G.dilate(oth, hw + clr + HALF_DIAG, J0, J1)
            if hv:
                mis = AND_NOT(oth, self.hv[l])
            else:
                mis = AND_NOT(self.hv[l], mine)
            OR(b, G.dilate(mis, hw + 0.3 + HALF_DIAG, J0, J1))
            OR(b, G.dilate(AND_NOT(self.hs_tr[l], mine), hw + 0.3 + HALF_DIAG, J0, J1))
            hol = {}
            for n, rows in (self.fixed_holes if soft else self.holes).items():
                if n != net:
                    OR(hol, rows)
            OR(b, G.dilate(hol, hw + 0.2 + HALF_DIAG, J0, J1))
            ph = {}
            for n, rows in self.pour_hard[l].items():
                if n != net:
                    OR(ph, rows)
            OR(b, G.dilate(ph, hw + 0.3 + HALF_DIAG, J0, J1))
            OR(b, G.dilate(self.ko_tr[l], hw + 0.02, J0, J1))
            OR(b, self.extra_notrack[l])
            # outside allowed area
            for j in range(J0, J1 + 1):
                b[j] = b.get(j, 0) | (~allowed_tr.get(j, 0) & G.full)
            blocked.append(win(b))
        vb = {}
        for l in CU6:
            oth, mine = other(l)
            OR(vb, G.dilate(oth, vr + clr + HALF_DIAG, J0, J1))
            if hv:
                mis = AND_NOT(oth, self.hv[l])
            else:
                mis = AND_NOT(self.hv[l], mine)
            OR(vb, G.dilate(mis, vr + 0.3 + HALF_DIAG, J0, J1))
        OR(vb, G.dilate(self.holes_fixed_all if soft else self.holes_all, via[1] / 2 + 0.2 + 0.02, J0, J1))
        # vias inside another net's pour only cost (the pour refills around the hole); pours we had to harden block
        ph, pst = {}, {}
        for l in ROUTE_LAYERS:
            for n, rows in self.pour_hard[l].items():
                if n != net:
                    OR(ph, rows)
            for n, rows in self.pour_strict[l].items():
                if n != net:
                    OR(pst, rows)
        OR(vb, G.dilate(pst, vr + 0.3 + HALF_DIAG, J0, J1))
        vpour = G.dilate(ph, vr + 0.3 + HALF_DIAG, J0, J1)
        OR(vb, G.dilate(self.smdpads, vr + 0.02, J0, J1))
        OR(vb, G.dilate(self.ko_via, vr + 0.02, J0, J1))
        OR(vb, self.extra_novia)
        for j in range(J0, J1 + 1):
            vb[j] = vb.get(j, 0) | (~allowed_v.get(j, 0) & G.full)
        vblock = win(vb)
        softb, vsoft = None, None
        if soft:
            softb = []
            for l in layers:
                mo = AND_NOT(self.mine_any[l], self.cu[l].get(net, {}))
                softb.append(win(G.dilate(mo, hw + clr + HALF_DIAG, J0, J1)))
            vs = {}
            for l in CU6:
                mo = AND_NOT(self.mine_any[l], self.cu[l].get(net, {}))
                OR(vs, G.dilate(mo, vr + clr + HALF_DIAG, J0, J1))
            OR(vs, G.dilate(self.mine_holes, via[1] / 2 + 0.2 + 0.02, J0, J1))
            vsoft = win(vs)
        scost = soft_cost
        pen = [win(self.pen_tr.get(l, {})) for l in layers]
        if not any(r is not None for p in pen for r in p):
            pen = None
        vpen = win(self.pen_via)
        psoft = [win(self.pour_soft.get(l, {})) for l in layers]
        vps = {}
        for l in ROUTE_LAYERS:
            OR(vps, self.pour_soft[l])
        OR(vps, vpour)
        vpsoft = win(vps)
        PEN, PEN_VIA = self.PEN, self.PEN_VIA
        # goals
        goal = []
        for li, l in enumerate(layers):
            rows = {}
            for d in dsts:
                OR(rows, d["rows"].get(l, {}))
            goal.append(win(rows))
        pgoal = None
        if plane_goal:
            pr = {}
            for d in dsts:
                OR(pr, d["plane"])
            if pr:
                pr = self._erode(pr, vr + 0.08, J0, J1)
                pgoal = win(pr)
        # sources
        starts = []
        for li, l in enumerate(layers):
            if src_layers and l not in src_layers:
                continue
            sw = win(src["rows"].get(l, {}))
            for jj in range(H):
                row = sw[jj]
                if row is None:
                    continue
                brow = blocked[li][jj]
                for ii in range(W):
                    if row[ii] == 49 and (brow is None or brow[ii] != 49):
                        starts.append((ii, jj, li))
        if not starts:
            return None, "no start cell"
        # Dijkstra
        INF = 1e18
        N = W * H * L
        gcost = [INF] * N
        prev = [-1] * N
        pdir = bytearray(N)        # incoming direction index + 1 (0 = none / via)
        nvia = bytearray(N)
        DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
        DC = [1.0, 1.4142, 1.0, 1.4142, 1.0, 1.4142, 1.0, 1.4142]
        lc = [l3_cost if l == pcbnew.In2_Cu else 1.0 for l in layers]
        vcost = via_cost / G.s
        heap = []
        for ii, jj, li in starts:
            k = (li * H + jj) * W + ii
            gcost[k] = 0.0
            heapq.heappush(heap, (0.0, k))
        end = None
        endvia = False
        WH = W * H
        while heap:
            gc, k = heapq.heappop(heap)
            if k >= N:      # plane-via pseudo state
                end, endvia = k - N, True
                break
            if gc > gcost[k]:
                continue
            li, rem = divmod(k, WH)
            jj, ii = divmod(rem, W)
            grow = goal[li][jj]
            if grow is not None and grow[ii] == 49 and gc > 0:
                end = k
                break
            pd = pdir[k]
            for di in range(8):
                if pd:
                    turn = (di - (pd - 1)) % 8
                    if turn in (3, 4, 5):           # > 90 deg turn (acute corner) or reversal
                        continue
                    tp = 0.0 if turn == 0 else (0.4 if turn in (1, 7) else 1.2)
                else:
                    tp = 0.0
                dx, dy = DIRS[di]
                i2, j2 = ii + dx, jj + dy
                if i2 < 0 or j2 < 0 or i2 >= W or j2 >= H:
                    continue
                br = blocked[li][j2]
                if br is not None and br[i2] == 49:
                    continue
                if dx and dy:   # no corner cutting
                    b1, b2 = blocked[li][jj], blocked[li][j2]
                    if (b1 is not None and b1[i2] == 49) or (b2 is not None and b2[ii] == 49):
                        continue
                k2 = (li * H + j2) * W + i2
                ng = gc + DC[di] * lc[li] + tp
                if softb is not None:
                    sr = softb[li][j2]
                    if sr is not None and sr[i2] == 49:
                        ng += scost
                if pen is not None:
                    pr_ = pen[li][j2]
                    if pr_ is not None and pr_[i2] == 49:
                        ng += PEN
                pr_ = psoft[li][j2]
                if pr_ is not None and pr_[i2] == 49:
                    ng += 4.0
                if ng < gcost[k2]:
                    gcost[k2] = ng
                    prev[k2] = k
                    pdir[k2] = di + 1
                    nvia[k2] = nvia[k]
                    heapq.heappush(heap, (ng, k2))
            vrow = vblock[jj]
            if vrow is None or vrow[ii] != 49:
                if nvia[k] < max_vias:
                    for l2 in range(L):
                        if l2 == li:
                            continue
                        br = blocked[l2][jj]
                        if br is not None and br[ii] == 49:
                            continue
                        k2 = (l2 * H + jj) * W + ii
                        ng = gc + vcost
                        pv = vpen[jj]
                        if pv is not None and pv[ii] == 49:
                            ng += PEN_VIA
                        pv = vpsoft[jj]
                        if pv is not None and pv[ii] == 49:
                            ng += 150.0
                        if vsoft is not None:
                            sr = vsoft[jj]
                            if sr is not None and sr[ii] == 49:
                                ng += scost * 10
                        if ng < gcost[k2]:
                            gcost[k2] = ng
                            prev[k2] = k
                            pdir[k2] = 0
                            nvia[k2] = nvia[k] + 1
                            heapq.heappush(heap, (ng, k2))
                if pgoal is not None:
                    pr = pgoal[jj]
                    if pr is not None and pr[ii] == 49:
                        heapq.heappush(heap, (gc + vcost, N + k))
        if end is None:
            import os
            dd = os.environ.get("G_DEBUG")
            if dd:
                for li in range(L):
                    fn = os.path.join(dd, "%s_%d_%d_L%d.pgm" % (net.replace("+", "p").replace("/", "_"), I0, J0, li))
                    sset = set((a, b) for a, b, c in starts if c == li)
                    with open(fn, "wb") as fh:
                        fh.write(b"P5 %d %d 255\n" % (W, H))
                        buf = bytearray()
                        for jj in range(H):
                            br, vr_, gr = blocked[li][jj], vblock[jj], goal[li][jj]
                            pr_ = pgoal[jj] if pgoal is not None else None
                            for ii in range(W):
                                if (ii, jj) in sset:
                                    v = 60
                                elif gr is not None and gr[ii] == 49:
                                    v = 200
                                elif br is not None and br[ii] == 49:
                                    v = 0
                                elif pr_ is not None and pr_[ii] == 49 and (vr_ is None or vr_[ii] != 49):
                                    v = 230
                                elif vr_ is not None and vr_[ii] == 49:
                                    v = 128
                                else:
                                    v = 255
                                buf.append(v)
                        fh.write(bytes(buf))
            return None, "no path"
        # back-track
        path = []
        k = end
        while k != -1:
            li, rem = divmod(k, WH)
            jj, ii = divmod(rem, W)
            path.append((ii + I0, jj + J0, li))
            k = prev[k]
        path.reverse()
        ei, ej, el = path[-1]
        dst = None
        for di_, d in enumerate(dsts):
            if endvia:
                if (d["plane"].get(ej, 0) >> ei) & 1:
                    dst = di_
                    break
            elif (d["rows"].get(layers[el], {}).get(ej, 0) >> ei) & 1:
                dst = di_
                break
        if soft or dry:
            return {"items": self._segments(path, layers, endvia), "dst": dst}, "soft"
        drawn = self._emit(net, path, layers, width, via, endvia)
        drawn["dst"] = dst
        return drawn, "ok"

    def ring(self, window, width=0.3):
        """Synthetic destination: the border band of `window` on every routing layer (escape checks)."""
        rows = {}
        x0, y0, x1, y1 = window
        self.g.rings([[(x0, y0), (x1, y0), (x1, y1), (x0, y1)]], rows)
        inner = self.g.rings([[(x0 + width, y0 + width), (x1 - width, y0 + width), (x1 - width, y1 - width),
                               (x0 + width, y1 - width)]])
        band = AND_NOT(rows, inner)
        return {"uuids": set(), "rows": defaultdict(dict, {l: dict(band) for l in ROUTE_LAYERS}), "plane": {},
                "pads": []}

    def _in_src_pad(self, src, i, j):
        for p in src["pads"]:
            for l, rows in self.exact.get(p.uuid, {}).items():
                if (rows.get(j, 0) >> i) & 1:
                    return True
        return False

    def _erode(self, rows, R, J0, J1):
        G = self.g
        comp = {}
        for j in range(max(0, J0 - 20), min(G.ny - 1, J1 + 20) + 1):
            v = ~rows.get(j, 0) & G.full
            if v:
                comp[j] = v
        d = G.dilate(comp, R, J0, J1)
        out = {}
        for j in range(J0, J1 + 1):
            v = rows.get(j, 0) & ~d.get(j, 0)
            if v:
                out[j] = v
        return out

    def _segments(self, path, layers, endvia):
        G = self.g
        drawn = []
        segs = []
        cur = [path[0]]
        for st in path[1:]:
            if st[2] != cur[-1][2]:
                segs.append(cur)
                cur = [st]
            else:
                cur.append(st)
        segs.append(cur)
        for si, pts in enumerate(segs):
            if si > 0:
                drawn.append(("via", (G.X(pts[0][0]), G.Y(pts[0][1]))))
            if len(pts) >= 2:
                simp = [pts[0]]
                for k in range(1, len(pts) - 1):
                    d1 = (pts[k][0] - simp[-1][0], pts[k][1] - simp[-1][1])
                    d2 = (pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1])
                    if d1[0] * d2[1] - d1[1] * d2[0] != 0:
                        simp.append(pts[k])
                simp.append(pts[-1])
                drawn.append(("trk", layers[pts[0][2]], [(G.X(p[0]), G.Y(p[1])) for p in simp]))
        if endvia:
            drawn.append(("via", (G.X(path[-1][0]), G.Y(path[-1][1]))))
        return drawn

    def _draw_via(self, net, x, y, size, drill):
        v = pcbnew.PCB_VIA(self.board)
        v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        v.SetWidth(mm(size))
        v.SetDrill(mm(drill))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(self.r.net(net))
        self.r._add(v)
        u = self._unit()
        u["items"].append(v)
        u["geom"].append(("via", x, y, size, drill))
        return self.add_copper(net, "via", (x, y, size, drill))

    def _draw_trk(self, net, l, a, b, width):
        t = pcbnew.PCB_TRACK(self.board)
        t.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1])))
        t.SetEnd(pcbnew.VECTOR2I(mm(b[0]), mm(b[1])))
        t.SetWidth(mm(width))
        t.SetLayer(l)
        t.SetNet(self.r.net(net))
        self.r._add(t)
        u = self._unit()
        u["items"].append(t)
        u["geom"].append(("trk", l, a, b, width))
        return self.add_copper(net, "trk", (a, b, width), l)

    def replay(self, uid, net, geoms):
        """Re-draw a unit from its recorded geometry (rip-up undo)."""
        old = self.cur
        self.cur = uid
        for g in geoms:
            if g[0] == "via":
                self._draw_via(net, *g[1:])
            else:
                self._draw_trk(net, *g[1:])
        self.cur = old

    def geom_of(self, uid):
        u = self.units.get(uid)
        return (u["net"], list(u["geom"])) if u else (None, [])

    def _emit(self, net, path, layers, width, via, endvia):
        drawn = self._segments(path, layers, endvia)
        out_ex = defaultdict(dict)
        for d in drawn:
            if d[0] == "via":
                x, y = d[1]
                ex = self._draw_via(net, x, y, via[0], via[1])
            else:
                _, l, xy = d
                ex = {}
                for a, b in zip(xy, xy[1:]):
                    if a == b:
                        continue
                    for ll, rows in self._draw_trk(net, l, a, b, width).items():
                        OR(ex.setdefault(ll, {}), rows)
            for l, rows in ex.items():
                if l in ROUTE_LAYERS:
                    OR(out_ex[l], rows)
        self.drawn.append((net, drawn))
        return {"rows": out_ex, "items": drawn}
