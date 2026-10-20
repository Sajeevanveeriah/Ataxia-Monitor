"""Run the candidate touch LTspice sweep and replay its real C++ decoder.

Raw waveforms stay in --output. The JSON includes failures. Exit 0 requires
functional checks and an explicitly selected current boundary to pass; exit 1
means a failed check and exit 2 means that the current boundary is unresolved.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

from vw_mtc1.investigation import step_parameters, validate_run_receipts
from vw_mtc1.ltraw import RawRead
from vw_mtc1.lttext import decode_text
from vw_mtc1.runlt import run
from vw_mtc1.touch import CORNERS, event_metrics, sample_codes, write_benches

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build" / "touch-verification")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--reuse", action="store_true",
                        help="Reuse matching, successful LTspice receipts and raw hashes")
    parser.add_argument("--cxx", default="g++")
    parser.add_argument("--current-boundary", choices=("unresolved", "pcb-source", "contact"),
                        default="unresolved", help="An explicit engineering requirement, not a plotting option")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    executable = output / ("touch_decoder.exe" if sys.platform == "win32" else "touch_decoder")
    subprocess.run([args.cxx, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
                    str(ROOT / "tests" / "touch_decoder_test.cpp"), "-o", str(executable)], check=True)
    subprocess.run([str(executable)], check=True)
    paths = write_benches(output)
    supporting = []
    for name in ("20261020-Touch-ADC-Settling-Rev00.cir",
                 "20261020-Touch-Board-Capacitor-Current-Rev00.cir"):
        path = output / name
        path.write_bytes((ROOT / "VW-MTC1" / "Simulation" / "Touch-Redesign" / name).read_bytes())
        supporting.append(path)
    all_paths = paths + supporting
    receipt_path = output / "runs.json"
    if args.reuse:
        receipts = json.loads(receipt_path.read_text())
        validate_run_receipts(receipts, [p.name for p in all_paths], output)
        for row in receipts:
            for suffix in (".raw", ".log"):
                path = (output / row["circuit"]).with_suffix(suffix)
                if sha(path) != row[f"{suffix[1:]}_sha256"]:
                    raise ValueError(f"Changed simulator output: {path}")
    else:
        receipts = []
        for path in all_paths:
            result = run(path, timeout=args.timeout)
            row = {"circuit": path.name, "exit_code": result[0], "netlist_sha256": sha(path)}
            if result[0]:
                raise RuntimeError(f"LTspice failed: {path.name}")
            row.update({f"{suffix[1:]}_sha256": sha(path.with_suffix(suffix)) for suffix in (".raw", ".log")})
            receipts.append(row)
            receipt_path.write_text(json.dumps(receipts, indent=2) + "\n")

    results, currents = [], []
    for corner, path in zip(CORNERS, paths):
        name, vdd, *_ = corner
        raw = RawRead(path.with_suffix(".raw"))
        steps = step_parameters(decode_text(path.with_suffix(".log").read_bytes()))
        sections = raw.step_slices()
        if len(steps) != 192 or len(sections) != len(steps):
            raise ValueError(f"Incomplete parameter sweep in {path}")
        jobs, lines = [], []
        for params, section in zip(steps, sections):
            currents.append({
                "corner": name, **params,
                "sum_positive_pcb_terminal_peak_uA": float(np.max(sum(
                    np.maximum(raw[f"I(Rlimit{ch})"][section], 0)
                    for ch in range(3))) * 1e6),
                "external_contact0_peak_uA": float(np.max(raw["I(Scontact0)"][section]) * 1e6),
                "sum_positive_external_contact_peak_uA": float(np.max(sum(
                    np.maximum(raw[f"I(Scontact{ch})"][section], 0)
                    for ch in range(3))) * 1e6),
            })
            for error in (-2, 0, 2):
                times, high, codes = sample_codes(raw, section, vdd, error, jitter_us=3)
                lines.append("0 0 0 0 0 0\n")
                lines.extend(f"{t} {int(h)} {' '.join(map(str, code))}\n"
                             for t, h, code in zip(times, high, codes))
                jobs.append((params, error, times))
        response = subprocess.run([str(executable), "--replay"], input="".join(lines),
                                  capture_output=True, text=True, check=True)
        decoded = np.asarray([[int(x) for x in line.split()]
                              for line in response.stdout.splitlines()], dtype=np.int64)
        if len(decoded) != sum(len(job[2]) for job in jobs):
            raise ValueError("Decoder replay did not return every sample")
        offset = 0
        for params, error, times in jobs:
            sample = decoded[offset:offset + len(times)]
            offset += len(times)
            if not np.array_equal(sample[:, 0], times):
                raise ValueError("Decoder output sample order mismatch")
            for ch in range(3):
                results.append({"corner": name, **params, "error_lsb": error, "channel": ch,
                                **event_metrics(times / 1e6, sample[:, 1].astype(bool),
                                                sample[:, 2], ch, params["off"])})
        print(f"{name}: {len(jobs)*3} channel replays complete", flush=True)

    failed = [x for x in results if not x["short_contact_pass"] or not x["gap_pair_pass"]]
    sampler = RawRead(supporting[0].with_suffix(".raw"))
    sampler_sections = sampler.step_slices()
    if len(sampler_sections) != 20:
        raise ValueError("Incomplete ADC acquisition sweep")
    settling_error = max(abs(float(np.interp(51.5e-6, sampler["time"][s],
                                            sampler["V(buf)"][s] - sampler["V(sample)"][s])))
                         for s in sampler_sections)
    capacitor = RawRead(supporting[1].with_suffix(".raw"))
    capacitor_steps = step_parameters(decode_text(supporting[1].with_suffix(".log").read_bytes()))
    if len(capacitor_steps) != 2 or len(capacitor.step_slices()) != 2:
        raise ValueError("Incomplete board-capacitor current sweep")
    peaks = {step["rl"]: float(np.max(capacitor["V(total)"][s]) * 1e6)
             for step, s in zip(capacitor_steps, capacitor.step_slices())}
    board_peak = max(peaks[1188000], max(x["sum_positive_pcb_terminal_peak_uA"]
                     for x in currents if x["corner"] == "board_only"))
    contact_peak = max(x["sum_positive_external_contact_peak_uA"]
                      for x in currents if x["corner"] == "board_only")
    selected_peak = {"pcb-source": board_peak, "contact": contact_peak}.get(args.current_boundary)
    current_pass = None if selected_peak is None else selected_peak <= 10
    report = {
        "model": "LTspice 26.1.1; bounded buffer surrogate, sampled MCP3204 error envelope",
        "decoder_sha256": sha(ROOT / "VW-MTC1" / "Firmware" / "touch_decoder.h"),
        "simulation_cases": len(currents), "channel_replays": len(results),
        "functional_failures": len(failed),
        "max_short_onset_delay_ms": max(x["short_onset_delay_ms"] or 0 for x in results),
        "max_release_delay_ms": max(x["release_delay_ms"] or 0 for x in results),
        "max_second_onset_delay_ms": max(x["second_onset_delay_ms"] or 0 for x in results),
        "adc_acquisition_cases": len(sampler_sections),
        "adc_acquisition_max_error_uV": settling_error * 1e6,
        "adc_acquisition_pass": settling_error <= 3.48 / 4096 / 2,
        "original_board_capacitor_peak_uA": peaks[9900],
        "board_only_terminal_peak_uA": board_peak,
        "all_sources_terminal_peak_uA": max(x["sum_positive_pcb_terminal_peak_uA"] for x in currents),
        "external_contact_peak_uA_board_sources_only": contact_peak,
        "current_boundary": args.current_boundary,
        "current_limit_pass": current_pass,
        "current_acceptance": "PENDING measurement-boundary clarification" if current_pass is None
            else ("PASS at selected boundary only" if current_pass else "FAIL at selected boundary"),
        "results": results, "currents": currents,
    }
    (output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ("results", "currents")}, indent=2))
    if failed or not report["adc_acquisition_pass"] or current_pass is False:
        return 1
    return 2 if current_pass is None else 0


if __name__ == "__main__":
    raise SystemExit(main())
