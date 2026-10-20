# Firefly_pcb2 PCB layout and verification (P2)

2026-10-20. Status: placed and fully routed native KiCad 10.0.5 board, 160 x 60 mm; digitally verified. **Not released for fabrication**: mounting, sensor apertures, host interface and the beeper part lifecycle remain open (see *Release blockers*).

## Files

| File | Content |
|---|---|
| `Firefly_pcb2.kicad_pcb` | Placed, routed and zone-filled board (fill saved by the final native DRC run) |
| `Firefly_pcb2.kicad_sch`, `.kicad_pro` | Circuit unchanged from the schematic stage; the title-block note now reads 160 x 60 mm |
| `libraries/SashSense.pretty/Fiducial_1mm_Mask2mm.kicad_mod` | Added local copy of the KiCad fiducial; all other footprints unchanged |
| `scripts/layout_pcb.py` | Explicit placement and every route; regenerates the board (`--overwrite`) |
| `scripts/verify_pcb.py`, `scripts/verify_outputs.py` | Independent board and exported-file checks |
| `scripts/make_pcb_outputs.ps1` | Re-runs ERC, DRC, all checks, previews and the manufacturing review package |
| `scripts/render_copper.py` | Per-layer copper review images |
| `reports/drc.json`, `drc.rpt`, `pcb_verification.json`, `output_verification.json`, `board_stats.txt` | Results quoted below |
| `outputs/previews/` | KiCad 3D top render and per-layer copper views |
| `outputs/Firefly_pcb2_board_layers.pdf` | Vector plot of every fabricated layer |
| `outputs/manufacturing_P2_PROVISIONAL/` | Gerbers, drill, CPL, BOM, assembly drawing, IPC-D-356, STEP; see its README |

The board was placed and routed from the exported schematic netlist. It was first laid out inside a provisional 500 x 500 mm outline; the outline was then trimmed to the populated area, without changing placement or routing, and every check below was re-run.

## Board

- Outline: a **160 x 60 mm** Edge.Cuts rectangle, from (30, 25) to (190, 85) mm, set by `OUTLINE_MM` in `scripts/cad_common.py`.
- Two copper layers, 1.6 mm nominal. GND pours on both layers 2 mm inside the edge, tied by 191 stitching vias.
- Four provisional M3 supports (3.2 mm NPTH), 5 mm in from each corner, each with a 4 mm-radius copper keepout. Three global fiducials. All are board-only items, outside the BOM and CPL.
- All 29 purchased parts and all pads are on the top side.

### Placement

| Part | Centre (mm) | Notes |
|---|---|---|
| U1 ESP32-S3-WROOM-1-N8 | (80.0, 38.5) | Antenna end 0.75 mm inside the top edge; manufacturer 48 x 21 mm keepout (15 mm beyond the module) respected on both layers |
| U2 VL53L1X | (140.0, 52.0), 180 deg | 61.5 mm from U1 |
| U3 AMG8833 | (172.0, 55.0), 180 deg | Lens centre (170.0, 55.0); 93.5 mm from U1, 120 mm from the beeper |
| BZ1 / Q1 beeper | (52.0, 62.0) / (61.5, 58.5) | South-west of the module |
| J1 3.3 V solder pads | (44.0, 34.0) | Pin 1 +3V3 (square), pin 2 GND; silk "+" / "GND" |
| J2 service pads | pin 1 at (93.0, 45.9) | 1 GND, 2 RX(in), 3 TX(out), 4 EN, 5 BOOT, 6 3V3 on silk |

Sensor positions, aperture locations and orientation are provisional; both sensors face +Z with nothing taller than the 0603 parts near their fields of view.

### Routing

Signals 0.2 mm (0.25 mm for EN/BOOT/BEEP), +3V3 0.8 mm from J1 to the module and 0.3-0.5 mm to the sensors, vias 0.6/0.3 mm. The I2C bus is a daisy chain module -> ToF -> AMG with test points on every sensor line. Pull-ups sit where +3V3 is reachable without crossings: R5 at the AMG, R6/R3 at the ToF, R7 at the AMG, R2 at J2.

The fixed GPIO order puts UART and interrupt lines between the bus pins, and the VL53L1X SDA/SCL order is the mirror image of the module's. Six short bottom-layer crossings are therefore used; everything else is on the top layer and the bottom remains a near-solid ground plane:

| Net | Bottom length | Why |
|---|---:|---|
| UART_RX, UART_TX | 9.4, 10.7 mm | Leave the module between the bus and interrupt lines; land directly on J2's plated pads |
| EN | 2.8 mm | Passes under BEEP_PWM so EN can reach J2 |
| I2C_SDA | 3.3 mm | ToF tap under SCL (mirror-image pin order) |
| TOF_INT | 6.2 mm | Reaches its pull-up R4 under TOF_XSHUT |
| AMG_INT | 2.4 mm | Crosses under the ToF +3V3 feed |

### Manufacturer-required circuits (checked on the board)

- AMG8833 pin 10 -> C10 1 uF -> R8 20 ohm -> GND in that series order; pin 12 -> C11 1.5 uF -> GND. Neither node touches +3V3. Pad distances 2.6 mm (C10, C11) and 1.5 mm (R8-C10).
- AMG VDD C9 100 nF at 3.1 mm and C8 10 uF at 5.6 mm; VPP tied to VDD; AD_SELECT to GND.
- VL53L1X C7 4.7 uF at AVDDVCSEL (pin 11, 2.6 mm) and C6 100 nF at AVDD (pin 1, 2.7 mm); the duplicated pin-1 land is kept.
- Module C3 100 nF (2.3 mm) and C2 10 uF (4.7 mm) at the 3V3 pin, C4/C5 47 uF at J1, EN RC R1/C1.
- No copper on U2 pin 8 (DNC), U3 pins 1/7/8/11/14 (NC) or any of the 27 unused module pins.

## Verification of the saved artifacts

| Check | Result |
|---|---|
| Native ERC, all severities | 0 errors, 0 warnings |
| `verify_schematic.py` | 186/186 pass (unchanged netlist) |
| Native DRC with `--schematic-parity --refill-zones --save-board`, all severities | **0 violations, 0 unconnected items, 0 parity issues** |
| Exact native unrouted count | **0** (DRC report); pcbnew connectivity independently also 0 |
| `verify_pcb.py` | 527/527 pass: outline, footprint/UUID/value/footprint parity, 153 pad-to-net comparisons, NC isolation, bypass topology and distances, antenna keepout, supports, via-in-pad, zone fills, track/via sizes |
| `verify_outputs.py` | 23/23 pass: Gerber outline and coordinates, job file, drill hits vs board holes, CPL positions/refs, BOM coverage, IPC-D-356, STEP, PDFs, previews |

KiCad's project defaults ignore five DRC checks (no courtyard, track not centred on via, tuning geometry, footprint filters, footprint type). No finding-specific exclusions exist. A scratch copy with those five set to *error* also gave 0 DRC violations; its parity section then lists 24 footprint-filter metadata mismatches, explained below.

## Schematic review findings (no circuit edits were made)

1. **Footprint-filter metadata.** `build_project.py` renames symbols by text replacement, which also rewrote the resistor/capacitor filters to `Device_R_*` / `Device_C_*`; the J1/J2 filters name connector libraries rather than the local library. Effect is limited to footprint-assignment filtering; fix the renaming in `build_project.py` before regenerating the schematic.
2. **Beeper lifecycle.** DigiKey lists PKLCS1212E4001-R1 as "Last Time Buy"; other distributors disagree. Confirm with Murata or choose a current part and re-audit its land pattern and drive before release.
3. **Supply entry.** J1 has no reverse-polarity, TVS or fuse protection, by design (regulated 3.3 V only). Decide on protection once the supply harness is known.
4. **Bulk capacitance.** The 47 uF 6.3 V X5R 1206 parts lose a substantial share of capacitance at 3.3 V DC bias; confirm the effective value from Murata data.
5. Programming is UART-only through J2 (USB D+/D- unused); use a 3.3 V adapter.
6. The module footprint's 12 thermal-via pads are 0.2 mm drills; confirm the fabricator's minimum.

The GPIO map, pull-ups, 100 kHz starting bus speed, sensor addresses and bypass values match the electrical review in `sensor_and_beeper_review.md`.

## Engineering limits

- I2C: routed SDA 116 mm, SCL 103 mm; trace capacitance roughly 5-14 pF (0.5-1.2 pF/cm assumption) before device and test-point loading. With 4.7 kohm and about 50 pF total, the RC rise time estimate is about 0.2 us. Measure on hardware.
- Thermal: the AMG8833 is 93.5 mm from the module, but continuous ground copper conducts heat between them; self-heating must be measured.
- RF: antenna keepout is clear on both layers; enclosure, supports and cables near the antenna are unknown.
- Size: the outline follows the existing placement. A smaller board would need parts re-placed; moving the AMG8833 closer to the module reduces its thermal separation.
- Digital checks do not establish mechanical fit, optics, thermal accuracy, RF performance, assembly yield or hardware function.

## Before fabrication

1. Beeper: confirmed availability of PKLCS1212E4001-R1, or an approved replacement.
2. Mechanics: support/mounting pattern, board thickness, enclosure, and sensor aperture or window positions (ToF 27 deg and AMG 60 deg fields of view).
3. Process: copper weight, finish and a fabricator DFM review.
4. Interface: the actual 3.3 V source and harness for J1/J2, which decides input protection.

## Reproduction

From the `SashSense_node2` directory in PowerShell (KiCad 10 at `C:\Program Files\KiCad\10.0`, or set `KICAD_ROOT`):

```powershell
& 'C:\Program Files\KiCad\10.0\bin\python.exe' scripts\layout_pcb.py --overwrite   # only to regenerate the board; replaces manual edits
powershell -ExecutionPolicy Bypass -File scripts\make_pcb_outputs.ps1           # ERC, DRC+refill, all checks, previews, outputs
```
