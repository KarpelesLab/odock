# odock — Requirements

Open USB4 (40 Gbps) deck, designed to be fabricated **and fully assembled** by JLCPCB,
usable as a bare PCB straight out of the box.

## Goals

- **Upstream:** USB-C, USB4 40 Gbps (TB3/TB4 host compatible), PD source to host up to **140 W (PD 3.1 EPR, 28 V × 5 A)**, 100 W SPR fallback.
- **Downstream:**
  - 1× USB-C USB4/TB (daisy chain, DP alt mode monitor — "USB display")
  - 1× HDMI (target HDMI 2.1 / 4K120 via DP→HDMI PCON; 4K60 minimum) — 40G version; odock-10 uses DP alt mode on the downstream USB-C only
  - 2× USB-A 10 Gbps
  - SD (UHS-I min, UHS-II stretch) + microSD
  - 2.5GbE RJ45
- **Power:** both modes
  - Bus-powered: runs from host with reduced features / downstream power budget
  - PD-in USB-C (EPR sink, up to 240 W chargers): full features + pass-through charging of host
  - DC barrel jack (5.5×2.5 mm high-current, accept 9–24 V, up to ~200 W at 24 V, overvoltage + reverse polarity
    protected): full features; host charging limited by PSU capability (12 V ≈ 60 W total)
  - Input priority: PD-in > barrel > bus power (ideal-diode / power-mux OR-ing, no back-feeding)
  - MCU-managed dynamic power budget: laptop contract renegotiated as input capability and downstream load change
  - Power path: 9–48 V in → buck-boost (LM5176/LM5177 class, external FETs) → 5–28 V PD source
- **Status display** (small SPI IPS LCD, MCU-driven; replaces most status LEDs — size TBD):
  - Negotiated link speed per port (USB2 / 5G / 10G / 20G / 40G)
  - LAN link speed (from RTL8156 LED pins) and activity
  - Display output: mode / lanes / resolution where readable
  - PD: input source + W available, contract with host (V × A), downstream port power, bus-powered mode
  - Mounting: panel on ~1 mm+ double-sided foam tape (or perimeter foam gasket) on the board surface; FPC tail
    bent back and soldered to pads or plugged into a connector. Area under the panel: copper/silk only if full-pad
    tape, or low-profile parts inside a perimeter gasket. Confirm JLC can apply tape + mount panel.
  - Keep a minimal LED or two (power / fault) for when the display is off or firmware is broken
  - Optional: MCU as USB device on the hub so a host-side app can push extra info
- **System MCU: RP2350B** (QFN-80, 48 GPIO; JLC C42415655 in stock) + QSPI flash
  - Drives the LCD, collects status (I2C/SMBus to PD controllers & hub, LED pins of PHY/card reader)
  - USB device on an internal hub port: UF2 drag-and-drop firmware updates through the deck itself,
    optional host-side status app, can reflash other on-board SPI flashes
  - **RP2350 flashes every other programmable component** (PD controllers, config EEPROMs, hub config);
    its firmware bundles their images so a single UF2 updates the whole deck.
  - PD controllers still boot autonomously from their own flash/EEPROM at runtime; hardware backstops
    (independent VBUS OVP, power-good gating) protect the laptop regardless of any firmware.
  - **User GPIO expansion (optional, unpopulated by default or low-profile):** 2.54 mm header with spare
    GPIOs (incl. ADC-capable pins, PIO-friendly), 3V3 / 5V / GND, series resistors + ESD; Qwiic/STEMMA QT
    (JST-SH 4-pin) I2C connector; SWD pads; BOOTSEL + reset buttons
- **Form factor:** compact, target ~100×60 mm, bare-PCB friendly (no sharp/live parts
  exposed on the bottom, thermal solution that works without an enclosure).
- **Silkscreen:** looks good — port/LED legend, back-side spec & pinout art.

## Constraints

- All parts orderable through JLCPCB assembly (LCSC stock or Global Sourcing).
- Works on arrival: any chip firmware must be pre-programmed by JLC, ROM-based, or
  self-flashable on first boot without extra tools.
- **Openness:** schematic, layout, and MCU firmware fully open. Vendor firmware blobs
  allowed but not committed if license forbids; no NDA content in the repo.
- Tooling: KiCad 9+, JLC impedance-controlled stackup (6–8 layers expected).

## Roadmap
1. **odock-10** — USB 3.2 10 Gbps + DP alt mode, all JLC-assemblable (see `odock-10.md`). Current focus.
2. 20G / 40G — USB4 core, once a chip + firmware can be sourced. Not started.

User GPIO header ships unpopulated. Display: 2.0" 320×240 IPS.

## Phases (per board)

0. Chip selection — availability, package/pitch, datasheet access, firmware story
1. Block diagram, power budget, stackup, board outline & connector placement
2. Schematic
3. Layout
4. MCU firmware (PD policy, status LEDs)
5. Prototype order (2–5 assembled) & bring-up
6. Rev B
