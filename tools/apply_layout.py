"""Apply placement-as-code scripts to a KiCad board.

Each hardware/<proj>/layout/<block>.py defines  place(board, h)  that positions ONLY its own footprints.
`h` is a helper (see Helper below). Scripts are applied in file-name order; afterwards a courtyard /
out-of-region check is printed. Run with KiCad's bundled Python:

  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 \
      tools/apply_layout.py hardware/odock-10 [--only block1,block2] [--out other.kicad_pcb]
"""
import os, sys, glob, importlib.util, argparse, math
import pcbnew

mm, MM = pcbnew.FromMM, pcbnew.ToMM


class Helper:
    def __init__(self, board):
        self.board = board
        self.fps = {fp.GetReference(): fp for fp in board.GetFootprints()}

    def fp(self, ref):
        return self.fps[ref]

    def put(self, ref, x, y, rot=0, side="top"):
        """Place footprint origin at (x, y) mm, rotation degrees, side 'top' | 'bottom'."""
        f = self.fps[ref]
        want_bot = side == "bottom"
        if f.IsFlipped() != want_bot:
            f.Flip(f.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
        f.SetOrientationDegrees(rot)
        f.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        return f

    def pad(self, ref, num):
        """Absolute (x, y) mm of a pad (after the footprint has been placed)."""
        for p in self.fps[ref].Pads():
            if p.GetNumber() == str(num):
                v = p.GetPosition()
                return MM(v.x), MM(v.y)
        raise KeyError(f"{ref} pad {num}")

    def pads_on_net(self, ref, net):
        return [(p.GetNumber(), MM(p.GetPosition().x), MM(p.GetPosition().y))
                for p in self.fps[ref].Pads() if p.GetNetname().split("/")[-1] == net]

    def bbox(self, ref):
        f = self.fps[ref]
        cy = f.GetCourtyard(pcbnew.B_CrtYd if f.IsFlipped() else pcbnew.F_CrtYd)
        b = cy.BBox() if cy.OutlineCount() else f.GetBoundingBox(False)
        return MM(b.GetLeft()), MM(b.GetTop()), MM(b.GetRight()), MM(b.GetBottom())

    def near(self, ref, ref_ic, pad, dx=0.0, dy=0.0, rot=0, side="top"):
        """Place `ref` at an offset from a pad of `ref_ic` (decoupling caps etc.)."""
        x, y = self.pad(ref_ic, pad)
        return self.put(ref, x + dx, y + dy, rot, side)


def overlaps(board):
    """Courtyard overlaps per side (rough, bbox-based) -> list of (refA, refB, side)."""
    items = []
    for f in board.GetFootprints():
        if f.GetReference().startswith(("H", "U1101")):   # holes; LCD outline is mechanical
            continue
        side = "bottom" if f.IsFlipped() else "top"
        cy = f.GetCourtyard(pcbnew.B_CrtYd if f.IsFlipped() else pcbnew.F_CrtYd)
        if not cy.OutlineCount():
            continue
        b = cy.BBox()
        tht = any(p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH for p in f.Pads())
        items.append((f.GetReference(), side, tht, b))
    out = []
    for i in range(len(items)):
        ra, sa, ta, ba = items[i]
        for j in range(i + 1, len(items)):
            rb, sb, tb, bb = items[j]
            if sa != sb and not (ta or tb):
                continue
            if ba.Intersects(bb):
                out.append((ra, rb, sa if sa == sb else "through"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--only", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    pd = os.path.abspath(a.project)
    proj = os.path.basename(pd)
    pcb = os.path.join(pd, proj + ".kicad_pcb")
    board = pcbnew.LoadBoard(pcb)
    h = Helper(board)
    only = set(x for x in a.only.split(",") if x)
    for path in sorted(glob.glob(os.path.join(pd, "layout", "*.py"))):
        name = os.path.splitext(os.path.basename(path))[0]
        if name.startswith("_") or (only and name not in only):
            continue
        spec = importlib.util.spec_from_file_location("layout_" + name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        before = {r: (f.GetPosition().x, f.GetPosition().y, f.GetOrientationDegrees(), f.IsFlipped())
                  for r, f in h.fps.items()}
        mod.place(board, h)
        own = set(getattr(mod, "REFS", []))
        rects = getattr(mod, "REGION", [])
        moved_foreign = [r for r, f in h.fps.items() if r not in own and
                         before[r] != (f.GetPosition().x, f.GetPosition().y, f.GetOrientationDegrees(), f.IsFlipped())]
        outside = []
        for r in own:
            if r not in h.fps:
                print(f"  {name}: REFS has unknown ref {r}")
                continue
            l, t, rr, b = h.bbox(r)
            if rects and not any(l >= x0 - 0.01 and t >= y0 - 0.01 and rr <= x1 + 0.01 and b <= y1 + 0.01
                                 for x0, y0, x1, y1 in rects):
                outside.append(r)
        print(f"applied layout/{name}.py: {len(own)} refs" +
              (f", OUTSIDE REGION: {' '.join(sorted(outside))}" if outside else "") +
              (f", MOVED NON-OWNED: {' '.join(sorted(moved_foreign))}" if moved_foreign else ""))
    ov = overlaps(board)
    for ra, rb, s in ov[:200]:
        print(f"OVERLAP {s:8} {ra} <-> {rb}")
    print(f"{len(ov)} courtyard overlaps")
    board.Save(a.out or pcb)


if __name__ == "__main__":
    main()
