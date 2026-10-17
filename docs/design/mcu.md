# odock-10 — MCU sheet (`mcu.kicad_sch`, refs 1000+)

Source: `hardware/odock-10/sheets/mcu.py` (generated, netlist-verified). References:
- RP2350 datasheet (build 2026, "DS"): pin table 14.8.2, abs max 14.9.1, GPIO functions 9.4.
- Raspberry Pi *Hardware design with RP2350* release 3 (2026-08-20), "minimal design" R4-S1 ("HWD").

Stock figures are from the JLC parts API on 2026-10-02.

## Block

```
+3V3 ─┬─ IOVDD x8, QSPI_IOVDD, USB_OTP_VDD, VREG_VIN (100 nF each, 4.7 µF C1001, 10 µF bulk)
      ├─ 33R ─ VREG_AVDD (4.7 µF)          VREG_LX ─ L1001 3.3 µH (AOTA, dot on +1V1 side) ─ +1V1 = DVDD x3 + VREG_FB (2x 4.7 µF)
      └─ 10R ─ ADC_AVDD (4.7 µF + 100 nF) ─ 10k ─ NTC_ADC0/1 (NTC to GND on sensors)
XIN ─ Y1001 ABM8-272-T3 12 MHz ─ 1k ─ XOUT, 2x 15 pF       QSPI ─ U1002 W25Q128JVSIQ; QSPI_SS ─ 1k ─ BOOTSEL ─ GND
RUN ─ 1k ─ RESET ─ GND      SWD pads TP1001-4 (SWCLK, SWDIO, RUN, GND)     USB_DP/DM ─ 27R ─ MCU_USB_DP/DN (hub port 6)
GPIO26/27 ─ 1k (R1026/R1027) ─ PMG1_SWCLK/SWDIO;  GPIO28 ─ PMG1_XRES_N (pass FET on pd_pmg1)
I2C1 (GPIO2/3) = I2C_SYS, 2.2k ─┬─ TCA9534 @0x20: EXT_PWR_PRESENT, LAPTOP_OVP_N, TEMP_ALERT_N, CR_CD_SD_N, CR_CD_USD_N,
                                 │                   ETH_RESET_N + ETH_I2C_EN (out), P7 spare (10k PD); INT ─ IOX_INT_N (GPIO46)
I2C0 (GPIO4/5) = I2C_PD 2.2k;  PIO I2C: HUB SMBus (GPIO8/9, no pull-ups), I2C_EXT/Qwiic (GPIO30/31, 4.7k)
```

## Part choice
- **RP2350B (C42415655)**: 3873 in stock, $1.28. It is the QFN-80 part with 48 GPIO and no internal flash.
  - The symbol and footprint are LCSC imports. Pin numbers match DS table 1674 (QFN-80 column).
    - GPIO0 = 77 … GPIO3 = 80, GPIO4 = 1.
    - IOVDD = 5/15/24/29/41/50/60/76, DVDD = 10/32/51.
    - VREG_AVDD/PGND/LX/VIN/FB = 61–65, USB_DM/DP = 66/67, USB_OTP_VDD = 68, QSPI_IOVDD = 69, ADC_AVDD = 59.
    - EP = GND (81).
  - Pin types are fixed with fix_pins.
- **The regulator and crystal follow HWD exactly.** RPi says layout or part deviations are "at your own risk".
  - **L1001 Abracon AOTA-B201610S3R3-101-T (C42411119)**: 3338 in stock. It is the polarity-marked 3.3 µH part RPi
    co-developed. **Orientation: the polarity dot goes on the +1V1/DVDD (C_OUT) pad; VREG_LX goes on the un-dotted pad**,
    as in the Pico 2 layout (RP2350 DS Fig. 26). The pin mapping is 1 = VREG_LX, 2 = +1V1, and the footprint's silk dot
    is already next to pad 2. The Abracon drawing labels the dot terminal "+", which contradicts RPi Fig. 28; follow the
    Pico 2 layout. A rotated or pin-swapped inductor degrades regulation under load (DS §6.3.8.3).
    - **Placement check:** JLC's CPL rotation for this part must be verified in the JLC placement preview so that the
      physical dot lands on pad 2 (+1V1). Reject the order preview if the dot faces VREG_LX.
  - **Y1001 Abracon ABM8-272-T3 (C20625731)**: 13.6k in stock. 12 MHz, CL 10 pF, ESR 50 Ω, the Pico 2 crystal.
    It uses 15 pF load caps and a 1k XOUT damping resistor.
  - Caps: C6/C7/C9 equivalents are 4.7 µF 0402 (C1001–C1003), and R3 = 33 Ω (R1001).
  - **C1028**, a second 4.7 µF 0402 on +1V1, sits at **DVDD pin 32** (bottom edge of the package, next to XIN/XOUT), as
    DS §6.3.8.1 recommends ("a second 4.7 µF on V_OUT, on the bottom edge of the package"). Keep it away from L1001/C_OUT.
- **U1002 W25Q128JVSIQ (C97521, basic)**: 49.6k in stock. 16 MB is the RP2350 maximum. It holds the RP2350 firmware plus the
  bundled PMG1 image, TPS26750 EEPROM image and hub configuration. QSPI_SS has a 10k pull-up, DNP per HWD (R1004), and the
  1k BOOTSEL resistor (R1005).
- **U1003 TCA9534PWR (C783615)**: 15k in stock, $0.71. It is needed because all 48 GPIO are used (see the table). Address
  0x20, free on I2C_SYS.
- Buttons SW1001 (BOOTSEL) and SW1002 (RESET) are TS-1187A-B-A-B (C318884, basic). A-B and C-D are joined internally
  (datasheet), and both sides are wired.
- LEDs: D1001 KT-0805G green (basic) is the power LED, on +3V3 through 330 Ω. D1002 KT-0603R red (basic) is the status LED,
  on GPIO47 through 1k.
- J1001 is the debug UART: a 1x3 2.54 mm header, unpopulated (`in_bom no`). TP1001–TP1004 are the SWD pads, copper only.

## GPIO allocation (complete)

FT = fault-tolerant pad: 5.5 V max with IOVDD at 3.3 V, and ≤ 3.63 V with IOVDD = 0 and very little current (DS 14.8.2.1).
GPIO40–47 are standard pads: max IOVDD + 0.5 V, so only 0.5 V while +3V3 is off.

| GPIO | Pin | Net | Dir | Function / block | Notes |
|---|---|---|---|---|---|
| 0 | 77 | UART_TX (local) | out | UART0 TX | Debug header J1001 |
| 1 | 78 | UART_RX (local) | in | UART0 RX | Debug header J1001 |
| 2 | 79 | I2C_SYS_SDA | io | I2C1 SDA | 2.2k PU here. INA226 ×2, INA237, TMP1075 ×8, TCA9534, EUI-48 EEPROM |
| 3 | 80 | I2C_SYS_SCL | io | I2C1 SCL | 2.2k PU here |
| 4 | 1 | I2C_PD_SDA | io | I2C0 SDA | 2.2k PU here. PMG1 HPI 0x42, TPS26750 0x21 |
| 5 | 2 | I2C_PD_SCL | io | I2C0 SCL | 2.2k PU here |
| 6 | 3 | I2C_PD_INT_N | in | PMG1 interrupt | OD, 10k PU on pd_pmg1 |
| 7 | 4 | PDIN_INT_N | in | TPS26750 interrupt | OD, 10k PU on power_input |
| 8 | 6 | HUB_SMB_DAT | io | PIO I2C SDA | **No pull-up here** (fed from HUB_SMB_PU on usb_hub). I2C0 pin, but I2C0 runs I2C_PD |
| 9 | 7 | HUB_SMB_CLK | io | PIO I2C SCL | Clock stretching is handled by the PIO program |
| 10 | 8 | HUB_SMB_PU | out | push-pull | Powers the hub SMBus pull-ups. Low at reset, so the hub boots stand-alone |
| 11 | 9 | HUB_RESET_N | OD | open-drain emulation | 10k PU + RAILS_PG wire-OR on usb_hub |
| 12 | 11 | HDR_GPIO0 | io | user header | GPIO12–19: PIO-contiguous. Free for the header: SPI1 (12–15), PWM6/7/0/1, PIO2, HSTX (not DVI) |
| 13 | 12 | HDR_GPIO1 | io | user header | |
| 14 | 13 | HDR_GPIO2 | io | user header | |
| 15 | 14 | HDR_GPIO3 | io | user header | |
| 16 | 16 | HDR_GPIO4 | io | user header | |
| 17 | 17 | HDR_GPIO5 | io | user header | |
| 18 | 18 | HDR_GPIO6 | io | user header | |
| 19 | 19 | HDR_GPIO7 | io | user header | |
| 20 | 20 | LCD_DC | out | SIO | SPI0 RX slot, unused by a write-only panel |
| 21 | 21 | LCD_CS_N | out | SPI0 CSn | |
| 22 | 22 | LCD_SCK (via 33R R1022) | out | SPI0 SCK | Up to 62.5 MHz |
| 23 | 23 | LCD_MOSI (via 33R R1023) | out | SPI0 TX | |
| 24 | 25 | LCD_RST_N | out | SIO | Reset pull-down holds the panel in reset until firmware runs |
| 25 | 26 | LCD_BL_PWM | out | PWM4 B | Reset pull-down plus 100k on display_ui keep the backlight off |
| 26 | 27 | PMG1_SWCLK (via 1k R1026) | out | PIO SWD probe | Then solder jumper on pd_pmg1. **Only with EXT_PWR_PRESENT = 1** |
| 27 | 28 | PMG1_SWDIO (via 1k R1027) | io | PIO SWD probe | Then solder jumper on pd_pmg1. **Only with EXT_PWR_PRESENT = 1** |
| 28 | 36 | PMG1_XRES_N | OD | open-drain emulation | Pass FET + jumper + 4.7k PU on pd_pmg1. **Only with EXT_PWR_PRESENT = 1** |
| 29 | 37 | PDIN_PRESENT | in | status | 3.3 V from the TPS26750 GPIO via 1k (power_input). It can be high while +3V3 is off, which an FT pin tolerates |
| 30 | 38 | I2C_EXT_SDA | io | PIO I2C (Qwiic) | 4.7k PU here. I2C1 pin, but I2C1 runs I2C_SYS |
| 31 | 39 | I2C_EXT_SCL | io | PIO I2C (Qwiic) | 4.7k PU here |
| 32 | 40 | BTN_A_N | in | user button A | 10k PU + 10 nF on display_ui |
| 33 | 42 | BTN_B_N | in | user button B | 10k PU + 10 nF on display_ui |
| 34 | 43 | USBA1_FORCE_EN | out | push-pull | Reset pull-down = off, plus 100k PD on usb_a |
| 35 | 44 | USBA2_FORCE_EN | out | push-pull | Same as USBA1_FORCE_EN |
| 36 | 45 | ETH_LED0 | in | PIO/SIO | RTL8156BG LED pin. Edge counting for activity |
| 37 | 46 | ETH_LED1 | in | PIO/SIO | |
| 38 | 47 | ETH_LED2 | in | PIO/SIO | |
| 39 | 48 | CR_LED | in | SIO | GL3224 activity. The GL3224 runs from +5V, so it can be live before +3V3; FT pin |
| 40 | 49 | ADC_ISNS1 ← 10k (R1018) ← USBA1_ISENSE | ain | ADC0 | 10 nF at the pin |
| 41 | 52 | ADC_ISNS2 ← 10k (R1019) ← USBA2_ISENSE | ain | ADC1 | 10 nF at the pin |
| 42 | 53 | NTC_ADC0 | ain | ADC2 | 10k bias to ADC_AVDD + 100 nF here. NTC to GND on sensors |
| 43 | 54 | NTC_ADC1 | ain | ADC3 | Same as NTC_ADC0 |
| 44 | 55 | HDR_ADC0 | ain | ADC4 | 10k + 10 nF + ESD on display_ui |
| 45 | 56 | HDR_ADC1 | ain | ADC5 | 10k + 10 nF + ESD on display_ui |
| 46 | 57 | IOX_INT_N (local) | in | TCA9534 INT | 10k PU to +3V3. Digital use of an ADC pin; it is never above +3V3 |
| 47 | 58 | LED_STATUS (local) | out | PWM11 B | Red status/fault LED, high = on |

**I/O expander (U1003, TCA9534 @ 0x20)**

| Port | Net | Dir | Notes |
|---|---|---|---|
| P0 | EXT_PWR_PRESENT | in | 3.3 V push-pull (74LVC1G32 on power_input), 100k PD on pd_pmg1 |
| P1 | LAPTOP_OVP_N | in | OD, 10k PU on power_laptop |
| P2 | TEMP_ALERT_N | in | TMP1075 wired-OR; **its single 10k PU (R1016) is here** |
| P3 | CR_CD_SD_N | in | Taps the GL3224 CD node through 1k on card_reader (GL3224 internal pull-up). The TCA9534 has no pulls |
| P4 | CR_CD_USD_N | in | Same as P3 |
| P5 | ETH_RESET_N | out | 10k PU here (R1017). The expander powers up as inputs, so the PHY runs without firmware. Write 0 to reset it |
| P6 | ETH_I2C_EN | out | Gates of the PHY I2C bridge Q801. 100k PD (R820) on the ethernet sheet, none here. See firmware rules |
| P7 | IOX_P7 (spare) | — | **10k PD here (R1028)**, so it never floats. Firmware sets it as output low. Candidates: a CCPROT fault flag or USBA1_OCS_N |

**Why an expander.** The must-have signal list needs 54 pins against 48 GPIO. The slow, level-type status signals went to
the expander. The PMG1 already reads EXT_PWR_PRESENT and LAPTOP_OVP_N and owns the safety reaction, so the RP2350 only
displays them. Interrupt-type and fast signals stay on native GPIO: both PD IRQs, buttons, LED activity, SPI and SWD.
- The optional VBUS/VIN/+5V ADC monitor was dropped: INA237 (VIN), INA226 (laptop VBUS) and INA226 (+5V) already measure
  those rails over I2C_SYS.

## Level and dead-deck review
- **The RP2350 GPIOs are FT on GPIO0–39 only.** With the deck unpowered, they take ≤ 3.63 V with negligible current.
- **Signals that can be high while +3V3 is off**, during a bus-powered cold start with the PMG1 on laptop VBUS:
  - **PDIN_PRESENT**: the TPS26750 runs from PD-in VBUS. It goes to GPIO29 (FT) with 1k series on power_input. OK.
  - **PMG1_SWDIO/SWCLK**: the PMG1 SWD pull-ups (~5.6k) go to PMG1_VDDD, which is 3.0–3.65 V in a dead deck, slightly over
    the 3.63 V FT limit with IOVDD = 0. The 1k series resistors R1026/R1027 add margin; the current is µA-level. OK.
  - **PMG1_XRES_N**: the pass FET on pd_pmg1 already isolates it, so the RP2350 does not clamp XRES.
  - **CR_LED**: the GL3224 is on +5V, which rises before +3V3. GPIO39 (FT). OK.
  - **I2C_PD / PD IRQs**: open drain with pull-ups to +3V3, so they idle at 0 V when +3V3 is off. OK.
- **ADC pins (40–47) are not FT.**
  - USBA1/2_ISENSE pass through 10k (R1018/R1019). usb_a powers the INA180s (U703, U706) from +3V3 and adds 1k/100 nF, so
    the 10k + 10 nF here is a second RC stage. It still limits clamp current to < 0.2 mA if a source were ever live.
  - NTC_ADC0/1 are passive and biased from ADC_AVDD, so they read 0 V when off.
  - HDR_ADC0/1 have 10k + 10 nF on display_ui (R1114/R1115, C1108/C1109). A user 3.3 V source with the deck off pushes
    only ~0.3 mA into the GPIO44/45 clamp.
  - IOX_INT_N is pulled to +3V3.
- **EXT_PWR_PRESENT, LAPTOP_OVP_N, TEMP_ALERT_N and CR_CD_*** are all 0–3.3 V and low or unpowered with +3V3 off, so no
  dividers are needed. The TCA9534 I/Os are 5.5 V tolerant regardless.
- **Reset state.** Every GPIO powers up as an input with a pull-down (DS table 1674). Consequences:
  - FORCE_EN is off.
  - The LCD is in reset with the backlight off.
  - HUB_SMB_PU is low, so the hub boots from ROM and the BOOTSEL UF2 still enumerates.
  - HUB_RESET_N and PMG1_XRES_N read high through their external pull-ups (a 10k or 4.7k pull-up against about 50k).
- **Stepping and erratum RP2350-E9** (pad pull-down latches at about 2.2 V after the pin was driven high, then released;
  A2 only, fixed in A3/A4, DS appendix D.5.1). The design relies on the internal pull-down for LCD_RST_N and LCD_CS_N, and
  FORCE_EN, HUB_SMB_PU and the backlight gate have only 100k externally. **The stepping of the JLC stock (C42415655) is not
  confirmed.** Bring-up item: read the package marking or CHIP_ID.REVISION on the first articles and record it here. If it is
  A2, change R629/R702/R707 to 4.7k (data review #4) and follow the firmware rule below.
- ETH_LEDx and CR_LED may be **power-on straps** on the RTL8156BG/GL3224. The RP2350 reset pull-down (35–189k) is weak, but
  the ethernet and card_reader sheets must set any such straps with ≤ 10k.

## Power
- Total ≈ 30–60 mA at 150 MHz on +3V3 (< 0.2 W). +1V1 is generated on chip and is used only by the RP2350. The sheet carries
  the `+1V1` PWR_FLAG.
- ADC_AVDD is +3V3 through 10 Ω / 4.7 µF. It is the ADC reference, and the NTC bias hangs on it, so the NTC reading is
  ratiometric.

## USB
- The 27 Ω series resistors (R1007/R1008, extended C25100) sit at the RP2350 pins, as RPi requires. The trace runs
  differential, 90 Ω, to hub port 6.
- No VBUS detect: the device is permanently attached to the hub.

## Firmware notes
- **Buses.** I2C1 runs I2C_SYS and I2C0 runs I2C_PD, both hardware at 400 kHz. I2C_PD may run at 1 MHz.
  - The HUB SMBus and Qwiic use PIO I2C with clock stretching. The USB7206C stretches the clock before tSMBUS_RDY.
  - GPIO8/9 map to I2C0 and GPIO30/31 to I2C1 (DS table 677). Those are the controllers already used by I2C_PD and
    I2C_SYS, so a hardware-I2C swap is only possible by giving up the other bus.
  - PIO budget: PIO0 at GPIOBASE 0 hosts the hub SMBus (8/9), the PMG1 SWD probe (26/27) and Qwiic (30/31). PIO1 at
    GPIOBASE 16 hosts the Ethernet/card-reader LED counters (36–39). PIO2 stays free (user header).
- **Hub SMBus sequence**: see `usb_hub.md` (SMB_PU high, then reset, then wait 40 ms, then config, then AA56h).
- **SWD to the PMG1**: debugprobe PIO program on GPIO26/27 plus XRES on GPIO28, **only while EXT_PWR_PRESENT = 1** (see
  firmware rules).
- **Ethernet LED decoding** (link speed and activity): PIO edge counters on GPIO36–39.
- **Recovery.** If firmware hangs with HUB_SMB_PU high, the hub waits forever. Fix: hold BOOTSEL and power-cycle.

## Firmware rules (firmware spec seed)

Every firmware constraint stated in `docs/design/*.md` and `docs/review/*.md`, collected in one place. The owner is the chip
whose firmware must obey the rule. "Source" is where the rule comes from; that document holds the reasoning. A rule marked
*(pending)* depends on a review fix that is not decided yet.

### RP2350: power and the PMG1
| # | Rule | Source |
|---|---|---|
| M1 | **Never assert PMG1_XRES_N, start an SWD session to the PMG1, or enter the PMG1 I2C bootloader unless EXT_PWR_PRESENT = 1** (TCA9534 P0). Re-check it right before each step and abort if it drops. Bus-powered, the PMG1 holds LAPTOP_SNK_EN, so a reset or flash removes +5V/+3V3, browns out the RP2350 mid-flash and leaves the PMG1 bricked (recoverable only with external power). | mcu_ui review #6 |
| M2 | PMG1_XRES_N and HUB_RESET_N are open-drain emulation: drive low or set as input. Never drive them high. | mcu, usb_hub |
| M3 | Bus-powered (EXT_PWR_PRESENT = 0): keep USBA1/2_FORCE_EN off and keep the total load within the bus-power budget (power-budget.md). | usb_a open issue 4 |
| M4 | The RP2350 can only *lower* the PMG1 power budget over I2C_PD (0x42). PDO caps by input source live in PMG1 firmware. | pd_pmg1 |
| M5 | Before any PD-in renegotiation, first reduce the laptop contract and port loads (VIN bulk vs cSnkBulkPd). | power review #4 |
| M6 | PD-in with a blank TPS26750 EEPROM or before a contract (AlwaysEnableSink at 5 V): keep the deck load low until a contract exists. | power_input open issue 2 |
| M7 | *(pending, power review #2a)* If the barrel/PD-in priority moves to policy, request a PD-in contract above the barrel voltage. | power review #2 |

### RP2350: USB hub
| # | Rule | Source |
|---|---|---|
| H1 | Hub SMBus attach sequence: HUB_SMB_PU high, then HUB_RESET_N low ≥ 5 µs, release and keep HUB_SMB_PU high ≥ 1 ms (strap hold; add ~2 ms of release time if C639 becomes 100 nF), wait ≥ 40 ms (tSMBUS_RDY), write the configuration, send **USB_ATTACH_WITH_SMBUS (AA56h)**, wait tATTACH_RDY. | usb_hub, data review #9 |
| H2 | Configuration: `USB3_HUB_CTL3` XTAL_ON + BIAS_ON = 1; `HUB_NRD` = 0x52 and `USB3_HUB_NON_REM` (ports 1, 4); `BC_CONFIG_P1` = 0 (card-reader port); `BC_CONFIG_P2/P3` = BC_EN \| DCP (optionally SE1/China mode). | usb_hub |
| H3 | Raise HUB_SMB_PU only from firmware that will finish H1. A hang with it high leaves the hub waiting forever; recovery is BOOTSEL + power cycle. Drive it low (not just released) before rebooting into BOOTSEL. | usb_hub, mcu |
| H4 | All hub SMBus traffic uses the PIO I2C on GPIO8/9 with clock stretching. There are no pull-ups unless HUB_SMB_PU is high. | usb_hub, mcu |

### RP2350: Ethernet (via TCA9534)
| # | Rule | Source |
|---|---|---|
| E1 | PHY power cycle: hold ETH_RESET_N (P5) low **≥ 100 ms** (t4 ≥ 50 ms plus QOD discharge). Ignore ETH_LED0..2 while the PHY is off. | ethernet |
| E2 | Set ETH_I2C_EN (P6) only while ETH_3V3 is up. **Clear P6 before any write that drives P5 low** (otherwise I2C_SYS, and the TCA9534 itself, can lock up). | ethernet, mcu_ui review #5 |
| E3 | MAC eFuse: **program once** (flag in RP2350 flash; every rewrite consumes ~36 B of ≥ 512 B). First bench-scan the PHY slave address with the bridge on vs off and check it does not collide with 0x0C, 0x20, 0x41/0x44/0x45, 0x48–0x4F or 0x50. Sequence: P6 on, write the OTP record with the EUI-48 from the 24AA025E48 (0xFA–0xFF), P6 off, power-cycle via P5 (E1), read PLA_IDR back over USB. | ethernet, data review #5, mcu_ui review #15 |

### RP2350: I/O, sensors, UI
| # | Rule | Source |
|---|---|---|
| I1 | TCA9534 at boot: P0–P4 inputs, P5 ETH_RESET_N and P6 ETH_I2C_EN outputs, **P7 output low** (spare). Read the input port in the IOX_INT_N handler to clear INT. | mcu |
| I2 | USB-A charge mode: drop FORCE_EN when ISENSE sits at the current limit for more than about 100 ms (the TPS2553 does not latch off). | usb_a |
| I3 | TMP1075 at boot: program per-sensor THIGH/TLOW (buck-boost/5V buck 100 °C, hub/PMG1/Ethernet 95 °C, laptop-C 70 °C, LCD 60 °C, ambient 55 °C). To find the source of TEMP_ALERT_N, either read all 8 or set TM = 1 and use the SMBus Alert Response Address 0x0C. | sensors, mcu_ui review #12 |
| I4 | Thermal derating policy: lower the laptop budget, turn off charge-mode ports, power down 2.5GbE via ETH_RESET_N. Hardware backstops do not depend on it. | sensors, power_rails |
| I5 | Backlight PWM ≥ 20 kHz (GPIO25). LCD SPI: 15 MHz is guaranteed, up to 62.5 MHz by tuning. | display_ui |
| I6 | Card detect is read from TCA9534 P3/P4 (no pulls to configure). CR_LED and ETH_LEDx are inputs only. | card_reader, mcu |
| I7 | Read CHIP_ID.REVISION at boot and log it. On A2 silicon (erratum E9), drive pull-down-dependent outputs (FORCE_EN, HUB_SMB_PU, LCD_BL_PWM, LCD_RST_N, LCD_CS_N) *low* before releasing them or rebooting; do not rely on the pad pull-down. | mcu_ui review #13, data review #4 |
| I8 | If DP alt-mode entry fails, the RP2350 (hub port 6) presents the USB Billboard class. | pd_mux review #10 |
| I9 | Update flow: compare bundled image versions (PMG1, TPS26750 EEPROM, hub config) at boot and reflash as needed, observing M1 for the PMG1. TPS26750 EEPROM programming needs the TPS26750 pass-through host commands (to be confirmed). | odock-10.md, power_input open issue 3 |

### PMG1 firmware (for reference; the RP2350 firmware depends on it)
| # | Rule | Source |
|---|---|---|
| P1 | **Dead-deck boot: sink first.** Stay a sink with Rd (no DRP toggling until the contract and the TPD4S480 FETs are on), read EXT_PWR_PRESENT = 0, optionally negotiate 5 V / 3 A, then drive LAPTOP_SNK_EN high from P0.0. | pd_pmg1, pd_mux review #8 |
| P2 | Back-powering: while P3V3_SNS is low, keep MUX_* CTL/FLIP, UP_HPD, DS_HPD, LAPTOP_SRC_EN low and the I2C target inactive. | pd_pmg1 |
| P3 | **Mux CTL0 pulse:** after boot and after every detach, pulse MUX_x_CTL0 L→H→L to put the TUSB1064/TUSB1046 into power-down (they power up in USB3/no-flip). Set FLIP together with or before CTL (16 ms debounce). | usbc_muxes, pd_mux review #4 |
| P4 | **Port-0 data-role swap:** port 0 is DFP by default when sourcing; DR_Swap to UFP after the explicit contract and before the laptop's DP Discover/Enter. Non-PD hosts get power but no data while the deck is externally powered. | pd_mux review #9 |
| P5 | DP: advertise pin assignment D on port 0 (C optional). Drive UP_HPD while port 0 is in DP configuration and HPD is high; forward IRQ_HPD (follow DS_HPD). | pd_pmg1, usbc_muxes |
| P6 | Laptop source sequence: VBB_VSEL2..0, then VBB_EN; wait for VBB_PG **and ≥ 5 ms after VBB_EN** (VBB_PG is not valid during soft start) and check VBUS on the PMG1 ADC; then LAPTOP_SRC_EN. After a VSEL change wait ≥ 35 ms (or measure VBUS) before PS_RDY. | power_laptop, power review #8 |
| P7 | **VBUS discharge after a step-down:** with no laptop load, enable the PMG1 VBUS discharge or cycle VBB_EN (the 150 Ω VBB_OUT discharge runs only while VBB_EN is low). | power_laptop |
| P8 | OVP latch (LAPTOP_OVP_N low): drop LAPTOP_SRC_EN and VBB_EN (≥ 1 ms), report to the RP2350, restart only at 5.1 V. Cycle VBB_EN after any +3V3 recovery while VBB_EN was high (TLV3011 without POR), unless TLV3011B is fitted. | power_laptop, power review #14 |
| P9 | PDO caps by input: 140 W only with VIN ≥ 16 V; a 12 V barrel is limited to ≤ 100 W including the 5 V rail; keep the LM51770 input current below the ~10.6 A peak hiccup limit. | power_laptop, power review #17 |
| P10 | **Downstream port 1: advertise 3 A only with external power**, default/1.5 A when bus-powered. Configure port 1 as an Rp source as early as possible in boot. Never turn on a sink path on port 1. Forced 5 V (on RP2350 request) turns off below ~25 mA for 5 min. | pd_pmg1, pd_mux reviews #7 and #11 |
| P11 | *(pending, power review #15)* If VBB_PG drops during VSEL down-steps on the bench, blank it in firmware during steps. | power review #15 |
| P12 | Bus-powered ↔ external-power transitions: PR_Swap or a brief detach (odock-10.md open question 2). | pd_pmg1 |

## Part list (this sheet)

| Ref | Part | LCSC | Type | Stock | Qty |
|---|---|---|---|---|---|
| U1001 | RP2350B | C42415655 | ext | 3873 | 1 |
| U1002 | W25Q128JVSIQ | C97521 | basic | 49.6k | 1 |
| U1003 | TCA9534PWR | C783615 | ext | 15k | 1 |
| L1001 | AOTA-B201610S3R3-101-T 3.3 µH | C42411119 | ext | 3338 | 1 |
| Y1001 | ABM8-272-T3 12 MHz | C20625731 | ext | 13.6k | 1 |
| SW1001, SW1002 | TS-1187A-B-A-B | C318884 | basic | 474k | 2 |
| D1001 | KT-0805G green | C2297 | basic | 3.1M | 1 |
| D1002 | KT-0603R red | C2286 | basic | 4.8M | 1 |
| R1007, R1008 | 27 Ω 0402 | C25100 | ext | 57k | 2 |
| C (4.7 µF) | 4.7 µF 0402 | C23733 | basic | — | 5 |
| C (100 nF) | 100 nF 0402 | C1525 | basic | — | 17 |
| C1006 | 10 µF 0603 | C19702 | basic | — | 1 |
| C1020, C1021 | 15 pF C0G 0402 | C1548 | basic | — | 2 |
| C1024, C1025 | 10 nF 0402 | C15195 | basic | — | 2 |
| R | 10/33/330/1k/2.2k/4.7k/10k 0402 | C25077/C25105/C25104/C11702/C25879/C25900/C25744 | basic | — | 27 |
| R1004 | 10k (DNP) | C25744 | basic | — | 1 |
| J1001, TP1001–TP1004 | header and pads | — | not in BOM | — | — |

`tools/bom_check.py`: all OK.

## Nets
- Global nets used:
  - Rails and power status: `+3V3`, `+1V1`, `GND`, `EXT_PWR_PRESENT`, `PDIN_PRESENT`, `LAPTOP_OVP_N`.
  - Buses and IRQs: `I2C_SYS_*`, `I2C_PD_*`, `I2C_PD_INT_N`, `PDIN_INT_N`, `I2C_EXT_*`.
  - Hub: `HUB_SMB_CLK/DAT`, `HUB_SMB_PU`, `HUB_RESET_N`, `MCU_USB_DP/DN`.
  - PMG1 debug: `PMG1_SWDIO/SWCLK/XRES_N`.
  - Display and UI: `LCD_*`, `BTN_A_N/BTN_B_N`, `HDR_GPIO0..7`, `HDR_ADC0/1`.
  - USB-A: `USBA1/2_FORCE_EN`, `USBA1/2_ISENSE`.
  - Ethernet, card reader, sensors: `NTC_ADC0/1`, `ETH_LED0..2`, `ETH_RESET_N`, `CR_CD_SD_N`, `CR_CD_USD_N`, `CR_LED`,
    `TEMP_ALERT_N`.
- **No new inter-sheet nets are needed.**

## Requirements on other sheets
1. **sensors**: put only the NTCs (NCP18XH103, 10k B3380) from NTC_ADC0/1 to GND. The bias and filter are here. Do not add a
   TEMP_ALERT_N pull-up; R1016 is the only one.
2. **usb_a** (done): the INA180A2s (U703, U706) run from +3V3 with 1k/100 nF, and FORCE_EN has 100k pull-downs (R702/R707).
3. **ethernet**: ETH_RESET_N has its pull-up here, so do not add another. ETH_I2C_EN (P6) has its only pull-down there
   (R820, 100k); there is none here. Any LED pin that is also a strap needs a ≤ 10k strap resistor.
4. **card_reader**: CR_CD_SD_N/CR_CD_USD_N tap the GL3224 card-detect nodes through 1k (GL3224 internal pull-up) and land
   on TCA9534 P3/P4, which has no pulls. CR_LED must be ≤ 3.6 V.
5. **pd_pmg1**: GPIO26/27 now reach PMG1_SWCLK/SWDIO through 1k (R1026/R1027) on this sheet; nothing to change there.

## Open issues
1. The expander adds I2C latency for the power-status display (≤ 1 ms, interrupt-driven), which is not safety relevant. If
   layout frees pins, move EXT_PWR_PRESENT back to a native GPIO.
2. The spare expander pin P7 could take a CCPROT fault flag (usbc_muxes) or USBA1_OCS_N (data review #11) if one is
   promoted to a global net. Then remove or keep R1028 according to the signal's own pull.
3. The crystal and regulator footprints are LCSC imports. Check them against the RPi minimal-board KiCad files. **Copy the
   RPi regulator placement** (C6/C7/L1 geometry). Inductor dot on the +1V1 pad (pad 2); check the JLC CPL rotation.
4. The QFN-80 EP land pattern (3.4 mm EP) and paste windows need checking against the DS package drawing.
5. The 16 MB flash holds the RP2350 firmware plus component images. Check the image budget once the PMG1 image size is known
   (CYPM1321 flash 128 KB, so it is not a concern).
6. RP2350 stepping of the JLC stock is unconfirmed (erratum E9, A2 only). Check on the first articles.
7. The RTL8156BG I2C-slave address is unknown and appears on I2C_SYS while ETH_I2C_EN is high. Bench-scan it before the
   eFuse write (firmware rule E3).
