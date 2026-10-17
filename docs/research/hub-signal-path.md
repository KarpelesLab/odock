# odock-10: USB 10G hub and high-speed signal path (researched 2026-10-02)

Stock is from the JLC parts API (JLC) and findchips (Mouser) on 2026-10-02. **V** = verified in a datasheet or
primary source (URL given). **I** = inferred or engineering judgement.

## TL;DR

- **Hub: Microchip USB7206C.** It has 5× USB 3.2 Gen2 downstream ports plus 1× USB2-only port, which is
  exactly RTL8156BG + GL3224 + 2× USB-A + downstream C on the five USB3 ports, and RP2350 on the USB2 port.
  The datasheet is public, the chip runs from ROM (no firmware blob), and the **per-port speed/connect
  registers are documented and readable over SMBus** (AN2935). For 3× USB-A, cascade a GL3523 (Gen1) behind
  one port to host GL3224 + RTL8156BG.
- **Correction to odock-10.md:** **TUSB1046-DCI is a DFP (host/source-side) mux and does not fit the upstream
  UFP port.** For the laptop-facing UFP, use **TI TUSB1064** (sink-side, UFP_D pin assignments C/D/E, 10G + HBR3).
  **TUSB1046-DCI is the right part for the downstream DFP C port**, so we still use it, just on the other port.
- **DP pass-through works as an AUX/HPD "wire" design.** TUSB1064 DP0/DP1 outputs go through AC caps into
  TUSB1046 DP0/DP1 inputs, and AUX is AC-coupled between the two chips' AUX pins. HPD comes from the downstream
  PD controller (Attention VDM from the monitor), goes onto one HPD net, and the upstream PD controller sends it
  to the laptop as an Attention VDM. Both muxes run in GPIO mode, driven by their PD controllers. The MCU only
  observes.
- **No redrivers needed on the USB-A 10G ports** at 50–80 mm (I). Instead, tune the hub's Gen2 TX de-emphasis
  registers.

## 1. USB 10G hub candidates

| Part | DS ports: USB3 Gen2 / USB2-only | Type-C features | Config / FW | Per-port speed over I2C | Bridge | Pkg | Datasheet | JLC stock / price | Mouser stock / price |
|---|---|---|---|---|---|---|---|---|---|
| **USB7206C** | **5 / 1** (all 5 at 10G) (V) | None native (Type-B-style US/DS); FlexConnect (role swap) | ROM firmware; straps, 8 kB OTP, SMBus config stage, or optional SPI flash (V) | **Yes, documented** (see below) (V) | USB→I2C/SPI/UART/I2S/GPIO via internal Hub Feature Controller (V) | VQFN-100 12×12 | Public (V) | USB7206CT/KDX C3210691: 21 @ $14.56; -I C3210686: 5 | USB7206CT/KDX 1950 @ $8.66; USB7206CT-I 1420 @ $10.82 |
| USB7216C | 3 Type-A Gen2 + 1 native USB-C Gen2 (4 USB3 in all) / 2 (V) | 1 native C (CC + internal orientation mux, no alt mode) | as USB7206C | Yes (same register family) (V, AN2935 covers 7216) | same | VQFN-100 | Public | C3210682: 3 | USB7216CT/KDX 3090 @ $9.45 |
| USB7252C | 1 Type-A + 2 native C (3 USB3) / 1 (V) | 2 native C, integrated mux, VCONN control | as USB7206C | Yes (V) | same | VQFN-100 | Public | C3210689: 28 @ $17.71 | USB7252CT/KDX 3635 @ $9.93 |
| USB7202 | US native C + 2 DS native C / 2 USB2 (V) | native C upstream | as above | Yes | same | VQFN-100 | Public | not listed | not listed |
| USB7205C / USB7214 / USB7256C | 7205C: 4/1; 7214: 2 C + 1 A (V, AN6202). USB7256C: no such part found | — | — | — | — | VQFN-100 | — | 0 / not listed | not checked |
| USB7302 / USB7304(S) | 2 / 4 Gen2 (V, AN6202); smaller QFN44/56/64, but no Hub Feature Controller or OTP per the guide | — | — | not documented | — | QFN | — | 0 | none found |
| Realtek RTS5420 | 4 / 0 (all 10G) | — | **SPI flash firmware** (V, prior research) | NDA | I2C master/slave, GPIO | QFN-88 10×10 | NDA | C35880247: 372 @ $6.56 | — |
| Genesys GL3590 | 4 / 0 (all 10G) | variants with C | ROM + I2C | NDA register map | 2× I2C engines | QFN-76/88 | NDA (leaked copies only) | 0 (C7470882) | — |
| VIA VL822 | 4 (Q7/Q8) or 2 (Q5) / 0 (all 10G) | Q8: integrated 10G mux for UFP + 2 DFP | **SPI flash firmware** (V, prelim DS) | not documented; PWM LED pins only | — | QFN-76/88/56 | prelim DS leaked | 0 | — |

Sources: USB7206C DS https://ww1.microchip.com/downloads/aemDocuments/documents/NCS/ProductDocuments/DataSheets/USB7206C-Data-Sheet-DS00003850.pdf ·
USB7252C DS https://ww1.microchip.com/downloads/aemDocuments/documents/UNG/ProductDocuments/DataSheets/USB7252C-Data-Sheet-DS00003852.pdf ·
USB7202 DS https://ww1.microchip.com/downloads/en/DeviceDoc/00002733D.pdf ·
Selection guide AN6202 https://ww1.microchip.com/downloads/aemDocuments/documents/UNG/ApplicationNotes/ApplicationNotes/AN6202-Microchip-USB3-Hub-Product-Selection-Guide-DS00006202.pdf ·
RTS5420 https://www.realtek.com/en/products/computer-peripheral-ics/item/rts5420 ·
GL3590 https://www.genesyslogic.com.tw/en/product/show.php?num=GL3590_GL3590-S&kind=USB3.2Gen2_Hub

Only the Microchip parts meet all of our needs: ≥ 5 USB3 ports in one chip, a public register map, ROM firmware,
and authorized-distributor stock. Every competitor is 4-port, so we would need two cascaded hubs, both with
SPI-flash firmware or NDA docs.

### USB7206C details (V unless marked)
- **Status registers** (AN2935, base BF80_0000h):
  - `USB30_HUB_DN_SPEED_IND1/2` @3852h/3853h: 2 bits per physical port, 01 = 5G, 10 = 10G, 11 = 20G.
  - `USB30_HUB_STAT` @3851h: USB3 connect per port (active-low) + upstream USB3 host detect.
  - `USB2_DN_SPEED41/75` @3195h/3196h: none/LS/FS/HS.
  - Also `USB2_LINK_STATE`, `SS_Px_LTSSM_STATE` (upstream: 61C0h), and per-port Gen1/Gen2 TX de-emphasis
    (`SS_Px_PIPE_TX_DEEMPH_*`).
  - These are **physical** port numbers. Use datasheet Table 3-7 to map them to logical ports.
  - AN2935: https://ww1.microchip.com/downloads/en/Appnotes/AN2935-Configuration-of-USB7202-USB7206-USB7216-USB725x-00002935B.pdf
  - The upstream link speed (Gen1 vs Gen2) has no explicit field. Infer it from the LTSSM state, or show "10G" if
    any downstream port is at 10G (I).
- **SMBus access:**
  - 7-bit address **0x2D**. Register read/write uses opcode 9937h with a buffer of {dir, len, 32-bit BE addr, data}
    (AN2935 §3.4).
  - Slave pins are SLV_I2C_CLK/DATA on PF26/PF27 in strap "Configuration 3" (CFG_STRAP2 = 200 k PD,
    CFG_STRAP1 = 10 k PD, CFG_STRAP3 = 200 k PD).
- **Catch: runtime SMBus access needs the SMBus boot stage.**
  - At boot the hub looks for 10 k pull-ups on the slave pins. If it finds them, it **waits indefinitely** in
    CFG_SMBUS until the master sends `USB_ATTACH_WITH_SMBUS` (AA56h). Only after that does the slave stay alive at
    runtime.
  - Firmware must also keep the clocks forced on, or SMBus goes dead while the host has the hub suspended.
  - Without the pull-ups, the hub boots straight from straps/OTP and works stand-alone, but SMBus is unavailable at
    runtime.
  - **Design (I):** feed the two 10 k SMBus pull-ups from an RP2350 GPIO (or a tiny load switch) and let the RP2350
    drive hub RESET_N (open-drain, with an external pull-up). Normal firmware raises the pull-ups, pulses reset,
    configures the hub, then sends AA56. In BOOTSEL mode or with broken firmware the GPIOs float, so the hub boots
    stand-alone and UF2 recovery through the hub still works.
- **Straps:** PRT_DIS_P/M per port, CFG_NON_REM (mark the RTL8156BG/GL3224/RP2350 ports non-removable),
  CFG_BC_EN (BC1.2 CDP/DCP on the USB-A ports). JLC does not need to program anything; OTP stays blank.
- **Bridges:** the Hub Feature Controller exposes USB→I2C master (PF18/PF31), SPI, GPIO and UART to the *upstream
  host*. This is optional. **Do not** connect the hub's I2C master to the PD controller bus, because host software
  must not be able to reach power policy (I).
- **Power:** VCORE 1.15 V + VDD33. Base current at upstream SS+ is 410 mA + 179 mA per active SS+ port on VCORE,
  and ≈31 mA + 11 mA per port on 3.3 V. With all 5 ports at 10G that is ≈1.31 A @ 1.15 V + ≈0.1 A @ 3.3 V
  ≈ **1.8 W**. Needs a 1.15 V/2 A buck and a solid thermal pad via array. Suspend draws 14 mW.
- **Clock:** 25 MHz crystal.

### Port plan (I)
| USB7206C logical port | Use | Path |
|---|---|---|
| 1 | Downstream USB-C 10G | SS → TUSB1046-DCI; USB2 → receptacle directly |
| 2, 3 | USB-A 10G #1/#2 | direct, CDP enabled |
| 4 | RTL8156BG (5G device) | direct, non-removable |
| 5 | GL3224 (5G) — or GL3523 uplink in the 3× USB-A variant | direct, non-removable |
| 6 (USB2-only) | RP2350B | non-removable |

**3× USB-A variant:** move GL3224 + RTL8156BG behind a **Genesys GL3523** Gen1 4-port hub (GL3523-OTY30 C390630,
11 863 @ $2.46, ROM-based (I)) on port 5, which frees a port for the third USB-A.
- Bandwidth is fine: 2.5GbE ≈ 290 MB/s plus UHS-I ≈ 100 MB/s fits inside one 5G uplink.
- The cost is about $2.5 and a 9×9 QFN.
- Those two devices are then not covered by the Microchip speed registers, but their speeds are fixed and known
  anyway (LAN speed comes from the RTL8156 LEDs).
- A second USB7206C would also work but is overkill (~$9, +1.8 W).

## 2. Alt-mode muxes / redrivers

| Part | Side | USB | DP | Pin assign. | Control | JLC | Mouser | Verdict |
|---|---|---|---|---|---|---|---|---|
| **TI TUSB1064** | **UFP (sink)** (V) | 10G | HBR3 (8.1G), 12 dB EQ | UFP_D C, D, E | GPIO (CTL0/CTL1/FLIP) **or** I2C (exclusive, chosen by the I2C_EN 4-level strap) | RNQT C2652412: 20 @ $5.74; IRNQT C702365: 53 @ $6.06 | RNQT 242 @ $10.04; IRNQT 162; -Q1 (VQFN 5×7) 2919 @ $14.34 | **Upstream pick** |
| TI TUSB564 | UFP | 5G only | HBR3 | C, D, E | GPIO/I2C | C882776: 41 | — | Fallback only (caps USB at 5G) |
| **TI TUSB1046-DCI** | **DFP (source)** (V) | 10G | HBR3, 14 dB EQ | C, D, E, F | GPIO or I2C; CAD_SNK pin disables AUX snoop | C2151061: 17; C2652434: 42 (~$4.1–4.5) | TUSB1046-DCIRNQR 2798 @ $7.97 | **Downstream pick** |
| TI TUSB1046A(I)-DCI | DFP | 10G | HBR3 | C–F | same + Intel DCI | AI-RNQT C702364: 67 @ $10.81 | AI-DCIRNQR 6777 @ $9.00 | Drop-in alternate |
| TI TUSB1146 | DFP | 10G, adaptive EQ | UHBR10 | C, D, E | GPIO/I2C | IRNQT C1880991: 43 @ $9.50 | not checked | Upgrade alternate |
| Diodes PI3USB31532 | either (passive, bidirectional) (V) | 10G | UHBR10, −1.7 dB IL | 2- or 4-lane DP + AUX/SBU mux | pin or I2C | ZLCEX C2655457: 25 @ $3.53; Q2 C23942354: 11 | 1698 @ $3.26 | Passive fallback for the downstream port |
| TI HD3SS460 | either (passive) | **5G only** (V) | HBR2 | — | GPIO | C2652446: 19 | — | Rejected |
| TI TUSB546(A)-DCI | DFP | **5G only** (V) | HBR3 | C–F | — | C2861512: 100 | — | Rejected (5G) |
| Diodes PI3DPX1205A | DFP (V) | 10G | HBR3 | — | I2C | C3764338: 157 | — | **Obsolete** (→ PI3DPX1225A) |
| Diodes PI3DPX1207C | 4-channel linear redriver + AUX/SBU switch, not a crosspoint | 10G | HBR3 | — | I2C/pin | C2057262: 3557 @ $2.53 | — | Not needed |
| Parade PS8740 | DFP | 5G | HBR2 | — | — | 0 | — | NRND, rejected |
| VIA VL170 | data-only 10G 2:1 mux (I) | 10G | none | — | — | 0 | — | Rejected |

Sources: https://www.ti.com/lit/ds/symlink/tusb1064.pdf · https://www.ti.com/lit/ds/symlink/tusb1046-dci.pdf ·
https://www.ti.com/lit/ds/symlink/tusb1146.pdf · https://www.ti.com/lit/ds/symlink/tusb546a-dci.pdf ·
https://www.ti.com/lit/ds/symlink/hd3ss460.pdf · https://www.diodes.com/assets/Datasheets/PI3USB31532.pdf ·
https://www.diodes.com/assets/Datasheets/PI3DPX1205A.pdf · https://www.paradetech.com/products/ps8740/

TUSB1064 has thin authorized stock: JLC has 73 in total and Mouser about 400 RNQT/IRNQT. Buy prototype quantities
early. Its automotive -Q1 version in VQFN 5×7 has 2919 at Mouser, but uses a different footprint.

**Who controls the muxes:**
- Each mux is driven by **its own port's PD controller**, using GPIO events: "DP mode" → CTL1, "USB3 enabled" →
  CTL0, plug orientation → FLIP. This is the approach in TI's EVMs (I, consistent with
  https://e2e.ti.com/support/interface/f/interface-forum/781271/).
- EQ is set with 4-level strap resistors.
- GPIO mode is preferred because it keeps alt mode autonomous of the MCU, matching the "PD boots by itself"
  rule. The RP2350 reads the CTL/FLIP nets as inputs for the LCD (mode, lanes, orientation).
- Leave a 0 Ω/strap option for I2C mode (I2C_EN = 1) in case AUX snoop must be disabled or EQ tuned at runtime.
  I2C and GPIO modes are mutually exclusive (V).
- TPS6599x-class controllers can alternatively drive TI muxes over their I2C master (I2C3m) (I, not yet checked
  against the chosen PD part).

**USB-A redrivers: not needed (I).**
- 50–80 mm (2–3 in) of 85 Ω microstrip/stripline on FR-4 costs roughly 1.5–3 dB at 5 GHz, depending on the
  laminate (see jlcpcb.md). Typical hub reference designs route several inches without redrivers.
- Tune `SS_Px_PIPE_TX_DEEMPH_GEN2` over SMBus if compliance or eye testing shows margin problems.
- Optional insurance: TUSB1002A (C2672378, 1000 @ $3.30; C1849392, 167 @ $1.90) on the longest run. It costs
  area and power, so add it only if the layout forces more than 100 mm.
- On the upstream path the cable loss is absorbed by TUSB1064's EQ; keep receptacle→TUSB1064→hub short.

## 3. Signal flow (upstream DP → downstream C)

```
Laptop C ──SSTX/RX (2 pairs, flip)──► TUSB1064 (UFP) ──SSTX/SSRX──► USB7206C upstream
            other 2 pairs (DP ML0/1) ──►   │  DP0/DP1 out ──100 nF──► TUSB1046-DCI DP0/DP1 in ──► downstream C (2 or 4 pairs, flip)
            SBU1/2 ◄──► TUSB1064 SBU◄►AUX ─100 nF─ AUX◄►SBU TUSB1046-DCI ◄──► downstream SBU1/2
            D+/D- ───────────────────────────────► hub USB2 upstream          hub port 1 SS ──► TUSB1046 SSTX/SSRX
            CC ──► PD ctrl A (UFP_D)  ◄── HPD net ◄── PD ctrl B (DFP_D) ◄── CC (downstream)
```

1. **Laptop attach.**
   - PD controller A (laptop port, the EPR source; the part is TBD) answers Discover SVIDs with the DP SVID
     (0xFF01) as **UFP_D**, advertising **pin assignment D** (2-lane DP + USB3) so that the USB 10G hub stays
     connected. Assignment C would drop USB3.
   - The laptop sends Configure(D). Controller A raises CTL0 + CTL1 and sets FLIP on TUSB1064.
   - Until a monitor exists, controller A reports **HPD low** in DP Status.
2. **Monitor attach on the downstream C port.**
   - PD controller B (DFP, 5 V source, DFP_D) discovers the monitor or adapter, enters DP mode, and picks **D if
     offered, else C**. In C it routes DP only on DP0/DP1 and the monitor's lanes 2/3 sit idle. This is fine,
     because the laptop trains only 2 lanes: its own config is D, so it caps LANE_COUNT_SET at 2 regardless of the
     monitor's DPCD MAX_LANE_COUNT = 4 (I).
   - In C there is no USB3 on the downstream port (USB2 still works).
   - Controller B sets TUSB1046 CTL0/CTL1/FLIP.
3. **HPD.**
   - The monitor sends Attention/Status (HPD_State, IRQ_HPD) to controller B.
   - Controller B drives a GPIO "HPD out" onto a **single HPD net**. That net feeds controller A's "HPD in" GPIO,
     TUSB1064 HPDIN and TUSB1046 HPDIN.
   - Controller A turns HPD level changes and IRQ_HPD pulses into Attention VDMs to the laptop.
   - The HPD-in/HPD-out GPIO functions are standard in TI/Infineon PD firmware (I). **Verify on the chosen PD
     part(s)**, including that IRQ_HPD (0.5–1 ms pulses) is forwarded.
   - If A and B are the two ports of one dual-port controller (e.g. TPS65994AD), check for an internal HPD
     pass-through option (I).
   - Both TUSB parts disable DP lanes after HPDIN has been low for more than 2 ms but keep AUX connected (V).
4. **AUX.**
   - The laptop runs AUX on SBU. TUSB1064 maps SBU1/2 to AUXp/n by FLIP. The signal then goes through one 100 nF
     cap per line to TUSB1046 AUXp/n, which maps it onto the downstream SBU by its own FLIP.
   - Biasing: give each chip its own datasheet network (V).
     - TUSB1064 side (sink bias): AUXp 1 MΩ → 3.3 V, AUXn 1 MΩ → GND.
     - TUSB1046 side (source bias): AUXp 100 kΩ → GND, AUXn 100 kΩ → 3.3 V.
     - Plus 2 MΩ to GND on each SBU pin.
   - Using a single shared coupling cap between the two bias networks is (I). Confirm against the VESA DP Alt Mode
     AUX bias rules at schematic time.
   - Both chips snoop LANE_COUNT_SET/SET_POWER_STATE passively. Snoop can be disabled (TUSB1046 CAD_SNK pin;
     TUSB1064 via I2C), which TI notes for non-compliant AUX sources (V).
5. **Main link.**
   - Path: laptop GPU → cable → TUSB1064 (EQ for the laptop cable) → ~20–40 mm board + 100 nF caps
     (75–265 nF allowed, V) → TUSB1046 (low EQ setting) → downstream cable → monitor.
   - Both are linear redrivers, transparent to link training (V). The monitor's swing/pre-emphasis requests travel
     over AUX to the laptop source.
   - Two linear redrivers in series is the normal dock topology. Diodes and TI both market linear redrivers as
     cascadable (V, PI3DPX1205A DS).
   - 2-lane HBR3 = 12.96 Gbps payload: 4K60 8-bit RGB with CVT-RB(2), or more with DSC (I).

## Risks / open items

- **PD controllers must support UFP_D (laptop side) and DFP_D (downstream side) DP alt mode, plus HPD GPIO
  pass-through.** This is the real gating item (odock-10 open question 1) and needs a second PD controller (or a
  dual-port part) for the downstream C port.
- **Hub enumeration depends on the MCU when SMBus is enabled.** Mitigate with GPIO-powered SMBus pull-ups, as
  described above. Also force the clocks on (AN2935) so the status registers stay readable while the host has the
  hub suspended.
- **TUSB1064 stock is thin.** Consign from Mouser/Arrow, or keep a TUSB1064-Q1 (VQFN 5×7) footprint variant.
- **USB7206C:** JLC has 26, Mouser has thousands. Plan a Mouser consignment. It is a 100-pin 0.4 mm-pitch VQFN
  that dissipates about 1.8 W, so add a thermal via array and a bottom copper pour (bare-PCB use).
- **Cascaded redrivers + HBR3:** prototype margin is unknown. Keep the TUSB1064→TUSB1046 DP run short and
  symmetric. A fallback is TUSB1146 (adaptive EQ) or PI3USB31532 (passive) on the downstream side.
- **Pin assignment C downstream** (adapters that only offer C or E) drops downstream USB3. This is expected, so show
  it on the LCD.
- The hub's per-port numbering is physical vs logical (DS Table 3-7). Firmware must map it before display.
