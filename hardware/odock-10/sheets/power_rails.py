"""odock-10 — power rails sheet: +5V main rail (LM5148 buck from VIN, 9-50 V -> 5.13 V / 8 A) with an
ideal-diode output (LM74700 + NFET) that blocks bus-power backfeed into VIN, INA226 on the +5V rail,
+3V3 (TPS62933) and +1V15 hub core (TPS62933P) from +5V, sequencing and power-good.
Design notes and calculations: docs/design/power_rails.md"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "tools", "schgen"))
from schgen import Sheet

# --- part numbers (LCSC) -------------------------------------------------------------------------
# basic parts
R_0, R_10K, R_12K, R_100K = "C17168", "C25744", "C25752", "C25741"
R_39K_0603 = "C23153"             # 39k 1 % 0603 (0402 39k is extended)
C_100P, C_1N, C_10N, C_22N = "C1546", "C1523", "C15195", "C1532"
C_100N_16V, C_100N_50V, C_1U_25V = "C1525", "C14663", "C52923"
C_4U7_16V, C_10U_25V, C_22U_25V, C_22U_6V3 = "C19666", "C15850", "C45783", "C59461"
# extended parts
R_73K2, R_14K3, R_64K9, R_41K2 = "C26986", "C25855", "C26984", "C100420"
R_31K6, R_4K42 = "C11463", "C52269"
R_100K_0805 = "C149504"           # 0805W8F1003T5E basic, VIN-side divider resistor, 150 V working voltage
R_4M_2512 = "C459681"             # RLP25FEGR004, 4 mOhm 1 % 2512 (LM5148 current sense)
R_2M_2512 = "C459679"             # RLP25FEGR002, 2 mOhm 1 % 2512 (INA226 shunt)
C_4U7_100V = "C697607"            # HMK325C7475KN-TE 4.7 uF 100 V X7S 1210
C_1U_100V = "C126585"             # GCM21BC72A105KE36L 1 uF 100 V X7S 0805
C_100N_100V = "C28233"            # CL21B104KCFNNNE 100 nF 100 V X7R 0805 (basic)
C_47U_10V = "C84494"              # GRM32ER71A476KE15L 47 uF 10 V X7R 1210
C_330U_POLY = "C54321566"         # 330 uF 6.3 V polymer, 6.3x6 (+5V hold-up)
D_BAT46W = "C83152"               # BAT46W-7-F 100 V Schottky SOD-123


def _note(s, text, at, size=1.27):
    """Multi-line note as one text item per line (embedded newlines do not survive schgen's quoting)."""
    for i, line in enumerate(text.split("\n")):
        s.note(line, at=(at[0], round(at[1] + i * 2.54, 2)), size=size)


def build(D):
    s = Sheet(D, "power_rails.kicad_sch", "odock-10 — Power rails (+5V / +3V3 / +1V15)", ref_base=300, paper="A2")

    # =============================================================================================
    # 1. +5V main buck: LM5148, VIN 9-50 V -> 5V_BUCK 5.13 V / 8 A, 300 kHz
    # =============================================================================================
    _note(s, "1. +5V MAIN BUCK  LM5148 (80 V sync buck controller)  VIN 9-50 V -> 5V_BUCK = 5.13 V, 8 A, fsw 300 kHz", (20.32, 22.86), 2.0)

    # input capacitors (VIN reaches 50.4 V; TVS clamps on power_input are >60 V -> 100 V parts).
    # No electrolytic: VIN capacitance is budgeted to <= 100 uF for USB PD (cSnkBulkPd); the one 47 uF damping
    # alu for the whole VIN node sits on power_input.
    y = 50.8
    for i in range(4):
        s.c("4.7u/100V", "VIN", "GND", size="1210", at=(38.1 + i * 12.7, y), lcsc=C_4U7_100V)
    for i in range(2):
        s.c("100n/100V", "VIN", "GND", size="0805", at=(88.9 + i * 12.7, y), lcsc=C_100N_100V,
            desc="HF decoupling at Q301 drain")

    # power stage
    s.part("odock:BSZ070N08LS5", "Q", "BSZ070N08LS5", at=(132.08, 50.8),
           pins={"S": "5V_SW", "G": "5V_HG", "D": "VIN"}, desc="HS FET 80 V 9.4 mOhm@4.5 V, Qsw 6.9 nC")
    s.part("odock:BSC0805LS", "Q", "BSC0805LS", at=(132.08, 83.82),
           pins={"S": "GND", "G": "5V_LG", "D": "5V_SW", "EP": "5V_SW"}, desc="LS FET 100 V 8.5 mOhm@4.5 V")
    s.r("0", "5V_HO", "5V_HG", at=(160.02, 50.8), lcsc=R_0, desc="HO gate resistor placeholder (tune ringing)")
    s.c("100n", "5V_BOOT", "5V_SW", at=(170.18, 50.8), lcsc=C_100N_16V, desc="CBOOT")
    s.r("2.2", "5V_SW", "5V_SNB", size="0805", at=(160.02, 83.82), dnp=True, lcsc="C17521", desc="SW RC snubber (DNP, tune)")
    s.c("1n/100V", "5V_SNB", "GND", size="0603", at=(170.18, 83.82), dnp=True, lcsc="C106247", desc="SW RC snubber (DNP, tune)")
    s.part("odock:MWSA1206S-4R7MT", "L", "4.7u", at=(195.58, 66.04),
           pins={"1": "5V_SW", "2": "5V_ISNS"}, desc="4.7 uH 15 A Irms / 24 A Isat, 9 mOhm")
    s.r("4m", "5V_ISNS", "5V_BUCK", size="2512", at=(215.9, 66.04), lcsc=R_4M_2512,
        desc="Current sense 4 mOhm 1 % (Kelvin to ISNS+/VOUT)")
    for i in range(6):
        s.c("47u/10V", "5V_BUCK", "GND", size="1210", at=(231.14 + i * 12.7, 66.04), lcsc=C_47U_10V)

    # controller
    s.part("odock:LM5148RGYR", "U", "LM5148", at=(101.6, 144.78),
           pins={"VIN": "5V_VINC", "EN": "5V_EN", "VCC": "5V_VCC", "VCCX": "5V_BUCK",
                 "VDDA": "5V_VDDA", "AGND": "GND", "PGND": "GND", "EP": "GND", "NC": "GND",
                 "RT": "5V_RT", "CNFG": "5V_CNFG", "FB": "5V_FB", "EXTCOMP": "5V_COMP",
                 "HO": "5V_HO", "LO": "5V_LG", "SW": "5V_SW", "CBOOT": "5V_BOOT",
                 "ISNS+": "5V_ISNS", "VOUT": "5V_BUCK", "PG/SYNCOUT": "PG_5V", "PFM/SYNC": "5V_VDDA"},
           desc="80 V synchronous buck controller")

    y = 195.58
    s.part("Device:D_Schottky", "D", "BAT46W", "Diode_SMD:D_SOD-123", at=(30.48, y),
           pins={"A": "VIN", "K": "5V_VINC"}, lcsc=D_BAT46W,
           desc="Blocks VOUT->VIN ESD-diode discharge into a collapsing VIN (TI SNVSC01 8.3.1)")
    s.c("1u/100V", "5V_VINC", "GND", size="0805", at=(48.26, y), lcsc=C_1U_100V)
    s.r("100k", "VIN", "5V_EN", size="0805", at=(58.42, y), lcsc=R_100K_0805, desc="UVLO RUV1")
    s.r("14.3k", "5V_EN", "GND", at=(68.58, y), lcsc=R_14K3, desc="UVLO RUV2: on 8.0 V / off 7.0 V")
    s.c("4.7u", "5V_VCC", "GND", size="0603", at=(78.74, y), lcsc=C_4U7_16V, desc="CVCC")
    s.c("100n", "5V_VDDA", "GND", at=(88.9, y), lcsc=C_100N_16V, desc="CVDDA")
    s.r("73.2k", "5V_RT", "GND", at=(99.06, y), lcsc=R_73K2, desc="RT: 299 kHz")
    s.r("41.2k", "5V_CNFG", "GND", at=(109.22, y), lcsc=R_41K2, desc="CNFG: primary, DRSS spread spectrum on")
    s.r("64.9k", "5V_BUCK", "5V_FB", at=(119.38, y), lcsc=R_64K9, desc="RFB1")
    s.r("12k", "5V_FB", "GND", at=(129.54, y), lcsc=R_12K, desc="RFB2: 0.8*(1+64.9/12) = 5.127 V")
    s.r("10k", "5V_COMP", "5V_CC", at=(139.7, y), lcsc=R_10K, desc="RCOMP")
    s.c("10n", "5V_CC", "GND", at=(149.86, y), lcsc=C_10N, desc="CCOMP")
    s.c("100p", "5V_COMP", "GND", at=(160.02, y), lcsc=C_100P, desc="CHF")
    s.r("100k", "5V_BUCK", "PG_5V", at=(170.18, y), lcsc=R_100K,
        desc="PG pull-up to own output: an unpowered LM5148 cannot hold PG low, 5V_BUCK = 0 V then")

    _note(s, "fsw = 1e6/(45*73.2k+53) = 299 kHz; tON at 50.4 V = 340 ns >> 50 ns min; dropout below ~5.3 V (VIN UVLO is 8 V).\n"
             "L = 4.7 uH: dI = 3.25 A p-p at 48 V, 2.7 A at 20 V. Slope comp: L_ideal = Vo*Rs/(24*f) = 2.85 uH -> 1.65x (stable).\n"
             "Rs = 4 mOhm, VCS-TH 49/60/73 mV -> peak limit 12.3/15/18.3 A, DC >= 10.6 A at 48 V; short-circuit peak 18.7 A < 24 A Isat.\n"
             "Comp (gm 1.2 mS, Gcs 10): RCOMP 10k, CCOMP 10n (zero 1.6 kHz), CHF 100p (pole 159 kHz).\n"
             "  fc = 18 kHz with ~430 uF total (+5V bulk + ceramics); 52 kHz with buck-side ceramics only (~150 uF) - both < fsw/5.\n"
             "PFM/SYNC = VDDA: diode emulation, no negative inductor current (cannot pump +5V energy back into VIN).\n"
             "VCCX = own output (> 4.3 V): gate drive from 5 V instead of the VIN LDO (saves ~0.5 W at 48 V).\n"
             "Loss at 8 A: ~2.6 W (20 V in, 94 %), ~3.6 W (48 V in, 92 %); incl. OR-FET + INA shunt: 93.3 % / 91.4 %.",
          (20.32, 210.82))

    # =============================================================================================
    # 2. Ideal-diode output OR-ing (backfeed block) + INA226 monitor
    # =============================================================================================
    _note(s, "2. BACKFEED BLOCK  5V_BUCK -> ideal diode (LM74700 + BSC0901NS) -> 5V_OR -> 2 mOhm shunt -> +5V", (20.32, 241.3), 2.0)
    y = 271.78
    s.part("odock:BSC0901NS", "Q", "BSC0901NS", at=(50.8, y),
           pins={"S": "5V_BUCK", "G": "5V_ORG", "D": "5V_OR"}, desc="OR FET 30 V 2.4 mOhm@4.5 V (source = buck side)")
    s.part("odock:LM74700QDBVTQ1", "U", "LM74700-Q1", at=(101.6, y),
           pins={"ANODE": "5V_BUCK", "CATHODE": "5V_OR", "GATE": "5V_ORG", "VCAP": "5V_VCAP",
                 "EN": "5V_BUCK", "GND": "GND"}, desc="Ideal diode controller, 20 mV regulation, <0.75 us reverse turn-off")
    s.c("100n/50V", "5V_VCAP", "5V_BUCK", size="0603", at=(134.62, y), lcsc=C_100N_50V, desc="VCAP (to ANODE)")
    s.c("100n/50V", "5V_OR", "GND", size="0603", at=(147.32, y), lcsc=C_100N_50V, desc="CATHODE min 0.1 uF")
    s.r("2m", "5V_OR", "+5V", size="2512", at=(160.02, y), lcsc=R_2M_2512, desc="INA226 shunt 2 mOhm 1 %")
    s.part("odock:INA226AIDGSR", "U", "INA226", at=(205.74, y),
           pins={"VIN+": "5V_OR", "VIN-": "+5V", "VBUS": "+5V", "VS+": "+3V3", "GND": "GND",
                 "A1": "GND", "A0": "+3V3", "SDA": "I2C_SYS_SDA", "SCL": "I2C_SYS_SCL"},
           nc=["Alert"], desc="Buck output current/voltage/power, I2C 0x41")
    s.c("100n", "+3V3", "GND", at=(238.76, y), lcsc=C_100N_16V)
    s.part("Device:C_Polarized", "C", "330u/6.3V", "Capacitor_SMD:CP_Elec_6.3x5.9", at=(254.0, y),
           pins={"1": "+5V", "2": "GND"}, lcsc=C_330U_POLY, desc="Polymer 330 uF, +5V hold-up / loop bulk")
    for i in range(2):
        s.c("22u", "+5V", "GND", size="0805", at=(264.16 + i * 10.16, y), lcsc=C_22U_25V)
    s.flag("+5V", at=(289.56, y))

    _note(s, "PROBLEM: in bus-powered mode +5V is fed from laptop VBUS (sink switch, power_laptop sheet) while VIN is absent.\n"
             "A plain sync buck would conduct +5V -> L -> Q301 body diode -> VIN (~4.3 V on VIN, which would also wake the\n"
             "LM51770 buck-boost at its 3.5 V UVLO and the LM5148's VOUT->VIN ESD diode would conduct too).\n"
             "FIX: the buck regulates its own node 5V_BUCK; LM74700 + Q303 form an ideal diode 5V_BUCK -> +5V.\n"
             "  VIN absent: LM74700 unpowered (ANODE ~0 V), Q303 off, its body diode reverse-biased -> zero reverse current.\n"
             "  Buck running: Q303 regulated to 20 mV forward drop (0.16 W at 8 A); reverse current -> gate pulled in <0.75 us.\n"
             "  Nothing on this sheet ties VIN-side pins to +5V (FB, VCCX, VOUT/ISNS+, PG pull-up all on 5V_BUCK).\n"
             "  VIN at a few volts: EN/UVLO divider keeps the LM5148 off below 7.0-8.0 V, D301 isolates its VIN pin.\n"
             "Handover: external power arrives -> buck soft-starts (3 ms) into 5V_BUCK -> diode conducts once 5V_BUCK > +5V,\n"
             "  +5V rises 5.0 -> 5.11 V; PG_5V (global, open drain, 100k to 5V_BUCK = 5.1 V level) goes high and, after a\n"
             "  2.7-6.7 ms RC on power_laptop, opens the sink switch (EXT_PWR_PRESENT AND PG_5V). Make-before-break.\n"
             "  PG_5V pull-up is deliberately 5V_BUCK, not +3V3/+5V: those exist while the LM5148 is unpowered (open-drain\n"
             "  PG floating) and would read 'good' exactly in the hand-over window. Do not feed PG_5V to 3.3 V-only inputs.\n"
             "  Loss of VIN: +5V held by 330 uF + ceramics.\n"
             "INA226 @ 0x41 (A1=GND, A0=VS): 2 mOhm, 8 A = 16 mV of +-81.92 mV FS; CURRENT_LSB 0.5 mA -> CAL = 5120.\n"
             "  Measures buck output only; bus-powered +5V current is seen by the laptop-VBUS INA226 (power_laptop).\n"
             "  ALERT unused (firmware polls); I2C pull-ups live on the MCU sheet.",
          (20.32, 292.1))

    # =============================================================================================
    # 3. +3V3 rail: TPS62933, +5V -> 3.33 V / 3 A, 1.2 MHz
    # =============================================================================================
    x0 = 340.36
    _note(s, "3. +3V3  TPS62933F forced-PWM (3.8-30 V in, 3 A)  +5V -> 3.33 V, 1.2 MHz", (x0, 22.86), 2.0)
    y = 53.34
    s.c("10u", "+5V", "GND", size="0805", at=(x0, y), lcsc=C_10U_25V)
    s.c("10u", "+5V", "GND", size="0805", at=(x0 + 10.16, y), lcsc=C_10U_25V)
    s.c("100n", "+5V", "GND", at=(x0 + 20.32, y), lcsc=C_100N_16V)
    s.r("100k", "+5V", "3V3_EN", at=(x0 + 30.48, y), lcsc=R_100K, desc="EN divider: on at 4.31 V")
    s.r("39k", "3V3_EN", "GND", size="0603", at=(x0 + 40.64, y), lcsc=R_39K_0603)
    s.part("odock:TPS62933DRLR", "U", "TPS62933F", at=(x0 + 71.12, y),
           pins={"VIN": "+5V", "EN": "3V3_EN", "RT": "GND", "SS": "3V3_SS", "FB": "3V3_FB",
                 "BST": "3V3_BST", "SW": "3V3_SW", "GND": "GND"}, lcsc="C5219272", mpn="TPS62933FDRLR",
           desc="3 A sync buck, forced PWM (RTL8156BG needs >=1 MHz PWM supply), RT=GND -> 1.2 MHz; same pinout as TPS62933")
    s.c("22n", "3V3_SS", "GND", at=(x0 + 101.6, y), lcsc=C_22N, desc="tSS = 22n*0.8/5.5u = 3.2 ms")
    s.c("100n", "3V3_BST", "3V3_SW", at=(x0 + 111.76, y), lcsc=C_100N_16V, desc="CBST")
    s.part("odock:MWSA0503S-2R2MT", "L", "2.2u", at=(x0 + 132.08, y + 15.24),
           pins={"1": "3V3_SW", "2": "+3V3"}, desc="2.2 uH 7 A, 29 mOhm")
    s.r("31.6k", "+3V3", "3V3_FB", at=(x0 + 152.4, y), lcsc=R_31K6, desc="RFBT")
    s.r("10k", "3V3_FB", "GND", at=(x0 + 162.56, y), lcsc=R_10K, desc="RFBB: 0.8*(1+3.16) = 3.33 V")
    for i in range(3):
        s.c("22u", "+3V3", "GND", size="0805", at=(x0 + 172.72 + i * 10.16, y), lcsc=C_22U_25V)
    s.flag("+3V3", at=(x0 + 210.82, y))
    _note(s, "dI = 3.33*(1-3.33/5.13)/(2.2u*1.2M) = 0.44 A p-p (15 % of 3 A). Cout 3x22 uF (~35 uF eff. at 3.3 V; TI table: 30 uF typ, 10 uF min).\n"
             "Soft start 3.2 ms (3.9 ms worst): inside RTL8156BG 3.3 V rise 0.5-10 ms and USB7206C <= 5 ms.\n"
             "EN divider 100k/39k: starts at +5V > 4.31 V (stops ~4.0 V) so a sagging bus-powered +5V cannot half-start the rail.\n"
             "Load ~1.5 A typ / 2.2 A max (hub VDD33, RTL8156BG, muxes, PMG1, RP2350, LCD, SD cards): ~0.3-0.7 W loss.",
          (x0, 96.52))

    # =============================================================================================
    # 4. +1V15 hub core: TPS62933P, +5V -> 1.154 V / 3 A (2 A design), enabled by +3V3, PG out
    # =============================================================================================
    _note(s, "4. +1V15  USB7206C VCORE (1.09-1.21 V, 1.15 V nom.)  TPS62933P  +5V -> 1.154 V, 1.2 MHz", (x0, 132.08), 2.0)
    y = 162.56
    s.c("10u", "+5V", "GND", size="0805", at=(x0, y), lcsc=C_10U_25V)
    s.c("10u", "+5V", "GND", size="0805", at=(x0 + 10.16, y), lcsc=C_10U_25V)
    s.c("100n", "+5V", "GND", at=(x0 + 20.32, y), lcsc=C_100N_16V)
    s.r("12k", "+3V3", "1V15_EN", at=(x0 + 30.48, y), lcsc=R_12K, desc="EN from +3V3: on at 2.66 V (2.82 V max)")
    s.r("10k", "1V15_EN", "GND", at=(x0 + 40.64, y), lcsc=R_10K)
    s.part("odock:TPS62933PDRLR", "U", "TPS62933P", at=(x0 + 71.12, y),
           pins={"VIN": "+5V", "EN": "1V15_EN", "RT": "GND", "PG": "RAILS_PG", "FB": "1V15_FB",
                 "BST": "1V15_BST", "SW": "1V15_SW", "GND": "GND"}, desc="3 A sync buck with PG, 2 ms internal SS")
    s.r("100k", "RAILS_PG", "+3V3", at=(x0 + 101.6, y), lcsc=R_100K, desc="PG pull-up")
    s.c("100n", "1V15_BST", "1V15_SW", at=(x0 + 111.76, y), lcsc=C_100N_16V, desc="CBST")
    s.part("odock:MWSA0503S-1R5MT", "L", "1.5u", at=(x0 + 132.08, y + 15.24),
           pins={"1": "1V15_SW", "2": "+1V15"}, desc="1.5 uH 8.2 A, 25 mOhm")
    s.r("4.42k", "+1V15", "1V15_FB", at=(x0 + 152.4, y), lcsc=R_4K42, desc="RFBT")
    s.r("10k", "1V15_FB", "GND", at=(x0 + 162.56, y), lcsc=R_10K, desc="RFBB: 0.8*(1+0.442) = 1.154 V")
    for i in range(4):
        s.c("22u", "+1V15", "GND", size="0603", at=(x0 + 172.72 + i * 10.16, y), lcsc=C_22U_6V3)
    s.flag("+1V15", at=(x0 + 220.98, y))
    _note(s, "USB7206C (DS00003850F): VCORE 1.09-1.21 V; ~1.31 A with all 5 ports at 10G (410 mA + 179 mA/port). 1.154 V +-1.5 % -> 1.137-1.171 V.\n"
             "Sequencing (sec. 9.6.1): VCORE rises after or with VDD33 -> EN from +3V3 divider; rise times <= 5 ms -> fixed 2 ms SS.\n"
             "dI = 1.15*(1-1.15/5.13)/(1.5u*1.2M) = 0.50 A p-p (17 % of 3 A, >10 % min for PCM). Cout 4x22 uF (+ hub 9x4.7 uF).\n"
             "RAILS_PG (open drain, 100k to +3V3): high only when +1V15 is in regulation, which implies +3V3 is up.\n"
             "  GLOBAL NET (nets.py): wire-ORed onto HUB_RESET_N on usb_hub through a Schottky (hub held in reset until VCORE good).",
          (x0, 205.74))

    # =============================================================================================
    # 5. rails not on this sheet
    # =============================================================================================
    _note(s, "5. RAILS NOT CREATED HERE\n"
             "+1V1: not needed. RP2350 core (DVDD 1.1 V) comes from its internal switching regulator (VREG_VIN from +3V3).\n"
             "RTL8156BG (non-S) has NO internal regulator: it needs an external 0.95 V (0.92-0.98 V, <= 650 mA) buck that it\n"
             "  enables itself via pin 5 POW_EXT_SWR (rise 0.5-2.2 ms). Only the RTL8156BGS has REG_OUT, and it is not stocked.\n"
             "  -> place a dedicated 0.95 V buck (e.g. TLV62569 from +3V3, EN = POW_EXT_SWR) on the ethernet sheet.\n"
             "GL3224: single 5 V supply (4.75-5.25 V) on its VBUS pin, internal 3.3 V / 1.2 V regulators -> fed from +5V.\n"
             "Sequencing: hub needs VCORE >= after VDD33 (done here); RTL8156BG sequences its own 0.95 V; GL3224 needs none.",
          (x0, 241.3))

    # PWR_FLAGs: nets fed through FET body diodes / passives (ERC power_pin_not_driven)
    s.flag("5V_VINC")
    s.flag("5V_BUCK")
    s.build()
    # PWR_FLAG (#FLG) symbols are virtual and never appear in the exported netlist: don't verify them
    s.expected = {k: v for k, v in s.expected.items() if not k[0].startswith("#")}
    return s
