# odock-10 — data-path sheet review (usb_hub, usb_a, card_reader, ethernet)

Reviewer: independent pre-layout review, 2026-10-02. Scope: `hardware/odock-10/sheets/usb_hub.py`, `usb_a.py`,
`card_reader.py`, `ethernet.py`, plus the nets they share with `mcu.py`, `usbc_muxes.py` and `power_rails.py`.

Method:
- Exported the full-project netlist with `kicad-cli sch export netlist` from the generated `.kicad_sch`.
- Checked every pin→net of U601 (USB7206C), U801 (RTL8156BG), U901 (GL3224), U701–U706, U802–U805, J701/J702, J801,
  J901/J902 against the datasheets:
  - USB7206C DS00003850F, USB7206 Hardware Design Checklist DS00003336A, AN2935 rev C.
  - GL3224 DS rev 1.11 (QFN-48), RTL8156BG(S) DS rev 1.1.
  - TPS2553 (Rev F), TPS22918 (Rev C), TPS62A0x (Rev E), INA180 (Rev H), 24AA025E48, TCA9534.
  - Hanbo SD-111 drawing, Hirose DM3 catalog, USAKRO DGUK211Q340CD2A4D2 drawing, RP2350 datasheet (errata).

## Findings

No BLOCKERs. Two MAJORs.

| # | Sev | Sheet | Refs / nets | Finding and evidence | Fix |
|---|---|---|---|---|---|
| 1 | **MAJOR** | card_reader | U901 pin 35 `MS2_INS/SD2_WP` = **GND** | **The pin is tied low, so slot 2 permanently reports "Memory Stick inserted".** GL3224 DS Table 3.1: MS2_INS/SD2_WP is a shared pin. As MS insertion detect, "0: Card insert, 1: No card". The sheet treats it only as SD WP ("tie low = write enabled"). With no microSD present, SD2_CDZ = 1 and MS2_INS = 0, which is the state of an MS card in slot 2. The ROM will then try MS init on the S2 pins and likely switch S2M2_VCC on into an empty socket. LUN 2 will never report "no media", or will report a media error. With a card inserted (CDZ = 0, pin = 0), it is the same state as an unlocked SD in slot 1, so it probably works. Leaving the pin on its internal pull-up is no better: that reports every microSD as write-protected. | **Tie pin 35 to `CR_USD_CDZ`** (the DM3AT detect-switch node) instead of GND. No card: high, so no MS and no WP. Card present: low, so write-enabled. This is the same state slot 1 has with an unlocked SD in the SD-111 (WP switch closes to GND only with a card present). The two internal 46k pull-ups in parallel are fine. |
| 2 | **MAJOR** | usb_hub | R625/R626 47k/47k, D602 BAT54WS → U601 pin 2 `HUB_VBUS_DET` | **VBUS_DET goes far above the checklist limit when the deck sources 9–28 V to the laptop.** `VBUS_LAPTOP` is a 5–28 V source in that case. The divider gives VBUS/2 and the Schottky clamps at +3V3 + Vf: 3.33 V + 0.24–0.30 V (BAT54 at about 0.45 mA, cold) = **3.57–3.63 V**. Limits: checklist §5.1 says "the voltage of the signal must be reduced to 2.7 V for input to the USB7206". DS §9.2 gives an input-pin operating range of −0.3 to **+3.6 V**. The design note checked only 5.25 V. At 4.4 V the margin is only 2.2 V against VIH 2.1 V (DS Table 9-3). No pure divider can meet both 4.4 V → ≥ 2.1 V and 28 V → ≤ 2.7 V. | Insert a buffer. Keep R625/R626 + D602, but feed that node into a 74LVC1G17 (or similar) on +3V3, which is 5.5 V tolerant, so 3.6 V is fine. Drive U601 pin 2 from the buffer output through 11k/49.9k (Microchip checklist Fig. 5-2), which gives about 2.7 V. Optional: OR in an override from PMG1/RP2350 (see #6). |
| 3 | MINOR | ethernet | C835/C836 220 nF (`ETH_TXP/N_IC` → `ETH_SS_RXP/N`) | **The RTL8156BG is a Gen1 (5 Gbps) transmitter** (DS §6.1, "USB 3.2 Gen1"). The USB 3.0 Gen1 C_AC_COUPLING range is 75–200 nF (USB 3.0 Table 6-10). The project's own card_reader sheet applies this rule and uses 100 nF for the GL3224 TX. 220 nF is out of range or marginal for a Gen1 TX and inconsistent between sheets. The hub-side 220 nF is fine, because the USB7206C is a Gen2 TX (75–265 nF). | Change C835/C836 to **100 nF 0402** (C1525, the same part as the card reader). |
| 4 | MINOR | usb_hub / usb_a / mcu | R629 100k (`HUB_SMB_PU`), R702/R707 100k (`USBAx_FORCE_EN`), RP2350 GPIO10/34/35 | **Erratum RP2350-E9** (RP2350 DS App. D.5.1, affects stepping **A2**, fixed in A3/A4). Once the pad has been driven high and then reverts to input (watchdog/firmware reset, reboot to BOOTSEL), it can latch at about 2.2 V. Only a pull of ≤ 8.2 kΩ overcomes the leakage, and 100k does not. Effects: (a) `HUB_SMB_PU` at about 2.2 V can make the hub see pull-ups at its next reset, so it waits forever with no USB, including no BOOTSEL. (b) `USBAx_FORCE_EN` at 2.2 V exceeds the LVC1G32 VIH (2.0 V), so ports can be forced on after a crash. | Confirm that JLC stock for C42415655 is stepping A3/A4 and record it in mcu.md. If it is A2, or unknown, change R629, R702 and R707 to **4.7k**. That is 0.7 mA from a push-pull GPIO, which is fine. |
| 5 | MINOR | ethernet | Q801 bridge, `ETH_I2C_EN`, `ETH_SDA/SCL`; I2C_SYS devices 0x20, 0x41/0x44/0x45, 0x48–0x4F, 0x50 | **The MAC-programming path is plausible but rests on three unverified assumptions.** (a) RTL DS §6.6/Fig. 4 only says "MACID can be modified via the I2C function … 'OTP code'". It does not say the write persists in eFuse, does not say the slave is active on a blank eFuse, and gives no 7-bit address. If the write is volatile, the MAC would have to be rewritten after every PHY power-up, before the host driver binds (a race with enumeration). (b) An unknown address could collide with an I2C_SYS device while the bridge is on. (c) The 2N7002DW has VGS(th) up to 2.5 V with a 3.3 V gate, so on-resistance is high but adequate for 4.7k pull-ups. The host-tool and OS-override fallbacks keep this from blocking anything. | Bench-test it on the first board before relying on it. Firmware: scan with the bridge on vs off to find the address and check for a collision. Write the OTP record once, power-cycle with ETH_RESET_N, and read PLA_IDR back over USB. Optional: use a BSS138-class FET (VGS(th) ≤ 1.5 V) for Q801. |
| 6 | MINOR | usb_hub | `HUB_VBUS_DET` semantics, CFG_BC_EN | **VBUS present on the laptop port does not mean a USB host is present.** VBUS is also present when the deck charges a laptop that is powered off or asleep, or over a charge-only cable. The hub then leaves DCP (DS Table 3-3: BC1.2 DCP/CDP; DCP only when VBUS_DET = 0, usb_hub.md) and waits as CDP for a host to power the ports. The USB-A ports then get neither VBUS (PRT_CTL low) nor a DCP signature. FORCE_EN restores VBUS only. | With the #2 buffer, add a gate input (for example a spare PMG1 GPIO for "data link expected", or an RP2350/TCA9534 override with a default pass-through) so firmware can hold VBUS_DET low when no host is enumerating. If not, document the limitation next to usb_hub open issue 3. |
| 7 | MINOR | card_reader / mcu | `MS1_INS/SD1_WP`, `CR_SD_WP` (J901 pin 11) | Wiring is correct per the SD-111 drawing: WP closes to GND only with an **unlocked** card, CD closes to pin 3. This relies on the GL3224 ROM giving SD1_CDZ = 0 priority over MS1_INS = 0, the same assumption that fix #1 makes for slot 2. The DS does not state that priority. | Bench item: unlocked SD in slot 1 must enumerate as writable SD (not MS). If not, add an inverter or a strap and ask Genesys/LCSC FAE. |
| 8 | NOTE | usb_hub | U601 pins 5/14/27/34/42 (`PRT_DIS_Px`), embedded devices | **PRT_DIS_P straps sample the D+ pull-ups of already-powered devices.** The straps latch on every RESET_N rising edge (DS §3.3.1). The GL3224 (its VBUS pin is on +5V, so its D+ pull-up is always on), the RTL8156BG, the RP2350 and any FORCE_EN-powered USB-A device hold D+ high, so PRT_DIS_Px = 1 when the RP2350 resets the hub. The DS says a port is disabled only when both P and M are high, so this should be harmless. "D+ disabled" alone is undefined. | First-board check: reset the hub over HUB_RESET_N with everything enumerated, and confirm ports 1, 4 and 6 come back. |
| 9 | NOTE | usb_hub | C639 1 nF, R624 10k on RESET_N; RAILS_PG (70 µs PG delay) | DS Table 9-6 note: "The clock input must be stable prior to RESET_N deassertion". RESET_N rises about 70 µs after +1V15 is good, and the 25 MHz crystal has had only the roughly 2 ms +1V15 soft start since VDD33 came up. | Probably fine, since internal POR also gates. Cheap margin: C639 = 100 nF (τ ≈ 1 ms). The RP2350 then needs about 2 ms of release before the ≥ 1 ms strap hold. Adjust the firmware wait. |
| 10 | NOTE | usb_hub | CFG_BC_EN 10k PU (BC on ports 1–3) | Port 1 (the GL3224) gets BC1.2 because the strap has no "ports 2, 3 only" option (DS Table 3-3). In DCP mode, D+ and D− of the GL3224 link are shorted until a host is seen. Harmless, and the RP2350 clears it. | Optional: swap the port map (USB-A on ports 1/2, GL3224 on port 3) with the 10k PD strap ("ports 1, 2"). This changes routing, so it is only worth doing if layout allows. |
| 11 | NOTE | usb_a | `USBAx_OCS_N` | For a forced port (FORCE_EN = 1, hub port off), the RP2350 only sees a fault indirectly, as ISENSE pinned at 1.61–1.80 A (TPS2553 DS: the non-latching part keeps limiting and thermal-cycles). | Optional: route `USBA1_OCS_N` to the spare TCA9534 P7 (5 V-tolerant input, no internal pull-up, so it does not load the hub's 50k). |
| 12 | NOTE | docs | usb_hub.md "Reset", ethernet.md open issue 2 and "New inter-sheet net", mcu.py note "P6/P7 spare (10k PD)", card_reader.md §CD, research/hub-signal-path.md | Stale or inconsistent text: (a) usb_hub.md says "VCORE before or with VDD33". DS §9.6.1 says VCORE **after** or with VDD33. The circuit (+1V15 EN from +3V3) is correct. (b) +3V3 is already TPS62933**F** (FCCM). (c) ETH_I2C_EN is now global and on P6, and mcu.py has no 10k PD on P6 (R820 100k on ethernet is the only one). (d) Card detect goes to the TCA9534 P3/P4, not to an RP2350 GPIO. TCA9534 has no internal pulls (TCA9534 DS §8), so the "pulls off" firmware rule is moot. (e) The research doc still shows port 1 → TUSB1046. | Text-only cleanup. |

## Verified correct (no action)

- **USB 3.x direction and AC coupling.** From the netlist, each link has exactly one series cap, at its transmitter.

  | Link | TX → cap → RX | RX path |
  |---|---|---|
  | Hub ↔ laptop | U601 91/92 → C601/C602 220 nF → TUSB1064 SSTX | TUSB1064 SSRX → C513/C514 → U601 94/95 |
  | P1 ↔ GL3224 | U601 7/8 → C603/C604 → U901 RX 11/10 | U901 TX 8/7 → C917/C918 100 nF → U601 10/11 |
  | P2/P3 ↔ USB-A | U601 TX → C605–C608 → J70x pins 9/8 (StdA_SSTX±, host-side names) | J70x pins 6/5 → U601 RX, no cap (the device owns its cap) |
  | P4 ↔ RTL8156BG | U601 36/37 → C609/C610 → U801 46/47 | U801 43/44 → C835/C836 → U601 39/40 |
  | P5 ↔ TUSB1046 | U601 83/84 → C611/C612 → TUSB1046 SSTX | TUSB1046 SSRX → C530/C531 → U601 86/87 |

  - No doubled or missing caps. The redriver connector-side caps are on usbc_muxes.
  - USB-A footprint pad order (5–9 rear row, 9 next to VBUS) matches the standard Std-A layout.
- **USB2 polarity.** Every D+ goes to D+ and every D− to D− (U601 5/6, 14/15, 27/28, 34/35, 81/82, 42/41, 89/90 to
  GL3224 5/4, J70x 3/2, RTL 50/49, MCU via 27 Ω).
- **Hub pinout.** The symbol matches the DS pin table (8× VDD33, 9× VCORE, EP = VSS).
  - Config 3 straps (10k PD / 200k PD / 200k PD) are correct.
  - CFG_NON_REM 200k PU means port 1 is non-removable. CFG_BC_EN 10k PU enables BC on ports 1–3.
  - TEST1–3 have 10k PU, TESTEN goes to GND and ATEST floats.
  - RBIAS is 12k 1 %. SPI_CLK/D1–D3 have weak PDs.
  - PF15 = PRT_CTL3 and PF16 = PRT_CTL2. Unused PRT_CTL/PRT_CTL_U3 pins float. PF26/27 are the SMBus slave.
  - Every VDD33/VCORE pin has 100 nF.
  - VCORE 1.154 V is inside the 1.09–1.21 V range. +1V15 is enabled from +3V3, which meets DS §9.6.1.
- **PRT_CTL / OR logic.** DS §8.2 confirms one combined open-drain pin with a 50k pull-up when the port is on.
  - The 74LVC1G32 input does not load it, and there is no external pull-up.
  - The TPS2553 is active-high EN with 7.5 ms FAULT# deglitch. RILIM 15.0 kΩ gives **1.61 / 1.70 / 1.80 A** (TPS2553 DS
    Electrical Characteristics), which is above BC1.2's 1.5 A.
  - The INA180A2 (gain 50) works with VS = 3.3 V and CM = 5 V, giving 1.5 V/A.
- **Hub VBUS_DET sequencing.** VBUS_DET must not rise before VDD33, and the D602 clamp guarantees it.
- **GL3224.** Pins match DS Table 3.1. VBUS = +5V. AVDD33/DVDD33/AVDD12/DVDD12/VUHS are all decoupled and kept local.
  - RTERM is 680 Ω 1 %. The 25 MHz crystal is well inside ±0.03 %.
  - SD-111 and DM3AT contact maps are correct. CD switches are normally open and close to GND, giving active-low CDZ.
  - The CD tap through 1k to the TCA9534 P3/P4 is fine (TCA9534 has no pulls and is 5 V tolerant).
- **RTL8156BG.** The BG variant has NC pins 3/4/6 and pin 5 = POW_EXT_SWR (DS Table 13).
  - Every 3.3 V and 0.95 V pin is decoupled. DVDD09_UPS is isolated with 1 µF.
  - The 0.954 V setpoint stays within 0.932–0.977 V (VFB 591–609 mV) inside the 0.92–0.98 V window.
  - TPS62A02A is FPWM. ETH_3V3 rise is about 1.68 ms (TPS22918 at 3.3 V, CT 1 nF), inside t1 of 0.5–10 ms. A ≥ 100 ms
    off time covers t4 ≥ 50 ms.
  - MDI0..3 → TD1..TD4 → RJ pins 1/2, 3/6, 4/5, 7/8 per the USAKRO drawing. LEDs are G 14+/13− and Y 12+/11−.
  - The crystal meets ±50 ppm and ESR 70 Ω.
- **24AA025E48 SOT-23-6.** The pinout matches and the address is 0x50 (A2 internally 0, DS §5). There is no conflict on
  I2C_SYS.
- **Ethernet power-cycle effect on the hub.** Port 4 sees a normal disconnect and reconnect.
  - Hub TX is AC-coupled into the unpowered PHY, and USB2 is only pulled down.
  - All PHY pulls, the LED buffer (LVC Ioff) and the I2C bridge (body diodes face away from the PHY) avoid back-powering it.

## Resolution (2026-10-02)

The fixes are in `usb_hub.py`, `usb_a.py`, `card_reader.py` and `ethernet.py`, with matching `docs/design/*.md`. New parts
were added last on each sheet, so existing reference designators are unchanged. The rebuild passes with
`netlist verify: OK`, and `tools/bom_check.py` reports 0 failing.

| # | Resolution |
|---|---|
| 1 | U901 pin 35 MS2_INS/SD2_WP now goes to **CR_USD_CDZ** instead of GND. The behaviour now mirrors slot 1: no card means no MS and no WP, and a card means SD present and writable. The sheet note and card_reader.md are updated. |
| 2 | HUB_VBUS_DET is now buffered. VBUS_LAPTOP → R625 47k / R626 **68k** (was 47k) → D602 BAT54WS clamp → `HUB_VBUS_SNS` → **U603 74LVC1G17W5-7** (C151394, on +3V3) → **R632 15k / R633 49.9k** → PF30. The sense node is 2.60 V at 4.4 V (above VT+ max 2.0 V) and clamps at about 3.6 V at 28 V, which the 5.5 V-tolerant input accepts. PF30 high is 2.46–2.64 V for +3V3 = 3.20–3.43 V, which is ≤ 2.7 V and above VIH 2.1 V. The checklist's 11k/49.9k ratio would give 2.73 V at our 3.33 V rail, hence 15k. The buffer runs from VDD33's own rail, so the sequencing is preserved. |
| 3 | C835/C836 are now **100 nF** (C1525), within the USB 3.x Gen1 TX range of 75–200 nF. |
| 4 | **R629 (HUB_SMB_PU), R702 and R707 (USBA1/2_FORCE_EN) are now 4.7k** (C25900). The GPIO load while high is 0.7 mA (HUB_SMB_PU up to about 1.4 mA with both SMBus lines low), well within the 4 mA drive. This is kept regardless of RP2350 stepping. Reading the stepping on the first boards is listed as a usb_hub bench item. |
| 5 | Bench items are added to the ethernet sheet note and to ethernet.md: address scan with the bridge on and off, collision check, persistence check via ETH_RESET_N power-cycle and PLA_IDR readback, and blank-eFuse behaviour. Q801 is now **BSS138DW-7-F** (C154900, VGS(th) ≤ 1.5 V). The bridge is also gated in hardware; see mcu_ui #5 below. |
| 6 | Documented as a limitation in the usb_hub sheet note and usb_hub.md. The hardware fix (74LVC1G08 plus a "data link expected" gate) needs a new inter-sheet net, so it was not done here. |
| 7 | Bench item added to card_reader.md open issue 7 and the sheet note: the ROM must give SDx_CDZ priority over MSx_INS. |
| 8, 9, 10 | Bench and optional items added to usb_hub.md open issue 9: PRT_DIS reset test, C639 → 100 nF fallback, and the BC port-map swap. |
| 11 | No change. TCA9534 P7 belongs to the mcu sheet. |
| 12 | (a) usb_hub.md now reads "VCORE **after** or with VDD33". (b) ethernet.md open issue 2 is marked resolved, since +3V3 is already the TPS62933F. (c) ethernet.md inter-sheet nets and the R820 description are fixed: ETH_I2C_EN is global, and mcu has no 10k pull-down. The mcu.py note belongs to the mcu owner. (d) card_reader.py/.md now say card detect goes to TCA9534 P3/P4, which has no pulls. (e) research/hub-signal-path.md was not touched because it is out of scope. |

**mcu_ui #5 (ethernet part).** The Q801 gates are now `ETH_BR_G`, driven by **U806 74LVC1G17 powered from ETH_3V3**,
with ETH_I2C_EN as its input and R821 100k to GND. The gates can only be high while ETH_I2C_EN = 1 and ETH_3V3 is up.
With ETH_3V3 off, the driver is unpowered (the Ioff input does not back-feed the PHY rail) and R821 holds the gates at
0 V. I2C_SYS therefore cannot be dragged into a dead PHY.
