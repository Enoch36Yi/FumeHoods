# SashSense

SashSense monitors fume hood sash position and whether someone is working at the hood. It is designed to beep when a user walks away and leaves the sash open. The wider project is working toward deployment across 191 UW fume hoods, supported by a UW STF Green Building Award.

I selected sensors, tested breadboard circuits, designed PCBs and built earlier ESP32 prototypes, coordinating team member contributions. AI assistance was used in automation of moving repository to GITHUB, and making the REPO more readable.

The in-hood node measures sash opening and temperature/humidity. The presence node uses VL53L1X and an AMG8833 thermopile array; it builds on SEAL's Firefly human-presence project.

## Open the designs

Use KiCad 10. Keep each project, board and schematic together, and preserve the node 2 library folders and library tables.

| Board | Project | Schematic | PCB |
| --- | --- | --- | --- |
| Node 1 | [KiCad project](SashSense_node1.kicad_pro) | [Schematic](SashSense_node1.kicad_sch) | [Board](SashSense_node1.kicad_pcb) |
| Node 2 | [KiCad project](SashSense_node2/Firefly_pcb2.kicad_pro) | [Schematic](SashSense_node2/Firefly_pcb2.kicad_sch) | [Board](SashSense_node2/Firefly_pcb2.kicad_pcb) |

Node 1 uses ESP32-WROOM-32E, SHT31, USB-C, CP2102N, AMS1117-3.3 and VL53L1X. Node 2 is a new reconstruction of the presence board, not a recovered original. It uses ESP32-S3-WROOM-1-N8, VL53L1X, AMG8833 and a transistor-driven piezo beeper.

[Node 2 BOM](SashSense_node2/outputs/BOM.csv) · [Node 2 details](SashSense_node2/README.md)

## Status and unfinished work

Neither revision is released for fabrication. Previously saved KiCad 10.0.5 checks reported zero ERC errors/warnings, unconnected items and configured schematic/PCB parity issues on both boards. Node 1 had one configured DRC finding: its ESP32 footprint differs from KiCad's library copy (0.3 mm instead of 0.2 mm thermal vias), kept on purpose. Node 2 had zero configured DRC findings, but a stricter check reported 24 footprint-filter metadata mismatches. These are historical results, not new validation.

Node 2's 160 × 60 mm outline was trimmed from a provisional 500 × 500 mm outline without changing component placement/routing. Sensor positions and mounting holes remain provisional. Its beeper is externally mounted; mounting, optical openings, a regulated 3.3 V harness and fabricator DFM review remain open. Hardware performance has not been established by these CAD checks.

## Repository contents

Editable boards, schematics, project settings, required node 2 symbols/footprints/library tables and the supplied node 2 BOM are retained. CAD generators, intermediate manifests, rendered exports and old check reports were removed from the current tree. Earlier files and engineering notes remain recoverable in Git history. Board, schematic, project and library content was not changed by this cleanup. No license has been added.
