# odock-10 — USB-A sheet (`usb_a.kicad_sch`, ref 700)

Source: `hardware/odock-10/sheets/usb_a.py`. Two USB 3.2 Gen2 (10 Gbps) Type-A ports on USB7206C hub ports 2 and 3.
Each port has a current-limited VBUS switch that the hub or the RP2350 can turn on, a current-sense amplifier, ESD
protection and VBUS bulk capacitance.

```
                        +3V3
USBAx_PWR_EN ══╗ (hub PRT_CTL, same node   ┌───────┐
  (0R on hub)  ╠══ USBAx_OCS_N ◄── FAULT# ─┤       │
               ║                    A ─────┤ 1G32  ├── USBAx_EN ──► EN
USBAx_FORCE_EN ╫──────(4.7k PD)──── B ─────┤  OR   │   (100k PD)
               ║                           └───────┘
+5V ── 30 mΩ ── USBAx_SW_IN ── TPS2553 (RILIM 15k) ── +5V_USBAx ── 150 µF + 10 µF + 100 nF ── VBUS (J pin 1)
        │  │                                                        USBLC6 VBUS clamp
        INA180A2 (×50) ── 1k ──┬── USBAx_ISENSE (RP2350 ADC)
                             100 nF
hub TX ─ 220 nF (usb_hub) ─ USBAx_SS_TXP/N ──┬── J pins 9/8 (StdA_SSTX+/−)
hub RX ───────────────────── USBAx_SS_RXP/N ─┼── J pins 6/5 (StdA_SSRX+/−)    TPD4E02B04 on all 4
hub USB2 ─────────────────── USBAx_DP/DN ────┴── J pins 3/2                    USBLC6-2SC6 on D+/D−
```

## Choices

### Connector
- **Amphenol GSB4111312HR** (C5429382, 3846 in stock). It is Amphenol's USB 3.1 Gen 2 Type-A family (GSB4), right-angle
  THT. No better-documented in-stock Gen2 Type-A was found (research note: the GSB311/Molex 48406 parts are 5 Gbps only).
- Shell/EH tabs and GND_DRAIN go straight to GND. odock-10 has no chassis, which matches the usbc_muxes convention.

### Pair naming and AC coupling
- In the Standard-A receptacle pin names (USB 3.2 §5.3), StdA_SSTX (pins 9/8) means the host transmits and StdA_SSRX
  (pins 6/5) means the host receives.
- With hub-view nets, **USBAx_SS_TX* → SSTX pins 9/8** and **USBAx_SS_RX* → SSRX pins 6/5**.
  - The task brief said "hub TX → connector SSRX". That only holds with device-side names, so the sheet follows the
    USB-IF host-side pin names. Check this against the GSB4 drawing when the PDF can be fetched (see open issues).
- AC coupling caps sit on the board of the transmitter they belong to (USB 3.2 §6.2.2, C_AC_COUPLING on the TX side):
  - hub TX: 220 nF on usb_hub (75–265 nF for Gen2);
  - device TX: the caps are inside the plugged device or cable plug, so the SSRX → hub RX path has **no caps here**. Adding
    a second series cap would just put two caps in series, which is wrong.

### Port power switch: TPS2553DBVR (C55266)
- Active-high EN, adjustable current limit, 7.5 ms FAULT# deglitch, reverse-voltage blocking.
- **RILIM = 15.0 kΩ**, the smallest value allowed. From DS table 7.5, the current limit is 1.61 A min, 1.70 A typ and
  1.80 A max (−40…105 °C).
  - The minimum stays above 1.5 A, so BC1.2 DCP/CDP (1.5 A) and the power budget's "7.5 W charge mode" are always
    available.
  - The maximum (1.8 A) is below the GSB4 contact rating class (about 1.8 A per pin) and the 2 A ADC range.
- Input: 10 µF 0805 plus 100 nF at the IN pin. Output: see VBUS bulk.

### Enable logic: hub PRT_CTL OR RP2350 FORCE_EN
- The USB7206C PRT_CTLx pin is both the power enable and the overcurrent sense (integration item 12; usb_hub joins
  `USBAx_PWR_EN` and `USBAx_OCS_N` with 0 Ω R630/R631).
  - Port on: the pin is an input with an internal ~50 kΩ pull-up, so the node is high.
  - Port off or OC latched: the hub drives the pin low.
- **74LVC1G32** (C10096, the same part as on power_input), powered from +3V3:
  - A = USBAx_PWR_EN. This is a CMOS input with no load, so the hub's weak pull-up is enough.
  - B = USBAx_FORCE_EN, which has a **4.7 kΩ** pull-down (R702/R707). The default is off while the RP2350 is in reset
    or BOOTSEL.
    - 4.7k rather than 100k because of **RP2350 erratum E9** (stepping A2). A pad that was driven high and then reverts
      to input can latch at about 2.2 V. That is above the LVC1G32 VIH of 2.0 V, so the port would be forced on after a
      crash or a reboot to BOOTSEL. Only a pull of ≤ 8.2 kΩ defeats the latch.
    - The push-pull GPIO sources 0.7 mA while forcing, which gives a negligible VOH drop at the default 4 mA drive.
  - Y = TPS2553 EN, with a 100 kΩ pull-down. This keeps the switch off during the +3V3 ramp, when +5V is up and the OR gate
    is unpowered with Ioff high-Z.
- TPS2553 FAULT# (open drain) → USBAx_OCS_N, which is the same node. **No pull-up is added on this sheet.**
- Behaviour:

  | Hub port | FORCE_EN | Overload | Result |
  |---|---|---|---|
  | on | 0 | no | Port powered by the hub |
  | on | 0 | yes | After 7.5 ms FAULT# pulls the node low. The hub sees OC and latches the port off (drives low). The OR output goes low, the switch turns off and FAULT# releases. The hub keeps it off until the host re-enables it. |
  | off | 1 | no | Port powered by the RP2350 (dumb-charge mode, no laptop or no enumeration) |
  | off | 1 | yes | The switch stays in constant-current limit with thermal cycling. FAULT# pulls a node the hub already drives low, so there is no conflict. The RP2350 sees ISENSE pinned at the limit (1.6–1.8 A) and drops FORCE_EN. |
  | on | 1 | yes | The hub reports OC to the host. The port stays current-limited until firmware drops FORCE_EN. |
- The RP2350 can read USBAx_OCS_N directly if the mcu sheet wants to: it is a high-Z GPIO input, and no pull-up may be
  enabled on it.

### Current sense: 30 mΩ + INA180A2 (C192764)
- The shunt sits on the switch input side, between +5V and USBAx_SW_IN. +5V_USBAx therefore stays the real port VBUS
  node, and the switch's 0.1 mA quiescent current is negligible.
- INA180A2 has a gain of 50 and a common-mode range of −0.2 to 26 V regardless of VS, so VS = +3V3 works and the output
  can never exceed the ADC's 3.3 V.
- Scale: 30 mΩ × 50 = **1.5 V/A**.
  - 2.0 A gives 3.00 V, and full scale is 2.2 A (the INA180 swings to VS − 20 mV).
  - The 1.8 A current-limit maximum gives 2.7 V.
- Auto-off threshold: 25 mA gives 37.5 mV.
  - The INA180 offset of ±150 µV × 50 = ±7.5 mV, about ±5 mA. That is fine for a "below about 25 mA for 5 min" rule.
  - The RP2350 ADC is 12-bit, so 0.8 mV is about 0.5 mA per LSB.
- Shunt: Yageo PE0805FRF470R03L (C858599), 30 mΩ, 1 %, 0805, 0.5 W. At 1.8 A it dissipates 97 mW.
- Output: 1 kΩ + 100 nF (fc 1.6 kHz) to the ADC pin. This gives some anti-alias filtering and isolates the INA180 from the
  ADC sampling cap.
- Layout: Kelvin-route IN+/IN− from the inner pad edges of the shunt.

### VBUS bulk
- USB 2.0 §7.2.4.1 asks for ≥ 120 µF of low-ESR capacitance per downstream port. Each port gets:
  - Panasonic **10TPF150ML** POSCAP (C347559): 150 µF, 10 V, 2917, 3275 in stock. The 10 V rating gives 2× margin on 5.1 V.
  - 10 µF 0805 and 100 nF at the connector.
- Inrush into 160 µF is limited by the TPS2553 soft start (about 1 ms ramp, below the current limit). The +5V rail holds
  330 µF polymer plus ceramics (power_rails).

### ESD
- SS lines: **TPD4E02B04** (C106794, 0.25 pF, the same as usbc_muxes), flow-through at the connector, one per port.
- D+/D−: **USBLC6-2SC6** (C7519, about 2.5 pF). VBUS pin 5 on +5V_USBAx, which also clamps the port VBUS. The pin pairs
  1/6 and 3/4 are flow-through.

## Part list (this sheet, both ports)

| Ref | Part | LCSC | JLC stock (2026-10-02) | Type | Qty |
|---|---|---|---|---|---|
| J701, J702 | Amphenol GSB4111312HR USB 3.2 Gen2 Type-A | C5429382 | 3846 | ext | 2 |
| U701, U704 | TI TPS2553DBVR | C55266 | 58 742 | ext | 2 |
| U702, U705 | TI SN74LVC1G32DBVR | C10096 | 112 507 | ext | 2 |
| U703, U706 | TI INA180A2IDBVR | C192764 | 99 670 | ext | 2 |
| D701, D703 | TI TPD4E02B04DQAR | C106794 | 105 950 | ext | 2 |
| D702, D704 | ST USBLC6-2SC6 | C7519 | 36 009 | ext | 2 |
| R704, R709 | Yageo PE0805FRF470R03L 30 mΩ 1 % 0805 | C858599 | 9045 | ext | 2 |
| C701, C709 | Panasonic 10TPF150ML 150 µF 10 V POSCAP | C347559 | 3275 | ext | 2 |
| R701, R706 | 15 kΩ 1 % 0402 (RILIM) | C25756 | 1.1 M | basic | 2 |
| R70x | 100 kΩ 0402 | C25741 | 8.2 M | basic | 4 |
| R705, R710 | 1 kΩ 0402 | C11702 | 7.2 M | basic | 2 |
| C70x | 10 µF 25 V 0805 | C15850 | 4.9 M | basic | 4 |
| C70x | 100 nF 0402 | C1525 | 21 M | basic | 10 |

`tools/bom_check.py`: all of the above OK (≥ 5 in stock).

## Open issues
1. **GSB4111312HR datasheet/footprint.** The Amphenol PDF and the LCSC datasheet could not be fetched (403, no URL). The
   easyeda footprint is named `USB-A-TH_U231-091N-4BLRC19-F1-A`.
   - Before layout, check pad positions and the SSTX/SSRX pin order (5/6 = SSRX, 8/9 = SSTX per USB-IF) against the
     Amphenol drawing.
   - Also confirm the 10 Gbps rating.
2. **TPS2553 footprint.** The import shares `SOT-23-6_L2.9-W1.6-P0.95-LS2.8-BR` with TLV6700DDCR/TLV3011. The import
   script kept the original. Same geometry name, but check it against the TI DBV land pattern.
3. **DCP with no host.** Forcing VBUS on gives power, but a BC1.2/Apple device only draws more than 500 mA if the hub
   presents DCP (D+/D− short) on that port.
   - Whether USB7206C applies its DCP signature on a port whose PRT_CTL is low (hub considers it off) is unverified
     (usb_hub open issue 3).
   - If not, forced mode is limited to non-negotiating loads, or the RP2350 must also enable the port over SMBus.
4. **Firmware.** Drop FORCE_EN when ISENSE sits at the current limit for more than about 100 ms, since the TPS2553 does
   not latch off by itself. Bus-powered mode: keep FORCE_EN off and stay within the budget (power-budget.md).
5. **Thermal.** TPS2553 at 1.7 A × 85 mΩ is about 0.25 W in SOT-23-6. Give the IN/OUT pins copper.

No new inter-sheet nets are needed. The mcu sheet must provide USBA1/2_FORCE_EN as push-pull GPIOs and
USBA1/2_ISENSE as ADC inputs.
