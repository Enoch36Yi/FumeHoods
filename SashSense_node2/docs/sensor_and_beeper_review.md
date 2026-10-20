# Firefly_pcb2 electrical and package review

2026-10-19. Schematic-stage review; no hardware test or final layout approval.

## Sources

- [ST VL53L1X DS12385 Rev 8, August 2024](https://www.st.com/resource/en/datasheet/vl53l1x.pdf): pinout p5, application p6, electrical limits, package/land drawings pp23-25. The review used Rev 8; the link points to ST's datasheet.
- [Panasonic AMG88xx ADI8000C66, 10-Feb-2023](https://industrial.panasonic.com/cdbs/www-data/pdf/ADI8000/ADI8000C66.pdf): rating/performance pp1-2, package and lands p3, external circuit p4. Official PDF, I2C specification and precautions are retained under `sources/sensor_audit`.
- [Espressif ESP32-S3-WROOM-1/1U datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf) and [current documentation entry](https://documentation.espressif.com/esp32-s3-wroom-1_wroom-1u_datasheet_en.html): module pin definition, recommended supply, EN and antenna layout. Installed KiCad 10 symbol pin names were checked for every used GPIO. A complete RF/module layout review remains necessary after routing.
- [onsemi MMBT3904L datasheet](https://www.onsemi.com/pdf/datasheet/mmbt3904lt1-d.pdf), pin/package diagram: SOT-23 pin 1 base, 2 emitter, 3 collector.
- [Murata P37E official archived catalog](https://www.murata.com/-/media/webrenewal/support/faqs/products/sound/sounder/char/sc0002/p37e.ashx?la=en), printed pp20 and 22 (PDF pages 22 and 24): PKLCS1212E package/lands and external-drive circuit guidance. Local copy `sources/Murata_P37E_official.pdf`. This is an old catalog, not a current lifecycle guarantee. [Current sounder lineup](https://www.murata.com/en-global/products/sound/sounder/overview/lineup/pkmcs) displays a discontinuation notice. Confirm the exact beeper's procurement status or select a verified current replacement before layout release.

## Supply and local bus

J1 is a new labelled solder-wire input: pin 1 regulated +3.3 V, pin 2 GND. It is not an existing host mating pinout. Use 3.3 V +/-5% with at least 1 A transient capability and short leads. There is no 5 V input, regulator, reverse-polarity protection or hot-plug qualification. ESP32-S3, AMG8833 and VL53L1X are powered from this common rail. The selected operating-voltage overlap is 3.0-3.5 V; verify transient overshoot, ground bounce and regulator tolerance at the assembled devices.

R5/R6 are the single shared 4.7 kohm I2C pull-up pair. Initial bus speed is 100 kHz. The estimate tr = 0.8473*Rp*Cb gives approximately 398 ns at 100 pF and 796 ns at 200 pF; a 300 ns target corresponds to about 75 pF, while 1 us corresponds to about 251 pF. These are RC estimates, not measured compliance. Select the final target from both manufacturers' timing specifications and actual layout/cable capacitance. No external I2C cable is designed; test pads are service access only.

## ST bare VL53L1X

U2: pins 1/11 +3V3; 2/3/4/6/12 GND; 5 XSHUT; 7 GPIO1 open-drain interrupt; 8 DNC left electrically unconnected; 9 SDA; 10 SCL. R3/R4 are 10 kohm pull-ups for XSHUT and interrupt. C6=100 nF and C7=4.7 uF are the local bypass pair. Configure the driver's 2V8 I/O mode for the 3.3 V interface. Default 7-bit address is 0x29; ST's 0x52 is the 8-bit write address.

The project-local footprint is the installed KiCad `ST_VL53L1x`, checked against drawing Figures 18-20. Body 4.90 x 2.50 x 1.56 mm. Normal lands 0.50 x 0.50 mm at 0.80 mm pitch; pin 1 has an intentional extended shape formed from two same-number pads. Pin 1 is upper-left in front-side PCB top view, pin 5 upper-right, 6 right-middle, 7 lower-right, 11 lower-left, 12 left-middle. DNC8 is the lower row next to GPIO1/SDA. The drawing's 4.9 mm package length takes precedence over the inconsistent 4.4 mm entry in the datasheet overview table.

Keep both emitter/receiver optical paths open along +Z. Typical full FoV 27 degrees, adjustable ROI. Final aperture, cover-glass material, spacing, optical isolation and crosstalk calibration remain mechanical/optical design tasks. Do not reuse the old enclosure aperture dimensions as verified geometry. Offset calibration and any cover-window calibration require hardware.

## Panasonic bare AMG8833

U3 is the 3.3 V high-gain 14-pin bare package, not a breakout. Pins 2 SDA, 3 SCL, 4 open-drain INT, 5 AD_SELECT to GND, 6 GND, 9 VDD, 13 VPP tied to VDD. Pins 1/7/8/11/14 remain electrically unconnected. AD_SELECT low gives 7-bit 0x68; high gives 0x69. R7=10 kohm interrupt pull-up. C8=10 uF plus C9=100 nF decouple VDD.

Internal bypass connections are important: pin 10 AVDD-PC -> C10=1 uF +/-10% -> R8=20 ohm -> GND; pin 12 DVDD-PC -> C11=1.5 uF +/-10% -> GND. Neither internal bypass pin is tied directly to +3V3. Manufacturer schematic and PCB land drawing were visually inspected.

The custom local footprint and `AMG8833_manifest.json` use body 11.6 x 8.0 mm, height 4.3 mm, optical lens center (+2.0, 0) relative to package center. In top view with +y downward, pin 1 is bottom-left, 7 bottom-right, 8 top-right, 14 top-left. Five inner lands use 1.27 mm pitch at x=-2.54, -1.27, 0, 1.27, 2.54; corners x=+/-5.5. Normal rows y=+/-3.05 with 2.6 mm long lands; inner widths 0.7 mm, corner widths 0.8 mm. Pin 1 is 3.6 mm long, centered y=+2.55. The asymmetry is intentional.

The AMG8833 high-gain operating ambient/object range is 0-80 C. Typical FoV 60 degrees; allow stabilization after power-up. Keep its field of view unobstructed and separate it from MCU, beeper and supply heating. Ordinary visible-transparent glass/acrylic are not automatically suitable thermal-IR windows. Final geometry and installed thermal performance remain unverified.

## Beeper

BZ1 is a passive external-drive Murata PKLCS1212E4001-R1 piezo, not an active DC buzzer or a magnetic coil. The copied KiCad footprint has pad centers x=+/-5.6 mm, y=0, size 1.2 x 4.0 mm, matching the 12.4 mm outside/10.0 mm inside land-span drawing. Nominal body 12 x 12 x 3 mm. Verify exact production variant/lifecycle before committing layout.

Q1 MMBT3904LT1G switches the low side. R9=1 kohm base resistor; R10=100 kohm base-emitter pull-down; R11=1 kohm across the piezo restores charge between cycles and bounds the collector's DC load. Start with short 4 kHz PWM beeps; keep the GPIO low/off at reset and idle. Never leave the transistor continuously on as a DC alarm. The base-emitter/collector mapping was checked against onsemi's drawing. Audible loudness, required alarm pattern, installed acoustic port and any additional transient clamp/series damping require review and physical tests. No sound-pressure level is claimed for this implementation.

## CAD checks and hardware limits

Native KiCad 10.0.5 schematic ERC reports 0 errors and 0 warnings. The independent exported-netlist/local-land verifier passes 186 checks, including all intended component/net mappings, required sensor no-connects, local library presence, both sensor land maps and the used module/transistor pins. ERC uses KiCad's existing default check selection; no finding-specific exclusions were added. These checks cannot establish hardware functionality, physical fit, solder-process suitability, optics, thermal accuracy, EMC/RF or integration with SashSense software.


Repository note: vendor PDFs referenced above remain in the original local review folder; use the linked manufacturer sources. They are not bundled in this repository.
