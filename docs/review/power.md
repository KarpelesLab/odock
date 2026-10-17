# Design review: power sheets (power_input, power_laptop, power_rails)

Reviewer: independent pre-layout review, 2026-10-02.

Scope:
- `hardware/odock-10/sheets/power_input.py`, `power_laptop.py` and `power_rails.py`. The pin→net maps in these files
  were treated as the schematic.
- The cross-sheet nets they share with `pd_pmg1.py`, `usbc_muxes.py`, `mcu.py`, `usb_hub.py` and `tools/schgen/nets.py`.
- Every symbol pin number was checked against `hardware/lib/odock.kicad_sym` and against the datasheet pin table.
- Pad numbering of the power MOSFET footprints, in particular the exposed drain pads, was checked in `odock.pretty`.

Datasheets read:

| Part | Document |
|---|---|
| TPS26750 | SLVSH67 |
| TPD4S480 | SLVSH00 |
| LM7480-Q1 / LM74800 | SNOSD95C |
| LM74502 | SNOSDE5A |
| TPS25947 / TPS259470A | SLVSFC9C |
| LM51770 | SNVSCL2A |
| LM5148 | SNVSC01 |
| LM74700-Q1 | SNOSD17G |
| TPS62933 / F / P | SLUSEA4D |
| TLV6700 | SNVSAV2B |
| TLV3011 | SBOS300C |
| INA237 | SBOSA20 |
| INA226 | SBOS547 |
| SN74LVC1G11, SN74LVC1G32 | TI datasheets |
| CSD18543Q3A | TI datasheet |
| PMG1-S3 | Infineon 002-31288 |

The USB PD R3.1 sink and source electrical parameters are quoted from the specification.

## Result

**No BLOCKER.** These all check out against the datasheets:
- Every IC pin mapping on the three sheets.
- MOSFET orientations: every back-to-back pair is common-drain with the sources on the outer rails, and every ideal
  diode has its source on the anode side.
- Exposed-pad (drain) numbering on all TDSON, VSONP and DFN FETs.
- Absolute maximum ratings at the nominal voltages: VIN ≤ 50.4 V, VBUS_LAPTOP ≤ 32.6 V.
- The divider maths (OV, UVLO, feedback and VSEL), checked numerically.
- The source/sink interlock on the laptop port, which is sound.

**Four MAJOR findings.** All four are in how the inputs hand over to each other, not in any individual circuit:
1. PD-in priority is keyed to "any PD contract", including 5 V.
2. Priority switching browns out the deck.
3. The bus-power → external-power handover browns out the deck.
4. The PD-in sink exposes about 320 µF of VIN capacitance to VBUS during PD voltage transitions.

The MINOR items and NOTES follow.

## Findings (sorted by severity)

| # | Sev | Sheet | Refs / nets | Finding | Evidence | Fix |
|---|---|---|---|---|---|---|
| 1 | **MAJOR** | power_input | U102 GPIO1 → `PDIN_PRES_L` → Q108 (barrel EN/UVLO); `BAR_OK`, `EXT_PWR_PRESENT` | **PD-in priority disables a working barrel whenever any PD-in sink path or contract is active, including 5 V.** GPIO1 is to be configured "high while sink contract active / PD power path enabled". With the AlwaysEnableSink strap the path is enabled at the implicit 5 V contract. A 5 V-only explicit contract asserts it too, e.g. a phone charger or a non-PD Type-C brick in the PD-in port. The barrel LM74800 is then forced into shutdown, so VIN = 5 V. The LM5148 (UVLO 8 V) and the LM51770 (8.06 V) stay off, and the deck will not run on the barrel. Worse, `BAR_OK` is detected on the jack side (VBAR) and is not gated by the barrel enable, so `EXT_PWR_PRESENT` reads **high** while VIN is 5 V. With a laptop attached, the sink switch is killed, +3V3 collapses, and the `EXT_PWR_PRESENT` driver loses power (100k pull-down on pd_pmg1). The sink re-enables and +3V3 returns, so `EXT_PWR_PRESENT` goes high again: a relaxation oscillation. This also defeats the stated assumption that "a 5 V PD contract does not count as external power". | TPS26750 SLVSH67 Table 7-6, p.34: AlwaysEnableSink "always enables the sink path regardless of the amount of current the attached source is offering". LM5148 EN 1.0 V / 10 µA (SNVSC01 Table 6-1). power_input.py §4–5. | Drive the priority from a qualified signal: **gate of Q108 = `PD_OK`**. PD_OK already means VBUS_PDIN within 7.7–56 V AND the sink path is on, and it runs on +3V3. Add a 2N7002 (or an RC-isolated gate) so PD_OK pulls BAR_EN low. Remove the `PDIN_PRES_L` connection to Q108. Then `EXT_PWR_PRESENT = PD_OK OR BAR_OK` is always truthful. Keep GPIO1 only as a status output for the MCU. |
| 2 | **MAJOR** | power_input | U105 EN/UVLO (BAR_EN), C118 47 nF HGATE dV/dt, Q107 | **Releasing the barrel after a PD-in loss browns out the deck.** Barrel priority puts U105 into *shutdown* (EN < V(ENF)). This applies to PD-in unplug, PD hard reset or the sink path opening while a barrel is present. On release, U105 must first recharge CAP (I(CAP) ≥ 1.3 mA into 100 nF, about 0.5–1 ms). HGATE then rises at 55 µA / 47 nF = **1.17 V/ms** from 0 V. It must climb to VIN + Vth before Q107 conducts. Q107's body diode points VIN_OR → BAR_MID, so it cannot bridge the gap. VIN meanwhile collapses: about 320 µF total at 5 A falls at about 16 V/ms, so the LM5148 drops out in < 1 ms while HGATE needs ≥ 5–15 ms. The deck resets and laptop charging drops on every PD-in unplug, even with a 24 V barrel plugged in. If GPIO1 asserts at the 5 V implicit contract, plugging PD-in while running on the barrel has the same effect, because VIN drops to 5 V during negotiation. | LM7480-Q1 SNOSD95C §7.5 p.6: I(HGATE) 39–75 µA, I(CAP) 1.3 mA min, V(ENF) shutdown; Table 6-1 p.3. power_input.py §4. | Do not implement priority by shutting the barrel controller down. Options: (a) **Preferred:** both inputs stay as armed ideal diodes (higher voltage wins). PD-in > barrel is implemented in PMG1/RP2350 policy by requesting a PD-in contract above the barrel voltage (28/36/48 V). (b) If hardware priority is kept, gate it with `PD_OK` (finding 1). Shrink the barrel CdVdt so HGATE re-arms in < 0.5 ms, and accept the hot-plug inrush, or add a separate inrush limiter. Either way, document that PD hard reset loses VIN for > 1 ms if the barrel is not armed. |
| 3 | **MAJOR** | power_laptop ↔ power_input ↔ power_rails | `EXT_PWR_PRESENT` → sink-kill AO3400A on `SNK_ON`; LM5148 soft start; `+5V` | **Bus-power → external-power handover is break-before-make with a 3–15 ms gap.** `EXT_PWR_PRESENT` comes from the *input side*: BAR_OK on the VBAR jack voltage, or PD_OK at 7.7 V on VBUS_PDIN. It kills the laptop sink switch within µs. The replacement +5V only appears later. VIN must first ramp: 1.17 V/ms through the barrel LM74800, so about 7 ms to the 8 V LM5148 UVLO. The LM5148 then soft-starts in 1.9–4.6 ms, and only then does the ideal diode conduct. On PD-in, PD_OK asserts at 7.7 V and the LM5148 needs ≥ 8 V plus 3 ms. +5V carries about 0.5 mF and up to 3 A, so it falls about 6 V/ms and is gone in < 0.2 ms. Every barrel or PD-in plug-in while bus-powered resets the deck (hub, Ethernet, laptop link). It can also oscillate as in finding 1, because `EXT_PWR_PRESENT` itself is powered from +3V3. The power_rails "handover" narrative assumes the sink opens *after* the buck conducts, but nothing enforces that. | LM5148 SNVSC01 §7.5 p.8: tSS-INT 1.9–4.6 ms; EN threshold 1 V. LM7480 §7.5 p.6. power_laptop.py §6, power_rails.py §2. | Make the handover make-before-break: kill the sink only when external power is *on +5V*. Put a second AO3400A in series with the EXT_PWR_PRESENT pull-down on `SNK_ON`, with its gate on **`PG_5V`** (LM5148 PG, already pulled up to 5V_BUCK, about 5.1 V ≤ AO3400A VGS). This needs a new global net. Alternative: an RC delay with a fast-release diode on that FET's gate, ≥ 30 ms. Overlap is safe: the TPS259470A blocks reverse current and the LM74700 ideal diode handles the OR. The SRC_ON interlock FET still forces the sink off before any sourcing. |
| 4 | **MAJOR** | power_input (+ VIN loads on power_laptop, power_rails) | U104/Q104/Q105 PD-in path; VIN bulk: C122/C123 2×100 µF, C124–C127, C201–C205, C301–C305… | **PD-in sink capacitance is far above cSnkBulkPd during PD voltage transitions.** Once the TPS26750 enables the path, the ideal diode (DGATE) and HGATE are fully on. HGATE's dV/dt only acts at turn-on. Every upward VBUS transition (5→9/15/20, 20→28/36/48 V EPR) therefore charges all of VIN directly from the source. VIN is about 206 µF on power_input, about 56 µF on power_laptop and about 57 µF on power_rails: ≈ **320 µF**, against the USB PD sink limit cSnkBulkPd ≤ 100 µF. At the allowed vSrcSlewPos of 30 mV/µs this is up to **9.6 A**, plus the deck load. Even at a gentle 10 mV/µs it is 3.2 A. That risks source OCP or hard reset on contract changes, especially EPR entry. Separately, the PD sink must drop to pSnkStdby (2.5 W) after Accept and before the transition. A deck sourcing 140 W to the laptop cannot do that unless firmware sequences it. | USB PD R3.1 sink electrical parameters: cSnkBulkPd max 100 µF, pSnkStdby 2.5 W; source: vSrcSlewPos ≤ 30 mV/µs. LM7480 Table 6-1, §7.5. | Budget the VIN capacitance seen by PD-in at ≤ 100 µF. Drop C122/C123 (2×100 µF). The converters already carry 2×47 µF alu plus ceramics, about 120 µF, so trim one more alu or move the damping alu behind the converters' own filters. If more bulk is needed, add a current-limited hot-swap stage on the PD path (e.g. TPS2663x or LM5069-class) instead of the plain LM74800 back-to-back pair. Add to the firmware contract: before any PD-in renegotiation, reduce the laptop contract and port loads to standby. |
| 5 | MINOR | power_input → pd_pmg1 | U102 GPIO1 → R 1k → `PDIN_PRESENT` → PMG1 P7.2 | **Back-drive of an unpowered PMG1 and overload of the TPS26750 dead-battery LDO.** On a PD-in-only cold start (no laptop, so PMG1_VDDD = 0 until +3V3 rises), GPIO1 can be high for hundreds of ms before the rails come up. It drives 3.3 V through 1 k into PMG1 P7.2, which is not fail-safe (only P4.0/P4.1 are): (3.3 − 0.5)/1k ≈ **2.8 mA**. That exceeds the PMG1 injection limit of 0.5 mA and the TPS26750 GPIO limit of 1 mA. It also comes out of the 5 mA total VBUS-LDO budget at the moment the TPS26750 is reading its EEPROM over 2.2 k pull-ups. | PMG1-S3 DS Table 3: SID.PWR.ABS#3 (GPIO ≤ VDDIO + 0.5 V), #6 (injection 0.5 mA); §2.6.3.1 fail-safe pins. TPS26750 §5.3.1 p.6: GPIO 1 mA, VBUS LDO 5 mA total. | Raise the series resistor to ≥ 22 k. Both loads are CMOS inputs. Q108 goes away with finding 1. Raise the I2Cc pull-ups to 4.7 k to cut the LDO_3V3 load during EEPROM boot. |
| 6 | MINOR | power_input | R (100k PD_OV_TOP), R (1M VBUS_PDIN→PD_MON_UV), R (1M BAR_MON_TOP), R (100k VBAR→BAR_EN), R (100k BAR_SW) | **0402 resistors across ≥ 48 V.** These use 0402 basic parts (C25741 / C26083, 50 V working voltage). VBUS_PDIN reaches 50.4 V continuously in EPR, and TVS clamping takes it to 60–82 V. VBAR can see a wrong 48 V brick or a reversed 24 V. The other two sheets correctly use 0805 (150 V) for their VIN-side divider tops. | UNI-ROYAL 0402WGF: 50 V max working voltage. power_laptop / power_rails use C17539, C17709, C96346 (0805). | Use 0603/0805 (≥ 75–150 V working voltage) for every resistor whose top terminal is on VBUS_PDIN, VBAR or SW. |
| 7 | MINOR | power_input | U106 window (BAR_OK UV), J102 spec "9–24 V" | **BAR_OK UV threshold of 9.2 V is above the 9 V minimum barrel spec.** With the TLV6700 threshold tolerance, 1N4148W Vf 0.4–0.7 V and 1 % resistors, the threshold spans about 9.0–9.6 V. A 9 V ±5 % brick runs the deck (LM5148 UVLO 8 V, LM51770 8.06 V) but reports `EXT_PWR_PRESENT` = 0. The laptop source is then never enabled, and the bus sink stays armed in parallel. | power_input.md §5; TLV6700 SNVSAV2B §7.5. | Lower UV to about 8.3 V (e.g. 1M / 47k / 15k → 8.2 V; re-check OV) or change the barrel spec to 12–24 V. |
| 8 | MINOR | power_laptop | U201 nFLT = `VBB_PG`, Q (BB_ENKILL→VBB_PG), U203 SRC_ON | **`VBB_PG` is not a valid power-good during LM51770 soft start.** The LM51770 disables its PG comparator during soft start, so nFLT is high-Z. BB_ENKILL releases VBB_PG as soon as the converter is enabled. VBB_PG therefore reads high for the 2.2 ms soft-start while VBB_OUT is still ramping. The documented hardware gate "source switch only after VBB_PG" does not hold in that window. A firmware that asserts LAPTOP_SRC_EN early, or waits for "VBB_PG high", closes the source switch onto a ramping rail. | LM51770 SNVSCL2A §8.3.15 p.37: "Power Good … This protection is disabled during the soft-start procedure." | Either have PMG1 firmware wait ≥ 5 ms after VBB_EN (and verify VBUS via the PMG1 ADC), or add an RC delay of about 10 ms on the BB_ENKILL→VBB_PG FET gate release. State this in the firmware contract. |
| 9 | MINOR | power_laptop | U207 OVP (trip 29.6–32.0 V), VBB_OUT 28 V setting (max 28.7 V) | **Little margin to the OVP latch on load dump.** Unplugging the laptop at 5 A × 28 V gives an overshoot of about ΔI / (2π·f_c·C) = 5 / (2π·3 kHz·220 µF) ≈ 1.2 V on VBB_OUT. That is up to 29.9 V against a 29.6 V minimum trip. A latched OVP then needs a VBB_EN cycle on every hot unplug at full power. | power_laptop.md §1 (f_BW 3 kHz, C_OUT ≈ 220 µF), §6. | Bench-measure the overshoot at 28 V / 5 A. If it is > 0.6 V, raise the trip to about 31.3 V nominal (e.g. 1.1 M / 45.3 k). The LM74800 backstop is 31.7–33.6 V; the PMG1 VBUS abs max is 34 V. Alternatively keep the trip and accept auto-handling in firmware. |
| 10 | MINOR | power_input | U102 ADCIN 5/5, U103 (blank from JLC) | **The sheet note "deck boots from a 5 V-only PD-in even with a blank EEPROM; RP2350 can then program it" is wrong.** With a blank EEPROM the TPS26750 enables the sink path at 5 V, but USB PD stays disabled until a host loads a configuration. VIN = 5 V does not start the LM5148 (UVLO 8 V), so the RP2350 never powers up from PD-in alone. First programming needs the barrel, laptop bus power, or the I2Cc test pads. | TPS26750 SLVSH67 §7.4.1 p.33 ("If no EEPROM is detected, then the device waits for an external host"), Table 7-6 p.34. | Correct the note and the bring-up procedure. Consider pre-programming the EEPROM (JLC programming service, or a programmed EEPROM part). |
| 11 | MINOR | power_input | D101 SMCJ51A, D102 SMCJ48CA vs U101 VBUS (63 V), U104/U105 A/VS (70 V) | **TVS clamp voltages exceed downstream absolute maximum ratings at rated surge.** SMCJ51A clamps at VC 82.4 V and SMCJ48CA at 77.4 V, above TPD4S480 VBUS 63 V and LM74800 A/VS 70 V. Already flagged for the TPD4S480 in power_input.md; the LM74800s and the 0402 resistors are affected too. The same applies to finding 7 of the design doc: a reversed barrel with PD-in active violates OUT/C ≤ 70 V + V(A). | LM7480 SNOSD95C §7.1 p.4; TPD4S480 SLVSH00 §5.1 p.5. | Use a lower-clamp or flat-clamp TVS (e.g. SMCJ43A/SMBJ45A-class with tighter VC, or TVS3301-type), or add a series 10 Ω on the TPD4S480 VBUS sense pin. Accept the residual risk explicitly for the prototype. |
| 12 | NOTE | power_input | U102 PP5V (pins 28/29) = GND | The datasheet requires PP5V 4.9–5.5 V in operation and ≥ 10 µF (cSrcBulkShared). Grounding it is not described. The internal PP_5V blocking FET should tolerate it (IPP5V_REV is specified with PP5V = 0 V), but confirm with TI before layout, as the design doc already says. | SLVSH67 Table 4-1 p.4, §5.3.1, §5.4. | Confirm on E2E, or tie PP5V to +5V with 10 µF (cheap). |
| 13 | NOTE | power_input | Q101 gate `PD_PP_EN_HV` | POWER_PATH_EN is Hi-Z at reset, so Q101's gate floats until the TPS26750 boots. PD_SINK_EN is undefined for a few ms. This is harmless today, because AlwaysEnableSink turns the path on anyway, but it is undefined behaviour. | SLVSH67 Table 4-1 ("RESET: Hi-Z"), §5.9 (8.5 µA source). | Add 1 MΩ gate-to-GND on Q101. 8.5 µA × 1 MΩ still gives > 6 V when enabled. |
| 14 | NOTE | power_laptop | U207 TLV3011 (non-B) | The non-B TLV3011 has no power-on reset, so its output is undefined while +3V3 ramps. If VBB_EN is already high, which can happen when PMG1 runs on laptop VBUS through a +3V3 brownout, the latch can set spuriously. | SBOS300C features ("Power-on-reset ('B' version)"). | Use TLV3011B (same pinout), or have firmware cycle VBB_EN after any +3V3 recovery. |
| 15 | NOTE | power_laptop | U201 MODE = GND (PSM), VBB_PG during VSEL down-steps | The design relies on "OVP1 masked in PSM" so that nFLT/VBB_PG does not drop when VBB_OUT lags a down-step with FB > 110 %. The datasheet sentence is ambiguous: it could mean PSM *operation* (pulse skipping) rather than MODE = low. If nFLT does assert, SRC_ON opens during every 28→20/15/9/5 V step. | SNVSCL2A §8.3.15 p.37. | Bench-verify a 28→5 V step with the laptop at standby load. Fallback: blank VBB_PG in firmware during steps, which needs SRC_ON to drop VBB_PG from the AND, or use FPWM (DNP 0 Ω). |
| 16 | NOTE | power_laptop / pd_pmg1 | VBUS_LAPTOP limit chain | The PMG1 VBUS_C_P0 *operating* range is 3.67–30 V; abs max is 34 V. The OVP (≤ 32.0 V) and the LM74800 backstop (≤ 33.6 V) sit between operating and abs max, which is acceptable as a fault-only limit. The SMBJ30A on usbc_muxes clamps far higher at rated Ipp. | PMG1 DS SID.PD.PWR#3, SID.PD.PWR.ABS#3. | None for the prototype. Keep the backstop below 34 V worst case (it is). |
| 17 | NOTE | power_laptop | U201 CFG 6.49 k (row 8: hiccup ON + ISNS limiter) | With hiccup enabled, reaching the peak or average current limit hiccups (1 ms on / 24 ms off) rather than limiting. power_laptop.md says a 12 V input "delivers ~100–130 W"; in practice it would hiccup and the laptop would lose VBUS. PMG1 policy must keep the input current under about 10.6 A peak. | SNVSCL2A §8.3.13 p.34, Table 8-1 p.38. | Correct the doc. PMG1 must cap the laptop offer by input voltage (12 V barrel → ≤ 100 W incl. 5 V rail). |
| 18 | NOTE | all | docs | Stale or inconsistent documentation: <br>• power_input.md §6 gives the INA237 CURRENT_LSB as 2¹⁹ / 39 µA with the INA228 constant 13107.2·10⁶. INA237 is 16-bit, so LSB = 625 µA and SHUNT_CAL = 819.2·10⁶·LSB·R·4 = 4096. The sheet note is correct. <br>• power_rails.md still lists "INA228 on VIN" and calls `RAILS_PG` a local, unconnected net. It is global in nets.py and used by usb_hub. <br>• power_rails.md part list gives U304 as TPS62933DRLR / C3200405, but the sheet uses TPS62933F (C5219272); keep the F variant. <br>• odock-10.md still shows LM74720 on the barrel. | INA237 SBOSA20 Eq. 1 (p.~27). | Update the docs so firmware and BOM follow the sheets. |
| 19 | NOTE | power_input | C122/C123 RVT 100 µF/80 V (EasyEDA footprint) | Symbol pin 1 = VIN, pin 2 = GND. Confirm that pad 1 of `CAP-SMD_BD10.0-…` is the + pad (chamfer side) before layout. If finding 4 removes these caps, this is moot. | — | Check the footprint silk and polarity. |

## What was verified and found correct

### Pin maps vs datasheet
All of these match the datasheet pin numbers:

| Part | Package | Notes |
|---|---|---|
| TPS26750 | RSM-32 | Pin 19 is VSYS in the datasheet and named GND in the symbol; both go to GND, which is correct. |
| TPD4S480 | RUK-20 | |
| LM74800 | DRR-12 | RTN pad left floating, as required. |
| LM74502 | DDF-8 | |
| TPS259470A | RPW-10 | |
| LM51770 | DCP-38 | |
| LM5148 | RGY-24 | |
| LM74700 | DBV-6 | |
| TPS62933F / P | DRL-8 | |
| TLV6700 | DDC | |
| TLV3011 | DBV | |
| INA237 / INA226 | MSOP-10 | IN+ = pin 10, IN− = pin 9. |
| AT24C512C | SOIC-8 | |
| SN74LVC1G11 | DBV | |
| SN74LVC1G32 | DBV | |
| BAV70 | SOT-23 | Common cathode on pin 3. |
| BAT54A | SOT-23 | Common anode on pin 3. |

MOSFET footprints:
- The exposed drain pad is numbered 8 on the BSC026N08NS5 and BSC040N08NS5 footprints.
- It is numbered 9 on the BSC0805LS, BSC0901NS and CSD18543Q3A footprints, and each of those symbols has a matching
  pin 9.

### Topology
- **LM74800 pairs:** all four are common-drain, with A and the DGATE FET source on the input side, and OUT and the
  HGATE FET source on the output side. VS = C = midpoint. When the deck is fed from the other input, the
  OUT − VS stress is only one body-diode drop (< 16.5 V abs max).
- **LM51770 current sense:**
  - RCS sits between SW1 and the inductor, as the datasheet requires (SW1 − CSA/CSB within ±0.3 V; Fig 8-17).
  - CFG 6.49 k = R2D #7 = table row 8 (DRSS, hiccup, PSM 10 %, limiter ON).
  - SYNC = VCC selects the positive limit direction.
  - VREF = 1.00 V, so the feedback maths applies.
  - VSEL codes reproduce 5.115 / 8.99 / 14.96 / 19.97 / 27.97 V, and no code can exceed 28 V.
- **Divider and timing values:**

| Item | Value |
|---|---|
| LM51770 UVLO | 8.06 V on / 6.78 V off |
| LM5148 EN | 7.99 V on / 6.99 V off |
| LM5148 fsw | 299 kHz |
| LM5148 output | 5.127 V |
| +3V3 | 3.328 V |
| +1V15 | 1.154 V |
| LM74800 OV, PD-in | 57.2 V |
| LM74800 OV, barrel | 27.4 V |
| LM74800 OV, laptop source | 32.6 V |
| LM74502 OV | 6.5 V |
| TPS259470A OVLO | 6.0 V |
| TPS259470A UVLO | 4.29 V |
| TPS259470A ILIM | 3.34 A |
| OVP trip | 30.76 V |

### Interlocks
- **Source and sink never both on:**
  - SRC_ON needs EXT_PWR_PRESENT high; SNK_ON needs it low.
  - SRC_ON also directly kills SNK_ON.
  - The LM74502 OV (6.5 V) and TPS259470A OVLO (6 V) block a 28 V VBUS even if firmware asserts LAPTOP_SNK_EN wrongly.
- **Unpowered logic:** every enable has a pull-down, so unpowered logic means everything is off.
- **OVP latch:**
  - It is set via 1N4148W/4.7 k (IN+ ≈ 2.06 V > 1.242 V).
  - It is reset only by VBB_EN low.
  - It acts on both the LM51770 enable and SRC_ON.

### Dead-deck bus-powered cold start
The power path is correct. The power-sheet side assumes PMG1 drives LAPTOP_SNK_EN from VDDD:
1. Laptop vSafe5V → LM74502 (VS ≥ 4 V) → Q215 → TPS259470A (UVLO 4.29 V) → +5V.
2. TPS62933F (EN 4.31 V) → +3V3.
3. EXT_PWR_PRESENT is held low by its 100 k pull-down while the 74LVC1G32 is unpowered. The TLV6700 outputs are low
   in UVLO, so EXT_PWR_PRESENT cannot glitch high during the +3V3 ramp.
4. 5V_BUCK and VBB_OUT stay isolated:
   - The LM74700 body diode is reverse-biased.
   - Q213 and the LM51770 output FET body diodes are reverse-biased.
   - Q301's body diode only connects to 5V_BUCK, never to +5V.

### Backfeed
No path was found from +5V or VBUS_LAPTOP back into VIN, or from VIN back into VBUS_PDIN or VBAR.

### Inter-sheet nets
Every global net used on these sheets has exactly one driver and the right level:
- `EXT_PWR_PRESENT`: push-pull, 3.3 V.
- `VBB_PG` and `LAPTOP_OVP_N`: open-drain with a single 10 k pull-up.
- `VBB_EN`, `VBB_VSELx`, `LAPTOP_SRC_EN` and `LAPTOP_SNK_EN`: PMG1 push-pull, with pull-downs on power_laptop.
- `PDIN_PRESENT`: TPS26750 GPIO, active high.
- `RAILS_PG`: open-drain, consumed on usb_hub through a Schottky.

I2C addresses on I2C_SYS do not collide:
- INA226 0x41 (rails) and 0x44 (laptop).
- INA237 0x45.
- TCA9534 0x20.

## Resolution (2026-10-02, second pass of power_input / power_laptop / power_rails)

All three sheets rebuilt with `build_all.py power_input power_laptop power_rails` → `netlist verify: OK`;
`tools/bom_check.py` → 0 failing parts. Reference designators below are the new ones (several shifted).

| # | Resolution |
|---|---|
| 1 | **Fixed (lead's approach).** Hardware PD-in priority removed: Q108 and the `PDIN_PRES_L` → barrel EN/UVLO link are gone. Both LM74800 paths are always-armed ideal-diode ORs; the higher input voltage supplies VIN. Source preference is firmware policy (request a PD voltage above the barrel to prefer PD-in). `PDIN_PRESENT` is informational only. `EXT_PWR_PRESENT = BAR_OK OR PD_OK` is now truthful by construction ("VIN is or is about to be fed ≥ ~8 V by PD-in or barrel"): PD_OK still requires VBUS_PDIN ≥ 7.7 V AND sink path on, so a 5 V contract never counts, and no shutdown can make BAR_OK lie. The relaxation oscillation is also impossible because the sink release now needs `PG_5V` (finding 3). |
| 2 | **Fixed** by option (a): no LM74800 is ever put into shutdown for priority, so there is no HGATE re-arm on PD-in loss; the other ideal diode takes over within µs and VIN only dips to the other input's voltage. Documented that a PD hard reset without a barrel still loses VIN (≈ 90 µF hold-up). |
| 3 | **Fixed.** New global `PG_5V` (LM5148 PG, open drain, 100 k to 5V_BUCK — kept on 5V_BUCK on purpose: an unpowered LM5148 cannot hold PG low, so a +3V3/+5V pull-up would read "good" exactly in the hand-over window). On power_laptop: SNK_ON = LAPTOP_SNK_EN AND NOT (EXT_PWR_PRESENT AND PG5_DLY) AND NOT SRC_ON, with Q218 (EXT) and Q219 (PG) in series, PG5_DLY = PG_5V via R251 100 k / C242 100 nF (2.7–6.7 ms after PG, fast release via D204 BAT46W). The +5V OR (TPS259470A reverse blocking + LM74700) handles the overlap without backfeed. Mutual exclusion: the source enable now also needs PG5_DLY (Q215/Q216 pull SRC_PGOK low), i.e. the same term that releases the sink, and the explicit SRC_ON → SNK_ON kill (Q220, µs vs ms HGATE) stays, so both switches are never on together and a source enable can no longer cut the sink before the buck runs. PG_5V is not diode-ANDed into SRC_PGOK, because the +3V3 pull-up would back-feed PG_5V to ≈ 2.8 V in bus-powered mode. |
| 4 | **Fixed.** C122/C123 2 × 100 µF and the two 47 µF alus on power_laptop and power_rails removed; the 4 × 2.2 µF on VIN reduced to C123 1 µF/100 V + C124 100 nF. One 47 µF/100 V alu (C122, C371305) on VIN is kept as an R-C damping branch through its ESR. Total capacitance the PD source charges (VBUS_PDIN + VIN on all three sheets, DC-bias derated, alu at +20 %) is ≈ 76 µF at 48 V, ≈ 89 µF at 20 V and ≤ 100 µF at 5 V worst case (91 µF nominal). Damping check: peak |Zout| 0.13–0.5 Ω for 0.5–2 µH of cable and 0.1–0.6 Ω ESR, against |Zin|min = 1.35 Ω (9 V / 60 W); it would be 0.55–2.2 Ω undamped. Added the pSnkStdby-before-renegotiation rule to the firmware contract (power_input.md §6). A hot-swap stage was not needed. |
| 5 | **Fixed.** GPIO1 → `PDIN_PRESENT` series resistor 1 k → 47 k (R117): ≤ 60 µA into the unpowered PMG1 P7.2. I2Cc pull-ups 2.2 k → 4.7 k (R108/R109). |
| 6 | **Fixed.** R121 (PD OV top), R125 (BAR_SW OV top) and R127 (VBAR UVLO top) are 100 k 0805 (C149504, 150 V); R129 (BAR_MON) and R133 (VBUS_PDIN mon) are 1 M 0805 (C17514). The remaining high-side 0402s on power_laptop (255 k, 422 k, 1.1 M) see ≤ 34 V, inside the 50 V rating. |
| 7 | **Fixed.** BAR_OK ladder 1 M / 39 k / 15 k: UV 8.2 V (≈ 8.0–8.5 V), so a 9 V −5 % brick counts; OV 28.5 V. (The suggested 1 M / 47 k / 15 k would give 7.35 V.) |
| 8 | **Fixed in hardware.** The VBB_PG hold FET (Q208) now has its own gate node BB_PGH: set fast from BB_ENKILL through D201 and released through R233 1 M / C227 4.7 nF. VBB_PG stays low for 5.4–9.2 ms after enable (≥ 2× the 2.2 ms soft start), so VBB_PG high means VBB_OUT is regulated. The firmware contract also says to check VBUS with the PMG1 ADC before PS_RDY. |
| 9 | **Fixed (trip raised a little, filter added).** OVP divider bottom 47 k → 46.4 k (trip 31.1 V, ≈ 29.9–32.3 V RSS, max corner 33.1 V < 34 V PMG1 abs max) and filter 470 pF → 2.2 nF (98 µs). The 1.2 V load-dump overshoot reaches the comparator as ≈ 0.7 V, i.e. ≤ 29.4 V. The suggested 45.3 k was not used: its worst-case corner, 33.8 V, is too close to 34 V. A run-away trips ≈ 2.6 V later, and VBUS_LAPTOP stays protected by the 4 µs LM74800 backstop. Bench-measure the overshoot; fallback C243 = 4.7 nF. |
| 10 | **Fixed.** The sheet note and power_input.md now state that a blank EEPROM does not boot the deck from PD-in. Added a bring-up section covering barrel/bus power, the I2Cc jig and a pre-programmed EEPROM. |
| 11 | **Partly fixed, residual risk accepted.** TVSs changed to 5 kW parts on the same SMC footprint: 5.0SMDJ51A (C2990373) and 5.0SMDJ48CA (C2649886). They clamp at ≈ 64–68 V at up to 18–19 A, against 82/77 V for the old parts at rated current. That is below the LM74800 70 V rating and the 80 V FETs. It is still above the TPD4S480 VBUS 63 V for surges ≥ ~5 A; this is accepted and documented for the prototype, with a series-R fallback. The reversed barrel + 48 V PD case (OUT/C rating) is still documented as accepted. |
| 12 | Not changed; it is already an open issue in power_input.md (confirm with TI, or tie PP5V to +5V with 10 µF). |
| 13 | Not changed in hardware (NOTE). It is harmless with AlwaysEnableSink. A 1 MΩ Q101 gate pull-down can be added at layout. |
| 14 | Docs: TLV3011B / VBB_EN cycle recommendation added to power_laptop.md risks. |
| 15 | Docs: bench-verification item added to power_laptop.md risks. |
| 16 | No action, as suggested. |
| 17 | Docs corrected: a 12 V input hiccups and does not deliver 100–130 W. PMG1 caps the offer by input voltage (12 V → ≤ 100 W incl. the 5 V rail). |
| 18 | Docs corrected: the INA237 LSB (625 µA, SHUNT_CAL 4096) in power_input.md; power_rails.md now lists the INA237 at 0x45 and the INA226 at 0x44, `RAILS_PG` as global, and U304 as TPS62933F C5219272; odock-10.md now shows LM74800 ×2 with no priority. The `nets.py` comment on `PDIN_PRESENT` ("disables barrel path") is stale but owned elsewhere; flagged in power_input.md. |
| 19 | Moot: the RVT 100 µF parts were removed. The remaining 47 µF alu uses KiCad's CP_Elec_10x10, which has a marked + pad. |
