"""odock-10 — USB hub sheet: Microchip USB7206C (USB 3.2 Gen2, 5x 10G + 1x USB2 downstream) with hub-TX AC caps,
straps, 25 MHz crystal, VBUS_DET from laptop VBUS, reset wire-OR (RP2350 + RAILS_PG), SMBus with RP2350-powered
pull-ups, optional (DNP) SPI flash.
Design notes: docs/design/usb_hub.md"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "tools", "schgen"))
from schgen import Sheet

# --- part numbers (LCSC) -------------------------------------------------------------------------
# basic parts
R_0, R_10K, R_12K, R_47K, R_100K, R_200K = "C17168", "C25744", "C25752", "C25792", "C25741", "C25764"
R_4K7, R_15K = "C25900", "C25756"
R_68K, R_49K9 = "C23231", "C23184"   # 0603 1 % basic (VBUS_DET divider / output attenuator)
C_20P, C_1N, C_100N, C_220N, C_4U7 = "C1554", "C1523", "C1525", "C16772", "C23733"
XTAL_25M = "C9006"                 # YXC X322525MOB4SI 25 MHz 3225, CL 12 pF, +-10 ppm, +-20 ppm stab., ESR 50 Ohm
# extended parts
HUB = "C3210691"                   # USB7206CT/KDX (commercial 0-70 C, T&R); alt C3210686 USB7206C-I/KDX (industrial)
D_SCHOTTKY = "C124205"             # BAT54WS-7-F 30 V Schottky SOD-323
BUF_ST = "C151394"                 # Diodes 74LVC1G17W5-7 Schmitt buffer SOT-25 (5.5 V tolerant input, Ioff)
FLASH = "C631790"                  # SST26VF016B-104I/SN 16 Mbit SPI/SQI flash (Microchip-verified), DNP

# hub physical/logical port (identity map, DS00003850F table 3-7) -> global net prefix
#   pins: (DP, DM, TXDP, TXDM, RXDP, RXDM)
PORTS = {
    1: ("CR",      (5, 6, 7, 8, 10, 11)),       # left side, upper  -> GL3224 card reader (front-left)
    2: ("USBA1",   (14, 15, 16, 17, 19, 20)),   # left side, lower  -> USB-A #1 (front-center, left)
    3: ("USBA2",   (27, 28, 29, 30, 32, 33)),   # bottom side, left -> USB-A #2 (front-center, right)
    4: ("ETH",     (34, 35, 36, 37, 39, 40)),   # bottom side, right-> RTL8156BG (back-right, around the PF side)
    5: ("HUB_DSC", (81, 82, 83, 84, 86, 87)),   # top side, right   -> TUSB1046 downstream C (back)
}


def _note(s, text, at, size=1.27):
    """Multi-line note as one text item per line (embedded newlines do not survive schgen's quoting)."""
    for i, line in enumerate(text.split("\n")):
        s.note(line, at=(at[0], round(at[1] + i * 2.54, 2)), size=size)


def build(D):
    s = Sheet(D, "usb_hub.kicad_sch", "odock-10 — USB 3.2 Gen2 hub (USB7206C)", ref_base=600, paper="A2")

    # =============================================================================================
    # 1. USB7206C
    # =============================================================================================
    _note(s, "1. USB7206C  USB 3.2 Gen2 hub, VQFN-100 12x12 (EP = VSS, via array to GND planes)", (20.32, 15.24), 2.0)
    pins = {
        # power
        "VDD33": "+3V3", "VCORE": "+1V15", "VSS": "GND",
        # upstream (laptop via TUSB1064). TX through 220 nF on this sheet, RX caps on the mux sheet.
        "89": "LAPTOP_USB_DP", "90": "LAPTOP_USB_DN",
        "91": "HUB_UP_TXP_IC", "92": "HUB_UP_TXN_IC",
        "94": "HUB_UP_SS_RXP", "95": "HUB_UP_SS_RXN",
        # USB2-only port 6 -> RP2350
        "42": "MCU_USB_DP", "41": "MCU_USB_DN",
        # misc
        "RESET_N": "HUB_RESET_N", "RBIAS": "HUB_RBIAS",
        "XTALI/CLK_IN": "HUB_XI", "XTALO": "HUB_XO",
        "TESTEN": "GND", "TEST1": "HUB_TEST1", "TEST2": "HUB_TEST2", "TEST3": "HUB_TEST3",
        "~{CFG_STRAP1}": "HUB_CFG1", "~{CFG_STRAP2}": "HUB_CFG2", "~{CFG_STRAP3}": "HUB_CFG3",
        "PF30/VBUS_MON_UP": "HUB_VBUS_DET",
        # SMBus slave (Configuration 3: PF26 = SLV_I2C_CLK, PF27 = SLV_I2C_DATA)
        "PF26": "HUB_SMB_CLK", "PF27": "HUB_SMB_DAT",
        # port power / overcurrent (combined PRT_CTLx pins): USB-A #1 = port 2, USB-A #2 = port 3
        "PF16": "USBA1_PWR_EN", "PF15": "USBA2_PWR_EN",
        # SPI (optional flash, DNP) / straps
        "SPI_CE_N/~{CFG_NON_REM}/PF20": "HUB_SPI_CE_N",
        "SPI_D0/~{CFG_BC_EN}/PF22": "HUB_SPI_D0",
        "SPI_CLK/PF21": "HUB_SPI_CLK", "SPI_D1/PF23": "HUB_SPI_D1",
        "SPI_D2/PF24": "HUB_SPI_D2", "SPI_D3/PF25": "HUB_SPI_D3",
        # unused programmable functions with "weak pull-down" termination (DS table 3-6)
        "PF3": "HUB_PF3", "PF4": "HUB_PF4", "PF5": "HUB_PF5", "PF6": "HUB_PF6", "PF7": "HUB_PF7",
        "PF18": "HUB_PF18", "PF19": "HUB_PF19", "PF31": "HUB_PF31", "PF29": "HUB_PF29",
    }
    for n, (pre, (dp, dm, txp, txm, rxp, rxm)) in PORTS.items():
        pins.update({str(dp): f"{pre}_DP", str(dm): f"{pre}_DN",
                     str(txp): f"HUB_P{n}_TXP_IC", str(txm): f"HUB_P{n}_TXN_IC",
                     str(rxp): f"{pre}_SS_RXP", str(rxm): f"{pre}_SS_RXN"})
    # NC: package NC pins, ATEST, PF8/PF9 (NC in config 3), PRT_CTLx_U3 (PortSplit only),
    # PRT_CTL1/4/5/6 of embedded ports (float, internal pull-up = "no overcurrent")
    nc = ["4", "12", "13", "80", "ATEST", "PF8", "PF9", "PF10", "PF11", "PF12",
          "PF17", "PF14", "PF13", "PF28"]
    s.part("odock:USB7206CT_KDX", "U", "USB7206CT/KDX", at=(190.5, 160.02), pins=pins, nc=nc, lcsc=HUB,
           desc="USB 3.2 Gen2 6-port hub, 5x 10G + 1x USB2 downstream, ROM firmware")

    # =============================================================================================
    # 2. Hub TX AC coupling (220 nF, USB 3.2: 75-265 nF on the transmitter side)
    # =============================================================================================
    x0, y0 = 304.8, 33.02
    _note(s, "2. HUB TX AC-COUPLING  220 nF 0402 X7R in series with every hub SS TX (upstream + 5 downstream).", (x0, y0 - 7.62), 2.0)
    _note(s, "Hub RX pairs have no caps here: the transmitting chip's side (TUSB1064/TUSB1046/GL3224/RTL8156/USB-A sheet) provides them.\n"
             "Place caps within ~5 mm of the hub pins, symmetric per pair, cut the reference plane under the 0402 pads (L2 void) for 10G.",
          (x0, y0 - 2.54))
    links = [("UP", "HUB_UP_TXP_IC", "HUB_UP_TXN_IC", "HUB_UP_SS_TXP", "HUB_UP_SS_TXN")]
    for n, (pre, _) in PORTS.items():
        links.append((f"P{n}", f"HUB_P{n}_TXP_IC", f"HUB_P{n}_TXN_IC", f"{pre}_SS_TXP", f"{pre}_SS_TXN"))
    for i, (tag, ap, an, bp, bn) in enumerate(links):
        y = y0 + 17.78 + i * 15.24
        s.c("220n", ap, bp, at=(x0 + 10.16, y), lcsc=C_220N, desc=f"{tag} hub TX+ AC cap")
        s.c("220n", an, bn, at=(x0 + 35.56, y), lcsc=C_220N, desc=f"{tag} hub TX- AC cap")

    # =============================================================================================
    # 3. Decoupling (DS fig. 4-1: 0.1 uF per pin + bulk)
    # =============================================================================================
    x0, y0 = 20.32, 254.0
    _note(s, "3. DECOUPLING  VDD33 x8 pins, VCORE x9 pins: 100 nF per pin at the pin, plus 4.7 uF + 1 nF per rail (DS fig. 4-1).", (x0, y0), 2.0)
    y = y0 + 20.32
    for i in range(8):
        s.c("100n", "+3V3", "GND", at=(x0 + i * 10.16, y), lcsc=C_100N, desc="VDD33 pin decoupling")
    s.c("4.7u", "+3V3", "GND", at=(x0 + 81.28, y), lcsc=C_4U7)
    s.c("4.7u", "+3V3", "GND", at=(x0 + 91.44, y), lcsc=C_4U7)
    s.c("1n", "+3V3", "GND", at=(x0 + 101.6, y), lcsc=C_1N)
    y = y0 + 40.64
    for i in range(9):
        s.c("100n", "+1V15", "GND", at=(x0 + i * 10.16, y), lcsc=C_100N, desc="VCORE pin decoupling")
    for i in range(3):
        s.c("4.7u", "+1V15", "GND", at=(x0 + 91.44 + i * 10.16, y), lcsc=C_4U7)
    s.c("1n", "+1V15", "GND", at=(x0 + 121.92, y), lcsc=C_1N)
    _note(s, "VCORE ~1.31 A (10G upstream + 5x 10G ports: 410 + 5*179 mA), VDD33 ~0.09 A -> ~1.8 W total; theta-JA 19 C/W (2S2P) -> ~+35 K.\n"
             "+1V15 bulk 4x22 uF sits at the TPS62933P (power_rails); route +1V15 as a pour on L4 under the hub.",
          (x0, y0 + 50.8))

    # =============================================================================================
    # 4. Clock, bias, test pins, straps
    # =============================================================================================
    x0, y0 = 20.32, 22.86
    _note(s, "4. CLOCK / BIAS / TEST / STRAPS", (x0, y0), 2.0)
    y = y0 + 20.32
    s.part("Device:Crystal_GND24", "Y", "25MHz", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", at=(x0 + 10.16, y),
           pins={"1": "HUB_XI", "3": "HUB_XO", "2": "GND", "4": "GND"}, lcsc=XTAL_25M,
           desc="25 MHz crystal CL 12 pF, +-10 ppm tol / +-20 ppm stab. (hub needs +-50 ppm)")
    s.c("20p", "HUB_XI", "GND", at=(x0 + 30.48, y), lcsc=C_20P, desc="CL = (20+2)/2 = 11 pF with ~2 pF stray")
    s.c("20p", "HUB_XO", "GND", at=(x0 + 40.64, y), lcsc=C_20P)
    s.r("12k", "HUB_RBIAS", "GND", at=(x0 + 50.8, y), lcsc=R_12K, desc="RBIAS 12.0k 1 %, at pin 100, short GND return")
    s.r("10k", "HUB_TEST1", "+3V3", at=(x0 + 60.96, y), lcsc=R_10K, desc="TEST1 pull-up (mandatory)")
    s.r("10k", "HUB_TEST2", "+3V3", at=(x0 + 71.12, y), lcsc=R_10K, desc="TEST2 pull-up (mandatory)")
    s.r("10k", "HUB_TEST3", "+3V3", at=(x0 + 81.28, y), lcsc=R_10K, desc="TEST3 pull-up (mandatory)")
    y = y0 + 40.64
    s.r("10k", "HUB_CFG1", "GND", at=(x0, y), lcsc=R_10K, desc="CFG_STRAP1 10k PD  } Configuration 3")
    s.r("200k", "HUB_CFG2", "GND", at=(x0 + 10.16, y), lcsc=R_200K, desc="CFG_STRAP2 200k PD } (only valid mode)")
    s.r("200k", "HUB_CFG3", "GND", at=(x0 + 20.32, y), lcsc=R_200K, desc="CFG_STRAP3 200k PD (unused, required)")
    s.r("200k", "HUB_SPI_CE_N", "+3V3", at=(x0 + 30.48, y), lcsc=R_200K,
        desc="CFG_NON_REM 200k PU: port 1 (GL3224) non-removable; also flash CE# pull-up")
    s.r("10k", "HUB_SPI_D0", "+3V3", at=(x0 + 40.64, y), lcsc=R_10K,
        desc="CFG_BC_EN 10k PU: BC1.2 DCP/CDP on ports 1-3 (USB-A = ports 2, 3)")
    s.r("100k", "HUB_SPI_CLK", "GND", at=(x0 + 50.8, y), lcsc=R_100K, desc="SPI_CLK weak PD (low during reset)")
    s.r("100k", "HUB_SPI_D1", "GND", at=(x0 + 60.96, y), lcsc=R_100K, desc="SPI_D1 weak PD")
    s.r("100k", "HUB_SPI_D2", "GND", at=(x0 + 71.12, y), lcsc=R_100K, desc="SPI_D2 weak PD (flash WP#)")
    s.r("100k", "HUB_SPI_D3", "GND", at=(x0 + 81.28, y), lcsc=R_100K, desc="SPI_D3 weak PD; remove if flash fitted")
    s.r("10k", "HUB_SPI_D3", "+3V3", at=(x0 + 91.44, y), lcsc=R_10K, dnp=True,
        desc="SPI_D3 = flash HOLD#: fit with U602 (and remove the PD)")
    y = y0 + 60.96
    for i, pf in enumerate(["PF3", "PF4", "PF5", "PF6", "PF7", "PF18", "PF19", "PF31", "PF29"]):
        s.r("100k", f"HUB_{pf}", "GND", at=(x0 + i * 10.16, y), lcsc=R_100K, desc=f"{pf} unused: weak PD (DS table 3-6)")
    _note(s, "Straps are latched at POR / RESET_N rising edge (hold >= 1 ms after). Config 3 (STRAP2 200k PD, STRAP1 10k PD) is the\n"
             "only valid USB7206C mode: PF26/27 = SMBus slave, PF15/16 = PRT_CTL3/2, PF30 = VBUS_DET, PF18/31 = I2C master (unused).\n"
             "PF3-7 (I2S), PF18/31 (I2C master), PF19 (MIC_DET), PF29 (GPIO93): unused -> 100k PD.  PF8/9 NC.  PRT_CTL1/4/5/6 float.\n"
             "CFG_NON_REM 200k PU = port 1 non-removable; CFG_BC_EN 10k PU = BC1.2 on ports 1-3. RP2350 refines both over SMBus\n"
             "(non-removable 1/4/6, BC on 2/3 only) when it is alive; with the RP2350 dead the strap defaults are safe.",
          (x0, y0 + 71.12))

    # =============================================================================================
    # 5. Reset, VBUS_DET, SMBus
    # =============================================================================================
    x0, y0 = 304.8, 147.32
    _note(s, "5. RESET / VBUS_DET / SMBUS", (x0, y0), 2.0)
    y = y0 + 20.32
    s.r("10k", "HUB_RESET_N", "+3V3", at=(x0, y), lcsc=R_10K, desc="RESET_N pull-up (all drivers open-drain)")
    s.c("1n", "HUB_RESET_N", "GND", at=(x0 + 10.16, y), lcsc=C_1N, desc="RESET_N filter (Microchip checklist)")
    s.part("Device:D_Schottky", "D", "BAT54WS", "Diode_SMD:D_SOD-323", at=(x0 + 22.86, y),
           pins={"A": "HUB_RESET_N", "K": "RAILS_PG"}, lcsc=D_SCHOTTKY,
           desc="Wire-OR: RAILS_PG low (+1V15 not good) holds RESET_N low; RP2350 pulling RESET_N does not load RAILS_PG")
    s.r("47k", "VBUS_LAPTOP", "HUB_VBUS_SNS", size="0402", at=(x0 + 38.1, y), lcsc=R_47K,
        desc="VBUS sense divider top (laptop VBUS 4.4-28 V)")
    s.r("68k", "HUB_VBUS_SNS", "GND", size="0603", at=(x0 + 48.26, y), lcsc=R_68K, desc="VBUS sense divider bottom: 4.4 V -> 2.60 V")
    s.part("Device:D_Schottky", "D", "BAT54WS", "Diode_SMD:D_SOD-323", at=(x0 + 60.96, y),
           pins={"A": "HUB_VBUS_SNS", "K": "+3V3"}, lcsc=D_SCHOTTKY,
           desc="Clamps the sense node to ~3.6 V when laptop VBUS is 9-28 V (<0.5 mA into +3V3 at 28 V)")
    s.r("10k", "HUB_SMB_CLK", "HUB_SMB_PU", at=(x0 + 76.2, y), lcsc=R_10K,
        desc="SMBus pull-up powered by RP2350 GPIO (10k: hub detects these at boot)")
    s.r("10k", "HUB_SMB_DAT", "HUB_SMB_PU", at=(x0 + 86.36, y), lcsc=R_10K, desc="SMBus pull-up powered by RP2350 GPIO")
    s.r("4.7k", "HUB_SMB_PU", "GND", at=(x0 + 96.52, y), lcsc=R_4K7,
        desc="Keeps pull-up rail at 0 V when RP2350 is off/BOOTSEL -> hub boots stand-alone (4.7k: RP2350-E9)")
    _note(s, "RESET_N = HUB_RESET_N (RP2350 open-drain) AND RAILS_PG (TPS62933P PG, open drain, 100k on power_rails) via D601.\n"
             "  Hub held in standby until +1V15 is in regulation (implies +3V3 up); 10k pull-up then releases it. trst >= 5 us.\n"
             "VBUS_DET (PF30): VBUS_LAPTOP -> 47k/68k (x0.591) + BAT54WS clamp to +3V3 -> HUB_VBUS_SNS -> 74LVC1G17 (+3V3, Schmitt,\n"
             "  5.5 V-tolerant input) -> 15k/49.9k -> PF30.  Sense node: 4.4 V -> 2.60 V (> VT+ max 2.0 V), 28 V -> ~3.6 V clamp (OK for\n"
             "  the LVC input), vSafe0V 0.8 V -> 0.47 V (< VT- min 0.8 V). PF30 high = +3V3 x 0.769 = 2.46-2.64 V for +3V3 3.20-3.43 V\n"
             "  (<= 2.7 V checklist 5.1, > VIH 2.1 V); 11k/49.9k from the checklist would give 2.73 V at our 3.33 V rail -> 15k.\n"
             "  Buffer powered from +3V3 = same rail as VDD33 -> VBUS_DET can never rise before VDD33.\n"
             "  VBUS present = laptop attached (deck sources VBUS only after attach). Limitation (review data #6): VBUS also exists for\n"
             "  a powered-off laptop / charge-only cable -> hub waits as CDP, USB-A get no VBUS until FORCE_EN (firmware).\n"
             "  VBUS_DET = 0 (no laptop): BC1.2 ports run as DCP; VBUS_DET = 1: CDP once the host powers the port.\n"
             "SMBus slave addr 0x2D. Pull-ups only when HUB_SMB_PU (RP2350 GPIO) is high -> hub enters CFG_SMBUS and waits for\n"
             "  the RP2350's config + USB_ATTACH_WITH_SMBUS (AA56h). HUB_SMB_PU low/floating (RP2350 off, BOOTSEL, broken FW):\n"
             "  no pull-ups seen -> hub boots from ROM+straps+OTP immediately -> RP2350 BOOTSEL (UF2) still enumerates on port 6.\n"
             "  Firmware: SMB_PU high -> RESET_N low >= 5 us -> release -> wait >= 40 ms -> config -> AA56h. No other pull-ups on this bus.",
          (x0, y0 + 30.48))

    # =============================================================================================
    # 6. Port power / overcurrent (USB-A)
    # =============================================================================================
    x0, y0 = 304.8, 238.76
    _note(s, "6. USB-A PORT POWER  PRT_CTLx = combined power-enable output + overcurrent input (DS 8.2)", (x0, y0), 2.0)
    y = y0 + 17.78
    s.r("0", "USBA1_PWR_EN", "USBA1_OCS_N", at=(x0, y), lcsc=R_0,
        desc="Net tie: PRT_CTL2 drives switch EN and senses FAULT# on the same pin")
    s.r("0", "USBA2_PWR_EN", "USBA2_OCS_N", at=(x0 + 10.16, y), lcsc=R_0,
        desc="Net tie: PRT_CTL3 drives switch EN and senses FAULT# on the same pin")
    _note(s, "USB-A #1 = hub port 2 (PRT_CTL2, PF16), USB-A #2 = hub port 3 (PRT_CTL3, PF15). Port on: pin = input + internal ~50k\n"
             "  pull-up (EN high), switch FAULT# (open drain) pulls it low = overcurrent; port off: hub drives it low.\n"
             "  USBAx_PWR_EN and USBAx_OCS_N are therefore the SAME node (0R ties, R630/R631). Do NOT add an external pull-up.\n"
             "  usb_a sheet: TPS2553 EN = PWR_EN OR FORCE_EN (gate input, high-Z), FAULT# open-drain -> OCS_N.\n"
             "Embedded ports (1 GL3224, 4 RTL8156, 5 TUSB1046/PMG1, 6 RP2350): PRT_CTL floats (internal pull-up, never reads OC).",
          (x0, y0 + 27.94))

    # =============================================================================================
    # 7. Optional SPI flash (DNP)
    # =============================================================================================
    x0, y0 = 304.8, 297.18
    _note(s, "7. OPTIONAL SPI FLASH (DNP)  only for Microchip-supplied custom firmware; ROM + straps + SMBus/OTP is the plan", (x0, y0), 2.0)
    s.part("odock:SST26VF016B-104I_SN", "U", "SST26VF016B", at=(x0 + 30.48, y0 + 17.78),
           pins={"~{CE}": "HUB_SPI_CE_N", "SCK": "HUB_SPI_CLK", "SI/SIO0": "HUB_SPI_D0", "SO/SIO1": "HUB_SPI_D1",
                 "~{WP}/SIO2": "HUB_SPI_D2", "HOLD/SIO3": "HUB_SPI_D3", "VDD": "+3V3", "VSS": "GND"},
           lcsc=FLASH, dnp=True, desc="16 Mbit SQI flash, hub-verified part (USB7206 checklist 9.2). DNP")
    s.c("100n", "+3V3", "GND", at=(x0 + 66.04, y0 + 17.78), lcsc=C_100N, dnp=True, desc="Flash decoupling (DNP)")
    _note(s, "Hub boots from flash only if it holds a valid image with the '2DFU' signature at 0x3FFFA; a blank flash -> ROM boot.\n"
             "With the flash fitted the CE#/D0 strap resistors stay (they are read before the flash is probed). Fit R614 (D3 10k PU)\n"
             "and remove R613 (D3 PD) so HOLD# is inactive. Flash images come only from Microchip -> not planned for odock-10.",
          (x0, y0 + 27.94))

    # =============================================================================================
    # 8. Port map
    # =============================================================================================
    _note(s, "8. PORT MAP (logical = physical on USB7206C)        hub side (chip rotated with pins 76-100 toward the back edge)\n"
             "  UP  : laptop via TUSB1064     top side, center        HUB_UP_SS_*, LAPTOP_USB_DP/DN\n"
             "  P1  : GL3224 card reader      left side, upper        CR_*       (non-removable, strap)\n"
             "  P2  : USB-A #1                left side, lower        USBA1_*    (BC1.2, PRT_CTL2)\n"
             "  P3  : USB-A #2                bottom side, left       USBA2_*    (BC1.2, PRT_CTL3)\n"
             "  P4  : RTL8156BG 2.5GbE        bottom side, right      ETH_*      (route around the PF/right side to the back-right)\n"
             "  P5  : TUSB1046 downstream C   top side, right         HUB_DSC_*\n"
             "  P6  : RP2350 (USB2 only)      bottom-right corner     MCU_USB_DP/DN (USB2 can use an inner layer to reach the MCU)",
          (20.32, 337.82))

    # VBUS_DET buffer (review data #2) - placed last so earlier references keep their numbers
    y2 = 167.64
    s.part("74xGxx:74LVC1G17", "U", "74LVC1G17", "Package_TO_SOT_SMD:SOT-23-5", at=(419.1, y2),
           pins={"2": "HUB_VBUS_SNS", "4": "HUB_VBUS_BUF", "5": "+3V3", "3": "GND"}, nc=["1"], lcsc=BUF_ST,
           mpn="74LVC1G17W5-7", desc="VBUS_DET Schmitt buffer on +3V3: input 5.5 V tolerant, output <= +3V3")
    s.c("100n", "+3V3", "GND", at=(434.34, y2), lcsc=C_100N, desc="VBUS_DET buffer decoupling")
    s.r("15k", "HUB_VBUS_BUF", "HUB_VBUS_DET", at=(444.5, y2), lcsc=R_15K,
        desc="VBUS_DET attenuator top (checklist fig. 5-2 topology)")
    s.r("49.9k", "HUB_VBUS_DET", "GND", size="0603", at=(454.66, y2), lcsc=R_49K9,
        desc="VBUS_DET attenuator bottom: 3.33 V -> 2.56 V (<= 2.7 V)")

    s.build()
    return s
