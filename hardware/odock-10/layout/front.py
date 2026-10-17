"""odock-10 front block: card reader (GL3224 + SD + microSD) and 2x USB-A ports.

Placement-as-code, applied by tools/apply_layout.py. Rationale and routing intent:
docs/layout-notes/front.md.

Board 130 x 89 mm: front edge = y 139. Mounting hole H3 at (104, 135): nothing within 4 mm.
Front edge, left to right: J901 full-size SD (x 124), J701 / J702 USB-A (x 151.5 / 170.5), J902 microSD in the
corner rect east of the USB-A ports (x 189, project-lead decision). GL3224 + card-reader passives on the bottom
under the SD socket (the top there is entirely socket).
"""

REGION = [
    (100.0, 112.0, 180.0, 139.5),   # front block (+0.5 mm: edge connectors' courtyards overhang the edge)
    (100.0, 108.0, 140.0, 139.5),   # card-reader column: the SD-111 courtyard (31.1 mm deep) reaches y 108.2
    # microSD corner. The DM3AT courtyard is 17.15 mm deep (body 16.3), so with the card face flush at y 139 it
    # starts at y 121.9: the corner rect is extended 2.5 mm north of the agreed (180,124)-(198,139).
    (180.0, 121.5, 198.0, 141.5),   # J902 overhangs the front edge by 2 mm (coordinator decision, LCD clearance)
]

CARD = (["C%d" % n for n in range(901, 921)] + ["D901", "J901", "J902"] +
        ["R%d" % n for n in range(901, 908)] + ["U901", "Y901"])
USBA = (["C%d" % n for n in range(701, 717)] + ["D701", "D702", "D703", "D704", "J701", "J702"] +
        ["R%d" % n for n in range(701, 711)] + ["U%d" % n for n in range(701, 707)])
REFS = CARD + USBA

EDGE_Y = 139.0
SD_X = 124.0          # J901 centre: courtyard x 108.1..139.8 (left edge >= 4 mm from H3 at x 104)
USD_X = 189.0         # J902 (top) centre, corner rect x 181.5..196.65
J701_X = 151.5        # USB-A 1  (floorplan 150, +1.5)
J702_X = 170.5        # USB-A 2  (floorplan 168, +2.5)
GL_X, GL_Y = 133.0, 117.5   # GL3224 (bottom)

T, B = "top", "bottom"


def place(board, h):
    # ---------------- Card reader ----------------
    # SD-111: card enters from +y (body front line at y_local = +18.67, contacts at -11.1) -> rot 0, front flush.
    h.put("J901", SD_X, EDGE_Y - 18.67, 0, T)
    # DM3AT microSD, top, rot 0: card opening faces +y (body front line y_local +8.71 on the edge), contacts at
    # the back (y 122.74): D1 184.15 .. D2 191.85, VCC 188.55, CDZ 183.2.
    h.put("J902", USD_X, EDGE_Y - 8.71 + 2.0, 0, T)   # +2 mm: socket overhangs the front edge so the LCD panel fits above it
    # GL3224 bottom, rot 270: USB side (pins 1-12) faces +x (toward the pair channel x 137.5..141.5 -> hub),
    # SD side (37-42) faces -y (toward the SD contact row at y 105.2), microSD side (27-32) faces -x
    # (toward J902's contact row at y 118.65), power/crystal side (13-24) faces +y.
    h.put("U901", GL_X, GL_Y, 270, B)

    # USB side (+x): decoupling right at pins 6 (AVDD33) and 9 (AVDD12), TX AC caps on the vertical TX run.
    h.put("C905", 138.35, 117.25, 0, B)     # 100n  AVDD33 pin 6
    h.put("C909", 138.35, 118.75, 0, B)     # 2.2u  AVDD12 pin 9
    h.put("C904", 138.35, 120.85, 0, B)     # 1u    AVDD33 pin 6 (bulk, below the RX escape)
    h.put("C918", 139.35, 114.00, 90, B)     # 100n  TXN AC cap
    h.put("C917", 140.60, 114.00, 90, B)     # 100n  TXP AC cap
    # SD side (-y): VUHS1 pin 43 / DVDD33 pin 44 caps above the NC pins 45-48 (SD bus pins 37-42 stay free).
    h.put("C911", 134.00, 112.60, 0, B)      # 1u    VUHS_1 pin 43
    h.put("C908", 136.15, 112.60, 0, B)      # 100n  DVDD33 pin 44
    # microSD side (-x): DVDD33 34, VUHS2 33, DVDD12 26 caps tight to the chip, clear of the bus via escapes.
    h.put("C907", 127.70, 114.35, 0, B)     # 100n  DVDD33 pin 34
    h.put("C912", 127.70, 115.90, 0, B)     # 1u    VUHS_2 pin 33
    h.put("C910", 127.70, 120.40, 0, B)     # 1u    DVDD12 pin 26 (1.2 V LDO out)
    # Power side (+y): CR_3V3 10u at pin 25, VBUS caps at pin 22, AVDD33 15, RTERM 16, crystal at 13/14.
    h.put("C903", 129.85, 122.60, 0, B)     # 10u 0603  DVDD33 pin 25 (3.3 V LDO out)
    h.put("C902", 132.60, 122.35, 0, B)     # 100n VBUS pin 22
    h.put("C906", 134.30, 122.75, 90, B)    # 100n AVDD33 pin 15
    h.put("C901", 130.00, 124.65, 0, B)     # 10u 0805 VBUS pin 22 bulk
    h.put("R901", 132.75, 125.00, 90, B)    # 680R 1 % RTERM pin 16
    h.put("Y901", 136.85, 125.30, 270, B)    # 25 MHz
    h.put("C919", 139.40, 124.25, 90, B)    # 20p XI
    h.put("C920", 136.40, 128.50, 0, B)     # 20p XO
    # Straps / detect / LED (slow, non-critical), below the crystal, clear of the SD peg at (136.0, 129.5).
    h.put("R902", 129.50, 128.50, 0, B)     # 10k SPI_MISO pull-up (ROM boot)
    h.put("R903", 131.70, 128.50, 0, B)     # 10k SPI_CK pull-down (DNP)
    h.put("R906", 133.90, 128.50, 0, B)     # 1k  LED -> CR_LED (RP2350)
    h.put("R907", 129.50, 130.00, 0, B)     # 1k  bench LED (DNP)
    h.put("R904", 131.70, 130.00, 0, B)     # 1k  SD CDZ -> CR_CD_SD_N (TCA9534)
    h.put("R905", 133.90, 130.00, 0, B)     # 1k  uSD CDZ -> CR_CD_USD_N (TCA9534)
    h.put("D901", 131.00, 132.00, 0, B)     # bench LED (DNP)
    # Card VCC caps "at the socket": SD VCC pad is J901 pin 4 (123.3, 105.2, top) -> bottom, just inside y 108;
    # microSD VCC is J902 pin 4 (121.0, 118.65, bottom) -> left of the contact row (keeps the bus approach free).
    h.put("C914", 123.30, 112.60, 0, B)     # 100n SD VCC
    h.put("C913", 125.45, 112.60, 0, B)     # 4.7u SD VCC
    h.put("C916", 115.30, 120.90, 0, B)     # 100n uSD VCC
    h.put("C915", 113.15, 120.90, 0, B)     # 4.7u uSD VCC

    # ---------------- USB-A ports ----------------
    for i, (jx, sfx) in enumerate(((J701_X, 0), (J702_X, 8))):   # port 2 refs: C+8, R+5, U+3, D+2
        c = lambda k: "C%d" % (700 + k + sfx)
        r = lambda k: "R%d" % (700 + k + 5 * i)
        u = lambda k: "U%d" % (700 + k + 3 * i)
        d = lambda k: "D%d" % (700 + k + 2 * i)
        j = "J70%d" % (i + 1)
        # Std-A, mating face (y_local +13.48 = "CONNECTOR EDGE = BOARD EDGE") on the front edge.
        h.put(j, jx, EDGE_Y - 13.48, 0, T)
        # SS ESD flow-through right above the SS pin row (pins 9/8/7/6/5 = TXP/TXN/GND/RXP/RXN, same order).
        h.put(d(1), jx, 120.75, 0, T)
        # USB2 ESD (+ VBUS clamp) right of the SS channel.
        h.put(d(2), jx + 4.0, 119.75, 0, T)
        # Power path left of the SS channel (VBUS = pin 1 at jx - 3.5): POSCAP, TPS2553, VBUS ceramics.
        h.put(c(1), jx - 9.0, 117.00, 90, T)         # 150u POSCAP (+ pad toward the connector)
        h.put(u(1), jx - 4.2, 114.30, 0, T)          # TPS2553: OUT (6) left -> POSCAP, IN (1) right
        h.put(c(2), jx - 4.25, 117.45, 0, T)        # 10u VBUS
        h.put(c(3), jx - 4.25, 119.35, 0, T)        # 100n VBUS at pin 1
        # Bottom: shunt + INA180 (Kelvin) under TPS IN, OR gate, small passives.
        h.put(r(4), jx - 3.9, 113.10, 0, B)          # 30 mR shunt (+5V -> SW_IN)
        h.put(c(4), jx - 8.1, 113.10, 0, B)          # 10u SW_IN
        h.put(u(3), jx - 3.9, 116.65, 0, B)         # INA180A2
        h.put(u(2), jx - 8.1, 116.65, 90, B)        # 74LVC1G32
        h.put(c(5), jx - 8.9, 119.60, 0, B)          # 100n SW_IN
        h.put(c(7), jx - 6.75, 119.60, 0, B)         # 100n INA180 VS
        h.put(r(1), jx - 4.6, 119.60, 0, B)          # 15k RILIM
        h.put(c(6), jx - 8.9, 121.10, 0, B)          # 100n OR-gate VCC
        h.put(r(3), jx - 6.75, 121.10, 0, B)         # 100k EN pull-down
        h.put(r(2), jx - 4.6, 121.10, 0, B)          # 4.7k FORCE_EN pull-down
        h.put(r(5), jx + 4.0, 114.00, 0, B)          # 1k ISENSE filter
        h.put(c(8), jx + 4.0, 115.60, 0, B)          # 100n ISENSE filter
