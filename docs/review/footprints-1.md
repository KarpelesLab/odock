# Footprint review 1/2 — entries [1]–[27] (odock-10)

Scope: the custom footprints in `hardware/lib/odock.pretty` listed as [1]–[27] in the footprint inventory
(the other half is in `footprints-2.md`). For each one I compared pad count, pad numbers against the symbol pin
numbers (`hardware/lib/odock.kicad_sym`), pitch, pad size, row spacing, EP size and paste, drills, pin‑1
orientation and courtyard with the manufacturer drawing. All 27 files load in pcbnew and
`kicad-cli fp upgrade` runs on them cleanly. Every symbol pin number has a pad, and the only pads without a
symbol pin are unnumbered paste apertures and NPTH holes.

**One problem affects the whole set:** every EasyEDA import had its courtyard drawn as the body outline,
leaving pads outside it (25/27 failed). All courtyards now cover pads + body + 0.25 mm (0.5 mm for the RJ45).
Large exposed pads that had 100 % paste now use segmented apertures.

**No footprint reassignments are needed.** Every part matches its footprint after the fixes below, including
the parts that share a footprint.

| # | Footprint | Part(s) | Status | Notes / reference |
|---|---|---|---|---|
| 1 | BGA-97_L6.0-W6.0-P0.50-TL_CYPD8225-97BZXIT | CYPM1321-97BZXI (U401) | **OK** | Infineon PMG1-S3 DS 002-31288 Rev *K, Fig.14 (BZ97A, PG-VFBGA-97): this is a non-uniform grid (outer ring 11×11 @0.50, inner 5×5 @0.65, ring‑to‑inner 0.70, D1 5.00). All 97 ball positions match, A1 is top-left, and all 97 ball names match the Fig.8 ballmap and the symbol. Pads are 0.24 mm NSMD for a 0.30 mm ball. The "CYPD8225" in the name is cosmetic. |
| 2 | CAP-SMD_BD10.0-L10.3-W10.3-LS10.8-FD | RVT 100µ/80V (C122, C123) | **FIXED** | The pads were 4.5×1.65 at ±4.5, so a terminal (C=11.1, P=4.5) barely landed on its pad and the pads stuck out of the courtyard. Replaced with KiCad `CP_Elec_10x10.5` (pads 4.4×2.5, gap 4.0), which matches the KNSCHA RVT spec "Recommended land" for Ø10 (X 2.5, Y 4.0, a 4.0). Pad 1 = + (chamfered side), which matches symbol pin 1 = VIN. |
| 3 | CONN-SMD_4P-P1.00_SM04B-SRSS-TB-LF-SN | QWIIC (J1102) | **FIXED** (courtyard) | Pads match JST SH SM04B-SRSS-TB and KiCad `JST_SH_SM04B-SRSS-TB` (0.6×1.55 @1.0, MP 1.2×1.8 at ±2.8, 3.875 row offset; this one uses 3.88). Converted from the legacy `module` format. |
| 4 | DC-IN_PJ-063BH | PJ-063BH (J102) | **FIXED** (pads, courtyard) | The reported pad spacing mismatch is not a real error. The Same Sky DS (10/20/2022) gives distances **from the panel edge**: hole 3.0, MS 5.0, pin 2 6.0, pin 1 12.0. Relative to the Ø1.6 hole that is 2.0 / 3.0 / 9.0, which is exactly what the footprint has. Slot sizes are correct (pin 1 3.0×1.0, pin 2 2.3×1.0, MS 1.0×2.5, 9.0 apart). Pads enlarged to give ≥0.4 mm annular ring (8 A), the silk was trimmed, and the courtyard now reaches the front edge. |
| 5 | DFN-8_L5.9-W5.2-P1.27-LS6.2-BL | BSC0901NS (Q303) | **FIXED** | Regenerated to the Infineon PG-TDSON-8 "recommended board pads & apertures" (BSC040N08NS5 DS Rev 2.1 Fig.3): S/G pads 0.5×0.925 at y 2.863, drain pins 0.6×0.8, drain pad 4.41 wide reaching 4.455 from the pin tips, and the 2×2 paste split (1.6×1.5). The old source/drain gap was 1.03 mm instead of 1.27 and the pads were undersized. EP = pad 9 (the symbol has 9 pins). |
| 6 | HTSSOP-38_L9.7-W4.4-P0.50-LS6.4-BL-EP | LM51770 (U201) | **FIXED** | TI DCP0038A (LM51770 DS SNVSCL2A p.63-65): pads 1.5×0.3 on 5.8 mm rows (the old ones were 1.715 long on 5.72), EP 4.7×2.9 with a 1:1 paste opening per the 0.125 mm stencil table. Pin 1 is bottom-left and the symbol pins 1–39 match. |
| 7 | IND-SMD_L11.3-W10.0_XAL1010-332ME | XAL1010-103MED (L201) | **OK** | Coilcraft XAL1010 Doc 804: land 2.38 wide on 6.65 centres, length B = 8.91 for -103. The footprint has 2.4 × 9.0 on 6.66, so it suits -103 even though the name says -332. The courtyard was already OK. Nothing changed. |
| 8 | IND-SMD_L13.45-W12.6 | MWSA1206S-4R7MT (L301) | **FIXED** | Sunlord MWSA-S spec Table 4-1: I=3.25, J=8.0 gap, H=5.5. The old pads (3.0×6.0, gap 9.0) overlapped the 2.0 mm terminals by only about 0.2 mm. New pads 3.25×5.5 at ±5.625, courtyard fixed. |
| 9 | IND-SMD_L2.0-W1.6_AOTA-B201610S3R3-101-T | AOTA-B201610S3R3 (L1001) | **FIXED** (courtyard) | The pads match the Abracon recommended land (1.0×1.6, gap 1.0). Converted from the legacy format. If the RP2350 EMI guidance on winding direction matters, orient the polarity dot during layout. |
| 10 | IND-SMD_L5.4-W5.2 | MWSA0503S-1R5/-2R2 (L302, L303) | **FIXED** (courtyard) | The pads already match Sunlord Table 4-1 (I 1.9, J 2.2, H 2.5) for both parts. |
| 11 | KEY-SMD_SKRTLAE010 | SKRTLAE010 (SW1101/2) | **FIXED** | Alps SKRT land dimensions: the pad positions and sizes were correct. The two Ø0.9 guide-boss holes were *plated* holes with zero annular ring; they are now NPTH. Added the body/button fab outline, the "no copper" area between pads 4/5 (Dwgs.User) and a courtyard covering the button. Converted from the legacy format. |
| 12 | LCD_FPC_Solder_12P_P0.50mm | HS20HS072RX (U1101) | **FIXED** (reworked) | Hansheng HS20HS072RX drawing p.10: 12 contacts @0.5, 3.5 mm exposed, tail 6.5 wide, 5 mm stiffener on the back. The contacts are on the panel's front side, so the tail has to be folded 180° under the panel (stated in the descr). With the panel-exit edge at +Y, pin 1 is at −X. The lands are now 0.3×4.75 and run 1.25 mm past the tail end so a hot-bar or iron can reach the joint. Added the tail/stiffener outline on F.Fab and silk alignment ticks, plus the LCSC property. The pin map matches the symbol (1 GND … 12 GND). **Check the fold direction against the mechanical stack-up.** This is a ZIF-style stiffened tail: the soldered joint is behind a 0.2–0.3 mm stiffener, so use hot-bar or pre-tin the lands. A 12P 0.5 mm FPC connector would be the safer choice. **Outcome (2026-10-02): REPLACED.** Following a project-lead decision, the panel now plugs into J1103 Hirose FH34SRJ-12S-0.5SH (C424659). That part is dual contact, 1.0 mm high, takes 0.3 mm FPC, and sits under the panel 14.5 mm inside the tail edge. Its footprint `FFC-SMD_12P-P0.50_FH34SRJ-12S-0.5SH` was corrected to the Hirose pattern: pads 0.3×0.8, tabs 0.4×0.8, E/F 7.1/7.9, 3.3 overall, and a new courtyard. The fold maps panel pin n to J pin 13−n, and the schematic is wired that way. U1101 is DNP and uses the pad-less `LCD_HS20HS072RX_Outline`. This footprint was deleted. See display_ui.md. |
| 13 | MSOP-10_L3.0-W3.0-P0.50-LS5.0-BL | INA226 (U204, U303) | **FIXED** (courtyard) | TI DGS0010A example land is 1.45×0.3 on 4.4. The footprint has 1.62×0.28 on 4.22 with the same outer edge, which is acceptable. |
| 14 | PG-TDSON-8_L5.0-W6.0-P1.27-BL-EP | BSC026N08NS5 (Q104–Q107) | **FIXED** | Same Infineon TDSON-8 land as #5 (BSC026N08NS5 DS Rev 2.3 outline PG-TDSON-8-U08 matches). The EP is numbered 8, as the symbol has 8 pins. |
| 15 | PG-TDSON-8_L5.2-W5.9-P1.27-LS6.2-BL-EP | BSC0805LS (Q201, Q202, Q302) | **FIXED** | Same land as #5. EP = pad 9 (symbol pin "EP"). |
| 16 | PG-TDSON-8_L5.9-W5.1-P1.27-LS6.2-BL | BSC040N08NS5 (Q213, Q214) | **FIXED** | Same land as #5 (this is the datasheet the Infineon land comes from). EP = pad 8. |
| 17 | PG-TSDSON-8_L3.3-W3.3-P0.65-BL-1 | BSZ070N08LS5 (Q301) | **FIXED** | PG-TSDSON-8 FL per BSZ070N08LS5 DS Rev 2.2 Fig.1 (F1 3.90, F2 2.29, F3 0.31, F6 1.00, F7 2.51, F8 1.64): fused 1.64 mm source bar for pins 1–3, separate gate, drain pad with pin fingers, 0.39 S–D gap (it was 0.54) and reduced paste. EP = pad 8. |
| 18 | QFN-32_L4.0-W4.0-P0.40-BL-EP2.8 | TPS26750 (U102) | **FIXED** | TI RSM0032B (TPS26750 DS p.65-67): pads 0.55×0.2 on 3.85 (they were 0.7 long on 4.1), EP 2.8 with 4×1.23 paste (77 %, it was 100 %). Pin 1 is at the left end of the bottom row, with CCW numbering as before. |
| 19 | QFN-48_L7.0-W7.0-P0.50-BL-EP5.1 | GL3224 (U901) | **FIXED** | Genesys GL3224 DS Fig.7.1 (EP 5.1–5.3, b 0.25, L 0.4): lands 0.27×0.8 on 6.8, EP 5.1 with 3×3 paste (~66 %, it was 100 % on 26 mm²). The pinout (Fig.3.1, pin 1 bottom-left, CCW) matches the symbol. |
| 20 | QFN-56_L6.0-W6.0-P0.35--TL-EP4.7 | RTL8156BG (U801) | **FIXED** | Realtek RTL8156BG(S) DS Rev 1.1 §10: EP J=K **4.5 nom (max 4.6)**, b 0.18, L 0.4. The EP copper was 4.7, larger than the package's maximum EP. It is now 4.5 with 2×2 paste (57 %); the file name still says EP4.7. The lands went from 0.15 to 0.2 wide (0.15 gap). Four netless (unnumbered) plated vias in the EP were removed; add GND thermal vias in the paste channels during layout. The pin ring is a 90° rotation of the DS top view (no mirror) and the names match the symbol. |
| 21 | QFN-80_L10.0-W10.0-P0.40-TL-EP3.4 | RP2350B (U1001) | **FIXED** | RP2350 DS Fig.146: pad rows 9.013 / 10.573 (pads 0.78 long, they were 0.665), EP 3.40 with 2×2 1.4 mm paste. Pin 1 is at the top of the left side. Spot-checked the symbol against the DS pin table (GPIO0 = 77, XIN = 30, RUN = 35, GPIO15 = 14). |
| 22 | RJ45-TH_DGUK211Q340CD2A4D2 | Usakro 2.5G magjack (J801) | **FIXED — pin numbering was wrong** | Usakro drawing A0 sheet 1, "Recommended PCB layout viewed from component side". The hole geometry was right but **every pad number was reversed** (signal n ↔ 11−n, LED n ↔ 25−n), which made the footprint a mirrored image of the jack. Pin 1 now sits rightmost in the inner row (nearer the LEDs), with green LED 13/14 on the left and yellow 11/12 on the right, as in the front view. The Ø3.2 posts were plated with zero annular ring and are now NPTH. Shield pads 15/16 (Ø1.7) are kept. Pin functions (sheet 3) match the symbol. |
| 23 | SD-SMD_DM3AT-SF-PEJM5 | Hirose DM3AT (J902) | **FIXED** (courtyard) | Hirose DM3 catalogue p.3 recommended pattern: all 14 pads match (P 1.1, 0.7×1.2, CD-switch pads at 3.7 / 9.9, shell pads at 14.05 / 14.5). SW_B = pad 9 and SW_A = pad 11, as in the drawing. **Layout:** keep traces out of the hatched areas in the drawing (under the switch and card-detect spring). |
| 24 | SD-SMD_SD-111 | Hanbo SD-111 (J901) | **FIXED** | Hanbo SD-111 drawing: contact/WP/CD x positions and sizes match. The peg holes were plated 1.7 with no ring; they are now **NPTH Ø1.50** (pegs are Ø1.35). The drawing puts the side tab pads at hole ±2.75/2.85, 1.4×2.2, while EasyEDA had them about 0.9 mm further in. The pads were widened (2.2/2.1 × 2.2) to cover both positions. Silk trimmed, and the courtyard now includes the body. |
| 25 | SMC_L6.9-W5.9-LS7.9-BI | SMCJ48CA (D102) | **FIXED** | MDD SMCJ DS "Suggested pad layout": pads 4.1×4.3 on 7.9 centres (12.0 overall); the old pads were 3.03×3.82. No polarity marking (bidirectional). |
| 26 | SMC_L6.9-W5.9-LS7.9-RD | SMCJ51A (D101) | **FIXED** | Same land as #25. Pad 1 = cathode band, which matches symbol 1 = C. |
| 27 | SOIC-8_L4.9-W3.9-P1.27-LS6.0-BL | AT24C512C (U103) | **FIXED** (courtyard) | Standard JEDEC SOIC-8: 0.59×1.8 on 5.2, pin 1 bottom-left. Within normal IPC range. |

## Datasheets used
- Infineon CYPM13xx PMG1-S3 DS 002-31288 Rev *K (infineon.com, fileId 8ac78c8c7ddc01d7017ddd0263aa58f3)
- LCSC C5246576 (KNSCHA RVT), C160404 (JST SH), C3095900 (Same Sky PJ-063BH), C152424 / C5955453 / C534374 /
  C534333 / C534678 (Infineon BSC0901NS, BSC026N08NS5, BSC0805LS, BSC040N08NS5, BSZ070N08LS5), C42411119
  (Abracon AOTA), C110293 (Alps SKRT), C5329582 (Hansheng HS20HS072RX), C49851 (TI INA226), C157358 (GL3224),
  C41376388 (RTL8156BG), C42415655 (RP2350), C19725134 (Usakro RJ45), C114218 (Hirose DM3), C410353 (Hanbo
  SD-111), C408370/C408371 (MDD SMCJ), C12371 (Microchip AT24C512C)
- TI LM51770 SNVSCL2A, TI TPS26750 (ti.com/lit/ds/symlink), Coilcraft XAL1010 Doc 804, Sunlord MWSA-S series spec
  (Digi-Key mirror)

## Notes for layout
- The regenerated footprints keep the original EasyEDA 3D model reference and pin‑1 location; #2 uses the KiCad
  stock model. #12 has no 3D model.
- `FL_001.kicad_mod` (committed in f6b48b1, not in either review list) is in the legacy `module` format and stops kicad-cli from
  loading the whole `odock.pretty` library (`fp export svg` fails with "Unable to load library"). Whoever
  imported it should run `kicad-cli fp upgrade`.
