# schgen — schematics as code

odock-10 schematic sheets are generated from Python so they can be reviewed, diffed and verified.

- Sheet sources: `hardware/odock-10/sheets/<sheet>.py`, each exposing `build(project_dir) -> Sheet`.
- Build + verify everything: `python3 hardware/odock-10/sheets/build_all.py` (or pass module names).
  Verification exports the netlist with `kicad-cli` and checks every pin is on its intended net.
- Never hand-edit generated `.kicad_sch` files — edit the Python and rebuild.

## Writing a sheet

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "tools", "schgen"))
from schgen import Sheet

def build(D):
    s = Sheet(D, "sensors.kicad_sch", "odock-10 — Sensors", ref_base=1200)
    s.part("odock:TMP1075DSGR", "U", "TMP1075", at=(60.96, 50.8),
           pins={"SDA": "I2C_SYS_SDA", "SCL": "I2C_SYS_SCL", "ALERT": "TEMP_ALERT_N",
                 "V+": "+3V3", "GND": "GND", "A0": "GND", "A1": "GND", "A2": "GND", "EP": "GND"})
    s.c("100n", "+3V3", "GND", at=(91.44, 50.8), lcsc="C1525")
    s.r("10k", "I2C_SYS_SDA", "+3V3", size="0402", lcsc="C25744")
    s.flag("+3V3")           # PWR_FLAG, only on the sheet that sources the rail
    s.note("Design notes ...", at=(20.32, 200))
    s.build()
    return s
```

- `pins` maps pin **name or number** → net. Every pin must be mapped or listed in `nc=[...]`.
- Nets in `nets.py: GLOBAL_NETS` become global labels (inter-sheet). `GND` uses the power symbol.
  Everything else is a local label scoped to the sheet. Add new inter-sheet nets to `nets.py`.
- `ref_base`: sheet reference offset (power_input 100, power_laptop 200, power_rails 300, pd_pmg1 400,
  usbc_muxes 500, usb_hub 600, usb_a 700, ethernet 800, card_reader 900, mcu 1000, display_ui 1100,
  sensors 1200) so references never collide.
- `at` positions in mm on a 2.54 mm grid; place related parts near each other. Symbols are placed
  unrotated (rot=0); a short wire stub + label is added on each pin.
- Passives: `s.r()`, `s.c()` with KiCad standard footprints; set `lcsc=` to a JLC **basic** part
  whenever possible. Other parts: `s.part("Device:L", ...)`, `s.part("odock:<symbol>", ...)`.

## Adding parts from LCSC

```sh
tools/import_lcsc.sh C42166327 C43131250      # symbol + footprint + 3D into hardware/lib
```
Then set pin electrical types (easyeda imports them as unspecified):
```python
from fix_pins import fix_pins
fix_pins("TPS26750SRSMR", {"VBUS": "power_in", "GND": "power_in", "SDA": "bidirectional"}, default="passive")
```
Both tools take a lock on `hardware/lib/.lock`, so parallel runs are safe. Always check the imported
footprint against the datasheet land pattern before layout.
