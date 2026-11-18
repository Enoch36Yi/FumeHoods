# Firefly presence board

A new reconstruction of the SashSense presence node: ESP32-S3-WROOM-1-N8, bare VL53L1X, bare AMG8833 and a transistor-driven piezo beeper. The two-layer board is 160 × 60 mm, trimmed to the populated area from an earlier provisional 500 × 500 mm outline. It is routed and digitally checked, but has not been fabricated or tested as hardware.

## Open it

Use KiCad 10.0.5 and open `Firefly_pcb2.kicad_pro`. Symbols and footprints are under `libraries/`, with project-relative library tables. Standard KiCad 3D model libraries are used where available; some components have no 3D body in the render.

The board takes externally regulated 3.3 V at J1. J2 is a set of provisional 3.3 V UART/service pads, not an established mating connector. USB D+/D− are unused. Existing-system host and firmware/backend compatibility still need to be established.

## BOM and status

[BOM](outputs/BOM.csv)

Previously saved checks reported no ERC errors or warnings, configured DRC violations, unconnected items or configured parity issues. A stricter run reported 24 footprint-filter metadata mismatches. These historical checks are not a new validation or fabrication approval.

Beeper sourcing, support pattern, sensor openings, board thickness, power harness and a fabricator DFM review remain open. J1 currently has no reverse-polarity, TVS or fuse protection. RF performance, optical behavior, self-heating, physical fit and assembled operation still require hardware tests.

The current repository keeps the editable design, project-local libraries and BOM. Generator scripts, generated reports and preview exports were removed; they remain in Git history. No design files were altered.
