# odock-10 — Board outline & placement plan

Provisional (2026-10-02). Outline in KiCad: **130 × 85 mm** (grown from 110 × 75: ~800 parts / ~9,200 mm² of
courtyards didn't fit; small passives also on the bottom side), 3 mm corner radius, 4× M3 mounting holes
(4 mm from corners) for rubber feet / standoffs. May grow after thermal data (see power-budget.md).

## Edge plan (top view)

```
                                BACK EDGE (110 mm)
 ┌────────────────────────────────────────────────────────────────────────────┐
 │ (H1)[DC jack][PD-in C]   [Laptop C][Down C]                 [  RJ45 2.5G ](H2)│
 │  ┌─────────── POWER ZONE ───────────┐  TUSB1064  TUSB1046     RTL8156BG     │
 │  │ LM74720  LM74700  TPS26750       │    PMG1-S3 (BGA)        MAC EEPROM    │
 │  │ LM51770 buck-boost + FETs + L    │                                       │
 │  │ LM5148 5V buck (far from LM51770)│      USB7206C hub                     │
 │  └──────────────────────────────────┘                                       │
 │   RP2350B  flash   [GPIO hdr, unpop]                ┌───────────────────┐   │
 │   GL3224                                             │  2.0" LCD 320×240 │   │
 │                                                      │  on 1 mm foam     │   │
 │                                                      └───────────────────┘   │
 │ (H3)[  SD socket  ][µSD]    [USB-A][USB-A]        [BTN A][BTN B]  [Qwiic](H4)│
 └────────────────────────────────────────────────────────────────────────────┘
                                FRONT EDGE
```

## Rationale
- **Laptop C and downstream C side by side on the back edge:** the DP lanes run TUSB1064 → TUSB1046
  over a few cm instead of across the board; monitor and laptop cables both exit the back.
- **Power zone in the back-left corner**, next to the power inputs and the laptop port (short 5 A paths),
  far from the LCD and the hub. Buck-boost and 5 V buck separated to spread heat.
- **Hub centered**: USB 10G runs of a few cm to USB-A (front), downstream C mux (back), GL3224, RTL8156.
- **Front edge = things users touch:** SD/microSD, USB-A, buttons, Qwiic. LCD on top face toward the
  front-right, readable from the user's side, away from heat sources.
- **Bottom side:** low-profile parts only, flat for bare-board use; back-side silkscreen art + pinout/specs.

## Stackup & rules
- JLC **JLC061611-1080A**: 6L 1.6 mm, 1 oz outer + 1 oz inner, NP-155F (TG155) — order with TG155.
  L1 signal · L2 GND · L3 signal · L4 power · L5 GND · L6 signal. L1–L2 and L5–L6 = 0.069 mm 1080 prepreg.
- Net classes in the KiCad project (geometry **estimated**, verify in JLC impedance calculator before layout):
  - `USB_90` (USB 3.x SS + USB2): 0.10 mm / 0.18 mm gap on L1
  - `HS_85` (USB-C SS, DP main link): 0.10 mm / 0.12 mm gap on L1
  - `PWR`, `PWR_HC` (laptop VBUS 5 A, 5 V 8 A — pours), `HV` (VIN ≤ 48 V, 0.3 mm clearance)
- Board minimums set to JLC 6L: 0.09 mm track/clearance, 0.15 mm drill, 0.25 mm via, 0.3 mm copper-to-edge.

## To verify during placement
- Real footprints/heights for every connector (JAE DX07S024XJ1R1100, Amphenol GSB4111312HR,
  12401610E4#2A, PJ-063BH, USAKRO RJ45, SD-111, DM3AT) and the LCD module outline + FPC tail length.
- PMG1-S3 BGA-97 fanout (pitch) — via-in-pad is free on 6L.
