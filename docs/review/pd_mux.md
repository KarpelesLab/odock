# Design review — USB-C / PD sheets (pd_pmg1, usbc_muxes)

Reviewer: independent pre-layout review, 2026-10-02. Scope: `hardware/odock-10/sheets/pd_pmg1.py`,
`hardware/odock-10/sheets/usbc_muxes.py`, plus the nets they share with `power_laptop.py`, `usb_hub.py`, `mcu.py`
and `tools/schgen/nets.py`. The pin→net maps in the `.py` files were treated as the schematic. Symbol pin numbers were
checked against `hardware/lib/odock.kicad_sym`.

Datasheets used (downloaded and read):
- Infineon PMG1-S3 002-31288 Rev. *K (2025-05-23), referred to below as **PMG1 DS**.
- TI TUSB1064 SLLSF48C, TUSB1046-DCI SLLSEW2E, TPD4S480 SLVSH00, TPD6S300 SLVSDK3C, TPD4E02B04 SLVSD85B.
- AO4842 (AOS).
- Infineon `mtb-example-pmg1s3-usbc-dock` design.modus, used for pin-function cross-checks.

## Result

**No BLOCKER and no MAJOR findings.** The things that are hardest to fix after layout all check out against the
datasheets:
- SuperSpeed direction and AC coupling, end to end.
- DP lane and AUX mapping for pin assignments C and D, in both plug orientations.
- Connector pinouts.
- PMG1 ball-out.
- Gate-driver topology.
- CC over-voltage protection and dead-battery hand-off.

What remains is a set of MINOR robustness issues plus several notes where the design docs or sheet comments say
something different from the datasheets. Each of those should be corrected so firmware is not written against a
wrong assumption.

## Findings (sorted by severity)

| # | Sev | Sheet | Refs / nets | Finding | Evidence | Fix |
|---|---|---|---|---|---|---|
| 1 | MINOR | usbc_muxes / pd_pmg1 | UP_HPD, U502 TUSB1064 HPDIN (pin 32) | **TUSB1064 HPDIN has no internal pull-down.** UP_HPD is driven only by PMG1 P1.3 through 1k and 10k. While the PMG1 is in reset, under SWD, unprogrammed or booting, P1.3 is Hi-Z and HPDIN floats. The sheet and docs say the pin has an "internal 500k pull-down", which is wrong for this part. CTL1 is held low by 100k, so the DP lanes stay off, which is why this is not MAJOR. A floating CMOS input can still draw shoot-through current, and any CTL1 glitch would enable the lanes. | TUSB1064 p.6, 2-State CMOS Input table: the 500 kΩ RPD is listed for "CTL1, CTL0, FLIP, and EN" only. Pin table p.4: HPDIN is "2 Level I" with no (PD). By contrast, TUSB1046-DCI p.6 R(ENPD) gives 150 kΩ on HPDIN pin 32. | Add 100k from UP_HPD (or UP_HPDIN) to GND. Fix the "internal 500k pull-downs in both muxes" text in usbc_muxes.py section 6 and in usbc_muxes.md. |
| 2 | MINOR | pd_pmg1 | U401 P5.5 (H4) = I2C_PD_INT_N, R 10k to +3V3 | **The interrupt output sits on a port with analog restrictions and is pulled up from an external rail.** Ports 2, 3 and 5 on the 97-BGA carry CTBm/SAR/LPCOMP. External voltage on them "must not exceed VDDIO" and may only be applied "after all supplies are up". VDDIO = VDDD = VSYS − 0.1 V ≈ 3.2 V, but the pull-up goes to +3V3 (3.3 V), so the pin sits about 0.1 V above VDDIO in normal operation, and +3V3 is the rail VDDD is derived from. This is within the 6 V / VDDIO + 0.5 V absolute maximum, but it violates the stated rule. | PMG1 DS p.18 §2.6.3 "GPIO power domain", rules 1 and 2. Table 4 p.32: VDDIO + 0.5 V limit. | Move I2C_PD_INT_N to a port-7 or port-1 GPIO, for example P7.6 (B9, spare; P7.x has no analog restriction). P5.5 is "EC interrupt" only by Infineon's convention; any GPIO works for our firmware. |
| 3 | MINOR | usbc_muxes | D501 SMBJ30A on VBUS_LAPTOP; U401 VBUS_C_P0 / CSP_P0 / CSN_P0 (34 V abs max) | **The VBUS TVS cannot keep the PMG1 34 V pins within absolute maximum during a surge or ringing event.** SMBJ30A has VBR 33.3–36.8 V and VC ≈ 48 V at IPP. The sheet note "VBR 33.3 V min, below PMG1 VBUS abs max 34 V at low current" is misleading: at VBR max the TVS is not even conducting at 34 V. Steady state is fine, because the power_laptop OVP latch trips at 30.8 V and the LM74800 at 32.6 V. Any TVS with VRWM ≥ 29.4 V has the same limitation. | PMG1 DS Table 3 p.31 (VBUS_ABS, VCSA_PIN_ABS = 34 V) and Table 4 p.33–34. JEDEC SMBJ30A ratings. | Pick one and record it as an accepted risk: (a) SMBJ28A (VRWM 28 V, VBR 31.1–34.4 V), which still has low leakage at 29.4 V and lowers the clamp; or (b) a flat-clamp TVS (e.g. TVS3300 class); or (c) keep SMBJ30A and accept the risk, since Infineon EPR references wire VBUS_C directly. Either way, correct the note. Keep the 10 µF + 100 nF close to J501 to tame hot-plug ringing. |
| 4 | NOTE | pd_pmg1 / usbc_muxes (comments) | MUX_UP_*, MUX_DS_* 100k pull-downs | Sheet comment pd_pmg1 §6 says the "100k pull-downs: PMG1 in reset/unpowered -> muxes default to USB3 off / DP off". That is false. Both chips enter **USB3 mode (no flip)** on VCC power-up regardless of CTL0, and leave it only on a CTL0 L→H→L transition. usbc_muxes.md states this correctly; pd_pmg1 does not. Firmware must pulse CTL0 after +3V3 comes up (P3V3_SNS) and on every detach. | TUSB1064 p.18 §8.4.1. TUSB1046-DCI p.17 §7.4.1. | Fix the pd_pmg1.py §6 note. Put the CTL0 pulse in the firmware contract in pd_pmg1.md. |
| 5 | NOTE | usbc_muxes.md (text only) | C509–C512 | The doc says laptop DP lanes on our TX pins "pass through both the laptop's cap and C509–C512 (110 nF)". Per the TI DFP_D reference, the source's RX-pin lanes carry **no** cap, so each lane sees exactly one cap: ours on our TX pins, the laptop's on our RX pins. The same holds downstream: TUSB1046 DP on our RX pins goes into the monitor's TX-pin caps. The circuit is correct; only the explanation is wrong. 220 nF is fine either way. | TUSB1046-DCI Fig. 8-2 p.32 (caps on TX1/TX2 only, RX DC). TUSB1064 pin table p.3 (TX = DP in / USB out). | Correct the text. |
| 6 | NOTE | pd_pmg1.md | VBUS_LSW, PMG1_VDDD | Doc "New / inter-sheet nets" and open issue 1 are stale. `VBUS_LSW` and `PMG1_VDDD` are already global in nets.py, CSA-0 is connected across sheets, and TPD4S480 VPWR is on PMG1_VDDD. | nets.py GLOBAL_NETS | Update the doc. |
| 7 | NOTE | pd_pmg1.md | Port 1, CYPM1321 Rd-DB | The doc claims a DRP phone on the downstream port of a dead deck may back-feed VBUS_DS through PMG1 Rd-DB. It cannot: TPD6S300 (VPWR = +3V3) has its CC FETs open when unpowered, and RPD_G1/2 = GND gives no Rd. One real transient exists: on an **externally powered cold start**, TPD6S300 closes its FETs ~ms after +3V3. If the PMG1 has not yet switched port 1 from Rd-DB to Rp, a charger plugged into the downstream port can briefly apply vSafe5V to VBUS_DS. The AO4842 pair blocks it, so the effect is harmless. | TPD6S300 Table "Device Mode", pin table p.3. PMG1 DS ordering table p.63 (CYPM1321 = RP, RD, RD-DB). | Fix the doc. Firmware: configure port 1 as Rp source as early as possible in boot. |
| 8 | NOTE | pd_pmg1 / usbc_muxes | U501 TPD4S480 + U401 port 0 dead battery | The hardware hand-off is correct: RPD_Gx tied to C_CCx, VPWR = PMG1_VDDD (so TPD and PMG1 power up together), and CYPM1321 keeps Rd-DB until firmware changes it. TI requires that the PD controller **must not start DRP toggling** before the TPD FETs are on (tON_FET ≤ 3.5 ms; DB resistors off ≤ 9.5 ms) and that its Rd be present the moment they close. PdStack dead-battery start (powered from VBUS, no VSYS) must come up as a sink with Rd, not DRP/Try.SRC. The CYPM1322 fallback, which has no Rd-DB, would leave a gap after 5.7–9.5 ms unless firmware asserts Rd first, so treat it as risky. | TPD4S480 §6.3.3 p.12–13, timing p.8. PMG1 DS ordering p.63. | Add to the firmware contract: dead-battery boot stays a sink, no DRP toggle until the contract. Keep CYPM1321 as the only approved part, or bench-test the 1322 fallback. |
| 9 | NOTE | pd_pmg1 | Port 0 data role | Port 0 sources power (Rp) whenever external power is present, so the Type-C default data role at attach is **DFP**, but the deck hardware is a UFP (hub upstream). Firmware must DR_Swap to UFP before the laptop's DP Discover/Enter. A non-PD Type-C host would end up UFP↔"DFP-deck" with no USB data. Hardware cannot fix this. | USB Type-C/PD role rules (Rp = DFP at attach). | Firmware: DR_Swap after the explicit contract. Document that non-PD hosts get power but no data while the deck is externally powered. |
| 10 | NOTE | pd_pmg1 | USBDP/USBDM NC | A UFP that offers alt modes must expose a Billboard if alt-mode entry fails. The PMG1 FS-USB is unused. The RP2350 sits on hub port 6 and can implement the Billboard class behind the hub, which is allowed for compound devices. | USB Type-C spec / Billboard class. pd-controllers.md line 61. | Assign Billboard to the RP2350 firmware. No hardware change. |
| 11 | NOTE | pd_pmg1 | Q402 AO4842, R415, VBUS_DS | Downstream VBUS drop: +5V ≈ 5.10 V − 15 mV (shunt) − 2 × 3 A × RDS(on). GD_VGS can be as low as 4.5 V; AO4842 is 30 mΩ max at 4.5 V and more when hot, which costs 0.18–0.24 V. That leaves ≈ 4.85 V before connector and copper loss, against vSafe5V min 4.75 V. In bus-powered mode +5V is the laptop's 5 V minus the sink-path drops, so the 3 A Rp cannot be honoured. The 0.38 W loss figure assumes 10 V gate drive. | PMG1 DS Table 46 p.59 (GD_VGS 4.5–10.5 V). AO4842 DS (RDS(on) < 30 mΩ at VGS = 4.5 V). | Firmware: advertise 3 A only with external power, default/1.5 A when bus-powered. Optional: a lower-RDS(on) dual NFET in SO-8. |
| 12 | NOTE | pd_pmg1 | U401 VBUS_IN/OUT_NGDO_P0, VBUS_IN/OUT_CTRL_P0 (NC) | Gate-driver pair 0 is left unconnected. CTRL pins are outputs, so NC is fine. The NGDO pins are HV inputs; floating them is not prohibited in the DS. | PMG1 DS Table 2 p.24, Fig. 13 p.30 | Optional: tie VBUS_IN/OUT_NGDO_P0 to VBUS_LAPTOP so they are not floating HV inputs. Confirm with Infineon (pd_pmg1.md open issue 2). |
| 13 | NOTE | usbc_muxes | UP/DS_CCPROT_FLT_N | TPD fault flags are not routed. A CC/SBU OVP or thermal event looks like a silent detach to the PMG1. Spare PMG1 GPIOs exist on port 7 and port 1. | TPD4S480 Table 6-3 p.14 | Optional: wire both flags to spare PMG1 GPIOs (P7.6 if #2 does not take it; P1.0, P1.5, P1.6). |
| 14 | NOTE | usbc_muxes | J501 DX07 B-row | The B-row (TX2/RX2) pins are through-hole on the DX07 footprint, which puts a via-length stub on 10 Gbps / HBR3 lanes. This is known (doc open issue 4); listed for completeness. | footprint `USB-C-TH_DX07S024XJ1R1100-1` (B1–B12 thru_hole) | Route B-row SS from the far side, or confirm the stub is short, in layout. |
| 15 | NOTE | pd_pmg1 / usbc_muxes | TPD4S480 VBUS pin | TPD4S480 VBUS is rated 24 V abs max while VPWR = 0 (63 V when VPWR > 2.7 V). This is safe as designed: PMG1_VDDD is alive whenever VBUS_LAPTOP > ~4 V (PMG1 VBUS regulator), and the deck only sources more than 20 V while the PMG1 runs. Do not move VPWR to +3V3. | TPD4S480 Abs Max p.5 | None. Keep VPWR = PMG1_VDDD. |

## Verified OK (no action)

- **Connector pinouts.** These match USB Type-C R2.x. J501 / J502 symbols:
  - A2/A3 = TX1±, B11/B10 = RX1±, B2/B3 = TX2±, A11/A10 = RX2±.
  - A5/B5 = CC1/CC2, A8/B8 = SBU1/SBU2.
  - A6/B6 = D+ and A7/B7 = D−, tied across rows.
  - All four VBUS and all four GND pins are mapped by name.
  - Shell: DX07 pad "0" (×4) and Amphenol 14/15 (×4) go to GND.
- **SS direction and AC coupling, laptop path.** Laptop TX → J501 RX → TUSB1064 RX1/RX2 is DC (TX caps are on the
  laptop side). TUSB1064 TX1/TX2 → 220 nF → J501 TX. Hub USB3UP_TXDP/DM (91/92) → 220 nF (usb_hub) → TUSB1064 SSTX
  (input). TUSB1064 SSRX (output) → 220 nF → hub USB3UP_RXDP/DM (94/95). Sources: TUSB1064 p.3–4, USB7206C pin table.
- **SS direction and AC coupling, downstream path.** Hub USB3DN_TXDP5 (83/84) → 220 nF → TUSB1046 SSTX. TUSB1046
  SSRX → 220 nF → hub 86/87. TUSB1046 TX1/TX2 → 220 nF → J502 TX. J502 RX is DC to TUSB1046 RX1/RX2, matching
  TUSB1046 Fig. 8-2. The order on every lane is connector → ESD → cap → mux.
- **DP lanes.** Checked against TUSB1064 Table 4 p.19 and TUSB1046 Table 7-4 p.18, with standard cable wiring
  (TX1↔RX1, TX2↔RX2, SBU1↔SBU2):
  - Laptop DFP_D, unflipped: DP0 on its RX2 reaches our TX2, and TUSB1064 routes TX2→DP0. Likewise DP1 via RX2→DP1,
    DP2 via RX1→DP2, DP3 via TX1→DP3.
  - Flipped: the complementary mapping applies.
  - Pin assignment D uses DP0/DP1 only, with USB on the other pair.
  - TUSB1064 DPn → 220 nF → TUSB1046 DPn is straight through. The TUSB1046 output mapping (DP0→RX2, DP1→TX2, DP2→TX1,
    DP3→RX1 unflipped) is the VESA DFP_D mapping.
- **AUX/SBU.**
  - Polarity: the laptop drives AUXp on its SBU1, which arrives at our SBU2, and TUSB1064 routes SBU2→AUXp when not
    flipped (Table 3 p.18). TUSB1046 drives AUXp→SBU1 when not flipped (Table 7-3).
  - Coupling: one 100 nF per AUX line between the chips; SBU is DC to the receptacle through the TPD FETs.
  - Bias: TUSB1064 side AUXp 1M to 3V3 and AUXn 1M to GND; TUSB1046 side AUXp 100k to GND and AUXn 100k to 3V3; 2M on
    each SBU. All per the TUSB1064 p.4 and TUSB1046 p.4 pin tables.
  - SBU DC level stays below the TPD4S480 SBU OVP (4.0 V min).
- **Mux control.** CTL1 = DP, CTL0 = USB3, FLIP = CC2 orientation. HL = 4-lane (C), HH = USB3 + 2-lane (D), for both
  chips (TUSB1064 Table 2, TUSB1046 Table 7-2). The PMG1 GPIOs (P3.0/3.1/3.2, P3.3/3.4/3.7) are plain GPIOs. The
  TUSB1046 HPDIN is pin 32 (HPDIN/RSVD2) in GPIO mode, and CTL1/HPDIN pin 23 is CTL1. With CAD_SNK = H, AUX snoop is
  off.
- **HPD.**
  - P7.1 is the port-1 HPD block, P1.4 the port-0 HPD block, P1.3 a GPIO (PMG1 DS Table 2 p.21–22). Port 1
    (DFP_D) drives HPD, port 0 (UFP_D) receives it. This is the correct direction for a pass-through dock.
  - Levels: VDDIO ≈ 3.2 V, TUSB VIH = 2.0 V. The voltage drop across 11k at ±25 µA leakage is negligible.
  - TUSB1046 HPDIN has a 150k internal pull-down.
- **PMG1 ball-out.** All 97 symbol balls match PMG1 DS Table 2, including the corrected C15 = CSP_P1 and
  M6 = AUX_N_P1. VDDA is tied to VDDD as the DS requires (Table 4 p.34).
- **PMG1 supplies.**
  - VSYS = +3V3 is within VSYS_DFP_DRP 3.0–5.5 V.
  - VBUS-powered VDDD is 3.0–3.65 V (60 mA regulator), which is within TPD4S480 VPWR 2.7–4.5 V.
  - Decoupling: VCCD 100 nF (80–120 nF), VDDD 4.7 µF, and 1 µF on VSYS/VDDIO/VDDA/VCONN, per Table 5.
  - P0.0 is VDDD-domain.
  - P4.0/P4.1 are the fail-safe I2C pins.
  - The XRES pass FET's body diode is reverse-biased in a dead deck.
- **PMG1 HV pins.**
  - VBUS_C_P0/P1, CSP/CSN and NGDO are rated 34 V abs max with a 30 V operating maximum. EPR 28 V + 5 % = 29.4 V fits.
  - VBUS_OUT_CTRL is rated 42 V.
  - No VBUS dividers are needed.
  - The CSA shunt is 5 mΩ ±1 % on both ports, matching the 4.95–5.05 mΩ spec (p.55).
  - CSP is on the supply side and CSN on the connector side on both ports.
- **Port-1 switch.** The topology is identical to PMG1 DS Fig. 11 p.29: shunt → VBUS_IN_NGDO at the inner source,
  common-drain dual NFET, VBUS_IN_CTRL on the supply-side gate, VBUS_OUT_CTRL on the connector-side gate,
  VBUS_OUT_NGDO and VBUS_C at the connector. Both body diodes point into the common drain, so the switch blocks in both
  directions. AO4842 VGS ±20 V covers the 5 V port.
- **CC protection.**
  - TPD4S480 handles 63 V on C_CC/C_SBU with OVP at 5.6–6.2 V. VCONN 600 mA can pass, and the PMG1 CC pins are rated
    6 V.
  - EPR_EN = VPWR is within its 0–VPWR range.
  - VBIAS uses 100 nF / 100 V (≥ 63 V required).
  - FLT has 100k to a 2.7–5.5 V rail.
  - TPD6S300: N.C. pins 16/17 go to GND per its pin table, RPD_G = GND (no Rd on a source-only port), and the VBIAS cap
    is rated 50 V against 24 V abs max.
  - cReceiver: 390 pF C0G + TPD CON_CC 40–120 pF stays within 200–600 pF.
- **ESD.** TPD4E02B04 is 0.25 pF typ / 0.33 pF max, specified for 10 Gbps, ±12 kV contact, VRWM ±3.6 V. The
  flow-through NC pad pairs (1↔10, 2↔9, 4↔7, 5↔6) are on the same nets.
- **I2C.** 0x42 is set in PMG1 firmware. The only other device on I2C_PD is TPS26750 (0x21), so there is no clash. Bus
  pull-ups are 2.2k to +3V3 on mcu.

## Suggested doc corrections (summary)

- pd_pmg1.py §6 note: muxes default to **USB3 on** at power-up, not off (#4).
- usbc_muxes.py §6 and usbc_muxes.md: TUSB1064 HPDIN has **no** internal pull-down (#1).
- usbc_muxes.md AC-coupling paragraph: one cap per DP lane, not two (#5).
- usbc_muxes.py §1 TVS note: SMBJ30A VBR max 36.8 V and VC ≈ 48 V are above 34 V (#3).
- pd_pmg1.md: VBUS_LSW / PMG1_VDDD are already global; the port-1 back-feed statement is wrong (#6, #7).

## Resolution (2026-10-02)

The fixes are in `pd_pmg1.py` and `usbc_muxes.py`, and the docs in `docs/design/pd_pmg1.md` and `usbc_muxes.md`. The
rebuild passes with `netlist verify: OK`, and `tools/bom_check.py` reports 0 failing.

| # | Resolution |
|---|---|
| 1 | Added **R544 100k UP_HPD → GND** on usbc_muxes; it was placed last, so other refs are unchanged. Corrected the "internal 500k pull-downs in both muxes" text in usbc_muxes.py §2/§6 and usbc_muxes.md: TUSB1064 HPDIN has none, and TUSB1046 HPDIN has 150k internal. |
| 2 | Moved **I2C_PD_INT_N from P5.5 (H4) to P7.6 (B9)**. P5.5 is now NC. The 10k pull-up now goes to **PMG1_VDDD** (= VDDIO) instead of +3V3, so the pin never exceeds VDDIO. In a dead deck, ≤ 0.33 mA flows into the unpowered RP2350 pad (fault-tolerant GPIO6) until +3V3 comes up, which is harmless. Firmware keeps INT_N released until P3V3_SNS is high. No net-name change was needed. |
| 3 | D501 is now **SMCJ28A** (Littelfuse C224047, 1500 W SMC; VRWM 28 V, VBR 31.1–34.4 V, VC 45.4 V at 33 A), replacing SMBJ30A. This lowers VBR and gives lower dynamic resistance than SMBJ28A. The sheet note and doc now state the **residual risk** plainly: no TVS with VRWM ≥ 28 V keeps VBUS_C_P0 / CSP_P0 / CSN_P0 below 34 V during a surge (TVS3300 is no better). This is accepted, as in Infineon's EPR references. Steady state is covered by the OVP latch (30.8 V) and the LM74800 (32.6 V). Bench item: leakage at 28–29.4 V, hot. |
| 4 | Fixed the pd_pmg1.py §6 note: the muxes power up in USB3 mode, and the pull-downs only hold CTL low. Added the CTL0 L→H→L pulse (after P3V3_SNS and on every detach) to the pd_pmg1.md firmware contract. |
| 5 | Corrected usbc_muxes.md: each DP lane sees exactly one cap (C509–C512 on our TX pins, the laptop's own caps on our RX pins; downstream likewise). |
| 6 | pd_pmg1.md: "New / inter-sheet nets" now states that VBUS_LSW and PMG1_VDDD are global. Open issue 1 is marked resolved (TPD4S480 / TPD6S300), and the OCP bullet is updated. |
| 7 | Replaced the wrong port-1 back-feed claim. TPD6S300 FETs are open when unpowered, so there is no back-feed in a dead deck. Documented the harmless externally-powered cold-start transient and the "port 1 to Rp early" firmware rule. Open issue 6 is updated. |
| 8 | Firmware contract added: a dead-battery boot stays a sink with Rd, with no DRP or Try.SRC before the contract. CYPM1321 is the only approved part, and CYPM1322 must be bench-tested first. |
| 9 | Firmware contract added: DR_Swap to UFP after the explicit contract. Documented that non-PD hosts get no data while the deck is externally powered. |
| 10 | Billboard is assigned to RP2350 firmware on hub port 6 (pd_pmg1.md open issue 9). |
| 11 | pd_pmg1.md: Rp 3 A is advertised only with external power, Default/1.5 A when bus-powered. The 0.38 W loss figure assumes 10 V gate drive. |
| 12–15 | No change: they are optional or informational. NGDO_P0 stays NC (open issue 2). The FLT# flags stay unrouted, since P7.6 is now used for INT_N but P1.0/P1.5/P1.6 remain spare. The DX07 B-row stub is a layout item. VPWR stays on PMG1_VDDD. |
