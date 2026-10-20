"""an_sim01.py - post-process SIM01 (LTC3536 3.3 V buck-boost)."""
import sys
import numpy as np
from vw_mtc1.common import *
from vw_mtc1.ltraw import RawRead, parse_meas
import matplotlib.pyplot as plt

TSW = 1 / 1.2e6
tag = sys.argv[1] if len(sys.argv) > 1 else ''   # '' = proposed values
res = {}


from vw_mtc1.waveform import moving_average as movavg


# ---------- start-up ----------
r = RawRead(lt('sim01a_buckboost_startup.raw'))
mz = parse_meas(lt('sim01a_buckboost_startup.log'))
t, vf, vo, iin = r['time'], r['V(ofilt)'], r['V(out)'], r['I(Rsrc)']
vfinal = mz['vfinal']
tu, va = movavg(t, vf, TSW)
os_avg = (va[tu > 0.3e-3].max() - vfinal) / vfinal * 100
os_f = (mz['vmaxf'] - vfinal) / vfinal * 100
res['startup_vout_final'] = check(round(vfinal, 4), 'V', '3.315 V nominal +/- 1 %', abs(vfinal - 3.315) < 0.033)
res['startup_overshoot_switching_avg'] = check(round(os_avg, 3), '%', '< 3 %', os_avg < 3,
                                               'one-switching-period average of the 20 MHz-limited rail')
res['startup_overshoot_peak_20MHz'] = check(round(os_f, 3), '%', '< 3 %', os_f < 3,
                                            'includes switching ripple peak')
res['startup_raw_spike_peak'] = check(round(mz['vmaxraw'], 3), 'V', 'report (ESL spikes, full bandwidth)', None,
                                      'ideal-switch edges into 0.5 nH ESL; not representative of a scope reading with 20 MHz limit')
res['startup_t10_to_t90'] = check(round((mz['t90'] - mz['t10']) * 1e3, 3), 'ms', 'report (soft start)', None)
res['startup_time_to_99pct'] = check(round(mz['tsettle'] * 1e3, 3), 'ms', 'report', None)
res['startup_input_current_peak'] = check(round(mz['iinpk'], 3), 'A', 'report', None,
                                           'C28 charging during the 20 us LTspice startup source ramp (simulation artefact, not converter inrush)')

fig, (a1, a2) = plt.subplots(2, 1, figsize=(FIGW, 5.6), sharex=True)
a1.plot(t * 1e3, vo, color='C7', lw=0.4, alpha=0.5, label='V(out) raw (ESL switching spikes)')
a1.plot(t * 1e3, vf, color='C0', lw=0.8, label='+3V3, 20 MHz BW limit')
a1.axhline(3.315 * 1.03, color='C3', ls='--', lw=0.8, label='+3 % overshoot limit')
a1.set_ylim(0, 3.9)
a1.set_ylabel('Voltage (V)')
a1.set_title('SIM01a LTC3536 start-up, VIN 3.7 V, 11 ohm (300 mA) load, PWM: overshoot %.2f %%' % os_avg)
a1.legend(loc='lower right')
tu2, ia = movavg(t, iin, TSW)
a2.plot(tu2 * 1e3, ia, color='C1', label='Input current (1-period average)')
a2.set_ylabel('Current (A)')
a2.set_xlabel('Time (ms)')
a2.legend(loc='upper right')
savefig(fig, 'sim01a_startup%s.png' % tag)

# ---------- load step ----------
r = RawRead(lt('sim01b_buckboost_loadstep.raw'))
mz = parse_meas(lt('sim01b_buckboost_loadstep.log'))
vins = [3.0, 3.7, 4.6]
fig, axs = plt.subplots(3, 1, figsize=(FIGW, 8.2), sharex=True)
for i, (sl, vin) in enumerate(zip(r.step_slices(), vins)):
    t, vf = r['time'][sl], r['V(ofilt)'][sl]
    m = t > 1.7e-3
    t, vf = t[m], vf[m]
    tu, va = movavg(t, vf, TSW)
    vpre = np.mean(va[(tu > 1.8e-3) & (tu < 2.0e-3)])
    vhi = np.mean(va[(tu > 2.4e-3) & (tu < 2.6e-3)])
    vpost = np.mean(va[(tu > 3.0e-3) & (tu < 3.19e-3)])
    out = {}
    for name, t0, t1, vref in (('up', 2.0e-3, 2.6e-3, vhi), ('down', 2.6e-3, 3.19e-3, vpost)):
        w = (tu >= t0) & (tu < t1)
        dev = va[w] - vref
        outside = np.where(np.abs(dev) > 0.01 * 3.315)[0]
        trec = (tu[w][outside[-1]] - t0) if len(outside) else 0.0
        # ringing: count alternating extrema of the period-averaged deviation > 3 mV
        d = dev
        ext = []
        s = np.sign(d)
        for j in range(1, len(d) - 1):
            if (d[j] - d[j - 1]) * (d[j + 1] - d[j]) < 0 and abs(d[j]) > 3e-3:
                if not ext or np.sign(d[j]) != np.sign(ext[-1][1]):
                    ext.append((tu[w][j], d[j]))
                elif abs(d[j]) > abs(ext[-1][1]):
                    ext[-1] = (tu[w][j], d[j])
        out[name] = (trec, len(ext), ext)
    vmin_f = float(vf[(t >= 2.0e-3) & (t < 2.6e-3)].min())
    vmax_f = float(vf[(t >= 2.6e-3)].max())
    vmin_a = float(va[(tu >= 2.0e-3) & (tu < 2.6e-3)].min())
    vmax_a = float(va[(tu >= 2.6e-3)].max())
    k = 'vin_%.1fV' % vin
    res['loadstep_%s_vmin' % k] = check(round(vmin_f, 4), 'V', '>= 3.13 V', vmin_f >= 3.13,
                                         '20 MHz BW, includes ripple; 1-period average %.4f V' % vmin_a)
    res['loadstep_%s_vmax' % k] = check(round(vmax_f, 4), 'V', '<= 3.48 V', vmax_f <= 3.48,
                                         '20 MHz BW, includes ripple; 1-period average %.4f V' % vmax_a)
    res['loadstep_%s_dip_pct' % k] = check(round((vmin_f - vpre) / vpre * 100, 2), '%', '>= -5 %', vmin_f >= 3.13)
    res['loadstep_%s_overshoot_pct' % k] = check(round((vmax_f - vhi) / vhi * 100, 2), '%', '<= +5 %', vmax_f <= 3.48)
    res['loadstep_%s_recovery_up' % k] = check(round(out['up'][0] * 1e6, 1), 'us', 'report (to within +/- 1 %)', None)
    res['loadstep_%s_recovery_down' % k] = check(round(out['down'][0] * 1e6, 1), 'us', 'report (to within +/- 1 %)', None)
    nr = max(out['up'][1], out['down'][1])
    res['loadstep_%s_ringing_extrema' % k] = check(nr, 'alternating extrema > 3 mV', '<= 3 (i.e. no more than ~1.5 cycles)',
                                                    nr <= 3, 'up: %d, down: %d' % (out['up'][1], out['down'][1]))
    res['loadstep_%s_load_regulation' % k] = check(round((vhi - vpre) * 1e3, 2), 'mV', 'report (50 -> 600 mA DC shift)', None)
    ax = axs[i]
    ax.plot((t - 2e-3) * 1e6, vf, color='C7', lw=0.4, alpha=0.6, label='+3V3, 20 MHz BW')
    ax.plot((tu - 2e-3) * 1e6, va, color='C0', lw=1.2, label='1-switching-period average')
    ax.axhline(3.13, color='C3', ls='--', lw=0.8)
    ax.axhline(3.48, color='C3', ls='--', lw=0.8, label='+/- 5 % limits')
    ax.set_ylim(3.10, 3.50)
    ax.set_ylabel('Vout (V)')
    ax.set_title('VIN = %.1f V: min %.3f V, max %.3f V, recovery %.0f / %.0f us' %
                 (vin, vmin_f, vmax_f, out['up'][0] * 1e6, out['down'][0] * 1e6))
    if i == 0:
        ax.legend(loc='upper right', ncol=3)
axs[-1].set_xlabel('Time from 50 -> 600 mA step (us); 600 -> 50 mA at 600 us')
axs[-1].set_xlim(-100, 1150)
fig.suptitle('SIM01b LTC3536 load step 50 mA <-> 600 mA, 1 us edges, PWM' + (' (%s)' % tag if tag else ''), fontsize=11)
savefig(fig, 'sim01b_loadstep%s.png' % tag)

# ---------- ripple / efficiency ----------
mz = parse_meas(lt('sim01c_buckboost_ripple_eff.log'))
r = RawRead(lt('sim01c_buckboost_ripple_eff.raw'))
loads = [0.05, 0.3, 0.6]
# parse stepped .meas tables from the log
from vw_mtc1.runlt import read_log
txt = read_log(lt('sim01c_buckboost_ripple_eff.log')).replace('\r', '')


def table(name):
    lines = txt.split('\n')
    i = lines.index('Measurement: %s' % name)
    vals = []
    for ln in lines[i + 2:]:
        p = ln.split()
        if not p or not p[0].isdigit():
            break
        vals.append(float(p[1]))
    return vals


eff = table('eff'); pin = table('pin'); pout = table('pout'); rpf = table('rpp_f'); rpr = table('rpp_raw')
for il, e, a, b in zip(loads, eff, pin, pout):
    res['eff_pwm_vin3p7_%dmA' % int(il * 1000)] = check(round(e * 100, 2), '%', 'report', None,
                                                        'Pin %.4f W, Pout %.4f W' % (a, b))
# ripple at 300 mA
sl = r.step_slices()[1]
t, vf, vo = r['time'][sl], r['V(ofilt)'][sl], r['V(out)'][sl]
res['ripple_pwm_300mA_pp_20MHz'] = check(round(rpf[1] * 1e3, 2), 'mV p-p', 'report (no limit given; ESP32-S3 tolerates far more)', None)
res['ripple_pwm_300mA_pp_fullBW'] = check(round(rpr[1] * 1e3, 1), 'mV p-p', 'report', None,
                                          'dominated by ideal-switch-edge ESL spikes in the model')
res['ripple_pwm_50mA_pp_20MHz'] = check(round(rpf[0] * 1e3, 2), 'mV p-p', 'report', None)
res['ripple_pwm_600mA_pp_20MHz'] = check(round(rpf[2] * 1e3, 2), 'mV p-p', 'report', None)

fig, ax = plt.subplots(figsize=(FIGW, 3.4))
m = (t > 2.9e-3) & (t < 2.9e-3 + 6 * TSW)
ax.plot((t[m] - 2.9e-3) * 1e6, vo[m] * 1e3 - 3315, color='C7', lw=0.5, alpha=0.6, label='raw node (full BW)')
ax.plot((t[m] - 2.9e-3) * 1e6, vf[m] * 1e3 - 3315, color='C0', lw=1.2, label='20 MHz BW: %.1f mV p-p' % (rpf[1] * 1e3))
ax.set_ylim(-60, 60)
ax.set_xlabel('Time (us)')
ax.set_ylabel('Vout - 3.315 V (mV)')
ax.set_title('SIM01c output ripple, VIN 3.7 V, 300 mA, PWM')
ax.legend(loc='upper right')
savefig(fig, 'sim01c_ripple_300mA.png')

# Burst mode
mzb = parse_meas(lt('sim01d_buckboost_burst.log'))
res['burst_20mA_eff'] = check(round(mzb['eff'] * 100, 2), '%', 'report', None,
                              'Pin %.4f W, Pout %.4f W' % (mzb['pin'], mzb['pout']))
res['burst_20mA_ripple_pp_20MHz'] = check(round(mzb['rpp_f'] * 1e3, 2), 'mV p-p', 'report', None)
res['burst_20mA_vavg'] = check(round(mzb['vavg'], 4), 'V', 'within +/- 5 %', abs(mzb['vavg'] - 3.315) < 0.166)
rb = RawRead(lt('sim01d_buckboost_burst.raw'))
t, vf = rb['time'], rb['V(ofilt)']
fig, ax = plt.subplots(figsize=(FIGW, 3.4))
m = (t > 6e-3) & (t < 6.5e-3)
ax.plot((t[m] - 6e-3) * 1e6, vf[m], color='C0', lw=0.8)
ax.set_xlabel('Time (us)')
ax.set_ylabel('+3V3, 20 MHz BW (V)')
ax.set_title('SIM01d Burst Mode, VIN 3.7 V, 20 mA: %.1f mV p-p, efficiency %.1f %%' % (mzb['rpp_f'] * 1e3, mzb['eff'] * 100))
savefig(fig, 'sim01d_burst_20mA.png')

fig, ax = plt.subplots(figsize=(FIGW, 3.6))
ax.plot(np.array(loads) * 1e3, np.array(eff) * 100, 'o-', color='C0', label='PWM (MODE = 0), VIN 3.7 V')
ax.plot([20], [mzb['eff'] * 100], 's', color='C1', ms=8, label='Burst Mode, VIN 3.7 V')
for x, y in zip(np.array(loads) * 1e3, np.array(eff) * 100):
    ax.annotate('%.1f %%' % y, (x, y), xytext=(4, -12), textcoords='offset points', fontsize=8)
ax.annotate('%.1f %%' % (mzb['eff'] * 100), (20, mzb['eff'] * 100), xytext=(6, -4), textcoords='offset points', fontsize=8)
ax.set_xlabel('Load current (mA)')
ax.set_ylabel('Efficiency Pout/Pin (%)')
ax.set_ylim(60, 100)
ax.set_xlim(0, 650)
ax.set_title('SIM01 LTC3536 efficiency (ADI macro-model, L1 DCR 24 mohm)')
ax.legend(loc='lower right')
savefig(fig, 'sim01c_efficiency.png')

key = 'SIM01_buckboost' + ('_' + tag if tag else '')
update_results(key, res)
for k, v in res.items():
    print(k, v)
