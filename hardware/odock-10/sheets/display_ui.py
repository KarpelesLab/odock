"""odock-10 — Display & UI sheet: HS20HS072RX 2.0" 240x320 IPS (ST7789, 4-wire SPI) plugged into a 12-pin 0.5 mm FPC
connector (Hirose FH34SRJ, dual contact), a PWM-dimmed low-side backlight switch, two side-push user buttons, unpopulated user GPIO header (series R + ESD + fused
supplies, populated), Qwiic (JST SH 4-pin) connector.
Design notes: docs/design/display_ui.md"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "tools", "schgen"))
from schgen import Sheet

# --- part numbers (LCSC) -------------------------------------------------------------------------
# basic parts
R_220, R_1K, R_10K, R_100, R_100K = "C25091", "C11702", "C25744", "C25076", "C25741"
C_10N, C_100N, C_4U7 = "C15195", "C1525", "C23733"
FET = ("Transistor_FET:AO3400A", "C20917")   # 30 V N-FET, Vgs(th) <= 1.45 V, SOT-23
# extended parts
LCD = "C5329582"                   # HS HS20HS072RX 2.0" IPS 240x320, ST7789, 12-pin 0.5 mm FPC (hand-fitted, DNP)
LCD_CONN = "C424659"               # Hirose FH34SRJ-12S-0.5SH(50): 12P 0.5 mm FPC, top+bottom contact, back-flip, 1.0 mm high
R_BL = "C22198"                    # 39 Ohm 1 % 1206 (0.25 W, UNI-ROYAL 1206W4F390JT5E): backlight current set
BTN = "C110293"                    # ALPS SKRTLAE010 side-push tact switch 4.5x3.4 mm (1/3 common, 2 = contact)
ESD = "C106794"                    # TI TPD4E02B04DQAR 4-ch ESD, 3.6 V working, USON-10 (already used on usbc_muxes)
PTC = "C75464"                     # Bourns MF-NSMF050-2 PTC 1206, 0.5 A hold / 1 A trip, 13.2 V
QWIIC = "C160404"                  # JST SM04B-SRSS-TB(LF)(SN) 4-pin 1.0 mm SMD right angle (Qwiic / STEMMA QT)

LCD_FP = "odock:LCD_HS20HS072RX_Outline"   # mechanical outline only (no pads)
# Panel FPC pin -> net. The tail folds 180 deg under the panel, so panel pin n lands on connector contact 13-n
# (docs/design/display_ui.md, "FPC connector"): J pin = 13 - panel pin.
LCD_PINS = {1: "GND", 2: "LCD_CS_N", 3: "LCD_DC", 4: "LCD_SCK", 5: "LCD_MOSI", 6: "LCD_RST_N", 7: None, 8: "+3V3",
            9: "+3V3", 10: "LCD_BL_A", 11: "LCD_BL_K", 12: "GND"}


def _note(s, text, at, size=1.27):
    for i, line in enumerate(text.split("\n")):
        s.note(line, at=(at[0], round(at[1] + i * 2.54, 2)), size=size)


def _esd(s, at, nets, desc):
    pins = {"GND": "GND"}
    nc = ["6", "7", "9", "10"]
    for pin, net in zip(["IO1", "IO2", "IO3", "IO4"], nets):
        if net:
            pins[pin] = net
        else:
            nc.append(pin)
    return s.part("odock:TPD4E02B04DQAR", "D", "TPD4E02B04", at=at, pins=pins, nc=nc, lcsc=ESD, desc=desc)


def build(D):
    s = Sheet(D, "display_ui.kicad_sch", "odock-10 — Display & user interface", ref_base=1100, paper="A3")

    # =============================================================================================
    # 1. LCD
    # =============================================================================================
    x0, y0 = 20.32, 15.24
    _note(s, "1. LCD  HS20HS072RX 2.0in IPS 240x320 (ST7789), SPI 4-wire, 3.3 V logic", (x0, y0), 2.0)
    y = y0 + 30.48
    s.part("odock:HS20HS072RX", "U", "HS20HS072RX", LCD_FP, at=(x0 + 15.24, y),
           nc=["GND", "CS", "RS", "SCL", "SDA", "RST", "NC", "I/O-VCC", "VCC", "A", "K"], lcsc=LCD, dnp=True,
           desc="2.0in 240x320 IPS TFT, ST7789 (4-wire SPI fixed in the module). NOT ASSEMBLED: order with the board, "
                "plug its FPC into J1103 by hand. Footprint = mechanical outline; pins are wired through J1103")
    s.c("4.7u", "+3V3", "GND", at=(x0 + 35.56, y), lcsc=C_4U7, desc="Panel VCI/IOVCC bulk, at J1103")
    s.c("100n", "+3V3", "GND", at=(x0 + 45.72, y), lcsc=C_100N, desc="Panel decoupling, at J1103")
    _note(s, "FPC pinout (datasheet sec. 6): 1 GND, 2 CS, 3 RS (D/C), 4 SCL, 5 SDA (MOSI), 6 RST, 7 NC, 8 IOVCC, 9 VCI, 10 LED-A, 11 LED-K, 12 GND.\n"
             "Interface is hard-wired to 4-wire SPI inside the module (no IM straps on the FPC); write-only (no MISO), up to 62.5 MHz.\n"
             "VCI 2.4-3.3 V / IOVCC 1.65-3.3 V: both on +3V3 = 3.33 V nom (~3.36 V max): accepted known deviation from the 3.3 V\n"
             "  recommended max (abs max 4.6 V). Retrimming +3V3 to 3.30 V (power_rails) would remove it.\n"
             "MECHANICAL: U1101 is DNP (hand-fitted after assembly); its footprint is the panel outline. J1103 = Hirose FH34SRJ (dual contact,\n"
             "  1.0 mm high, 0.3 mm FPC) UNDER the panel, opening toward the tail edge, 14.5 mm inside it. The tail folds 180 deg under the panel\n"
             "  (contacts face the PCB), so PANEL PIN n -> J1103 PIN 13-n. Foam tape >= 1.5 mm with a window over J1103 and the tail.",
          (x0, y0 + 50.8))

    # =============================================================================================
    # 2. Backlight
    # =============================================================================================
    x0, y0 = 20.32, 88.9
    _note(s, "2. BACKLIGHT  4 white LEDs in parallel, Vf 3.0 V typ (2.8-3.2) @ 80 mA max -> from +5V, 39R, low-side PWM", (x0, y0), 2.0)
    y = y0 + 15.24
    s.r("39", "+5V", "LCD_BL_A", size="1206", at=(x0, y), lcsc=R_BL,
        desc="Current set: (5.13-3.0)/39 = 55 mA typ; 69 mA worst (+5V = 5.5 V laptop vSafe5V, Vf 2.8) < 80 mA abs; 0.19 W max")
    s.part(FET[0], "Q", "AO3400A", at=(x0 + 17.78, y), pins={"G": "BL_GATE", "D": "LCD_BL_K", "S": "GND"},
           lcsc=FET[1], desc="Low-side backlight switch (PWM)")
    s.r("100", "LCD_BL_PWM", "BL_GATE", at=(x0 + 33.02, y), lcsc=R_100, desc="Gate series R (edge rate / ringing)")
    s.r("100k", "BL_GATE", "GND", at=(x0 + 43.18, y), lcsc=R_100K, desc="Backlight off while the RP2350 is in reset/unpowered")
    _note(s, "Not from +3V3: 0.1-0.5 V headroom over Vf would make the current depend on LED Vf. 55 mA typ (+5V 5.13 V) -> ~0.28 W.\n"
             "Worst case: bus-powered +5V = laptop VBUS up to 5.5 V: (5.5-2.8)/39 = 69 mA (72 mA at Vf 2.7 V hot) < 80 mA abs max.\n"
             "  Min (4.75 V, Vf 3.2) = 40 mA. PWM does not reduce the peak current, so R1101 alone must keep it under 80 mA.\n"
             "PWM: LCD_BL_PWM (GPIO25, PWM4 B) at >= 20 kHz (inaudible), 0-100 %. Firmware dims after inactivity.",
          (x0, y0 + 25.4))

    # =============================================================================================
    # 3. User buttons
    # =============================================================================================
    x0, y0 = 20.32, 132.08
    _note(s, "3. USER BUTTONS  side-push (actuator overhangs the front edge), active low", (x0, y0), 2.0)
    y = y0 + 15.24
    for i, (net, lab) in enumerate([("BTN_A_N", "A"), ("BTN_B_N", "B")]):
        x = x0 + i * 45.72
        s.part("odock:SKRTLAE010", "SW", f"BTN_{lab}", at=(x + 7.62, y),
               pins={"2": net, "1": "GND", "3": "GND", "4": "GND", "5": "GND"}, lcsc=BTN,
               desc=f"User button {lab} (ALPS SKRT side push, 1.6 N); pins 1/3 common, 4/5 mounting tabs")
        s.r("10k", net, "+3V3", at=(x + 22.86, y), lcsc=R_10K, desc="Pull-up (button to GND)")
        s.c("10n", net, "GND", at=(x + 33.02, y), lcsc=C_10N, desc="RC 100 us: bounce/ESD filter (firmware debounces too)")
    _note(s, "Button A: per-port forced-5V 'charge mode' toggle; button B: LCD page/select (firmware-defined, remappable).\n"
             "Place on the front edge with the actuator 0.3-0.5 mm past the board outline. Footprint has 2 x 0.9 mm guide-boss holes.",
          (x0, y0 + 25.4))

    # =============================================================================================
    # 4. User GPIO header (unpopulated) with series R + ESD
    # =============================================================================================
    x0, y0 = 160.02, 15.24
    _note(s, "4. USER GPIO HEADER  2x8 2.54 mm, UNPOPULATED (in_bom no); series R + ESD + fuses populated", (x0, y0), 2.0)
    y = y0 + 15.24
    for i in range(8):
        s.r("220", f"HDR_GPIO{i}", f"HDR_P{i}", at=(x0 + i * 10.16, y), lcsc=R_220,
            desc=f"Series R GPIO{12 + i}: limits fault/ESD current into the RP2350")
    for i in range(2):
        s.r("10k", f"HDR_ADC{i}", f"HDR_A{i}", at=(x0 + 81.28 + i * 10.16, y), lcsc=R_10K,
            desc=f"Series R ADC{4 + i}: ADC pins are not fault tolerant; 10k limits back-power (3.3 V, deck off) to ~0.3 mA")
    y = y0 + 45.72
    _esd(s, (x0 + 15.24, y), ["HDR_P0", "HDR_P1", "HDR_P2", "HDR_P3"], "Header ESD P0-P3, at the header pins")
    _esd(s, (x0 + 50.8, y), ["HDR_P4", "HDR_P5", "HDR_P6", "HDR_P7"], "Header ESD P4-P7, at the header pins")
    _esd(s, (x0 + 86.36, y), ["HDR_A0", "HDR_A1", None, None], "Header ESD A0/A1, at the header pins")
    y = y0 + 76.2
    s.part("Device:Polyfuse", "F", "0.5A", "Fuse:Fuse_1206_3216Metric", at=(x0, y), pins={"1": "+5V", "2": "+5V_USR"},
           lcsc=PTC, desc="+5V to header: 0.5 A hold / 1 A trip")
    s.part("Device:Polyfuse", "F", "0.5A", "Fuse:Fuse_1206_3216Metric", at=(x0 + 12.7, y), pins={"1": "+3V3", "2": "+3V3_USR"},
           lcsc=PTC, desc="+3V3 to header + Qwiic: 0.5 A hold / 1 A trip (protects the +3V3 rail from user shorts)")
    s.c("100n", "+5V_USR", "GND", at=(x0 + 25.4, y), lcsc=C_100N)
    s.c("100n", "+3V3_USR", "GND", at=(x0 + 35.56, y), lcsc=C_100N)
    hdr = {"1": "+5V_USR", "2": "+3V3_USR", "3": "HDR_P0", "4": "HDR_P1", "5": "HDR_P2", "6": "HDR_P3", "7": "GND", "8": "GND",
           "9": "HDR_P4", "10": "HDR_P5", "11": "HDR_P6", "12": "HDR_P7", "13": "HDR_A0", "14": "HDR_A1", "15": "GND", "16": "GND"}
    s.part("Connector_Generic:Conn_02x08_Odd_Even", "J", "USER GPIO",
           "Connector_PinHeader_2.54mm:PinHeader_2x08_P2.54mm_Vertical", at=(x0 + 68.58, y + 5.08), pins=hdr, in_bom=False,
           desc="User GPIO header, unpopulated (solder a 2x8 2.54 mm header)")
    _note(s, "Pinout (silkscreen, top and back):  1 5V   2 3V3 | 3 G12  4 G13 | 5 G14  6 G15 | 7 GND  8 GND\n"
             "                                    9 G16 10 G17 | 11 G18 12 G19 | 13 A4(G44) 14 A5(G45) | 15 GND 16 GND\n"
             "HDR_P0..7 = RP2350 GPIO12..19: contiguous (PIO). FREE for the header: SPI1 (12-15), PWM6/7/0/1, PIO2, HSTX (not DVI:\n"
             "  220R + ESD break TMDS). UART0 (debug), SPI0 (LCD), I2C0 (I2C_PD) and I2C1 (I2C_SYS) are already taken.\n"
             "3.3 V LOGIC ONLY. 220R + ESD (TPD4E02B04 VRWM 3.6 V): 5 V is abuse, not a feature, even though the FT pads survive it.\n"
             "A0/A1 (ADC4/5) via 10k + 10 nF: 0-3.3 V, not fault tolerant. 5V/3V3 pins are outputs (do not back-feed the deck).",
          (x0, y0 + 99.06))

    # =============================================================================================
    # 5. Qwiic
    # =============================================================================================
    x0, y0 = 160.02, 147.32
    _note(s, "5. QWIIC / STEMMA QT  JST SH 4-pin, I2C_EXT (PIO I2C, 4.7k pull-ups on mcu sheet), 3.3 V", (x0, y0), 2.0)
    y = y0 + 17.78
    s.part("odock:SM04B-SRSS-TB", "J", "QWIIC", at=(x0 + 10.16, y),
           pins={"1": "GND", "2": "+3V3_USR", "3": "I2C_EXT_SDA", "4": "I2C_EXT_SCL", "5": "GND", "6": "GND"}, lcsc=QWIIC,
           desc="Qwiic: 1 GND, 2 3V3, 3 SDA, 4 SCL; pads 5/6 = mounting tabs")
    _esd(s, (x0 + 45.72, y), ["I2C_EXT_SDA", "I2C_EXT_SCL", None, None], "Qwiic ESD, at the connector")
    s.c("100n", "+3V3_USR", "GND", at=(x0 + 76.2, y), lcsc=C_100N, desc="Qwiic supply decoupling at the connector")
    _note(s, "Qwiic power shares the fused +3V3_USR with the header. Bus is independent of I2C_SYS (no risk to the sensors/PD bus).",
          (x0, y0 + 30.48))

    # Review fix (docs/review/mcu_ui.md #11), created last so existing reference designators do not shift.
    for i in range(2):
        s.c("10n", f"HDR_ADC{i}", "GND", at=(261.62 + i * 10.16, 30.48), lcsc=C_10N,
            desc=f"ADC{4 + i} charge reservoir at the RP2350 side of the 10k (as ISENSE)")
    # FPC connector for the LCD (replaces the soldered tail), created last so existing references do not shift (J1103).
    jp = {str(13 - n): net for n, net in LCD_PINS.items() if net}
    jp.update({"13": "GND", "14": "GND"})
    s.part("odock:FH34SRJ-12S-0.5SH", "J", "LCD FPC", at=(93.98, 40.64), pins=jp,
           nc=[str(13 - n) for n, net in LCD_PINS.items() if not net], lcsc=LCD_CONN,
           desc="LCD FPC connector, dual contact. Tail folds under the panel: J pin = 13 - panel pin (1 GND, 2 LED-K, 3 LED-A, "
                "4 VCI, 5 IOVCC, 6 NC, 7 RST, 8 SDA, 9 SCL, 10 RS, 11 CS, 12 GND); 13/14 tabs to GND")
    s.build()
    return s
