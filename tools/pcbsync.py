"""pcbsync — update a KiCad board from its schematic (like "Update PCB from Schematic", scriptable).

- exports the netlist with kicad-cli, loads footprints from the project libraries
- adds missing footprints (placed via an optional placement hook), keeps the position/side/rotation of
  footprints already on the board, swaps footprints whose library footprint changed (in place)
- sets reference, value, schematic link (path) and pad nets; removes footprints whose symbol is gone
  (only those that were created from the schematic — mounting holes etc. without a path are kept)

Run with KiCad's bundled Python:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 \
      tools/pcbsync.py hardware/odock-10
"""
import os, sys, re, subprocess, tempfile, importlib.util
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
KICAD_CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
_tok = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))')


def parse(text):
    """Minimal s-expression parser (KiCad's Python 3.9 can't import schgen)."""
    pos, stack, out = 0, [], None
    while True:
        m = _tok.match(text, pos)
        if not m or m.end() == pos:
            break
        pos = m.end()
        if m.group(1):
            stack.append([])
        elif m.group(2):
            node = stack.pop()
            if stack:
                stack[-1].append(node)
            else:
                out = node
        elif m.group(3) is not None:
            stack[-1].append(m.group(3).replace('\\"', '"'))
        else:
            stack[-1].append(m.group(4))
    return out


def find(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def first(node, key):
    r = find(node, key)
    return r[0] if r else None

KICAD_FP = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"


def lib_path(project_dir, nick):
    if nick == "odock":
        return os.path.join(project_dir, "..", "lib", "odock.pretty")
    return os.path.join(KICAD_FP, f"{nick}.pretty")


def read_netlist(project_dir):
    proj = os.path.basename(os.path.normpath(project_dir))
    out = os.path.join(tempfile.mkdtemp(prefix="pcbsync-"), proj + ".net")
    subprocess.run([KICAD_CLI, "sch", "export", "netlist", "-o", out,
                    os.path.join(project_dir, proj + ".kicad_sch")], check=True, capture_output=True)
    tree = parse(open(out).read())
    comps = {}
    for c in find(first(tree, "components"), "comp"):
        ref = str(first(c, "ref")[1])
        fp = first(c, "footprint")
        sp = first(c, "sheetpath")
        props = {str(p[1][1]): (str(p[2][1]) if len(p) > 2 else "") for p in find(c, "property")}
        comps[ref] = dict(ref=ref, value=str(first(c, "value")[1]), fp=str(fp[1]) if fp else "",
                          sheet=str(first(sp, "names")[1]), path=str(first(sp, "tstamps")[1]) + str(first(c, "tstamps")[1]),
                          props=props)
    pins = {}
    for n in find(first(tree, "nets"), "net"):
        name = str(first(n, "name")[1])
        for node in find(n, "node"):
            pins[(str(first(node, "ref")[1]), str(first(node, "pin")[1]))] = name
    return comps, pins


def sync(project_dir, placer=None, refresh=()):
    proj = os.path.basename(os.path.normpath(project_dir))
    pcb_path = os.path.join(project_dir, proj + ".kicad_pcb")
    board = pcbnew.LoadBoard(pcb_path)
    comps, pins = read_netlist(project_dir)

    nets = {}
    def net(name):
        if name not in nets:
            ni = board.FindNet(name)
            if ni is None:
                ni = pcbnew.NETINFO_ITEM(board, name)
                board.Add(ni)
            nets[name] = ni
        return nets[name]

    existing = {fp.GetReference(): fp for fp in board.GetFootprints()}
    added, swapped, removed = [], [], []
    for ref, c in sorted(comps.items()):
        if not c["fp"] or ref.startswith("#"):
            continue
        nick, name = c["fp"].split(":", 1)
        fp = existing.get(ref)
        if fp is not None and (str(fp.GetFPID().GetUniStringLibId()) != c["fp"] or ref in refresh
                               or "*" in refresh):
            pos, rot, side = fp.GetPosition(), fp.GetOrientation(), fp.GetLayer()
            board.Remove(fp)
            fp = None
            swapped.append((ref, pos, rot, side))
        if fp is None:
            new = pcbnew.FootprintLoad(lib_path(project_dir, nick), name)
            if new is None:
                print(f"WARNING: footprint {c['fp']} for {ref} not found", file=sys.stderr)
                continue
            new.SetFPID(pcbnew.LIB_ID(nick, name))
            board.Add(new)
            sw = [s for s in swapped if s[0] == ref]
            if sw:
                _, pos, rot, side = sw[0]
                if side == pcbnew.B_Cu:
                    new.Flip(new.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
                new.SetPosition(pos); new.SetOrientation(rot)
            else:
                added.append(new)
            fp = new
        fp.SetReference(ref)
        fp.SetValue(c["value"])
        fp.SetPath(pcbnew.KIID_PATH(c["path"]))
        fp.SetDNP("dnp" in c["props"])
        fp.SetExcludedFromBOM("exclude_from_bom" in c["props"])
        for pad in fp.Pads():
            n = pins.get((ref, pad.GetNumber()))
            pad.SetNet(net(n) if n and not n.startswith("unconnected-") else board.FindNet(""))
    for ref, fp in existing.items():
        if ref not in comps and str(fp.GetPath().AsString()) not in ("", "/"):
            board.Remove(fp)
            removed.append(ref)
    if placer and added:
        placer(board, added, comps)
    board.BuildConnectivity()
    board.Save(pcb_path)
    print(f"pcbsync: {len(comps)} schematic parts, added {len(added)}, swapped {len(swapped)}, removed {len(removed)}")
    return board


if __name__ == "__main__":
    args = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith("--") and sys.argv[i - 1] != "--refresh"]
    pd = os.path.abspath(args[0] if args else os.path.join(HERE, "..", "hardware", "odock-10"))
    placer = None
    hook = os.path.join(pd, "placement.py")
    if os.path.exists(hook):
        spec = importlib.util.spec_from_file_location("placement", hook)
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        placer = mod.place
    refresh = ()
    if "--refresh" in sys.argv:
        refresh = tuple(sys.argv[sys.argv.index("--refresh") + 1].split(","))
    sync(pd, placer, refresh)
