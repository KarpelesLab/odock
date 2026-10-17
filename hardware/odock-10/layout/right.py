"""odock-10 placement: right block = Ethernet (8xx) + MCU (10xx) + Display & UI (11xx) + sensors U1206-U1208.

Board 130 x 89 mm (front edge y = 139, H4 at (226,135)). Region (180,50)-(230,139) minus the front-left corner
(180,123.5)-(198,141.5) reserved for the microSD socket J902 (overhangs the front edge by 2 mm; resolves the LCD conflict). See docs/layout-notes/right.md for rationale/routing intent.

Floor plan of the block (top view, back edge = top):

    y=50  +-- Ethernet ---------------------------+---------+
          | EEPROM/bridge/load-switch | straps     | RJ45    |  flash   (x 223-229)
          | RTL8156BG (rot 90): USB -> left, MDI -> right    |  VREG L/C
          | 0.95 V buck below-left                 +---------+  RP2350B (rot 0)
    y=72  +-- LCD panel (36.2 x 51.8, rot 180,    |           crystal, SWD pads
          |   tail edge toward the back, on 1.5 mm |           BOOTSEL / RESET
          |   foam; only <= 1.2 mm parts under it) |           user header J1101
    y=121 +-- (J902 corner) --+ J1001, LEDs, RC    |           (right edge)
          |                   | BTN A | BTN B | U1208 | Qwiic ----+ (H4)
    y=139        FRONT EDGE

Mostly passives on the bottom side (decoupling under the ICs, display/header support parts under the panel).
"""

REGION = [
    (180.0, 50.0, 230.0, 123.75),   # J902 corner starts at y 123.5 (socket overhangs the front edge by 2 mm)
    (198.0, 50.0, 230.0, 139.0),   # right part, full depth to the new front edge
    (201.5, 48.5, 222.5, 73.0),    # J801 courtyard overhangs the back edge (mating face on the edge line)
    (198.0, 130.0, 223.0, 141.5),  # SW1101/SW1102 actuators and the Qwiic courtyard stick out past the front edge
]

ETH = (["C%d" % n for n in range(801, 842)] + ["FB801", "J801", "L801", "Q801", "Y801"] +
       ["R%d" % n for n in range(801, 822)] + ["U%d" % n for n in range(801, 807)])
MCU = (["C%d" % n for n in range(1001, 1029)] + ["D1001", "D1002", "J1001", "L1001", "SW1001", "SW1002"] +
       ["R%d" % n for n in range(1001, 1029)] + ["TP1001", "TP1002", "TP1003", "TP1004",
                                                 "U1001", "U1002", "U1003", "Y1001"])
UI = (["C%d" % n for n in range(1101, 1110)] + ["D1101", "D1102", "D1103", "D1104", "F1101", "F1102",
                                                "J1101", "J1102", "J1103", "Q1101"] +
      ["R%d" % n for n in range(1101, 1116)] + ["SW1101", "SW1102", "U1101"])
SENS = ["U1206", "U1207", "U1208", "C1206", "C1207", "C1208", "TP1207"]
REFS = ETH + MCU + UI + SENS

# key coordinates (mm, absolute)
LCD_C = (198.4, 97.5)         # panel centre; rot 180 -> tail edge (FPC) toward the back. Panel y 71.6-123.4: the
                              # top edge must clear the RJ45 body (y 71.4). The bottom edge then overlaps the
                              # J902 corner moved to y >= 123.5 (J902 overhangs the edge by 2 mm): conflict resolved.
RTL_C = (196.5, 63.6)         # RTL8156BG, rot 90
MCU_C = (223.7, 78.3)         # RP2350B, rot 0


def place(board, h):
    def P(ref, x, y, rot=0, side="top"):
        h.put(ref, round(x / 0.05) * 0.05, round(y / 0.05) * 0.05, rot, side)

    def B(ref, x, y, rot=0):
        P(ref, x, y, rot, "bottom")

    # ------------------------------------------------------------------ Ethernet
    P("J801", 212.0, 62.95, 180)          # edge marker on y = 50, opening toward the back
    rx, ry = RTL_C
    P("U801", rx, ry, 90)                 # MDI side -> +x (jack), USB side -> -x (hub), pins 1-14 -> +y
    # USB 3 TX AC caps in-line on the PHY TX pair (pins 43/44, left side, top), heading left to the hub
    # rot 180 (2026-10-03): pad 1 (ETH_TX*_IC) faces east toward U801 pins 43/44
    P("C835", 191.4, 61.15, 180)
    P("C836", 191.4, 62.4, 180)
    # MDI centre-tap caps right below jack pins 5/6 (top side, under the panel's top edge: 0402 <= 1.2 mm)
    P("C837", 211.0, 72.6, 0)             # 390 pF
    P("C838", 213.15, 72.6, 0)            # alt CT cap (DNP)
    # bottom pin row (pins 7, 9, 10, 13, 56) caps on the bottom, between the EP and the crystal
    for x, ref in zip([194.6, 195.85, 197.1, 198.35, 199.6], ["C825", "C823", "C805", "C810", "C820"]):
        B(ref, x, 68.15, 90)              # DVDD09 56, DVDD09 7, PLL 9, AVDD33_XTAL 10, AVDD09 13
    # crystal + RSET on the bottom, right under the XI/XO / RSET pins (bottom edge of the QFN)
    B("Y801", 197.6, 71.1, 0)
    B("C833", 194.6, 70.5, 90)
    B("R804", 200.85, 72.1, 90)
    B("C834", 200.85, 74.3, 90)
    B("R805", 201.1, 70.2, 0)             # RSET pin 14
    # right pin row (MDI side) power pins: caps on the bottom under the pin row
    for i, ref in enumerate(["C812", "C821", "C813", "C822", "C814"]):   # pins 17, 18, 21, 24, 25
        B(ref, 200.55, 66.25 - 1.25 * i, 0)
    B("C811", 200.55, 60.0, 0)            # AVDD33_XTAL 2.2u
    # top pin row power pins (31, 36, 42) + left-bottom power pins (51, 52, 54, 55, 56): bottom side
    B("C824", 198.6, 59.5, 90)            # DVDD09 pin 31
    B("C817", 196.35, 59.5, 90)           # DVDD33 pin 36
    B("C829", 194.1, 59.5, 90)            # U3VDD09 pin 42
    B("C830", 192.85, 59.5, 90)           # U3VDD09 pin 42 (2.2u)
    B("R809", 190.0, 59.5, 90)            # GPIO4 pin 53
    for i, ref in enumerate(["C818", "C831", "C832", "C819", "C826"]):   # pins 51, 52, 54, 55, 56 (2.2u)
        B(ref, 192.55, 64.35 + 1.25 * i, 0)
    # buck feedback / EN under U803, AVDD33 bulk, buck VIN HF
    for i, ref in enumerate(["R802", "R803", "R801", "C815", "C816", "C807"]):
        B(ref, 189.85, 64.5 + 1.25 * i, 0)
    B("C827", 186.9, 64.6, 0)             # DVDD09 bulk 10u (0603)
    B("C828", 186.9, 66.4, 0)             # DVDD09 bulk 10u (0603)
    B("C804", 186.9, 68.2, 0)             # PLL 22u
    B("FB801", 186.9, 70.15, 0)           # PLL bead (pin 9)
    B("R807", 183.3, 64.6, 0)             # LANWAKE pin 1
    B("R806", 183.3, 65.85, 0)            # GPI pin 2
    # 0.95 V buck (TPS62A02A) below-left of the RTL, between the USB corridor and the panel edge
    P("U803", 190.35, 66.0, 0)
    P("L801", 186.2, 66.85, 180)           # SW pad (1) toward U803
    P("C806", 190.35, 68.5, 0)           # buck VIN, at VIN/GND pins
    P("C808", 182.1, 65.55, 0)             # buck out
    P("C809", 182.1, 67.4, 0)            # buck out
    # strap / pull-up resistors (pins 30-40) on the bottom, above the RTL's top pin row
    for x, ref in zip([193.5, 194.75, 196.0, 197.25, 198.5], ["R812", "R811", "R810", "R808", "R814"]):
        B(ref, x, 57.3, 90)
    for x, ref in zip([193.5, 194.75, 196.0, 197.25], ["R815", "R818", "R819", "R813"]):
        B(ref, x, 55.05, 90)
    # LED buffer, jack LED resistors, thermocouple pad, temperature sensor
    P("U804", 194.0, 56.25, 0)
    P("C839", 197.3, 56.25, 90)
    B("R816", 201.0, 52.0, 0)             # green LED (jack pin 13, far side: route on an inner layer)
    B("R817", 201.0, 53.25, 0)            # yellow LED (jack pin 11)
    P("TP1207", 199.95, 55.1)              # TC_ETH
    P("U1206", 200.55, 58.35, 0)           # between the RTL and the magjack
    B("C1206", 201.05, 56.2, 0)
    # I2C bridge + gate driver + EEPROM + PHY load switch (back strip)
    P("Q801", 195.6, 52.25, 0)
    P("R820", 198.4, 51.55, 0)
    P("R821", 198.4, 52.8, 0)
    P("U806", 189.5, 52.35, 0)
    P("C841", 192.6, 51.9, 90)
    P("U805", 183.0, 52.35, 0)
    P("C840", 186.0, 51.9, 90)
    P("U802", 183.0, 56.05, 0)
    P("C801", 186.2, 55.45, 90)
    P("C802", 187.45, 55.45, 90)
    P("C803", 189.4, 56.05, 90)

    # ------------------------------------------------------------------ MCU
    mx, my = MCU_C
    P("U1001", mx, my, 0)                 # VREG/USB/QSPI edge up (flash, regulator), crystal/SWD edge down
    P("U1002", 225.85, 64.0, 270)         # QSPI flash above the QSPI pins
    B("C1022", 227.6, 69.4, 0)            # flash VCC (pin 8, bottom-right)
    # core regulator (copy of the Pico 2 arrangement: L + C_in + C_out tight at pins 61-65)
    # whole regulator group nudged 0.15 mm north (2026-10-03) for the USB pin 66/67 escape vias above the pins
    P("L1001", 226.4, 71.2, 180)         # pad 1 (VREG_LX) right, pad 2 (+1V1, dot) left over VREG_FB
    P("C1002", 223.9, 71.25, 90)           # C_out (+1V1) beside L pad 2
    P("C1001", 226.4, 69.25, 0)            # C_in (VREG_VIN pin 64)
    P("C1003", 228.95, 71.3, 90)           # VREG_AVDD (pin 61)
    B("R1001", 228.5, 73.25, 0)           # VREG_AVDD RC
    B("R1007", 224.85, 72.25, 90)          # USB DP 27R (pins 66/67 just below)
    B("R1008", 226.1, 72.25, 90)           # USB DM 27R
    # decoupling on the bottom inside / at the pin ring
    B("C1007", 220.5, 76.1, 0)            # IOVDD pin 5
    B("C1017", 220.5, 78.1, 0)            # DVDD pin 10
    B("C1008", 220.5, 80.1, 0)            # IOVDD pin 15
    B("C1012", 221.5, 74.4, 90)          # IOVDD pin 76
    B("C1015", 222.75, 74.4, 90)         # QSPI_IOVDD pin 69
    B("C1016", 224.0, 74.4, 90)          # USB_OTP_VDD pin 68
    B("C1011", 227.0, 74.6, 0)            # IOVDD pin 60
    B("C1005", 227.0, 75.85, 0)           # ADC_AVDD pin 59
    B("C1019", 227.0, 77.75, 0)           # DVDD pin 51
    B("C1009", 227.0, 79.0, 0)            # IOVDD pin 50
    B("C1010", 227.0, 80.25, 0)            # IOVDD pin 41
    B("C1013", 221.1, 82.05, 90)          # IOVDD pin 24
    B("C1014", 222.35, 82.05, 90)         # IOVDD pin 29
    B("C1018", 225.6, 82.05, 90)          # DVDD pin 32
    B("C1028", 224.3, 84.6, 90)           # second V_OUT cap at DVDD pin 32 (bottom edge, by XIN/XOUT)
    B("C1004", 228.95, 84.9, 90)           # ADC_AVDD 4.7u
    B("R1002", 227.7, 84.9, 90)          # ADC_AVDD 10R
    B("C1006", 221.0, 85.9, 0)            # +3V3 bulk 10u
    # ADC filters (pins 49, 52-56), NTC bias
    B("C1024", 218.35, 84.45, 90)          # ADC_ISNS1
    B("C1025", 217.1, 84.45, 90)           # ADC_ISNS2
    B("C1026", 215.85, 84.45, 90)          # NTC_ADC0
    B("C1027", 214.6, 84.45, 90)           # NTC_ADC1
    B("C1108", 213.35, 84.45, 90)          # HDR_ADC0 (at the RP2350 side of the 10k)
    B("C1109", 212.1, 84.45, 90)           # HDR_ADC1
    B("R1018", 218.35, 86.8, 90)
    B("R1019", 217.1, 86.8, 90)
    B("R1020", 215.85, 86.8, 90)
    B("R1021", 214.6, 86.8, 90)
    # crystal (Pico 2 parts), below the XIN/XOUT pins
    P("Y1001", 223.5, 86.4, 0)
    P("R1003", 226.9, 85.0, 0)            # XOUT damping
    P("C1021", 226.9, 86.6, 0)            # XTAL_O load
    P("C1020", 220.2, 87.25, 0)           # XIN load
    # SWD pads, BOOTSEL / RESET
    for i, ref in enumerate(["TP1001", "TP1002", "TP1003", "TP1004"]):
        P(ref, 218.45, 90.0 + 2.3 * i)
    P("SW1001", 225.4, 94.4, 0)
    P("SW1002", 225.4, 100.4, 0)
    B("R1005", 220.6, 92.0, 90)           # QSPI_SS -> BOOTSEL 1k
    B("R1004", 221.85, 92.0, 90)          # QSPI_SS pull-up (DNP)
    B("R1006", 220.6, 98.0, 90)           # RUN -> RESET 1k
    # pull-ups and series parts on the bottom, left of the RP2350 (under the panel's right edge)
    for i, ref in enumerate(["R1009", "R1010", "R1011", "R1012", "R1013", "R1014", "R1015", "R1016", "R1017"]):
        B(ref, 216.6, 72.7 + 1.25 * i, 0)
    B("R1028", 214.4, 72.7, 0)
    B("R1022", 220.3, 88.5, 0)            # LCD SCK 33R
    B("R1023", 220.3, 89.75, 0)           # LCD MOSI 33R
    B("R1026", 223.0, 88.5, 0)            # PMG1 SWCLK 1k
    B("R1027", 223.0, 89.75, 0)           # PMG1 SWDIO 1k
    # I/O expander on the bottom, under the panel (any spot is fine: slow signals)
    B("U1003", 211.0, 76.6, 90)
    B("C1023", 211.0, 80.2, 0)
    # debug UART header (unpopulated) in the front strip, behind the button row
    P("J1001", 202.45, 126.5, 90)
    # power / status LEDs right behind the two user buttons (visible from the front)
    P("D1001", 201.6, 133.9, 0)
    P("D1002", 208.4, 134.0, 0)
    P("R1024", 204.9, 132.6, 90)
    P("R1025", 210.9, 133.9, 90)

    # ------------------------------------------------------------------ Display & UI
    cx, cy = LCD_C
    P("U1101", cx, cy, 180)               # mechanical outline, tail edge toward the back
    P("J1103", cx - 0.43, cy - 9.6, 180)  # FH34SRJ under the panel, 14.5 mm inside the tail edge, opening to it
    jx, jy = cx - 0.43, cy - 9.6
    B("C1102", jx - 1.0, jy + 2.6, 0)     # panel VCC/IOVCC at J1103 pins 4/5
    B("C1101", jx - 1.0, jy + 3.85, 0)
    B("Q1101", jx - 5.0, jy + 2.6, 0)     # backlight low-side switch (LED-K, pin 2)
    B("R1102", jx - 5.0, jy + 5.2, 0)
    B("R1103", jx - 5.0, jy + 6.45, 0)
    B("R1101", jx - 1.0, jy + 6.0, 0)     # 39R backlight (0.19 W), bottom side
    P("U1207", cx, 92.3, 0)               # LCD temperature: under the panel, just below the foam window
    B("C1207", cx + 2.2, 92.7, 90)
    # user buttons (side-push, actuator past the front edge)
    P("SW1101", 201.6, 138.2, 0)
    P("SW1102", 208.4, 138.2, 0)
    P("R1104", 200.3, 131.3, 0)
    P("C1103", 202.6, 131.3, 0)
    P("R1105", 207.1, 131.3, 0)
    P("C1104", 209.4, 131.3, 0)
    # Qwiic + ESD + decoupling, ambient sensor between SW1102 and Qwiic
    P("J1102", 218.3, 136.55, 0)
    P("D1104", 217.5, 132.0, 0)
    P("C1107", 220.6, 132.2, 0)
    P("U1208", 213.0, 136.95, 90)          # AMBIENT: front edge, far from heat sources
    P("C1208", 213.0, 133.9, 0)
    # user GPIO header J1101 (unpopulated) on the right edge; silk pinout to its left (top side kept free)
    P("J1101", 224.95, 107.0, 0)
    B("D1101", 221.3, 110.8, 90)          # ESD P0-P3
    B("D1102", 221.3, 118.4, 90)          # ESD P4-P7
    B("D1103", 221.3, 122.5, 90)          # ESD A0/A1
    for i, ref in enumerate(["R1106", "R1107", "R1108", "R1109"]):
        B(ref, 218.5, 108.4 + 1.25 * i, 0)
    for i, ref in enumerate(["R1110", "R1111", "R1112", "R1113"]):
        B(ref, 218.5, 116.0 + 1.25 * i, 0)
    B("R1114", 218.5, 121.9, 0)
    B("R1115", 218.5, 123.15, 0)
    B("F1101", 218.9, 105.3, 0)           # +5V -> +5V_USR
    B("F1102", 218.9, 102.6, 0)           # +3V3 -> +3V3_USR
    B("C1105", 222.4, 105.9, 90)
    B("C1106", 222.4, 103.6, 90)
