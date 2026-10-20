"""runlt.py - run an LTspice netlist in batch mode with a timeout.

python runlt.py file.cir [timeout_s]
Returns non-zero if LTspice fails, times out, or the .log reports an error.
"""
import subprocess, sys, os, time

LTSPICE = r'C:\Users\sajee\AppData\Local\Programs\ADI\LTspice\LTspice.exe'


def read_log(path):
    raw = open(path, 'rb').read()
    return raw.decode('utf-16-le') if raw[1:2] == b'\x00' else raw.decode('latin-1')


def run(cir, timeout=300):
    cir = os.path.abspath(cir)
    t0 = time.time()
    p = subprocess.Popen([LTSPICE, '-b', cir], cwd=os.path.dirname(cir))
    try:
        rc = p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()  # kill only this LTspice instance
        print('TIMEOUT', cir)
        return 2, None
    dt = time.time() - t0
    log = os.path.splitext(cir)[0] + '.log'
    txt = read_log(log) if os.path.exists(log) else ''
    bad = any(s in txt.lower() for s in ('error', 'singular matrix', 'time step too small'))
    print('%s rc=%s %.1fs %s' % (os.path.basename(cir), rc, dt, 'LOG-ERROR' if bad else 'ok'))
    return (1 if bad else rc), txt


if __name__ == '__main__':
    rc, txt = run(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 300)
    if txt:
        print(txt)
    sys.exit(rc)
