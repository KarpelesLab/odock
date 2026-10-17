# odock-10 design review: MCU, display/UI and sensors

Reviewed on 2026-10-02 by an independent reviewer. This is a report only; no project files were changed.

**Scope.** The sheets `hardware/odock-10/sheets/mcu.py`, `display_ui.py` and `sensors.py`, plus every MCU net where it
lands on another sheet: pd_pmg1, usb_hub, usb_a, ethernet, card_reader, power_input, power_laptop and power_rails.

**Method.**
- I dumped the netlist from the `.py` sources into scratch. Sheet `build()` was stubbed out, so no `.kicad_sch` file was
  written. I then traced every net that touches U1001 or U1003 across all sheets.
- I compared the result against the documents below. "DS" means the RP2350 datasheet and "HWD" means *Hardware design
  with RP2350*.
  - RP2350 DS: table 677 (GPIO functions), tables 1673–1679 (pins), table 1680 (absolute maximum ratings), §14.9 (IO DC
    characteristics), §6.3.8 (regulator) and appendix D (errata).
  - HWD §2–5.
  - Abracon AOTA-B201610S3R3-101-T rev A.
  - TI TCA9534 (SCPS197).
  - TI TMP1075 (table 7-2, register map).
  - TI TPD4E02B04.
  - HS20HS072RX V1.0 (sections 2, 3.2 and 6).
  - ALPS SKRTLAE010 and XKB TS-1187A drawings.
  - Microchip USB7206C (PRT_DIS straps).
- I checked LCSC/JLC part values for all 33 MCU, UI and sensor part numbers through the JLC API. All of them match the
  schematic values.

## Findings

| # | Sev | Sheet | Refs / nets | Finding | Fix |
|---|---|---|---|---|---|
| 1 | **MAJOR** | mcu | L1001 (VREG_LX / +1V1) | The placement instruction for the inductor polarity dot is backwards (details below) | Reword it: "dot on the +1V1/COUT pad" |
| 2 | MINOR | mcu | U1003 P7 (`IOX_P7`) | A TCA9534 input is left floating, and the 10k pull-downs on P6/P7 promised in mcu.md are missing | Add a 10k pull-down on P7 |
| 3 | MINOR | display_ui | R1101, U1101 LED-A/K | Backlight current can exceed the panel's 80 mA absolute maximum when +5V comes from laptop VBUS | R1101 → 39 Ω (or 43 Ω) |
| 4 | MINOR | mcu | +1V1 (C1002) | The second 4.7 µF on the regulator output that RPi recommends is missing | Add 4.7 µF 0402 at DVDD pin 32 |
| 5 | MINOR | mcu + ethernet | U1003 P5 `ETH_RESET_N`, P6 `ETH_I2C_EN`, Q801 | The PHY I2C bridge can lock up I2C_SYS, and with it the expander that controls the bridge | Gate the bridge with ETH_3V3 in hardware |
| 6 | MINOR | mcu / pd_pmg1 | GPIO28 `PMG1_XRES_N`, GPIO26/27 SWD | Resetting or flashing the PMG1 while the deck runs on bus power removes the deck's own supply | Firmware interlock on EXT_PWR_PRESENT + documentation |
| 7 | NOTE | mcu / pd_pmg1 | GPIO26/27 ↔ PMG1 P1.1/P1.2 | In a dead deck, PMG1 SWD pull-ups go to VDDD (up to 3.65 V), into an unpowered FT pad rated ≤ 3.63 V | Optional 1k series resistors |
| 8 | NOTE | display_ui | U1101 VCI/IOVCC | +3V3 = 3.33 V nominal against a panel recommended maximum of 3.3 V | Accept, or document |
| 9 | NOTE | display_ui / mcu docs | HDR_GPIO0..7 | The listed header peripherals are mostly already in use, and HSTX "DVI!" does not suit the 220 Ω series resistors | Fix the silkscreen/doc claims |
| 10 | NOTE | mcu docs | GPIO8/9, GPIO30/31 | "Also hardware-I2C capable, so buses can be swapped" is only half true | Reword |
| 11 | NOTE | display_ui | D1101–D1103, HDR_P*, HDR_A* | The header "5 V tolerant" claim and ADC back-powering need clarifying | Document the header as 3.3 V; optionally use larger ADC series R |
| 12 | NOTE | sensors / docs | U1201–U1208 | TMP1075 does support SMBus Alert Response | Correct the doc and simplify the ISR |
| 13 | NOTE | mcu | U1001 stepping | Erratum RP2350-E9 (pull-down latch) affects A2 only | Confirm the JLC stock is A3/A4 |
| 14 | NOTE | docs | various | Documentation and reference-designator inconsistencies | Fix the docs |
| 15 | NOTE | ethernet / mcu | I2C_SYS address map | The RTL8156BG I2C-slave address is unknown and lands on I2C_SYS whenever the bridge is enabled | Bench-scan before enabling |

No BLOCKER was found. Every GPIO peripheral assignment is possible on its pin, the I2C pull-ups are placed correctly, and
the dead-deck back-feed paths are handled (see "Verified OK" below).

---

### 1. MAJOR: the L1001 polarity-dot instruction is backwards (mcu)

**The defect.** Two places tell layout and assembly to put the dot toward VREG_LX:
- the L1001 description in `mcu.py:112`: "polarity dot toward VREG_LX (RPi: orientation matters)";
- `docs/design/mcu.md:32`: "Place it with the dot toward VREG_LX, as in the RPi layout".

**Evidence.**
- RP2350 DS Fig. 26 is the Pico 2 regulator layout, and RPi says to copy it exactly (§6.3.8.1, "at your own risk"
  otherwise).
  - It shows VREG_LX (pin 63 on QFN-80) routed to the *right* inductor pad.
  - The *orientation indicator* sits on the *left* pad, and that pad runs to C_OUT and the V_OUT/DVDD vias.
  - So the dot belongs on the **+1V1 (DVDD/COUT) side**, not on VREG_LX.
- The imported footprint already agrees with RPi. In `IND-SMD_L2.0-W1.6_AOTA-B201610S3R3-101-T`, the silk dot at
  (0.90, −1.10) is next to pad 2, and pad 2 is +1V1 in the netlist (L1001.2). The netlist is therefore right and the
  instruction is wrong.
- Following the instruction would mean rotating the part 180° or swapping its pins. RPi says that degrades regulation
  under load and transients (DS §6.3.8.3).
- Caution: the Abracon datasheet's illustration (p.4) labels the dot terminal "+", which contradicts RPi Fig. 28. Treat
  the Pico 2 layout (Fig. 26) as the authority.

**Fix.**
- Change the L1001 description and mcu.md to "polarity dot on the +1V1/DVDD (C_OUT) pad, VREG_LX on the un-dotted pad
  (RP2350 DS Fig. 26)".
- Keep the current pin mapping (1 = VREG_LX, 2 = +1V1).
- Check the JLC CPL rotation against the footprint dot.
- Copy the inductor/capacitor geometry from the RPi minimal-board KiCad files (already listed as open issue 3).

### 2. MINOR: TCA9534 P7 floats, and the documented pull-downs on P6/P7 do not exist (mcu)

**Evidence.**
- `IOX_P7` is a single-pin net: U1003.12 only.
- mcu.md:113 and the mcu.py section 6 note both say "P6/P7 spare (10k PD)", but there is no such resistor. P6 is no
  longer spare either: it is ETH_I2C_EN, pulled down by 100k R820 on the ethernet sheet.
- TCA9534 DS §8.3.1: an input is high-impedance, and there are no internal pull-ups. Fig. 33 says unused pins "must be
  configured as outputs".

**Consequence.** Until firmware configures P7 as an output, the floating input causes:
- spurious `IOX_INT_N` interrupts (INT fires on any input edge, DS §8.3.2);
- extra ICC.
It also stays floating whenever the RP2350 is in BOOTSEL or running blank firmware.

**Fix.** Add a 10k pull-down (or pull-up) on IOX_P7. Correct the mcu.md P6/P7 row.

### 3. MINOR: backlight current can exceed the 80 mA absolute maximum (display_ui)

**Evidence.**
- HS20HS072RX §2: IF absolute maximum is 80 mA. §3.2: Vf is 2.8–3.2 V at 80 mA for 4 LEDs in parallel (20 mA × 4).
- R1101 is 33 Ω from +5V. The design worst case used 5.25 V.
- In bus-powered mode, +5V is laptop VBUS through the sink switch (power_rails note). vSafe5V may be up to 5.5 V.
  - (5.5 − 2.8) / 33 Ω = **82 mA**, before counting the lower Vf of hot LEDs.
- Normal external power gives +5V = 5.13 V, so (5.13 − 2.8) / 33 = 71 mA. That is fine.
- PWM dimming does not help, because the peak current is what matters.

**Fix.** Change R1101 to 39 Ω 1206.
- Typical (5.13 V, Vf 3.0 V): 55 mA.
- Worst case (5.5 V, Vf 2.8 V): 69 mA.
- Minimum (4.75 V, Vf 3.2 V): 40 mA.
If more margin is wanted, use 43 Ω.

### 4. MINOR: second COUT on DVDD missing (mcu)

**Evidence.** RP2350 DS §6.3.8.1: "In addition to C_OUT, for best performance we recommend a second 4.7 µF capacitor is
used on the V_OUT net, located on the bottom edge of the package (DVDD pin 23 on the QFN-60)". The QFN-80 equivalent of
that pin is DVDD pin 32, next to XIN/XOUT.

mcu.py has only C1002 (4.7 µF) plus 3 × 100 nF on +1V1.

**Fix.** Add a 4.7 µF 0402 (C23733) on +1V1 at pin 32. Keep it away from L1001/C_OUT, as the datasheet says.

### 5. MINOR: the PHY I2C bridge can lock up I2C_SYS and the expander that controls it (mcu + ethernet)

**The setup.**
- `ETH_I2C_EN` (U1003 P6) drives the gates of the 2N7002DW bridge (Q801).
- `ETH_RESET_N` (U1003 P5) switches ETH_3V3 through U802. U802 has QOD, so ETH_3V3 is discharged to 0 V when off.
- The PHY-side pull-ups (R818/R819, 4.7k) go to ETH_3V3.
- ethernet.py notes "enable only while ETH_3V3 is on". Nothing enforces this in hardware.

**The failure.**
- Suppose P6 is high while P5 is low. That happens with a firmware bug, or with the thermal-derating path that powers
  the PHY down while a MAC write is in progress.
- Then I2C_SYS_SDA/SCL are pulled through the conducting FET channels into the unpowered PHY pins and pull-ups.
- This loads I2C_SYS toward the low or undefined region:
  - with the 2.2k bus pull-up against the 4.7k to 0 V, the bus sits at about 2.25 V, which is below VIH = 2.31 V;
  - the PHY's own ESD clamps to its dead rail pull it lower still.
- The TCA9534 that would clear P6 sits on that same I2C_SYS. It has no reset pin, so I2C_SYS stays dead until a full
  power cycle.

**Fix**, preferably in hardware: only allow the gate drive when ETH_3V3 is up.
- Option A: feed the Q801 gates from ETH_I2C_EN through a series resistor, with a small N-FET pulling the gates low when
  ETH_3V3 is absent.
- Option B: take the gate drive from ETH_3V3 through a P6-controlled switch.

As a minimum, firmware must clear P6 before any write that drives P5 low.

### 6. MINOR: PMG1 reset/flash on bus power cuts the deck's supply (mcu / pd_pmg1)

**Evidence.**
- In bus-powered mode, +5V and +3V3 exist only because PMG1 P0.0 drives LAPTOP_SNK_EN (power_laptop: SNK_ON =
  LAPTOP_SNK_EN 10k/47k ...).
- The RP2350 can assert PMG1_XRES_N (GPIO28, then JP401 and the pass FET Q401) and reflash the PMG1 over SWD.
- Once the PMG1 is in reset, its GPIOs go Hi-Z: LAPTOP_SNK_EN drops, the deck loses +3V3, and the RP2350 browns out in
  the middle of the flash.
- The PMG1 is then left with a corrupt image. It is only recoverable with external power, because a bus-powered start
  needs working PMG1 firmware.

**Fix.**
- Document it as a requirement: firmware must only toggle PMG1_XRES_N or start a PMG1 SWD session when EXT_PWR_PRESENT = 1
  (TCA9534 P0).
- Add it to pd_pmg1.md / mcu.md "Firmware notes".
- The PMG1 I2C bootloader path has the same constraint.

### 7. NOTE: PMG1 SWD pull-ups into the unpowered RP2350 (mcu / pd_pmg1)

**Evidence.**
- In a dead-deck start, PMG1 VDDIO = PMG1_VDDD = 3.0–3.65 V (from the VBUS regulator, pd_pmg1 note).
- The PMG1 SWD pull-ups (~5.6k) drive GPIO26/27 directly through JP402/JP403.
- RP2350 DS table 1673/1680: an FT pad with IOVDD = 0 is specified to "very little current … below 3.63 V".
- So at the top of the VDDD range this is marginally out of spec. The source impedance is high (5.6k) and the likely
  current is µA-level, so the practical risk is low.

**Fix (optional).** Fit 1k series resistors in PMG1_SWDIO/SWCLK on the mcu side. This is harmless for SWD at ≤ 10 MHz.

### 8. NOTE: LCD supply at 3.33 V (display_ui)

**Evidence.** HS20HS072RX §3.1 gives a recommended maximum of 3.3 V for both VCI and IOVCC; the absolute maximum is
4.6 V. +3V3 is set to 3.33 V (power_rails RFBT/RFBB = 31.6k/10k), so it is up to about 3.36 V with resistor tolerance.

This is only marginally out of the recommended range, and is common practice.

**Fix.** Accept it and record it as a known deviation. Alternatively, retrim +3V3 to 3.30 V; the RP2350 accepts
3.135–3.63 V, so it would not care.

### 9. NOTE: the user-header capability claims are wrong (display_ui.py:127, display_ui.md:107-108)

**What the docs claim.** "UART0 (12/13), SPI1 (12–15), SPI0 (16–19), I2C0/I2C1 on every pair" is listed as available.

**What is actually free.** Checked against DS table 677 and the GPIO allocation:
- I2C0 is I2C_PD (GPIO4/5) and I2C1 is I2C_SYS (GPIO2/3), so neither controller is free.
- UART0 is the debug console (GPIO0/1).
- SPI0 is the LCD (GPIO20–23).
- The genuinely free hardware for the header is SPI1 (12–15), PWM slices 6/7/0/1, HSTX, and the third PIO block.

**HSTX "DVI!".** DVI breakouts drive TMDS through their own ~270 Ω resistors. The added 220 Ω series resistors (R1106–
R1113) and the TVS capacitance make DVI unlikely to work.

**Fix.** Correct the silkscreen/back-side table text before it is drawn. Either drop "DVI" or fit 0 Ω/DNP options for
R1106–R1113.

### 10. NOTE: the "swap buses" claim for GPIO8/9 and GPIO30/31 (mcu.py section 5 note, mcu.md "Firmware notes")

DS table 677: GPIO8/9 map to I2C0, and GPIO30/31 map to I2C1. Those are the same controllers as I2C_PD and I2C_SYS.

A swap is therefore only possible by giving up the other bus. The PIO assignment itself is feasible:
- PIO0 at GPIOBASE 0 can host the SMBus (8/9), SWD (26/27) and Qwiic (30/31);
- PIO1 at GPIOBASE 16 can host the LED counters (36–39);
- PIO2 stays free.

**Fix.** Reword the note.

### 11. NOTE: header protection details (display_ui)

**The "5 V tolerant while powered" claim** (display_ui.md and the sheet note).
- The FT pads do allow 5.5 V with IOVDD up.
- But TPD4E02B04 VRWM is 3.6 V and VBRF is 5.5 V minimum. Leakage at 5 V is unspecified, though VHOLD = 5.8 V means a 5 V
  source cannot hold the clamp in snapback.
- Specify the header as 3.3 V logic and treat 5 V as abuse, not a feature.

**HDR_A0/A1 back-power risk.**
- 1k into non-FT pads: a user's 3.3 V source applied with the deck off pushes about 2.7 mA through the GPIO44/45 clamp
  into the whole +3V3 rail.
- Optional fix: 10k series plus 10 nF at the pin, as already done for ISENSE.

### 12. NOTE: TMP1075 does support SMBus Alert Response (sensors)

**Evidence.**
- sensors.md and sensors.py say "ALERT has no per-device flag (LM75-style), so the ISR reads all 8".
- TMP1075 DS §7.3.2.6 says otherwise: in interrupt mode (TM = 1), the devices answer ARA (0x0C) with their address.
  Arbitration clears one device at a time.
- 0x0C is free on I2C_SYS.

The power-on default is comparator mode (config 00FFh), which keeps the blank-firmware 80 °C flag. Firmware could
switch to TM = 1 after boot.

**Fix.** Correct the doc. This is optional and has no hardware impact.

### 13. NOTE: RP2350 erratum E9

**Evidence.** RP2350-E9 is the pad pull-down that fails to pull a pin low after it was driven high with input enabled.
DS appendix D.5.1 lists it as affecting **A2 only**.

The design relies on internal pull-downs in several places:
- LCD_RST_N and LCD_CS_N have no external resistor;
- FORCE_EN, SMB_PU and the backlight gate have 100k externally, which E9 would overpower on A2 silicon.

**Fix.** Confirm that the JLC/LCSC stock (C42415655) is A3/A4, using the marking or CHIP_ID.REVISION on the first
articles.

### 14. NOTE: documentation and netlist mismatches

| Location | What is wrong | Correct value |
|---|---|---|
| mcu.md:76–77 | LCD series resistors listed as R1024/R1025 | They are **R1022/R1023**. R1025 is the status-LED 1k |
| mcu.md:130 | ISENSE 10k listed as R1019/R1021 | They are **R1018/R1019**. R1020/R1021 are the NTC bias |
| mcu.py section 7 note, mcu.md "Requirements on other sheets" 2 | They still discuss an INA180 powered from +5V | usb_a already powers the INA180s (U703, U706) from +3V3 (and adds 1k/100 nF). The 10k series is now just a second RC stage |
| ethernet.py:245 | R820 description: "its 10k PD also holds it off" | No 10k pull-down exists on the mcu side (see finding 2) |
| card_reader.py section 5 note | Says the RP2350 taps the card-detect nodes, and "internal pulls OFF" | CR_CD_SD_N/USD_N go to **TCA9534 P3/P4**, which has no pulls at all. The circuit is fine; only the note is wrong |

### 15. NOTE: RTL8156BG slave address on I2C_SYS

While ETH_I2C_EN is high, the PHY's I2C slave is on I2C_SYS, and its address is "not in the DS" (ethernet.py).

It must not collide with any address already used on I2C_SYS:
- 0x20 (TCA9534);
- 0x41/0x44/0x45 (INA);
- 0x48–0x4F (TMP1075);
- 0x50 (EUI EEPROM);
- 0x0C (ARA, if finding 12 is adopted).

**Fix.** Bench-scan the PHY address with the other devices isolated, before relying on the eFuse write.

---

## Verified OK (no action)

**Pinout and symbol.**
- RP2350B: the symbol pin numbers match DS table 1674/1679 for QFN-80:
  - IOVDD 5/15/24/29/41/50/60/76;
  - DVDD 10/32/51;
  - VREG 61–65, USB 66/67, USB_OTP_VDD 68, QSPI 69–75, ADC_AVDD 59, EP 81.
- The `GPIOn_ADCm` pin names for 40–47 are correct.

**GPIO feasibility (DS table 677).**

| Function | Pins |
|---|---|
| UART0 TX/RX | GPIO0/1 |
| I2C1 | GPIO2/3 |
| I2C0 | GPIO4/5 |
| SPI0 RX/CSn/SCK/TX | GPIO20/21/22/23 |
| PWM4 B | GPIO25 |
| PWM11 B | GPIO47 |
| HSTX | GPIO12–19 |
| ADC0–7 | GPIO40–47 |

- The FT pins are GPIO0–39, SWD and RUN (≤ 3.63 V while unpowered).
- The non-FT pins are GPIO40–47 (max IOVDD + 0.5 V).

**RP2350 support circuit.**
- It matches HWD/DS:
  - 3.3 µH AOTA inductor;
  - C_IN/C_OUT/VREG_AVDD 4.7 µF;
  - 33 Ω VREG_AVDD filter;
  - VREG_FB to DVDD;
  - ABM8-272-T3 crystal with 2 × 15 pF and a 1k XOUT resistor (Crystal_GND24 pin 1/3 = crystal, 2/4 = GND, matching
    the ABM8);
  - W25Q128JVSIQ pinout, SD0 → DI, SD1 → DO;
  - QSPI_SS 10k DNP plus 1k to BOOTSEL;
  - 27 Ω USB series resistors to hub port 6;
  - 1k on RUN against the internal pull-up (about 0.1 V when pressed).
- TS-1187A A-B / C-D pairs are joined, and footprint pads 1/2 (A/B) sit on the same side.
- SKRTLAE010: pins 1/3 are common and pin 2 is the contact, per the ALPS circuit diagram.

**I2C pull-ups: exactly one set per bus.**

| Bus | Pull-ups | Location |
|---|---|---|
| I2C_SYS | R1009/R1010 | only (the bridge adds PHY-side 4.7k only while enabled; 2.2 mA, OK) |
| I2C_PD | R1011/R1012 | only |
| I2C_EXT | R1013/R1014 | only |
| Hub SMBus | none on mcu | R627/R628 to HUB_SMB_PU, with 100k R629 on usb_hub |

- I2C_SYS capacitance is estimated at ≤ 130 pF, giving tr ≈ 240 ns at 2.2k, which is within 300 ns.

**Drive types.**
- HUB_SMB_PU is push-pull with 100k PD.
- HUB_RESET_N is open-drain emulation with a 10k PU and the RAILS_PG Schottky OR. With the RP2350 in reset it sits at
  ≥ 2.58 V (10k against the 36k minimum pull-down).
- PMG1_XRES_N goes through the gate=+3V3 pass FET with 10k on the RP2350 side. It is isolated in a dead deck, and the
  body diode is reverse-biased.
- ETH_RESET_N is a TCA9534 push-pull output with 10k PU. The power-on input state means the PHY is on.
- USBA1/2_FORCE_EN are push-pull with 100k PD on usb_a.

**Dead-deck sources.**
- PDIN_PRESENT: 1k into FT GPIO29.
- CR_LED: 1k, GL3224 3.3 V, into FT GPIO39.
- ETH_LED0..2: buffered on +3V3.
- I2C_PD and both IRQs: pull-ups on +3V3, so they idle at 0 V.
- ISENSE: INA180 is on +3V3, plus 1k + 10k series.
- NTC: biased from ADC_AVDD.
- IOX_INT_N: pulled to +3V3.
- EXT_PWR_PRESENT, LAPTOP_OVP_N, TEMP_ALERT_N and CR_CD_*: all on TCA9534 inputs, which are high-Z and 5.5 V tolerant.

**Single pull-ups.**
- TEMP_ALERT_N has only R1016.
- TCA9534 address 0x20 (A2..A0 = 000) is free on I2C_SYS.
- TCA9534 TSSOP-16 symbol pinout is correct.

**Sensors.**
- TMP1075 straps decode to 0x48–0x4F (DS table 7-2), with no conflict against INA 0x41/0x44/0x45 (straps checked on
  power_rails, power_laptop and power_input), TCA9534 0x20 or EEPROM 0x50.
- TMP1075 DSG pinout is correct.
- TMP1075 defaults: config 00FFh, TLOW 75 °C, THIGH 80 °C.

**LCD.**
- FPC pinout matches HS20HS072RX §6: 1 GND, 2 CS, 3 RS, 4 SCL, 5 SDA, 6 RST, 7 NC, 8 IOVCC, 9 VCI, 10 A, 11 K, 12 GND.
- The interface is 4-wire SPI with no IM straps.
- The backlight is 4 LEDs in parallel with separate A/K pins, so the low-side AO3400A switch is valid. Gate PD 100k.

**Qwiic and header protection.**
- Qwiic pinout: 1 GND, 2 3V3, 3 SDA, 4 SCL.
- The header has 220 Ω + ESD on GPIO and 1k + ESD on ADC, plus PTC-fused 5V/3V3.
- Qwiic has ESD at the connector.
- Hub port 6 PRT_DIS strap: both DP and DM must be high to disable the port, so the RP2350's FS pull-up on DP alone
  cannot disable it.

---

## Resolution

Applied on 2026-10-02 to `mcu.py`, `display_ui.py`, `sensors.py` and `docs/design/mcu.md`, `display_ui.md`, `sensors.md`.
`build_all.py mcu display_ui sensors` gives "netlist verify: OK" and `tools/bom_check.py` gives 0 failing. New parts were
created at the end of each `build()`, so no existing reference designator moved.

| # | Status | Resolution |
|---|---|---|
| 1 | **Fixed** (text) | The L1001 description, a new section-2 sheet note and mcu.md now say: polarity dot on the +1V1/DVDD (C_OUT) pad 2, VREG_LX on the un-dotted pad 1 (RP2350 DS Fig. 26). Pin mapping unchanged (1 = VREG_LX, 2 = +1V1), matching the footprint dot. Added a placement note: verify the JLC CPL rotation in the placement preview so the dot lands on pad 2. mcu.md open issue 3 updated. |
| 2 | **Fixed** | Added **R1028** 10k from IOX_P7 to GND. The mcu.py note and the mcu.md expander table now show P6 = ETH_I2C_EN (output, 100k pull-down R820 on the ethernet sheet, none here) and P7 = spare with 10k PD; firmware rule I1 sets P7 as output low. The stale R820 description on ethernet.py ("its 10k PD also holds it off") belongs to the ethernet owner. |
| 3 | **Fixed** | R1101 33 Ω → **39 Ω 1 % 1206, C22198** (UNI-ROYAL 1206W4F390JT5E, 94k in stock). Worst case at +5V = 5.5 V, Vf 2.8 V: 69 mA (72 mA at Vf 2.7 V), under 80 mA. Typical at 5.13 V, Vf 3.0 V: 55 mA. Minimum at 4.75 V, Vf 3.2 V: 40 mA. Dissipation ≤ 0.19 W. Sheet note and display_ui.md updated. |
| 4 | **Fixed** | Added **C1028** 4.7 µF 0402 (C23733) on +1V1, described and noted as "at DVDD pin 32, bottom edge, away from L1001/C_OUT". |
| 5 | Not handled here | Ethernet-sheet fix by another agent. The firmware minimum (clear P6 before P5 low) is firmware rule E2 in mcu.md. |
| 6 | **Fixed** (doc + sheet note) | Rule M1 in the new mcu.md "Firmware rules" section: never assert PMG1_XRES_N, start PMG1 SWD or use the PMG1 I2C bootloader unless EXT_PWR_PRESENT = 1. It is also in the GPIO table (GPIO26–28), mcu.md "Firmware notes", the section-3 note and a new section-11 "Firmware rules" note on mcu.py. pd_pmg1.md is owned by another agent; it should reference M1. |
| 7 | **Fixed** | Added **R1026/R1027** 1k in series between GPIO26/27 and PMG1_SWCLK/SWDIO (GPIO nets renamed MCU_PMG1_SWCLK/SWDIO, local). The global nets are unchanged. |
| 8 | Accepted (documented) | Recorded as a known deviation in the display_ui.py LCD note and display_ui.md: +3V3 = 3.33 V nominal against the 3.3 V recommended maximum, with retrimming as an option. |
| 9 | **Fixed** (text) | The header note and display_ui.md now list only the free functions (SPI1, PWM6/7/0/1, PIO2, HSTX). They state that UART0, SPI0, I2C0 and I2C1 are in use and that HSTX is not DVI-capable behind 220 Ω + ESD (do not print "DVI"). mcu.md GPIO12 row is fixed too. |
| 10 | **Fixed** (text) | The mcu.py section-5 note, the GPIO8/30 rows and mcu.md "Firmware notes" now say that GPIO8/9 = I2C0 and GPIO30/31 = I2C1, the controllers already used, so a swap costs the other bus. The PIO0/PIO1/PIO2 budget is added. |
| 11 | **Fixed** | The header is documented as 3.3 V logic, with 5 V treated as abuse. HDR_ADC0/1 series resistors R1114/R1115 1k → **10k**, plus **C1108/C1109** 10 nF at the RP2350 side. Back-power into GPIO44/45 drops from ~2.7 mA to ~0.3 mA. |
| 12 | **Fixed** (text) | The sensors.py note and sensors.md now describe the ARA (0x0C, TM = 1 after boot) as an option next to reading all 8. 0x0C is added to the I2C_SYS map. Firmware rule I3. |
| 13 | Open (bring-up) | Stepping cannot be confirmed from the JLC API. mcu.md now has a stepping/E9 paragraph, open issue 6 and firmware rule I7: read CHIP_ID.REVISION; on A2, drive pull-down-dependent pins low before releasing them, and switch R629/R702/R707 to 4.7k (data review #4, other sheets). |
| 14 | **Fixed** for owned files | mcu.md: LCD series resistors are R1022/R1023, ISENSE 10k are R1018/R1019, the INA180 text matches usb_a (+3V3, 1k/100 nF; requirement 2 marked done), and the card-detect text points to TCA9534 P3/P4. The mcu.py section-7 note is reworded. The ethernet.py R820 description and the card_reader.py section-5 note belong to other owners and are still open. |
| 15 | Documented | Firmware rule E3 (bench-scan the PHY address against 0x0C/0x20/0x41/0x44/0x45/0x48–0x4F/0x50 before the eFuse write), mcu.md open issue 7, and the sensors.md I2C map. |

Also: display_ui.md's footprint paragraph now matches the reworked `LCD_FPC_Solder_12P_P0.50mm` (footprint review 1, item 12):
0.3 × 4.75 mm lands, pin 1 at −X with the exit edge at +Y, a 180° fold, and hot-bar or pre-tinning through the stiffener.
mcu.md also gained a "Firmware rules" section, which collects every firmware constraint from `docs/design/*.md` and
`docs/review/*.md` and is the seed of the firmware spec.
