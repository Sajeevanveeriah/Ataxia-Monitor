* vw_hall_afe.inc - VW-MTC1 Hall channel analogue front end (1 of 4)
* Shared by the SIM04 netlists.
*
* hall_lpf : R50 1 Meg pull-down at the input (defined level if the sensor
*            cable is unplugged), then a unity-gain Sallen-Key low-pass:
*            R51 = R52 = 10 k, C51 (feedback, R51/R52 junction to output)
*            = 100 nF, C52 (+input to GND) = 47 nF.
*            Expected fc = 1/(2*pi*10k*sqrt(100n*47n)) = 232 Hz, Q = 0.73.
*            Pins: in out vdd
*
* U6 = MCP6004 (one quarter). No Microchip model is installed, so the
* LTspice UniversalOpAmp2 'level2' model is configured to MCP6004 class
* headline specs (ASSUMPTION - generic model):
*   GBW 1 MHz, slew 0.6 V/us, Avol 112 dB (4e5), output to within 25 mV of
*   the rails (Rail=25m), output current limit 15 mA (approx. at 3.3 V),
*   rail-to-rail input (the level2 model has no input common-mode limit).
*   level2 pins: In+ In- V+ V- OUT
.lib UniversalOpAmp2.lib
.subckt hall_lpf in out vdd
R50  in 0 1Meg
R51  in n1 10k
R52  n1 n2 10k
C51  n1 out 100n
C52  n2 0 47n
XU6  n2 out vdd 0 out level2 Avol=4e5 GBW=1Meg Slew=0.6Meg Ilimit=15m Rail=25m Vos=0
.ends hall_lpf
