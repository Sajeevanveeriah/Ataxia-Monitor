"""an_sim02.py - post-process SIM02 (LTC4054 charger) and SIM02b (hot-plug)."""
import numpy as np
from common import *
from ltraw import RawRead, parse_meas
import matplotlib.pyplot as plt

res = {}
r = RawRead(lt('sim02a_charger_cccv.raw'))
mz = parse_meas(lt('sim02a_charger_cccv.log'))
t, vb, vc, ib, iled, vchrg = r['time'], r['V(bat)'], r['V(cell)'], r['I(Rint)'], r['I(D20)'], r['V(chrg)']
icc = mz['i_cc']
icalc = 1000 * 1.0 / 2.49e3
res['cc_current'] = check(round(icc * 1e3, 1), 'mA', '402 mA +/- 7 % (374-430 mA)', 374e-3 <= icc <= 430e-3,
                          'calc 1000 x 1 V / 2.49 k = %.1f mA' % (icalc * 1e3))
res['trickle_current'] = check(round(mz['i_trickle'] * 1e3, 1), 'mA', 'report (expected ~C/10 below ~2.9 V; from memory of the datasheet, not re-checked)', None)
# trickle -> CC threshold
k = np.where(ib > 0.2)[0][0]
res['trickle_to_cc_vbat'] = check(round(float(vb[k]), 3), 'V', 'report (expected ~2.9 V; from memory, not re-checked)', None)
# CV voltage: BAT pin voltage while in CV phase (current between 380 and 50 mA, after CC)
m_cv = (ib < 0.30) & (ib > 0.06) & (t > 3)
vcv = float(np.median(vb[m_cv]))
res['cv_voltage'] = check(round(vcv, 4), 'V', '4.2 V +/- 1 % (4.158-4.242 V)', 4.158 <= vcv <= 4.242)
# termination: last sample with current above 1 mA after CV phase
idx = np.where((ib > 1e-3) & (t > 3))[0]
kt = idx[-1]
# current just before the drop (average over 5 ms before)
w = (t > t[kt] - 5e-3) & (t <= t[kt] - 0.2e-3)
iterm = float(np.mean(ib[w]))
res['termination_current'] = check(round(iterm * 1e3, 1), 'mA', 'about 40 mA (C/10 of 402 mA); +/- 25 % (30-50 mA)',
                                   30e-3 <= iterm <= 50e-3,
                                   'terminated at t = %.3f s (scaled time) with V(PROG) = %.1f mV; the ADI macro-model '
                                   'terminates at V(PROG) ~ 80 mV and its IBAT/IPROG ratio falls to ~895 at low current. '
                                   'Fixed by the IC, not by board values; datasheet C/10 limits not checked here' % (t[kt], float(np.mean(r['V(prog)'][w])) * 1e3))
res['led_current_charging'] = check(round(float(np.median(iled[(t > 1) & (t < 3)])) * 1e3, 2), 'mA', 'report', None)
res['led_current_after_termination'] = check(round(float(np.mean(iled[t > t[kt] + 0.1])) * 1e6, 3), 'uA', 'report (CHRG high-Z)', None)

fig, (a1, a2) = plt.subplots(2, 1, figsize=(FIGW, 6), sharex=True)
a1.plot(t, vb, label='V(BAT pin)')
a1.plot(t, vc, '--', label='Cell OCV (scaled 1.5 F model)')
a1.axhline(4.2, color='C3', ls=':', lw=0.8)
a1.set_ylabel('Voltage (V)')
a1.set_title('SIM02a LTC4054-4.2 charge cycle, RPROG 2.49 k (time scaled by 1.5 F cell)')
a1.legend(loc='lower right')
a2.plot(t, ib * 1e3, color='C2', label='Charge current')
a2.plot(t, iled * 1e3 * 100, color='C3', lw=0.8, label='CHRG LED current x100')
a2.axhline(40, color='grey', ls=':', lw=0.8)
a2.annotate('CC %.0f mA' % (icc * 1e3), (3, icc * 1e3), xytext=(0, 6), textcoords='offset points', fontsize=8)
a2.annotate('terminates at %.1f mA' % (iterm * 1e3), (t[kt], iterm * 1e3), xytext=(-140, 20), textcoords='offset points',
            fontsize=8, arrowprops=dict(arrowstyle='->', lw=0.6))
a2.set_ylabel('Current (mA)')
a2.set_ylim(-20, 460)
a2.set_xlabel('Time (s, scaled)')
a2.legend(loc='center left')
savefig(fig, 'sim02a_charger_cccv.png')

# ---- thermal CALCULATION (not a simulation) ----
calc = {}
for vbat in (3.0, 3.7):
    p = (5.0 - vbat) * 0.4
    for tja in (80, 125):
        for ta in (25, 40):
            tj = ta + p * tja
            calc['VBAT%.1f_thetaJA%d_Ta%d' % (vbat, tja, ta)] = {
                'P_W': round(p, 3), 'Tj_C': round(tj, 1), 'thermal_regulation_engages': tj >= 120}
res['thermal_calc_NOT_SIMULATED'] = calc

# ---- hot plug ----
r = RawRead(lt('sim02b_usb_hotplug.raw'))
mz = parse_meas(lt('sim02b_usb_hotplug.log'))
t = r['time']
res['hotplug_peak_10uF_ceramic_only'] = check(round(mz['vpk_i'], 3), 'V', '< 10 V (LTC4054 VCC abs max as recalled, not re-checked against the datasheet)', mz['vpk_i'] < 10)
res['hotplug_peak_10uF_plus_1R5'] = check(round(mz['vpk_ii'], 3), 'V', 'report', mz['vpk_ii'] < 10)
res['hotplug_peak_10uF_1R5_plus_1uF_pin'] = check(round(mz['vpk_iii'], 3), 'V', 'report', mz['vpk_iii'] < 10,
                                                   'board configuration (1 uF at the VCC pin rings with the cable inductance)')
fig, ax = plt.subplots(figsize=(FIGW, 3.6))
for n, lab, v in (('V(vb1)', '(i) 10 uF ceramic only', mz['vpk_i']), ('V(vb2)', '(ii) 10 uF + 1.5 ohm', mz['vpk_ii']),
                  ('V(vb3)', '(iii) 10 uF + 1.5 ohm, plus 1 uF at pin', mz['vpk_iii'])):
    ax.plot((t - 10e-6) * 1e6, r[n], label='%s: peak %.2f V' % (lab, v))
ax.set_xlim(-5, 120)
ax.set_xlabel('Time after plug-in (us)')
ax.set_ylabel('VCC (V)')
ax.set_title('SIM02b USB hot-plug through 1 uH / 100 mohm cable')
ax.legend(loc='upper right')
savefig(fig, 'sim02b_usb_hotplug.png')

update_results('SIM02_charger', res)
for k, v in res.items():
    print(k, v)
