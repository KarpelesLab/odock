# odock-10 — power rails sheet (`power_rails.kicad_sch`, refs 300+)

Source: `hardware/odock-10/sheets/power_rails.py` (generated, netlist-verified; second pass after
`docs/review/power.md`). Stock figures are from the JLC parts
API on 2026-10-02. Re-check them before ordering.

## Topology

```
VIN 9-50 V ──┬─ D301 BAT46W ─► LM5148 VIN pin (controller bias only)
             └─ Q301 BSZ070N08LS5 / Q302 BSC0805LS ─ L301 4.7 uH ─ RS303 4 mΩ ─► 5V_BUCK (5.13 V)
                                                                                │  6x 47 uF
                     LM74700-Q1 + Q303 BSC0901NS (ideal diode, source = 5V_BUCK) ▼
                                                                              5V_OR ─ R312 2 mΩ (INA226) ─► +5V
                                                     laptop VBUS sink switch (power_laptop) ──────────────► +5V
+5V ─► TPS62933  (1.2 MHz) ─► +3V3  (3.33 V, 3 A part, ~2.2 A max load)
+5V ─► TPS62933P (1.2 MHz) ─► +1V15 (1.154 V, USB7206C VCORE), EN = +3V3 divider, PG ─► RAILS_PG
```

Global nets used: `VIN`, `+5V`, `+3V3`, `+1V15`, `I2C_SYS_SCL`, `I2C_SYS_SDA`, `RAILS_PG`, `PG_5V`, `GND`.
PWR_FLAGs on `+5V`, `+3V3`, `+1V15`. **`+1V1` is not created** (see "Rails not needed").

Power-good outputs (both global in `nets.py`):
- `RAILS_PG`: open drain with 100 k to +3V3. It is high when +1V15 is in regulation, which implies +3V3 is up.
  usb_hub wire-ORs it onto `HUB_RESET_N` through a Schottky, so the hub is held in reset until VCORE is good.
- `PG_5V`: LM5148 PG, open drain, **100 k pull-up to 5V_BUCK** (≈ 5.1 V level). Consumed on power_laptop to release
  the bus-power sink switch (and to permit the source switch) only once the buck regulates. The pull-up rail is
  deliberately 5V_BUCK: an unpowered LM5148 cannot hold its open-drain PG low, so a pull-up to an always-present
  rail (+3V3/+5V, which the laptop keeps alive in bus-powered mode) would read "good" exactly during the hand-over
  window while VIN ramps. With 5V_BUCK it is 0 V whenever the buck is off. Not for 3.3 V-only inputs (5.1 V level);
  consumers must not source current into it (power_laptop uses FET gates only).

## 1. Backfeed problem and its solution

In bus-powered mode the laptop feeds `+5V` through the sink switch while VIN is absent. With a plain synchronous
buck, +5V would reach VIN through L301 and the body diode of the high-side FET, putting about 4.3 V on VIN. That
voltage would:
- Wake the LM51770 buck-boost (UVLO 3.5 V).
- Bias the LM5148 (VIN 3.5 V min).
- Forward-bias the LM5148's internal VOUT→VIN ESD diode.
- Drain the laptop's 15 W budget into VIN capacitance and loads.

The fix:
1. **The buck regulates a private node, `5V_BUCK`.** Every LM5148 pin that senses or biases from the output is on
   this node, never on +5V. That covers FB divider, VOUT/ISNS+, VCCX and the PG pull-up.
2. **An ideal diode connects `5V_BUCK` to `+5V`:** LM74700-Q1 plus BSC0901NS (30 V, 2.4 mΩ at 4.5 V), with the source
   on the buck side.
   - **VIN absent:** ANODE (5V_BUCK) sits at 0 V, so the LM74700 is unpowered and the gate is off. The FET body diode
     points 5V_BUCK→+5V, so it is reverse-biased and no current flows back.
   - **Buck running:** the forward drop is regulated to 20 mV (0.16 W at 8 A).
   - **Reverse current:** it is detected at −11 mV, and the gate is discharged with 2.37 A in under 0.75 µs.
3. **The LM5148 runs in diode-emulation mode** (PFM/SYNC = VDDA). The low-side FET cannot sink negative inductor
   current, so the buck cannot pump energy from its output back into VIN at light load or during an overvoltage.
4. **VIN at a few volts.**
   - The EN/UVLO divider (100 k / 14.3 k, 1.0 V threshold with 10 µA hysteresis current) starts the controller at
     8.0 V and stops it at 7.0 V. Including tolerance, that is 7.6–8.4 V on and 6.6–7.4 V off.
   - Below that the LM5148 sits in standby (124 µA) and never switches, so a 5 V-only PD-in contract or a dying
     barrel brick cannot make it run in deep dropout.
   - D301 (BAT46W, 100 V) in series with the controller's VIN pin follows the TI datasheet recommendation (SNVSC01
     §8.3.1). It stops the internal VOUT→VIN ESD diode from discharging 5V_BUCK into a VIN that collapses faster than
     the output.
   - The power stage has no such diode. The only charge that can flow back into a collapsing VIN is the buck's own
     ~150 µF on 5V_BUCK, through Q301's body diode. +5V stays isolated behind Q303.
5. **Handover when external power arrives while bus-powered (make-before-break, review finding 3).**
   1. `EXT_PWR_PRESENT` rises (input side) but does **not** open the sink switch on its own.
   2. VIN ramps, the LM5148 passes its 8 V UVLO and soft-starts (1.9–4.6 ms) into the unloaded 5V_BUCK.
   3. When 5V_BUCK rises above +5V (≈5.0 V from the laptop), Q303 conducts and +5V rises to ≈5.11 V. During the
      overlap the TPS259470A (reverse-current blocking) and the LM74700 form a two-way ideal-diode OR on +5V;
      neither source can back-feed the other. If laptop VBUS is higher (up to 5.5 V) the sink keeps carrying
      the load and the LM74700 simply stays off.
   4. PG_5V goes high; after the 2.7–6.7 ms RC on power_laptop the sink switch opens (`EXT_PWR_PRESENT` AND
      `PG_5V`) and the buck takes the full load (≤ 3 A step, ≈ 60 mV dip).
   No pre-bias issue arises, because 5V_BUCK starts from 0 V.
6. **External power lost while sourcing.** +5V droops while the laptop takes over (FRS or PR_Swap, decided on other
   sheets). The 330 µF polymer plus ceramics on +5V bridge about 150 µs at ≤2 A (≈0.9 V droop). At full 8 A load they
   cannot, so a brief brownout or reset there is expected.

## 2. +5V buck (LM5148) calculations

Requirements:
- VIN 9–50.4 V (EPR 48 V + 5 %). The TVS clamps on power_input are 51/48 V standoff and break down at about 57–63 V.
- VOUT 5.13 V at 8 A. Power budget: 37 W / 7.4 A max.

| Item | Value | Calculation |
|---|---|---|
| Output voltage | 5.127 V (≈5.11 V on +5V after the 20 mV OR drop) | VREF 0.8 V × (1 + 64.9 k / 12 k). Chosen above 5.0 V for USB-A and downstream port drops; GL3224 needs 4.75–5.25 V |
| Switching frequency | 299 kHz | RT = (10⁶/f − 53)/45 = 72.9 k → 73.2 k. Lower fsw keeps switching and Coss losses at 48 V manageable |
| Duty / on-time | D = 0.10 (50 V) … 0.59 (9 V); tON(min) = 340 ns ≫ 50 ns | Dropout (tOFF(min) 90 ns) begins at ~5.3 V, below UVLO |
| Inductor | 4.7 µH, Sunlord MWSA1206S-4R7MT, 15 A Irms, 24 A Isat, 9 mΩ | ΔI = Vo(1−Vo/Vin)/(L·f) = 3.25 A p-p at 48 V, 2.7 A at 20 V, 1.6 A at 9 V |
| Slope compensation | L_ideal = Vo·Rs/(24·f) = 2.85 µH; actual 1.65× | Over-compensated, so stable at all duty cycles |
| Current sense | 4 mΩ 2512 1 % (RLP25FEGR004), Kelvin | VCS-TH 49/60/73 mV gives peak limit 12.3/15.0/18.3 A. Min DC limit at 48 V = 12.3 − 1.63 = 10.6 A (≥ 1.3 × 8 A). A 5 mΩ shunt would give only 8.2 A minimum, too tight |
| Short-circuit peak | 18.3 A + 48 V × 45 ns / 4.7 µH = 18.7 A | < 24 A Isat. FETs fine. Hiccup after 512 cycles |
| Output capacitance | 6 × 47 µF 10 V X7R 1210 on 5V_BUCK (~150 µF effective at 5 V) + 330 µF polymer + 2 × 22 µF on +5V | Ripple ΔI/(8·f·C) = 3.25/(8 × 300k × 150µ) = 9 mV. Cap RMS 0.94 A total |
| Load step 4 A | ≈ ΔI/(2π·fc·C) = 4/(2π × 18k × 430µ) ≈ 80 mV (1.6 %) | |
| Compensation | RCOMP 10 k, CCOMP 10 nF, CHF 100 pF | fc = 2π-form: RCOMP = 2π·fc·(Vo/VREF)·(Rs·Gcs/gm)·C → fc ≈ 18 kHz with 430 µF, ≈ 52 kHz with 150 µF only (light load: the LM74700 linear-regulates, which partly decouples the far-side bulk). Zero 1.6 kHz, pole 159 kHz |
| Input capacitance | 4 × 4.7 µF 100 V X7S 1210 + 2 × 100 nF 100 V 0603. **No alu here** (review finding 4): VIN total ≤ 100 µF for USB PD cSnkBulkPd; the single 47 µF damping alu for VIN sits on power_input (stability calc there) | ICIN,rms = Io·√(D(1−D)) = 2.5 A (48 V) … 3.96 A (9 V), split over 4 MLCCs. ΔVIN ≈ D(1−D)Io/(f·C) = 0.42 V p-p at 48 V (~6 µF effective) |
| Soft start | 3 ms internal | Inrush into 5V_BUCK ≈ 150 µF × 5.1 V / 3 ms = 0.26 A (+5V is behind the diode) |
| UVLO | on 8.0 V, off 7.0 V | RUV1 = ΔV/IHYS = 1 V/10 µA = 100 k (0805, VIN side, 150 V rating); RUV2 = 100k × 1/(8 − 1) = 14.3 k |
| Bias | VCCX = 5V_BUCK (> 4.3 V switches VCC to VCCX) | The VIN LDO would otherwise dissipate (14 + 16 nC) × 5 V × 300 kHz × 48 V / 5 V ≈ 0.4 W, plus IQ |
| CNFG | 41.2 k: primary, dual random spread spectrum ON | |
| CBOOT | 100 nF | ΔV = Qg/C = 14 nC / 100 nF = 0.14 V |
| Snubber | 2.2 Ω + 1 nF across SW–GND, **DNP** | Fit only if SW ringing at 48 V exceeds ~70 V |

### MOSFETs
- Q301 HS is the **BSZ070N08LS5**: 80 V, 9.4 mΩ max at 4.5 V, Qsw 6.9 nC, Qg 14 nC at 4.5 V, 3.3 × 3.3 mm. It is
  logic-level because LM5148 gate drive is 5 V. Low Qsw matters because switching loss dominates at 10 % duty.
- Q302 LS is the **BSC0805LS**: 100 V, 8.5 mΩ max at 4.5 V, Qrr 12 nC, 5 × 6 mm. Conduction dominates (89 % duty).
- Voltage margin: VIN max 50.4 V vs 80 V. The VDS spike must stay below 80 V, so layout needs a tight hot loop with
  the 100 nF caps at the HS drain. RHO is a 0 Ω placeholder and the snubber is DNP.

### Loss / efficiency at 8 A (estimate)
Assumptions: Rds(on) at 4.5 V max × 1.45 hot; DCR × 1.25; core loss 0.25 W; switching loss from Qsw with HO
1.06 Ω / 0.5 Ω + Rg; Coss loss ≈ ½ Qoss·V·f; Qrr·V·f.

| VIN | HS | LS | Switching + Coss + Qrr | Inductor | Shunt | Buck η | + OR FET 0.20 W + INA shunt 0.13 W | Total loss |
|---|---|---|---|---|---|---|---|---|
| 12 V | 0.39 | 0.44 | 0.24 | 0.97 | 0.26 | 94.4 % | **93.7 %** | 2.8 W |
| 20 V | 0.23 | 0.59 | 0.43 | 0.98 | 0.26 | 94.0 % | **93.3 %** | 3.0 W |
| 28 V | 0.17 | 0.65 | 0.66 | 0.98 | 0.26 | 93.5 % | **92.8 %** | 3.2 W |
| 48 V | 0.10 | 0.71 | 1.36 | 0.98 | 0.26 | 92.0 % | **91.4 %** | 3.9 W |

- The ~93 % target is met for barrel (12–24 V) and 20/28 V PD inputs at full load, and exceeded at typical loads.
- At 48 V × 8 A (240 W charger, all ports maxed) the 5V path dissipates ≈3.9 W, about 1.1 W over the power-budget
  figure.
- Hot spots:
  - Q301 at ~1.2–1.4 W in 3.3 × 3.3 mm. Needs a copper pour and via array, θJA ≈ 40 K/W → +50 K.
  - L301 at ~1 W (13.5 × 12.6 mm).
  - Q302 at ~0.7 W.
- Put a TMP1075 next to Q301/L301 (already planned on the sensors sheet). Firmware should derate charge-mode ports
  first when VIN = 48 V and the stage runs hot.

## 3. +3V3 (TPS62933F, C5219272)
- +5V → 3.33 V (31.6 k / 10 k). RT = GND sets 1.2 MHz.
- L = 2.2 µH MWSA0503S-2R2MT: ΔI = 3.33 × (1 − 3.33/5.13)/(2.2 µ × 1.2 M) = 0.44 A.
- Cout 3 × 22 µF 25 V 0805 X5R, about 35 µF effective (TI table: 30 µF typ, 10 µF min).
- Cin 2 × 10 µF + 100 nF.
- **Soft start:** CSS 22 nF → 22 n × 0.8 / 5.5 µA = 3.2 ms (3.9 ms worst case). This satisfies the RTL8156BG
  3.3 V rise (0.5–10 ms) and the USB7206C (≤ 5 ms unless RESET_N is held).
- **EN divider** 100 k / 39 k (EN 1.21 V rising): starts at +5V ≥ 4.31 V and stops around 4.0 V, so the rail cannot
  limp along on a collapsing bus-powered +5V.
- **Load:**
  - Hub VDD33 0.1 A, RTL8156BG 3.3 V 0.09 A, TUSB1064 + TUSB1046 ~0.3 A, PMG1/TPS26750 ~0.05 A, RP2350 + flash
    ~0.06 A, LCD ~0.1 A, SD + microSD up to 0.3 A, sensors and LEDs.
  - Total ≈ 1–1.5 A typ, ≤ 2.2 A worst case, for 0.3–0.7 W loss.
  - GL3224 is not on this rail (it is 5 V-fed).

## 4. +1V15 (TPS62933P, C5219254) — USB7206C VCORE
- **Datasheet (DS00003850F §9.2):** VCORE 1.09–1.21 V (1.15 V nominal), so the net name +1V15 is correct.
- **Current:** 410 mA + 179 mA per active SS port, ≈ 1.31 A with 5 ports at 10G. The 3 A part is used at ≤ 2 A.
- **Output:** 4.42 k / 10 k → 1.154 V. With ±1 % VREF and 1 % resistors that is about ±1.5 % (1.137–1.171 V), well
  inside the window.
- **Sequencing (§9.6.1):** VCORE must rise after or together with VDD33. EN is therefore taken from +3V3 through
  12 k / 10 k, which enables at 2.66 V typ and 2.82 V max with +3V3 at 3.33 V.
  - Rise times must be ≤ 5 ms. The TPS62933P has a fixed 2 ms soft start.
  - The PG output (85/90 % thresholds, 70 µs delay) drives `RAILS_PG`.
- L = 1.5 µH MWSA0503S-1R5MT: ΔI = 0.50 A p-p, 17 % of 3 A. That is above the ≥ 10 % peak-current-mode guideline.
- **Output capacitance:** 4 × 22 µF 6.3 V 0603 here plus the hub's 9 × (4.7 µF + 0.1 µF + 1 nF) on the hub sheet. The
  internal compensation wants more capacitance at low VOUT, so ≈ 80 µF effective is provided here.
- **Why from +5V and not +3V3:** one conversion instead of two (≈ 85 % vs ≈ 80 % overall). It also avoids a 5.5 V-max
  part on the +5V rail (TPS62A02 / TLV62569), which could see laptop VBUS transients in bus-powered mode. And it
  shares a part family with +3V3.

## 5. Rails not needed / handled elsewhere
- **+1V1: not created.** The RP2350 core (DVDD 1.1 V) comes from its on-chip switching regulator, fed from +3V3
  (VREG_VIN). Its inductor and caps belong on the MCU sheet.
- **RTL8156BG needs an external 0.95 V rail.**
  - Datasheet §5.8/§5.13/§7: only the RTL8156B**GS** has the built-in switching regulator. The RTL8156BG (the stocked
    part, C41376388; the BGS is not stocked) needs 0.95 V (0.92–0.98 V, ±3 %, ≤ 650 mA max / 364 mA typ) on AVDD09,
    DVDD09, U2VDD09 and U3VDD09.
  - It enables its regulator itself through **pin 5 POW_EXT_SWR** (active high), with a 0.95 V rise of 0.5–2.2 ms
    and a ≥ 50 ms off-on interval. DVDD09_UPS must stay isolated.
  - Because the enable comes from the PHY and the rail should be dedicated, it belongs on the **ethernet sheet**. A
    suitable choice is TLV62569 (C141836, 2 A, 242k stock) from +3V3 with EN = POW_EXT_SWR and FB divider
    0.6 × (1 + 5.83 k / 10 k) ≈ 0.95 V. The 1–2 ms soft start meets the 0.5–2.2 ms rise.
  - Budget: 0.95 V × 0.65 A ≈ 0.6 W max from +3V3, which is already inside the +3V3 headroom above.
- **GL3224:** single 4.75–5.25 V supply on its VBUS pin, with internal 5→3.3 V and 3.3→1.2 V regulators (datasheet
  §4.6, §5). It is fed from +5V with no external sequencing. In bus-powered mode +5V can sag below 4.75 V under heavy
  load, so watch the sink-switch drop.

## Part list (this sheet)

| Ref | Part | LCSC | JLC stock | Type |
|---|---|---|---|---|
| U301 | TI LM5148RGYR (VQFN-24) | C7470701 | 57 474 | ext |
| Q301 | Infineon BSZ070N08LS5 (TSDSON-8FL) | C534678 | 3 281 | ext |
| Q302 | Infineon BSC0805LS (TDSON-8) | C534374 | 15 000 | ext |
| L301 | Sunlord MWSA1206S-4R7MT 4.7 µH 15 A | C408521 | 879 | ext |
| R303 | TA-I RLP25FEGR004 4 mΩ 2512 | C459681 | 15 078 | ext |
| D301 | Diodes BAT46W-7-F | C83152 | 107 563 | ext |
| C301–C304 | Taiyo HMK325C7475KN-TE 4.7 µF 100 V 1210 | C697607 | 330 431 | ext (47 µF alu removed) |
| C305–C306 | Samsung CL21B104KCFNNNE 100 nF 100 V X7R 0805 | C28233 | 1 251 499 | basic |
| C309–C314 | Murata GRM32ER71A476KE15L 47 µF 10 V 1210 | C84494 | 56 437 | ext |
| C315 | Murata GCM21BC72A105KE36L 1 µF 100 V 0805 | C126585 | 30 481 | ext |
| U302 | TI LM74700QDBVTQ1 (SOT-23-6) | C2653623 | 5 563 | ext |
| Q303 | Infineon BSC0901NS (TDSON-8) | C152424 | 5 000 | ext |
| R312 | TA-I RLP25FEGR002 2 mΩ 2512 | C459679 | 52 095 | ext |
| U303 | TI INA226AIDGSR (VSSOP-10) | C49851 | 44 400 | ext |
| C323 | 330 µF 6.3 V polymer 6.3×6 (MA6.3V330M6X6) | C54321566 | 6 338 | ext |
| U304 | TI TPS62933FDRLR (SOT-583, forced PWM) | C5219272 | 2 524 | ext; keep the F variant (RTL8156BG needs PWM) |
| U305 | TI TPS62933PDRLR (SOT-583) | C5219254 | 7 010 | ext |
| L302 | Sunlord MWSA0503S-2R2MT 2.2 µH | C408408 | 7 617 | ext |
| L303 | Sunlord MWSA0503S-1R5MT 1.5 µH | C408407 | 2 445 | ext |
| R (E96) | 73.2 k C26986, 14.3 k C25855, 64.9 k C26984, 41.2 k C100420, 31.6 k C11463, 4.42 k C52269 | | all > 7k | ext |
| R/C basic | 10 k C25744, 12 k C25752, 39 k 0603 C23153, 100 k C25741, 100 k 0805 (150 V) C149504, 0 Ω C17168; 100 pF C1546, 10 nF C15195, 22 nF C1532, 100 nF C1525 / C14663 (50 V 0603), 4.7 µF C19666, 10 µF 25 V C15850, 22 µF 25 V 0805 C45783, 22 µF 6.3 V 0603 C59461 | | | basic |

DNP: R302 2.2 Ω 0805 and C308 1 nF 100 V 0603 (SW snubber).

## Thermal / loss summary (worst case, everything maxed)
| Block | Loss |
|---|---|
| 5V buck + OR + shunt at 8 A | 2.8 W (12–20 V in) … 3.9 W (48 V in) |
| +3V3 at 2.2 A | ~0.7 W |
| +1V15 at 1.31 A | ~0.3 W |
| **Sheet total** | **≈ 3.8–4.9 W** (typ. 1.5–2 W at 3–4 A on +5V) |

## Assumptions
- External power always gives VIN ≥ 9 V. The UVLO is 8 V, so 5 V-only PD contracts do not run the 5 V buck; that is
  intended.
- +5V loads on other sheets add ≥ 50 µF ceramic plus bulk. The USB-A ports need ≥ 120 µF each per the USB spec.
- The I2C_SYS pull-ups and the I2C address plan are owned by the MCU sheet.
  - Addresses: INA226 here at **0x41** (A1 = GND, A0 = VS); INA237 on VIN at 0x45 (power_input); laptop-VBUS
    INA226 at 0x44 (power_laptop); TMP1075s at 0x48–0x4F.

## Open issues / risks
1. ~~`RAILS_PG` → `HUB_RESET_N`~~ resolved: `RAILS_PG` is global and usb_hub wire-ORs it through a Schottky.
2. **RTL8156BG 0.95 V regulator is missing from the plan.** It must be added on the ethernet sheet (§5). The draft
   docs assumed an internal regulator.
3. **48 V corner:** HS FET ~1.3 W in 3.3 × 3.3 mm. Validate the temperature on the prototype. Fallback: BSC0805LS
   (5 × 6) for Q301 as well, which costs +0.2 W switching loss but spreads heat better. Alternatively lower fsw to
   250 kHz with the same L, giving 3.9 A ripple, still within limits.
4. **Inductor stock:** MWSA1206S-4R7MT has 879 in stock. Drop-in alternate: Bourns SRP1265A-4R7M (C780205, 8.4 mΩ,
   28 A sat), but it shares stock with the buck-boost. Check the footprint, since both are 13.5 × 12.5 mm class.
5. **Loop stability with the ideal diode in the output path** needs a bench Bode plot. At light load the LM74700
   regulates the OR-FET linearly, so the +5V bulk is partly decoupled and fc moves toward ~50 kHz (< fsw/5).
6. **Hold-up on loss of VIN at high load** is not covered (330 µF ≈ 150 µs at 2 A). It depends on the PR_Swap/FRS
   policy.
7. **GL3224 4.75 V minimum in bus-powered mode** depends on the sink-switch/cable drop on power_laptop.
8. **Tooling note:** `tools/import_lcsc.sh` runs `kicad-cli sym upgrade` without `--force`, so newly imported symbols
   stay in easyeda's 2-space format and `fix_pins.py` cannot find them. This sheet worked around it with
   `kicad-cli sym upgrade --force` under the lib lock. The script should add `--force`.
