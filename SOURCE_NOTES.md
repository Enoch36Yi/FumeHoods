# Source notes

The in-hood KiCad project was renamed from `PCB_FUMEHOODS` to `SashSense_node1`. Its distance sensor was later changed from VL53L0X to the pin-compatible VL53L1X, and its rule-check findings were fixed (SCL and +5V moved off the board edge, ground pour joined with GND vias, C5 rotated, silkscreen corrected). The repository history retains the earlier files.

The original local folder also contains a KiCad automatic PCB snapshot dated 2026-09-02. That snapshot is kept separately.

`SashSense_node2` is a new reconstruction of the presence board, not a recovered copy of the lost original. It includes project-local libraries, generation and verification scripts, engineering notes, PDFs and selected previews.

Vendor PDFs, internal notes, drafts, large STEP exports and manufacturing archives are not included. The electrical review links to manufacturer datasheets. The export script generates the manufacturing review files locally; the saved output-verification report covers that complete local package.

Neither board is released for fabrication. No license has been added.
