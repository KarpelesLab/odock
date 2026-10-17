# odock-10 — power_laptop sheet

Source: `hardware/odock-10/sheets/power_laptop.py` (generates `power_laptop.kicad_sch`, ref_base 200, A2).
Status: second pass after the power review (`docs/review/power.md`), 2026-10-02. `build_all.py power_laptop` → `netlist verify: OK`;
`tools/bom_check.py` → all parts on this sheet are JLC parts with stock (none consigned).
Stock figures: JLC parts API on 2026-10-02. Datasheets used: TI SNVSCL2A (LM51770), SNOSD95C (LM7480-Q1),
SNOSDE5A (LM74502), SLVSFC9C (TPS25947), SBOS300C (TLV3011), SBOS547 (INA226), Infineon BSC0805LS rev 2.1,
TI SLPS633 (CSD18543Q3A).

## Topology

```
 VIN 9-50 V ──┬─ 4x4.7µ/100V (no electrolytic: VIN ≤ 100 µF budget, see power_input §6)
              Q201 (HO1) ─ BB_SW1 ─ RCS 4 mΩ ─ L201 10 µH ─ BB_SW2 ─ Q204 (HO2) ─ BB_PSO ─ RISNS 8 mΩ ─ VBB_OUT
              Q202 (LO1)                                  Q203 (LO2)    4x10µ/50V              2x10µ + 2x100µ polymer
              U201 LM51770: 347 kHz, PSM, avg I-limit 6.25 A (hiccup), FB network selected by VBB_VSEL0..2
              EN = VBB_EN AND LAPTOP_OVP_N (discharge 150 Ω while disabled), nFLT = VBB_PG

 VBB_OUT ─ Q213 (DGATE, ideal diode) ─ SRC_MID ─ Q214 (HGATE) ─ VBUS_LSW ─ 5 mΩ (INA226 U204, 0x44) ─ VBUS_LAPTOP
            U202 LM74800-Q1, EN = SRC_ON, OV backstop 32.6 V on VBUS_LAPTOP          10 µF/50 V + 100 nF   (to connector)

 VBUS_LSW ─ Q215 (60 V, LM74502 U205, OV 6.5 V) ─ SNK_MID ─ U206 TPS259470A eFuse (3.3 A, OVLO 6 V, RCB) ─ +5V
            EN = SNK_ON

 PG5_DLY = PG_5V delayed 2.7–6.7 ms on rising, fast falling               (R251/C242/D204, node SNK_PGD)
 SRC_ON = LAPTOP_SRC_EN · EXT_PWR_PRESENT · VBB_PG · LAPTOP_OVP_N · PG5_DLY  (U203 74LVC1G11 + BAT54A + Q215/Q216)
 SNK_ON = LAPTOP_SNK_EN · /(EXT_PWR_PRESENT · PG5_DLY) · /SRC_ON          (resistor + series FET pair + kill FET)
 VBB_PG = nFLT, held low while disabled and 5.4–9.2 ms after enable (Q208, BB_PGH 1M/4.7 nF)
 LAPTOP_OVP_N = NOT latch( max(VBUS_LAPTOP, VBB_OUT) > 31.1 V ), reset by VBB_EN low   (U207 TLV3011)
```

### Interface nets
Global (all from `nets.py`): `VIN`, `VBB_OUT`, `VBUS_LAPTOP`, `+5V`, `VBB_EN`, `VBB_PG`,
`VBB_VSEL0..2`, `LAPTOP_SRC_EN`, `LAPTOP_SNK_EN`, `LAPTOP_OVP_N`, `EXT_PWR_PRESENT`, **`PG_5V`** (input; LM5148
power-good from power_rails, open drain, 100 k to 5V_BUCK, 5.1 V level), `I2C_SYS_SCL/SDA`, `+3V3`, `GND`.
PWR_FLAG on `VBB_OUT`.

Signals this sheet *drives*: `VBB_PG` (open-drain + 10k pull-up to +3V3 here), `LAPTOP_OVP_N` (open-drain FET +
10k pull-up here), `VBB_OUT`, `VBUS_LAPTOP` (when sourcing), `+5V` (when sinking). Other sheets must not add
pull-ups/pull-downs to `VBB_PG` / `LAPTOP_OVP_N`. Inputs `VBB_EN`, `VBB_VSELx`, `LAPTOP_SRC_EN` have 100k
pull-downs here (floating PMG1 → converter off, 5 V setting, source off). `LAPTOP_SNK_EN` has an effective
47k pull-down (through 10k). Inputs are 3.3 V logic (5 V tolerant except `LAPTOP_SNK_EN`, which sees 0.82× its level).

PMG1 firmware contract:
- VBB_EN high → converter starts at 5.115 V; `VBB_PG` is held low for 5.4–9.2 ms after enable (LM51770 nFLT is
  not valid during its 2.2 ms soft start) and is a true power-good after that. Firmware should still check VBUS
  with the PMG1 ADC before PS_RDY.
- VSEL codes (VSEL2..0): `000` 5.1 V, `001` 9 V, `010` 15 V, `100` 20 V, `111` 28 V. Any code change is
  slewed in hardware (τ 4.6–7 ms, ≤ 5 mV/µs); wait ≥ 35 ms (or measure VBUS) before PS_RDY.
- Assert `LAPTOP_SRC_EN` only after `VBB_PG`; hardware blocks it otherwise (and also until `PG_5V` has been
  high for the RC delay, i.e. the deck runs from its own buck and the sink switch is released).
- `LAPTOP_SNK_EN` may stay asserted through a bus-power → external-power hand-over: hardware releases the sink
  only after the LM5148 regulates. De-assert it before a PR_Swap to source.
- To clear an OVP latch, drop `VBB_EN` (≥ 1 ms), then restart at 5 V.
- After a down-step with no laptop load, enable the PMG1 VBUS discharge or cycle VBB_EN.

## 1. Buck-boost power stage (LM51770)

Part choice: **LM51770DCPR** (C43351171, 1007 in stock, $5.32): 3.5–78 V in (85 V abs), 1.8 MHz capable,
average current limiter, PSM. LM5177 (60 V, 151 stock) has less margin at 50.4 V; LM51772 (I2C, 55 V) has
1 piece in stock. Its features fit: external FB divider (hardware voltage select), ISNS average current
limit with hiccup, nFLT power-good.

| Quantity | Formula (datasheet) | Value |
|---|---|---|
| fsw | R_RT = (1/fsw − 20 ns)·30.3 GΩ (Eq. 2) | R_RT = 86.6k → **347 kHz** |
| Gate charge check | ≤ 42 nC/driver at 600 kHz | BSC0805LS 16 nC, CSD18543Q3A ~6 nC at 5 V |
| Inductor ripple, buck 48→28 V | (VIN−VO)·D/(L·f) | 3.36 A p-p (worst) |
| Ripple, buck 48→5 V / 20→5 V | | 1.29 / 1.08 A |
| Ripple, boost 14→28 / 12→28 / 9→28 V | VIN·D/(L·f) | 2.0 / 1.98 / 1.76 A |
| Peak inductor current, 140 W from 20 V | IIN + ΔI/2 = 7.19 + 0.83 | 8.0 A |
| Peak current limit | Vth+(CSB−CSA) / RCS = 50 mV / 4 mΩ | **12.5 A** (10.6–14.4 A) |
| Inductor | Isat 17.5 A > 14.4 A max limit; Irms 15.5 A | XAL1010-103 |
| Avg output current limit | 50 mV / RISNS 8 mΩ (49–51.7 mV) | **6.25 A** (6.1–6.5 A), hiccup 1 ms/24 ms |
| Slope | R_SLOPE = L/RCS · 50e6 (Eq. 12) = 125k | **100k** (×0.8 → more slope, TI guidance) |
| Eq. 13 / Eq. 14 | RCS/L < fsw/(10·VOmax); 100 < RCS/L < 8000 | 400 < 1240 ✓; 400 ✓ |
| CSA/CSB filter | C = t_on,min / (2π·20 Ω·10) | 10 Ω + 10 Ω + 100 pF |
| Soft start | C_SS = 10 µA · t / 1 V | 22 nF → 2.2 ms |
| UVLO | 1.25 V·(1 + 200k/43k) + 200k·5 µA | on 8.06 V, off 6.78 V |
| VCC | ≥ 10 µF effective | 2× 22 µF 0805 (≈ 24 µF at 5 V) |

Full 140 W needs VIN ≳ 16 V: from 12 V the input current would be 12.4 A average (13.4 A peak), above the
10.6 A guaranteed peak limit. With CFG row 8 the peak/average limit **hiccups** (1 ms on / 24 ms off) rather than
limiting, so the laptop would lose VBUS — it does *not* "deliver ~100–130 W". PMG1 policy must cap the laptop
offer by input voltage so the input current stays below ≈ 10 A peak: 12 V barrel → ≤ 100 W including the 5 V
rail (a 12 V barrel is budgeted at 60 W total in `power-budget.md` anyway).

CFG = 6.49k (R2D setting #7, table row 8): DRSS spread spectrum **on**, hiccup **on**, PSM entry 10 %,
ISNS **current limiter** on. SYNC = VCC (positive limit direction latched at start-up, no external clock),
DTRK = GND, HO1_LL/HO2_LL open. BIAS = VBB_OUT via 10 Ω/1 µF: VMAX picks min(VIN, BIAS) above 6.5 V, so the VCC
LDO runs from VBB_OUT (≤ 28 V) instead of 48 V once the output is above 6.5 V.

MODE = GND (PSM, 0 Ω; DNP 0 Ω to VCC selects FPWM). Reasons: no reverse current, so down-steps never pump
VBB_OUT energy back into VIN (VIN is fed through ideal diodes and could rise by tens of volts with only the
input caps to absorb 0.5·220 µF·(28²−5²) = 83 mJ); OVP1 is masked in PSM so nFLT does not glitch during
down-steps; light-load efficiency. Down-steps are then discharged by the laptop (it drops to standby before a
lower PDO, ~90 mA at 28 V → ~0.4 V/ms on 220 µF) and the PMG1 VBUS discharge.

### Compensation (Eq. 3–11), starting point
Feedback AC gain is fixed by the slew network (section 2): at crossover Cm shorts node BB_FBM, so the AC divider is
Rtop : (Rbot‖Rs) = 100k : 1.42k → **71.8 V equivalent** for every code.

- f_RHPZ = VO(1−D)²/(2π·IO·L): 14.4 kHz (9 V→28 V, 3.2 A current-limited), 20 kHz (12 V, 4.1 A), 45 kHz (20 V, 5 A).
- f_BW < f_RHPZ/3 = 4.8 kHz and < (1−Dmax)·fsw/10 = 11 kHz → **f_BW = 3 kHz**.
- R_COMP = 2π·3 kHz·71.8·10·4 mΩ·220 µF / (600 µS·(1−0.68)) = **62k**.
- f_pole,boost = 2·IO/(2π·VO·CO) = 258 Hz; f_CZ = 1.5× = 387 Hz → C_COMP = **6.8 nF**; C_HF = 1/(2π·10·f_BW·R) = **82 pF**.
- Buck mode (5 V, 20 V in) crossover ≈ 8 kHz with the same network (no RHPZ), boost ≈ 2.6 kHz.
- Current limiter (IMONOUT): 10k + 1 nF → integrator crossover ≈ 6 kHz (gm_ILIM 200 µS · RISNS/(10·RCS)).
- The Cm/Rs network adds a lag doublet at ~25–35 Hz (higher loop gain below it at low codes). Phase there is
  well below crossover; check conditional stability in SIMPLIS/PSpice (TI model) and by bode measurement at
  5, 20 and 28 V, 0.5 A and 5 A, before freezing values.

### Capacitors
- Input: 4× 4.7 µF/100 V X7S 1210 (≈ 2.1 µF each at 48 V, ≈ 3.5 µF at 20 V). RMS in buck
  = IO·√(D(1−D)) = 2.5 A worst → < 1 A per ceramic. **The 47 µF alu was removed** (review finding 4): the PD-in
  source sees all VIN capacitance, budgeted to ≤ 100 µF (cSnkBulkPd); the single 47 µF damping alu for the VIN
  node is on power_input (stability calculation there, §6). Do not add bulk on VIN here.
  All VIN-side parts ≥ 100 V (≥ 63 V required; VIN max 50.4 V).
- Output, power-stage side (BB_PSO): 4× 10 µF/50 V X7R 1210 (hot loop for Q203/Q204). VBB_OUT: 2× 10 µF/50 V +
  2× 100 µF/35 V polymer (80 % of rating at 28 V) + 100 nF. Boost RMS = IO·√(VO/VIN − 1) = 3.2 A at 20 V in.
  Ripple at 20 V in: ΔV ≈ IO·D/(C·f) ≈ 18 mV + ESR.

### Efficiency / loss estimate at 28 V × 5 A (140 W)
Model: R_DS(on) at 4.5 V gate × 1.4 (hot), switching ½·V·I·(tr+tf)·f with 16 ns (BSC0805LS) / 6 ns
(CSD18543Q3A), Coss via Qoss, Qrr + 40 ns dead time, DCR × 1.25 (hot), core loss rough, gate drive from VCC LDO.

| VIN | Mode | D | IL avg | ΔI p-p | Ipk | Loss | η |
|---|---|---|---|---|---|---|---|
| 12 V* | boost | 0.57 | 12.4 A | 2.0 A | 13.4 A | 9.3 W | 93.8 % |
| 20 V | boost | 0.29 | 7.2 A | 1.65 A | 8.0 A | **3.9 W** | 97.3 % |
| 48 V | buck | 0.58 | 5.0 A | 3.4 A | 6.7 A | **3.7 W** | 97.4 % |

*12 V × 140 W exceeds the guaranteed current limit (see above); shown for reference only.
Breakdown at 20 V: Q201 0.62, Q203 0.25 + 0.21 sw, Q204 0.62 + 0.52 (Qrr/dead), Coss 0.23, L 0.92, RCS 0.21,
RISNS 0.20 W. At 48 V: Q201 0.18 + 0.67 sw, Q202 0.13 + 0.31, SW1 Coss 0.67, Q204 0.44, L 0.69, VCC LDO 0.31 W.

## 2. Output voltage select (VBB_VSEL0..2 from PMG1)

VOUT = 1 V·(1 + Rtop·G_FB). Rtop = 100k (VBB_OUT → FB), Rbot = 24.3k → **5.115 V** with all VSEL low (also when
PMG1 is unpowered: 100k pull-downs). Switched branches hang off node **BB_FBM**, joined to FB by **Rs = 1.5k** and
held by **Cm = 4.7 µF**; each branch is a resistor + AO3400A to GND (gate via 1k).

Why not plain FET-switched FB resistors: (1) an abrupt FB step makes the output slew as fast as the loop allows
(≫ 30 mV/µs) and trips nFLT (FB outside ±10 %), which would drop VBB_PG and open the source switch on every
step; (2) per-gate RC slowing gives independent bit timing, and a multi-bit change can pass through an
intermediate code (e.g. 010 → 101 via 111 = 28 V). With the shared Rs/Cm node every change, single- or multi-bit,
moves the FB current as **one first-order exponential**; FET switching glitches last ns and are filtered.

| Code VSEL2..0 | Use | Nominal | ±1 % R + ±1 % VREF (MC) |
|---|---|---|---|
| 000 | default / vSafe5V | 5.115 V | ±2.6 % |
| 001 | 9 V | 8.991 V | −2.9/+2.4 % |
| 010 | 15 V | 14.958 V | −2.8/+2.3 % |
| 100 | 20 V | 19.974 V | −2.7/+2.5 % |
| 111 | 28 V | 27.973 V | −2.5/+2.4 % (max 28.7 V) |
| 011 / 101 / 110 | unused | 17.8 / 22.3 / 26.1 V | |

Branch resistors: VSEL0 24.3k, VSEL1 8.66k, VSEL2 5.23k (E96, solved so that one-hot gives 9/15/20 V and all-on
gives 28 V exactly; G is monotonic in each bit, so **no code can exceed 28 V**). Time constant
τ = Cm/(1/Rs + ΣG) = 7.1 ms (→000), 6.6 ms (001), 5.5 ms (100), 4.6 ms (111). Largest step 5→28 V: initial
slew 23 V/4.6 ms = **5 mV/µs** (PD vSrcSlewPos ≤ 30 mV/µs); 99 % settled in < 35 ms (tSrcSettle 275 ms).
The loop (3 kHz) tracks a ms ramp, so FB stays within ±10 % and VBB_PG stays high during steps.
Optional PPS/AVS fine trim is not implemented (laptops use fixed 28 V for 140 W); a future injection resistor from a
PMG1 PWM/RC into BB_FBM would add it with limited authority.

## 3. Enable, discharge, VBB_PG qualification

- BB_ENKILL is pulled up from VIN (470k 0805, 5.1 V zener) → by default it turns on Q (EN/UVLO → GND, converter
  off), the 2N7002 + 150 Ω/1 W VBB_OUT discharge (τ = 33 ms on 220 µF, 83 mJ max) and Q208 holding VBB_PG low
  (nFLT is high-Z in shutdown and its PG comparator is disabled during soft start, SNVSCL2A §8.3.15).
- **VBB_PG soft-start blanking (review finding 8):** Q208's gate is node BB_PGH, charged from BB_ENKILL through
  D201 (1N4148W, fast: VBB_PG drops as soon as the converter is disabled) and discharged through R233 1 M into
  BB_ENKILL with C227 4.7 nF to GND (τ 4.7 ms). From ≈ 4.5 V the gate falls below the AO3400A threshold
  (0.65–1.45 V) 5.4–9.2 ms after enable — ≥ 2× the 2.2 ms soft start — so VBB_PG high means VBB_OUT is regulated.
  The extra 4.7 nF on BB_ENKILL slows its rise on disable by < 0.4 ms at 9 V VIN.
- Two series AO3400A (gates VBB_EN and LAPTOP_OVP_N) pull BB_ENKILL low → converter enabled. So the
  LM51770 runs only with **VBB_EN AND no OVP latch**, and the discharge is off exactly when it runs.
- With VIN absent nothing is pulled; VBB_PG floats high through its pull-up but `EXT_PWR_PRESENT` is low then,
  so the source switch stays off. Treat VBB_PG as valid only while VBB_EN is high (and ≥ 10 ms after it rose).

## 4. Laptop source switch (LM74800-Q1 + 2× BSC026N08NS5)

- Common-drain back-to-back pair, A = VBB_OUT, OUT = VBUS_LSW. DGATE FET = ideal diode (reverse comparator
  −4.5 mV, 0.5 µs turn-off): the laptop can never back-feed VBB_OUT/the converter (FRS, PR_Swap, faults).
  HGATE FET = on/off. 80 V/2.6 mΩ at 10–11 V gate drive: 5 A → 2·25·2.6 mΩ·1.3 = **0.17 W**.
  (Same FET as the power_input LM74800 pairs; was BSC040N08NS5 before the cost pass. Qg 74 nC vs 43 nC:
  turn-on is set by the 22 nF dV/dt cap anyway; DGATE 2.6 A pull-down discharges 74 nC in ~30 ns, so the
  0.5 µs reverse turn-off is unaffected.)
- EN/UVLO = SRC_ON (100k pull-down). Inrush: HGATE 55 µA into 22 nF (+100 Ω) → 2.5 V/ms; closes at vSafe5V
  into ≤ 20 µF → negligible inrush.
- OV backstop independent of +3V3 and logic: VSNS = VBUS_LAPTOP, SW → 255k/10k → OV: 1.231·26.5 = **32.6 V**
  (31.7–33.6 V), turns HGATE off in 4 µs.
- **Hardware enable** SRC_ON = LAPTOP_SRC_EN AND EXT_PWR_PRESENT AND VBB_PG AND LAPTOP_OVP_N AND PG5_DLY:
  SN74LVC1G11 (3-input AND) with input C = SRC_PGOK, a BAT54A diode-AND of the two open-drain signals
  (10k pull-up; low level ≈ 0.3 V < VIL 0.8 V), plus Q216 pulling SRC_PGOK low while Q215 (gate = SNK_PGD, the
  delayed PG_5V) is off (R242 100 k pull-up to +3V3 on its drain). PG_5V is not diode-ORed into SRC_PGOK
  directly: the 10 k/+3V3 pull-up would back-feed the PG_5V node (100 k to an unpowered 5V_BUCK) to ≈ 2.8 V and
  fake "good" in bus-powered mode.
- Logic unpowered (+3V3 absent) → SRC_ON pulled low → off.

## 5. Bus-power sink switch (VBUS → +5V)

Requirement: ~3 A limit, withstand ≥ 30 V when off (VBUS is 28 V while sourcing), never on together with the
source, never back-feed.
- **Stage 1** — CSD18543Q3A (60 V) as high-side switch driven by **LM74502** (C3236215, 8157 stock; 3.2–65 V,
  charge pump, OV pin). Drain on VBUS_LSW, source on SNK_MID: off it blocks VBUS up to 60 V; its body diode
  points back towards VBUS (reverse is handled by stage 2). OV cut-off 422k/100k → 1.25·5.22 = **6.5 V**
  (6.1–6.9 V), 1 µs: a >5 V contract can never reach +5V.
- **Stage 2** — **TPS259470A** eFuse (C3662799, 1538 stock; 28 V abs, used ≤ 6.5 V): true reverse-current blocking
  (+5V from the LM5148 never back-feeds VBUS), active current limit ILM 1.0k → 3340/R = **3.34 A** (3.0–3.7 A),
  auto-retry 110 ms; OVLO 40.2k/10k → **6.0 V**; UVLO 121k/47k → **4.29 V** rising / 3.9 V falling;
  dVdt 3.3 nF → ~0.6 V/ms soft start into the +5V bulk (≈ 0.6 A into 1000 µF); ITIMER 1 nF ≈ 0.8 ms.
- **Enable** SNK_ON = LAPTOP_SNK_EN (10k series, 47k pull-down → 2.7 V high) AND NOT (EXT_PWR_PRESENT AND
  PG5_DLY) AND NOT SRC_ON → LM74502 EN/UVLO (1.24 V threshold). Q218 (gate EXT_PWR_PRESENT) and Q219 (gate
  SNK_PGD) in series pull SNK_ON low; Q220 (gate SRC_ON) pulls it low directly.
- **PG5_DLY / SNK_PGD** = `PG_5V` through R251 100 k into C242 100 nF (τ = 20 ms with the 100 k PG pull-up on
  power_rails): crosses the AO3400A threshold 2.7–6.7 ms after the LM5148 PG rises — after its soft start has
  finished and 5V_BUCK has taken over +5V. D204 (BAT46W) discharges it at once when PG_5V drops. A rising EXT
  edge alone never kills the sink; loss of external power (EXT low) re-enables it in µs via Q218.
- **Bus-power → external-power hand-over is make-before-break (review finding 3):**
  1. External power appears → `EXT_PWR_PRESENT` high; the sink stays on (PG_5V low) and keeps +5V up.
  2. VIN ramps (barrel 1.17 V/ms), LM5148 starts at 8 V and soft-starts 5V_BUCK; when 5V_BUCK exceeds +5V the
     LM74700 conducts. During the overlap both paths feed +5V: the TPS259470A blocks reverse current into
     VBUS, the LM74700 blocks reverse current into 5V_BUCK, so whichever is higher carries the load, no backfeed.
  3. PG_5V high + 2.7–6.7 ms → Q219 on → sink off → +5V carried by the buck alone (load step ≤ 3 A).
  4. Only now can SRC_PGOK go high (Q215/Q216), so a source enable can never cut the sink before the buck runs.
- **Interlock / mutual exclusion:** the source requires EXT_PWR_PRESENT AND PG5_DLY high, which is exactly the
  sink release term; in addition SRC_ON forces the sink off through Q220 in ~2 µs while the source LM74800
  HGATE needs ms to turn its FET on. Even if the two thresholds on SNK_PGD (Q215 vs Q219) differ, the explicit
  SRC_ON kill opens the sink long before the source conducts, so both are never on together.
- Loss at 3 A: 9·(8 mΩ·1.3 + 28 mΩ + 5 mΩ shunt) ≈ 0.39 W.

Why not a single eFuse: no stocked eFuse combines ≥ 30 V off-state, 3 A and reverse blocking at 5 V: TPS2663x
(60 V) has a 4.5 V minimum and a 15.5 V default UVLO, and only fixed 35 V OV clamp variants are in stock
(would pass up to 33 V to +5V); TPS2660 is 2.2 A; TPS25947 alone is 28 V abs max (< 31.1 V OVP trip).

## 6. Independent VBUS OVP (latched) → LAPTOP_OVP_N

- Senses **max(VBUS_LAPTOP, VBB_OUT)** through a BAV70 (100 V; BAT54C is only 30 V): catches a run-away converter
  (e.g. open Rtop, which would otherwise run to the 83.5 V OVP2) before the source switch closes.
- Divider 1.1M/46.4k + diode: trip = 1.242·(1 + 1100/46.4) + 0.45 = **31.1 V**; ≈ 29.9–32.3 V RSS (29.3–33.1 V
  with every corner stacked: ref 1.208–1.276 V, offset ±15 mV, 1 % resistors, Vf 0.35–0.55 V) — above the 28.7 V
  worst-case regulation, ≤ 34 V PMG1 VBUS abs max. C243 2.2 nF → 98 µs filter.
- **Load-dump margin (review finding 9):** a 5 A unplug at 28 V overshoots VBB_OUT by ≈ 5 A/(2π·3 kHz·220 µF)
  ≈ 1.2 V for ~100 µs; through the 98 µs filter the comparator sees ≈ 0.7 V of it (simulated first-order), i.e.
  ≤ 29.4 V against a ≈ 29.9 V (RSS) minimum trip — no false latch. Cost: a run-away (≤ 28 V/ms at the current
  limit) trips ≈ 2.6 V later; VBUS_LAPTOP stays protected by the 4 µs LM74800 backstop (31.7–33.6 V). Bench
  check the overshoot at 28 V / 5 A; if > 1 V, raise C243 to 4.7 nF.
- **TLV3011** (C2870632; open-drain, internal 1.242 V reference; TLV3012 would be push-pull). Output pull-up
  10k goes to **VBB_EN**. On a trip the output releases, 1N4148W + 4.7k drive IN+ to 2.0 V (> 1.242 V even with
  VBUS = 0) → **latched**. AO3400A inverts to LAPTOP_OVP_N (10k to +3V3).
- Effects: SRC_ON drops (source switch opens), the LM51770 EN AND drops (converter off, VBB_OUT discharged,
  VBB_PG low).
- **Reset only by VBB_EN low** (the latch pull-up source disappears). Latched instead of auto-retry because >30 V
  on the laptop port means a real hardware fault (feedback open, FET short, back-feed); auto-retry would
  re-apply the overvoltage periodically. Clearing requires a deliberate PMG1 VBB_EN cycle, which restarts from the
  5.1 V default and re-arms the latch. RP2350 has no path to VBB_EN.

## 7. VBUS_LAPTOP monitor and capacitance

- **INA226** (C49851, 44k stock) at **0x44** (A1 = VS, A0 = GND; power_rails uses 0x41, power_input INA237 0x45).
  Shunt 5 mΩ 1206 (RLM12FTCMR005, 1 W) between VBUS_LSW (IN+) and VBUS_LAPTOP (IN−): 5 A → 25 mV of ±81.92 mV, 0.125 W;
  positive = sourcing, negative = bus-powered sink. CURRENT_LSB = 0.5 mA → CAL = 0.00512/(0.5 mA·5 mΩ) = **2048**,
  POWER_LSB 12.5 mW. VBUS pin on the connector side (36 V max). ALERT unused.
- Connector-side capacitance (VBUS_LAPTOP + VBUS_LSW, no switch between them): 10 µF/50 V X7R + 2× 100 nF →
  ≈ 9 µF at 5 V, ≈ 4 µF at 28 V: inside **cSnkBulk 1–10 µF** for bus-powered attach, and small for fast
  vSafe0V/role swaps. **cSrcBulk ≥ 10 µF** is met behind the source switch (VBB_OUT ≈ 220 µF). VBUS TVS and the
  receptacle live on `usbc_muxes`.

## Thermal estimate (140 W, 20 V in)

| Item | Loss | Note |
|---|---|---|
| Q201 / Q203 / Q204 | 0.62 / 0.46 / 1.14 W | TDSON / VSONP on 2 oz pours + via arrays: ~35–45 K/W → ≤ +50 K at Q204 |
| L201 XAL1010-103 | 0.9 W | (7.2/15.5)²·40 K ≈ +9 K self-heating |
| RCS + RISNS | 0.41 W | 2512 |
| LM51770 | 0.1–0.5 W | VCC LDO; worst 48 V in at 5 V out: 11 mA·48 V = 0.53 W → +18 K (33.6 K/W) |
| Source FETs + 5 mΩ shunt | 0.39 W | |
| **Total hot zone** | **≈ 4.5 W** | 48 V in: ≈ 4.3 W |

Consistent with `power-budget.md` (5.5 W budget for buck-boost + path). Place a TMP1075 (sensors sheet) between
Q204 and L201; firmware derates the contract on temperature. Keep the zone away from the LM5148 stage and hub.

## Part list (this sheet)

| Ref | Part | LCSC | JLC stock | Note |
|---|---|---|---|---|
| U201 | TI LM51770DCPR | C43351171 | 1007 | buck-boost controller |
| Q201, Q202 | Infineon BSC0805LS | C534374 | 15000 | 100 V, 7.7 mΩ @4.5 V |
| Q203, Q204, Q217 | TI CSD18543Q3A | C840100 | 12215 | 60 V, 12 mΩ @4.5 V |
| L201 | Coilcraft XAL1010-103MED | C6358489 | 707 | 10 µH, Isat 17.5 A |
| R201 | TA-I RLP25FEGR004 2512 | C459681 | 15078 | 4 mΩ peak sense (3 W, 50 ppm; same as R303) |
| R202 | Yageo PE2512FKE070R008L | C2075410 | 1855 | 8 mΩ output sense |
| R243 | TA-I RLM12FTCMR005 1206 | C316225 | 201600 | 5 mΩ INA226 shunt (1 W; same as R415) |
| U202 | TI LM74800QDRRRQ1 | C3215600 | 4038 | source switch (also 2× on power_input) |
| Q213, Q214 | Infineon BSC026N08NS5ATMA1 | C5955453 | 5786 | 80 V, 2.6 mΩ (same as Q104–Q107) |
| U203 | TI SN74LVC1G11DBVR | C22046 | 13937 | 3-input AND |
| U204 | TI INA226AIDGSR | C49851 | 44390 | 0x44 |
| U205 | TI LM74502DDFR | C3236215 | 8157 | sink stage 1 |
| U206 | TI TPS259470ARPWR | C3662799 | 1538 | sink stage 2 eFuse |
| U207 | TI TLV3011AIDBVR | C2870632 | 7893 | OVP comparator + ref (TLV3011B has POR: see risks) |
| D202 | BZT52C5V1 | C173407 | 610k | |
| D203 | BAT54A | C130910 | 288k | |
| D205 | BAV70 | C68978 | 210k | basic |
| D201, D206 | 1N4148W | C81598 | 5.2M | basic |
| D204 | BAT46W | C83152 | 107k | PG_5V delay fast discharge |
| Q205–Q211, Q215, Q216, Q218–Q221 | AO3400A | C20917 | 959k | basic |
| R255 | 46.4 k 0402 | C5126026 | 175k | OVP divider |
| Q212 (discharge) | 2N7002 | C8545 | 1.6M | basic |
| Q217 | TI CSD18543Q3A | C840100 | 12215 | sink stage 1 (listed above with Q203/Q204) |
| C201–C204 | Taiyo HMK325C7475KN-TE 4.7 µF/100 V | C697607 | 330k | (47 µF VIN alu removed) |
| C205–C210, C233 | TDK C3225X7R1H106KT000E 10 µF/50 V | C432929 | 28k | |
| C211, C212 | KNSCHA 100 µF/35 V polymer | C2982822 | 7842 | 6.3×7 |
| R235 | 150 Ω 1 W 2512 | C2934049 | 52k | discharge |
| others | 0402/0603/0805 R/C | see `power_laptop.py` | ≥ 18k | mostly basic |

`python3 tools/bom_check.py` passes for every part on this sheet.

## Assumptions
- VIN 9–50.4 V from power_input; ≥ 140 W available only from inputs ≥ ~16 V (PD 20/28/48 V, barrel 19–24 V).
- PMG1 (pd_pmg1 sheet) drives VBB_EN, VBB_VSEL0..2, LAPTOP_SRC_EN, LAPTOP_SNK_EN as 3.3 V push-pull GPIOs,
  provides VBUS discharge and its own VBUS OVP/OCP; laptop connector + TVS on usbc_muxes.
- EXT_PWR_PRESENT is a 3.3 V push-pull signal (74LVC1G32 on power_input).
- The laptop drops to standby current before accepting a lower voltage (PD sink behaviour).

## Open issues / risks
1. **Loop compensation** is a datasheet-equation starting point; the Cm/Rs doublet must be checked for
   conditional stability (TI model in SIMPLIS/PSpice, bode measurement). Fallback: Cm 2.2 µF (2× faster slew,
   still ≤ 10 mV/µs) or FPWM.
2. **LM74800 at VS = 5.1 V**: gate drive is specified 7 V for 3–5 V supply while the CAP UVLO rising threshold
   is up to 7.9 V — confirm the source switch closes at vSafe5V on the bench. Fallbacks: default 5.2 V
   (Rbot 23.7k), or LM74502H + discrete reverse comparator.
3. **Dead-battery bus power**: LAPTOP_SNK_EN must be driven high by PMG1 from its VBUS-powered domain while +3V3
   is absent; otherwise the deck can never boot from the laptop. Coordinate with pd_pmg1.
4. **PSM down-steps** rely on the laptop load/PMG1 VBUS discharge; with no load VBB_OUT stays at the old
   voltage until VBB_EN is cycled (then the 150 Ω discharge runs). FPWM option exists (DNP R) but returns
   energy to VIN.
5. OVP window (≈ 29.9–32.3 V RSS) is driven by the TLV3011 1 % reference + 15 mV offset; tighter would need a
   separate 0.5 % reference. The non-B TLV3011 has **no power-on reset**: its output is undefined while +3V3
   ramps, so with VBB_EN already high (PMG1 alive on laptop VBUS through a +3V3 brownout) the latch can set
   spuriously. Use TLV3011B (same pinout) when stocked, or have firmware cycle VBB_EN after any +3V3 recovery.
10. **OVP1/nFLT in PSM during VSEL down-steps** (review note 15): the "OVP1 masked in PSM" sentence in SNVSCL2A
    §8.3.15 may mean pulse-skipping operation rather than MODE = low. If nFLT asserts while VBB_OUT lags a
    down-step, VBB_PG drops and SRC_ON opens on every 28→5 V step. Bench-verify a 28→5 V step at standby load;
    fallback FPWM (DNP 0 Ω) or firmware blanking.
6. 12 V input cannot deliver 140 W (current limit) — PMG1 policy must cap the offer by input source (already
   in power-budget.md).
7. Footprints to check before layout: XAL1010 (EasyEDA name references XAL1010-332ME land pattern), LM51770
   HTSSOP-38 exposed pad, TPS259470 RPW HotRod pads, polymer/alu caps use KiCad CP_Elec footprints (6.3×7.7,
   10×10) — compare with the KNSCHA 6.3×7 / SamYoung 10×10 land patterns.
8. Layout: minimise the two hot loops (VIN caps–Q201–Q202, BB_PSO caps–Q204–Q203), Kelvin-route CSA/CSB, ISNSP/N
   and INA226 IN± , keep BB_FB/BB_FBM small and away from SW nodes, 2 oz copper + via arrays under the FETs.
9. Optional RC snubbers on BB_SW1/BB_SW2 and gate resistor values (0 Ω placeholders R203–R206) to be tuned for EMI.
