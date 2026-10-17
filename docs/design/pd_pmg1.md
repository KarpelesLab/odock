# pd_pmg1 — PMG1-S3 dual-port PD controller (odock-10)

Sheet: `hardware/odock-10/pd_pmg1.kicad_sch`, generated from `hardware/odock-10/sheets/pd_pmg1.py` (ref base 400).
Datasheet: Infineon 002-31288 Rev. *K (2025-05-23), "EZ-PD PMG1-S3 Power Delivery MCU Gen1". Pin functions and
the SCB0 / SCB5 / HPD pin choices follow Infineon's `mtb-example-pmg1s3-usbc-dock` (`templates/TARGET_PMG1S3DUAL/config/design.modus`).

## Part choice: CYPM1321-97BZXI instead of CYPM1322
In datasheet Table 50 (ordering information), **CYPM1322 lists "Dead battery terminations: No"**, while **CYPM1321
has "RP, RD, RD-DB"**. The ball-out is the same. A dead deck has to show Rd to the laptop while it is unpowered,
or the laptop never turns on VBUS and the deck cannot start bus-powered. So the sheet uses **CYPM1321-97BZXIT, LCSC
C20190828, 20 in stock (≥ 5 OK), $6.93**. EasyEDA has no model for C20190828, so the symbol and footprint come from
the identical-package CYPM1322 (C6580811). Two pin names in the imported symbol were wrong and are fixed in
`hardware/lib`: ball C15 is CSP_P1 (it was imported as a second CSN_P1), and M6 is AUX_N_P1 (imported as AUX_P_P1).
Fallback: CYPM1322 (C6580811, 50 in stock). It only works if the CC OVP part on usbc_muxes (TPD4S480) supplies the
dead-battery Rd.

## Block summary
```
 VBUS_LAPTOP ─────────────── VBUS_C_P0 (28 V regulator, discharge, UV/OV)      VSYS ◄── +3V3
 VBUS_LSW ─ 5 mΩ (power_laptop INA226 shunt) ─ VBUS_LAPTOP  ──► CSP_P0 / CSN_P0 (OCP/SCP/RCP)
 LAPTOP_CC1/2 ─ 390 pF ───── CC1_P0 / CC2_P0 (DRP, Rd-DB)     VDDD ─┬─ VDDIO, VDDA  (PMG1_VDDD)
 +5V ── 5 mΩ ── DS_SRC ─ AO4842 (back-to-back) ─ VBUS_DS             └─ XRES 4.7k pull-up
          CSP_P1  CSN_P1/VBUS_IN_NGDO_P1   G: VBUS_IN_CTRL_P1 / VBUS_OUT_CTRL_P1, VBUS_OUT_NGDO_P1 = VBUS_C_P1
 DS_CC1/2 ─ 390 pF ───────── CC1_P1 / CC2_P1 (source)          VCONN_Source_P0/P1 ◄── +5V
```

## GPIO / pin table
| Ball | Pin | Net | Dir | Function |
|---|---|---|---|---|
| P3 | P1.1 | PMG1_SWCLK_L → JP → PMG1_SWCLK | in | SWD clock (primary SWD) |
| R3 | P1.2 | PMG1_SWDIO_L → JP → PMG1_SWDIO | io | SWD data |
| E14 | XRES | PMG1_XRES ← pass FET ← JP ← PMG1_XRES_N | in | reset (4.7k to VDDD, 100 nF) |
| E15 | P4.0 | I2C_PD_SCL | io | SCB0 I2C target (fail-safe pin; dock: I2C_HPIM) |
| D12 | P4.1 | I2C_PD_SDA | io | SCB0 I2C target |
| B9 | P7.6 | I2C_PD_INT_N | out OD | interrupt to RP2350, 10k to **PMG1_VDDD** (moved from P5.5, review pd_mux #2: ports 2/3/5 carry analog functions and must not see an external voltage above VDDIO) |
| R8 | P0.0 | LAPTOP_SNK_EN | out | bus-power sink switch enable (**VDDD-domain pin**) |
| A2 | P2.0 | VBB_EN | out | LM51770 enable (also resets OVP latch) |
| B2 | P2.1 | VBB_VSEL0 | out | buck-boost voltage select bit 0 |
| A7 | P2.4 | VBB_VSEL1 | out | bit 1 |
| A5 | P2.5 | VBB_VSEL2 | out | bit 2 |
| B7 | P2.6 | LAPTOP_SRC_EN | out | request laptop source switch (hardware AND on power_laptop) |
| G15 | P7.0 | EXT_PWR_PRESENT | in | external power present (100k pull-down here) |
| A14 | P7.2 | PDIN_PRESENT | in | PD-in contract active (input-power policy) |
| B13 | P7.3 | VBB_PG | in | buck-boost power good |
| B11 | P7.4 | LAPTOP_OVP_N | in | hardware OVP latch tripped (low) |
| A9 | P7.5 | P3V3_SNS | in | +3V3 present (10k/100k) |
| A1 | P3.0 | MUX_UP_CTL0 | out | TUSB1064 CTL0 (USB3), 100k pull-down |
| B3 | P3.1 | MUX_UP_CTL1 | out | TUSB1064 CTL1 (DP), 100k pull-down |
| C2 | P3.2 | MUX_UP_FLIP | out | TUSB1064 FLIP, 100k pull-down |
| B1 | P3.3 | MUX_DS_CTL0 | out | TUSB1046 CTL0, 100k pull-down |
| D4 | P3.4 | MUX_DS_CTL1 | out | TUSB1046 CTL1, 100k pull-down |
| C1 | P3.7 | MUX_DS_FLIP | out | TUSB1046 FLIP, 100k pull-down |
| G14 | P7.1 | HPD1_OUT → 1k → DS_HPD | out | port-1 HPD block (fixed function), drives TUSB1046 HPDIN |
| M10 | P1.4 | DS_HPD | in | port-0 HPD block (fixed function), receive mode |
| K4 | P1.3 | HPD0_OUT → 1k → UP_HPD | out | GPIO, drives TUSB1064 HPDIN |
| A3 | P2.2 | PMG1_UART_TX (TP) | out | SCB5 debug UART TX (dock: CYBSP_UART) |
| B5 | P2.3 | PMG1_UART_RX (TP) | in | SCB5 debug UART RX |
| — | P1.0, P1.5, P1.6, P2.7, P3.5, P3.6 (SCB4, which the dock uses for its power I2C, kept free), P5.0–P5.5, P0.1–P0.7, P6.0–P6.3 | NC | | spare |
| — | USBDP/USBDM, AUX_P/N_P0/P1 | NC | | the TUSB parts handle SBU↔AUX; the FS-USB billboard has no free hub port |
| R14/R15/P14/P15 | VBUS_IN/OUT_NGDO_P0, VBUS_IN/OUT_CTRL_P0 | NC | | gate-driver pair 0 unused: the port-0 power path is external |

Port-1 power pins: VBUS_C_P1 and VBUS_OUT_NGDO_P1 go to VBUS_DS. VBUS_IN_NGDO_P1 and CSN_P1 go to DS_SRC. CSP_P1
goes to +5V. VBUS_IN_CTRL_P1 drives the supply-side FET gate and VBUS_OUT_CTRL_P1 the connector-side FET gate.

## Power and boot
- **Supplies.** VSYS = +3V3, so VDDD = VSYS − 0.1 V. **VDDIO and VDDA are tied to VDDD** (local net `PMG1_VDDD`).
  With no +3V3, the internal 28 V regulator (60 mA max) feeds VDDD from VBUS_C_P0 or VBUS_C_P1 at 3.0–3.65 V, and
  every GPIO still works. Trade-off: with VDDIO tied to VDDD, the whole chip may source or sink only **10 mA of GPIO
  current in total** (SID.GPIO.DC#11a). The loads here are CMOS inputs, ≥ 47k pull-downs and open-drain I2C lines,
  about 3 mA worst case. Do not hang LEDs on PMG1 pins.
- **Decoupling** (Table 5 and Fig. 12):
  - VDDD: 4.7 µF + 100 nF.
  - VCCD: 100 nF only (80–120 nF, no external load).
  - VSYS, VDDIO and VDDA: 1 µF + 100 nF per ball.
  - VCONN_Source: 1 µF per port.
  - VBUS_C: 100 nF / 50 V per port.
- **VBUS ratings.** VBUS_C, CSP/CSN and NGDO are rated **34 V abs max**. VBUS_LAPTOP is clamped by the power_laptop
  OVP latch at 30.8 V and by the LM74800 OV backstop at 32.6 V, so these pins connect directly, as in Infineon's
  EPR figures. Steady state is therefore covered. The connector TVS (SMCJ28A, usbc_muxes) is the best available
  clamp but **cannot** hold these pins below 34 V during a surge: VBR is 31.1–34.4 V and VC is 45.4 V at 33 A, and no
  TVS with VRWM ≥ 28 V can do better. This is an accepted residual risk, as in Infineon's EPR references.
- **Dead-deck cold start** (no PD-in, no barrel):
  1. CYPM1321 shows Rd-DB on CC1/CC2 of the laptop port. The laptop applies vSafe5V.
  2. The PMG1 boots from VBUS_C_P0.
  3. Firmware reads EXT_PWR_PRESENT = low. It has a 100k pull-down here because its 74LVC1G32 driver is unpowered
     and Ioff.
  4. Firmware runs port 0 as a sink with Rd, optionally negotiates 5 V / 3 A, and drives **LAPTOP_SNK_EN high from
     P0.0**. That pin is in the VDDD domain, at ≥ 3.0 V. Through power_laptop's 10k / 47k divider, SNK_ON gets
     ≥ 2.46 V, well above the LM74502 EN threshold of 1.24 V.
  5. +5V comes up, then +3V3. VSYS takes over from the VBUS regulator.
  6. The RP2350 boots, and P3V3_SNS goes high.
- **Back-powering rule.** While P3V3_SNS is low, firmware keeps every output that faces a +3V3-powered chip low:
  MUX_* CTL/FLIP, UP_HPD, DS_HPD, LAPTOP_SRC_EN and the I2C target.
  - The TUSB HPDIN pins are not fail-safe. The 1k series resistors limit injection current if firmware gets this wrong.
  - XRES is isolated by a pass FET whose gate is tied to +3V3. Otherwise the unpowered RP2350 pin would clamp XRES low
    and keep the PMG1 in reset during a dead-deck boot.
- **Externally powered start.** +3V3 is present, so the PMG1 boots from VSYS. Port 0 becomes source/DRP with Rp; the
  power_laptop sequence follows.
- **Port 1 in a dead deck.** CYPM1321 also has Rd-DB on port 1, but it sits behind the TPD6S300 (VPWR = +3V3), whose
  CC FETs are open while unpowered, and RPD_G1/2 = GND gives no Rd of its own. So a DRP phone on the downstream port
  of a dead deck sees nothing and cannot back-feed VBUS_DS (the earlier claim was wrong, review pd_mux #7).
  - One real transient: on an **externally powered cold start**, the TPD6S300 closes its FETs a few ms after +3V3.
    If the PMG1 has not yet switched port 1 from Rd-DB to Rp, a charger on the downstream port can briefly apply
    vSafe5V to VBUS_DS. The AO4842 pair blocks VBUS_DS → +5V, so this is harmless. Firmware configures port 1 as an
    Rp source as early as possible in boot.

## Laptop port (port 0) power: firmware contract
- The power path is external, in power_laptop. Use PdStack application callbacks (psrc/psnk enable, set voltage)
  that drive GPIOs instead of the NGDO gate driver.
  - **Source:** set VBB_VSEL2..0 (`000` 5.1 V, `001` 9 V, `010` 15 V, `100` 20 V, `111` 28 V), then VBB_EN. Wait for
    VBB_PG, then raise LAPTOP_SRC_EN. Hardware also requires EXT_PWR_PRESENT, VBB_PG and LAPTOP_OVP_N.
  - **Sink** (bus-powered only): LAPTOP_SNK_EN. Hardware forces it off while EXT_PWR_PRESENT or SRC_ON is high.
- The PDO list is capped in PMG1 firmware by input source and power (VIN ≥ 16 V for 140 W; see power_laptop.md).
  The RP2350 can only *lower* the budget over I2C.
- OCP/SCP/RCP use CSA 0 on the shared 5 mΩ INA226 shunt (`VBUS_LSW` is global, so CSA 0 is connected across sheets).
  UV/OV come from VBUS_C_P0. The internal discharge acts on VBUS_LAPTOP only. VBB_OUT, behind the LM74800 ideal
  diode, is discharged by cycling VBB_EN (power_laptop).
- OVP latch (LAPTOP_OVP_N low): drop LAPTOP_SRC_EN and VBB_EN, report to the RP2350, and re-enable only from 5.1 V.
- Bus-powered ↔ external-power transitions: PR_Swap or a brief detach (odock-10.md open question 2).
- **Dead-battery boot** (powered from VBUS, no VSYS) must come up as a **sink with Rd**: no DRP toggling and no
  Try.SRC until the contract. TPD4S480 closes its CC FETs ≤ 3.5 ms after VPWR and drops its own DB resistors by
  9.5 ms; the PMG1 Rd must be present the moment the FETs close (TPD4S480 §6.3.3). CYPM1321 (Rd-DB) is the only
  approved part; the CYPM1322 fallback would leave an Rd gap and must be bench-tested first (review pd_mux #8).
- **Data role.** Port 0 sources power (Rp) whenever external power is present, so the Type-C default data role at
  attach is DFP, but the deck is a UFP (hub upstream). Firmware DR_Swaps to UFP after the explicit contract, before
  the laptop's DP Discover/Enter. A non-PD Type-C host gets power but **no USB data** while the deck is externally
  powered (review pd_mux #9).

## Downstream port (port 1)
- Source 5 V / 3 A. The path is +5V → 5 mΩ (C316225) → AO4842 back-to-back (common drain) → VBUS_DS, driven by
  gate-driver pair 1.
  - Gate drive is 4.5–10.5 V; AO4842 is rated VGS ±20 V.
  - Loss is about 0.38 W at 3 A.
  - CSA 1 provides OCP and SCP. The connector-side cap is 10 µF + 100 nF.
- **Rp advertisement:** 3 A only with external power. Bus-powered, +5V is the laptop's 5 V minus the sink-path drops,
  and 2 × 3 A × AO4842 RDS(on) at the minimum 4.5 V gate drive (≤ 30 mΩ, more when hot) leaves ≈ 4.85 V before the
  connector, so advertise Default/1.5 A there. The 0.38 W loss figure assumes 10 V gate drive (review pd_mux #11).
- **Forced 5 V:** the RP2350 asks over I2C. Firmware enables the path without Rd and turns it off automatically
  below about 25 mA for 5 min. No extra hardware.
- Current reading for the LCD: the PMG1 CSA/ADC VBUS current, read over I2C. This replaces the INA180 option for
  the C port.

## DisplayPort / HPD flow (TUSB datasheets: HPDIN is an *input* on both TUSB1064 and TUSB1046-DCI)
1. Laptop → port 0: Discover/Enter DP (UFP_D, pin assignment C/D). Port 0 sets MUX_UP_CTL1 (DP) and MUX_UP_CTL0
   (USB3 on, for pin D), and MUX_UP_FLIP from CC orientation.
2. Port 1 (DFP_D) enters DP mode on the monitor and sets MUX_DS_CTL0/CTL1/FLIP.
3. Monitor Attention/Status (HPD_State, IRQ_HPD) arrives at port 1. **The port-1 HPD block drives P7.1
   (HPD1_OUT → 1k → DS_HPD)** into TUSB1046 HPDIN and **into P1.4, the port-0 HPD block in receive mode**. Port 0
   turns level changes and IRQ_HPD pulses into DP Status/Attention VDMs to the laptop. This is the standard dock
   behaviour, as if DS_HPD came from a local DP sink.
4. **UP_HPD** (P1.3 → 1k → TUSB1064 HPDIN) is driven by firmware high while port 0 is in DP configuration and HPD is
   high. TUSB1064 enables its DP lanes only while HPDIN is high. Firmware should copy IRQ_HPD to UP_HPD as well, or
   simply follow DS_HPD.
5. AUX is passed through by the two TUSB parts (AC-coupled, usbc_muxes). The PMG1 SBU/AUX switches are unused.

**Mux power-up state (review pd_mux #4).** The 100k pull-downs only hold CTL0/CTL1/FLIP low while the PMG1 is in
reset. Both TUSB1064 and TUSB1046 enter **USB3 mode (no flip)** at VCC power-up regardless of CTL0, and leave it only
on a CTL0 L→H→L transition (TUSB1064 §8.4.1, TUSB1046 §7.4.1). Firmware contract: pulse CTL0 on both muxes after
P3V3_SNS goes high and on every detach. The DP lanes stay off meanwhile (CTL1 low; TUSB1064 HPDIN has an external
100k pull-down on usbc_muxes, TUSB1046 HPDIN an internal 150k).

## Host interface
- I2C_PD on SCB0 (P4.0/P4.1), the only fail-safe I2C pins. **Target address 0x42** (firmware-defined; it is the
  CCGx HPI alternate address). Other devices on the bus: TPS26750 at 0x21, so there is no clash. The TPS26750
  EEPROM at 0x50 is on its private bus. Bus pull-ups are on the MCU sheet.
- Command set (our firmware): status (contracts, roles, DP state, VBUS V/I per port, faults), request budget ≤ X W,
  forced-5V on/off for port 1, firmware version.
- I2C_PD_INT_N is open-drain from **P7.6**, with a 10k pull-up to **PMG1_VDDD** on this sheet, so the pin never sees
  more than VDDIO. VDDD (≥ 3.0 V) is well above the RP2350 VIH. In a dead deck VDDD is up before +3V3, so up to
  ≈ 0.33 mA flows through the 10k into the unpowered RP2350 pad until +3V3 comes up (milliseconds later). That is
  harmless, and the RP2350 pad is fault-tolerant. Firmware keeps INT_N released until P3V3_SNS is high.
- **Firmware update:** the RP2350 acts as SWD programmer on P1.1/P1.2 plus XRES, through three default-closed solder
  jumpers. These use `Jumper:SolderJumper_2_Bridged` with footprint `SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm`
  and are `in_bom no`; `pd_pmg1.py` post-processes the generated file to set that. Cut them to isolate the PMG1
  (no flash interlock, per odock-10.md). The PMG1 I2C bootloader is an alternative path.
- Test pads: SWDIO_L, SWCLK_L, XRES, UART TX/RX, GND. These allow an external probe after the jumpers are cut.

## Parts (JLC stock 2026-10-02)
| Ref | Part | LCSC | Stock | Notes |
|---|---|---|---|---|
| U401 | CYPM1321-97BZXIT | C20190828 | 20 | extended; footprint from C6580811 |
| Q402 | AO4842 dual NFET 30 V SO-8 | C427016 | 2855 | port-1 back-to-back |
| Q401 | AO3400A | C20917 | 959k | basic; XRES pass FET |
| R415 | 5 mΩ 1 % 1 W 1206 RLM12FTCMR005 | C316225 | 201k | port-1 CSA shunt |
| C416–C419 | 390 pF C0G 50 V 0402 | C282239 | 70k | CC caps |
| caps | 100 nF 0402 C1525, 1 µF 0402 C52923, 4.7 µF 0603 C19666, 10 µF/25 V 0805 C15850, 100 nF/50 V 0603 C14663 | | | basic |
| resistors | 1k C11702, 4.7k C25900, 10k C25744, 100k C25741 (0402) | | | basic |
| JP401–403 | solder jumpers | — | — | in_bom no |
| TP401–406 | test pads | — | — | |

`tools/bom_check.py`: 0 failing, 0 without LCSC.

## New / inter-sheet nets
- `VBUS_LSW` and `PMG1_VDDD` are global in `nets.py`. CSA 0 is connected to the power_laptop shunt, and the
  usbc_muxes TPD4S480 VPWR runs from PMG1_VDDD.
- Local nets on this sheet: HPD0_OUT, HPD1_OUT, P3V3_SNS, XRES_RP, PMG1_XRES, PMG1_SWDIO_L, PMG1_SWCLK_L,
  PMG1_UART_TX/RX, PMG1_VCCD, DS_SRC, DS_GIN, DS_GOUT, DS_FETD.

## Open issues
1. ~~CC/SBU over-voltage protection~~ — **resolved.** TPD4S480 on the laptop port (VPWR = PMG1_VDDD, RPD_Gx = C_CCx
   for the dead-battery Rd) and TPD6S300 on the downstream port, both on usbc_muxes.
2. **NGDO pair 0 unused.** VBUS_IN/OUT_NGDO_P0 and the CTRL_P0 pins are left open. Confirm with Infineon's EPR dock
   schematic, or tie the NGDO sense pins to VBUS_LAPTOP.
3. **External laptop power path.** Confirm that PdStack/the solution layer allows a fully GPIO-controlled source
   and sink path with the CSA still active for OCP. The dock example uses NGDO plus buck-boost drivers.
4. **CSA 0 placement.** CSA 0 shares the INA226 Kelvin taps. Both are high-impedance, but route the four sense lines
   as two Kelvin pairs.
5. **VSYS back-feed.** Check that VSYS does not back-feed +3V3 from the VBUS regulator in a dead deck. The datasheet
   implies an internal switch; verify on the bench.
6. **Downstream port.** There is no back-feed in a dead deck (TPD6S300 FETs are open; see "Port 1 in a dead deck").
   Firmware must never enable a sink path on port 1, and there is no hardware sink path there.
7. **BGA footprint.** The footprint is an EasyEDA import (CYPD8225 package, 0.5 mm pitch, 6×6). Check pad size and
   solder-mask definition against Infineon's land pattern before layout. 0.5 mm BGA needs via-in-pad or a 0.2 mm
   via fan-out on 6 layers.
8. **HPD and IRQ_HPD.** PdAltMode needs application code to forward port-1 Attention to port 0 (or the hardware
   HPD loop above), and to drive UP_HPD. Verify that IRQ_HPD pulses (0.5–1 ms) survive the HPD-block decode and
   re-encode.
9. **Billboard.** USB FS is not connected. If DP entry fails, the Billboard requirement is met by the RP2350
   firmware on hub port 6 (allowed for compound devices).
10. **JLC stock.** Only 20 CYPM1321 are in stock. Re-check before ordering; CYPM1322 (50) is the fallback (see
    issue 1).
