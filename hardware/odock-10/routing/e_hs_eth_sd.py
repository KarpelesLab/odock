"""Ethernet MDI (U801 RTL8156BG -> J801) + PHY crystal, SD bus (U901 GL3224 -> J901) and microSD bus
(U901 -> J902). See docs/routing-notes/hs_hub.md.

MDI pair order is reversed between PHY and jack: MDI0/MDI1 stay on L1 and enter the jack from above
(under the GND shell pin, P lands on the upper-row pin, N drops between pins to the lower row);
MDI2/MDI3 change to L6 through vias next to the PHY and do the same on L6 (MDI3 through the gap
between the shell pin and the peg hole). No MDI-swap eFuse needed.
"""
import os, math, importlib.util

_spec = importlib.util.spec_from_file_location("_hs_lib", os.path.join(os.path.dirname(__file__), "_hs_lib.py"))
H = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(H)

F, B, L3 = "F.Cu", "B.Cu", "In2.Cu"
WM, GM = H.ETH100[F]          # 0.09 / 0.20
HP = (WM + GM) / 2            # half pitch of an MDI pair (0.145)

NETS = [f"ETH_MDI{i}_{s}" for i in range(4) for s in "PN"] + [
    "ETH_XI", "ETH_XO", "ETH_XO_X",
    "CR_SD_CLK", "CR_SD_CMD", "CR_SD_D0", "CR_SD_D1", "CR_SD_D2", "CR_SD_D3",
    "CR_USD_CLK", "CR_USD_CLK_S", "CR_USD_CMD", "CR_USD_D0", "CR_USD_D1", "CR_USD_D2", "CR_USD_D3",
]


def tune(P, N, q, side, **kw):
    """Accordion-tune the shorter of P/N on the segment nearest q (bumps to `side` of that segment)."""
    lp, ln = H.L(P), H.L(N)
    if abs(lp - ln) < 0.02:
        return P, N
    if lp < ln:
        P = H.serp(P, H.seg_near(P, q), ln - lp, side, center=q, **kw)
    else:
        N = H.serp(N, H.seg_near(N, q), lp - ln, side, center=q, **kw)
    return P, N


def mdi(r):
    u = lambda n: r.pad_of_net("U801", n)
    j = lambda n: r.pad_of_net("J801", n)
    xt = u("ETH_MDI0_P")[0] + 0.35          # PHY pad toe x (199.8)
    # ---------------- MDI0 (L1): under the shell pin at y 66.15, P straight onto pin 1
    p, n = u("ETH_MDI0_P"), u("ETH_MDI0_N")
    jp, jn = j("ETH_MDI0_P"), j("ETH_MDI0_N")
    y0 = 66.15
    P = [p, (xt + 0.5, p[1]), (xt + 0.5 + (y0 + HP - p[1]), y0 + HP), (jp[0] - 0.85, y0 + HP), jp]
    N = [n, (xt + 0.5, n[1]), (xt + 0.5 + (y0 - HP - n[1]), y0 - HP), (jn[0] - 0.3, y0 - HP),
         (jn[0], y0 - HP + 0.3), jn]
    P, N = tune(P, N, (202.6, y0 + HP), -1, maxamp=0.9)
    H.draw(r, "ETH_MDI0_P", P, F, WM); H.draw(r, "ETH_MDI0_N", N, F, WM)
    H.log("MDI0 (L1)", P, N)
    # ---------------- MDI1 (L1): under the shell at 65.47, then up to 63.8 above the pin rows
    p, n = u("ETH_MDI1_P"), u("ETH_MDI1_N")
    jp, jn = j("ETH_MDI1_P"), j("ETH_MDI1_N")
    y1, y1b = 65.47, 63.8
    xr = 205.55                              # start of the rise (east of the shell pin)
    c0 = (p[1] + n[1]) / 2
    path = [(xt + 0.35, c0), (xt + 0.8, c0), (xt + 0.8 + (y1 - c0), y1), (xr, y1), (xr + (y1 - y1b), y1b),
            (jn[0] - 0.4, y1b)]
    Lf, Rt = H.pair_lines(path, WM, GM)      # heading east: left = north = N
    P = [p, (xt, p[1])] + Rt[:-1] + [(jp[0] - 0.4, Rt[-1][1]), (jp[0], Rt[-1][1] + 0.4), jp]
    N = [n, (xt, n[1])] + Lf + [(jn[0], Lf[-1][1] + 0.4), jn]
    P, N = tune(P, N, (206.9, y1b + HP), -1, maxamp=0.85)
    H.draw(r, "ETH_MDI1_P", P, F, WM); H.draw(r, "ETH_MDI1_N", N, F, WM)
    H.log("MDI1 (L1)", P, N)
    # ---------------- MDI2 (L1 -> vias in the slot west of the shell pin -> L6 under the shell at 65.45)
    p, n = u("ETH_MDI2_P"), u("ETH_MDI2_N")
    jp, jn = j("ETH_MDI2_P"), j("ETH_MDI2_N")
    vn, vp = (202.1, 62.95), (202.1, 63.65)
    P1 = [p, (xt + 0.6, p[1]), (vp[0] - 0.6, p[1]), vp]
    N1 = [n, (xt + 0.6, n[1]), (vn[0] - 0.4, n[1]), vn]
    xs_ = 202.375                           # slot centreline (heading south: P west, N east)
    y2 = 65.45
    path = [(xs_, 64.1), (xs_, y2 - 0.4), (xs_ + 0.4, y2), (jn[0] - 0.4, y2)]
    Lf, Rt = H.pair_lines(path, WM, GM)      # heading south: left = east = N
    N6 = [vn, (Lf[0][0], vn[1] + (Lf[0][0] - vn[0]))] + Lf + [(jn[0], Lf[-1][1] + 0.4), jn]
    P6 = [vp, (Rt[0][0], Rt[0][1])] + Rt[1:-1] + [(jp[0] - 0.3, Rt[-1][1]), (jp[0], Rt[-1][1] + 0.3), jp]
    P, N = H.chain(P1, P6), H.chain(N1, N6)
    P, N = tune(P, N, (204.0, y2 + HP), -1, maxamp=0.75)
    i = P.index(vp); H.draw(r, "ETH_MDI2_P", P[:i + 1], F, WM); H.draw(r, "ETH_MDI2_P", P[i:], B, WM)
    i = N.index(vn); H.draw(r, "ETH_MDI2_N", N[:i + 1], F, WM); H.draw(r, "ETH_MDI2_N", N[i:], B, WM)
    r.via("ETH_MDI2_N", *vn); r.via("ETH_MDI2_P", *vp)
    H.log("MDI2 (L1/L6)", P, N)
    # ---------------- MDI3 (L1 -> vias north of the shell pin -> L6 through the shell/peg gap -> y 63.0)
    p, n = u("ETH_MDI3_P"), u("ETH_MDI3_N")
    jp, jn = j("ETH_MDI3_P"), j("ETH_MDI3_N")
    vn, vp = (202.9, 61.25), (202.9, 61.95)
    P1 = [p, (xt + 0.6, p[1]), (vp[0] - 0.6, p[1]), vp]
    N1 = [n, (xt + 0.6, n[1]), (vn[0] - 0.6, vn[1] + 0.2), (vn[0] - 0.4, vn[1]), vn]
    y3a, y3 = 61.6, 63.0
    k = 0.578 / 0.816
    xa = 203.93
    path = [(vn[0] + 0.5, y3a), (xa, y3a), (xa + (y3 - y3a) / k, y3), (jn[0] - 0.4, y3)]
    Lf, Rt = H.pair_lines(path, WM, GM)      # heading east: left = north = N
    N6 = [vn, (Lf[0][0], Lf[0][1])] + Lf[1:] + [(jn[0], Lf[-1][1] + 0.4), jn]
    P6 = [vp, (Rt[0][0], Rt[0][1])] + Rt[1:-1] + [(jp[0] - 0.4, Rt[-1][1]), (jp[0], Rt[-1][1] + 0.4), jp]
    P, N = H.chain(P1, P6), H.chain(N1, N6)
    P, N = tune(P, N, (209.0, y3 + HP), -1, maxamp=0.9)
    i = P.index(vp); H.draw(r, "ETH_MDI3_P", P[:i + 1], F, WM); H.draw(r, "ETH_MDI3_P", P[i:], B, WM)
    i = N.index(vn); H.draw(r, "ETH_MDI3_N", N[:i + 1], F, WM); H.draw(r, "ETH_MDI3_N", N[i:], B, WM)
    r.via("ETH_MDI3_N", *vn); r.via("ETH_MDI3_P", *vp)
    H.log("MDI3 (L1/L6)", P, N)


def phy_xtal(r):
    """U801 pins 12 (XI) / 11 (XO) -> vias -> Y801 / C833 / R804 / C834 on the bottom.
    XO drops at the crystal centre and runs east between the pad rows to R804; XI goes around the
    south of the XO via to its own via west of the crystal (no crossing)."""
    xi, xo = r.pad_of_net("U801", "ETH_XI"), r.pad_of_net("U801", "ETH_XO")
    w = 0.12
    vo, vi = (197.6, 71.1), (195.45, 71.1)
    toe = xi[1] + 0.35
    H.draw(r, "ETH_XO", [xo, (xo[0], toe + 0.3), (vo[0], toe + 0.45), vo], F, w)
    H.draw(r, "ETH_XI", [xi, (xi[0], 71.7), (vi[0] + 0.3, 71.7), (vi[0], 71.4), vi], F, w)
    r.via("ETH_XO", *vo); r.via("ETH_XI", *vi)
    y1, y3 = r.pad_of_net("Y801", "ETH_XI"), r.pad_of_net("Y801", "ETH_XO_X")
    c833 = r.pad_of_net("C833", "ETH_XI")
    r4o, r4x = r.pad_of_net("R804", "ETH_XO"), r.pad_of_net("R804", "ETH_XO_X")
    c834 = r.pad_of_net("C834", "ETH_XO_X")
    H.draw(r, "ETH_XI", [c833, (vi[0] - 0.3, c833[1]), vi, (y1[0] - 0.35, y1[1] + 0.35), y1], B, w)
    H.draw(r, "ETH_XO", [vo, (r4o[0] - 0.55, vo[1]), r4o], B, w)
    H.draw(r, "ETH_XO_X", [y3, (y3[0] + 0.9, y3[1]), (r4x[0] - 0.4, r4x[1]), r4x], B, w)
    H.draw(r, "ETH_XO_X", [r4x, (r4x[0] + 0.6, r4x[1] + 0.3), (r4x[0] + 0.6, c834[1] - 0.3), (c834[0] + 0.3, c834[1]), c834], B, w)


def sd1(r):
    """SD slot 1: U901 pins 37-42 (bottom) -> J901 contacts (top). Routed on L6 (B.Cu, 50 ohm, solid L5
    GND below), nested so nothing crosses, one via per line just north of its contact, then a short L1
    stub. Lengths matched to the longest (D1) with accordion meanders in the free bottom area."""
    W = H.SE50[B]
    u = lambda n: r.pad_of_net("U901", n)
    jp = lambda n: r.pad_of_net("J901", n)
    yv = 107.85
    sig = {}
    # (net, run y, via x)
    D1, D0, CLK, CMD, D3, D2 = ("CR_SD_D1", "CR_SD_D0", "CR_SD_CLK", "CR_SD_CMD", "CR_SD_D3", "CR_SD_D2")
    runs = [(D1, 113.2, jp(D1)[0]), (D0, 112.0, jp(D0)[0]), (CLK, 111.3, jp(CLK)[0]),
            (CMD, 110.6, jp(CMD)[0] - 0.38)]
    for net, yr, xv in runs:
        p = u(net)
        pts = [p, (p[0], yr + 0.3), (p[0] - 0.3, yr), (xv + 0.3, yr), (xv, yr - 0.3), (xv, yv)]
        sig[net] = (pts, (xv, yv))
    p = u(D3)                                   # straight north to its via, L1 stub west to pad 1
    sig[D3] = ([p, (p[0], yv)], (p[0], yv))
    p = u(D2)
    x2 = jp(D2)[0]
    sig[D2] = ([p, (p[0], 110.6), (x2, 110.6 - (x2 - p[0])), (x2, yv)], (x2, yv))
    full = {}
    for net, (pts, v) in sig.items():
        pad = jp(net)
        stub = [v, (pad[0], v[1]) if abs(pad[0] - v[0]) > 1e-3 else v, (pad[0], pad[1] - 0.6), pad]
        full[net] = (pts, stub)
    target = max(H.L(a) + H.L(b) for a, b in full.values())
    # meanders: (net, point on segment, side, amax); heading north, side +1 = west, -1 = east
    tunes = {D0: ((jp(D0)[0], 109.8), +1, 1.15), CLK: ((jp(CLK)[0], 109.5), +1, 3.5),
             CMD: ((jp(CMD)[0] - 0.38, 109.2), +1, 5.5), D3: ((u(D3)[0], 109.1), +1, 3.8),
             D2: ((jp(D2)[0], 108.9), -1, 3.0)}
    for net, (pts, stub) in full.items():
        extra = target - H.L(pts) - H.L(stub)
        if net in tunes and extra > 0.05:
            q, side, amax = tunes[net]
            pts = H.serp(pts, H.seg_near(pts, q), extra, side, maxamp=amax, amax=amax,
                         top=0.3, gap=0.36 if net != CLK else 0.42, margin=0.25, center=q)
        H.draw(r, net, pts, B, W)
        r.via(net, *pts[-1])
        H.draw(r, net, stub, F, 0.2)
        H.LOG.append((f"SD1 {net[3:]}", H.L(pts) + H.L(stub), target))


def usd(r):
    """microSD slot 2: U901 pins 27-32 (-x side, bottom) -> J902 (top), ~110 mm.
    Bottom stubs west between C912/C910, turn north into a via row at y 114.3 (so the L3 bus can leave
    southward with D1 west / D2 east); L3 lanes fan out west under the SD socket (length-tuning
    meanders there), turn east into the band y 129.7-132.4, north at x 179-181.7, east along
    y 120.2-122.9 and drop into one via per contact just north of the J902 contact row.
    CLK goes through R908 (bottom, just west of the via row); all lines are matched to the longest."""
    W3 = H.SE50[L3]
    W6 = H.SE50[B]
    u = lambda n: r.pad_of_net("U901", n)
    jp = lambda n: r.pad_of_net("J902", n)
    D2, D3, CMD, CLK, D0, D1 = ("CR_USD_D2", "CR_USD_D3", "CR_USD_CMD", "CR_USD_CLK", "CR_USD_D0", "CR_USD_D1")
    CLKS = "CR_USD_CLK_S"
    yrow = 114.3
    xvia = {D2: 126.3, D3: 125.55, CMD: 124.8, CLK: 123.2, D0: 122.3, D1: 121.55}
    # bottom stubs
    stub = {}
    for net, xv in xvia.items():
        p = u(net)
        pts = [p, (p[0] - 0.4, p[1]), (xv + 0.3, p[1]), (xv, p[1] - 0.3), (xv, yrow)]
        stub[net] = pts
        H.draw(r, net, pts, B, W6)
        r.via(net, xv, yrow)
    # CLK -> R908 (bottom, west of the via row) -> CLK_S: CLK on L3 over the D0/D1 vias, CLK_S on B.Cu
    # under the D0/D1 stubs to a via between the D0 and CMD lanes
    r1, r2 = r.pad_of_net("R908", CLK), r.pad_of_net("R908", CLKS)
    v1 = (r1[0] - 0.55, r1[1])
    clk3 = [(xvia[CLK], yrow), (xvia[CLK], 113.9), (xvia[CLK] - 0.3, 113.6), (v1[0] + 0.4, 113.6), (v1[0], 114.0), v1]
    H.draw(r, CLK, clk3, L3, W3)
    r.via(CLK, *v1)
    H.draw(r, CLK, [v1, r1], B, W6)
    v2 = (118.45, 119.75)
    clks6 = [r2, (r2[0], 117.5), (v2[0] + 0.1, v2[1] - 0.6), v2]
    H.draw(r, CLKS, clks6, B, W6)
    r.via(CLKS, *v2)
    clks_head = [v2]
    # L3 lanes: (net, start point, fan-out c=x+y of the 45-degree SW diagonal, lane x, band y)
    order = [D1, D0, CLKS, CMD, D3, D2]
    lane_x = {D1: 113.0, D0: 115.4, CLKS: 117.8, CMD: 120.4, D3: 122.9, D2: 125.4}
    band_y = {D2: 129.7, D3: 130.2, CMD: 130.7, CLKS: 131.3, D0: 131.9, D1: 132.4}
    vert_x = {D2: 179.0, D3: 179.5, CMD: 180.0, CLKS: 180.6, D0: 181.2, D1: 181.7}
    top_y = {D1: 122.9, D0: 122.4, CLKS: 121.8, CMD: 121.2, D3: 120.7, D2: 120.2}
    pad_of = {D1: jp(D1), D0: jp(D0), CLKS: jp(CLKS), CMD: jp(CMD), D3: jp(D3), D2: jp(D2)}
    start = {n: (xvia[n], yrow) for n in (D1, D0, CMD, D3, D2)}
    start[CLKS] = v2
    c = 236.15
    lanes = {}
    for net in order:
        sx, sy = start[net]
        ys = max(sy + 0.3, c - sx)            # start of the SW diagonal
        c = sx + ys
        xl = lane_x[net]
        yl = c - xl                           # end of the diagonal on the lane
        by, vx, ty = band_y[net], vert_x[net], top_y[net]
        pad = pad_of[net]
        vy = 123.4
        pts = [(sx, sy), (sx, ys), (xl, yl), (xl, by - 0.4), (xl + 0.4, by), (vx - 0.4, by), (vx, by - 0.4),
               (vx, ty + 0.4), (vx + 0.4, ty), (pad[0] - 0.4, ty), (pad[0], ty + 0.4), (pad[0], vy)]
        lanes[net] = pts
        c += 0.9
    # lengths (bottom stub + L3 + L1 stub); CLK path includes the R908 detour
    l1 = {n: H.L([(pad_of[n][0], 123.4), pad_of[n]]) for n in order}
    tot = {}
    for n in order:
        if n == CLKS:
            tot[n] = H.L(stub[CLK]) + H.L(clk3) + H.L([v1, r1]) + H.L(clks6) + H.L(lanes[n]) + l1[n]
        else:
            tot[n] = H.L(stub[n]) + H.L(lanes[n]) + l1[n]
    target = max(tot.values())
    for n in order:
        pts = lanes[n]
        extra = target - tot[n]
        if extra > 0.05:
            q = (pts[2][0], (pts[2][1] + pts[3][1]) / 2)      # the lane's southward run
            amax = 1.5 if n != D1 else 1.3
            pts = H.serp(pts, 2, extra, -1, maxamp=amax, amax=amax * 1.6, top=0.3,
                         gap=0.6 if n == CLKS else 0.45, margin=0.3, center=q)
        H.draw(r, n, pts, L3, W3)
        r.via(n, *pts[-1])
        H.draw(r, n, [pts[-1], pad_of[n]], F, 0.2)
        name = "CLK (pin->R908->J902)" if n == CLKS else n[7:]
        H.LOG.append((f"uSD {name}", tot[n] + max(0.0, extra), target))


def route(board, r):
    mdi(r)
    phy_xtal(r)
    sd1(r)
    usd(r)
    for w in H.WARN:
        print("WARNING:", w)
    for name, lp, ln in H.LOG:
        print(f"  {name:34s} P {lp:7.2f}  N {ln:7.2f}  skew {abs(lp - ln):.3f}")
