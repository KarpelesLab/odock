# odock-10 — Floorplan (placement regions)

Board **130 × 89 mm** (grown from 85 on 2026-10-03 so the 31 mm-deep SD socket fits), origin (top-left) at (100, 50) mm.
**Back edge = top (y = 50)**, front edge = bottom (y = 139).
Mounting holes H1 (104,54), H2 (226,54), H3 (104,135), H4 (226,135): keep ≥ 4 mm clear.
Regions apply to both sides (small passives may go on the bottom under their block). Placement is code:
`hardware/odock-10/layout/<block>.py`, applied with `tools/apply_layout.py`.

```
 x: 100          138                  180                       230
 y=50 ┌───────────┬────────────────────┬──────────────────────────┐  BACK EDGE
      │ power     │ usbc               │ right: ethernet          │
      │ (input +  │ PD + muxes + both  │ RJ45, RTL8156BG          │
      │  laptop   │ data USB-C conns   │                          │
  y=80│  power)   ├────────────────────┤                          │
      │ buck-boost│ hubrails           ├──────────────────────────┤
      │           │ USB7206C + rails   │ right: MCU + display/UI  │
 y=108├───────────┴────────────────────┤ RP2350, LCD (on foam),   │
      │  (gap y 108–112: shared)       │ header                   │
 y=112├───────────┬────────────────────┤                          │
      │ front:    │ front:             │ µSD │ buttons, Qwiic     │
      │ card rdr  │ USB-A ×2           │(front block)             │
 y=139└───────────┴────────────────────┴──────────────────────────┘  FRONT EDGE
```

| Block script | Sheets | Region (x0,y0)–(x1,y1) | Extra refs |
|---|---|---|---|
| `power.py` | Power input, Laptop power out | (100,50)–(138,108) | U1201 C1201 TH1201 TP1201 |
| `usbc.py` | USB-C muxes & DP, PD controller | (138,50)–(180,80) | U1204 C1204 U1205 C1205 TP1204 TP1205 |
| `hubrails.py` | USB hub, Rails | (138,80)–(180,108) | U1202 C1202 U1203 C1203 TH1202 TP1202 TP1203 |
| `front.py` | Card reader (100–138), USB-A ports (138–180), **J902 µSD at the front edge x≈182–198** | (100,112)–(180,139) + (180,124)–(198,139) | — |
| `right.py` | Ethernet (y 50–80), MCU + Display & UI (y 80–139), minus the µSD corner (180,124)–(198,139) | (180,50)–(230,139) | U1206–U1208 C1206–C1208 (TP1206/TP1208 reassigned, see below) |

Edge connectors (x = centre, approximate): back — J102 barrel 108, J101 PD-in 124, J501 laptop 150, J502 downstream 168,
J801 RJ45 212; front — J901 SD 116, J701 150, J702 168, **J902 µSD ≈190**, SW1101/SW1102/J1102 Qwiic in x 199–222.

Inter-block signal exits: usbc → hubrails (USB 10G up/downstream, USB2) at y≈80; hubrails → front (USB-A,
card reader 10G/5G) at y≈108; hubrails → right (Ethernet 10G at x≈180 upper, RP2350 USB2 lower); power → hubrails
(VIN to the 5 V buck) at x≈138; power ↔ usbc (VBUS_LAPTOP to J501) along y 50–65; usbc ↔ right/hubrails: PMG1
I²C/SWD to RP2350.
Thermal: keep the LM51770 power stage (power) and the LM5148 power stage (hubrails) ≥ 15 mm apart; nothing hot under the LCD.
