"""an_sim06_07.py - post-process SIM06 (haptic ERM) and SIM07 (buzzer)."""
import numpy as np
from common import *
from ltraw import RawRead, parse_meas
from runlt import read_log
import matplotlib.pyplot as plt


def table(log, name):
    lines = read_log(log).replace('\r', '').split('\n')
    i = lines.index('Measurement: %s' % name)
    vals = []
    for ln in lines[i + 2:]:
        p = ln.split()
        if not p or not p[0].isdigit():
            break
        vals.append(float(p[1]))
    return vals


# ---------- SIM06a sweep ----------
log = lt('sim06a_haptic_duty_sweep.log')
vm = table(log, 'vmot')
duties = [0.6, 0.7, 0.8, 0.9]
sweep = {'VSYS3.7': dict(zip(duties, vm[0::2])), 'VSYS4.6': dict(zip(duties, vm[1::2]))}
# ---------- SIM06b chosen duty ----------
log = lt('sim06b_haptic_erm.log')
names = ['vmot', 'imot', 'imot_pp', 'vdpk', 'vloc_pp', 'isys', 'tgr', 'tgf']
tb = {n: table(log, n) for n in names}
res = {'duty_sweep_vmotor_avg_V': {k: {str(d): round(v, 3) for d, v in s.items()} for k, s in sweep.items()}}
for i, (vs, duty) in enumerate(((3.7, 0.76), (4.6, 0.55))):
    p = 'VSYS%.1f_' % vs
    res[p + 'duty'] = check(duty * 100, '%', 'chosen for ~3.0 V average motor voltage', None)
    res[p + 'motor_avg_voltage'] = check(round(tb['vmot'][i], 3), 'V', '3.0 V +/- 0.1 V', abs(tb['vmot'][i] - 3.0) <= 0.1)
    res[p + 'motor_avg_current'] = check(round(tb['imot'][i] * 1e3, 1), 'mA', 'report', None)
    res[p + 'motor_current_ripple_pp'] = check(round(tb['imot_pp'][i] * 1e3, 1), 'mA p-p', 'report', None,
                                               'L/R = 6 us << 50 us period, so the current is near-discontinuous')
    res[p + 'drain_peak'] = check(round(tb['vdpk'][i], 3), 'V', '< 20 V (AO3400A VDS 30 V abs max)', tb['vdpk'][i] < 20)
    res[p + 'vsys_local_ripple_pp'] = check(round(tb['vloc_pp'][i] * 1e3, 2), 'mV p-p', 'report', None)
    res[p + 'vsys_avg_current'] = check(round(tb['isys'][i] * 1e3, 1), 'mA', 'report', None)
    res[p + 'gate_rise_10_90'] = check(round(tb['tgr'][i] * 1e9, 1), 'ns', 'report', None, 'includes Miller plateau; 100 ohm gate resistor')
    res[p + 'gate_fall_90_10'] = check(round(tb['tgf'][i] * 1e9, 1), 'ns', 'report', None)
update_results('SIM06_haptic_erm', res)
for k, v in res.items():
    print(k, v)

r = RawRead(lt('sim06b_haptic_erm.raw'))
fig, axs = plt.subplots(3, 1, figsize=(FIGW, 7.2), sharex=True)
for (sl, vs, duty, col) in zip(r.step_slices(), (3.7, 4.6), (76, 55), ('C0', 'C1')):
    t = r['time'][sl]
    m = (t > 3.5e-3) & (t < 3.5e-3 + 3 / 20e3)
    tt = (t[m] - 3.5e-3) * 1e6
    axs[0].plot(tt, r['V(drain)'][sl][m], color=col, label='VSYS %.1f V, duty %d %%' % (vs, duty))
    axs[1].plot(tt, r['I(RM)'][sl][m] * 1e3, color=col)
    axs[2].plot(tt, r['V(gate)'][sl][m], color=col)
axs[0].set_ylabel('Drain (V)')
axs[0].legend(loc='upper right')
axs[0].set_title('SIM06b ERM driver, AO3400A + 1N5819, 20 kHz, ~3.0 V average on the motor')
axs[1].set_ylabel('Motor current (mA)')
axs[2].set_ylabel('Gate (V)')
axs[2].set_xlabel('Time (us)')
savefig(fig, 'sim06_haptic_erm.png')

# ---------- SIM07 ----------
mz = parse_meas(lt('sim07_buzzer.log'))
res7 = {
    'drain_peak': check(round(mz['vdpk'], 3), 'V', '< 20 V (AO3400A VDS 30 V abs max)', mz['vdpk'] < 20),
    'rail_3v3_ripple_pp': check(round(mz['v33_pp'] * 1e3, 2), 'mV p-p', 'report', None,
                                '+3V3 modelled as ideal 3.315 V behind 50 mohm with 22 uF (10 uF eff) local; converter loop not included'),
    'buzzer_peak_current': check(round(mz['ibz_pk'] * 1e3, 1), 'mA', 'report', None),
    'buzzer_avg_current': check(round(mz['ibz_avg'] * 1e3, 1), 'mA', 'report', None),
    'flyback_peak_current': check(round(mz['id80_pk'] * 1e3, 1), 'mA', '< 1N4148 rating (Iave 200 mA model)', None),
}
update_results('SIM07_buzzer', res7)
for k, v in res7.items():
    print(k, v)
r = RawRead(lt('sim07_buzzer.raw'))
t = r['time']
m = (t > 18e-3) & (t < 19e-3)
fig, (a1, a2) = plt.subplots(2, 1, figsize=(FIGW, 5.2), sharex=True)
a1.plot((t[m] - 18e-3) * 1e3, r['V(drain)'][m], label='Q3 drain')
a1.plot((t[m] - 18e-3) * 1e3, r['V(v33)'][m], label='+3V3 at C80')
a1.set_ylabel('Voltage (V)')
a1.legend(loc='center right')
a1.set_title('SIM07 buzzer 16 ohm + 1 mH, 4 kHz 50 %%: drain peak %.2f V, rail ripple %.1f mV p-p' %
             (mz['vdpk'], mz['v33_pp'] * 1e3))
a2.plot((t[m] - 18e-3) * 1e3, r['I(RBZ)'][m] * 1e3, color='C2', label='Buzzer current')
a2.plot((t[m] - 18e-3) * 1e3, r['I(D80)'][m] * 1e3, color='C3', label='Flyback 1N4148')
a2.set_ylabel('Current (mA)')
a2.set_xlabel('Time (ms)')
a2.legend(loc='upper right')
savefig(fig, 'sim07_buzzer.png')
