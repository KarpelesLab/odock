"""High-speed hub downstream links (USB7206C U601 ports 1-4 and 6) + hub crystal.

See docs/routing-notes/hs_hub.md. Geometry is computed from pad positions where it matters.
In-line AC caps that are placed with the IC-side pad facing away from the IC (C603-C608) cannot be
routed straight through: the script then stops each leg short of the cap (no pad contact) and
prints a warning; once the cap is rotated 180 deg the same code connects it.
"""
import os, sys, math, importlib.util

_spec = importlib.util.spec_from_file_location("_hs_lib", os.path.join(os.path.dirname(__file__), "_hs_lib.py"))
H = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(H)

F, B, L3 = "F.Cu", "B.Cu", "In2.Cu"
W1, G1 = H.USB90[F]
W3, G3 = H.USB90[L3]

NETS = [
    # P3 -> J702
    "USBA2_SS_TXP", "USBA2_SS_TXN", "USBA2_SS_RXP", "USBA2_SS_RXN", "USBA2_DP", "USBA2_DN",
    "HUB_P3_TXP_IC", "HUB_P3_TXN_IC",
    # P1 -> U901 (GL3224), P2 -> J701
    "CR_SS_TXP", "CR_SS_TXN", "CR_SS_RXP", "CR_SS_RXN", "CR_DP", "CR_DN", "CR_TXP_IC", "CR_TXN_IC",
    "HUB_P1_TXP_IC", "HUB_P1_TXN_IC",
    "USBA1_SS_TXP", "USBA1_SS_TXN", "USBA1_SS_RXP", "USBA1_SS_RXN", "USBA1_DP", "USBA1_DN",
    "HUB_P2_TXP_IC", "HUB_P2_TXN_IC",
    # P4 -> U801 (RTL8156BG), P6 -> U1001 (RP2350)
    "ETH_SS_TXP", "ETH_SS_TXN", "ETH_SS_RXP", "ETH_SS_RXN", "ETH_DP", "ETH_DN", "HUB_P4_TXP_IC", "HUB_P4_TXN_IC",
    "ETH_TXP_IC", "ETH_TXN_IC", "MCU_USB_DP", "MCU_USB_DN", "USB_DP_IC", "USB_DM_IC",
    # hub 25 MHz crystal
    "HUB_XI", "HUB_XO",
]


def stub_end(a, b, cut):
    """Point on segment a->b at distance `cut` before b."""
    d = math.hypot(b[0] - a[0], b[1] - a[1])
    t = max(0.0, (d - cut) / d)
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def cap_leg(r, net, pts, layer, w, connected, cut=0.75):
    """Draw a leg ending (pts[-1]) at an in-line cap pad; if not connected, stop `cut` short."""
    if not connected:
        pts = list(pts[:-1]) + [stub_end(pts[-2], pts[-1], cut)]
    H.draw(r, net, pts, layer, w)


def p3(r):
    """Hub port 3 -> J702 (USB-A 2): SS on L1 straight down the x 168.5-172.5 channel through D703,
    USB2 on L3 to D704, then L3/L6 into the connector pins."""
    tp, tn = r.pad("U601", 29), r.pad("U601", 30)
    rp, rn = r.pad("U601", 32), r.pad("U601", 33)
    ytoe = tp[1] + 0.51
    cP, cN = "C607", "C608"
    ok = H.cap_ok(r, cP, "HUB_P3_TXP_IC", "USBA2_SS_TXP", tp) and H.cap_ok(r, cN, "HUB_P3_TXN_IC", "USBA2_SS_TXN", tn)
    # cap pad positions: near = toward the hub (north), far = south
    pa, pb = r.pad(cP, 1), r.pad(cP, 2)
    na, nb = r.pad(cN, 1), r.pad(cN, 2)
    pnear, pfar = (pa, pb) if pa[1] < pb[1] else (pb, pa)
    nnear, nfar = (na, nb) if na[1] < nb[1] else (nb, na)
    if not ok:
        H.WARN.append("P3 TX: C607/C608 IC-side pad faces away from U601 -> rotate both 180 deg; "
                      "legs stop 0.75 mm short of the caps")
    # --- TX hub -> caps (single traces, cap pitch 1.25)
    cap_leg(r, "HUB_P3_TXP_IC", [tp, (tp[0], ytoe + 0.25), (pnear[0], ytoe + 0.25 + (tp[0] - pnear[0])),
                                  (pnear[0], pnear[1])], F, W1, ok)
    cap_leg(r, "HUB_P3_TXN_IC", [tn, (tn[0], ytoe + 0.25), (nnear[0], ytoe + 0.25 + (nnear[0] - tn[0])),
                                  (nnear[0], nnear[1])], F, W1, ok)
    # --- TX caps -> D703 -> J702 (pair centreline from below the caps to the ESD)
    d = r.pad("D703", 10), r.pad("D703", 9)
    cx0 = (pfar[0] + nfar[0]) / 2
    xT = (d[0][0] + d[1][0]) / 2
    y0 = pfar[1] + 0.9
    yj = 109.25
    path = [(cx0, y0), (cx0, yj), (xT, yj + (xT - cx0)), (xT, d[0][1] - 1.0)]
    Lf, Rt = H.pair_lines(path, W1, G1)          # heading south: left = east = N
    N = ([nfar, (nfar[0], nfar[1] + 0.3)] if ok else [(nfar[0], nfar[1] + 0.7)]) + Lf
    P = ([pfar, (pfar[0], pfar[1] + 0.3)] if ok else [(pfar[0], pfar[1] + 0.7)]) + Rt
    usba_ss_end(r, "D703", "J702", "USBA2_SS_TX", P, N, "P3 USBA2_SS_TX (cap->J702)")
    # --- RX hub -> D703 -> J702
    d = r.pad("D703", 7), r.pad("D703", 6)
    cx = (rp[0] + rn[0]) / 2
    xR = (d[0][0] + d[1][0]) / 2
    yj = 109.55
    path = [(cx, ytoe + 0.1), (cx, yj), (xR, yj + (xR - cx)), (xR, d[0][1] - 1.0)]
    Lf, Rt = H.pair_lines(path, W1, G1)
    usba_ss_end(r, "D703", "J702", "USBA2_SS_RX", [rp] + Rt, [rn] + Lf, "P3 USBA2_SS_RX (U601->J702)")
    # --- USB2: pins 27/28 -> L3 -> D704 -> L3 (DP) / L6 (DN) -> J702 pins 3/2
    up, un = r.pad("U601", 27), r.pad("U601", 28)
    vdp, vdn = (165.75, 108.25), (166.35, 107.75)
    dp = [up, (up[0], ytoe + 0.05), (up[0] - 0.9, ytoe + 0.95), (vdp[0], vdp[1] - 0.35), vdp]
    dn = [un, (un[0], ytoe + 0.05), (un[0] - 0.9, ytoe + 0.95), (vdn[0] - 0.25, vdn[1] - 0.3), vdn]
    H.draw(r, "USBA2_DP", dp, F, W1)
    H.draw(r, "USBA2_DN", dn, F, W1)
    r.via("USBA2_DP", *vdp)
    r.via("USBA2_DN", *vdn)
    e6, e4 = r.pad("D704", 6), r.pad("D704", 4)
    xc = (e6[0] + e4[0]) / 2
    yrun = 109.67
    path = [(vdn[0] + 0.6, yrun), (xc, yrun), (xc, e6[1] - 2.0)]
    Lf, Rt = H.pair_lines(path, W3, G3)          # heading east: left = north = DN
    dn3 = [vdn, (vdn[0], Lf[0][1])] + Lf
    dp3 = [vdp, (vdp[0], Rt[0][1])] + Rt
    usba_usb2_end(r, "D704", "J702", "USBA2", dp3, dn3)
    H.log("P3 USBA2_DP/DN", dp + dp3, dn + dn3)


def usba_ss_end(r, desd, jconn, base, P, N, name):
    """Finish an SS pair arriving from the north on L1 at the TPD4E02B04 `desd` (flow-through, pads
    10/9 = TX, 7/6 = RX on the north row) and fan out to the USB-A THT pins."""
    tx = base.endswith("TX")
    a, b, c, e = (10, 9, 1, 2) if tx else (7, 6, 4, 5)
    pn, nn, ps, ns = (r.pad(desd, k) for k in (a, b, c, e))
    jp, jn = (r.pad(jconn, 9), r.pad(jconn, 8)) if tx else (r.pad(jconn, 6), r.pad(jconn, 5))
    P = list(P) + [(pn[0], pn[1] - 0.6), pn, ps]
    N = list(N) + [(nn[0], nn[1] - 0.6), nn, ns]
    if tx:   # both go west; P farther
        yb = ps[1] + 0.43
        P += [(ps[0], yb), (jp[0] + 1.5, yb), (jp[0], yb + 1.5), jp]
        N += [(ns[0], yb), (jn[0], yb + (ns[0] - jn[0])), jn]
    else:    # both go east; N farther, passing over the RXP pin
        yb = ps[1] + 0.53
        P += [(ps[0], yb), (ps[0] + 1.1, yb + 1.1), (jp[0], yb + 1.5), jp]
        N += [(ns[0], yb), (ns[0] + 1.1, yb + 1.1), (jn[0] - 0.6, yb + 1.1), (jn[0], yb + 1.7), jn]
    q = ((pn[0] + nn[0]) / 2, pn[1] - 5.0)       # the straight run north of the ESD array
    P, N = H.match(P, N, segP=H.seg_near(P, q), segN=H.seg_near(N, q), sideP=-1, sideN=+1)
    H.draw(r, base + "P", P, F, W1)
    H.draw(r, base + "N", N, F, W1)
    H.log(name, P, N)


def usba_usb2_end(r, desd, jconn, base, dp3, dn3):
    """USB2 pair arriving on L3 heading south toward the USBLC6 `desd` (pins 6/4 north, 1/3 south):
    via up to L1 through the flow-through pads, via down, DP to the THT pin 3 on L3, DN to pin 2 on L6."""
    e6, e4 = r.pad(desd, 6), r.pad(desd, 4)
    e1, e3 = r.pad(desd, 1), r.pad(desd, 3)
    vn6, vn4 = (e6[0], e6[1] - 1.3), (e4[0], e4[1] - 1.3)
    dn3 += [(e4[0], vn4[1] - 0.5), vn4]
    dp3 += [(e6[0], vn6[1] - 0.5), vn6]
    H.draw(r, base + "_DN", dn3, L3, W3)
    H.draw(r, base + "_DP", dp3, L3, W3)
    r.via(base + "_DP", *vn6)
    r.via(base + "_DN", *vn4)
    H.draw(r, base + "_DP", [vn6, e6, e1], F, 0.2)
    H.draw(r, base + "_DN", [vn4, e4, e3], F, 0.2)
    j3, j2 = r.pad(jconn, 3), r.pad(jconn, 2)
    vs1, vs3 = (e1[0], e1[1] + 1.15), (e3[0], e3[1] + 1.15)
    H.draw(r, base + "_DP", [e1, vs1], F, 0.2)
    H.draw(r, base + "_DN", [e3, vs3], F, 0.2)
    r.via(base + "_DP", *vs1)
    r.via(base + "_DN", *vs3)
    H.draw(r, base + "_DP", [vs1, (j3[0] + 2.0, vs1[1] + 0.25), (j3[0] + 2.0, j3[1] - 0.82),
                           (j3[0] + 1.18, j3[1]), j3], L3, W3)
    H.draw(r, base + "_DN", [vs3, (vs3[0], vs3[1] + 0.5), (j2[0] + 0.2, vs3[1] + 0.5),
                           (j2[0], vs3[1] + 0.7), j2], B, W1)


def caps(r, cP, cN, netP_ic, netN_ic, src):
    """Return (ok, pnear, pfar, nnear, nfar): pad positions of an in-line cap pair, near = the pad
    position closer to `src` (where the IC-side net belongs)."""
    ok = H.cap_ok(r, cP, netP_ic, None, src) if False else None
    out = []
    for c in (cP, cN):
        a, b = r.pad(c, 1), r.pad(c, 2)
        da = math.hypot(a[0] - src[0], a[1] - src[1])
        db = math.hypot(b[0] - src[0], b[1] - src[1])
        out.append((a, b) if da < db else (b, a))
    ok = (r.pad_of_net(cP, netP_ic) == out[0][0]) and (r.pad_of_net(cN, netN_ic) == out[1][0])
    return ok, out[0][0], out[0][1], out[1][0], out[1][1]


def hub_left(r):
    """Hub ports 1 (GL3224 card reader) and 2 (USB-A 1), left side of U601 (pins 5-20)."""
    pin = lambda k: r.pad("U601", k)
    xt = pin(5)[0] - 0.51                      # pad toe x (164.65)
    LA, LC, LB = 108.05, 108.95, 109.85        # L6 lanes (centre y) of A (CR USB2), C (CR RX), B (CR TX)
    # ---------------- A: CR_DP/DN (pins 5/6): L1 west lane -> swap vias -> L6
    xa = 159.3
    path = [(xt, 95.0), (xa + 0.4, 95.0), (xa, 95.4), (xa, 106.0)]
    Lf, Rt = H.pair_lines(path, W1, G1)        # heading west: left = south = DN
    vdn, vdp = (159.6, 106.5), (Rt[-1][0], 107.2)
    dn1 = [pin(6)] + Lf + [(vdn[0], Lf[-1][1] + 0.16), vdn]
    dp1 = [pin(5)] + Rt + [vdp]
    H.draw(r, "CR_DN", dn1, F, W1); H.draw(r, "CR_DP", dp1, F, W1)
    r.via("CR_DN", *vdn); r.via("CR_DP", *vdp)
    # L6 west lane, then south at x 137.27 into U901 pins 4/5
    u4, u5 = r.pad_of_net("U901", "CR_DN"), r.pad_of_net("U901", "CR_DP")
    xs = 137.72                                # leaves toe-via room for U901 pins 1/2 at x 137.15
    path = [(157.6, LA), (xs + 0.5, LA), (xs, LA + 0.5), (xs, u4[1] - 0.35)]
    Lf, Rt = H.pair_lines(path, W1, G1)        # heading west: right = north = DN
    dn6 = [vdn, (158.4, vdn[1]), (158.4 - (Rt[0][1] - vdn[1]), Rt[0][1])] + Rt + [(u4[0] + 0.38, u4[1]), u4]
    dp6 = [vdp, (158.85, vdp[1]), (158.85 - (Lf[0][1] - vdp[1]), Lf[0][1])] + Lf + \
          [(Lf[-1][0], u5[1] - 0.3), (Lf[-1][0] - 0.3, u5[1]), u5]
    q = (150.0, LA)
    dp_all, dn_all = H.match(dp1 + dp6, dn1 + dn6, segP=len(dp1) + H.seg_near(dp6, q), segN=len(dn1) + H.seg_near(dn6, q),
                             sideP=+1, sideN=-1, center=q, h=0.12, hmax=0.15)
    dp6, dn6 = dp_all[len(dp1):], dn_all[len(dn1):]
    H.draw(r, "CR_DN", dn6, B, W1); H.draw(r, "CR_DP", dp6, B, W1)
    H.log("P1 CR_DP/DN", dp_all, dn_all)

    # ---------------- B: P1 TX (pins 7/8) through C603/C604 -> swap vias -> L6 -> U901 pins 10/11
    ok, pnear, pfar, nnear, nfar = caps(r, "C603", "C604", "HUB_P1_TXP_IC", "HUB_P1_TXN_IC", pin(7))
    if not ok:
        H.WARN.append("P1 TX: C603/C604 IC-side pad faces away from U601 -> rotate both 180 deg; "
                      "legs stop 0.75 mm short of the caps")
    xb = (pnear[0] + nnear[0]) / 2
    yb = pnear[1] - 1.1
    path = [(xt - 0.25, 95.74), (xb + 0.4, 95.74), (xb, 96.14), (xb, yb)]
    Lf, Rt = H.pair_lines(path, W1, G1)        # heading west: right = north = P
    icp = [pin(7)] + Rt + [(pnear[0], Rt[-1][1] + (Rt[-1][0] - pnear[0])), pnear]
    icn = [pin(8)] + Lf + [(nnear[0], Lf[-1][1] + (nnear[0] - Lf[-1][0])), nnear]
    q = (xb, (96.2 + yb) / 2)
    icp, icn = H.match(icp, icn, segP=H.seg_near(icp, q), segN=H.seg_near(icn, q), sideP=-1, sideN=+1)
    cap_leg(r, "HUB_P1_TXP_IC", icp, F, W1, ok); cap_leg(r, "HUB_P1_TXN_IC", icn, F, W1, ok)
    H.log("P1 HUB_P1_TX_IC (U601->cap)", icp, icn)
    xbo = 161.6
    vbn, vbp = (161.95, 109.0), (161.4, 110.2)
    p0 = [pfar, (pfar[0], pfar[1] + 0.4)] if ok else [(pfar[0], pfar[1] + 0.75)]
    n0 = [nfar, (nfar[0], nfar[1] + 0.4)] if ok else [(nfar[0], nfar[1] + 0.75)]
    bp1 = p0 + [(xbo - 0.14, p0[-1][1] + (xbo - 0.14 - pfar[0])), (xbo - 0.14, 108.6), (vbp[0], 108.66), vbp]
    bn1 = n0 + [(xbo + 0.14, n0[-1][1] + (nfar[0] - xbo - 0.14)), (xbo + 0.14, 108.4), vbn]
    r.via("CR_SS_TXN", *vbn); r.via("CR_SS_TXP", *vbp)
    H.gvia(r, 160.75, 110.55)                    # return via for the L1 -> L6 change
    # L6: west on lane LB (N north), south at x 141.5, west into pins 10/11
    t10, t11 = r.pad_of_net("U901", "CR_SS_TXN"), r.pad_of_net("U901", "CR_SS_TXP")
    xs = 141.5
    ym = (t10[1] + t11[1]) / 2
    path = [(160.6, LB), (xs + 0.4, LB), (xs, LB + 0.4), (xs, ym - 0.4), (xs - 0.4, ym), (t10[0] + 0.75, ym)]
    Lf, Rt = H.pair_lines(path, W1, G1)        # heading west: right = north = N
    bn6 = [vbn, (161.3, Rt[0][1])] + Rt + [t10]
    bp6 = [vbp, (vbp[0] - 0.3, Lf[0][1])] + Lf + [t11]
    bp, bn = H.chain(bp1, bp6), H.chain(bn1, bn6)
    # match the whole cap->GL leg: bumps on the L6 west run (seg index found by position)
    q = (154.0, LB)
    bp, bn = H.match(bp, bn, segP=H.seg_near(bp, q), segN=H.seg_near(bn, q), sideP=+1, sideN=-1, center=q, h=0.15, hmax=0.15)
    split = lambda pts, v: (pts[:pts.index(v) + 1], pts[pts.index(v):])
    a1, a6 = split(bp, vbp); b1, b6 = split(bn, vbn)
    H.draw(r, "CR_SS_TXP", a1, F, W1); H.draw(r, "CR_SS_TXP", a6, B, W1)
    H.draw(r, "CR_SS_TXN", b1, F, W1); H.draw(r, "CR_SS_TXN", b6, B, W1)
    H.log("P1 CR_SS_TX (cap->U901)", bp, bn)

    # ---------------- C: P1 RX (pins 10/11): stacked vias -> L3 -> swap vias -> L6 -> C918/C917 -> U901
    vcp, vcn = (162.9, 96.95), (162.9, 97.65)
    cp1 = [pin(10), (xt, pin(10)[1]), (xt - 0.2, 97.0), (vcp[0] + 0.3, 97.0), vcp]
    cn1 = [pin(11), (xt, pin(11)[1]), (xt - 0.2, 97.28), (vcn[0] + 0.55, 97.28), (vcn[0] + 0.2, vcn[1]), vcn]
    H.draw(r, "CR_SS_RXP", cp1, F, W1); H.draw(r, "CR_SS_RXN", cn1, F, W1)
    r.via("CR_SS_RXP", *vcp); r.via("CR_SS_RXN", *vcn)
    xc3 = 160.6
    path = [(162.5, 97.3), (xc3 + 0.4, 97.3), (xc3, 97.7), (xc3, 107.3)]
    Lf, Rt = H.pair_lines(path, W3, G3)        # heading west: right = north = P
    vcn6, vcp6 = (160.95, 107.85), (160.35, 108.55)
    cp3 = [vcp, (vcp[0] - 0.25, Rt[0][1])] + Rt + [(vcp6[0], Rt[-1][1] + 0.07), vcp6]
    cn3 = [vcn, (vcn[0] - 0.25, Lf[0][1])] + Lf + [(vcn6[0], Lf[-1][1] + 0.17), vcn6]
    r.via("CR_SS_RXN", *vcn6); r.via("CR_SS_RXP", *vcp6)
    c918, c917 = r.pad_of_net("C918", "CR_SS_RXN"), r.pad_of_net("C917", "CR_SS_RXP")
    xs = (c918[0] + c917[0]) / 2
    path = [(159.4, LC), (xs + 0.4, LC), (xs, LC + 0.4), (xs, c918[1] - 1.0)]
    Lf, Rt = H.pair_lines(path, W1, G1)        # heading west: right = north = N
    cn6 = [vcn6, (159.95, vcn6[1])] + Rt + [(c918[0], c918[1] - 0.5), c918]
    cp6 = [vcp6, (159.75, Lf[0][1])] + Lf + [(c917[0], c917[1] - 0.5), c917]
    cp, cn = H.chain(cp1, cp3, cp6), H.chain(cn1, cn3, cn6)
    q = (146.0, LC)
    cp, cn = H.match(cp, cn, segP=H.seg_near(cp, q), segN=H.seg_near(cn, q), sideP=+1, sideN=-1, center=q, h=0.15, hmax=0.15)
    i1, i2 = cp.index(vcp), cp.index(vcp6)
    H.draw(r, "CR_SS_RXP", cp[i1:i2 + 1], L3, W3); H.draw(r, "CR_SS_RXP", cp[i2:], B, W1)
    i1, i2 = cn.index(vcn), cn.index(vcn6)
    H.draw(r, "CR_SS_RXN", cn[i1:i2 + 1], L3, W3); H.draw(r, "CR_SS_RXN", cn[i2:], B, W1)
    H.log("P1 CR_SS_RX (U601->C917/8)", cp, cn)
    # GL TX -> caps (pad 1, from the south)
    g7, g8 = r.pad_of_net("U901", "CR_TXN_IC"), r.pad_of_net("U901", "CR_TXP_IC")
    k8, k7 = r.pad_of_net("C918", "CR_TXN_IC"), r.pad_of_net("C917", "CR_TXP_IC")
    ym = (g7[1] + g8[1]) / 2
    path = [(g7[0] + 0.5, ym), (xs - 0.4, ym), (xs, ym - 0.4), (xs, k8[1] + 1.1)]
    Lf, Rt = H.pair_lines(path, W1, G1)        # heading east: left = north = TXN
    tn = [g7] + Lf + [(k8[0], Lf[-1][1] - (Lf[-1][0] - k8[0])), k8]
    tp = [g8] + Rt + [(k7[0], Rt[-1][1] - (k7[0] - Rt[-1][0])), k7]
    q = (xs, (ym + k8[1]) / 2)
    tp, tn = H.match(tp, tn, segP=H.seg_near(tp, q), segN=H.seg_near(tn, q), sideP=-1, sideN=+1,
                     top=0.15, gap=0.15, margin=0.12)
    H.draw(r, "CR_TXN_IC", tn, B, W1); H.draw(r, "CR_TXP_IC", tp, B, W1)
    H.log("P1 CR_TX_IC (U901->C917/8)", tp, tn)

    # ---------------- D: USBA1_DP/DN (pins 14/15): toe vias -> L3 -> D702 -> J701
    vdp, vdn = (164.3, 98.25), (164.3, 98.85)
    H.draw(r, "USBA1_DP", [pin(14), (xt - 0.05, pin(14)[1]), vdp], F, W1)
    H.draw(r, "USBA1_DN", [pin(15), (xt - 0.05, pin(15)[1]), vdn], F, W1)
    r.via("USBA1_DP", *vdp); r.via("USBA1_DN", *vdn)
    e6, e4 = r.pad("D702", 6), r.pad("D702", 4)
    xd = 163.6
    xc = (e6[0] + e4[0]) / 2
    ytop = e6[1] - 2.0
    path = [(xd, 99.4), (xd, 111.4), (xd - 4.2, 115.6), (xc + 1.0, 115.6), (xc, ytop)]
    Lf, Rt = H.pair_lines(path, W3, G3)        # heading south: left = east = DN
    dp3 = [vdp, (Rt[0][0] + 0.18, vdp[1]), (Rt[0][0], vdp[1] + 0.18)] + Rt
    dn3 = [vdn, (Lf[0][0], vdn[1] + (vdn[0] - Lf[0][0]))] + Lf
    usba_usb2_end(r, "D702", "J701", "USBA1", dp3, dn3)

    # ---------------- E: P2 TX (pins 16/17) through C605/C606 -> J701 via D701
    ok, pnear, pfar, nnear, nfar = caps(r, "C605", "C606", "HUB_P2_TXP_IC", "HUB_P2_TXN_IC", pin(16))
    if not ok:
        H.WARN.append("P2 TX: C605/C606 IC-side pad faces away from U601 -> rotate both 180 deg; "
                      "legs stop 0.75 mm short of the caps")
    xe = (pnear[0] + nnear[0]) / 2
    ye = 99.54
    path = [(164.3, ye), (xe + 0.4, ye), (xe, ye + 0.4), (xe, pnear[1] - 1.4)]
    Lf, Rt = H.pair_lines(path, W1, G1)        # heading west: right = north = P
    icp = [pin(16), (xt, pin(16)[1]), (xt - 0.2, Rt[0][1])] + Rt[1:] + \
          [(pnear[0], Rt[-1][1] + (Rt[-1][0] - pnear[0])), pnear]
    icn = [pin(17), (xt, pin(17)[1]), (xt - 0.08, Lf[0][1])] + Lf[1:] + \
          [(nnear[0], Lf[-1][1] + (nnear[0] - Lf[-1][0])), nnear]
    icp, icn = H.match(icp, icn, segP=4, segN=4, sideP=-1, sideN=+1, h=0.15, hmax=0.15)
    cap_leg(r, "HUB_P2_TXP_IC", icp, F, W1, ok); cap_leg(r, "HUB_P2_TXN_IC", icn, F, W1, ok)
    H.log("P2 HUB_P2_TX_IC (U601->cap)", icp, icn)
    d10, d9 = r.pad("D701", 10), r.pad("D701", 9)
    xT = (d10[0] + d9[0]) / 2
    yw = 111.2
    path = [(xe, pfar[1] + 1.0), (xe, yw - 0.4), (xe - 0.4, yw), (xT + 0.4, yw), (xT, yw + 0.4), (xT, d10[1] - 1.0)]
    Lf, Rt = H.pair_lines(path, W1, G1)        # heading south: right = west = P
    P = ([pfar, (pfar[0], pfar[1] + 0.3)] if ok else [(pfar[0], pfar[1] + 0.75)]) + Rt
    N = ([nfar, (nfar[0], nfar[1] + 0.3)] if ok else [(nfar[0], nfar[1] + 0.75)]) + Lf
    usba_ss_end(r, "D701", "J701", "USBA1_SS_TX", P, N, "P2 USBA1_SS_TX (cap->J701)")

    # ---------------- F: P2 RX (pins 19/20) -> J701 via D701
    d7, d6 = r.pad("D701", 7), r.pad("D701", 6)
    xR = (d7[0] + d6[0]) / 2
    yf = 111.9
    path = [(xt - 0.2, 100.74), (164.2, 100.74), (163.8, 101.14), (163.8, 103.2), (164.25, 103.65),
            (164.25, yf - 0.4), (163.85, yf), (xR + 0.4, yf), (xR, yf + 0.4), (xR, d7[1] - 1.0)]
    Lf, Rt = H.pair_lines(path, W1, G1)        # heading west: right = north = P
    usba_ss_end(r, "D701", "J701", "USBA1_SS_RX", [pin(19), (xt, pin(19)[1])] + Rt, [pin(20), (xt, pin(20)[1])] + Lf,
                "P2 USBA1_SS_RX (U601->J701)")


def p4_p6(r):
    """Hub port 4 (ETH_*: U801 RTL8156BG) and port 6 (MCU_USB: RP2350 via R1007/R1008).
    TX: L1, loops under the PF strap pins into C609/C610 (P threads the C610 pad gap to fix the
    polarity), then north along x 180.2 and east into U801 pins 46/47.
    RX: hub stub on L1 -> vias at y 107.5 -> L3 (stripline) -> vias west of C835/C836 -> L1.
    ETH USB2: L1 outer lane, hops to L6 around the C536/C808 pinch (y 64-72), back to L1 at x 181.6.
    MCU USB2 (full speed): L1 -> L6 -> L3 along y 71 -> L6 at x 222.9 -> R1007/R1008 pad 2."""
    pin = lambda k: r.pad("U601", k)
    ytoe = pin(36)[1] + 0.51
    # ---- TX (pins 36/37)
    ok = H.cap_ok(r, "C609", "HUB_P4_TXP_IC", "ETH_SS_TXP", pin(36)) and \
         H.cap_ok(r, "C610", "HUB_P4_TXN_IC", "ETH_SS_TXN", pin(37))
    c9i, c9o = r.pad_of_net("C609", "HUB_P4_TXP_IC"), r.pad_of_net("C609", "ETH_SS_TXP")
    c10i, c10o = r.pad_of_net("C610", "HUB_P4_TXN_IC"), r.pad_of_net("C610", "ETH_SS_TXN")
    xslot = (c10i[0] + c10o[0]) / 2
    ymid = (c9i[1] + c10i[1]) / 2
    xd = (pin(36)[0] + pin(37)[0]) / 2
    yT = 108.1
    path = [(xd, ytoe + 0.05), (xd, yT - 0.4), (xd + 0.4, yT), (c10i[0] - 0.9, yT)]
    Lf, Rt = H.pair_lines(path, W1, G1)        # heading south: right = west = P; after the turn P south
    xn = c10i[0] - 0.48
    tn = [pin(37)] + Lf + [(xn - 0.4, Lf[-1][1]), (xn, Lf[-1][1] - 0.4), (xn, c10i[1]), c10i]
    tp = [pin(36)] + Rt + [(xslot - 0.55, Rt[-1][1]), (xslot, Rt[-1][1] - 0.55), (xslot, ymid), (c9i[0], ymid), c9i]
    H.draw(r, "HUB_P4_TXP_IC", tp, F, 0.09); H.draw(r, "HUB_P4_TXN_IC", tn, F, W1)
    H.log("P4 HUB_P4_TX_IC (U601->C609/10)", tp, tn)
    ic_skew = H.L(tp) - H.L(tn)                 # compensated on the cap->U801 section
    u46, u47 = r.pad_of_net("U801", "ETH_SS_TXP"), r.pad_of_net("U801", "ETH_SS_TXN")
    xc, yc = 180.2, 63.1
    path = [(c9o[0] + 0.9, ymid), (xc - 0.4, ymid), (xc, ymid - 0.4), (xc, yc + 0.4), (xc + 0.4, yc), (u46[0] - 2.0, yc)]
    Lf, Rt = H.pair_lines(path, W1, G1)        # heading east: left = north = P
    xP = u46[0] - 0.585 - (Lf[-1][1] - u46[1])          # 45-degree fan-in, P above N
    xN = u47[0] - 0.395 - (Rt[-1][1] - u47[1])
    P = [c9o, (c9o[0] + 0.45, c9o[1]), (Lf[0][0], Lf[0][1])] + Lf[1:-1] + [(xP, Lf[-1][1]), (u46[0] - 0.585, u46[1]), u46]
    N = [c10o, (c10o[0] + 0.45, c10o[1]), (Rt[0][0], Rt[0][1])] + Rt[1:-1] + [(xN, Rt[-1][1]), (u47[0] - 0.395, u47[1]), u47]
    q = (xc, 85.0)
    P, N = H.match(P, N, segP=H.seg_near(P, q), segN=H.seg_near(N, q), sideP=+1, sideN=-1, center=q,
                   offset=-ic_skew)
    H.draw(r, "ETH_SS_TXP", P, F, W1); H.draw(r, "ETH_SS_TXN", N, F, W1)
    H.log("P4 ETH_SS_TX (cap->U801)", P, N)
    H.log("P4 TX total U601->U801", tp + P, tn + N)

    # ---- RX (pins 39/40): vias at y 107.5 -> L3 -> vias west of C835/C836
    vrp, vrn = (171.25, 107.5), (171.95, 107.5)
    rp1 = [pin(39), (pin(39)[0], vrp[1] - 0.5), vrp]
    rn1 = [pin(40), (pin(40)[0], vrn[1] - 0.5), vrn]
    r.via("ETH_SS_RXP", *vrp); r.via("ETH_SS_RXN", *vrn)
    c835, c836 = r.pad(  "C835", 1), r.pad("C836", 1)   # west pads (where the RX nets belong)
    vtp, vtn = (189.4, c835[1]), (189.4, c836[1])
    xr, yr = 180.0, 107.9
    ye = (vtp[1] + vtn[1]) / 2
    path = [(175.0, yr), (xr - 0.4, yr), (xr, yr - 0.4), (xr, ye + 0.4), (xr + 0.4, ye), (vtp[0] - 1.0, ye)]
    Lf, Rt = H.pair_lines(path, W3, G3)        # heading east: left = north = P
    # through the hub via field: P passes north of the RXN/MCU vias, N south of them
    rp3 = [vrp, (vrp[0] + 0.4, 107.0), (174.1, 107.0), (174.1 + Lf[0][1] - 107.0, Lf[0][1])] + Lf + \
          [(vtp[0] - 0.4, Lf[-1][1]), vtp]
    rn3 = [vrn, (vrn[0] + 0.25, Rt[0][1] - 0.05), (vrn[0] + 0.3, Rt[0][1])] + Rt + [(vtn[0] - 0.4, Rt[-1][1]), vtn]
    r.via("ETH_SS_RXP", *vtp); r.via("ETH_SS_RXN", *vtn)
    H.gvia(r, vtp[0] + 0.5, (vtp[1] + vtn[1]) / 2)      # return vias at the L3 -> L1 change
    H.gvia(r, vtp[0] - 0.4, vtp[1] - 0.65)
    okr = H.cap_ok(r, "C835", "ETH_SS_RXP", "ETH_TXP_IC", vtp) and H.cap_ok(r, "C836", "ETH_SS_RXN", "ETH_TXN_IC", vtn)
    if not okr:
        H.WARN.append("P4 RX: C835/C836 hub-side pad faces the RTL -> rotate both 180 deg; RX legs stop "
                      "0.75 mm short of the caps, ETH_TXP/N_IC (U801 pins 43/44 -> caps) not routed")
    pa = [(vtp[0], vtp[1]), (min(r.pad(c, 1)[0] for c in ("C835",)) if False else r.pad("C835", 1)[0] if
          math.hypot(r.pad("C835", 1)[0] - vtp[0], 0) < math.hypot(r.pad("C835", 2)[0] - vtp[0], 0) else r.pad("C835", 2)[0], vtp[1])]
    near835 = min((r.pad("C835", 1), r.pad("C835", 2)), key=lambda q: abs(q[0] - vtp[0]))
    near836 = min((r.pad("C836", 1), r.pad("C836", 2)), key=lambda q: abs(q[0] - vtn[0]))
    cap_leg(r, "ETH_SS_RXP", [vtp, near835], F, W1, okr)
    cap_leg(r, "ETH_SS_RXN", [vtn, near836], F, W1, okr)
    rp, rn = H.chain(rp1, rp3), H.chain(rn1, rn3)
    q = (xr, 85.0)
    rp, rn = H.match(rp, rn, segP=H.seg_near(rp, q), segN=H.seg_near(rn, q), sideP=+1, sideN=-1, center=q)
    H.draw(r, "ETH_SS_RXP", rp[:rp.index(vrp) + 1], F, W1); H.draw(r, "ETH_SS_RXP", rp[rp.index(vrp):], L3, W3)
    H.draw(r, "ETH_SS_RXN", rn[:rn.index(vrn) + 1], F, W1); H.draw(r, "ETH_SS_RXN", rn[rn.index(vrn):], L3, W3)
    H.log("P4 ETH_SS_RX (U601->C835/6)", rp + [near835], rn + [near836])
    if okr:
        far835 = max((r.pad("C835", 1), r.pad("C835", 2)), key=lambda q: abs(q[0] - vtp[0]))
        far836 = max((r.pad("C836", 1), r.pad("C836", 2)), key=lambda q: abs(q[0] - vtn[0]))
        u43, u44 = r.pad_of_net("U801", "ETH_TXP_IC"), r.pad_of_net("U801", "ETH_TXN_IC")
        H.draw(r, "ETH_TXP_IC", [far835, (u43[0] - 0.75, far835[1]), (u43[0] - 0.55, u43[1]), u43], F, W1)
        H.draw(r, "ETH_TXN_IC", [far836, (far836[0] + 0.2, far836[1] - 0.2), (u44[0] - 0.9, u44[1]), u44], F, W1)

    # ---- ETH USB2 (pins 34/35)
    u49, u50 = r.pad_of_net("U801", "ETH_DN"), r.pad_of_net("U801", "ETH_DP")
    xe, ye2 = 181.2, 108.8
    xd = (pin(34)[0] + pin(35)[0]) / 2
    vdn, vdp = (180.9, 71.9), (181.6, 71.9)
    path = [(xd, ytoe + 0.05), (xd, ye2 - 0.4), (xd + 0.4, ye2), (xe - 0.4, ye2), (xe, ye2 - 0.4), (xe, vdn[1] + 0.8)]
    Lf, Rt = H.pair_lines(path, W1, G1)        # heading south: left = east = DN; heading north: DN west
    dn1 = [pin(35)] + Lf + [(vdn[0], vdn[1] + 0.5), vdn]
    dp1 = [pin(34)] + Rt + [(vdp[0], vdp[1] + 0.5), vdp]
    r.via("ETH_DN", *vdn); r.via("ETH_DP", *vdp)
    wdn, wdp = (181.6, 63.75), (181.6, 64.45)
    dn6 = [vdn, (181.15, vdn[1] - 0.25), (181.15, wdn[1]), wdn]
    dp6 = [vdp, (181.43, vdp[1] - 0.17), (181.43, 64.9), wdp]
    r.via("ETH_DN", *wdn); r.via("ETH_DP", *wdp)
    ym = 63.88
    dn1b = [wdn, (u49[0] - 0.8, wdn[1]), (u49[0] - 0.475, u49[1]), u49]
    dp1b = [wdp, (wdp[0] + 0.42, ym + 0.14), (u50[0] - 0.65, ym + 0.14), (u50[0] - 0.4, u50[1]), u50]
    H.draw(r, "ETH_DN", dn1, F, W1); H.draw(r, "ETH_DP", dp1, F, W1)
    H.draw(r, "ETH_DN", dn6, B, W1); H.draw(r, "ETH_DP", dp6, B, W1)
    H.draw(r, "ETH_DN", dn1b, F, W1); H.draw(r, "ETH_DP", dp1b, F, W1)
    H.log("P4 ETH_DP/DN", dp1 + dp6 + dp1b, dn1 + dn6 + dn1b)

    # ---- MCU USB (pins 41/42), full speed: DP takes the north lane on L6/L3
    m41, m42 = pin(41), pin(42)
    vmn, vmp = (172.7, 107.5), (173.4, 107.5)
    mn1 = [m41, (m41[0], 106.4), (vmn[0], 106.9), vmn]
    mp1 = [m42, (m42[0], 106.0), (vmp[0], 106.8), vmp]
    r.via("MCU_USB_DN", *vmn); r.via("MCU_USB_DP", *vmp)
    xm = 182.6
    wmp, wmn = (xm, 71.6), (xm + 0.7, 71.6)
    mp6 = [vmp, (vmp[0] + 0.4, 107.9), (xm - 0.4, 107.9), (xm, 107.5), (xm, wmp[1]), wmp]
    mn6 = [vmn, (vmn[0] + 0.4, 108.25), (xm - 0.4 + 0.35 + 0.15, 108.25), (xm + 0.35, 107.75),
           (xm + 0.35, wmn[1] + 0.35), wmn]
    r.via("MCU_USB_DN", *wmn); r.via("MCU_USB_DP", *wmp)
    r1007, r1008 = r.pad_of_net("R1007", "MCU_USB_DP"), r.pad_of_net("R1008", "MCU_USB_DN")
    # L3 along y 72.9 (DN) / 73.26 (DP): clear of the J801 pins and the PHY crystal vias
    xv = 222.9
    zmn, zmp = (xv, 71.0), (xv, 71.75)
    mn3 = [wmn, (wmn[0], 72.9), (xv - 1.1, 72.9), (xv - 0.7, 72.5), (xv - 0.7, 71.4), (xv - 0.3, 71.0), zmn]
    mp3 = [wmp, (wmp[0], 73.26), (xv - 0.4, 73.26), (xv, 72.86), zmp]
    r.via("MCU_USB_DN", *zmn); r.via("MCU_USB_DP", *zmp)
    mn6b = [zmn, (zmn[0] + 0.25, 71.15), (r1008[0] - 0.2, 71.15), r1008]
    mp6b = [zmp, (r1007[0], zmp[1]), r1007]
    for net, rr, pn in (("USB_DP_IC", "R1007", 67), ("USB_DM_IC", "R1008", 66)):
        rp1 = r.pad_of_net(rr, net)
        up = r.pad("U1001", pn)
        v = (rp1[0], 72.55)
        r.via(net, *v)
        H.draw(r, net, [rp1, v], B, W1)
        H.draw(r, net, [v, (up[0], v[1] + abs(up[0] - v[0]) * 0.0 + 0.3), up] if abs(up[0] - v[0]) < 0.3
               else [v, (up[0], 72.95), up], F, W1)
    H.draw(r, "MCU_USB_DN", mn1, F, W1); H.draw(r, "MCU_USB_DP", mp1, F, W1)
    H.draw(r, "MCU_USB_DN", mn6, B, W1); H.draw(r, "MCU_USB_DP", mp6, B, W1)
    H.draw(r, "MCU_USB_DN", mn3, L3, W3); H.draw(r, "MCU_USB_DP", mp3, L3, W3)
    H.draw(r, "MCU_USB_DN", mn6b, B, W1); H.draw(r, "MCU_USB_DP", mp6b, B, W1)
    H.log("P6 MCU_USB_DP/DN", mp1 + mp6 + mp3 + mp6b, mn1 + mn6 + mn3 + mn6b)


def hub_xtal(r):
    """Y601 -> U601 pins 98 (XI) / 97 (XO), L1. XO is the outer loop (north of C328, down x 164.5 into
    pad 3's east side); XI runs inside it and threads between the crystal's pad rows into pad 1.
    The toes of pins 99/100 stay free for their vias (+3V3 at (166.45, 91.15), RBIAS at (165.75, 91.4)).
    C637/C638 (bottom) hang off one via per net."""
    p98, p97 = r.pad("U601", 98), r.pad("U601", 97)
    y1, y3 = r.pad("Y601", 1), r.pad("Y601", 3)
    toe = p98[1] - 0.51
    w = 0.12
    xo = [p97, (p97[0], 89.48), (164.5, 89.48), (164.5, y3[1]), y3]
    xi = [p98, (p98[0], 90.67), (165.0, 90.67), (165.0, 92.85), (y1[0], 92.85), y1]
    H.draw(r, "HUB_XO", xo, F, w); H.draw(r, "HUB_XI", xi, F, w)
    vo, vi = (164.5, 91.5), (165.0, 92.0)
    r.via("HUB_XO", *vo); r.via("HUB_XI", *vi)
    c638, c637 = r.pad_of_net("C638", "HUB_XO"), r.pad_of_net("C637", "HUB_XI")
    H.draw(r, "HUB_XO", [vo, (vo[0] - 0.15, 91.35), (c638[0], 91.35), c638], B, w)
    H.draw(r, "HUB_XI", [vi, (vi[0] - 0.35, 92.65), (161.35, 92.65), (161.1, 92.9), (161.1, c637[1]), c637], B, w)
    H.log("hub XI / XO (Y601->U601)", xi, xo)


# Power-pin toe vias the other scripts need between my pairs (kept clear; checked with KEEP_TEST=1)
TOE_VIAS = [("+1V15", 164.15, 96.55), ("+1V15", 164.3, 100.12),
            ("/USB hub/HUB_RBIAS", 165.75, 91.4), ("+3V3", 166.45, 91.15),
            ("/Card reader/CR_SD_CDZ", 137.15, 114.65), ("/Card reader/CR_SD_WP", 137.15, 115.35)]


def route(board, r):
    p3(r)
    hub_left(r)
    p4_p6(r)
    hub_xtal(r)
    if os.environ.get("KEEP_TEST"):
        for net, x, y in TOE_VIAS:
            r.via(net, x, y)
    for w in H.WARN:
        print("WARNING:", w)
    for name, lp, ln in H.LOG:
        print(f"  {name:34s} P {lp:7.2f}  N {ln:7.2f}  skew {abs(lp - ln):.3f}")
