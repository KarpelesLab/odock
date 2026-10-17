"""schgen — generate KiCad schematic sheets from Python descriptions.

Each sheet is described in code (parts + pin->net maps). The generator places symbols, adds a short
wire stub + net label on every connected pin (local label, global label for nets listed in nets.py,
power symbol for GND), no-connect markers for unused pins, and embeds the library symbols.
`verify()` exports the netlist with kicad-cli and checks every pin landed on the intended net.

Coordinates are in mm (schematic, Y down). Keep `at` on the 2.54 mm grid.
"""
import os, re, uuid, json, subprocess, hashlib

KICAD = "/Applications/KiCad/KiCad.app"
KICAD_CLI = f"{KICAD}/Contents/MacOS/kicad-cli"
KICAD_SYMS = f"{KICAD}/Contents/SharedSupport/symbols"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LIBS = {"odock": os.path.join(ROOT, "hardware/lib/odock.kicad_sym")}
GRID = 1.27

# ---------------------------------------------------------------- s-expression parsing
_tok = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))')

class Q(str):
    """Quoted string atom."""

def parse(text):
    """Parse s-expr text -> nested lists; each list node gets (start, end) span in `spans`."""
    pos, stack, out = 0, [], None
    spans = {}
    starts = []
    n = len(text)
    while pos < n:
        m = _tok.match(text, pos)
        if not m or m.end() == pos:
            if text[pos:].strip() == "":
                break
            raise ValueError(f"parse error at {pos}: {text[pos:pos+40]!r}")
        pos = m.end()
        if m.group(1):
            stack.append([]); starts.append(m.start(1))
        elif m.group(2):
            node = stack.pop(); st = starts.pop()
            spans[id(node)] = (st, m.end(2))
            if stack:
                stack[-1].append(node)
            else:
                out = node
        elif m.group(3) is not None:
            stack[-1].append(Q(m.group(3).replace('\\"', '"').replace("\\\\", "\\")))
        else:
            stack[-1].append(m.group(4))
    return out, spans

def find(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]

def first(node, key):
    r = find(node, key)
    return r[0] if r else None

def q(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'

_NS = uuid.UUID("6f64656b-0000-4000-8000-736368676e30")   # fixed namespace for odock schgen
_ustate = {"sheet": None, "n": 0}

def U(key=None):
    """Deterministic UUIDs so rebuilds don't churn git or break schematic<->PCB links.
    Keyed UUIDs (symbols: sheet+ref+unit) are stable across edits; unkeyed ones follow generation order."""
    if _ustate["sheet"] is None:
        return str(uuid.uuid4())
    if key is None:
        _ustate["n"] += 1
        key = f"#{_ustate['n']}"
    return str(uuid.uuid5(_NS, f"{_ustate['sheet']}:{key}"))

def snap(v, g=GRID):
    return round(round(v / g) * g, 4)

# ---------------------------------------------------------------- library symbols
class LibSymbol:
    def __init__(self, lib, name, raw, pins, props):
        self.lib, self.name, self.raw, self.pins, self.props = lib, name, raw, pins, props

    @property
    def lib_id(self):
        return f"{self.lib}:{self.name}"

    def units(self):
        return sorted({p["unit"] for p in self.pins if p["unit"] > 0}) or [1]

_libcache = {}

def _load_lib(lib):
    if lib in _libcache:
        return _libcache[lib]
    path = LIBS.get(lib) or os.path.join(KICAD_SYMS, f"{lib}.kicad_sym")
    text = open(path, encoding="utf-8").read()
    tree, spans = parse(text)
    syms = {}
    for s in find(tree, "symbol"):
        syms[str(s[1])] = (s, text[spans[id(s)][0]:spans[id(s)][1]], spans)
    _libcache[lib] = (text, syms)
    return _libcache[lib]

def _pins_of(sym, name):
    pins = []
    for sub in find(sym, "symbol"):
        m = re.match(re.escape(name) + r"_(\d+)_(\d+)$", str(sub[1]))
        unit, style = (int(m.group(1)), int(m.group(2))) if m else (0, 1)
        if style not in (0, 1):
            continue
        for p in find(sub, "pin"):
            at = first(p, "at")
            pins.append(dict(etype=p[1], x=float(at[1]), y=float(at[2]), ang=float(at[3]) if len(at) > 3 else 0.0,
                             name=str(first(p, "name")[1]), number=str(first(p, "number")[1]), unit=unit))
    return pins

def load_symbol(lib_id):
    lib, name = lib_id.split(":", 1)
    text, syms = _load_lib(lib)
    if name not in syms:
        raise KeyError(f"symbol {lib_id} not found")
    sym, raw, spans = syms[name]
    props = {str(p[1]): str(p[2]) for p in find(sym, "property")}
    ext = first(sym, "extends")
    if ext:
        parent = load_symbol(f"{lib}:{ext[1]}")
        body = parent.raw
        ptree, pspans = parse(body)
        child_props = "".join("\n\t\t" + raw[spans[id(p)][0]:spans[id(p)][1]] for p in find(sym, "property"))
        # rebuild: header + child props + parent non-property children
        pchildren = []
        for c in ptree[2:]:
            if isinstance(c, list) and c[0] == "property":
                continue
            if isinstance(c, list):
                s0, e0 = pspans[id(c)]
                pchildren.append(body[s0:e0].replace(f'"{parent.name}_', f'"{name}_'))
        raw = f'(symbol "{name}"' + child_props + "".join("\n\t\t" + c for c in pchildren) + ")"
        pins = parent.pins
        props = {**parent.props, **props}
    else:
        pins = _pins_of(sym, name)
    return LibSymbol(lib, name, raw, pins, props)

def embed(sym):
    """lib_symbols copy: top-level name prefixed with library nickname."""
    return sym.raw.replace(f'(symbol "{sym.name}"', f'(symbol "{sym.lib_id}"', 1)

# ---------------------------------------------------------------- shared nets
def _shared_nets():
    p = os.path.join(os.path.dirname(__file__), "nets.py")
    ns = {}
    exec(open(p).read(), ns)
    return set(ns["GLOBAL_NETS"]), set(ns.get("POWER_SYMBOL_NETS", ["GND"]))

# ---------------------------------------------------------------- sheet
class Part:
    def __init__(self, sheet, sym, ref, value, fp, at, pins, nc, unit, props, rot):
        self.sheet, self.sym, self.ref, self.value, self.fp = sheet, sym, ref, value, fp
        self.at, self.pins, self.nc, self.unit, self.props, self.rot = at, pins, nc, unit, props, rot

class Sheet:
    def __init__(self, project_dir, filename, title, ref_base=0, paper="A3"):
        self.dir, self.filename, self.title, self.paper = project_dir, filename, title, paper
        self.ref_base = ref_base
        self.parts, self.notes = [], []
        self.counters = {}
        self.globals, self.power_nets = _shared_nets()
        self._auto = [20.32, 30.48]

    # -- references
    def _ref(self, prefix):
        n = self.counters.get(prefix, 0) + 1
        self.counters[prefix] = n
        return f"{prefix}{self.ref_base + n}"

    def part(self, lib_id, prefix, value, fp="", at=None, pins=None, nc=(), unit=None, lcsc=None, mpn=None,
             datasheet="", desc="", rot=0, ref=None, dnp=False, extra=None, in_bom=True):
        """Add a part. pins: {pin name or number: net}. Pins with the same name all get that net.
        Every pin must be mapped or listed in nc (by name or number)."""
        sym = load_symbol(lib_id)
        if at is None:
            at = tuple(self._auto)
            self._auto[0] += 15.24
            if self._auto[0] > 380:
                self._auto = [20.32, self._auto[1] + 20.32]
        fp = fp or sym.props.get("Footprint", "")
        lcsc = lcsc or sym.props.get("LCSC Part") or sym.props.get("LCSC")
        mpn = mpn or sym.props.get("MPN")
        props = {"Datasheet": datasheet or sym.props.get("Datasheet", ""), "Description": desc or sym.props.get("Description", "")}
        if lcsc: props["LCSC"] = lcsc
        if mpn: props["MPN"] = mpn
        if extra: props.update(extra)
        p = Part(self, sym, ref or self._ref(prefix), value, fp, (snap(at[0], 2.54), snap(at[1], 2.54)),
                 dict(pins or {}), set(map(str, nc)), unit, props, rot)
        p.dnp = dnp
        p.in_bom = in_bom
        self.parts.append(p)
        return p

    # passives ---------------------------------------------------------
    def r(self, value, a, b, size="0402", at=None, lcsc=None, **kw):
        return self.part("Device:R", "R", value, f"Resistor_SMD:R_{size}_{_metric(size)}Metric", at,
                         {"1": a, "2": b}, lcsc=lcsc, **kw)

    def c(self, value, a, b, size="0402", at=None, lcsc=None, **kw):
        return self.part("Device:C", "C", value, f"Capacitor_SMD:C_{size}_{_metric(size)}Metric", at,
                         {"1": a, "2": b}, lcsc=lcsc, **kw)

    def flag(self, net, at=None):
        """PWR_FLAG on a net (put one on each power net, on the sheet that sources it)."""
        return self.part("power:PWR_FLAG", "#FLG", "PWR_FLAG", at=at, pins={"1": net})

    def note(self, text, at=(20.32, 15.24), size=1.27):
        self.notes.append((text, at, size))

    # -- generation
    def _pin_nets(self, part):
        """-> list of (pin, net or None for NC)."""
        out = []
        units = [part.unit] if part.unit else part.sym.units()
        for pin in part.sym.pins:
            if pin["unit"] not in (0, *units):
                continue
            key = None
            for k in (pin["number"], pin["name"]):
                if k in part.pins:
                    key = k; break
            if key is not None:
                out.append((pin, part.pins[key]))
            elif pin["number"] in part.nc or pin["name"] in part.nc:
                out.append((pin, None))
            else:
                raise ValueError(f"{part.ref} ({part.sym.lib_id}): pin {pin['number']} '{pin['name']}' not mapped")
        used = {p["number"] for p, _ in out} | {p["name"] for p, _ in out}
        for k in part.pins:
            if k not in used:
                raise ValueError(f"{part.ref}: mapped pin '{k}' does not exist on {part.sym.lib_id}")
        return out

    def build(self):
        path = os.path.join(self.dir, self.filename)
        old_uuid = None
        if os.path.exists(path):
            m = re.search(r'\(uuid "([^"]+)"\)', open(path).read())
            old_uuid = m.group(1) if m else None
        root_path = os.path.join(self.dir, os.path.basename(self.dir) + ".kicad_sch")
        rt = open(root_path).read()
        root_uuid = re.search(r'\(uuid "([^"]+)"\)', rt).group(1)
        m = re.search(r'\(sheet\b.*?\(uuid "([^"]+)"\).*?"Sheetfile" "' + re.escape(self.filename) + '"', rt, re.S)
        # the regex above may span sheets; take the last uuid before the Sheetfile match
        block = rt[:m.end()]
        sheet_uuid = re.findall(r'\(sheet\b(?:(?!\(sheet\b).)*?\(uuid "([^"]+)"\)', block, re.S)[-1]
        project = os.path.basename(self.dir)
        inst_path = f"/{root_uuid}/{sheet_uuid}"

        _ustate["sheet"], _ustate["n"] = self.filename, 0
        out = [f'(kicad_sch\n\t(version 20260306)\n\t(generator "eeschema")\n\t(generator_version "10.0")\n'
               f'\t(uuid "{old_uuid or U()}")\n\t(paper "{self.paper}")\n'
               f'\t(title_block\n\t\t(title {q(self.title)})\n\t\t(rev "A")\n\t\t(company "odock")\n'
               f'\t\t(comment 1 "Generated by tools/schgen — edit the Python source, not this file")\n\t)\n']
        syms = {}
        for p in self.parts:
            syms[p.sym.lib_id] = p.sym
        need_gnd = any(n in self.power_nets for p in self.parts for n in p.pins.values())
        pwr_syms = {}
        for n in sorted(self.power_nets):
            pwr_syms[n] = load_symbol(f"power:{n}")
        out.append("\t(lib_symbols\n")
        for s in list(syms.values()) + ([*pwr_syms.values()] if need_gnd else []):
            out.append("\t\t" + embed(s).replace("\n", "\n\t\t") + "\n")
        out.append("\t)\n")

        body = []
        pwr_n = [0]
        expected = {}
        for p in self.parts:
            ox, oy = p.at
            units = [p.unit] if p.unit else p.sym.units()
            pin_nets = self._pin_nets(p)
            for ui, unit in enumerate(units):
                ux, uy = ox + ui * 50.8, oy
                upins = [pn for pn, _ in pin_nets if pn["unit"] in (0, unit)]
                ys = [uy - pn["y"] for pn in upins] or [uy]
                if upins and all(int(pn["ang"]) % 180 == 90 for pn in upins):
                    rpos, vpos = (ux + 2.54, uy - 1.27), (ux + 2.54, uy + 1.27)   # vertical 2-pin parts: text right
                else:
                    rpos, vpos = (ux, min(ys) - 3.81), (ux, max(ys) + 3.81)
                props = [("Reference", p.ref, rpos, False), ("Value", p.value, vpos, False),
                         ("Footprint", p.fp, (ux, uy), True)]
                props += [(k, v, (ux, uy), True) for k, v in p.props.items()]
                ptxt = "".join(
                    f'\t\t(property {q(k)} {q(v)}\n\t\t\t(at {x:.2f} {y:.2f} 0)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n'
                    + ("\t\t\t\t(hide yes)\n" if hide else "") + "\t\t\t)\n\t\t)\n" for k, v, (x, y), hide in props)
                pin_uuids = "".join(f'\t\t(pin {q(pin["number"])}\n\t\t\t(uuid "{U(f"pin:{p.ref}:{pin["number"]}")}")\n\t\t)\n'
                                    for pin, _ in pin_nets if pin["unit"] in (0, unit))
                body.append(
                    f'\t(symbol\n\t\t(lib_id {q(p.sym.lib_id)})\n\t\t(at {ux:.2f} {uy:.2f} {p.rot})\n\t\t(unit {unit})\n'
                    f'\t\t(exclude_from_sim no)\n\t\t(in_bom {"yes" if p.in_bom else "no"})\n\t\t(on_board yes)\n\t\t(dnp {"yes" if p.dnp else "no"})\n'
                    f'\t\t(uuid "{U(f"sym:{p.ref}:{unit}")}")\n{ptxt}{pin_uuids}'
                    f'\t\t(instances\n\t\t\t(project {q(project)}\n\t\t\t\t(path {q(inst_path)}\n\t\t\t\t\t(reference {q(p.ref)})\n'
                    f'\t\t\t\t\t(unit {unit})\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n')
                for pin, net in pin_nets:
                    if pin["unit"] not in (0, unit):
                        continue
                    if pin["unit"] == 0 and ui > 0:
                        continue
                    px, py, ang = _xform(pin["x"], pin["y"], pin["ang"], p.rot)
                    cx, cy = snap(ux + px), snap(uy - py)
                    expected[(p.ref, pin["number"])] = net
                    if net is None:
                        body.append(f'\t(no_connect\n\t\t(at {cx:.2f} {cy:.2f})\n\t\t(uuid "{U()}")\n\t)\n')
                        continue
                    dx, dy = _outward(ang)
                    L = 2.54
                    ex, ey = snap(cx + dx * L), snap(cy + dy * L)
                    body.append(f'\t(wire\n\t\t(pts\n\t\t\t(xy {cx:.2f} {cy:.2f}) (xy {ex:.2f} {ey:.2f})\n\t\t)\n'
                                f'\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n\t\t(uuid "{U()}")\n\t)\n')
                    body.append(self._label(net, ex, ey, dx, dy, pwr_syms, pwr_n, project, inst_path))
        for text, (x, y), size in self.notes:
            body.append(f'\t(text {q(text)}\n\t\t(exclude_from_sim no)\n\t\t(at {x} {y} 0)\n\t\t(effects\n\t\t\t(font\n'
                        f'\t\t\t\t(size {size} {size})\n\t\t\t)\n\t\t\t(justify left top)\n\t\t)\n\t\t(uuid "{U()}")\n\t)\n')
        out += body
        out.append(")\n")
        open(path, "w").write("".join(out))
        self.expected = expected
        return path

    def _label(self, net, x, y, dx, dy, pwr_syms, pwr_n, project, inst_path):
        ang = {(-1, 0): 180, (1, 0): 0, (0, 1): 270, (0, -1): 90}[(dx, dy)]
        if net in self.power_nets:
            pwr_n[0] += 1
            ref = f"#PWR{self.ref_base + pwr_n[0]:04d}"
            s = pwr_syms[net]
            rot = {270: 0, 0: 90, 90: 180, 180: 270}[ang]  # GND symbol body points along the stub direction
            return (f'\t(symbol\n\t\t(lib_id {q(s.lib_id)})\n\t\t(at {x:.2f} {y:.2f} {rot})\n\t\t(unit 1)\n'
                    f'\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(dnp no)\n\t\t(uuid "{U()}")\n'
                    f'\t\t(property "Reference" {q(ref)}\n\t\t\t(at {x:.2f} {y:.2f} 0)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)\n'
                    f'\t\t(property "Value" {q(net)}\n\t\t\t(at {x:.2f} {y + 3.81:.2f} 0)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)\n'
                    f'\t\t(property "Footprint" ""\n\t\t\t(at {x:.2f} {y:.2f} 0)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)\n'
                    f'\t\t(pin "1"\n\t\t\t(uuid "{U()}")\n\t\t)\n'
                    f'\t\t(instances\n\t\t\t(project {q(project)}\n\t\t\t\t(path {q(inst_path)}\n\t\t\t\t\t(reference {q(ref)})\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n')
        just = "left" if ang in (0, 90) else "right"
        if net in self.globals:
            return (f'\t(global_label {q(net)}\n\t\t(shape passive)\n\t\t(at {x:.2f} {y:.2f} {ang})\n\t\t(fields_autoplaced yes)\n'
                    f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify {just})\n\t\t)\n\t\t(uuid "{U()}")\n'
                    f'\t\t(property "Intersheetrefs" "${{INTERSHEET_REFS}}"\n\t\t\t(at {x:.2f} {y:.2f} 0)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)\n\t)\n')
        return (f'\t(label {q(net)}\n\t\t(at {x:.2f} {y:.2f} {ang})\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n'
                f'\t\t\t(justify {just} bottom)\n\t\t)\n\t\t(uuid "{U()}")\n\t)\n')

def _metric(size):
    return {"0201": "0603", "0402": "1005", "0603": "1608", "0805": "2012", "1206": "3216", "1210": "3225",
            "1812": "4532", "2010": "5025", "2512": "6332"}[size]

def _xform(x, y, ang, rot):
    """Rotate pin position/angle by symbol rotation (degrees CCW, symbol coords).
    Only rot=0 is verified; check with verify() if you use other rotations."""
    import math
    r = math.radians(rot)
    xr = x * math.cos(r) - y * math.sin(r)
    yr = x * math.sin(r) + y * math.cos(r)
    return xr, yr, (ang + rot) % 360

def _outward(ang):
    """Pin angle (direction pin->body, symbol coords) -> outward unit vector in schematic coords (Y down)."""
    a = int(round(ang)) % 360
    return {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[a]

# ---------------------------------------------------------------- verification
def verify(project_dir, sheets):
    """Export netlist via kicad-cli and check each sheet's expected pin->net assignments."""
    proj = os.path.basename(project_dir)
    import tempfile
    net_path = os.path.join(tempfile.mkdtemp(prefix="schgen-"), f"{proj}.net")
    subprocess.run([KICAD_CLI, "sch", "export", "netlist", "-o", net_path, os.path.join(project_dir, proj + ".kicad_sch")],
                   check=True, capture_output=True)
    tree, _ = parse(open(net_path).read())
    actual = {}
    for net in find(first(tree, "nets"), "net"):
        name = str(first(net, "name")[1])
        for node in find(net, "node"):
            actual[(str(first(node, "ref")[1]), str(first(node, "pin")[1]))] = name
    errors = []
    for s in sheets:
        for (ref, pin), net in s.expected.items():
            if ref.startswith("#"):      # PWR_FLAG / power symbols are not in the netlist
                continue
            got = actual.get((ref, pin))
            if net is None:
                if got and not got.startswith("unconnected-"):
                    errors.append(f"{ref}.{pin}: expected NC, got {got}")
                continue
            if got is None:
                errors.append(f"{ref}.{pin}: expected {net}, not in netlist")
            elif got.split("/")[-1] != net:
                errors.append(f"{ref}.{pin}: expected {net}, got {got}")
    return errors
