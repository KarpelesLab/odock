"""Shared helpers for a_planes.py / b_power.py (zones, rule areas, legal via placement).

Not a routing script itself (leading underscore: apply_routing.py skips it).
"""
import math
import pcbnew

mm, MM = pcbnew.FromMM, pcbnew.ToMM
CU = {"F.Cu": pcbnew.F_Cu, "In1.Cu": pcbnew.In1_Cu, "In2.Cu": pcbnew.In2_Cu, "In3.Cu": pcbnew.In3_Cu,
      "In4.Cu": pcbnew.In4_Cu, "B.Cu": pcbnew.B_Cu}
ALL_CU = list(CU)

# Board outline (mm) and the copper pull-back used for every zone outline.
BX0, BY0, BX1, BY1 = 100.0, 50.0, 230.0, 139.0
EDGE = 0.5            # zone outline inset from the board edge (DRC copper-to-edge is 0.3)
HOLES = [(104, 54), (226, 54), (104, 135), (226, 135)]   # M3 mounting holes (no net)

# Nets in the HV net class of odock-10.kicad_pro: the .kicad_dru "high voltage" rule wants 0.3 mm between them and
# any non-HV copper (pad-to-pad inside a footprint exempt).
HV_NETS = {"VIN", "VIN_OR", "VBUS_PDIN", "VBAR", "VBUS_LAPTOP", "VBB_OUT", "VBUS_LSW", "BB_SW1", "BB_SW2", "BAR_SW"}


def short(n):
    return str(n).split("/")[-1]


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def board_poly(inset=EDGE, chamfer=2.0):
    """Board outline inset by `inset`, corners chamfered (the outline has rounded corners)."""
    x0, y0, x1, y1 = BX0 + inset, BY0 + inset, BX1 - inset, BY1 - inset
    c = chamfer
    return [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1), (x0, y1 - c),
            (x0, y0 + c)]


def circle(cx, cy, r, n=24):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def add_zone(board, r, name, net, layer, poly, priority=0, clearance=0.3, min_width=0.25, full=True,
             tht_thermal=False, holes=()):
    """Copper zone. full=True: solid pad connection (power), else thermal reliefs. holes: list of polygons cut
    out of the outline."""
    z = r.zone(name, net, layer, poly, priority=priority, clearance=clearance, min_width=min_width,
               thermal=not full)
    if tht_thermal:
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)
    z.SetThermalReliefGap(mm(0.3))
    z.SetThermalReliefSpokeWidth(mm(0.4))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    ol = z.Outline()
    for h in holes:
        ol.NewHole()
        for x, y in h:
            ol.Append(mm(x), mm(y), 0, 0)
    return z


def add_keepout(board, name, layers, poly, tracks=True, vias=True, pours=True):
    """Rule area (keep-out). layers: list of copper layer names."""
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetZoneName(name)
    ls = pcbnew.LSET()
    for l in layers:
        ls.AddLayer(CU[l])
    z.SetLayerSet(ls)
    z.SetDoNotAllowTracks(tracks)
    z.SetDoNotAllowVias(vias)
    z.SetDoNotAllowZoneFills(pours)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    ol = z.Outline()
    ol.NewOutline()
    for x, y in poly:
        ol.Append(mm(x), mm(y))
    board.Add(z)
    return z


def _seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _in_poly(x, y, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def _poly_dist(x, y, poly):
    """0 inside, else distance to the outline."""
    if _in_poly(x, y, poly):
        return 0.0
    n = len(poly)
    return min(_seg_dist(x, y, *poly[i], *poly[(i + 1) % n]) for i in range(n))


class ViaPlacer:
    """Places through vias only where they are legal against every pad, hole, track and via already on the
    board (any net), against keep-out polygons, the board edge and the mounting holes."""

    def __init__(self, board, keepouts=(), clearance=0.2):
        self.board = board
        self.clr = clearance
        # list of (polygon, layers): vias are blocked by every keep-out, tracks only on its layers
        # entries: polygon | (polygon, layers) | (polygon, layers, blocks_vias)
        self.keepouts = []
        for k in keepouts:
            if isinstance(k, tuple) and len(k) in (2, 3) and isinstance(k[1], (set, frozenset)):
                self.keepouts.append((k[0], k[1], k[2] if len(k) == 3 else True))
            else:
                self.keepouts.append((k, frozenset(ALL_CU), True))
        self.pads = []
        for fp in board.GetFootprints():
            for p in fp.Pads():
                bb = p.GetBoundingBox()
                hs = None
                if p.GetDrillSizeX() > 0:
                    hs = p.GetEffectiveHoleShape()
                cu = [l for l in (pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu,
                                  pcbnew.In4_Cu) if p.IsOnLayer(l)]
                self.pads.append((p, fp.GetReference(), short(p.GetNetname()),
                                  (MM(bb.GetLeft()), MM(bb.GetTop()), MM(bb.GetRight()), MM(bb.GetBottom())),
                                  hs, cu))
        self.refresh()

    ghost_tracks = []      # copper of scripts that run later (HS routes), class-wide: treated as obstacles
    ghost_vias = []

    def refresh(self):
        self.tracks, self.vias = list(ViaPlacer.ghost_tracks), list(ViaPlacer.ghost_vias)
        for t in self.board.GetTracks():
            n = short(t.GetNetname())
            if t.GetClass() == "PCB_VIA":
                p = t.GetPosition()
                self.vias.append((n, MM(p.x), MM(p.y), MM(t.GetWidth(pcbnew.F_Cu)), MM(t.GetDrillValue())))
            else:
                a, b = t.GetStart(), t.GetEnd()
                self.tracks.append((n, MM(a.x), MM(a.y), MM(b.x), MM(b.y), MM(t.GetWidth()), t.GetLayer()))

    def ok(self, net, x, y, size=0.6, drill=0.3, allow_pads=(), clr=None, hvclr=0.3):
        net = short(net)
        clr = self.clr if clr is None else clr
        rad = size / 2
        if not (BX0 + 0.8 + rad < x < BX1 - 0.8 - rad and BY0 + 0.8 + rad < y < BY1 - 0.8 - rad):
            return False
        for hx, hy in HOLES:
            if math.hypot(x - hx, y - hy) < 4.3 + rad:
                return False
        for poly, _ls, bv in self.keepouts:
            if bv and _poly_dist(x, y, poly) < rad + 0.05:
                return False
        v = pcbnew.VECTOR2I(mm(x), mm(y))
        for p, ref, pn, (l, t, rr, b), hs, cu in self.pads:
            hv = (pn in HV_NETS) != (net in HV_NETS)
            c = max(clr, hvclr) if hv else clr
            if x < l - rad - c - 0.05 or x > rr + rad + c + 0.05 or y < t - rad - c - 0.05 or y > b + rad + c + 0.05:
                continue
            if hs is not None and hs.Collide(v, mm(rad + 0.25)):
                return False
            same = (pn == net)
            if same and (ref, p.GetNumber()) in allow_pads:
                continue
            for layer in cu:
                if p.GetEffectiveShape(layer).Collide(v, mm(rad + (0.0 if same else c))):
                    return False
        for n, vx, vy, vs, vd in self.vias:
            d = math.hypot(x - vx, y - vy)
            if n == net:
                if d < max(rad + vs / 2 + 0.1, drill / 2 + vd / 2 + 0.25):
                    return False
            elif d < rad + vs / 2 + max(clr, hvclr if ((n in HV_NETS) != (net in HV_NETS)) else clr):
                return False
        for n, ax, ay, bx, by, w, layer in self.tracks:
            if n == net:
                continue
            c = max(clr, hvclr) if ((n in HV_NETS) != (net in HV_NETS)) else clr
            if _seg_dist(x, y, ax, ay, bx, by) < rad + w / 2 + c:
                return False
        return True

    def place(self, r, net, x, y, size=0.6, drill=0.3, allow_pads=(), clr=None, hvclr=0.3):
        if not self.ok(net, x, y, size, drill, allow_pads, clr, hvclr):
            return False
        r.via(net, x, y, size, drill)
        self.vias.append((short(net), x, y, size, drill))
        return True

    def fill(self, r, net, area, pitch=1.0, size=0.6, drill=0.3, maxn=999, allow_pads=(), target=None,
             step=0.1):
        """Greedy: candidate points on a fine grid inside `area` (polygon or (x0,y0,x1,y1)), nearest to
        `target` first (default: area centre), keeping `pitch` between the new vias. Returns the count."""
        if len(area) == 4 and not isinstance(area[0], (tuple, list)):
            area = rect(*area)
        xs = [p[0] for p in area]
        ys = [p[1] for p in area]
        if target is None:
            target = (sum(xs) / len(xs), sum(ys) / len(ys))
        cands = []
        nx = int((max(xs) - min(xs)) / step) + 1
        ny = int((max(ys) - min(ys)) / step) + 1
        for i in range(nx):
            for j in range(ny):
                x, y = round(min(xs) + i * step, 3), round(min(ys) + j * step, 3)
                if _in_poly(x, y, area):
                    cands.append((math.hypot(x - target[0], y - target[1]), x, y))
        cands.sort()
        placed = []
        for _, x, y in cands:
            if len(placed) >= maxn:
                break
            if any(math.hypot(x - px, y - py) < pitch for px, py in placed):
                continue
            if self.place(r, net, x, y, size, drill, allow_pads):
                placed.append((x, y))
        return len(placed)

    def grid(self, r, net, area, pitch, size=0.6, drill=0.3, allow_pads=(), jitter=(0.0, 0.4, -0.4, 0.8, -0.8)):
        """Regular grid (stitching): one via per grid node, nudged by `jitter` offsets if the node is blocked."""
        if len(area) == 4 and not isinstance(area[0], (tuple, list)):
            area = rect(*area)
        xs = [p[0] for p in area]
        ys = [p[1] for p in area]
        n = 0
        x = math.ceil(min(xs) / pitch) * pitch
        while x <= max(xs):
            y = math.ceil(min(ys) / pitch) * pitch
            while y <= max(ys):
                done = False
                for dx in jitter:
                    for dy in jitter:
                        if done:
                            break
                        px, py = x + dx, y + dy
                        if _in_poly(px, py, area) and self.place(r, net, px, py, size, drill, allow_pads):
                            n += 1
                            done = True
                y += pitch
            x += pitch
        return n

    def pad_box(self, ref, num):
        for p, rf, pn, bb, hs, cu in self.pads:
            if rf == ref and p.GetNumber() == str(num):
                return bb
        raise KeyError(f"{ref}.{num}")


class GridRouter:
    """Tiny A* grid router for short local connections (Kelvin taps, gate drives). Obstacles: every pad,
    track and via of another net already on the board, keep-out polygons, board edge, mounting holes.
    Layers: list of copper layer names. Same-net copper is free. Returns True when routed."""

    def __init__(self, board, placer, step=0.1):
        self.board = board
        self.vp = placer
        self.step = step

    def route(self, r, net, a, b, layers=("F.Cu",), width=0.2, clr=0.2, via=(0.45, 0.25), window=3.0,
              via_cost=3.0, la=None, lb=None, extra_block=(), strict=False, soft_block=()):
        import heapq
        net = short(net)
        clr = clr + 0.025          # grid sampling margin
        self.vp.refresh()
        s = self.step
        # grid aligned on the start point (fine-pitch pins need their lane centred on a grid line)
        x0 = a[0] - s * round((a[0] - min(a[0], b[0]) + window) / s)
        y0 = a[1] - s * round((a[1] - min(a[1], b[1]) + window) / s)
        x1, y1 = max(a[0], b[0]) + window, max(a[1], b[1]) + window
        nx, ny = int((x1 - x0) / s) + 1, int((y1 - y0) / s) + 1
        L = len(layers)
        lid = [CU[l] for l in layers]
        hv = net in HV_NETS
        blocked = [bytearray(nx * ny) for _ in range(L)]
        vblock = bytearray(nx * ny)
        hw = width / 2
        vr = via[0] / 2

        soft = [bytearray(nx * ny) for _ in range(L)]   # HV extra clearance (ignored next to the end points)
        vsoft = bytearray(nx * ny)

        def mark(li, bx0, by0, bx1, by1, test, infl, sft=False):
            i0, i1 = max(0, int((bx0 - infl - x0) / s)), min(nx - 1, int((bx1 + infl - x0) / s) + 1)
            j0, j1 = max(0, int((by0 - infl - y0) / s)), min(ny - 1, int((by1 + infl - y0) / s) + 1)
            arr = (vsoft if li is None else soft[li]) if sft else (vblock if li is None else blocked[li])
            for i in range(i0, i1 + 1):
                x = x0 + i * s
                for j in range(j0, j1 + 1):
                    if test(x, y0 + j * s, infl):
                        arr[j * nx + i] = 1

        def mark2(li, bx0, by0, bx1, by1, test, infl0, c, ishv, soft_ok=False):
            # HV clearance is hard, except against pads of the end-point footprints (fine-pitch pins next to the
            # pin being entered), where it is relaxed within 1 mm of the end points
            if ishv and c > clr and (not soft_ok or li is None):     # vias always keep the HV clearance
                mark(li, bx0, by0, bx1, by1, test, infl0 + c)
                return
            mark(li, bx0, by0, bx1, by1, test, infl0 + clr)
            if ishv and c > clr:
                mark(li, bx0, by0, bx1, by1, test, infl0 + c, True)

        va_, vb_ = pcbnew.VECTOR2I(mm(a[0]), mm(a[1])), pcbnew.VECTOR2I(mm(b[0]), mm(b[1]))
        end_refs = set()
        for p, ref, pn, (l, t, rr, bb), hs, cu in self.vp.pads:
            if l - 0.1 <= a[0] <= rr + 0.1 and t - 0.1 <= a[1] <= bb + 0.1 or \
                    l - 0.1 <= b[0] <= rr + 0.1 and t - 0.1 <= b[1] <= bb + 0.1:
                if any(p.GetEffectiveShape(lyr).Collide(va_, mm(0.05)) or p.GetEffectiveShape(lyr).Collide(vb_, mm(0.05))
                       for lyr in cu):
                    end_refs.add(ref)

        for p, ref, pn, (l, t, rr, bb), hs, cu in self.vp.pads:
            if rr < x0 - 2 or l > x1 + 2 or bb < y0 - 2 or t > y1 + 2:
                continue
            if hs is not None:
                def th(x, y, infl, hs=hs):
                    return hs.Collide(pcbnew.VECTOR2I(mm(x), mm(y)), mm(infl))
                for li in range(L):
                    mark(li, l, t, rr, bb, th, hw + 0.25)
                mark(None, l, t, rr, bb, th, vr + 0.25)
            if pn == net:
                if not strict:
                    continue
                va, vb = pcbnew.VECTOR2I(mm(a[0]), mm(a[1])), pcbnew.VECTOR2I(mm(b[0]), mm(b[1]))
                if any(p.GetEffectiveShape(lyr).Collide(va, 0) or p.GetEffectiveShape(lyr).Collide(vb, 0)
                       for lyr in cu):
                    continue
            ishv = hv != (pn in HV_NETS)
            c = max(clr, 0.3) if ishv else clr
            for layer in cu:
                shp = p.GetEffectiveShape(layer)

                def tp(x, y, infl, shp=shp):
                    return shp.Collide(pcbnew.VECTOR2I(mm(x), mm(y)), mm(infl))
                if layer in lid:
                    mark2(lid.index(layer), l, t, rr, bb, tp, hw, c, ishv, ref in end_refs)
                mark2(None, l, t, rr, bb, tp, vr, c, ishv, ref in end_refs)
        for n, vx, vy, vs, vd in self.vp.vias:
            if n == net and (not strict or math.hypot(vx - a[0], vy - a[1]) < 0.6 or
                             math.hypot(vx - b[0], vy - b[1]) < 0.6):
                continue
            ishv = hv != (n in HV_NETS)
            c = max(clr, 0.3) if ishv else clr
            f = lambda x, y, infl, vx=vx, vy=vy: math.hypot(x - vx, y - vy) < infl
            for li in range(L):
                mark2(li, vx - vs / 2, vy - vs / 2, vx + vs / 2, vy + vs / 2, f, vs / 2 + hw, c, ishv)
            mark2(None, vx - vs / 2, vy - vs / 2, vx + vs / 2, vy + vs / 2, f, vs / 2 + vr, c, ishv)
        for n, ax, ay, bx, by, w, layer in self.vp.tracks:
            if n == net:
                continue
            ishv = hv != (n in HV_NETS)
            c = max(clr, 0.3) if ishv else clr
            f = lambda x, y, infl, ax=ax, ay=ay, bx=bx, by=by: _seg_dist(x, y, ax, ay, bx, by) < infl
            if layer in lid:
                mark2(lid.index(layer), min(ax, bx), min(ay, by), max(ax, bx), max(ay, by), f, w / 2 + hw, c, ishv)
            mark2(None, min(ax, bx), min(ay, by), max(ax, bx), max(ay, by), f, w / 2 + vr, c, ishv)
        polys = list(self.vp.keepouts) + [(pp[0], frozenset(pp[1]), True) if isinstance(pp, tuple)
                                          else (pp, frozenset(ALL_CU), True) for pp in extra_block]
        polys = [(pp, pls, bv) for pp, pls, bv in polys
                 if not (max(q[0] for q in pp) < x0 - 1 or min(q[0] for q in pp) > x1 + 1 or
                         max(q[1] for q in pp) < y0 - 1 or min(q[1] for q in pp) > y1 + 1)]
        for i in range(nx):
            x = x0 + i * s
            for j in range(ny):
                y = y0 + j * s
                k = j * nx + i
                edge = not (BX0 + 0.3 + hw < x < BX1 - 0.3 - hw and BY0 + 0.3 + hw < y < BY1 - 0.3 - hw)
                hole = any(math.hypot(x - hx, y - hy) < 4.0 for hx, hy in HOLES)
                if edge or hole:
                    for li in range(L):
                        blocked[li][k] = 1
                    vblock[k] = 1
                    continue
                for pp, pls, bv in polys:
                    dd = _poly_dist(x, y, pp)
                    if bv and dd < vr + 0.05:
                        vblock[k] = 1
                    if dd < hw + 0.05:
                        for li in range(L):
                            if layers[li] in pls:
                                blocked[li][k] = 1
        for pp, pls in soft_block:
            if (max(q[0] for q in pp) < x0 - 1 or min(q[0] for q in pp) > x1 + 1 or
                    max(q[1] for q in pp) < y0 - 1 or min(q[1] for q in pp) > y1 + 1):
                continue
            lis = [li for li in range(L) if layers[li] in pls]
            if not lis:
                continue
            xs_ = [q[0] for q in pp]
            ys_ = [q[1] for q in pp]
            for i in range(max(0, int((min(xs_) - x0) / s)), min(nx, int((max(xs_) - x0) / s) + 1)):
                for j in range(max(0, int((min(ys_) - y0) / s)), min(ny, int((max(ys_) - y0) / s) + 1)):
                    if _in_poly(x0 + i * s, y0 + j * s, pp):
                        for li in lis:
                            soft[li][j * nx + i] = 1
        for i in range(nx):
            x = x0 + i * s
            for j in range(ny):
                k = j * nx + i
                y = y0 + j * s
                far = math.hypot(x - a[0], y - a[1]) > 1.0 and math.hypot(x - b[0], y - b[1]) > 1.0
                if far:
                    if vsoft[k]:
                        vblock[k] = 1
                    for li in range(L):
                        if soft[li][k]:
                            blocked[li][k] = 1
        sa = (int(round((a[0] - x0) / s)), int(round((a[1] - y0) / s)))
        sb = (int(round((b[0] - x0) / s)), int(round((b[1] - y0) / s)))
        starts = [layers.index(la)] if la else list(range(L))
        goals = set([layers.index(lb)] if lb else range(L))
        # start/goal cells are inside same-net pads: force-free a small disc around them
        for (ci, cj), lis in ((sa, starts), (sb, goals)):
            for li in lis:
                for di in range(-1, 2):
                    for dj in range(-1, 2):
                        ii, jj = ci + di, cj + dj
                        if 0 <= ii < nx and 0 <= jj < ny:
                            blocked[li][jj * nx + ii] = 0
        dirs = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414),
                (-1, -1, 1.414)]
        h = lambda i, j: math.hypot(i - sb[0], j - sb[1])
        openq = []
        g = {}
        prev = {}
        for li in starts:
            st = (sa[0], sa[1], li)
            g[st] = 0
            heapq.heappush(openq, (h(*sa), 0, st))
        end = None
        while openq:
            f, gc, cur = heapq.heappop(openq)
            if gc > g.get(cur, 1e18):
                continue
            i, j, li = cur
            if (i, j) == sb and li in goals:
                end = cur
                break
            nb = []
            for di, dj, c in dirs:
                ii, jj = i + di, j + dj
                if 0 <= ii < nx and 0 <= jj < ny and not blocked[li][jj * nx + ii]:
                    # turn penalty keeps paths straight
                    pd = prev.get(cur)
                    tpen = 0
                    if pd is not None and pd[2] == li and (i - pd[0], j - pd[1]) != (di, dj):
                        tpen = 0.6
                    nb.append(((ii, jj, li), c + tpen))
            if not vblock[j * nx + i]:
                for l2 in range(L):
                    if l2 != li and not blocked[l2][j * nx + i]:
                        nb.append(((i, j, l2), via_cost / s * 0.1 * 10))
            for st, c in nb:
                ng = gc + c
                if ng < g.get(st, 1e18):
                    g[st] = ng
                    prev[st] = cur
                    heapq.heappush(openq, (ng + h(st[0], st[1]), ng, st))
        if end is None:
            import os
            dd = os.environ.get("PWR_DEBUG")
            if dd:
                for li in range(L):
                    with open(os.path.join(dd, "fail_%s_%d_%d_%s.pgm" % (net.replace("+", "p"), int(a[0] * 10),
                                                                        int(a[1] * 10), layers[li])), "wb") as fh:
                        fh.write(b"P5 %d %d 255\n" % (nx, ny))
                        fh.write(bytes((0 if blocked[li][j * nx + i] else (128 if vblock[j * nx + i] else 255))
                                       if (i, j) not in (sa, sb) else 60 for j in range(ny) for i in range(nx)))
            return False
        path = [end]
        while path[-1] in prev:
            path.append(prev[path[-1]])
        path.reverse()
        # emit: split per layer, simplify collinear points
        segs = []
        cur_l = path[0][2]
        pts = [path[0]]
        for st in path[1:]:
            if st[2] != cur_l:
                segs.append((cur_l, pts))
                r.via(net, x0 + st[0] * s, y0 + st[1] * s, via[0], via[1])
                cur_l = st[2]
                pts = [st]
            else:
                pts.append(st)
        segs.append((cur_l, pts))
        for li, pts in segs:
            if len(pts) < 2 and not (pts is segs[0][1] or pts is segs[-1][1]):
                continue
            simp = [pts[0]]
            for k in range(1, len(pts) - 1):
                d1 = (pts[k][0] - simp[-1][0], pts[k][1] - simp[-1][1])
                d2 = (pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1])
                if d1[0] * d2[1] - d1[1] * d2[0] != 0:
                    simp.append(pts[k])
            simp.append(pts[-1])
            xy = [(round(x0 + p[0] * s, 4), round(y0 + p[1] * s, 4)) for p in simp]
            if pts is segs[0][1] and math.hypot(xy[0][0] - a[0], xy[0][1] - a[1]) > 1e-3:
                xy.insert(0, tuple(a))
            if pts is segs[-1][1] and math.hypot(xy[-1][0] - b[0], xy[-1][1] - b[1]) > 1e-3:
                xy.append(tuple(b))
            r.track(net, xy, layers[li], width)
        self.vp.refresh()
        return True


def load_ghosts(board, router_cls, names):
    """Apply the routing scripts `names` (module names in this directory) to a fresh copy of the board file and
    return their tracks/vias as (tracks, vias) lists in ViaPlacer format. Lets an early script (b_power) keep clear of
    copper drawn by scripts that run after it (the high-speed routes)."""
    import os, io, glob, contextlib, importlib.util
    here = os.path.dirname(os.path.abspath(__file__))
    path = board.GetFileName()
    if not path or not os.path.exists(path):
        return [], []
    tmp = pcbnew.LoadBoard(path)
    owned = set()
    for name in names:
        fn = os.path.join(here, name + ".py")
        if not os.path.exists(fn):
            continue
        spec = importlib.util.spec_from_file_location("ghost_" + name, fn)
        mod = importlib.util.module_from_spec(spec)
        with contextlib.redirect_stdout(io.StringIO()):
            spec.loader.exec_module(mod)
            nets = set()
            for n in getattr(mod, "NETS", []):
                for k in tmp.GetNetsByName().keys():
                    if str(k) == n or str(k).split("/")[-1] == n:
                        nets.add(str(k))
            for t in list(tmp.GetTracks()):
                if t.GetNetname() in nets:
                    tmp.Remove(t)
            try:
                mod.route(tmp, router_cls(tmp))
            except Exception as e:      # a broken HS script must not stop the power routing
                print("ghost %s failed: %s" % (name, e))
        owned |= nets
    tracks, vias = [], []
    for t in tmp.GetTracks():
        if t.GetNetname() not in owned and short(t.GetNetname()) != "GND":
            continue
        n = short(t.GetNetname())
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition()
            vias.append((n, MM(p.x), MM(p.y), MM(t.GetWidth(pcbnew.F_Cu)), MM(t.GetDrillValue())))
        else:
            a, b = t.GetStart(), t.GetEnd()
            tracks.append((n, MM(a.x), MM(a.y), MM(b.x), MM(b.y), MM(t.GetWidth()), t.GetLayer()))
    return tracks, vias
