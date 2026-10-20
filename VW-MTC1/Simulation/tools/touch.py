"""Synchronous touch candidate: reproducible LTspice benches and event checks.

This is a functional model, not a Microchip device macro-model or a patient
current certification. The acceptance record must retain the measurement
boundary: PCB output current and discharge of external capacitance differ.
"""
from pathlib import Path

import numpy as np


BASE_CORNERS = [
    ("nominal", 3.3, 0, 230, 100e-12),
    ("low_false", 3.15, 1, 253, 110e-12),
    ("high_false", 3.6, 1, 253, 110e-12),
    ("low_miss", 3.15, -1, 253, 110e-12),
    ("high_miss", 3.6, -1, 253, 110e-12),
]
CORNERS = [(f"{name}_{hz}hz", vdd, d, vm, cc, hz)
           for hz in (50, 60) for name, vdd, d, vm, cc in BASE_CORNERS]
CORNERS += [("low_false_48hz", 3.15, 1, 253, 110e-12, 48),
            ("low_false_62hz", 3.15, 1, 253, 110e-12, 62),
            ("board_only", 3.6, -1, 0, 110e-12, 50)]
CONTACT_OFFSETS_US = (0, 125, 250, 375, 440, 450, 460, 462,
                      474, 475, 485, 495, 500, 625, 750, 875)
SWEEP_STEPS = 24 * len(CONTACT_OFFSETS_US) * 2
CONTACTS = ((.020, .022), (.030, .032), (.037, .039), (.050, .070), (.075, .095))


def bridge_bench(vdd=3.3, direction=0, mains_rms=230, coupling=100e-12,
                 mains_hz=50, interaction=False):
    """All three channels together, including common excitation impedance.

    Reference ratios oppose the signal bridges. Node capacitance covers the
    270 pF C0G component and input/protection/layout capacitance (260 to 300 pF).
    OPA4323 offset, gain and bandwidth envelopes are explicit bounded
    surrogates, not a manufacturer macro-model. ADS8344NB error and measured
    sampling-time uncertainty are injected on replay.
    """
    lines = [
        "* VW-MTC1 synchronous bridge candidate; see touch.py for model limits.",
        ".step param PHCASE 0 23 1",
        ".param PH=table(PHCASE," + ",".join(f"{i},{30*(i%12)}" for i in range(24)) + ")",
        ".param RINPUT=1.15Meg*(1+0.015*if(PHCASE<12,-1,1))",
        ".step param OFF list " + " ".join(f"{x}u" for x in CONTACT_OFFSETS_US),
        ".step param CP list 30p 200p",
        f"Vdd vdd 0 {vdd}",
        "Radc vdd vadc 10",
        "Cadc vadc 0 5.9u",
        "Iadc vadc 0 2.01m",
        "* REF3325: use +1% DC envelope for the worst code-error sensitivity.",
        "* Noise/settling bounds are included in the +/-12-code replay error.",
        "Vref vref 0 2.525",
        f"Vexc src 0 PULSE(0 {vdd} 0 1u 1u 499u 1m)",
        "Rgpio src drive 50",
        "Rscale drive exc 220",
        "Rshunt exc 0 100",
        f"Vmains mains 0 SINE(0 {mains_rms*np.sqrt(2):.12g} {mains_hz} 0 0 {{PH}})",
        ".model SWC SW(Ron=1 Roff=1e12 Vt=.5 Vh=0)",
    ]
    for ch in range(4):
        d = direction if ch < 3 else -direction
        lines += [
            f"Rdrive{ch} exc sense{ch} {100e3*(1+.001*d):.12g}",
            f"Rup{ch} vdd sense{ch} {187e3*(1-.001*d):.12g}",
            f"Rdn{ch} sense{ch} 0 {200e3*(1-.001*d):.12g}",
            f"Cboard{ch} sense{ch} 0 {280e-12+20e-12*d:.12g}",
            f"Ebuf{ch} buf{ch} 0 value={{limit((1-{.0001*d})*V(sense{ch})+{.0015*d},.055,V(vdd)-.055)}}",
            f"Rbuf{ch} buf{ch} adc{ch} 1k",
            f"Cbuf{ch} adc{ch} 0 318p",
        ]
        if ch < 3:
            lines += [
                f"Rlimit{ch} sense{ch} pin{ch} {{RINPUT}}",
                f"Cwire{ch} pin{ch} 0 {{CP}}",
                f"Cmains{ch} mains pin{ch} {coupling:.12g}",
                f"Ileak{ch} sense{ch} 0 {12e-9*d:.12g}",
                f"Rskin{ch} pin{ch} contact{ch} {100e3 if ch == 1 else 1}",
                f"Scontact{ch} contact{ch} 0 ctl 0 SWC",
            ]
    waveform = ["0 0"]
    for start, stop in CONTACTS:
        waveform += [f"{{{start:.9g}+OFF}} 0", f"{{{start+1e-6:.9g}+OFF}} 1",
                     f"{{{stop:.9g}+OFF}} 1", f"{{{stop+1e-6:.9g}+OFF}} 0"]
    lines += [
        "Vcontact ctl 0 PWL(" + " ".join(waveform) + ")",
        ".save V(adc0) V(adc1) V(adc2) V(adc3) "
        "I(Rlimit0) I(Rlimit1) I(Rlimit2) I(Scontact0) I(Scontact1) I(Scontact2) "
        "V(sense0) V(sense1) V(sense2) V(sense3) V(vref)",
        ".options plotwinsize=0 reltol=1e-5 abstol=1e-12 vntol=1e-7 method=gear",
        ".tran 0 115m 0 20u",
        ".end",
    ]
    circuit = "\n".join(lines) + "\n"
    if interaction:
        # One electrode at a time, with different interference phases on the
        # two idle electrodes. Combine channel/phase/resistor into one step
        # because LTspice permits only three nested .step dimensions.
        circuit = circuit.replace(
            ".param PH=table(PHCASE," + ",".join(f"{i},{30*(i%12)}" for i in range(24)) + ")",
            ".param PH=table(PHCASE," + ",".join(f"{i},{90*(i%4)}" for i in range(24)) + ")\n"
            ".param CSEL=floor(PHCASE/8)")
        circuit = circuit.replace("if(PHCASE<12,-1,1)", "if(mod(PHCASE,8)<4,-1,1)")
        circuit = circuit.replace(
            ".step param OFF list " + " ".join(f"{x}u" for x in CONTACT_OFFSETS_US),
            ".step param OFF list 0u 450u 495u 750u")
        for ch in range(3):
            circuit = circuit.replace(
                f"Cmains{ch} mains pin{ch}",
                f"Vmains{ch} mains{ch} 0 SINE(0 {mains_rms*np.sqrt(2):.12g} {mains_hz} 0 0 {{PH+{120*ch}}})\n"
                f"Cmains{ch} mains{ch} pin{ch}")
            circuit = circuit.replace(
                f"Scontact{ch} contact{ch} 0 ctl 0 SWC",
                f"Bselect{ch} ctl{ch} 0 V=if(CSEL=={ch},V(ctl),0)\n"
                f"Scontact{ch} contact{ch} 0 ctl{ch} 0 SWC")
    return circuit


def sample_codes(raw, section, vdd, error_lsb=0, jitter_us=5):
    """Replay four pipelined ADS8344 acquisitions 12 us apart, 16-bit data.

    Error signs oppose the reference to exercise worst carrier-amplitude
    discrimination. A fixed seed makes bounded jitter repeatable.
    """
    t = raw["time"][section]
    n = np.arange(229)
    ts = .000450 + n * .0005
    jitter = np.random.default_rng(743).uniform(-jitter_us, jitter_us, len(n)) * 1e-6
    codes = np.column_stack([
        np.rint(np.interp(ts + ch * .000012 + jitter, t,
                          raw[f"V(adc{ch})"][section]) /
                np.interp(ts + ch * .000012 + jitter, t, raw["V(vref)"][section]) * 65536)
        + error_lsb * (-1.)**n * (1 if ch == 3 else -1)
        for ch in range(4)
    ]).astype(int)
    # 100 ns capture/aperture uncertainty is independent of actual jitter.
    uncertainty = np.random.default_rng(997).uniform(-1e-7, 1e-7, len(n))
    times = np.rint((ts + jitter + uncertainty) * 1e9).astype(np.int64)
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
    windows = [(offset + a, offset + b) for a, b in
               ((.020, .030), (.030, .037), (.037, .050), (.050, .075), (.075, .100))]
    matched = [[e for e in edges if start <= e[0] < end] for start, end in windows]
    contact_ends = [offset + stop for _, stop in CONTACTS]
    correct = [len(events) == 2 and events[0][1] and not events[1][1] and
               events[0][0] < contact_end <= events[1][0]
               for events, contact_end in zip(matched, contact_ends)]
    # A 2 ms pulse may end before a causal filter reports it. Permit an onset
    # within 5 ms of its start, while still requiring exactly one complete
    # event. Report that delay explicitly rather than implying live tracking.
    for i in range(3):
        short = matched[i]
        start, end = CONTACTS[i]
        correct[i] = (len(short) == 2 and short[0][1] and not short[1][1] and
                      short[0][0] < offset + start + .005 and
                      offset + end <= short[1][0] < offset + end + .005)
    short = matched[0]
    outside = [e for e in edges if not any(a <= e[0] < b for a, b in windows)]
    extra_events = len(outside) + sum(max(0, len(events) - 2) for events in matched)
    gap = (times_s >= offset + .070) & (times_s < offset + .075)
    gap_open = bool(np.any(gap & valid & ~state))
    short_gap = (times_s >= offset + .032) & (times_s < offset + .037)
    short_gap_open = bool(np.any(short_gap & valid & ~state))
    stable = bool(np.all(valid[times_s >= .006]))
    pair_ok = correct[3] and correct[4] and gap_open and extra_events == 0 and stable
    return {
        "short_contact_pass": correct[0],
        "gap_pair_pass": pair_ok,
        "short_pair_pass": correct[1] and correct[2] and short_gap_open and extra_events == 0 and stable,
        "idle_or_extra_events": extra_events,
        "valid_after_warmup": stable,
        "edges": edges,
        "short_onset_delay_ms": None if not correct[0] else
            1000 * (short[0][0] - offset - .020),
        "release_delay_ms": None if not correct[3] else
            1000 * (matched[3][1][0] - offset - .070),
        "second_onset_delay_ms": None if not correct[4] else
            1000 * (matched[4][0][0] - offset - .075),
    }


def write_benches(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, vdd, direction, mains_rms, coupling, mains_hz in CORNERS:
        path = directory / f"touch_{name}.cir"
        path.write_text(bridge_bench(vdd, direction, mains_rms, coupling, mains_hz), encoding="utf-8")
        paths.append(path)
    return paths


def contact_current_bench(bounce=False):
    """Peak frequency-weighted contact current, including stored wire charge.

    Rigel 288+ manual, appendix E: Rbody=1k, Rfilter=10k, Cfilter=15n.
    We take the output PEAK divided by nominal 1k, never a time average.
    Static high excitation precharges all exposed capacitance to its largest
    normal-operation voltage. N=1 gives a conservative single-channel bound;
    three times that peak bounds the sum over three independent contacts.
    N=3 checks simultaneous contact through one common measuring network.
    CW=300p is deliberately outside the 200p wire/parasitic budget.
    """
    lines = [
        "* Rev B board-generated contact-current test; external mains source zeroed.",
        "* Frequency-weighted PEAK criterion, not an unlimited-bandwidth current claim.",
        ".step param MD 0 7 1",
    ]
    if bounce:
        lines += [".step param PERIOD list 50u 100u 200u 500u 1m 5m",
                  ".step param DUTY list 0.1 0.5 0.9", ".param CW=200p N=1"]
    else:
        lines += [".step param CW list 1f 200p 300p", ".step param N list 1 3"]
    lines += [
        ".param RB=table(MD,0,950,1,1050,2,950,3,1050,4,950,5,1050,6,950,7,1050)",
        ".param RF=table(MD,0,9500,1,9500,2,10500,3,10500,4,9500,5,9500,6,10500,7,10500)",
        ".param CM=table(MD,0,14.25n,1,14.25n,2,14.25n,3,14.25n,4,15.75n,5,15.75n,6,15.75n,7,15.75n)",
        "Vdd vdd 0 3.6", "Rgpio vdd drive 1",
        "Rscale drive exc {220*.999}", "Rshunt exc 0 {100*1.001}",
        ".model SWC SW(Ron=1 Roff=1T Vt=.5 Vh=0)",
    ]
    for ch in range(4):
        lines += [f"Rdrive{ch} exc sense{ch} 100100",
                  f"Rup{ch} vdd sense{ch} 186813", f"Rdn{ch} sense{ch} 0 200200",
                  f"Cboard{ch} sense{ch} 0 300p"]
        if ch < 3:
            lines += [f"Rlimit{ch} sense{ch} pin{ch} 1132750",
                      f"Ileak{ch} 0 sense{ch} 12n",
                      f"Cwire{ch} pin{ch} 0 {{CW+110p}}",
                      f"Scontact{ch} pin{ch} body {'ctl' if ch == 0 else 'other_ctl'} 0 SWC"]
    lines += [
        "Bother other_ctl 0 V=if(N>1,V(ctl),0)",
        "Rbody body 0 {RB}", "Rfilter body weighted {RF}", "Cfilter weighted 0 {CM}",
        "Vctl ctl 0 " + ("PULSE(0 1 1m 10n 10n {PERIOD*DUTY-10n} {PERIOD})"
                          if bounce else "PWL(0 0 1m 0 1.00001m 1)"),
        ".save V(weighted) V(body) I(Scontact0) I(Scontact1) I(Scontact2)",
        ".options plotwinsize=0 reltol=1e-5 abstol=1e-12 vntol=1e-7 method=gear",
        ".tran 0 12m .95m 1u" if bounce else ".tran 0 3m .95m 20n",
        ".meas tran weighted_peak_uA MAX abs(V(weighted)*1000)",
        ".end",
    ]
    return "\n".join(lines) + "\n"
