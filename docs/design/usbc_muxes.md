# odock-10 — usbc_muxes sheet

Source: `hardware/odock-10/sheets/usbc_muxes.py` (generates `usbc_muxes.kicad_sch`, ref_base 500, A1).
Status: first schematic pass, 2026-10-02. `build_all.py usbc_muxes` gives `netlist verify: OK`.
`tools/bom_check.py`: every part on this sheet is a JLC part with stock ≥ 5 (none consigned).
Datasheets used: TI SLLSF48C (TUSB1064), SLLSEW2E (TUSB1046-DCI), SLVSH00 (TPD4S480), SLVSDK3C (TPD6S300),
SLVSD85B (TPD4E02B04), Infineon PMG1-S3 datasheet (CC/SBU abs max 6 V, VCONN FETs).

## Topology

```
 Laptop USB-C J501 (DX07, 48 V/5 A)                                          Downstream USB-C J502 (12401610E4#2A)
  VBUS ── SMCJ28A + 100n ── VBUS_LAPTOP                                       VBUS ── SMAJ6.0A + 100n ── VBUS_DS
  CC1/2 ── TPD4S480 U501 (63 V OVP, dead-batt Rd) ── LAPTOP_CC1/2             CC1/2 ── TPD6S300 U504 (24 V OVP) ── DS_CC1/2
  SBU1/2 ─ TPD4S480 ── UP_SBU1/2 ── TUSB1064 SBU                              SBU1/2 ─ TPD6S300 ── DS_SBU1/2 ── TUSB1046 SBU
  D+/D- (A6/B6, A7/B7) ──────────── LAPTOP_USB_DP/DN (hub upstream USB2)      D+/D- ── (TPD6S300 ESD) ── HUB_DSC_DP/DN
  TX1/TX2 ◄─220n── TUSB1064 TX1/TX2         TUSB1046 TX1/TX2 ──220n──► TX1/TX2
  RX1/RX2 ──────► TUSB1064 RX1/RX2          TUSB1046 RX1/RX2 ─────────► RX1/RX2
  (TPD4E02B04 ESD D502/D503/D504 at the connector)                            (TPD4E02B04 D506/D507)

 TUSB1064 U502 (UFP_D)                                       TUSB1046-DCI U503 (DFP_D)
   SSTX ◄──────────── HUB_UP_SS_TX (220n on usb_hub)          SSTX ◄──────────── HUB_DSC_SS_TX (220n on usb_hub)
   SSRX ──220n──────► HUB_UP_SS_RX                            SSRX ──220n──────► HUB_DSC_SS_RX
   DP0..3 ──220n (C515-C522)──────────────────────────────►  DP0..3
   AUXp/n ──100n (C523/C524)──────────────────────────────►  AUXp/n
   (1M up / 1M down: UFP_D bias)                             (100k down / 100k up: DFP_D bias)
   CTL0/CTL1/FLIP ◄── MUX_UP_*   (PMG1 port 0)                CTL0/CTL1/FLIP ◄── MUX_DS_*   (PMG1 port 1)
   HPDIN ◄─10k── UP_HPD (100k PD) (PMG1 output)              HPDIN ◄─10k── DS_HPD          (PMG1 output)
```

### Interface nets

| Net | Dir (this sheet) | Other sheet | Notes |
|---|---|---|---|
| VBUS_LAPTOP | bidir | power_laptop, pd_pmg1 | Laptop VBUS, 5–28 V. TVS + 100 nF here, bulk on power_laptop |
| VBUS_DS | in | pd_pmg1 / power | 5 V source. TVS + 100 nF here; switch and bulk cap elsewhere |
| LAPTOP_CC1/2, DS_CC1/2 | bidir | pd_pmg1 | System side of the CC OVP FETs (PMG1 CC pins) |
| LAPTOP_USB_DP/DN | bidir | usb_hub | Hub upstream USB2. Both connector rows are tied at the receptacle |
| HUB_DSC_DP/DN | bidir | usb_hub | Downstream-C USB2, straight to the receptacle |
| HUB_UP_SS_TXP/N, HUB_DSC_SS_TXP/N | in | usb_hub | Hub transmits. **DC on this sheet**: the 220 nF caps are on usb_hub |
| HUB_UP_SS_RXP/N, HUB_DSC_SS_RXP/N | out | usb_hub | Hub receives. **220 nF caps on this sheet** (C513/C514, C530/C531) |
| MUX_UP_CTL0/CTL1/FLIP | in | pd_pmg1 | PMG1 port 0 GPIOs → TUSB1064 (fail-safe inputs, 500 k internal pull-down) |
| MUX_DS_CTL0/CTL1/FLIP | in | pd_pmg1 | PMG1 port 1 GPIOs → TUSB1046 (fail-safe inputs, 500 k internal pull-down) |
| UP_HPD | in | pd_pmg1 | PMG1 output → TUSB1064 HPDIN (10 k series, R544 100 k to GND here) |
| DS_HPD | in | pd_pmg1 | PMG1 output → TUSB1046 HPDIN (pin 32, 10 k series) |
| PMG1_VDDD | in | pd_pmg1 | PMG1 always-on supply. Powers TPD4S480 VPWR (≈0.16 mA, 1 µF local cap) |
| +3V3, GND | in | power_rails | Muxes ≈0.6 W max together, TPD6S300 VPWR |
| UP_CCPROT_FLT_N, DS_CCPROT_FLT_N | local | (optional) | Open-drain fault flags with pull-ups. Promote to global if pd_pmg1 has a spare GPIO |

DP_ML0/1_P/N and DP_AUX_P/N use the existing global names, but only this sheet uses them. DP_ML2/3 and the
TUSB1046-side DS_DP_ML*/DS_AUX_* nets are local.

## Mux control (GPIO mode, I2C_EN = 0 on both)

Both chips decode CTL1/CTL0/FLIP the same way (TUSB1064 Table 2, TUSB1046 Table 7-2):

| CTL1 | CTL0 | FLIP | Mode | TUSB1064 (UFP_D) | TUSB1046 (DFP_D) |
|---|---|---|---|---|---|
| L | L | x | Power down (≈0.7 mW) | — | — |
| L | H | L/H | USB 10G only, normal/flipped | — | — |
| H | L | L/H | 4-lane DP, no USB3 | pin assignment C | C and E |
| H | H | L/H | USB 10G + 2-lane DP | pin assignment D | D and F |

- PMG1 drives CTL1 = "DP configured", CTL0 = "USB3 enabled", FLIP = "CC2 orientation". Each port drives its own mux.
- **After VCC power-up both chips default to USB3 mode (no flip).** With no partner attached, firmware must pulse
  CTL0 L→H→L to reach power-down (datasheet §8.4.1). If the PMG1 GPIOs stay low or in reset, the muxes stay in
  USB3/no-flip. So a non-flipped laptop gets 10G even before PMG1 firmware runs.
- CTL/FLIP are debounced for 16 ms (tCTL_DB). The firmware should set FLIP together with or before CTL.
- AUX↔SBU mapping follows CTL1/FLIP. AUX opens after CTL1 has been low for more than 2 ms.

### Signal routing per mode (receptacle pin ← chip pin)

Laptop port, TUSB1064 (from Table 4). Orientation "flip" = CC2 attached.

| Mode | TX1 A2/A3 | RX1 B11/B10 | TX2 B2/B3 | RX2 A11/A10 | SBU1 / SBU2 |
|---|---|---|---|---|---|
| USB only, no flip | USB out (from hub SSTX) | USB in (→ SSRX → hub) | — | — | open |
| USB only, flip | — | — | USB out | USB in | open |
| USB + 2-lane DP (D), no flip | USB out | USB in | DP ML0 in → DP0 | DP ML1 in → DP1 | AUXn / AUXp |
| USB + 2-lane DP (D), flip | DP ML0 → DP0 | DP ML1 → DP1 | USB out | USB in | AUXp / AUXn |
| 4-lane DP (C), no flip | ML3 → DP3 | ML2 → DP2 | ML0 → DP0 | ML1 → DP1 | AUXn / AUXp |
| 4-lane DP (C), flip | ML0 → DP0 | ML1 → DP1 | ML3 → DP3 | ML2 → DP2 | AUXp / AUXn |

Downstream port, TUSB1046 (Table 7-4): DP0→RX2, DP1→TX2 (and DP2→TX1, DP3→RX1 in 4-lane) when not flipped.
Flipped: DP0→RX1, DP1→TX1 (DP2→TX2, DP3→RX2). AUXp→SBU1, AUXn→SBU2 when not flipped, swapped when flipped. USB uses
the other pair. Lane numbers match between the chips (TUSB1064 DPn → TUSB1046 DPn), so the DP link needs no swaps.

### Operating scenarios
1. **USB only** (laptop attached, no monitor): laptop CTL = LH (+FLIP). Downstream port is USB-only (LH) or power-down.
2. **USB + 2-lane DP (normal case)**: PMG1 port 0 advertises UFP_D pin assignment D, so the laptop enters D and the hub
   keeps 10G. Port 1 picks D if the monitor offers it, else C. With C, TUSB1046 runs HL: downstream USB3 is lost but USB2
   still works, and only DP0/1 carry data because the laptop trains 2 lanes.
3. **4-lane DP (optional)**: if firmware advertises C on port 0 (e.g. a user "4-lane/HBR3 4K120" setting), TUSB1064 =
   HL and the hub upstream falls back to USB2 only. All four DP lanes are wired and AC-coupled for this case.

### HPD
- **DS_HPD** = monitor HPD as decoded by PMG1 port 1 (DFP_D) from DP Status Update / Attention VDMs, including IRQ_HPD
  pulses. PMG1 output → R522 10 k → TUSB1046 HPDIN (pin 32 in GPIO mode).
- **UP_HPD** = HPD state that PMG1 port 0 (UFP_D) reports to the laptop. PMG1 output → R505 10 k → TUSB1064 HPDIN.
- Both mux HPDIN pins: low for more than 2 ms disables the DP lanes and AUX stays connected. IRQ_HPD (0.5–1 ms) does not
  disable them. In GPIO mode TUSB1064 has no AUX snoop, so all lanes of the selected configuration run while HPDIN is high.
- The 10 k series resistors protect against pins that are not fail-safe (TUSB1046 note 2: pins 29/32 leak into VCC if
  driven while +3V3 is off; the PMG1 runs from VBUS in a dead deck).
- **Pull-downs.** TUSB1064 HPDIN has **no** internal pull-down: the 500 k RPD in its datasheet (p.6) applies to
  CTL0/CTL1/FLIP/EN only, and the pin table lists HPDIN as a plain 2-level input. R544 (100 k, UP_HPD → GND) keeps it
  defined while PMG1 P1.3 is Hi-Z (reset, SWD, unprogrammed, booting). TUSB1046-DCI HPDIN has a 150 k internal
  pull-down (R(ENPD)), so DS_HPD needs none. Both lanes groups are therefore off while the PMG1 is in reset.

## AC coupling (rule: one 75–265 nF cap per SS segment, at its transmitter)

| Segment | Cap | Where |
|---|---|---|
| TUSB1064 TX1/TX2 → laptop receptacle TX pins | C509–C512 220 nF | here |
| Laptop TX → receptacle RX → TUSB1064 RX | laptop side | DC here |
| Hub TX → TUSB1064/TUSB1046 SSTX | 220 nF | usb_hub |
| TUSB1064/TUSB1046 SSRX → hub RX | C513/C514, C530/C531 220 nF | here |
| TUSB1064 DP0–3 → TUSB1046 DP0–3 | C515–C522 220 nF | here (one cap per line, not one per chip) |
| TUSB1046 TX1/TX2 → downstream receptacle TX | C532–C535 220 nF | here |
| Downstream RX → TUSB1046 RX | device side | DC here |
| AUX TUSB1064 ↔ TUSB1046 | C523/C524 100 nF | here |

220 nF (0402 X7R, JLC basic C16772) is used everywhere. Each lane sees exactly **one** cap: per the TI DFP_D
reference (TUSB1046-DCI Fig. 8-2), a DP source puts its caps on its TX-pin lanes only and leaves its RX-pin lanes DC.
So the laptop's DP lanes that arrive on our TX pins (its RX pins) see only C509–C512, and the lanes that arrive on our
RX pins see only the laptop's own caps. Downstream works the same way: TUSB1046 DP on our RX pins goes into the
monitor's TX-pin caps.

**AUX bias.** TUSB1064 side: AUXp 1 M → +3V3, AUXn 1 M → GND, the UFP_D (sink) bias the laptop expects. TUSB1046
side: AUXp 100 k → GND, AUXn 100 k → +3V3, the DFP_D (source) bias the monitor expects. A single 100 nF per line between
them keeps the two DC biases independent. Each SBU pin has 2 M to GND on the mux side (R502/R503, R542/R543).

## Equalization straps

Every 4-level pin has two footprints: a GND-side resistor (1 k = "0", 20 k = "R") and a VCC-side 1 k ("1"). Both
unfitted = "F". The chips latch the levels at power-up/EN, so EQ can be retuned on the bench by moving 0402s.
TUSB1064 EN uses 10 k/100 nF to +3V3 (≈1 ms after VCC).

| Chip | Path | Pins | Setting | Gain |
|---|---|---|---|---|
| TUSB1064 | Laptop cable → RX1/RX2 (USB) | EQ1/EQ0 = R/F | #6 | 6.6 dB @ 5 GHz |
| TUSB1064 | Hub TX → SSTX (~40 mm + hub de-emphasis) | SSEQ1/SSEQ0 = 0/1 | #3 | 2.2 dB |
| TUSB1064 | Laptop cable → DP lanes | DPEQ1/DPEQ0 = R/R | #5 | 6.5 dB @ 4.05 GHz |
| TUSB1046 | Downstream cable → RX1/RX2 (USB) | EQ1/EQ0 = R/1 | #7 | 5.2 dB |
| TUSB1046 | Hub TX → SSTX (short) | SSEQ1/SSEQ0 = 0/F | #2 | 1.7 dB |
| TUSB1046 | TUSB1064 → DP inputs (~30 mm) | DPEQ1/DPEQ0 = 0/0 | #0 | 1.0 dB |

TUSB1046 CAD_SNK = H (R523, 10 k to +3V3) disables AUX snoop, so the lanes follow CTL only. This is robust against
AUX traffic the chip cannot parse. Fitting R524 instead of R523 re-enables snoop, which turns unused lanes off.
I2C is unused. I2C_EN has a DNP 1 k pull-up on both chips for a possible I2C variant, which would also need CTL0/FLIP
rewired as SDA/SCL and pull-ups.

## Protection

- **Laptop CC/SBU: TPD4S480** (U501): 63 V-tolerant OVP FETs + IEC ESD on CC1/CC2/SBU1/SBU2. The PMG1 CC/SBU pins are
  6 V abs max, and the laptop VBUS reaches 28 V. RPD_Gx is tied to C_CCx, so the dead-battery Rd shows while VPWR is off:
  a dead deck still looks like a sink, and the laptop turns on 5 V (bus-powered cold start). The PMG1's own Rd sits behind
  the open FETs. VPWR = PMG1_VDDD: once the PMG1 has power (from VBUS or the deck), the FETs close after about 3.5 ms
  and the internal Rd drops out, so the PMG1 owns CC (Rp as source, DRP). VBUS_LV and EPR_BLK_G are left open, because
  PMG1-S3 VBUS sensing is 28 V rated. EPR_EN is tied to VPWR, so the divider is always on and the unloaded VBUS_LV
  stays below its 24 V abs max at 28 V without relying on the auto-EPR threshold. VBIAS has 100 nF/100 V. The CC FETs pass VCONN (600 mA) for e-marked 5 A cables.
- **Downstream CC/SBU: TPD6S300** (U504): 24 V OVP on CC/SBU + ESD on CC, SBU and D+/D- (D1/D2 = HUB_DSC_DP/DN).
  RPD_G1/2 = GND: **no dead-battery Rd on a source-only port** (it would make the port look like a sink). N.C. pins
  16/17 go to GND as the datasheet says. VPWR = +3V3, because port 1 only runs when the deck is powered.
- **SuperSpeed ESD: TPD4E02B04** (0.25 pF typ, 0.33 pF max, ±0.07 pF matching, rated for 10 Gbps). One per pair of
  pairs: D502 (TX1/RX1), D503 (TX2/RX2), D506/D507 on the downstream port. D504 covers laptop D+/D-. Flow-through
  package: the NC pads (10↔1, 9↔2, 7↔4, 6↔5) carry the same net, so route each line straight across the pads.
  TPD4E05U06 (0.5 pF) was rejected because it is rated only for 5 Gbps.
- **VBUS TVS.** Laptop: **SMCJ28A** (Littelfuse C224047, 1500 W SMC; VRWM 28 V, VBR 31.1–34.4 V at 1 mA, VC 45.4 V at
  33 A). It replaces SMBJ30A (VBR 33.3–36.8 V, VC ≈ 48 V), which did not even conduct at 34 V.
  - At 29.4 V (28 V EPR + 5 %) the part is about 1.7 V below VBR min, so leakage stays in the µA range. Bench-check
    it hot at 28 V.
  - Compared with SMBJ, the SMC package has about 2.5× lower dynamic resistance, so it clamps lower at a given surge
    current.
  - **Residual risk, accepted:** no TVS with VRWM ≥ 28 V can keep the PMG1 VBUS_C_P0 / CSP_P0 / CSN_P0 pins (34 V abs
    max) below 34 V during a surge or a hard ringing event. Flat-clamp parts such as the TVS3300 have VRWM 33 V and do
    no better. Infineon's EPR references wire VBUS_C directly in the same way.
  - Steady-state over-voltage is handled by the power_laptop OVP latch (30.8 V) and the LM74800 backstop (32.6 V).
    Keep the VBUS caps (100 nF here, bulk on power_laptop) close to J501 to damp hot-plug ringing.
  - Downstream: SMAJ6.0A (VRWM 6 V > 5.25 V).
- **Shells:** both receptacle shells go straight to GND (JLC practice), stitched to the plane next to the connector.
  If EMI or ESD testing needs it, a bleed (1 M ∥ 4.7 nF) would require a separate chassis net, which we do not have
  on a bare board.

## Layout notes

- 85 Ω differential (stackup class `HS_85` in board-layout.md) for all SS and DP pairs, 90 Ω for USB2 and AUX.
  Intra-pair skew < 0.1 mm (5 ps), no via stubs (back-drill not available: use through-vias only close to the
  connector, or keep high-speed on L1/L3 with GND reference).
- Order on every SS line: receptacle pad → ESD (straight over the pads) → AC cap (TX lines) → mux. Put the caps
  close to the mux, with GND voids under the 0402 pads (~1 pad width) to cut the capacitive dip.
- Keep the laptop receptacle → TUSB1064 run ≤ 20 mm (cable loss is absorbed by EQ), TUSB1064 → hub ≤ 50 mm, and
  TUSB1064 → TUSB1046 DP lanes ≤ 50 mm, matched between pairs within 2 mm (DP inter-lane skew budget is generous, but
  keep it tight).
- TUSB1064/TUSB1046: 100 nF on each VCC pin at the pin, 10 µF shared. Thermal pad gets a via array to GND.
- TPD4S480 VBIAS cap and TPD6S300 VBIAS cap go at the pin. CC traces stay short and away from VBUS.
- The JAE DX07 has THT B-row pins: B-row SS signals transition through the board at the connector. Check the land
  pattern and B-row pin assignment against the JAE drawing before layout (easyeda import).
- Amphenol 12401610E4#2A is all-SMD (shield THT). Verify the footprint against the Amphenol drawing.

## Part list (this sheet)

| Ref | Part | LCSC | JLC stock (2026-10-02) | Type |
|---|---|---|---|---|
| J501 | JAE DX07S024XJ1R1100 USB-C 24P 48 V/5 A | C134113 | 1626 (also J101 on power_input) | extended |
| J502 | Amphenol 12401610E4#2A USB-C 24P 20 V/5 A | C5119948 | 7161 | extended |
| U502 | TI TUSB1064IRNQT | C702365 | 53 | extended |
| U503 | TI TUSB1046-DCIRNQT | C2652434 | 42 | extended |
| U501 | TI TPD4S480RUKR | C43131250 | 2881 (also U101) | extended |
| U504 | TI TPD6S300RUKR | C2649810 | 17349 | extended |
| D502–D504, D506, D507 | TI TPD4E02B04DQAR | C106794 | 105950 | extended |
| D501 | SMCJ28A (Littelfuse), D_SMC | C224047 | 5845 | extended |
| R544 | 100 k 0402 (UP_HPD pull-down) | C25741 | — | basic |
| D505 | SMAJ6.0A (MDD) | C364284 | 99852 | extended |
| C (×26) | 220 nF 0402 X7R | C16772 | 2.3 M | basic |
| C | 100 nF 0402 / 10 µF 0603 / 1 µF 0402 / 100 nF 0603 50 V | C1525 / C19702 / C52923 / C14663 | — | basic |
| C502 | 100 nF 0805 100 V X7R | C28233 | 1.25M | basic |
| R | 1 k / 10 k / 20 k / 100 k / 1 M 0402, 2 M 0603 | C11702 / C25744 / C25765 / C25741 / C26083 / C22976 | — | basic |

TUSB1064 (53) and TUSB1046 (42) have thin JLC stock: order the prototype run early. Alternates with the same RNQ
footprint: TUSB1064RNQT C2652412 (20), TUSB1046A-DCI C702363/C702364.

## Open issues

1. **PMG1 firmware:** pulse CTL0 L→H→L for power-down after boot/detach. Advertise pin assignment D on port 0, with an
   optional C mode. Forward IRQ_HPD. Set FLIP before CTL1.
2. **PMG1_VDDD load:** TPD4S480 VPWR draws up to 160 µA plus the R501 pull-up (33 µA). Confirm with the pd_pmg1 budget
   (≈10 mA total) that VDDD stays up in every state where the PMG1 must see CC.
3. **cReceiver**: the 390 pF CC caps are on pd_pmg1 next to the PMG1 CC pins (checked). The TPD on-capacitance adds
   about 74 pF, so the total stays inside 200–600 pF.
4. **Connector footprints** (easyeda imports) must be checked against the JAE/Amphenol drawings, especially the DX07
   THT B-row numbering and the shield pads.
5. **EQ settings** are first guesses from channel length. Tune them on the bench (eye/compliance with a 1 m 10G cable
   and a monitor over HBR3) by moving the strap 0402s.
6. **Cascaded linear redrivers on HBR3:** margin is unknown. The fallback is TUSB1146 (adaptive EQ) or PI3USB31532
   (passive) on the downstream side, but neither shares the RNQ footprint.
7. **TPD4S480 EPR_EN tied high** (to VPWR): the divider is always on and VBUS_LV is unused. Confirm with TI that
   permanent EPR mode has no side effects on the CC/SBU OVP behaviour at 5–20 V.
8. **Fault flags** UP/DS_CCPROT_FLT_N are local nets with pull-ups. Wire them to PMG1/RP2350 if pins are free.
9. **Thermal:** TUSB1064 + TUSB1046 ≈ 0.6 W total. Place a TMP1075 near them (sensors sheet, "PMG1/TUSB1064 area").
