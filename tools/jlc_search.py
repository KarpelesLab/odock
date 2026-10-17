"""Search the JLCPCB parts library (stock, basic/extended, price).
usage: python3 tools/jlc_search.py <keyword> [<keyword> ...]"""
import sys, json, urllib.request, time

def q(k, n=30):
    req = urllib.request.Request(
        "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList",
        data=json.dumps({"keyword": k, "currentPage": 1, "pageSize": n}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    for attempt in range(4):
        try:
            d = json.load(urllib.request.urlopen(req, timeout=30)); break
        except Exception:
            if attempt == 3: raise
            time.sleep(2 * (attempt + 1))
    L = (d.get("data") or {}).get("componentPageInfo", {}).get("list") or []
    print("==", k, len(L))
    for c in L:
        p = c.get("componentPrices") or []
        pr = p[0]["productPrice"] if p else None
        nb = c.get("noBuyReason") if c.get("isBuyComponent") == "0" else ""
        print(f'  {c["componentCode"]:<12} {c["componentModelEn"][:28]:<28} {(c.get("componentBrandEn") or "")[:14]:<14} '
              f'{(c.get("componentSpecificationEn") or "")[:22]:<22} stk={c["stockCount"]:<7} {c["componentLibraryType"]:<7} ${pr} '
              f'{("NOBUY:" + nb[:30]) if nb else ""} | {(c.get("describe") or "")[:80]}')

for k in sys.argv[1:]:
    q(k)
