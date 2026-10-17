# USB-C PD controller selection — odock-10 (researched 2026-10-02)

[V] = verified in datasheet/vendor page (URL in Sources), [S] = stock/price query 2026-10-02 (JLC parts API,
findchips authorized distis), [I] = inference / to verify on hardware or with vendor.

Ports: **(a)** laptop port — data UFP, power **source** 5–28 V EPR 140 W, DP Alt Mode **UFP_D** (pin C/D), SOP'
e-marker discovery, drives external buck-boost + FETs. **(b)** downstream C — data DFP, source 5 V/3 A,
DP Alt Mode **DFP_D**. **(c)** PD-in — **sink** EPR up to 48 V / 240 W.

## Comparison

| Part | EPR | DP Alt Mode | Ports | Config / firmware | Datasheet | Package | JLC stock [S] | Mouser/other [S] | Lifecycle | Fit |
|---|---|---|---|---|---|---|---|---|---|---|
| **Infineon PMG1-S3** CYPM1322-97BZXI (dual) / CYPM1311-48LDXI (single) | **Source + sink, 28 V** (VBUS abs max 34 V) [V] | DFP & UFP roles, pin C/D/E masks, HPD/Attention handling, in source form (PdAltMode) [V] | 2 (BGA) / 1 (QFN) | User firmware (ModusToolbox, free). PdStack `pmg1_pd3_drp_epr` = closed precompiled lib under Cypress EULA; PdAltMode DP = source. Public **dock reference app** (2-port, EPR 140 W source on port 0, DP alt, buck-boost drivers) [V] | Public [V] | 97-BGA 6×6 (0.65/0.5 mm grid, pitch to confirm) / QFN-48 6×6 0.4 mm | 1322: **50**; 1321-T: 20; 1311: 0 | 1322: **Mouser 8095 @ $7.13** (1) / $5.49 (10); 1311: Mouser 958 @ $6.20 | Active [V] | **Ports a + b** |
| **TI TPS26750** | **Source + sink, 28/36/48 V + AVS** [V] | None | 1 | ROM + config from external I2C EEPROM (0x50) or host load; ADCIN straps choose dead-battery behaviour; free web GUI [V] | Public [V] | VQFN-32 4×4 | 165 (+52 "A") | Mouser 1500 @ $3.21 | Active [V] | **Port c** |
| Infineon CCG8 CYPD8125 (1p QFN48) / CYPD8225 (2p BGA97) | Source + sink, 28 V [V] | Yes (notebook-side DFP_D; SBU mux) [V]; UFP_D dock use not targeted [I] | 1 / 2 | Host SDK 3.7 via Infineon Developer Center (registration) [V/I] | Public [V] | QFN-48 / BGA-97 | 8125: 50; 8225: 0 | 8125: Mouser 0, Verical/Rochester ~5k; 8225: element14 1794 | Active | Same silicon class as PMG1-S3 but notebook-firmware oriented → PMG1-S3 preferred |
| TI TPS66994 / TPS66993 / TPS66994E | Yes (Intel TBT5 dock ref, per E2E) [I] | Yes [I] | 2 | Flash-based; config tool + datasheet are **secure/NDA** (E2E threads: docs via email/mySecure) [I] | **Not public** (ti.com/product 404) [V] | VQFN-52 [S] | 0 (JLC lists TPS66994ECAREPR) | None at authorized distis via findchips | ? | **Rejected** — NDA, no stock |
| TI TPS65994AD / AE | **No** — PD 3.0, 5–20 V, VBUS abs max 28 V [V] | DP source (DFP_D) [V] | 2 | App Customization Tool, EEPROM boot [V] | Public | VQFN-48 6×6 | AD 497, AE 7 | Mouser ~4k each @ $6.03 | **NRND** [V] | Rejected (SPR, NRND) |
| TI TPS65988 | **No** — 20 V/5 A max [V] | DP source + sink (HPD sink side) [V] | 2 | App Customization Tool, SPI flash boot [V] | Public | VQFN-56 7×7 | DJ 99 | Mouser 1382 @ $8.70 | **NRND** [V] | Rejected (no EPR) |
| Infineon CCG7D/7S/7SC/7DC (CYPD7xxx) | No — car-charger, ≤21.5 V out [V] | No (charger) | 1–2 + integrated buck-boost | EZ-PD Configurator | Public | QFN-40/68 | 7271-T: 44, others ~0 | Verical ~1k | Active | Rejected |
| VIA Labs VL108 | **All ports EPR to 48 V** [V] | DP Alt Mode v2.0 [V] | **3** (1 charging UFP + 2 DRP DFP) [V] | VIA firmware in SPI flash (shared with VLI hub) [V]; NDA [I] | Not public | QFN-60 7×7 / QFN-48 6×6 [V] | 0 ("no longer mfd" stub) | None authorized | Active (USB-IF TID 9064) | Functionally ideal, **not sourceable/open** |
| Richtek RT1716 | No — PD 3.0 TCPC, ≤100 W [V] | MCU-side | 1 (TCPC only) | Needs a full stack on an MCU | Public | WLCSP-8 | 2247 | — | Active | TCPC only |
| Richtek RT1719 | No — PD 3.0 sink [V] | No | 1 | I2C | Public | WQFN-20 | 0 | Mouser 1494 | Active | Rejected |
| ST STUSB4761 | No — PD 3.0 AC/DC **source**, VDD ≤22 V [V] | No | 1 | NVM | Public | QFN-16 | 0 | Arrow 15k, 99 wk LT | Active | Rejected |
| Weltrend WT66xx | WT6636F PD 3.0 source (charger); EPR parts exist (WT6686B/6690B) for chargers [I] | Dongle parts only [I] | 1 | Mask/OTP, factory programmed | Mostly NDA | — | 0 | — | — | Rejected |
| Open stack on STM32G0/G4 UCPD | UCPD HW is EPR-capable [V]; **Chromium EC: EPR sink only — no EPR source states** in `usb_pe_drp_sm.c` [V]; ST USBPD lib closed, no DP UFP | Chromium EC has `usb_pd_alt_mode_ufp.c` + DFP DP [V] | 1–2 per MCU | Fully open (EC) but large | — | — | STM32G0B1 295 | — | — | Possible but EPR source + UFP_D + certification work from scratch → **not for rev A** |

## Recommendation

```
 Laptop C (a) ── CC/VBUS ── PMG1-S3 port 0 (EPR src 28 V, UFP_D) ──I2C(private)── buck-boost setpoint
                 SS/SBU ─── TUSB1064 (UFP_D crosspoint, I2C from PMG1)
 Down C   (b) ── CC/VBUS ── PMG1-S3 port 1 (5 V src, DFP_D)
                 SS/SBU ─── TUSB1046-DCI (DFP_D crosspoint, I2C from PMG1)
 PD-in C  (c) ── TPS26750 (EPR sink ≤48 V) + EEPROM + TPD4S480
 RP2350 ── I2C (monitor/request only) ── PMG1-S3 (I2C slave, our command set), TPS26750 (I2C target)
```

1. **Ports (a)+(b): one Infineon PMG1-S3 dual-port, CYPM1322-97BZXI** (or 2× CYPM1311 QFN-48 if the BGA is
   unwanted — then SBU/AUX switching is done by the TUSB parts, and HPD/Attention relay goes over GPIO/I2C).
   - Only sourceable, publicly documented, Active part found that does **EPR source + DP Alt UFP_D** on the same port.
   - Start from Infineon's public `mtb-example-pmg1s3-usbc-dock` (EPR 140 W source on port 0, source on port 1,
     DP alt mode, MP4247/RT6190 buck-boost drivers, signed FW update, billboard). DP passthrough
     (port 1 sink HPD → port 0 Attention/Status) is our application code on top of PdAltMode [I].
   - SOP' discovery / 5 A cable check: in PdStack (standard for EPR source) [I — confirm config flag].
2. **Port (c): TI TPS26750** (as planned). Datasheet: EPR 28/36/48 V sink, boots from ROM + I2C EEPROM [V].
3. **Correction to odock-10.md:** **TUSB1046-DCI is a *DFP_D* (source-side) redriver** [V] → use it on the
   **downstream** port; the laptop port needs **TUSB1064** (UFP_D sink-side, pin C/D/E) [V].
   JLC: TUSB1064IRNQT 53, TUSB1064RNQT 20; Mouser 242 @ $10.04 [S].

### Safety model (power safety independent of RP2350 firmware)
- PMG1-S3 owns: PDO list (hard-capped in its firmware to what the input stage can deliver, max 28 V),
  provider NFET gate driver, hardware VBUS OVP/UVP/OCP/SCP/RCP comparators [V], and the **buck-boost setpoint
  on its private I2C/feedback** — RP2350 has no electrical path to the buck-boost control.
- RP2350 talks to PMG1 over a narrow I2C command set (status, "set budget ≤ X W"); PMG1 validates and clamps.
- **Reflash gating:** PMG1 flash ships blank, JLC does not pre-program [V, jlcpcb.md] → RP2350 flashes it over
  SWD on first boot (CAT2/PSoC 4 HSSP programming via external MCU, public AN84858 [I]). To stop user firmware
  re-flashing later: PMG1 XRES driven only by POR + a physical button (not an RP2350 GPIO), and PMG1 firmware
  repurposes its SWD pins after boot, so SWD acquire is only possible on blank silicon or with the button held [I —
  verify acquire-window behaviour on CAT2]. Same idea for TPS26750: EEPROM WP held by hardware, released by button.
- Billboard: required when alt mode fails; PMG1-S3 has USB FS device (needs a hub port) or RP2350 emulates it [I].

### External parts (ports a/b)
- 2× back-to-back NFET pairs (common-drain on source path [V]) per port; 5 mΩ VBUS sense resistor per port [V];
  VBUS TVS (≥30 V working for EPR), CC/SBU ESD (TPD4S480-class on all EPR ports; TPD4S480 2881 at JLC [S]).
- TUSB1064 (a), TUSB1046-DCI (b); SPI flash for PMG1 dual-image FW update optional (reference uses one).
- Buck-boost with I2C setpoint or feedback-injection DAC controlled by PMG1 — reference drivers exist only for
  MP4247/RT6190 (≤36 V in); our 9–48 V input needs an LM5177x-class part + new driver [I].

## Risks
- **Closed PdStack library** (Cypress EULA, Cypress-hardware-only): firmware app is open, but the PD stack binary
  is fetched by ModusToolbox, not committed. Acceptable under requirements ("blobs allowed, not committed") [I].
- Dock-UFP_D + DFP_D passthrough on PMG1 is application work; reference dock routes DP to a hub/MST, not to a
  second Type-C port [I]. Plan bring-up time; Infineon PMG1-S3 dock kit useful for prototyping.
- 97-BGA fanout on 6–8 L; JLC handles ≥0.35 mm pitch [V, jlcpcb.md]. QFN-48 ×2 fallback avoids it.
- JLC stock of CYPM1322 is only 50 → consign from Mouser (8095 in stock).
- USB-IF certification not planned; e-marker/EPR-entry interoperability with MacBook Pro M4 Max must be tested.
- VL108 is the cleaner single-chip answer (covers a+b+c incl. 48 V sink) if VIA ever sells it openly — watch.

## Sources
- PMG1-S3 datasheet: https://www.infineon.com/assets/row/public/documents/24/49/infineon-cypm13xx-ez-pd-pmg1-s3-power-delivery-mcu-gen1-datasheet-en.pdf
- PMG1-S3 dock example: https://github.com/Infineon/mtb-example-pmg1s3-usbc-dock · PdStack: https://github.com/Infineon/pdstack · PdAltMode: https://github.com/Infineon/pdaltmode
- CCG8 datasheet: https://www.infineon.com/assets/row/public/documents/24/49/infineon-ez-pd-tm-ccg8-usb-type-c-port-controller-datasheet-en.pdf · Host SDK: https://www.infineon.com/design-resources/development-tools/sdk/usb-controllers-sdk/ez-pd-host-software-development-kit
- CCG7: https://www.infineon.com/part/CYPD7291-68LDXS
- TPS26750: https://www.ti.com/lit/ds/symlink/tps26750.pdf · TPS65994AE: https://www.ti.com/lit/ds/symlink/tps65994ae.pdf · TPS65994AD: https://www.ti.com/lit/ds/symlink/tps65994ad.pdf · TPS65988: https://www.ti.com/lit/ds/symlink/tps65988.pdf (status: ti.com/product pages, NRND)
- TPS66994 access threads: https://e2e.ti.com/support/power-management-group/power-management/f/power-management-forum/1674812/tps65000-technical-data-for-tps66993-tps66994-tps66994e · https://e2e.ti.com/support/power-management-group/power-management/f/power-management-forum/1438307/tps65994ae-ask-request-to-access-tps66994-secure-resource
- TUSB1064: https://www.ti.com/lit/ds/symlink/tusb1064.pdf · TUSB1046-DCI: https://www.ti.com/lit/ds/symlink/tusb1046-dci.pdf
- VL108: https://www.via-labs.com/product_show.php?id=117
- RT1716: https://www.mouser.com/datasheet/2/1458/DS1716_04-3104891.pdf · RT1719: https://www.richtek.com/Home/Products/USB%20PD%20IF/USB%20Type-C%20and%20Power%20Delivery/RT1719
- STUSB4761: https://www.farnell.com/datasheets/3212211.pdf
- Chromium EC PE: https://chromium.googlesource.com/chromiumos/platform/ec/+/refs/heads/main/common/usbc/usb_pe_drp_sm.c
