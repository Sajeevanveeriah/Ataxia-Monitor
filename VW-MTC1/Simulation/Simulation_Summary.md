# VW-MTC1 Simulation Summary

Voltwyn MazeTrack Controller VW-MTC1 - LTspice verification of the proposed analogue and power values.

- Simulator: LTspice 26.1.1 (batch mode, `LTspice.exe -b`). Every number below comes from a .raw or .log file in `LTspice/`, read by the scripts in `tools/` (`ltraw.py` raw parser, `an_sim*.py` analysis). Plots in `Plots/`, machine-readable results in `results.json`.
- Plotting used the Python 3.13 runtime bundled with MechFaber (has numpy/scipy/matplotlib); the system Python 3.14 has numpy and scipy but no matplotlib and nothing was installed.
- Items labelled CALCULATION are hand formulas, not simulations.
- Generated: 2026-10-19 10:56 UTC+1100 (system clock, Australia/Melbourne local time).

## Final component values and changes from the proposal

| Ref | Function | Proposed | Final | Changed? | Evidence |
|---|---|---|---|---|---|
| L1 | LTC3536 inductor | 4.7 uH XFL4020-472 | 4.7 uH XFL4020-472 | no | SIM01 |
| C30, C31 | +3V3 output | 2 x 22 uF X5R 0805 | 2 x 22 uF X5R 0805 | no | SIM01 |
| C28, C29 | LTC3536 input | 22 uF + 100 nF | 22 uF + 100 nF | no | SIM01 |
| R30/R31 | feedback | 1 M / 221 k | 1 M / 221 k | no | SIM01 (3.315 V) |
| C32/R32 | feed-forward | 47 pF + 6.49 k | 47 pF + 6.49 k | no | SIM01b, no ringing |
| C33/R33 | compensation | 220 pF + 49.9 k | 220 pF + 49.9 k | no (no retune needed) | SIM01b |
| R21 (RPROG) | LTC4054 charge current | 2.49 k | 2.49 k | no | SIM02a |
| C20 + R20 | LTC4054 VCC damping | 10 uF + 1.5 ohm in series | 10 uF + 1.5 ohm in series | no | SIM02b |
| D40 | VBUS -> VSYS Schottky | 1N5819 or MBR0520L | 1N5819 class (B5819W, 1 A) | choice | SIM03 (VSYS draws up to ~0.5 A) |
| R43 | Q1 gate / VBUS pull-down | 100 k | **2.2 k** | **YES** | SIM03a/e: with 100 k Q1 never turns on after unplug |
| C42 | VSYS bulk | (none) | **100 uF low-ESR, ESR ~50 mohm (polymer/tantalum)** | **YES (added)** | SIM03c: replug overshoot +6.4 % -> +3.3 % |
| R50-R52, C51, C52 | Hall LPF | 1 M, 10 k, 10 k, 100 nF, 47 nF | unchanged | no | SIM04 |
| RS (series) | touch input | 100 k | **10 k** | **YES** | SIM05 |
| RPU (pull-up) | touch input | 1 M | **360 k** | **YES** | SIM05 |
| CF (node cap) | touch input | 10 nF | **27 nF** | **YES** | SIM05 |
| Q2 duty | ERM PWM 20 kHz | (to choose) | 76 % at VSYS 3.7 V, 55 % at VSYS 4.6 V | chosen | SIM06 |

## Fail list (honest view)

Checks marked FAIL in results.json. Proposed-value fails are followed by a revision that passes, except: (1) SIM02 termination current (macro-model behaviour, no board fix), (2) SIM05 5 ms gap resolution, which no passive value set met within the 10 uA limit (see SIM05). Rows starting rejected_ or replug_C41 are intermediate study cases, not the final design.

- SIM02_charger / termination_current
- SIM05_touch_input / proposed_CC50pF_touch_2ms_pulses
- SIM05_touch_input / proposed_CC50pF_touch_20ms_x2_with_5ms_gap_pulses
- SIM05_touch_input / proposed_CC100pF_false_outputs_idle
- SIM05_touch_input / proposed_CC100pF_touch_2ms_pulses
- SIM05_touch_input / proposed_CC100pF_touch_20ms_x2_with_5ms_gap_pulses
- SIM05_touch_input / proposed_CC100pF_skin_bridge_100k_pulses
- SIM05_touch_input / revised_CC50pF_touch_20ms_x2_with_5ms_gap_pulses
- SIM05_touch_input / revised_CC100pF_touch_20ms_x2_with_5ms_gap_pulses
- SIM03_power_path / proposed_vsys_on_battery_14ms
- SIM03_power_path / proposed_v3v3_max
- SIM03_power_path / proposed_v3v3_replug_window_min_max
- SIM03_power_path / rejected_bat54_attempt_vsys_on_battery_14ms
- SIM03_power_path / rejected_bat54_attempt_v3v3_max
- SIM03_power_path / rejected_bat54_attempt_v3v3_replug_window_min_max
- SIM03_power_path / replug_C41_22_uF
- SIM03_power_path / replug_C41_2_x_22_uF

## SIM00 - MOSFET model fits (vw_models.lib)

AO3401A and AO3400A are not in the LTspice library, so VDMOS fits were written to the headline values in the brief (RDS(on) = Rd + 1/(Kp x Vov)). Capacitances (Ciss ~650-700 pF) are set as parameters but were not separately simulated.

| Check | Simulated | Limit | Result | Note |
|---|---|---|---|---|
| AO3401A_rds_on_vgs_-4.5V | 49.95 mohm | about 50 mohm | PASS |  |
| AO3401A_rds_on_vgs_-2.5V | 69.71 mohm | about 70 mohm | PASS |  |
| AO3401A_vgs_th_250uA | -0.905 V | about -0.9 V | PASS |  |
| AO3400A_rds_on_vgs_4.5V | 30.01 mohm | about 30 mohm | PASS |  |
| AO3400A_rds_on_vgs_2.5V | 45.11 mohm | about 45 mohm | PASS |  |
| AO3400A_vgs_th_250uA | 1.004 V | about 1.0 V | PASS |  |

## SIM01 - 3.3 V buck-boost (U4 LTC3536EMSE)

Files: `sim01a_buckboost_startup.cir`, `sim01b_buckboost_loadstep.cir`, `sim01c_buckboost_ripple_eff.cir`, `sim01d_buckboost_burst.cir`, shared circuit `vw_3v3_buckboost.inc`; schematic `sim01a_buckboost_startup_sch.asc`. Plots: `sim01a_startup.png`, `sim01b_loadstep.png`, `sim01c_ripple_300mA.png`, `sim01c_efficiency.png`, `sim01d_burst_20mA.png`.

| Check | Simulated | Limit | Result | Note |
|---|---|---|---|---|
| startup_vout_final | 3.315 V | 3.315 V nominal +/- 1 % | PASS |  |
| startup_overshoot_switching_avg | 0.015 % | < 3 % | PASS | one-switching-period average of the 20 MHz-limited rail |
| startup_overshoot_peak_20MHz | 0.376 % | < 3 % | PASS | includes switching ripple peak |
| startup_raw_spike_peak | 3.779 V | report (ESL spikes, full bandwidth) | INFO | ideal-switch edges into 0.5 nH ESL; not representative of a scope reading with 20 MHz limit |
| startup_t10_to_t90 | 0.706 ms | report (soft start) | INFO |  |
| startup_time_to_99pct | 0.91 ms | report | INFO |  |
| startup_input_current_peak | 1.919 A | report | INFO | C28 charging during the 20 us LTspice startup source ramp (simulation artefact, not converter inrush) |
| loadstep_vin_3.0V_vmin | 3.197 V | >= 3.13 V | PASS | 20 MHz BW, includes ripple; 1-period average 3.2321 V |
| loadstep_vin_3.0V_vmax | 3.396 V | <= 3.48 V | PASS | 20 MHz BW, includes ripple; 1-period average 3.3915 V |
| loadstep_vin_3.0V_dip_pct | -3.54 % | >= -5 % | PASS |  |
| loadstep_vin_3.0V_overshoot_pct | 2.45 % | <= +5 % | PASS |  |
| loadstep_vin_3.0V_recovery_up | 47.3 us | report (to within +/- 1 %) | INFO |  |
| loadstep_vin_3.0V_recovery_down | 42.4 us | report (to within +/- 1 %) | INFO |  |
| loadstep_vin_3.0V_ringing_extrema | 1 alternating extrema > 3 mV | <= 3 (i.e. no more than ~1.5 cycles) | PASS | up: 1, down: 1 |
| loadstep_vin_3.0V_load_regulation | -0.08 mV | report (50 -> 600 mA DC shift) | INFO |  |
| loadstep_vin_3.7V_vmin | 3.217 V | >= 3.13 V | PASS | 20 MHz BW, includes ripple; 1-period average 3.2515 V |
| loadstep_vin_3.7V_vmax | 3.385 V | <= 3.48 V | PASS | 20 MHz BW, includes ripple; 1-period average 3.3794 V |
| loadstep_vin_3.7V_dip_pct | -2.95 % | >= -5 % | PASS |  |
| loadstep_vin_3.7V_overshoot_pct | 2.12 % | <= +5 % | PASS |  |
| loadstep_vin_3.7V_recovery_up | 27.9 us | report (to within +/- 1 %) | INFO |  |
| loadstep_vin_3.7V_recovery_down | 29 us | report (to within +/- 1 %) | INFO |  |
| loadstep_vin_3.7V_ringing_extrema | 1 alternating extrema > 3 mV | <= 3 (i.e. no more than ~1.5 cycles) | PASS | up: 1, down: 1 |
| loadstep_vin_3.7V_load_regulation | -0.16 mV | report (50 -> 600 mA DC shift) | INFO |  |
| loadstep_vin_4.6V_vmin | 3.222 V | >= 3.13 V | PASS | 20 MHz BW, includes ripple; 1-period average 3.2568 V |
| loadstep_vin_4.6V_vmax | 3.383 V | <= 3.48 V | PASS | 20 MHz BW, includes ripple; 1-period average 3.3778 V |
| loadstep_vin_4.6V_dip_pct | -2.81 % | >= -5 % | PASS |  |
| loadstep_vin_4.6V_overshoot_pct | 2.06 % | <= +5 % | PASS |  |
| loadstep_vin_4.6V_recovery_up | 32.1 us | report (to within +/- 1 %) | INFO |  |
| loadstep_vin_4.6V_recovery_down | 36.4 us | report (to within +/- 1 %) | INFO |  |
| loadstep_vin_4.6V_ringing_extrema | 1 alternating extrema > 3 mV | <= 3 (i.e. no more than ~1.5 cycles) | PASS | up: 1, down: 1 |
| loadstep_vin_4.6V_load_regulation | -0.11 mV | report (50 -> 600 mA DC shift) | INFO |  |
| eff_pwm_vin3p7_50mA | 93.93 % | report | INFO | Pin 0.1765 W, Pout 0.1657 W |
| eff_pwm_vin3p7_300mA | 93.93 % | report | INFO | Pin 1.0587 W, Pout 0.9945 W |
| eff_pwm_vin3p7_600mA | 90.97 % | report | INFO | Pin 2.1862 W, Pout 1.9889 W |
| ripple_pwm_300mA_pp_20MHz | 37.08 mV p-p | report (no limit given; ESP32-S3 tolerates far more) | INFO |  |
| ripple_pwm_300mA_pp_fullBW | 1133 mV p-p | report | INFO | dominated by ideal-switch-edge ESL spikes in the model |
| ripple_pwm_50mA_pp_20MHz | 14.72 mV p-p | report | INFO |  |
| ripple_pwm_600mA_pp_20MHz | 63.85 mV p-p | report | INFO |  |
| burst_20mA_eff | 79.14 % | report | INFO | Pin 0.0826 W, Pout 0.0653 W |
| burst_20mA_ripple_pp_20MHz | 31.18 mV p-p | report | INFO |  |
| burst_20mA_vavg | 3.267 V | within +/- 5 % | PASS |  |

Notes and assumptions:

- COUT: each 22 uF X5R 0805 modelled as 10 uF effective at 3.3 V DC bias, ESR 3 mohm, ESL 0.5 nH (assumption). CIN 22 uF modelled the same way. LTspice raised the capacitor Cpar to 10 pF (log message).
- V(out) at full bandwidth shows large spikes (about 1.1 V p-p at 300 mA) caused by the ideal switch edges of the macro-model driving the 0.5 nH ESL. They are not representative of a real board measured with a 20 MHz scope limit, so all regulation and ripple checks use a buffered 20 MHz single-pole copy of the rail (V(ofilt)). Layout ESL will still produce real high-frequency spikes; keep C30/C31 tight to the IC.
- Ringing check: the one-switching-period average of the rail shows one extremum per step at every VIN, so the loop is well damped and the compensation was not retuned.
- Efficiency comes from the ADI macro-model with L1 DCR only (no core loss, no capacitor ESR loss beyond 3 mohm). The 94 % figure at 50 mA in PWM looks optimistic and has not been checked against the datasheet curves here.
- Burst Mode: the average output in Burst Mode sits lower than in PWM (3.2670 V); that is the Burst Mode hysteresis band, still within +/- 5 %.

## SIM02 - Li-ion charger (U3 LTC4054-4.2) and USB hot-plug

Files: `sim02a_charger_cccv.cir`, `sim02b_usb_hotplug.cir`. Plots: `sim02a_charger_cccv.png`, `sim02b_usb_hotplug.png`.

| Check | Simulated | Limit | Result | Note |
|---|---|---|---|---|
| cc_current | 407.9 mA | 402 mA +/- 7 % (374-430 mA) | PASS | calc 1000 x 1 V / 2.49 k = 401.6 mA |
| trickle_current | 39 mA | report (expected ~C/10 below ~2.9 V; from memory of the datasheet, not re-checked) | INFO |  |
| trickle_to_cc_vbat | 2.942 V | report (expected ~2.9 V; from memory, not re-checked) | INFO |  |
| cv_voltage | 4.217 V | 4.2 V +/- 1 % (4.158-4.242 V) | PASS |  |
| termination_current | 28.8 mA | about 40 mA (C/10 of 402 mA); +/- 25 % (30-50 mA) | FAIL | terminated at t = 7.059 s (scaled time) with V(PROG) = 80.0 mV; the ADI macro-model terminates at V(PROG) ~ 80 mV and its IBAT/IPROG ratio falls to ~895 at low current. Fixed by the IC, not by board values; datasheet C/10 limits not checked here |
| led_current_charging | 1.39 mA | report | INFO |  |
| led_current_after_termination | 20.05 uA | report (CHRG high-Z) | INFO |  |
| hotplug_peak_10uF_ceramic_only | 7.962 V | < 10 V (LTC4054 VCC abs max as recalled, not re-checked against the datasheet) | PASS |  |
| hotplug_peak_10uF_plus_1R5 | 5 V | report | PASS |  |
| hotplug_peak_10uF_1R5_plus_1uF_pin | 6.235 V | report | PASS | board configuration (1 uF at the VCC pin rings with the cable inductance) |

Interpretation of the brief: "VCC through a 1.5 ohm series resistor into 10 uF" was modelled as the LTC4054 datasheet hot-plug recommendation, i.e. 1.5 ohm in series WITH the 10 uF capacitor (an RC snubber at VCC), not a resistor in the supply path. A 1.5 ohm supply-path resistor would drop 0.6 V at 400 mA.

Battery model (scaled): 1.5 F capacitor behind 0.25 ohm internal resistance, starting at 2.85 V, as in the ADI example. Currents and thresholds are real; only the time axis is compressed (about 7 s instead of hours).

Termination: the macro-model ends the charge at V(PROG) = 80 mV, which is 28.8 mA in the cell (the IBAT/IPROG ratio also falls to about 895 at low current). This misses the "about 40 mA" target (C/10 = 40.2 mA). It is set by the IC, not by board values, so no value was changed. The real part should be checked against the datasheet C/10 specification; this simulation cannot settle it.

Hot-plug: (ii) 10 uF + 1.5 ohm damps the ring completely (5.00 V peak). With the 1 uF VCC-pin capacitor added (the real board), the 1 uF rings with the cable inductance to 6.24 V, still below the 10 V VCC abs max as recalled for the LTC4054 (not re-checked against the datasheet). Ceramic DC-bias derating of the 10 uF at 5 V was not modelled.

### Thermal - CALCULATION (not a simulation)

P = (5 V - VBAT) x 0.4 A, Tj = Ta + P x theta-JA.

| VBAT | P (W) | theta-JA (C/W) | Ta (C) | Tj (C) | Thermal regulation (120 C) engages? |
|---|---|---|---|---|---|
| 3.0 V | 0.80 | 80 | 25 | 89.0 | no |
| 3.0 V | 0.80 | 80 | 40 | 104.0 | no |
| 3.0 V | 0.80 | 125 | 25 | 125.0 | yes |
| 3.0 V | 0.80 | 125 | 40 | 140.0 | yes |
| 3.7 V | 0.52 | 80 | 25 | 66.6 | no |
| 3.7 V | 0.52 | 80 | 40 | 81.6 | no |
| 3.7 V | 0.52 | 125 | 25 | 90.0 | no |
| 3.7 V | 0.52 | 125 | 40 | 105.0 | no |

With a 4-layer board (80 C/W) the charger stays out of thermal regulation in all four cases. On a poor layout (125 C/W) it will fold back the current at low battery voltage (VBAT 3.0 V), which is safe but slows charging.

## SIM03 - Power path, USB unplug / replug

Files: `sim03a_powerpath_unplug_proposed.cir` (proposed), `sim03b_powerpath_unplug_revised.cir` (REJECTED BAT54 gate-feed attempt, kept for the record), `sim03c_replug_line_step.cir` (replug mitigation study), `sim03e_q1_gate_study.cir` (R43 study, simplified constant-power load), `sim03d_powerpath_unplug_final.cir` (final). Plots: `sim03_powerpath_proposed.png`, `sim03_powerpath_rejected_bat54_attempt.png`, `sim03c_replug_options.png`, `sim03e_q1_gate_study.png`, `sim03_powerpath_final.png`.

D40: 1N5819 model from standard.dio (OnSemi, 1 A). MBR0520L (0.5 A) was not used because VSYS draws up to about 0.5 A with a 600 mA ESP32 burst on +3V3. Q1: AO3401A VDMOS fit (SIM00).

| Check | Simulated | Limit | Result | Note |
|---|---|---|---|---|
| proposed_vsys_on_usb | 4.648 V | report | INFO |  |
| proposed_vsys_min_after_unplug | 2.949 V | >= 2.95 V (LTC3536 VIN min 1.8 V; report) | INFO |  |
| proposed_vsys_on_battery_14ms | 2.952 V | about VBAT - I x RDS(on) (Q1 on) | FAIL | below ~3.0 V means Q1 is still off and VSYS is fed by its body diode |
| proposed_v3v3_min | 3.191 V | >= 3.149 V (-5 %) | PASS | -3.75 % |
| proposed_v3v3_max | 3.584 V | <= 3.481 V (+5 %) | FAIL | 8.13 % |
| proposed_v3v3_unplug_window_min_max | 3.191, 3.332 V | 3.149 - 3.481 V | PASS |  |
| proposed_v3v3_replug_window_min_max | 3.291, 3.584 V | 3.149 - 3.481 V | FAIL |  |
| proposed_q1_turn_on_delay | n/a ms | report (body diode conducts until then) | INFO | not within the 10 ms unplugged window |
| proposed_reverse_current_into_vbus_avg | 60.72 uA | report (positive = VBUS -> VSYS, negative = into VBUS) | INFO | D40 average over 6-15 ms; switching-frequency displacement peaks via D40 capacitance: min -4.52 mA |
| proposed_reverse_current_into_vbus_end | 0.461 uA | report (14-15 ms average, negative = into VBUS) | INFO |  |
| proposed_vbus_at_14ms | 2.952 V | report | INFO |  |
| rejected_bat54_attempt_vsys_on_usb | 4.648 V | report | INFO |  |
| rejected_bat54_attempt_vsys_min_after_unplug | 2.949 V | >= 2.95 V (LTC3536 VIN min 1.8 V; report) | INFO |  |
| rejected_bat54_attempt_vsys_on_battery_14ms | 2.952 V | about VBAT - I x RDS(on) (Q1 on) | FAIL | below ~3.0 V means Q1 is still off and VSYS is fed by its body diode |
| rejected_bat54_attempt_v3v3_min | 3.19 V | >= 3.149 V (-5 %) | PASS | -3.76 % |
| rejected_bat54_attempt_v3v3_max | 3.585 V | <= 3.481 V (+5 %) | FAIL | 8.14 % |
| rejected_bat54_attempt_v3v3_unplug_window_min_max | 3.19, 3.331 V | 3.149 - 3.481 V | PASS |  |
| rejected_bat54_attempt_v3v3_replug_window_min_max | 3.291, 3.585 V | 3.149 - 3.481 V | FAIL |  |
| rejected_bat54_attempt_q1_turn_on_delay | n/a ms | report (body diode conducts until then) | INFO | not within the 10 ms unplugged window |
| rejected_bat54_attempt_reverse_current_into_vbus_avg | 61.41 uA | report (positive = VBUS -> VSYS, negative = into VBUS) | INFO | D40 average over 6-15 ms; switching-frequency displacement peaks via D40 capacitance: min -4.54 mA |
| rejected_bat54_attempt_reverse_current_into_vbus_end | 1.112 uA | report (14-15 ms average, negative = into VBUS) | INFO |  |
| rejected_bat54_attempt_vbus_at_14ms | 2.953 V | report | INFO |  |
| final_vsys_on_usb | 4.648 V | report | INFO |  |
| final_vsys_min_after_unplug | 2.951 V | >= 2.95 V (LTC3536 VIN min 1.8 V; report) | INFO |  |
| final_vsys_on_battery_14ms | 3.651 V | about VBAT - I x RDS(on) (Q1 on) | PASS | below ~3.0 V means Q1 is still off and VSYS is fed by its body diode |
| final_v3v3_min | 3.262 V | >= 3.149 V (-5 %) | PASS | -1.61 % |
| final_v3v3_max | 3.419 V | <= 3.481 V (+5 %) | PASS | 3.13 % |
| final_v3v3_unplug_window_min_max | 3.262, 3.348 V | 3.149 - 3.481 V | PASS |  |
| final_v3v3_replug_window_min_max | 3.291, 3.419 V | 3.149 - 3.481 V | PASS |  |
| final_q1_turn_on_delay | 5.509 ms | report (body diode conducts until then) | INFO | VBAT - VSYS < 0.1 V |
| final_reverse_current_into_vbus_avg | -7.044 uA | report (positive = VBUS -> VSYS, negative = into VBUS) | INFO | D40 average over 6-15 ms; switching-frequency displacement peaks via D40 capacitance: min -4.29 mA |
| final_reverse_current_into_vbus_end | -31.71 uA | report (14-15 ms average, negative = into VBUS) | INFO |  |
| final_vbus_at_14ms | 2.092 V | report | INFO |  |
| replug_C41_22_uF | 3.28, 3.526 V (+3V3 min, max) | 3.149 - 3.481 V | FAIL | D40 peak 7.38 A, VSYS peak 5.570 V |
| replug_C41_2_x_22_uF | 3.291, 3.493 V (+3V3 min, max) | 3.149 - 3.481 V | FAIL | D40 peak 8.18 A, VSYS peak 5.277 V |
| replug_C41_22_uF_+_100_uF_bulk | 3.291, 3.425 V (+3V3 min, max) | 3.149 - 3.481 V | PASS | D40 peak 8.87 A, VSYS peak 4.650 V |
| gate_study_R43_1k_q1_on_delay | 2.18 ms | report | INFO | USB current in R43 5.00 mA; VBUS at 400 ms = 0.032 V |
| gate_study_R43_2.2k_q1_on_delay | 4.47 ms | report | INFO | USB current in R43 2.27 mA; VBUS at 400 ms = 0.069 V |
| gate_study_R43_10k_q1_on_delay | 18.93 ms | report | INFO | USB current in R43 0.50 mA; VBUS at 400 ms = 0.344 V |
| gate_study_R43_100k_q1_on_delay | n/a ms | report | INFO | not within 398 ms; VBUS at 400 ms = 2.555 V |

What the simulations showed:

1. Proposed circuit: Q1 never turned on during the 10 ms unplugged window. Its gate is VBUS, and VBUS keeps C40 (10 uF) charged; with R41+R42 || R43 = 66.7 k the time constant is about 0.67 s, and the 1N5819 reverse leakage from VSYS holds VBUS near 2-2.6 V (SIM03e, 100 k case: VBUS still 2.56 V after 400 ms). VSYS therefore ran on the Q1 body diode at about 2.95 V (0.37 A x ~0.7 V = ~0.27 W in the body diode). The +3V3 rail itself stayed in regulation during the unplug because the LTC3536 works from 2.95 V.
2. A BAT54 gate feed (SIM03b) did not help: the gate still follows the slowly decaying VBUS. Rejected.
3. R43 study (SIM03e): Q1 turn-on after unplug is 2.2 ms (1 k), 4.5 ms (2.2 k), 18.9 ms (10 k), never within 400 ms (100 k). 2.2 k was chosen: 2.3 mA extra USB current, body diode conducts for about 4.5 ms only.
4. Replug: VSYS steps up to about 4.65 V within about 10 us and the LTC3536 overshoots +3V3 by +8.1 % (proposed). SIM03c compared options from the worst-case starting level (2.95 V): 22 uF alone +6.4 %, 2 x 22 uF +5.4 %, 22 uF + 100 uF low-ESR bulk +3.3 % (PASS). The bulk capacitor also removes the 5.57 V VSYS ring.
5. Inrush: D40 peak current on replug reaches 7-9 A in the model (ideal 5 V source behind 1 uH / 100 mohm). With 100 uF on VSYS the USB attach inrush is larger; USB 2.0 limits downstream capacitance at attach (10 uF class limit) - compliance was NOT checked here. If USB compliance matters, add an inrush limiter or a soft-start load switch.
6. Reverse current into VBUS while unplugged: in the proposed circuit the 6-15 ms average D40 current is positive (VBUS capacitor discharging into VSYS), so there is no back-feed. In the final circuit, once Q1 is on and VBUS has discharged below VSYS, the 1N5819 reverse leakage flows into VBUS: -31.7 uA average at 14-15 ms (model Is = 31.7 uA at 25 C; a real 1N5819 leaks more when hot). VBUS then settles at roughly leakage x 2.2 k (tens of mV). Switching-frequency displacement current through the D40 junction capacitance reaches a few mA peak.
7. Final circuit (SIM03d, R43 2.2 k + C42 100 uF): Q1 on 5.5 ms after unplug, VSYS on battery 3.651 V, +3V3 stays between 3.2617 V and 3.4187 V over unplug and replug (PASS, +/- 5 %).

## SIM04 - Hall sensor analogue front end (U6 MCP6004, one of four channels)

Files: `sim04a_hall_afe_ac.cir`, `sim04b_hall_afe_tran.cir`, `sim04c_hall_afe_ripple.cir`, `sim04d_adc_settling.cir`, shared `vw_hall_afe.inc`; schematic `sim04a_hall_afe_sch.asc`. Plots: `sim04a_hall_afe_bode.png`, `sim04b_hall_old_vs_new.png`, `sim04b_hall_peak_timing.png`, `sim04d_adc_sample_settling.png`.

| Check | Simulated | Limit | Result | Note |
|---|---|---|---|---|
| ac_f_minus3dB | 238 Hz | expected 232 Hz (calc) | PASS | f0 (-90 deg) = 230.9 Hz |
| ac_Q | 0.729 - | expected 0.73 (calc) | PASS |  |
| ac_peaking | 0.0148 dB | < 0.5 dB | PASS |  |
| ac_gain_50Hz | 0.014 dB | passband, > -0.5 dB | PASS |  |
| ac_gain_1kHz | -25.44 dB | report (Nyquist 1 kHz) | INFO |  |
| ac_gain_1p2MHz | -45.61 dB | report | INFO | Sallen-Key high-frequency feed-through limited by op-amp model output impedance and GBW |
| ac_group_delay_10Hz | 0.947 ms | < 2 ms | PASS |  |
| ripple_1p2MHz_old_pp | 9.996 mV p-p | report | INFO |  |
| ripple_1p2MHz_new_pp | 0.0524 mV p-p | report | INFO |  |
| tran_input_broadband_noise_rms | 19.88 mV rms | target 20 mV rms | INFO |  |
| tran_noise_rms_old | 21.41 mV rms | report | INFO | sampled at 2 kS/s; broadband + 50 Hz + 1.2 MHz ripple (rms-combined from SIM04c) |
| tran_noise_rms_new | 7.336 mV rms | lower than old | PASS |  |
| tran_snr_old | 31.45 dB | report (0.8 V peak / noise rms) | INFO |  |
| tran_snr_new | 40.75 dB | report | INFO |  |
| tran_snr_improvement | 9.3 dB | > 0 dB | PASS |  |
| tran_peak_time_mean_error_old | -0.0125 ms | report (mean error about known delay) | INFO |  |
| tran_peak_time_mean_error_new | 0.148 ms | report (mean error about known delay) | INFO |  |
| tran_peak_time_error_rms_old | 1.332 ms rms | report (max-sample method) | INFO |  |
| tran_peak_time_error_rms_new | 0.6415 ms rms | report (max-sample method) | INFO |  |
| tran_peak_time_error_max_old | 3.275 ms | report | INFO |  |
| tran_peak_time_error_max_new | 1.158 ms | report | INFO |  |
| tran_peak_time_error_rms_old_interp | 1.317 ms rms | report (3-point parabolic interpolation) | INFO |  |
| tran_peak_time_error_rms_new_interp | 0.6033 ms rms | report (3-point parabolic interpolation) | INFO |  |
| tran_peak_time_error_max_old_interp | 3.188 ms | report | INFO |  |
| tran_peak_time_error_max_new_interp | 0.9624 ms | report | INFO |  |
| tran_clean_peak_delay_new | 0.942 ms | < 2 ms (fixed filter delay, can be subtracted in firmware) | PASS |  |
| adc_sample_settling_0p5LSB | 0.635 us | < 1.5 us | PASS | generic op-amp model; real MCP6004 open-loop output impedance not modelled |
| adc_kick_dip_at_opamp_output | 78.7 mV | report | INFO |  |

Notes and assumptions:

- No Microchip MCP6004 model is installed. U6 uses the LTspice UniversalOpAmp2 `level2` model set to GBW 1 MHz, slew 0.6 V/us, Avol 4e5 (112 dB), output within 25 mV of the rails, 15 mA current limit, no input common-mode limit. It does not model the real MCP6004 open-loop output impedance, so the 1.2 MHz gain (Sallen-Key feed-through) and the sample-capacitor settling are likely optimistic.
- Noise: broadband part = 0.0806 x white(1e5 x time) (calibrated to 19.88 mV rms over the run), plus 10 mV amplitude 50 Hz. The 1.2 MHz ripple (10 mV p-p) was simulated separately (SIM04c, 10 ns step) and combined by rms. All noise figures are taken from ADC-rate samples (2 kS/s, 20 sampling phases).
- The filter passes 50 Hz untouched (0 dB at 50 Hz). In the new design the remaining 7.3 mV rms is mostly the 50 Hz term (10 mV amplitude = 7.07 mV rms); by subtraction (a calculation, not a separate run) the broadband residue is about 2 mV rms. A firmware 50 Hz notch or averaging over 20 ms would remove most of what is left.
- Peak timing: the new path adds a fixed 0.942 ms delay (clean-path peak delay, equal to the 10 Hz group delay); it is constant and can be subtracted in firmware. Error figures are about that known delay. Ten magnet passes at 103.7 ms spacing (so the 50 Hz phase differs each pass) x 20 sampling phases = 200 estimates per design.
- ADC kick-back: worst case sample capacitor at 0 V, channel at 2.45 V. The op-amp output dips 78.7 mV and the sample capacitor settles to 0.4 mV in 0.64 us (< 1.5 us).

## SIM05 - Maze touch-detection input (wire / start / finish)

File: `sim05_touch_input.cir` (stepped over 9 value sets, 2 mains phases, 50 and 100 pF coupling). Plot: `sim05_touch_input.png`.

Model: U7 74LVC1G17 as an LTspice SCHMITT device, VT+ 1.7 V / VT- 1.0 V (assumption). Contact = 1 ohm switch to the grounded handle ring. Mains = 230 V rms 50 Hz through 50 pF (nominal) or 100 pF (worst case); pin stray 30 pF; ESD diodes ignored as instructed. "Pulses" counts buffer-output low periods.

| Check | Simulated | Limit | Result | Note |
|---|---|---|---|---|
| proposed_CC50pF_false_outputs_idle | 0 pulses (worst of 2 mains phases) | 0 | PASS | idle node min 1.533 V vs VT- 1.0 V; node range over run -0.188 to 4.834 V (LVC input abs max is typically 6.5 V - not checked against the datasheet here; ESD clamps ignored as specified) |
| proposed_CC50pF_touch_2ms_pulses | 2, 1 pulses (phase 0, 90 deg) | 1 each | FAIL | widths [[2.65, 7.06], [11.4]] ms |
| proposed_CC50pF_touch_20ms_x2_with_5ms_gap_pulses | 2, 1 pulses (phase 0, 90 deg) | 2 each (gap resolved) | FAIL | widths [[20.58, 32.11], [51.4]] ms |
| proposed_CC50pF_skin_bridge_100k_pulses | 1, 1 pulses (phase 0, 90 deg) | 1 each, no chatter | PASS | node range [[0.173, 0.93], [0.173, 0.927]] V; latency [1.903, 2.302] ms |
| proposed_CC50pF_touch_0p5ms_detected | 0, 1 pulses (phase 0, 90 deg) | report | INFO |  |
| proposed_CC50pF_detection_latency | 1.444, 1.678 ms (phase 0, 90 deg) | report | INFO |  |
| proposed_CC100pF_false_outputs_idle | 5 pulses (worst of 2 mains phases) | 0 | FAIL | idle node min -0.068 V vs VT- 1.0 V; node range over run -2.296 to 6.355 V (LVC input abs max is typically 6.5 V - not checked against the datasheet here; ESD clamps ignored as specified) |
| proposed_CC100pF_touch_2ms_pulses | 3, 2 pulses (phase 0, 90 deg) | 1 each | FAIL | widths [[1.54, 9.68, 6.14], [11.81, 6.34]] ms |
| proposed_CC100pF_touch_20ms_x2_with_5ms_gap_pulses | 3, 3 pulses (phase 0, 90 deg) | 2 each (gap resolved) | FAIL | widths [[19.63, 32.47, 6.47], [51.4, 6.09, 67.11]] ms |
| proposed_CC100pF_skin_bridge_100k_pulses | 2, 0 pulses (phase 0, 90 deg) | 1 each, no chatter | FAIL | node range [[-0.204, 1.306], [-0.204, 1.304]] V; latency [1.191, None] ms |
| proposed_CC100pF_touch_0p5ms_detected | 2, 2 pulses (phase 0, 90 deg) | report | INFO |  |
| proposed_CC100pF_detection_latency | 1.553, 1.935 ms (phase 0, 90 deg) | report | INFO |  |
| proposed_patient_dc_current_worst_calc | 3.12 uA | <= 10 uA | PASS | calculation: 3.4 V rail (3.315 V + 2.5 %), resistors -1 % |
| proposed_patient_dc_current_calc | 3 uA | <= 10 uA design target (IEC 60601-1 type BF DC patient auxiliary current figure; not a certification) | PASS | calculation 3.3 V / (RS + RPU), RS 100 k, RPU 1000 k |
| revised_CC50pF_false_outputs_idle | 0 pulses (worst of 2 mains phases) | 0 | PASS | idle node min 2.580 V vs VT- 1.0 V; node range over run 0.089 to 3.870 V (LVC input abs max is typically 6.5 V - not checked against the datasheet here; ESD clamps ignored as specified) |
| revised_CC50pF_touch_2ms_pulses | 1, 1 pulses (phase 0, 90 deg) | 1 each | PASS | widths [[14.02], [11.65]] ms |
| revised_CC50pF_touch_20ms_x2_with_5ms_gap_pulses | 2, 1 pulses (phase 0, 90 deg) | 2 each (gap resolved) | FAIL | widths [[24.02, 31.16], [52.34]] ms |
| revised_CC50pF_skin_bridge_100k_pulses | 1, 1 pulses (phase 0, 90 deg) | 1 each, no chatter | PASS | node range [[0.454, 1.105], [0.454, 1.09]] V; latency [3.745, 9.83] ms |
| revised_CC50pF_touch_0p5ms_detected | 1, 1 pulses (phase 0, 90 deg) | report | INFO |  |
| revised_CC50pF_detection_latency | 0.341, 0.369 ms (phase 0, 90 deg) | report | INFO |  |
| revised_CC100pF_false_outputs_idle | 0 pulses (worst of 2 mains phases) | 0 | PASS | idle node min 1.992 V vs VT- 1.0 V; node range over run 0.042 to 4.437 V (LVC input abs max is typically 6.5 V - not checked against the datasheet here; ESD clamps ignored as specified) |
| revised_CC100pF_touch_2ms_pulses | 1, 1 pulses (phase 0, 90 deg) | 1 each | PASS | widths [[16.54], [12.62]] ms |
| revised_CC100pF_touch_20ms_x2_with_5ms_gap_pulses | 2, 1 pulses (phase 0, 90 deg) | 2 each (gap resolved) | FAIL | widths [[22.49, 32.52], [52.62]] ms |
| revised_CC100pF_skin_bridge_100k_pulses | 1, 1 pulses (phase 0, 90 deg) | 1 each, no chatter | PASS | node range [[0.136, 1.423], [0.136, 1.408]] V; latency [2.592, 10.898] ms |
| revised_CC100pF_touch_0p5ms_detected | 1, 1 pulses (phase 0, 90 deg) | report | INFO |  |
| revised_CC100pF_detection_latency | 0.355, 0.404 ms (phase 0, 90 deg) | report | INFO |  |
| revised_patient_dc_current_worst_calc | 9.28 uA | <= 10 uA | PASS | calculation: 3.4 V rail (3.315 V + 2.5 %), resistors -1 % |
| revised_patient_dc_current_calc | 8.92 uA | <= 10 uA design target (IEC 60601-1 type BF DC patient auxiliary current figure; not a certification) | PASS | calculation 3.3 V / (RS + RPU), RS 10 k, RPU 360 k |

Value sweep (core = no false outputs, one clean pulse for the 2 ms touch and for the skin bridge; gap = the 5 ms gap between two 20 ms contacts gives two pulses; both mains phases):

| CFG | RS | RPU | CF | I patient nominal / tolerance (uA, calc) | core 50 pF | core 100 pF | 5 ms gap 50 pF | 5 ms gap 100 pF | 0.5 ms touch detected | latency 2 ms touch (ms) |
|---|---|---|---|---|---|---|---|---|---|---|
| CFG0 | 100 k | 1000 k | 10 nF | 3.00 / 3.12 | False | False | False | False | [0, 1, 2, 2] | [1.444, 1.678, 1.553, 1.935] |
| CFG1 | 22 k | 330 k | 15 nF | 9.38 / 9.76 | True | False | False | False | [1, 1, 0, 1] | [0.467, 0.49, 0.506, 0.545] |
| CFG2 | 10 k | 330 k | 15 nF | 9.71 / 10.10 | True | False | False | False | [1, 1, 1, 1] | [0.205, 0.216, 0.223, 0.241] |
| CFG3 | 10 k | 330 k | 18 nF | 9.71 / 10.10 | True | False | False | False | [1, 1, 1, 1] | [0.241, 0.256, 0.258, 0.285] |
| CFG4 | 10 k | 330 k | 22 nF | 9.71 / 10.10 | True | True | False | False | [1, 1, 1, 1] | [0.287, 0.308, 0.303, 0.339] |
| CFG5 | 10 k | 330 k | 27 nF | 9.71 / 10.10 | True | True | False | False | [1, 1, 1, 1] | [0.345, 0.37, 0.359, 0.405] |
| CFG6 | 10 k | 330 k | 33 nF | 9.71 / 10.10 | True | True | False | False | [1, 1, 1, 1] | [0.412, 0.442, 0.424, 0.479] |
| CFG7 | 10 k | 360 k | 22 nF | 8.92 / 9.28 | True | False | False | False | [1, 1, 1, 1] | [0.285, 0.307, 0.3, 0.34] |
| CFG8 | 10 k | 360 k | 27 nF | 8.92 / 9.28 | True | True | False | False | [1, 1, 1, 1] | [0.341, 0.369, 0.355, 0.404] |

Findings:

- Proposed 100 k / 1 M / 10 nF FAILS: at 50 pF the 2 ms touch chatters on release (two pulses) because the 50 Hz ripple at the node (about 3 V p-p) is far larger than the 0.7 V hysteresis while the node recovers slowly (1 M x 10 nF = 10 ms); at 100 pF the mains alone produces false outputs and the node swings from -2.3 V to 6.4 V.
- Revised 10 k / 360 k / 27 nF passes the core checks at 50 and 100 pF for both mains phases, detects 0.5 ms touches, latency 0.34-0.40 ms, DC current through a person 8.9 uA nominal (9.3 uA with 1 % resistors and a 3.4 V rail), inside the 10 uA design target (IEC 60601-1 type BF DC patient auxiliary current figure, used as a design target, not a certification).
- The 5 ms gap is NOT reliably resolved by any value set in the sweep. The release time is set by RPU x CF, and the mains immunity needs a large CF while the 10 uA limit needs a large RPU. A rough bound (calculation): release time >= VT+ x CF / Imax, and CF must hold the 50 Hz ripple below the hysteresis, giving a release of roughly 15 ms at 100 pF coupling. In the revised design a 2 ms touch gives a 12-17 ms output pulse, so two touches closer than about 15 ms merge into one. Firmware should count contact onsets (falling edges), not pulse widths, and treat the pulse width as stretched.
- The skin-bridge (100 k) case gives one clean pulse, but its detection latency varies with mains phase (about 2.6-10.9 ms) because the node sits near VT- while the 50 Hz ripple decides the crossing.

## SIM06 - Haptic ERM driver (Q2 AO3400A)

Files: `sim06a_haptic_duty_sweep.cir` (duty 60-90 %), `sim06b_haptic_erm.cir` (chosen duty). Plot: `sim06_haptic_erm.png`.

Motor model: 25 ohm + 150 uH + back-EMF E = 0.5 x the motor average terminal voltage (behavioural RC average, steady state only). Flyback 1N5819, 10 uF + 100 nF local decoupling after 50 mohm, 100 ohm gate resistor, 100 k pull-down.

| Check | Simulated | Limit | Result | Note |
|---|---|---|---|---|
| VSYS3.7_duty | 76 % | chosen for ~3.0 V average motor voltage | INFO |  |
| VSYS3.7_motor_avg_voltage | 2.998 V | 3.0 V +/- 0.1 V | PASS |  |
| VSYS3.7_motor_avg_current | 60 mA | report | INFO |  |
| VSYS3.7_motor_current_ripple_pp | 88.5 mA p-p | report | INFO | L/R = 6 us << 50 us period, so the current is near-discontinuous |
| VSYS3.7_drain_peak | 3.983 V | < 20 V (AO3400A VDS 30 V abs max) | PASS |  |
| VSYS3.7_vsys_local_ripple_pp | 4.53 mV p-p | report | INFO |  |
| VSYS3.7_vsys_avg_current | 56.4 mA | report | INFO |  |
| VSYS3.7_gate_rise_10_90 | 162.6 ns | report | INFO | includes Miller plateau; 100 ohm gate resistor |
| VSYS3.7_gate_fall_90_10 | 176.6 ns | report | INFO |  |
| VSYS4.6_duty | 55 % | chosen for ~3.0 V average motor voltage | INFO |  |
| VSYS4.6_motor_avg_voltage | 2.985 V | 3.0 V +/- 0.1 V | PASS |  |
| VSYS4.6_motor_avg_current | 59.7 mA | report | INFO |  |
| VSYS4.6_motor_current_ripple_pp | 122.9 mA p-p | report | INFO | L/R = 6 us << 50 us period, so the current is near-discontinuous |
| VSYS4.6_drain_peak | 4.896 V | < 20 V (AO3400A VDS 30 V abs max) | PASS |  |
| VSYS4.6_vsys_local_ripple_pp | 6.36 mV p-p | report | INFO |  |
| VSYS4.6_vsys_avg_current | 53.8 mA | report | INFO |  |
| VSYS4.6_gate_rise_10_90 | 166.3 ns | report | INFO | includes Miller plateau; 100 ohm gate resistor |
| VSYS4.6_gate_fall_90_10 | 180 ns | report | INFO |  |

Duty sweep (motor average voltage, V): VSYS 3.7 V: {'0.6': 2.553, '0.7': 2.84, '0.8': 3.101, '0.9': 3.329}; VSYS 4.6 V: {'0.6': 3.178, '0.7': 3.532, '0.8': 3.856, '0.9': 4.138}. The duties 76 % and 55 % were interpolated from the sweep and then re-simulated.

The drain is clamped by the flyback diode at VSYS + Vf (no layout inductance modelled), far below the 20 V target. L/R = 6 us is much shorter than the 50 us PWM period, so the motor current is close to discontinuous and the ripple is larger than the average; a real ERM has more inductance than this and will be smoother.

## SIM07 - Magnetic buzzer driver (Q3 AO3400A) - optional, done

File: `sim07_buzzer.cir`. Plot: `sim07_buzzer.png`. +3V3 modelled as an ideal 3.315 V source behind 50 mohm with 22 uF (10 uF effective) local; the LTC3536 loop is not included. Buzzer = 16 ohm + 1 mH coil only.

| Check | Simulated | Limit | Result | Note |
|---|---|---|---|---|
| drain_peak | 4.231 V | < 20 V (AO3400A VDS 30 V abs max) | PASS |  |
| rail_3v3_ripple_pp | 9.05 mV p-p | report | INFO | +3V3 modelled as ideal 3.315 V behind 50 mohm with 22 uF (10 uF eff) local; converter loop not included |
| buzzer_peak_current | 178.5 mA | report | INFO |  |
| buzzer_avg_current | 84 mA | report | INFO |  |
| flyback_peak_current | 178 mA | < 1N4148 rating (Iave 200 mA model) | INFO |  |

## Model limits (read before relying on the numbers)

- Ceramic capacitors: DC-bias derating is a fixed estimate (22 uF -> 10 uF at 3.3 V); 10 uF parts at 5 V were not derated.
- LTC3536 and LTC4054 use ADI encrypted macro-models: efficiency, light-load losses and termination detail are only as good as those models.
- MOSFETs: VDMOS fits to four headline numbers each (SIM00), not manufacturer models; capacitances not verified.
- Op-amp: generic UniversalOpAmp2, not an MCP6004 model.
- Battery: scaled capacitor model; no temperature, no NTC, no protection IC.
- Touch input: ideal Schmitt thresholds, no ESD diodes, single coupling capacitance; real maze wiring coupling and mains phase vary.
- No PCB parasitics beyond the stated ESR/ESL and trace resistances; no temperature sweeps; no Monte Carlo.
- Schematics: `sim01a_buckboost_startup_sch.asc` and `sim04a_hall_afe_sch.asc` were generated by script with net-label flags on every pin. Both were run in LTspice batch mode and gave the same results as the .cir files (SIM04a: -3 dB 237.99 Hz, 1 kHz -25.44 dB; SIM01a: VOUT 3.3149 V, t90 0.729 ms). Their visual layout was not inspected in the GUI.
