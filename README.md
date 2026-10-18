# SashSense fume hood sensor hardware

KiCad schematic and PCB layout for a fume hood sensing node developed by Enoch Yi as part of SashSense at the University of Washington Sensors, Energy, and Automation Laboratory (SEAL).

The project addresses instrumentation for fume hood sash monitoring. This repository provides an inspectable electrical design: an ESP32 module, time-of-flight sensor, temperature/humidity sensor, USB interface, power regulation, and a two-pin external connection. It is a hardware design snapshot, with unresolved PCB checks documented below.

## Contributions and scope

Enoch is SashSense project lead. He designed and built two ESP32-based PCBs per hood, selected sensors, tested breadboard circuits, set technical direction, and coordinated team members. He confirmed authorization to share the supplied design files privately. Broader lab funding, deployment, and team activities are project context; this repository does not establish sole authorship of the wider SashSense system.

The current two-board system uses an in-hood ESP32/VL53L1X/SHT31 node and an ESP32/VL53L1X/AMG8833 presence node. An audible reminder beeps when a user walks away from an open hood. The project received a UW STF Green Building Award; deployment to 191 UW fume hoods is in progress. These current-system facts were confirmed by Enoch in his application record. This archive contains only the supplied in-hood schematic/board revision; the presence-board CAD remains undocumented at his direction. Firmware, measured performance, and deployment logs are not included.

## Electrical architecture

| Block | Component in the supplied schematic |
| --- | --- |
| Controller and radio | U1, ESP32-WROOM-32E |
| Time-of-flight sensing | U5, VL53L0CXV0DH1 |
| Temperature and humidity | U2, SHT31-DIS |
| USB interface | J2 USB-C and U4 CP2102N USB-to-UART bridge |
| Power regulation | U3 AMS1117-3.3; +5 V and +3.3 V rails |
| External connection | J1 two-pin connector; PCB annotation identifies reed-switch wiring |
| Service controls | Reset and boot pushbuttons |

The schematic and PCB are the authority for wiring and pin assignments. The resume names a VL53L1X, while this revision's schematic names a VL53L0X-family part with a `ST_VL53L1x` footprint. Reconcile the intended device and package before procurement or fabrication.

## Inspect and reproduce

Use KiCad 10 with its standard symbol and footprint libraries. Verification here used **KiCad CLI 10.0.5**. No Python packages or firmware toolchain are needed to inspect these files.

1. Open `PCB_FUMEHOODS.kicad_pro` in KiCad.
2. Open the schematic and PCB editors to inspect the sources.
3. Reproduce the exported view and checks from the repository directory:

```sh
kicad-cli sch export svg --output review/ PCB_FUMEHOODS.kicad_sch
kicad-cli sch erc --output review/erc.rpt PCB_FUMEHOODS.kicad_sch
kicad-cli pcb drc --output review/drc.rpt PCB_FUMEHOODS.kicad_pcb
```

The SVG below is generated from the supplied schematic, not a conceptual replacement.

[View schematic PDF](PCB_FUMEHOODS.pdf)

![SashSense PCB layout](PCB_FUMEHOODS-board.svg)

![SashSense electrical schematic](PCB_FUMEHOODS.svg)

[Open schematic SVG](PCB_FUMEHOODS.svg)

## Verified results and current status

Checks performed on the copied, unmodified source files:

| Check | Observed result |
| --- | --- |
| Schematic export | Successful SVG export |
| Electrical rules check | 0 reported errors and 0 warnings under the project's configured checks |
| PCB design rules check | 10 violations: 7 copper-to-edge clearance errors and 3 warnings |
| Schematic/PCB parity | 0 reported parity issues using `--schematic-parity` |
| PCB connectivity | 9 reported unconnected items involving the GND zone |
| Footprint errors section | 0 reported footprint errors |

See `erc.rpt`, `drc.rpt`, and `parity.rpt` for exact findings and ignored checks. The DRC warnings concern an ESP32 footprint/library mismatch, undersized silkscreen text, and a silkscreen overlap. A successful CLI exit alone does not mean a board passed DRC.

This revision is **not ready to describe as fabrication-validated**. Resolve the edge clearances, investigate zone connectivity after checking/refilling zones, review the footprint discrepancy and sensor identity, and rerun the checks before fabrication. The source files were not modified to suppress findings.

No bench test, accuracy, energy-saving, production, or completed deployment result was verified from this package. An ERC pass is a software rule check, not proof of electrical or physical performance.

## File inventory

- `PCB_FUMEHOODS.kicad_pro`: project settings and configured design rules.
- `PCB_FUMEHOODS.kicad_sch`: editable electrical schematic.
- `PCB_FUMEHOODS.kicad_pcb`: editable board layout.
- `PCB_FUMEHOODS.svg`: generated schematic view.
- `erc.rpt`, `drc.rpt`: recorded KiCad checks, including exclusions.
- `SOURCE_NOTES.md`: provenance, review scope, and exclusions.
- `SHA256SUMS.txt`: hashes of the three source files.

## Sharing and ownership

This repository is intended for controlled private sharing. Reviewers need explicit repository access. No license is granted by this repository; no open-source license has been added to lab-associated work.


