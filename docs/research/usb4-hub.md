# USB4 core chip options (researched 2026-10-02)

V = verified (source in agent report / URLs below), I = inferred.

| Chip | Provides | Fits odock? | Package | Docs / FW | PD | Availability |
|---|---|---|---|---|---|---|
| VIA Labs VL830/VL832 | 1× USB4 **upstream only** (endpoint device), 4× USB 10G + USB2, 1× DP 1.4a out; no PCIe, no TB3 compat (V) | **No** — no USB4 downstream, no PCIe | 10×10 FCCSP-328, 0.5 mm (V) | NDA; signed FW in SPI (fwupd supports updates) | VL105 / VL108 | Not on LCSC (consigned-only JLC entry) |
| **Intel JHL8440** (Goshen Ridge, TB4) | 1 up + 3 down 40G (DP alt), native PCIe Gen3 x1, native USB 10G (V) | **Yes, full topology** | 10.7×10.7 BGA, pitch not public | NDA; Intel-signed FW, licensed vendors only | TPS65988 / TPS65994AD / CYPD5235 in docks | Mouser 0 stock, "shipping restricted", $21/$18 @1/@10; not at DigiKey |
| Intel JHL9440/9480 (Barlow Ridge, TB4/TB5) | 4 ports, PCIe Gen4 x4, DP 2.1 (V) | Yes (overkill) | ~13×13 FC-CSP ~496 balls (I) | NDA, signed | CCG8/PMG1 (Anker) | B1 (S RN80–83) EOL; **B2 current** (JHL9440 S RPNP, JHL9480 S RPNM) per Intel PCN 856970; Mouser JHL9440 1 pc @ $21 |
| **Realtek RTS5490** | 1 up + **2 down USB4 40G**, 2× USB 20G, DP in/out, **integrated PD to 240 W**, internal PCIe switch/xHCI (V); external PCIe lane unknown | **Yes except maybe NIC** (→ RTL8156BG over USB) | BGA511 (I), pitch unknown | NDA (I); signed FW (V) | Integrated | JLC C55343694 (extended, 0 stock) — Global Sourcing target |
| Parade PS9010 | USB4 dock controller, details NDA | Maybe | 8.5×11.5 BGA-274 | NDA | ? | Not found anywhere |
| ASMedia ASM2464PD | USB4/TB → PCIe Gen4 x4 bridge, no DP, no hub | Only as PCIe-centric core | FCCSP-273, 0.46 mm | NDA, but **open RE firmware** (tinygrad/asm2464pd-firmware) | — | JLC C7509569, 0 stock |

LCSC in stock today: TPS65994AD (C2864593), TPS65988DJ (C2863638), RTL8125BG (C3013605),
KTI226V/i226 (C26159200), RTL8156BG (C41376388).

## Key risks
- **Firmware** is the main blocker: every viable chip needs vendor-signed firmware, distributed under NDA.
- Schematic openness: pinouts/reference designs come from NDA docs.
- No distributor stock for any viable core chip.
- No prior open hardware using any USB4 hub chip found.

## Sources
- VL830 https://www.via-labs.com/product_show.php?id=114 · VLI roadmap https://www.via-ic.com/upload/1f/5c05f70ba58e953e605d8fb9739672.pdf
- JHL8440 https://www.intel.com/content/www/us/en/products/sku/189982/intel-jhl8440-thunderbolt-4-controller/specifications.html
- RTS5490 https://dancharblog.wordpress.com/2023/06/05/realtek-rts5490-controller-downstream-port-analysis/ · https://jlcpcb.com/partdetail/RealtekSemicon-RTS5490GR/C55343694
- Surface USB4 dock (RTS5490) teardown https://dancharblog.wordpress.com/2025/02/19/surface-usb4-dock-for-business-teardown-and-review/
- CalDigit TS4 (JHL8440) teardown https://dancharblog.wordpress.com/2022/03/05/caldigit-ts4-teardown/
- Dock list https://dancharblog.wordpress.com/2024/01/01/usb4-tb4-docks/
- Parade PS9010 https://www.paradetech.com/parade-introduces-usb4-dock-controller/
- ASM2464PD open firmware https://github.com/tinygrad/asm2464pd-firmware

## Authorized distributor sweep (2026-10-02)
- Only Intel parts at authorized distis (Mouser; export-flagged). RTS5490, PS9010, ASM2464PD, VL830: no authorized source.
- No other USB4 hub/dock controller found at DigiKey/Mouser.
- Intel PCN 856970: https://cdrdv2-public.intel.com/856970/PCN856970-00.pdf
