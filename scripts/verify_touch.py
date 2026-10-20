"""Verify Rev B touch timing and the documented current measurement criteria.

Exit 0 requires every selected test to pass. A selected --case run is explicitly
marked partial; only the complete suite is release evidence. Raw data stays in
--output. Reuse checks input, log and waveform hashes before analysis.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import time

import numpy as np
from vw_mtc1.investigation import step_parameters, validate_run_receipts
from vw_mtc1.ltraw import RawRead
from vw_mtc1.lttext import decode_text
from vw_mtc1.runlt import run
from vw_mtc1.touch import CORNERS, SWEEP_STEPS, bridge_bench, contact_current_bench, event_metrics, sample_codes, write_benches

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def execute(path, timeout):
    start = time.monotonic()
    result = run(path, timeout=timeout)
    row = {"circuit": path.name, "exit_code": result[0], "elapsed_s": time.monotonic()-start,
           "netlist_sha256": sha(path)}
    if result[0]:
        raise RuntimeError(f"LTspice failed: {path.name}")
    for suffix in (".raw", ".log"):
        row[f"{suffix[1:]}_sha256"] = sha(path.with_suffix(suffix))
    return row


def current_results(path, bounce=False):
    raw = RawRead(path.with_suffix(".raw"))
    steps = step_parameters(decode_text(path.with_suffix(".log").read_bytes()))
    sections = raw.step_slices()
    expected = 144 if bounce else 48
    if len(steps) != expected or len(sections) != expected:
        raise ValueError(f"Incomplete current sweep: {path.name}")
    rows = []
    for params, section in zip(steps, sections):
        n = 1 if bounce else int(params["n"])
        weighted = float(np.max(np.abs(raw["V(weighted)"][section]))*1000)
        total_current = sum(raw[f"I(Scontact{ch})"][section] for ch in range(3))
        rows.append({**params, "contacts": n, "weighted_peak_uA": weighted,
                     "three_contact_bound_uA": weighted*3 if n == 1 else weighted,
                     "raw_contact_peak_uA": float(np.max(np.abs(total_current))*1e6),
                     "in_capacitance_envelope": bounce or params["cw"] <= 200.001e-12})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT/"build/touch-verification")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--reuse", action="store_true")
    parser.add_argument("--workers", type=int, choices=(1, 2, 3), default=2)
    parser.add_argument("--case", action="append", help="Named corner family; omit for the complete suite")
    parser.add_argument("--interaction", action="store_true",
                        help="Single-electrode/crosstalk suite with independent interference phases")
    parser.add_argument("--cxx", default="g++")
    args = parser.parse_args()
    sources = [ROOT/'VW-MTC1/Firmware/touch_decoder.h',
               ROOT/'VW-MTC1/Firmware/touch_acquisition.h',
               ROOT/'VW-MTC1/Simulation/tools/touch.py',
               ROOT/'scripts/verify_touch.py', ROOT/'tests/touch_decoder_test.cpp']
    source_hashes = {str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in sources}
    selected = [c for c in CORNERS if not args.case or c[0] in args.case]
    if args.interaction:
        selected = [c for c in selected if c[0].startswith(("low_", "high_")) and c[-1] in (50, 60)]
    if not selected or (args.case and set(args.case)-{c[0] for c in selected}):
        parser.error("Unknown corner family")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    executable = output/("touch_decoder.exe" if __import__('os').name == 'nt' else "touch_decoder")
    subprocess.run([args.cxx, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
                    str(ROOT/"tests/touch_decoder_test.cpp"), "-o", str(executable)], check=True)
    subprocess.run([str(executable)], check=True)
    all_generated = write_benches(output)
    paths = [p for c, p in zip(CORNERS, all_generated) if c in selected]
    if args.interaction:
        for corner, path in zip(selected, paths):
            path.write_text(bridge_bench(*corner[1:], interaction=True), encoding="utf-8")
    support = []
    for name in ("20261020-Touch-ADC-Settling-Rev01.cir", "20261020-Touch-Board-Capacitor-Current-Rev01.cir"):
        path = output/name
        path.write_bytes((ROOT/"VW-MTC1/Simulation/Touch-Redesign"/name).read_bytes())
        support.append(path)
    for name, bounce in (("contact-current.cir", False), ("contact-bounce.cir", True)):
        path = output/name
        path.write_text(contact_current_bench(bounce), encoding="utf-8")
        support.append(path)
    inputs = paths+support
    receipt_path = output/"runs.json"
    if args.reuse:
        receipts = json.loads(receipt_path.read_text())
        validate_run_receipts(receipts, [p.name for p in inputs], output)
        for row in receipts:
            for suffix in (".raw", ".log"):
                if sha((output/row["circuit"]).with_suffix(suffix)) != row[f"{suffix[1:]}_sha256"]:
                    raise ValueError(f"Changed simulator output: {row['circuit']}{suffix}")
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            receipts = list(pool.map(lambda p: execute(p, args.timeout), inputs))
        receipt_path.write_text(json.dumps(receipts, indent=2)+"\n")

    results, currents, headroom = [], [], []
    for corner, path in zip(selected, paths):
        name, vdd, direction, _, _, hz = corner
        raw = RawRead(path.with_suffix(".raw"))
        steps = step_parameters(decode_text(path.with_suffix(".log").read_bytes()))
        sections = raw.step_slices()
        expected_steps = 192 if args.interaction else SWEEP_STEPS
        if len(steps) != expected_steps or len(sections) != expected_steps:
            raise ValueError(f"Incomplete parameter sweep: {path.name}")
        jobs, lines = [], []
        for params, section in zip(steps, sections):
            index = int(params["phcase"])
            params.update(ph=(index % 4)*90 if args.interaction else (index % 12)*30,
                          limiting_resistor=1.15e6*(.985 if (index % 8 < 4 if args.interaction else index < 12) else 1.015),
                          mains_hz=hz)
            if args.interaction:
                params["active_channel"] = index // 8
            currents.append({"corner": name, **params,
                "sum_abs_pcb_terminal_peak_uA": float(np.max(sum(np.abs(raw[f"I(Rlimit{ch})"][section]) for ch in range(3)))*1e6),
                "sum_abs_raw_contact_peak_uA": float(np.max(sum(np.abs(raw[f"I(Scontact{ch})"][section]) for ch in range(3)))*1e6)})
            linear_ok = all(float(np.min(raw[f"V(sense{ch})"][section])) * (1-.0001*(direction if ch<3 else -direction)) + .0015*(direction if ch<3 else -direction) >= .055 and float(np.max(raw[f"V(sense{ch})"][section])) * (1-.0001*(direction if ch<3 else -direction)) + .0015*(direction if ch<3 else -direction) <= vdd-.055 for ch in range(4))
            # Also test ADC headroom at the LOW reference corner; the waveforms
            # use the high corner for pessimistic quantisation/error sensitivity.
            linear_ok = linear_ok and all(
                float(np.max(raw[f"V(adc{ch})"][section])) <= 2.475*64511/65536
                for ch in range(4))
            headroom.append({"corner": name, **params, "linear_range_pass": linear_ok,
                "sense_min_V": min(float(np.min(raw[f"V(sense{ch})"][section])) for ch in range(4)),
                "sense_max_V": max(float(np.max(raw[f"V(sense{ch})"][section])) for ch in range(4))})
            for error in (-12, 0, 12):
                times, high, codes = sample_codes(raw, section, vdd, error)
                lines.append("0 0 0 0 0 0\n")
                lines.extend(f"{t} {int(h)} {' '.join(map(str, code))}\n" for t, h, code in zip(times, high, codes))
                jobs.append((params, error, times))
        response = subprocess.run([str(executable), "--replay"], input="".join(lines), capture_output=True, text=True, check=True)
        decoded = np.asarray([[int(x) for x in line.split()] for line in response.stdout.splitlines()], dtype=np.int64)
        if len(decoded) != sum(len(job[2]) for job in jobs):
            raise ValueError("Incomplete C++ replay")
        offset = 0
        for params, error, times in jobs:
            samples = decoded[offset:offset+len(times)]
            offset += len(times)
            if not np.array_equal(samples[:,0], times):
                raise ValueError("Replay timestamp mismatch")
            # Firmware rejects delivery beyond 150 us, including the 48 us
            # serial transfer and processing. Use that full bound here.
            ready = times/1e9 + 150e-6
            for ch in range(3):
                if args.interaction and ch != params["active_channel"]:
                    idle = bool(np.all(samples[ready >= .006,1]) and
                                not np.any(samples[ready >= .006,2] & (1 << ch)))
                    metrics = dict(short_contact_pass=idle, short_pair_pass=idle,
                                   gap_pair_pass=idle, idle_channel=True,
                                   short_onset_delay_ms=None, release_delay_ms=None,
                                   second_onset_delay_ms=None)
                else:
                    metrics = event_metrics(ready, samples[:,1].astype(bool), samples[:,2], ch, params["off"])
                results.append({"corner": name, **params, "error_lsb": error, "channel": ch,
                                **metrics})
        print(f"{name}: {len(jobs)*3} channel replays", flush=True)
        del raw, lines, decoded, response

    sampler = RawRead(support[0].with_suffix(".raw"))
    sampler_sections = sampler.step_slices()
    if len(sampler_sections) != 20:
        raise ValueError("Incomplete ADC acquisition sweep")
    settling = max(abs(float(np.interp(52.25e-6, sampler['time'][s], sampler['V(buf)'][s]-sampler['V(sample)'][s]))) for s in sampler_sections)
    capacitor = RawRead(support[1].with_suffix(".raw"))
    capacitor_steps = step_parameters(decode_text(support[1].with_suffix(".log").read_bytes()))
    if len(capacitor_steps) != 2 or len(capacitor.step_slices()) != 2:
        raise ValueError("Incomplete board capacitor sweep")
    peaks = {p['rl']:float(np.max(capacitor['V(total)'][s])*1e6) for p,s in zip(capacitor_steps,capacitor.step_slices())}
    current_rows = current_results(support[2])
    bounce_rows = current_results(support[3], bounce=True)
    operating_current = [r['three_contact_bound_uA'] for r in current_rows if r['in_capacitance_envelope']]
    current_peak = max(operating_current+[r['three_contact_bound_uA'] for r in bounce_rows])
    oversized = [r['three_contact_bound_uA'] for r in current_rows if not r['in_capacitance_envelope']]
    failed = [r for r in results if not r['short_contact_pass'] or not r['short_pair_pass'] or not r['gap_pair_pass']]
    summary = {
        'revision':'B', 'suite':'interaction' if args.interaction else 'simultaneous',
        'complete_suite': not args.case and len(selected)==(8 if args.interaction else len(CORNERS)),
        'model':'LTspice26.1.1; bounded OPA4323 surrogate; ADS8344NB error and timing envelope',
        'simulation_cases':len(currents), 'channel_replays':len(results), 'functional_failures':len(failed),
        'analogue_headroom_pass':all(r['linear_range_pass'] for r in headroom),
        'max_short_onset_delay_ms':max(r['short_onset_delay_ms'] or 0 for r in results),
        'max_release_delay_ms':max(r['release_delay_ms'] or 0 for r in results),
        'max_second_onset_delay_ms':max(r['second_onset_delay_ms'] or 0 for r in results),
        'adc_acquisition_cases':20, 'adc_acquisition_max_error_uV':settling*1e6,
        'adc_acquisition_pass':settling <= 2.475/65536/2,
        'original_board_capacitor_peak_uA':peaks[9900],
        'board_capacitor_peak_uA':peaks[1132750],
        'contact_current_cases':len(current_rows), 'contact_bounce_cases':len(bounce_rows),
        'contact_weighted_three_input_peak_uA':current_peak,
        # An out-of-envelope cable is unsafe when ANY tolerance corner exceeds
        # the ceiling; requiring every corner to fail hid a valid regression.
        'oversized_capacitance_negative_control_detected':max(oversized)>10,
        'oversized_capacitance_peak_uA':max(oversized),
        'legacy_current_negative_control_detected':peaks[9900]>10,
        'current_definition':'Peak sum at the published 1 kOhm / 10 kOhm / 15 nF measuring network, all three inputs including stored charge; separate unweighted PCB bound. Not an unlimited-bandwidth contact-current claim.',
        'current_limit_pass':current_peak<=10 and peaks[1132750]<=10,
        'source_sha256':source_hashes,
    }
    summary['pass'] = (not failed and summary['analogue_headroom_pass'] and summary['adc_acquisition_pass'] and summary['current_limit_pass']
                       and summary['oversized_capacitance_negative_control_detected'] and summary['legacy_current_negative_control_detected'])
    if source_hashes != {str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in sources}:
        raise RuntimeError("Sources changed during verification; rerun before accepting the results")
    report={**summary,'results':results,'terminal_currents':currents,'analogue_headroom':headroom,
            'contact_current':current_rows,'contact_bounce':bounce_rows}
    (output/'results.json').write_text(json.dumps(report,indent=2)+"\n")
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary,indent=2))
    if failed: print('First functional failure:',json.dumps(failed[0]))
    return 0 if summary['pass'] else 1


if __name__=='__main__':
    raise SystemExit(main())
