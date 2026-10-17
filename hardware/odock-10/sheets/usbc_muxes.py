"""odock-10 — USB-C ports + alt-mode muxes: laptop USB-C receptacle (JAE DX07, 28 V EPR) -> TI TUSB1064 (UFP_D
crosspoint redriver, GPIO mode) -> hub upstream 10G + DP main link/AUX -> TI TUSB1046-DCI (DFP_D crosspoint, GPIO mode)
-> downstream USB-C receptacle (Amphenol 12401610E4#2A, 5 V source). CC/SBU short-to-VBUS protection (TPD4S480 laptop,
TPD6S300 downstream), 0.25 pF ESD arrays on every SuperSpeed line, VBUS TVS, AC coupling, EQ straps.
Design notes: docs/design/usbc_muxes.md"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "tools", "schgen"))
from schgen import Sheet

# --- part numbers (LCSC) -------------------------------------------------------------------------
R_1K, R_10K, R_20K, R_100K, R_1M = "C11702", "C25744", "C25765", "C25741", "C26083"   # 0402 basic
R_2M_0603 = "C22976"                                                                  # 0603 basic
C_100N = "C1525"            # 0402 16 V basic
C_220N = "C16772"           # 0402 16 V X7R basic (AC coupling, all 10G / HBR3 lanes)
C_1U = "C52923"             # 0402 25 V basic
C_10U = "C19702"            # 0603 10 V basic
C_100N_50V = "C14663"       # 0603 50 V basic
C_100N_100V = "C28233"      # CL21B104KCFNNNE 0805 100 V X7R basic (TPD4S480 VBIAS: >= 63 V rated)
TVS_LAPTOP = ("SMCJ28A", "C224047", "Diode_SMD:D_SMC")   # Littelfuse, 28 V standoff, VBR 31.1-34.4 V, 1500 W
TVS_DS = ("SMAJ6.0A", "C364284", "Diode_SMD:D_SMA")      # 6 V standoff, 400 W
ESD_HS = "odock:TPD4E02B04DQAR"                           # C106794, 0.25 pF, 10 Gbps, flow-through USON-10

# EQ / mode straps (4-level pins).  level: '0' 1k->GND, 'R' 20k->GND, 'F' open, '1' 1k->VCC
UP_STRAPS = {"I2C_EN": "0", "EQ1": "R", "EQ0": "F", "SSEQ1": "0", "SSEQ0/A0": "1", "DPEQ1": "R", "DPEQ0/A1": "R"}
DS_STRAPS = {"I2C_EN": "0", "EQ1": "R", "EQ0": "1", "SSEQ1": "0", "SSEQ0/A0": "F", "DPEQ1": "0", "DPEQ0/A1": "0"}


def _note(s, text, at):
    """Multi-line note as one text item per line."""
    for i, line in enumerate(text.split("\n")):
        s.note(line, at=(at[0], round(at[1] + i * 2.54, 2)))


def _strap(s, net, level, x, y, pin):
    """Two footprints per 4-level pin (GND side, VCC side); populate per level, others DNP (EQ tuning on the bench)."""
    gnd_val, gnd_lc = ("1k", R_1K) if level == "0" else ("20k", R_20K)
    s.r(gnd_val, net, "GND", at=(x, y), lcsc=gnd_lc, dnp=level not in ("0", "R"),
        desc=f"{pin} strap to GND (level {level})")
    s.r("1k", net, "+3V3", at=(x + 10.16, y), lcsc=R_1K, dnp=level != "1", desc=f"{pin} strap to VCC (level {level})")


def _esd(s, at, ch, desc):
    """TPD4E02B04: IO1..IO4 + straight-through NC pads (10<->1, 9<->2, 7<->4, 6<->5) on the same nets."""
    io = {"1": ch[0], "2": ch[1], "4": ch[2], "5": ch[3]}
    pins, nc = {"GND": "GND"}, []
    for p, thru in (("1", "10"), ("2", "9"), ("4", "7"), ("5", "6")):
        if io[p]:
            pins[p] = io[p]; pins[thru] = io[p]
        else:
            nc += [p, thru]
    return s.part(ESD_HS, "D", "TPD4E02B04", at=at, pins=pins, nc=nc, lcsc="C106794", desc=desc)


def _cap_row(s, pairs, x, y, val="220n", lc=C_220N, dx=10.16, desc=""):
    for i, (a, b) in enumerate(pairs):
        s.c(val, a, b, at=(x + i * dx, y), lcsc=lc, desc=desc)


def build(D):
    s = Sheet(D, "usbc_muxes.kicad_sch", "odock-10 — USB-C ports, TUSB1064 / TUSB1046 alt-mode muxes", ref_base=500,
              paper="A1")

    # =============================================================================================
    # 1. Laptop USB-C receptacle + protection
    # =============================================================================================
    _note(s, "1. LAPTOP USB-C (UFP data, EPR source up to 28 V x 5 A, bus-powered sink 5 V)\n"
             "JAE DX07S024XJ1R1100 (C134113): 48 V / 5 A, USB 3.x 10G. Shell -> GND (direct, JLC practice; via-stitch to plane).\n"
             "Pins by number (A row / B row checked vs USB Type-C R2.x receptacle table and symbol names):\n"
             "  A2/A3 TX1+/-  B2/B3 TX2+/-  (ours: TUSB1064 TX through 220 nF)  B11/B10 RX1+/-  A11/A10 RX2+/-  (DC to TUSB1064 RX)\n"
             "  A6/B6 D+ and A7/B7 D- tied at the connector -> LAPTOP_USB_DP/DN (hub upstream USB2).  A8/B8 SBU1/2 -> TPD4S480.\n"
             "VBUS TVS SMCJ28A (1500 W SMC): VRWM 28 V, VBR 31.1-34.4 V @1 mA, VC 45.4 V @33 A. At 29.4 V (28 V EPR +5 %) it is ~2 V\n"
             "  below VBR min -> leakage stays in the uA range (bench-check hot). It does NOT hold the PMG1 34 V abs-max pins below 34 V\n"
             "  during a surge (no TVS with VRWM >= 28 V can): accepted residual risk, same as Infineon's EPR references (VBUS_C direct).\n"
             "  SMC over SMBJ: ~2.5x lower dynamic resistance -> lower clamp at a given surge current. Steady state is covered by the\n"
             "  OVP latch (power_laptop, ~30.8 V) and the LM74800 backstop (32.6 V).  Keep the VBUS caps close to J501 (hot-plug).\n"
             "  Only 100 nF on VBUS here (cSnkBulk budget on power_laptop).\n"
             "TPD4S480 (C43131250): 63 V short-to-VBUS OVP + IEC ESD on CC1/CC2/SBU1/SBU2 (PMG1 CC/SBU pins are 6 V abs max).\n"
             "  VPWR = PMG1_VDDD: the PMG1 always-on rail (from VBUS or the deck). It MUST be up whenever PMG1 runs, otherwise the CC\n"
             "  FETs stay open and the laptop sees only the dead-battery Rd.  RPD_Gx = C_CCx: dead-battery Rd while VPWR is off, so a\n"
             "  laptop applies 5 V to a dead deck (bus-powered cold start).  Removed 3.5 ms after VPWR is up -> PMG1 owns CC (Rp/Rd/DRP).\n"
             "  EPR_EN = VPWR (divider always on, keeps unloaded VBUS_LV < 24 V abs max); VBUS_LV, EPR_BLK_G open (PMG1 senses 28 V).\n"
             "  FLT# (open drain) -> UP_CCPROT_FLT_N, pulled up to PMG1_VDDD; route to a PMG1 GPIO if pins allow (optional).\n"
             "ESD: TPD4E02B04 (0.25 pF, 10 Gbps) on all 8 SS lines + USB2, at the connector, flow-through (route over pads 1-10, 2-9, 4-7, 5-6).",
          at=(20.32, 12.7))
    x0, y0 = 45.72, 96.52
    s.part("odock:DX07S024XJ1R1100", "J", "USB-C laptop", at=(x0, y0),
           pins={"VBUS": "VBUS_LAPTOP", "GND": "GND", "0": "GND",
                 "A5": "UP_C_CC1", "B5": "UP_C_CC2", "A8": "UP_C_SBU1", "B8": "UP_C_SBU2",
                 "A6": "LAPTOP_USB_DP", "B6": "LAPTOP_USB_DP", "A7": "LAPTOP_USB_DN", "B7": "LAPTOP_USB_DN",
                 "A2": "UP_C_TX1_P", "A3": "UP_C_TX1_N", "B2": "UP_C_TX2_P", "B3": "UP_C_TX2_N",
                 "B11": "UP_RX1_P", "B10": "UP_RX1_N", "A11": "UP_RX2_P", "A10": "UP_RX2_N"},
           desc="USB-C receptacle 24P, 48 V / 5 A, 10G (laptop port)")
    s.part("Device:D_Zener", "D", TVS_LAPTOP[0], TVS_LAPTOP[2], at=(25.4, 152.4), lcsc=TVS_LAPTOP[1],
           pins={"K": "VBUS_LAPTOP", "A": "GND"}, desc="TVS 28 V unidirectional 1500 W SMC, laptop VBUS")
    s.c("100n/50V", "VBUS_LAPTOP", "GND", size="0603", at=(38.1, 152.4), lcsc=C_100N_50V)
    _esd(s, (35.56, 190.5), ("UP_C_TX1_P", "UP_C_TX1_N", "UP_RX1_P", "UP_RX1_N"), "ESD 10G, laptop TX1/RX1")
    _esd(s, (35.56, 228.6), ("UP_C_TX2_P", "UP_C_TX2_N", "UP_RX2_P", "UP_RX2_N"), "ESD 10G, laptop TX2/RX2")
    _esd(s, (35.56, 266.7), ("LAPTOP_USB_DP", "LAPTOP_USB_DN", None, None), "ESD, laptop USB2 D+/D-")

    s.part("odock:TPD4S480RUKR_C43131250", "U", "TPD4S480", at=(127.0, 106.68),
           pins={"VBUS": "VBUS_LAPTOP", "EPR_EN": "PMG1_VDDD", "VPWR": "PMG1_VDDD", "VBIAS": "UP_TPD_VBIAS",
                 "C_CC1": "UP_C_CC1", "RPD_G1": "UP_C_CC1", "C_CC2": "UP_C_CC2", "RPD_G2": "UP_C_CC2",
                 "CC1": "LAPTOP_CC1", "CC2": "LAPTOP_CC2", "C_SBU1": "UP_C_SBU1", "C_SBU2": "UP_C_SBU2",
                 "SBU1": "UP_SBU1", "SBU2": "UP_SBU2", "~{FLT}": "UP_CCPROT_FLT_N", "GND": "GND", "EP": "GND"},
           nc=["VBUS_LV", "EPR_BLK_G"], desc="CC/SBU 63 V short-to-VBUS protection + IEC ESD (laptop port)")
    x, y = 93.98, 152.4
    s.c("100n/100V", "UP_TPD_VBIAS", "GND", size="0805", at=(x, y), lcsc=C_100N_100V, desc="VBIAS, >= 63 V rated")
    s.c("1u", "PMG1_VDDD", "GND", at=(x + 10.16, y), lcsc=C_1U, desc="TPD4S480 VPWR")
    s.r("100k", "UP_CCPROT_FLT_N", "PMG1_VDDD", at=(x + 20.32, y), lcsc=R_100K)
    s.r("2M", "UP_SBU1", "GND", size="0603", at=(x + 30.48, y), lcsc=R_2M_0603, desc="SBU1 2M to GND (TUSB1064 DS)")
    s.r("2M", "UP_SBU2", "GND", size="0603", at=(x + 40.64, y), lcsc=R_2M_0603, desc="SBU2 2M to GND (TUSB1064 DS)")

    # =============================================================================================
    # 2. TUSB1064 (UFP_D crosspoint redriver)
    # =============================================================================================
    _note(s, "2. TUSB1064 UFP_D MUX/REDRIVER  (TUSB1064IRNQT C702365, GPIO mode: I2C_EN = 0)\n"
             "Controlled by PMG1 port 0: MUX_UP_CTL1 = DP enabled, MUX_UP_CTL0 = USB3 enabled, MUX_UP_FLIP = plug flipped (all fail-safe,\n"
             "  500k internal pull-down). CTL1/CTL0: LL power down | LH USB3 only | HL 4-lane DP (pin assign. C) | HH USB3 + 2-lane DP (D).\n"
             "  Power-up default is USB3 mode: PMG1 must pulse CTL0 L-H-L to power it down when nothing is attached. 16 ms debounce.\n"
             "AC coupling: 220 nF on our TX1/TX2 (to receptacle TX pins) and on SSRX -> HUB_UP_SS_RX (we transmit into the hub).\n"
             "  HUB_UP_SS_TX -> SSTX is DC here: the 220 nF hub-TX caps sit on usb_hub.  RX1/RX2 DC (the laptop TX has its caps).\n"
             "  Rule: exactly one 75-265 nF cap per SS line, at the transmitter end of each segment.\n"
             "EQ straps (bench-tunable, both footprints on every 4-level pin):\n"
             "  EQ1/EQ0 = R/F  #6 6.6 dB  (laptop cable -> RX1/RX2, USB)       SSEQ1/SSEQ0 = 0/1  #3 2.2 dB  (hub TX, ~40 mm)\n"
             "  DPEQ1/DPEQ0 = R/R  #5 6.5 dB at 4.05 GHz (laptop cable, DP lanes)\n"
             "EN: 10k/100n RC to +3V3 -> 4-level pins latched ~1 ms after VCC.  HPDIN <- UP_HPD (10k series: pin not fail-safe).\n"
             "  TUSB1064 HPDIN has NO internal pull-down (DS p.6: 500k only on CTL0/CTL1/FLIP/EN): 100k UP_HPD -> GND here.\n"
             "  In GPIO mode AUX snoop is off: all DP lanes of the selected config are on while HPDIN is high; off after HPDIN low > 2 ms.\n"
             "AUX: AUXp 1M -> +3V3, AUXn 1M -> GND (UFP_D/sink bias seen by the laptop), 100 nF to TUSB1046 AUX (section 4).\n"
             "SBU1/2 DC to the receptacle via TPD4S480, 2M to GND.  I2C option: fit the 1k I2C_EN pull-up and re-wire CTL0/FLIP as SDA/SCL.",
          at=(170.18, 12.7))
    xu, yu = 218.44, 101.6
    up_pins = {"VCC": "+3V3", "EP": "GND",
               "TX1p": "UP_TX1_P", "TX1n": "UP_TX1_N", "TX2p": "UP_TX2_P", "TX2n": "UP_TX2_N",
               "RX1p": "UP_RX1_P", "RX1n": "UP_RX1_N", "RX2p": "UP_RX2_P", "RX2n": "UP_RX2_N",
               "SSTXp": "HUB_UP_SS_TXP", "SSTXn": "HUB_UP_SS_TXN", "SSRXp": "UP_SSRX_P", "SSRXn": "UP_SSRX_N",
               "DP0p": "DP_ML0_P", "DP0n": "DP_ML0_N", "DP1p": "DP_ML1_P", "DP1n": "DP_ML1_N",
               "DP2p": "DP_ML2_P", "DP2n": "DP_ML2_N", "DP3p": "DP_ML3_P", "DP3n": "DP_ML3_N",
               "AUXp": "DP_AUX_P", "AUXn": "DP_AUX_N", "SBU1": "UP_SBU1", "SBU2": "UP_SBU2",
               "CTL0/SDA": "MUX_UP_CTL0", "CTL1": "MUX_UP_CTL1", "FLIP/SCL": "MUX_UP_FLIP",
               "HPDIN": "UP_HPDIN", "EN": "UP_MUX_EN"}
    for pin in UP_STRAPS:
        up_pins[pin] = "UP_" + pin.split("/")[0]
    s.part("odock:TUSB1064IRNQT", "U", "TUSB1064", at=(xu, yu), pins=up_pins, nc=["NC"], lcsc="C702365",
           desc="USB 10G + DP 1.4 UFP_D linear redriver crosspoint")
    # supply
    x, y = 170.18, 152.4
    for i in range(3):
        s.c("100n", "+3V3", "GND", at=(x + i * 10.16, y), lcsc=C_100N, desc="TUSB1064 VCC pin decoupling")
    s.c("10u", "+3V3", "GND", size="0603", at=(x + 30.48, y), lcsc=C_10U)
    s.r("10k", "UP_MUX_EN", "+3V3", at=(x + 40.64, y), lcsc=R_10K, desc="TUSB1064 EN pull-up")
    s.c("100n", "UP_MUX_EN", "GND", at=(x + 50.8, y), lcsc=C_100N, desc="EN delay ~1 ms")
    s.r("10k", "UP_HPD", "UP_HPDIN", at=(x + 60.96, y), lcsc=R_10K, desc="HPDIN series (not fail-safe)")
    s.r("1M", "DP_AUX_P", "+3V3", at=(x + 71.12, y), lcsc=R_1M, desc="AUXp 1M to DP_PWR (UFP_D bias)")
    s.r("1M", "DP_AUX_N", "GND", at=(x + 81.28, y), lcsc=R_1M, desc="AUXn 1M to GND (UFP_D bias)")
    # straps
    x, y = 170.18, 190.5
    for i, (pin, lvl) in enumerate(UP_STRAPS.items()):
        _strap(s, "UP_" + pin.split("/")[0], lvl, x + (i % 4) * 22.86, y + (i // 4) * 35.56, pin)
    # AC coupling: receptacle TX + hub link
    _cap_row(s, [("UP_TX1_P", "UP_C_TX1_P"), ("UP_TX1_N", "UP_C_TX1_N"), ("UP_TX2_P", "UP_C_TX2_P"),
                 ("UP_TX2_N", "UP_C_TX2_N")], 93.98, 200.66, desc="AC coupling, laptop-port TX (10G / DP)")
    _cap_row(s, [("UP_SSRX_P", "HUB_UP_SS_RXP"), ("UP_SSRX_N", "HUB_UP_SS_RXN")], 93.98, 246.38,
             desc="AC coupling, TUSB1064 SSRX -> hub upstream RX (hub TX caps are on usb_hub)")

    # =============================================================================================
    # 3. DP main link + AUX between the muxes
    # =============================================================================================
    _note(s, "3. DP MAIN LINK + AUX  TUSB1064 -> TUSB1046  (one cap per line, both redrivers are linear: transparent to link training)\n"
             "DP0..DP3 220 nF (75-265 nF).  2 lanes used in pin assignment D (laptop advertises D: USB3 stays up), all 4 in C.\n"
             "AUX: one 100 nF per line between the two bias networks (TUSB1064 side 1M up/down, TUSB1046 side 100k down/up).\n"
             "Route as 85 ohm diff (90 ohm AUX), DP lanes length-matched within a pair (<0.1 mm), between pairs < 2 mm. Keep < 50 mm.",
          at=(170.18, 266.7))
    dp = [(f"DP_ML{l}_{pn}", f"DS_DP_ML{l}_{pn}") for l in range(4) for pn in ("P", "N")]
    _cap_row(s, dp, 170.18, 299.72, desc="AC coupling, DP main link TUSB1064 -> TUSB1046")
    s.c("100n", "DP_AUX_P", "DS_AUX_P", at=(170.18 + 8 * 10.16, 299.72), lcsc=C_100N, desc="AC coupling, DP AUX+")
    s.c("100n", "DP_AUX_N", "DS_AUX_N", at=(170.18 + 9 * 10.16, 299.72), lcsc=C_100N, desc="AC coupling, DP AUX-")

    # =============================================================================================
    # 4. TUSB1046-DCI (DFP_D crosspoint redriver)
    # =============================================================================================
    _note(s, "4. TUSB1046-DCI DFP_D MUX/REDRIVER  (TUSB1046-DCIRNQT C2652434, GPIO mode: I2C_EN = 0)\n"
             "Controlled by PMG1 port 1: MUX_DS_CTL1 = DP enabled, MUX_DS_CTL0 = USB3 enabled, MUX_DS_FLIP = plug flipped.\n"
             "  CTL1/CTL0: LL power down | LH USB3 only | HL 4-lane DP (C/E) | HH USB3 + 2-lane DP (D/F). Default after power-up: USB3.\n"
             "USB side: HUB_DSC_SS_TX -> SSTX DC (hub-TX caps on usb_hub); SSRX -> 220 nF -> HUB_DSC_SS_RX. Receptacle TX via 220 nF, RX DC.\n"
             "HPDIN (pin 32 in GPIO mode) <- DS_HPD through 10k (pin not fail-safe).  CAD_SNK = H (10k to +3V3): AUX snoop off,\n"
             "  lanes follow CTL only (robust with non-compliant AUX); DNP pull-down re-enables snoop (lane power saving).\n"
             "EQ straps: EQ1/EQ0 = R/1  #7 5.2 dB (downstream cable -> RX1/RX2)   SSEQ1/SSEQ0 = 0/F  #2 1.7 dB (hub TX, short)\n"
             "  DPEQ1/DPEQ0 = 0/0  #0 1.0 dB (from TUSB1064 over ~30 mm).\n"
             "AUX: AUXp 100k -> GND, AUXn 100k -> +3V3 (DFP_D/source bias seen by the monitor).  SBU1/2 via TPD6S300, 2M to GND.",
          at=(320.04, 12.7))
    xd, yd = 375.92, 101.6
    ds_pins = {"VCC": "+3V3", "EP": "GND",
               "TX1p": "DS_TX1_P", "TX1n": "DS_TX1_N", "TX2p": "DS_TX2_P", "TX2n": "DS_TX2_N",
               "RX1p": "DS_RX1_P", "RX1n": "DS_RX1_N", "RX2p": "DS_RX2_P", "RX2n": "DS_RX2_N",
               "SSTXp": "HUB_DSC_SS_TXP", "SSTXn": "HUB_DSC_SS_TXN", "SSRXp": "DS_SSRX_P", "SSRXn": "DS_SSRX_N",
               "AUXp": "DS_AUX_P", "AUXn": "DS_AUX_N", "SBU1": "DS_SBU1", "SBU2": "DS_SBU2",
               "CTL0/SDA": "MUX_DS_CTL0", "CTL1/HPDIN": "MUX_DS_CTL1", "FLIP/SCL": "MUX_DS_FLIP",
               "HPDIN/RSVD2": "DS_HPDIN", "CAD_SNK/RSVD1": "DS_CAD_SNK"}
    for l in range(4):
        ds_pins[f"DP{l}p"] = f"DS_DP_ML{l}_P"
        ds_pins[f"DP{l}n"] = f"DS_DP_ML{l}_N"
    for pin in DS_STRAPS:
        ds_pins[pin] = "DS_" + pin.split("/")[0]
    s.part("odock:TUSB1046-DCIRNQT", "U", "TUSB1046-DCI", at=(xd, yd), pins=ds_pins, lcsc="C2652434",
           desc="USB 10G + DP 1.4 DFP_D linear redriver crosspoint")
    x, y = 320.04, 152.4
    for i in range(4):
        s.c("100n", "+3V3", "GND", at=(x + i * 10.16, y), lcsc=C_100N, desc="TUSB1046 VCC pin decoupling")
    s.c("10u", "+3V3", "GND", size="0603", at=(x + 40.64, y), lcsc=C_10U)
    s.r("10k", "DS_HPD", "DS_HPDIN", at=(x + 50.8, y), lcsc=R_10K, desc="HPDIN series (not fail-safe)")
    s.r("10k", "DS_CAD_SNK", "+3V3", at=(x + 60.96, y), lcsc=R_10K, desc="CAD_SNK high: AUX snoop disabled")
    s.r("10k", "DS_CAD_SNK", "GND", at=(x + 71.12, y), lcsc=R_10K, dnp=True, desc="DNP: CAD_SNK low = AUX snoop on")
    s.r("100k", "DS_AUX_P", "GND", at=(x + 81.28, y), lcsc=R_100K, desc="AUXp 100k to GND (DFP_D bias)")
    s.r("100k", "DS_AUX_N", "+3V3", at=(x + 91.44, y), lcsc=R_100K, desc="AUXn 100k to DP_PWR (DFP_D bias)")
    x, y = 320.04, 190.5
    for i, (pin, lvl) in enumerate(DS_STRAPS.items()):
        _strap(s, "DS_" + pin.split("/")[0], lvl, x + (i % 4) * 22.86, y + (i // 4) * 35.56, pin)
    _cap_row(s, [("DS_SSRX_P", "HUB_DSC_SS_RXP"), ("DS_SSRX_N", "HUB_DSC_SS_RXN")], 320.04, 266.7,
             desc="AC coupling, TUSB1046 SSRX -> hub downstream-C RX (hub TX caps are on usb_hub)")
    _cap_row(s, [("DS_TX1_P", "DS_C_TX1_P"), ("DS_TX1_N", "DS_C_TX1_N"), ("DS_TX2_P", "DS_C_TX2_P"),
                 ("DS_TX2_N", "DS_C_TX2_N")], 370.84, 266.7, desc="AC coupling, downstream-port TX (10G / DP)")

    # =============================================================================================
    # 5. Downstream USB-C receptacle + protection
    # =============================================================================================
    _note(s, "5. DOWNSTREAM USB-C (DFP data, 5 V / 3 A source by PMG1 port 1, DP alt mode DFP_D)\n"
             "Amphenol 12401610E4#2A (C5119948): 20 V / 5 A, USB 3.2 Gen2. Shield pins 14/15 -> GND.\n"
             "USB2 D+/D- (both rows) -> HUB_DSC_DP/DN directly (ESD in TPD6S300 D1/D2).  VBUS_DS switch + bulk cap: pd_pmg1 / power.\n"
             "TVS SMAJ6.0A on VBUS_DS (6 V standoff over 5.25 V max).  100 nF at the connector.\n"
             "TPD6S300 (C2649810): 24 V CC/SBU OVP + IEC ESD (CC, SBU, D+/D-); VPWR = +3V3 (port 1 only runs with the deck powered).\n"
             "  RPD_G1/2 = GND: NO dead-battery Rd on a source-only port.  N.C. pins 16/17 -> GND per datasheet.\n"
             "  CC FETs pass VCONN (600 mA) if PMG1 port 1 supplies it.  FLT# -> DS_CCPROT_FLT_N (100k to +3V3), optional PMG1 GPIO.\n"
             "ESD TPD4E02B04 on all 8 SS lines, flow-through at the connector.",
          at=(482.6, 12.7))
    xj, yj = 584.2, 96.52
    s.part("odock:12401610E4#2A", "J", "USB-C downstream", at=(xj, yj),
           pins={"VBUS": "VBUS_DS", "GND": "GND", "14": "GND", "15": "GND",
                 "A5": "DS_C_CC1", "B5": "DS_C_CC2", "A8": "DS_C_SBU1", "B8": "DS_C_SBU2",
                 "A6": "HUB_DSC_DP", "B6": "HUB_DSC_DP", "A7": "HUB_DSC_DN", "B7": "HUB_DSC_DN",
                 "A2": "DS_C_TX1_P", "A3": "DS_C_TX1_N", "B2": "DS_C_TX2_P", "B3": "DS_C_TX2_N",
                 "B11": "DS_RX1_P", "B10": "DS_RX1_N", "A11": "DS_RX2_P", "A10": "DS_RX2_N"},
           desc="USB-C receptacle 24P, 20 V / 5 A, 10G (downstream port)")
    s.part("Device:D_Zener", "D", TVS_DS[0], TVS_DS[2], at=(637.54, 152.4), lcsc=TVS_DS[1],
           pins={"K": "VBUS_DS", "A": "GND"}, desc="TVS 6 V unidirectional 400 W, downstream VBUS")
    s.c("100n/50V", "VBUS_DS", "GND", size="0603", at=(609.6, 152.4), lcsc=C_100N_50V)
    _esd(s, (604.52, 190.5), ("DS_C_TX1_P", "DS_C_TX1_N", "DS_RX1_P", "DS_RX1_N"), "ESD 10G, downstream TX1/RX1")
    _esd(s, (604.52, 228.6), ("DS_C_TX2_P", "DS_C_TX2_N", "DS_RX2_P", "DS_RX2_N"), "ESD 10G, downstream TX2/RX2")

    s.part("odock:TPD6S300RUKR", "U", "TPD6S300", at=(508.0, 106.68), lcsc="C2649810",
           pins={"C_SBU1": "DS_C_SBU1", "C_SBU2": "DS_C_SBU2", "VBIAS": "DS_TPD_VBIAS",
                 "C_CC1": "DS_C_CC1", "C_CC2": "DS_C_CC2", "RPD_G1": "GND", "RPD_G2": "GND",
                 "~{FLT}": "DS_CCPROT_FLT_N", "VPWR": "+3V3", "CC1": "DS_CC1", "CC2": "DS_CC2",
                 "SBU1": "DS_SBU1", "SBU2": "DS_SBU2", "N.C.": "GND", "D1": "HUB_DSC_DP", "D2": "HUB_DSC_DN",
                 "GND": "GND", "EP": "GND"},
           desc="CC/SBU 24 V short-to-VBUS protection + IEC ESD (downstream port)")
    x, y = 482.6, 167.64
    s.c("100n/50V", "DS_TPD_VBIAS", "GND", size="0603", at=(x, y), lcsc=C_100N_50V, desc="VBIAS, >= 35 V rated")
    s.c("1u", "+3V3", "GND", at=(x + 10.16, y), lcsc=C_1U, desc="TPD6S300 VPWR")
    s.r("100k", "DS_CCPROT_FLT_N", "+3V3", at=(x + 20.32, y), lcsc=R_100K)
    s.r("2M", "DS_SBU1", "GND", size="0603", at=(x + 30.48, y), lcsc=R_2M_0603, desc="SBU1 2M to GND (TUSB1046 DS)")
    s.r("2M", "DS_SBU2", "GND", size="0603", at=(x + 40.64, y), lcsc=R_2M_0603, desc="SBU2 2M to GND (TUSB1046 DS)")

    # =============================================================================================
    # 6. Interface summary
    # =============================================================================================
    _note(s, "6. INTERFACES / ASSUMPTIONS\n"
             "HPD (both nets are PMG1 OUTPUTS on pd_pmg1 and mux HPDIN INPUTS here; 10k series):\n"
             "  DS_HPD = downstream monitor HPD as decoded by PMG1 port 1 (DFP_D) from DP Status / Attention VDMs (incl. IRQ_HPD pulses)\n"
             "           -> TUSB1046 HPDIN.\n"
             "  UP_HPD = HPD state PMG1 port 0 (UFP_D) reports to the laptop (DP Status/Attention) -> TUSB1064 HPDIN (enables the\n"
             "           TUSB1064 DP lanes; low > 2 ms turns them off, IRQ_HPD pulses are harmless).\n"
             "  Pull-downs: TUSB1064 HPDIN has none internally -> external 100k on UP_HPD; TUSB1046-DCI HPDIN has 150k internal\n"
             "  (R(ENPD)). Both HPDIN inputs are therefore low while PMG1 is in reset -> lanes off.\n"
             "PMG1_VDDD (global, pd_pmg1): powers TPD4S480 VPWR (~0.16 mA) so CC works in a dead deck.  Optional new nets kept local:\n"
             "  UP_CCPROT_FLT_N / DS_CCPROT_FLT_N.  DP_ML0/1 and DP_AUX nets are global names but only used on this sheet.\n"
             "CC lines: cReceiver caps (PMG1 reference 390 pF) and VCONN source belong to pd_pmg1 next to the PMG1 CC pins.\n"
             "Hub links: hub-TX 220 nF caps on usb_hub, hub-RX 220 nF caps (our SSRX outputs) on this sheet.\n"
             "I2C: both muxes in GPIO mode, SDA/SCL pins are CTL0/FLIP; I2C_EN pull-up footprints (DNP) for a later I2C variant.",
          at=(20.32, 330.2))
    s.flag("VBUS_LAPTOP")   # driven by the laptop or our source switch through FETs
    # TUSB1064 HPDIN pull-down (review pd_mux #1) - placed last so earlier references keep their numbers
    s.r("100k", "UP_HPD", "GND", at=(231.14, 172.72), lcsc=R_100K,
        desc="UP_HPD pull-down: TUSB1064 HPDIN has no internal PD (PMG1 P1.3 Hi-Z in reset)")
    s.build()
    return s
