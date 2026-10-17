"""odock-10 — Ethernet sheet: Realtek RTL8156BG-CG (USB 3.2 Gen1 -> 2.5GBASE-T) on hub port 4, switched 3.3 V
(ETH_RESET_N = PHY power-cycle), external 0.95 V core buck enabled by POW_EXT_SWR, 25 MHz crystal, USAKRO 2.5G magjack
with green/yellow LEDs, buffered LED outputs to the RP2350, EUI-48 MAC EEPROM and an isolatable I2C bridge for writing
the MAC into the PHY's eFuse.
Design notes: docs/design/ethernet.md"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "tools", "schgen"))
from schgen import Sheet

# --- part numbers (LCSC) -------------------------------------------------------------------------
# basic parts
R_0, R_510, R_4K7, R_10K, R_100K = "C17168", "C25123", "C25900", "C25744", "C25741"
C_20P, C_1N, C_100N, C_220N = "C1554", "C1523", "C1525", "C16772"
C_1U, C_2U2, C_4U7, C_10U, C_22U = "C52923", "C12530", "C23733", "C19702", "C59461"   # 0402 / 0402 / 0402 / 0603 10V / 0603 6.3V
BEAD = "C1015"                     # Sunlord GZ2012D101TF 100 Ohm@100 MHz 0805 (basic)
XTAL_25M = "C9006"                 # YXC X322525MOB4SI 25 MHz 3225, CL 12 pF, +-10 ppm, ESR 50 Ohm (same as hub)
# extended parts
R_2K49 = "C25884"                  # 2.49k 1 % 0402 (RSET)
R_59K = "C32297"                   # 59k 1 % 0402 (0.95 V FB top)
C_390P = "C282239"                 # Yageo CC0402JRNPO9BN391 390 pF C0G 50 V 0402 (same part as pd_pmg1 CC caps)
PHY = "C41376388"                  # Realtek RTL8156BG-CG QFN-56 6x6 0.35 mm
BUCK = "C5820994"                  # TI TPS62A02ADRLR 2 A forced-PWM 2.4 MHz buck, SOT-563
L_1U = "C91250"                    # Sunlord SWPA4018S1R0NT 1 uH 4x4x1.8 mm
LSW = "C131941"                    # TI TPS22918DBVR 2 A load switch, CT slew + QOD
BUF = "C68245"                     # TI SN74LVC3G17DCUR triple Schmitt buffer, VSSOP-8
EEPROM = "C129895"                 # Microchip 24AA025E48T-I/OT 2 kbit EEPROM with EUI-48, SOT-23-6
QDUAL = "C154900"                  # Diodes BSS138DW-7-F dual N-MOSFET SOT-363 (VGS(th) 0.5-1.5 V; same pinout as 2N7002DW-7-F)
BUF_ST = "C151394"                 # Diodes 74LVC1G17W5-7 Schmitt buffer SOT-25 (bridge gate driver, VCC = ETH_3V3)
RJ45 = "C19725134"                 # USAKRO DGUK211Q340CD2A4D2 2.5G magjack, tab-up, green/yellow LEDs


def _note(s, text, at, size=1.27):
    """Multi-line note as one text item per line (embedded newlines do not survive schgen's quoting)."""
    for i, line in enumerate(text.split("\n")):
        s.note(line, at=(at[0], round(at[1] + i * 2.54, 2)), size=size)


def build(D):
    s = Sheet(D, "ethernet.kicad_sch", "odock-10 — 2.5 GbE (RTL8156BG)", ref_base=800, paper="A2")

    # =============================================================================================
    # 1. RTL8156BG
    # =============================================================================================
    _note(s, "1. RTL8156BG-CG  USB 3.2 Gen1 (5G) <-> 2.5GBASE-T MAC/PHY, QFN-56 6x6 0.35 mm, EP = GND (via array)", (20.32, 15.24), 2.0)
    s.part("odock:RTL8156BG-CG", "U", "RTL8156BG-CG", at=(101.6, 101.6), lcsc=PHY,
           pins={
               # power: 3.3 V domain = ETH_3V3 (switched), 0.95 V domain = ETH_0V95 (external buck)
               "9": "ETH_AVDD33_PLL", "AVDD33_XTAL": "ETH_3V3", "17": "ETH_3V3", "21": "ETH_3V3", "25": "ETH_3V3",
               "DVDD33": "ETH_3V3", "U2VDD33": "ETH_3V3", "DVDD33_UPS": "ETH_3V3",
               "AVDD09": "ETH_0V95", "DVDD09": "ETH_0V95", "U3VDD09": "ETH_0V95", "U2VDD09": "ETH_0V95",
               "DVDD09_UPS": "ETH_0V95_UPS", "GND": "GND",
               "POW_EXT_SWR": "ETH_SWR_EN",
               # USB: hub TX -> PHY RX direct (caps on usb_hub); PHY TX -> 220 nF here -> hub RX
               "U3SSRXP": "ETH_SS_TXP", "U3SSRXN": "ETH_SS_TXN",
               "U3SSTXP": "ETH_TXP_IC", "U3SSTXN": "ETH_TXN_IC",
               "U2DP": "ETH_DP", "U2DM": "ETH_DN",
               # clock / bias
               "CKXTAL1": "ETH_XI", "CKXTAL2": "ETH_XO", "RSET": "ETH_RSET",
               # MDI
               "MDIP0": "ETH_MDI0_P", "MDIN0": "ETH_MDI0_N", "MDIP1": "ETH_MDI1_P", "MDIN1": "ETH_MDI1_N",
               "MDIP2": "ETH_MDI2_P", "MDIN2": "ETH_MDI2_N", "MDIP3": "ETH_MDI3_P", "MDIN3": "ETH_MDI3_N",
               # LEDs (active low by default) / straps
               "LED0/EEDI/SPISI": "ETH_LED0_N", "LED1/EESK/SPISCK": "ETH_LED1_N", "LED2": "ETH_LED2_N",
               "EECS/TWSI_SCL": "ETH_EECS",
               "GPI": "ETH_GPI", "LANWAKEB": "ETH_LANWAKE_N", "DOCK_DET": "ETH_DOCK_DET",
               "CONFIG_SEQ": "ETH_CFG_SEQ", "GPIO4": "ETH_GPIO4",
               # I2C slave (MACID programming) -> bridge to I2C_SYS
               "GPIO1/SDA": "ETH_SDA", "GPIO2/SCL": "ETH_SCL",
           },
           nc=["3", "4", "6", "CKOUT", "LED3", "GPIO3", "EEDO/SPISO", "TWSI_SDA/SPICSB"],
           desc="USB 3.0 to 10/100/1000/2500M Ethernet controller; needs external 0.95 V (BG variant)")
    _note(s, "Pin 9 (AVDD33 next to the XTAL) is fed through a ferrite bead (PLL supply, Realtek ref 'AVDD33_PLL').\n"
             "DVDD09_UPS (54) is an INTERNAL LDO output: 1 uF only, never tie to the 0.95 V rail.\n"
             "NC: 3/4/6 (BGS-only regulator pins), CKOUT, LED3, GPIO3, EEDO/SPISO, TWSI_SDA/SPICSB (no EEPROM/flash on the PHY).",
          (20.32, 167.64))

    # =============================================================================================
    # 2. Power: switched 3.3 V (ETH_RESET_N) + 0.95 V core buck
    # =============================================================================================
    x0, y0 = 203.2, 22.86
    _note(s, "2. POWER  ETH_3V3 = +3V3 via TPS22918 (ON = ETH_RESET_N)   ETH_0V95 = TPS62A02A (EN = POW_EXT_SWR)", (x0, y0), 2.0)
    y = y0 + 20.32
    s.part("odock:TPS22918DBVR", "U", "TPS22918", "Package_TO_SOT_SMD:SOT-23-6", at=(x0 + 15.24, y),
           pins={"VIN": "+3V3", "GND": "GND", "ON": "ETH_RESET_N", "CT": "ETH_LSW_CT", "QOD": "ETH_3V3",
                 "VOUT": "ETH_3V3"}, lcsc=LSW,
           desc="PHY 3.3 V load switch = PHY reset: ETH_RESET_N low -> PHY unpowered (QOD discharges ETH_3V3)")
    s.c("1u", "+3V3", "GND", at=(x0 + 38.1, y), lcsc=C_1U, desc="load switch input cap")
    s.c("1n", "ETH_LSW_CT", "GND", at=(x0 + 48.26, y), lcsc=C_1N, desc="CT 1 nF -> ETH_3V3 rise ~1.7 ms (PHY t1 0.5-10 ms)")
    s.c("10u", "ETH_3V3", "GND", at=(x0 + 58.42, y), size="0603", lcsc=C_10U, desc="ETH_3V3 bulk")
    s.part("Device:FerriteBead", "FB", "100R@100MHz", "Inductor_SMD:L_0805_2012Metric", at=(x0 + 71.12, y),
           pins={"1": "ETH_3V3", "2": "ETH_AVDD33_PLL"}, lcsc=BEAD, desc="PLL AVDD33 (pin 9) filter")
    s.c("22u", "ETH_AVDD33_PLL", "GND", at=(x0 + 81.28, y), size="0603", lcsc=C_22U, desc="pin 9 bulk (Realtek ref 22 uF)")
    s.c("100n", "ETH_AVDD33_PLL", "GND", at=(x0 + 91.44, y), lcsc=C_100N, desc="pin 9, at the pin")
    y = y0 + 45.72
    s.part("odock:TPS62A02ADRLR", "U", "TPS62A02A", at=(x0 + 15.24, y),
           pins={"VIN": "ETH_3V3", "GND": "GND", "EN": "ETH_SWR_EN", "SW": "ETH_SW", "FB": "ETH_FB"},
           nc=["PG"], lcsc=BUCK, desc="0.95 V / 0.65 A max core buck, forced PWM 2.4 MHz, 1 ms soft start")
    s.r("100k", "ETH_SWR_EN", "GND", at=(x0 + 33.02, y), lcsc=R_100K, desc="EN pull-down: buck off until POW_EXT_SWR = 1")
    s.c("10u", "ETH_3V3", "GND", at=(x0 + 43.18, y), size="0603", lcsc=C_10U, desc="buck input, at VIN/GND pins")
    s.c("100n", "ETH_3V3", "GND", at=(x0 + 53.34, y), lcsc=C_100N, desc="buck input HF")
    s.part("Device:L", "L", "1uH", "Inductor_SMD:L_Sunlord_SWPA4018S", at=(x0 + 63.5, y),
           pins={"1": "ETH_SW", "2": "ETH_0V95"}, lcsc=L_1U, desc="1 uH (TI matrix for 0.6-1.2 V: 1 uH + 2x22 uF)")
    s.r("59k", "ETH_0V95", "ETH_FB", at=(x0 + 73.66, y), lcsc=R_59K, desc="FB top 59k 1 %")
    s.r("100k", "ETH_FB", "GND", at=(x0 + 83.82, y), lcsc=R_100K, desc="FB bottom 100k 1 % -> 0.6 x 1.59 = 0.954 V")
    s.c("22u", "ETH_0V95", "GND", at=(x0 + 93.98, y), size="0603", lcsc=C_22U, desc="buck output")
    s.c("22u", "ETH_0V95", "GND", at=(x0 + 104.14, y), size="0603", lcsc=C_22U, desc="buck output")
    _note(s, "RTL8156BG 0.95 V: 0.92-0.98 V (+-3 %), 364 mA typ / 650 mA max; rise 0.5-2.2 ms; off->on >= 50 ms (DS table 25/27).\n"
             "VOUT = 0.6 V x (1 + 59k/100k) = 0.954 V; VFB +-1.5 % + 1 % resistors -> 0.932-0.977 V worst case (inside window).\n"
             "TPS62A02A = forced-PWM variant (Realtek: switcher feeding the PHY must run PWM >= 1 MHz); 1 ms soft start meets t3.\n"
             "The buck runs from ETH_3V3, so ETH_RESET_N low also kills 0.95 V; EN = POW_EXT_SWR (PHY output, 100k PD).\n"
             "ETH_RESET_N (TCA9534 P5 on mcu, 10k PU there): high/hi-Z = PHY powered -> Ethernet works with a dead/blank RP2350.\n"
             "  Firmware: hold low >= 100 ms (t4 >= 50 ms + QOD discharge). Also usable to turn 2.5GbE off for thermal derating.\n"
             "Loss: 0.95 V x 0.65 A / ~85 % -> ~0.11 W in the buck; PHY total ~0.6-0.65 W typ (sensors sheet: TMP1075 'RJ45/RTL8156').",
          (x0, y0 + 58.42))

    # =============================================================================================
    # 3. Decoupling
    # =============================================================================================
    x0, y0 = 20.32, 190.5
    _note(s, "3. DECOUPLING  every cap at its pin (0402, short via to the GND EP/plane); bulk per Realtek reference", (x0, y0), 2.0)
    y = y0 + 20.32
    caps33 = [("100n", C_100N, "AVDD33_XTAL pin 10"), ("2.2u", C_2U2, "AVDD33_XTAL pin 10 (ref 2.2 uF)"),
              ("100n", C_100N, "AVDD33 pin 17"), ("100n", C_100N, "AVDD33 pin 21"), ("100n", C_100N, "AVDD33 pin 25"),
              ("2.2u", C_2U2, "AVDD33 bulk (ref 2x 2.2 uF)"), ("2.2u", C_2U2, "AVDD33 bulk"),
              ("100n", C_100N, "DVDD33 pin 36"), ("100n", C_100N, "U2VDD33 pin 51"), ("100n", C_100N, "DVDD33_UPS pin 55")]
    for i, (v, l, d) in enumerate(caps33):
        s.c(v, "ETH_3V3", "GND", at=(x0 + i * 10.16, y), lcsc=l, desc=d)
    y = y0 + 40.64
    caps09 = [("2.2u", C_2U2, "AVDD09 pin 13"), ("2.2u", C_2U2, "AVDD09 pin 18"), ("2.2u", C_2U2, "AVDD09 pin 24"),
              ("100n", C_100N, "DVDD09 pin 7"), ("100n", C_100N, "DVDD09 pin 31"), ("100n", C_100N, "DVDD09 pin 56"),
              ("2.2u", C_2U2, "DVDD09 pin 56 (ref 2.2 uF)"), ("10u", C_10U, "DVDD09 bulk (ref 10 uF)"),
              ("10u", C_10U, "DVDD09 bulk"),
              ("100n", C_100N, "U3VDD09 pin 42"), ("2.2u", C_2U2, "U3VDD09 pin 42"), ("100n", C_100N, "U2VDD09 pin 52")]
    for i, (v, l, d) in enumerate(caps09):
        s.c(v, "ETH_0V95", "GND", at=(x0 + i * 10.16, y), size="0603" if v == "10u" else "0402", lcsc=l, desc=d)
    s.c("1u", "ETH_0V95_UPS", "GND", at=(x0 + 12 * 10.16, y), lcsc=C_1U, desc="DVDD09_UPS pin 54 (internal LDO, isolated)")

    # =============================================================================================
    # 4. Clock, bias, straps
    # =============================================================================================
    x0, y0 = 203.2, 106.68
    _note(s, "4. CLOCK / RSET / STRAPS (pull values from Realtek RTL8125B ref + verified open RTL8156B design)", (x0, y0), 2.0)
    y = y0 + 20.32
    s.part("Device:Crystal_GND24", "Y", "25MHz", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", at=(x0 + 10.16, y),
           pins={"1": "ETH_XI", "3": "ETH_XO_X", "2": "GND", "4": "GND"}, lcsc=XTAL_25M,
           desc="25 MHz SMD crystal (PHY: +-50 ppm all-in, ESR <= 70 Ohm, DL <= 0.5 mW)")
    s.c("20p", "ETH_XI", "GND", at=(x0 + 27.94, y), lcsc=C_20P, desc="CL = (20+~3)/2 = 11.5 pF")
    s.c("20p", "ETH_XO_X", "GND", at=(x0 + 38.1, y), lcsc=C_20P)
    s.r("0", "ETH_XO_X", "ETH_XO", at=(x0 + 48.26, y), lcsc=R_0,
        desc="CKXTAL2 series R (Realtek R27): 0R, tune for crystal drive level")
    s.r("2.49k", "ETH_RSET", "GND", at=(x0 + 58.42, y), lcsc=R_2K49, desc="RSET 2.49k 1 %, at pin 14 (Realtek)")
    y = y0 + 40.64
    straps = [("4.7k", "ETH_GPI", "ETH_3V3", "GPI pull-up (LAN-disable input if enabled in eFuse)"),
              ("4.7k", "ETH_LANWAKE_N", "ETH_3V3", "LANWAKEB open-drain pull-up (unused)"),
              ("4.7k", "ETH_DOCK_DET", "ETH_3V3", "DOCK_DET high = 'docked' (no self-reset)"),
              ("4.7k", "ETH_GPIO4", "ETH_3V3", "GPIO4 pull-up (unused)"),
              ("4.7k", "ETH_LED0_N", "ETH_3V3", "LED0/EEDI strap pull-up + LED idle level"),
              ("4.7k", "ETH_LED1_N", "ETH_3V3", "LED1/EESK strap pull-up (Realtek 'PU for normal application')"),
              ("10k", "ETH_LED2_N", "ETH_3V3", "LED2 idle level (LED pins float when off)"),
              ("4.7k", "ETH_EECS", "GND", "EECS/TWSI_SCL pull-down (no EEPROM)")]
    for i, (v, a, b, d) in enumerate(straps):
        s.r(v, a, b, at=(x0 + i * 10.16, y), lcsc=R_4K7 if v == "4.7k" else R_10K, desc=d)
    s.r("10k", "ETH_CFG_SEQ", "GND", at=(x0 + 81.28, y), lcsc=R_10K,
        desc="CONFIG_SEQ low: config 1 = CDC-NCM, 2 = ECM, 3 = RTK (only if enabled in eFuse)")
    s.r("10k", "ETH_CFG_SEQ", "ETH_3V3", at=(x0 + 91.44, y), lcsc=R_10K, dnp=True,
        desc="CONFIG_SEQ high option: config 1 = RTK vendor (DNP)")
    _note(s, "Straps/pulls go to ETH_3V3 (never +3V3) so nothing back-powers the PHY while ETH_RESET_N holds it off.\n"
             "Crystal: same YXC 25 MHz/12 pF part as the hub (shared reel). Keep XI/XO short, GND guard, no traces under it.",
          (x0, y0 + 55.88))

    # =============================================================================================
    # 5. USB 3 TX AC coupling
    # =============================================================================================
    x0, y0 = 406.4, 22.86
    _note(s, "5. USB  PHY TX -> 100 nF -> hub RX (hub TX caps on usb_hub)", (x0, y0), 2.0)
    y = y0 + 17.78
    s.c("100n", "ETH_TXP_IC", "ETH_SS_RXP", at=(x0 + 10.16, y), lcsc=C_100N, desc="PHY TX+ AC cap (USB 3.x Gen1 TX: 75-200 nF)")
    s.c("100n", "ETH_TXN_IC", "ETH_SS_RXN", at=(x0 + 25.4, y), lcsc=C_100N, desc="PHY TX- AC cap")
    _note(s, "Hub port 4 (ETH_*): longest SS run on the board (around the hub's PF side). 90 Ohm diff, caps near the PHY,\n"
             "symmetric, L2 void under the 0402 pads. USB2 ETH_DP/DN: 90 Ohm, no series parts. The PHY is Gen1 (5 Gbps):\n"
             "Gen1 C_AC_COUPLING = 75-200 nF -> 100 nF (same as the GL3224 TX); 220 nF is only valid for Gen2 transmitters.",
          (x0, y0 + 27.94))

    # =============================================================================================
    # 6. MDI / magjack
    # =============================================================================================
    x0, y0 = 406.4, 63.5
    _note(s, "6. MDI + MAGJACK  USAKRO DGUK211Q340CD2A4D2 (2.5G, LEDs)", (x0, y0), 2.0)
    y = y0 + 25.4
    s.part("odock:DGUK211Q340CD2A4D2", "J", "RJ45 2.5G", at=(x0 + 20.32, y), lcsc=RJ45,
           pins={"TD1+": "ETH_MDI0_P", "TD1-": "ETH_MDI0_N", "TD2+": "ETH_MDI1_P", "TD2-": "ETH_MDI1_N",
                 "TD3+": "ETH_MDI2_P", "TD3-": "ETH_MDI2_N", "TD4+": "ETH_MDI3_P", "TD4-": "ETH_MDI3_N",
                 "CT": "ETH_MCT",
                 "LED_G+": "ETH_3V3", "LED_G-": "ETH_LEDG_K", "LED_Y+": "ETH_3V3", "LED_Y-": "ETH_LEDY_K",
                 "SHELL": "GND"},
           desc="RJ45 with 2.5G magnetics and 2 LEDs, THT, tab-up")
    s.c("390p", "ETH_MCT", "GND", at=(x0 + 50.8, y), lcsc=C_390P,
        desc="PHY-side centre taps: 390 pF (Realtek RTL8125B-series ref; 2.5G voltage-mode driver)")
    s.c("100n", "ETH_MCT", "GND", at=(x0 + 60.96, y), lcsc=C_100N, dnp=True,
        desc="alt. CT cap (gigabit-style 100 nF), DNP")
    s.r("510", "ETH_LEDG_K", "ETH_LED0_N", at=(x0 + 71.12, y), lcsc=R_510, desc="green LED (left) from LED0, ~2.5 mA")
    s.r("510", "ETH_LEDY_K", "ETH_LED1_N", at=(x0 + 81.28, y), lcsc=R_510, desc="yellow LED (right) from LED1, ~3 mA")
    _note(s, "MDIx -> TDx+1: MDI0=BI_DA (RJ 1/2), MDI1=BI_DB (3/6), MDI2=BI_DC (4/5), MDI3=BI_DD (7/8). 100 Ohm diff pairs, length-\n"
             "  matched within pair, no vias if possible, no planes under the magjack's cable side. If the QFN-to-jack order forces\n"
             "  crossings use the PHY's MDI-swap option (eFuse/register) instead of vias.\n"
             "Jack: 1CT:1CT 2.5G magnetics, 4x75R + 1nF/2kV Bob Smith inside, green LED left / yellow right (pins 14/13, 12/11).\n"
             "No extra ESD on MDI: the magnetics give 2250 VDC isolation and the Realtek reference has none.\n"
             "Shell -> GND (odock convention: no separate chassis; via-stitch both shell pins). LEDs are low-side driven by the PHY\n"
             "  (LED anode at ETH_3V3, active-low pins, Realtek default); function per LED set by eFuse/driver (OCP 0xDD90).",
          (x0, y0 + 50.8))

    # =============================================================================================
    # 7. LED buffer to RP2350
    # =============================================================================================
    x0, y0 = 406.4, 139.7
    _note(s, "7. LED BUFFER  SN74LVC3G17 -> ETH_LED0..2 (RP2350)", (x0, y0), 2.0)
    y = y0 + 20.32
    s.part("odock:SN74LVC3G17DCUR", "U", "SN74LVC3G17", at=(x0 + 17.78, y), lcsc=BUF,
           pins={"VCC": "+3V3", "GND": "GND", "1A": "ETH_LED0_N", "1Y": "ETH_LED0", "2A": "ETH_LED1_N",
                 "2Y": "ETH_LED1", "3A": "ETH_LED2_N", "3Y": "ETH_LED2"},
           desc="buffers PHY LED pins (which also drive the jack LEDs) for the MCU")
    s.c("100n", "+3V3", "GND", at=(x0 + 40.64, y), lcsc=C_100N, desc="buffer decoupling")
    _note(s, "ETH_LEDx = PHY LEDx level, i.e. ACTIVE LOW (low = LED lit) with the default LED polarity. The jack LEDs load LED0/1,\n"
             "  so the RP2350 must not read those pins directly; the buffers also isolate the MCU from the switched PHY rail.\n"
             "PHY unpowered (ETH_RESET_N low): inputs sit at 0 V (pull-ups on the dead ETH_3V3) -> outputs low; firmware ignores them.\n"
             "LVC inputs are 5.5 V tolerant with no clamp to VCC, so they never back-power ETH_3V3.",
          (x0, y0 + 33.02))

    # =============================================================================================
    # 8. MAC address: EUI-48 EEPROM + I2C bridge to the PHY's I2C slave
    # =============================================================================================
    x0, y0 = 203.2, 190.5
    _note(s, "8. MAC ADDRESS  24AA025E48 (EUI-48 at 0xFA-0xFF, I2C_SYS 0x50) + switchable bridge to the PHY I2C slave", (x0, y0), 2.0)
    y = y0 + 22.86
    s.part("odock:24AA025E48T-I_OT", "U", "24AA025E48T-I/OT", "Package_TO_SOT_SMD:SOT-23-6", at=(x0 + 15.24, y),
           pins={"VCC": "+3V3", "VSS": "GND", "SDA": "I2C_SYS_SDA", "SCL": "I2C_SYS_SCL", "A0": "GND", "A1": "GND"},
           lcsc=EEPROM, desc="2 kbit I2C EEPROM with factory EUI-48, addr 0x50 (A2 bit = 0, A1 = A0 = GND)")
    s.c("100n", "+3V3", "GND", at=(x0 + 33.02, y), lcsc=C_100N, desc="EEPROM decoupling")
    s.part("Transistor_FET:Q_Dual_NMOS_S1G1D2S2G2D1", "Q", "BSS138DW", "Package_TO_SOT_SMD:SOT-363_SC-70-6",
           at=(x0 + 50.8, y), lcsc=QDUAL, unit=None, mpn="BSS138DW-7-F",
           pins={"1": "ETH_SDA", "2": "ETH_BR_G", "6": "I2C_SYS_SDA",
                 "4": "ETH_SCL", "5": "ETH_BR_G", "3": "I2C_SYS_SCL"},
           desc="I2C bridge: source = PHY side (pulled to ETH_3V3), drain = I2C_SYS, gates = ETH_BR_G")
    s.r("4.7k", "ETH_SDA", "ETH_3V3", at=(x0 + 111.76, y), lcsc=R_4K7, desc="PHY SDA (GPIO1) pull-up")
    s.r("4.7k", "ETH_SCL", "ETH_3V3", at=(x0 + 121.92, y), lcsc=R_4K7, desc="PHY SCL (GPIO2) pull-up")
    s.r("100k", "ETH_I2C_EN", "GND", at=(x0 + 132.08, y), lcsc=R_100K,
        desc="bridge off by default: TCA9534 P6 is an input (Hi-Z) until firmware configures it")
    _note(s, "RTL8156BG MAC sources (DS 6.4/6.6): internal eFuse/OTP (>= 512 B autoload) or an external 93C46/TWSI EEPROM, the latter\n"
             "  only after a Realtek PG-tool eFuse command selects it; blank eFuse -> chip defaults (no unique MAC). DS 6.6: 'MACID can be\n"
             "  modified via the I2C function' = I2C SLAVE on GPIO1/SDA + GPIO2/SCL, 36-byte 'OTP code': [addr] 25 C0 00 MAC0..MAC5 + 26x 00\n"
             "  (= eFuse autoload record 'write 6 bytes to OCP 0xC000 / PLA_IDR'). The 7-bit slave address is not in the DS -> bench scan.\n"
             "Plan: RP2350 reads the EUI-48 from U805 (0x50, 0xFA..0xFF), powers the PHY, sets ETH_I2C_EN, writes the OTP code ONCE (eFuse is\n"
             "  one-time; each rewrite burns ~36 B of the 512 B), clears ETH_I2C_EN and logs it. Fallbacks: host tool (Realtek PG tool /\n"
             "  rtunicpg) programs the same EUI-48 over USB (RP2350 reports it in the status app), or the OS overrides the MAC at runtime.\n"
             "Bridge: with the gates low the PHY can see I2C_SYS traffic (body diodes) but can never pull I2C_SYS low, and an unpowered PHY\n"
             "  is not back-fed. Gate drive ETH_BR_G = 74LVC1G17 powered from ETH_3V3, input ETH_I2C_EN (TCA9534 P6): the gates can only\n"
             "  be high while ETH_3V3 is up (driver unpowered -> Ioff, 100k holds the gates low; VOH <= ETH_3V3 while it decays, QOD\n"
             "  takes it to 0 V). So ETH_I2C_EN = 1 with ETH_RESET_N = 0 (firmware bug, thermal power-down mid-write) can no longer drag\n"
             "  I2C_SYS into the dead PHY pull-ups and lock the TCA9534 that controls both (review mcu_ui #5). Firmware should still\n"
             "  clear P6 before powering the PHY down.  Q801 = BSS138DW (VGS(th) <= 1.5 V) for solid conduction with a 3.3 V gate.\n"
             "Bench items (review data #5): scan I2C_SYS with the bridge on vs off (PHY address, collisions with 0x20/0x41/0x44/0x45/\n"
             "  0x48-0x4F/0x50); confirm the OTP write persists (write once, power-cycle via ETH_RESET_N, read PLA_IDR over USB) and that\n"
             "  the slave answers on a blank eFuse. Volatile write -> rely on the host-tool / OS fallbacks.",
          (x0, y0 + 35.56))

    # =============================================================================================
    # 9. Layout notes
    # =============================================================================================
    _note(s, "9. LAYOUT  (board-layout.md: RJ45 back-right corner, RTL8156BG + MAC EEPROM in front of it)\n"
             "  - QFN-56 0.35 mm pitch (0.15 mm pads, 0.2 mm gaps): JLC 6-layer OK; EP 4.5 mm in DS, imported footprint has 4.7 mm -> check.\n"
             "  - Buck (U, L, 2x22u) within 10 mm of the QFN; 0.95 V as a short pour on L1/L3; SW node small, away from MDI and XTAL.\n"
             "  - TMP1075 'RJ45/RTL8156' (sensors sheet) between the QFN and the magjack. PHY theta-JA 19 C/W (4L ref board) -> +12 K.\n"
             "  - MDI pairs over unbroken GND (L2), stop the planes 1.5 mm before the magjack's cable-side pins (Bob Smith is inside).",
          (20.32, 337.82))

    # PWR_FLAGs: load-switched / filtered / regulator-output rails
    s.flag("ETH_AVDD33_PLL")
    s.flag("ETH_0V95")
    # Bridge gate driver (review mcu_ui #5) - placed last so earlier references keep their numbers
    y = 213.36
    s.part("74xGxx:74LVC1G17", "U", "74LVC1G17", "Package_TO_SOT_SMD:SOT-23-5", at=(284.48, y),
           pins={"2": "ETH_I2C_EN", "4": "ETH_BR_G", "5": "ETH_3V3", "3": "GND"}, nc=["1"], lcsc=BUF_ST,
           mpn="74LVC1G17W5-7",
           desc="Bridge gate driver powered from ETH_3V3: gates = ETH_I2C_EN AND ETH_3V3 present (Ioff input)")
    s.c("100n", "ETH_3V3", "GND", at=(299.72, y), lcsc=C_100N, desc="gate driver decoupling")
    s.r("100k", "ETH_BR_G", "GND", at=(345.44, y), lcsc=R_100K,
        desc="bridge gates low while the gate driver is unpowered (ETH_3V3 off)")

    s.build()
    return s
