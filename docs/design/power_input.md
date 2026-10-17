# odock-10 — power_input sheet

Source: `hardware/odock-10/sheets/power_input.py` (generates `power_input.kicad_sch`, ref_base 100, A2).
Status: second pass after the power review (`docs/review/power.md`), 2026-10-02. `build_all.py power_input` →
`netlist verify: OK`.
Stock figures: JLC parts API on 2026-10-02.

## Topology

```
 USB-C PD-in (J101) ─ VBUS_PDIN ─┬─ 5.0SMDJ51A, 2.2 µF + 100 nF
   CC ─ TPD4S480 (U101) ─ TPS26750 (U102) ── EEPROM AT24C512C (U103, private I2Cc)
   │       VBUS → VBUS_LV (×0.42 in EPR) → TPS26750 VBUS
   │       TPS26750 POWER_PATH_EN ─ 2×2N7002 buffer ─ PD_SINK_EN
   └─ Q104 ──(PD_MID)── Q105 ──┐   LM74800 U104: ideal diode + load switch, EN = PD_SINK_EN, OV 57 V
                                ├── VIN_OR ── 2 mΩ shunt ── VIN (47 µF/100 V alu damping + 1 µF + 100 nF)
 Barrel PJ-063BH (J102) ─ VBAR ─┤                           INA237 (U109) on I2C_SYS, 0x45
   5.0SMDJ48CA, 100 nF          │
   └─ Q106 ──(BAR_MID)── Q107 ──┘   LM74800 U105: reverse polarity, OV 27.4 V, UVLO 6.8 V
                                    (always armed: no PD-in priority, the higher input feeds VIN)

 EXT_PWR_PRESENT = BAR_OK OR PD_OK      (SN74LVC1G32, U108; all on +3V3)
   BAR_OK = TLV6700 window on VBAR (8.2 … 28.5 V), via 1N4148W
   PD_OK  = TLV6700 window on VBUS_PDIN (7.7 … 56.2 V) AND TPS26750 sink path enabled (Q103)
```

All four path FETs are BSC026N08NS5 (80 V, 2.6 mΩ, TDSON-8). Both inputs are true ideal diodes with a
second, series cut-off FET, so neither input can back-feed the other. VIN may also be back-fed from
downstream (e.g. the bidirectional buck-boost); both paths block that.

**No hardware input priority (review findings 1 and 2).** Both LM74800s stay armed whenever their input is
within its UVLO/OV window; the input with the higher voltage supplies VIN, and when it goes away the other ideal
diode takes over within the LM74800 reverse/forward response (µs), with VIN dipping only to the other input's
voltage. The earlier design shut the barrel LM74800 down from `PDIN_PRESENT` (Q108); that browned the deck out on
every PD-in loss (HGATE needs ms to re-arm from 0 V) and disabled a working barrel on a 5 V PD contract. Source
preference is now a firmware/power-budget policy: to prefer PD-in over a barrel, request a PD voltage above the
barrel (e.g. 28/36/48 V vs 19–24 V); to prefer the barrel, request a lower PD voltage or none. `PDIN_PRESENT` is
kept as an informational signal only.

### Interface nets
Global (from `nets.py`): `VIN`, `VBUS_PDIN`, `EXT_PWR_PRESENT`, `PDIN_PRESENT`, `I2C_PD_SCL/SDA`,
`PDIN_INT_N`, `I2C_SYS_SCL/SDA`, `+3V3`, `GND`. **No new inter-sheet nets.** (The `nets.py` comment on
`PDIN_PRESENT` still says "disables barrel path"; that is no longer true — it is status only.)
PWR_FLAGs: `VIN`, `VBUS_PDIN`, plus local `VBAR`.

## 1. PD-in connector and protection

- **J101 JAE DX07S024XJ1R1100** (C134113, 1626 in stock): 24-pin, 5 A / 48 V EPR rated. Same part as the
  laptop port, so one footprint to validate. Power only: VBUS, CC1/CC2, GND, shell → GND.
  **USB2 D+/D-, SBU and SuperSpeed pins are left unconnected** (no data on this port). Consequence: no
  BC1.2 detection, which is irrelevant here since a 5 V-only charger cannot run the deck anyway.
- **TVS 5.0SMDJ51A** (Liown, C2990373, 2.8k; replaced SMCJ51A C408371 on the same SMC/DO-214AB footprint):
  VRWM 51 V ≥ 50.4 V (EPR 48 V + 5 %), VBR 56.7–62.7 V, VC 82.4 V at 61 A. The 5 kW die has about a third of the
  SMCJ51A dynamic resistance (≈ 0.32 Ω vs ≈ 1.1 Ω): ≈ 64 V at 5 A and ≈ 68 V at 18 A, where the SMCJ51A was at
  82 V. See risks: the TPD4S480 VBUS pin is 63 V abs max.
- **TPD4S480** (C43131250, 2881): follows the TI reference (TPD4S480 Fig. 7-1, TPS26750 Fig. 8-24):
  RPD_G1/G2 shorted to C_CC1/C_CC2 (dead-battery Rd needed: the deck may be completely unpowered),
  VBIAS 100 nF/100 V (≥ 63 V required), VPWR from TPS26750 LDO_3V3 with 1 µF, VBUS_LV 100 nF/50 V,
  FLT# 10 k to LDO_3V3 → TPS26750 GPIO2. EPR_EN from TPS26750 GPIO0 (also auto-asserts above
  EPR_THRESH). EPR_BLK_G unused (the optional blocking FET is only needed to source 5 V from PP5V).
  SBU channels unused.

## 2. TPS26750 (U102)

- Supplies: VIN_3V3 = `+3V3` (10 µF), LDO_3V3 10 µF (5–25 µF allowed), LDO_1V5 10 µF (4.5–12 µF), CC1/CC2
  220 pF each (200–480 pF). VBUS pins = VBUS_LV (≤ 21.2 V in EPR: 0.42 × 50.4 V).
- **PP5V tied to GND**: sink-only port, no 5 V source and no VCONN needed. (Open issue: confirm with TI that
  grounding PP5V is acceptable; alternative is +5V with 10 µF.)
- **ADCIN1/ADCIN2 = 100 k / 100 k each** (DIV 0.5 → decoded 5/5): *AlwaysEnableSink*, I2C target address
  index #2 = **0x21**. The sink path is enabled at the implicit 5 V contract. **With a blank EEPROM (JLC
  delivers it blank) USB PD stays disabled** until a host loads a configuration (SLVSH67 §7.4.1), so VIN is only
  5 V, which does not start the LM5148 (UVLO 8 V): the RP2350 does **not** power up from PD-in alone. First
  programming needs the barrel, laptop bus power, or the I2Cc test pads (see bring-up below). Consider ordering
  the EEPROM pre-programmed. This matches the TI example schematic. Alternative (TI's recommendation when a patch is loaded from EEPROM): *SafeMode*,
  ADCIN1 → LDO_3V3, ADCIN2 → GND (7/0), address 0x20 — then a blank EEPROM means no PD-in power.
- **EEPROM AT24C512C-SSHD-T** (C12371, 53k): 64 KB ≥ 36 KB required, address 0x50 (A2..A0 = GND), WP = GND,
  4.7 k pull-ups to LDO_3V3 (was 2.2 k: less load on the 5 mA dead-battery LDO), own 100 nF. Test pads TP101/TP102 on I2Cc for recovery programming.
  The RP2350 reaches it only through the TPS26750 host interface (I2Ct at 0x21); see open issues.
- GPIO use (configured in the EEPROM image):
  - GPIO0 → `PDIN_EPR_EN` (TPD4S480 EPR_EN), 100 k pull-down.
  - GPIO1 → `PDIN_PRES_L` → 47 k (R117) → **`PDIN_PRESENT`**; 100 k pull-down so Hi-Z / blank EEPROM = low.
    Configure as push-pull "sink contract active / PD power path enabled". **Informational only** (PMG1 P7.2,
    RP2350); it no longer controls any power path. The 47 k limits back-drive into the unpowered PMG1 P7.2
    (not fail-safe) during a PD-in-only cold start to (3.3 − 0.5) V / 47 k ≈ 60 µA (< 0.5 mA PMG1 injection limit,
    < 1 mA TPS26750 GPIO limit). Both loads are CMOS inputs, so the RC delay is negligible.
  - GPIO2 ← TPD4S480 FLT#.
  - GPIO3–7, GPIO11: 100 k to GND (datasheet: tie low when unused; resistor avoids a short if a config drives one).
  - I2Ct_IRQ → `PDIN_INT_N` (10 k to +3V3 on this sheet). I2Cc_IRQ 10 k to LDO_3V3 (must not be grounded).
  - I2Ct SDA/SCL → `I2C_PD_SDA/SCL`; pull-ups expected on the MCU sheet.
- POWER_PATH_EN (6–12 V, ~10 µA charge-pump output, not a logic level) is buffered exactly as datasheet
  Fig. 8-5: Q101 inverts it (`PD_PP_EN_INV`, 100 k to LDO_3V3), Q102 gives `PD_SINK_EN` (100 k to LDO_3V3)
  for the LM74800 EN. Q103 (gate = `PD_PP_EN_INV`) pulls `PD_OK` low while the sink path is off.

## 3. PD-in sink path (U104 LM74800-Q1, Q104/Q105)

Chosen over a TPS26750-driven FET pair because POWER_PATH_EN is referenced to GND and cannot drive a high-side
NFET at 48 V; the LM74800 adds reverse blocking (ideal diode), OV cut-off and inrush control.

- Common-drain back-to-back: Q104 source = VBUS_PDIN (DGATE, ideal diode), Q105 source = VIN_OR (HGATE).
  VS = C = PD_MID, 100 nF VS–GND (100 V), 100 nF CAP–VS.
- **OV**: R121 100 k (from SW) / R122 2.2 k → V_OV = 1.231 × (102.2 / 2.2) = **57.2 V** (55.5–58.9 V with
  V_OVR 1.195–1.267 V); recovery at 1.13 × 46.45 = 52.5 V. Above 50.4 V EPR max, below 70 V abs max.
- **Inrush**: CdVdT = 47 nF/100 V + 100 Ω on HGATE. dV/dt = 55 µA / 47 nF = 1.17 V/ms → 48 V in ~41 ms;
  into ≤ 100 µF total on VIN (§6) I ≈ 0.12 A. (The cap sees up to VIN + 11 V ≈ 62 V → 100 V part.)
  HGATE dV/dt acts only at turn-on: during PD voltage transitions the path is fully on and the source charges
  all of VIN directly, which is why VIN capacitance is budgeted to cSnkBulkPd (§6).
- R121 (OV divider top, sees VBUS_PDIN through SW) is 0805 (150 V working voltage), like every resistor with a
  terminal on VBUS_PDIN or VBAR.
- Losses: 5 A × (2 × 2.6 mΩ) = 0.13 W (+ 10.5 mV regulated drop on Q104 at light load).

## 4. Barrel path (U105 LM74800-Q1, Q106/Q107)

- **J102 Same Sky PJ-063BH** (C3095900, 240 stock — low, pre-order): 5.5 × 2.5 mm, 8 A, 24 V.
  Pin 1 = centre pin (+), pin 2 = sleeve/spring (–) per datasheet. The two MS (mounting/shield) tabs are
  **left unconnected**: tying them to GND would short a reversed plug if the shield touches the sleeve.
- **TVS 5.0SMDJ48CA** (Littelfuse, C2649886, 1.3k; replaced SMCJ48CA C408370, same SMC footprint, bidirectional):
  standoff 48 V so a wrongly plugged 36–48 V brick or a reversed 24 V supply does not destroy it; VC 77.4 V at
  65 A, ≈ 64 V at 19 A (SMCJ48CA: 77.4 V at 19 A), under the 80 V FETs and the 70 V LM74800 A pin.
- **Why LM74800 instead of the planned LM74720 (C5219205)**: the LM74720 turns its second FET off by pulling
  the gate (PD pin) to GND. In an OR-ing design VIN stays up from PD-in, so that gives Vgs ≈ −48 V (beyond the
  ±20 V rating); TI's 18 V gate-source zener would then conduct and dump up to 10 mA × ~47 V into the PD
  pull-down. The LM74800 references HGATE to OUT, provides the same −65 V reverse protection and an
  adjustable OV, adds an accurate UVLO, needs no boost inductor, and is the same part as the PD path (4040 in
  stock vs 776).
- **OV**: R125 100 k / R126 4.7 k → 1.231 × 104.7 / 4.7 = **27.4 V** (26.6–28.2 V); recovers at 25.2 V
  (1.132 × 22.28). A 24 V ± 5 % brick (25.2 V max) never trips it.
- **UVLO**: R127 100 k / R128 22 k on EN/UVLO → rising 1.231 × 122 / 22 = **6.8 V**, falling 6.3 V.
  R125/R127 (tops on BAR_SW / VBAR) are 0805, 150 V.
- **No PD-in priority** (review findings 1/2): Q108 and the `PDIN_PRES_L` → EN/UVLO connection are removed.
  Both paths are always-armed ideal diodes; the higher voltage wins with no cross-conduction, and a hand-over
  in either direction never passes through a shutdown/re-arm of an LM74800.
- Inrush: identical to the PD path (47 nF + 100 Ω, 1.17 V/ms).
- Losses: 8.3 A × 2 × 2.6 mΩ = 0.36 W (on top of the jack contact resistance).

## 5. EXT_PWR_PRESENT

Derived from the input side only (VIN can be back-fed, and a plain VIN comparator would see that):

**Meaning:** VIN is (or is about to be) supplied at ≥ ~8 V by PD-in or the barrel. Because both input paths
are always armed, an asserted OK term really means that input is feeding (or about to feed) VIN; a 5 V PD
contract never counts. The laptop sink switch is released only on `EXT_PWR_PRESENT` AND `PG_5V` (power_laptop),
so an `EXT_PWR_PRESENT` that rises while VIN is still ramping cannot brown the deck out.

- **BAR_OK**: TLV6700 U106 window on VBAR through D103 (1N4148W, keeps negative voltage off the TLV6700
  inputs, abs min −0.3 V). Ladder R129 1 M (0805) / R130 39 k / R131 15 k (total 1.054 MΩ), V_IT 0.40 V, diode
  ≈ 0.4 V at the ~8 µA ladder current (0.3–0.5 V):
  - UV (INA+ at the 1 M / 39 k node): 0.4 × 1054 / 54 + 0.4 = **8.2 V** (≈ 8.0–8.5 V with TLV6700, 1 % R and
    diode tolerance), so a 9 V −5 % brick (8.55 V) counts. Was 9.2 V (review finding 7).
  - OV (INB− at the 39 k / 15 k node): 0.4 × 1054 / 15 + 0.4 = **28.5 V** (≈ barrel OV 27.4 V; in the
    26.6–28.5 V band BAR_OK may read high while the LM74800 is already cut off — only reachable with an
    out-of-spec 27–28 V brick; harmless now because the sink release also needs `PG_5V`).
  - At 48 V on VBAR the UV input sees 2.4 V (< 7 V abs max).
- **PD_OK**: TLV6700 U107 window on VBUS_PDIN, R133 1 M (0805) / R134 47 k / R135 7.5 k (1.0545 MΩ):
  UV 0.4 × 1054.5 / 54.5 = **7.7 V**, OV 0.4 × 1054.5 / 7.5 = **56.2 V**, wire-ANDed with Q103 (sink path
  enabled). **A 5 V PD contract therefore does not count as external power** (5 V on VIN cannot run the
  buck-boost/laptop source path usefully).
- Open-drain outputs per source wire-AND into BAR_OK / PD_OK (100 k pull-ups to +3V3), then SN74LVC1G32 U108
  → `EXT_PWR_PRESENT` (push-pull, +3V3). Everything runs from +3V3, which exists whenever anything powers the
  deck (both TLV6700s are low when +3V3 is absent, and so is the gate).

## 6. VIN: shunt, monitor, bulk

- **Shunt** R137 TA-I RLP25FEGR002, 2 mΩ 1 % 3 W 50 ppm 2512 (C459679, 52k; same part as R312): 8.3 A → 16.6 mV, P = 0.14 W.
  Placed between VIN_OR and VIN so both sources and any back-feed are measured. Route IN+/IN− as Kelvin pairs.
- **INA237** (U109, C2864837, JLC stock ~5k; replaced the 0-stock INA228 — same pinout):
  85 V common mode, 16-bit. VBUS pin = VIN. VS = +3V3. Address **0x45**
  (A1 = A0 = VS) — chosen to avoid the TMP1075 range 0x48–0x4F and the usual 0x40/0x41 of the INA226s.
  ADCRANGE = 1 (±40.96 mV) → ±20.5 A full scale. The INA237 is 16-bit: CURRENT_LSB = 20.48 A / 2¹⁵ = 625 µA;
  SHUNT_CAL = 819.2 × 10⁶ × 625 µA × 0.002 Ω × 4 (ADCRANGE=1) = **4096**. ALERT unused (NC).
- **VIN capacitance (review finding 4).** With the PD-in sink path on, the PD source charges *everything* on
  VBUS_PDIN and VIN at every upward PD transition (HGATE dV/dt only acts at turn-on). USB PD limits this to
  **cSnkBulkPd ≤ 100 µF**. The old 2 × 100 µF + 2 × 47 µF electrolytics (≈ 320 µF) are gone; VIN now carries
  one **47 µF / 100 V alu (C122, SamYoung MVK, C371305)** for damping, plus C123 1 µF / 100 V and C124 100 nF.
  The converter sheets keep only their input ceramics. Budget (ceramics with DC-bias derating; alu at +20 %
  tolerance, 56.4 µF):

  | Where | Parts | at 5 V | at 20 V | at 48 V |
  |---|---|---|---|---|
  | VBUS_PDIN (before the switch) | C101 2.2 µF/100 V 1210, C102 100 nF, PD_MID 100 nF | 2.4 | 2.0 | 1.4 |
  | VIN, power_input | C122 47 µF alu, C123 1 µF/100 V 0805, C124 100 nF, BAR_MID 100 nF | 57.6 | 57.3 | 57.0 |
  | VIN, power_laptop | C201–C204 4 × 4.7 µF/100 V X7S 1210, C214 100 nF, C215 1 µF | 19.9 | 14.9 | 9.0 |
  | VIN, power_rails | C301–C304 4 × 4.7 µF/100 V X7S 1210, C305/C306 100 nF, C315 1 µF (behind D301) | 20.0 | 15.0 | 9.1 |
  | **Total** | | **≈ 100 (worst)** | **≈ 89** | **≈ 76** |

  Derating used: 4.7 µF/100 V X7S 1210 ≈ 75 % at 20 V and 45 % at 48 V; 2.2 µF/100 V X7R ≈ 80 % / 55 %;
  1 µF/100 V 0805 ≈ 70 % / 40 %. With the nominal 47 µF the 5 V figure is 91 µF. At 30 mV/µs (vSrcSlewPos max)
  the transition charge current is ≤ 2.7 A at 20 V+, ≤ 3 A at 5 V.
- **Damping / input-filter stability.** The source (charger + cable, ≈ 0.5–2 µH, ≈ 30 mΩ) and the ≈ 31 µF of
  converter ceramics form an LC with Z0 ≈ 0.13–0.25 Ω; undamped, its peak output impedance is 0.55–2.2 Ω, which
  meets the converters' negative input impedance (|Zin| = V²/P ≥ 1.35 Ω at 9 V / 60 W, 2.1 Ω at 20 V / 190 W).
  The 47 µF alu is a series R-C damping branch through its own ESR (≈ 0.1–0.6 Ω): computed peak |Zout| is
  0.13–0.5 Ω over that L/ESR range (0.7 Ω with a cold, 1 Ω ESR and 2 µH) — ≥ 6 dB below |Zin|min. It sits at
  the VIN node next to the shunt, between the two converter input groups.
- Firmware contract: before any PD-in renegotiation (Request after Accept, EPR entry) the deck must drop to
  pSnkStdby (≤ 2.5 W) — reduce the laptop contract (PMG1) and port loads, or renegotiate only while the barrel
  carries the load. VIN hold-up with ≈ 90 µF is negligible; a PD hard reset without a barrel resets the deck.

## Part list

| Ref | Part | LCSC | JLC stock | Notes |
|---|---|---|---|---|
| J101 | JAE DX07S024XJ1R1100 | C134113 | 1626 | USB-C 48 V/5 A, hybrid THT |
| J102 | Same Sky PJ-063BH | C3095900 | 240 | Low stock; pre-order |
| U101 | TI TPD4S480RUKR | C43131250 | 2881 | |
| U102 | TI TPS26750SRSMR | C42166327 | 165 | Low stock; Mouser ~1500 |
| U103 | Microchip AT24C512C-SSHD-T | C12371 | 53480 | |
| U104, U105 | TI LM74800QDRRRQ1 | C3215600 | 4040 | LM74800MDRRR C7216630 (6031) is a drop-in |
| U106, U107 | TI TLV6700DDCR | C2868382 | 1613 | |
| U108 | TI SN74LVC1G32DBVR | C10096 | 112k | |
| U109 | TI INA237AIDGSR | C2864837 | 5240 | Replaced INA228 (0 stock) |
| Q104–Q107 | Infineon BSC026N08NS5 | C5955453 | 5786 | 80 V 2.6 mΩ; TPH2R608NH C5379811 alternative |
| Q101–Q103 | 2N7002 | C8545 | basic | (Q108 removed with the PD-in priority) |
| D101 | 5.0SMDJ51A (Liown) | C2990373 | 2797 | 5 kW, SMC; same footprint as SMCJ51A |
| D102 | 5.0SMDJ48CA (Littelfuse) | C2649886 | 1332 | 5 kW bidirectional, SMC |
| D103 | 1N4148W | C81598 | basic | |
| R137 | RLP25FEGR002 2 mΩ 2512 | C459679 | 52095 | same as R312 |
| C122 | SamYoung MVK 47 µF 100 V alu 10×10 | C371305 | 1847 | VIN damping (only VIN electrolytic) |
| C123 | 1 µF 100 V X7S 0805 | C126585 | 30k | |
| C101 | 2.2 µF 100 V X7R 1210 | C153036 | 347k | |
| C102, C103, C112, C115, C116, C124 | 100 nF 100 V X7R 0805 | C28233 | 1.25M | basic |
| C114, C118 | 47 nF 100 V 0603 | C576852 | 233k | |
| C106–C108 | 10 µF 0603 | C19702 | basic | |
| R121, R125, R127 | 100 k 0805 (150 V) | C149504 | basic | divider tops on VBUS_PDIN / BAR_SW / VBAR |
| R129, R133 | 1 M 0805 (150 V) | C17514 | basic | |
| others | 0402/0603 R & C | C25741, C25744, C25879, C25900, C25076, C25768, C25756, C25792, C1525, C14663, C52923, C1603 | basic | |
| R135 | 7.5 k 1 % 0603 | C23234 | 1.3M | basic |
| R130 | 39 k 1 % 0603 | C23153 | 458k | basic |

Approximate cost of the sheet: ≈ $21 incl. INA237 (~$1.9) and TPS26750 (~$3.2).

## Assumptions

- PD-in sources are USB PD compliant: VBUS starts at vSafe5V, and 28–48 V only after EPR entry. This matters
  because the TPD4S480 VBUS pin tolerates only 24 V until VPWR (TPS26750 LDO_3V3) is up.
- The TPS26750 configuration (TI web tool) sets: sink-only, PDOs 5 V + 9/15/20 V SPR + 28/36/48 V EPR,
  GPIO0 = EPR mode, GPIO1 = power path / contract active (push-pull), GPIO2 = fault input.
- Total VIN capacitance (this sheet + downstream) ≤ 100 µF (§6); other sheets must not add capacitance on VIN.
- +3V3 is generated from VIN (or from laptop 5 V in bus-powered mode) on the power_rails sheet.

## Open issues / risks

1. **TVS margin (accepted residual risk for the prototype).** No stocked TVS with VRWM ≥ 50.4 V stays under
   63 V (TPD4S480 VBUS abs max) at its full rated surge. The 5 kW parts now fitted clamp PD-in at ≈ 64 V (5 A) /
   68 V (18 A) and the barrel at ≈ 64 V (19 A), i.e. inside the 70 V LM74800 A/VS rating and the 80 V FETs up to
   ≈ 20 A, and marginally above the TPD4S480 63 V only for surges ≥ ~5 A. Realistic events on these ports are
   cable hot-plug ringing and ESD (sub-amp to few-amp, µs); IEC 61000-4-5 surge does not apply to a ≤ 3 m DC/USB
   cable input. Fallback if a prototype fails: a series 10–47 Ω on the TPD4S480 VBUS sense pin (check its
   supply current first). A reversed barrel together with 48 V PD-in still exceeds the LM74800 OUT/C rating
   (70 V + V(A)) — see item 7.
2. **AlwaysEnableSink at 5 V**: before a contract (or with a blank EEPROM) the sink path is closed at 5 V.
   5 V on VIN runs nothing (LM5148 UVLO 8 V, LM51770 8.06 V, `PD_OK` low), and the always-armed barrel still
   feeds VIN if present. A blank EEPROM therefore cannot boot the deck from PD-in (see §2 bring-up).
3. **EEPROM update path**: RP2350 → TPS26750 I2Ct → EEPROM requires the TPS26750 host commands for I2C
   pass-through/EEPROM programming — confirm in the TPS26750 Host Interface TRM. Fallback: I2Cc test pads
   TP101/TP102 (programming jig) or an optional link from RP2350 to the I2Cc bus (would need a new global net).
   WP is hard-tied to GND (writable); the odock-10 plan mentions a controlled WP — not implemented, needs a net.
4. **PP5V tied to GND** — confirm with TI (E2E) for a sink-only TPS26750.
5. **TPS26750 I2C address 0x21** on I2C_PD: check against the PMG1-S3 address chosen on pd_pmg1.
6. **PJ-063BH footprint** (easyeda import): pad spacing (hole → MS 2.0 mm, hole → pin 2 3.0 mm, pin 2 → pin 1
   6.0 mm) has to be checked against the datasheet's recommended layout (which seems to give 3.0 / 5.0 / 12.0
   mm from a different reference) before layout.
7. **Reverse barrel + PD 48 V at the same time**: with A = −24 V, the LM74800 OUT/C pins are rated only up to
   70 V + V(A) = 46 V while VIN = 48 V. Edge case; accepted for the prototype.
8. **BAR_OK OV window** (28.5 V) is ~1 V above the LM74800 OV (27.4 V); EXT_PWR_PRESENT may read high with an
   out-of-spec 27–28 V brick while the barrel path is already off.
9. PJ-063BH (240) and TPS26750 (165) stock is low at JLC — order early.
10. `tools/import_lcsc.sh` appends symbols with space indentation that `kicad-cli sym upgrade` does not
    rewrite unless `--force` is given, and `fix_pins.py` only matches tab-indented symbols. I ran
    `sym upgrade --force` once under the lock. Also `schgen.verify()` reports `#FLG` PWR_FLAG pins as missing,
    and multi-line `note()` text is lost (embedded newlines). The sheet works around both locally.

## Bring-up: first EEPROM programming

The TPS26750 EEPROM ships blank, and a blank TPS26750 never negotiates above 5 V, so the RP2350 cannot be
powered from PD-in alone. Program it with one of:
1. Barrel (≥ 9 V) or laptop bus power, then RP2350 → TPS26750 host interface (I2Ct, 0x21) → EEPROM.
2. A programming jig on the I2Cc test pads TP101/TP102 (TPS26750 held unpowered or in reset).
3. JLC/LCSC pre-programmed EEPROM (cleanest for production).
