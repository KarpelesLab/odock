"""odeck-10 hubrails region (138,80)-(180,108): local nets + supply drops (phase g, hybrid plan).

Routes every still-unconnected connection of the nets LOCAL to the hubrails block (USB7206C straps / TEST / PF /
SPI-flash pins, RBIAS, VBUS-detect chain, LM5148 analog side, LM74700, TPS62933F/P dividers, ...) and ties every
still-unconnected pad of the shared supply nets in the region (+3V3, +1V15, +5V, GND, VIN) to copper of the same net
(an inner plane through a via, a pour, a track).  Signal nets that leave the region are left to Freerouting.

Method: KiCad zone fill + connectivity (GND_L1/GND_L6 ignored, like f_fanout) gives the copper clusters of each net;
the raster maze router in _g_hubrails_lib.py (0.025 mm grid) joins a cluster to the others on L1/L3/L6 with 0.45/0.25
vias (0.35/0.15 only when nothing else fits), against every pad/track/via/pour/rule area already on the board (a-f):
0.15 mm clearance, 0.3 mm to HV copper and to HS tracks, 0.3 mm to pours (no pull-back), 0.2 mm to holes.
- Units (one local net, its SPI-flash legs, or one supply stray) are routed in order; a failed connection may rip up
  the units in its way, as a transaction kept only if they all route again.
- Pours: other nets may only nibble a pour within 0.9 mm of a pad sitting in its cut-outs; after routing the pours
  are refilled and any that lost a piece/area gets hardened and its intruders re-routed.  Inner planes: a route whose
  vias would cut an L4 island of another net in two is undone and retried with those via spots banned.
- Signal pads of nets that leave the region are checked for an escape path (3 mm); one we boxed in gets a reserved
  corridor if that costs no local connection.
Copper stays inside the region + 0.5 mm; no vias in the hub upstream/P5 corridor (x 167.5-174, y < 90.8).
GROUPED: everything drawn goes into group "route:g_hubrails".  Runtime ~13 min.  See docs/routing-notes/g_hubrails.md.
"""
import os
import sys
import time
import fnmatch
import json
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew  # noqa: E402
import _g_hubrails_lib as GL  # noqa: E402

NETS = []
GROUPED = True

REGION = (138.0, 80.0, 180.0, 108.0)
ALLOWED = [(137.5, 79.5, 180.5, 108.5)]          # region + 0.5 mm
BOUNDS = (136.5, 78.5, 181.5, 109.5)
HUB_RING = (165.75, 92.75, 176.25, 103.25)      # inside the USB7206C pad ring (soft cost)
CORRIDOR_NOVIA = [(167.5, 78.5, 174.0, 90.8)]   # hub UP/P5 corridor: no vias (pin-toe vias at y > 90.8 allowed)

# nets local to the region (build/partition.json, "local" -> "hubrails")
LOCAL = [
    "HUB_RBIAS", "+1V15",
    # hub right side, strap column (top to bottom)
    "HUB_PF29", "HUB_SPI_D3", "HUB_SPI_D2", "HUB_SPI_D1", "HUB_SPI_D0", "HUB_SPI_CE_N", "HUB_SPI_CLK",
    "HUB_PF19", "HUB_TEST3", "HUB_TEST2", "HUB_TEST1", "HUB_PF18",
    # hub left / bottom straps
    "HUB_PF31", "HUB_CFG1", "HUB_CFG2", "HUB_CFG3", "HUB_PF3", "HUB_PF4", "HUB_PF5", "HUB_PF6", "HUB_PF7",
    "HUB_VBUS_SNS", "HUB_VBUS_DET", "HUB_VBUS_BUF",
    "3V3_EN", "3V3_SS", "3V3_FB", "1V15_EN", "1V15_FB", "RAILS_PG",
    "5V_CNFG", "5V_RT", "5V_COMP", "5V_CC", "5V_FB", "5V_VDDA", "5V_VCC", "5V_VINC", "5V_EN", "5V_VCAP",
    "5V_BUCK", "5V_OR", "5V_SW", "5V_SNB",
]
SUPPLY = ["+3V3", "+5V", "GND", "VIN"]
# signal nets that leave the region (Freerouting): their pads here must keep an escape path
ESCAPE_NETS = ["I2C_SYS_SDA", "I2C_SYS_SCL", "TEMP_ALERT_N", "USBA1_OCS_N", "USBA2_OCS_N", "USBA1_PWR_EN",
               "USBA2_PWR_EN", "NTC_ADC1", "HUB_RESET_N", "HUB_SMB_CLK", "HUB_SMB_DAT", "HUB_SMB_PU", "PG_5V",
               "VBUS_LAPTOP"]
PRE_RESERVE = []          # e.g. "U1203.1": tried, costs 8 local connections (see notes)
RIGHT_STRAPS = ["HUB_PF29", "HUB_SPI_D3", "HUB_SPI_D2", "HUB_SPI_D1", "HUB_SPI_D0", "HUB_SPI_CE_N", "HUB_SPI_CLK",
                "HUB_PF19", "HUB_TEST3", "HUB_TEST2", "HUB_TEST1", "HUB_PF18"]

WIDTHS = {"GND": (0.25, 0.2, 0.15), "+3V3": (0.2, 0.15), "+1V15": (0.2, 0.15), "+5V": (0.25, 0.2, 0.15),
          "VIN": (0.2, 0.15), "5V_BUCK": (0.2, 0.15), "5V_OR": (0.2, 0.15), "5V_SW": (0.3, 0.2),
          "5V_SNB": (0.3, 0.2), "5V_VCC": (0.3, 0.2, 0.15), "5V_VDDA": (0.2, 0.15), "5V_VINC": (0.25, 0.15),
          "5V_VCAP": (0.2, 0.15)}
VIA = (0.45, 0.25)


def _classes(board):
    pro = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "odeck-10.kicad_pro")
    pats = [(p["pattern"], p["netclass"]) for p in json.load(open(pro))["net_settings"]["netclass_patterns"]]
    hv, hs = set(), set()
    for n in board.GetNetsByName().keys():
        s = GL.short(n)
        for pat, cls in pats:
            if fnmatch.fnmatchcase(s, pat) or fnmatch.fnmatchcase(str(n), pat):
                if cls == "HV":
                    hv.add(s)
                elif cls in ("USB_90", "HS_85", "ETH_100"):
                    hs.add(s)
                break
    return hv, hs


def _inreg(x, y):
    return REGION[0] <= x <= REGION[2] and REGION[1] <= y <= REGION[3]


def _bbox(pads):
    xs = [p.pos[0] for p in pads]
    ys = [p.pos[1] for p in pads]
    return min(xs), min(ys), max(xs), max(ys)


LOCAL_ONLY = None      # debug: restrict to these nets


def route(board, r):
    t0 = time.time()
    import a_planes
    gnd_outer = set(a_planes.GND_POURS)
    for z in board.Zones():
        if z.GetZoneName() in gnd_outer:
            z.UnFill()
    to_fill = [z for z in board.Zones() if not z.GetIsRuleArea() and z.GetZoneName() not in gnd_outer]
    pcbnew.ZONE_FILLER(board).Fill(to_fill)
    board.BuildConnectivity()
    conn = board.GetConnectivity()
    hv, hs = _classes(board)
    BR = GL.BitRouter(board, r, BOUNDS, ALLOWED, hv, hs, skip_zones=gnd_outer)
    for rc in CORRIDOR_NOVIA:
        BR.g.rect(*rc, out=BR.extra_novia)
    # soft costs: copper inside the hub pad ring (heel side) steals the strap pins' escapes
    for l in (pcbnew.F_Cu,):
        BR.g.rect(*HUB_RING, out=BR.pen_tr[l])
    BR.g.rect(*HUB_RING, out=BR.pen_via)
    print("g_hubrails: raster ready %.1fs" % (time.time() - t0))
    pour0 = {}
    for z in to_fill:
        if z.GetZoneName() in BR.zone_rows:
            fl = z.GetFilledPolysList(z.GetLayer())
            pour0[z.GetZoneName()] = (fl.OutlineCount(), fl.Area() / 1e12)

    fullname = {}
    for n in board.GetNetsByName().keys():
        fullname.setdefault(GL.short(n), str(n))

    from collections import defaultdict, deque

    # escape check for the pads of signal nets that leave the region (Freerouting): path to a ring 3 mm away
    esc_pads = []
    for net in ESCAPE_NETS:
        if net not in fullname:
            continue
        for c in BR.clusters(conn, fullname[net], None):
            for p in c["pads"]:
                if _inreg(*p.pos):
                    one = BR._mk_cluster({p.uuid})
                    esc_pads.append((net, p, one))

    def escapes(per_net=None):
        boxed = set()
        for net, p, one in esc_pads:
            if per_net:
                per_net(net)
            win = (p.pos[0] - 3.0, p.pos[1] - 3.0, p.pos[0] + 3.0, p.pos[1] + 3.0)
            res, why = BR.route(net, one, [BR.ring(win)], width=0.15, via=VIA, window=win, plane_goal=False,
                                dry=True)
            if not res:
                res, why = BR.route(net, one, [BR.ring(win)], width=0.15, via=(0.35, 0.15), window=win,
                                    plane_goal=False, dry=True)
            if not res:
                boxed.add("%s.%s(%s)" % (p.ref, p.num, net))
        return boxed
    boxed0 = escapes()
    print("g_hubrails: %d escape pads, %d already boxed in before routing: %s" %
          (len(esc_pads), len(boxed0), " ".join(sorted(boxed0))))

    reserv = []

    def apply_reservations(exclude=None):
        BR.extra_notrack = {l: {} for l in GL.ROUTE_LAYERS}
        BR.extra_novia = {}
        for rc in CORRIDOR_NOVIA:
            BR.g.rect(*rc, out=BR.extra_novia)
        for rnet, tr, vi in reserv:
            if rnet == exclude:
                continue
            for l, rows in tr.items():
                GL.OR(BR.extra_notrack[l], rows)
            GL.OR(BR.extra_novia, vi)

    def corridor(items, width=0.15, via=VIA):
        tr, vi = defaultdict(dict), {}
        G = BR.g
        for d in items:
            if d[0] == "via":
                x, y = d[1]
                for l in GL.ROUTE_LAYERS:
                    G.circle(x, y, via[0] / 2 + 0.15 + 0.15 + 0.02, tr[l])
                G.circle(x, y, via[0] / 2 + 0.15 + 0.225 + 0.02, vi)
            else:
                _, l, xy = d
                for a, b in zip(xy, xy[1:]):
                    G.capsule(a[0], a[1], b[0], b[1], width / 2 + 0.15 + 0.15 + 0.02, tr[l])
                    G.capsule(a[0], a[1], b[0], b[1], width / 2 + 0.15 + 0.225 + 0.02, vi)
        return tr, vi


    # pre-reserved escape corridors (pads that the local routing would otherwise box in)
    for net, p, one in esc_pads:
        if "%s.%s" % (p.ref, p.num) not in PRE_RESERVE:
            continue
        win = (p.pos[0] - 3.0, p.pos[1] - 3.0, p.pos[0] + 3.0, p.pos[1] + 3.0)
        apply_reservations(exclude=net)
        res = BR.route(net, one, [BR.ring(win)], width=0.15, via=VIA, window=win, plane_goal=False, dry=True)[0]
        if res:
            reserv.append((net,) + corridor(res["items"], 0.15, VIA))
        apply_reservations()

    def clone(c):
        return {"uuids": set(c["uuids"]), "rows": defaultdict(dict, {l: dict(v) for l, v in c["rows"].items()}),
                "plane": dict(c["plane"]), "pads": list(c["pads"])}

    nets = [n for n in LOCAL + SUPPLY if not LOCAL_ONLY or n in LOCAL_ONLY]
    templ = {}
    for net in nets:
        if net in fullname:
            templ[net] = BR.clusters(conn, fullname[net], None)

    def dist(a, b):
        if not a["pads"] or not b["pads"]:
            return 1e9
        return min(math.hypot(p.pos[0] - q.pos[0], p.pos[1] - q.pos[1]) for p in a["pads"] for q in b["pads"])

    def is_flash(c):
        return any(p.ref == "U602" for p in c["pads"])

    # ---- units: a local net (or its SPI-flash legs), or one stray cluster of a supply net
    units = {}          # uid -> dict(kind, net, ...)
    order = []
    NS = {}             # local net -> current cluster list
    for net in LOCAL:
        if net not in templ or len(templ[net]) < 2:
            continue
        units["L:" + net] = {"kind": "L", "net": net}
        if net.startswith("HUB_SPI") and any(is_flash(c) for c in templ[net]):
            units["F:" + net] = {"kind": "F", "net": net, "dep": "L:" + net}
    supply_units = []
    for net in SUPPLY + ["+1V15"]:
        if net not in templ:
            continue
        cl = templ[net]
        main = max(cl, key=lambda c: (bool(c["plane"]), len(c["uuids"])))
        if net == "+1V15":
            continue      # +1V15 is local: handled as an L unit
        for k, c in enumerate(cl):
            if c is main or not c["pads"] or not any(_inreg(*p.pos) for p in c["pads"]):
                continue
            uid = "S:%s:%s.%s" % (net, c["pads"][0].ref, c["pads"][0].num)
            units[uid] = {"kind": "S", "net": net, "src": c, "main": main}
            supply_units.append(uid)
    # order: RBIAS + hub-side +1V15 first, hub-side +3V3 toe drops, the local nets (right-side straps first),
    # the SPI-flash legs, then the other supply ties
    first = ["L:HUB_RBIAS", "L:+1V15"] + ["L:" + n for n in RIGHT_STRAPS]

    def span(uid):
        ps = [p for c in templ[units[uid]["net"]] for p in c["pads"]]
        b = _bbox(ps)
        return (b[2] - b[0]) + (b[3] - b[1])
    hub_s = [u for u in supply_units if any(p.ref == "U601" for p in units[u]["src"]["pads"])]
    order = [u for u in first if u in units] + \
        sorted([u for u in units if u.startswith("L:") and u not in first], key=span) + hub_s + \
        [u for u in units if u.startswith("F:")] + [u for u in supply_units if u not in hub_s]

    stats = {"ok": 0, "rip": 0}
    rips = defaultdict(int)
    failed = {}          # uid -> [labels]

    def attempt(net, src, dsts, wins, bb, plane_goal, soft=False):
        widths = WIDTHS.get(net, (0.15,))
        vias = (VIA, (0.35, 0.15))
        uid = BR.cur
        saved = dict(BR.extra_novia)
        try:
            for via in vias:
                for m in wins:
                    win = (bb[0] - m, bb[1] - m, bb[2] + m, bb[3] + m)
                    for w in (widths[-1:] if soft else widths):
                        for _ in range(4):
                            n0 = len(BR.units[uid]["geom"]) if (not soft and uid in BR.units) else 0
                            res, why = BR.route(net, src, dsts, width=w, via=via, window=win,
                                                plane_goal=plane_goal, soft=soft)
                            if not res or soft:
                                break
                            nv = [(d[1][0], d[1][1], via[0]) for d in res["items"] if d[0] == "via"]
                            bad = BR.split_check(net, nv) if nv else []
                            if not bad:
                                break
                            # this route would cut an inner plane of another net in two: undo, ban its vias
                            geo = BR.geom_of(uid)
                            BR.remove_unit(uid)
                            if n0:
                                BR.replay(uid, geo[0], geo[1][:n0])
                            BR.cur = uid
                            for x, y, sz in nv:
                                BR.g.circle(x, y, 0.6, BR.extra_novia)
                            res = None
                        if res:
                            return res, w, via
            return None, None, None
        finally:
            BR.extra_novia = saved

    depth = [0]

    def closure(cs):
        out = set()
        stack = list(cs)
        while stack:
            c = stack.pop()
            if c in out:
                continue
            out.add(c)
            for d, u in units.items():
                if u.get("dep") == c and (d in done or d in BR.units):
                    stack.append(d)
            for d in units[c].get("deps", ()):
                if d in done or d in BR.units:
                    stack.append(d)
        return out

    def snap(uids):
        sn = {"u": {}, "ns": {}}
        for x in uids:
            u = units[x]
            sn["u"][x] = (BR.geom_of(x), x in done, list(failed[x]) if x in failed else None,
                          u.get("cluster"), set(u.get("deps", set())), u.get("ns_after"))
            if u["kind"] in ("L", "F") and u["net"] in NS:
                sn["ns"][u["net"]] = [clone(c) for c in NS[u["net"]]]
        return sn

    def restore(sn):
        for x in sn["u"]:
            BR.remove_unit(x)
        for x, (geo, dn, fl, cl, deps, nsa) in sn["u"].items():
            if nsa is None:
                units[x].pop("ns_after", None)
            else:
                units[x]["ns_after"] = nsa
            if geo[0] is not None:
                BR.replay(x, geo[0], geo[1])
            if dn:
                done.add(x)
            else:
                done.discard(x)
            if fl is None:
                failed.pop(x, None)
            else:
                failed[x] = fl
            if cl is None:
                units[x].pop("cluster", None)
            else:
                units[x]["cluster"] = cl
            units[x]["deps"] = deps
        for net, cl in sn["ns"].items():
            NS[net] = cl

    def rip(x):
        BR.remove_unit(x)
        done.discard(x)
        failed.pop(x, None)
        units[x].pop("cluster", None)
        units[x]["deps"] = set()

    def rerun(xs):
        cur = BR.cur
        depth[0] += 1
        for x in sorted(xs, key=lambda q: order.index(q) if q in order else 1e9):
            run_unit(x)
        depth[0] -= 1
        BR.cur = cur

    def connect_one(uid, net, src, dsts, local, plane_goal):
        if local:
            near = min((d for d in dsts if d["pads"]), key=lambda d: dist(src, d), default=None)
            bb = _bbox(src["pads"] + ([p for p in near["pads"] if _inreg(*p.pos)] if near else []))
            wins = [1.5, 4.0, 8.0]
        else:
            bb = _bbox(src["pads"])
            wins = [2.0, 4.5, 9.0, 14.0]
        res, w, via = attempt(net, src, dsts, wins, bb, plane_goal)
        if res or depth[0] > 0:
            return res, w, via
        # rip-up & reroute, as a transaction: kept only if the ripped units all route again
        sres, sw, svia = attempt(net, src, dsts, wins, bb, plane_goal, soft=True)
        if not sres:
            return None, None, None
        cs = BR.conflicts(net, sres["items"], sw, svia)
        cs = {c for c in cs if c != uid and c in units and units[c].get("dep") != uid}
        if not cs or len(cs) > 5 or any(rips[c] >= 4 for c in cs):
            return None, None, None
        allc = closure(cs) - {uid}
        if any(units[c].get("dep") == uid for c in allc):
            return None, None, None
        sn = snap(allc)
        ugeo = BR.geom_of(uid)
        before = sum(len(failed.get(c, [])) for c in allc) + 1
        for c in allc:
            rip(c)
        BR.cur = uid
        res, w, via = attempt(net, src, dsts, wins, bb, plane_goal)
        if not res:
            restore(sn)
            BR.cur = uid
            return None, None, None
        rerun(allc)
        after = sum(len(failed.get(c, [])) for c in allc)
        if after >= before:
            BR.remove_unit(uid)
            if ugeo[0] is not None:
                BR.replay(uid, ugeo[0], ugeo[1])
            restore(sn)
            BR.cur = uid
            return None, None, None
        for c in allc:
            rips[c] += 1
        stats["rip"] += 1
        return res, w, via

    def run_unit(uid):
        u = units[uid]
        net = u["net"]
        BR.cur = uid
        fl = []
        if u["kind"] == "S":
            src = clone(u["src"])
            peers = [v for k, v in units.items() if k != uid and v["kind"] == "S" and v["net"] == net and
                     v.get("cluster") is not None]
            dsts = [clone(u["main"])] + [v["cluster"] for v in peers]
            res, w, via = connect_one(uid, net, src, dsts, False, True)
            label = "%s %s.%s" % (net, src["pads"][0].ref, src["pads"][0].num)
            if res:
                stats["ok"] += 1
                for l, rows in res["rows"].items():
                    GL.OR(src["rows"][l], rows)
                u["cluster"] = src
                k = res.get("dst")
                if k is not None and k > 0:
                    peers[k - 1].setdefault("deps", set()).add(uid)
            else:
                fl.append(label)
        else:
            if u["kind"] == "L":
                NS[net] = [clone(c) for c in templ[net]]
            else:       # flash legs start again from the state the strap unit left (a re-run must not reuse merges)
                NS[net] = [clone(c) for c in units["L:" + net].get("ns_after", NS[net])]
            cl = NS[net]
            main = max(cl, key=lambda c: (bool(c["plane"]), len(c["uuids"])))
            if u["kind"] == "L":
                pending = [c for c in cl if c is not main and not is_flash(c)]
                if is_flash(main):
                    pending = [c for c in cl if not is_flash(c)][1:]
            else:
                pending = [c for c in cl if is_flash(c)]
            others = list(cl)
            while pending:
                pending.sort(key=lambda c: min([dist(c, d) for d in others if d is not c] or [1e9]))
                src = pending.pop(0)
                dsts = [c for c in others if c is not src and (u["kind"] == "F" or not is_flash(c))]
                if not dsts:
                    continue
                res, w, via = connect_one(uid, net, src, dsts, True, bool(main["plane"]))
                label = "%s %s" % (net, ",".join("%s.%s" % (p.ref, p.num) for p in src["pads"][:3]))
                if not res:
                    fl.append(label)
                    continue
                stats["ok"] += 1
                for l, rows in res["rows"].items():
                    GL.OR(src["rows"][l], rows)
                tgt = dsts[res["dst"]] if res.get("dst") is not None else main
                BR.merge(tgt, src)
                others = [c for c in others if c is not src]
                cl[:] = others
            if u["kind"] == "L":
                u["ns_after"] = [clone(c) for c in cl]
        if fl:
            failed[uid] = fl
        done.add(uid)

    queue = deque(order)
    done = set()
    guard = [0]

    def drain():
        while queue and guard[0] < 600:
            guard[0] += 1
            uid = queue.popleft()
            if uid in done:
                continue
            dep = units[uid].get("dep")
            if dep and dep not in done:
                if dep not in queue:
                    queue.append(dep)
                queue.append(uid)
                continue
            run_unit(uid)
    drain()
    # second chance for units with open connections (copper moved around since); kept only if better
    for uid in list(failed):
        if uid not in failed:
            continue
        grp = closure({uid})
        sn = snap(grp)
        before = sum(len(failed.get(c, [])) for c in grp)
        for c in grp:
            rip(c)
        rerun(grp)
        if sum(len(failed.get(c, [])) for c in grp) >= before:
            restore(sn)
    fails = [f for fl in failed.values() for f in fl]
    stats["fail"] = len(fails)
    total = 0
    for uid, u in units.items():
        if u["kind"] == "S":
            total += 1
        elif u["kind"] == "F":
            total += sum(1 for c in templ[u["net"]] if is_flash(c))
        else:
            total += sum(1 for c in templ[u["net"]] if not is_flash(c)) - 1
    stats["ok"] = total - stats["fail"]
    # pads we boxed in: reserve an escape corridor (rip the units in the way, re-route them around it; kept only
    # if no connection is lost). The corridor is a no-go area for the rest of this script and stays free.
    for net, p, one in esc_pads:
        tag = "%s.%s(%s)" % (p.ref, p.num, net)
        if tag in boxed0:
            continue
        win = (p.pos[0] - 3.0, p.pos[1] - 3.0, p.pos[0] + 3.0, p.pos[1] + 3.0)
        apply_reservations(exclude=net)
        ok = BR.route(net, one, [BR.ring(win)], width=0.15, via=VIA, window=win, plane_goal=False, dry=True)[0] or \
            BR.route(net, one, [BR.ring(win)], width=0.15, via=(0.35, 0.15), window=win, plane_goal=False,
                     dry=True)[0]
        if ok:
            apply_reservations()
            continue
        sres = None
        for via in (VIA, (0.35, 0.15)):
            sres = BR.route(net, one, [BR.ring(win)], width=0.15, via=via, window=win, plane_goal=False,
                            soft=True)[0]
            if sres:
                break
        apply_reservations()
        if not sres:
            continue
        cs = BR.conflicts(net, sres["items"], 0.15, via)
        grp = closure(cs)
        sn = snap(grp)
        before = sum(len(failed.get(c, [])) for c in grp)
        for c in grp:
            rip(c)
        reserv.append((net,) + corridor(sres["items"], 0.15, via))
        apply_reservations()
        rerun(grp)
        if sum(len(failed.get(c, [])) for c in grp) > before:
            reserv.pop()
            apply_reservations()
            restore(sn)
            print("  escape for %s would cost a local connection: left boxed" % tag)
        else:
            print("  escape corridor reserved for %s (%d units re-routed)" % (tag, len(grp)))
    # pours we nibbled must stay in one piece: refill, compare outline counts / area with the start, and for a
    # pour that got split or lost copper, harden its band and re-route the units that went into it
    def pour_state():
        pcbnew.ZONE_FILLER(board).Fill(soft_zones)
        st = {}
        for z in soft_zones:
            fl = z.GetFilledPolysList(z.GetLayer())
            st[z.GetZoneName()] = (fl.OutlineCount(), fl.Area() / 1e12)
        return st
    soft_names = set(n for n, ents in BR.zone_rows.items() if any(l in GL.ROUTE_LAYERS for l, _, _ in ents))
    soft_zones = [z for z in to_fill if z.GetZoneName() in soft_names]
    for it in range(4):
        st = pour_state()
        bad = [n for n, (c, a) in st.items() if c > pour0[n][0] or
               a < pour0[n][1] - (max(2.0, 0.08 * pour0[n][1]) if n in soft_names else 0.10 * pour0[n][1])]
        if not bad:
            break
        for n in bad:
            print("  pour %s split / shrunk (%d->%d pieces, %.1f->%.1f mm2): hardening, re-routing" %
                  (n, pour0[n][0], st[n][0], pour0[n][1], st[n][1]))
            grp = closure(BR.units_in(n))
            BR.harden(n)
            for c in grp:
                rip(c)
            rerun(grp)
    # inner planes: final piece count (coarse raster) vs. the start
    vias_all = [(g[1], g[2], g[3], u["net"]) for u in BR.units.values() for g in u["geom"] if g[0] == "via"]
    if hasattr(BR, "coarse"):
        for name, e in BR.coarse.items():
            n1 = BR._pieces(e, [(x, y, sz) for x, y, sz, n in vias_all if n != e[0]])
            if n1 != e[4]:
                print("  WARNING inner plane %s: %d -> %d pieces" % (name, e[4], n1))
    fails = [f for fl in failed.values() for f in fl]
    stats["fail"] = len(fails)
    stats["ok"] = total - stats["fail"]
    boxed1 = escapes(per_net=lambda n: apply_reservations(exclude=n)) - boxed0
    apply_reservations()
    print("g_hubrails: escape pads newly boxed in by this script: %d %s" % (len(boxed1), " ".join(sorted(boxed1))))
    for z in to_fill:
        z.UnFill()
    print("g_hubrails: %d connections routed (%d rip-ups), %d failed, %.1fs" %
          (stats["ok"], stats["rip"], stats["fail"], time.time() - t0))
    if fails:
        print("  failed:", "; ".join(fails))
