"""odock-10 — PD controller sheet: Infineon PMG1-S3 dual-port (CYPM1321-97BZXI, BGA-97).
Port 0 = laptop port (DRP: EPR source up to 28 V / 5 A through the power_laptop path, sink in bus-powered mode;
data UFP; DP Alt Mode UFP_D; drives TUSB1064). Port 1 = downstream USB-C (5 V / 3 A source through an
AO4842 back-to-back NFET pair on the PMG1 gate driver, 5 mOhm CSA shunt; data DFP; DP Alt Mode DFP_D;
drives TUSB1046). Host interface I2C_PD (0x42) + INT_N to the RP2350, SWD through cuttable solder jumpers.
Design notes, pin table and firmware contract: docs/design/pd_pmg1.md"""
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "tools", "schgen"))
from schgen import Sheet

# --- LCSC part numbers ---------------------------------------------------------------------------
PMG1_LCSC = "C20190828"          # CYPM1321-97BZXIT (dead-battery Rd), 20 in stock; symbol/footprint of C6580811
R_1K, R_4K7, R_10K, R_100K = "C11702", "C25900", "C25744", "C25741"     # 0402 basic
R_5M_1206 = "C316225"            # TA-I RLM12FTCMR005, 5 mOhm 1 % 1 W 1206 (port-1 CSA shunt)
C_100N, C_1U, C_4U7_0603, C_390P = "C1525", "C52923", "C19666", "C282239"   # 0402 X7R/X5R basic; 390 pF C0G
C_100N_50V = "C14663"            # 0603 50 V basic
C_10U_25V = "C15850"             # 0805 25 V basic
FET_DUAL = ("Transistor_FET:AO4842", "C427016")   # 30 V dual NFET, 21 mOhm @10 V, VGS +-20 V, SO-8
FET_SMALL = ("Transistor_FET:AO3400A", "C20917")
PMG1_SYM = "odock:CYPM1322-97BZXI_C6580811"      # same ball-out as CYPM1321 (pins C15/M6 renamed per datasheet)

TP_FP = "TestPoint:TestPoint_Pad_D1.0mm"
JP_FP = "Jumper:SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm"


def build(D):
    s = Sheet(D, "pd_pmg1.kicad_sch", "odock-10 — PD controller PMG1-S3 (laptop + downstream USB-C)",
              ref_base=400, paper="A2")

    # =============================================================================================
    # 0. Overview
    # =============================================================================================
    s.note("PMG1-S3 DUAL-PORT PD CONTROLLER  (CYPM1321-97BZXI = CYPM1322 + dead-battery Rd on CC)\n"
           "Port 0 = laptop USB-C: DRP. Source 5-28 V EPR 140 W via power_laptop (VBB_EN, VBB_VSEL2..0, VBB_PG,\n"
           "  LAPTOP_SRC_EN); sink in bus-powered mode (LAPTOP_SNK_EN). Data UFP, DP Alt Mode UFP_D -> TUSB1064.\n"
           "  The port-0 power path is EXTERNAL (LM74800/LM74502 on power_laptop): PMG1 gate-driver pair 0 is unused,\n"
           "  firmware switches the path with GPIOs. CSA 0 senses the INA226 shunt (VBUS_LSW -> VBUS_LAPTOP, 5 mOhm).\n"
           "Port 1 = downstream USB-C: source 5 V / 3 A from +5V through 5 mOhm (CSA 1) and AO4842 back-to-back on\n"
           "  gate-driver pair 1. Data DFP, DP Alt Mode DFP_D -> TUSB1046. Forced-5V mode = firmware only.\n"
           "VBUS_C_P0 / CSP/CSN / NGDO are 34 V abs max: VBUS_LAPTOP is capped at 30.8 V (OVP latch) / 32.6 V\n"
           "  (LM74800 OV) on power_laptop, so the pins connect directly as in Infineon's EPR references.\n"
           "  CC/SBU are 6 V abs max: CC/SBU over-voltage protection (TPD4S480) belongs next to the connectors\n"
           "  (usbc_muxes) - see docs/design/pd_pmg1.md.\n"
           "HPD: UP_HPD and DS_HPD are both PMG1 OUTPUTS (TUSB1064/TUSB1046 HPDIN are inputs). DS_HPD = port-1 HPD\n"
           "  (monitor Attention) from the port-1 HPD block (P7.1), also looped into the port-0 HPD receiver (P1.4)\n"
           "  so port 0 reports it to the laptop like a dock's DP sink. UP_HPD (P1.3) = HPD as reported to the laptop.",
           at=(20.32, 12.7))

    # =============================================================================================
    # 1. PMG1-S3
    # =============================================================================================
    pins = {
        # supplies
        "VSYS": "+3V3", "VDDD": "PMG1_VDDD", "VDDIO": "PMG1_VDDD", "VDDA": "PMG1_VDDD", "VCCD": "PMG1_VCCD",
        "VSS": "GND", "XRES": "PMG1_XRES",
        "VCONN_Source_P0": "+5V", "VCONN_Source_P1": "+5V",
        # port 0 (laptop)
        "VBUS_C_P0": "VBUS_LAPTOP", "CSP_P0": "VBUS_LSW", "CSN_P0": "VBUS_LAPTOP",
        "CC1_P0": "LAPTOP_CC1", "CC2_P0": "LAPTOP_CC2",
        # port 1 (downstream)
        "VBUS_C_P1": "VBUS_DS", "CSP_P1": "+5V", "CSN_P1": "DS_SRC",
        "VBUS_IN_NGDO_P1": "DS_SRC", "VBUS_IN_CTRL_P1": "DS_GIN", "VBUS_OUT_CTRL_P1": "DS_GOUT",
        "VBUS_OUT_NGDO_P1": "VBUS_DS",
        "CC1_P1": "DS_CC1", "CC2_P1": "DS_CC2",
        # debug / host
        "P1.1": "PMG1_SWCLK_L", "P1.2": "PMG1_SWDIO_L",
        "P4.0": "I2C_PD_SCL", "P4.1": "I2C_PD_SDA", "P7.6": "I2C_PD_INT_N",
        "P2.2": "PMG1_UART_TX", "P2.3": "PMG1_UART_RX",
        # HPD
        "P1.4": "DS_HPD", "P7.1": "HPD1_OUT", "P1.3": "HPD0_OUT",
        # laptop power path
        "P0.0": "LAPTOP_SNK_EN",
        "P2.0": "VBB_EN", "P2.1": "VBB_VSEL0", "P2.4": "VBB_VSEL1", "P2.5": "VBB_VSEL2", "P2.6": "LAPTOP_SRC_EN",
        "P7.0": "EXT_PWR_PRESENT", "P7.2": "PDIN_PRESENT", "P7.3": "VBB_PG", "P7.4": "LAPTOP_OVP_N",
        "P7.5": "P3V3_SNS",
        # muxes
        "P3.0": "MUX_UP_CTL0", "P3.1": "MUX_UP_CTL1", "P3.2": "MUX_UP_FLIP",
        "P3.3": "MUX_DS_CTL0", "P3.4": "MUX_DS_CTL1", "P3.7": "MUX_DS_FLIP",
    }
    nc = ["P1.0", "P1.5", "P1.6", "P2.7", "P3.5", "P3.6", "P5.0", "P5.1", "P5.2", "P5.3", "P5.4", "P5.5",
          "P0.1", "P0.2", "P0.3", "P0.4", "P0.5", "P0.6", "P0.7", "P6.0", "P6.1", "P6.2", "P6.3",
          "USBDP", "USBDM", "AUX_P_P0", "AUX_N_P0", "AUX_P_P1", "AUX_N_P1",
          "VBUS_IN_NGDO_P0", "VBUS_OUT_NGDO_P0", "VBUS_IN_CTRL_P0", "VBUS_OUT_CTRL_P0"]
    s.part(PMG1_SYM, "U", "CYPM1321-97BZXI", at=(452.12, 233.68), pins=pins, nc=nc, lcsc=PMG1_LCSC,
           mpn="CYPM1321-97BZXIT",
           datasheet="https://www.infineon.com/assets/row/public/documents/24/49/infineon-cypm13xx-ez-pd-pmg1-s3-power-delivery-mcu-gen1-datasheet-en.pdf",
           desc="EZ-PD PMG1-S3 dual-port USB PD MCU, 28 V EPR, dead-battery Rd, BGA-97 6x6 0.5 mm")

    # =============================================================================================
    # 2. Supplies / decoupling
    # =============================================================================================
    s.note("2. PMG1 SUPPLY (dead-deck capable)\n"
           "VSYS = +3V3 (deck powered): VDDD = VSYS - 0.1 V. Dead deck (no +3V3): the internal 28 V VBUS regulator\n"
           "  powers VDDD (3.0-3.65 V, 60 mA max) from VBUS_C_P0 (laptop) or VBUS_C_P1. VSYS has priority.\n"
           "VDDIO and VDDA tied to VDDD (PMG1_VDDD) so EVERY GPIO works in a dead-deck cold start\n"
           "  (LAPTOP_SNK_EN is additionally on a VDDD-domain pin, P0.0). Cost: 10 mA total GPIO budget\n"
           "  (SID.GPIO.DC#11a) - all loads here are CMOS inputs / >= 47k pull-downs / I2C open-drain (< 3 mA).\n"
           "CYPM1321 presents dead-battery Rd on CC while unpowered -> the laptop applies vSafe5V, PMG1 boots,\n"
           "  sees EXT_PWR_PRESENT low and drives LAPTOP_SNK_EN -> +5V -> +3V3. (CYPM1322 has NO dead-battery Rd.)\n"
           "Decoupling per datasheet Table 5 / Fig. 12: VDDD 4.7 uF + 100 nF, VCCD 100 nF (80-120 nF, no load),\n"
           "  VSYS / VDDIO / VDDA 1 uF + 100 nF per ball, VCONN_Source 1 uF per port.\n"
           "VCONN_Source_P0/P1 = +5V (4.85-5.5 V): VCONN for e-marked 5 A EPR cables when sourcing.",
           at=(20.32, 78.74))
    x, y = 25.4, 134.62
    dec = [("1u", "+3V3", C_1U, "VSYS"), ("100n", "+3V3", C_100N, "VSYS"),
           ("4.7u", "PMG1_VDDD", C_4U7_0603, "VDDD"), ("100n", "PMG1_VDDD", C_100N, "VDDD"),
           ("1u", "PMG1_VDDD", C_1U, "VDDIO"), ("100n", "PMG1_VDDD", C_100N, "VDDIO B8"),
           ("100n", "PMG1_VDDD", C_100N, "VDDIO H12"),
           ("1u", "PMG1_VDDD", C_1U, "VDDA"), ("100n", "PMG1_VDDD", C_100N, "VDDA D6"),
           ("100n", "PMG1_VDDD", C_100N, "VDDA F6"),
           ("100n", "PMG1_VCCD", C_100N, "VCCD (80-120 nF)"),
           ("1u", "+5V", C_1U, "VCONN_Source_P0"), ("1u", "+5V", C_1U, "VCONN_Source_P1")]
    for i, (v, net, lc, d) in enumerate(dec):
        size = "0603" if v == "4.7u" else "0402"
        s.c(v, net, "GND", size=size, at=(x + (i % 7) * 10.16, y + (i // 7) * 20.32), lcsc=lc, desc=f"Decoupling {d}")
    s.c("100n/50V", "VBUS_LAPTOP", "GND", size="0603", at=(x + 71.12, y), lcsc=C_100N_50V, desc="VBUS_C_P0 local")
    s.c("100n/50V", "VBUS_DS", "GND", size="0603", at=(x + 71.12, y + 20.32), lcsc=C_100N_50V, desc="VBUS_C_P1 local")

    # =============================================================================================
    # 3. CC
    # =============================================================================================
    s.note("3. CC LINES  390 pF to GND on each CC (Infineon reference; within cReceiver 200-600 pF).\n"
           "CC pins are 6 V abs max: LAPTOP_CC1/2 must arrive through CC OVP (TPD4S480) on usbc_muxes.",
           at=(20.32, 180.34))
    for i, net in enumerate(["LAPTOP_CC1", "LAPTOP_CC2", "DS_CC1", "DS_CC2"]):
        s.c("390p", net, "GND", at=(25.4 + i * 10.16, 198.12), lcsc=C_390P, desc="CC capacitor, C0G 50 V")

    # =============================================================================================
    # 4. Reset / SWD / UART debug
    # =============================================================================================
    s.note("4. RESET + SWD (RP2350 = SWD programmer; default-closed solder jumpers, cut to isolate)\n"
           "XRES: 4.7k pull-up to VDDD + 100 nF (Infineon Fig. 12). The RP2350 side goes through a pass FET\n"
           "  (gate = +3V3, BSS138-style): with +3V3 absent (dead-deck boot) the unpowered RP2350 pin cannot clamp\n"
           "  XRES low and hold the PMG1 in reset. With +3V3 present, RP2350 driving PMG1_XRES_N low resets PMG1\n"
           "  (non-inverting; 10k pull-up to +3V3 on the RP2350 side keeps the FET off when the pin is Hi-Z).\n"
           "SWD: P1.1 = SWCLK, P1.2 = SWDIO (primary SWD pins), direct through JP. Only PMG1's own SWD pull-ups\n"
           "  (~5.6k) can back-feed an unpowered RP2350 (< 0.6 mA) - harmless.\n"
           "UART debug (SCB5, as in Infineon's dock example): P2.2 TX / P2.3 RX on test pads.",
           at=(20.32, 220.98))
    x, y = 25.4, 266.7
    s.r("4.7k", "PMG1_XRES", "PMG1_VDDD", at=(x, y), lcsc=R_4K7, desc="XRES pull-up")
    s.c("100n", "PMG1_XRES", "GND", at=(x + 10.16, y), lcsc=C_100N, desc="XRES filter")
    s.part(FET_SMALL[0], "Q", "AO3400A", at=(x + 27.94, y), lcsc=FET_SMALL[1],
           pins={"G": "+3V3", "S": "XRES_RP", "D": "PMG1_XRES"},
           desc="XRES isolation pass FET (off when +3V3 absent)")
    s.r("10k", "XRES_RP", "+3V3", at=(x + 43.18, y), lcsc=R_10K, desc="RP2350-side XRES pull-up")
    jp = []
    for i, (a, b) in enumerate([("PMG1_XRES_N", "XRES_RP"), ("PMG1_SWDIO", "PMG1_SWDIO_L"),
                                ("PMG1_SWCLK", "PMG1_SWCLK_L")]):
        jp.append(s.part("Jumper:SolderJumper_2_Bridged", "JP", "SWD_CUT", JP_FP, at=(x + 60.96 + i * 27.94, y),
                         pins={"A": a, "B": b}, in_bom=False, desc="Default-closed solder jumper: cut to isolate PMG1 from RP2350"))
    y2 = y + 22.86
    for i, net in enumerate(["PMG1_SWDIO_L", "PMG1_SWCLK_L", "PMG1_XRES", "PMG1_UART_TX", "PMG1_UART_RX", "GND"]):
        s.part("Connector:TestPoint", "TP", net.replace("PMG1_", ""), TP_FP, at=(x + i * 12.7, y2), pins={"1": net})

    # =============================================================================================
    # 5. Host interface + status inputs
    # =============================================================================================
    s.note("5. HOST INTERFACE (RP2350)  I2C_PD on SCB0 (P4.0 SCL / P4.1 SDA: the only fail-safe I2C pins,\n"
           "  same SCB as the dock example's HPI). PMG1 target address 0x42 (firmware-defined, CCGx HPI alternate\n"
           "  address; TPS26750 = 0x21 on the same bus). Bus pull-ups on the MCU sheet (+3V3).\n"
           "I2C_PD_INT_N: P7.6 (B9), open-drain, 10k pull-up to PMG1_VDDD here (never above VDDIO). Not P5.5: ports 2/3/5\n"
           "  carry analog functions and must not see an external voltage above VDDIO or before all supplies are up (DS 2.6.3);\n"
           "  a +3V3 pull-up sits ~0.1 V above VDDIO (= VDDD = VSYS - 0.1 V). VDDD-referenced high (3.0-3.65 V) is > RP2350 VIH.\n"
           "  Dead deck: VDDD up, RP2350 unpowered -> <= 0.35 mA into the RP2350 pad through 10k; PMG1 firmware leaves INT_N\n"
           "  released (high) until P3V3_SNS is high, so the RP2350 never sees a spurious edge at boot.\n"
           "P3V3_SNS (P7.5): +3V3 present (10k/100k). Firmware keeps every output towards +3V3-powered chips\n"
           "  (mux CTL/FLIP, UP_HPD, DS_HPD, LAPTOP_SRC_EN) low until P3V3_SNS is high (no back-powering).\n"
           "EXT_PWR_PRESENT 100k pull-down: its 74LVC1G32 driver is unpowered (Ioff) in a dead deck; without it the\n"
           "  net floats - here AND at the power_laptop sink-switch FET gate.",
           at=(20.32, 302.26))
    x, y = 25.4, 345.44
    s.r("10k", "I2C_PD_INT_N", "PMG1_VDDD", at=(x, y), lcsc=R_10K, desc="INT_N pull-up to VDDIO rail (P7.6)")
    s.r("10k", "+3V3", "P3V3_SNS", at=(x + 10.16, y), lcsc=R_10K, desc="+3V3 sense")
    s.r("100k", "P3V3_SNS", "GND", at=(x + 20.32, y), lcsc=R_100K, desc="+3V3 sense")
    s.r("100k", "EXT_PWR_PRESENT", "GND", at=(x + 30.48, y), lcsc=R_100K,
        desc="Defined low in a dead deck (driver unpowered)")

    # =============================================================================================
    # 6. Muxes + HPD
    # =============================================================================================
    s.note("6. MUX CONTROL (TUSB1064 / TUSB1046 in GPIO mode, I2C_EN = 0)\n"
           "Port 0 -> TUSB1064: CTL0 = USB3 on, CTL1 = DP on, FLIP = CC orientation (P3.0/P3.1/P3.2).\n"
           "Port 1 -> TUSB1046: CTL0, CTL1, FLIP (P3.3/P3.4/P3.7). 100k pull-downs hold CTL0/CTL1/FLIP low while PMG1 is\n"
           "  in reset/unpowered. NOTE: both muxes still enter USB3 mode (no flip) at VCC power-up regardless of CTL0 and\n"
           "  leave it only on a CTL0 L-H-L pulse (TUSB1064 8.4.1, TUSB1046 7.4.1): firmware pulses CTL0 after P3V3_SNS\n"
           "  goes high and on every detach. DP lanes stay off (CTL1 low; TUSB1064 HPDIN 100k PD on usbc_muxes).\n"
           "HPD: HPD1_OUT (P7.1, port-1 HPD block, output: follows the monitor's HPD_State/IRQ_HPD Attention) -> 1k\n"
           "  -> DS_HPD -> TUSB1046 HPDIN, and -> P1.4 (port-0 HPD block in receive mode, as a dock's DP sink HPD)\n"
           "  -> port 0 sends Attention/Status to the laptop. HPD0_OUT (P1.3, GPIO) -> 1k -> UP_HPD -> TUSB1064\n"
           "  HPDIN (DP lanes enabled only while high). 1k: limits injection into the non-fail-safe HPDIN pins.",
           at=(203.2, 12.7))
    x, y = 208.28, 63.5
    for i, net in enumerate(["MUX_UP_CTL0", "MUX_UP_CTL1", "MUX_UP_FLIP", "MUX_DS_CTL0", "MUX_DS_CTL1", "MUX_DS_FLIP"]):
        s.r("100k", net, "GND", at=(x + i * 10.16, y), lcsc=R_100K, desc="Mux control default low")
    s.r("1k", "HPD1_OUT", "DS_HPD", at=(x + 66.04, y), lcsc=R_1K, desc="Port-1 HPD out -> DS_HPD")
    s.r("1k", "HPD0_OUT", "UP_HPD", at=(x + 76.2, y), lcsc=R_1K, desc="Port-0 HPD -> UP_HPD")

    # =============================================================================================
    # 7. Port 1 VBUS source path
    # =============================================================================================
    s.note("7. PORT 1 (DOWNSTREAM) VBUS SOURCE  +5V -> 5 mOhm (CSP_P1/CSN_P1) -> AO4842 back-to-back -> VBUS_DS\n"
           "Gate-driver pair 1 (VBUS_IN_CTRL_P1 = supply-side FET, VBUS_OUT_CTRL_P1 = connector-side FET), common\n"
           "  drain: blocks both directions when off (a phone/charger on the port cannot back-feed +5V).\n"
           "  Gate overdrive 4.5-10.5 V, OFF VGS down to -VBUS: AO4842 VGS +-20 V, 30 V, 21 mOhm -> 3 A: 0.38 W.\n"
           "CSA 1: OCP/SCP/RCP on the 5 mOhm shunt (Kelvin-route CSP/CSN). Discharge: integrated on VBUS_C_P1.\n"
           "Forced 5 V mode: firmware turns the path on without Rd (user-initiated, auto-off) - no extra hardware.\n"
           "VBUS_DS: 10 uF + 100 nF here; TVS at the connector (usbc_muxes).",
           at=(203.2, 88.9))
    x, y = 208.28, 139.7
    s.c("10u", "+5V", "GND", size="0805", at=(x, y), lcsc=C_10U_25V, desc="Port-1 source input bulk")
    s.r("5m", "+5V", "DS_SRC", size="1206", at=(x + 12.7, y), lcsc=R_5M_1206, mpn="RLM12FTCMR005",
        desc="Port-1 VBUS current sense 5 mOhm 1 % 1206 (PMG1 CSA)")
    s.part(FET_DUAL[0], "Q", "AO4842", at=(x + 30.48, y + 25.4), lcsc=FET_DUAL[1],
           pins={"S1": "DS_SRC", "G1": "DS_GIN", "D1": "DS_FETD", "S2": "VBUS_DS", "G2": "DS_GOUT", "D2": "DS_FETD"},
           desc="Dual 30 V NFET, back-to-back port-1 VBUS switch")
    s.c("10u", "VBUS_DS", "GND", size="0805", at=(x + 132.08, y), lcsc=C_10U_25V, desc="VBUS_DS bulk")
    s.flag("VBUS_DS", at=(x + 147.32, y))

    s.build()
    return s


def _no_bom(s, refs):
    """Solder jumpers are copper only: mark them in_bom no (schgen writes in_bom yes for every symbol)."""
    path = os.path.join(s.dir, s.filename)
    t = open(path).read()
    blocks = t.split("\n\t(symbol\n")
    for i, b in enumerate(blocks[1:], 1):
        m = re.search(r'\(property "Reference" "([^"]+)"', b)
        if m and m.group(1) in refs:
            blocks[i] = b.replace("(in_bom yes)", "(in_bom no)", 1)
    open(path, "w").write("\n\t(symbol\n".join(blocks))
