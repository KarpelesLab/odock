"""Shared helpers for the high-speed routing scripts (d_hs_hub.py, e_hs_eth_sd.py).

File name starts with "_" so tools/apply_routing.py does not run it as a routing script.
Conventions: coordinates in mm, y grows downward (KiCad). "Left" of a travel direction means
screen-left (heading east, left is north). Diff pairs are generated from a centreline.
"""
import math

SQ2 = math.sqrt(2.0)

# Trace geometry per layer (estimates, see docs/routing-notes/hs_hub.md; confirm with JLC's calculator).
USB90 = {"F.Cu": (0.10, 0.18), "B.Cu": (0.10, 0.18), "In2.Cu": (0.16, 0.20)}
ETH100 = {"F.Cu": (0.09, 0.20), "B.Cu": (0.09, 0.20)}
SE50 = {"F.Cu": 0.12, "B.Cu": 0.12, "In2.Cu": 0.20}

LOG = []          # (name, length P, length N) for the notes
WARN = []


def L(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def _left(dx, dy):
    n = math.hypot(dx, dy) or 1.0
    return (dy / n, -dx / n)


def offset(pts, d):
    """Offset polyline by d to the screen-left (negative d = right), mitred joints."""
    out = []
    n = len(pts)
    for i in range(n):
        if i == 0:
            nx, ny = _left(pts[1][0] - pts[0][0], pts[1][1] - pts[0][1])
            out.append((pts[0][0] + nx * d, pts[0][1] + ny * d))
        elif i == n - 1:
            nx, ny = _left(pts[-1][0] - pts[-2][0], pts[-1][1] - pts[-2][1])
            out.append((pts[-1][0] + nx * d, pts[-1][1] + ny * d))
        else:
            a = _left(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
            b = _left(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
            bx, by = a[0] + b[0], a[1] + b[1]
            bl = math.hypot(bx, by) or 1.0
            bx, by = bx / bl, by / bl
            c = bx * a[0] + by * a[1]
            k = d / max(c, 0.2)
            out.append((pts[i][0] + bx * k, pts[i][1] + by * k))
    return out


def pair_lines(path, w, g):
    """Return (left, right) polylines of a coupled pair along centreline `path`."""
    d = (w + g) / 2.0
    return offset(path, d), offset(path, -d)


def bumps(pts, i, extra, side, h=0.22, top=0.2, gap=0.2, margin=0.25, hmax=0.3, center=None):
    """Insert 45-degree trapezoid bumps (length tuning) on segment i of polyline pts.
    side=+1 bumps to the screen-left of the segment direction, -1 to the right.
    Returns the new point list. Each bump adds 2*h*(sqrt2-1)."""
    if extra <= 1e-4:
        return list(pts)
    a, b = pts[i], pts[i + 1]
    seg = math.hypot(b[0] - a[0], b[1] - a[1])
    ux, uy = (b[0] - a[0]) / seg, (b[1] - a[1]) / seg
    nx, ny = _left(ux, uy)
    nx, ny = nx * side, ny * side
    k = 2 * (SQ2 - 1)
    nb = max(1, int(math.ceil(extra / (k * h))))
    hh = extra / (nb * k)
    while hh > hmax:
        nb += 1
        hh = extra / (nb * k)
    pitch = 2 * hh + top + gap
    total = nb * pitch - gap
    if total > seg - 2 * margin:
        # try taller bumps
        nb2 = max(1, int((seg - 2 * margin + gap) // (2 * hmax + top + gap)))
        hh2 = extra / (nb2 * k)
        if nb2 >= 1 and hh2 <= hmax * 1.6:
            nb, hh = nb2, hh2
            pitch = 2 * hh + top + gap
            total = nb * pitch - gap
        if total > seg - 2 * margin:
            raise ValueError(f"bumps: segment {seg:.2f} too short for {extra:.3f} extra")
    s = (seg - total) / 2.0
    if center is not None:
        c = (center[0] - a[0]) * ux + (center[1] - a[1]) * uy
        s = min(max(margin, c - total / 2.0), seg - margin - total)
    new = list(pts[:i + 1])
    for _ in range(nb):
        p0 = (a[0] + ux * s, a[1] + uy * s)
        new.append(p0)
        new.append((p0[0] + ux * hh + nx * hh, p0[1] + uy * hh + ny * hh))
        new.append((p0[0] + ux * (hh + top) + nx * hh, p0[1] + uy * (hh + top) + ny * hh))
        new.append((p0[0] + ux * (2 * hh + top), p0[1] + uy * (2 * hh + top)))
        s += pitch
    new.extend(pts[i + 1:])
    return new


def longest_seg(pts, lo=0, hi=None):
    hi = len(pts) - 1 if hi is None else hi
    best, bi = -1, lo
    for i in range(lo, hi):
        d = math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
        if d > best:
            best, bi = d, i
    return bi


def match(P, N, segP=None, segN=None, sideP=+1, sideN=-1, tol=0.02, offset=0.0, **kw):
    """Equalise lengths: add bumps to the shorter polyline on its given (or longest) segment.
    sideP/sideN: bump direction for P/N (+1 left / -1 right of segment direction).
    offset: target L(P) - L(N) (used to cancel the skew of another section of the same link)."""
    lp, ln = L(P) - offset, L(N)
    if abs(lp - ln) <= tol:
        return P, N
    if lp < ln:
        i = longest_seg(P) if segP is None else segP
        P = bumps(P, i, ln - lp, sideP, **kw)
        return P, N
    else:
        i = longest_seg(N) if segN is None else segN
        N = bumps(N, i, lp - ln, sideN, **kw)
    return P, N


def draw(r, net, pts, layer, w):
    clean = [pts[0]]
    for p in pts[1:]:
        if math.hypot(p[0] - clean[-1][0], p[1] - clean[-1][1]) > 1e-4:
            clean.append(p)
    r.track(net, clean, layer, w)


def gvia(r, x, y):
    r.via("GND", x, y, 0.45, 0.25)


def log(name, P, N):
    LOG.append((name, L(P), L(N)))


def chain(*parts):
    """Concatenate polylines, dropping duplicate joints."""
    out = []
    for p in parts:
        for q in p:
            if not out or math.hypot(q[0] - out[-1][0], q[1] - out[-1][1]) > 1e-4:
                out.append(q)
    return out


def cap_ok(r, cap, net_near, net_far, src):
    """True if the in-line cap's pad on `net_near` is the one closer to `src` (i.e. the cap is
    oriented for a straight-through route)."""
    a = r.pad_of_net(cap, net_near)
    b = r.pad_of_net(cap, net_far)
    da = math.hypot(a[0] - src[0], a[1] - src[1])
    db = math.hypot(b[0] - src[0], b[1] - src[1])
    return da < db


def seg_near(pts, q):
    """Index of the segment of pts closest to point q."""
    best, bi = 1e9, 0
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy or 1e-12
        t = max(0.0, min(1.0, ((q[0] - a[0]) * dx + (q[1] - a[1]) * dy) / L2))
        d = math.hypot(a[0] + t * dx - q[0], a[1] + t * dy - q[1])
        if d < best:
            best, bi = d, i
    return bi


def serp(pts, i, extra, side, maxamp=0.8, top=0.3, gap=0.3, ch=0.1, margin=0.2, center=None, amax=None):
    """Accordion meander on segment i: n bumps of amplitude A with perpendicular legs and 45-degree
    chamfered corners (cut `ch`). Each bump adds 2*A - 2*ch*(2 - sqrt2). Returns new point list."""
    if extra <= 1e-4:
        return list(pts)
    a, b = pts[i], pts[i + 1]
    seg = math.hypot(b[0] - a[0], b[1] - a[1])
    ux, uy = (b[0] - a[0]) / seg, (b[1] - a[1]) / seg
    nx, ny = _left(ux, uy)
    nx, ny = nx * side, ny * side
    loss = 2 * ch * (2 - SQ2)
    per = 2 * maxamp - loss
    nb = max(1, int(math.ceil(extra / per)))
    pitch = top + gap
    if amax is not None:            # fewer, taller bumps if the segment is short
        nbmax = max(1, int((seg - 2 * margin + gap) // pitch))
        nb = min(nb, nbmax)
    A = (extra / nb + loss) / 2.0
    if amax is not None and A > amax:
        raise ValueError(f"serp: needs amplitude {A:.2f} > {amax}")
    total = nb * pitch - gap
    if total > seg - 2 * margin:
        raise ValueError(f"serp: segment {seg:.2f} too short for {nb} bumps")
    s = (seg - total) / 2.0
    if center is not None:
        c = (center[0] - a[0]) * ux + (center[1] - a[1]) * uy
        s = min(max(margin, c - total / 2.0), seg - margin - total)
    P = lambda t, h: (a[0] + ux * t + nx * h, a[1] + uy * t + ny * h)
    new = list(pts[:i + 1])
    for _ in range(nb):
        new += [P(s, 0), P(s, A - ch), P(s + ch, A), P(s + top - ch, A), P(s + top, A - ch), P(s + top, 0)]
        s += pitch
    new.extend(pts[i + 1:])
    return new
