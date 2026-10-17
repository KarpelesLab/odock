"""hubrails block: USB hub (USB7206C, 6xx) + Rails (LM5148 5 V/8 A, TPS62933F +3V3, TPS62933P +1V15, 3xx)
+ sensors U1202/U1203/TH1202/TP1202/TP1203.  Region (138,80)-(180,108).  See docs/layout-notes/hubrails.md.

Floor plan inside the region (top side):
  x 138.5-160   LM5148 power column: L301 (top), FETs Q301/Q302 directly under L301's SW pad, input caps
                bottom-left (VIN enters at the left edge, y 96-108), U301 right of L301, C323 bottom-right.
                Output side (47 uF bank, OR-FET Q303, LM74700, 2 mOhm shunt, INA226) on the BOTTOM side under L301/R303.
  x 160-164.3   P1/P2 (card reader, USB-A #1) pair channel running down from the hub's left side (y >= 94.5).
                Above it: 25 MHz crystal (top-left hub corner), +3V3 buck (TPS62933F) in the top-left strip.
  x 164.3-177.7 USB7206C U601 (centre 171, 98), rot 0 -> upstream/P5 pins face the back (usbc block),
                P3/P4/P6 face the front, PF/SPI side faces the right block.  100 nF per-pin caps on the bottom
                in the ring between the EP via field and the pad row; straps/bulk on the bottom outside the ring.
  x 167.5-174   top corridor: upstream + P5 pairs (and their TX AC caps) going straight up to y 80.
  x 174-180     top-right: +1V15 buck (TPS62933P) next to the VCORE pin 78 corner.
  y 104.8-108   under the hub: P3 straight down (J702), P4/P6 turn right to the right block; their AC caps.
"""

REGION = [(138.0, 80.0, 180.0, 108.0)]

HUB = [f"C{n}" for n in range(601, 642)] + ["D601", "D602"] + [f"R{n}" for n in range(601, 634)] + \
      ["U601", "U602", "U603", "Y601"]
RAILS = [f"C{n}" for n in range(301, 342)] + ["D301", "L301", "L302", "L303", "Q301", "Q302", "Q303"] + \
        [f"R{n}" for n in range(301, 322)] + [f"U{n}" for n in range(301, 306)]
SENS = ["U1202", "C1202", "U1203", "C1203", "TH1202", "TP1202", "TP1203"]
REFS = HUB + RAILS + SENS

HX, HY = 171.0, 98.0          # USB7206C centre


def place(board, h):
    T, B = "top", "bottom"
    P = h.put

    def hp(dx, dy):
        return HX + dx, HY + dy

    # ================================================================== USB7206C (U601)
    # rot 0: pin 1 top-left; pins 76-100 (UP 89-95, P5 81-87, XTAL 97/98, RBIAS 100) face the back edge,
    # pins 1-25 (P1, P2) face left, 26-50 (P3, P4, P6) face the front, 51-75 (PF/SPI/SMBus) face the right block.
    P("U601", HX, HY, 0, T)

    # --- per-pin 100 nF.  The footprint carries the EP via array as PTH pads, so nothing may sit under the
    #     package on the bottom.  Right-side pins (no pairs there) get their caps on TOP at the pad row; pins
    #     interleaved with the SS pairs get theirs on the BOTTOM just outside the courtyard (via at the pad toe).
    P("C620", *hp(7.4, 4.75), 90, T)      # VDD33 pin 53
    P("C632", *hp(7.4, 2.6), 90, T)       # VCORE pin 55
    P("C616", *hp(7.4, 0.45), 90, T)      # VDD33 pin 62
    P("C617", *hp(7.4, -1.7), 90, T)      # VDD33 pin 67
    P("C633", *hp(7.4, -3.85), 90, T)     # 4.7u VCORE bulk
    P("C622", *hp(7.4, -6.0), 90, T)      # 4.7u VDD33 bulk
    # top edge, bottom side, row 1 (y_rel -7.4)
    P("C624", *hp(4.6, -7.4), 0, B)       # VCORE pin 78
    P("C618", *hp(2.4, -7.4), 0, B)       # VDD33 pin 79
    P("C625", *hp(0.2, -7.4), 0, B)       # VCORE pin 85
    P("C613", *hp(-4.2, -7.4), 0, B)      # VDD33 (+3V3 pad 1 right behind pin 99, so its toe via can land on it)
    P("C626", *hp(-2.0, -7.4), 0, B)      # VCORE (+1V15 pad 1 behind pin 93); swapped with C613 2026-10-03
    P("C614", *hp(-6.4, -7.4), 0, B)      # VDD33 pin 99
    # top edge, bottom side, row 2 (y_rel -8.65): RBIAS + bulk
    P("R601", *hp(-5.0, -8.65), 0, B)     # RBIAS 12k 1 % (pin 100)
    P("C623", *hp(-2.8, -8.65), 0, B)     # 1n VDD33
    P("C636", *hp(-0.6, -8.65), 0, B)     # 1n VCORE
    P("C634", *hp(1.6, -8.65), 0, B)      # 4.7u VCORE
    P("C635", *hp(3.8, -8.65), 0, B)      # 4.7u VCORE
    # left edge, bottom side: column 1 (x_rel -7.4), column 2 (-8.8)
    P("R622", *hp(-7.4, -3.8), 90, B)     # PF31 100k (pin 3)
    P("C627", *hp(-7.4, -1.65), 90, B)    # VCORE pin 9
    P("R607", *hp(-7.4, 0.5), 90, B)      # CFG_STRAP3 200k (pin 23)
    P("C628", *hp(-7.4, 2.65), 90, B)     # VCORE pin 18
    P("C629", *hp(-7.4, 4.8), 90, B)      # VCORE pin 25
    P("C639", *hp(-8.8, -1.65), 90, B)    # RESET_N 1n
    P("R624", *hp(-8.8, 0.5), 90, B)      # RESET_N 10k PU
    P("R605", *hp(-8.8, 2.65), 90, B)     # CFG_STRAP1 10k (pin 21)
    P("R606", *hp(-8.8, 4.8), 90, B)      # CFG_STRAP2 200k (pin 22)
    # bottom edge, bottom side: row A (y_rel 7.4), row B (8.65)
    P("C619", *hp(-4.6, 7.4), 0, B)       # VDD33 pin 26
    P("C630", *hp(-2.4, 7.4), 0, B)       # VCORE pin 31
    P("C631", *hp(-0.2, 7.4), 0, B)       # VCORE pin 38
    P("C615", *hp(2.0, 7.4), 0, B)        # VDD33 pin 43
    P("C621", *hp(4.2, 7.4), 0, B)        # 4.7u VDD33
    P("R629", *hp(-5.6, 8.65), 0, B)      # HUB_SMB_PU 4.7k pull-down (erratum E9)
    P("R619", *hp(-3.4, 8.65), 0, B)      # PF7
    P("R615", *hp(-1.2, 8.65), 0, B)      # PF3 (pins 44-48: PF3..PF7, 100k PD)
    P("R616", *hp(1.0, 8.65), 0, B)       # PF4
    P("R617", *hp(3.2, 8.65), 0, B)       # PF5
    P("R618", *hp(5.4, 8.65), 0, B)       # PF6
    # right edge, bottom side: one strap column (x_rel 7.95, rot 0, 1.25 mm pitch), ordered like the pins
    col = ["R628", "R627", "R623", "R614", "R613", "R612", "R611", "R609", "R608", "R610", "R621", "R604",
           "R603", "R602", "R620", "R631", "R630"]
    for k, r in enumerate(col):
        P(r, *hp(7.95, -10.8 + 1.25 * k), 0, B)

    # --- 25 MHz crystal at the top-left corner (XI/XO = pins 98/97), 20 pF load caps right under its pads
    P("Y601", 161.95, 92.85, 0, T)
    P("C638", 162.3, 92.0, 0, B)          # XO 20p
    P("C637", 161.65, 93.75, 90, B)       # XI 20p

    # --- SS TX AC caps (top, in-line, <= 5 mm from the pins)
    P("C601", HX - 1.9, HY - 9.8, 90, T)   # UP TXP  (pins 91/92 -> TUSB1064)
    P("C602", HX - 0.65, HY - 9.8, 90, T)  # UP TXN
    P("C612", HX + 1.35, HY - 9.8, 90, T)  # P5 TXN (pin 84 at x 172.6)  -- C611/C612 swapped 2026-10-03:
    P("C611", HX + 2.6, HY - 9.8, 90, T)   # P5 TXP (pin 83 at x 173.0)     P/N order now matches the hub pins
    P("C603", 160.55, 101.0, 270, T)       # P1 TXP (pins 7/8 -> GL3224), outer lane of the left channel
    P("C604", 161.8, 101.0, 270, T)        # P1 TXN
    P("C605", 162.3, 105.4, 270, T)        # P2 TXP (pins 16/17 -> USB-A #1), inner lane
    P("C606", 163.55, 105.4, 270, T)       # P2 TXN
    P("C607", HX - 4.2, 106.55, 270, T)    # P3 TXP (pins 29/30 -> USB-A #2, straight down)
    P("C608", HX - 2.95, 106.55, 270, T)   # P3 TXN
    # (C603-C608 rot 270: pad 1 = hub-side net faces north toward the hub pins)
    P("C609", 177.4, 105.5, 0, T)          # P4 TXP (pins 36/37 -> RTL8156BG, turns right); 2 mm east of the
    P("C610", 177.4, 106.75, 0, T)         # P4 TXN    pin 43-48 pocket so the +3V3/PF3-PF7 escape vias fit

    # --- VBUS_DET buffer chain (VBUS_LAPTOP -> 47k/68k + clamp -> 74LVC1G17 -> 15k/49.9k -> pin 2)
    # (packed toward y 80 / x 160 so the top side over R312 pad 2 (+5V, 157.2,87.4) stays free for its L4 vias)
    P("D602", 158.9, 81.4, 0, T)          # BAT54WS clamp to +3V3
    P("C641", 156.6, 81.4, 90, T)         # U603 100n (pad 1 +3V3 toward pin 5)
    P("U603", 158.15, 84.55, 90, T)       # 74LVC1G17
    P("R626", 159.75, 88.6, 270, T)       # 68k (0603), vertical, east of the R312.2 via field
    P("R632", 158.6, 91.3, 0, T)          # 15k -> HUB_VBUS_DET
    P("R625", 160.75, 96.3, 90, B)        # 47k from VBUS_LAPTOP
    P("R633", 160.6, 99.15, 90, B)        # 49.9k (0603) at pin 2
    P("D601", 160.25, 102.6, 90, B)       # BAT54WS: RAILS_PG wire-OR onto RESET_N (pin 1)

    # --- optional SPI flash (DNP): bottom, under the top corridor
    P("U602", HX - 0.6, 84.15, 90, B)
    P("C640", 166.4, 88.0, 0, B)

    # --- hub temperature sensor U1203: bottom, at the bottom-left package corner (< 1 mm from the courtyard)
    P("U1203", 162.8, 105.5, 90, B)
    P("C1203", 160.5, 106.6, 90, B)

    # ================================================================== +1V15 buck (top-right corner)
    P("L303", 176.95, 83.5, 270, T)       # SW pad at the bottom (toward U305), +1V15 pad at the top
    P("U305", 175.95, 88.4, 0, T)         # SW pin top-right toward L303, VIN/GND at the bottom
    P("C336", 175.95, 90.55, 0, T)        # 100n at VIN
    P("C334", 178.65, 89.05, 90, T)       # 10u VIN
    P("C338", 174.95, 81.2, 0, B)         # 22u +1V15 (under L303)
    P("C339", 178.25, 81.2, 0, B)
    P("C340", 174.95, 83.0, 0, B)
    P("C341", 178.25, 83.0, 0, B)
    P("C335", 175.15, 85.05, 0, B)        # 10u VIN
    P("R320", 177.65, 84.95, 90, B)       # FB top
    P("R321", 178.9, 84.95, 90, B)        # FB bottom
    P("C337", 174.35, 86.85, 0, B)        # BST
    P("R319", 176.5, 86.85, 0, B)         # RAILS_PG 100k pull-up
    P("R318", 174.35, 88.1, 0, B)         # EN 10k
    P("R317", 176.5, 88.1, 0, B)          # EN 12k from +3V3

    # ================================================================== +3V3 buck (top-left strip)
    P("L302", 164.15, 83.25, 0, T)        # pad1 SW right, pad2 +3V3 left
    P("U304", 165.95, 88.05, 270, T)      # SW pin top-right, VIN/GND at the bottom
    P("C328", 165.95, 90.15, 0, T)        # 100n at VIN
    P("C326", 162.3, 87.5, 0, T)          # 10u VIN
    P("C327", 162.3, 89.75, 0, T)         # 10u VIN
    P("C331", 161.8, 81.85, 90, B)        # 22u +3V3 out, under L302
    P("C332", 164.1, 81.85, 90, B)
    P("C333", 166.4, 81.85, 90, B)
    P("R313", 161.5, 85.6, 90, B)         # EN top 100k
    P("R316", 162.75, 85.6, 90, B)        # FB bottom
    P("R315", 164.0, 85.6, 90, B)         # FB top
    P("C329", 165.25, 85.6, 90, B)        # SS 22n
    P("C330", 166.5, 85.6, 90, B)         # BST
    P("R314", 162.75, 87.6, 0, B)         # EN bottom 39k (0603)

    # ================================================================== LM5148 5 V / 8 A
    P("L301", 145.25, 87.95, 90, T)       # SW pad at the bottom (y~93.6), ISNS pad at the top
    P("Q301", 142.5, 97.9, 90, T)         # HS: VIN left, SW right (toward Q302 / L301 SW pad)
    P("Q302", 147.9, 99.4, 0, T)          # LS: SW top (EP), GND bottom
    P("R303", 154.1, 84.35, 270, T)       # 4 mOhm: ISNS top (next to L301 ISNS), 5V_BUCK bottom
    P("U301", 154.55, 91.9, 0, T)         # gate-drive pins at the bottom toward the FETs
    P("C301", 140.95, 101.7, 0, T)        # 4.7u/100V: VIN pad left (Q301 drain), GND pad right
    P("C302", 140.95, 105.25, 0, T)
    P("C303", 148.2, 105.0, 180, T)       # under Q302: GND pad left (Q302 source pins), VIN pad right
    P("C305", 144.6, 105.35, 90, T)       # 100n/100V
    P("C304", 140.95, 101.7, 0, B)        # 4th 4.7u directly under C301
    P("C306", 140.95, 105.25, 0, B)       # 2nd 100n under C302
    P("C307", 157.9, 94.4, 90, T)         # CBOOT
    P("R301", 153.2, 96.75, 0, T)         # HO gate 0R
    P("C323", 156.0, 102.75, 90, T)       # 330u polymer on +5V
    P("C324", 157.5, 96.6, 0, T)          # 22u +5V
    # controller small parts (bottom)
    P("R306", 150.15, 88.55, 0, B)        # RT 73.2k (next to U301 pin 4)
    P("R307", 150.15, 89.8, 0, B)         # CNFG 41.2k (pin 3)
    P("C316", 151.85, 97.8, 90, B)        # VCC 4.7u
    P("C317", 151.85, 100.8, 90, B)       # VDDA 100n
    P("R309", 154.0, 96.3, 0, B)          # FB bottom 12k
    P("R308", 154.0, 97.55, 0, B)         # FB top 64.9k (from 5V_BUCK)
    P("R310", 154.0, 98.8, 0, B)          # RCOMP
    P("C318", 154.0, 100.05, 0, B)        # CCOMP
    P("C319", 154.0, 101.3, 0, B)         # CHF
    P("D301", 156.6, 98.8, 90, B)         # BAT46W VIN -> VINC
    P("R305", 158.6, 97.5, 90, B)         # UVLO bottom 14.3k
    P("R311", 158.6, 99.75, 90, B)        # PG_5V pull-up
    P("C315", 155.0, 103.3, 0, B)         # VINC 1u/100V
    P("R304", 155.0, 105.6, 0, B)         # UVLO top 100k (0805, VIN side)
    P("R302", 151.95, 104.45, 90, B)      # snubber R (DNP)
    P("C308", 151.2, 107.2, 0, B)         # snubber C (DNP)
    # output side on the bottom (under L301 / R303)
    for i, r in enumerate(["C309", "C310", "C311", "C312", "C313", "C314"]):
        P(r, 140.25 + (i % 3) * 3.5, 82.85 + (i // 3) * 4.95, 90, B)   # 6x 47u on 5V_BUCK
    P("Q303", 152.05, 84.15, 180, B)      # OR-FET: source (5V_BUCK) row + gate at the bottom (toward R303 pad 2 / U302), drain+EP (5V_OR) top
    P("R312", 157.2, 84.4, 270, B)        # 2 mOhm INA226 shunt 5V_OR -> +5V
    P("U302", 149.9, 92.75, 90, B)        # LM74700
    P("C320", 145.15, 92.65, 90, B)       # VCAP
    P("C321", 146.95, 92.65, 90, B)       # 5V_OR 100n
    P("C325", 143.1, 92.65, 90, B)        # 22u +5V
    P("U303", 159.05, 91.75, 180, B)       # INA226 (Kelvin to R312)
    P("C322", 158.95, 95.75, 0, B)

    # ================================================================== sensors
    P("TH1202", 139.25, 97.9, 90, T)      # NTC on Q301 drain copper
    P("U1202", 147.85, 105.0, 0, B)       # TMP1075 "5V BUCK" on the Q302-source / input-cap GND copper
    P("C1202", 150.15, 105.0, 90, B)
    P("TP1203", 144.55, 106.15, 0, B)     # thermocouple pad TC_5V_FET (GND copper next to Q301/Q302)
    P("TP1202", 140.3, 92.65, 0, B)       # thermocouple pad (under L301, SW-pad end)
