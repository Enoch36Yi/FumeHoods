# SashSense

SashSense monitors fume hood sash position and whether someone is working at the hood. It beeps when a user walks away and leaves the sash open. We are working toward deployment on 191 UW fume hoods, supported by a UW STF Green Building Award.

I lead the project at UW's Sensors, Energy, and Automation Laboratory (SEAL). I selected the sensors, tested the circuits on a breadboard, and designed and built the two ESP32-based PCBs. I also set technical direction and coordinated the team's work.

The current system has two nodes:

- Inside the hood: VL53L1X for sash opening and SHT31 for temperature and humidity.
- Presence detection: VL53L1X and an AMG8833 thermopile array.

## The board here

This repository contains an earlier in-hood board: the KiCad project, schematic, layout, and an exported schematic PDF. The presence-board CAD and firmware are not included.

[Open the schematic PDF](PCB_FUMEHOODS.pdf)

![In-hood PCB layout](PCB_FUMEHOODS-board.svg)

| Function | Parts in this revision |
| --- | --- |
| Controller | ESP32-WROOM-32E |
| Sensors | VL53L0CXV0DH1 and SHT31-DIS |
| USB and power | USB-C, CP2102N USB-to-UART, AMS1117-3.3 |
| External input and controls | Two-pin reed-switch connection, reset and boot buttons |

This revision labels the distance sensor as VL53L0X-family and uses a `ST_VL53L1x` footprint. The current system specifies VL53L1X. That difference needs to be reconciled before ordering this board.

## Open and check it

Use KiCad 10 with its standard libraries. Open `PCB_FUMEHOODS.kicad_pro`, then the schematic or PCB editor.

```sh
mkdir review
kicad-cli sch erc --output review/erc.rpt PCB_FUMEHOODS.kicad_sch
kicad-cli pcb drc --schematic-parity --output review/drc.rpt PCB_FUMEHOODS.kicad_pcb
```

KiCad CLI 10.0.5 reported:

- ERC: 0 errors and 0 warnings.
- PCB/schematic parity: 0 issues.
- DRC: 7 copper-to-edge clearance errors and 3 warnings.
- Connectivity: 9 unconnected items involving the ground zone.

The reports (`erc.rpt`, `drc.rpt`, `parity.rpt`) include the configured exclusions. The remaining work is to resolve the edge clearances and zone connectivity, review the ESP32 footprint mismatch and silkscreen warnings, and confirm the sensor part/footprint. This revision has not passed fabrication or bench acceptance.

Original CAD files are unchanged. `SHA256SUMS.txt` records their hashes; `SOURCE_NOTES.md` records where they came from. This is a private repository for controlled sharing.
