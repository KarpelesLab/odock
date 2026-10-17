"""odock-10 — card reader sheet: Genesys GL3224-ONY04 (USB 3.1 Gen1, 2 LUN, ROM firmware) on hub port 1, full-size SD
(Hanbo SD-111, push-push, WP switch) on slot 1, microSD (Hirose DM3AT, push-push) on slot 2. Single +5V supply, internal
5->3.3 V / 3.3->1.2 V regulators and card power switches, 25 MHz crystal, GL3224 TX AC caps, card detect + activity to RP2350.
Design notes: docs/design/card_reader.md"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "tools", "schgen"))
from schgen import Sheet

# --- part numbers (LCSC) -------------------------------------------------------------------------
# basic parts
R_1K, R_10K = "C11702", "C25744"                                   # 0402 1 %
C_20P, C_100N, C_1U, C_2U2, C_4U7 = "C1554", "C1525", "C52923", "C12530", "C23733"   # 0402
C_10U_0603, C_10U_0805 = "C19702", "C15850"                        # 0603 10 V / 0805 25 V X5R
XTAL_25M = "C9006"           # YXC X322525MOB4SI 25 MHz 3225, CL 12 pF, +-10 ppm (same as usb_hub)
LED_G = "C2297"              # KENTO KT-0805G green 0805 (DNP, bench activity LED)
# extended parts
R_680_1PCT = "C23228"        # UNI-ROYAL 0603WAF6800T5E 680 Ohm 1 % 0603 basic (RTERM)
CR_IC = "C157358"            # Genesys GL3224-ONY04 QFN-48 7x7
SD_SOCKET = "C410353"        # Hanbo SD-111 full-size SD, push-push, CD + WP switches
USD_SOCKET = "C114218"       # Hirose DM3AT-SF-PEJM5 microSD, push-push, normally-open detect switch


def _note(s, text, at, size=1.27):
    """Multi-line note as one text item per line (embedded newlines do not survive schgen's quoting)."""
    for i, line in enumerate(text.split("\n")):
        s.note(line, at=(at[0], round(at[1] + i * 2.54, 2)), size=size)


def build(D):
    s = Sheet(D, "card_reader.kicad_sch", "odock-10 — SD / microSD card reader (GL3224)", ref_base=900)

    # =============================================================================================
    # 1. GL3224
    # =============================================================================================
    _note(s, "1. GL3224-ONY04  USB 3.1 Gen1 (5 Gbps) 2-LUN card reader, QFN-48 7x7, EP = GND (via array)", (20.32, 15.24), 2.0)
    pins = {
        # power: single 5 V input, internal regulators produce CR_3V3 (DVDD33 pin 25) and CR_1V2 (DVDD12 pin 26)
        "VBUS": "+5V", "AVDD33": "CR_3V3", "DVDD33": "CR_3V3", "AVDD12": "CR_1V2", "DVDD12": "CR_1V2",
        "VUHS_1": "CR_VUHS1", "VUHS_2": "CR_VUHS2",
        "S1M1_VCC": "CR_SD_VCC", "S2M2_VCC": "CR_USD_VCC",
        "GND": "GND", "EP": "GND",
        # USB: GL3224 TX -> 100 nF -> hub RX (CR_SS_RX*), hub TX (220 nF on usb_hub) -> CR_SS_TX* -> GL3224 RX
        "DP": "CR_DP", "DM": "CR_DN",
        "TXP": "CR_TXP_IC", "TXN": "CR_TXN_IC",
        "RXP": "CR_SS_TXP", "RXN": "CR_SS_TXN",
        "RTERM": "CR_RTERM", "X1": "CR_XI", "X2": "CR_XO",
        # slot 1: full-size SD (4-bit; S1D4-7 = MMC 8-bit only -> NC)
        "SD1_CDZ": "CR_SD_CDZ", "MS1_INS/SD1_WP": "CR_SD_WP",
        "S1CK_M1D0": "CR_SD_CLK", "S1CM_M1D2": "CR_SD_CMD",
        "S1D0_M1D1": "CR_SD_D0", "S1D1_M1BS": "CR_SD_D1", "S1D2_M1CK": "CR_SD_D2", "S1D3_M1D3": "CR_SD_D3",
        # slot 2: microSD (no WP switch -> SD2_WP tied low = write enabled)
        "SD2_CDZ": "CR_USD_CDZ", "MS2_INS/SD2_WP": "CR_USD_CDZ",
        "S2CK_M2D0": "CR_USD_CLK", "S2CM_M2D2": "CR_USD_CMD",
        "S2D0_M2D1": "CR_USD_D0", "S2D1_M2BS": "CR_USD_D1", "S2D2_M2CK": "CR_USD_D2", "S2D3_M2D3": "CR_USD_D3",
        # misc
        "LED": "CR_LED_IC", "SPI_MISO": "CR_SPI_MISO", "SPI_CK": "CR_SPI_CK",
    }
    nc = ["S1D4_M1D7", "S1D5_M1D6", "S1D6_M1D5", "S1D7_M1D4", "SPI_CS", "SPI_MOSI"]
    s.part("odock:GL3224-ONY04", "U", "GL3224-ONY04", at=(119.38, 104.14), pins=pins, nc=nc, lcsc=CR_IC,
           desc="USB 3.1 Gen1 dual-LUN SD/microSD reader, ROM firmware, internal regulators + card power FETs")

    # =============================================================================================
    # 2. Power / decoupling
    # =============================================================================================
    x0, y0 = 20.32, 180.34
    _note(s, "2. POWER  +5V -> VBUS; internal LDOs -> CR_3V3 (pin 25), CR_1V2 (pin 26)", (x0, y0), 2.0)
    y = y0 + 22.86
    s.c("10u", "+5V", "GND", size="0805", at=(x0, y), lcsc=C_10U_0805, desc="VBUS pin 22 bulk")
    s.c("100n", "+5V", "GND", at=(x0 + 10.16, y), lcsc=C_100N, desc="VBUS pin 22 HF")
    s.c("10u", "CR_3V3", "GND", size="0603", at=(x0 + 22.86, y), lcsc=C_10U_0603, desc="3.3 V LDO output, at DVDD33 pin 25")
    s.c("1u", "CR_3V3", "GND", at=(x0 + 33.02, y), lcsc=C_1U, desc="AVDD33 pin 6")
    s.c("100n", "CR_3V3", "GND", at=(x0 + 43.18, y), lcsc=C_100N, desc="AVDD33 pin 6")
    s.c("100n", "CR_3V3", "GND", at=(x0 + 53.34, y), lcsc=C_100N, desc="AVDD33 pin 15")
    s.c("100n", "CR_3V3", "GND", at=(x0 + 63.5, y), lcsc=C_100N, desc="DVDD33 pin 34")
    s.c("100n", "CR_3V3", "GND", at=(x0 + 73.66, y), lcsc=C_100N, desc="DVDD33 pin 44")
    s.c("2.2u", "CR_1V2", "GND", at=(x0 + 86.36, y), lcsc=C_2U2, desc="AVDD12 pin 9 (1.2 V LDO)")
    s.c("1u", "CR_1V2", "GND", at=(x0 + 96.52, y), lcsc=C_1U, desc="DVDD12 pin 26 (1.2 V LDO output)")
    s.c("1u", "CR_VUHS1", "GND", at=(x0 + 109.22, y), lcsc=C_1U, desc="VUHS_1 pin 43: slot-1 SD IO 3.3/1.8 V (internal)")
    s.c("1u", "CR_VUHS2", "GND", at=(x0 + 119.38, y), lcsc=C_1U, desc="VUHS_2 pin 33: slot-2 SD IO 3.3/1.8 V (internal)")
    s.c("4.7u", "CR_SD_VCC", "GND", at=(x0 + 132.08, y), lcsc=C_4U7, desc="SD card VDD (S1M1_VCC switch output)")
    s.c("100n", "CR_SD_VCC", "GND", at=(x0 + 142.24, y), lcsc=C_100N, desc="SD card VDD, at the socket")
    s.c("4.7u", "CR_USD_VCC", "GND", at=(x0 + 154.94, y), lcsc=C_4U7, desc="microSD VDD (S2M2_VCC switch output)")
    s.c("100n", "CR_USD_VCC", "GND", at=(x0 + 165.1, y), lcsc=C_100N, desc="microSD VDD, at the socket")
    _note(s, "VBUS = +5V (4.75-5.25 V). CR_3V3 / CR_1V2 are the GL3224's own LDO outputs: never tie them to +3V3 or any other rail.\n"
             "Genesys GL3224(E) demo board V3.00 + open GL3224 designs: VBUS 2.2-10 uF, DVDD33 2.2-10 uF, AVDD33/DVDD33 pins 0.1-1 uF, AVDD12 2.2 uF,\n"
             "  DVDD12 1 uF, VUHS 0.1-1 uF, card VCC up to 10 uF. Card power is switched by the GL3224's on-chip FETs (S1M1_VCC / S2M2_VCC);\n"
             "  card VCC kept at 4.7 uF + 100 nF so the internal 3.3 V LDO is not dipped at card power-on (proven designs use up to 10 uF).\n"
             "Budget: GL3224 147 mA (SS U0 active) + up to ~200 mA per UHS-I card, all through the internal 5->3.3 V LDO:\n"
             "  ~(5.1-3.3) V x 0.35 A = 0.63 W in the QFN (theta-JA 33 C/W -> +21 K). Thermal pad via array to inner GND planes.",
          (x0, y0 + 35.56))

    # =============================================================================================
    # 3. USB, clock, RTERM, SPI straps
    # =============================================================================================
    x0, y0 = 200.66, 22.86
    _note(s, "3. USB / CLOCK / RTERM / ROM OPTIONS", (x0, y0), 2.0)
    y = y0 + 17.78
    s.c("100n", "CR_TXP_IC", "CR_SS_RXP", at=(x0, y), lcsc=C_100N, desc="GL3224 TX+ AC cap (Gen1 TX: 75-200 nF)")
    s.c("100n", "CR_TXN_IC", "CR_SS_RXN", at=(x0 + 10.16, y), lcsc=C_100N, desc="GL3224 TX- AC cap (Gen1 TX: 75-200 nF)")
    s.r("680", "CR_RTERM", "GND", size="0603", at=(x0 + 22.86, y), lcsc=R_680_1PCT, desc="RTERM 680 Ohm 1 % (DS table 3.1), short GND return")
    s.part("Device:Crystal_GND24", "Y", "25MHz", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", at=(x0 + 40.64, y),
           pins={"1": "CR_XI", "3": "CR_XO", "2": "GND", "4": "GND"}, lcsc=XTAL_25M,
           desc="25 MHz CL 12 pF +-10 ppm (GL3224 needs +-300 ppm)")
    s.c("20p", "CR_XI", "GND", at=(x0 + 55.88, y), lcsc=C_20P, desc="CL = (20+2)/2 = 11 pF with ~2 pF stray")
    s.c("20p", "CR_XO", "GND", at=(x0 + 66.04, y), lcsc=C_20P)
    y = y0 + 48.26
    s.r("10k", "CR_SPI_MISO", "CR_3V3", at=(x0, y), lcsc=R_10K, desc="SPI_MISO pull-up: no flash fitted -> reads 0xFF -> ROM boot")
    s.r("10k", "CR_SPI_CK", "GND", at=(x0 + 10.16, y), lcsc=R_10K, dnp=True,
        desc="DNP. ROM option: SPI_CK pull-down = SSC on card clock (Genesys demo board)")
    _note(s, "Hub link: CR_SS_TX* = hub transmits (220 nF on usb_hub) -> GL3224 RXP/RXN direct. GL3224 TXP/TXN -> 100 nF here -> CR_SS_RX* -> hub.\n"
             "  GL3224 is USB 3.1 Gen1: hub port 1 trains at 5 Gbps (~400 MB/s) - well above UHS-I SDR104 (104 MB/s).\n"
             "  Gen1 transmitter AC cap range is 75-200 nF, so 100 nF here (the 220 nF Gen2 value is out of range for a Gen1 TX).\n"
             "No reset pin: internal POR. Boots from ROM (no SPI flash). SPI_CS / SPI_MOSI NC, S1D4-7 NC (MMC 8-bit only).\n"
             "Crystal: GL3224 accepts 25 MHz +-0.03 %; same YXC 3225 part as the hub (JLC basic).",
          (x0, y0 + 60.96))

    # =============================================================================================
    # 4. Card sockets
    # =============================================================================================
    x0, y0 = 200.66, 121.92
    _note(s, "4. CARD SOCKETS  slot 1 = full-size SD (S1*), slot 2 = microSD (S2*). Both push-push.", (x0, y0), 2.0)
    y = y0 + 25.4
    s.part("odock:SD-111", "J", "SD-111", at=(x0 + 15.24, y),
           pins={"CD/DAT3": "CR_SD_D3", "CMD": "CR_SD_CMD", "VSS1": "GND", "VDD": "CR_SD_VCC", "CLK": "CR_SD_CLK",
                 "VSS2": "GND", "DAT0": "CR_SD_D0", "DAT1": "CR_SD_D1", "DAT2": "CR_SD_D2",
                 "CD": "CR_SD_CDZ", "WP": "CR_SD_WP", "EP": "GND"},
           lcsc=SD_SOCKET, desc="Full-size SD push-push. CD closes to VSS on insert; WP closes to GND when card unlocked")
    s.part("odock:DM3AT-SF-PEJM5", "J", "DM3AT", at=(x0 + 81.28, y),
           pins={"DAT2": "CR_USD_D2", "CD/DAT3": "CR_USD_D3", "CMD": "CR_USD_CMD", "VDD": "CR_USD_VCC",
                 "CLK": "CR_USD_CLK_S", "VSS": "GND", "DAT0": "CR_USD_D0", "DAT1": "CR_USD_D1",
                 "SW_B": "CR_USD_CDZ", "SW_A": "GND", "10": "GND", "12": "GND", "13": "GND", "14": "GND"},
           lcsc=USD_SOCKET, desc="microSD push-push. Detect switch A-B normally open, closes on insert")
    _note(s, "SD-111 (Hanbo drawing): CD switch to pin 3 VSS1 closes with a card; WP switch to GND closes when the card is UNLOCKED, open when\n"
             "  locked or no card -> GL3224 SD1_WP (46k internal pull-up): 0 = write enable, 1 = write protect. Matches directly, no inverter.\n"
             "  Pin 2 is MS1_INS/SD1_WP: with no card the WP switch is open (high) so no false Memory Stick insert is seen.\n"
             "DM3AT: normally-open detect switch SW_A (GND) - SW_B (CDZ). Pin 35 MS2_INS/SD2_WP is tied to CR_USD_CDZ (NOT GND): it is also\n"
             "  the Memory Stick insert input (0 = MS inserted). No card: CDZ high -> no MS, no WP. Card: low -> SD present, write enabled\n"
             "  (same state as slot 1 with an unlocked SD). Two 46k internal pull-ups in parallel on the node (~23k) - fine.\n"
             "  Bench item: the ROM must give SDx_CDZ = 0 priority over MSx_INS = 0 (DS silent) - unlocked SD in each slot enumerates\n"
             "  as writable SD, not MS. If not: inverter/strap, ask Genesys FAE.\n"
             "CMD / DAT0-3 pull-ups: GL3224 internal 15k (DS table 5.3) -> no external resistors. Route each slot's CLK/CMD/DAT as a\n"
             "  50 Ohm group, length-matched +-1 mm, CLK with GND guard (SDR104 = 208 MHz), keep stubs to zero.",
          (x0, y0 + 50.8))

    # =============================================================================================
    # 5. Card detect (TCA9534) + activity (RP2350)
    # =============================================================================================
    x0, y0 = 200.66, 205.74
    _note(s, "5. CARD DETECT -> TCA9534 P3/P4, ACTIVITY -> RP2350 (read-only)", (x0, y0), 2.0)
    y = y0 + 17.78
    s.r("1k", "CR_SD_CDZ", "CR_CD_SD_N", at=(x0, y), lcsc=R_1K, desc="SD card detect branch to TCA9534 P3 (series protection)")
    s.r("1k", "CR_USD_CDZ", "CR_CD_USD_N", at=(x0 + 10.16, y), lcsc=R_1K, desc="microSD card detect branch to TCA9534 P4")
    s.r("1k", "CR_LED_IC", "CR_LED", at=(x0 + 20.32, y), lcsc=R_1K, desc="Activity (GL3224 LED, active high) to RP2350")
    s.r("1k", "CR_LED_IC", "CR_LED_A", at=(x0 + 33.02, y), lcsc=R_1K, dnp=True, desc="DNP bench activity LED (~1 mA)")
    s.part("Device:LED", "D", "green", "LED_SMD:LED_0805_2012Metric", at=(x0 + 45.72, y),
           pins={"A": "CR_LED_A", "K": "GND"}, lcsc=LED_G, dnp=True, desc="DNP bench activity LED")
    _note(s, "The GL3224 needs the card-detect switches itself (SD1_CDZ / SD2_CDZ, 46k internal pull-up to CR_3V3, low = card).\n"
             "  The TCA9534 (mcu, P3/P4) taps the same nodes through 1k: input only, no internal pulls (TCA9534 DS 8), 5 V tolerant.\n"
             "  1k limits current if the pin is ever mis-configured as output. CR_3V3 exists whenever +5V does, and +3V3 is derived\n"
             "  from +5V, so the expander never sees the node while unpowered in a way that back-feeds the GL3224.\n"
             "  CR_USD_CDZ also drives GL3224 pin 35 (MS2_INS/SD2_WP), see section 4.\n"
             "CR_LED: GL3224 LED output (push-pull 3.3 V, active high = access), 1k to the RP2350 GPIO (firmware shows activity on the LCD).",
          (x0 + 60.96, y0 + 12.7))

    # microSD clock series termination (bus is ~90 mm long after the 130x89 re-floorplan); place next to GL3224 pin S2CK
    s.r("22", "CR_USD_CLK", "CR_USD_CLK_S", lcsc="C25092",
        desc="microSD CLK source series termination, at the GL3224 pin (tune 22-33 R on the bench)")
    s.build()
    return s
