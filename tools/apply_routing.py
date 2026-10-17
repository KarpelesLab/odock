"""Apply routing-as-code scripts (critical nets, pours) to a KiCad board.

Each hardware/<proj>/routing/<name>.py defines:
    NETS = [...]           # nets this script owns: their existing tracks/vias are deleted before place()
    GROUPED = True         # optional: everything drawn via the Router goes into group "route:<name>", and only that
                           # group is deleted on re-run (use this when sharing nets with other scripts; NETS = [])
    ZONES = [...]          # optional: zone names (strings) this script owns; same-named zones are replaced
    def route(board, r):   # draw with the Router helper `r`
Scripts run in file-name order, so later scripts (e.g. the autorouter output) can build on earlier ones.

  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 \
      tools/apply_routing.py hardware/odock-10 [--only a,b] [--out other.kicad_pcb] [--drc]
"""
import os, sys, glob, math, argparse, importlib.util, subprocess
import pcbnew

mm, MM = pcbnew.FromMM, pcbnew.ToMM
LAYERS = {"F.Cu": pcbnew.F_Cu, "In1.Cu": pcbnew.In1_Cu, "In2.Cu": pcbnew.In2_Cu,
          "In3.Cu": pcbnew.In3_Cu, "In4.Cu": pcbnew.In4_Cu, "B.Cu": pcbnew.B_Cu,
          "L1": pcbnew.F_Cu, "L2": pcbnew.In1_Cu, "L3": pcbnew.In2_Cu, "L4": pcbnew.In3_Cu,
          "L5": pcbnew.In4_Cu, "L6": pcbnew.B_Cu}


def V(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


def _offset_polyline(pts, d):
    """Offset a polyline by distance d (left = positive, in a y-down frame) with mitred joints."""
    out = []
    n = len(pts)
    def normal(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1.0
        return (-dy / L, dx / L)
    for i in range(n):
        if i == 0:
            nx, ny = normal(pts[0], pts[1])
            out.append((pts[0][0] + nx * d, pts[0][1] + ny * d))
        elif i == n - 1:
            nx, ny = normal(pts[-2], pts[-1])
            out.append((pts[-1][0] + nx * d, pts[-1][1] + ny * d))
        else:
            n1, n2 = normal(pts[i - 1], pts[i]), normal(pts[i], pts[i + 1])
            bx, by = n1[0] + n2[0], n1[1] + n2[1]
            bl = math.hypot(bx, by) or 1.0
            bx, by = bx / bl, by / bl
            cos_half = bx * n1[0] + by * n1[1]
            k = d / max(cos_half, 0.2)
            out.append((pts[i][0] + bx * k, pts[i][1] + by * k))
    return out


class Router:
    def __init__(self, board, group=None, fps=None):
        self.board = board
        self.group = group      # PCB_GROUP owning everything this script draws (see clear())
        # NB: KiCad's SWIG GetFootprints() can crash after items were removed from the board -> pass a cached dict
        self.fps = fps if fps is not None else {fp.GetReference(): fp for fp in board.GetFootprints()}
        self.nets = {}

    # ---- lookup
    def net(self, name):
        if name not in self.nets:
            ni = self.board.FindNet(name)
            if ni is None:  # hierarchical local nets are named "/Sheet/NET"
                cands = [n for n in self.board.GetNetsByName().keys() if str(n).split("/")[-1] == name]
                if len(cands) != 1:
                    raise KeyError(f"net {name!r}: {len(cands)} matches")
                ni = self.board.FindNet(str(cands[0]))
            self.nets[name] = ni
        return self.nets[name]

    def pad(self, ref, num):
        for p in self.fps[ref].Pads():
            if p.GetNumber() == str(num):
                v = p.GetPosition()
                return (MM(v.x), MM(v.y))
        raise KeyError(f"{ref}.{num}")

    def pad_of_net(self, ref, net):
        full = self.net(net).GetNetname()
        hits = [p for p in self.fps[ref].Pads() if p.GetNetname() == full]
        if not hits:
            raise KeyError(f"{ref} has no pad on {net}")
        v = hits[0].GetPosition()
        return (MM(v.x), MM(v.y))

    # ---- primitives
    def track(self, net, pts, layer="F.Cu", width=0.15):
        ni = self.net(net)
        for a, b in zip(pts, pts[1:]):
            if a == b:
                continue
            t = pcbnew.PCB_TRACK(self.board)
            t.SetStart(V(*a)); t.SetEnd(V(*b)); t.SetWidth(mm(width))
            t.SetLayer(LAYERS[layer]); t.SetNet(ni)
            self._add(t)

    def via(self, net, x, y, size=0.45, drill=0.25, top="F.Cu", bottom="B.Cu"):
        v = pcbnew.PCB_VIA(self.board)
        v.SetPosition(V(x, y)); v.SetWidth(mm(size)); v.SetDrill(mm(drill))
        if (top, bottom) == ("F.Cu", "B.Cu"):
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
        else:
            v.SetViaType(pcbnew.VIATYPE_BLIND_BURIED)
        v.SetLayerPair(LAYERS[top], LAYERS[bottom])
        v.SetNet(self.net(net))
        self._add(v)

    def pair(self, netp, netn, path, layer="F.Cu", width=0.10, gap=0.12, p_from=None, n_from=None,
             p_to=None, n_to=None):
        """Coupled differential pair along centreline `path` (list of (x,y)). P is on the LEFT of the
        travel direction (y-down frame). Optional p_from/n_from/p_to/n_to: (x,y) points (pads or vias)
        joined to the pair's ends with short fan-out segments on the same layer."""
        d = (width + gap) / 2
        P, N = _offset_polyline(path, d), _offset_polyline(path, -d)
        if p_from: P = [p_from] + P
        if n_from: N = [n_from] + N
        if p_to: P = P + [p_to]
        if n_to: N = N + [n_to]
        self.track(netp, P, layer, width)
        self.track(netn, N, layer, width)
        return P, N

    def pair_via(self, netp, netn, x, y, angle_deg=0, pitch=None, size=0.45, drill=0.25, gnd_vias=True,
                 top="F.Cu", bottom="B.Cu"):
        """Two signal vias for a pair centred at (x,y), side by side along `angle`, plus optional GND
        return vias beside them. Returns ((xp,yp),(xn,yn))."""
        pitch = pitch or (size + 0.25)
        a = math.radians(angle_deg)
        ux, uy = math.cos(a), math.sin(a)
        p = (x - ux * pitch / 2, y - uy * pitch / 2)
        n = (x + ux * pitch / 2, y + uy * pitch / 2)
        self.via(netp, *p, size, drill, top, bottom)
        self.via(netn, *n, size, drill, top, bottom)
        if gnd_vias:
            k = pitch / 2 + size + 0.2
            self.via("GND", x - ux * k, y - uy * k, size, drill)
            self.via("GND", x + ux * k, y + uy * k, size, drill)
        return p, n

    def zone(self, name, net, layer, poly, priority=0, clearance=0.25, min_width=0.2, thermal=True,
             fill_mode_solid=True):
        z = pcbnew.ZONE(self.board)
        z.SetZoneName(name)
        z.SetLayer(LAYERS[layer])
        if net:
            z.SetNet(self.net(net))
        z.SetAssignedPriority(priority)
        z.SetLocalClearance(mm(clearance))
        z.SetMinThickness(mm(min_width))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL if thermal else pcbnew.ZONE_CONNECTION_FULL)
        ol = z.Outline()
        ol.NewOutline()
        for x, y in poly:
            ol.Append(mm(x), mm(y))
        self._add(z)
        return z

    def _add(self, item):
        self.board.Add(item)
        if self.group is not None:
            self.group.AddItem(item)


def group_for(board, name):
    """Delete the previous run's items of script `name` (its 'route:<name>' group) and return a fresh group."""
    gname = "route:" + name
    for g in list(board.Groups()):
        if g.GetName() == gname:
            items = list(g.GetItems())
            g.RemoveAll()
            board.Remove(g)
            for it in items:
                board.Remove(it)
    g = pcbnew.PCB_GROUP(board)
    g.SetName(gname)
    board.Add(g)
    return g


def clear(board, nets, zones):
    full = set()
    for n in nets:
        ni = board.FindNet(n)
        if ni is None:
            for k in board.GetNetsByName().keys():
                if str(k).split("/")[-1] == n:
                    full.add(str(k))
        else:
            full.add(ni.GetNetname())
    for t in list(board.GetTracks()):
        if t.GetNetname() in full:
            board.Remove(t)
    for z in list(board.Zones()):
        if z.GetZoneName() in zones:
            board.Remove(z)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--only", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--drc", action="store_true")
    ap.add_argument("--no-fill", action="store_true")
    ap.add_argument("--pcb", default="", help="input board (default: the project's .kicad_pcb)")
    a = ap.parse_args()
    pd = os.path.abspath(a.project)
    proj = os.path.basename(pd)
    pcb = a.pcb or os.path.join(pd, proj + ".kicad_pcb")
    board = pcbnew.LoadBoard(pcb)
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    only = set(x for x in a.only.split(",") if x)
    for path in sorted(glob.glob(os.path.join(pd, "routing", "*.py"))):
        name = os.path.splitext(os.path.basename(path))[0]
        if name.startswith("_") or (only and name not in only):
            continue
        spec = importlib.util.spec_from_file_location("routing_" + name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        clear(board, getattr(mod, "NETS", []), set(getattr(mod, "ZONES", [])))
        grp = group_for(board, name) if getattr(mod, "GROUPED", False) else None
        mod.route(board, Router(board, grp, fps))
        print(f"applied routing/{name}.py")
    if not a.no_fill:
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    out = a.out or pcb
    board.Save(out)
    if a.drc:
        rpt = out + ".drc.rpt"
        subprocess.run(["/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli", "pcb", "drc",
                        "--severity-error", "-o", rpt, out], capture_output=True)
        print(open(rpt).read()[-3000:])


if __name__ == "__main__":
    main()
    sys.stdout.flush(); sys.stderr.flush()
    os._exit(0)   # skip SWIG destructors: KiCad segfaults at exit after items were removed from a board
