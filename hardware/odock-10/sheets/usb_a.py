"""odock-10 — USB-A sheet: 2x USB 3.2 Gen2 (10 Gbps) Type-A receptacles (hub ports 2/3) with TPS2553 current-limited
VBUS switches (enable = hub PRT_CTL OR RP2350 force), 30 mOhm + INA180A2 per-port current sense, 0.25 pF ESD on SS lines,
USBLC6 on D+/D-, 150 uF VBUS bulk per port.
Design notes: docs/design/usb_a.md"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "tools", "schgen"))
from schgen import Sheet

# --- part numbers (LCSC) -------------------------------------------------------------------------
# basic parts
R_1K, R_15K, R_100K = "C11702", "C25756", "C25741"          # 0402 1 %
R_4K7 = "C25900"                                             # 0402 1 % basic
C_100N, C_10U_0805 = "C1525", "C15850"                       # 0402 16 V X7R; 0805 25 V X5R
# extended parts
CONN = "C5429382"            # Amphenol GSB4111312HR, USB 3.2 Gen2 Type-A, right angle THT
SWITCH = "C55266"            # TI TPS2553DBVR, adjustable current-limited switch, EN active high
CSA = "C192764"              # TI INA180A2IDBVR, gain 50 V/V current-sense amp
OR_GATE = "C10096"           # TI SN74LVC1G32DBVR single OR (same part as power_input)
ESD_HS = "C106794"           # TI TPD4E02B04DQAR 0.25 pF 4-ch, 10 Gbps (same as usbc_muxes)
ESD_USB2 = "C7519"           # ST USBLC6-2SC6, D+/D- + VBUS clamp
R_SHUNT = "C858599"          # Yageo PE0805FRF470R03L 30 mOhm 1 % 0805 (0.5 W)
C_150U = "C347559"           # Panasonic 10TPF150ML POSCAP 150 uF 10 V 2917 (low ESR)

# port -> (hub port, PRT_CTL pin) for notes
PORTS = {1: ("hub port 2", "PRT_CTL2/PF16"), 2: ("hub port 3", "PRT_CTL3/PF15")}


def _note(s, text, at, size=1.27):
    """Multi-line note as one text item per line (embedded newlines do not survive schgen's quoting)."""
    for i, line in enumerate(text.split("\n")):
        s.note(line, at=(at[0], round(at[1] + i * 2.54, 2)), size=size)


def _esd4(s, at, ch, desc):
    """TPD4E02B04: IO1..IO4 + straight-through NC pads (10<->1, 9<->2, 7<->4, 6<->5) on the same nets."""
    io = {"1": ch[0], "2": ch[1], "4": ch[2], "5": ch[3]}
    pins = {"GND": "GND"}
    for p, thru in (("1", "10"), ("2", "9"), ("4", "7"), ("5", "6")):
        pins[p] = io[p]; pins[thru] = io[p]
    return s.part("odock:TPD4E02B04DQAR", "D", "TPD4E02B04", at=at, pins=pins, lcsc=ESD_HS, desc=desc)


def _port(s, n, x0, y0):
    P = f"USBA{n}"
    vbus = f"+5V_USBA{n}"
    hub, ctl = PORTS[n]
    _note(s, f"{n}. USB-A #{n}  ({hub}, {ctl})", (x0, y0), 2.0)

    # ---------------- connector + ESD + bulk
    y = y0 + 25.4
    s.part("odock:GSB4111312HR", "J", "GSB4111312HR", at=(x0 + 15.24, y),
           pins={"VBUS": vbus, "D-": f"{P}_DN", "D+": f"{P}_DP", "GND": "GND", "GND_DRAIN": "GND",
                 "SSRX-": f"{P}_SS_RXN", "SSRX+": f"{P}_SS_RXP", "SSTX-": f"{P}_SS_TXN", "SSTX+": f"{P}_SS_TXP",
                 "EH": "GND"},
           lcsc=CONN, desc="USB 3.2 Gen2 Type-A receptacle. SSTX = host(hub) transmit, SSRX = host receive")
    _esd4(s, (x0 + 66.04, y), (f"{P}_SS_TXP", f"{P}_SS_TXN", f"{P}_SS_RXP", f"{P}_SS_RXN"),
          f"ESD 10G, USB-A #{n} SS lines, at the connector")
    s.part("odock:USBLC6-2SC6", "D", "USBLC6-2SC6", at=(x0 + 132.08, y),
           pins={"1": f"{P}_DP", "6": f"{P}_DP", "3": f"{P}_DN", "4": f"{P}_DN", "2": "GND", "5": vbus},
           lcsc=ESD_USB2, desc=f"ESD USB2 D+/D- + VBUS, USB-A #{n} (flow-through 1-6 / 3-4)")
    y = y0 + 50.8
    s.part("Device:C_Polarized", "C", "150u/10V", "Capacitor_Tantalum_SMD:CP_EIA-7343-31_Kemet-D", at=(x0 + 10.16, y),
           pins={"1": vbus, "2": "GND"}, lcsc=C_150U, desc="VBUS bulk >= 120 uF per downstream port (USB 2.0 7.2.4.1)")
    s.c("10u", vbus, "GND", size="0805", at=(x0 + 22.86, y), lcsc=C_10U_0805, desc="VBUS ceramic at the connector")
    s.c("100n", vbus, "GND", at=(x0 + 33.02, y), lcsc=C_100N, desc="VBUS HF decoupling at the connector")

    # ---------------- power switch + enable OR
    y = y0 + 78.74
    s.part("odock:TPS2553DBVR", "U", "TPS2553", at=(x0 + 15.24, y),
           pins={"IN": f"{P}_SW_IN", "GND": "GND", "EN": f"{P}_EN", "/FAULT": f"{P}_OCS_N", "ILIM": f"{P}_ILIM",
                 "OUT": vbus},
           lcsc=SWITCH, desc="Current-limited switch, RILIM 15k -> 1.61/1.70/1.80 A (min/typ/max)")
    s.r("15k", f"{P}_ILIM", "GND", at=(x0 + 55.88, y), lcsc=R_15K, desc="RILIM 15.0k 1 %: ILIM 1.61 A min (> 1.5 A DCP)")
    s.c("10u", f"{P}_SW_IN", "GND", size="0805", at=(x0 + 66.04, y), lcsc=C_10U_0805, desc="Switch input cap")
    s.c("100n", f"{P}_SW_IN", "GND", at=(x0 + 76.2, y), lcsc=C_100N, desc="Switch input HF cap, at IN pin")
    s.part("74xGxx:74LVC1G32", "U", "SN74LVC1G32", "Package_TO_SOT_SMD:SOT-23-5", at=(x0 + 124.46, y),
           pins={"1": f"{P}_PWR_EN", "2": f"{P}_FORCE_EN", "4": f"{P}_EN", "5": "+3V3", "3": "GND"},
           lcsc=OR_GATE, desc="EN = hub PRT_CTL (high = port on) OR RP2350 force")
    y = y0 + 101.6
    s.c("100n", "+3V3", "GND", at=(x0 + 109.22, y), lcsc=C_100N, desc="OR gate decoupling")
    s.r("4.7k", f"{P}_FORCE_EN", "GND", at=(x0 + 124.46, y), lcsc=R_4K7,
        desc="FORCE_EN default off (RP2350 in reset / BOOTSEL); 4.7k overrides RP2350-E9 pad latch (~2.2 V)")
    s.r("100k", f"{P}_EN", "GND", at=(x0 + 139.7, y), lcsc=R_100K,
        desc="Switch off while +3V3 is not up yet (OR gate unpowered, Ioff)")

    # ---------------- current sense
    y = y0 + 101.6
    s.r("30m", "+5V", f"{P}_SW_IN", size="0805", at=(x0 + 10.16, y), lcsc=R_SHUNT,
        desc="30 mOhm 1 % 0805 0.5 W shunt; Kelvin-route INA180 IN+/IN- from its pads")
    y = y0 + 124.46
    s.part("odock:INA180A2IDBVR", "U", "INA180A2", at=(x0 + 15.24, y),
           pins={"IN+": "+5V", "IN-": f"{P}_SW_IN", "VS": "+3V3", "GND": "GND", "OUT": f"{P}_ISNS"},
           lcsc=CSA, desc="Gain 50: 1.5 V/A, 0-2.2 A -> 0-3.3 V")
    s.c("100n", "+3V3", "GND", at=(x0 + 45.72, y), lcsc=C_100N, desc="INA180 VS decoupling")
    s.r("1k", f"{P}_ISNS", f"{P}_ISENSE", at=(x0 + 60.96, y), lcsc=R_1K, desc="ADC RC filter / isolation")
    s.c("100n", f"{P}_ISENSE", "GND", at=(x0 + 76.2, y), lcsc=C_100N, desc="ADC RC filter, fc = 1.6 kHz")


def build(D):
    s = Sheet(D, "usb_a.kicad_sch", "odock-10 — USB-A 10 Gbps ports (2x), port power, current sense", ref_base=700)

    _note(s, "USB-A 10G PORTS  2x Amphenol GSB4111312HR (USB 3.2 Gen2), hub ports 2/3 of the USB7206C (usb_hub sheet)",
          (20.32, 15.24), 2.0)
    _port(s, 1, 20.32, 25.4)
    _port(s, 2, 220.98, 25.4)

    _note(s, "NOTES\n"
             "AC coupling (USB 3.2 6.2.x: the cap belongs to the TRANSMITTER's board): hub TX -> 220 nF on usb_hub -> USBAx_SS_TX* -> connector\n"
             "  SSTX (pins 9/8). Device TX caps are inside the plugged device -> connector SSRX (pins 6/5) -> USBAx_SS_RX* -> hub RX with NO cap here.\n"
             "  Connector pin names are the USB-IF host-side names (StdA_SSTX = host transmits): hub TX goes to SSTX, not SSRX.\n"
             "Port power: TPS2553 EN = USBAx_PWR_EN (hub PRT_CTL: ~50k internal pull-up = on, driven low = off) OR USBAx_FORCE_EN (RP2350).\n"
             "  FAULT# (open drain, 7.5 ms deglitch) -> USBAx_OCS_N = same node as PWR_EN (0R on usb_hub). No pull-up on this node here.\n"
             "  Hub-owned port: FAULT# pulls the node low -> hub reads overcurrent, latches the port off (drives low) -> OR output follows.\n"
             "  Forced port (FORCE_EN high): switch stays on in constant-current limit / thermal cycling; FAULT# only pulls the hub's node\n"
             "  (port already off at the hub, or hub reports OC). RP2350 sees the fault as ISENSE pinned at ~1.6-1.8 A -> firmware drops FORCE_EN.\n"
             "FORCE_EN pull-down 4.7k (not 100k): RP2350 erratum E9 (stepping A2) can leave a pad that was driven high and then\n"
             "  reverted to input latched at ~2.2 V (> LVC1G32 VIH 2.0 V) -> port forced on after a crash/BOOTSEL. Only <= 8.2k defeats\n"
             "  the latch; 4.7k costs 0.7 mA from the push-pull GPIO while forced on (VOH drop negligible at 4 mA drive).\n"
             "Current limit: RILIM 15.0k -> 1.61 A min / 1.80 A max (TPS2553 DS table): covers BC1.2 DCP/CDP 1.5 A.\n"
             "Current sense: 30 mOhm before the switch (IN side), INA180A2 x50 -> 1.5 V/A; 2.0 A = 3.0 V, full scale 2.2 A at 3.3 V.\n"
             "  25 mA auto-off threshold = 37.5 mV out; INA180 offset +-150 uV x50 = +-7.5 mV (~5 mA). Shunt loss 1.8 A: 97 mW.\n"
             "  Route IN+/IN- as a Kelvin pair from the inner edges of the shunt pads.\n"
             "VBUS bulk 150 uF POSCAP + 10 uF + 100 nF per port at the connector (USB 2.0: >= 120 uF per downstream port).\n"
             "  TPS2553 soft start (~1 ms) limits inrush into the bulk; the 10 uF on the switch IN side + +5V rail caps supply the transient.\n"
             "ESD: TPD4E02B04 (0.25 pF) on the 4 SS lines, USBLC6-2SC6 on D+/D- (clamps to VBUS), all at the connector, flow-through.\n"
             "Shell / EH tabs and GND_DRAIN -> GND directly (no chassis on odock-10; via-stitch the tabs to all GND planes).",
          (20.32, 190.5))

    # PWR_FLAGs: switch inputs fed through the current-sense shunts
    s.flag("USBA1_SW_IN")
    s.flag("USBA2_SW_IN")
    s.build()
    return s
