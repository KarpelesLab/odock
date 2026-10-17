"""Check every LCSC part used in the odock-10 schematics against JLCPCB stock.
Rule (2026-10-02): every part must be a JLC part with stock >= MIN_STOCK (default 5) — no consignment.
usage: python3 tools/bom_check.py [--min 5] [project_dir]"""
import sys, os, re, glob, json, time, urllib.request, argparse

def jlc(code):
    req = urllib.request.Request(
        "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList",
        data=json.dumps({"keyword": code, "currentPage": 1, "pageSize": 5}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    for attempt in range(5):
        try:
            d = json.load(urllib.request.urlopen(req, timeout=30)); break
        except Exception:
            if attempt == 4: raise
            time.sleep(2 * (attempt + 1))
    for c in (d.get("data") or {}).get("componentPageInfo", {}).get("list") or []:
        if c.get("componentCode") == code:
            return c
    return None

ap = argparse.ArgumentParser()
ap.add_argument("--min", type=int, default=5)
ap.add_argument("project", nargs="?", default=os.path.join(os.path.dirname(__file__), "..", "hardware", "odock-10"))
a = ap.parse_args()
uses = {}
missing = []
for f in sorted(glob.glob(os.path.join(a.project, "*.kicad_sch"))):
    t = open(f).read()
    for blk in re.split(r'\n\t\(symbol\n', t)[1:]:
        ref = re.search(r'\(property "Reference" "([^"]+)"', blk)
        if not ref or ref.group(1).startswith(("#", "TP")) or "(in_bom no)" in blk:
            continue
        l = re.search(r'\(property "LCSC" "([^"]*)"', blk)
        val = re.search(r'\(property "Value" "([^"]*)"', blk)
        if l and l.group(1).strip():
            uses.setdefault(l.group(1).strip(), []).append((ref.group(1), val.group(1) if val else "", os.path.basename(f)))
        else:
            missing.append((ref.group(1), val.group(1) if val else "", os.path.basename(f)))
bad = []
total = 0.0
ext = 0
for code, refs in sorted(uses.items()):
    c = jlc(code)
    stock = c.get("stockCount", 0) if c else None
    need = len(refs)
    ok = c is not None and stock >= max(a.min, need)
    name = c.get("componentModelEn") if c else "NOT FOUND"
    lt = c.get("componentLibraryType") if c else "-"
    print(f"{'OK ' if ok else 'BAD'} {code:<11} {name[:28]:<28} {lt:<7} stock={stock!s:<7} qty/board={need:<3} {', '.join(r for r, _, _ in refs[:6])}{' …' if need > 6 else ''}")
    if not ok:
        bad.append(code)
    if c:
        prices = c.get("componentPrices") or []
        if prices:
            total += float(prices[0]["productPrice"]) * need
        if c.get("componentLibraryType") != "base":
            ext += 1
for ref, val, f in missing:
    print(f"NOLCSC {ref:<8} {val:<20} {f}")
print(f"\n{len(uses)} unique parts, {len(bad)} failing, {len(missing)} without LCSC")
print(f"parts cost/board at qty-1 prices: ${total:.2f}; extended (non-basic) unique parts: {ext} (JLC fee ~${3 * ext} per order)")
sys.exit(1 if bad or missing else 0)
