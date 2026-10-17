"""Rough initial placement for odock-10, used by tools/pcbsync.py for footprints that are NEW on the board.
Already-placed footprints are never moved, so hand placement in KiCad is preserved on re-sync.

Strategy: connectors go to fixed edge positions (docs/board-layout.md), the LCD outline is mechanical
(non-blocking), then every other part is packed nearest-free around its sheet's anchor point, largest first;
small parts that don't fit on top within reach go to the bottom side.
Board origin (top-left) = (100, 50) mm; back edge = top (y = 50), front edge = bottom.
"""
import math
import pcbnew

X0, Y0 = 100.0, 50.0
GRID = 0.5          # occupancy grid (mm)
GAP = 0.4           # clearance added around courtyards (mm)

# connector ref -> (x, y, edge) ; edge = side the mating face must point to
EDGE = {
    "J102": (112, None, "back"),   # barrel
    "J101": (127, None, "back"),   # PD-in USB-C
    "J501": (152, None, "back"),   # laptop USB-C
    "J502": (166, None, "back"),   # downstream USB-C
    "J801": (212, None, "back"),   # RJ45
    "J901": (120, None, "front"),  # SD
    "J902": (142, None, "front"),  # microSD
    "J701": (162, None, "front"),  # USB-A 1
    "J702": (180, None, "front"),  # USB-A 2
    "SW1101": (200, None, "front"),
    "SW1102": (210, None, "front"),
    "J1102": (222, None, "front"),  # Qwiic
}
NONBLOCKING = {"U1101"}                       # LCD panel outline (sits on foam over low parts)
FIXED = {"U1101": (204, 104, 0)}              # (x, y, rotation)

ANCHOR = {
    "/Power input/": (114, 64), "/Laptop power out/": (116, 90), "/Rails/": (116, 114),
    "/PD controller/": (152, 70), "/USB-C muxes & DP/": (160, 62), "/USB hub/": (172, 88),
    "/Ethernet/": (210, 70), "/USB-A ports/": (172, 122), "/Card reader/": (132, 122),
    "/MCU/": (142, 100), "/Display & UI/": (210, 116), "/Sensors/": (165, 102),
}


def _mm(v):
    return pcbnew.ToMM(v)


def _bbox(fp):
    cy = fp.GetCourtyard(pcbnew.F_CrtYd if not fp.IsFlipped() else pcbnew.B_CrtYd)
    bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False)
    return _mm(bb.GetLeft()), _mm(bb.GetTop()), _mm(bb.GetRight()), _mm(bb.GetBottom())


def _opening_dir(fp):
    """Direction the connector opens toward: from pad centroid to courtyard centre (unit axis vector)."""
    pads = list(fp.Pads())
    if not pads:
        return (0, -1)
    px = sum(_mm(p.GetPosition().x) for p in pads) / len(pads)
    py = sum(_mm(p.GetPosition().y) for p in pads) / len(pads)
    l, t, r, b = _bbox(fp)
    dx, dy = (l + r) / 2 - px, (t + b) / 2 - py
    return (1 if dx > 0 else -1, 0) if abs(dx) > abs(dy) else (0, 1 if dy > 0 else -1)


class Grid:
    def __init__(self, W, H):
        self.W, self.H = W, H
        self.nx, self.ny = int(W / GRID), int(H / GRID)
        self.top = bytearray(self.nx * self.ny)
        self.bot = bytearray(self.nx * self.ny)

    def _cells(self, l, t, r, b):
        i0, j0 = int((l - X0 - GAP) / GRID), int((t - Y0 - GAP) / GRID)
        i1, j1 = int(math.ceil((r - X0 + GAP) / GRID)), int(math.ceil((b - Y0 + GAP) / GRID))
        return i0, j0, i1, j1

    def free(self, layer, l, t, r, b, edge_margin=0.5):
        if l < X0 + edge_margin or t < Y0 + edge_margin or r > X0 + self.W - edge_margin or b > Y0 + self.H - edge_margin:
            return False
        g = self.top if layer == "top" else self.bot
        i0, j0, i1, j1 = self._cells(l, t, r, b)
        for j in range(max(j0, 0), min(j1, self.ny)):
            row = j * self.nx
            if any(g[row + max(i0, 0):row + min(i1, self.nx)]):
                return False
        return True

    def mark(self, layer, l, t, r, b, through=False):
        for g in ([self.top, self.bot] if through else [self.top if layer == "top" else self.bot]):
            i0, j0, i1, j1 = self._cells(l, t, r, b)
            for j in range(max(j0, 0), min(j1, self.ny)):
                row = j * self.nx
                for i in range(max(i0, 0), min(i1, self.nx)):
                    g[row + i] = 1


def _board_size(board):
    bb = board.GetBoardEdgesBoundingBox()
    return _mm(bb.GetWidth()), _mm(bb.GetHeight())


def _is_tht(fp):
    return any(p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH for p in fp.Pads())


def place(board, added, comps):
    W, H = _board_size(board)
    grid = Grid(W, H)
    added_set = {fp.GetReference() for fp in added}
    V = lambda x, y: pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))

    # occupancy from footprints that are already placed (incl. mounting holes)
    for fp in board.GetFootprints():
        if fp.GetReference() in added_set or fp.GetReference() in NONBLOCKING:
            continue
        grid.mark("bot" if fp.IsFlipped() else "top", *_bbox(fp), through=_is_tht(fp) or fp.GetReference().startswith("H"))

    todo = []
    for fp in added:
        ref = fp.GetReference()
        if ref in FIXED:
            x, y, rot = FIXED[ref]
            fp.SetPosition(V(x, y)); fp.SetOrientationDegrees(rot)
        elif ref in EDGE:
            x, _, edge = EDGE[ref]
            fp.SetOrientationDegrees(0)
            fp.SetPosition(V(x, 0))
            want = (0, -1) if edge == "back" else (0, 1)
            for rot in (0, 90, 180, 270):
                fp.SetOrientationDegrees(rot)
                if _opening_dir(fp) == want:
                    break
            l, t, r, b = _bbox(fp)
            cx = fp.GetPosition()
            if edge == "back":       # front face flush with (slightly over) the back edge
                fp.SetPosition(V(x, _mm(cx.y) + (Y0 - 0.5) - t))
            else:
                fp.SetPosition(V(x, _mm(cx.y) + (Y0 + H + 0.5) - b))
            grid.mark("top", *_bbox(fp), through=_is_tht(fp))
        else:
            todo.append(fp)

    def area(fp):
        l, t, r, b = _bbox(fp)
        return (r - l) * (b - t)

    todo.sort(key=area, reverse=True)
    for fp in todo:
        sheet = comps.get(fp.GetReference(), {}).get("sheet", "")
        ax, ay = ANCHOR.get(sheet, (X0 + W / 2, Y0 + H / 2))
        fp.SetPosition(V(ax, ay))
        l, t, r, b = _bbox(fp)
        w, h = r - l, b - t
        small = w * h < 25 and not _is_tht(fp)
        placed = False
        layers = ["top", "bot"] if small else ["top"]
        for layer in layers:
            reach = 35 if layer == "top" else 70
            best = None
            step = GRID * 2
            n = int(reach / step)
            for rad in range(0, n + 1):
                cands = []
                for k in range(-rad, rad + 1):
                    cands += [(k, -rad), (k, rad), (-rad, k), (rad, k)] if rad else [(0, 0)]
                for (di, dj) in cands:
                    L, T = ax + di * step - w / 2, ay + dj * step - h / 2
                    if grid.free(layer, L, T, L + w, T + h):
                        d = math.hypot(di, dj)
                        if best is None or d < best[0]:
                            best = (d, L, T)
                if best:
                    break
            if best:
                _, L, T = best
                if layer == "bot":
                    fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
                l2, t2, _, _ = _bbox(fp)
                p = fp.GetPosition()
                fp.SetPosition(V(_mm(p.x) + L - l2, _mm(p.y) + T - t2))
                grid.mark(layer, *_bbox(fp), through=_is_tht(fp))
                placed = True
                break
        if not placed:
            print(f"placement: no room for {fp.GetReference()} ({sheet}) — left at anchor", flush=True)
