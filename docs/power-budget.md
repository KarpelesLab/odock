# odock-10 — Power budget

Draft estimates (2026-10-02) from datasheet typicals/maxima and research notes; to be replaced by
measurements from the prototype's instrumentation (INA226/INA228 + TMP1075 probes).

## Internal loads (deck electronics)

| Load | Rail | Typ (W) | Max (W) | Notes |
|---|---|---|---|---|
| USB7206C hub | 3.3 V + 1.15 V | 1.0 | 1.8 | all ports at 10G |
| RTL8156BG 2.5GbE | 3.3 V + core | 0.6 | 1.0 | 2.5G link, traffic |
| GL3224 card reader | 3.3 V (int. regs) | 0.2 | 0.4 | |
| SD + microSD cards | 3.3 V | 0.2 | 1.0 | UHS-I cards under load |
| TUSB1064 + TUSB1046 | 3.3 V | 0.5 | 1.0 | USB 10G + 2-lane DP active |
| PMG1-S3 + TPS26750 | 3.3 V / VBUS | 0.1 | 0.2 | |
| RP2350B + flash | 3.3 V / 1.1 V | 0.1 | 0.2 | |
| LCD (backlight on) | 3.3 V | 0.2 | 0.3 | firmware dims/turns off |
| Sensors, EEPROMs, LEDs | 3.3 V | <0.05 | 0.1 | |
| **Subtotal** | | **~2.9** | **~6.0** | |
| Rail conversion losses (3.3/1.15/1.2 V bucks, ~88 %) | | 0.4 | 0.8 | |
| **Internal total (from 5 V rail)** | | **~3.3** | **~6.8** | |

## Downstream port loads (5 V rail)

| Port | Normal | Charge mode / max |
|---|---|---|
| USB-A #1 | 4.5 W (0.9 A) | 7.5 W (1.5 A, BC1.2 DCP) |
| USB-A #2 | 4.5 W (0.9 A) | 7.5 W (1.5 A) |
| Downstream USB-C | 7.5 W (1.5 A) | 15 W (3 A) |
| **Total** | 16.5 W | **30 W** |

5 V rail max ≈ 30 + 6.8 ≈ **37 W (7.4 A)** → LM5148 sized for 8 A; ~93 % → ~2.8 W loss.

## Laptop output

| Contract | Out | Buck-boost in (~96.5 %) | Loss |
|---|---|---|---|
| 140 W EPR (28 V × 5 A) | 140 W | 145 W | ~5 W + ~0.5 W path |
| 100 W SPR (20 V × 5 A) | 100 W | 104 W | ~3.5 W |
| 60 W (20 V × 3 A) | 60 W | 62 W | ~2 W |

## Worst case total (everything maxed, 140 W to laptop)

- Input: 145 (laptop) + 37 / 0.93 (5 V rail) + ~1 (input path, sensing) ≈ **186 W**
- **Heat on board ≈ 5.5 (buck-boost + path) + 2.8 (5 V buck) + 6.8 (electronics) + ~1 ≈ 16 W**
  (port loads' power leaves the board; internal electronics' power does not).
- Typical (laptop at 60–100 W, ports lightly used): ~7–9 W heat.

## Laptop budget per input source

Laptop gets `input capability − 5 V rail draw / 0.93 − margin`, renegotiated live by PMG1 (on RP2350 request).

| Input | Available | Laptop, ports idle | Laptop, ports maxed |
|---|---|---|---|
| PD-in 240 W (48 V × 5 A) | 240 W | 140 W | 140 W |
| PD-in 140 W (28 V × 5 A) | 140 W | ~125 W → offer 100 W SPR or EPR at reduced current | ~95 W |
| PD-in 100 W (20 V × 5 A) | 100 W | ~90 W | ~55 W |
| PD-in 65 W | 65 W | ~55 W | ~20 W |
| Barrel 24 V × 8 A | 192 W | 140 W | 140 W |
| Barrel 19.5 V × 7.7 A (150 W brick) | 150 W | 135 W | ~105 W |
| Barrel 12 V × 5 A | 60 W | ~50 W | ~15 W |
| Bus-powered (laptop supplies 5 V × 3 A) | 15 W | — | — |

Barrel capability is unknown (no negotiation): start conservative, raise while VIN holds, back off on sag
(see requirements). Optional solder-jumper/firmware setting for PSU size.

## Bus-powered mode (15 W from laptop)

Internal ≈ 3.3 W typ / 6.8 W max leaves **~8 W** for downstream:
- USB-A: 0.9 A default, current-limited; no charge mode
- Downstream USB-C: advertise 5 V × 1.5 A max (or default USB), reduced if needed
- Firmware enforces a total budget; LCD shows "bus powered" + remaining budget.

## Thermal implications
- 16 W worst case is too much for a bare 100×60 mm board → board will likely grow, and firmware derates
  (laptop contract first, then charge-mode ports) based on TMP1075 readings.
- Keep buck-boost (5.5 W) and 5 V buck (2.8 W) apart from each other, from the LCD, and from the hub.
