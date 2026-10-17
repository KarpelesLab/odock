"""Set electrical pin types on a symbol in hardware/lib/odock.kicad_sym (easyeda2kicad imports all pins as
'unspecified').  usage (python):  fix_pins("TMP1075DSGR", {"V+": "power_in", "GND": "power_in", "SDA": "bidirectional"})
Keys are pin names or numbers; values are KiCad pin types: input output bidirectional tri_state passive free
unspecified power_in power_out open_collector open_emitter no_connect.  Unlisted pins keep their type."""
import re, os, time, contextlib
LIB = os.path.join(os.path.dirname(__file__), "..", "..", "hardware/lib/odock.kicad_sym")

@contextlib.contextmanager
def lib_lock(lib=LIB):
    """Same lock directory as tools/import_lcsc.sh."""
    d = os.path.join(os.path.dirname(os.path.abspath(lib)), ".lock")
    while True:
        try:
            os.mkdir(d); break
        except FileExistsError:
            time.sleep(0.5)
    try:
        yield
    finally:
        os.rmdir(d)

def fix_pins(symbol, types, default=None, lib=LIB):
    with lib_lock(lib):
        _fix_pins(symbol, types, default, lib)

def _fix_pins(symbol, types, default, lib):
    text = open(lib).read()
    m = re.search(r'\n\t\(symbol "' + re.escape(symbol) + r'"\n', text)
    if not m:
        raise KeyError(symbol)
    start = m.start()
    nxt = re.search(r'\n\t\(symbol "', text[m.end():])
    end = m.end() + nxt.start() if nxt else len(text)
    block = text[start:end]
    def repl(pm):
        body = pm.group(0)
        name = re.search(r'\(name "([^"]*)"', body).group(1)
        num = re.search(r'\(number "([^"]*)"', body).group(1)
        t = types.get(num, types.get(name, default))
        return re.sub(r'^\(pin \w+', f'(pin {t}', body) if t else body
    block2 = re.sub(r'\(pin \w+ \w+.*?\(number "[^"]*"', repl, block, flags=re.S)
    open(lib, "w").write(text[:start] + block2 + text[end:])
