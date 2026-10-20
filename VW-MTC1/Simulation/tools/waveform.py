"""Pure waveform calculations shared by the simulation analysis scripts."""
import numpy as np


def moving_average(t, y, win, dt=10e-9):
    """Resample and smooth without the zero-padding roll-off at either edge."""
    tu = np.arange(t[0], t[-1], dt)
    yu = np.interp(tu, t, y)
    n = max(1, int(round(win / dt)))
    yp = np.pad(yu, (n // 2, n - 1 - n // 2), mode='edge')
    return tu, np.convolve(yp, np.ones(n) / n, mode='valid')


def low_intervals(t, out, threshold=1.65):
    """Return sampled low spans, including pulses touching either trace edge."""
    lo = out < threshold
    ed = np.diff(lo.astype(int))
    falls = list(t[1:][ed == 1])
    rises = list(t[1:][ed == -1])
    if lo[0]:
        falls = [t[0]] + falls
    if len(rises) < len(falls):
        rises.append(t[-1])
    return list(zip(falls, rises))
