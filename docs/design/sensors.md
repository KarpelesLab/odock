# odock-10 — Sensors sheet (`sensors.kicad_sch`, refs 1200+)

Source: `hardware/odock-10/sheets/sensors.py` (generated, netlist-verified). The sheet holds the prototype's thermal
instrumentation (odock-10.md "Thermal & power instrumentation"). Power monitors (INA226/INA237/INA180) live on the
power and usb_a sheets.

## Contents
- **8 × TMP1075DSGR** (C2870250, WSON-8 2×2 mm, ±1 °C max from −40 to 110 °C, 38k stock) on I2C_SYS.
  - Each has 100 nF at V+ and its EP soldered to GND.
  - ALERT (open drain) is wire-ORed onto `TEMP_ALERT_N`.
- **2 × NCP18XH103F03RB** NTC (C13564, 10k 1 %, B25/50 = 3380 K, 0603) from `NTC_ADC0/1` to GND.
- **8 × thermocouple pads** (TestPoint 2 × 2 mm copper, `in_bom = no`), tied to GND at each hot spot.

Owned by the **mcu sheet**, so not added here:
- the I2C_SYS pull-ups (2.2k);
- the single `TEMP_ALERT_N` pull-up (10k R1016, read by TCA9534 P2);
- the NTC bias (10k 1 % from ADC_AVDD) and the 100 nF ADC filter caps.

## Sensor map (layout must follow this)

| Ref | Addr | A2 A1 A0 | Tag | Location |
|---|---|---|---|---|
| U1201 | 0x48 | 0 0 0 | BUCK-BOOST | LM51770 power stage (power_laptop), between the FET bridge and the XAL1010 inductor |
| U1202 | 0x49 | 0 0 1 | 5V BUCK | LM5148 stage (power_rails), next to Q301 high-side FET / L301 (48 V hot spot) |
| U1203 | 0x4A | 0 1 0 | HUB | USB7206C: bottom side under the hub's EP via field, or top side ≤ 3 mm from the package |
| U1204 | 0x4B | 0 1 1 | PMG1/MUX | between PMG1-S3 (BGA) and TUSB1064 |
| U1205 | 0x4C | 1 0 0 | LAPTOP-C | laptop USB-C receptacle, at the VBUS/GND pins inside the 5 A VBUS pour |
| U1206 | 0x4D | 1 0 1 | ETHERNET | between RTL8156BG and the RJ45 magjack |
| U1207 | 0x4E | 1 1 0 | LCD | under the 2.0" LCD module, centre of its footprint (top side) |
| U1208 | 0x4F | 1 1 1 | AMBIENT | front-left board corner near the SD socket, far from every heat source |

- **Address straps** go directly to GND/+3V3 (DS table 7-2: 0x48 + A2A1A0). This uses the full 0x48–0x4F block reserved in
  the I2C map.
- **Other I2C_SYS devices:** INA226 at 0x41/0x44, INA237 at 0x45, TCA9534 at 0x20, EUI-48 EEPROM at 0x50 (ethernet sheet),
  the ARA 0x0C if used, and the RTL8156BG I2C slave (address unknown) while ETH_I2C_EN is high.
- **What a sensor measures:** the WSON exposed pad is the thermal path, so each sensor reads the copper it sits on, not the
  air. Give every sensor's GND/EP pour a direct copper connection to the source's thermal pour (or a via stitch to the
  plane right under the source).

## TMP1075 configuration (firmware)
- **Power-on default** (config 00FFh): 12-bit continuous conversion (27.5 ms), comparator-mode ALERT active low,
  TLOW 75 °C / THIGH 80 °C.
  - So `TEMP_ALERT_N` already flags 80 °C on any sensor with blank firmware.
- **At boot:** program per-sensor limits. Suggested starting points, to be tuned from prototype data:
  - buck-boost and 5V buck: 100 °C;
  - hub, PMG1, Ethernet: 95 °C;
  - laptop-C: 70 °C (connector/cable limit);
  - LCD: 60 °C;
  - ambient: 55 °C.
- **Finding the source:** TMP1075 supports the SMBus Alert Response (DS §7.3.2.6). In interrupt mode (config TM = 1) each
  alerting device answers a read of the Alert Response Address **0x0C** with its own address, and arbitration clears them one
  at a time. 0x0C is free on I2C_SYS. The power-on default is comparator mode, which keeps the blank-firmware 80 °C flag, so
  firmware switches to TM = 1 after boot if it wants ARA. The simple alternative is to read all 8 temperature registers
  (~2 ms at 400 kHz).
- **Derating** is a firmware policy (renegotiate the laptop contract, turn off charge-mode ports, power down 2.5GbE through
  `ETH_RESET_N`). The hardware safety backstops do not depend on it.

## NTC hot spots
- **TH1201 → `NTC_ADC0`:** buck-boost inductor (XAL1010), on the inductor's pad copper.
- **TH1202 → `NTC_ADC1`:** LM5148 high-side FET Q301, on its drain/SW-side copper as close as clearance allows.
- **Circuit:** ratiometric divider. 10k bias from ADC_AVDD sits on the mcu sheet, the NTC goes to GND here.
  - V/AVDD = R_NTC / (10k + R_NTC):

    | Temperature | R_NTC | V/AVDD |
    |---|---|---|
    | 25 °C | 10k | 0.50 |
    | 85 °C | ≈ 1.45k | 0.127 |
    | 100 °C | ≈ 0.97k | 0.088 |
    | 125 °C | ≈ 0.53k | 0.050 |

  - Resolution at 100 °C ≈ 0.6 LSB/°C with the 12-bit ADC. That is adequate for a derating threshold.
- **Why NTCs here:** these two spots are too small or noisy for a WSON (switch-node copper). The NTC's GND end must
  return to the local power ground plane.
- **Routing:** `NTC_ADCx` is a high-impedance analog net. Route it away from SW nodes, guarded by GND. The 100 nF at the ADC
  pin (mcu sheet) does the filtering.

## Thermocouple pads
TP1201–TP1208 are 2 × 2 mm bare copper (solder-mask opened), connected to GND, ≤ 3 mm from the part:

| Ref | Label | Spot |
|---|---|---|
| TP1201 | TC_BB_FET | hottest LM51770 bridge FET |
| TP1202 | TC_BB_L | buck-boost inductor XAL1010 |
| TP1203 | TC_5V_FET | LM5148 high-side FET Q301 |
| TP1204 | TC_5V_L | LM5148 inductor L301 |
| TP1205 | TC_HUB | USB7206C |
| TP1206 | TC_LAPTOP_C | laptop USB-C VBUS pins |
| TP1207 | TC_ETH | RTL8156BG |
| TP1208 | TC_ORFET | LM74700 OR-FET Q303 / sink-switch area |

Use them for bonding K-type beads (Kapton tape or thermal epoxy), or as matte reference spots for IR-camera emissivity
calibration. They are GND-tied, so they also work as scope ground points. `tools/bom_check.py` skips them (TP prefix,
not in BOM).

## Global nets used
`+3V3`, `GND`, `I2C_SYS_SCL`, `I2C_SYS_SDA`, `TEMP_ALERT_N`, `NTC_ADC0`, `NTC_ADC1`. No new nets are needed.

## Part list

| Ref | Part | LCSC | JLC stock | Type |
|---|---|---|---|---|
| U1201–U1208 | TI TMP1075DSGR (WSON-8) | C2870250 | 38 492 | ext |
| TH1201–TH1202 | Murata NCP18XH103F03RB 10k NTC 0603 | C13564 | 258 064 | ext |
| C1201–C1208 | 100 nF 0402 | C1525 | — | basic |
| TP1201–TP1208 | TestPoint_Pad_2.0x2.0mm (copper only) | — | — | not in BOM |

## Open issues
1. Sensor placement in this table assumes the board-layout.md floor plan. Revisit if the power zone moves.
2. I2C_SYS load: 8 TMP1075 + 3 INA + TCA9534 + EEPROM + traces is about 150 pF (mcu note). That is fine with 2.2k at
   400 kHz, but the sensors are spread over the whole board, so route I2C_SYS as a daisy chain away from SW nodes.
3. U1205 (laptop-C) sits inside a 5 A pour that can reach ~28 V VBUS. Only its GND/EP touches copper, but keep the VBUS
   clearance class (`HV`/`PWR_HC`) to the sensor's pads.
