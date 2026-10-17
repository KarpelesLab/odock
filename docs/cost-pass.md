# odock-10 — JLC extended-part cost pass (2026-10-02)

JLC charges ~$3 per unique **extended** (non-basic) LCSC part per assembly order. This pass swapped every
generic passive that has a JLC **basic** equivalent with equal-or-better specs (same value, same or larger
voltage/power rating, same-or-better dielectric/tolerance/TCR), and merged duplicate extended parts.
Net connectivity is unchanged (`build_all.py`: netlist verify OK); `tools/bom_check.py`: 0 failing.

## Result

| | Before | After | Delta |
|---|---|---|---|
| Unique LCSC parts | 187 | 181 | −6 |
| Extended unique parts | 129 | 114 | **−15** |
| Extended-part fee per order | ~$387 | ~$342 | **−$45 / order** |
| Parts cost per board (qty-1 prices) | $161.91 | $161.88 | −$0.03 |

The JLC basic library is now small (e.g. 0402 resistors: ~30 basic values, all E6/E12-ish; no basic
zener, NTC, PTC, dual FET, power inductor, ≥ 0.1 µF/100 V ceramic below 0805, or 2512 resistor), so most
remaining extended parts are ICs, connectors, power parts or precision values with no basic equivalent.

## Swaps

| Ref(s) | Old LCSC | New LCSC (basic unless noted) | Why equivalent |
|---|---|---|---|
| C102, C103, C112, C115, C116, C124, C214, C305, C306, C502 | C15725 CL10B104KC8NNNC 100 nF 100 V X7R **0603** | C28233 CL21B104KCFNNNE 100 nF 100 V X7R **0805** | Same C/V/dielectric/tolerance; no basic 100 V 100 nF in 0603, so footprint 0603→0805 (HV decoupling, power zone not space-critical). |
| C243 (OVP_DIV filter) | C1531 2.2 nF 50 V X7R 0402 | C1604 2.2 nF 50 V X7R **0603** | Same value/V/X7R; node < 3 V. |
| C239 (SNK_DVDT) | C1536 3.3 nF 50 V X7R 0402 | C1613 3.3 nF 50 V X7R **0603** | Same value/V/X7R; dV/dt pin is low voltage. |
| C223 (LM51770 COMP zero) | C1542 6.8 nF 50 V X7R 0402 | C1631 6.8 nF 50 V X7R **0603** | Same value/V/X7R; keep it next to the COMP pin. |
| C837 (ETH magnetics CT) | C76967 GRM1555 390 pF C0G 50 V 0402 | C282239 CC0402JRNPO9BN391 390 pF C0G 50 V 0402 *(ext, merged)* | Identical spec; merged with the pd_pmg1 CC caps (C416–C419). |
| R304 (LM5148 UVLO top, VIN) | C96346 RC0805FR-07100KL 100 k 1 % 0805 150 V | C149504 0805W8F1003T5E 100 k 1 % 0805 150 V | Identical spec (already used on power_input). |
| R130 (BAR_MON ladder), R314 (3V3_EN) | C25783 39 k 1 % 0402 | C23153 39 k 1 % **0603** | Same value, 1 %, 100 ppm; 0402 39 k is extended. |
| R135 (PD_MON ladder) | C25918 7.5 k 1 % 0402 | C23234 7.5 k 1 % **0603** | Same value, 1 %, 100 ppm. |
| R626 (hub VBUS sense) | C36871 68 k 1 % 0402 | C23231 68 k 1 % **0603** | Same value, 1 %, 100 ppm. |
| R633 (hub VBUS_DET attenuator) | C25897 49.9 k 1 % 0402 | C23184 49.9 k 1 % **0603** | Same value, 1 %, 100 ppm. |
| R901 (GL3224 RTERM) | C137948 RC0402FR-07680RL 680 Ω 1 % | C23228 0603WAF6800T5E 680 Ω 1 % **0603** | Same value/tolerance. Keep the short GND return. |
| R137 (VIN shunt, INA237) | C844691 WSL25122L000FEA18 2 mΩ 1 % 2 W ±275 ppm 2512 | C459679 RLP25FEGR002 2 mΩ 1 % **3 W ±50 ppm** 2512 *(ext, merged)* | Better power and TCR; same footprint; merged with R312. |
| R201 (LM51770 peak sense) | C844693 WSL25124L000FEA 4 mΩ 1 % 1 W ±150 ppm 2512 | C459681 RLP25FEGR004 4 mΩ 1 % **3 W ±50 ppm** 2512 *(ext, merged)* | Better power and TCR; same footprint; merged with R303 (LM5148 sense). |
| R243 (INA226 laptop VBUS shunt) | C844900 WSL25125L000FEA 5 mΩ 1 % 1 W ±110 ppm **2512** | C316225 RLM12FTCMR005 5 mΩ 1 % 1 W ±100 ppm **1206** *(ext, merged)* | Same R/power, slightly better TCR; 5 A → 0.125 W (12 % of rating). Merged with R415; footprint shrinks 2512→1206. |
| Q213, Q214 (laptop source LM74800 pair) | C534333 BSC040N08NS5 80 V 4 mΩ | C5955453 BSC026N08NS5ATMA1 80 V **2.6 mΩ** *(ext, merged)* | Same package family (TDSON-8 5×6), same pinout, lower R_DS(on) (0.26 W → 0.17 W at 5 A). Same FET as the power_input LM74800 pairs. Qg 74 vs 43 nC: turn-on set by the 22 nF dV/dt cap, DGATE 2.6 A pull-down still turns off in ~30 ns. |

Docs updated: design/power_input.md, power_laptop.md, power_rails.md, usbc_muxes.md, ethernet.md,
usb_hub.md, card_reader.md.

## Kept extended (reason)

**ICs (no basic equivalent, function-specific)** — RP2350B, USB7206C, RTL8156BG, GL3224, PMG1-S3, TPS26750,
LM51770, LM5148, LM74800 (×3), LM74700, LM74502, TPS259470, TPS62933F/P (different modes by design),
TPS62A02A, TPS2553, TPS22918, INA226, INA237, INA180A2, TLV6700, TLV3011, TMP1075, TCA9534, AT24C512C,
24AA025E48 (EUI-48), SST26VF016B, SN74LVC1G32/1G11/3G17, 74LVC1G17, TUSB1064, TUSB1046, TPD4S480,
TPD6S300, TPD4E02B04, USBLC6-2SC6.

**Connectors / mechanical** — USB-C ×2 (DX07S024), USB-A ×2, PJ-063BH barrel, 12401610E4#2A, RJ45 magjack,
SD-111, DM3AT µSD, FH34SRJ FPC, SM04B Qwiic, SKRTLAE010 buttons, LCD module.

**Power semis / magnetics** — BSC0805LS, BSZ070N08LS5, BSC0901NS, CSD18543Q3A, AO4842, XAL1010-103,
MWSA1206S-4R7, MWSA0503S-2R2/-1R5, SWPA4018S1R0 (no basic power inductors), AOTA-B201610 3.3 µH and
ABM8-272-T3 12 MHz (RPi-mandated for RP2350).

**Protection** — 5.0SMDJ51A, 5.0SMDJ48CA, SMCJ28A, SMAJ6.0A (no basic TVS with these standoff voltages;
the only basic SMB TVS are 6.5 V/6.8 V bidirectional), MF-NSMF050-2 PTC (no basic PTC).

**Small discretes** — BAT54WS (VBUS-sense clamp: basic 1N5819WS leaks 500 µA, would corrupt the 47k/68k
divider), BAT54A (common anode; basic BAV70 is common cathode), BAT46W (100 V; basic 1N4148W is only
75 V on a 48–50 V net with TVS overshoot), BZT52C5V1 (no basic zener), BSS138DW (I²C bridge; basic
AO3400A adds ~10× capacitance, 2N7002 V_GS(th) up to 2.5 V at 3.3 V drive), NCP18XH103 NTC (no basic NTC).

**Capacitors** — 1 µF/2.2 µF/4.7 µF/47 nF 100 V and 10 µF 50 V X7R (no basic 100 V caps except 100 nF
0805; basic 10 µF 50 V is X5R 0805/1206 — DC-bias loss at 28 V), 47 µF 10 V X7R 1210 (basic is X5R 1206),
1 nF 100 V C308 (DNP snubber — not placed, so no JLC fee in practice), 390 pF C0G and 82 pF C0G (no basic
value), POSCAP 150 µF, polymer 100 µF/35 V and 330 µF/6.3 V, alu 47 µF/100 V.

**Resistors** — precision 1 % E96 set-points with no basic value in any size (checked 0402, 0603 and 0805):
41.2 k (LM5148 CNFG strap), 73.2 k (RT), 64.9 k / 14.3 k (FB, UVLO), 31.6 k, 4.42 k (FB), 24.3 k / 8.66 k
/ 5.23 k (buck-boost VSEL FB), 6.49 k (CFG strap), 86.6 k (RT), 62 k (COMP), 43 k (EN), 1.1 M / 46.4 k (OVP
31.1 V), 255 k, 422 k / 121 k / 40.2 k (sink OV/UV), 2.49 k (PHY RSET), 59 k (PHY buck FB), 27 Ω (RP2350
USB termination, RPi value), 39 Ω 1206 (backlight), 150 Ω 2512 1 W (discharge), shunts 8 mΩ 2512, 30 mΩ 0805,
2/4/5 mΩ (merged above). Changing these to basic values would move thresholds/output voltages; not done.

## Further options (not applied)

- Several E96/E24 values exist as JLC **"preferred extended"** in 0603 (40.2 k C12447, 62 k C23221, 43 k
  C23172, 27 Ω C25190). If the order uses Economic PCBA and JLC still waives the fee for preferred
  extended parts, moving these to 0603 would save another ~$12/order. `bom_check.py` counts them as
  extended either way.
- Re-picking feedback dividers to basic-value pairs (e.g. +3V3 FB 47 k/15 k = 3.307 V instead of 31.6 k/10 k)
  would remove a few more, at the cost of re-verifying each rail/threshold; out of scope for a no-degradation pass.
