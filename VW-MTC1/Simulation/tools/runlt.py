"""runlt.py - run an LTspice netlist in batch mode with a timeout.

python -m vw_mtc1.runlt file.cir [timeout_s]
Returns non-zero if LTspice fails, times out, or the .log reports an error.
"""
import argparse
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

from vw_mtc1.lttext import decode_text


def read_log(path):
    return decode_text(Path(path).read_bytes())


def find_ltspice(executable=None):
    """Explicit path, environment override, PATH, then standard Windows installs."""
    if executable is not None:
        return os.fspath(executable)
    if os.environ.get('LTSPICE_EXE'):
        return os.environ['LTSPICE_EXE']
    found = shutil.which('LTspice') or shutil.which('XVIIx64')
    if found:
        return found
    for base, suffix in (('LOCALAPPDATA', 'Programs/ADI/LTspice/LTspice.exe'),
                         ('ProgramFiles', 'ADI/LTspice/LTspice.exe'),
                         ('ProgramFiles', 'LTC/LTspiceXVII/XVIIx64.exe')):
        if os.environ.get(base):
            candidate = Path(os.environ[base]) / suffix
            if candidate.is_file():
                return str(candidate)
    raise FileNotFoundError('LTspice not found. Set LTSPICE_EXE to its executable path.')


def _log_signature(path):
    if not path.exists():
        return None
    stat = path.stat()
    return stat.st_mtime_ns, stat.st_size, path.read_bytes()


def run(cir, timeout=300, executable=None):
    cir = os.path.abspath(cir)
    if not Path(cir).is_file():
        raise FileNotFoundError(cir)
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('Timeout must be finite and positive')
    log = Path(cir).with_suffix('.log')
    previous_log = _log_signature(log)
    t0 = time.monotonic()
    p = subprocess.Popen([find_ltspice(executable), '-b', cir], cwd=os.path.dirname(cir))
    try:
        rc = p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()  # kill only this LTspice instance
        p.wait()  # reap the terminated process before returning
        print('TIMEOUT', cir)
        return 2, None
    dt = time.monotonic() - t0
    current_log = _log_signature(log)
    txt = read_log(log) if current_log else ''
    fresh = current_log is not None and current_log != previous_log and bool(txt.strip())
    bad = not fresh or bool(re.search(
        r'^\s*(?:fatal\s+)?error\b|singular matrix|time step too small|'
        r'^\s*Measurement\b.*FAIL|^\s*\d+\s+failed\b',
        txt, re.IGNORECASE | re.MULTILINE))
    print('%s rc=%s %.1fs %s' % (os.path.basename(cir), rc, dt, 'LOG-ERROR' if bad else 'ok'))
    return (rc if rc else int(bad)), txt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('circuit', type=Path)
    parser.add_argument('timeout', nargs='?', type=float, default=300)
    parser.add_argument('--executable', type=Path, help='Override LTSPICE_EXE/PATH lookup')
    args = parser.parse_args()
    try:
        rc, txt = run(args.circuit, args.timeout, args.executable)
    except (OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')
    if txt:
        print(txt)
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
