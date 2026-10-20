"""make_summary.py - build Simulation_Summary.md from results.json.

All numbers in the tables are read from results.json (written by the an_*.py
scripts from the LTspice .raw/.log files). Narrative text is fixed here.
"""
import json, os, re, datetime
from common import ROOT, RESULTS, LT
from ltraw import parse_meas

R = json.load(open(RESULTS))

# SIM00 MOSFET model check -> results.json
m = parse_meas(os.path.join(LT, 'sim00_mosfet_model_check.log'))


def ck(v, u, lim, ok, note=None):
    d = {'value': v, 'units': u, 'limit': lim, 'result': 'PASS' if ok else 'FAIL'}
    if note:
        d['note'] = note
    return d


R['SIM00_mosfet_models'] = {
    'AO3401A_rds_on_vgs_-4.5V': ck(round(m['rdsp_45'] * 1e3, 2), 'mohm', 'about 50 mohm', abs(m['rdsp_45'] - 0.05) < 0.005),
    'AO3401A_rds_on_vgs_-2.5V': ck(round(m['rdsp_25'] * 1e3, 2), 'mohm', 'about 70 mohm', abs(m['rdsp_25'] - 0.07) < 0.007),
    'AO3401A_vgs_th_250uA': ck(round(m['vthp'], 3), 'V', 'about -0.9 V', abs(m['vthp'] + 0.9) < 0.1),
    'AO3400A_rds_on_vgs_4.5V': ck(round(m['rdsn_45'] * 1e3, 2), 'mohm', 'about 30 mohm', abs(m['rdsn_45'] - 0.03) < 0.003),
    'AO3400A_rds_on_vgs_2.5V': ck(round(m['rdsn_25'] * 1e3, 2), 'mohm', 'about 45 mohm', abs(m['rdsn_25'] - 0.045) < 0.0045),
    'AO3400A_vgs_th_250uA': ck(round(m['vthn'], 3), 'V', 'about 1.0 V', abs(m['vthn'] - 1.0) < 0.1),
}
json.dump(R, open(RESULTS, 'w'), indent=2)


def fmt(v):
    if v is None:
        return 'n/a'
    if isinstance(v, float):
        return ('%.4g' % v)
    if isinstance(v, list):
        return ', '.join(fmt(x) for x in v)
    return str(v)


def table(sim, keys=None, skip=()):
    d = R[sim]
    rows = ['| Check | Simulated | Limit | Result | Note |', '|---|---|---|---|---|']
    for k, v in d.items():
        if keys and k not in keys:
            continue
        if k in skip or not isinstance(v, dict) or 'result' not in v:
            continue
        note = v.get('note', '').replace('|', '/')
        rows.append('| %s | %s %s | %s | %s | %s |' % (k, fmt(v['value']), v['units'], v['limit'], v['result'], note))
    return '\n'.join(rows)


def g(sim, key, field='value'):
    return R[sim][key][field]


S1, S2, S3, S4, S5, S6, S7 = ('SIM01_buckboost', 'SIM02_charger', 'SIM03_power_path', 'SIM04_hall_afe',
                              'SIM05_touch_input', 'SIM06_haptic_erm', 'SIM07_buzzer')
has_final = 'final_vsys_on_usb' in R[S3]
fails = []
for sim, d in R.items():
    for k, v in d.items():
        if isinstance(v, dict) and v.get('result') == 'FAIL':
            fails.append((sim, k))

out = []
w = out.append
w('# VW-MTC1 Simulation Summary')
w('')
w('Voltwyn MazeTrack Controller VW-MTC1 - LTspice verification of the proposed analogue and power values.')
w('')
w('- Simulator: LTspice 26.1.1 (batch mode, `LTspice.exe -b`). Every number below comes from a .raw or .log '
  'file in `LTspice/`, read by the scripts in `tools/` (`ltraw.py` raw parser, `an_sim*.py` analysis). '
  'Plots in `Plots/`, machine-readable results in `results.json`.')
w('- Plotting used the Python 3.13 runtime bundled with MechFaber (has numpy/scipy/matplotlib); the system '
  'Python 3.14 has numpy and scipy but no matplotlib and nothing was installed.')
w('- Items labelled CALCULATION are hand formulas, not simulations.')
w('- Generated: %s (system clock, Australia/Melbourne local time).' %
  datetime.datetime.now().astimezone().strftime('%Y-%m-%d %H:%M UTC%z'))
w('')
w('## Final component values and changes from the proposal')
w('')
w('| Ref | Function | Proposed | Final | Changed? | Evidence |')
w('|---|---|---|---|---|---|')
w('| L1 | LTC3536 inductor | 4.7 uH XFL4020-472 | 4.7 uH XFL4020-472 | no | SIM01 |')
w('| C30, C31 | +3V3 output | 2 x 22 uF X5R 0805 | 2 x 22 uF X5R 0805 | no | SIM01 |')
w('| C28, C29 | LTC3536 input | 22 uF + 100 nF | 22 uF + 100 nF | no | SIM01 |')
w('| R30/R31 | feedback | 1 M / 221 k | 1 M / 221 k | no | SIM01 (3.315 V) |')
w('| C32/R32 | feed-forward | 47 pF + 6.49 k | 47 pF + 6.49 k | no | SIM01b, no ringing |')
w('| C33/R33 | compensation | 220 pF + 49.9 k | 220 pF + 49.9 k | no (no retune needed) | SIM01b |')
w('| R21 (RPROG) | LTC4054 charge current | 2.49 k | 2.49 k | no | SIM02a |')
w('| C20 + R20 | LTC4054 VCC damping | 10 uF + 1.5 ohm in series | 10 uF + 1.5 ohm in series | no | SIM02b |')
w('| D40 | VBUS -> VSYS Schottky | 1N5819 or MBR0520L | 1N5819 class (B5819W, 1 A) | choice | SIM03 (VSYS draws up to ~0.5 A) |')
w('| R43 | Q1 gate / VBUS pull-down | 100 k | **2.2 k** | **YES** | SIM03a/e: with 100 k Q1 never turns on after unplug |')
w('| C42 | VSYS bulk | (none) | **100 uF low-ESR, ESR ~50 mohm (polymer/tantalum)** | **YES (added)** | SIM03c: replug overshoot +6.4 % -> +3.3 % |')
w('| R50-R52, C51, C52 | Hall LPF | 1 M, 10 k, 10 k, 100 nF, 47 nF | unchanged | no | SIM04 |')
w('| RS (series) | touch input | 100 k | **10 k** | **YES** | SIM05 |')
w('| RPU (pull-up) | touch input | 1 M | **360 k** | **YES** | SIM05 |')
w('| CF (node cap) | touch input | 10 nF | **27 nF** | **YES** | SIM05 |')
w('| Q2 duty | ERM PWM 20 kHz | (to choose) | 76 % at VSYS 3.7 V, 55 %% at VSYS 4.6 V | chosen | SIM06 |'.replace('%%', '%'))
w('')
w('## Fail list (honest view)')
w('')
w('Checks marked FAIL in results.json. Proposed-value fails are followed by a revision that passes, except: '
  '(1) SIM02 termination current (macro-model behaviour, no board fix), (2) SIM05 5 ms gap resolution, which no '
  'passive value set met within the 10 uA limit (see SIM05). Rows starting rejected_ or replug_C41 are intermediate '
  'study cases, not the final design.')
w('')
for sim, k in fails:
    w('- %s / %s' % (sim, k))
w('')

# ---------------- SIM00 ----------------
w('## SIM00 - MOSFET model fits (vw_models.lib)')
w('')
w('AO3401A and AO3400A are not in the LTspice library, so VDMOS fits were written to the headline values in the brief '
  '(RDS(on) = Rd + 1/(Kp x Vov)). Capacitances (Ciss ~650-700 pF) are set as parameters but were not separately simulated.')
w('')
w(table('SIM00_mosfet_models'))
w('')

# ---------------- SIM01 ----------------
w('## SIM01 - 3.3 V buck-boost (U4 LTC3536EMSE)')
w('')
w('Files: `sim01a_buckboost_startup.cir`, `sim01b_buckboost_loadstep.cir`, `sim01c_buckboost_ripple_eff.cir`, '
  '`sim01d_buckboost_burst.cir`, shared circuit `vw_3v3_buckboost.inc`; schematic `sim01a_buckboost_startup_sch.asc`. '
  'Plots: `sim01a_startup.png`, `sim01b_loadstep.png`, `sim01c_ripple_300mA.png`, `sim01c_efficiency.png`, `sim01d_burst_20mA.png`.')
w('')
w(table(S1))
w('')
w('Notes and assumptions:')
w('')
w('- COUT: each 22 uF X5R 0805 modelled as 10 uF effective at 3.3 V DC bias, ESR 3 mohm, ESL 0.5 nH (assumption). '
  'CIN 22 uF modelled the same way. LTspice raised the capacitor Cpar to 10 pF (log message).')
w('- V(out) at full bandwidth shows large spikes (about 1.1 V p-p at 300 mA) caused by the ideal switch edges of the '
  'macro-model driving the 0.5 nH ESL. They are not representative of a real board measured with a 20 MHz scope limit, '
  'so all regulation and ripple checks use a buffered 20 MHz single-pole copy of the rail (V(ofilt)). Layout ESL will '
  'still produce real high-frequency spikes; keep C30/C31 tight to the IC.')
w('- Ringing check: the one-switching-period average of the rail shows one extremum per step at every VIN, so the loop '
  'is well damped and the compensation was not retuned.')
w('- Efficiency comes from the ADI macro-model with L1 DCR only (no core loss, no capacitor ESR loss beyond 3 mohm). '
  'The 94 % figure at 50 mA in PWM looks optimistic and has not been checked against the datasheet curves here.')
w('- Burst Mode: the average output in Burst Mode sits lower than in PWM (%.4f V); that is the Burst Mode hysteresis '
  'band, still within +/- 5 %%.' % g(S1, 'burst_20mA_vavg'))
w('')

# ---------------- SIM02 ----------------
w('## SIM02 - Li-ion charger (U3 LTC4054-4.2) and USB hot-plug')
w('')
w('Files: `sim02a_charger_cccv.cir`, `sim02b_usb_hotplug.cir`. Plots: `sim02a_charger_cccv.png`, `sim02b_usb_hotplug.png`.')
w('')
w(table(S2, skip=('thermal_calc_NOT_SIMULATED',)))
w('')
w('Interpretation of the brief: "VCC through a 1.5 ohm series resistor into 10 uF" was modelled as the LTC4054 '
  'datasheet hot-plug recommendation, i.e. 1.5 ohm in series WITH the 10 uF capacitor (an RC snubber at VCC), not a '
  'resistor in the supply path. A 1.5 ohm supply-path resistor would drop 0.6 V at 400 mA.')
w('')
w('Battery model (scaled): 1.5 F capacitor behind 0.25 ohm internal resistance, starting at 2.85 V, as in the ADI '
  'example. Currents and thresholds are real; only the time axis is compressed (about 7 s instead of hours).')
w('')
w('Termination: the macro-model ends the charge at V(PROG) = 80 mV, which is 28.8 mA in the cell (the IBAT/IPROG ratio '
  'also falls to about 895 at low current). This misses the "about 40 mA" target (C/10 = 40.2 mA). It is set by the IC, '
  'not by board values, so no value was changed. The real part should be checked against the datasheet C/10 '
  'specification; this simulation cannot settle it.')
w('')
w('Hot-plug: (ii) 10 uF + 1.5 ohm damps the ring completely (5.00 V peak). With the 1 uF VCC-pin capacitor added (the real '
  'board), the 1 uF rings with the cable inductance to %.2f V, still below the 10 V VCC abs max as recalled for the LTC4054 (not re-checked against the datasheet). '
  'Ceramic DC-bias derating of the 10 uF at 5 V was not modelled.' % g(S2, 'hotplug_peak_10uF_1R5_plus_1uF_pin'))
w('')
w('### Thermal - CALCULATION (not a simulation)')
w('')
w('P = (5 V - VBAT) x 0.4 A, Tj = Ta + P x theta-JA.')
w('')
w('| VBAT | P (W) | theta-JA (C/W) | Ta (C) | Tj (C) | Thermal regulation (120 C) engages? |')
w('|---|---|---|---|---|---|')
for k, v in R[S2]['thermal_calc_NOT_SIMULATED'].items():
    mm = re.match(r'VBAT([\d.]+)_thetaJA(\d+)_Ta(\d+)', k)
    w('| %s V | %.2f | %s | %s | %.1f | %s |' % (mm.group(1), v['P_W'], mm.group(2), mm.group(3), v['Tj_C'],
                                                 'yes' if v['thermal_regulation_engages'] else 'no'))
w('')
w('With a 4-layer board (80 C/W) the charger stays out of thermal regulation in all four cases. On a poor layout '
  '(125 C/W) it will fold back the current at low battery voltage (VBAT 3.0 V), which is safe but slows charging.')
w('')

# ---------------- SIM03 ----------------
w('## SIM03 - Power path, USB unplug / replug')
w('')
w('Files: `sim03a_powerpath_unplug_proposed.cir` (proposed), `sim03b_powerpath_unplug_revised.cir` (REJECTED BAT54 '
  'gate-feed attempt, kept for the record), `sim03c_replug_line_step.cir` (replug mitigation study), '
  '`sim03e_q1_gate_study.cir` (R43 study, simplified constant-power load), `sim03d_powerpath_unplug_final.cir` (final). '
  'Plots: `sim03_powerpath_proposed.png`, `sim03_powerpath_rejected_bat54_attempt.png`, `sim03c_replug_options.png`, '
  '`sim03e_q1_gate_study.png`%s.' % (', `sim03_powerpath_final.png`' if has_final else ''))
w('')
w('D40: 1N5819 model from standard.dio (OnSemi, 1 A). MBR0520L (0.5 A) was not used because VSYS draws up to about 0.5 A '
  'with a 600 mA ESP32 burst on +3V3. Q1: AO3401A VDMOS fit (SIM00).')
w('')
w(table(S3))
w('')
w('What the simulations showed:')
w('')
w('1. Proposed circuit: Q1 never turned on during the 10 ms unplugged window. Its gate is VBUS, and VBUS keeps C40 '
  '(10 uF) charged; with R41+R42 || R43 = 66.7 k the time constant is about 0.67 s, and the 1N5819 reverse leakage from '
  'VSYS holds VBUS near 2-2.6 V (SIM03e, 100 k case: VBUS still 2.56 V after 400 ms). VSYS therefore ran on the Q1 body '
  'diode at about 2.95 V (0.37 A x ~0.7 V = ~0.27 W in the body diode). The +3V3 rail itself stayed in regulation '
  'during the unplug because the LTC3536 works from 2.95 V.')
w('2. A BAT54 gate feed (SIM03b) did not help: the gate still follows the slowly decaying VBUS. Rejected.')
w('3. R43 study (SIM03e): Q1 turn-on after unplug is 2.2 ms (1 k), 4.5 ms (2.2 k), 18.9 ms (10 k), never within 400 ms '
  '(100 k). 2.2 k was chosen: 2.3 mA extra USB current, body diode conducts for about 4.5 ms only.')
w('4. Replug: VSYS steps up to about 4.65 V within about 10 us and the LTC3536 overshoots +3V3 by +8.1 % (proposed). '
  'SIM03c compared options from the worst-case starting level (2.95 V): 22 uF alone +6.4 %, 2 x 22 uF +5.4 %, '
  '22 uF + 100 uF low-ESR bulk +3.3 % (PASS). The bulk capacitor also removes the 5.57 V VSYS ring.')
w('5. Inrush: D40 peak current on replug reaches 7-9 A in the model (ideal 5 V source behind 1 uH / 100 mohm). '
  'With 100 uF on VSYS the USB attach inrush is larger; USB 2.0 limits downstream capacitance at attach (10 uF class '
  'limit) - compliance was NOT checked here. If USB compliance matters, add an inrush limiter or a soft-start load switch.')
w('6. Reverse current into VBUS while unplugged: in the proposed circuit the 6-15 ms average D40 current is positive '
  '(VBUS capacitor discharging into VSYS), so there is no back-feed. In the final circuit, once Q1 is on and VBUS has '
  'discharged below VSYS, the 1N5819 reverse leakage flows into VBUS: %.1f uA average at 14-15 ms (model Is = 31.7 uA '
  'at 25 C; a real 1N5819 leaks more when hot). VBUS then settles at roughly leakage x 2.2 k (tens of mV). '
  'Switching-frequency displacement current through the D40 junction capacitance reaches a few mA peak.' %
  R[S3]['final_reverse_current_into_vbus_end']['value'])
w('7. Final circuit (SIM03d, R43 2.2 k + C42 100 uF): Q1 on %.1f ms after unplug, VSYS on battery %.3f V, +3V3 stays '
  'between %.4f V and %.4f V over unplug and replug (PASS, +/- 5 %%).' % (
  R[S3]['final_q1_turn_on_delay']['value'], R[S3]['final_vsys_on_battery_14ms']['value'],
  R[S3]['final_v3v3_min']['value'], R[S3]['final_v3v3_max']['value']))
w('')

# ---------------- SIM04 ----------------
w('## SIM04 - Hall sensor analogue front end (U6 MCP6004, one of four channels)')
w('')
w('Files: `sim04a_hall_afe_ac.cir`, `sim04b_hall_afe_tran.cir`, `sim04c_hall_afe_ripple.cir`, `sim04d_adc_settling.cir`, '
  'shared `vw_hall_afe.inc`; schematic `sim04a_hall_afe_sch.asc`. Plots: `sim04a_hall_afe_bode.png`, '
  '`sim04b_hall_old_vs_new.png`, `sim04b_hall_peak_timing.png`, `sim04d_adc_sample_settling.png`.')
w('')
w(table(S4))
w('')
w('Notes and assumptions:')
w('')
w('- No Microchip MCP6004 model is installed. U6 uses the LTspice UniversalOpAmp2 `level2` model set to GBW 1 MHz, '
  'slew 0.6 V/us, Avol 4e5 (112 dB), output within 25 mV of the rails, 15 mA current limit, no input common-mode limit. '
  'It does not model the real MCP6004 open-loop output impedance, so the 1.2 MHz gain (Sallen-Key feed-through) and the '
  'sample-capacitor settling are likely optimistic.')
w('- Noise: broadband part = 0.0806 x white(1e5 x time) (calibrated to %.2f mV rms over the run), plus 10 mV amplitude '
  '50 Hz. The 1.2 MHz ripple (10 mV p-p) was simulated separately (SIM04c, 10 ns step) and combined by rms. All noise '
  'figures are taken from ADC-rate samples (2 kS/s, 20 sampling phases).' % g(S4, 'tran_input_broadband_noise_rms'))
w('- The filter passes 50 Hz untouched (0 dB at 50 Hz). In the new design the remaining 7.3 mV rms is mostly the 50 Hz '
  'term (10 mV amplitude = 7.07 mV rms); by subtraction (a calculation, not a separate run) the broadband residue is '
  'about 2 mV rms. A firmware 50 Hz notch or averaging over 20 ms would remove most of what is left.')
w('- Peak timing: the new path adds a fixed %.3f ms delay (clean-path peak delay, equal to the 10 Hz group delay); it '
  'is constant and can be subtracted in firmware. Error figures are about that known delay. Ten magnet passes at '
  '103.7 ms spacing (so the 50 Hz phase differs each pass) x 20 sampling phases = 200 estimates per design.' %
  g(S4, 'tran_clean_peak_delay_new'))
w('- ADC kick-back: worst case sample capacitor at 0 V, channel at 2.45 V. The op-amp output dips %.1f mV and the '
  'sample capacitor settles to 0.4 mV in %.2f us (< 1.5 us).' % (g(S4, 'adc_kick_dip_at_opamp_output'),
                                                                   g(S4, 'adc_sample_settling_0p5LSB')))
w('')

# ---------------- SIM05 ----------------
w('## SIM05 - Maze touch-detection input (wire / start / finish)')
w('')
w('File: `sim05_touch_input.cir` (stepped over 9 value sets, 2 mains phases, 50 and 100 pF coupling). Plot: '
  '`sim05_touch_input.png`.')
w('')
w('Model: U7 74LVC1G17 as an LTspice SCHMITT device, VT+ 1.7 V / VT- 1.0 V (assumption). Contact = 1 ohm switch to the '
  'grounded handle ring. Mains = 230 V rms 50 Hz through 50 pF (nominal) or 100 pF (worst case); pin stray 30 pF; ESD '
  'diodes ignored as instructed. "Pulses" counts buffer-output low periods.')
w('')
w(table(S5))
w('')
w('Value sweep (core = no false outputs, one clean pulse for the 2 ms touch and for the skin bridge; '
  'gap = the 5 ms gap between two 20 ms contacts gives two pulses; both mains phases):')
w('')
w('| CFG | RS | RPU | CF | I patient nominal / tolerance (uA, calc) | core 50 pF | core 100 pF | 5 ms gap 50 pF | 5 ms gap 100 pF | 0.5 ms touch detected | latency 2 ms touch (ms) |')
w('|---|---|---|---|---|---|---|---|---|---|---|')
for k, v in R[S5]['sweep_summary'].items():
    w('| %s | %g k | %g k | %g nF | %.2f / %.2f | %s | %s | %s | %s | %s | %s |' % (
        k, v['RS_k'], v['RPU_k'], round(v['CF_nF'], 1), v['patient_dc_uA_calc'], v['patient_dc_uA_calc_worst'],
        v['core_pass_50pF'], v['core_pass_100pF'], v['gap_resolved_50pF'], v['gap_resolved_100pF'],
        v['detect_0p5ms'], v['latency_ms']))
w('')
w('Findings:')
w('')
w('- Proposed 100 k / 1 M / 10 nF FAILS: at 50 pF the 2 ms touch chatters on release (two pulses) because the 50 Hz '
  'ripple at the node (about 3 V p-p) is far larger than the 0.7 V hysteresis while the node recovers slowly '
  '(1 M x 10 nF = 10 ms); at 100 pF the mains alone produces false outputs and the node swings from -2.3 V to 6.4 V.')
w('- Revised 10 k / 360 k / 27 nF passes the core checks at 50 and 100 pF for both mains phases, detects 0.5 ms touches, '
  'latency 0.34-0.40 ms, DC current through a person 8.9 uA nominal (9.3 uA with 1 % resistors and a 3.4 V rail), '
  'inside the 10 uA design target (IEC 60601-1 type BF DC patient auxiliary current figure, used as a design target, '
  'not a certification).')
w('- The 5 ms gap is NOT reliably resolved by any value set in the sweep. The release time is set by RPU x CF, and the '
  'mains immunity needs a large CF while the 10 uA limit needs a large RPU. A rough bound (calculation): release time >= '
  'VT+ x CF / Imax, and CF must hold the 50 Hz ripple below the hysteresis, giving a release of roughly 15 ms at 100 pF '
  'coupling. In the revised design a 2 ms touch gives a 12-17 ms output pulse, so two touches closer than about 15 ms '
  'merge into one. Firmware should count contact onsets (falling edges), not pulse widths, and treat the pulse width as '
  'stretched.')
w('- The skin-bridge (100 k) case gives one clean pulse, but its detection latency varies with mains phase '
  '(about 2.6-10.9 ms) because the node sits near VT- while the 50 Hz ripple decides the crossing.')
w('')

# ---------------- SIM06 ----------------
w('## SIM06 - Haptic ERM driver (Q2 AO3400A)')
w('')
w('Files: `sim06a_haptic_duty_sweep.cir` (duty 60-90 %), `sim06b_haptic_erm.cir` (chosen duty). Plot: `sim06_haptic_erm.png`.')
w('')
w('Motor model: 25 ohm + 150 uH + back-EMF E = 0.5 x the motor average terminal voltage (behavioural RC average, '
  'steady state only). Flyback 1N5819, 10 uF + 100 nF local decoupling after 50 mohm, 100 ohm gate resistor, 100 k pull-down.')
w('')
w(table(S6))
w('')
w('Duty sweep (motor average voltage, V): VSYS 3.7 V: %s; VSYS 4.6 V: %s. The duties 76 %% and 55 %% were interpolated '
  'from the sweep and then re-simulated.' % (R[S6]['duty_sweep_vmotor_avg_V']['VSYS3.7'], R[S6]['duty_sweep_vmotor_avg_V']['VSYS4.6']))
w('')
w('The drain is clamped by the flyback diode at VSYS + Vf (no layout inductance modelled), far below the 20 V target. '
  'L/R = 6 us is much shorter than the 50 us PWM period, so the motor current is close to discontinuous and the ripple '
  'is larger than the average; a real ERM has more inductance than this and will be smoother.')
w('')

# ---------------- SIM07 ----------------
w('## SIM07 - Magnetic buzzer driver (Q3 AO3400A) - optional, done')
w('')
w('File: `sim07_buzzer.cir`. Plot: `sim07_buzzer.png`. +3V3 modelled as an ideal 3.315 V source behind 50 mohm with '
  '22 uF (10 uF effective) local; the LTC3536 loop is not included. Buzzer = 16 ohm + 1 mH coil only.')
w('')
w(table(S7))
w('')

w('## Model limits (read before relying on the numbers)')
w('')
w('- Ceramic capacitors: DC-bias derating is a fixed estimate (22 uF -> 10 uF at 3.3 V); 10 uF parts at 5 V were not derated.')
w('- LTC3536 and LTC4054 use ADI encrypted macro-models: efficiency, light-load losses and termination detail are only '
  'as good as those models.')
w('- MOSFETs: VDMOS fits to four headline numbers each (SIM00), not manufacturer models; capacitances not verified.')
w('- Op-amp: generic UniversalOpAmp2, not an MCP6004 model.')
w('- Battery: scaled capacitor model; no temperature, no NTC, no protection IC.')
w('- Touch input: ideal Schmitt thresholds, no ESD diodes, single coupling capacitance; real maze wiring coupling and '
  'mains phase vary.')
w('- No PCB parasitics beyond the stated ESR/ESL and trace resistances; no temperature sweeps; no Monte Carlo.')
w('- Schematics: `sim01a_buckboost_startup_sch.asc` and `sim04a_hall_afe_sch.asc` were generated by script with net-label '
  'flags on every pin. Both were run in LTspice batch mode and gave the same results as the .cir files '
  '(SIM04a: -3 dB 237.99 Hz, 1 kHz -25.44 dB; SIM01a: VOUT 3.3149 V, t90 0.729 ms). Their visual layout was not '
  'inspected in the GUI.')
w('')
open(os.path.join(ROOT, 'Simulation_Summary.md'), 'w', encoding='utf-8').write('\n'.join(out))
print('wrote Simulation_Summary.md,', len(out), 'lines; fails:', len(fails))
