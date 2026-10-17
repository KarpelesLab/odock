# odock-10 — USB hub sheet (`usb_hub.kicad_sch`, refs 600+)

Source: `hardware/odock-10/sheets/usb_hub.py` (generated, netlist-verified). References:
- USB7206C datasheet DS00003850F (cited as "DS").
- AN2935 rev C, *Configuration of USB7206/USB7206C/…*.
- USB7206 Hardware Design Checklist DS00003336A. The USB7206C checklist PDF is blocked behind a 403. The USB7206 and
  USB7206C share pinout and strap tables.

Stock figures are from the JLC parts API on 2026-10-02.

## Block

```
LAPTOP_USB_DP/DN ─────────────────────────────── USB2UP (89/90)
HUB_UP_SS_TXP/N ◄── 220 nF ── USB3UP_TX (91/92)        USB7206C          P1 ─► CR_*      (GL3224)
HUB_UP_SS_RXP/N ───────────► USB3UP_RX (94/95)        U601              P2 ─► USBA1_*   (USB-A #1)
VBUS_LAPTOP ─ 47k/68k + BAT54WS ─ 74LVC1G17 ─ 15k/49.9k ─► VBUS_DET (PF30) P3 ─► USBA2_*   (USB-A #2)
HUB_RESET_N ─┬─ 10k↑ + 1 nF ─► RESET_N            25 MHz Y601            P4 ─► ETH_*     (RTL8156BG)
RAILS_PG ◄───┘ D601 (BAT54WS, wire-OR)            RBIAS 12k 1 %          P5 ─► HUB_DSC_* (TUSB1046)
HUB_SMB_CLK/DAT ─ 10k ─ HUB_SMB_PU (RP2350 GPIO) ─ 4.7k ─ GND          P6 ─► MCU_USB_DP/DN (RP2350, USB2)
USBA1_PWR_EN ═ PRT_CTL2 ═ (0R R630) ═ USBA1_OCS_N;  USBA2_PWR_EN ═ PRT_CTL3 ═ (0R R631) ═ USBA2_OCS_N
```

Every downstream SS TX goes through 220 nF before it reaches its global net.

## Part choice
- **USB7206CT/KDX (C3210691)**: 21 in stock, $14.56, commercial grade (0–70 °C).
  - Industrial alternative: USB7206C-I/KDX (C3210686), 5 in stock, $15.52. The pinout is identical, so only the LCSC
    field changes.
  - Board quantity is 1, so both pass the ≥ 5 rule. **Stock is thin, so order early.**
- The symbol and footprint were imported from LCSC. **The pin numbers and names match DS fig. 3-1 and the pin table on
  page 9** (8× VDD33: 26/43/53/62/67/79/88/99; 9× VCORE: 9/18/25/31/38/55/78/85/93; EP = VSS = pin 101).
  - Pin types are fixed with fix_pins.
  - Check the footprint (VQFN-100 12×12, 0.4 mm pitch, EP 8.0 mm) against the DS land pattern before layout.

## Port map (logical = physical on USB7206C, DS table 3-7)

The chip is oriented with its upstream side (pins 76–100) toward the back edge, where the laptop C and TUSB1064 sit.
The other sides then face as follows: left side (pins 1–25) faces left, bottom side (pins 26–50) faces the front, and the
PF/SPI side (pins 51–75) faces right.

| Hub port | Pins (D+/D-, TX±, RX±) | Chip side | Function | Nets | Notes |
|---|---|---|---|---|---|
| UP | 89/90, 91/92, 94/95 | top, center | Laptop via TUSB1064 | LAPTOP_USB_*, HUB_UP_SS_* | TUSB1064 is back-center |
| P1 | 5/6, 7/8, 10/11 | left, upper | GL3224 card reader | CR_* | Outermost left route to the front-left zone. Non-removable (strap) |
| P2 | 14/15, 16/17, 19/20 | left, lower | USB-A #1 (left) | USBA1_* | Exits the bottom-left corner to the front-center. BC1.2, PRT_CTL2 |
| P3 | 27/28, 29/30, 32/33 | bottom, left | USB-A #2 (right) | USBA2_* | Runs straight to the front. BC1.2, PRT_CTL3 |
| P4 | 34/35, 36/37, 39/40 | bottom, right | RTL8156BG | ETH_* | Routes right and then back along the quiet PF side to the back-right corner. Longest SS run, so check its length |
| P5 | 81/82, 83/84, 86/87 | top, right | TUSB1046 → downstream C | HUB_DSC_* | TUSB1046 is back, right of TUSB1064 |
| P6 | 42/41 (USB2 only) | bottom-right corner | RP2350 | MCU_USB_DP/DN | USB2 only, so it can take an inner layer to reach the MCU on the left |

The SS lanes do not cross each other. The only crossing is the P6 USB2 pair, which is tolerant of a layer change.

If layout changes this map, the hub can remap ports (USB2 `HUB_PRT_REMAP_*` 30FB–30FEh, USB3 `USB3_PRT_REMAP*`
3858–3862h) and swap D+/D- (`HUB_PRT_SWAP` 30FAh). These settings need SMBus or OTP, so the strap defaults would then
apply to physical ports.

## AC coupling (assumption shared with usbc_muxes, card_reader, ethernet, usb_a)
- **Every hub SS TX (upstream plus five downstream) has a 220 nF 0402 X7R series cap on this sheet** (C601–C612).
  - USB 3.2 requires 75–265 nF at the transmitter.
  - The global `*_SS_TX*` nets are therefore already AC-coupled.
- **Hub RX pairs have no caps here.** Each link partner provides caps on its own TX:
  - TUSB1064: on the usbc_muxes sheet.
  - TUSB1046: its hub-facing output, on the usbc_muxes sheet.
  - GL3224: on the card_reader sheet.
  - RTL8156BG: on the ethernet sheet.
  - USB-A: the plugged device's own caps.
- Layout:
  - Place the caps within about 5 mm of the hub, keep each pair symmetric, and void L2 under the cap pads.
  - 0201 would be better for 10G, but no basic-part 0201 220 nF was chosen. 0402 with a pad void is fine.

## Straps and configuration

Straps latch at POR and on the RESET_N rising edge, and need ≥ 1 ms hold.

| Pin | Strap | Resistor | Setting |
|---|---|---|---|
| 21 CFG_STRAP1 | mode | 10k PD | Configuration 3, **the only valid mode on the USB7206C**. PF26/27 = SMBus slave, PF15/16 = PRT_CTL3/2, PF30 = VBUS_DET |
| 22 CFG_STRAP2 | mode | 200k PD | Configuration 3 |
| 23 CFG_STRAP3 | — | 200k PD | Required |
| 69 SPI_CE_N / CFG_NON_REM | non-removable | 200k PU | Port 1 (GL3224) non-removable. Also acts as the flash CE# pull-up |
| 70 SPI_D0 / CFG_BC_EN | battery charging | 10k PU | BC1.2 DCP + CDP on ports 1–3. Ports 2 and 3 are the USB-A ports; port 1 is harmless, see below |
| 5/6, 14/15, … | PRT_DIS_Px/Mx | none | All ports enabled. Do not pull the D+/D- lines high |
| 63–65 TEST1–3 | — | 10k PU | Mandatory |
| 24 TESTEN | — | GND | |
| 96 ATEST | — | NC | |
| 68 SPI_CLK | — | 100k PD | Must be low during reset |
| 71–73 SPI_D1–D3 | — | 100k PD | D3 = flash HOLD#. If the flash is fitted, fit R614 (10k PU) and remove R613 |
| PF3–7, PF18, PF19, PF31, PF29 | unused | 100k PD | DS table 3-6 "weak pull-down" |
| PF8/9, PF10–12 (PRT_CTLx_U3), PRT_CTL1/4/5/6 | unused | NC | Float |

**CFG_STRAP and SMBus check, verified.**
- DS §5.1.4 says "Configuration 1 → SMBUS_CHECK", and AN2935 says "CONFIG1 for USB7206C". That text is copied from the
  USB7252C/USB7202 datasheets, where Config 1 is the mode that carries SLV_I2C pins.
- On the USB7206/USB7206C, DS table 3-4 and checklist §4 both state that **Configuration 3 (STRAP2 200k PD, STRAP1 10k PD)
  is the only valid configuration**, and that it carries SLV_I2C on PF26/PF27.
- Checklist §10.2.1 then says: "Pull-up resistors must be detected by the hub at start-up in order for the I2C/SMBus
  interface to become active … If pull-ups are detected … the hub waits indefinitely".
- Conclusion: in Config 3, the SMBus check runs and is decided purely by the pull-ups.
- Residual risk: confirm on the first board (see open issues).

## SMBus boot behavior (RP2350 alive vs not)
- Hub address: 7-bit **0x2D** (write 5Ah, read 5Bh).
- Register access uses command **9937h** with a buffer of {dir, len, 32-bit address, data} (AN2935 §3).
- The hub's SMBus pull-ups (10k each, R627/R628 on this sheet) are fed from **HUB_SMB_PU, an RP2350 GPIO**. R629 (**4.7k**)
  pulls HUB_SMB_PU to GND, and the RP2350's default pad pull-down helps too.
  - 4.7k rather than 100k because of **RP2350 erratum E9** (DS App. D.5.1, stepping A2; fixed in A3/A4): a pad that was
    driven high and then reverts to input (watchdog reset, reboot to BOOTSEL) can latch at about 2.2 V, and only a pull
    of ≤ 8.2 kΩ overcomes it. At 2.2 V the hub could see pull-ups at its next reset and wait forever, with no USB and no
    BOOTSEL. The GPIO drives 3.3 V / 4.7k ≈ 0.7 mA into R629, plus 2 × 10k into the bus lines when they are low (about
    1.4 mA worst case). That is well within the default 4 mA drive, with a negligible VOH drop. The stepping of the JLC
    RP2350 stock (C42415655) is unknown, so the stronger pull-down stays regardless.
  - **There must be no other pull-ups on HUB_SMB_CLK/DAT** (mcu sheet).

| RP2350 state | HUB_SMB_PU | Hub sees at SMBUS_CHECK | Hub behavior |
|---|---|---|---|
| Running our firmware | driven high (3.3 V) | 10k pull-ups on both pins | Enters CFG_SMBUS and waits indefinitely. RP2350 writes its config, then sends **USB_ATTACH_WITH_SMBUS (AA56h)** so the SMBus stays alive at runtime |
| BOOTSEL / unpowered / broken firmware (GPIO input + default pull-down) | ~0 V (R629) | No pull-up (lines low) | Goes straight to CFG_OTP, then USB_ATTACH, using **ROM + strap defaults**. All six ports work, BC1.2 is on ports 1–3, and the **RP2350 BOOTSEL UF2 device enumerates on port 6** |
| Firmware hangs after raising HUB_SMB_PU | high | pull-ups | Hub waits forever, so there is no USB. Recovery: power cycle while holding BOOTSEL (the GPIO then stays low) |

Firmware sequence:
1. Drive HUB_SMB_PU high.
2. Drive HUB_RESET_N low for ≥ 5 µs (open-drain: output-low or input).
3. Release HUB_RESET_N, then keep HUB_SMB_PU high for ≥ 1 ms (strap hold).
4. Wait **≥ 40 ms** (tSMBUS_RDY). The hub clock-stretches before then.
5. Write the configuration registers:
   - `USB3_HUB_CTL3` (BF80_3842h) bit 0 `USB3_XTAL_ON` = 1 and bit 1 `USB3_BIAS_ON` = 1, so the clocks stay on and the
     SMBus stays readable while the host suspends the hub (DS §9.6.5 note).
   - Non-removable bitmap:
     - USB2: `HUB_NRD` (BF80_3009h) = 0x52 (physical ports 1, 4, 6).
     - USB3: `USB3_HUB_NON_REM` (BFD2_E5D2h). Encoding per AN2935, physical ports 1 and 4.
   - BC1.2: `BC_CONFIG_P1` (BFD2_3433h) = 0, which turns BC off on the card-reader port. `BC_CONFIG_P2/P3`
     (3434h/3435h) = BC_EN | DCP, optionally plus SE1 or China mode for Apple/Samsung profiles.
   - Optional TX de-emphasis tuning: `SS_Px_PIPE_TX_DEEMPH_GEN2` at 62B8h (upstream) and 66B8h/6AB8h/6EB8h/72B8h/76B8h
     (P1–P5).
   - Optional strings, VID/PID and serial.
6. Send AA56h.
7. Wait tATTACH_RDY before the next SMBus access.

## Per-port speed readout (AN2935, base BF80_0000h, all runtime-readable after AA56h)

| Register | Offset | Content |
|---|---|---|
| USB30_HUB_STAT | 3851h | Bit 0 = USB3 host on upstream. Bits 1–6 = USB3 device connected on DS port n (**0 = connected**) |
| USB30_HUB_DN_SPEED_IND1 | 3852h | 2 bits per port. Bits 1:0 = P1, 3:2 = P2, 5:4 = P3, 7:6 = P4. 01 = 5G, 10 = 10G, 11 = 20G, else none |
| USB30_HUB_DN_SPEED_IND2 | 3853h | Bits 1:0 = P5 |
| USB2_DN_SPEED41 / 75 | 3195h / 3196h | 2 bits per port. 00 = none, 01 = LS, 10 = FS, 11 = HS (P1–P4, then P5–P7) |
| PORT_STAT_REG_0..6 | 3C50h–3C68h | Per-port status (upstream = 0) |
| PORT_PWR_STAT | 30E5h | Port power state |
| BC_EN | 30D0h | Bits 6:1 = BC active per port |
| USB30_SUSP_IND / USB2_SUSP_IND | 3857h / 3197h | Suspend state |

The upstream link speed (Gen1 vs Gen2) has no direct field. Show 10G if any downstream port runs at 10G, or infer it from
`PHY_STATE1/2` (3870h/3874h).

Physical port to function, for the LCD: P1 card reader, P2 USB-A #1, P3 USB-A #2, P4 Ethernet, P5 downstream C, P6 MCU.

## BC1.2 / charging
- The CFG_BC_EN strap (10k PU) enables BC1.2 on ports 1–3 with no firmware involved. Behavior depends on VBUS_DET:
  - **VBUS_DET = 0 (no laptop):** the ports act as **DCP** (D+/D- shorted).
  - **VBUS_DET = 1:** the ports act as **CDP** once the host powers the port. CDP allows 1.5 A during enumeration.
- Port 1 (GL3224) also gets BC.
  - It is harmless: the GL3224 never runs BC detection, and in DCP mode there is no host anyway.
  - The RP2350 clears it when alive (`BC_CONFIG_P1` = 0).
- SE1 (Apple 1/2/2.5 A) and China mode are only available via SMBus/OTP (`BC_CONFIG_Px` bits 4 and 2:1). Firmware option.
- **VBUS_DET source** (reworked after review data #2). The old 47k/47k + clamp drove PF30 to 3.57–3.63 V whenever the
  deck sourced 9–28 V, which is above the checklist's 2.7 V and at the 3.6 V operating limit. No pure divider can map
  both 4.4 V → ≥ 2.1 V and 28 V → ≤ 2.7 V, so a buffer was added:
  - Path: VBUS_LAPTOP → R625 47k / R626 68k → `HUB_VBUS_SNS`, with D602 BAT54WS clamping it to +3V3. The node then
    feeds U603 74LVC1G17 (Schmitt buffer on +3V3, 5.5 V-tolerant input, Ioff). Its output `HUB_VBUS_BUF` goes through
    R632 15k / R633 49.9k to PF30.
  - Sense-node levels:

    | Laptop VBUS | Sense node | Threshold |
    |---|---|---|
    | 4.4 V | 2.60 V | above VT+ max ≈ 2.0 V |
    | 0.8 V (vSafe0V) | 0.47 V | below VT− min ≈ 0.8 V |
    | 28 V | clamped at about 3.6 V | fine for the LVC input |

    At 28 V the clamp injects ≤ 0.47 mA into +3V3, and R625 dissipates 13 mW.
  - PF30 high = +3V3 × 0.769, which is 2.46–2.64 V for +3V3 = 3.20–3.43 V. That satisfies ≤ 2.7 V (checklist §5.1) and
    > VIH 2.1 V. The checklist's Fig. 5-2 values (11k/49.9k) would give 2.73 V at our 3.33 V rail, so the top resistor is
    15k. PF30 low = buffer VOL, about 0 V.
  - The buffer runs from +3V3, the same rail as VDD33, so VBUS_DET can never rise before VDD33.
  - VBUS on the laptop port is present only while a laptop is attached, whether the deck is sinking from it or sourcing to
    it, so VBUS present ≈ host attached. Toggling VBUS also soft-resets the hub (checklist §6.1).
  - **Limitation (review data #6):** VBUS present does not guarantee a USB host. A powered-off or sleeping laptop, or
    a charge-only cable, also gives VBUS. The hub then leaves DCP and waits as CDP, and the USB-A ports get neither
    VBUS nor a DCP signature. FORCE_EN restores VBUS only.
    - Hardware fix, not done here: replace U603 with a 74LVC1G08 whose second input is a firmware "data link
      expected" gate. That needs a new inter-sheet net to a spare PMG1 or RP2350 pin, which this sheet does not own.
- Charging current comes from the TPS2553 switches on the usb_a sheet. DCP still needs port VBUS.
  - The hub may keep PRT_CTL low while unenumerated (unverified).
  - The RP2350 FORCE_EN path on usb_a covers that case.

## Port power / overcurrent
- **PRT_CTLx is a single combined pin** (DS §8.2):
  - Port on: it is an input with an internal ~50k pull-up, so it acts as an open-drain "enable".
  - A low level from the switch FAULT# is an overcurrent. The hub then latches the port off and drives the pin low.
- So `USBAx_PWR_EN` and `USBAx_OCS_N` are **the same node**. They are joined by 0 Ω R630/R631, which lets the nets be
  separated if usb_a needs it.
- Notes for the usb_a sheet:
  - Feed the TPS2553 EN from (PWR_EN OR FORCE_EN) through a high-impedance gate input.
  - Connect FAULT# (open-drain) to OCS_N.
  - **Do not add an external pull-up** (checklist §6.2).
  - With the RP2350 forcing power while the hub holds the port off, a FAULT# only pulls an already-low node low, so
    nothing conflicts.
- Embedded ports (1, 4, 5, 6): PRT_CTL floats, and the internal pull-up means it never reports overcurrent.
  - The downstream C VBUS is controlled by PMG1, not the hub.

## Reset
- `RESET_N` is driven by three things:
  - The 10k pull-up to +3V3 with a 1 nF filter.
  - `HUB_RESET_N` from the RP2350, open-drain.
  - `RAILS_PG` from the TPS62933P PG, open-drain with 100k on power_rails, through **D601 BAT54WS**: anode on
    HUB_RESET_N, cathode on RAILS_PG.
- Result:
  - The hub stays in standby until +1V15 is in regulation, which implies +3V3 is up. That satisfies "VCORE **after** or with
    VDD33, RESET_N after VDD33" (DS §9.6.1). +1V15 is enabled from +3V3, so VCORE cannot lead.
  - When the RP2350 resets the hub, RAILS_PG is not loaded, so other RAILS_PG users still read a true power-good.
  - Low level with PG asserted: ≈ 0.25 V + VOL, below VIL 0.9 V.
  - The RP2350 default pad pull-down (~50k) against the 10k pull-up gives about 2.75 V, above VIH 2.1 V. In BOOTSEL the hub
    therefore runs.

## Clock
- Y601 YXC X322525MOB4SI (C9006, basic): 25 MHz 3225, CL 12 pF, ±10 ppm tolerance, ±20 ppm stability, ESR 50 Ω. The hub
  needs ±50 ppm.
- C637/C638 are 20 pF C0G: (20 + 2 pF stray) / 2 = 11 pF ≈ CL. Trim on the bench if the ppm error shows up.

## Power / thermal
- VCORE (+1V15): up to 410 mA + 5 × 179 mA ≈ **1.31 A** with all ports at 10G.
- VDD33: ≈ 31 + 5 × 11 + 11 ≈ 0.1 A.
- Total ≈ **1.8 W**. Suspend draws 14 mW, reset 5 mW.
- Package θJA is 19 °C/W on 2S2P, which gives about +35 K. θJB is 9 °C/W, so heat leaves mainly through the EP via array
  into the L2/L5 GND planes.
  - Put the hub near the TMP1075 "USB7206C" sensor (sensors sheet).
  - The commercial part is rated 0–70 °C ambient and Tj ≤ 125 °C.
- Decoupling:
  - Per pin: 100 nF on each of 8× VDD33 and 9× VCORE.
  - Bulk: 2× 4.7 µF + 1 nF on VDD33, 3× 4.7 µF + 1 nF on VCORE.
  - The +1V15 rail bulk (4× 22 µF) is at the regulator.

## Optional SPI flash (DNP)
- U602 SST26VF016B-104I/SN (C631790, 145 in stock, $2.33) is a Microchip-verified part (checklist §9.2).
  - It is wired for quad mode with a 100 nF cap (C640, DNP).
- The hub boots from flash only if the flash holds an image with the "2DFU" signature at 0x3FFFA. A blank flash means ROM
  boot. Images come only from Microchip, so it is **not planned**; this is a footprint only.
- The CE#/D0 straps stay when the flash is fitted.

## Part list (this sheet)

| Ref | Part | LCSC | Type | Stock | Qty |
|---|---|---|---|---|---|
| U601 | USB7206CT/KDX | C3210691 | ext | 21 | 1 |
| U602 | SST26VF016B-104I/SN (DNP) | C631790 | ext | 145 | 1 |
| Y601 | X322525MOB4SI 25 MHz | C9006 | basic | 199k | 1 |
| D601, D602 | BAT54WS-7-F | C124205 | ext | 65k | 2 |
| U603 | 74LVC1G17W5-7 (Diodes) SOT-25, VBUS_DET buffer | C151394 | ext | 10.8k | 1 |
| C641 | 100 nF 0402 (U603) | C1525 | basic | — | 1 |
| R629 | 4.7k 0402 (HUB_SMB_PU pull-down, E9) | C25900 | basic | — | 1 |
| R626 | 68k 1 % 0603 | C23231 | basic | 1.0M | 1 |
| R632, R633 | 15k 0402 (C25756, basic) / 49.9k 1 % 0603 (C23184, basic) | | | | 2 |
| C601–C612 | 220 nF 16 V X7R 0402 | C16772 | basic | 2.3M | 12 |
| C613–C620, C624–C632, C640 | 100 nF 0402 | C1525 | basic | 21M | 18 |
| 4.7 µF caps | 4.7 µF 10 V X5R 0402 | C23733 | basic | 2.3M | 5 |
| 1 nF caps | 1 nF 0402 | C1523 | basic | 3.3M | 3 |
| C637, C638 | 20 pF C0G 0402 | C1554 | basic | 657k | 2 |
| R (12k) | 12k 1 % 0402 (RBIAS) | C25752 | basic | 1.1M | 1 |
| R (10k) | 10k 0402 | C25744 | basic | 21M | 9 |
| R (100k) | 100k 0402 | C25741 | basic | 8M | 13 |
| R (200k) | 200k 0402 | C25764 | basic | 2.3M | 3 |
| R625 | 47k 0402 | C25792 | basic | 5.5M | 1 |
| R630, R631 | 0 Ω 0402 | C17168 | basic | 9M | 2 |

`tools/bom_check.py`: all OK.

## Nets
- Global nets used:
  - Rails: `+3V3`, `+1V15`, `GND`.
  - Upstream: `LAPTOP_USB_DP/DN`, `HUB_UP_SS_TXP/TXN/RXP/RXN`.
  - Downstream: `HUB_DSC_*`, `USBA1_*`, `USBA2_*`, `CR_*`, `ETH_*`, `MCU_USB_DP/DN`.
  - Port power: `USBA1/2_PWR_EN`, `USBA1/2_OCS_N`.
  - Control: `HUB_SMB_CLK/DAT`, `HUB_SMB_PU`, `HUB_RESET_N`, `RAILS_PG`, **`VBUS_LAPTOP`** (VBUS_DET sense).
- No new inter-sheet nets are needed.

## Open issues
1. **Confirm the SMBus boot stage on hardware.** Text in DS/AN2935 says "Config 1" while the 7206C only has Config 3.
   - Bring-up test: with HUB_SMB_PU high, the hub must not enumerate until AA56h.
   - Fallback if it never waits: runtime SMBus may still work for status reads. Check that too.
2. **USB7206C stock (21/5)** is the hard constraint. Buy as soon as the BOM freezes.
3. Does the hub drive PRT_CTL high (port power on) for DCP when VBUS_DET = 0, or only after host enumeration? This decides
   whether no-laptop DCP charging needs the RP2350 FORCE_EN. Verify on the bench.
4. The P4 → RTL8156BG route is the longest SS run (it goes around the hub's PF side). Check its length and loss in
   placement, and tune `SS_P4_PIPE_TX_DEEMPH_GEN2` if needed.
5. usbc_muxes must put AC caps on the TUSB1064 TX → hub RX and on the TUSB1046 hub-facing TX. card_reader and ethernet
   put caps on their device TX.
6. The mcu sheet must not add pull-ups on HUB_SMB_CLK/DAT. HUB_SMB_PU needs a push-pull GPIO. HUB_RESET_N needs open-drain
   emulation.
7. Footprint check: the easyeda VQFN-100 land pattern and EP paste pattern against DS §10. The EP needs a via array
   (about 6×6, 0.3 mm vias, tented or filled).
8. TUSB1046/PMG1 port 5: the hub doesn't control port power for the downstream C. PMG1 owns VBUS. The hub's PRT_CTL5 is
   left unused.
9. **Bench items (review data):**
   - **#8 PRT_DIS straps.** The PRT_DIS_Px straps sample the D+ pull-ups of embedded devices that are already
     powered. With everything enumerated, reset the hub over HUB_RESET_N and confirm that ports 1, 4 and 6 come back.
   - **#9 Clock before RESET_N.** RESET_N rises about 70 µs after +1V15 is good. If the hub misbehaves on cold start,
     change C639 1 nF to 100 nF (τ ≈ 1 ms). The firmware strap-hold wait then has to grow by about 2 ms.
   - **#10 BC on port 1.** BC1.2 on port 1 (GL3224) is harmless, and the RP2350 clears it. If layout allows, swap the
     port map (USB-A on ports 1/2) with the 10k PD CFG_BC_EN strap.
   - **E9 check.** Read the RP2350 stepping on the first boards. With A3/A4, R629 could go back to a weaker value, but
     it does not need to.
