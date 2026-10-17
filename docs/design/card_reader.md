# odock-10 — Card reader sheet (`card_reader.kicad_sch`, ref 900)

Source: `hardware/odock-10/sheets/card_reader.py`. Genesys **GL3224-ONY04** (QFN-48, 2 LUN) on USB7206C hub port 1. It
drives a full-size SD socket (slot 1) and a microSD socket (slot 2).

```
CR_SS_TXP/N (hub TX, 220 nF on usb_hub) ──────────► RXP/RXN 11/10
CR_SS_RXP/N ◄── 100 nF ◄── TXP/TXN 8/7                     GL3224-ONY04 (U901)
CR_DP/CR_DN ──────────────── DP/DM 5/4                      ROM firmware, internal POR
+5V ── VBUS 22 ─► int. LDO ─► CR_3V3 (25; AVDD33 6/15, DVDD33 34/44) ─► int. LDO ─► CR_1V2 (26; AVDD12 9)
25 MHz (YXC 3225) X1/X2 13/14     RTERM 16 ── 680 Ω 1 %      SPI_MISO 10k PU (ROM boot), SPI_CK DNP 10k PD
S1M1_VCC 23 ─ CR_SD_VCC ─► SD-111  VDD      S1 CLK/CMD/D0-3, SD1_CDZ ◄─ CD sw, SD1_WP ◄─ WP sw
S2M2_VCC 24 ─ CR_USD_VCC ► DM3AT   VDD      S2 CLK/CMD/D0-3, SD2_CDZ = MS2_INS/SD2_WP ◄─ detect sw
SD1_CDZ ─ 1k ─► CR_CD_SD_N    SD2_CDZ ─ 1k ─► CR_CD_USD_N    LED 21 ─ 1k ─► CR_LED  (+ DNP bench LED)
```

## Choices

### GL3224-ONY04 (C157358, 1646 in stock)
- **It is USB 3.1 Gen1 (5 Gbps), not 10G** (DS rev 1.11 ch. 1–2), so hub port 1 trains at 5 Gbps.
  - That is about 400 MB/s usable, against UHS-I SDR104 at 104 MB/s per card, so it is not a bottleneck.
  - No Gen2 card reader is in JLC stock.
- Runs from ROM. **No SPI flash fitted**:
  - SPI_MISO has a 10 kΩ pull-up to CR_3V3, so a missing flash reads 0xFF and the chip boots from ROM.
  - SPI_CS and SPI_MOSI are NC.
  - SPI_CK has a DNP 10 kΩ pull-down. This is the Genesys ROM-option strap: pull-down = SSC on the card clock, for EMI
    tuning.
  - A flash footprint is not worth it. Updates go through Genesys' MP tool only, and the RP2350 does not need it.
- No reset pin; the chip has an internal POR (DS fig. 5.2: 95 ms from reset release to USB ready).
- MS (Memory Stick) is not supported by our sockets. S1D4–S1D7 (MMC 8-bit) are NC.

### Power
- The only supply is **+5V on VBUS** (4.75–5.25 V; +5V is about 5.11 V).
- The internal 5 → 3.3 V LDO output is DVDD33 pin 25, which feeds the local net CR_3V3 (AVDD33 6/15, DVDD33 34/44). The
  internal 3.3 → 1.2 V LDO output is DVDD12 pin 26, which feeds CR_1V2 (AVDD12 9).
  - These nets are **local** and must never be tied to +3V3.
- Decoupling follows the Genesys GL3224(E) QFN48 demo board V3.00 and the open GL3224 designs (wuxx/SD-Reader-GL3224,
  OSHWHub):

  | Pin(s) | Cap |
  |---|---|
  | VBUS 22 | 10 µF + 100 nF |
  | CR_3V3 at pin 25 | 10 µF |
  | AVDD33 6 | 1 µF + 100 nF |
  | AVDD33 15, DVDD33 34, 44 | 100 nF each |
  | AVDD12 9 | 2.2 µF |
  | DVDD12 26 | 1 µF |
  | VUHS_1 43, VUHS_2 33 (internal SD IO 3.3/1.8 V for UHS-I) | 1 µF each |
  | Card VCC (S1M1_VCC 23, S2M2_VCC 24; on-chip card power FETs) | 4.7 µF + 100 nF each, at the socket |

- Card VCC is kept below the 10 µF some designs use, so the internal LDO dips less at card power-on.
- Budget:
  - GL3224 draws 147 mA in SS U0 active (DS table 5.3). Each UHS-I card draws up to about 200 mA. Everything runs through
    the internal LDO.
  - Worst case is (5.11 − 3.3) V × ~0.35–0.55 A ≈ 0.6–1.0 W in the QFN. θJA is 33 °C/W, giving +20…33 K.
  - The power budget lists 0.4 W for the chip plus 1.0 W for the cards; the LDO loss sits inside those numbers.
  - The thermal pad needs a via array to inner GND.

### Clock, USB, RTERM
- 25 MHz crystal: YXC X322525MOB4SI (C9006, JLC basic, the same as the hub). CL is 12 pF with 2 × 20 pF.
  - The GL3224 only needs ±300 ppm (25 MHz ± 0.03 %).
  - The Genesys demo board V3 removed its crystal option. Crystal-less operation is not documented for the -ONY04, so
    the crystal stays.
- RTERM: 680 Ω 1 % (UNI-ROYAL 0603WAF6800T5E 0603, C23228) to GND, as DS table 3.1 recommends.
- AC coupling, following integration item 14 (the transmitter side owns the cap):
  - Hub TX → CR_SS_TX* (220 nF on usb_hub) → GL3224 RX directly.
  - GL3224 TX → **100 nF** here → CR_SS_RX* → hub RX.
  - **100 nF, not 220 nF**, because the GL3224 is a Gen1 transmitter, and Gen1 allows C_AC_COUPLING of 75–200 nF. The
    open-source GL3224 boards also use 100 nF.
  - The hub-side 220 nF is fine because the USB7206C is a Gen2 transmitter (75–265 nF).
- USB2 D+/D− go to the hub directly.
- Embedded link, so no ESD on the USB lines. The hub straps port 1 as non-removable.

### Sockets
- **Full-size SD: Hanbo SD-111** (C410353, 5209 in stock), push-push.
  - From the Hanbo drawing, the **CD** switch (pin 10) closes to VSS1 (pin 3) when a card is inserted.
  - The **WP** switch (pin 11) closes to GND when the card is **unlocked**. It is open when the card is locked or no card
    is present.
  - This matches the GL3224 directly. SD1_CDZ: 0 = card. MS1_INS/SD1_WP has a 46 kΩ pull-up: 0 = write enable,
    1 = write protect.
  - With no card, pin 2 is high, so the ROM never sees a false Memory Stick insert.
- **microSD: Hirose DM3AT-SF-PEJM5** (C114218, 16 792 in stock), push-push.
  - The detect switch is normally open between SW_A (GND) and SW_B (CR_USD_CDZ).
  - Shell pads 10, 12, 13 and 14 go to GND.
  - **Pin 35 MS2_INS/SD2_WP is tied to `CR_USD_CDZ`** (review data #1). It is a shared pin: as Memory Stick insert
    detect, 0 means card inserted (GL3224 DS Table 3.1).
    - The old tie to GND made slot 2 permanently report "MS inserted". The internal pull-up alone would report every
      microSD as write-protected.
    - With the tie to CR_USD_CDZ: no card → high, so no MS and no WP. Card → low, so SD present and write enabled.
      This is the same state slot 1 has with an unlocked SD.
    - The two 46 kΩ internal pull-ups in parallel (≈ 23 kΩ) are fine.
- CMD/DAT pull-ups: the GL3224 has internal 15 kΩ pull-ups on CMD and D[3:0] (DS table 5.3), so there are no external
  resistors.
- No ESD array on the card lines, which follows every reference design. The GL3224 is rated 4 kV HBM. Any array would load
  the 208 MHz SDR104 clock; see open issues.

### Card detect → TCA9534, activity → RP2350
- The GL3224 needs both CD switches itself (SD1_CDZ / SD2_CDZ), so the switches connect to the GL3224. The **TCA9534
  I/O expander** (mcu, P3/P4) taps the same nodes through 1 kΩ, onto `CR_CD_SD_N` and `CR_CD_USD_N`.
  - The TCA9534 has no internal pulls (DS §8) and is 5 V tolerant, so the old "RP2350 pulls off" rule no longer
    applies.
  - The 1 kΩ limits current if the pin is ever mis-configured as an output against a closed switch.
  - CR_3V3 exists whenever +5V exists, and +3V3 is made from +5V, so there is no back-powering path.
- `CR_LED`: the GL3224 LED output (push-pull 3.3 V, active high) goes through 1 kΩ to an RP2350 GPIO, and the LCD shows
  activity.
  - A DNP 1 kΩ + green 0805 LED is provided for bench use.

## Part list (this sheet)

| Ref | Part | LCSC | JLC stock (2026-10-02) | Type | Qty |
|---|---|---|---|---|---|
| U901 | Genesys GL3224-ONY04 QFN-48 | C157358 | 1646 | ext | 1 |
| J901 | Hanbo SD-111 full-size SD push-push | C410353 | 5209 | ext | 1 |
| J902 | Hirose DM3AT-SF-PEJM5 microSD push-push | C114218 | 16 792 | ext | 1 |
| Y901 | YXC X322525MOB4SI 25 MHz 3225 | C9006 | 199 410 | basic | 1 |
| R901 | UNI-ROYAL 0603WAF6800T5E 680 Ω 1 % 0603 | C23228 | 2 389 645 | basic | 1 |
| R902, R903 (DNP) | 10 kΩ 0402 | C25744 | 21 M | basic | 2 |
| R904–R906, R907 (DNP) | 1 kΩ 0402 | C11702 | 7.2 M | basic | 4 |
| D901 (DNP) | KENTO KT-0805G green LED | C2297 | 3.1 M | basic | 1 |
| C901 | 10 µF 25 V 0805 | C15850 | 4.9 M | basic | 1 |
| C903 | 10 µF 10 V 0603 | C19702 | 10 M | basic | 1 |
| C909 | 2.2 µF 0402 | C12530 | 5.1 M | basic | 1 |
| C913, C915 | 4.7 µF 0402 | C23733 | 2.4 M | basic | 2 |
| C904, C910–C912 | 1 µF 0402 | C52923 | 5.6 M | basic | 4 |
| C902, C905–C908, C914, C916–C918 | 100 nF 0402 (decoupling + 2× TX AC caps) | C1525 | 21 M | basic | 9 |
| C919, C920 | 20 pF C0G 0402 | C1554 | 657 k | basic | 2 |

`tools/bom_check.py`: 149 unique parts across the project, 0 failing, 0 without LCSC.

## Open issues
1. **No official GL3224 SD reference schematic** was available; the datasheet has no application circuit.
   - Decoupling and pin usage come from the Genesys eMMC demo board (same QFN48) and two working open designs.
   - Ask Genesys or the LCSC FAE for the SD/microSD reference before layout, especially about card-VCC capacitance and
     whether VUHS needs 1 µF or 0.1 µF.
2. **Thermal.** The internal LDO burns up to about 1 W with two UHS-I cards active.
   - Option (seen on OSHWHub "GL3224_DUALTF"): an external 3.3 V buck onto DVDD33, back-driving the internal LDO.
   - That is undocumented, so it is not done here. Revisit with prototype temperature data (place a TMP1075/NTC nearby).
3. **+5V in bus-powered mode** must stay ≥ 4.75 V at the GL3224 (integration item 2).
4. **Footprints.** Check the SD-111 easyeda footprint (NPTH pegs, WP/CD pad positions) and the DM3AT (shell pads 10, 12,
   13, 14 and switch pads 9/11) against the manufacturer land patterns. The GL3224 EP is 5.1 mm (QFN-48 7×7).
5. **Card-line ESD / series termination.** None is fitted. If SDR104 shows ringing on the bench, add 22–33 Ω series
   resistors on CLK; a 0402 footprint could be added at layout.
6. **Firmware (RP2350):** CD inputs on TCA9534 P3/P4. Optionally clear BC1.2 on hub port 1 (usb_hub already plans
   `BC_CONFIG_P1` = 0).

No new inter-sheet nets are needed. The mcu sheet reads CR_CD_SD_N and CR_CD_USD_N on the TCA9534, and CR_LED on an
RP2350 GPIO with pulls disabled.
7. **Bench: MS-vs-SD priority** (review data #1 and #7). Both slots rely on the GL3224 ROM giving SDx_CDZ = 0 priority
   over MSx_INS = 0, and the DS does not state that priority. Test: an unlocked SD in slot 1 and a microSD in slot 2 must
   each enumerate as a writable SD, not as MS. If either fails, add an inverter or strap and ask the Genesys/LCSC FAE.
