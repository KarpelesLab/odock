"""odock-10 — laptop power sheet: LM51770 4-switch buck-boost (VIN 9-48 V -> VBB_OUT 5.1/9/15/20/28 V x 5 A),
voltage select by PMG1 GPIOs (VBB_VSEL0..2) through a slew-limited feedback network, LM74800 source switch
VBB_OUT -> VBUS_LAPTOP with hardware enable gating, LM74502 + TPS259470 bus-power sink switch
VBUS_LAPTOP -> +5V, independent latched ~30.8 V OVP (TLV3011), INA226 on laptop VBUS.
Design notes and calculations: docs/design/power_laptop.md"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "tools", "schgen"))
from schgen import Sheet

# --- LCSC part numbers ---------------------------------------------------------------------------
# resistors 0402 1 % (basic where available)
R_0, R_10, R_1K, R_1K5, R_4K7, R_10K, R_47K, R_100K, R_1M = (
    "C17168", "C25077", "C11702", "C25867", "C25900", "C25744", "C25792", "C25741", "C26083")
R_24K3, R_8K66, R_5K23, R_6K49, R_86K6, R_62K, R_43K = (
    "C26969", "C5126133", "C2933105", "C2998055", "C48533697", "C2909375", "C8329")
R_1M1, R_255K, R_40K2, R_121K, R_422K = "C133039", "C270623", "C25893", "C11693", "C477738"
R_46K4 = "C5126026"                                # OVP divider bottom (trip 31.1 V)
R_200K_0805, R_470K_0805 = "C17539", "C17709"      # 0805, 150 V working voltage (VIN-side)
R_10_0603 = "C22859"
R_150_2512 = "C2934049"                            # 1 W, VBB_OUT discharge
R_SNS_4M = "C459681"                               # TA-I RLP25FEGR004 4 mOhm 1 % 3 W 50 ppm 2512 (peak current sense; same as power_rails)
R_SNS_8M = "C2075410"                              # Yageo PE2512FKE070R008L 8 mOhm 2512 (avg current limit)
R_SNS_5M = "C316225"                               # TA-I RLM12FTCMR005 5 mOhm 1 % 1 W 1206 (INA226 shunt; same as pd_pmg1)
# capacitors
C_100P, C_82P, C_470P, C_1N, C_3N3, C_6N8, C_22N, C_100N = (
    "C1546", "C45501", "C1537", "C1523", "C1613", "C1631", "C1532", "C1525")   # 3.3n/6.8n: 0603 basic
C_2N2, C_4N7 = "C1604", "C1538"                    # 2.2 nF: 0603 basic (0402 is extended)
C_100N_50V, C_22N_50V = "C14663", "C21122"                          # 0603
C_100N_100V = "C28233"                                              # CL21B104KCFNNNE 0805 100 V X7R (basic)
C_1U_50V, C_4U7_16V = "C15849", "C19666"                            # 0603
C_10U_25V, C_22U_25V, C_1U_100V = "C15850", "C45783", "C126585"     # 0805
C_4U7_100V, C_10U_50V = "C697607", "C432929"                        # 1210
C_100U_35V_POLY = "C2982822"                                        # polymer 6.3x7, VBB_OUT bulk
# semis
FET_SMALL = ("Transistor_FET:AO3400A", "C20917")   # 30 V logic-level, SOT-23
FET_60V_SMALL = ("Transistor_FET:2N7002", "C8545")
D_1N4148W, D_BAT46W = "C81598", "C83152"


def _note(s, text, at):
    s.note(text, at=at)


def _nfet(s, g, d, src, at, part=FET_SMALL, desc=""):
    return s.part(part[0], "Q", part[0].split(":")[1], at=at, lcsc=part[1], pins={"G": g, "D": d, "S": src},
                  desc=desc)


def build(D):
    s = Sheet(D, "power_laptop.kicad_sch", "odock-10 — Laptop power (buck-boost, source/sink switches, OVP)",
              ref_base=200, paper="A2")

    # =============================================================================================
    # 1. Buck-boost power stage
    # =============================================================================================
    _note(s, "1. LM51770 4-SWITCH BUCK-BOOST POWER STAGE   VIN 9-50 V -> VBB_OUT 5.1/9/15/20/28 V, 5 A (140 W)\n"
           "fsw = 347 kHz (RT 86.6k). L = Coilcraft XAL1010-103 10 uH (Isat 17.5 A, 14.75 mOhm max).\n"
           "Ripple: 3.4 A p-p worst (48 V -> 28 V buck), 2.0 A (14 V -> 28 V boost).\n"
           "Input half-bridge: 2x BSC0805LS (100 V, 7.7 mOhm @4.5 V, Qg 16 nC). Output: 2x CSD18543Q3A (60 V, 12 mOhm).\n"
           "Peak current sense RCS = 4 mOhm (WSL2512): limit 50 mV/4 mOhm = 12.5 A (10.6 A min) -> full 140 W from VIN >= ~16 V.\n"
           "Average output current limit RISNS = 8 mOhm: 50 mV -> 6.25 A (6.1 A min), hiccup (CFG).\n"
           "Input: 4x 4.7 uF/100 V X7S only (VIN reaches 50.4 V). No electrolytic here: the PD-in source sees all VIN\n"
           "  capacitance (cSnkBulkPd <= 100 uF); the single 47 uF damping alu for VIN sits on power_input.\n"
           "Output: 4x 10 uF/50 V on the power-stage side, 2x 10 uF/50 V + 2x 100 uF/35 V polymer on VBB_OUT.\n"
           "Loss at 140 W: ~3.9 W from 20 V (boost), ~3.7 W from 48 V (buck), eta ~97 %. See docs/design/power_laptop.md.",
           at=(20.32, 12.7))
    y = 66.04
    for i in range(4):
        s.c("4.7u/100V", "VIN", "GND", size="1210", at=(22.86 + i * 12.7, y), lcsc=C_4U7_100V)
    s.part("odock:BSC0805LS", "Q", "BSC0805LS", at=(99.06, y), pins={"S": "BB_SW1", "G": "BB_G1", "D": "VIN", "EP": "VIN"},
           desc="100 V NFET, buck high side (HO1)")
    s.part("odock:BSC0805LS", "Q", "BSC0805LS", at=(144.78, y), pins={"S": "GND", "G": "BB_G2", "D": "BB_SW1", "EP": "BB_SW1"},
           desc="100 V NFET, buck low side (LO1)")
    s.r("4m", "BB_SW1", "BB_LS", size="2512", at=(172.72, y), lcsc=R_SNS_4M, mpn="RLP25FEGR004",
        desc="Peak current sense 4 mOhm 1 % 2512 (CSA/CSB Kelvin)")
    s.part("odock:XAL1010-103MED", "L", "10u", at=(190.5, y), pins={"1": "BB_LS", "2": "BB_SW2"},
           desc="10 uH 17.5 A shielded inductor")
    s.part("odock:CSD18543Q3A", "Q", "CSD18543Q3A", at=(228.6, y), pins={"S": "GND", "G": "BB_G3", "D": "BB_SW2"},
           desc="60 V NFET, boost low side (LO2)")
    s.part("odock:CSD18543Q3A", "Q", "CSD18543Q3A", at=(274.32, y), pins={"S": "BB_SW2", "G": "BB_G4", "D": "BB_PSO"},
           desc="60 V NFET, boost high side (HO2)")
    s.r("8m", "BB_PSO", "VBB_OUT", size="2512", at=(299.72, y), lcsc=R_SNS_8M, mpn="PE2512FKE070R008L",
        desc="Output current sense 8 mOhm 1 % 2512 (ISNSP/ISNSN Kelvin)")
    y = 99.06
    for i in range(4):
        s.c("10u/50V", "BB_PSO", "GND", size="1210", at=(91.44 + i * 10.16, y), lcsc=C_10U_50V)
    for i in range(2):
        s.c("10u/50V", "VBB_OUT", "GND", size="1210", at=(137.16 + i * 10.16, y), lcsc=C_10U_50V)
    for i in range(2):
        s.part("Device:C_Polarized", "C", "100u/35V", "Capacitor_SMD:CP_Elec_6.3x7.7", at=(162.56 + i * 12.7, y),
               pins={"1": "VBB_OUT", "2": "GND"}, lcsc=C_100U_35V_POLY, desc="Polymer 100 uF 35 V, VBB_OUT bulk")
    s.c("100n/50V", "VBB_OUT", "GND", size="0603", at=(193.04, y), lcsc=C_100N_50V)
    s.flag("VBB_OUT", at=(205.74, y))
    # gate resistors (0 R, footprints for EMI tuning)
    y = 124.46
    for i, (a, b) in enumerate([("BB_HO1", "BB_G1"), ("BB_LO1", "BB_G2"), ("BB_LO2", "BB_G3"), ("BB_HO2", "BB_G4")]):
        s.r("0", a, b, at=(91.44 + i * 10.16, y), lcsc=R_0, desc="Gate resistor (0 R, tune 1-4.7 R for EMI)")

    # =============================================================================================
    # 2. LM51770 controller
    # =============================================================================================
    _note(s, "2. LM51770 CONTROLLER\n"
           "BIAS from VBB_OUT (10 R/1 uF): VCC LDO runs from min(VIN, VBB_OUT) above 6.5 V -> less LDO loss at 48 V in.\n"
           "EN/UVLO: 200k/43k from VIN -> on at 8.1 V, off at 6.8 V (5 uA hysteresis current).\n"
           "  Q pulls EN/UVLO low unless VBB_EN AND LAPTOP_OVP_N (see section 3).\n"
           "CFG 6.49k = R2D #7: spread spectrum ON, hiccup ON, PSM entry 10 %, average current LIMIT on ISNS.\n"
           "SYNC = VCC (positive current-limit direction, no external clock). DTRK = GND (unused).\n"
           "MODE = GND: power-save mode (no reverse current: down-steps are discharged by the load and the\n"
           "  VBUS discharge of the PD controller; OVP1 is masked in PSM so nFLT does not glitch). DNP 0R -> VCC = FPWM.\n"
           "SLOPE 100k (L/RCS x 50e6 = 125k, x0.8 for more slope). RCS/L = 400 /s < fsw/(10 x 28 V) = 1240 /s.\n"
           "SS 22 nF -> 2.2 ms soft start to 5.1 V. VCC 2x 22 uF (>= 10 uF effective at 5 V).\n"
           "Compensation (fbw 3 kHz, AC divider = 71.8 V equiv., COUT ~220 uF, Dmax 0.68, RCS 4 mOhm):\n"
           "  RCOMP = 2pi fbw x 71.8 x 10 RCS COUT / (gm (1-Dmax)) = 62k, CCOMP 6.8 nF (fz 380 Hz), CHF 82 pF.\n"
           "IMONOUT (limiter comp): 10k + 1 nF -> current loop ~6 kHz. All loop values are starting points: verify\n"
           "  with TI quickstart calculator / SIMPLIS and bode measurement at 5, 20 and 28 V.\n"
           "CSA/CSB filter 10 R + 10 R + 100 pF (tau 2 ns << 88 ns min on-time / 10). nFLT = VBB_PG (10k to +3V3).",
           at=(264.16, 12.7))
    s.part("odock:LM51770DCPR", "U", "LM51770", at=(342.9, 132.08),
           pins={"BIAS": "BB_BIAS", "VIN": "VIN", "EN/UVLO": "BB_EN", "IMONOUT": "BB_IMON", "nFLT": "VBB_PG",
                 "DTRK": "GND", "SYNC": "BB_VCC", "MODE": "BB_MODE", "CFG": "BB_CFG", "SLOPE": "BB_SLOPE",
                 "RT": "BB_RT", "SS/ATRK": "BB_SS", "AGND": "GND", "COMP": "BB_COMP", "FB": "BB_FB",
                 "VOUT": "VBB_OUT", "ISNSN": "VBB_OUT", "ISNSP": "BB_PSO", "SW2": "BB_SW2", "HB2": "BB_HB2",
                 "HO2": "BB_HO2", "LO2": "BB_LO2", "PGND": "GND", "VCC": "BB_VCC", "LO1": "BB_LO1",
                 "HO1": "BB_HO1", "HB1": "BB_HB1", "SW1": "BB_SW1", "CSA": "BB_CSA", "CSB": "BB_CSB", "EP": "GND"},
           nc=["NC", "HO1_LL", "HO2_LL"], desc="78 V 4-switch buck-boost controller")
    ctl = [
        ("c", "100n/100V", "VIN", "GND", "0805", C_100N_100V, {}), ("c", "1u/100V", "VIN", "GND", "0805", C_1U_100V, {}),
        ("r", "200k", "VIN", "BB_EN", "0805", R_200K_0805, {}), ("r", "43k", "BB_EN", "GND", "0402", R_43K, {}),
        ("r", "10", "VBB_OUT", "BB_BIAS", "0603", R_10_0603, {}), ("c", "1u/50V", "BB_BIAS", "GND", "0603", C_1U_50V, {}),
        ("c", "22u", "BB_VCC", "GND", "0805", C_22U_25V, {}), ("c", "22u", "BB_VCC", "GND", "0805", C_22U_25V, {}),
        ("c", "100n/50V", "BB_HB1", "BB_SW1", "0603", C_100N_50V, {}),
        ("c", "100n/50V", "BB_HB2", "BB_SW2", "0603", C_100N_50V, {}),
        ("r", "10", "BB_SW1", "BB_CSA", "0402", R_10, {}), ("r", "10", "BB_LS", "BB_CSB", "0402", R_10, {}),
        ("c", "100p", "BB_CSA", "BB_CSB", "0402", C_100P, {}),
        ("r", "86.6k", "BB_RT", "GND", "0402", R_86K6, {}), ("r", "100k", "BB_SLOPE", "GND", "0402", R_100K, {}),
        ("r", "6.49k", "BB_CFG", "GND", "0402", R_6K49, {}), ("c", "22n", "BB_SS", "GND", "0402", C_22N, {}),
        ("r", "62k", "BB_COMP", "BB_COMPZ", "0402", R_62K, {}), ("c", "6.8n", "BB_COMPZ", "GND", "0603", C_6N8, {}),
        ("c", "82p", "BB_COMP", "GND", "0402", C_82P, {}),
        ("r", "10k", "BB_IMON", "BB_IMONZ", "0402", R_10K, {}), ("c", "1n", "BB_IMONZ", "GND", "0402", C_1N, {}),
        ("r", "0", "BB_MODE", "GND", "0402", R_0, {"desc": "MODE = GND: PSM (default)"}),
        ("r", "0", "BB_MODE", "BB_VCC", "0402", R_0, {"dnp": True, "desc": "DNP: MODE = VCC -> FPWM"}),
        ("r", "10k", "VBB_PG", "+3V3", "0402", R_10K, {}),
    ]
    for i, (kind, val, a, b, size, lc, kw) in enumerate(ctl):
        at = (271.78 + (i % 9) * 12.7, 190.5 + (i // 9) * 25.4)
        (s.r if kind == "r" else s.c)(val, a, b, size=size, at=at, lcsc=lc, **kw)

    # =============================================================================================
    # 3. Output voltage select (feedback network) + enable / discharge
    # =============================================================================================
    _note(s, "3. OUTPUT VOLTAGE SELECT  (PMG1 GPIOs only; RP2350 has no path here)\n"
           "VOUT = 1 V x (1 + Rtop x Gfb). Rtop 100k, Rbot 24.3k -> 5.115 V with all VSEL low (default, no firmware).\n"
           "Switched branches hang off node BB_FBM, which connects to FB through Rs = 1.5k and is held by Cm = 4.7 uF:\n"
           "  any VSEL change (even several bits at once) moves the FB current as ONE first-order exponential,\n"
           "  tau = Cm x (Rs || branches) = 4.6-7 ms -> max slew 23 V / 4.6 ms = 5 mV/us (PD limit 30 mV/us),\n"
           "  settles in < 35 ms; FB stays within the +-10 % nFLT window, so VBB_PG does not drop on steps.\n"
           "  VSEL2..0 = 000 5.12 V | 001 8.99 V | 010 14.96 V | 100 19.97 V | 111 27.97 V   (one-hot + all-on)\n"
           "             011 17.8 V | 101 22.3 V | 110 26.1 V (unused). Max of ANY code is 28 V by construction.\n"
           "  Worst case with 1 % parts and 1 % VREF: +-2.8 % (inside PD +-5 %).\n"
           "VSEL inputs: 100k pull-downs (floating PMG1 -> 5 V), 1k gate resistors, AO3400A switches.\n"
           "ENABLE: LM51770 runs only if VBB_EN AND LAPTOP_OVP_N. BB_ENKILL is pulled up from VIN (470k + 5.1 V zener):\n"
           "  default ON (= converter OFF, VBB_OUT discharged through 150 R / 2N7002, ~25 ms).\n"
           "  VBB_EN high AND LAPTOP_OVP_N high -> two series FETs pull BB_ENKILL low -> EN released, discharge off.\n"
           "  BB_ENKILL also holds VBB_PG low while disabled (LM51770 nFLT is high-Z in shutdown / soft start):\n"
           "  that hold FET's gate BB_PGH follows BB_ENKILL up at once (1N4148W) but decays through 1M/4.7 nF, so\n"
           "  VBB_PG stays low 5.4-9.2 ms after enable (> 2.2 ms soft start x2): VBB_PG high = output regulated.",
           at=(20.32, 147.32))
    x, y = 25.4, 200.66
    s.r("100k", "VBB_OUT", "BB_FB", at=(x, y), lcsc=R_100K, desc="FB top")
    s.r("24.3k", "BB_FB", "GND", at=(x + 10.16, y), lcsc=R_24K3, desc="FB bottom (5.1 V default)")
    s.r("1.5k", "BB_FB", "BB_FBM", at=(x + 20.32, y), lcsc=R_1K5, desc="Rs, slew network")
    s.c("4.7u", "BB_FBM", "GND", size="0603", at=(x + 30.48, y), lcsc=C_4U7_16V, desc="Cm, slew network")
    for i, (r, lc, sel) in enumerate([("24.3k", R_24K3, 0), ("8.66k", R_8K66, 1), ("5.23k", R_5K23, 2)]):
        s.r(r, "BB_FBM", f"BB_VS{sel}D", at=(x + 40.64 + i * 10.16, y), lcsc=lc, desc=f"VSEL{sel} branch")
        _nfet(s, f"BB_VS{sel}G", f"BB_VS{sel}D", "GND", at=(x + 15.24 + i * 35.56, y + 33.02), desc=f"VSEL{sel} switch")
        s.r("1k", f"VBB_VSEL{sel}", f"BB_VS{sel}G", at=(x + i * 10.16, y + 58.42), lcsc=R_1K)
        s.r("100k", f"VBB_VSEL{sel}", "GND", at=(x + 30.48 + i * 10.16, y + 58.42), lcsc=R_100K)
    # enable / discharge
    s.r("100k", "VBB_EN", "GND", at=(x + 60.96, y + 58.42), lcsc=R_100K)
    _nfet(s, "BB_PGH", "VBB_PG", "GND", at=(x + 96.52, y + 58.42),
          desc="Holds VBB_PG low while disabled and for >= 5.4 ms after enable (nFLT high-Z in shutdown / soft start)")
    s.part("Device:D", "D", "1N4148W", "Diode_SMD:D_SOD-123", at=(x + 116.84, y + 58.42), lcsc=D_1N4148W,
           pins={"A": "BB_ENKILL", "K": "BB_PGH"}, desc="Fast set of the VBB_PG hold (converter disabled)")
    s.r("1M", "BB_PGH", "BB_ENKILL", at=(x + 132.08, y + 58.42), lcsc=R_1M, desc="VBB_PG hold release delay")
    s.c("4.7n", "BB_PGH", "GND", at=(x + 142.24, y + 58.42), lcsc=C_4N7, desc="tau 4.7 ms -> release 5.4-9.2 ms")
    x, y = 40.64, 292.1
    s.part("Device:D_Zener", "D", "BZT52C5V1", "Diode_SMD:D_SOD-123", at=(x, y), lcsc="C173407",
           pins={"K": "BB_ENKILL", "A": "GND"}, desc="5.1 V zener, gate clamp")
    s.r("470k", "VIN", "BB_ENKILL", size="0805", at=(x + 15.24, y), lcsc=R_470K_0805)
    _nfet(s, "BB_ENKILL", "BB_EN", "GND", at=(x + 45.72, y), desc="Pulls LM51770 EN/UVLO low (converter off)")
    _nfet(s, "VBB_EN", "BB_ENKILL", "BB_ENS", at=(x + 78.74, y), desc="Enable AND: VBB_EN")
    _nfet(s, "LAPTOP_OVP_N", "BB_ENS", "GND", at=(x + 116.84, y), desc="Enable AND: no OVP latch")
    _nfet(s, "BB_ENKILL", "BB_DIS", "GND", at=(x + 147.32, y), part=FET_60V_SMALL, desc="VBB_OUT discharge")
    s.r("150", "VBB_OUT", "BB_DIS", size="2512", at=(x + 162.56, y), lcsc=R_150_2512, desc="Discharge 150 R 1 W")

    # =============================================================================================
    # 4. Source switch VBB_OUT -> VBUS_LAPTOP
    # =============================================================================================
    _note(s, "4. LAPTOP SOURCE SWITCH  VBB_OUT -> VBUS_LSW -> 5 mOhm -> VBUS_LAPTOP\n"
           "LM74800-Q1: Q (DGATE) = ideal diode (blocks laptop -> VBB_OUT in < 1 us), Q (HGATE) = on/off,\n"
           "  common drain, 2x BSC026N08NS5 (80 V, 2.6 mOhm @10 V; same FET as power_input): 5 A -> 0.13 W total.\n"
           "HARDWARE ENABLE: SRC_ON = LAPTOP_SRC_EN AND EXT_PWR_PRESENT AND (VBB_PG AND LAPTOP_OVP_N AND PG5_DLY)\n"
           "  74LVC1G11 3-input AND; VBB_PG and LAPTOP_OVP_N (both open-drain, 10k pull-ups) diode-ANDed by BAT54A;\n"
           "  2 FETs pull SRC_PGOK low unless the delayed PG_5V (SNK_PGD) is high: the source can only close after the\n"
           "  bus-power sink has been released (same delayed PG_5V) and +5V runs from the LM5148.\n"
           "  100k pull-downs: unpowered logic or floating PMG1 GPIO -> switch OFF.\n"
           "INTERLOCK: SRC_ON also forces the sink switch off (Q on SNK_ON, us) while the source HGATE needs ms:\n"
           "  the sink is released by EXT_PWR_PRESENT AND PG5_DLY, the source needs both too -> never both on.\n"
           "Backstop OV on the LM74800 OV pin (independent of logic and +3V3): 255k/10k from VBUS_LAPTOP\n"
           "  via VSNS/SW -> HGATE off above 32.6 V (31.7-33.6 V).\n"
           "Soft turn-on: HGATE 55 uA into 22 nF -> 2.5 V/ms.",
           at=(406.4, 12.7))
    x, y = 421.64, 66.04
    s.part("odock:BSC026N08NS5ATMA1", "Q", "BSC026N08NS5", at=(x, y), pins={"S": "VBB_OUT", "D": "SRC_MID", "G": "SRC_DGATE"},
           desc="80 V NFET, source ideal diode")
    s.part("odock:BSC026N08NS5ATMA1", "Q", "BSC026N08NS5", at=(x + 50.8, y), pins={"S": "VBUS_LSW", "D": "SRC_MID", "G": "SRC_HGATE"},
           desc="80 V NFET, source on/off")
    s.part("odock:LM74800QDRRRQ1", "U", "LM74800-Q1", at=(x + 25.4, y + 38.1),
           pins={"DGATE": "SRC_DGATE", "A": "VBB_OUT", "VSNS": "VBUS_LAPTOP", "SW": "SRC_OVT", "OV": "SRC_OV",
                 "EN/UVLO": "SRC_ON", "GND": "GND", "HGATE": "SRC_HGATE", "OUT": "VBUS_LSW", "VS": "SRC_MID",
                 "CAP": "SRC_CAP", "C": "SRC_MID"},
           nc=["RTN"], desc="Ideal diode + load switch controller, laptop source (RTN pad floating)")
    x2, y2 = 411.48, 134.62
    s.c("100n/50V", "SRC_MID", "GND", size="0603", at=(x2, y2), lcsc=C_100N_50V)
    s.c("100n/50V", "SRC_CAP", "SRC_MID", size="0603", at=(x2 + 12.7, y2), lcsc=C_100N_50V)
    s.r("255k", "SRC_OVT", "SRC_OV", at=(x2 + 25.4, y2), lcsc=R_255K)
    s.r("10k", "SRC_OV", "GND", at=(x2 + 38.1, y2), lcsc=R_10K)
    s.r("100", "SRC_HGATE", "SRC_DVDT", at=(x2 + 50.8, y2), lcsc="C25076")
    s.c("22n/50V", "SRC_DVDT", "GND", size="0603", at=(x2 + 63.5, y2), lcsc=C_22N_50V)
    s.r("100k", "SRC_ON", "GND", at=(x2 + 76.2, y2), lcsc=R_100K)
    # enable logic
    y3 = 165.1
    s.part("74xGxx:74LVC1G11", "U", "SN74LVC1G11", "Package_TO_SOT_SMD:SOT-23-6", at=(x2 + 22.86, y3), lcsc="C22046",
           pins={"1": "LAPTOP_SRC_EN", "3": "EXT_PWR_PRESENT", "6": "SRC_PGOK", "4": "SRC_ON", "5": "+3V3", "2": "GND"},
           desc="3-input AND, source enable")
    s.part("Diode:BAT54A", "D", "BAT54A", "Package_TO_SOT_SMD:SOT-23", at=(x2 + 91.44, y3), lcsc="C130910",
           pins={"3": "SRC_PGOK", "1": "VBB_PG", "2": "LAPTOP_OVP_N"}, desc="Diode AND (common anode)")
    s.r("10k", "SRC_PGOK", "+3V3", at=(x2 + 119.38, y3), lcsc=R_10K)
    s.r("100k", "LAPTOP_SRC_EN", "GND", at=(x2 + 129.54, y3), lcsc=R_100K)
    _nfet(s, "SNK_PGD", "SRC_PG5N", "GND", at=(x2 + 22.86, y3 + 22.86), desc="PG_5V (delayed) inverter")
    s.r("100k", "SRC_PG5N", "+3V3", at=(x2 + 45.72, y3 + 22.86), lcsc=R_100K)
    _nfet(s, "SRC_PG5N", "SRC_PGOK", "GND", at=(x2 + 68.58, y3 + 22.86),
          desc="Source enable needs PG_5V (delayed): sink released first")
    s.c("100n", "+3V3", "GND", at=(x2 + 139.7, y3), lcsc=C_100N)

    # =============================================================================================
    # 5. VBUS_LAPTOP node: shunt, INA226, local capacitance
    # =============================================================================================
    _note(s, "5. VBUS_LAPTOP MONITOR + CAPACITANCE\n"
           "INA226 on I2C_SYS at 0x44 (A1 = VS, A0 = GND). Shunt 5 mOhm (WSL2512): 5 A -> 25 mV of +-81.92 mV,\n"
           "  0.125 W. Bidirectional: + = sourcing to laptop, - = bus-powered sink. CURRENT_LSB 0.5 mA -> CAL = 2048.\n"
           "  VBUS pin on the connector side (36 V max > 32.6 V backstop). Kelvin-route IN+/IN-. ALERT unused.\n"
           "Capacitance on the connector side (VBUS_LAPTOP + VBUS_LSW, no switch between): 10 uF/50 V + 2x 100 nF\n"
           "  -> ~9 uF at 5 V, ~4 uF at 28 V: within cSnkBulk (1-10 uF) for bus-powered attach.\n"
           "  cSrcBulk (>= 10 uF) is met behind the source switch (VBB_OUT ~220 uF).\n"
           "  VBUS TVS + connector live on usbc_muxes; PMG1 provides VBUS discharge for down-transitions.",
           at=(406.4, 190.5))
    x, y = 421.64, 238.76
    s.r("5m", "VBUS_LSW", "VBUS_LAPTOP", size="1206", at=(x, y), lcsc=R_SNS_5M, mpn="RLM12FTCMR005",
        desc="INA226 shunt 5 mOhm 1 % 1206 1 W")
    s.part("odock:INA226AIDGSR", "U", "INA226", at=(x + 40.64, y),
           pins={"VIN+": "VBUS_LSW", "VIN-": "VBUS_LAPTOP", "VBUS": "VBUS_LAPTOP", "VS+": "+3V3", "GND": "GND",
                 "A1": "+3V3", "A0": "GND", "SDA": "I2C_SYS_SDA", "SCL": "I2C_SYS_SCL"},
           nc=["Alert"], desc="Laptop VBUS current/voltage/power, I2C 0x44")
    s.c("100n", "+3V3", "GND", at=(x + 71.12, y), lcsc=C_100N)
    s.c("10u/50V", "VBUS_LAPTOP", "GND", size="1210", at=(x + 86.36, y), lcsc=C_10U_50V)
    s.c("100n/50V", "VBUS_LAPTOP", "GND", size="0603", at=(x + 99.06, y), lcsc=C_100N_50V)
    s.c("100n/50V", "VBUS_LSW", "GND", size="0603", at=(x + 111.76, y), lcsc=C_100N_50V)

    # =============================================================================================
    # 6. Sink switch VBUS_LAPTOP -> +5V (bus-powered mode)
    # =============================================================================================
    _note(s, "6. BUS-POWER SINK SWITCH  VBUS_LSW -> SNK_MID -> +5V  (only without external power)\n"
           "Stage 1, 60 V blocking: CSD18543Q3A driven by LM74502 (charge pump, 3.2-65 V). Off -> blocks up to 60 V\n"
           "  (VBUS is 28 V when we source); body diode points back to VBUS, reverse handled by stage 2.\n"
           "  OV cut-off 422k/100k -> 6.5 V (6.1-6.9 V), 1 us: a >5 V contract can never reach +5V.\n"
           "Stage 2, TPS259470A eFuse (28 V abs): true reverse-current blocking (+5V never back-feeds VBUS),\n"
           "  ILM 1.0k -> 3.34 A (3.0-3.7 A) active current limit, auto-retry; OVLO 40.2k/10k -> 6.0 V;\n"
           "  UVLO 121k/47k -> 4.3 V; dVdt 3.3 nF -> ~0.6 V/ms (soft start into the +5V bulk); ITIMER 1 nF.\n"
           "ENABLE: SNK_ON = LAPTOP_SNK_EN (10k / 47k) AND NOT (EXT_PWR_PRESENT AND PG5_DLY) AND NOT SRC_ON.\n"
           "  PG5_DLY = SNK_PGD = PG_5V (LM5148 PG, open drain, 100k to 5V_BUCK on power_rails) via 100k/100 nF,\n"
           "  rise delay 2.7-6.7 ms, fast fall through BAT46W: make-before-break hand-over, the sink stays on until\n"
           "  the buck regulates; overlap is safe (+5V OR: TPS259470A reverse blocking + LM74700 ideal diode).\n"
           "  LAPTOP_SNK_EN must be driven from a VBUS-powered domain in dead-battery (PMG1 VDDD from VBUS).\n"
           "Loss at 3 A: 9 x (8 m + 28 m + 5 m shunt) = 0.37 W.",
           at=(406.4, 279.4))
    x, y = 421.64, 337.82
    s.part("odock:CSD18543Q3A", "Q", "CSD18543Q3A", at=(x, y), pins={"D": "VBUS_LSW", "S": "SNK_MID", "G": "SNK_GATE"},
           desc="60 V NFET, sink blocking switch")
    s.part("odock:LM74502DDFR", "U", "LM74502", at=(x + 53.34, y),
           pins={"EN/UVLO": "SNK_ON", "GND": "GND", "VCAP": "SNK_VCAP", "VS": "VBUS_LSW", "GATE": "SNK_GATE",
                 "OV": "SNK_OV", "SRC": "SNK_MID"},
           nc=["N.C"], desc="High-side switch controller with OV, sink stage 1")
    s.part("odock:TPS259470ARPWR", "U", "TPS259470A", at=(x + 116.84, y),
           pins={"EN/UVLO": "SNK_UV", "OVLO/OVCSEL": "SNK_OVLO", "IN": "SNK_MID", "OUT": "+5V", "DVDT": "SNK_DVDT",
                 "GND": "GND", "ILM": "SNK_ILM", "ITIMER": "SNK_ITIMER"},
           nc=["PG/AUXOFF", "~{FLT}/PGTH"], desc="23 V 5.5 A eFuse w/ reverse blocking, sink stage 2")
    x2, y2 = 411.48, 363.22
    s.c("100n/50V", "VBUS_LSW", "GND", size="0603", at=(x2, y2), lcsc=C_100N_50V)
    s.c("100n/50V", "SNK_VCAP", "VBUS_LSW", size="0603", at=(x2 + 12.7, y2), lcsc=C_100N_50V)
    s.r("422k", "VBUS_LSW", "SNK_OV", at=(x2 + 25.4, y2), lcsc=R_422K)
    s.r("100k", "SNK_OV", "GND", at=(x2 + 38.1, y2), lcsc=R_100K)
    s.c("1u/50V", "SNK_MID", "GND", size="0603", at=(x2 + 50.8, y2), lcsc=C_1U_50V)
    s.r("121k", "SNK_MID", "SNK_UV", at=(x2 + 63.5, y2), lcsc=R_121K)
    s.r("47k", "SNK_UV", "GND", at=(x2 + 76.2, y2), lcsc=R_47K)
    s.r("40.2k", "SNK_MID", "SNK_OVLO", at=(x2 + 88.9, y2), lcsc=R_40K2)
    s.r("10k", "SNK_OVLO", "GND", at=(x2 + 101.6, y2), lcsc=R_10K)
    s.r("1k", "SNK_ILM", "GND", at=(x2 + 114.3, y2), lcsc=R_1K)
    s.c("3.3n", "SNK_DVDT", "GND", size="0603", at=(x2 + 127, y2), lcsc=C_3N3)
    s.c("1n", "SNK_ITIMER", "GND", at=(x2 + 139.7, y2), lcsc=C_1N)
    s.c("10u", "+5V", "GND", size="0805", at=(x2 + 152.4, y2), lcsc=C_10U_25V)
    # sink enable logic
    y3 = 398.78
    _nfet(s, "EXT_PWR_PRESENT", "SNK_ON", "SNK_KX", at=(345.44, y3), desc="Sink off with external power ...")
    _nfet(s, "SNK_PGD", "SNK_KX", "GND", at=(345.44, y3 + 25.4), desc="... AND the 5 V buck regulating (PG_5V)")
    s.r("100k", "PG_5V", "SNK_PGD", at=(375.92, y3 + 25.4), lcsc=R_100K, desc="PG_5V release delay")
    s.c("100n", "SNK_PGD", "GND", at=(386.08, y3 + 25.4), lcsc=C_100N, desc="tau 20 ms incl. 100k PG pull-up")
    s.part("Device:D_Schottky", "D", "BAT46W", "Diode_SMD:D_SOD-123", at=(401.32, y3 + 25.4), lcsc=D_BAT46W,
           pins={"A": "SNK_PGD", "K": "PG_5V"}, desc="Fast discharge when PG_5V drops")
    _nfet(s, "SRC_ON", "SNK_ON", "GND", at=(375.92, y3), desc="Interlock: sink off while sourcing")
    s.r("10k", "LAPTOP_SNK_EN", "SNK_ON", at=(391.16, y3), lcsc=R_10K)
    s.r("47k", "SNK_ON", "GND", at=(401.32, y3), lcsc=R_47K)

    # =============================================================================================
    # 7. Independent laptop VBUS OVP (latched)
    # =============================================================================================
    _note(s, "7. INDEPENDENT VBUS OVP (latched)  -> LAPTOP_OVP_N\n"
           "Senses max(VBUS_LAPTOP, VBB_OUT) through BAV70 (100 V): also catches a run-away buck-boost before the\n"
           "  source switch closes. 1.1M/46.4k + 0.45 V diode: trip = 1.242 x 24.7 + 0.45 = 31.1 V (~29.9-32.3 V RSS,\n"
           "  29.3-33.1 V all corners) > 28.7 V max regulation; 2.2 nF -> 98 us filter: a 5 A laptop unplug at 28 V\n"
           "  (~1.2 V overshoot) reaches the comparator as ~0.7 V -> 29.4 V, no false latch. Run-away lag ~2.6 V.\n"
           "TLV3011 (open-drain, internal 1.242 V ref): output pulled up to VBB_EN (10k). On a trip the output\n"
           "  releases, 1N4148W + 4.7k feed back into IN+ (2.0 V > 1.242 V even with VBUS = 0) -> LATCHED.\n"
           "  Q inverts to LAPTOP_OVP_N (10k to +3V3): opens the source switch (SRC_ON AND) and disables the LM51770.\n"
           "RESET only by VBB_EN low (pull-up source gone; converter is then also off and VBB_OUT discharged).\n"
           "Latched, not auto-retry: >30 V on a laptop port means a real fault (FB open, back-feed); retrying would\n"
           "  re-apply it. Clearing needs a deliberate PMG1 VBB_EN cycle, which restarts from the 5.1 V default.",
           at=(215.9, 261.62))
    x, y = 243.84, 309.88
    s.part("Diode:BAV70", "D", "BAV70", "Package_TO_SOT_SMD:SOT-23", at=(x, y), lcsc="C68978",
           pins={"1": "VBUS_LAPTOP", "2": "VBB_OUT", "3": "OVP_TOP"}, desc="Dual diode common cathode 100 V")
    s.r("1.1M", "OVP_TOP", "OVP_DIV", at=(x + 20.32, y), lcsc=R_1M1)
    s.r("46.4k", "OVP_DIV", "GND", at=(x + 30.48, y), lcsc=R_46K4)
    s.c("2.2n", "OVP_DIV", "GND", size="0603", at=(x + 40.64, y), lcsc=C_2N2)
    s.part("odock:TLV3011AIDBVR", "U", "TLV3011", at=(x + 73.66, y),
           pins={"IN+": "OVP_DIV", "IN-": "OVP_REF", "REF": "OVP_REF", "OUT": "OVP_TRIP", "VCC": "+3V3", "GND": "GND"},
           desc="Comparator + 1.242 V reference, open drain")
    s.c("100n", "+3V3", "GND", at=(x + 96.52, y), lcsc=C_100N)
    y += 33.02
    s.r("10k", "OVP_TRIP", "VBB_EN", at=(x, y), lcsc=R_10K, desc="Pull-up to VBB_EN = latch reset")
    s.part("Device:D", "D", "1N4148W", "Diode_SMD:D_SOD-123", at=(x + 22.86, y), lcsc="C81598",
           pins={"A": "OVP_TRIP", "K": "OVP_FB"})
    s.r("4.7k", "OVP_FB", "OVP_DIV", at=(x + 43.18, y), lcsc=R_4K7, desc="Latch feedback")
    _nfet(s, "OVP_TRIP", "LAPTOP_OVP_N", "GND", at=(x + 73.66, y), desc="OVP inverter")
    s.r("10k", "LAPTOP_OVP_N", "+3V3", at=(x + 93.98, y), lcsc=R_10K)

    # PWR_FLAGs: nets fed through FET body diodes / passives (ERC power_pin_not_driven)
    s.flag("SRC_MID")
    s.flag("BB_BIAS")
    s.build()
    return s
