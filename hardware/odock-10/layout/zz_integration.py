"""Cross-block placement fixes, applied after all block scripts.

- Thermocouple pads re-assigned to the block whose hot spot they measure (sensors.py labels):
  TP1202 TC_BB_L (L201, power), TP1204 TC_5V_L (L301, hubrails), TP1205 TC_HUB (U601, hubrails),
  TP1206 TC_LAPTOP_C (J501 VBUS, usbc), TP1208 TC_ORFET (Q303, hubrails).
- R908 (microSD CLK series termination, added after the block placement) at the U901 pin-29 escape via row.
- ("@", (x, y), side) targets an absolute point instead of a footprint; ("=", (x, y), side) places exactly there
  (courtyards still checked by apply_layout.py) (2026-10-03 routing fixes).
Each part goes to the nearest free spot (courtyard-clear, both sides checked for THT) around its target.
"""
import math
import pcbnew

MM = pcbnew.ToMM
REGION = []      # cross-block: no region check
REFS = ["TP1202", "TP1204", "TP1205", "TP1206", "TP1208", "R908"]

# ref -> (target ref, target pad or None for footprint centre, preferred side)
TARGETS = {
    "TP1202": ("@", (108.1, 84.45), "bottom"),  # under L201 (bottom), clear of the Q204 EP thermal-via area
    "TP1204": ("L301", None, "bottom"),
    "TP1205": ("U601", None, "bottom"),
    "TP1206": ("=", (143.7, 64.84), "top"),     # J501 VBUS side (between C501 and TP403), outside the laptop SS lane fan-in
    "TP1208": ("Q303", None, None),          # same side as Q303
    "R908":   ("=", (119.4, 114.9), "bottom"),  # µSD CLK source R, west of the U901 escape via row (CLK via 123.2,114.3);
                                                # fixed: the free-spot search treats the J901 socket outline (NPTH) as blocking
}


def _boxes(board, skip):
    out = []
    for f in board.GetFootprints():
        r = f.GetReference()
        if r in skip or r == "U1101":
            continue
        cy = f.GetCourtyard(pcbnew.B_CrtYd if f.IsFlipped() else pcbnew.F_CrtYd)
        b = cy.BBox() if cy.OutlineCount() else f.GetBoundingBox(False)
        tht = any(p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH) for p in f.Pads())
        out.append(("bottom" if f.IsFlipped() else "top", tht,
                    (MM(b.GetLeft()), MM(b.GetTop()), MM(b.GetRight()), MM(b.GetBottom()))))
    return out


def _free(boxes, side, l, t, r, b, edge):
    x0, y0, x1, y1 = edge
    if l < x0 + 0.5 or t < y0 + 0.5 or r > x1 - 0.5 or b > y1 - 0.5:
        return False
    for s, tht, (L, T, R, B) in boxes:
        if (s == side or tht) and not (r + 0.2 < L or l - 0.2 > R or b + 0.2 < T or t - 0.2 > B):
            return False
    return True


def place(board, h):
    eb = board.GetBoardEdgesBoundingBox()
    edge = (MM(eb.GetLeft()), MM(eb.GetTop()), MM(eb.GetRight()), MM(eb.GetBottom()))
    for ref, (tref, tpad, side) in TARGETS.items():
        if tref == "=":
            h.put(ref, tpad[0], tpad[1], 0, side)
            continue
        if tref == "@":
            tx, ty = tpad
            h.put(ref, tx, ty, 0, side)
            l, t, r, b = h.bbox(ref)
            w, hh = r - l, b - t
            boxes = _boxes(board, {ref})
            best = _search(boxes, side, tx, ty, w, hh, edge)
            _commit(h, ref, best, side, l, t, r, b, tref)
            continue
        tf = h.fp(tref)
        if side is None:
            side = "bottom" if tf.IsFlipped() else "top"
        if tpad:
            pads = [p for p in tf.Pads() if p.GetNumber() == tpad or p.GetPadName() == tpad]
            if not pads:   # pad given by function name: find the pad whose net ends with the net name of the pin
                pads = [p for p in tf.Pads() if "USD_CLK" in p.GetNetname() and not p.GetNetname().endswith("_S")]
            tx, ty = MM(pads[0].GetPosition().x), MM(pads[0].GetPosition().y)
        else:
            tx, ty = MM(tf.GetPosition().x), MM(tf.GetPosition().y)
        h.put(ref, tx, ty, 0, side)
        l, t, r, b = h.bbox(ref)
        w, hh = r - l, b - t
        boxes = _boxes(board, {ref})
        best = _search(boxes, side, tx, ty, w, hh, edge)
        _commit(h, ref, best, side, l, t, r, b, tref)


def _search(boxes, side, tx, ty, w, hh, edge):
    best = None
    for rad in range(0, 60):
        for k in range(-rad, rad + 1):
            for di, dj in ((k, -rad), (k, rad), (-rad, k), (rad, k)):
                cx, cy = tx + di * 0.5, ty + dj * 0.5
                if _free(boxes, side, cx - w / 2, cy - hh / 2, cx + w / 2, cy + hh / 2, edge):
                    d = math.hypot(di, dj)
                    if best is None or d < best[0]:
                        best = (d, cx, cy)
        if best:
            break
    return best


def _commit(h, ref, best, side, l, t, r, b, tref):
    if best:
        _, cx, cy = best
        # footprint origin may not be the bbox centre
        ox, oy = MM(h.fp(ref).GetPosition().x) - (l + r) / 2, MM(h.fp(ref).GetPosition().y) - (t + b) / 2
        h.put(ref, cx + ox, cy + oy, 0, side)
    else:
        print(f"zz_integration: no free spot for {ref} near {tref}")
