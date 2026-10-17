# odock-10 — 10 Gbps prototype

First odock build. Goal: a fully working, fully open USB-C deck assembled entirely by JLCPCB
(**JLC parts only, ≥ 5 in stock — no consignment**, decided 2026-10-02; check with `tools/bom_check.py`), validating everything the
later 20G/40G versions will reuse: power architecture, MCU/LCD firmware, card reader, 2.5GbE,
board outline and silkscreen style. Only the core and high-speed section change later.

Status: **planning** (updated 2026-10-02). Stock figures are JLC parts API / Mouser on 2026-10-02 —
re-check before ordering. Detailed research: `research/pd-controllers.md`, `research/hub-signal-path.md`,
`research/power-and-assembly.md`.

## Block diagram

```
 Laptop USB-C ═══ TUSB1064 (UFP mux) ══ USB 10G ══► USB7206C hub
 (data UFP, 10G     │                                 ├─ 10G ─► USB-A #1
  + DP alt C/D,     │                                 ├─ 10G ─► USB-A #2
  EPR src 140 W)    │                                 ├─ 10G ─► GL3224 ─► SD + microSD
                    │                                 ├─ 10G ─► RTL8156BG ─► RJ45 2.5GbE
                    │                                 ├─ 10G ─► TUSB1046 (DFP mux) ═══ downstream USB-C
                    │                                 └─ USB2 ─► RP2350B (UF2, status app)
                    └── DP 2-lane HBR3 + AUX ───────────────────► TUSB1046 (DP alt out, 4K60)

 PMG1-S3 (CYPM1322, dual-port): port 0 = laptop (EPR source, DP UFP_D, drives TUSB1064)
                                port 1 = downstream C (5 V/3 A source, DP DFP_D, drives TUSB1046, HPD relay)
 TPS26750 + TPD4S480: PD-in charger port (EPR sink, up to 48 V)

 PD-in 5–48 V ──► LM74800 (ideal diode + OV)  ─┐
 Barrel 9–24 V ─► LM74800 (rev/OV/UVLO)       ┴─► VIN 9–48 V ─┬─► LM51770 buck-boost ─► 5/9/15/20/28 V ─► [src switch] ─► laptop VBUS
                  (both always armed: higher voltage wins)     ├─► LM5148 ─► 5 V (USB-A, downstream C, LCD)
 Laptop VBUS ────► [sink switch, released only when external power AND 5 V buck PG] ─► 5 V rail (bus-powered mode)
                                                     └─► 3.3 V / 1.15 V / 1.2 V bucks

 RP2350B ── I2C: PD controllers (status/requests only), hub SMBus (port speeds), LCD SPI,
            RTL8156 LED pins, card-detect; 2.0" LCD, GPIO header (unpopulated), Qwiic, SWD
```

## Parts (draft)

| Block | Part | Stock (JLC / Mouser) | Notes |
|---|---|---|---|
| PD: laptop + downstream C | Infineon PMG1-S3 CYPM1322-97BZXI (BGA-97) | 50 / 8095, $7.13 | 28 V EPR src/sink, DP alt UFP_D + DFP_D; Infineon dock example on GitHub; PD stack is a closed Infineon library (downloaded at build, not committed). Fallback: 2× QFN-48 PMG1 |
| PD: charger input | TI TPS26750 + TPD4S480 | 165 / — ; 2881 | EPR sink 28/36/48 V, boots from ROM + I2C EEPROM |
| Upstream mux | TI TUSB1064 (UFP) | 73 / ~400 | 10G + 2-lane DP HBR3, pin assign C/D/E. **Buy early** |
| Downstream mux | TI TUSB1046-DCI (DFP) | 59 / 2798 | |
| USB 10G hub | Microchip USB7206C | 26 / 1950, $8.66 | 5× 10G + 1× USB2; ROM; per-port speed via SMBus (AN2935); ~1.8 W, needs 1.15 V/2 A |
| SD + microSD | Genesys GL3224-ONY04 | 1646 | 2 slots, UHS-I, ROM |
| 2.5GbE | Realtek RTL8156BG-CG | 2915 | LED pins → RP2350 |
| Input OR / protection | LM74800 ×2 (barrel: reverse + OV + UVLO; PD-in: ideal diode + OV) | 4k+ | No hardware priority: both armed, higher voltage wins; source preference is firmware policy (PD voltage request). LM74720 dropped (gate −VIN issue), LTC4417 rejected (36 V max) |
| Buck-boost to laptop | TI LM51770 + external FETs | 1007 / 2131 | 78 V rated; defaults 5 V; voltage steps set by PD-controller GPIOs (MCU can't set voltage); ~96–97 % eff. Plan B BQ25756 |
| 5 V rail | TI LM5148 (80 V buck ctrl) | 57k | Up to ~8 A |
| 3.3 V / 1.x V | TPS62933 / TPS563201; TPS62A02 / TLV62569 | stock | |
| USB-A port switches | TPS2553 | stock | |
| MCU | RP2350B + W25Q128 | 3875 / 51k | |
| Display | HS20HS072RX 2.0" 320×240 IPS | 2208 | JLC hand-solders FPC; foam tape TBC with JLC |
| Barrel jack | Same Sky PJ-063BH (5.5×2.5, 8 A) | 240 / 1580 | 2.1 mm plugs won't fit |
| RJ45 2.5G | USAKRO DGUK211Q340CD2A4D2 | 111 | Low stock; no LEDs |
| USB-A 10G | Amphenol GSB4111312HR | 3846 | |
| USB-C (laptop, PD-in; 48 V/5 A/10G) | JAE DX07S024XJ1R1100 | 1626 | |
| USB-C (downstream, 20 V/5 A/10G) | Amphenol 12401610E4#2A | stock | |
| SD / microSD sockets | Hanbo SD-111 / Hirose DM3AT | 5209 / 18849 | |

## Decisions (2026-10-02)
- Display out: **DP alt mode over the downstream USB-C** only (no full-size DP/HDMI on odock-10).
- **2× USB-A 10G.** Hub ports: USB-A ×2, downstream C, GL3224, RTL8156BG on the 5× 10G ports; RP2350 on USB2.
- Board may grow beyond 100×60 mm if thermals need it; prototype carries extensive thermal instrumentation.
- **RP2350 is the update hub for every other programmable part.** Its firmware bundles images/configs for
  the other chips and flashes them on first boot and on updates.

## Firmware & update architecture
RP2350 firmware = its own code + a bundle of component images. On boot it compares versions and
(re)flashes as needed; updates ship as a single UF2 dropped onto the deck over USB.

| Component | Programmable storage | RP2350 path |
|---|---|---|
| PMG1-S3 (laptop + downstream PD) | internal flash | SWD (RP2350 as SWD probe, debugprobe-style) or PMG1 I2C bootloader |
| TPS26750 (PD-in) | I2C config EEPROM | RP2350 writes EEPROM (WP pin controlled) |
| USB7206C hub | ROM + runtime SMBus config; optional SPI flash | SMBus config at boot; SPI flash optional |
| GL3224 card reader | ROM; optional SPI flash | not needed initially |
| RTL8156BG | ROM; MAC in EEPROM/eFuse | **unique MAC** from a 24AA02E48/24AA025E48 EUI-48 EEPROM (C38987 / C129895) read by RP2350 and programmed into the PHY config |
| LCD | — | — |

**Safety trade-off:** if the RP2350 can reflash the PD controllers, a bad RP2350 firmware could too.
Hardware backstops that stay independent of *all* firmware:
- Independent hardware OVP on laptop VBUS (comparator + gate kill of the source switch above ~30 V), and
  source switch only enabled with buck-boost power-good.
- **No flash interlock** (decided 2026-10-02): prototypes are expendable. A default-closed solder jumper
  in the PMG1 SWD lines lets anyone who wants it cut the RP2350 off from the PD controller.

## Thermal & power instrumentation (prototype)
- **I2C temperature sensors** (TMP1075, C2870250, 38k stock, 8 addresses) at: buck-boost FETs/inductor,
  LM5148 5 V stage, USB7206C, PMG1/TUSB1064 area, laptop USB-C connector, RJ45/RTL8156, LCD, board edge/ambient.
  Plus a few NTC 0603 (NCP18XH103, C13564) on RP2350 ADC pins for hot spots too small for an SOIC/WSON.
- **Power monitors:** INA226 (36 V max, C49851) on laptop VBUS and 5 V rail; VIN (up to 48 V) needs an
  85 V part — INA237 (C2864837, pin-compatible with INA228/INA238).
- RP2350 logs everything over USB (CDC/serial or the status app) and shows it on the LCD; firmware
  derating policy is tuned from this data. Pads for external thermocouples on key spots.

## User buttons & forced 5 V charging
- **Two user buttons** on RP2350 GPIOs (in addition to BOOTSEL/reset); functions defined in firmware
  (e.g. button A: per-port "charge mode" toggle, button B: LCD page / select). Freely remappable.
- **Forced 5 V ("dumb charge") mode** per port, user-triggered: powers a port even when the device is
  non-compliant (USB-C device without Rd on CC, or no host attached to enumerate the hub).
  - USB-A: TPS2553 load switches (C55266, 58k stock) enabled by RP2350 (OR'd with hub PRTPWR), so ports
    can be powered with no laptop attached. Check USB7206C BC1.2 DCP/CDP + Apple/Samsung charging profiles.
  - Downstream USB-C: PMG1 port 1 sources 5 V without Rd on request from RP2350 (our PMG1 firmware;
    intentionally out-of-spec, user-initiated only).
- **Per-port power measurement:** shunt + INA180A2 (C192764, 99k stock, $0.19) per USB-A port into RP2350
  ADC; USB-C port via PMG1 integrated VBUS current sense (verify) or the same shunt + INA180 scheme.
- **Auto-off:** forced 5 V turns off after 5 min below a low-current threshold (~25 mA, tunable). Per-port
  watts shown on the LCD.

## Key design rules
- **Power safety independent of RP2350 firmware:** PD controllers boot autonomously; buck-boost voltage
  selected only by PD-controller GPIOs; buck-boost/power-path controls on a bus/pins the RP2350 can't reach.
- **Laptop-port direction:** source switch (to laptop) enabled only with external power + buck-boost
  power-good; sink switch (bus power → 5 V rail) enabled only with no external power. Back-to-back FETs,
  never both on. Live transitions via PR_Swap / Fast Role Swap.
- **Hub boot independent of RP2350:** hub SMBus pull-ups powered from an RP2350 GPIO, so in BOOTSEL /
  broken-firmware state the hub boots with defaults and UF2 recovery still works.
- **DP path:** TUSB1064 DP outputs → AC caps → TUSB1046 DP inputs; AUX AC-coupled between muxes;
  each PD port drives its own mux; HPD: monitor → port 1 → port 0 → laptop.

## Power & thermal
- Laptop: up to 140 W EPR, 100 W SPR fallback. Test host: MacBook Pro 16" M4 Max.
- Worst-case board dissipation **~12–14 W** → ~60–80 K rise on a bare 100×60 mm board. **Biggest risk.**
  Mitigations: temperature-based power derating by firmware (thermistors near buck-boost/hub),
  heavy copper + via arrays, optional bottom aluminium plate, or slightly larger board.

## Open questions
2. Does PMG1-S3 support PR_Swap / Fast Role Swap for bus-powered ↔ external-power transitions, and do
   Macs accept it? Alternative: accept a brief disconnect when external power is plugged/unplugged.
5. JLC: foam tape application for the LCD; low stock on RJ45 (111), TUSB1064 (73), USB7206C (26), PMG1 (50)
   → consign from Mouser/DigiKey.
6. Thermal budget vs board size — board may grow beyond 100×60; decide after prototype heat data.
7. Stackup: 6-layer standard likely enough for 10G; decide during layout.

## Schematic status
| Sheet | Status | Design notes |
|---|---|---|
| power_input | drafted, netlist-verified | `design/power_input.md` |
| power_laptop | drafted, netlist-verified | `design/power_laptop.md` |
| power_rails | drafted, netlist-verified | `design/power_rails.md` |
| pd_pmg1 | drafted, netlist-verified (CYPM1321 — has dead-battery Rd) | `design/pd_pmg1.md` |
| usbc_muxes | drafted, netlist-verified | `design/usbc_muxes.md` |
| usb_hub | drafted, netlist-verified | `design/usb_hub.md` |
| usb_a | drafted, netlist-verified | `design/usb_a.md` |
| card_reader | drafted, netlist-verified (GL3224 is 5 Gbps) | `design/card_reader.md` |
| ethernet | drafted, netlist-verified | `design/ethernet.md` |
| mcu | drafted, netlist-verified (TCA9534 expander for slow status I/O) | `design/mcu.md` |
| display_ui | drafted, netlist-verified | `design/display_ui.md` |
| sensors | drafted, netlist-verified | `design/sensors.md` |

**Review pass (2026-10-02):** independent schematic review of all sheets (`review/power.md`, `review/pd_mux.md`,
`review/data.md`, `review/mcu_ui.md`) — 0 BLOCKER, 7 MAJOR, all fixed (see each file's Resolution section);
footprint verification of all 54 custom footprints (`review/footprints-1.md`, `-2.md`) — 50 fixed (incl. a mirrored
RJ45 pinout), USB-A drawing still to confirm. Power-input priority is now diode-OR (highest voltage wins), firmware
chooses source preference. Firmware rules collected in `design/mcu.md`. 186 parts, ERC clean.

**All 12 sheets drafted (2026-10-02):** 181 unique parts, all JLC stock ≥ 5, netlist verify OK, ERC clean except one
spare-pin label. Parts ≈ $160/board at qty-1 prices; 125 extended part types (~$375 JLC fee per order — swap
passives to basic parts to cut this). Lowest stock: CYPM1321 (20), USB7206CT (21), TUSB1046 (42), TUSB1064 (53).

## I2C address map (so far)
| Bus | Addr | Device |
|---|---|---|
| I2C_SYS | 0x41 | INA226, +5V rail (power_rails) |
| I2C_SYS | 0x44 | INA226, laptop VBUS (power_laptop) |
| I2C_SYS | 0x45 | INA237, VIN (power_input) |
| I2C_SYS | 0x48–0x4F | TMP1075 ×8 (sensors) |
| I2C_SYS | 0x20 | TCA9534 I/O expander (mcu) |
| I2C_SYS | 0x50 | 24AA025E48 EUI-48 MAC EEPROM (ethernet) |
| I2C_PD | 0x21 | TPS26750 target (power_input) |
| I2C_PD | 0x42 | PMG1-S3 HPI (pd_pmg1) |
| HUB SMBus | 0x2D | USB7206C (usb_hub) |
| TPS26750 private | 0x50 | AT24C512C config EEPROM (RP2350 writes it via TPS26750 pass-through — confirm) |

## Cross-sheet integration items (from power sheet design)
1. **RTL8156BG needs an external 0.95 V rail** (internal-regulator BGS variant not stocked): regulator on the
   ethernet sheet (e.g. TLV62569 from +3V3, enabled by the PHY's POW_EXT_SWR pin).
2. **GL3224 runs from 5 V** (4.75–5.25 V): check +5V sag in bus-powered mode (sink switch drop).
3. **RAILS_PG** (open-drain, +1V15 good) should wire-OR onto HUB_RESET_N → MCU drives HUB_RESET_N open-drain;
   promote RAILS_PG to a global net when building usb_hub/mcu.
4. **LAPTOP_SNK_EN must work with a dead deck** (bus-powered cold start, no +3V3 yet): pd_pmg1 must drive it
   from VBUS-powered logic (PMG1 powered from laptop VBUS).
5. **PD-in TVS** (SMCJ51A, 82 V clamp at full surge) exceeds TPD4S480 VBUS abs max (63 V) — revisit clamp.
6. **Footprints to check before layout:** PJ-063BH (pad spacing mismatch found), XAL1010, HTSSOP-38 (LM51770),
   TPS25947, electrolytics, all easyeda imports.
7. **LM51770 compensation** needs simulation/Bode (shared VSEL RC node adds lag); LM74800 charge-pump start at
   5.1 V output to bench-check (or default 5.2 V). Full 140 W needs VIN ≳ 16 V.
8. **LM5148** at 8 A from 48 V ≈ 91 % (≈ 3.9 W) — ~1 W above budget; high-side FET is the hot spot.
9. TPS26750 boots in AlwaysEnableSink so the deck works with a blank EEPROM; draws from 5 V sources before a contract.

### From data-path sheets
10. **PMG1 CC pins are 6 V-rated** → laptop port CC/SBU behind TPD4S480 (EPR, dead-battery Rd enabled, powered
    from PMG1_VDDD; EPR_EN tied high — confirm with TI that permanent EPR mode is fine at low VBUS).
11. **PMG1 firmware duties:** GPIO-switched port-0 power path while still using PMG1 CSA (Infineon example uses
    the internal gate driver — confirm stack allows it); pulse mux CTL0 to power muxes down when unattached;
    advertise pin assignment D on the laptop port; forward IRQ_HPD; VBUS discharge after voltage step-downs.
12. **Hub port power pin is shared PRTPWR/OCS** → USBAx_PWR_EN and USBAx_OCS_N are one node (0 Ω joined);
    usb_a sheet must not add a pull-up there.
13. **MCU sheet:** no pull-ups on HUB_SMB_*; HUB_SMB_PU from a push-pull GPIO; HUB_RESET_N driven open-drain.
14. **AC coupling convention:** hub sheet caps all hub TX; device-side sheets cap their TX toward the hub
    (card_reader, ethernet, usb_a connectors per USB 3.x rules).
15. **Footprints to verify:** both USB-C receptacles (DX07 THT B-row numbering), PMG1 BGA-97 (0.5 mm), USB7206C VQFN-100.
16. Low stock: CYPM1321 (20), TUSB1046 (42), TUSB1064 (53), USB7206CT (21) — order the prototype run early.
17. Two linear redrivers in series at HBR3 — EQ is a first guess (both sides have bench-tunable strap footprints).

### From remaining sheets
18. **RP2350B pins ran out** (54 needed / 48) → TCA9534 at 0x20 for EXT_PWR_PRESENT, LAPTOP_OVP_N, TEMP_ALERT_N,
    card detects, ETH_RESET_N, ETH_I2C_EN. Hub SMBus and Qwiic on PIO I2C.
19. **RTL8156BG has no reset pin** → ETH_RESET_N switches the PHY's 3.3 V (TPS22918); hold low ≥ 100 ms.
    +3V3 regulator changed to TPS62933F (forced PWM — Realtek wants ≥ 1 MHz PWM supply).
20. **MAC address:** blank RTL8156BG has no unique MAC; plan = RP2350 reads 24AA025E48 and writes the PHY eFuse
    once over the PHY's I2C (bridge enabled by ETH_I2C_EN). Slave address/feasibility unverified → bench-test early;
    fallback host tool / OS override.
21. **LCD FPC tail** has a stiffener (connector-style): confirm JLC can solder it; fallback 12-pin 0.5 mm FPC connector.
22. Forced-5 V on USB-A: check whether USB7206C presents the BC1.2 signature on a port it considers off.
23. More footprints to verify: USB-A (GSB4111312HR), TPS2553 SOT-23-6 (shared name), SD-111, DM3AT,
    RTL8156BG EP size (4.7 vs 4.5 mm), RJ45 (shell pad renumbered), RP2350B QFN-80, LCD FPC (hand-made).

## Notes on a 20 Gbps step
USB 3.2 Gen2x2 (20G) is **not supported by Apple Silicon Macs** (they fall back to 10G), uses all 4
lanes (no DP alt mode at the same time), and essentially no Gen2x2 hub chips exist. A useful 20G step
would therefore be **USB4 at 20 Gbps**, which still needs a USB4 chip — same sourcing problem as 40G.
