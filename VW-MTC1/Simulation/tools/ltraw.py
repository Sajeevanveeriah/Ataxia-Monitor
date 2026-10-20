"""ltraw.py - minimal reader for LTspice binary/ASCII .raw files.

Supports transient (time float64, others float32 or float64 when the
'double' flag is set), AC (complex128 throughout), .op, and stepped runs
(.step). Handles both normal (point-major) and 'fastaccess' (variable-major)
layouts.

Usage:
    from vw_mtc1.ltraw import RawRead
    r = RawRead('sim01.raw')
    t = r['time']; v = r['V(out)']
    runs = r.step_slices()   # list of slice objects, one per .step run
"""
import numpy as np
from vw_mtc1.lttext import decode_text, text_encoding


class RawRead:
    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as f:
            data = f.read()
        # Header encoding: UTF-16LE (LTspice default) or ASCII.
        enc = text_encoding(data)
        # find the 'Binary:' or 'Values:' marker
        for marker in ('Binary:\n', 'Values:\n', 'Binary:\r\n', 'Values:\r\n'):
            m = marker.encode('utf-8' if enc == 'utf-8-sig' else enc)
            idx = data.find(m)
            if idx >= 0:
                self.binary = marker.startswith('Binary')
                hdr = decode_text(data[:idx])
                body = data[idx + len(m):]
                break
        else:
            raise ValueError(f'No Binary:/Values: marker in {path}')
        self.header = hdr
        self.meta = {}
        self.names = []
        lines = hdr.replace('\r', '').split('\n')
        i = 0
        while i < len(lines):
            ln = lines[i]
            if ln.startswith('Variables:'):
                i += 1
                while i < len(lines) and lines[i].startswith(('\t', ' ')):
                    parts = lines[i].split()
                    if len(parts) >= 3:
                        self.names.append(parts[1])
                    i += 1
                continue
            if ':' in ln:
                k, v = ln.split(':', 1)
                self.meta[k.strip()] = v.strip()
            i += 1
        flags = self.meta.get('Flags', '').lower().split()
        self.flags = flags
        nvar = int(self.meta['No. Variables'])
        npts = int(self.meta['No. Points'])
        self.nvar, self.npts = nvar, npts
        if nvar < 1 or npts < 0 or len(self.names) != nvar:
            raise ValueError(f'Invalid variable/point counts in {path}')
        self.is_complex = 'complex' in flags
        self.stepped = 'stepped' in flags
        plotname = self.meta.get('Plotname', '').lower()
        self.is_tran = 'transient' in plotname
        if self.binary:
            self._read_binary(body, nvar, npts, flags)
        else:
            self._read_ascii(body.decode(enc), nvar, npts)
        if self.is_tran:
            # Both binary and ASCII files can contain negative time flags.
            self.data[:, 0] = np.abs(self.data[:, 0])
        self._lower = {n.lower(): k for k, n in enumerate(self.names)}

    def _read_binary(self, body, nvar, npts, flags):
        point_size = nvar * 16 if self.is_complex else (nvar * 8 if 'double' in flags else 8 + 4 * (nvar - 1))
        if len(body) < npts * point_size:
            raise ValueError(f'Truncated binary waveform in {self.path}')
        if self.is_complex:
            arr = np.frombuffer(body[:npts * nvar * 16], dtype='<c16')
            arr = arr.reshape(npts, nvar) if 'fastaccess' not in flags \
                else arr.reshape(nvar, npts).T
            self.data = arr
            return
        double = 'double' in flags
        if 'fastaccess' in flags:
            cols, off = [], 0
            for k in range(nvar):
                dt = '<f8' if (k == 0 or double) else '<f4'
                sz = np.dtype(dt).itemsize * npts
                cols.append(np.frombuffer(body[off:off + sz], dtype=dt).astype(float))
                off += sz
            self.data = np.column_stack(cols)
        else:
            if double:
                arr = np.frombuffer(body[:npts * nvar * 8], dtype='<f8').reshape(npts, nvar)
                self.data = arr.astype(float)
            else:
                fields = [('t', '<f8')] + [('v%d' % k, '<f4') for k in range(1, nvar)]
                rec = np.frombuffer(body[:npts * (8 + 4 * (nvar - 1))], dtype=np.dtype(fields))
                out = np.empty((npts, nvar))
                out[:, 0] = rec['t']
                for k in range(1, nvar):
                    out[:, k] = rec['v%d' % k]
                self.data = out

    def _read_ascii(self, txt, nvar, npts):
        tok = txt.split()
        if len(tok) != npts * (nvar + 1):
            raise ValueError(f'Invalid ASCII waveform length in {self.path}')
        vals = []
        p = 0
        for _ in range(npts):
            p += 1  # index
            row = []
            for _ in range(nvar):
                s = tok[p]; p += 1
                if self.is_complex:
                    re_, im_ = s.split(',')
                    row.append(complex(float(re_), float(im_)))
                else:
                    row.append(float(s))
            vals.append(row)
        self.data = np.array(vals, dtype=complex if self.is_complex else float).reshape(npts, nvar)

    def __getitem__(self, name):
        k = self._lower.get(name.lower())
        if k is None:
            raise KeyError('%s not in %s; have %s' % (name, self.path, self.names))
        col = self.data[:, k]
        return col if self.is_complex else np.asarray(col, dtype=float)

    def has(self, name):
        return name.lower() in self._lower

    def step_slices(self):
        """Return list of slices, one per .step run (detected by axis reset)."""
        x = np.real(self.data[:, 0])
        if not len(x):
            return []
        br = np.where(np.diff(x) < 0)[0] + 1
        edges = [0] + list(br) + [len(x)]
        return [slice(edges[i], edges[i + 1]) for i in range(len(edges) - 1)]


def resample(t, y, dt, t0=None, t1=None):
    """Linear resample onto a uniform grid (for FFT / rms on compressed data)."""
    t, y = _samples(t, y)
    t0 = t[0] if t0 is None else t0
    t1 = t[-1] if t1 is None else t1
    _interval(t, t0, t1)
    if not np.isfinite(dt) or dt <= 0:
        raise ValueError('Sampling interval must be finite and positive')
    tu = np.arange(t0, t1, dt)
    return tu, np.interp(tu, t, y)


def window(t, y, t0, t1):
    m = (t >= t0) & (t <= t1)
    return t[m], y[m]


def tavg(t, y, t0, t1):
    """Time-weighted average of y over [t0, t1] (trapezoidal)."""
    t, y = _samples(t, y)
    _interval(t, t0, t1)
    inside = (t > t0) & (t < t1)
    tt = np.concatenate(([t0], t[inside], [t1]))
    yy = np.interp(tt, t, y)
    return np.trapezoid(yy, tt) / (t1 - t0)


def _samples(t, y):
    t, y = np.asarray(t, dtype=float), np.asarray(y)
    if t.ndim != 1 or y.ndim != 1 or len(t) != len(y) or len(t) < 2:
        raise ValueError('Expected matching one-dimensional arrays with at least two samples')
    if not np.all(np.isfinite(t)) or not np.all(np.isfinite(y)) or np.any(np.diff(t) <= 0):
        raise ValueError('Samples must be finite with a strictly increasing time axis; split stepped runs first')
    return t, y


def _interval(t, t0, t1):
    if not np.isfinite(t0) or not np.isfinite(t1) or not t[0] <= t0 < t1 <= t[-1]:
        raise ValueError('Window must have positive duration and lie within the sampled time range')


def parse_meas(logpath):
    """Parse .meas results from an LTspice .log into a dict (lower-case keys)."""
    import re
    out = {}
    with open(logpath, 'rb') as stream:
        txt = decode_text(stream.read())
    for ln in txt.replace('\r', '').split('\n'):
        ma = re.match(r'^\s*([A-Za-z_][\w]*)\s*:.*\sAT\s+([-+0-9.eE]+)\s*$', ln)
        if ma:  # WHEN-type result: "name: V(x)=val AT time"
            out[ma.group(1).lower()] = float(ma.group(2))
            continue
        m = re.match(r'^\s*([A-Za-z_][\w]*)\s*:\s*.*?=\s*([-+0-9.eE]+)', ln)
        if m:
            try:
                out[m.group(1).lower()] = float(m.group(2))
            except ValueError:
                pass
        m2 = re.match(r'^\s*([A-Za-z_][\w]*)\s*=\s*([-+0-9.eE]+)', ln)
        if m2 and m2.group(1).lower() not in out:
            try:
                out[m2.group(1).lower()] = float(m2.group(2))
            except ValueError:
                pass
    return out
