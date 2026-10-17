# odock-10 — Display & UI sheet (`display_ui.kicad_sch`, refs 1100+)

Source: `hardware/odock-10/sheets/display_ui.py` (generated, netlist-verified). References:
- HS20HS072RX datasheet (Hansheng, V1.0, LCSC C5329582): sec. 3 electrical, sec. 5 outline, sec. 6 interface, sec. 8 SPI
  timing.
- Hirose FH34SRJ catalog (2019-08): connector dimensions, recommended PCB pattern and FPC dimensions.
- ALPS SKRT series data, TI TPD4E02B04 datasheet.

Stock figures are from the JLC parts API on 2026-10-02.

## Block

```
LCD_CS_N/DC/SCK/MOSI/RST_N ──► J1103 FH34SRJ 12P FPC ══ U1101 HS20HS072RX (ST7789, 4-wire SPI, hand-fitted) ◄── +3V3 (4.7 µF + 100 nF)
+5V ── R1101 39R 1206 ── LED-A   LED-K ── Q1101 AO3400A ── GND;  LCD_BL_PWM ── 100R ── gate, 100k PD
BTN_A_N / BTN_B_N ── SKRTLAE010 side-push to GND, 10k PU, 10 nF
HDR_GPIO0..7 ── 220R ─┬─ J1101 2x8 (unpopulated)       +5V ── F1101 0.5 A PTC ── +5V_USR  ─┐
HDR_ADC0/1 ─┬ 10k ─┤   TPD4E02B04 x3 at the pins     +3V3 ─ F1102 0.5 A PTC ── +3V3_USR ─┴─ header pins 1/2, Qwiic
I2C_EXT_SDA/SCL ──────── J1102 JST SH 4-pin (Qwiic), TPD4E02B04
```

## LCD (U1101, connector J1103)
- **HS20HS072RX (C5329582)**: 2208 in stock, $3.59. **Not assembled by JLC** (`dnp`, kept in the BOM so it gets
  ordered): it is plugged into J1103 by hand after assembly.
  - 2.0" a-Si IPS, 240×320 (the datasheet's "2.4"" is a typo; the outline says 2.0"), RGB, 262k colours.
  - The controller is an **ST7789** (the datasheet says ST7789T3 in one place and ST7789V2 in another; both use the
    same command set).
- **The FPC pinout (datasheet sec. 6) matches the LCSC symbol**. The J1103 column is the connector contact each panel pin lands
  on after the fold (see below):

| Panel pin | Name | Net | J1103 pin | Notes |
|---|---|---|---|---|
| 1 | GND | GND | 12 |  |
| 2 | CS | LCD_CS_N | 11 |  |
| 3 | RS | LCD_DC | 10 | Data/command |
| 4 | SCL | LCD_SCK | 9 | Via 33R on mcu |
| 5 | SDA | LCD_MOSI | 8 | Via 33R on mcu. Write-only |
| 6 | RST | LCD_RST_N | 7 |  |
| 7 | NC | — | 6 |  |
| 8 | I/O-VCC | +3V3 | 5 | 1.65–3.3 V recommended (see below) |
| 9 | VCC | +3V3 | 4 | 2.4–3.3 V recommended (see below) |
| 10 | A | LCD_BL_A | 3 | Backlight anode |
| 11 | K | LCD_BL_K | 2 | Backlight cathode |
| 12 | GND | GND | 1 |  |

- **Supply: known deviation.** +3V3 is set to 3.33 V (power_rails 31.6k/10k) and can reach about 3.36 V with resistor
  tolerance. That is marginally above the panel's 3.3 V recommended maximum for VCI and IOVCC (abs max 4.6 V). Accepted as
  common practice. Retrimming +3V3 to 3.30 V on power_rails would remove it; the RP2350 accepts 3.135–3.63 V.
- **SPI mode.** The module fixes the interface to 4-wire SPI internally. There are no IM pins on the FPC, so no straps are
  needed.
  - Timing (sec. 8): write clock ≥ 66 ns, so ~15 MHz is guaranteed. ST7789 parts typically run at 62.5 MHz from the RP2350;
    tune in firmware.
  - Logic thresholds are 0.3/0.7 IOVCC at 3.3 V.
- **FPC connector J1103: Hirose FH34SRJ-12S-0.5SH(50) (C424659)**: 14k in stock, $0.21 (extended). Project-lead decision,
  replacing the soldered tail (old open issue 1).
  - 0.5 mm pitch, **top and bottom (dual) contact**, back-flip lock, **1.0 mm above the board**, 8.0 × 3.8 mm.
  - It takes **0.3 ± 0.03 mm FPC** with a 6.5 mm wide 12-way tail (Hirose dimension G = 6.5). The panel tail is 0.3 mm thick
    with its stiffener and 6.5 mm wide, so it fits as is. The 5 mm stiffener is longer than Hirose's 2.5 mm, which only stiffens
    the part of the tail outside the connector. The tail has 3.5 mm of exposed gold against Hirose's 1.5 mm uncovered area, so
    ≈ 2 mm of contacts stays outside the opening. They face the PCB, so keep the copper under them covered by solder mask
    (no exposed pads or untented vias).
  - Why this part: it is the only dual-contact part with a low profile in JLC stock, so the contact side is not a risk. Other
    options: XUNPU FPC-05FB-12PH20 (C2856829, dual contact but 2.0 mm high) and JUSHUO AFC01-S12FCA-00 (C262661, 2.0 mm,
    single contact). Neither fits under the panel.
  - Footprint `odock:FFC-SMD_12P-P0.50_FH34SRJ-12S-0.5SH` is the EasyEDA import, corrected to the Hirose recommended pattern:
    - Signal pads 0.3 × 0.8 at 0.5 mm pitch (B = 5.5). The import had 0.9 mm.
    - Tabs 0.4 × 0.8, E = 7.1 / F = 7.9. The import had 0.6 × 1.2.
    - 3.3 mm from the outer edge of the signal pads to the outer edge of the tabs. The import had 3.45.
    - Courtyard now covers the body and tabs plus 0.25 mm. F.Fab body outline and silk pin-1 dot added.
    - The signal pads are at the rear (actuator side, −Y) and the FPC opening is at +Y. **Seen from the top with the opening
      at +Y, contact 1 is at +X** (Hirose drawing; pad 1 at +2.75).
- **Panel footprint**: `odock:LCD_HS20HS072RX_Outline` is a mechanical outline with **no pads**, `exclude_from_pos_files`.
  - All U1101 pins are NC in the schematic. The signals are carried by J1103, so pcbnew sees no pads without a net.
  - F.Fab shows the panel (front view, origin at the panel centre), the active area, the unfolded and folded tail, and where
    J1103 goes. Cmts.User shows the foam-tape window. Silk has corner marks for placing the panel.
- **Fold geometry** (front view = PCB top view, panel portrait, tail edge at the bottom):
  - The tail leaves the **bottom (short, 36.2 mm) edge**: left edge 15.28 mm from the panel's left side, 6.5 mm wide, 20.7 ±
    0.5 mm long. Seen from the front, panel pin 1 is on the left (centre 15.78 mm from the left side).
  - The contacts are on the panel's front side, and the stiffener is on the back.
  - The tail folds 180° under the panel about an axis parallel to that edge. A fold keeps X positions, so **pin 1 stays on
    the left (−X)**. The contacts now **face the PCB** (bottom contact, which the dual-contact connector accepts), and the tail
    runs back under the panel (−Y).
  - J1103 sits **under the panel**, rotation 0, so its opening faces the tail edge. Contact 1 is then at +X, the side where
    panel pin 12 arrives. So **panel pin n lands on J1103 contact 13 − n**, and the schematic maps J1103 that way. Each net
    still reaches the same panel pin as before (J1 GND … J12 GND, J2 LED-K, J4 VCI, J11 CS).
  - Placement in the panel footprint's frame: J1103 origin at **(+0.43, +9.6) mm** from the panel centre. That puts the housing
    opening **14.5 mm inside the tail edge**, and the J1103 contacts line up with the tail (centre 18.53 mm from the left side).
  - Tail budget:
    - The tail leaves the panel ≈ 1.0 mm above its back, so ≈ 2.5 mm above the PCB. The FPC slot is ≈ 0.5 mm high, so the
      fold is a ≈ 2 mm diameter loop: 0.3 mm straight, then ≈ 3.1 mm of bend.
    - About 1.8 mm of the tail goes into the connector.
    - With the shortest tail (20.2 mm), the opening falls ≈ 14.6 mm inside the edge. Longer tails make the loop bulge
      outward instead.
    - The loop sticks out **≈ 1.3–2 mm past the panel's bottom edge**. Leave ≥ 3 mm there in the enclosure and the board
      outline.
  - **Foam tape must be ≥ 1.3 mm; use 1.5 mm.** J1103 is 1.0 mm high under the panel back, so the old "~1 mm" no longer works.
    Leave a window over J1103 and the tail path, open to the tail edge (Cmts.User on the outline footprint, ≈ 9.2 × 18.9 mm).
    No other parts may sit under the panel.
  - Assembly by hand, after reflow:
    1. Apply the foam tape.
    2. Hold the panel face down beyond the tail edge, so the tail lies flat on the PCB with the contacts down.
    3. Slide the tail into J1103 and close the back-flip actuator. It is at the rear of J1103, still reachable at this point.
    4. Swing the panel over its tail edge onto the foam.
  - Check against a sample panel: the tail exit height, the measured tail length and the loop size. Adjust the J1103 Y
    position before layout freeze.
- **Mechanical** (sec. 5):
  - Outline 51.8 × 36.2 × 2.05 mm, active area 40.8 × 30.6 mm. The AA top edge is 2.64 mm below the top of the outline, and
    the AA is centred left to right.
  - The tail is 0.3 mm thick with a 5 mm stiffener behind the fingers.
  - The panel mounts on **1.5 mm double-sided foam tape**, with the window described above.

## Backlight
- 4 white LEDs in parallel: Vf 3.0 V typ (2.8–3.2) at 80 mA total, 80 mA abs max (sec. 3.2).
- **From +5V through R1101 39 Ω 1 % 1206 (C22198, UNI-ROYAL 1206W4F390JT5E, 94k in stock)**, with low-side switch
  **Q1101 AO3400A** (C20917, basic). It was 33 Ω; mcu_ui review #3 showed that bus-powered +5V (laptop vSafe5V, up to
  5.5 V) would push 82 mA through 33 Ω.
  - Typical, external power (+5V = 5.13 V, Vf 3.0 V): (5.13 − 3.0)/39 = **55 mA**. Bus-powered at 5.0 V: 51 mA.
  - **Worst case** (+5V = 5.5 V, Vf 2.8 V): **69 mA**; 72 mA even at Vf 2.7 V (hot LEDs). Under the 80 mA abs max.
  - Minimum (4.75 V, Vf 3.2 V): 40 mA.
  - PWM does not help the abs-max case, because the peak current is what matters.
  - R1101 dissipates ≤ 0.19 W (1206 is rated 0.25 W). Backlight power is about 0.28 W at 100 %.
  - +3V3 is not used: with only 0.1–0.5 V of headroom, the current would track Vf spread.
- Gate drive: LCD_BL_PWM (GPIO25, PWM4 B) through 100 Ω.
  - R1103 100k pulls the gate down, so the backlight is off while the RP2350 is unpowered, in reset or in BOOTSEL.
  - The AO3400A Vgs(th) is ≤ 1.45 V, giving < 50 mΩ at 3.3 V gate drive.
- Firmware: PWM at ≥ 20 kHz, so it is inaudible, with dimming on inactivity.

## User buttons (SW1101, SW1102)
- **ALPS SKRTLAE010 (C110293)**: 87k in stock, $0.14. Side-push, 4.5 × 3.4 × 3.3 mm, 1.6 N, sharp feel, guide bosses
  (2 × Ø0.9 mm holes).
  - It mounts on the **front edge** with the actuator just past the board outline, so the buttons are pressed from the front
    like a device's side keys.
  - Pins 1/3 are common and go to GND. Pin 2 is the contact (BTN_x_N). Pins 4/5 are the metal mounting tabs, tied to GND.
- Each button has a 10k pull-up to +3V3 and a 10 nF cap. The 100 µs RC filters ESD and bounce; firmware debounces too.
- Active low, on GPIO32/33.
- The functions are defined in firmware. Default: A = per-port forced-5V toggle, B = LCD page.
- Rejected: TS-1088R-02026, which turned out to be a top-push 3×4 switch despite the "R". Its symbol and footprint were
  imported into hardware/lib but are unused.

## User GPIO header (J1101, unpopulated)
- 2×8 2.54 mm, `PinHeader_2x08_P2.54mm_Vertical`, **`in_bom no`**.
- The protection is populated, so a user-soldered header is safe:
  - 220 Ω series on HDR_GPIO0..7 (R1106–R1113).
  - **10k + 10 nF on HDR_ADC0/1** (R1114/R1115, C1108/C1109 at the RP2350 side, as for ISENSE). The ADC pins are not
    fault tolerant: a user's 3.3 V source applied with the deck off now pushes ~0.3 mA (was 2.7 mA with 1k) through the
    GPIO44/45 clamp into +3V3. The 10 nF is the ADC's charge reservoir.
  - TPD4E02B04 ESD arrays (D1101–D1103) at the header pins.
  - **PTC fuses** F1101 (+5V → +5V_USR) and F1102 (+3V3 → +3V3_USR): Bourns MF-NSMF050-2, 0.5 A hold / 1 A trip,
    0.15–0.7 Ω. +3V3_USR also feeds the Qwiic port, and F1102 protects the shared +3V3 rail from user shorts.
- Pinout (planned for silkscreen on top and an annotated table on the back):

| Pin | Signal | Pin | Signal |
|---|---|---|---|
| 1 | +5V (fused) | 2 | +3V3 (fused) |
| 3 | GPIO12 (HDR_GPIO0) | 4 | GPIO13 |
| 5 | GPIO14 | 6 | GPIO15 |
| 7 | GND | 8 | GND |
| 9 | GPIO16 | 10 | GPIO17 |
| 11 | GPIO18 | 12 | GPIO19 (HDR_GPIO7) |
| 13 | ADC4 (GPIO44, HDR_ADC0) | 14 | ADC5 (GPIO45, HDR_ADC1) |
| 15 | GND | 16 | GND |

- GPIO12–19 are contiguous for PIO. What is actually free for the header (DS table 677 against the GPIO allocation):
  - **SPI1** (12–15), **PWM** slices 6/7/0/1, the third PIO block (**PIO2**), and **HSTX**.
  - Not free: UART0 is the debug console (GPIO0/1), SPI0 is the LCD, I2C0 is I2C_PD and I2C1 is I2C_SYS.
  - HSTX is usable for slow/custom serial output, but **not for DVI**: DVI breakouts expect to drive TMDS through their own
    ~270 Ω resistors, and the 220 Ω series resistors plus the ESD capacitance make it unlikely to work. Do not print "DVI"
    on the silkscreen.
- **The header is 3.3 V logic.** The FT pads survive 5.5 V with +3V3 up (≤ 3.63 V with the deck off), but the TPD4E02B04
  has VRWM 3.6 V and its leakage at 5 V is unspecified. Treat 5 V as abuse, not a feature.
- The 5V and 3V3 header pins are outputs. Back-feeding the deck through them is not supported.

## Qwiic (J1102)
- **JST SM04B-SRSS-TB(LF)(SN) (C160404)**: 35k in stock, $0.26. The XYECONN clone C51940130 at $0.04 also exists.
- Pins: 1 GND, 2 +3V3_USR, 3 I2C_EXT_SDA, 4 I2C_EXT_SCL. Pads 5/6 are mounting tabs, tied to GND.
- The I2C_EXT pull-ups (4.7k) are on the mcu sheet. The bus is PIO I2C on GPIO30/31 and is separate from I2C_SYS, so a bad
  Qwiic device cannot hang the sensor/PD bus.
- ESD: D1104 on SDA/SCL. 100 nF at the connector.

## Part list (this sheet)

| Ref | Part | LCSC | Type | Stock | Qty |
|---|---|---|---|---|---|
| U1101 | HS20HS072RX LCD (DNP, hand-fitted) | C5329582 | ext | 2208 | 1 |
| J1103 | Hirose FH34SRJ-12S-0.5SH(50) | C424659 | ext | 14k | 1 |
| Q1101 | AO3400A | C20917 | basic | 959k | 1 |
| R1101 | 39 Ω 1 % 1206 | C22198 | ext | 94k | 1 |
| SW1101, SW1102 | ALPS SKRTLAE010 | C110293 | ext | 87k | 2 |
| D1101–D1104 | TPD4E02B04DQAR | C106794 | ext | 106k | 4 |
| F1101, F1102 | MF-NSMF050-2 | C75464 | ext | 62k | 2 |
| J1102 | SM04B-SRSS-TB | C160404 | ext | 35k | 1 |
| R1106–R1113 | 220 Ω 0402 | C25091 | basic | 1.4M | 8 |
| R1104, R1105, R1114, R1115 | 10k 0402 | C25744 | basic | — | 4 |
| R1102 / R1103 | 100 Ω / 100k 0402 | C25076 / C25741 | basic | — | 2 |
| C1103, C1104, C1108, C1109 | 10 nF 0402 | C15195 | basic | — | 4 |
| C1101 | 4.7 µF 0402 | C23733 | basic | — | 1 |
| C1102, C1105–C1107 | 100 nF 0402 | C1525 | basic | — | 4 |
| J1101 | 2×8 header | — | not in BOM | — | — |

`tools/bom_check.py`: all OK.

## Nets
- Global nets used:
  - Rails: `+3V3`, `+5V`, `GND`.
  - LCD: `LCD_SCK/MOSI/CS_N/DC/RST_N/BL_PWM`.
  - UI: `BTN_A_N/BTN_B_N`, `HDR_GPIO0..7`, `HDR_ADC0/1`, `I2C_EXT_SCL/SDA`.
- Local nets: +5V_USR, +3V3_USR, HDR_P0..7, HDR_A0/1, LCD_BL_A/K, BL_GATE.
- **No new inter-sheet nets are needed.**

## Open issues
1. **FPC attach: resolved.** The panel plugs into J1103 (FH34SRJ, dual contact) and is hand-fitted. Panel pin n goes to J
   pin 13 − n. Foam tape is now 1.5 mm.
2. Check the fold loop, the tail exit height and the J1103 Y offset (14.5 mm inside the tail edge) against a sample panel
   before layout freeze.
3. Panel current consumption is "TBD" in the datasheet. Budget ~10 mA from +3V3 plus 55 mA (≤ 69 mA) from +5V for the
   backlight.
4. Check the button footprint (LCSC import, `KEY-SMD_SKRTLAE010`) against the ALPS land pattern. The ALPS drawing has a
   keep-out between the pads, which must be free of copper.
5. If enclosure designs need top-press buttons, swap SW1101/SW1102 for TS-1187A (C318884). It is the same circuit.
