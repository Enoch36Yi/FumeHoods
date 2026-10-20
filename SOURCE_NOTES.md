# Source notes

The root KiCad files are the original in-hood project, renamed from PCB_FUMEHOODS to SashSense_node1 for this repository. The schematic, board and project settings are byte-identical to the original local files. Fresh checks after the rename gave ERC 0, parity 0, 10 DRC findings and 9 unconnected items; exported net connectivity also matched the original exactly.

The original folder has no project Git repository. Its .history directory contains one KiCad automatic PCB snapshot (dffdc29, 2026-09-02) with no remote. That snapshot and all original local files remain untouched. The repository history retains the earlier filenames.

SashSense_node2 contains selected source and review files from SashSense_Reconstruction. Firefly_pcb2 is a new presence-board reconstruction, not recovery of the lost original board. Its native CAD files are unchanged from the supplied design. In a separate working copy, ERC, native DRC/parity/unrouted checks, and 186 schematic / 527 board / 25 artifact checks were rerun successfully. A stricter scratch copy records the 24 footprint-filter metadata parity issues separately.

Selected project-local libraries, builders, engineering review docs, schematic/layer PDFs, a few previews and verification reports are included. Original vendor PDF downloads, internal handoff notes, drafts, local preferences, large STEP exports and manufacturing archives are excluded. The output verification report refers to the complete local manufacturing review package; the export script recreates those files on demand. The netlist XML's absolute source pathname was replaced with the schematic filename; electrical content was preserved and rechecked.

The user confirmed authorship/authorization for private sharing of this engineering work and requested both board revisions here. No new license has been added. Neither board is released for fabrication.
