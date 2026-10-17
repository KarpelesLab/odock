"""Regenerate every odock-10 sheet from its Python source and verify the netlist.
usage: python3 hardware/odock-10/sheets/build_all.py [sheet_module ...]"""
import sys, os, importlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, "..", "..", "..", "tools", "schgen")]
from schgen import verify
D = os.path.abspath(os.path.join(HERE, ".."))
mods = sys.argv[1:] or sorted(f[:-3] for f in os.listdir(HERE) if f.endswith(".py") and f != "build_all.py")
sheets = []
for m in mods:
    s = importlib.import_module(m).build(D)
    sheets.append(s)
    print(f"built {s.filename}: {len(s.parts)} parts")
errs = verify(D, sheets)
print("\n".join(errs) if errs else "netlist verify: OK")
sys.exit(1 if errs else 0)
