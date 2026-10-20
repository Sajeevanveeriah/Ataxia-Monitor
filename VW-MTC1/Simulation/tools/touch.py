"""Synchronous touch candidate: reproducible LTspice benches and event checks.

This is a functional model, not a Microchip device macro-model or a patient
current certification. The acceptance record must retain the measurement
boundary: PCB output current and discharge of external capacitance differ.
"""
from pathlib import Path

import numpy as np


CORNERS = [
    ("nominal", 3.3, 0, 230, 100e-12),
    ("low_false", 3.15, 1, 253, 110e-12),
    ("high_false", 3.48, 1, 253, 110e-12),
    ("low_miss", 3.15, -1, 253, 110e-12),
    ("high_miss", 3.48, -1, 253, 110e-12),
    ("board_only", 3.48, -1, 0, 110e-12),
]


def bridge_bench(vdd=3.3, direction=0, mains_rms=230, coupling=100e-12):
    """All three channels together, including common excitation impedance.

    Reference ratios oppose the three signal bridges. The 20 pF node budget
    includes a 10 pF component plus input/protection/layout capacitance.
    Buffer offset, a 0.5 MHz pole and 25 mV rail limits are explicit bounded
    surrogates. ADC nonlinearity and sampling jitter are injected on replay.
    """
    lines = [
        "* VW-MTC1 synchronous bridge candidate; see touch.py for model limits.",
        ".step param PH 0 330 30",
        ".step param OFF list 0 125u 250u 375u 500u 625u 750u 875u",
        ".step param CP list 30p 200p",
        f"Vdd vdd 0 {vdd}",
        f"Vexc src 0 PULSE(0 {vdd} 0 1u 1u 499u 1m)",
        "Rgpio src exc 50",
        f"Vmains mains 0 SINE(0 {mains_rms*np.sqrt(2):.12g} 50 0 0 {{PH}})",
        ".model SWC SW(Ron=1 Roff=1e12 Vt=.5 Vh=0)",
    ]
    for ch in range(4):
        d = direction if ch < 3 else -direction
        lines += [
            f"Rdrive{ch} exc sense{ch} {100e3*(1+.001*d):.12g}",
            f"Rup{ch} vdd sense{ch} {200e3*(1-.001*d):.12g}",
            f"Rdn{ch} sense{ch} 0 {200e3*(1-.001*d):.12g}",
            f"Cboard{ch} sense{ch} 0 20p",
            f"Ebuf{ch} buf{ch} 0 value={{limit(V(sense{ch})+{.0045*d},.025,V(vdd)-.025)}}",
            f"Rbuf{ch} buf{ch} adc{ch} 1k",
            f"Cbuf{ch} adc{ch} 0 318p",
        ]
        if ch < 3:
            lines += [
                f"Rlimit{ch} sense{ch} pin{ch} {1.2e6*(1+.01*direction):.12g}",
                f"Cwire{ch} pin{ch} 0 {{CP}}",
                f"Cmains{ch} mains pin{ch} {coupling:.12g}",
                f"Ileak{ch} sense{ch} 0 {10e-9*d:.12g}",
                f"Rskin{ch} pin{ch} contact{ch} {100e3 if ch == 1 else 1}",
                f"Scontact{ch} contact{ch} 0 ctl 0 SWC",
            ]
    lines += [
        "Vcontact ctl 0 PWL(0 0 {20m+OFF} 0 {20.001m+OFF} 1 "
        "{22m+OFF} 1 {22.001m+OFF} 0 {50m+OFF} 0 {50.001m+OFF} 1 "
        "{70m+OFF} 1 {70.001m+OFF} 0 {75m+OFF} 0 {75.001m+OFF} 1 "
        "{95m+OFF} 1 {95.001m+OFF} 0)",
        ".save V(adc0) V(adc1) V(adc2) V(adc3) "
        "I(Rlimit0) I(Rlimit1) I(Rlimit2) I(Scontact0) I(Scontact1) I(Scontact2)",
        ".options plotwinsize=0",
        ".tran 0 115m 0 10u",
        ".end",
    ]
    return "\n".join(lines) + "\n"


def sample_codes(raw, section, vdd, error_lsb=0, jitter_us=0):
    """Replay four sequential acquisitions 25 us apart through a 12-bit ADC.

    Error signs oppose the reference to exercise worst carrier-amplitude
    discrimination. A fixed seed makes bounded jitter repeatable.
    """
    t = raw["time"][section]
    n = np.arange(229)
    ts = .000405 + n * .0005
    jitter = np.random.default_rng(743).uniform(-jitter_us, jitter_us, len(n)) * 1e-6
    codes = np.column_stack([
        np.rint(np.interp(ts + ch * .000025 + jitter, t,
                          raw[f"V(adc{ch})"][section]) / vdd * 4096)
        + error_lsb * (-1.)**n * (1 if ch == 3 else -1)
        for ch in range(4)
    ]).astype(int)
    times = np.rint((ts + jitter) * 1e6).astype(np.int64)
    return times, n % 2 == 0, codes


def event_metrics(times_s, valid, masks, channel, offset=0):
    """Match each stimulus to exactly one event; reject chatter and idle events."""
    times_s, valid, masks = map(np.asarray, (times_s, valid, masks))
    if not (times_s.ndim == valid.ndim == masks.ndim == 1 and
            len(times_s) == len(valid) == len(masks) and len(times_s) > 2):
        raise ValueError("Expected matching one-dimensional sample arrays")
    if np.any(np.diff(times_s) <= 0) or channel not in (0, 1, 2):
        raise ValueError("Invalid time axis or channel")
    state = (masks & (1 << channel)) != 0
    # Initialisation is not an onset. Invalid samples cannot bridge a gap.
    changed = (state[1:] != state[:-1]) & valid[1:] & valid[:-1]
    edges = [(float(times_s[i+1]), bool(state[i+1])) for i in np.flatnonzero(changed)]
    windows = [(offset + .020, offset + .030),
               (offset + .050, offset + .075),
               (offset + .075, offset + .100)]
    matched = [[e for e in edges if start <= e[0] < end] for start, end in windows]
    contact_ends = [offset + .022, offset + .070, offset + .095]
    correct = [len(events) == 2 and events[0][1] and not events[1][1] and
               events[0][0] < contact_end <= events[1][0]
               for events, contact_end in zip(matched, contact_ends)]
    # A 2 ms pulse may end before a causal filter reports it. Permit an onset
    # within 5 ms of its start, while still requiring exactly one complete
    # event. Report that delay explicitly rather than implying live tracking.
    short = matched[0]
    correct[0] = (len(short) == 2 and short[0][1] and not short[1][1] and
                  short[0][0] < offset + .025 and short[1][0] >= offset + .022)
    outside = [e for e in edges if not any(a <= e[0] < b for a, b in windows)]
    gap = (times_s >= offset + .070) & (times_s < offset + .075)
    gap_open = bool(np.any(gap & valid & ~state))
    stable = bool(np.all(valid[times_s >= .006]))
    pair_ok = correct[1] and correct[2] and gap_open and not outside and stable
    return {
        "short_contact_pass": correct[0],
        "gap_pair_pass": pair_ok,
        "idle_or_extra_events": len(outside),
        "valid_after_warmup": stable,
        "edges": edges,
        "short_onset_delay_ms": None if not correct[0] else
            1000 * (short[0][0] - offset - .020),
        "release_delay_ms": None if not correct[1] else
            1000 * (matched[1][1][0] - offset - .070),
        "second_onset_delay_ms": None if not correct[2] else
            1000 * (matched[2][0][0] - offset - .075),
    }


def write_benches(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, vdd, direction, mains_rms, coupling in CORNERS:
        path = directory / f"touch_{name}.cir"
        path.write_text(bridge_bench(vdd, direction, mains_rms, coupling), encoding="utf-8")
        paths.append(path)
    return paths
