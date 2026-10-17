# odock-10 — power stage & JLC assembly research (2026-10-02)

Tags: **[V]** checked against a datasheet, vendor page or JLC page (URL given) · **[S]** JLC parts API stock on 2026-10-02
(`q.py`, LCSC numbers) · **[I]** inference or engineering estimate, verify before committing.
Stock moves fast. Re-check before ordering.

---

## 0. Key findings

1. **The LTC4417 cannot take the PD-in rail.** It is specified for 2.5–36 V, with ±42 V protection [V: Newark/ADI
   listing "PowerPath Prioritizer 2.5 to 36 V", https://www.newark.com/analog-devices/ltc4417iuf-pbf/powerpath-prioritizer-qfn-ep-24/dp/51AK7246].
   A 48 V EPR source (50.4 V max) is out of range. **Use discrete ideal-diode controllers (LM74720/LM74800/LM74700),
   with priority set by hardware enable logic.**
2. **The LM5176 has thin margin at 48 V.** It operates up to 55 V, 60 V abs max [V: https://www.ti.com/product/LM5176].
   **LM51770** runs 3.5–78 V (85 V abs) and is "bidirectional" [V: https://www.ti.com/product/LM51770]. It is in stock
   (JLC 1007, Mouser 2131) and is the preferred buck-boost.
3. **Do not put bus power onto VSYS. Feed it straight onto the 5 V rail.** A laptop sources 5 V (Macs ≈ 15 W), and a
   5 V input cannot go through a buck to make 5 V. Keeping VSYS as an "external power only" rail (9–48 V) also
   makes the source and sink paths simple to interlock.
4. **Thermals are the biggest risk.** At full load, the losses on a bare 100×60 mm board come to about 12–14 W, which
   means a rise of roughly 60–80 K. See §5.
5. **JLC will hand-solder the LCD.** The HS20HS072RX part page says "Assembly Type: Wave Soldering, Standard Only",
   which means operator-soldered. Applying foam tape is **not** a listed service. See §6.

---

## 1. Input OR-ing and the laptop-port direction problem

### Comparison

| Option | V range | Fits? | JLC stock [S] | Notes |
|---|---|---|---|---|
| LTC4417 (3-input priority, back-to-back PFETs) | 2.5–36 V, ±42 V | **No** (48 V EPR) | C688510 IUF#TR 3248, C688503 2602 | Would only work if PD-in were capped at 28 V. PFETs at 8 A are lossy and large |
| LTC4418 (dual) | 2.5–40 V [I] | No | C688513 48 | Same voltage problem |
| **LM74720-Q1** (ideal diode, back-to-back NFET, OVP, EN) | 3–65 V, −65 V reverse [V: https://www.ti.com/product/LM74720-Q1] | **Yes, barrel** | C5219205 776 | Adjustable OV cut-off, 0.5 µs reverse block, 29 mA boost (fast FET drive). LM74721 C5219199 only 5 in stock |
| **LM74800-Q1 / LM74800M** (back-to-back NFET, EN, OV/UV) | 3–65 V [I, same family] | **Yes** | C3215600 4040, C7216630 6031 | Good second source for the LM74720 role and for the sink switch |
| LM74700-Q1 (single NFET ideal diode, EN) | 3.2–65 V [I] | Yes (OR-ing only) | C2653623 5563, C2941042 1448 | No load disconnect in the forward direction. Use it as the PD-path diode |
| LM5050-1 (OR-ing controller) | 5–75 V [I] | Partial | C473393 18017 | No EN/OVP, no reverse polarity. OK as a plain OR diode |
| TPS2121 (integrated mux) | 2.7–22 V, 4.5 A | **No for VSYS** | C485916 32291 | Too little current and voltage for the main path |
| LM5060 / LM5069 (hot-swap) | 5.5–65 / 9–80 V | Optional | C74456 1460 / C111822 10364 | Use only if inrush/eFuse control is wanted on VSYS |
| TPS2663x (60 V eFuse, integrated) | 4.5–60 V, 6 A [I] | Marginal | C1850278 956 | Too low for 8 A barrel |

### Recommended topology

```
 PD-in USB-C (EPR sink, ≤48 V/5 A)
   TPD4S480 + SMCJ58A ── Q1a/Q1b (TPS26750 sink gate drive) ── Q2 (LM74700 ideal diode) ──┐
                                                                                           │
 Barrel 5.5×2.5 (9–24 V, ≤8 A)                                                             ├── VSYS 9–50 V (external only)
   SMCJ33CA ── Q3a/Q3b back-to-back 80 V (LM74720: reverse −65 V, OVP ≈ 26–27 V, EN) ───────┘    │
                         ▲ EN_BARREL = barrel_ok AND NOT pd_ok (2 small FETs, no MCU)                │
                                                                                                   ├─► LM51770 4-sw buck-boost ─► VOUT_SRC
                                                                                                   │        (5/9/15/20/28 V)         │
                                                                                                   │                       Q5a/Q5b back-to-back 40–60 V
                                                                                                   │                     (laptop PD ctrl source gate)
                                                                                                   │                                  │
                                                                                                   └─► LM5148 buck ─► V5 ◄──┐         ▼
                                                                                                                             │   LAPTOP VBUS
                                                                       Q4a/Q4b back-to-back 60 V (LM74800, EN) ◄────────────┼─────────┘
                                                                       EN_SNK = PDctl_sink_en AND NOT EXT_PRESENT            │
                                                                                     └──────── bus-power path ──────────────┘
                                                                         V5 ─► 3V3 (TPS62933/TPS563201) ─► 1V2 (TPS62A02/TLV62569)
```

- **Priority, enforced in hardware [I].** `pd_ok` comes from a divider and comparator (or the TPS26750 power-good) on
  the PD-in rail after contract. It pulls the LM74720 EN low through an NFET, so the barrel turns off whenever PD-in is
  live. Both paths are ideal diodes, so make-before-break overlap is safe: the higher rail conducts for a moment and
  nothing back-feeds. The logic is powered from each input itself, so no MCU and no always-on rail are needed.
- **`EXT_PRESENT` = VSYS > ~8 V** (comparator or the LM5148 PGOOD).
  - **Sink path (Q4) is allowed only when EXT_PRESENT is low AND the laptop-port PD controller requests sink.**
  - **Source path (Q5) is allowed only when EXT_PRESENT is high AND the PD controller enables source AND the
    buck-boost PGOOD is high.** The source/sink loop (VSYS→buck-boost→VBUS→sink→V5) can then never close.
  - Both are back-to-back pairs, so either one blocks in both directions when off.
- **The bus-power path goes to V5, not to VSYS.** Q4 driven by an LM74800 is both the on/off switch and the reverse
  blocker. While the LM5148 runs (5.1 V), Q4 is held off by EN_SNK. Request **5 V-only sink PDOs** from the laptop, so
  V5 stays within USB-A/LCD limits.
  - Bus-power budget ≈ 15 W in. The deck draws about 4–5 W itself, so the downstream budget is about 8–9 W
    (USB-A limited to 500–900 mA total, downstream C at 5 V/1.5 A or less).
- **Role sequencing on the laptop port.** This belongs to the PD-controller policy, and it needs a dual-role-power
  (DRP) controller with dead-battery support and PR_Swap/FRS (Fast Role Swap) [I].
  - **Attach with no external power:** the deck presents Rd (sink, UFP). Dead-battery mode closes Q4 autonomously.
  - **Attach with external power:** the deck presents Rp. The buck-boost starts at its 5 V default and Q5 closes.
    The deck negotiates SPR/EPR, then does a DR_Swap so it becomes the UFP.
  - **External power arrives while sinking:** V5 is handed to the LM5148 and EN_SNK drops. The PD controller sends
    a **PR_Swap**: the laptop goes to vSafe0V, then the deck sources 5 V, then the contract is raised. If the laptop
    rejects the swap, stay a sink.
  - **External power is lost while sourcing:** VSYS collapses. With FRS (PD 3.x), the laptop takes over 5 V within
    about 150 µs. Size the V5 hold-up caps (several hundred µF) to bridge the gap. Without FRS, the deck resets and
    the USB link drops, re-attaching as a sink. Confirm that the chosen laptop-port PD controller supports FRS and
    that Macs accept PR_Swap from a dock [I].
- **Barrel protection.**
  - LM74720 OV cut-off at about 26.5 V, protecting against a 28–48 V adapter plugged into the barrel.
  - **Bidirectional TVS** with standoff above the OV threshold, so it does not burn if someone plugs in 36–48 V:
    SMCJ33CA, or uni-directional SMCJ33A on the drain side [I].
  - 80 V FETs. Reverse polarity is blocked by the back-to-back pair (−65 V).
- **PD-in protection.** TPD4S480 (already chosen) plus a TVS rated for 48 V EPR: SMCJ58A, C151899 3584 / C409417 2717 [S].

### Path FETs (all [S])

| Use | Part | LCSC | Stock | Key spec |
|---|---|---|---|---|
| Barrel / PD-in / VSYS (80 V) | Infineon BSC026N08NS5 | C5955453 | 5786 | 80 V, 2.6 mΩ, TDSON-8 |
| " | Toshiba TPH2R608NH | C5379811 | 30654 | 75 V, 2.1 mΩ, SOP-Adv 5×6 |
| " | TI CSD19502Q5B | C2864118 | 7579 | 80 V, 3.4 mΩ |
| " | Infineon BSC040N08NS5 | C534333 | 6678 | 80 V, 4 mΩ |
| Bus sink Q4 (≤3 A) | TI CSD18543Q3A | C840100 | 12215 | 60 V, 8.1 mΩ, 3.3×3.3 |
| Source switch Q5 (≤28 V, 5 A) | BSC026N08NS5 / TPH2R608NH | — | — | Low Rds is cheap here. 60 V+ for margin on 28 V |

Conduction loss: barrel at 8.3 A through 2 × 2.6 mΩ ≈ 0.36 W. PD path at 3.6 A (175 W at 48 V) through 3 FETs ≈ 0.1 W [I].

---

## 2. Buck-boost VSYS (9–50 V) → laptop VBUS (5–28 V, 5 A, 140 W)

| Part | VIN | VOUT | V-set method | JLC [S] | Notes |
|---|---|---|---|---|---|
| **LM51770** (HTSSOP-38) | 3.5–78 V, 85 V abs | 3.3–78 V | FB divider + "dynamic output voltage tracking for PWM or analog input" | C43351171 **1007** (Mouser 2131) | Up to 1.8 MHz, average I-limit with IMON, PSM, bidirectional. Drop-in successor to LM5177 [V: https://www.ti.com/product/LM51770] |
| LM5177 (HTSSOP-38) | 3.5–60 V, 85 V abs | 3.3–60 V | Same, analog/PWM tracking | C7425536 151 | ≤600 kHz [V: https://www.ti.com/product/LM5177] |
| LM51772 (VQFN-40) | 0(3.5)–55 V | 1–55 V | **I2C**, 10/20 mV steps; I-limit 0.5–7 A over I2C; "USB C/PD compatible" | C41383743 **1** (Mouser 33) | Ideal feature set, but no stock and 55 V limit [V: https://www.ti.com/product/LM51772] |
| LM5176 (HTSSOP-28) | 4.2–55 V, 60 V abs | 0.8–55 V | FB injection | C442493 **12168** | Cheapest and best stocked. Only 5–10 V margin over a 48 V EPR source [V: https://www.ti.com/product/LM5176] |
| LM5175 | 3.5–42 V [I] | — | FB | C113356 6491 | **Not usable** at 48 V in |
| **BQ25756** (VQFN-36) | 4.2–70 V, 85 V abs | ≤70 V | **I2C**. Reverse (OTG) mode regulates VAC 3.3–65 V, I-limit 0.4–20 A; EPR named | C19272232 **9088** | Bidirectional charger controller, 200–600 kHz [V: https://www.ti.com/product/BQ25756] |
| LT8390 (ADI) | 4–60 V | — | FB | C673802 1766 | ~$12, no advantage |
| TPS55288 | ≤36 V | — | I2C | C2864583 5157 | Integrated, too low VIN/current |

**Can the BQ25756 also do the sink path? Technically yes, but not worth it [I].**
- Wire VAC = laptop VBUS and VBAT = VSYS. Reverse mode then gives an I2C-set PD source, and forward mode could pull
  power from the laptop.
- But the laptop only offers about 5 V/3 A. Boosting that into VSYS and bucking it back to 5 V is wasteful. Forward
  mode is also a battery charger: with no battery, VSYS needs a charge-termination/CV workaround.
- Reverse mode is off at power-up and needs I2C writes to enable (plus watchdog handling). Laptop charging would then
  depend on firmware. Safety would not, because the PD controller's OVP still opens Q5.
- Keep the BQ25756 as a **stocked Plan B to the LM51770** (9k in stock) if I2C control is acceptable.

### Recommended: LM51770, 5 V default, voltage selected by the PD controller in hardware [I]

**Setting the voltage**
- The resistor divider defaults to 5 V (vSafe5V at power-up, with no firmware involved).
- 9/15/20/28 V are selected by **2–3 PD-controller GPIOs** ("voltage select" GPIO events). Each one switches an
  extra FB resistor through a small NFET (2N7002-class). This is the usual TI PD-controller + external-regulator
  scheme. It is MCU-independent and satisfies "power safety must not depend on MCU firmware".
- AVS / fine trim (optional): an RP2350 PWM → RC → resistor injection into FB, with **limited authority** (e.g. ±1 V,
  set by the resistor ratio).
  - Laptops at 140 W use the 28 V fixed PDO, so AVS is not needed for odock-10.
  - PD transition rules (slew ≤30 mV/µs, ±5%) are handled by soft-start/tracking caps.

**Safety layers [I]**
- The PD controller's VBUS OVP/UVP opens Q5.
- The LM51770 average current limit is set to about 5.5 A on output IMON.
- OVP comparator: a TL431-class part on VOUT_SRC pulls buck-boost EN low above roughly 30 V.

**Efficiency estimate at 140 W out, 250–400 kHz, 2 × 80 V FETs on the input side, 2 × 40–60 V on the output side,
4.7 µH [I]**

| Operating point | Mode | η | Loss |
|---|---|---|---|
| 48 V → 28 V × 5 A | Buck | ~97% | ~4.3 W |
| 20 V (PD) → 28 V | Boost | ~96% | ~5.8 W |
| 24 V barrel → 28 V | Buck-boost / boost | ~96% | ~5.8 W |
| 12 V barrel → 20 V × 2.25 A (45 W, PSU-limited) | Boost | ~95% | ~2.4 W |

Components:
- **Inductor:** Bourns SRP1265A-4R7M (C780205, 600 in stock; 13.5 A Irms / 28 A Isat / 8.4 mΩ) [S].
  Premium alternative: Coilcraft XAL1010-472 (C19271849, 157 in stock, 24 A, 5.2 mΩ, $13).
  Peak input current in boost from 20 V at 140 W is about 8 A.
- **Input-side FETs:** BSC070N10NS5 (C534364, 14639 in stock, 100 V / 7 mΩ, low Qg) or BSC040N08NS5.
- **Output-side FETs:** CSD18543Q3A or BSC040N08NS5.
- **Sense resistors:** 2–3 mΩ, 2512.
- **Caps:** 100 V X7R 1210 plus a 63 V polymer/electrolytic on the input; 50 V X7R plus polymer on the output.

---

## 3. Housekeeping rails

Load estimate:
- USB-A 3 × 0.9 A (1.5 A BC1.2 CDP on one port) ≈ 3.2 A
- Downstream C 5 V/3 A
- LCD backlight + RP2350 + 3V3/1V2 loads ≈ 1.5 A (at 5 V)
- **Total V5 ≈ 7–8 A (≈ 40 W) worst case.**

| Rail | Recommended | LCSC / stock [S] | Notes |
|---|---|---|---|
| **V5, 8 A from VSYS 9–50 V** | **TI LM5148** 80 V sync buck controller, VQFN-24, 2.2 MHz capable | C7470701 **57474**, $1.16 | 400 kHz, MWSA1004S-3R3 (C408483 501; 11 A / 16 A) + 2 × BSC070N10NS5. η ≈ 93% from 48 V → ≈ 3 W loss [I]. Alternatives: LM5146 (100 V, C3188679 3908), LM5145 (75 V, C485912 2210), dual LM5143-Q1 (65 V, C1849541 452) if V5 is split into ports and system |
| Always-on / aux (optional) | LMR38020 80 V 2 A | C5149193 11594 | Only if a standby rail independent of V5 is wanted |
| USB-A port switches | TPS2553 (adjustable I-limit) | C55266 58742 | Or SY6280AAC C55136 121k (cheap). Per-port FAULT → RP2350 |
| Downstream C 5 V/3 A switch | TPS25946 eFuse or TPS2557 (5 A adj.) | C3662780 1753 / C130056 1942 | Or the downstream PD controller's integrated 5 V switch, if it has one |
| 3V3, ~2–3 A, from V5 | TPS62933 (30 V, 3 A) or TPS563201 (17 V, 3 A) | C3200405 34272 / C116592 114631 | Feeds hub, RTL8156 (internal regulator), GL3224, RP2350, LCD |
| 1V2 / 1V1 (hub core, etc.) | TPS62A02 (2 A) or TLV62569 (2 A) | C5350187 31993 / C141836 242955 | Check per chip: USB72xx core rail, GL3224/RTL8156 internal regulators |
| RP2350 core | Internal SMPS | — | Per RP2350 datasheet |

In bus-powered mode V5 comes straight from Q4, so every rail derived from V5 works unchanged.

---

## 4. Barrel jack (5.5 × 2.5 mm, ≥8 A)

| Part | LCSC | Stock [S] | Rating (JLC/LCSC listing) | Notes |
|---|---|---|---|---|
| **Same Sky (CUI) PJ-063BH** | C3095900 | 240 | 2.5 mm pin, **8 A, 24 V**, THT | Recommended. Mouser 1580, TME 300, Arrow 1246 [findchips] |
| Same Sky PJ-063AH | C22434582 | 491 | 2.0 mm pin, 8 A | 2.0 mm pin, so the wrong size |
| XKB DC-042C-W-2.5 | C480371 | 1340 | 2.5 mm, 8 A, 24 V, right angle | Cheap stocked alternative. Check the datasheet for the pin current rating |
| XKB DC-005R-8A-2.5 | C7433305 | 322 | 8 A, 30 V, right angle | "8A" variant of DC-005 |
| HCTL HC-DC-007B-2.5-G1 | C19270564 | 305 | 2.5 mm, 8 A, 24 V | — |
| Switchcraft RAPC722X | C3095256 | 2 | 5 A | Not enough current |

Notes:
- **2.1 mm compatibility:** a 2.1 mm plug **cannot** go onto a 2.5 mm pin (its bore is too small). A 2.5 mm plug on a
  2.1 mm jack fits loosely and makes poor contact. So one jack cannot serve both; stay with 2.5 mm, which is common on
  high-power laptop bricks, and say so on the silkscreen [I].
- 8 A × 24 V = 192 W. At the 200 W target the jack runs at its limit, so derate the barrel to about 7.5 A in the MCU
  budget policy [I].
- A 24 V contact voltage rating is typical for these jacks. The LM74720 OVP keeps anything above about 27 V off the
  board.

---

## 5. Thermal budget (bare PCB) [I]

| Source | Worst-case loss |
|---|---|
| Buck-boost at 140 W | 4.5–6 W |
| Input path + source switch + sense resistors | 0.5–1 W |
| V5 buck at 40 W | ~3 W |
| 3V3/1V2 bucks | ~0.5 W |
| Hub + TUSB1046 + RTL8156 + GL3224 + RP2350/LCD | ~3.5–4 W |
| **Total** | **~12–14 W** |

**What this means for a 100 × 60 mm board**
- The board has about 120 cm² of surface across both faces. Natural convection plus radiation gives
  h ≈ 12–15 W/m²K, so θ ≈ 6 K/W for the board as a whole.
- **14 W → about 80 K rise; 10 W → about 60 K.** That is too hot for a desk object, with hot spots higher still.

**Mitigations**
- Spread the power stage over a large inner-plane copper area (2 oz outer layers if JLC offers it on 6/8 layers).
- A bottom aluminium plate on standoffs with a gap pad would roughly double the effective area.
- Grow the board: 120 × 80 mm gives θ ≈ 4 K/W.
- **Thermal derating policy:** an NTC near the buck-boost read by the RP2350, with the laptop contract renegotiated
  from 140 W down to 100/60 W when hot. As a hardware backstop, an NTC on the LM51770 EN/ILIM or a PD-controller
  thermal input.
- Sustained 140 W plus all ports at full load is rare. Design for about 8 W continuous with derating above that.

---

## 6. JLC assembly questions

**Prices** [V: https://jlcpcb.com/help/article/pcb-assembly-price, https://jlcpcb.com/help/article/pcb-assembly-faqs]

| Item | Price |
|---|---|
| Standard PCBA setup | $25.56 single-sided / $51.12 double-sided |
| Stencil | $8.21 / $16.42 |
| SMT | $0.0016/joint |
| **THT ("wave soldering" parts, actually soldered by hand)** | **$3.58 hand-soldering labour per order + $0.0164/joint**, +1 day |

- Estimate for barrel (3) + RJ45 (~14) + 3 × USB-A Gen2 (~13 each) + LCD tail (~12) + a hybrid USB-C ≈ 80–90 joints,
  which is **about $1.4/board plus $3.58/order [I]**.
- Ask for leads to be trimmed flush, to meet the "no sharp parts on the bottom" goal [I].

**LCD panel**
- The JLC part page for **HS20HS072RX (C5329582, 2208 in stock)** lists "**Assembly Type: Wave Soldering**" and
  "**PCBA Type: Standard Only**" [V: https://jlcpcb.com/partdetail/HS-HS20HS072RX/C5329582]. JLC therefore treats it
  as an operator-soldered part and will solder the FPC tail.
- **Double-sided foam tape:**
  - Not a listed service. The JLC parts category "Double-sided tape" is empty
    [V: https://jlcpcb.com/parts/2nd/Office_Supplies/Double-sided_tape_3230], and "foam tape" returns no stocked part [S].
  - The FAQ and capabilities pages list wire soldering, programming, stacked parts and flex fixtures, but no adhesive
    or mechanical assembly [V: https://jlcpcb.com/capabilities/pcb-assembly-capabilities].
  - → **Ask JLC support** whether they will apply customer-consigned die-cut foam tape (3M 4914-class, 1.1 mm) as a
    special request [I].
  - Plan B: the panel is soldered and the user applies the tape (ship a die-cut pad).
  - Plan C: a locating feature, such as two printed/PCB standoffs or a solder-tab bracket, so the hand-soldered panel
    is positioned without tape.
  - Give JLC an assembly drawing showing the FPC bend direction and the panel outline on silk.

---

## 7. Connectors in JLC stock

**2.5G RJ45 magjack with LEDs (THT)**

| Part | LCSC | Stock [S] | Notes |
|---|---|---|---|
| **USAKRO DGUK211Q340CD2A4D2 (2.5G)** | C19725134 | 111 | Datasheet: "TAB-UP 1X1 2.5G", LEDs, IL −1.0 dB max 1–125 MHz [V: LCSC datasheet] |
| USAKRO DGUK511Q340AB2A8D2 (2.5G) | C19725141 | 47 | 2.5G, LEDs, shielded |
| USAKRO DGUK111Q340AB2A1D2 (2.5G) | C19725125 | 8 | — |
| YDS 51F-1210GY2D2NL | C179768 | 745 | Name suggests 10G, unverified (datasheet fetch blocked) |
| HanRun HR911130A/C | C54408 10841 / C50933 3751 | — | **1G-rated only.** Avoid for 2.5GBASE-T |

The stock is thin, so pre-buy the 2.5G parts into the JLC parts library, or consign a Pulse/Bel 2.5G magjack from
Mouser.

**USB-A 10G (USB 3.1/3.2 Gen2) receptacles**

| Part | LCSC | Stock [S] | Notes |
|---|---|---|---|
| **Amphenol GSB4111312HR** | C5429382 | 3846 | GSB4 = Amphenol's "USB 3.1 Gen 2" Type-A family. GSB41113xxHR is right angle, 10 Gb/s [V: search of Amphenol GSB4X datasheet io_usb_3_1_gen2_gsb4x.pdf; PDF itself 403]. Pin current 1.8 A class [I] |
| Amphenol GSB412137CHR | C464567 | 4222 | GSB4 family, listed "USB 3.1" (orientation to check) |
| Amphenol GSB311131HR | C473057 | 15198 | **5 Gbps only** [V: LCSC datasheet "up to 5 Gbps"]. Avoid |
| Molex 48406-0003 | C565298 | 1162 | USB 3.0 (5G) |

**USB-C receptacles, 5 A / 48 V (EPR) + 10G**

| Part | LCSC | Stock [S] | Notes |
|---|---|---|---|
| **JAE DX07S024XJ1R1100** | C134113 | 1626 | 24P, **5 A, 48 V**, USB 3.x 10G, USB-IF certified, hybrid THT legs [V: https://www.heilind.com/jaedx07s024xj1r1100.html; JAE DX07 PIM https://www.tti.com/content/dam/ttiinc/manufacturers/jae/doc/jae-dx07-series-usb-type-c-connectors-datasheet-specifications.pdf]. **Laptop port + PD-in** |
| JAE DX07S024JA1R1300 | C2840478 | 5266 | 24P, 5 A, 48 V, mid-mount ("laminated board") per listing. Confirm 10G in the JAE PIM |
| JAE DX07S024WJ1R350 / WJ3R400 | C5246837 167 / C5159529 2235 | — | 24P, 5 A, 48 V (WJ3R400 is vertical) |
| **Amphenol 12401610E4#2A** | C5119948 | 7161 | 24P, **USB 3.2 Gen2 10G, 5 A, but 20 V** [V: https://www.newark.com/amphenol-icc-commercial-products/12401610e4-2a/usb-conn-3-1-type-c-rcpt-r-a-smt/dp/59AC8815]. Fine for the downstream C (5 V), **not** for 28/48 V ports |
| GCT USB4085/USB4105/USB4110/USB4135, Molex 2171750001 | — | — | USB 2.0 / 6-pin only. Not suitable |

**SD (full-size) and microSD, push-push**

| Part | LCSC | Stock [S] | Height | Notes |
|---|---|---|---|---|
| **Hanbo SD-111** | C410353 | 5209 | 2.9 mm | Full-size, push-push |
| Hirose DM1AA-SF-PEJ(82) | C506790 | 585 | 2.9 mm | Full-size, push-push, locating pins (premium) |
| SHOU HAN SD-CZ 11P H2.8 PUSH | C53223914 | 170 | 2.8 mm | Full-size, push-push |
| **Hirose DM3AT-SF-PEJM5** | C114218 | 18849 | 1.68 mm | microSD, push-push (listing field "No" seems wrong; DM3AT is push-push) [I] |
| SHOU HAN MICRO SD4.0 9P H1.4 PUSH | C53223918 | 993 | 1.4 mm | Lowest profile, push-push |
| Minlenda MLD-TF PUSH-H18 | C52750848 | 21276 | 1.8 mm | Cheap push-push |
| Amphenol 114-00841-68 | C3195424 | 2731 | 1.55 mm | microSD, listed push-pull |

No UHS-II full-size socket in JLC stock. That matches the "UHS-I minimum" goal.

---

## 8. Risks and open items

1. **Thermal** (§5). This is the biggest risk for "bare-PCB, 140 W" at 100 × 60 mm.
2. **Laptop-port PD controller features.** It must support DRP, dead-battery sink, PR_Swap and ideally FRS, and drive
   two back-to-back gate pairs (Q4/Q5) or accept external gate drivers. This depends on open question 1 in
   odock-10.md.
3. **Stock depth.** LM51770 (1007), LM74720 (776), 2.5G magjack (111), PJ-063BH (240). Pre-order into the JLC library.
   Fallbacks: BQ25756 (9088), LM74800 (10k), DC-042C-W-2.5 (1340).
4. **LM51770 DTRK/tracking pin details, and GPIO-switched FB transient behaviour (overshoot when stepping
   28 V → 5 V)** need datasheet review and simulation. Add an active VBUS discharge (bleeder FET) on VOUT_SRC for
   fast down-transitions [I].
5. **48 V creepage/rating everywhere on VSYS.** Use ≥100 V caps, or 80 V with derating, and 80 V FETs. The TVS
   clamp must stay below the FET V(BR).
6. **Foam tape** not confirmed (§6). Ask JLC support before layout freezes the area under the panel.
