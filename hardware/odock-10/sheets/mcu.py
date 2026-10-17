"""odock-10 — MCU sheet: RP2350B (QFN-80) per Raspberry Pi "Hardware design with RP2350" (minimal design, rev R4-S1):
internal core regulator (3.3 uH polarised inductor), 12 MHz ABM8-272-T3 crystal, W25Q128JV QSPI flash, BOOTSEL/RUN buttons,
SWD pads, USB FS to the hub's USB2-only port; system I2C pull-ups, TCA9534 I/O expander for slow status inputs, ADC front
ends (NTC bias, ISENSE protection), status LEDs, debug UART header.
Design notes + complete GPIO table: docs/design/mcu.md"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "tools", "schgen"))
from schgen import Sheet

# --- part numbers (LCSC) -------------------------------------------------------------------------
# basic parts
R_0, R_10, R_33, R_330, R_1K, R_2K2, R_4K7, R_10K = "C17168", "C25077", "C25105", "C25104", "C11702", "C25879", "C25900", "C25744"
C_15P, C_10N, C_100N, C_4U7, C_10U = "C1548", "C15195", "C1525", "C23733", "C19702"
LED_GRN, LED_RED = "C2297", "C2286"          # KT-0805G (green, power), KT-0603R (red, status)
SW_TACT = "C318884"                          # TS-1187A-B-A-B 5.1x5.1 top push (A-B / C-D internally joined)
FLASH = "C97521"                             # W25Q128JVSIQ 128 Mbit QSPI, SOIC-8 208 mil (basic)
# extended parts
MCU = "C42415655"                            # RP2350B QFN-80 10x10
XTAL = "C20625731"                           # Abracon ABM8-272-T3 12 MHz CL 10 pF ESR 50 Ohm (RPi-mandated)
L_VREG = "C42411119"                         # Abracon AOTA-B201610S3R3-101-T 3.3 uH 0806, polarity-marked (RPi-mandated)
R_27 = "C25100"                              # 27 Ohm 1 % 0402 (USB series termination)
IOX = "C783615"                              # TI TCA9534PWR 8-bit I2C I/O expander, TSSOP-16

TP_FP = "TestPoint:TestPoint_Pad_D1.0mm"

# GPIO -> net (complete RP2350B allocation; see docs/design/mcu.md for the reasoning per pin)
GPIO = {
    0: "UART_TX",          # UART0 TX  -> debug header J1001 (local)
    1: "UART_RX",          # UART0 RX
    2: "I2C_SYS_SDA",      # I2C1 SDA (hardware)
    3: "I2C_SYS_SCL",      # I2C1 SCL
    4: "I2C_PD_SDA",       # I2C0 SDA (hardware)
    5: "I2C_PD_SCL",       # I2C0 SCL
    6: "I2C_PD_INT_N",     # PMG1 HPI interrupt (open drain, 10k PU on pd_pmg1)
    7: "PDIN_INT_N",       # TPS26750 I2Ct IRQ (open drain, 10k PU on power_input)
    8: "HUB_SMB_DAT",      # PIO I2C (SDA = n, SCL = n+1); also I2C0-capable. NO pull-ups here
    9: "HUB_SMB_CLK",
    10: "HUB_SMB_PU",      # push-pull: powers the hub SMBus pull-ups (usb_hub)
    11: "HUB_RESET_N",     # open-drain emulation: output-low or input
    12: "HDR_GPIO0",       # 12..19: user header, HSTX-capable, PIO-contiguous
    13: "HDR_GPIO1",
    14: "HDR_GPIO2",
    15: "HDR_GPIO3",
    16: "HDR_GPIO4",
    17: "HDR_GPIO5",
    18: "HDR_GPIO6",
    19: "HDR_GPIO7",
    20: "LCD_DC",          # SIO (SPI0 RX position, unused by a write-only panel)
    21: "LCD_CS_N",        # SPI0 CSn
    22: "MCU_LCD_SCK",     # SPI0 SCK  -> 33R -> LCD_SCK
    23: "MCU_LCD_MOSI",    # SPI0 TX   -> 33R -> LCD_MOSI
    24: "LCD_RST_N",       # reset default pull-down holds the panel in reset until firmware runs
    25: "LCD_BL_PWM",      # PWM4 B; reset pull-down = backlight off
    26: "MCU_PMG1_SWCLK",  # PIO SWD probe (debugprobe-style) -> 1k -> PMG1_SWCLK, via solder jumpers on pd_pmg1
    27: "MCU_PMG1_SWDIO",  #   1k series: limits PMG1 VDDD pull-up current into the unpowered FT pad (dead deck)
    28: "PMG1_XRES_N",     # open-drain emulation; pass FET + jumper on pd_pmg1
    29: "PDIN_PRESENT",    # 3.3 V from TPS26750 GPIO via 1k (power_input); FT pin, safe when +3V3 is off
    30: "I2C_EXT_SDA",     # PIO I2C for Qwiic (also I2C1-capable)
    31: "I2C_EXT_SCL",
    32: "BTN_A_N",
    33: "BTN_B_N",
    34: "USBA1_FORCE_EN",  # push-pull; reset pull-down = forced power off
    35: "USBA2_FORCE_EN",
    36: "ETH_LED0",        # RTL8156BG LED outputs (inputs here; PIO edge counting for activity)
    37: "ETH_LED1",
    38: "ETH_LED2",
    39: "CR_LED",          # GL3224 activity LED output
    40: "ADC_ISNS1",       # ADC0 <- 10k <- USBA1_ISENSE
    41: "ADC_ISNS2",       # ADC1 <- 10k <- USBA2_ISENSE
    42: "NTC_ADC0",        # ADC2, 10k 1 % bias to ADC_AVDD here, NTC to GND on sensors sheet
    43: "NTC_ADC1",        # ADC3
    44: "HDR_ADC0",        # ADC4 (1k series + ESD on display_ui)
    45: "HDR_ADC1",        # ADC5
    46: "IOX_INT_N",       # TCA9534 INT (open drain, 10k PU here)
    47: "LED_STATUS",      # PWM11 B, red status/fault LED (active high)
}


def _note(s, text, at, size=1.27):
    """Multi-line note as one text item per line (embedded newlines do not survive schgen's quoting)."""
    for i, line in enumerate(text.split("\n")):
        s.note(line, at=(at[0], round(at[1] + i * 2.54, 2)), size=size)


def build(D):
    s = Sheet(D, "mcu.kicad_sch", "odock-10 — MCU (RP2350B)", ref_base=1000, paper="A2")

    # =============================================================================================
    # 1. RP2350B
    # =============================================================================================
    _note(s, "1. RP2350B  QFN-80 10x10, 0.4 mm pitch, EP = GND (via array). All 48 GPIO allocated (table in docs/design/mcu.md)", (20.32, 15.24), 2.0)
    pins = {f"GPIO{n}" if n < 40 else f"GPIO{n}_ADC{n - 40}": net for n, net in GPIO.items()}
    pins.update({
        "IOVDD": "+3V3", "QSPI_IOVDD": "+3V3", "USB_OTP_VDD": "+3V3", "VREG_VIN": "+3V3",
        "VREG_AVDD": "VREG_AVDD", "ADC_AVDD": "ADC_AVDD",
        "DVDD": "+1V1", "VREG_FB": "+1V1", "VREG_LX": "VREG_LX", "VREG_PGND": "GND", "GND": "GND",
        "XIN": "XIN", "XOUT": "XOUT", "RUN": "RUN", "SWCLK": "MCU_SWCLK", "SWDIO": "MCU_SWDIO",
        "USB_DP": "USB_DP_IC", "USB_DM": "USB_DM_IC",
        "QSPI_SS": "QSPI_SS", "QSPI_SCLK": "QSPI_SCLK", "QSPI_SD0": "QSPI_SD0", "QSPI_SD1": "QSPI_SD1",
        "QSPI_SD2": "QSPI_SD2", "QSPI_SD3": "QSPI_SD3",
    })
    s.part("odock:RP2350B_C42415655", "U", "RP2350B", at=(190.5, 170.18), pins=pins, lcsc=MCU,
           desc="RP2350B dual Cortex-M33/Hazard3 MCU, 48 GPIO, QFN-80 (no internal flash)")

    # =============================================================================================
    # 2. Power: core regulator + decoupling (RPi minimal design: C6/C7/C9 4.7u, L1 AOTA 3.3u, R3 33R)
    # =============================================================================================
    x0, y0 = 20.32, 33.02
    _note(s, "2. POWER  +3V3 in; internal switching regulator makes +1V1 (DVDD). Copy the RPi minimal-board regulator layout exactly.", (x0, y0), 2.0)
    y = y0 + 15.24
    s.part("odock:AOTA-B201610S3R3-101-T", "L", "3.3u", at=(x0 + 7.62, y), pins={"1": "VREG_LX", "2": "+1V1"}, lcsc=L_VREG,
           desc="Core regulator inductor: polarity dot on the +1V1/DVDD (C_OUT) pad 2, VREG_LX on the un-dotted pad 1 (RP2350 DS Fig. 26)")
    s.c("4.7u", "+3V3", "GND", at=(x0 + 20.32, y), lcsc=C_4U7, desc="C6: VREG_VIN input cap, at pin 64")
    s.c("4.7u", "+1V1", "GND", at=(x0 + 30.48, y), lcsc=C_4U7, desc="C7: regulator output cap (DVDD/VREG_FB)")
    s.r("33", "+3V3", "VREG_AVDD", at=(x0 + 40.64, y), lcsc=R_33, desc="R3: VREG_AVDD RC filter (~200 uA)")
    s.c("4.7u", "VREG_AVDD", "GND", at=(x0 + 50.8, y), lcsc=C_4U7, desc="C9: VREG_AVDD filter cap")
    s.r("10", "+3V3", "ADC_AVDD", at=(x0 + 60.96, y), lcsc=R_10, desc="ADC_AVDD RC filter (ADC reference = ADC_AVDD)")
    s.c("4.7u", "ADC_AVDD", "GND", at=(x0 + 71.12, y), lcsc=C_4U7)
    s.c("100n", "ADC_AVDD", "GND", at=(x0 + 81.28, y), lcsc=C_100N, desc="ADC_AVDD pin 59 decoupling")
    s.c("10u", "+3V3", "GND", size="0603", at=(x0 + 91.44, y), lcsc=C_10U, desc="+3V3 bulk at the MCU")
    s.flag("+1V1", at=(x0 + 101.6, y))
    y = y0 + 33.02
    for i in range(8):
        s.c("100n", "+3V3", "GND", at=(x0 + i * 10.16, y), lcsc=C_100N, desc="IOVDD pin decoupling (pins 5/15/24/29/41/50/60/76)")
    s.c("100n", "+3V3", "GND", at=(x0 + 81.28, y), lcsc=C_100N, desc="QSPI_IOVDD (69)")
    s.c("100n", "+3V3", "GND", at=(x0 + 91.44, y), lcsc=C_100N, desc="USB_OTP_VDD (68)")
    y = y0 + 50.8
    for i in range(3):
        s.c("100n", "+1V1", "GND", at=(x0 + i * 10.16, y), lcsc=C_100N, desc="DVDD pin decoupling (10/32/51)")
    _note(s, "+1V1 is the RP2350 core (DVDD), made on-chip (VREG_LX -> L1001 -> VREG_FB/DVDD); it is not used elsewhere.\n"
             "L1001 ORIENTATION: dot = +1V1/C_OUT side (pad 2), as on the Pico 2 layout (DS Fig. 26); NOT toward VREG_LX. Rotated or\n"
             "  pin-swapped = worse regulation. Check the JLC CPL rotation/preview against the footprint dot before ordering.\n"
             "Second 4.7u on +1V1 sits at DVDD pin 32 (bottom edge of the package), not next to L1001/C_OUT.\n"
             "VREG_PGND: own via cluster, return the C6/C7 switching loop straight to pin 62 (RPi datasheet 'External components').\n"
             "ADC_AVDD = +3V3 through 10R/4.7u: the ADC reference; NTC bias resistors hang on ADC_AVDD -> ratiometric.\n"
             "Load: ~30-60 mA at 150 MHz both cores; < 0.2 W.", (x0, y0 + 60.96))

    # =============================================================================================
    # 3. Clock, flash, boot, reset, SWD
    # =============================================================================================
    x0, y0 = 20.32, 116.84
    _note(s, "3. CLOCK / QSPI FLASH / BOOTSEL / RUN / SWD", (x0, y0), 2.0)
    y = y0 + 17.78
    s.part("Device:Crystal_GND24", "Y", "12MHz", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", at=(x0 + 10.16, y),
           pins={"1": "XIN", "3": "XTAL_O", "2": "GND", "4": "GND"}, lcsc=XTAL,
           desc="ABM8-272-T3 12 MHz CL 10 pF ESR 50R (Pico 2 crystal, RPi-recommended)")
    s.c("15p", "XIN", "GND", at=(x0 + 27.94, y), lcsc=C_15P, desc="C3: 15p/2 + ~3 pF stray = 10.5 pF")
    s.c("15p", "XTAL_O", "GND", at=(x0 + 38.1, y), lcsc=C_15P, desc="C4")
    s.r("1k", "XOUT", "XTAL_O", at=(x0 + 48.26, y), lcsc=R_1K, desc="R2: XOUT damping (prevents crystal overdrive at 3.3 V)")
    y = y0 + 38.1
    s.part("odock:W25Q128JVSIQTR", "U", "W25Q128JVSIQ", at=(x0 + 20.32, y),
           pins={"~{CS}": "QSPI_SS", "CLK": "QSPI_SCLK", "DI": "QSPI_SD0", "DO": "QSPI_SD1", "IO2": "QSPI_SD2",
                 "IO3": "QSPI_SD3", "VCC": "+3V3", "GND": "GND"}, lcsc=FLASH,
           desc="128 Mbit QSPI flash: RP2350 firmware + bundled images for PMG1/TPS26750/hub (16 MB = RP2350 max)")
    s.c("100n", "+3V3", "GND", at=(x0 + 45.72, y), lcsc=C_100N, desc="C2: flash decoupling")
    s.r("10k", "QSPI_SS", "+3V3", at=(x0 + 55.88, y), lcsc=R_10K, dnp=True,
        desc="R1: CS pull-up, DNP per RPi (W25Q128JV does not need it)")
    y = y0 + 55.88
    s.r("1k", "QSPI_SS", "BOOTSEL_SW", at=(x0, y), lcsc=R_1K, desc="R6: lets QSPI_SS overdrive the button when booting")
    s.part("odock:TS-1187A-B-A-B", "SW", "BOOTSEL", at=(x0 + 15.24, y),
           pins={"A": "BOOTSEL_SW", "B": "BOOTSEL_SW", "C": "GND", "D": "GND"}, lcsc=SW_TACT,
           desc="BOOTSEL: hold while resetting/powering -> USB mass-storage (UF2) boot")
    s.r("1k", "RUN", "RUN_SW", at=(x0 + 33.02, y), lcsc=R_1K, desc="RUN button series R (RUN has an internal pull-up)")
    s.part("odock:TS-1187A-B-A-B", "SW", "RESET", at=(x0 + 48.26, y),
           pins={"A": "RUN_SW", "B": "RUN_SW", "C": "GND", "D": "GND"}, lcsc=SW_TACT, desc="RUN / reset button")
    y = y0 + 73.66
    for i, (net, lab) in enumerate([("MCU_SWCLK", "SWCLK"), ("MCU_SWDIO", "SWDIO"), ("RUN", "RUN"), ("GND", "GND")]):
        s.part("Connector:TestPoint", "TP", lab, TP_FP, at=(x0 + i * 12.7, y), pins={"1": net},
               desc=f"RP2350 SWD pad: {lab}")
    _note(s, "SWD pads (TP1001-TP1004, 1.0 mm, 2.54 mm apart): SWCLK, SWDIO, RUN, GND -> pogo jig or Raspberry Pi Debug Probe.\n"
             "BOOTSEL also recovers a hub stuck waiting for SMBus config: hold BOOTSEL + power-cycle -> HUB_SMB_PU stays low.\n"
             "PMG1 SWD (GPIO26/27 -> 1k -> PMG1_SWCLK/SWDIO) + PMG1_XRES_N (GPIO28). FIRMWARE RULE: never assert PMG1_XRES_N, start a\n"
             "  PMG1 SWD session or enter the PMG1 I2C bootloader unless EXT_PWR_PRESENT = 1 (TCA9534 P0). Bus-powered, the PMG1 holds\n"
             "  LAPTOP_SNK_EN: reset/flash drops +5V/+3V3, the RP2350 browns out mid-flash and the PMG1 is left bricked.\n"
             "Place the QSPI_SS resistors next to the flash; keep the QSPI bus short and direct, no stubs.",
          (x0, y0 + 81.28))

    # =============================================================================================
    # 4. USB (FS device on hub port 6)
    # =============================================================================================
    x0, y0 = 20.32, 228.6
    _note(s, "4. USB FS  -> USB7206C port 6 (USB2-only)", (x0, y0), 2.0)
    y = y0 + 12.7
    s.r("27", "USB_DP_IC", "MCU_USB_DP", at=(x0, y), lcsc=R_27, desc="USB series termination, close to the RP2350")
    s.r("27", "USB_DM_IC", "MCU_USB_DN", at=(x0 + 10.16, y), lcsc=R_27, desc="USB series termination, close to the RP2350")
    _note(s, "27R at the RP2350 pins (RPi requirement). Route as a 90R differential pair over solid GND. No VBUS sense: the\n"
             "RP2350 is always attached to the hub; firmware treats bus reset/suspend as attach/detach.", (x0, y0 + 20.32))

    # =============================================================================================
    # 5. I2C buses: pull-ups for I2C_SYS, I2C_PD, I2C_EXT (NOT the hub SMBus)
    # =============================================================================================
    x0, y0 = 304.8, 33.02
    _note(s, "5. I2C PULL-UPS  (hub SMBus has none here: HUB_SMB_PU feeds them on usb_hub)", (x0, y0), 2.0)
    y = y0 + 15.24
    s.r("2.2k", "I2C_SYS_SDA", "+3V3", at=(x0, y), lcsc=R_2K2, desc="I2C_SYS pull-up (INA2xx x3, TMP1075 x8, TCA9534, EEPROM: ~150 pF)")
    s.r("2.2k", "I2C_SYS_SCL", "+3V3", at=(x0 + 10.16, y), lcsc=R_2K2)
    s.r("2.2k", "I2C_PD_SDA", "+3V3", at=(x0 + 22.86, y), lcsc=R_2K2, desc="I2C_PD pull-up (PMG1 HPI 0x42, TPS26750 0x21)")
    s.r("2.2k", "I2C_PD_SCL", "+3V3", at=(x0 + 33.02, y), lcsc=R_2K2)
    s.r("4.7k", "I2C_EXT_SDA", "+3V3", at=(x0 + 45.72, y), lcsc=R_4K7, desc="Qwiic pull-up (Qwiic boards add their own)")
    s.r("4.7k", "I2C_EXT_SCL", "+3V3", at=(x0 + 55.88, y), lcsc=R_4K7)
    _note(s, "I2C_SYS = I2C1 (GPIO2/3), I2C_PD = I2C0 (GPIO4/5): hardware controllers, 400 kHz (1 MHz possible on I2C_PD).\n"
             "I2C_EXT (GPIO30/31) and HUB SMBus (GPIO8/9) run on PIO I2C (clock stretching supported). GPIO8/9 map to I2C0 and\n"
             "GPIO30/31 to I2C1 = the controllers already used by I2C_PD / I2C_SYS, so a hardware swap costs the other bus.\n"
             "Pull-ups go to +3V3: with +3V3 off (dead-deck start, PMG1 on VBUS)\n"
             "the PD bus idles low and no current flows into the unpowered RP2350 (all pins here are fault tolerant up to 3.63 V).",
          (x0, y0 + 25.4))

    # =============================================================================================
    # 6. I/O expander for slow status signals
    # =============================================================================================
    x0, y0 = 304.8, 76.2
    _note(s, "6. I/O EXPANDER  TCA9534 @ 0x20 on I2C_SYS: status inputs + PHY reset (48 GPIOs are all used)", (x0, y0), 2.0)
    y = y0 + 22.86
    s.part("odock:TCA9534PWR", "U", "TCA9534PWR", at=(x0 + 17.78, y),
           pins={"VCC": "+3V3", "GND": "GND", "A0": "GND", "A1": "GND", "A2": "GND",
                 "SDA": "I2C_SYS_SDA", "SCL": "I2C_SYS_SCL", "~{INT}": "IOX_INT_N",
                 "P0": "EXT_PWR_PRESENT", "P1": "LAPTOP_OVP_N", "P2": "TEMP_ALERT_N", "P3": "CR_CD_SD_N",
                 "P4": "CR_CD_USD_N", "P5": "ETH_RESET_N", "P6": "ETH_I2C_EN", "P7": "IOX_P7"}, lcsc=IOX,
           desc="8-bit I2C GPIO expander, addr 0x20 (A2..A0 = 000), interrupt on input change")
    s.c("100n", "+3V3", "GND", at=(x0 + 45.72, y), lcsc=C_100N, desc="TCA9534 decoupling")
    s.r("10k", "IOX_INT_N", "+3V3", at=(x0 + 55.88, y), lcsc=R_10K, desc="INT open-drain pull-up")
    s.r("10k", "TEMP_ALERT_N", "+3V3", at=(x0 + 66.04, y), lcsc=R_10K,
        desc="TMP1075 ALERT wired-OR pull-up (the only one: sensors sheet adds none)")
    s.r("10k", "ETH_RESET_N", "+3V3", at=(x0 + 76.2, y), lcsc=R_10K,
        desc="PHY reset released by default (expander powers up as inputs) -> Ethernet works without firmware")
    # P6 = ETH_I2C_EN (100k pull-down R820 on the ethernet sheet)
    _note(s, "P0 EXT_PWR_PRESENT (3.3 V push-pull, 100k PD on pd_pmg1)  P1 LAPTOP_OVP_N (open drain, 10k PU on power_laptop)\n"
             "P2 TEMP_ALERT_N (TMP1075 wired-OR, 10k PU here)  P3/P4 CR_CD_SD_N / CR_CD_USD_N (card detect, pull-ups on card_reader)\n"
             "P5 ETH_RESET_N (output: write 0 to reset the RTL8156BG; 10k PU here)  P6 ETH_I2C_EN (output; 100k PD R820 on ethernet)\n"
             "P7 spare (10k PD here; firmware: configure as output low). Candidates: a CCPROT fault or USBA1_OCS_N.\n"
             "All are 0-3.3 V signals that are low or unpowered whenever +3V3 is off -> no level shifting needed. These signals are\n"
             "also seen by the PMG1 (EXT_PWR_PRESENT, LAPTOP_OVP_N) which owns the safety reaction; the RP2350 only displays them.",
          (x0, y0 + 40.64))

    # =============================================================================================
    # 7. ADC front ends
    # =============================================================================================
    x0, y0 = 304.8, 142.24
    _note(s, "7. ADC  GPIO40-47 are NOT fault tolerant (max IOVDD + 0.5 V, i.e. 0.5 V with +3V3 off) -> series R on live sources", (x0, y0), 2.0)
    y = y0 + 15.24
    s.r("10k", "USBA1_ISENSE", "ADC_ISNS1", at=(x0, y), lcsc=R_10K,
        desc="Limits injection if the INA180 output is live (or > 3.3 V) while +3V3 is off")
    s.c("10n", "ADC_ISNS1", "GND", at=(x0 + 10.16, y), lcsc=C_10N, desc="ADC charge reservoir / 1.6 kHz anti-alias")
    s.r("10k", "USBA2_ISENSE", "ADC_ISNS2", at=(x0 + 22.86, y), lcsc=R_10K)
    s.c("10n", "ADC_ISNS2", "GND", at=(x0 + 33.02, y), lcsc=C_10N)
    s.r("10k", "ADC_AVDD", "NTC_ADC0", at=(x0 + 45.72, y), lcsc=R_10K,
        desc="NTC bias, 1 % (NCP18XH103 10k B3380 to GND on sensors sheet), ratiometric to the ADC reference")
    s.c("100n", "NTC_ADC0", "GND", at=(x0 + 55.88, y), lcsc=C_100N)
    s.r("10k", "ADC_AVDD", "NTC_ADC1", at=(x0 + 68.58, y), lcsc=R_10K)
    s.c("100n", "NTC_ADC1", "GND", at=(x0 + 78.74, y), lcsc=C_100N)
    _note(s, "ADC0/1 USBA1/2_ISENSE: INA180A2 (gain 50, on +3V3 with 1k/100 nF on usb_a) -> 10k + 10 nF here: second RC stage,\n"
             "  and limits injection into the non-FT pads (< 0.2 mA) should the source ever be live with +3V3 off.\n"
             "ADC2/3 NTC_ADC0/1: 10k bias from ADC_AVDD, NTC to GND remote. 25 C -> 1/2 ADC_AVDD; 100 C -> ~0.3 V.\n"
             "ADC4/5 HDR_ADC0/1: user header (10k + 10 nF + ESD on display_ui), 0-3.3 V only. ADC_AVDD = 3.3 V reference (internal temp = ch 8).",
          (x0, y0 + 25.4))

    # =============================================================================================
    # 8. LCD SPI series resistors
    # =============================================================================================
    x0, y0 = 304.8, 185.42
    _note(s, "8. LCD SPI  SPI0 (GPIO20-23) at up to 62.5 MHz write clock; series R at the source", (x0, y0), 2.0)
    y = y0 + 12.7
    s.r("33", "MCU_LCD_SCK", "LCD_SCK", at=(x0, y), lcsc=R_33, desc="SCK source termination (edge rate / EMI)")
    s.r("33", "MCU_LCD_MOSI", "LCD_MOSI", at=(x0 + 10.16, y), lcsc=R_33, desc="MOSI source termination")

    # =============================================================================================
    # 9. Status LEDs + debug UART
    # =============================================================================================
    x0, y0 = 304.8, 213.36
    _note(s, "9. STATUS LEDs / DEBUG UART", (x0, y0), 2.0)
    y = y0 + 15.24
    s.r("330", "+3V3", "LED_PWR_A", at=(x0, y), lcsc=R_330, desc="~2 mA power LED")
    s.part("Device:LED", "D", "PWR green", "LED_SMD:LED_0805_2012Metric", at=(x0 + 10.16, y),
           pins={"A": "LED_PWR_A", "K": "GND"}, lcsc=LED_GRN, desc="Power LED: +3V3 present (firmware independent)")
    s.r("1k", "LED_STATUS", "LED_ST_A", at=(x0 + 22.86, y), lcsc=R_1K, desc="~1.3 mA status LED")
    s.part("Device:LED", "D", "STATUS red", "LED_SMD:LED_0603_1608Metric", at=(x0 + 33.02, y),
           pins={"A": "LED_ST_A", "K": "GND"}, lcsc=LED_RED, desc="Status / fault LED (GPIO47 high = on, PWM)")
    s.part("Connector_Generic:Conn_01x03", "J", "DEBUG UART", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
           at=(x0 + 50.8, y), pins={"1": "UART_TX", "2": "UART_RX", "3": "GND"}, in_bom=False,
           desc="Unpopulated 3-pin debug UART (3.3 V): 1 TX (GPIO0), 2 RX (GPIO1), 3 GND")
    _note(s, "Power LED shows +3V3 even with no/broken firmware; status LED is firmware-driven (blink codes, fault).\n"
             "J1001 (unpopulated, in_bom no): UART0 115200 8N1 debug console; GPIO0/1 are fault tolerant (FTDI cable safe).",
          (x0, y0 + 25.4))

    # =============================================================================================
    # 10. Notes
    # =============================================================================================
    _note(s, "10. CROSS-SHEET RULES\n"
             "Dead-deck start (PMG1 on laptop VBUS, +3V3 off): every signal that can be high then (PDIN_PRESENT, PMG1_SWDIO/SWCLK pulls\n"
             "  via 1k, CR_LED from the +5V-powered GL3224) lands on a fault-tolerant GPIO (0-39, <= 3.63 V while unpowered). ADC pins\n"
             "  (40-47) only see sources that are off with +3V3, or go through >= 1k (ISENSE 10k, header 10k). PMG1_XRES_N has its pass FET on pd_pmg1.\n"
             "HUB_SMB_CLK/DAT: no pull-ups here. HUB_SMB_PU: push-pull. HUB_RESET_N, PMG1_XRES_N: drive low or Hi-Z only.\n"
             "Reset state of all GPIOs = input + ~50k pull-down: FORCE_EN off, LCD in reset, backlight off, SMB_PU low (hub boots stand-alone).",
          (20.32, 330.2))
    _note(s, "11. FIRMWARE RULES (full list: docs/design/mcu.md 'Firmware rules')\n"
             "PMG1_XRES_N / PMG1 SWD / PMG1 I2C bootloader: ONLY while EXT_PWR_PRESENT = 1 (bus-powered = PMG1 is the deck's supply).\n"
             "TCA9534: configure P7 (spare) as output low; P5/P6 outputs: clear P6 ETH_I2C_EN before driving P5 ETH_RESET_N low.\n"
             "ETH power cycle via P5 >= 100 ms. HUB_SMB_PU high only with working firmware; AA56h after config.",
          (20.32, 350.52))

    # Review fixes (docs/review/mcu_ui.md), created last so existing reference designators do not shift.
    s.c("4.7u", "+1V1", "GND", at=(50.8, 83.82), lcsc=C_4U7,
        desc="Second V_OUT cap (RP2350 DS 6.3.8.1): at DVDD pin 32 (bottom edge, by XIN/XOUT), away from L1001/C_OUT")
    s.r("1k", "MCU_PMG1_SWCLK", "PMG1_SWCLK", at=(76.2, 190.5), lcsc=R_1K,
        desc="PMG1 SWD series R: dead deck = PMG1 VDDD (<= 3.65 V) pull-up into unpowered FT GPIO26; harmless for SWD <= 10 MHz")
    s.r("1k", "MCU_PMG1_SWDIO", "PMG1_SWDIO", at=(86.36, 190.5), lcsc=R_1K,
        desc="PMG1 SWD series R (GPIO27)")
    s.r("10k", "IOX_P7", "GND", at=(391.16, 99.06), lcsc=R_10K,
        desc="TCA9534 P7 spare: pull-down so the input never floats (no spurious INT, no extra ICC in BOOTSEL/blank firmware)")

    # PWR_FLAGs: RC-filtered analog supplies
    s.flag("VREG_AVDD")
    s.flag("ADC_AVDD")
    s.build()
    return s
