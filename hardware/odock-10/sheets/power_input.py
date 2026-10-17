"""odock-10 — power input sheet: PD-in USB-C (TPS26750 + TPD4S480, EPR sink up to 48 V), barrel jack
(LM74800, reverse/OV/UVLO protection), input OR-ing onto VIN, EXT_PWR_PRESENT generation, INA237 VIN monitor.
Design notes and calculations: docs/design/power_input.md"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "tools", "schgen"))
from schgen import Sheet

# --- part numbers (LCSC) -------------------------------------------------------------------------
R_100K, R_10K, R_1K, R_2K2, R_4K7, R_47K, R_33K, R_15K, R_1M, R_100, R_0 = (
    "C25741", "C25744", "C11702", "C25879", "C25900", "C25792", "C25779", "C25756", "C26083", "C25076", "C17168")
R_7K5 = "C23234"                 # 0603 basic (0402 7.5k is extended)
R_22K = "C25768"                 # extended (1.2M stock)
R_39K = "C23153"                 # 0603 basic (0402 39k is extended)
R_100K_0805 = "C149504"          # 0805 basic, 150 V working voltage (resistors with a terminal on VBUS_PDIN/VBAR)
R_1M_0805 = "C17514"             # 0805 basic, 150 V working voltage
C_1U_100V = "C126585"            # 0805 100 V X7S
C_47U_100V = "C371305"           # SamYoung MVK 47 uF 100 V alu 10x10 (VIN damping)
TVS_PDIN = ("C2990373", "5.0SMDJ51A")   # Liown 5 kW, SMC (DO-214AB): same footprint as SMCJ51A, ~1/3 the dynamic R
TVS_BAR = ("C2649886", "5.0SMDJ48CA")   # Littelfuse 5 kW bidirectional, SMC
C_100N_16V = "C1525"             # 0402 basic
C_100N_50V = "C14663"            # 0603 basic
C_100N_100V = "C28233"           # CL21B104KCFNNNE 100 nF 100 V X7R 0805 (basic; no basic 100 V 0603)
C_220P = "C1603"                 # 0603 50 V basic
C_1U_25V = "C52923"              # 0402 basic
C_10U_10V = "C19702"             # 0603 basic
C_2U2_100V = "C153036"           # 1210 100 V X7R
C_47N_100V = "C576852"           # 0603 100 V X7R
FET = "odock:BSC026N08NS5ATMA1"  # 80 V, 2.6 mOhm, TDSON-8 (C5955453)


def _note(s, text, at):
    """Multi-line note as one text item per line (embedded newlines do not survive schgen's quoting)."""
    for i, line in enumerate(text.split("\n")):
        s.note(line, at=(at[0], round(at[1] + i * 2.54, 2)))


def build(D):
    s = Sheet(D, "power_input.kicad_sch", "odock-10 — Power input (PD-in, barrel, VIN)", ref_base=100, paper="A2")

    # =============================================================================================
    # 1. PD-in USB-C receptacle + protection
    # =============================================================================================
    _note(s, "1. PD-IN USB-C (power only)\n"
           "JAE DX07S024XJ1R1100 (48 V / 5 A EPR-rated, C134113). Only VBUS, CC, GND, shell used:\n"
           "USB2 D+/D-, SBU and SS pins are left open (no data on this port; no BC1.2).\n"
           "Shell tied to GND. 5.0SMDJ51A TVS (5 kW, SMC): VRWM 51 V > 50.4 V EPR max, VBR 56.7-62.7 V,\n"
           "  Rdyn ~0.32 Ohm -> ~64 V at 5 A, ~68 V at 18 A (SMCJ51A: 82 V). Residual risk vs TPD4S480 63 V: see doc.\n"
           "TPD4S480: CC short-to-VBUS (63 V) protection, dead-battery Rd (RPD_Gx tied to C_CCx),\n"
           "VBUS -> VBUS_LV scaler (x0.42 in EPR) so the TPS26750 VBUS pin (22 V max) can sense 48 V.\n"
           "EPR_BLK_G unused (no 5 V source FET: sink-only port). SBU channels unused.",
           at=(20.32, 12.7))
    s.part("odock:DX07S024XJ1R1100", "J", "USB-C PD-in", at=(45.72, 76.2),
           pins={"VBUS": "VBUS_PDIN", "CC1": "PDIN_C_CC1", "CC2": "PDIN_C_CC2", "GND": "GND", "0": "GND"},
           nc=["A2", "A3", "B2", "B3", "A10", "A11", "B10", "B11", "A6", "A7", "B6", "B7", "A8", "B8"],
           desc="USB-C receptacle 24P, 5 A / 48 V, PD-in (power only)")
    s.part("odock:SMCJ51A_C408371", "D", TVS_PDIN[1], at=(91.44, 60.96), pins={"C": "VBUS_PDIN", "A": "GND"},
           lcsc=TVS_PDIN[0], mpn=TVS_PDIN[1], desc="TVS 51 V uni 5 kW (SMC), VBUS_PDIN")
    s.c("2.2u/100V", "VBUS_PDIN", "GND", size="1210", at=(83.82, 81.28), lcsc=C_2U2_100V)
    s.c("100n/100V", "VBUS_PDIN", "GND", size="0805", at=(93.98, 81.28), lcsc=C_100N_100V)
    s.flag("VBUS_PDIN", at=(104.14, 81.28))

    s.part("odock:TPD4S480RUKR_C43131250", "U", "TPD4S480", at=(152.4, 76.2),
           pins={"VBUS": "VBUS_PDIN", "VBUS_LV": "PDIN_VBUS_LV", "EPR_EN": "PDIN_EPR_EN", "VPWR": "PD_LDO_3V3",
                 "VBIAS": "PDIN_VBIAS", "C_CC1": "PDIN_C_CC1", "RPD_G1": "PDIN_C_CC1", "C_CC2": "PDIN_C_CC2",
                 "RPD_G2": "PDIN_C_CC2", "CC1": "PDIN_CC1", "CC2": "PDIN_CC2", "~{FLT}": "PDIN_FLT_N",
                 "GND": "GND", "EP": "GND"},
           nc=["C_SBU1", "C_SBU2", "SBU1", "SBU2", "EPR_BLK_G"], desc="EPR CC/SBU protection + VBUS scaler")
    s.c("100n/100V", "PDIN_VBIAS", "GND", size="0805", at=(124.46, 116.84), lcsc=C_100N_100V)   # VBIAS >=63 V rated
    s.c("1u", "PD_LDO_3V3", "GND", size="0402", at=(134.62, 116.84), lcsc=C_1U_25V)            # VPWR
    s.c("100n/50V", "PDIN_VBUS_LV", "GND", size="0603", at=(144.78, 116.84), lcsc=C_100N_50V)  # VBUS_LV (<=21.2 V)
    s.r("10k", "PDIN_FLT_N", "PD_LDO_3V3", at=(154.94, 116.84), lcsc=R_10K)

    # =============================================================================================
    # 2. TPS26750 PD sink controller + config EEPROM
    # =============================================================================================
    _note(s, "2. TPS26750 EPR SINK CONTROLLER (TI SLVSH67 Fig. 8-24 reference)\n"
           "Powered from +3V3 (VIN_3V3) when the deck runs, else from VBUS via its internal LDO (dead battery).\n"
           "ADCIN1 = ADCIN2 = 100k/100k (decoded 5/5): 'AlwaysEnableSink', I2C target index #2 = 0x21.\n"
           "  Blank EEPROM: sink path closes at 5 V but PD stays off until a host loads a config, and 5 V on VIN\n"
           "  does NOT start the LM5148 (UVLO 8 V). First EEPROM programming needs barrel, laptop bus power or I2Cc pads.\n"
           "  (SafeMode alternative: ADCIN1 -> LDO_3V3, ADCIN2 -> GND = 7/0, address 0x20.)\n"
           "Config/patch from AT24C512C (64 KB >= 36 KB req.) at 0x50 on the private I2Cc bus.\n"
           "  RP2350 updates it through the TPS26750 host interface (I2Ct, 0x21); I2Cc test pads for recovery.\n"
           "GPIO0 = EPR_EN (to TPD4S480), GPIO1 = PDIN_PRESENT (informational only, 47k series: <= 60 uA into an\n"
           "  unpowered PMG1/RP2350 pin; config: high while sink contract active),\n"
           "GPIO2 = TPD4S480 FLT# input, other GPIOs strapped to GND through 100k (datasheet: tie low if unused).\n"
           "PP5V tied to GND: sink-only port, no 5 V sourcing / VCONN (verify with TI).\n"
           "I2C_PD pull-ups live on the MCU sheet; PDIN_INT_N pull-up here.",
           at=(205.74, 12.7))
    s.part("odock:TPS26750SRSMR_C42166327", "U", "TPS26750", at=(271.78, 83.82),
           pins={"VIN_3V3": "+3V3", "LDO_3V3": "PD_LDO_3V3", "LDO_1V5": "PD_LDO_1V5",
                 "VBUS": "PDIN_VBUS_LV", "PP5V": "GND", "CC1": "PDIN_CC1", "CC2": "PDIN_CC2",
                 "ADCIN1": "PD_ADCIN1", "ADCIN2": "PD_ADCIN2",
                 "GPIO0": "PDIN_EPR_EN", "GPIO1": "PDIN_PRES_L", "GPIO2": "PDIN_FLT_N",
                 "GPIO3": "PD_GPIO3", "GPIO4/USB_P/LD1": "PD_GPIO4", "GPIO5/USB_N/LD2": "PD_GPIO5",
                 "GPIO6": "PD_GPIO6", "GPIO7": "PD_GPIO7", "GPIO11": "PD_GPIO11",
                 "I2Ct_SDA": "I2C_PD_SDA", "I2Ct_SCL": "I2C_PD_SCL", "~{I2Ct_IRQ}": "PDIN_INT_N",
                 "I2Cc_SDA": "PD_I2CC_SDA", "I2Cc_SCL": "PD_I2CC_SCL", "~{I2Cc_IRQ}": "PD_I2CC_IRQ_N",
                 "POWER_PATH_EN": "PD_PP_EN_HV", "GND": "GND"},
           nc=["NC"], desc="USB PD 3.1 EPR sink controller")
    # supply decoupling (CVIN_3V3 >=5 uF, CLDO_3V3 5..25 uF, CLDO_1V5 4.5..12 uF)
    x0, y0 = 220.98, 139.7
    s.c("10u", "+3V3", "GND", size="0603", at=(x0, y0), lcsc=C_10U_10V)
    s.c("10u", "PD_LDO_3V3", "GND", size="0603", at=(x0 + 10.16, y0), lcsc=C_10U_10V)
    s.c("10u", "PD_LDO_1V5", "GND", size="0603", at=(x0 + 20.32, y0), lcsc=C_10U_10V)
    s.c("220p", "PDIN_CC1", "GND", size="0603", at=(x0 + 30.48, y0), lcsc=C_220P)
    s.c("220p", "PDIN_CC2", "GND", size="0603", at=(x0 + 40.64, y0), lcsc=C_220P)
    # ADCIN straps 100k/100k -> decoded 5/5
    s.r("100k", "PD_LDO_3V3", "PD_ADCIN1", at=(x0 + 50.8, y0), lcsc=R_100K)
    s.r("100k", "PD_ADCIN1", "GND", at=(x0 + 60.96, y0), lcsc=R_100K)
    s.r("100k", "PD_LDO_3V3", "PD_ADCIN2", at=(x0 + 71.12, y0), lcsc=R_100K)
    s.r("100k", "PD_ADCIN2", "GND", at=(x0 + 81.28, y0), lcsc=R_100K)
    # interrupt / I2Cc pull-ups (LDO_3V3 per datasheet), PDIN_INT_N to +3V3
    s.r("10k", "PDIN_INT_N", "+3V3", at=(x0 + 91.44, y0), lcsc=R_10K)
    s.r("10k", "PD_I2CC_IRQ_N", "PD_LDO_3V3", at=(x0 + 101.6, y0), lcsc=R_10K)
    s.r("4.7k", "PD_I2CC_SDA", "PD_LDO_3V3", at=(x0 + 111.76, y0), lcsc=R_4K7)   # 4.7k: less LDO_3V3 load
    s.r("4.7k", "PD_I2CC_SCL", "PD_LDO_3V3", at=(x0 + 121.92, y0), lcsc=R_4K7)   # during dead-battery EEPROM boot
    # unused GPIOs -> GND through 100k (Hi-Z by default; resistor protects if a config drives them)
    y1 = 180.34
    for i, g in enumerate(["PD_GPIO3", "PD_GPIO4", "PD_GPIO5", "PD_GPIO6", "PD_GPIO7", "PD_GPIO11"]):
        s.r("100k", g, "GND", at=(x0 + i * 10.16, y1), lcsc=R_100K)
    # PDIN_PRESENT: GPIO1, default low. 47k series: GPIO1 can be high (VBUS-LDO powered) while PMG1 P7.2 (not
    # fail-safe) and the RP2350 are unpowered -> (3.3 - 0.5) V / 47k = 60 uA < 0.5 mA PMG1 injection limit.
    s.r("100k", "PDIN_PRES_L", "GND", at=(x0 + 60.96, y1), lcsc=R_100K)
    s.r("47k", "PDIN_PRES_L", "PDIN_PRESENT", at=(x0 + 71.12, y1), lcsc=R_47K)
    s.r("100k", "PDIN_EPR_EN", "GND", at=(x0 + 81.28, y1), lcsc=R_100K)

    s.part("odock:AT24C512C-SSHD-T", "U", "AT24C512C", at=(355.6, 76.2),
           pins={"A0": "GND", "A1": "GND", "A2": "GND", "WP": "GND", "VCC": "PD_LDO_3V3", "GND": "GND",
                 "SDA": "PD_I2CC_SDA", "SCL": "PD_I2CC_SCL"},
           desc="512 Kbit I2C EEPROM, TPS26750 config/patch (0x50)")
    s.c("100n", "PD_LDO_3V3", "GND", at=(345.44, 96.52), lcsc=C_100N_16V)
    s.part("Connector:TestPoint", "TP", "I2Cc_SDA", "TestPoint:TestPoint_Pad_D1.0mm", at=(360.68, 96.52),
           pins={"1": "PD_I2CC_SDA"})
    s.part("Connector:TestPoint", "TP", "I2Cc_SCL", "TestPoint:TestPoint_Pad_D1.0mm", at=(370.84, 96.52),
           pins={"1": "PD_I2CC_SCL"})

    # POWER_PATH_EN buffer (datasheet Fig. 8-5): POWER_PATH_EN is a 6-12 V / 10 uA charge-pump output,
    # buffered by two NFETs into a logic-level PD_SINK_EN (LDO_3V3 domain).
    _note(s, "POWER_PATH_EN BUFFER (Fig. 8-5)\nQ101: inverts POWER_PATH_EN, Q102: PD_SINK_EN (LM74800 EN),\n"
           "Q103: pulls PD_OK low while the sink path is off.", at=(480.06, 154.94))
    xb, yb = 495.3, 180.34
    s.part("Transistor_FET:2N7002", "Q", "2N7002", at=(xb, yb), lcsc="C8545",
           pins={"G": "PD_PP_EN_HV", "D": "PD_PP_EN_INV", "S": "GND"})
    s.part("Transistor_FET:2N7002", "Q", "2N7002", at=(xb + 22.86, yb), lcsc="C8545",
           pins={"G": "PD_PP_EN_INV", "D": "PD_SINK_EN", "S": "GND"})
    s.part("Transistor_FET:2N7002", "Q", "2N7002", at=(xb + 45.72, yb), lcsc="C8545",
           pins={"G": "PD_PP_EN_INV", "D": "PD_OK", "S": "GND"})
    s.r("100k", "PD_PP_EN_INV", "PD_LDO_3V3", at=(xb, yb + 25.4), lcsc=R_100K)
    s.r("100k", "PD_SINK_EN", "PD_LDO_3V3", at=(xb + 22.86, yb + 25.4), lcsc=R_100K)

    # =============================================================================================
    # 3. PD-in sink power path: LM74800 + back-to-back 80 V NFETs -> VIN_OR
    # =============================================================================================
    _note(s, "3. PD-IN SINK PATH  VBUS_PDIN -> VIN_OR\n"
           "LM74800-Q1 ideal diode (Q104, DGATE) + load switch (Q105, HGATE), common drain, 2x BSC026N08NS5 80 V.\n"
           "EN/UVLO = PD_SINK_EN: path closes only when the TPS26750 enables its sink path.\n"
           "OV: 100k/2.2k -> 1.231 V x 102.2/2.2 = 57.2 V (55.5-58.9 V) > 50.4 V EPR max.\n"
           "Inrush: HGATE 55 uA into 47 nF -> 1.17 V/ms; ~0.12 A into <= 100 uF of VIN capacitance.\n"
           "Always armed (no priority): PD-in and barrel are both ideal-diode ORed, the higher voltage feeds VIN.\n"
           "VIN capacitance seen by the PD source <= 100 uF (cSnkBulkPd) incl. downstream converter inputs: see doc.\n"
           "Reverse/backfeed from VIN (barrel or buck-boost) blocked by Q104 (ideal diode).\n"
           "Conduction: 5 A x 2 x 2.6 mOhm = 0.13 W.",
           at=(406.4, 12.7))
    s.part(FET, "Q", "BSC026N08NS5", at=(429.26, 63.5), pins={"S": "VBUS_PDIN", "D": "PD_MID", "G": "PD_DGATE"},
           desc="80 V NFET, PD-in ideal diode")
    s.part(FET, "Q", "BSC026N08NS5", at=(487.68, 63.5), pins={"S": "VIN_OR", "D": "PD_MID", "G": "PD_HGATE"},
           desc="80 V NFET, PD-in load switch")
    s.part("odock:LM74800QDRRRQ1", "U", "LM74800-Q1", at=(457.2, 101.6),
           pins={"DGATE": "PD_DGATE", "A": "VBUS_PDIN", "VSNS": "VBUS_PDIN", "SW": "PD_OV_TOP", "OV": "PD_OV",
                 "EN/UVLO": "PD_SINK_EN", "GND": "GND", "HGATE": "PD_HGATE", "OUT": "VIN_OR", "VS": "PD_MID",
                 "CAP": "PD_CAP", "C": "PD_MID"},
           nc=["RTN"], desc="Ideal diode + load switch controller, PD-in")
    x2, y2 = 419.1, 132.08
    s.c("100n/100V", "PD_MID", "GND", size="0805", at=(x2, y2), lcsc=C_100N_100V)        # VS
    s.c("100n/50V", "PD_CAP", "PD_MID", size="0603", at=(x2 + 10.16, y2), lcsc=C_100N_50V)  # CAP-VS (<15 V)
    s.r("100k", "PD_OV_TOP", "PD_OV", size="0805", at=(x2 + 20.32, y2), lcsc=R_100K_0805)
    s.r("2.2k", "PD_OV", "GND", at=(x2 + 30.48, y2), lcsc=R_2K2)
    s.r("100", "PD_HGATE", "PD_DVDT", at=(x2 + 40.64, y2), lcsc=R_100)
    s.c("47n/100V", "PD_DVDT", "GND", size="0603", at=(x2 + 50.8, y2), lcsc=C_47N_100V)

    # =============================================================================================
    # 4. Barrel jack: LM74800 reverse polarity + OV + UVLO + PD-in priority -> VIN_OR
    # =============================================================================================
    _note(s, "4. BARREL INPUT 9-24 V / 8 A  (Same Sky PJ-063BH, 5.5x2.5 mm, pin 1 = centre +)\n"
           "MS mounting tabs left unconnected (would short to + on a reversed plug if tied to GND).\n"
           "5.0SMDJ48CA bidirectional TVS (5 kW): survives a reversed 24 V and a wrong 48 V brick (VBR 53.3 V min).\n"
           "LM74800-Q1 (same as PD path) instead of LM74720: the LM74720 PD pin pulls the HSFET gate to GND,\n"
           "  i.e. Vgs = -VIN while PD-in holds VIN up; the LM74800 HGATE is referenced to OUT.\n"
           "Q106 = ideal diode (DGATE, blocks reverse polarity to -65 V), Q107 = OV / UVLO / enable cut-off (HGATE).\n"
           "OV: 100k/4.7k -> 1.231 V x 104.7/4.7 = 27.4 V (26.6-28.2 V), recovers at 25.2 V.\n"
           "UVLO: 100k/22k -> 1.231 V x 122/22 = 6.8 V rising, 6.3 V falling.\n"
           "NO hardware PD-in priority: barrel and PD-in are both always-armed ideal diodes, the higher voltage\n"
           "  supplies VIN, so a hand-over never collapses VIN. Source preference = firmware policy (request a PD\n"
           "  voltage above the barrel to prefer PD-in). Divider tops on VBAR/SW are 0805 (150 V).\n"
           "Inrush: HGATE 55 uA into 47 nF -> 1.17 V/ms. Conduction: 8.3 A x 2 x 2.6 mOhm = 0.36 W.",
           at=(20.32, 198.12))
    s.part("odock:PJ-063BH_C3095900", "J", "PJ-063BH", at=(30.48, 254.0),
           pins={"1": "VBAR", "2": "GND"}, nc=["0"], desc="DC jack 5.5x2.5 mm, 8 A")
    s.part("odock:SMCJ48CA_C408370", "D", TVS_BAR[1], at=(63.5, 246.38), pins={"1": "VBAR", "2": "GND"},
           lcsc=TVS_BAR[0], mpn=TVS_BAR[1], desc="TVS 48 V bidirectional 5 kW (SMC), barrel")
    s.c("100n/100V", "VBAR", "GND", size="0805", at=(78.74, 261.62), lcsc=C_100N_100V)
    s.part(FET, "Q", "BSC026N08NS5", at=(116.84, 246.38), pins={"S": "VBAR", "D": "BAR_MID", "G": "BAR_DGATE"},
           desc="80 V NFET, barrel ideal diode")
    s.part(FET, "Q", "BSC026N08NS5", at=(175.26, 246.38), pins={"S": "VIN_OR", "D": "BAR_MID", "G": "BAR_HGATE"},
           desc="80 V NFET, barrel OV/UVLO/enable switch")
    s.part("odock:LM74800QDRRRQ1", "U", "LM74800-Q1", at=(147.32, 284.48),
           pins={"DGATE": "BAR_DGATE", "A": "VBAR", "VSNS": "VBAR", "SW": "BAR_SW", "OV": "BAR_OV",
                 "EN/UVLO": "BAR_EN", "GND": "GND", "HGATE": "BAR_HGATE", "OUT": "VIN_OR", "VS": "BAR_MID",
                 "CAP": "BAR_CAP", "C": "BAR_MID"},
           nc=["RTN"], desc="Ideal diode + load switch controller, barrel (RTN pad floating per datasheet)")
    x3, y3 = 195.58, 271.78
    s.c("100n/100V", "BAR_MID", "GND", size="0805", at=(x3, y3), lcsc=C_100N_100V)        # VS
    s.c("100n/50V", "BAR_CAP", "BAR_MID", size="0603", at=(x3 + 10.16, y3), lcsc=C_100N_50V)  # CAP-VS
    s.r("100", "BAR_HGATE", "BAR_DVDT", at=(x3 + 20.32, y3), lcsc=R_100)
    s.c("47n/100V", "BAR_DVDT", "GND", size="0603", at=(x3 + 30.48, y3), lcsc=C_47N_100V)
    s.r("100k", "BAR_SW", "BAR_OV", size="0805", at=(x3, y3 + 35.56), lcsc=R_100K_0805)
    s.r("4.7k", "BAR_OV", "GND", at=(x3 + 10.16, y3 + 35.56), lcsc=R_4K7)
    s.r("100k", "VBAR", "BAR_EN", size="0805", at=(x3 + 20.32, y3 + 35.56), lcsc=R_100K_0805)
    s.r("22k", "BAR_EN", "GND", at=(x3 + 30.48, y3 + 35.56), lcsc=R_22K)

    # =============================================================================================
    # 5. EXT_PWR_PRESENT: input-side detection (not VIN, which can be back-fed)
    # =============================================================================================
    _note(s, "5. EXT_PWR_PRESENT = BAR_OK OR PD_OK  (from the input side, never from VIN)\n"
           "Meaning: VIN is (or is about to be) supplied >= ~8 V by PD-in or barrel. Both paths are always armed, so\n"
           "  either OK term implies that input actually feeds VIN (no priority shutdown can make it lie).\n"
           "BAR_OK: TLV6700 window on VBAR (via 1N4148W, blocks reverse polarity), 1M/39k/15k ladder (0805 top):\n"
           "  UV = 0.4 x 1054/54 + 0.4 = 8.2 V (8.0-8.5 V: a 9 V -5 % brick counts), OV = 0.4 x 1054/15 + 0.4 = 28.5 V.\n"
           "PD_OK: TLV6700 window on VBUS_PDIN, 1M/47k/7.5k: UV 7.7 V, OV 56.2 V, AND sink path on (Q103).\n"
           "  A 5 V-only PD contract therefore does NOT count as external power.\n"
           "The laptop sink switch is released only when EXT_PWR_PRESENT AND PG_5V (power_laptop), so a\n"
           "  slightly early EXT_PWR_PRESENT (VIN still ramping) never browns out the deck.\n"
           "Open-drain outputs wired-AND per source, pull-ups to +3V3; 74LVC1G32 OR -> EXT_PWR_PRESENT.\n"
           "All of it runs from +3V3, which exists whenever anything powers the deck.",
           at=(287.02, 198.12))
    x4, y4 = 304.8, 248.92
    s.part("odock:TLV6700DDCR", "U", "TLV6700", at=(x4 + 15.24, y4),
           pins={"VDD": "+3V3", "GND": "GND", "INA+": "BAR_MON_UV", "INB-": "BAR_MON_OV",
                 "OUTA": "BAR_OK", "OUTB": "BAR_OK"}, desc="Window comparator, barrel present")
    s.part("Device:D", "D", "1N4148W", "Diode_SMD:D_SOD-123", at=(x4 - 30.48, y4 + 27.94), lcsc="C81598",
           pins={"A": "VBAR", "K": "BAR_MON_TOP"})
    s.r("1M", "BAR_MON_TOP", "BAR_MON_UV", size="0805", at=(x4, y4 + 27.94), lcsc=R_1M_0805)
    s.r("39k", "BAR_MON_UV", "BAR_MON_OV", size="0603", at=(x4 + 10.16, y4 + 27.94), lcsc=R_39K)
    s.r("15k", "BAR_MON_OV", "GND", at=(x4 + 20.32, y4 + 27.94), lcsc=R_15K)
    s.r("100k", "BAR_OK", "+3V3", at=(x4 + 30.48, y4 + 27.94), lcsc=R_100K)
    s.c("100n", "+3V3", "GND", at=(x4 + 40.64, y4 + 27.94), lcsc=C_100N_16V)

    x5 = 383.54
    s.part("odock:TLV6700DDCR", "U", "TLV6700", at=(x5 + 15.24, y4),
           pins={"VDD": "+3V3", "GND": "GND", "INA+": "PD_MON_UV", "INB-": "PD_MON_OV",
                 "OUTA": "PD_OK", "OUTB": "PD_OK"}, desc="Window comparator, PD-in VBUS present")
    s.r("1M", "VBUS_PDIN", "PD_MON_UV", size="0805", at=(x5, y4 + 27.94), lcsc=R_1M_0805)
    s.r("47k", "PD_MON_UV", "PD_MON_OV", at=(x5 + 10.16, y4 + 27.94), lcsc=R_47K)
    s.r("7.5k", "PD_MON_OV", "GND", size="0603", at=(x5 + 20.32, y4 + 27.94), lcsc=R_7K5)
    s.r("100k", "PD_OK", "+3V3", at=(x5 + 30.48, y4 + 27.94), lcsc=R_100K)
    s.c("100n", "+3V3", "GND", at=(x5 + 40.64, y4 + 27.94), lcsc=C_100N_16V)

    s.part("74xGxx:74LVC1G32", "U", "SN74LVC1G32", "Package_TO_SOT_SMD:SOT-23-5", at=(480.06, 254.0),
           lcsc="C10096", pins={"1": "BAR_OK", "2": "PD_OK", "4": "EXT_PWR_PRESENT", "5": "+3V3", "3": "GND"},
           desc="Single 2-input OR")
    s.c("100n", "+3V3", "GND", at=(472.44, 287.02), lcsc=C_100N_16V)

    # =============================================================================================
    # 6. VIN: OR node, shunt, bulk capacitance, INA237 monitor
    # =============================================================================================
    _note(s, "6. VIN (9-50 V)  VIN_OR -> 2 mOhm shunt -> VIN\n"
           "INA237 (85 V CM, 16-bit, pin-compatible with INA228/INA238) on I2C_SYS at 0x45 (A1 = A0 = VS).\n"
           "  Shunt 2 mOhm 2512 1 %: 8.3 A -> 16.6 mV, 0.14 W; ADCRANGE=1 (+-40.96 mV) -> +-20.5 A FS,\n"
           "  CURRENT_LSB = 20.48 A / 2^15 = 625 uA. Bidirectional: shows backfeed too. Kelvin-route IN+/IN-.\n"
           "  INA237AIDGSR C2864837 (JLC stock 5k). ALERT unused.\n"
           "VIN capacitance budget (USB PD cSnkBulkPd <= 100 uF, everything the PD source charges when the sink path\n"
           "  is on): here 47 uF/100 V alu (damping, ESR ~0.1-0.6 Ohm) + 1 uF/100 V + 100 nF; power_laptop and\n"
           "  power_rails 4x 4.7 uF/100 V each (no electrolytics there). Total ~90 uF at 20 V, <= 99 uF at 5 V worst.\n"
           "  The 47 uF R-C branch damps cable L vs the converter ceramics: peak Zout <= 0.5 Ohm << Zin,min 1.35 Ohm.",
           at=(20.32, 340.36))
    x6, y6 = 30.48, 393.7
    s.part("Device:C_Polarized", "C", "47u/100V", "Capacitor_SMD:CP_Elec_10x10", at=(x6, y6),
           pins={"1": "VIN", "2": "GND"}, lcsc=C_47U_100V,
           desc="Alu 47 uF 100 V, VIN damping (only electrolytic on VIN: cSnkBulkPd budget)")
    s.c("1u/100V", "VIN", "GND", size="0805", at=(x6 + 50.8, y6), lcsc=C_1U_100V)
    s.c("100n/100V", "VIN", "GND", size="0805", at=(x6 + 60.96, y6), lcsc=C_100N_100V)
    s.r("2m", "VIN_OR", "VIN", size="2512", at=(x6 + 101.6, y6), lcsc="C459679",
        mpn="RLP25FEGR002", desc="Shunt 2 mOhm 1 % 2512, VIN current")
    s.part("odock:INA237AIDGSR", "U", "INA237", at=(x6 + 147.32, y6),
           pins={"10": "VIN_OR", "9": "VIN", "VBUS": "VIN", "VS": "+3V3", "GND": "GND", "A0": "+3V3",
                 "A1": "+3V3", "SDA": "I2C_SYS_SDA", "SCL": "I2C_SYS_SCL"},
           nc=["ALERT"], desc="85 V power monitor, VIN")
    s.c("100n", "+3V3", "GND", at=(x6 + 180.34, y6), lcsc=C_100N_16V)
    s.flag("VIN", at=(x6 + 200.66, y6))
    s.flag("VBAR", at=(x6 + 210.82, y6))

    # PWR_FLAGs: nets fed through FET body diodes / passives (ERC power_pin_not_driven)
    s.flag("GND")
    s.flag("PD_MID")
    s.flag("BAR_MID")
    s.build()
    # PWR_FLAG (#FLG) symbols are virtual and never appear in the exported netlist: don't verify them
    # (schgen.verify() should skip '#' references; workaround kept local to this sheet).
    s.expected = {k: v for k, v in s.expected.items() if not k[0].startswith("#")}
    return s
