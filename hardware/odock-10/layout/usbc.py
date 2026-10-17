"""usbc block: USB-C muxes & DP (5xx) + PD controller (4xx) + sensors U1204/U1205 (+ TP1204/TP1205).

Region (138,50)-(180,80).  See docs/layout-notes/usbc.md for the rationale and the routing intent.

Top view, back edge = y 50:

  D501   J501 laptop C (x 150.7)    PMG1 BGA (x 160.9)    J502 downstream C (x 171)   D505
         D503 D502 (ESD) + TX caps   decaps all around     D507 D506 (ESD) + TX caps
            lanes turn right ->  [TUSB1064 r270] =DP caps= [TUSB1046 r270]  <- lanes turn left
                                 hub SS on the top edges -> vias -> L3 down the middle -> y 80
  U501 TPD4S480 / D504 / U504 TPD6S300 on the bottom, right behind the connector CC/SBU/D+- pins.
"""

REGION = [
    (138.0, 50.0, 180.0, 80.0),
    # edge connectors only: shell front flush with the back edge, so the courtyard pokes ~0.5 mm past it
    (144.0, 49.4, 177.0, 61.2),
]

REFS = (
    # PD controller sheet
    [f"C{n}" for n in range(401, 423)] + ["JP401", "JP402", "JP403", "Q401", "Q402"]
    + [f"R{n}" for n in range(401, 416)] + [f"TP{n}" for n in range(401, 407)] + ["U401"]
    # USB-C muxes & DP sheet
    + [f"C{n}" for n in range(501, 539)] + [f"D{n}" for n in range(501, 508)] + ["J501", "J502"]
    + [f"R{n}" for n in range(501, 545)] + ["U501", "U502", "U503", "U504"]
    # sensors sheet parts assigned to this block by floorplan.md
    + ["U1204", "C1204", "U1205", "C1205", "TP1204", "TP1205"]
)

XJ1, YJ1 = 150.7, 57.05      # J501 laptop USB-C (JAE DX07, rot 180): shell front at y ~49.9
XJ2, YJ2 = 171.0, 55.25      # J502 downstream USB-C (Amphenol, rot 180): shell front at y ~49.97
YU = 69.55                   # both muxes (centre y)
XU2 = 156.85                 # TUSB1064 rot 270: connector pins on the left edge, DP right, hub SS top, AUX/SBU/CTL bottom
XU3 = 166.3                  # TUSB1046 rot 270: connector pins on the right edge, DP left, hub SS top, AUX/SBU/CTL bottom
XP, YP = 160.9, 54.05       # PMG1 BGA rot 180: port-0 balls (laptop) left, port-1 balls right, VBB/MUX rows at the bottom
YESD1, YESD2 = 62.45, 62.6   # ESD rows behind each connector
T, B = "top", "bottom"
PX, PY = 2.15, 1.25          # 0402 grid pitch (courtyard 1.95 x 1.03 -> >= 0.2 mm gaps)


def grid(h, refs, x0, y0, ncol, side=B, rot=0, px=PX, py=PY):
    for i, r in enumerate(refs):
        h.put(r, round(x0 + (i % ncol) * px, 3), round(y0 + (i // ncol) * py, 3), rot, side)


def place(board, h):
    # ---------------- connectors ----------------
    h.put("J501", XJ1, YJ1, 180)
    h.put("J502", XJ2, YJ2, 180)

    # laptop VBUS TVS left of J501: VBUS pad (1) at the bottom next to the J501 VBUS pins, GND pad toward the edge
    h.put("D501", 141.4, 55.5, 90)
    h.put("C501", 143.25, 62.35, 0)         # VBUS_LAPTOP 100n/50V 0603
    h.put("U1205", 140.0, 62.75, 0)         # TMP1075 "LAPTOP-C" in the VBUS/GND copper next to J501
    h.put("C1205", 140.0, 64.95, 0)

    # ---------------- laptop side: ESD + TX AC caps (top), protectors (bottom) ----------------
    h.put("D503", 148.15, YESD1, 0)         # TX2/RX2 lanes (left half of J501)
    h.put("D502", 152.05, YESD1, 180)       # TX1/RX1 lanes (right half of J501)
    h.put("C511", 146.9, 64.6, 90)          # UP_TX2_P
    h.put("C512", 148.12, 64.6, 90)         # UP_TX2_N
    h.put("C510", 152.45, 64.6, 90)         # UP_TX1_N
    h.put("C509", 153.67, 64.6, 90)         # UP_TX1_P
    h.put("U501", XJ1, 65.05, 0, B)         # TPD4S480: C_CC/C_SBU pins face J501; 2 mm south (2026-10-03) so the
                                            # A-row slow nets (CC1/SBU1/D+-) get via room below the A row
    h.put("C502", 153.95, 62.8, 90, B)      # VBIAS 100n/100V 0805
    h.put("C503", 155.75, 62.35, 90, B)     # VPWR (PMG1_VDDD) 1u
    h.put("R501", 157.0, 62.35, 90, B)      # FLT pull-up
    h.put("D504", 146.9, 63.05, 0, B)       # LAPTOP_USB_DP/DN ESD, flow-through vertical

    # ---------------- TUSB1064 ----------------
    h.put("U502", XU2, YU, 270)
    h.put("C513", 156.45, 64.85, 90)        # hub SSRX AC caps right above the top-edge SSRX pins
    h.put("C514", 157.67, 64.85, 90)
    # VCC decoupling on the bottom: 100n at each VCC pin + shared 10u
    h.put("C504", 156.25, 65.25, 0, B)      # pin 6 (top edge)
    h.put("C505", 154.25, 71.45, 0, B)      # pin 20 (left edge, bottom end)
    h.put("C506", 158.3, 73.85, 90, B)      # pin 28 (bottom edge)
    h.put("C507", 155.75, 74.6, 0, B)       # 10u 0603
    # left-edge straps EQ0/EQ1/I2C_EN (bottom, under the lane fan-in)
    grid(h, ["R512", "R513", "R510", "R511", "R508", "R509"], 151.75, 67.65, 2)   # 0.8 mm south to clear U501
    # top-edge straps SSEQ1/DPEQ1 (bottom, above the top-right corner)
    grid(h, ["R514", "R515", "R518", "R519"], 159.0, 62.3, 2)
    # bottom edge: SBU 2M pull-downs, AUX bias (top)
    h.put("R502", 155.3, 74.05, 0)          # UP_SBU1 2M 0603
    h.put("R503", 155.3, 75.8, 0)           # UP_SBU2 2M 0603
    h.put("R506", 158.3, 73.8, 0)           # DP_AUX_P 1M -> 3V3
    h.put("R507", 158.3, 75.05, 0)          # DP_AUX_N 1M -> GND

    # ---------------- DP main link: 8 AC caps in-line between the muxes (P column / N column) ----------------
    for k, (cp, cn) in enumerate([("C515", "C516"), ("C517", "C518"), ("C519", "C520"), ("C521", "C522")]):
        y = YU - 2.0 + k * 1.22
        h.put(cp, 160.51, round(y - 0.05, 3), 0)
        h.put(cn, 162.62, round(y + 0.3, 3), 0)
    # AUX AC caps in the AUX row below the muxes
    h.put("C523", 161.6, 73.8, 0)           # AUX_P 100n
    h.put("C524", 161.6, 75.05, 0)          # AUX_N 100n
    # bottom side between the muxes: TUSB1064 DP-edge straps / HPD / EN, TUSB1046 DP-edge straps / I2C_EN
    grid(h, ["R516", "R517", "R520", "R521", "R505", "R544", "R504", "C508",
             "R535", "R536", "R539", "R540", "R527", "R528"], 160.55, 65.35, 2)

    # ---------------- TUSB1046 ----------------
    h.put("U503", XU3, YU, 270)
    h.put("C530", 165.8, 64.85, 90)         # DS SSRX AC caps
    h.put("C531", 167.02, 64.85, 90)
    h.put("C526", 165.65, 64.95, 0, B)       # pin 6 (top edge)
    h.put("C525", 167.8, 64.95, 0, B)       # pin 1 (top edge)
    h.put("C527", 164.4, 72.85, 90, B)      # pin 20 (left edge, bottom end)
    h.put("C528", 167.7, 73.85, 90, B)      # pin 28 (bottom edge)
    h.put("C529", 165.45, 74.8, 0, B)      # 10u 0603
    grid(h, ["R533", "R534", "R537", "R538"], 164.95, 61.95, 2)            # top-edge straps
    # right-edge straps EQ0/EQ1/CAD_SNK: two vertical columns west of x 171.1 (2026-10-03) so the D507/D506 gap
    # column x 171.2-172.3 is free of bottom pads from y 61.2 to 70.6 (through vias for the J502 slow nets)
    for k, (ra, rb) in enumerate([("R531", "R532"), ("R529", "R530"), ("R523", "R524")]):
        h.put(ra, 169.5, 66.55 + 2.05 * k, 90, B)
        h.put(rb, 170.6, 66.55 + 2.05 * k, 90, B)
    h.put("R525", 164.9, 73.8, 0)           # DS_AUX_P 100k -> GND
    h.put("R526", 164.9, 75.05, 0)          # DS_AUX_N 100k -> 3V3
    h.put("R542", 167.95, 74.05, 0)         # DS_SBU1 2M 0603
    h.put("R543", 167.95, 75.8, 0)          # DS_SBU2 2M 0603

    # ---------------- downstream side: ESD + TX AC caps (top), protector (bottom) ----------------
    h.put("D507", 169.8, YESD2, 0)          # TX2/RX2 (left half of J502)
    h.put("D506", 173.6, YESD2, 180)        # TX1/RX1 (right half of J502)
    h.put("C534", 168.55, 64.8, 90)         # DS_TX2_P
    h.put("C535", 169.77, 64.8, 90)         # DS_TX2_N
    h.put("C533", 174.0, 64.8, 90)          # DS_TX1_N
    h.put("C532", 175.22, 64.8, 90)         # DS_TX1_P
    # U504 3.2 mm east (2026-10-03): frees the bottom under the D507/D506 gap (x 171.2-172.3) for through vias;
    # D+/D- ESD pins 19/20 face that via column, CC/SBU pins 1-5 face J502
    h.put("U504", XJ2 + 3.2, 63.4, 0, B)    # TPD6S300
    h.put("C537", 177.08, 62.72, 270, B)    # VBIAS 100n/50V 0603 (east of U504)
    h.put("C538", 176.85, 65.3, 90, B)      # VPWR (+3V3) 1u at pin 10
    h.put("R541", 177.95, 65.3, 90, B)      # FLT pull-up

    # ---------------- downstream VBUS: TVS + caps at J502, back-to-back switch + shunt toward +5V (hubrails) ----------------
    h.put("D505", 178.15, 64.95, 90)        # SMAJ6.0A VBUS_DS, right of J502
    h.put("C536", 178.3, 69.5, 0)          # VBUS_DS 100n/50V
    h.put("Q402", 176.05, 74.9, 0)          # AO4842: pin1 DS_SRC, pin3 VBUS_DS (left), common drain (right)
    h.put("R415", 170.85, 77.4, 90)         # 5 mOhm CSA-1 shunt, +5V end toward y 80 (hubrails)
    h.put("C422", 172.6, 73.0, 0, B)        # VBUS_DS 10u 0805 at Q402 pin 3
    h.put("C421", 170.85, 77.4, 90, B)      # +5V 10u 0805 under the shunt
    h.put("C415", 176.05, 78.85, 0)         # PMG1 VBUS_C_P1 (VBUS_DS) 100n/50V

    # ---------------- PMG1 ----------------
    h.put("U401", XP, YP, 180)
    xl, xr = XP - 3.755, XP + 3.755         # one 0402 column each side of the BGA (BGA courtyard +-3.0)
    h.put("C416", xl, 51.5, 90)             # LAPTOP_CC1 390p
    h.put("C417", xl, 53.62, 90)            # LAPTOP_CC2 390p
    h.put("C412", xl, 55.74, 90)            # VCONN port 0 (+5V) 1u
    h.put("C418", xr, 51.5, 90)             # DS_CC1 390p
    h.put("C419", xr, 53.62, 90)            # DS_CC2 390p
    h.put("C413", xr, 55.74, 90)            # VCONN port 1 (+5V) 1u
    # below the BGA (VDDD/VDDIO/VDDA balls, VCCD, VSYS are on the bottom rows after rot 180)
    x0 = XP - 3.25
    grid(h, ["C402", "C401", "C404", "C411"], x0, 57.85, 4, T, 0, 2.11)
    grid(h, ["C406", "C405", "C407", "C410"], x0, 59.07, 4, T, 0, 2.11)
    grid(h, ["C409", "C408"], x0, 60.55, 2, T, 0, 2.11)
    h.put("C403", x0 + 5.05, 60.55, 0)      # VDDD 4.7u 0603
    h.put("C414", x0 + 0.55, 62.3, 0)       # VBUS_C_P0 (VBUS_LAPTOP) 100n/50V 0603
    h.put("C420", x0 + 3.35, 62.3, 0)       # XRES 100n
    h.put("R401", x0 + 5.5, 62.3, 0)        # XRES 4.7k pull-up
    # bottom-side column left of the BGA (never under it)
    h.put("R406", xl, 51.5, 90, B)          # EXT_PWR_PRESENT 100k pull-down (ball G15, left)
    h.put("R403", xl, 53.7, 90, B)         # I2C_PD_INT_N 10k pull-up to VDDD
    h.put("U1204", 161.0, 58.4, 0, B)       # TMP1075 "PMG1/MUX": between BGA and TUSB1064, bottom
    h.put("C1204", 163.55, 58.4, 90, B)

    # ---------------- PMG1 periphery ----------------
    grid(h, ["R407", "R408", "R409"], 150.6, 76.15, 3)       # MUX_UP CTL0/CTL1/FLIP pull-downs (bottom)
    # MUX_DS CTL0/CTL1/FLIP pull-downs + DS HPD series R (bottom): under the TX1/RX1 lane copper south of U504,
    # where no through via fits anyway (2026-10-03; was a row at y 71.2 / grid cell)
    for k, r in enumerate(["R410", "R411", "R412", "R522"]):
        h.put(r, 173.7, 66.6 + 1.25 * k, 0, B)
    h.put("R414", 152.2, 74.05, 0)          # HPD0_OUT -> UP_HPD 1k
    h.put("R413", 152.2, 75.3, 0)           # HPD1_OUT -> DS_HPD 1k
    h.put("R404", 152.2, 76.55, 0)          # P3V3_SNS 10k
    h.put("R405", 152.2, 77.8, 0)           # P3V3_SNS 100k
    # SWD/XRES cut jumpers + XRES isolation FET: bottom side, bottom-right corner (toward the RP2350 at x>180, y>80)
    h.put("JP401", 177.9, 72.75, 0, B)      # XRES
    h.put("JP402", 177.9, 75.55, 0, B)      # SWDIO
    h.put("JP403", 177.9, 78.35, 0, B)      # SWCLK
    h.put("Q401", 174.2, 77.1, 90, B)       # XRES pass FET (gate = +3V3)
    h.put("R402", 175.35, 73.5, 90, B)      # XRES_RP 10k pull-up
    # probe pads (SWDIO_L, SWCLK_L, XRES, UART TX/RX, GND), top, free corner left of the lane fan-in
    grid(h, ["TP401", "TP402", "TP403", "TP404", "TP405", "TP406"], 139.6, 67.6, 3, T, 0, 2.35, 2.35)
    # thermocouple pads (GND copper) - floorplan puts them here; their targets (L301, USB7206C) are in hubrails
    h.put("TP1205", 159.9, 78.3, 0)         # TC_HUB: closest point of this region to the USB7206C
    h.put("TP1204", 163.6, 78.3, 0)         # TC_5V_L
