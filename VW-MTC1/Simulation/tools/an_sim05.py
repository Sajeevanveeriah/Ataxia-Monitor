"""an_sim05.py - post-process SIM05 (maze touch input)."""
import numpy as np
from vw_mtc1.common import *
from vw_mtc1.ltraw import RawRead
import matplotlib.pyplot as plt

r = RawRead(lt('sim05_touch_input.raw'))
CFGS = {0: (100e3, 1e6, 10e-9), 1: (22e3, 330e3, 15e-9), 2: (10e3, 330e3, 15e-9), 3: (10e3, 330e3, 18e-9),
        4: (10e3, 330e3, 22e-9), 5: (10e3, 330e3, 27e-9), 6: (10e3, 330e3, 33e-9),
        7: (10e3, 360e3, 22e-9), 8: (10e3, 360e3, 27e-9)}
steps = [(c, ph, cc) for cc in (50e-12, 100e-12) for ph in (0, 90) for c in sorted(CFGS)]
EVENTS = [  # name, window start, window end, contact start, expected pulses
    ('idle_start', 0.0, 59e-3, None, 0),
    ('touch_0.5ms', 60e-3, 99e-3, 60e-3, None),
    ('touch_2ms', 100e-3, 139e-3, 100e-3, 1),
    ('touch_20ms_x2_5ms_gap', 140e-3, 229e-3, 140e-3, 2),
    ('skin_100k_50ms', 230e-3, 300e-3, 230e-3, 1),
    ('idle_end', 300e-3, 340e-3, None, 0),
]


from vw_mtc1.waveform import low_intervals as lows


rows, traces = {}, {}
for (cfg, ph, cc), sl in zip(steps, r.step_slices()):
    t, vin, out = r['time'][sl], r['V(in)'][sl], r['V(out)'][sl]
    iv = lows(t, out)
    row = {}
    for name, a, b, tc, exp in EVENTS:
        ps = [(f, s) for f, s in iv if a <= f < b]
        row[name] = {'pulses': len(ps), 'latency_ms': (round(float(ps[0][0] - tc) * 1e3, 3) if ps and tc is not None else None),
                     'widths_ms': [round(float(s - f) * 1e3, 2) for f, s in ps]}
    idle = ((t > 20e-3) & (t < 59e-3)) | (t > 300e-3)
    row['idle_vin_min_V'] = round(float(vin[idle].min()), 3)
    row['vin_max_V'] = round(float(vin[t > 20e-3].max()), 3)
    row['vin_min_V'] = round(float(vin[t > 20e-3].min()), 3)
    sk = (t > 240e-3) & (t < 280e-3)
    row['skin_vin_range_V'] = [round(float(vin[sk].min()), 3), round(float(vin[sk].max()), 3)]
    # core = no false outputs, exactly one pulse for the 2 ms contact and for the skin bridge,
    #        and no extra pulses in the 20 ms / gap window (<= 2)
    row['core_pass'] = (row['idle_start']['pulses'] == 0 and row['idle_end']['pulses'] == 0 and
                        row['touch_2ms']['pulses'] == 1 and row['skin_100k_50ms']['pulses'] == 1 and
                        1 <= row['touch_20ms_x2_5ms_gap']['pulses'] <= 2)
    row['gap_resolved'] = row['touch_20ms_x2_5ms_gap']['pulses'] == 2
    rows[(cfg, ph, cc)] = row
    traces[(cfg, ph, cc)] = (t, vin, out)

summary = {}
for cfg in sorted(CFGS):
    rs, rpu, cf = CFGS[cfg]
    rr = [rows[(cfg, ph, cc)] for cc in (50e-12, 100e-12) for ph in (0, 90)]
    summary[cfg] = {
        'RS_k': rs / 1e3, 'RPU_k': rpu / 1e3, 'CF_nF': cf * 1e9,
        'patient_dc_uA_calc': round(3.3 / (rs + rpu) * 1e6, 2),
        # tolerance case: 3.4 V rail (3.315 V + 2.5 %), resistors -1 %
        'patient_dc_uA_calc_worst': round(3.4 / (0.99 * (rs + rpu)) * 1e6, 2),
        'core_pass_50pF': all(rows[(cfg, ph, 50e-12)]['core_pass'] for ph in (0, 90)),
        'core_pass_100pF': all(rows[(cfg, ph, 100e-12)]['core_pass'] for ph in (0, 90)),
        'gap_resolved_50pF': all(rows[(cfg, ph, 50e-12)]['gap_resolved'] for ph in (0, 90)),
        'gap_resolved_100pF': all(rows[(cfg, ph, 100e-12)]['gap_resolved'] for ph in (0, 90)),
        'detect_0p5ms': [rows[(cfg, ph, cc)]['touch_0.5ms']['pulses'] for cc in (50e-12, 100e-12) for ph in (0, 90)],
        'latency_ms': [rows[(cfg, ph, cc)]['touch_2ms']['latency_ms'] for cc in (50e-12, 100e-12) for ph in (0, 90)],
    }
    print(cfg, summary[cfg])

# selection: core pass at 50 pF and 100 pF and patient current <= 10 uA; prefer gap resolution, then lowest latency
cands = [c for c in CFGS if c != 0 and summary[c]['core_pass_50pF'] and summary[c]['core_pass_100pF']
         and summary[c]['patient_dc_uA_calc_worst'] <= 10]
cands.sort(key=lambda c: (-(summary[c]['gap_resolved_50pF'] + summary[c]['gap_resolved_100pF']),
                          max(x for x in summary[c]['latency_ms'] if x is not None)))
fallback = [c for c in CFGS if c != 0 and summary[c]['core_pass_50pF'] and summary[c]['patient_dc_uA_calc'] <= 10]
chosen = cands[0] if cands else (fallback[0] if fallback else None)
print('candidates passing core at both CC:', cands, 'chosen:', chosen)

res = {'sweep_summary': {('CFG%d' % k): v for k, v in summary.items()},
       'sweep_detail': {'CFG%d_PH%d_CC%dpF' % (c, p, cc * 1e12): v for (c, p, cc), v in rows.items()},
       'chosen_cfg': chosen}
for cfg, lab in ((0, 'proposed'), (chosen, 'revised')):
    if cfg is None:
        continue
    rs, rpu, cf = CFGS[cfg]
    for cc in (50e-12, 100e-12):
        R = [rows[(cfg, ph, cc)] for ph in (0, 90)]
        p = '%s_CC%dpF_' % (lab, cc * 1e12)
        nf = max(x['idle_start']['pulses'] + x['idle_end']['pulses'] for x in R)
        res[p + 'false_outputs_idle'] = check(nf, 'pulses (worst of 2 mains phases)', '0', nf == 0,
                                              'idle node min %.3f V vs VT- 1.0 V; node range over run %.3f to %.3f V (LVC input abs max is typically 6.5 V - not checked against the datasheet here; ESD clamps ignored as specified)' % (
                                                  min(x['idle_vin_min_V'] for x in R), min(x['vin_min_V'] for x in R), max(x['vin_max_V'] for x in R)))
        n2 = [x['touch_2ms']['pulses'] for x in R]
        res[p + 'touch_2ms_pulses'] = check(n2, 'pulses (phase 0, 90 deg)', '1 each', all(v == 1 for v in n2),
                                            'widths %s ms' % [x['touch_2ms']['widths_ms'] for x in R])
        n20 = [x['touch_20ms_x2_5ms_gap']['pulses'] for x in R]
        res[p + 'touch_20ms_x2_with_5ms_gap_pulses'] = check(n20, 'pulses (phase 0, 90 deg)', '2 each (gap resolved)',
                                                             all(v == 2 for v in n20),
                                                             'widths %s ms' % [x['touch_20ms_x2_5ms_gap']['widths_ms'] for x in R])
        ns = [x['skin_100k_50ms']['pulses'] for x in R]
        res[p + 'skin_bridge_100k_pulses'] = check(ns, 'pulses (phase 0, 90 deg)', '1 each, no chatter', all(v == 1 for v in ns),
                                                   'node range %s V; latency %s ms' % ([x['skin_vin_range_V'] for x in R],
                                                                                         [x['skin_100k_50ms']['latency_ms'] for x in R]))
        n05 = [x['touch_0.5ms']['pulses'] for x in R]
        res[p + 'touch_0p5ms_detected'] = check(n05, 'pulses (phase 0, 90 deg)', 'report', None)
        lat = [x['touch_2ms']['latency_ms'] for x in R]
        res[p + 'detection_latency'] = check(lat, 'ms (phase 0, 90 deg)', 'report', None)
    res['%s_patient_dc_current_worst_calc' % lab] = check(round(3.4 / (0.99 * (rs + rpu)) * 1e6, 2), 'uA', '<= 10 uA',
                                                          3.4 / (0.99 * (rs + rpu)) <= 10e-6,
                                                          'calculation: 3.4 V rail (3.315 V + 2.5 %), resistors -1 %')
    res['%s_patient_dc_current_calc' % lab] = check(round(3.3 / (rs + rpu) * 1e6, 2), 'uA',
                                                    '<= 10 uA design target (IEC 60601-1 type BF DC patient auxiliary current figure; not a certification)',
                                                    3.3 / (rs + rpu) <= 10e-6, 'calculation 3.3 V / (RS + RPU), RS %g k, RPU %g k' % (rs / 1e3, rpu / 1e3))

fig, axs = plt.subplots(2, 1, figsize=(FIGW, 6.8), sharex=True)
for ax, cfg in zip(axs, [0, chosen if chosen is not None else 2]):
    rs, rpu, cf = CFGS[cfg]
    for cc, col, off in ((50e-12, 'C0', 0.0), (100e-12, 'C1', -0.6)):
        t, vin, out = traces[(cfg, 0, cc)]
        ax.plot(t * 1e3, vin, color=col, lw=0.8, label='V(in), CC = %d pF' % (cc * 1e12))
        ax.plot(t * 1e3, out / 3.3 * 0.45 - 0.75 + off, color=col, lw=1.0)
    ax.axhline(1.7, color='C3', ls='--', lw=0.7)
    ax.axhline(1.0, color='C3', ls=':', lw=0.7, label='VT+ 1.7 V / VT- 1.0 V')
    for x0, x1, c in ((60, 60.5, 'k'), (100, 102, 'k'), (140, 160, 'k'), (165, 185, 'k'), (230, 280, 'g')):
        ax.axvspan(x0, x1, color=c, alpha=0.08)
    ax.set_ylabel('V(in) (V)')
    ax.set_ylim(-1.6, 6.6)
    ax.set_title('%s: RS %g k, RPU %g k, CF %g nF' % ('Proposed' if cfg == 0 else 'Revised', rs / 1e3, rpu / 1e3, cf * 1e9))
    ax.legend(loc='upper right', ncol=3, fontsize=7.5)
axs[-1].set_xlabel('Time (ms); grey = contacts 0.5, 2, 20+20 ms (5 ms gap), green = 100 k skin bridge')
fig.suptitle('SIM05 touch input, 230 V 50 Hz coupled (buffer outputs drawn below 0 V: 50 pF upper, 100 pF lower)', fontsize=10)
savefig(fig, 'sim05_touch_input.png')
update_results('SIM05_touch_input', res)
for k, v in res.items():
    if not k.startswith('sweep'):
        print(k, v)
