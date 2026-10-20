# Future first-article bring-up

This revision has not been fabricated or tested as hardware. Complete the layout review before assembly and use this checklist for the first assembled board.

Board access (P2 layout): TP1 +3V3, TP2 GND, TP3 SDA, TP4 SCL, TP5 TOF_XSHUT, TP6 TOF_INT, TP7 AMG_INT, TP8 BEEP_PWM. J1: pin 1 (square, "+") regulated 3.3 V, pin 2 GND. J2 (pin 1 square): 1 GND, 2 RX into the module, 3 TX out of the module, 4 EN, 5 BOOT, 6 +3V3. SW1 RESET, SW2 BOOT.

1. Inspect component orientation, soldering, optics and the isolated AMG internal bypass nodes. Check rail-to-ground resistance and that unused/DNC sensor pins remain unconnected. Confirm the 3.3 V input polarity and actual service-pad order.
2. Power from a current-limited regulated 3.3 V source. Check voltage and overshoot directly at all three devices during startup and Wi-Fi bursts. Input current limit must accommodate the module's transients without repeated brownout. Never apply 5 V to J1/J2 supply pads.
3. Check EN rise/reset behavior and BOOT pull-up/button operation. Use 3.3 V UART logic and common ground; TX/RX must cross to the programmer. Avoid powering the rail from both programmer and bench supply without an approved power-sharing arrangement.
4. Flash the board using the exact ESP32-S3-WROOM-1-N8 configuration and new GPIO map. Scan at 100 kHz, expecting 7-bit addresses 0x29 and 0x68. A scan is insufficient: initialize with the proper sensor drivers, read identification/status, detect timeouts and exercise shutdown/interrupt behavior.
5. Select VL53L1X 2V8 I/O mode. Verify ToF distances and range-status reporting against targets across the sash's actual travel. Calibrate offset; validate any final cover window and crosstalk settings.
6. Let AMG8833 stabilize; inspect its 8x8 frame and temperature response with a known scene. Confirm orientation and rejection of board/self heating. The high-gain part's operating range is 0-80 C.
7. Measure SDA/SCL rise time, low voltage and ringing with the actual routed board and any connected cable. Adjust pull-ups/speed from measured capacitance and the devices' timing limits.
8. Test short 4 kHz beeps, boot-time silence and PWM stop behavior. Verify sound level in the enclosure; leave the piezo driver off at idle and avoid sustained DC.
9. Verify mounted-board support, optical openings, acoustic opening, cable strain relief and radio performance. Finally exercise real SashSense telemetry end to end using its actual backend contract, including invalid/stale/offline states.
