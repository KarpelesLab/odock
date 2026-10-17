"""odock-10 power routing: power pours on L1/L6 (+ two L3 helper pours), via arrays for layer changes and thermal
paths, Kelvin sense and gate-drive connections of the power stages, card-reader VCC.

Runs after a_planes.py (L2/L5 GND planes, L4 islands, GND pours/keep-outs). Pour priorities: GND pours 0,
L4 islands 5, power pours 10, switch-node copper 11, hot-loop GND copper 12.
Notes: docs/routing-notes/power.md.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _pwrlib as L  # noqa: E402

rect = L.rect

# ------------------------------------------------------------------------------------------------ pours
# (name, net, layer, polygon, priority)
POURS = [
    # --- power input: barrel (VBAR) and PD-in (VBUS_PDIN) to the ideal-diode pairs, OR node, shunt
    ("P_VBAR_L1", "VBAR", "F.Cu", rect(101.5, 58.4, 106.3, 63.8), 10),
    # J102 pin 1 -> down between the left peg and the sleeve pin -> along y 62-64 -> Q106 sources (bottom)
    ("P_VBAR_L6", "VBAR", "B.Cu", [(110.4, 50.5), (116.2, 50.5), (116.2, 52.3), (111.85, 52.3), (111.85, 63.75),
                                   (102.95, 63.75), (102.95, 69.45), (100.6, 69.45), (100.6, 61.7), (101.9, 61.7),
                                   (101.9, 59.6), (103.7, 59.6), (103.7, 61.7), (110.4, 61.7)], 10),
    ("P_BAR_MID_L6", "BAR_MID", "B.Cu", rect(103.3, 63.85, 113.45, 68.75), 10),
    ("P_PD_MID_L6", "PD_MID", "B.Cu", rect(118.15, 63.85, 128.3, 68.75), 10),
    ("P_VBUS_PDIN_L1", "VBUS_PDIN", "F.Cu", rect(127.55, 61.7, 132.15, 66.55), 10),
    ("P_VBUS_PDIN_L6", "VBUS_PDIN", "B.Cu", [(128.9, 63.85), (130.8, 63.85), (130.8, 65.5), (134.2, 65.5),
                                             (134.2, 67.25), (130.8, 67.25), (130.8, 67.6), (128.9, 67.6)], 10),
    ("P_VIN_OR_L6", "VIN_OR", "B.Cu", [(114.0, 63.9), (117.4, 63.9), (117.4, 69.25), (116.7, 69.25),
                                       (116.7, 70.55), (111.9, 70.55), (111.9, 69.6), (114.0, 69.6)], 10),
    ("P_VIN_L6_R137", "VIN", "B.Cu", [(109.2, 74.9), (112.0, 74.9), (112.0, 76.45), (115.6, 76.45), (115.6, 78.3),
                                      (109.2, 78.3)], 10),
    # --- LM51770 buck-boost: buck leg (VIN / SW1 / LS), boost leg (SW2 / PSO), output (VBB_OUT)
    ("P_VIN_L1_BUCK", "VIN", "F.Cu", rect(106.85, 99.15, 112.0, 107.85), 10),
    ("P_VIN_L6_BUCK", "VIN", "B.Cu", [(104.3, 104.4), (106.6, 104.4), (106.6, 99.3), (112.2, 99.3), (112.2, 104.6),
                                      (108.3, 104.6), (108.3, 107.9), (104.3, 107.9)], 10),
    ("P_GND_HOT_BB1", "GND", "F.Cu", rect(100.7, 102.6, 106.45, 107.85), 12),
    ("P_GND_HOT_BB1B", "GND", "F.Cu", rect(112.15, 104.5, 114.1, 107.85), 12),
    ("P_BB_SW1", "BB_SW1", "F.Cu", [(100.7, 92.9), (101.7, 92.9), (101.7, 96.9), (112.0, 96.9), (112.0, 98.35),
                                    (106.0, 98.35), (106.0, 101.9), (100.7, 101.9)], 11),
    ("P_BB_LS", "BB_LS", "F.Cu", [(101.6, 89.5), (111.0, 89.5), (111.0, 92.4), (108.4, 92.4), (108.4, 96.6),
                                  (107.35, 96.6), (107.35, 92.4), (101.6, 92.4)], 11),
    ("P_BB_SW2", "BB_SW2", "F.Cu", [(104.6, 81.2), (108.5, 81.2), (108.5, 79.45), (111.45, 79.45), (111.45, 85.7),
                                    (101.6, 85.7), (101.6, 82.8), (104.6, 82.8)], 11),
    ("P_BB_PSO_L1A", "BB_PSO", "F.Cu", [(104.6, 71.2), (107.3, 71.2), (107.3, 81.0), (104.5, 81.0), (104.5, 78.0),
                                        (101.2, 78.0), (101.2, 75.9), (104.6, 75.9)], 10),
    ("P_BB_PSO_L1B", "BB_PSO", "F.Cu", rect(111.6, 71.2, 113.15, 75.1), 10),
    ("P_BB_PSO_L6", "BB_PSO", "B.Cu", [(103.4, 74.3), (105.2, 74.3), (105.2, 78.6), (107.4, 78.6), (107.4, 81.0),
                                       (103.4, 81.0)], 10),
    ("P_GND_HOT_BB2", "GND", "F.Cu", [(107.6, 71.2), (109.4, 71.2), (109.4, 78.1), (111.45, 78.1), (111.45, 79.3),
                                      (109.45, 79.3), (109.45, 78.35), (107.6, 78.35)], 12),
    ("P_GND_HOT_BB2B", "GND", "F.Cu", rect(101.2, 73.0, 104.3, 74.8), 12),
    ("P_VIN_L1_C122", "VIN", "F.Cu", rect(130.9, 88.2, 134.2, 93.0), 10),
    ("P_VBB_OUT_A", "VBB_OUT", "F.Cu", rect(118.75, 67.95, 121.5, 75.25), 10),
    ("P_VBB_OUT_B", "VBB_OUT", "F.Cu", rect(115.1, 75.3, 117.95, 82.0), 10),
    ("P_VBB_OUT_C211", "VBB_OUT", "F.Cu", rect(121.8, 74.9, 126.6, 78.6), 10),
    ("P_VBB_OUT_C212", "VBB_OUT", "F.Cu", rect(121.8, 83.2, 126.6, 86.0), 10),
    # --- laptop source switch (Q213/Q214), sink path, laptop VBUS
    ("P_SRC_MID_L1", "SRC_MID", "F.Cu", rect(122.3, 67.9, 132.45, 73.0), 10),
    ("P_SRC_MID_L6", "SRC_MID", "B.Cu", rect(123.8, 69.0, 132.6, 74.2), 10),
    ("P_VBUS_LSW_L1A", "VBUS_LSW", "F.Cu", [(133.25, 69.35), (135.0, 69.35), (135.0, 71.35), (138.3, 71.35),
                                            (138.3, 72.3), (133.25, 72.3)], 10),
    ("P_VBUS_LSW_L3", "VBUS_LSW", "In2.Cu", rect(133.4, 69.5, 138.6, 81.6), 10),
    ("P_VBUS_LSW_L1B", "VBUS_LSW", "F.Cu", rect(134.75, 78.3, 138.5, 81.3), 10),
    ("P_VBUS_LAPTOP_L1A", "VBUS_LAPTOP", "F.Cu", [(133.2, 64.1), (135.95, 64.1), (135.95, 67.6), (137.3, 67.6),
                                                  (137.3, 68.5), (133.2, 68.5)], 10),
    ("P_VBUS_LAPTOP_L1B", "VBUS_LAPTOP", "F.Cu", rect(139.5, 57.4, 143.3, 63.1), 10),
    ("P_VBUS_LAPTOP_L6", "VBUS_LAPTOP", "B.Cu", rect(138.6, 53.6, 153.6, 61.4), 10),
    ("P_P5V_SINK_L6", "+5V", "B.Cu", rect(131.5, 76.1, 132.75, 78.2), 10),
    ("P_SNK_MID_L1", "SNK_MID", "F.Cu", rect(133.45, 78.4, 134.45, 80.3), 10),
    # --- LM5148 5 V / 8 A (hubrails)
    ("P_VIN_L1_HUB", "VIN", "F.Cu", [(140.25, 96.4), (143.2, 96.4), (143.2, 99.3), (140.4, 99.3), (140.4, 106.9),
                                     (143.6, 106.9), (143.6, 105.5), (145.6, 105.5), (145.6, 106.9),
                                     (148.8, 106.9), (148.8, 103.3), (150.6, 103.3), (150.6, 107.8),
                                     (138.3, 107.8), (138.3, 99.8), (140.25, 99.8)], 10),
    ("P_VIN_L6_HUB", "VIN", "B.Cu", [(138.3, 95.8), (143.4, 95.8), (143.4, 99.6), (140.6, 99.6), (140.6, 106.3),
                                     (138.3, 106.3)], 10),
    ("P_GND_HOT_5V", "GND", "F.Cu", [(141.6, 100.1), (145.3, 100.1), (145.3, 101.4), (149.1, 101.4),
                                     (149.1, 103.2), (147.6, 103.2), (147.6, 106.6), (145.75, 106.6),
                                     (145.75, 105.3), (143.4, 105.3), (143.4, 106.75), (141.6, 106.75)], 12),
    ("P_5V_SW", "5V_SW", "F.Cu", [(142.3, 91.7), (148.2, 91.7), (148.2, 95.75), (150.3, 95.75), (150.3, 100.75),
                                  (145.4, 100.75), (145.4, 99.25), (143.25, 99.25), (143.25, 97.3),
                                  (144.75, 97.3), (144.75, 95.4), (142.3, 95.4)], 11),
    ("P_5V_SW_L6", "5V_SW", "B.Cu", rect(145.4, 95.8, 150.4, 100.8), 11),
    ("P_5V_ISNS_L1", "5V_ISNS", "F.Cu", [(142.3, 80.45), (156.0, 80.45), (156.0, 81.35), (152.3, 81.35),
                                         (152.3, 84.2), (142.3, 84.2)], 10),
    ("P_5V_BUCK_L1", "5V_BUCK", "F.Cu", rect(152.2, 87.35, 156.0, 88.2), 10),
    ("P_5V_BUCK_L6", "5V_BUCK", "B.Cu", [(139.3, 82.95), (148.75, 82.95), (148.75, 85.95), (155.1, 85.95),
                                         (155.1, 88.0), (149.4, 88.0), (149.4, 90.55), (139.3, 90.55)], 10),
    ("P_5V_OR_L6", "5V_OR", "B.Cu", [(149.6, 80.5), (159.1, 80.5), (159.1, 81.5), (154.5, 81.5), (154.5, 85.6),
                                     (149.6, 85.6)], 10),
    ("P_P5V_R312_L6", "+5V", "B.Cu", [(155.3, 87.3), (162.8, 87.3), (162.8, 88.55), (158.6, 88.55), (158.6, 92.6),
                                      (155.3, 92.6)], 10),
    # --- downstream USB-C VBUS (usbc block)
    ("P_DS_SRC_L1", "DS_SRC", "F.Cu", [(169.75, 72.45), (174.8, 72.45), (174.8, 73.55), (172.35, 73.55),
                                       (172.35, 76.75), (169.75, 76.75)], 10),
    ("P_VBUS_DS_Q402", "VBUS_DS", "F.Cu", rect(174.3, 74.85, 177.2, 76.2), 10),
    ("P_DS_FETD", "DS_FETD", "F.Cu", rect(177.3, 72.45, 179.65, 77.35), 10),
    ("P_VBUS_DS_D505", "VBUS_DS", "F.Cu", rect(176.8, 65.4, 179.4, 70.3), 10),
    # --- Ethernet rails: U802 OUT pins and L801 output pad to their L4 islands
    ("P_ETH_3V3_U802", "ETH_3V3", "F.Cu", rect(183.5, 54.7, 186.2, 57.2), 10),
    ("P_ETH_0V95_L801", "ETH_0V95", "F.Cu", rect(183.85, 64.7, 186.5, 69.0), 10),
    # --- USB-A port power (front): TPS2553 OUT -> POSCAP -> VBUS pin; shunt -> SW_IN -> TPS IN (via L3 strip)
    ("P_USBA1_OUT", "+5V_USBA1", "F.Cu", [(140.9, 118.7), (144.9, 118.7), (144.9, 114.8), (146.95, 114.8),
                                          (146.95, 117.3), (147.4, 117.3), (147.4, 123.2), (149.2, 124.3),
                                          (149.2, 126.4), (146.3, 126.4), (146.3, 121.5), (140.9, 121.5)], 10),
    ("P_USBA2_OUT", "+5V_USBA2", "F.Cu", [(159.9, 118.7), (163.9, 118.7), (163.9, 114.8), (165.95, 114.8),
                                          (165.95, 117.3), (166.4, 117.3), (166.4, 123.2), (168.2, 124.3),
                                          (168.2, 126.4), (165.3, 126.4), (165.3, 121.5), (159.9, 121.5)], 10),
    ("P_USBA1_SWIN_L1", "USBA1_SW_IN", "F.Cu", rect(147.2, 114.8, 149.3, 117.0), 10),
    ("P_USBA1_SWIN_L6", "USBA1_SW_IN", "B.Cu", [(148.45, 111.4), (149.3, 111.4), (149.3, 114.1), (148.45, 114.1)], 10),
    ("P_USBA1_SWIN_L3", "USBA1_SW_IN", "In2.Cu", rect(147.2, 111.3, 149.3, 117.1), 10),
    ("P_USBA2_SWIN_L1", "USBA2_SW_IN", "F.Cu", rect(166.2, 114.8, 168.3, 117.0), 10),
    ("P_USBA2_SWIN_L6", "USBA2_SW_IN", "B.Cu", [(167.45, 111.4), (168.3, 111.4), (168.3, 114.1), (167.45, 114.1)], 10),
    ("P_USBA2_SWIN_L3", "USBA2_SW_IN", "In2.Cu", rect(166.2, 111.3, 168.3, 117.1), 10),
]
ZONES = [p[0] for p in POURS]

# Nets whose tracks/vias this script draws (old copies are deleted before route()). Pour-only nets (BAR_MID,
# PD_MID, DS_SRC, DS_FETD, +5V_USBA1/2) are not listed; GND vias placed here are covered by a_planes' NETS.
NETS = [
    "VBAR", "VBUS_PDIN", "VIN_OR", "VIN", "BAR_DGATE", "BAR_HGATE", "PD_DGATE", "PD_HGATE",
    "BB_SW1", "BB_SW2", "BB_LS", "BB_PSO", "VBB_OUT", "BB_HO1", "BB_HO2", "BB_LO1", "BB_LO2", "BB_HB1", "BB_HB2",
    "BB_G1", "BB_G2", "BB_G3", "BB_G4", "BB_CSA", "BB_CSB",
    "SRC_MID", "SRC_DGATE", "SRC_HGATE", "VBUS_LSW", "VBUS_LAPTOP", "SNK_MID", "SNK_GATE", "+5V",
    "5V_SW", "5V_ISNS", "5V_BUCK", "5V_OR", "5V_HO", "5V_HG", "5V_LG", "5V_BOOT", "5V_ORG",
    "+3V3", "+1V15", "3V3_SW", "1V15_SW",
    "3V3_BST", "1V15_BST", "ETH_SW",
    "VBUS_DS",
    "USBA1_SW_IN", "USBA2_SW_IN",
    "ETH_0V95", "ETH_3V3", "CR_SD_VCC", "CR_USD_VCC",
    "GND",      # hot-loop GND via rows and the GND escapes above (z_stitch.py adds the board-wide stitching last)
]

# Pads that may hold a via (EP thermal arrays; filled via-in-pad is free on JLC 6-layer).
EP_OK = {("Q201", "9"), ("Q204", "9"), ("Q213", "8"), ("Q214", "8"), ("Q301", "8"), ("Q302", "9"),
         ("Q303", "9"), ("Q217", "9"), ("D101", "1"), ("Q104", "1"), ("Q104", "2"), ("Q104", "3"),
         ("R312", "2"), ("C324", "1"), ("C323", "1"), ("R202", "1"), ("R137", "2"), ("R303", "2"),
         ("Q303", "1"), ("Q303", "2"), ("Q303", "3"), ("R415", "1"), ("C421", "1")}

# ------------------------------------------------------------------------------------------------ via fields
# (net, area (x0,y0,x1,y1) or polygon, max count, pitch, size, drill)
VIAS = [
    # input
    ("VBAR", (101.0, 63.1, 106.0, 63.6), 6, 0.9, 0.6, 0.3),        # D102.1 -> L4 VBAR
    ("VBAR", (100.95, 65.0, 101.2, 69.4), 4, 0.9, 0.5, 0.25),      # Q106 sources (left of the pins)
    ("VBAR", (102.5, 65.0, 102.95, 66.0), 1, 0.9, 0.5, 0.25),      # Q106 sources (right of the pins)
    ("VBUS_PDIN", (129.4, 63.6, 130.3, 67.2), 3, 1.2, 0.6, 0.3),   # D101.1 / Q104 sources (filled via-in-pad)
    ("VBUS_PDIN", (132.15, 64.4, 133.0, 65.6), 1, 0.9, 0.6, 0.3),  # C101
    ("VBUS_PDIN", (127.2, 60.9, 128.9, 63.4), 1, 0.9, 0.5, 0.25),  # C102
    ("VIN", [(109.4, 74.9), (112.0, 74.9), (112.0, 76.4), (115.6, 76.4), (115.6, 78.3), (109.4, 78.3)], 12, 0.85,
     0.6, 0.3, True),                                               # R137.2 (outer half) -> L4 VIN tab
    # buck leg
    ("VIN", (107.4, 99.6, 111.5, 103.0), 12, 1.1, 0.6, 0.3),       # Q201 EP (thermal + VIN to L4/L6)
    ("VIN", (106.0, 103.9, 112.0, 107.85), 6, 0.9, 0.6, 0.3),      # C201/C203/C202/C204
    ("GND", (100.8, 103.8, 106.4, 107.8), 10, 0.9, 0.6, 0.3),      # Q202 sources / C201.2 / C204.2
    ("GND", (112.2, 104.0, 114.1, 107.8), 6, 0.9, 0.6, 0.3),       # C203.2 / C202.2
    ("VIN", (130.9, 88.2, 134.4, 93.2), 6, 0.9, 0.6, 0.3),         # C122
    # boost leg / PSO
    ("BB_PSO", (104.8, 79.2, 107.0, 80.7), 3, 0.9, 0.6, 0.3),      # Q204 EP
    ("BB_PSO", (101.2, 75.0, 107.3, 78.3), 6, 0.9, 0.6, 0.3),      # C206/C207/C208
    ("BB_PSO", (111.5, 70.6, 113.1, 75.3), 7, 0.9, 0.6, 0.3, True),  # R202.1 (east half left for R137 Kelvin)
    ("GND", (101.2, 72.9, 104.3, 74.9), 4, 0.9, 0.6, 0.3),         # C208.2
    ("GND", (107.5, 71.2, 111.5, 79.3), 8, 0.9, 0.6, 0.3),         # C205.2 / C206.2 / C207.2 / Q203 sources
    # output
    ("VBB_OUT", (116.85, 75.4, 117.85, 82.0), 6, 0.9, 0.6, 0.3, True),  # C209.1 / C210.1
    ("VBB_OUT", (117.2, 70.0, 121.5, 75.3), 6, 0.9, 0.6, 0.3),     # R202.2 / Q213 sources
    ("VBB_OUT", (121.8, 74.9, 126.6, 78.8), 5, 0.9, 0.6, 0.3),     # C211.1
    ("VBB_OUT", (121.8, 83.0, 126.6, 86.2), 5, 0.9, 0.6, 0.3),     # C212.1
    ("SRC_MID", (122.7, 68.5, 126.1, 72.5), 9, 1.1, 0.6, 0.3),     # Q213 EP
    ("SRC_MID", (128.7, 68.5, 132.1, 72.5), 9, 1.1, 0.6, 0.3),     # Q214 EP
    ("VBUS_LSW", (134.6, 69.5, 138.3, 72.3), 6, 0.9, 0.6, 0.3),    # Q214 sources / R243.1 -> L3
    ("VBUS_LSW", (137.6, 78.3, 138.4, 81.3), 4, 0.8, 0.6, 0.3),    # Q217 -> L3
    ("VBUS_LAPTOP", (133.2, 63.9, 138.3, 70.2), 8, 0.9, 0.6, 0.3),  # C233 / R243.2 -> L4
    ("VBUS_LAPTOP", (139.0, 60.2, 143.6, 61.8), 8, 0.8, 0.6, 0.3),  # D501.1 -> L4 / L6
    ("VBUS_LAPTOP", (141.6, 61.6, 142.8, 63.4), 1, 0.9, 0.6, 0.3),  # C501
    ("VBUS_LAPTOP", (138.6, 53.6, 153.6, 61.4), 14, 1.4, 0.6, 0.3),  # stitch the L6 pour fragments (USB2/SBU/CC cut it)
    ("+5V", (131.3, 75.8, 132.9, 78.2), 4, 0.8, 0.6, 0.3, True),    # U206 OUT -> L4 +5V
    # LM5148 stage
    ("VIN", (140.3, 96.5, 143.0, 99.3), 9, 0.9, 0.6, 0.3),          # Q301 drain/EP (thermal)
    ("VIN", (138.4, 99.4, 140.7, 107.6), 6, 0.9, 0.6, 0.3),         # C301/C302/C304/C306
    ("VIN", (143.3, 105.3, 150.6, 107.8), 4, 0.9, 0.6, 0.3),        # C305/C303
    ("GND", (141.6, 100.1, 149.1, 106.75), 12, 0.8, 0.6, 0.3),      # hot-loop GND row into L2
    ("5V_SW", (145.9, 97.0, 149.9, 100.3), 9, 1.0, 0.6, 0.3),       # Q302 EP -> bottom SW pour (thermal)
    ("5V_BUCK", (152.5, 87.25, 155.7, 87.9), 5, 0.7, 0.6, 0.3),     # R303.2 (outer half) -> Q303 sources / L6
    ("5V_BUCK", (139.3, 82.95, 148.75, 90.55), 10, 1.2, 0.6, 0.3),  # bottom pour -> L4 copy
    ("+5V", (155.4, 87.3, 158.9, 88.5), 10, 0.75, 0.6, 0.3, True),  # R312.2 (outer half, via-in-pad) -> L4 +5V
    ("+5V", (158.9, 87.3, 162.8, 88.6), 6, 0.75, 0.6, 0.3, True),   # R312.2 bottom pour east of U303 -> L4
    ("+5V", (155.3, 88.5, 158.6, 92.8), 6, 0.75, 0.6, 0.3),         # R312.2 pour -> L4 (after the sense routes)
    ("+5V", (154.6, 102.6, 157.4, 108.0), 5, 0.9, 0.6, 0.3),        # C323
    ("+5V", (155.6, 94.8, 157.6, 98.2), 3, 0.9, 0.6, 0.3),          # C324
    # small bucks
    ("+3V3", (160.5, 81.6, 163.7, 85.2), 6, 0.9, 0.6, 0.3),         # L302.2 / Cout -> L4 +3V3
    ("+5V", (160.0, 86.6, 167.5, 91.0), 4, 0.9, 0.6, 0.3),          # U304 VIN / C326-C328
    ("+1V15", (173.6, 79.9, 179.3, 83.6), 5, 0.9, 0.6, 0.3),        # L303.2 / Cout -> L4 +1V15
    # downstream USB-C
    ("VBUS_DS", (175.15, 74.3, 177.1, 76.9), 3, 0.8, 0.6, 0.3),     # Q402 pin 3 -> L4
    ("VBUS_DS", (176.6, 65.2, 179.5, 70.5), 3, 0.9, 0.6, 0.3),      # D505 / C536
    ("VBUS_DS", (170.8, 71.2, 172.5, 74.2), 1, 0.9, 0.5, 0.25),     # C422 (bottom)
    # USB-A ports
    ("+5V", (145.6, 111.0, 147.6, 114.0), 3, 0.8, 0.6, 0.3),        # R704.1 -> L4
    ("USBA1_SW_IN", (147.8, 111.3, 149.3, 112.3), 2, 0.8, 0.6, 0.3),
    ("USBA1_SW_IN", (147.2, 116.1, 149.1, 117.0), 2, 0.8, 0.6, 0.3),
    ("+5V", (164.6, 111.0, 166.6, 114.0), 3, 0.8, 0.6, 0.3),        # R709.1 -> L4
    ("USBA2_SW_IN", (166.8, 111.3, 168.3, 112.3), 2, 0.8, 0.6, 0.3),
    ("USBA2_SW_IN", (166.2, 116.1, 168.1, 117.0), 2, 0.8, 0.6, 0.3),
    # Ethernet rails
    ("ETH_0V95", (183.6, 64.6, 186.4, 69.4), 4, 0.9, 0.5, 0.25),    # L801.2 -> L4 island
    ("ETH_3V3", (183.6, 54.7, 186.2, 57.2), 3, 0.9, 0.5, 0.25),     # U802 OUT -> L4 island
]


# ------------------------------------------------------------------------------------------------ local routes
# U201 pins are entered at the toe (or the inner end) rather than the pad centre, so no track runs along a 0.5 mm
# pitch pad next to its HV neighbour.
# (net, from, to, layers, width). from/to: (ref, pad) = pad centre, (ref, pad, dx, dy) = offset from it (Kelvin
# taps at the inner pad edge), or (x, y). Routed by the small grid router in this order.
F, B, I2 = "F.Cu", "B.Cu", "In2.Cu"
ROUTES = [
    # LM51770 gate drive (0 ohm resistors R203-R206 in the loop), bootstrap and driver returns. Bootstrap/SW
    # returns first (shortest loops), then gate drives, then the Kelvin taps (which may use L3).
    # R202 output-current sense first: pins 22 (VBB_OUT) / 23 (PSO) leave north up the toe column (C220 is now on
    # the bottom), U201.20 joins C210 directly
    ("VBB_OUT", ("R202", "2", -0.5, 0.0), ("U201", "22", -0.65, 0.0), (F, I2), 0.15, {"via": (0.4, 0.2), "window": 4.0}),
    ("BB_PSO", ("R202", "1", 0.5, 0.0), ("U201", "23", -0.65, 0.0), (F, I2), 0.15, {"via": (0.4, 0.2), "window": 4.0}),
    ("VBB_OUT", ("U201", "20", -0.65, 0.0), ("C210", "1"), (F,), 0.2),
    # boost bootstrap: C220 (bottom) under pins 25/26, reached through small vias next to the pin ends
    ("BB_SW2", ("U201", "25", -0.65, 0.0), ("Q203", "8"), (F,), 0.25),
    ("BB_SW2", ("U201", "25", 0.65, 0.0), ("C220", "2"), (F, B), 0.2, {"via": (0.35, 0.15), "no_body": True}),
    ("BB_HB2", ("U201", "26", 0.65, 0.0), ("@via", 1), (F,), 0.2, {"no_body": True}),     # @via 1 = DIRECT_VIAS[1]
    ("BB_HB2", ("@via", 1), ("C220", "1"), (B,), 0.2, {"no_body": True}),
    ("BB_HO2", ("U201", "27", -0.65, 0.0), ("R206", "1"), (F, I2, B), 0.25, {"via": (0.4, 0.2), "window": 5.0}),
    ("BB_LO2", ("U201", "29", -0.65, 0.0), ("R205", "1"), (F, I2, B), 0.25, {"via": (0.4, 0.2), "window": 5.0}),
    ("BB_G3", ("R205", "2"), ("Q203", "4"), (F, I2, B), 0.3, {"window": 6.0}),
    ("BB_G4", ("R206", "2"), ("Q204", "4"), (F, I2, B), 0.3, {"window": 6.0}),
    ("BB_SW1", ("U201", "36", -0.65, 0.0), ("C219", "2"), (F,), 0.25),
    ("BB_HB1", ("U201", "35", -0.65, 0.0), ("C219", "1"), (F,), 0.25),
    ("BB_SW1", ("C219", "2"), ("Q201", "1"), (F, I2), 0.3),
    ("BB_HO1", ("U201", "34", -0.65, 0.0), ("R203", "1"), (F, I2), 0.25, {"via": (0.4, 0.2)}),
    ("BB_LO1", ("U201", "32", -0.65, 0.0), ("R204", "1"), (F, I2), 0.25, {"via": (0.4, 0.2)}),
    ("BB_G1", ("Q201", "4"), ("R203", "2"), (F, I2), 0.3),
    ("BB_G2", ("R204", "2"), ("Q202", "4"), (F, I2), 0.3),
    # R201 current sense (Kelvin from the inner pad edges) -> R210/R211/C221 filter -> CSA/CSB
    ("BB_SW1", ("R201", "1", 0.5, 0.0), ("R210", "1"), (F, B), 0.15),
    ("BB_LS", ("R201", "2", -0.5, 0.0), ("R211", "1"), (F, B), 0.15),
    ("BB_CSA", ("R210", "2"), ("C221", "1"), (B,), 0.15),
    ("BB_CSB", ("R211", "2"), ("C221", "2"), (B,), 0.15),
    ("BB_CSB", ("C221", "2"), ("U201", "38", -0.65, 0.0), (B, F, I2), 0.15, {"via": (0.4, 0.2)}),
    # GND of the parts that now sit on the bottom inside the boost switch-node area (no vias allowed under SW2):
    # out on L6 to a via north of the area (C114, R122) or south of it (TP1202)
    ("GND", ("R122", "2"), (109.8, 79.0), (B,), 0.25, {"end_via": (108.4, 78.4, 112.4, 79.3), "cross_pours": True}),
    ("GND", ("C114", "2"), ("R122", "2"), (B,), 0.25, {"cross_pours": True}),
    ("GND", ("TP1202", "1"), (108.1, 86.3), (B,), 0.3, {"end_via": (106.0, 85.9, 110.5, 88.0)}),
    # ideal-diode / source-switch gate drives
    ("BAR_DGATE", ("Q106", "4"), ("U105", "1"), (B, I2), 0.25),
    ("BAR_HGATE", ("Q107", "4"), ("U105", "8"), (B, I2), 0.25),
    ("PD_HGATE", ("Q105", "4"), ("U104", "8"), (B, I2), 0.25),
    ("PD_DGATE", ("Q104", "4"), ("U104", "1"), (B, I2), 0.25),
    ("SRC_DGATE", ("Q213", "4"), ("U202", "1"), (F, B, I2), 0.25),
    ("SRC_HGATE", ("Q214", "4"), ("U202", "8"), (F, B, I2), 0.25),
    # input-current (R137 -> INA237 U109) and laptop-current (R243 -> INA226 U204) Kelvin taps
    ("VIN", ("R137", "2", 0.0, -0.45), ("U109", "9"), (B, I2), 0.15),
    ("VIN_OR", ("R137", "1", 0.0, 0.45), ("U109", "10"), (B, I2, F), 0.15, {"via": (0.4, 0.2), "window": 5.0}),
    ("VIN", ("U109", "9"), ("U109", "8"), (B,), 0.15),
    ("VBUS_LSW", ("R243", "1", 0.0, -0.4), ("U204", "10"), (F, B, I2), 0.15),
    ("VBUS_LAPTOP", ("R243", "2", 0.0, 0.4), ("U204", "9"), (F, B, I2), 0.15),
    ("VBUS_LAPTOP", ("U204", "9"), ("U204", "8"), (B,), 0.15),
    # sink path: Q217 -> U206 -> +5V
    ("SNK_MID", ("Q217", "2"), ("U206", "5"), (F, B), 0.3),
    ("SNK_GATE", ("Q217", "4"), ("U205", "6"), (F,), 0.25),
    ("+5V", ("U206", "6"), (132.2, 77.5), (B,), 0.3),
    # LM5148 gate drive, bootstrap, SW return, current sense
    ("5V_HG", ("Q301", "4"), ("R301", "2"), (F, I2), 0.4, {"window": 6.0}),
    ("5V_HO", ("R301", "1"), ("U301", "13"), (F,), 0.25),
    ("5V_LG", ("U301", "11"), ("Q302", "4"), (F, I2), 0.4),
    ("5V_BOOT", ("C307", "1"), ("U301", "15"), (F,), 0.25),
    ("5V_SW", ("C307", "2"), ("U301", "14"), (F,), 0.25),
    ("5V_SW", ("U301", "14"), ("Q302", "5"), (F, I2), 0.3),
    ("5V_BUCK", ("R303", "2", 0.0, -0.45), ("U301", "21"), (F, I2), 0.15),
    ("5V_ISNS", ("R303", "1", 0.0, 0.45), ("U301", "20"), (F, I2), 0.15),
    ("5V_BUCK", ("U301", "16"), ("R303", "2"), (F, I2, B), 0.15, {"window": 5.0}),
    ("5V_ORG", ("Q303", "4"), ("U302", "5"), (B,), 0.25, {"cross_pours": True}),
    ("5V_OR", ("R312", "1", 0.0, 0.45), ("U303", "10"), (B, I2), 0.15),
    ("+5V", ("R312", "2", 0.0, -0.45), ("U303", "9"), (B, I2), 0.15),
    ("+5V", ("U303", "9"), ("U303", "8"), (B,), 0.15),
    # small bucks (hubrails) and the Ethernet buck: SW node, bootstrap
    ("3V3_SW", ("U304", "5"), ("L302", "1"), (F,), 0.3),
    ("3V3_SW", ("C330", "2"), ("L302", "1"), (B, F), 0.3),
    ("3V3_BST", ("C330", "1"), ("U304", "6"), (B, F), 0.25),
    ("1V15_SW", ("U305", "5"), ("L303", "1"), (F,), 0.3),
    ("1V15_SW", ("C337", "2"), ("L303", "1"), (B, F), 0.3),
    ("1V15_BST", ("C337", "1"), ("U305", "6"), (B, F), 0.25),
    ("+5V", ("U305", "3"), ("C336", "1"), (F,), 0.25),
    ("ETH_SW", ("U803", "2"), ("L801", "1"), (F,), 0.3),
    # USB-A port current-sense Kelvin taps (INA180 IN+/IN- from the inner edges of R704/R709)
    ("+5V", ("R704", "1", 0.35, 0.0), ("U703", "3"), (B, I2), 0.15),
    ("USBA1_SW_IN", ("R704", "2", -0.35, 0.0), ("U703", "4"), (B, I2), 0.15),
    ("+5V", ("R709", "1", 0.35, 0.0), ("U706", "3"), (B, I2), 0.15),
    ("USBA2_SW_IN", ("R709", "2", -0.35, 0.0), ("U706", "4"), (B, I2), 0.15),
    # card-reader VCC (>= 0.4 mm)
    ("CR_USD_VCC", ("U901", "24"), ("C916", "1"), (B,), 0.25),
    ("CR_USD_VCC", ("C916", "1"), ("C915", "1"), (B,), 0.4),
    ("CR_SD_VCC", ("U901", "23"), ("C913", "1"), (B, I2), 0.25, {"via": (0.4, 0.2)}),
    ("CR_SD_VCC", ("C913", "1"), ("C914", "1"), (B, I2), 0.4, {"via": (0.45, 0.25)}),
    ("CR_SD_VCC", ("C914", "1"), ("J901", "4"), (B, I2, F), 0.4, {"via": (0.45, 0.25), "window": 4.0}),
    # downstream USB-C VBUS: A-row pins joined to the B-row pins between the rows (if the HS vias leave room)
    ("VBUS_DS", ("J502", "A4"), ("J502", "B9"), (F,), 0.2, {"cross_pours": True, "window": 1.0}),
    ("VBUS_DS", ("J502", "B9"), (172.5, 57.4), (F,), 0.25, {"end_via": (171.4, 56.6, 173.7, 57.95), "via": (0.5, 0.25)}),
    ("VBUS_DS", ("J502", "B4"), (170.0, 57.4), (F,), 0.25, {"end_via": (168.8, 56.6, 171.1, 57.95), "via": (0.5, 0.25)}),
]

# Plain straight links: USB-C receptacle A-row VBUS pins to the B-row VBUS pins right behind them.
LINKS = [
    ("VBUS_PDIN", ("J101", "A4"), ("J101", "B9"), 0.25),
    ("VBUS_PDIN", ("J101", "A9"), ("J101", "B4"), 0.25),
    ("VBUS_LAPTOP", ("J501", "A4"), ("J501", "B9"), 0.25),
    ("VBUS_LAPTOP", ("J501", "A9"), ("J501", "B4"), 0.25),
]
# Vias straight through overlapping top/bottom pads (filled via-in-pad): CSA filter cap under its U201 pin.
DIRECT_VIAS = [
    ("BB_CSA", (114.67, 91.7), 0.35, 0.15, {("U201", "37"), ("C221", "1")}),
    ("BB_HB2", (116.25, 86.2), 0.35, 0.15, set()),     # next to the inner end of U201.26, over C220 pad 1
    ("+5V", (170.85, 78.6), 0.6, 0.3, {("R415", "1"), ("C421", "1")}),      # R415 pad 1 / C421 pad 1 -> L4 +5V
]
# Pad -> short stub -> via (J502 VBUS pins are all SMD).
STUBS = [
]


_END_VIAS = []


def _pt(r, spec):
    if spec[0] == "@via":
        return _END_VIAS[spec[1]]
    if len(spec) == 2 and isinstance(spec[0], str):
        return r.pad(*spec)
    if len(spec) == 4:
        x, y = r.pad(spec[0], spec[1])
        return (x + spec[2], y + spec[3])
    return spec


def _side(r, spec):
    if spec[0] == "@via":
        return None
    if isinstance(spec[0], str):
        return "B.Cu" if r.fps[spec[0]].IsFlipped() else "F.Cu"
    return None


# Scripts that run after this one and whose copper is final: everything here keeps clear of it.
HS_SCRIPTS = ["c_hs_usbc", "d_hs_hub", "e_hs_eth_sd"]


def route(board, r):
    del _END_VIAS[:]
    L.ViaPlacer.ghost_tracks, L.ViaPlacer.ghost_vias = L.load_ghosts(board, type(r), HS_SCRIPTS)
    print("b_power: keeping clear of %d HS tracks / %d HS vias" % (len(L.ViaPlacer.ghost_tracks),
                                                                  len(L.ViaPlacer.ghost_vias)))
    for name, net, layer, poly, prio in POURS:
        L.add_zone(board, r, name, net, layer, poly, priority=prio, clearance=0.3, min_width=0.25, full=True)
    ap = __import__("a_planes")
    kos = [(poly, frozenset(["In2.Cu", "In3.Cu"]), n != "KO_5V_SW_Q302") for n, poly in ap.SW_KO]
    kos += [(poly, frozenset(["In2.Cu"]), True) for n, poly in ap.L3_KO]
    vp_tight = L.ViaPlacer(board, keepouts=list(kos))   # for the few deliberate vias inside a pin field
    # no power via inside the pin field of an IC (either side): it would block the IC's own escape routing
    for fp in board.GetFootprints():
        if not fp.GetReference().startswith("U") or len(fp.Pads()) < 8 or fp.GetReference() == "U1101":
            continue
        bxs = [p.GetBoundingBox() for p in fp.Pads()]
        kos.append((rect(min(L.MM(q.GetLeft()) for q in bxs), min(L.MM(q.GetTop()) for q in bxs),
                         max(L.MM(q.GetRight()) for q in bxs), max(L.MM(q.GetBottom()) for q in bxs)),
                    frozenset(), True))     # blocks vias only
    vp = L.ViaPlacer(board, keepouts=kos)
    # via fields marked early (where space is contested) go first, the local routes then find their way around
    # them; the remaining fields are placed after the routes
    report = []

    def fields(early):
        for v in VIAS:
            net, area, n, pitch, size, drill = v[:6]
            if (len(v) > 6 and v[6]) != early:
                continue
            k = vp.fill(r, net, area, pitch=pitch, size=size, drill=drill, maxn=n, allow_pads=EP_OK)
            report.append((net, area, n, k))
    fields(True)
    for net, a, b, w in LINKS:
        r.track(net, [r.pad(*a), r.pad(*b)], "F.Cu", w)
    vp.refresh()
    gr = L.GridRouter(board, vp)
    failed = []
    # keep local routes out of the gap between IC pin rows and exposed pads
    body = []
    for fp in board.GetFootprints():
        if not fp.GetReference().startswith("U") or len(fp.Pads()) < 6:
            continue
        ep = max(fp.Pads(), key=lambda p: p.GetSize().x * p.GetSize().y)
        bb = ep.GetBoundingBox()
        ex0, ey0, ex1, ey1 = L.MM(bb.GetLeft()), L.MM(bb.GetTop()), L.MM(bb.GetRight()), L.MM(bb.GetBottom())
        if (ex1 - ex0) * (ey1 - ey0) < 1.5 or ep.GetDrillSizeX() != 0:
            continue
        # block the package interior: from the EP out to the inner ends of the pin rows
        bx0, by0, bx1, by1 = ex0 - 0.45, ey0 - 0.45, ex1 + 0.45, ey1 + 0.45
        for p in fp.Pads():
            if p.GetNumber() == ep.GetNumber():
                continue
            pb_ = p.GetBoundingBox()
            px0, py0, px1, py1 = L.MM(pb_.GetLeft()), L.MM(pb_.GetTop()), L.MM(pb_.GetRight()), L.MM(pb_.GetBottom())
            cx, cy = (px0 + px1) / 2, (py0 + py1) / 2
            if ey0 <= cy <= ey1 or ex0 <= cx <= ex1:
                if cx < ex0:
                    bx0 = min(bx0, px1 + 0.05)
                elif cx > ex1:
                    bx1 = max(bx1, px0 - 0.05)
                elif cy < ey0:
                    by0 = min(by0, py1 + 0.05)
                elif cy > ey1:
                    by1 = max(by1, py0 - 0.05)
        body.append(rect(bx0, by0, bx1, by1))
    for net, xy, size, drill, allow in DIRECT_VIAS:
        vp_tight.refresh()
        if vp_tight.place(r, net, xy[0], xy[1], size, drill, allow_pads=allow, clr=0.15, hvclr=0.15):
            _END_VIAS.append(xy)
        else:
            _END_VIAS.append(None)
            failed.append((net, "direct via", xy))
        vp.refresh()
    for rt in ROUTES:
        net, a, b, layers, w = rt[:5]
        opt = rt[5] if len(rt) > 5 else {}
        la, lb = _side(r, a), _side(r, b)
        if la not in layers:
            la = None
        if lb not in layers:
            lb = None
        if any(s[0] == "@via" and (s[1] >= len(_END_VIAS) or _END_VIAS[s[1]] is None) for s in (a, b)):
            failed.append((net, a, b, "missing via"))
            continue
        pa, pb = _pt(r, a), _pt(r, b)
        if opt.get("end_via"):
            # nearest legal via spot to `b` inside the given area (where the target plane is)
            ax0, ay0, ax1, ay1 = opt["end_via"]
            cands = sorted(((x / 10.0 - pb[0]) ** 2 + (y / 10.0 - pb[1]) ** 2, x / 10.0, y / 10.0)
                           for x in range(int(ax0 * 10), int(ax1 * 10) + 1)
                           for y in range(int(ay0 * 10), int(ay1 * 10) + 1))
            evs = opt.get("via", (0.5, 0.25))
            hvc = 0.15 if opt.get("tight") else 0.3
            pl = vp_tight if opt.get("tight") else vp
            pl.refresh()
            spot = next(((x, y) for _d, x, y in cands if pl.ok(net, x, y, evs[0], evs[1], clr=0.15, hvclr=hvc)),
                        None)
            if not spot:
                failed.append((net, a, b, "no via spot"))
                continue
            pb = spot
        lb2 = lb or (layers[0] if not isinstance(b[0], str) else None)
        kel = w <= 0.15     # Kelvin / sense: keep off other same-net copper (pads, vias, pours) except at the ends
        kw = dict(layers=list(layers), width=w, clr=0.15, via=opt.get("via", (0.45, 0.25)),
                  window=opt.get("window", 3.0), strict=kel,
                  extra_block=([] if opt.get("no_body") else body) + opt.get("block", []),
                  soft_block=[(p[3], {p[2]}) for p in POURS
                              if (kel or L.short(p[1]) != L.short(net)) and not opt.get("cross_pours")])
        ok = (gr.route(r, net, pa, pb, la=la, lb=lb2, **kw) or gr.route(r, net, pb, pa, la=lb2, lb=la, **kw))
        if not ok:
            gr.step = 0.05
            ok = gr.route(r, net, pa, pb, la=la, lb=lb2, **kw)
            gr.step = 0.1
        if not ok:
            failed.append((net, a, b))
        elif opt.get("end_via"):
            evs = opt.get("via", (0.5, 0.25))
            pl.place(r, net, pb[0], pb[1], evs[0], evs[1], clr=0.15, hvclr=0.15 if opt.get("tight") else 0.3)
            vp.refresh()
            _END_VIAS.append(pb)
    for net, a, xy, w in STUBS:
        if vp.ok(net, xy[0], xy[1], 0.5, 0.25):
            if a:
                r.track(net, [r.pad(*a), xy], "F.Cu", w)
            vp.place(r, net, xy[0], xy[1], 0.5, 0.25)
        else:
            failed.append((net, a, xy))
    vp.refresh()
    fields(False)
    L.ViaPlacer.ghost_tracks, L.ViaPlacer.ghost_vias = [], []
    for net, area, n, k in report:
        if k < n:
            print("b_power: %-12s %s placed %d/%d vias" % (net, area, k, n))
    for f in failed:
        print("b_power: FAILED route", f)
