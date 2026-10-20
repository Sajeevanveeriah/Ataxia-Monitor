"""Measurements for the charger and two-contact diagnostic circuits."""
import re
import hashlib
from pathlib import Path

import numpy as np

from vw_mtc1.ltraw import tavg
from vw_mtc1.waveform import low_intervals


def validate_run_receipts(receipts, expected_names, output):
    """Reject failed, missing or modified runs before reusing stored waveforms."""
    names = [row["circuit"] for row in receipts]
    if len(names) != len(set(names)) or set(names) != set(expected_names):
        raise ValueError("Run receipts do not match the requested diagnostic set")
    for row in receipts:
        circuit = Path(output) / row["circuit"]
        if row["exit_code"] != 0:
            raise ValueError(f"Cannot analyse a failed run: {circuit.name}")
        if hashlib.sha256(circuit.read_bytes()).hexdigest() != row["netlist_sha256"]:
            raise ValueError(f"Diagnostic input changed after execution: {circuit.name}")


def step_parameters(log_text):
    """Read actual simulator step order instead of assuming nesting/list order."""
    steps = []
    for line in log_text.splitlines():
        if re.match(r"^\s*\.step\s", line, re.IGNORECASE):
            values = re.findall(r"(\w+)=([-+.\deE]+)(?=\s|$)", line)
            if not values:
                raise ValueError(f"Unrecognised step record: {line}")
            steps.append({name.lower(): float(value) for name, value in values})
    return steps


def termination_metrics(t, current, prog, rprog, cc_window, after):
    """Measure the current plateau immediately before a distinct cutoff edge.

    The 2ms to 0.1ms pre-edge window excludes the switching transition. Time
    weighting avoids bias from the adaptive solver's dense transition samples.
    """
    t, current, prog = map(np.asarray, (t, current, prog))
    icc = float(tavg(t, current, *cc_window))
    candidates = np.flatnonzero(
        (t[:-1] > after) & (current[:-1] > .01 * icc) & (current[:-1] < .3 * icc)
    )
    if icc <= 0 or not len(candidates):
        raise ValueError("No constant-current phase or termination candidates")
    delta = np.diff(current)
    edge = int(candidates[np.argmin(delta[candidates])])
    if delta[edge] >= -.01 * icc:
        raise ValueError("No distinct termination edge")
    cutoff = float(t[edge])
    window = (cutoff - .002, cutoff - .0001)
    iterm = float(tavg(t, current, *window))
    vprog = float(tavg(t, prog, *window))
    ratio = iterm / icc
    crossings = np.flatnonzero(
        (t[:-1] > after) & (t[:-1] < cutoff) &
        (prog[:-1] >= .1) & (prog[1:] < .1)
    )
    below_100_ms = None
    if len(crossings):
        k = crossings[-1]
        crossing = float(np.interp(.1, [prog[k + 1], prog[k]], [t[k + 1], t[k]]))
        below_100_ms = (cutoff - crossing) * 1000
    return {
        "cutoff_s": cutoff,
        "cc_current_mA": icc * 1000,
        "termination_current_mA": iterm * 1000,
        "termination_fraction": ratio,
        "pre_cutoff_prog_mV": vprog * 1000,
        "observed_current_to_prog_ratio": iterm * rprog / vprog if vprog else None,
        "time_below_100mV_ms": below_100_ms,
        "datasheet_ratio_check": "PASS" if .085 <= ratio <= .115 else "FAIL",
    }


def touch_pair_metrics(t, vin, output, gap, supply=3.3):
    """Require a distinct onset for each contact, not just any two pulses."""
    t, vin, output = map(np.asarray, (t, vin, output))
    intervals = low_intervals(t, output, threshold=supply / 2)
    starts = [.140, .160 + gap]
    counts = [int(sum(start <= fall < start + .020 for fall, _ in intervals)) for start in starts]
    gap_samples = (t >= .160001) & (t < .160 + gap)
    if not np.any(gap_samples):
        raise ValueError("No samples in the contact gap")
    high_during_gap = bool(np.any(output[gap_samples] > supply / 2))
    pair_pulses = int(sum(.140 <= fall < .210 + gap for fall, _ in intervals))
    idle_pulses = int(sum(.030 <= fall < .139 or .230 + gap <= fall < .270
                         for fall, _ in intervals))
    release = next((rise for fall, rise in intervals
                    if .140 <= fall < .160 and .160 <= rise < .160 + gap), None)
    resolved = counts == [1, 1] and high_during_gap and pair_pulses == 2
    return {
        "contact_onsets": counts,
        "pair_pulses": pair_pulses,
        "idle_pulses": idle_pulses,
        "high_during_gap": high_during_gap,
        "gap_peak_input_V": float(vin[gap_samples].max()),
        "first_release_delay_ms": None if release is None else float((release - .160) * 1000),
        "gap_resolved": resolved,
        "gap_and_idle_pass": resolved and idle_pulses == 0,
    }
