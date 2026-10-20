# Firefly presence board

A new reconstruction of the SashSense presence node: ESP32-S3-WROOM-1-N8, bare VL53L1X, bare AMG8833 and a transistor-driven piezo beeper. The two-layer board has a provisional 500 × 500 mm outline. It is routed and digitally checked, but has not been fabricated or tested as hardware.

## Open it

Use KiCad 10.0.5 and open `Firefly_pcb2.kicad_pro`. Symbols and footprints are under `libraries/`, with project-relative library tables. Standard KiCad 3D model libraries are used where available; some components have no 3D body in the render.

The board takes externally regulated 3.3 V at J1. J2 is a set of provisional 3.3 V UART/service pads, not an established mating connector. USB D+/D− are unused. Existing-system host and firmware/backend compatibility still need to be established.

## Reproduce the checks

Run from this directory. KiCad's Python interpreter provides `pcbnew`; ordinary Python does not include it.

```powershell
$kc = 'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe'
$kp = 'C:\Program Files\KiCad\10.0\bin\python.exe'
& $kc sch export netlist --format kicadxml --output reports/netlist.xml Firefly_pcb2.kicad_sch
& $kc sch erc --severity-all --format json --output reports/erc.json Firefly_pcb2.kicad_sch
& $kp scripts/verify_schematic.py
& $kc pcb drc --schematic-parity --refill-zones --severity-all --format json --output reports/drc.json Firefly_pcb2.kicad_pcb
& $kp scripts/verify_pcb.py
```

`make_pcb_outputs.ps1` runs the larger pipeline, including renders, Gerbers, drill files, BOM/CPL and the output checks. The manufacturing review files are generated on demand under `outputs/manufacturing_P2_PROVISIONAL`; they are not committed here. The saved 25-check output report was rerun against the complete local artifact package before publication.

```powershell
.\scripts\make_pcb_outputs.ps1
```

To regenerate the routed board, export the netlist first, then use `& $kp scripts/layout_pcb.py --overwrite`. That replaces manual layout edits. The older schematic generator, `build_project.py`, also recreates a draft board and has a known footprint-filter metadata bug; do not run it just to open or check this revision.

## Results and release blockers

The saved CAD passed ERC (0 errors/warnings), configured DRC (0), configured parity (0), and unrouted count (0). The independent checks passed 186/186 for the schematic and 527/527 for the board. A stricter scratch project with five ignored categories enabled still had 0 DRC violations, but reported 24 footprint-filter metadata parity mismatches. See `reports/drc_strict.json` and the layout review.

Beeper sourcing, support pattern, sensor openings, board thickness, power harness and large-board fabrication/assembly acceptance remain open. J1 currently has no reverse-polarity, TVS or fuse protection. RF performance, optical behavior, self-heating, physical fit and assembled operation still require hardware tests.

`docs/pcb_layout_review.md` records placement and routing decisions; `docs/bringup_checklist.md` is the future hardware checklist. Vendor datasheets and earlier drafts remain in the original local project folder. The schematic-stage snapshot and original local files were not changed.
