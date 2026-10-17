"""odock-10 — Sensors sheet: 8x TMP1075 on I2C_SYS (0x48-0x4F, ALERT wire-OR to TEMP_ALERT_N), 2x NTC hot-spot
thermistors into RP2350 ADC (bias on the mcu sheet), and copper thermocouple pads at the hot spots.
Design notes: docs/design/sensors.md"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "tools", "schgen"))
from schgen import Sheet

# --- part numbers (LCSC) -------------------------------------------------------------------------
C_100N = "C1525"                   # basic 100 nF 0402
TMP = "C2870250"                   # TI TMP1075DSGR, WSON-8 2x2 (+-1 C max -40..110 C)
NTC = "C13564"                     # Murata NCP18XH103F03RB 10k 1 % B25/50 3380 K, 0603
TP_FP = "TestPoint:TestPoint_Pad_2.0x2.0mm"

# (address, A2 A1 A0, placement, layout hint)
SENSORS = [
    (0x48, "000", "BUCK-BOOST", "LM51770 power stage (power_laptop): between the FET bridge and the 10 uH XAL1010 inductor"),
    (0x49, "001", "5V BUCK", "LM5148 stage (power_rails): next to Q301 high-side FET / L301 (48 V corner hot spot)"),
    (0x4A, "010", "HUB", "USB7206C (usb_hub): on the bottom side under the hub EP via field, or top side <= 3 mm from the package"),
    (0x4B, "011", "PMG1/MUX", "PMG1-S3 BGA + TUSB1064 (pd_pmg1 / usbc_muxes): between the two"),
    (0x4C, "100", "LAPTOP-C", "laptop USB-C receptacle (DX07): at the VBUS/GND pins, inside the 5 A VBUS pour"),
    (0x4D, "101", "ETHERNET", "RTL8156BG / RJ45 (ethernet): between the QFN-56 and the magjack"),
    (0x4E, "110", "LCD", "under the 2.0in LCD module (display_ui), centre of its footprint, top side"),
    (0x4F, "111", "AMBIENT", "board edge / ambient: front-left corner near the SD socket, far from every heat source"),
]

# thermocouple / IR-reference pads (copper only, GND-tied for heat spreading; not in BOM)
TPADS = [
    ("TC_BB_FET", "buck-boost FETs (LM51770 bridge, hottest FET)"),
    ("TC_BB_L", "buck-boost inductor XAL1010"),
    ("TC_5V_FET", "LM5148 high-side FET Q301"),
    ("TC_5V_L", "LM5148 inductor L301"),
    ("TC_HUB", "USB7206C package top / EP"),
    ("TC_LAPTOP_C", "laptop USB-C VBUS pins"),
    ("TC_ETH", "RTL8156BG"),
    ("TC_ORFET", "LM74700 OR-FET Q303 / sink switch area (5 V path)"),
]


def _note(s, text, at, size=1.27):
    """Multi-line note as one text item per line (embedded newlines do not survive schgen's quoting)."""
    for i, line in enumerate(text.split("\n")):
        s.note(line, at=(at[0], round(at[1] + i * 2.54, 2)), size=size)


def build(D):
    s = Sheet(D, "sensors.kicad_sch", "odock-10 — Thermal sensors", ref_base=1200)

    # =============================================================================================
    # 1. TMP1075 x8
    # =============================================================================================
    _note(s, "1. TMP1075 x8 on I2C_SYS  (0x48-0x4F, A2..A0 strapped to GND/+3V3; ALERT open-drain wire-OR -> TEMP_ALERT_N)",
          (20.32, 15.24), 2.0)
    refs = []
    for i, (addr, bits, tag, where) in enumerate(SENSORS):
        col, row = i % 4, i // 4
        x, y = 40.64 + col * 93.98, 45.72 + row * 43.18
        a2, a1, a0 = ("+3V3" if b == "1" else "GND" for b in bits)
        u = s.part("odock:TMP1075DSGR", "U", "TMP1075", at=(x, y), lcsc=TMP,
                   pins={"V+": "+3V3", "GND": "GND", "EP": "GND", "SDA": "I2C_SYS_SDA", "SCL": "I2C_SYS_SCL",
                         "ALERT": "TEMP_ALERT_N", "A2": a2, "A1": a1, "A0": a0},
                   desc=f"I2C temp sensor 0x{addr:02X} - {tag}: {where}")
        s.c("100n", "+3V3", "GND", at=(x + 27.94, y), lcsc=C_100N, desc=f"{u.ref} decoupling, at V+")
        refs.append(u.ref)
        _note(s, f"{u.ref}  0x{addr:02X}  {tag}", (x - 15.24, y + 15.24), 1.5)
    _note(s, "Placement (reference -> location; layout must put each sensor here, EP soldered to a GND pour that touches the source):\n"
             + "\n".join(f"  {r}  0x{a:02X}  {t:<10} {w}" for r, (a, _, t, w) in zip(refs, SENSORS)),
          (20.32, 116.84))
    _note(s, "I2C_SYS pull-ups (2.2k) and the single TEMP_ALERT_N pull-up (10k, read by TCA9534 P2) live on the MCU sheet - none here.\n"
             "TMP1075 power-on default (config 00FFh): 12-bit continuous, comparator-mode ALERT active low, THIGH 80 C / TLOW 75 C. Firmware\n"
             "  reprograms per-sensor limits at boot (e.g. buck-boost 100 C, hub 95 C, LCD 60 C) and uses TEMP_ALERT_N as the\n"
             "  derating interrupt. To find the source: switch to interrupt mode (TM = 1) after boot and read the SMBus Alert Response\n"
             "  Address 0x0C (DS 7.3.2.6, free on I2C_SYS), or simply read all 8 temperatures (~2 ms at 400 kHz).\n"
             "Accuracy +-1 C max (-40..110 C); WSON EP is the thermal path - it measures the copper it sits on, not air.",
          (20.32, 144.78))

    # =============================================================================================
    # 2. NTC hot spots
    # =============================================================================================
    x0, y0 = 20.32, 167.64
    _note(s, "2. NTC HOT SPOTS  NCP18XH103F03RB 10k B3380 0603 to GND; 10k 1 % bias + 100 nF from ADC_AVDD on the MCU sheet", (x0, y0), 2.0)
    y = y0 + 20.32
    s.part("Device:Thermistor_NTC", "TH", "10k NTC", "Resistor_SMD:R_0603_1608Metric", at=(x0 + 10.16, y),
           pins={"1": "NTC_ADC0", "2": "GND"}, lcsc=NTC,
           desc="NTC_ADC0: buck-boost inductor (XAL1010) - touching the inductor's pad copper, GND end on the GND plane")
    s.part("Device:Thermistor_NTC", "TH", "10k NTC", "Resistor_SMD:R_0603_1608Metric", at=(x0 + 30.48, y),
           pins={"1": "NTC_ADC1", "2": "GND"}, lcsc=NTC,
           desc="NTC_ADC1: LM5148 high-side FET Q301 - on its drain/SW copper side, as close as clearance allows")
    _note(s, "TH1201 -> NTC_ADC0: buck-boost inductor hot spot.   TH1202 -> NTC_ADC1: LM5148 Q301 (high-side FET) hot spot.\n"
             "Ratiometric divider (bias to ADC_AVDD = ADC reference): V = AVDD x R_NTC / (10k + R_NTC); 25 C -> 0.50, 85 C -> 0.12,\n"
             "  100 C -> 0.08 x AVDD (R(100 C) ~ 0.97k). Route NTC_ADCx as a guarded trace away from SW nodes; the 100 nF at the ADC pin\n"
             "  (mcu sheet) filters switching noise. Thermistor GND end is the local power GND: measure at low fsw-phase-noise points.",
          (x0 + 45.72, y0 + 10.16))

    # =============================================================================================
    # 3. Thermocouple pads
    # =============================================================================================
    x0, y0 = 20.32, 205.74
    _note(s, "3. THERMOCOUPLE PADS  2x2 mm bare copper (TestPoint footprint, not in BOM), tied to GND at each hot spot", (x0, y0), 2.0)
    y = y0 + 20.32
    for i, (lab, where) in enumerate(TPADS):
        s.part("Connector:TestPoint", "TP", lab, TP_FP, at=(x0 + 10.16 + i * 22.86, y), pins={"1": "GND"},
               in_bom=False, desc=f"thermocouple pad: {where}")
    _note(s, "Bond a K-type bead with Kapton/thermal epoxy to the pad (or use it as an emissivity reference spot for an IR camera).\n"
             "Pads sit in the hot part's GND/thermal pour, <= 3 mm from the package, solder-mask opened. Locations:\n"
             + "\n".join(f"  TP{1201 + i}  {lab:<12} {w}" for i, (lab, w) in enumerate(TPADS)),
          (x0, y0 + 33.02))

    s.build()
    return s
