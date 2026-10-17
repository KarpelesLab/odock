# odock-10 — Ethernet sheet (`ethernet.kicad_sch`, refs 800+)

Source: `hardware/odock-10/sheets/ethernet.py` (generated, netlist-verified). Stock figures are from the JLC parts API on
2026-10-02. Re-check them before ordering.

## Sources used
- **RTL8156BG(S)-CG datasheet Rev 1.1** (Realtek, NDA, but a copy circulates publicly, e.g. on doc.chipmall.com). It gives
  pinout, power, sequencing, crystal specs, EEPROM/eFuse/I2C-MACID behaviour and LED registers.
- **Realtek RTL8125D/8125B(G)(S)/8111K reference schematic** (2024, public). This is the PCIe sibling and uses the same
  2.5G PHY and the same `POW_EXT_SWR` scheme. It gives RSET, the magnetics centre-tap capacitor, LED circuit, strap pull-ups
  and the "switcher must run PWM ≥ 1 MHz" rule.
- **gamefunc/rtl8156-vl822-fe2.1-open-pcb** (GitHub, verified working RTL8156B board). The EasyEDA Pro `.eprj` file is
  SQLite, and its pad netlist was extracted. It confirms the pull values (4.7k PU on GPI, LANWAKEB, DOCK_DET, GPIO1/2/4, LED0,
  LED1; 4.7k PD on EECS; 2.49k RSET; 1 µF on DVDD09_UPS; 12 pF crystal caps) and that CONFIG_SEQ/GPIO3/LED2/3 can float.
  It also warns that some EasyEDA RTL8156 libraries use a 7×7 package: the real part is **QFN-56 6×6, 0.35 mm**.

## Topology

```
+3V3 ─ TPS22918 (ON = ETH_RESET_N, CT 1 nF, QOD) ─► ETH_3V3 ─┬─ RTL8156BG 3.3 V pins (+ bead ─► pin 9 PLL)
                                                              └─ TPS62A02A (EN = POW_EXT_SWR) ─ 1 µH ─► ETH_0V95 ─► 0.95 V pins
hub P4 ── ETH_SS_TX± (capped on usb_hub) ──► U3SSRX     U3SSTX ─ 100 nF ─► ETH_SS_RX± ── hub P4
       ── ETH_DP/DN ─────────────────────► U2DP/DM
RTL MDI0..3 ──► USAKRO DGUK211Q340CD2A4D2 (2.5G magjack, CT 390 pF, green/yellow LEDs)
RTL LED0/1/2 ─┬─ jack LEDs (LED0 green, LED1 yellow, 510 Ω from ETH_3V3)
              └─ SN74LVC3G17 (+3V3) ─► ETH_LED0..2 ─► RP2350 GPIO36-38
24AA025E48 (I2C_SYS 0x50) ── RP2350 reads EUI-48
RTL GPIO1/SDA, GPIO2/SCL ── BSS138DW bridge (gates = ETH_I2C_EN AND ETH_3V3, via 74LVC1G17 on ETH_3V3) ── I2C_SYS   (MAC programming into the PHY eFuse)
```

## 1. Reset = power cycle
**The RTL8156BG has no reset pin.** Its 56 pins are fully allocated: there is no PERST#/RESETB. So `ETH_RESET_N` drives the
ON pin of a TPS22918 load switch that feeds the whole PHY. Because the 0.95 V buck runs from ETH_3V3, it switches off too.
- `ETH_RESET_N` comes from TCA9534 P5 on the mcu sheet, with a 10k pull-up there (no pull-up on this sheet).
  - The expander powers up as inputs, so the PHY is powered with a dead or blank RP2350.
- **Firmware:** hold `ETH_RESET_N` low for at least 100 ms. That covers t4 (≥ 50 ms off-to-on interval, DS table 25)
  plus QOD discharge of ~45 µF.
  - The same control turns 2.5GbE off for thermal derating, which saves ~0.6 W.
- **Rise time:** CT = 1 nF gives tR ≈ 1.7 ms at 3.3 V (TPS22918 DS), inside the PHY's t1 of 0.5–10 ms. Inrush is about
  45 µF × 3.3 V / 1.7 ms ≈ 90 mA.
- **QOD** is tied to VOUT, so the internal pull-down discharges ETH_3V3 and the 0.95 V buck sees UVLO quickly.
- **No back-powering of the off PHY:**
  - Every strap and pull-up returns to ETH_3V3, never +3V3.
  - The LED buffer inputs have no VCC clamp (LVC Ioff).
  - The I2C bridge's body diodes point away from the PHY.
  - The USB lines come from the hub, and an unpowered USB device is a normal case.
- Alternative (unused): DOCK_DET low triggers a "self-reset" (DS 6.23). The feature is eFuse-dependent and undocumented, so
  DOCK_DET is simply pulled high.

## 2. 0.95 V core rail (integration item #1)
- **Requirement (DS 9.2/9.7/8.1):**
  - 0.92–0.98 V (±3 %), 364 mA typ / 650 mA max.
  - Rise 0.5–2.2 ms; ≥ 50 ms off-on.
  - Abs max 1.05 V.
  - The PHY enables the regulator itself through **pin 5 POW_EXT_SWR**, an active-high output.
  - Realtek's reference says a switcher feeding the PHY must run PWM ≥ 1 MHz.
- **Part:** TPS62A02A**DRLR** (C5820994, 11.6k stock).
  - It is the forced-PWM "A" variant at 2.4 MHz, so there is no PSM ripple at the PHY's light load.
  - Internal 1 ms soft start, which meets t3.
  - VIN 2.5–5.5 V from ETH_3V3, with UVLO at 2.3–2.5 V.
  - Output discharge when disabled.
  - Chosen over TLV62569 (the PSM part named in power_rails.md) because of the forced-PWM requirement.
- **Setpoint:** VOUT = 0.6 V × (1 + 59k/100k) = **0.954 V**.
  - Tolerance stack: VFB ±1.5 % over temperature and two 1 % resistors (±0.8 %).
  - Worst case 0.932–0.977 V, inside the 0.92–0.98 V window. Ripple at 2.4 MHz with 2×22 µF is a few mV.
- **Filter:**
  - L = 1 µH SWPA4018S1R0NT; COUT = 2 × 22 µF 0603 at the buck (TI table 8-3 standard combination for VOUT < 1.2 V).
  - Plus 3 × 2.2 µF + 2 × 10 µF + 4 × 100 nF + 2.2 µF at the PHY pins.
- **EN:** 100k pull-down. The buck stays off until the PHY asserts POW_EXT_SWR. PG is unused.
- **Loss:** ≈ 0.1 W in the buck. PHY total ≈ 0.6–0.65 W typ (0.95 V × 0.36 A + 3.3 V × 0.09 A), about 1 W worst case.

## 3. Clock, bias, straps
- **Crystal:** YXC X322525MOB4SI 25 MHz (C9006, basic). This is the same part as the hub (12 pF CL, ±10 ppm) with 2 × 20 pF.
  The PHY needs ±50 ppm all-in, ESR ≤ 70 Ω and an SMD package. A 0 Ω series resistor on the CKXTAL2 side (Realtek R27) lets
  the drive level be tuned (PHY DL max 0.5 mW).
- **RSET:** 2.49k 1 % at pin 14.

| Pin | Net | Termination | Why |
|---|---|---|---|
| 1 LANWAKEB | ETH_LANWAKE_N | 4.7k PU | open drain, unused |
| 2 GPI | ETH_GPI | 4.7k PU | LAN-disable input if enabled in eFuse; otherwise idle |
| 5 POW_EXT_SWR | ETH_SWR_EN | 100k PD → buck EN | defined level while the PHY powers up |
| 30 EECS/TWSI_SCL | ETH_EECS | 4.7k PD | no EEPROM (Realtek and open design) |
| 33/34 GPIO2/SCL, GPIO1/SDA | ETH_SCL/SDA | 4.7k PU + bridge | I2C slave for MACID (§5) |
| 35 CONFIG_SEQ | ETH_CFG_SEQ | 10k PD (+10k PU DNP) | low = CDC-NCM first; only active if enabled in eFuse |
| 37 DOCK_DET | ETH_DOCK_DET | 4.7k PU | "connected" → no self-reset |
| 38 LED0/EEDI | ETH_LED0_N | 4.7k PU + green LED | strap/idle; mcu requires ≤ 10k on strap pins |
| 39 LED1/EESK | ETH_LED1_N | 4.7k PU + yellow LED | Realtek "PU for normal application" |
| 40 LED2 | ETH_LED2_N | 10k PU | LED pins float when off |
| 53 GPIO4 | ETH_GPIO4 | 4.7k PU | as the open design |
| 3, 4, 6, 8, 28, 29, 32, 41 | — | NC | BGS-only pins, CKOUT, SPI flash, GPIO3, LED3 |

## 4. LEDs
- **Jack LEDs:**
  - LED anode at ETH_3V3, cathode through 510 Ω into the PHY pin (Realtek's low-side, active-low scheme). This gives
    ~2.5–3 mA.
  - Green (left) = LED0, yellow (right) = LED1.
  - What each LED shows (link speed, activity) is set by the LED registers (DS tables 14–18, OCP 0xDD90 area) through eFuse or
    the host driver. Blink rate is set at OCP 0xDD88.
- **RP2350 inputs:**
  - The jack LEDs and 4.7k pull-ups load the pins, and the PHY rail is switched. So a SN74LVC3G17 Schmitt triple buffer on
    +3V3 drives `ETH_LED0..2`.
  - The levels are **active low** (low = LED lit). The mcu sheet counts edges on GPIO36-38 for activity.
  - With the PHY off, the buffer inputs sit at 0 V, so the outputs are low. Firmware ignores the LEDs while it holds
    ETH_RESET_N low.
  - The buffer also means the RP2350 never loads the LED0/LED1 strap pins (mcu requirement 3).

## 5. MAC address
How the RTL8156BG gets its MAC (DS 6.4, 6.6, tables 20–21):
1. **eFuse/OTP autoload** (≥ 512 B, programmed with Realtek's PG tool). Distribution parts are blank, so you get the chip's
   default MAC or a host-randomised one. Commercial dongles have their MAC burnt into eFuse at the factory.
2. **External 93C46/56/66 (3-wire) or TWSI EEPROM.** It is only read after an eFuse autoload command (`20 DC 00 01` = TWSI)
   selects it, which again needs the PG tool. The content uses Realtek's layout, which a 24AA0xxE48 with its EUI-48 at
   0xFA–0xFF does not match. **Not usable as a plug-in MAC source.**
3. **I2C slave "MACID modified via I2C" (DS 6.6, figure 4)** on GPIO1/SDA (34) and GPIO2/SCL (33). The host writes a 36-byte
   "OTP code":
   - `[7-bit addr][W] 25 C0 00 MAC0 MAC1 MAC2 MAC3 MAC4 MAC5` followed by 26 × `00`.
   - Decoded, `25 C0 00` is an eFuse autoload record: "write 6 bytes to OCP 0xC000". That address is PLA_IDR, the MAC
     register in the Linux r8152 driver.
   - So this **burns the MAC into the PHY's eFuse** from an I2C master. That master can be the RP2350.

**Implemented path:**
- **U805, 24AA025E48T-I/OT** (C129895, SOT-23-6) on I2C_SYS at **0x50** (A1 = A0 = GND).
  - The 24AA**02**E48 was rejected: it ignores its chip-select bits and would occupy 0x50–0x57.
  - The RP2350 reads the EUI-48 at 0xFA–0xFF.
- **I2C bridge Q801 (BSS138DW, VGS(th) 0.5–1.5 V):**
  - Sources sit on the PHY side, pulled up to ETH_3V3. Drains sit on I2C_SYS.
  - The gates are `ETH_BR_G`, driven by **U806 74LVC1G17 powered from ETH_3V3**. Its input is `ETH_I2C_EN` (TCA9534
    P6, 100k PD R820), and R821 (100k) holds ETH_BR_G low.
    - The gates can therefore be high only while ETH_I2C_EN = 1 **and** ETH_3V3 is up.
    - With ETH_3V3 off, the driver is unpowered. The LVC Ioff input takes the 3.3 V from P6 without back-feeding
      ETH_3V3, and R821 keeps the gates at 0 V.
    - While ETH_3V3 decays, VOH ≤ ETH_3V3, so the gates never exceed the PHY rail. The TPS22918 QOD then takes it to
      0 V.
  - This fixes review mcu_ui #5. Before, ETH_I2C_EN = 1 with ETH_RESET_N = 0 (a firmware bug, or a thermal power-down
    in the middle of a write) pulled I2C_SYS into the dead 4.7k pull-ups and PHY clamps to about 2.25 V. That is
    below VIH, and it locked the TCA9534 that controls both signals until a power cycle. Firmware should still clear
    P6 before powering the PHY down.
  - **Off:** the PHY can see I2C_SYS traffic through the body diodes but can never pull I2C_SYS low. An unpowered PHY is not
    back-fed.
  - **On:** a normal bidirectional bridge. The BSS138DW replaces the 2N7002DW (VGS(th) up to 2.5 V) for solid
    conduction with a 3.3 V gate.
- **Firmware flow:**
  1. On first boot (flag in RP2350 flash), with the PHY powered, set ETH_I2C_EN.
  2. Write the OTP code with the EUI-48.
  3. Clear ETH_I2C_EN.
  4. Power-cycle the PHY through ETH_RESET_N so the eFuse is re-autoloaded.
  - **Program once.** eFuse is one-time, and every rewrite appends ~36 B of the ≥ 512 B.
- **Unknowns to settle on the bench:**
  - The 7-bit slave address is not given in the datasheet. Scan with the bridge on and the PHY powered.
  - Whether the I2C slave is active on a blank eFuse.
  - Whether the address collides with an I2C_SYS device while the bridge is on (0x20, 0x41/0x44/0x45, 0x48–0x4F,
    0x50). Scan with the bridge on and then off.
  - Whether the write **persists**. Write once, power-cycle with ETH_RESET_N, and read PLA_IDR back over USB. If the
    write turns out to be volatile, use the host-tool or OS fallbacks rather than rewriting on every power-up, which
    would race the host driver.
- **Fallbacks:**
  - (a) A host tool (Realtek PG tool for Windows, or `rtunicpg` on Linux) writes the same EUI-48 over USB. The RP2350 shows the
    address in the status app/LCD.
  - (b) The OS sets the MAC at runtime (`ip link set address`, `ifconfig en… ether`).
  - (c) The 24AA025E48 still gives every deck a unique, printable address for the label.

## 6. MDI and magjack
- **Jack:** USAKRO DGUK211Q340CD2A4D2 (C19725134, 111 in stock, $2.85), tab-up, THT.
  - The jack datasheet shows **green (14+/13−) and yellow (12+/11−) LEDs**, so the "no LEDs" note in odock-10.md was wrong.
  - 1CT:1CT, OCL 180 µH, return loss to 200 MHz, Hi-pot 2250 VDC. Cable-side 4 × 75 Ω + 1000 pF/2 kV are inside.
  - It is the only stocked 2.5G-rated jack with ≥ 100 stock. Alternates: DGUK511Q340AB2A8D2 (C19725141, 47 stock, same
    LEDs, different footprint) and DGUK111Q340AB2A1D2 (8 stock). The common HR911130A (10k stock) is 1G-rated only.
- **Footprint:** the imported easyeda footprint numbered both shell pads "15", while the symbol has 15/16. The second shell
  pad was renamed to 16 in `hardware/lib/odock.pretty/RJ45-TH_DGUK211Q340CD2A4D2.kicad_mod`. Verify the rest of the
  footprint against the drawing (pitch 1.27/2.54 staggered, LED pins 11–14, Ø3.2 pegs).
- **Pair mapping:** MDI0→TD1 (RJ 1/2, BI_DA), MDI1→TD2 (3/6, BI_DB), MDI2→TD3 (4/5, BI_DC), MDI3→TD4 (7/8, BI_DD). If the
  QFN-to-jack order forces crossings, use the PHY MDI-swap option (DS 6.15) rather than vias. Auto-MDIX and polarity
  correction cover the rest.
- **PHY-side centre taps** (pins 5 and 6): 390 pF C0G to GND, the RTL8125B-series value (2.5G voltage-mode driver: no bias
  feed). A 100 nF DNP alternate is provided.
- **No ESD array on MDI.** The magnetics isolate and Realtek's reference has none.
- **Shell to GND directly.** This follows the odock convention of no chassis net, the same as USB connectors.

## Global nets used
`+3V3`, `GND`, `ETH_SS_TXP/TXN/RXP/RXN`, `ETH_DP`, `ETH_DN`, `ETH_LED0..2`, `ETH_RESET_N`, `I2C_SYS_SCL`, `I2C_SYS_SDA`.
There are no PWR_FLAGs: ETH_3V3 and ETH_0V95 are local and driven by power_out pins.

## Inter-sheet nets
- `ETH_I2C_EN` is global (TCA9534 P6 on mcu). Its only pull-down is R820 (100k) on this sheet; mcu has none.
- New local nets: `ETH_BR_G` (bridge gates).

## Part list (this sheet)

| Ref | Part | LCSC | JLC stock | Type |
|---|---|---|---|---|
| U801 | Realtek RTL8156BG-CG (QFN-56 6×6) | C41376388 | 2 915 | ext |
| U802 | TI TPS22918DBVR load switch | C131941 | 12 939 | ext |
| U803 | TI TPS62A02ADRLR 2 A FPWM buck | C5820994 | 11 582 | ext |
| U804 | TI SN74LVC3G17DCUR | C68245 | 3 108 | ext |
| U805 | Microchip 24AA025E48T-I/OT | C129895 | 6 430 | ext |
| Q801 | Diodes BSS138DW-7-F | C154900 | 121 051 | ext |
| U806 | Diodes 74LVC1G17W5-7 (bridge gate driver) | C151394 | 10 871 | ext |
| J801 | USAKRO DGUK211Q340CD2A4D2 2.5G magjack | C19725134 | 111 | ext |
| L801 | Sunlord SWPA4018S1R0NT 1 µH | C91250 | 5 113 | ext |
| FB801 | Sunlord GZ2012D101TF 100 Ω bead 0805 | C1015 | 2.3 M | basic |
| Y801 | YXC X322525MOB4SI 25 MHz | C9006 | 199 k | basic |
| R | 2.49k 1 % C25884, 59k 1 % C32297 | | > 100 k | ext |
| C | 390 pF C0G 50 V C282239 (same as pd_pmg1 CC caps) | | 70 k | ext |
| R/C basic | 0 Ω C17168, 510 Ω C25123, 4.7k C25900, 10k C25744, 100k C25741; 20 pF C1554, 1 nF C1523, 100 nF C1525 (incl. C835/C836 PHY TX AC caps, C841), 1 µF C52923, 2.2 µF C12530, 10 µF 0603 C19702, 22 µF 0603 C59461 | | | basic |

DNP: the CONFIG_SEQ pull-up (10k) and the 100 nF alternate CT cap.

## Open issues / risks
1. **I2C MACID path is unverified.** The slave address and whether it works on a blank eFuse are unknown. Bench-test early.
   The host-tool fallback always works.
2. ~~3.3 V supply PWM ≥ 1 MHz~~ — resolved: +3V3 is already the TPS62933**F** (FCCM, 1.2 MHz) on power_rails.
3. **RTL QFN-56 footprint:** EP is 4.7 mm in the easyeda import vs 4.5 mm (J/K) in the datasheet. Pads are 0.15 mm at
   0.35 mm pitch. Check paste and mask.
4. **Magjack stock (111)** is low. Order early, or switch footprint to C19725141.
5. **LED functions/polarity** depend on eFuse defaults of the delivered chips. Firmware can only observe, not set them, unless
   the host driver or PG tool programs the LED registers.
6. **Thermal:** about 1 W worst case in a 6×6 QFN, θJA 19 °C/W on Realtek's 4-layer board, gives about +20 K. The DS notes
   the PHY masks 2.5G when it overheats. TMP1075 U1206 sits between the QFN and the jack.
