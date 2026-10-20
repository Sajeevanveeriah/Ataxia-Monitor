"""an_sim03.py - post-process SIM03a/b (power path unplug/replug) and SIM03c."""
import os
import numpy as np
from vw_mtc1.common import *
from vw_mtc1.ltraw import RawRead, parse_meas
from vw_mtc1.runlt import read_log
import matplotlib.pyplot as plt

TSW = 1 / 1.2e6
res = {}


from vw_mtc1.waveform import moving_average


def movavg(t, y, win, dt=20e-9):
    return moving_average(t, y, win, dt)


for tag, fn in (('proposed', 'sim03a_powerpath_unplug_proposed'), ('rejected_bat54_attempt', 'sim03b_powerpath_unplug_revised'),
                ('final', 'sim03d_powerpath_unplug_final')):
    if not os.path.exists(lt(fn + '.log')) or 'vsys_usb' not in parse_meas(lt(fn + '.log')):
        print('SKIP (not run yet):', fn)
        continue
    r = RawRead(lt(fn + '.raw'))
    mz = parse_meas(lt(fn + '.log'))
    t = r['time']
    vbus, vsys, vbat, v3 = r['V(vbus)'], r['V(vsys)'], r['V(vbat)'], r['V(ofilt)']
    id40 = r['I(D40)']
    p = tag + '_'
    res[p + 'vsys_on_usb'] = check(round(mz['vsys_usb'], 3), 'V', 'report', None)
    res[p + 'vsys_min_after_unplug'] = check(round(mz['vsys_min'], 3), 'V', '>= 2.95 V (LTC3536 VIN min 1.8 V; report)', None)
    res[p + 'vsys_on_battery_14ms'] = check(round(mz['vsys_bat'], 3), 'V', 'about VBAT - I x RDS(on) (Q1 on)', mz['vsys_bat'] > 3.5,
                                            'below ~3.0 V means Q1 is still off and VSYS is fed by its body diode')
    w = t > 4e-3
    tu, va = movavg(t[w], v3[w], TSW)
    dev_min = (mz['v3_min'] - 3.315) / 3.315 * 100
    dev_max = (mz['v3_max'] - 3.315) / 3.315 * 100
    res[p + 'v3v3_min'] = check(round(mz['v3_min'], 4), 'V', '>= 3.149 V (-5 %)', mz['v3_min'] >= 3.315 * 0.95, '%.2f %%' % dev_min)
    res[p + 'v3v3_max'] = check(round(mz['v3_max'], 4), 'V', '<= 3.481 V (+5 %)', mz['v3_max'] <= 3.315 * 1.05, '%.2f %%' % dev_max)
    # windows: unplug (5-15 ms) and replug (15-20 ms)
    for nm, a, b in (('unplug', 5e-3, 15e-3), ('replug', 15e-3, 20e-3)):
        m = (t >= a) & (t < b)
        res[p + 'v3v3_%s_window_min_max' % nm] = check([round(float(v3[m].min()), 4), round(float(v3[m].max()), 4)], 'V',
                                                       '3.149 - 3.481 V', bool(v3[m].min() >= 3.149 and v3[m].max() <= 3.481))
    # Q1 turn-on: V(vbat) - V(vsys) falls below 0.1 V after unplug
    m = t > 5e-3
    dv = vbat[m] - vsys[m]
    k0 = np.where(dv > 0.3)[0]          # body diode starts conducting
    k = np.where(dv[k0[0]:] < 0.1)[0] + k0[0] if len(k0) else []
    ton = float(t[m][k[0]] - 5e-3) if len(k) else None
    # only report a turn-on that happens before the replug
    if ton is not None and ton > 10e-3:
        ton = None
    res[p + 'q1_turn_on_delay'] = check(None if ton is None else round(ton * 1e3, 4), 'ms',
                                        'report (body diode conducts until then)', None,
                                        'not within the 10 ms unplugged window' if ton is None else 'VBAT - VSYS < 0.1 V')
    # reverse current into VBUS while unplugged (I(D40) < 0 means VSYS -> VBUS)
    m = (t > 6e-3) & (t < 15e-3)
    tt, ia = movavg(t[m], id40[m], 10 * TSW)
    res[p + 'reverse_current_into_vbus_avg'] = check(round(float(np.trapezoid(id40[m], t[m]) / (t[m][-1] - t[m][0])) * 1e6, 3), 'uA',
                                                     'report (positive = VBUS -> VSYS, negative = into VBUS)', None,
                                                     'D40 average over 6-15 ms; switching-frequency displacement peaks via D40 capacitance: min %.2f mA' % (id40[m].min() * 1e3))
    res[p + 'reverse_current_into_vbus_end'] = check(round(float(mz['id_rev_end']) * 1e6, 3), 'uA', 'report (14-15 ms average, negative = into VBUS)', None)
    res[p + 'vbus_at_14ms'] = check(round(mz['vbus_end'], 3), 'V', 'report', None)

    fig, (a1, a2) = plt.subplots(2, 1, figsize=(FIGW, 6.4), sharex=True)
    s = slice(None, None, 50)
    a1.plot(t[s] * 1e3, vbus[s], label='VBUS')
    a1.plot(t[s] * 1e3, vsys[s], label='VSYS')
    a1.plot(t[s] * 1e3, vbat[s], label='VBAT')
    if r.has('V(gate)'):
        a1.plot(t[s] * 1e3, r['V(gate)'][s], '--', label='Q1 gate')
    a1.axvspan(5, 15, color='grey', alpha=0.1)
    a1.set_ylabel('Voltage (V)')
    a1.set_ylim(0, 5.5)
    a1.legend(loc='lower left', ncol=4)
    a1.set_title('SIM03 %s power path: USB unplugged 5 - 15 ms (shaded), 300 mA on +3V3' % tag)
    a2.plot(t[s] * 1e3, v3[s], color='C7', lw=0.5, label='+3V3 (20 MHz BW)')
    a2.plot(tu * 1e3, va, color='C0', label='1-period average')
    a2.axhline(3.315 * 0.95, color='C3', ls='--', lw=0.8)
    a2.axhline(3.315 * 1.05, color='C3', ls='--', lw=0.8, label='+/- 5 %')
    a2.set_ylim(3.0, 3.7)
    a2.set_ylabel('+3V3 (V)')
    a2.set_xlabel('Time (ms)')
    a2.legend(loc='upper left', ncol=3)
    savefig(fig, 'sim03_powerpath_%s.png' % tag)

# ---- SIM03c replug mitigation ----
txt = read_log(lt('sim03c_replug_line_step.log')).replace('\r', '')


def table(name):
    lines = txt.split('\n')
    i = lines.index('Measurement: %s' % name)
    vals = []
    for ln in lines[i + 2:]:
        q = ln.split()
        if not q or not q[0].isdigit():
            break
        vals.append(float(q[1]))
    return vals


opts = ['C41 22 uF', 'C41 2 x 22 uF', 'C41 22 uF + 100 uF bulk']
vmax, vmin, idpk, vpk = table('v3_max'), table('v3_min'), table('id40_pk'), table('vsys_pk')
for o, a, b, c, d in zip(opts, vmax, vmin, idpk, vpk):
    res['replug_%s' % o.replace(' ', '_')] = check([round(b, 4), round(a, 4)], 'V (+3V3 min, max)', '3.149 - 3.481 V',
                                                   a <= 3.481 and b >= 3.149, 'D40 peak %.2f A, VSYS peak %.3f V' % (c, d))
r = RawRead(lt('sim03c_replug_line_step.raw'))
fig, (a1, a2) = plt.subplots(2, 1, figsize=(FIGW, 5.8), sharex=True)
for sl, o in zip(r.step_slices(), opts):
    t = r['time'][sl]
    m = (t > 1.95e-3) & (t < 2.4e-3)
    a1.plot((t[m] - 2e-3) * 1e6, r['V(vsys)'][sl][m], label=o)
    tu, va = movavg(t[m], r['V(ofilt)'][sl][m], TSW)
    a2.plot((tu - 2e-3) * 1e6, va, label=o)
a1.set_ylabel('VSYS (V)')
a1.legend(loc='lower right')
a1.set_title('SIM03c USB replug at t = 0 (battery -> USB), revised power path')
a2.axhline(3.315 * 1.05, color='C3', ls='--', lw=0.8, label='+5 %')
a2.set_ylabel('+3V3, 1-period avg (V)')
a2.set_xlabel('Time after replug (us)')
a2.legend(loc='upper right')
savefig(fig, 'sim03c_replug_options.png')

# ---- SIM03e gate pull-down study ----
r = RawRead(lt('sim03e_q1_gate_study.raw'))
r43s = [1e3, 2.2e3, 10e3, 100e3]   # LTspice ran the list in ascending order (checked against 5/R43 in the log)
lg = read_log(lt('sim03e_q1_gate_study.log')).replace(chr(13), '')
iu = [float(x.split()[1]) for x in lg.split('Measurement: i_usb_r43')[1].strip().split(chr(10))[1:5]]
assert all(abs(5 / a - b) < 1e-9 for a, b in zip(r43s, iu)), iu
fig, (a1, a2) = plt.subplots(2, 1, figsize=(FIGW, 5.8), sharex=True)
for sl, rv in zip(r.step_slices(), r43s):
    t = r['time'][sl]
    vb, vs, vbat = r['V(vbus)'][sl], r['V(vsys)'][sl], r['V(vbat)'][sl]
    m = t > 2e-3
    dv = vbat[m] - vs[m]
    k0 = np.where(dv > 0.3)[0]
    k = np.where(dv[k0[0]:] < 0.1)[0] + k0[0] if len(k0) else []
    ton = float(t[m][k[0]] - 2e-3) if len(k) else None
    res['gate_study_R43_%gk_q1_on_delay' % (rv / 1e3)] = check(None if ton is None else round(ton * 1e3, 2), 'ms',
        'report', None, ('not within 398 ms; VBUS at 400 ms = %.3f V' % vb[-1]) if ton is None else
        'USB current in R43 %.2f mA; VBUS at 400 ms = %.3f V' % (5 / rv * 1e3, vb[-1]))
    a1.plot(t * 1e3, vb, label='R43 = %g k' % (rv / 1e3))
    a2.plot(t * 1e3, vs, label='R43 = %g k' % (rv / 1e3))
a1.set_ylabel('VBUS = Q1 gate (V)')
a1.set_xscale('symlog', linthresh=10)
a1.legend(loc='upper right')
a1.set_title('SIM03e Q1 turn-on after unplug at 2 ms vs R43 (constant-power 1.06 W load)')
a2.set_ylabel('VSYS (V)')
a2.set_xlabel('Time (ms, linear to 10 ms then log)')
a2.legend(loc='lower right')
savefig(fig, 'sim03e_q1_gate_study.png')

update_results('SIM03_power_path', res)
for k, v in res.items():
    print(k, v)
