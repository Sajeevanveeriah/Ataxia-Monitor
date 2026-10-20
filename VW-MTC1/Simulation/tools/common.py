"""common.py - shared paths, plot style and results.json helper."""
import os, json, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LT = os.path.join(ROOT, 'LTspice')
PLOTS = os.path.join(ROOT, 'Plots')
RESULTS = os.path.join(ROOT, 'results.json')
sys.path.insert(0, os.path.dirname(__file__))

plt.rcParams.update({
    'figure.facecolor': 'white', 'axes.facecolor': 'white',
    'axes.grid': True, 'grid.alpha': 0.35, 'font.size': 10,
    'axes.titlesize': 11, 'axes.labelsize': 10, 'legend.fontsize': 8.5,
    'lines.linewidth': 1.2, 'savefig.dpi': 150,
})
FIGW = 7.5  # inches, fits A4 text width


def lt(name):
    return os.path.join(LT, name)


def savefig(fig, name):
    fig.tight_layout()
    p = os.path.join(PLOTS, name)
    fig.savefig(p, dpi=150, facecolor='white')
    plt.close(fig)
    print('wrote', p)


def check(value, units, limit, passed, note=None):
    import numpy as _np
    if isinstance(value, _np.generic):
        value = value.item()
    if passed is not None:
        passed = bool(passed)
    d = {'value': value, 'units': units, 'limit': limit,
         'result': ('PASS' if passed else 'FAIL') if passed is not None else 'INFO'}
    if note:
        d['note'] = note
    return d


def update_results(sim_key, payload):
    data = {}
    if os.path.exists(RESULTS):
        with open(RESULTS) as f:
            data = json.load(f)
    data[sim_key] = payload
    with open(RESULTS, 'w') as f:
        json.dump(data, f, indent=2)
    print('updated results.json:', sim_key)
