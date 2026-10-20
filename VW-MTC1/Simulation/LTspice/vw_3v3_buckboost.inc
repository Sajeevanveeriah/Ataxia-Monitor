* vw_3v3_buckboost.inc - VW-MTC1 3.3 V rail, U4 = LTC3536EMSE buck-boost
* Shared by SIM01 (converter checks) and SIM03 (power path / USB unplug).
*
* Pins : vin  - VSYS input (pin 7 VIN, RT, SHDN tied here)
*        out  - +3V3 rail
*        mode - MODE/SYNC pin (0 = PWM, high = Burst Mode)
*        ofilt- +3V3 viewed through a 20 MHz single-pole bandwidth limit
*               (buffered, no load on the rail); this is what a scope with
*               20 MHz BW limit would show and removes the ESL switching
*               spikes that ideal switch edges create in the model.
* Values (proposed design):
*   L1  4.7 uH Coilcraft XFL4020-472, Rser 24 mohm
*   C28 CIN 22 uF ceramic modelled as 10 uF effective (DC bias), 3 mohm, 0.5 nH
*   C29 100 nF
*   C30,C31 COUT 2 x 22 uF X5R 0805 each modelled as 10 uF effective at 3.3 V
*           DC bias, Rser 3 mohm, Lser 0.5 nH  (ASSUMPTION - derating estimate)
*   R30 1 Meg / R31 221 k feedback -> 3.315 V
*   C32 CFF / R32 RFF feed-forward across R30 (default 47 pF / 6.49 k)
*   C33 CC  / R33 RC  FB-to-VC compensation (default 220 pF / 49.9 k)
*   RT and /SHDN tied to VIN -> 1.2 MHz, always enabled.
.subckt vw_3v3_bb vin out mode ofilt params: CC=220p RC=49.9k CFF=47p RFF=6.49k
C28   vin 0 10u Rser=3m Lser=0.5n
C29   vin 0 100n Rser=10m
XU4   vin 0 mode sw1 sw2 out vin vin fb vc 0 LTC3536
L1    sw1 sw2 4.7u Rser=24m
C30   out 0 10u Rser=3m Lser=0.5n
C31   out 0 10u Rser=3m Lser=0.5n
R30   out fb 1Meg
C32   out fb {CFF} Rser={RFF}
R31   fb 0 221k
C33   fb vc {CC} Rser={RC}
* 20 MHz measurement filter (not part of the board)
Ebw   ob 0 out 0 1
Rbw   ob ofilt 1k
Cbw   ofilt 0 7.958p
.ends vw_3v3_bb
