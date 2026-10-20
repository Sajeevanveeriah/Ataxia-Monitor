"""an_sim04.py - post-process SIM04 (Hall analogue front end)."""
import numpy as np
from common import *
from ltraw import RawRead
import matplotlib.pyplot as plt

res = {}
# ---------------- AC ----------------
r = RawRead(lt('sim04a_hall_afe_ac.raw'))
f = np.real(r['frequency'])
H = r['V(adc)']
mag = 20 * np.log10(np.abs(H))
ph = np.unwrap(np.angle(H))
w = 2 * np.pi * f
gd = -np.gradient(ph, w)


def at(x, y, x0):
    return float(np.interp(np.log10(x0), np.log10(x), y))


f3 = float(np.interp(-3.0103, mag[::-1], f[::-1]))  # monotonic fall region
# use first crossing explicitly
k = np.where(mag < -3.0103)[0][0]
f3 = float(np.exp(np.interp(-3.0103, [mag[k], mag[k - 1]], [np.log(f[k]), np.log(f[k - 1])])))
# Q from |H| at the -90 degree frequency (2nd-order low-pass: |H(f0)| = Q)
phd = np.degrees(ph)
k90 = np.where(phd < -90)[0][0]
f0 = float(np.exp(np.interp(-90, [phd[k90], phd[k90 - 1]], [np.log(f[k90]), np.log(f[k90 - 1])])))
Q = 10 ** (at(f, mag, f0) / 20)
peak_db = float(mag.max())
g50, g1k, g1m2 = at(f, mag, 50), at(f, mag, 1e3), at(f, mag, 1.2e6)
gd10 = at(f, gd, 10)
fc_exp = 1 / (2 * np.pi * 10e3 * np.sqrt(100e-9 * 47e-9))

res['ac_f_minus3dB'] = check(round(f3, 1), 'Hz', 'expected 232 Hz (calc)', abs(f3 - fc_exp) / fc_exp < 0.1,
                             'f0 (-90 deg) = %.1f Hz' % f0)
res['ac_Q'] = check(round(Q, 3), '-', 'expected 0.73 (calc)', abs(Q - 0.73) < 0.05)
res['ac_peaking'] = check(round(peak_db, 4), 'dB', '< 0.5 dB', peak_db < 0.5)
res['ac_gain_50Hz'] = check(round(g50, 3), 'dB', 'passband, > -0.5 dB', g50 > -0.5)
res['ac_gain_1kHz'] = check(round(g1k, 2), 'dB', 'report (Nyquist 1 kHz)', None)
res['ac_gain_1p2MHz'] = check(round(g1m2, 2), 'dB', 'report', None,
                              'Sallen-Key high-frequency feed-through limited by op-amp model output impedance and GBW')
res['ac_group_delay_10Hz'] = check(round(gd10 * 1e3, 3), 'ms', '< 2 ms', gd10 < 2e-3)

fig, (a1, a2) = plt.subplots(2, 1, figsize=(FIGW, 6.2), sharex=True)
a1.semilogx(f, mag, color='C0')
a1.axhline(-3, color='grey', ls=':', lw=0.8)
for fx, lab in [(50, '50 Hz'), (1e3, '1 kHz (Nyquist)'), (1.2e6, '1.2 MHz')]:
    a1.axvline(fx, color='C3', ls='--', lw=0.7)
    a1.annotate('%s: %.1f dB' % (lab, at(f, mag, fx)), (fx, at(f, mag, fx)), xytext=(5, 8),
                textcoords='offset points', fontsize=8, color='C3')
a1.axvline(f3, color='C2', ls='--', lw=0.7)
a1.annotate('-3 dB at %.0f Hz' % f3, (f3, -3), xytext=(5, -15), textcoords='offset points', fontsize=8, color='C2')
a1.set_ylabel('Gain (dB)')
a1.set_ylim(-90, 5)
a1.set_title('SIM04a Hall front end: Sallen-Key LPF (10 k / 10 k, 100 nF / 47 nF), U6 generic MCP6004 model')
a2.semilogx(f, np.degrees(ph), color='C0', label='Phase')
a2.set_ylabel('Phase (deg)')
a3 = a2.twinx()
a3.semilogx(f, gd * 1e3, color='C1', label='Group delay')
a3.set_ylabel('Group delay (ms)', color='C1')
a3.set_ylim(0, 1.5)
a3.grid(False)
a2.set_xlabel('Frequency (Hz)')
a2.set_xlim(1, 1e7)
a2.annotate('group delay at 10 Hz = %.3f ms' % (gd10 * 1e3), (10, 0), xytext=(5, -40),
            textcoords='offset points', fontsize=8, color='C1')
savefig(fig, 'sim04a_hall_afe_bode.png')

# ---------------- ripple (SIM04c) ----------------
rr = RawRead(lt('sim04c_hall_afe_ripple.raw'))
tr = rr['time']
m = tr >= 20e-3
tu = np.arange(20e-3, 22e-3, 5e-9)
rip_old = np.interp(tu, tr, rr['V(adc_old)']) - 1.65
rip_new = np.interp(tu, tr, rr['V(adc_new)'])
rip_new = rip_new - rip_new.mean()
rip_old_rms = float(np.sqrt(np.mean((rip_old - rip_old.mean()) ** 2)))
rip_new_rms = float(np.sqrt(np.mean(rip_new ** 2)))
rip_old_pp = float(np.ptp(rip_old))
rip_new_pp = float(np.ptp(rip_new))
res['ripple_1p2MHz_old_pp'] = check(round(rip_old_pp * 1e3, 3), 'mV p-p', 'report', None)
res['ripple_1p2MHz_new_pp'] = check(round(rip_new_pp * 1e3, 4), 'mV p-p', 'report', None)

# ---------------- transient (SIM04b) ----------------
r = RawRead(lt('sim04b_hall_afe_tran.raw'))
t = r['time']
sc, nz = r['V(sc)'], r['V(nz)']
old, new, cl = r['V(adc_old)'], r['V(adc_new)'], r['V(adc_cl)']
centres = (50 + 103.7 * np.arange(10)) * 1e-3
TEND = 1040e-3
TS = 0.5e-3  # 2 kS/s per channel

# continuous-time noise check
tu = np.arange(20e-3, TEND, 2e-6)
nzu = np.interp(tu, t, nz)
bb = nzu - 10e-3 * np.sin(2 * np.pi * 50 * tu)
noise_in_rms = float(np.sqrt(np.mean(bb ** 2)))

offsets = np.arange(0, TS, TS / 20)
err_old, err_new, err_old_i, err_new_i = [], [], [], []
n_old_s, n_new_s = [], []
for off in offsets:
    ts = np.arange(20e-3 + off, TEND - 5e-3, TS)
    so = np.interp(ts, t, old)
    sn = np.interp(ts, t, new)
    n_old_s.append(so - np.interp(ts, t, sc))
    n_new_s.append(sn - np.interp(ts, t, cl))
    for c in centres:
        w_ = (ts > c - 40e-3) & (ts < c + 40e-3)
        for s, eo, ei in ((so, err_old, err_old_i), (sn, err_new, err_new_i)):
            idx = np.where(w_)[0]
            j = idx[np.argmax(s[idx])]
            eo.append(ts[j] - c)
            y0, y1, y2 = s[j - 1], s[j], s[j + 1]
            den = (y0 - 2 * y1 + y2)
            d = 0.5 * (y0 - y2) / den if den != 0 else 0
            ei.append(ts[j] + d * TS - c)
n_old_s = np.concatenate(n_old_s)
n_new_s = np.concatenate(n_new_s)
# remove the small DC offset of the filtered path (1 M pull-down divider) from noise
n_old_rms_lf = float(np.sqrt(np.mean((n_old_s - n_old_s.mean()) ** 2)))
n_new_rms_lf = float(np.sqrt(np.mean((n_new_s - n_new_s.mean()) ** 2)))
# combine with 1.2 MHz ripple (uncorrelated -> rms sum); ripple aliases on sampling
n_old_rms = float(np.hypot(n_old_rms_lf, rip_old_rms))
n_new_rms = float(np.hypot(n_new_rms_lf, rip_new_rms))
snr_old = float(20 * np.log10(0.8 / n_old_rms))
snr_new = float(20 * np.log10(0.8 / n_new_rms))
err_old, err_new = np.array(err_old), np.array(err_new)
err_old_i, err_new_i = np.array(err_old_i), np.array(err_new_i)


# systematic delay of each path = peak time of its noise-free output
k0 = (t > centres[1] - 20e-3) & (t < centres[1] + 20e-3)
tpk_clean_new = float(t[k0][np.argmax(cl[k0])] - centres[1])
tpk_clean_old = 0.0  # old path is the sensor itself (100 ohm into a high-Z ADC pin)


def stats(e, d0):
    x = e - d0  # error about the known systematic delay
    return float(x.mean()), float(np.sqrt(np.mean(x ** 2))), float(np.abs(x).max())


so_ = stats(err_old, tpk_clean_old); sn_ = stats(err_new, tpk_clean_new)
soi = stats(err_old_i, tpk_clean_old); sni = stats(err_new_i, tpk_clean_new)

res['tran_input_broadband_noise_rms'] = check(round(noise_in_rms * 1e3, 2), 'mV rms', 'target 20 mV rms', None)
res['tran_noise_rms_old'] = check(round(n_old_rms * 1e3, 3), 'mV rms', 'report', None,
                                  'sampled at 2 kS/s; broadband + 50 Hz + 1.2 MHz ripple (rms-combined from SIM04c)')
res['tran_noise_rms_new'] = check(round(n_new_rms * 1e3, 3), 'mV rms', 'lower than old', n_new_rms < n_old_rms)
res['tran_snr_old'] = check(round(snr_old, 2), 'dB', 'report (0.8 V peak / noise rms)', None)
res['tran_snr_new'] = check(round(snr_new, 2), 'dB', 'report', None)
res['tran_snr_improvement'] = check(round(snr_new - snr_old, 2), 'dB', '> 0 dB', snr_new > snr_old)
res['tran_peak_time_mean_error_old'] = check(round(so_[0] * 1e3, 4), 'ms', 'report (mean error about known delay)', None)
res['tran_peak_time_mean_error_new'] = check(round(sn_[0] * 1e3, 4), 'ms', 'report (mean error about known delay)', None)
res['tran_peak_time_error_rms_old'] = check(round(so_[1] * 1e3, 4), 'ms rms', 'report (max-sample method)', None)
res['tran_peak_time_error_rms_new'] = check(round(sn_[1] * 1e3, 4), 'ms rms', 'report (max-sample method)', None)
res['tran_peak_time_error_max_old'] = check(round(so_[2] * 1e3, 4), 'ms', 'report', None)
res['tran_peak_time_error_max_new'] = check(round(sn_[2] * 1e3, 4), 'ms', 'report', None)
res['tran_peak_time_error_rms_old_interp'] = check(round(soi[1] * 1e3, 4), 'ms rms', 'report (3-point parabolic interpolation)', None)
res['tran_peak_time_error_rms_new_interp'] = check(round(sni[1] * 1e3, 4), 'ms rms', 'report (3-point parabolic interpolation)', None)
res['tran_peak_time_error_max_old_interp'] = check(round(soi[2] * 1e3, 4), 'ms', 'report', None)
res['tran_peak_time_error_max_new_interp'] = check(round(sni[2] * 1e3, 4), 'ms', 'report', None)
res['tran_clean_peak_delay_new'] = check(round(tpk_clean_new * 1e3, 4), 'ms', '< 2 ms (fixed filter delay, can be subtracted in firmware)', tpk_clean_new < 2e-3)
res['_n_peak_estimates_per_design'] = len(err_old)

# ---------------- settling (SIM04d) ----------------
r = RawRead(lt('sim04d_adc_settling.raw'))
t = r['time']; v = r['V(csamp)']; a = r['V(adc)']
vf = float(np.mean(v[t > 1.015e-3]))
m = t > 1e-3
e = np.abs(v[m] - vf)
bad = np.where(e > 0.4e-3)[0]
ts_settle = float(t[m][bad[-1]] - 1e-3) if len(bad) else 0.0
dip = float(np.interp(0.9999e-3, t, a) - a[m].min())
res['adc_sample_settling_0p5LSB'] = check(round(ts_settle * 1e6, 3), 'us', '< 1.5 us', ts_settle < 1.5e-6,
                                          'generic op-amp model; real MCP6004 open-loop output impedance not modelled')
res['adc_kick_dip_at_opamp_output'] = check(round(dip * 1e3, 2), 'mV', 'report', None)

fig, ax = plt.subplots(figsize=(FIGW, 3.6))
tt = (t[m] - 1e-3) * 1e6
ax.plot(tt, (v[m] - vf) * 1e3, label='V(Csample) - final')
ax.plot(tt, (a[m] - vf) * 1e3, label='U6 output - final', alpha=0.8)
ax.axhspan(-0.4, 0.4, color='C2', alpha=0.2, label='+/- 0.5 LSB (0.40 mV)')
ax.axvline(1.5, color='C3', ls='--', lw=0.8, label='1.5 us sample window')
ax.set_xlim(0, 3)
ax.set_ylim(-5, 5)
ax.set_xlabel('Time after sample switch closes (us)')
ax.set_ylabel('Error (mV)')
ax.set_title('SIM04d MCP3204 sample kick-back (20 pF via 1 k, 0 V -> 2.45 V): settles in %.2f us' % (ts_settle * 1e6))
ax.legend(loc='upper right')
savefig(fig, 'sim04d_adc_sample_settling.png')

# ---------------- transient plot ----------------
r = RawRead(lt('sim04b_hall_afe_tran.raw'))
t = r['time']
c1 = centres[1]
m = (t > c1 - 40e-3) & (t < c1 + 40e-3)
fig, (a1, a2) = plt.subplots(2, 1, figsize=(FIGW, 6.4))
a1.plot((t[m] - c1) * 1e3, r['V(adc_old)'][m], color='C7', lw=0.5, label='Old design: sensor direct to ADC')
a1.plot((t[m] - c1) * 1e3, r['V(adc_new)'][m], color='C0', lw=1.4, label='New: Sallen-Key LPF output')
a1.plot((t[m] - c1) * 1e3, r['V(sc)'][m], color='C3', ls='--', lw=1.0, label='Clean magnet signal (truth)')
a1.set_xlabel('Time relative to magnet centre (ms)')
a1.set_ylabel('ADC input (V)')
a1.set_title('SIM04b magnet pass (+0.8 V, sigma 12 ms), 20 mV rms broadband noise + 10 mV 50 Hz')
a1.legend(loc='upper right')
a2.hist(n_old_s * 1e3, bins=80, alpha=0.6, color='C7', density=True,
        label='Old: %.2f mV rms (SNR %.1f dB)' % (n_old_rms * 1e3, snr_old))
a2.hist(n_new_s * 1e3, bins=80, alpha=0.8, color='C0', density=True,
        label='New: %.2f mV rms (SNR %.1f dB)' % (n_new_rms * 1e3, snr_new))
a2.set_xlabel('Noise at ADC samples, 2 kS/s (mV)')
a2.set_ylabel('Probability density (1/mV)')
a2.set_title('Sampled noise distribution; SNR improvement %.1f dB' % (snr_new - snr_old))
a2.legend()
savefig(fig, 'sim04b_hall_old_vs_new.png')

fig, ax = plt.subplots(figsize=(FIGW, 3.4))
bins = np.linspace(-4, 4, 65)
ax.hist((err_old_i - tpk_clean_old) * 1e3, bins=bins, alpha=0.6, color='C7', label='Old: %.3f ms rms, max %.2f ms' % (soi[1] * 1e3, soi[2] * 1e3))
ax.hist((err_new_i - tpk_clean_new) * 1e3, bins=bins, alpha=0.8, color='C0', label='New: %.3f ms rms, max %.2f ms (fixed %.3f ms delay removed)' % (sni[1] * 1e3, sni[2] * 1e3, tpk_clean_new * 1e3))
ax.set_xlabel('Peak-time error, 2 kS/s samples + parabolic interpolation (ms)')
ax.set_ylabel('Count')
ax.set_title('SIM04b peak timing error, %d estimates per design' % len(err_old))
ax.legend()
savefig(fig, 'sim04b_hall_peak_timing.png')

update_results('SIM04_hall_afe', res)
for k, v in res.items():
    print(k, v)
