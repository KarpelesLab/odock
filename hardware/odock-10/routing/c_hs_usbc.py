"""odock-10 routing: high-speed nets of the usbc block and their links to the hub.

See docs/routing-notes/hs_usbc.md for the plan, layer use, lengths and open items.
"""
import math

# ---------------------------------------------------------------------------------------------
# Widths (brief): L1/L6 85 ohm 0.10/0.12, 90 ohm 0.10/0.18; L3 85 ohm 0.18/0.18, 90 ohm 0.16/0.20
W85, G85 = 0.10, 0.12
G85D = G85                     # lane nets are HS_85 now (netclass patterns): nominal 0.12 gap
W90, G90 = 0.10, 0.18
W85_L3, G85_L3 = 0.18, 0.18
W90_L3, G90_L3 = 0.16, 0.20
WCC = 0.20                     # CC lines (controlled 0.2 mm)
WSLOW = 0.10                   # SBU / misc (0.3 mm from the HS_85/USB_90 neighbours)
VIA_HS = (0.45, 0.25)          # signal vias for 10G / DP pairs
VIA_S = (0.40, 0.20)           # slow-signal vias in congested spots
VIA_T = (0.35, 0.15)           # tight spots (JLC 6L: 0.15 drill is standard)

DP_LANES = [f"DP_ML{k}_{p}" for k in range(4) for p in "PN"] + \
           [f"DS_DP_ML{k}_{p}" for k in range(4) for p in "PN"]

LAPTOP_LANES = ["UP_C_TX1_P", "UP_C_TX1_N", "UP_TX1_P", "UP_TX1_N", "UP_C_TX2_P", "UP_C_TX2_N", "UP_TX2_P",
                "UP_TX2_N", "UP_RX1_P", "UP_RX1_N", "UP_RX2_P", "UP_RX2_N"]

DS_LANES = ["DS_C_TX1_P", "DS_C_TX1_N", "DS_TX1_P", "DS_TX1_N", "DS_C_TX2_P", "DS_C_TX2_N", "DS_TX2_P",
            "DS_TX2_N", "DS_RX1_P", "DS_RX1_N", "DS_RX2_P", "DS_RX2_N"]

HUB_SS = ["HUB_UP_SS_TXP", "HUB_UP_SS_TXN", "HUB_UP_SS_RXP", "HUB_UP_SS_RXN", "UP_SSRX_P", "UP_SSRX_N",
          "HUB_UP_TXP_IC", "HUB_UP_TXN_IC",
          "HUB_DSC_SS_TXP", "HUB_DSC_SS_TXN", "HUB_DSC_SS_RXP", "HUB_DSC_SS_RXN", "DS_SSRX_P", "DS_SSRX_N",
          "HUB_P5_TXP_IC", "HUB_P5_TXN_IC"]

SLOW2 = ["UP_C_CC1", "UP_C_CC2", "UP_C_SBU1", "UP_C_SBU2", "LAPTOP_CC1", "LAPTOP_CC2"]
SLOW3 = ["DS_CC1", "DS_CC2", "DS_SBU1", "DS_SBU2", "HUB_DSC_DP", "HUB_DSC_DN"]
SLOW4 = ["DS_C_CC1", "DS_C_CC2", "DS_C_SBU1", "DS_C_SBU2"]
SLOW = SLOW2 + SLOW3 + SLOW4 + ["DP_AUX_P", "DP_AUX_N", "DS_AUX_P", "DS_AUX_N", "UP_SBU1", "UP_SBU2", "LAPTOP_USB_DP", "LAPTOP_USB_DN"]

NETS = DP_LANES + LAPTOP_LANES + DS_LANES + HUB_SS + SLOW

LOG = []


def _len(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


# ---------------------------------------------------------------------------------------------
def dp_main_link(r):
    """U502 right edge -> 220 nF (P column x 160.51, N column x 162.62) -> U503 left edge, L1.
    P and N run straight out of the pins for 0.9 mm so a 0.35 mm strap via fits between lanes at
    x 159.4 (U502 side) / 163.75 (U503 side)."""
    for k in range(4):
        pp = r.pad_of_net("U502", f"DP_ML{k}_P"); pn = r.pad_of_net("U502", f"DP_ML{k}_N")
        qp = r.pad_of_net("U503", f"DS_DP_ML{k}_P"); qn = r.pad_of_net("U503", f"DS_DP_ML{k}_N")
        cp = "C%d" % (515 + 2 * k); cn = "C%d" % (516 + 2 * k)
        cp1, cp2 = r.pad(cp, 1), r.pad(cp, 2)
        cn1, cn2 = r.pad(cn, 1), r.pad(cn, 2)
        # P: above the N cap (N cap pad top = cn1.y - 0.31; keep 0.2 from centre)
        yp_hi = cn1[1] - 0.31 - 0.20
        yP = min(qp[1], yp_hi)
        P1 = [pp, (159.65, pp[1]), (159.80, cp1[1]), cp1]
        P2 = [cp2, (161.45, cp2[1]), (161.60, yP), (163.45, yP), (163.60, qp[1]), qp]
        if abs(yP - qp[1]) < 1e-6:
            P2 = [cp2, (161.45, cp2[1]), (161.60, yP), qp]
        # N: below the P cap (P cap pad bottom = cp1.y + 0.31; keep 0.2 from centre)
        yN = cp1[1] + 0.31 + 0.20
        N1 = [pn, (159.05, pn[1]), (159.05 + (yN - pn[1]), yN), (161.55, yN), (161.80, cn1[1]), cn1]
        N2 = [cn2, (163.40, cn2[1]), (163.55, qn[1]), qn]
        r.track(f"DP_ML{k}_P", P1, "F.Cu", W85)
        r.track(f"DS_DP_ML{k}_P", P2, "F.Cu", W85)
        r.track(f"DP_ML{k}_N", N1, "F.Cu", W85)
        r.track(f"DS_DP_ML{k}_N", N2, "F.Cu", W85)
        lp = _len(P1) + _len(P2) + (cp2[0] - cp1[0])
        ln = _len(N1) + _len(N2) + (cn2[0] - cn1[0])
        LOG.append(("DP ML%d" % k, lp, ln))


def bump(pts, seg, side, h, n=1, w=None):
    """Insert n 45-degree bumps of height h on segment index `seg` of polyline pts (side +1 = left of
    travel in a y-down frame). Adds about 0.83*h*n of length. Returns new list."""
    a, b = pts[seg], pts[seg + 1]
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    nx, ny = (uy * side, -ux * side)      # left normal in y-down frame is (dy, -dx)
    out = list(pts[:seg + 1])
    pitch = L / (n + 1)
    for i in range(n):
        c = pitch * (i + 1)
        for t, hh in ((c - 1.5 * h, 0), (c - 0.5 * h, h), (c + 0.5 * h, h), (c + 1.5 * h, 0)):
            out.append((a[0] + ux * t + nx * hh, a[1] + uy * t + ny * hh))
    out += pts[seg + 1:]
    return out


def _offset(pts, d):
    import sys
    return sys.modules["__main__"]._offset_polyline(pts, d)


def _nearest_seg(pts, q):
    best, bi = 1e9, 0
    for i, (a, b) in enumerate(zip(pts, pts[1:])):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy or 1e-12
        t = max(0.0, min(1.0, ((q[0] - a[0]) * dx + (q[1] - a[1]) * dy) / L2))
        d = math.hypot(a[0] + t * dx - q[0], a[1] + t * dy - q[1])
        if d < best:
            best, bi = d, i
    return bi


def lane(r, netp, netn, path, layer="F.Cu", w=W85, g=G85D, p_from=None, n_from=None, p_to=None, n_to=None,
         name=None, extra_p=0.0, extra_n=0.0, pleft=True, tune=()):
    """Coupled pair along centreline with P on the visual LEFT of travel (pleft=True); returns (P, N).
    tune: [(which 'P'/'N', (x, y) near the segment, side +1 visual-left/-1 right, bump height, count)] adds
    45-degree bumps (length matching) to that leg before it is drawn."""
    d = (w + g) / 2
    L, R = _offset(path, -d), _offset(path, d)      # visual left / right in the y-down frame
    P, N = (L, R) if pleft else (R, L)
    if p_from: P = [p_from] + P
    if n_from: N = [n_from] + N
    if p_to: P = P + [p_to]
    if n_to: N = N + [n_to]
    for which, q, side, h, n in tune:
        pts = P if which == "P" else N
        pts = bump(pts, _nearest_seg(pts, q), side, h, n)
        if which == "P":
            P = pts
        else:
            N = pts
    r.track(netp, P, layer, w)
    r.track(netn, N, layer, w)
    if name:
        LOG.append((name, _len(P) + extra_p, _len(N) + extra_n))
    return P, N


def chamfer(pts, d=0.3):
    """Replace interior corners of a polyline by 45-degree chamfers of leg d (for 90-degree corners)."""
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        a, b, c = pts[i - 1], pts[i], pts[i + 1]
        l1 = math.hypot(b[0] - a[0], b[1] - a[1]); l2 = math.hypot(c[0] - b[0], c[1] - b[1])
        k1, k2 = min(d, l1 / 2), min(d, l2 / 2)
        out.append((b[0] - (b[0] - a[0]) / l1 * k1, b[1] - (b[1] - a[1]) / l1 * k1))
        out.append((b[0] + (c[0] - b[0]) / l2 * k2, b[1] + (c[1] - b[1]) / l2 * k2))
    out.append(pts[-1])
    return out


def laptop_fanin(r):
    """D502/D503 (flow-through) -> TX caps -> U502 left edge as nested L-shapes on L1 (85 ohm)."""
    U = "U502"
    # --- TX1: D502 bottom pads 10/9 -> C509/C510 -> pins 9/10
    d10, d9 = r.pad("D502", 10), r.pad("D502", 9)
    r.track("UP_C_TX1_P", [d10, (d10[0], 63.40), (r.pad("C509", 2)[0], 63.75), r.pad("C509", 2)], "F.Cu", W85)
    r.track("UP_C_TX1_N", [d9, (d9[0], 63.40), (r.pad("C510", 2)[0], 63.75), r.pad("C510", 2)], "F.Cu", W85)
    pp, pn = r.pad_of_net(U, "UP_TX1_P"), r.pad_of_net(U, "UP_TX1_N")
    cx, cy = 153.40, (pp[1] + pn[1]) / 2
    path = chamfer([(cx, 66.00), (cx, cy), (154.45, cy)], 0.35)
    c1, c2 = r.pad("C509", 1), r.pad("C510", 1)
    lane(r, "UP_TX1_P", "UP_TX1_N", path, p_from=(c1[0], c1[1]), n_from=(c2[0], c2[1]),
         p_to=pp, n_to=pn, name="UP TX1 (cap-mux)", tune=[("P", (153.52, 66.6), 1, 0.38, 1)])
    # --- RX1: D502 bottom pads 7/6 -> pins 12/13
    d7, d6 = r.pad("D502", 7), r.pad("D502", 6)
    pp, pn = r.pad_of_net(U, "UP_RX1_P"), r.pad_of_net(U, "UP_RX1_N")
    cx, cy = (d7[0] + d6[0]) / 2, (pp[1] + pn[1]) / 2
    path = chamfer([(cx, 63.45), (cx, cy), (154.45, cy)], 0.5)
    lane(r, "UP_RX1_P", "UP_RX1_N", path, p_from=d7, n_from=d6, p_to=pp, n_to=pn, name="UP RX1 (esd-mux)")
    # --- RX2: D503 bottom pads 4/5 -> pins 16/15
    d4, d5 = r.pad("D503", 4), r.pad("D503", 5)
    pp, pn = r.pad_of_net(U, "UP_RX2_P"), r.pad_of_net(U, "UP_RX2_N")
    cx, cy = (d4[0] + d5[0]) / 2, (pp[1] + pn[1]) / 2
    path = chamfer([(cx, 63.45), (cx, cy), (154.45, cy)], 0.5)
    lane(r, "UP_RX2_P", "UP_RX2_N", path, p_from=d4, n_from=d5, p_to=pp, n_to=pn, name="UP RX2 (esd-mux)",
         pleft=False, tune=[("N", (149.03, 66.0), 1, 0.25, 2)])
    # --- TX2: D503 bottom pads 1/2 -> C511/C512 -> pins 19/18
    d1, d2 = r.pad("D503", 1), r.pad("D503", 2)
    r.track("UP_C_TX2_P", [d1, (d1[0], 63.30), (r.pad("C511", 2)[0], 63.55), r.pad("C511", 2)], "F.Cu", W85)
    r.track("UP_C_TX2_N", [d2, (d2[0], 63.30), (r.pad("C512", 2)[0], 63.80), r.pad("C512", 2)], "F.Cu", W85)
    pp, pn = r.pad_of_net(U, "UP_TX2_P"), r.pad_of_net(U, "UP_TX2_N")
    c1, c2 = r.pad("C511", 1), r.pad("C512", 1)
    cx, cy = 147.51, (pp[1] + pn[1]) / 2
    path = chamfer([(cx, 66.10), (cx, cy), (154.45, cy)], 0.5)
    lane(r, "UP_TX2_P", "UP_TX2_N", path, p_from=c1, n_from=c2, p_to=pp, n_to=pn, name="UP TX2 (cap-mux)",
         pleft=False, tune=[("N", (147.64, 67.0), 1, 0.40, 2), ("P", (147.39, 69.6), -1, 0.20, 1)])


def via(r, net, xy, v=VIA_HS):
    r.via(net, xy[0], xy[1], v[0], v[1])
    return xy


def ds_fanin(r):
    """D506/D507 -> TX caps -> U503 right edge (L1). U503's pin order swaps the two pairs of each half
    relative to the ESD order, so one pair per half hops on L3 (RX2 on the left half, TX1 on the right)."""
    U = "U503"
    # --- ESD -> TX caps (connector side of the caps, L1)
    for d, c, net in (("D507", "C534", "DS_C_TX2_P"), ("D507", "C535", "DS_C_TX2_N"),
                      ("D506", "C533", "DS_C_TX1_N"), ("D506", "C532", "DS_C_TX1_P")):
        a = [p for p in (1, 2, 9, 10) if r.fps[d] and any(pp.GetNumber() == str(p) and pp.GetNetname().endswith(net)
                                                          for pp in r.fps[d].Pads())]
        dp = max((r.pad(d, n) for n in a), key=lambda q: q[1])          # bottom-row pad
        cp = r.pad(c, 2)
        r.track(net, [dp, (dp[0], dp[1] + 0.35), (cp[0], cp[1] - 0.45), cp], "F.Cu", W85)
    # --- TX2 (inner left) on L1: caps -> pins 37/36
    pp, pn = r.pad_of_net(U, "DS_TX2_P"), r.pad_of_net(U, "DS_TX2_N")
    c1, c2 = r.pad("C534", 1), r.pad("C535", 1)
    cx, cy = 169.35, (pp[1] + pn[1]) / 2
    path = chamfer([(cx, 66.05), (cx, cy), (168.70, cy)], 0.35)
    lane(r, "DS_TX2_P", "DS_TX2_N", path, p_from=c1, n_from=c2, p_to=pp, n_to=pn, name="DS TX2 (cap-mux)",
         pleft=False)
    # --- RX2 (outer left): D507 4/5 -> vias -> L3 -> vias at U503 NE corner -> pins 40/39
    d4, d5 = r.pad("D507", 4), r.pad("D507", 5)
    pp, pn = r.pad_of_net(U, "DS_RX2_P"), r.pad_of_net(U, "DS_RX2_N")
    vp1, vn1 = (170.45, 65.30), (171.00, 65.30)
    vp2, vn2 = (168.20, 66.00), (168.70, 66.45)
    for n, a, b in (("DS_RX2_P", vp1, vp2), ("DS_RX2_N", vn1, vn2)):
        via(r, n, a, VIA_T); via(r, n, b, VIA_T)
    r.track("DS_RX2_P", bump([d4, (d4[0], 63.40), vp1], 1, 1, 0.16, 2), "F.Cu", W85)
    r.track("DS_RX2_N", [d5, (d5[0], 64.9), vn1], "F.Cu", W85)
    r.track("DS_RX2_P", bump([vp1, (169.95, 65.30), (169.45, 65.55), vp2], 2, -1, 0.20, 2), "In2.Cu", W85_L3)
    r.track("DS_RX2_N", [vn1, (171.00, 65.65), (170.60, 66.05), (169.25, 66.05), vn2], "In2.Cu", W85_L3)
    r.track("DS_RX2_P", [vp2, (pp[0], vp2[1] + 0.4), pp], "F.Cu", W85)
    r.track("DS_RX2_N", [vn2, (vn2[0], pn[1]), pn], "F.Cu", W85)
    # --- RX1 (inner right) on L1: D506 7/6 -> pins 30/31
    d7, d6 = r.pad("D506", 7), r.pad("D506", 6)
    pp, pn = r.pad_of_net(U, "DS_RX1_P"), r.pad_of_net(U, "DS_RX1_N")
    cx, cy = (d7[0] + d6[0]) / 2, (pp[1] + pn[1]) / 2
    path = chamfer([(cx, 63.45), (cx, cy), (168.70, cy)], 0.5)
    lane(r, "DS_RX1_P", "DS_RX1_N", path, p_from=d7, n_from=d6, p_to=pp, n_to=pn, name="DS RX1 (esd-mux)",
         tune=[("N", (172.73, 66.5), -1, 0.25, 2)])
    # --- TX1 (outer right): caps C533/C532 -> vias -> L3 -> vias west of RX1 -> pins 34/33
    pp, pn = r.pad_of_net(U, "DS_TX1_P"), r.pad_of_net(U, "DS_TX1_N")
    c1, c2 = r.pad("C532", 1), r.pad("C533", 1)
    vp1, vn1 = (176.40, 66.60), (175.75, 66.70)        # east of R410; leaves room for the DS_CC vias
    vn2, vp2 = (171.60, 69.70), (171.60, 70.30)
    for n, a, b in (("DS_TX1_P", vp1, vp2), ("DS_TX1_N", vn1, vn2)):
        via(r, n, a); via(r, n, b)
    r.track("DS_TX1_P", [c1, (c1[0] + 0.23, c1[1] + 0.20), (c1[0] + 0.23, 65.90), (176.40, 66.40), vp1], "F.Cu", W85)
    r.track("DS_TX1_N", [c2, (c2[0], 66.40), (175.45, 66.40), vn1], "F.Cu", W85)
    lane(r, "DS_TX1_P", "DS_TX1_N", [(176.07, 67.15), (176.07, 67.45), (173.52, 70.00), (172.05, 70.00)],
         "In2.Cu", W85_L3, G85_L3, p_from=vp1, n_from=vn1, p_to=vp2, n_to=vn2, name="DS TX1 (L3 hop)",
         )
    cy = (pp[1] + pn[1]) / 2
    lane(r, "DS_TX1_P", "DS_TX1_N", [(171.20, cy), (168.70, cy)], p_from=vp2, n_from=vn2, p_to=pp, n_to=pn,
         name="DS TX1 (via-mux)")


# L3 corridor (x 159.8-163.4, under the DP caps): centre-lines of the four hub pairs, west -> east
COL = {"UP_TX": 160.37, "UP_RX": 161.19, "P5_RX": 162.01, "P5_TX": 162.83}
# L3 east-runs at the bottom of the corridor (y of the pair centre-line)
ROW = {"P5_TX": 75.55, "P5_RX": 76.92, "UP_RX": 77.74, "UP_TX": 78.56}
# L1 columns in the hub corridor (x of the pair centre-line)
HCOL = {"UP_RX": 167.95, "UP_TX": 169.45, "USB_L": 171.01, "P5_RX": 171.70, "P5_TX": 172.97}


def hub_links(r):
    """TUSB1064/TUSB1046 USB side <-> USB7206C upstream port and port 5 (90 ohm).
    Top: short L1 escapes from the mux pins / SSRX caps to via pairs, L3 east/west into the corridor under
    the DP caps, L3 south, L3 east at y 76-79, via pairs back to L1 (x 166.9-174.2, y 78-79.5) and L1
    down the hub corridor (x 168-174) to the hub pins / hub-side TX caps (y 88.2)."""
    W, G = W90_L3, G90_L3
    # ---------------- SSRX caps (chip side) --------------------------------------------------------
    for u, pin_net, cap in (("U502", "UP_SSRX_P", "C513"), ("U502", "UP_SSRX_N", "C514"),
                            ("U503", "DS_SSRX_P", "C530"), ("U503", "DS_SSRX_N", "C531")):
        a, b = r.pad_of_net(u, pin_net), r.pad(cap, 1)
        r.track(pin_net, [a, (a[0], a[1] - 0.45), (b[0], b[1] + 0.40), b], "F.Cu", W90)
    # ---------------- top escapes (L1) + vias -------------------------------------------------------
    # UP TX (pins 8/7): P via west, N via north (free spots between C513 and the bottom decaps)
    tP, tN = r.pad_of_net("U502", "HUB_UP_SS_TXP"), r.pad_of_net("U502", "HUB_UP_SS_TXN")
    vtP, vtN = (154.90, 64.95), (155.60, 64.30)
    r.track("HUB_UP_SS_TXP", [tP, (tP[0], 66.05), (vtP[0], 65.50), vtP], "F.Cu", W90)
    r.track("HUB_UP_SS_TXN", [tN, (tN[0], 64.80), (vtN[0], 64.55), vtN], "F.Cu", W90)
    # UP RX (cap pads 2, north side)
    rP, rN = r.pad("C513", 2), r.pad("C514", 2)
    vrP, vrN = (rP[0], 63.55), (157.30, 63.60)
    r.track("HUB_UP_SS_RXP", [rP, vrP], "F.Cu", W90)
    r.track("HUB_UP_SS_RXN", [rN, vrN], "F.Cu", W90)
    # P5 TX (pins 8/7)
    sP, sN = r.pad_of_net("U503", "HUB_DSC_SS_TXP"), r.pad_of_net("U503", "HUB_DSC_SS_TXN")
    vsP, vsN = (164.15, 66.05), (164.45, 65.30)
    r.track("HUB_DSC_SS_TXP", [sP, (164.60, 66.05), vsP], "F.Cu", W90)
    r.track("HUB_DSC_SS_TXN", [sN, (sN[0], 66.25), (164.85, 65.80), (164.65, 65.45), vsN], "F.Cu", W90)
    # P5 RX (cap pads 2) -> L1 west along y 63.45 -> vias in the free box x 162.2-163.7
    qP, qN = r.pad("C530", 2), r.pad("C531", 2)
    vqN, vqP = (162.75, 63.15), (163.45, 63.75)
    r.track("HUB_DSC_SS_RXN", [qN, (qN[0], 63.60), (qN[0] - 0.29, 63.31)], "F.Cu", W90)
    lane(r, "HUB_DSC_SS_RXP", "HUB_DSC_SS_RXN", [(qP[0], 63.45), (163.95, 63.45)], "F.Cu", W90, G90,
         p_from=qP, n_from=(qN[0] - 0.29, 63.31), p_to=vqP, n_to=vqN, name="P5 RX (cap-via)",
         tune=[("P", (164.8, 63.59), 1, 0.40, 1)])
    for n, xy in (("HUB_UP_SS_TXP", vtP), ("HUB_UP_SS_TXN", vtN), ("HUB_UP_SS_RXP", vrP), ("HUB_UP_SS_RXN", vrN),
                  ("HUB_DSC_SS_TXP", vsP), ("HUB_DSC_SS_TXN", vsN), ("HUB_DSC_SS_RXP", vqP),
                  ("HUB_DSC_SS_RXN", vqN)):
        via(r, n, xy)
    # ---------------- L3: top approach, corridor, bottom east-runs ----------------------------------
    # UP TX: east along y 65.0 (P south = visual right), corridor column, east-run at ROW
    c, y0 = COL["UP_TX"], 64.62
    lane(r, "HUB_UP_SS_TXP", "HUB_UP_SS_TXN",
         chamfer([(vtN[0], y0), (c, y0), (c, ROW["UP_TX"]), (166.55, ROW["UP_TX"])], 0.6), "In2.Cu", W, G,
         p_from=vtP, n_from=vtN, p_to=(166.90, 79.00), n_to=(166.90, 78.40), name="UP TX (L3)", pleft=False,
         tune=[("P", (163.6, 78.74), -1, 0.30, 4)])
    # UP RX: P passes north of the N via; east along y 63.32, column, east-run
    c, y0 = COL["UP_RX"], 63.27
    yR = ROW["UP_RX"]
    lane(r, "HUB_UP_SS_RXP", "HUB_UP_SS_RXN",
         chamfer([(157.95, y0), (c, y0), (c, yR), (167.75, yR)], 0.6), "In2.Cu", W, G,
         p_from=(vrP[0] + 0.35, y0 - 0.18), n_from=vrN, name="UP RX (L3)",
         tune=[("N", (159.5, 63.45), -1, 0.35, 2)])
    r.track("HUB_UP_SS_RXP", [vrP, (vrP[0] + 0.35, y0 - 0.18)], "In2.Cu", W)
    r.track("HUB_UP_SS_RXN", [(167.75, yR + 0.18), (168.00, 78.15)], "In2.Cu", W)
    r.track("HUB_UP_SS_RXP", [(167.75, yR - 0.18), (168.45, yR - 0.18), (168.60, yR - 0.03), (168.60, 78.15)],
            "In2.Cu", W)
    # P5 RX: from the box vias west to its column (P east in the corridor)
    c = COL["P5_RX"]
    lane(r, "HUB_DSC_SS_RXP", "HUB_DSC_SS_RXN",
         chamfer([(162.75, 63.45), (c, 63.45), (c, ROW["P5_RX"]), (172.60, ROW["P5_RX"]), (172.60, 79.10)], 0.6),
         "In2.Cu", W, G, p_from=vqP, n_from=vqN, p_to=(172.90, 79.50), n_to=(172.30, 79.50), name="P5 RX (L3)",
         tune=[("P", (168.0, 76.74), 1, 0.25, 6)])
    # P5 TX: N detours south of the P via so P ends up west in the corridor (fixes the hub cap order)
    c = COL["P5_TX"]
    lane(r, "HUB_DSC_SS_TXP", "HUB_DSC_SS_TXN",
         chamfer([(163.95, 65.73), (c, 65.73), (c, ROW["P5_TX"]), (168.60, ROW["P5_TX"]), (173.85, ROW["P5_TX"]),
                  (173.85, 79.10)], 0.6),
         "In2.Cu", W, G, p_from=vsP, n_from=(164.25, 65.55), p_to=(174.15, 79.50), n_to=(173.55, 79.50),
         name="P5 TX (L3)", tune=[("P", (171.0, 75.37), 1, 0.30, 3)])
    r.track("HUB_DSC_SS_TXN", [vsN, (164.25, 65.55)], "In2.Cu", W)
    # ---------------- bottom transitions L3 -> L1 ---------------------------------------------------
    for n, xy in (("HUB_UP_SS_TXP", (166.90, 79.00)), ("HUB_UP_SS_TXN", (166.90, 78.40)),
                  ("HUB_UP_SS_RXP", (168.60, 78.15)), ("HUB_UP_SS_RXN", (168.00, 78.15)),
                  ("HUB_DSC_SS_RXP", (172.90, 79.50)), ("HUB_DSC_SS_RXN", (172.30, 79.50)),
                  ("HUB_DSC_SS_TXP", (174.15, 79.50)), ("HUB_DSC_SS_TXN", (173.55, 79.50))):
        via(r, n, xy)
    # ---------------- L1 hub corridor ---------------------------------------------------------------
    # UP RX: straight down to pins 94/95
    hP, hN = r.pad_of_net("U601", "HUB_UP_SS_RXP"), r.pad_of_net("U601", "HUB_UP_SS_RXN")
    c = HCOL["UP_RX"]
    lane(r, "HUB_UP_SS_RXP", "HUB_UP_SS_RXN", [(c, 78.75), (c, 83.00), (c, 90.85)], "F.Cu", W90, G90,
         p_from=(168.60, 78.15), n_from=(168.00, 78.15), p_to=(hP[0], 91.15), n_to=(c - 0.14, 91.30),
         name="UP RX (L1)", extra_p=1.01, extra_n=0.86, tune=[("N", (168.03, 80.5), -1, 0.32, 3), ("N", (168.03, 87.0), -1, 0.32, 1)])
    r.track("HUB_UP_SS_RXP", [(hP[0], 91.15), hP], "F.Cu", W90)
    r.track("HUB_UP_SS_RXN", [(c - 0.14, 91.30), (hN[0], 91.65), hN], "F.Cu", W90)
    # UP TX: north-east to y 77.1, east, down the column to the caps C601/C602
    c = HCOL["UP_TX"]
    cP, cN = r.pad("C601", 2), r.pad("C602", 2)
    lane(r, "HUB_UP_SS_TXP", "HUB_UP_SS_TXN",
         chamfer([(167.25, 77.75), (167.25, 77.10), (c, 77.10), (c, 86.70)], 0.5), "F.Cu", W90, G90,
         p_from=(167.39, 78.75), n_from=(166.90, 78.40), p_to=cP, n_to=cN, name="UP TX (L1)", pleft=False,
         tune=[("P", (169.31, 82.0), -1, 0.40, 5)])
    r.track("HUB_UP_SS_TXP", [(166.90, 79.00), (167.39, 78.75)], "F.Cu", W90)
    # P5 RX: from the vias west under R415's corner to its column, down to pins 86/87
    hP, hN = r.pad_of_net("U601", "HUB_DSC_SS_RXP"), r.pad_of_net("U601", "HUB_DSC_SS_RXN")
    c = HCOL["P5_RX"]
    lane(r, "HUB_DSC_SS_RXP", "HUB_DSC_SS_RXN",
         chamfer([(172.60, 79.85), (c, 80.75), (c, 84.60), (c, 87.00), (c, 91.10)], 0.3),
         "F.Cu", W90, G90, p_from=(172.90, 79.50), n_from=(172.30, 79.50), p_to=hP, n_to=hN, name="P5 RX (L1)",
         tune=[("P", (171.84, 85.8), 1, 0.45, 1), ("P", (171.84, 82.5), 1, 0.35, 1)])
    # P5 TX: down to the caps C611/C612
    c = HCOL["P5_TX"]
    cP, cN = r.pad("C611", 2), r.pad("C612", 2)
    lane(r, "HUB_DSC_SS_TXP", "HUB_DSC_SS_TXN", chamfer([(173.85, 79.95), (c, 80.85), (c, 84.50), (c, 86.70)], 0.3),
         "F.Cu", W90, G90, p_from=(174.15, 79.50), n_from=(173.55, 79.50), p_to=cP, n_to=cN,
         name="P5 TX (L1)", tune=[("P", (173.11, 82.6), 1, 0.38, 2)])
    pinP, pinN = r.pad_of_net("U601", "HUB_P5_TXP_IC"), r.pad_of_net("U601", "HUB_P5_TXN_IC")
    a, b = r.pad("C611", 1), r.pad("C612", 1)
    r.track("HUB_P5_TXP_IC", [pinP, (pinP[0], 89.90), (a[0], 89.30), a], "F.Cu", W90)
    r.track("HUB_P5_TXN_IC", [pinN, (pinN[0], 89.90), (b[0], 89.65), b], "F.Cu", W90)
    # ---------------- hub-side TX caps -> pins (IC side). C601/C602 and C611/C612 sit in reverse P/N order
    # w.r.t. pins 91/92 and 83/84. UP: the N leg crosses the P chain under C601's body (between its pads,
    # 0.09 mm track, 0.155 mm to each pad). P5: no room (P5 RX + laptop USB2 fill the gap west of C611 and
    # the bottom decaps leave no via spot) -> left open, see notes (swap C611<->C612).
    pinP, pinN = r.pad_of_net("U601", "HUB_UP_TXP_IC"), r.pad_of_net("U601", "HUB_UP_TXN_IC")
    a, b = r.pad("C601", 1), r.pad("C602", 1)
    r.track("HUB_UP_TXP_IC", [pinP, (pinP[0], 89.60), (a[0] + 0.15, 89.05), (a[0], a[1])], "F.Cu", W90)
    yb = (r.pad("C601", 1)[1] + r.pad("C601", 2)[1]) / 2
    r.track("HUB_UP_TXN_IC", [pinN, (pinN[0], 91.35), (168.55, 90.50), (168.55, yb + 0.15),
                              (168.70, yb), (b[0] - 0.15, yb), (b[0] - 0.15, b[1])], "F.Cu", 0.09)


def esd_thru(r, ref, pairs, net_of):
    """Flow-through straps across a TPD4E02B04: top-row pad -> bottom-row pad (same net)."""
    for a, b in pairs:
        r.track(net_of(r, ref, a), [r.pad(ref, a), r.pad(ref, b)], "F.Cu", W85)


def _pnet(r, ref, num):
    for p in r.fps[ref].Pads():
        if p.GetNumber() == str(num):
            return p.GetNetname().split("/")[-1]


def laptop_conn(r):
    """J501 -> D502/D503 (L1). A-row pairs (TX1, RX2) drop straight onto the ESD. The B row is THT on the
    DX07: TX2 (B2/B3) leaves on L3 through the B1-B4 gap, RX1 (B10/B11) through the B9-B12 gap, and both
    come up next to the ESD top pads."""
    J = "J501"
    for ref in ("D502", "D503"):
        esd_thru(r, ref, ((1, 10), (2, 9), (4, 7), (5, 6)), _pnet)
    # TX1 (A2/A3) -> D502 1/2 ; RX2 (A11/A10) -> D503 7/6
    for a, d, ref in (("A2", 1, "D502"), ("A3", 2, "D502"), ("A11", 7, "D503"), ("A10", 6, "D503")):
        pa, pd = r.pad(J, a), r.pad(ref, d)
        r.track(_pnet(r, J, a), [pa, (pa[0], 60.45), (pd[0], 61.10), pd], "F.Cu", W85)
    # TX2 on L3 from the THT pins
    b2, b3 = r.pad(J, "B2"), r.pad(J, "B3")
    vP, vN = (146.95, 60.70), (147.60, 61.10)
    r.track("UP_C_TX2_P", [b2, (148.44, 57.90), (148.44, 59.85), (148.17, 60.12), (147.25, 60.12), vP],
            "In2.Cu", W85_L3)
    r.track("UP_C_TX2_N", [b3, (148.81, 57.90), (148.81, 60.15), (148.48, 60.48), (147.85, 60.48), vN],
            "In2.Cu", W85_L3)
    via(r, "UP_C_TX2_P", vP); via(r, "UP_C_TX2_N", vN)
    r.track("UP_C_TX2_P", [vP, r.pad("D503", 10)], "F.Cu", W85)
    r.track("UP_C_TX2_N", [vN, r.pad("D503", 9)], "F.Cu", W85)
    # RX1 on L3 from the THT pins
    b11, b10 = r.pad(J, "B11"), r.pad(J, "B10")
    wN, wP = (152.00, 60.68), (152.03, 61.28)
    r.track("UP_RX1_N", [b10, (152.59, 57.90), (152.59, 59.95), (152.07, 60.47), wN], "In2.Cu", W85_L3)
    r.track("UP_RX1_P", [b11, (152.96, 57.90), (152.96, 60.95), (152.53, 61.28), wP], "In2.Cu", W85_L3)
    via(r, "UP_RX1_N", wN, VIA_S); via(r, "UP_RX1_P", wP, VIA_S)
    r.track("UP_RX1_N", [wN, (151.60, 61.08), (151.15, 61.45), r.pad("D502", 5)], "F.Cu", W85)
    r.track("UP_RX1_P", [wP, (151.62, 61.45), r.pad("D502", 4)], "F.Cu", W85)


def ds_conn(r):
    """J502 (all SMD, B row behind A row) -> D506/D507 (L1). TX1/RX2 (A row) stay on L1 and shift right
    under the A-row ends; TX2/RX1 (B row) drop to L3 through 0.35 mm vias between the rows and come up
    above the ESD top pads, under the TX1/RX2 jogs."""
    J = "J502"
    for ref in ("D506", "D507"):
        esd_thru(r, ref, ((1, 10), (2, 9), (4, 7), (5, 6)), _pnet)
    a2, a3 = r.pad(J, "A2"), r.pad(J, "A3")
    d1, d2 = r.pad("D506", 1), r.pad("D506", 2)
    r.track("DS_C_TX1_P", [a2, (a2[0], 60.85), (d1[0] - 0.25, 60.85), (d1[0], 61.10), d1], "F.Cu", W85)
    r.track("DS_C_TX1_N", [a3, (a3[0], 61.07), (d2[0] - 0.20, 61.07), (d2[0], 61.27), d2], "F.Cu", W85)
    a11, a10 = r.pad(J, "A11"), r.pad(J, "A10")
    d7, d6 = r.pad("D507", 7), r.pad("D507", 6)
    r.track("DS_RX2_P", [a11, (a11[0], 61.20), (d7[0] - 0.25, 61.20), (d7[0], 61.45), d7], "F.Cu", W85)
    r.track("DS_RX2_N", [a10, (a10[0], 60.95), (d6[0] - 0.25, 60.95), (d6[0], 61.20), d6], "F.Cu", W85)
    # B-row pairs
    for (bp, bn, netp, netn, dp, dn, vp2, vn2) in (
            ("B2", "B3", "DS_C_TX2_P", "DS_C_TX2_N", ("D507", 10), ("D507", 9), (168.80, 61.60), (169.45, 61.60)),
            ("B11", "B10", "DS_RX1_P", "DS_RX1_N", ("D506", 4), ("D506", 5), (173.05, 61.47), (172.55, 61.53))):
        pb, nb = r.pad(J, bp), r.pad(J, bn)
        vp1, vn1 = (pb[0], 59.42), (nb[0], 59.42)
        for n, a, b in ((netp, vp1, vp2), (netn, vn1, vn2)):
            via(r, n, a, VIA_T); via(r, n, b, VIA_T)
        r.track(netp, [pb, vp1], "F.Cu", W85); r.track(netn, [nb, vn1], "F.Cu", W85)
        for n, a, b in ((netp, vp1, vp2), (netn, vn1, vn2)):
            ym = a[1] + 0.6
            r.track(n, [a, (a[0], ym), (b[0], ym + abs(b[0] - a[0])), b], "In2.Cu", W85_L3)
        for n, v, d in ((netp, vp2, dp), (netn, vn2, dn)):
            pd = r.pad(*d)
            r.track(n, [v, (v[0] + (pd[0] - v[0]) * 0.3, v[1] + 0.15), pd], "F.Cu", W85)


def aux(r):
    """DP AUX: U502 26/27 -> R506/R507 (1M bias) -> C523/C524 -> R525/R526 (100k bias) -> U503 24/25, L1.
    The UP side needs one crossing (pins P-west/N-east, caps P-north): N hops on L3 between two 0.4 mm vias."""
    p26, p27 = r.pad_of_net("U502", "DP_AUX_P"), r.pad_of_net("U502", "DP_AUX_N")
    r506, r507 = r.pad("R506", 1), r.pad("R507", 1)
    c523, c524 = r.pad("C523", 1), r.pad("C524", 1)
    r.track("DP_AUX_P", [p26, (p26[0], 73.20), (r506[0] - 0.14, 73.48), (r506[0], r506[1]), (r506[0], 74.12),
                         (158.05, 74.42), (c523[0] - 0.27, 74.42), (c523[0], 74.11), c523], "F.Cu", W90)
    v1, v2 = (159.05, 72.90), (159.30, 75.95)
    via(r, "DP_AUX_N", v1, VIA_S); via(r, "DP_AUX_N", v2, VIA_S)
    r.track("DP_AUX_N", [p27, (p27[0] + 0.1, 72.95), (v1[0] - 0.2, 72.95), v1], "F.Cu", W90)
    r.track("DP_AUX_N", [v1, (159.30, 73.50), v2], "In2.Cu", W90)
    r.track("DP_AUX_N", [(r507[0], 75.37), (r507[0], 75.95), v2, (c524[0] - 0.3, 75.95), (c524[0], 75.65), c524],
            "F.Cu", W90)
    r.track("DP_AUX_N", [r507, (r507[0], 75.37)], "F.Cu", W90)
    # U503 side
    q24, q25 = r.pad_of_net("U503", "DS_AUX_P"), r.pad_of_net("U503", "DS_AUX_N")
    a, b = r.pad("C523", 2), r.pad("R525", 1)
    r.track("DS_AUX_P", [a, b, (b[0], 73.20), (q24[0] - 0.15, 73.20), (q24[0], 73.05), q24], "F.Cu", W90)
    a, b = r.pad("C524", 2), r.pad("R526", 1)
    r.track("DS_AUX_N", [a, b, (b[0], 74.42), (q25[0] - 0.25, 74.42), (q25[0], 74.17), q25], "F.Cu", W90)


def up_sbu(r):
    """UP_SBU1/2: TPD4S480 U501 15/14 (bottom) -> L6 south -> via pair -> L1 -> R502/R503 (2M) -> U502 24/25.
    The two vias are staggered so the pair order flips between L6 (SBU2 north) and L1 (SBU1 north)."""
    u15, u14 = r.pad_of_net("U501", "UP_SBU1"), r.pad_of_net("U501", "UP_SBU2")
    m24, m25 = r.pad_of_net("U502", "UP_SBU1"), r.pad_of_net("U502", "UP_SBU2")
    r502, r503 = r.pad("R502", 1), r.pad("R503", 1)
    v1, v2 = (153.00, 72.95), (153.60, 73.55)          # SBU1 west/north, SBU2 east/south
    via(r, "UP_SBU1", v1, VIA_S); via(r, "UP_SBU2", v2, VIA_S)
    # L6
    r.track("UP_SBU2", [u14, (u14[0], 72.10), (u14[0] + 0.4, 72.50), (v2[0], 72.50), v2], "B.Cu", WSLOW)
    r.track("UP_SBU1", [u15, (u15[0], 73.20), (u15[0] + 0.4, 73.60), (v1[0] - 0.3, 73.60), (v1[0], 73.30), v1],
            "B.Cu", WSLOW)
    # L1
    r.track("UP_SBU1", [m24, (m24[0], 73.00), (v1[0] + 0.3, 73.00), v1], "F.Cu", WSLOW)
    r.track("UP_SBU1", [(r502[0], 73.00), r502], "F.Cu", WSLOW)
    r.track("UP_SBU2", [m25, (m25[0], 73.15), (m25[0] - 0.15, 73.30), (155.30, 73.30), (155.30, r503[1]), r503,
                        (153.90, r503[1]), (v2[0], 75.50), v2], "F.Cu", WSLOW)


def laptop_usb2(r):
    """LAPTOP_USB_DP/DN: D504 (bottom, flow-through) -> L6 south along x 146 -> L3 east along y 79.7 (below the
    hub-SS transitions) -> vias under R415's south edge -> L1 hub corridor between UP TX and P5 RX -> pins 89/90.
    The receptacle side (A6/A7 + B6/B7 -> D504 top pads) is not routed (see notes)."""
    W, G = W90_L3, G90_L3
    for a, b in ((1, 10), (2, 9)):
        r.track(_pnet(r, "D504", a), [r.pad("D504", a), r.pad("D504", b)], "B.Cu", W90)
    dp, dn = r.pad("D504", 10), r.pad("D504", 9)
    vP1, vN1 = (145.85, 78.90), (146.50, 80.00)        # staggered: DP north on L3
    r.track("LAPTOP_USB_DP", [dp, (146.01, 64.00), (146.01, 78.30), vP1], "B.Cu", W90)
    r.track("LAPTOP_USB_DN", [dn, (146.29, 64.00), (146.29, 79.40), vN1], "B.Cu", W90)
    vN2, vP2 = (170.45, 80.15), (171.05, 80.15)
    for n, a, b in (("LAPTOP_USB_DP", vP1, vP2), ("LAPTOP_USB_DN", vN1, vN2)):
        via(r, n, a); via(r, n, b)
    pDP = [vP1, (145.85, 79.30), (146.07, 79.52), (170.75, 79.52), vP2]
    pDN = [vN1, (146.62, 79.88), (170.18, 79.88), vN2]
    r.track("LAPTOP_USB_DN", pDN, "In2.Cu", W); r.track("LAPTOP_USB_DP", pDP, "In2.Cu", W)
    c = HCOL["USB_L"]
    hP, hN = r.pad_of_net("U601", "LAPTOP_USB_DP"), r.pad_of_net("U601", "LAPTOP_USB_DN")
    qN = [vN2, (vN2[0], 80.40), (c - 0.14, 80.82), (c - 0.14, 90.20), (hN[0], 90.87), hN]
    qP = [vP2, (c + 0.14, 80.25), (c + 0.14, 90.40), (hP[0], 90.95), hP]
    r.track("LAPTOP_USB_DN", qN, "F.Cu", W90); r.track("LAPTOP_USB_DP", qP, "F.Cu", W90)
    LOG.append(("LAPTOP USB2 (D504-hub)", _len([dp, (146.01, 64.0), (146.01, 78.3), vP1]) + _len(pDP) + _len(qP),
                _len([dn, (146.29, 64.0), (146.29, 79.4), vN1]) + _len(pDN) + _len(qN)))


def _hv(n):
    n = n.split("/")[-1]
    return n.startswith("VBUS_") or n == "+5V" or n.startswith("VIN")


def gnd_returns(r, sites, per_site=2, reach=1.3):
    """Add GND return vias (0.45/0.25) next to each signal-via transition: nearest free spots (checked
    against every pad on F.Cu/In2.Cu/B.Cu and against this script's own copper) within `reach` mm."""
    import pcbnew
    M = pcbnew.FromMM
    mine = set(NETS)
    obst = []
    for fp in r.board.GetFootprints():
        for p in fp.Pads():
            n = p.GetNetname().split("/")[-1]
            if n == "GND":
                continue
            npth = p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH
            for L in (pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
                if p.IsOnLayer(L) or npth:
                    obst.append((p.GetEffectiveShape(L if p.IsOnLayer(L) else pcbnew.F_Cu),
                                 0.25 if npth else (0.32 if _hv(n) else 0.17), p.GetPosition()))
                    break
    def add_track_obst(t):
        for L in (pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
            if t.IsOnLayer(L):
                obst.append((t.GetEffectiveShape(L), 0.25 if t.Type() == pcbnew.PCB_VIA_T else 0.17,
                             t.GetPosition() if t.Type() == pcbnew.PCB_VIA_T else t.GetStart()))
    for t in r.board.GetTracks():
        if t.GetNetname().split("/")[-1] in mine:
            add_track_obst(t)
    placed = []
    for (x0, y0) in sites:
        got = 0
        cands = []
        k = 0.1
        steps = int(reach / k)
        for i in range(-steps, steps + 1):
            for j in range(-steps, steps + 1):
                d = math.hypot(i * k, j * k)
                if 0.55 <= d <= reach:
                    cands.append((d, x0 + i * k, y0 + j * k))
        cands.sort()
        for d, x, y in cands:
            if got >= per_site:
                break
            c = pcbnew.SHAPE_CIRCLE(pcbnew.VECTOR2I(M(x), M(y)), M(0.225))
            ok = all(not sh.Collide(c, M(cl)) for sh, cl, _ in obst)
            ok = ok and all(math.hypot(x - a, y - b) >= 0.75 for a, b in placed)
            if ok:
                r.via("GND", x, y, 0.45, 0.25)
                placed.append((x, y))
                got += 1
    print(f"  GND return vias placed: {len(placed)} (sites {len(sites)})")


GND_SITES = [(147.27, 60.90), (152.02, 60.98),                       # laptop TX2 / RX1 B-row hops
             (169.25, 59.42), (173.25, 59.42), (169.12, 61.60), (172.88, 61.54),   # downstream B-row hops
             (170.72, 65.50), (168.45, 66.22),                       # downstream RX2 hop
             (174.61, 66.03), (171.60, 70.00),                       # downstream TX1 hop
             (155.25, 64.62), (157.02, 63.55), (164.37, 65.65), (163.10, 63.45),   # hub SS, mux end
             (166.90, 78.70), (168.30, 78.15), (172.60, 79.50), (173.85, 79.50)]   # hub SS, L3 -> L1


def laptop_receptacle(r):
    """J501 slow nets (U501 moved 2 mm south, so the D502/D503 gap above it is free on every layer).
    - D+: A6 -> B6 on L1; B6 (THT) -> L6 west along y 59.7 -> D504 pad 1.  D-: A7 -> via -> L6; B7 (THT) -> L6
      west along y 59.98 -> D504 pad 2 (D504 is flow-through to the hub run).
    - SBU1 (A8) -> via -> L6 -> U501 pin 1.  CC1 (A5) -> via -> L6 -> pin 4, and around the corner to pin 7.
    - CC2 (B5) / SBU2 (B8): the THT B row only lets them out upwards; both run on L3 above the B row, through
      the gaps between the shell pads (y 56.0), around the shell, and come back south: CC2 west of the
      connector (x 145.3) to a via inside the CC1 loop (pins 5/6), SBU2 east of it (x 156.0) to a via above pin 2."""
    J, U = "J501", "U501"
    pin = lambda n: r.pad(U, n)
    a5, a6, a7, a8 = (r.pad(J, k) for k in ("A5", "A6", "A7", "A8"))
    b5, b6, b7, b8 = (r.pad(J, k) for k in ("B5", "B6", "B7", "B8"))
    ab = a5[1] + 0.55                                  # A-row pad bottom edge
    # vias
    v_s1 = (a8[0] - 0.20, ab + 1.17)                   # SBU1
    v_dn = (a7[0], ab + 0.42)                          # D- (A row)
    v_c1 = (a5[0] - 0.03, ab + 0.34)                   # CC1
    v_s2 = (pin(2)[0], ab + 1.62)                      # SBU2, above pin 2
    v_c2 = (pin(5)[0] + 0.45, pin(5)[1] - 0.10)        # CC2, inside the CC1 loop, between pins 5 and 6
    for n, v in (("UP_C_SBU1", v_s1), ("LAPTOP_USB_DN", v_dn), ("UP_C_CC1", v_c1), ("UP_C_SBU2", v_s2),
                 ("UP_C_CC2", v_c2)):
        via(r, n, v, VIA_T)
    # ---- L1 escapes from the A row
    r.track("UP_C_SBU1", [a8, (a8[0] + 0.05, ab + 0.30), (a8[0] + 0.05, v_s1[1] - 0.40), v_s1], "F.Cu", WSLOW)
    r.track("LAPTOP_USB_DN", [a7, v_dn], "F.Cu", W90)
    r.track("UP_C_CC1", [a5, v_c1], "F.Cu", WSLOW)
    r.track("LAPTOP_USB_DP", [a6, (a6[0], a6[1] - 0.55), b6], "F.Cu", W90)
    # ---- USB2 on L6 to D504 top pads
    d1, d2 = r.pad("D504", 1), r.pad("D504", 2)
    yP, yN = 59.70, 59.98
    r.track("LAPTOP_USB_DP", [b6, (b6[0], yP), (d1[0] + 0.28, yP), (d1[0], yP + 0.28), d1], "B.Cu", W90)
    r.track("LAPTOP_USB_DN", [b7, (b7[0], yN), (d2[0] + 0.28, yN), (d2[0], yN + 0.28), d2], "B.Cu", W90)
    r.track("LAPTOP_USB_DN", [v_dn, (v_dn[0], yN)], "B.Cu", W90)
    # ---- L6 into U501
    r.track("UP_C_SBU1", [v_s1, (v_s1[0], pin(1)[1] - 0.45), (pin(1)[0], pin(1)[1] - 0.25), pin(1)], "B.Cu", WSLOW)
    r.track("UP_C_SBU2", [v_s2, pin(2)], "B.Cu", WSLOW)
    yl = pin(4)[1] - 0.57                              # CC1 loop row, north of the top pins
    xl = pin(6)[0] + 0.65                              # CC1 loop column, east of the right pins
    r.track("UP_C_CC1", [v_c1, (pin(4)[0], v_c1[1] + 0.32), (pin(4)[0], yl), pin(4)], "B.Cu", 0.15)
    r.track("UP_C_CC1", [(pin(4)[0], yl), (xl, yl), (xl, pin(7)[1]), pin(7)], "B.Cu", 0.15)
    r.track("UP_C_CC2", [pin(5), (pin(5)[0] + 0.15, v_c2[1]), v_c2, (pin(6)[0] - 0.05, pin(6)[1] - 0.20), pin(6)],
            "B.Cu", 0.15)
    # ---- CC2 / SBU2 on L3 around the receptacle
    yg = 56.02                                         # between the two shell pads on each side
    r.track("UP_C_CC2", [b5, (b5[0], yg), (145.30, yg), (145.30, 62.40), (v_c2[0] - 0.75, 62.40),
                         (v_c2[0] - 0.20, 62.95), v_c2], "In2.Cu", WCC)
    r.track("UP_C_SBU2", [b8, (b8[0], yg), (156.15, yg), (156.15, v_s2[1]), v_s2], "In2.Cu", WSLOW)


def laptop_cc(r):
    """LAPTOP_CC1/2: U501 pins 12/11 (bottom) -> L6 east under the block -> north through the bottom channels
    (CC2 x 157.85, CC1 x 163.0 then under the BGA) -> vias -> L1 to the 390 pF caps and both PMG1 balls."""
    U = "U501"
    p12, p11 = r.pad_of_net(U, "LAPTOP_CC1"), r.pad_of_net(U, "LAPTOP_CC2")
    n15, n14 = r.pad("U401", "N15"), r.pad("U401", "N14")
    j15, j14 = r.pad("U401", "J15"), r.pad("U401", "J14")
    c416, c417 = r.pad("C416", 1), r.pad("C417", 1)
    v2 = (157.85, 54.60)
    v1 = (157.95, 52.80)
    via(r, "LAPTOP_CC2", v2, VIA_T); via(r, "LAPTOP_CC1", v1, VIA_T)
    y2, y1 = p11[1], p12[1] + 0.59
    r.track("LAPTOP_CC2", [p11, (p11[0] + 0.40, y2), (v2[0], y2), v2], "B.Cu", WCC)
    # threads between the two P5 RX vias (162.75,63.15)/(163.45,63.75) at 0.15 mm, then the bottom channel
    r.track("LAPTOP_CC1", [p12, (p12[0], y1), (159.20, y1), (159.20, 64.40), (162.30, 64.40)], "B.Cu", WCC)
    r.track("LAPTOP_CC1", [(162.30, 64.40), (162.45, 64.21), (163.75, 62.69), (163.75, 60.30)], "B.Cu", 0.15)
    r.track("LAPTOP_CC1", [(163.75, 60.30), (164.10, 59.95), (164.50, 59.95), (164.50, 53.30), (164.00, v1[1]),
                           v1], "B.Cu", WCC)
    # L1 at the PMG1
    r.track("LAPTOP_CC2", [v2, (v2[0], c417[1]), (c417[0], c417[1])], "F.Cu", WCC)
    r.track("LAPTOP_CC2", [(v2[0], c417[1]), (v2[0], j15[1] + 0.30), (v2[0] + 0.30, j15[1]), j15, j14],
            "F.Cu", 0.15)
    r.track("LAPTOP_CC1", [v1, (n15[0] - 0.18, n15[1]), n15, n14], "F.Cu", WCC)
    r.track("LAPTOP_CC1", [v1, (c416[0] + 0.25, c416[1] + 0.20), c416], "F.Cu", WCC)


def ds_cc(r):
    """DS_CC1/2: TPD6S300 U504 pins 12/11 (bottom) -> vias just south -> L3 west along y 64.45/64.85 (north of the
    DS RX2 hop vias) -> north at x 166.0/165.6 -> vias -> L1: CC1 between C418/C419 to N1/N2, CC2 between
    C419's pads to J1/J2."""
    U = "U504"
    p12, p11 = r.pad_of_net(U, "DS_CC1"), r.pad_of_net(U, "DS_CC2")
    va1, va2 = (p12[0] - 0.05, 65.85), (p11[0] + 0.05, 65.95)
    vb1, vb2 = (165.50, r.pad("U401", "N1")[1]), (166.00, 55.00)
    for n, a, b in (("DS_CC1", va1, vb1), ("DS_CC2", va2, vb2)):
        via(r, n, a, VIA_T); via(r, n, b, VIA_T)
    r.track("DS_CC1", [p12, va1], "B.Cu", 0.15)
    r.track("DS_CC2", [p11, va2], "B.Cu", 0.15)
    r.track("DS_CC2", [va2, (va2[0], 64.85), (174.65, 64.45), (vb2[0] + 0.40, 64.45), (vb2[0], 64.05), vb2],
            "In2.Cu", WCC)
    r.track("DS_CC1", [va1, (va1[0], 65.20), (174.15, 64.80), (vb1[0] + 0.40, 64.80), (vb1[0], 64.40), vb1],
            "In2.Cu", WCC)
    n1, n2 = r.pad("U401", "N1"), r.pad("U401", "N2")
    j1, j2 = r.pad("U401", "J1"), r.pad("U401", "J2")
    c418, c419 = r.pad("C418", 1), r.pad("C419", 1)
    r.track("DS_CC1", [vb1, n1, n2], "F.Cu", WCC)
    r.track("DS_CC1", [(c418[0], n1[1]), c418], "F.Cu", WCC)
    xc = 163.93                                                   # between the ball column and the caps
    r.track("DS_CC2", [vb2, (165.70, 54.70), (xc + 0.15, 54.70), (xc, 54.55), (xc, j1[1] + 0.30),
                       (xc - 0.30, j1[1]), j1, j2], "F.Cu", 0.15)
    r.track("DS_CC2", [(c419[0], 54.70), c419], "F.Cu", 0.15)


def ds_sbu(r):
    """DS_SBU1/2: U504 pins 15/14 (bottom) -> L6 west under the pins -> south down the free column
    (x 172.25/172.55) -> west along y 71.85 -> SBU1 via (169.3,71.85) -> L1 -> U503 27 + R542; SBU2 on to a via
    at (166.9,73.25) between DS AUX-N and SBU1 -> U503 26, and on L3 to a via next to R543."""
    U = "U504"
    p15, p14 = r.pad_of_net(U, "DS_SBU1"), r.pad_of_net(U, "DS_SBU2")
    m27, m26 = r.pad_of_net("U503", "DS_SBU1"), r.pad_of_net("U503", "DS_SBU2")
    r542, r543 = r.pad("R542", 1), r.pad("R543", 1)
    v1, v2, v3 = (169.30, 71.80), (166.90, 73.25), (167.20, 74.90)
    via(r, "DS_SBU1", v1, VIA_T)
    via(r, "DS_SBU2", v2, VIA_T); via(r, "DS_SBU2", v3, VIA_T)
    r.track("DS_SBU1", [p15, (p15[0], 65.40), (172.25 + 0.30, 65.40), (172.25, 65.70), (172.25, 71.30),
                        (171.80, 71.75), v1], "B.Cu", WSLOW)
    r.track("DS_SBU2", [p14, (p14[0], 65.75), (172.55 + 0.20, 65.75), (172.55, 65.95), (172.55, 71.65),
                        (172.15, 72.05), (171.00, 72.05), (170.80, 72.25), (167.30, 72.25), (167.00, 72.55),
                        (167.00, 73.00), v2], "B.Cu", WSLOW)
    r.track("DS_SBU1", [v1, (168.90, 72.25), (168.90, 72.70), (168.65, 73.00), (m27[0], 73.00), m27], "F.Cu", WSLOW)
    r.track("DS_SBU1", [(m27[0] + 0.05, 73.00), (m27[0] + 0.05, r542[1] - 0.40)], "F.Cu", WSLOW)
    r.track("DS_SBU2", [m26, v2], "F.Cu", WSLOW)
    r.track("DS_SBU2", [v2, (167.10, 73.70), (167.20, 74.20), v3], "In2.Cu", WSLOW)
    r.track("DS_SBU2", [v3, r543], "F.Cu", WSLOW)


def ds_usb2_hub(r):
    """HUB_DSC_DP/DN: U504 pins 20/19 (ESD tap, bottom) -> vias in the free column -> L3 east under U504 ->
    south along x 176.3-176.7 -> vias under the hub corridor's east edge -> L1 column x 174.45/174.73 -> hub 81/82.
    The receptacle side (J502 A6/A7/B6/B7) joins at the column vias."""
    W, G = W90_L3, G90_L3
    U = "U504"
    p20, p19 = r.pad_of_net(U, "HUB_DSC_DP"), r.pad_of_net(U, "HUB_DSC_DN")
    vP, vN = (171.45, 63.35), (172.10, 63.40)                    # free column, south of the CC/SBU lanes
    via(r, "HUB_DSC_DP", vP); via(r, "HUB_DSC_DN", vN)
    r.track("HUB_DSC_DP", [p20, (p20[0] - 0.35, p20[1]), (171.80, p20[1]), (vP[0], p20[1] + 0.35), vP], "B.Cu", W90)
    r.track("HUB_DSC_DN", [p19, (p19[0] - 0.35, p19[1]), (vN[0], p19[1] + 0.35), vN], "B.Cu", W90)
    yP, yN = 62.90, 63.26                                          # L3 run under U504 (DP north)
    hP, hN = (177.36, 79.40), (177.00, 79.55)
    vP2, vN2 = (175.15, 80.40), (175.95, 79.90)
    via(r, "HUB_DSC_DP", vP2); via(r, "HUB_DSC_DN", vN2)
    qP = [vP, (171.85, yP), (177.00, yP), (177.36, yP + 0.36), hP, (177.36, 80.40), vP2]
    qN = [vN, (172.19, yN), (176.64, yN), (177.00, yN + 0.36), hN, (176.70, 79.85), vN2]
    r.track("HUB_DSC_DP", qP, "In2.Cu", W); r.track("HUB_DSC_DN", qN, "In2.Cu", W)
    a81, a82 = r.pad("U601", 81), r.pad("U601", 82)
    cN, cP = 174.45, 174.73
    q1N = [vN2, (cN + 0.30, vN2[1]), (cN, vN2[1] + 0.30), (cN, 90.20), (a82[0], 91.25), a82]
    q1P = [vP2, (cP, vP2[1] + 0.42), (cP, 90.40), (a81[0], 91.33), a81]
    r.track("HUB_DSC_DN", q1N, "F.Cu", W90); r.track("HUB_DSC_DP", q1P, "F.Cu", W90)
    LOG.append(("DS USB2 (U504-hub)", _len(qP) + _len(q1P), _len(qN) + _len(q1N)))


def ds_receptacle(r):
    """J502 slow nets -> U504 (TPD6S300, bottom) and the DSC USB2 column vias.
    - A-row CC1/D-/SBU1 (A5/A7/A8) go up into 0.35 mm vias between the SMD rows (y 59.42); B-row CC2/D-/SBU2
      (B5/B7/B8) go north to vias at y 57.75; D+ is A6-B6 on L1, then straight down the D507/D506 gap to the DP
      column via.
    - D-: A7 + B7 joined on L3, down x 170.95 to the DN column via.
    - SBU1/SBU2 on L6 into U504 pins 1/2 from the north.
    - CC1/CC2 on L3 north of the B row (y 57.3/57.0), round J502's east shell pad, then vias north of the TX1 jog
      (174.4,60.25) / (175.45,60.75) and L6 into pins 4/5."""
    J, U = "J502", "U504"
    a5, a6, a7, a8 = (r.pad(J, k) for k in ("A5", "A6", "A7", "A8"))
    b5, b6, b7, b8 = (r.pad(J, k) for k in ("B5", "B6", "B7", "B8"))
    yb = (a5[1] + b5[1]) / 2 - 0.0                               # between the rows (59.42)
    yn = b5[1] - 0.82                                            # north of the B row (57.75)
    va8, va7, va5 = (a8[0], yb), (a7[0], yb), (a5[0], yb)
    vb5, vb7, vb8 = (b5[0], yn), (b7[0] - 0.25, yn - 0.05), (b8[0] + 0.10, yn)
    vc1, vc2 = (174.35, 60.30), (175.45, 60.75)
    for n, v in (("DS_C_SBU1", va8), ("HUB_DSC_DN", va7), ("DS_C_CC1", va5), ("DS_C_CC2", vb5),
                 ("HUB_DSC_DN", vb7), ("DS_C_SBU2", vb8), ("DS_C_CC1", vc1), ("DS_C_CC2", vc2)):
        via(r, n, v, VIA_T)
    for n, a, v in (("DS_C_SBU1", a8, va8), ("HUB_DSC_DN", a7, va7), ("DS_C_CC1", a5, va5),
                    ("DS_C_CC2", b5, vb5), ("HUB_DSC_DN", b7, vb7), ("DS_C_SBU2", b8, vb8)):
        r.track(n, [a, v], "F.Cu", W90 if n.startswith("HUB") else WSLOW)
    # D+ on L1: B6 - A6 - down the ESD gap to the DP column via
    vP = (171.45, 63.35)
    r.track("HUB_DSC_DP", [b6, (b6[0] + 0.10, b6[1] + 0.38), (a6[0], a6[1] - 0.37), a6, (a6[0], 61.70), vP],
            "F.Cu", W90)
    # D- on L3
    vN = (172.10, 63.40)
    r.track("HUB_DSC_DN", [vb7, (vb7[0] - 0.20, vb7[1]), (170.95, yn + 0.85), (170.95, 63.65), (171.15, 63.85),
                           (171.74, 63.85), vN], "In2.Cu", W90_L3)
    r.track("HUB_DSC_DN", [va7, (170.95, yb + 0.20)], "In2.Cu", W90_L3)
    # SBU on L6
    p1, p2 = r.pad(U, 1), r.pad(U, 2)
    r.track("DS_C_SBU1", [va8, (va8[0], 60.85), (p1[0] + 0.05, 60.85), (p1[0] + 0.05, 61.45), p1], "B.Cu", WSLOW)
    r.track("DS_C_SBU2", [vb8, (172.35, vb8[1] + 0.25), (172.35, 60.55), (p2[0] + 0.05, 60.55),
                          (p2[0] + 0.05, 61.45), p2], "B.Cu", WSLOW)
    # CC on L3 round the north of the B row
    r.track("DS_C_CC1", [va5, (a5[0] - 0.03, yb - 0.45), (a5[0] - 0.03, 57.30), (175.80, 57.30), (175.80, 60.25), vc1],
            "In2.Cu", WSLOW)
    r.track("DS_C_CC2", [vb5, (b5[0], 57.00), (176.15, 57.00), (176.15, 60.75), vc2], "In2.Cu", WCC)
    p4, p5 = r.pad(U, 4), r.pad(U, 5)
    r.track("DS_C_CC1", [vc1, (p4[0], vc1[1] + 0.20), p4], "B.Cu", WCC)
    r.track("DS_C_CC2", [vc2, (p5[0], vc2[1] + 0.45), p5], "B.Cu", WCC)


def route(board, r):
    dp_main_link(r)
    laptop_fanin(r)
    ds_fanin(r)
    hub_links(r)
    laptop_conn(r)
    ds_conn(r)
    aux(r)
    up_sbu(r)
    laptop_usb2(r)
    laptop_receptacle(r)
    laptop_cc(r)
    ds_cc(r)
    ds_sbu(r)
    ds_usb2_hub(r)
    ds_receptacle(r)
    gnd_returns(r, GND_SITES)
    for name, lp, ln in LOG:
        print(f"  {name:22s} P {lp:6.2f}  N {ln:6.2f}  skew {lp - ln:+.3f}")
