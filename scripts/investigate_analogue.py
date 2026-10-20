"""Run or reanalyse the committed charger/touch diagnostic netlists."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import time
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from vw_mtc1.investigation import step_parameters, termination_metrics, touch_pair_metrics, validate_run_receipts
from vw_mtc1.ltraw import RawRead
from vw_mtc1.runlt import read_log, run


STEMS = {
    "charger_ramp": ("20261020-Charger-Termination-Rev00", 9),
    "charger_scale": ("20261020-Charger-Scale-Rev00", 4),
    "touch_gap": ("20261020-Touch-Gap-Rev00", 360),
    "touch_thresholds": ("20261020-Touch-Thresholds-Rev00", 180),
}


def analyse(output):
    report = {}
    for study, (stem, count) in STEMS.items():
        raw = RawRead(output / (stem + ".raw"))
        params = step_parameters(read_log(output / (stem + ".log")))
        slices = raw.step_slices()
        if len(params) != count or len(slices) != count:
            raise ValueError(f"{study}: expected {count} steps, found {len(params)} log records/{len(slices)} raw runs")
        rows = []
        for values, selection in zip(params, slices):
            t = raw["time"][selection]
            if study.startswith("charger"):
                scale = values.get("scale", 1.)
                window = (.02, .1) if study == "charger_ramp" else (3 * scale, 3.5 * scale)
                after = .2 if study == "charger_ramp" else 3 * scale
                cc_samples = (t >= window[0]) & (t <= window[1])
                if np.median(raw["V(chrg)"][selection][cc_samples]) >= 1.:
                    raise ValueError(f"{study}: model did not assert charging status during the CC reference window")
                result = termination_metrics(t, raw["I(Vsense)"][selection],
                                             raw["V(prog)"][selection], values.get("rp", 2490),
                                             window, after)
                result["datasheet_rprog_test_condition"] = values.get("rp") in (2000, 10000)
                if study == "charger_scale":
                    cell = termination_metrics(t, raw["I(Rint)"][selection],
                                               raw["V(prog)"][selection], 2490, window, after)
                    result["cell_termination_current_mA"] = cell["termination_current_mA"]
            else:
                if study == "touch_gap":
                    case = int(values["case"])
                    gap = [.005, .010, .015, .020, .025][case % 5]
                    values.update({"gap": gap, "cf": 15e-9 if case < 5 else 27e-9, "supply": 3.3})
                else:
                    values.update({"cf": 27e-9, "cc": 100e-12,
                                   "supply": 3.3 if values["th"] == 0 else 3.})
                result = touch_pair_metrics(t, raw["V(in)"][selection], raw["V(out)"][selection],
                                            values["gap"], values["supply"])
            rows.append({"parameters": values, **result})
        report[study] = rows
    return report


def plot_results(report, output):
    measurements = report["measurements"]
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5), layout="constrained")
    ax = axes[0, 0]
    ax.axhspan(8.5, 11.5, color="#dcefdc", label="Datasheet range at 2k / 10k")
    for step, marker in ((1e-5, "o"), (1e-4, "s"), (.001, "^")):
        rows = [r for r in measurements["charger_ramp"] if r["parameters"]["tmax"] == step]
        ax.plot([r["parameters"]["rp"] / 1000 for r in rows],
                [r["termination_fraction"] * 100 for r in rows], marker,
                label=f"Max timestep {step * 1e6:g} us")
    ax.set(xlabel="RPROG (kohm)", ylabel="Termination / measured CC (%)",
           title="Charger model: termination ratio", ylim=(0, 13))
    ax.legend(fontsize=7)
    ax.grid(alpha=.2)
    ax = axes[0, 1]
    for step, marker in ((.0002, "o"), (.002, "s")):
        rows = [r for r in measurements["charger_scale"] if r["parameters"]["tmax"] == step]
        ax.plot([r["parameters"]["scale"] for r in rows],
                [r["termination_current_mA"] for r in rows], marker + "-",
                label=f"Max timestep {step * 1000:g} ms")
    ax.axhspan(30, 50, color="#dcefdc", label="Existing project target")
    ax.set(xlabel="Battery capacitance scale (1 = 1.5 F)", ylabel="Termination current (mA)",
           title="Original charger topology: scale control", ylim=(25, 52))
    ax.legend(fontsize=7)
    ax.grid(alpha=.2)
    ax = axes[1, 0]
    base = output / STEMS["touch_gap"][0]
    raw = RawRead(base.with_suffix(".raw"))
    for params, selection in zip(step_parameters(read_log(base.with_suffix(".log"))), raw.step_slices()):
        if params["case"] == 5 and params["cc"] == 100e-12 and params["ph"] in (0, 90):
            t = raw["time"][selection]
            mask = (t >= .155) & (t <= .174)
            ax.plot(t[mask] * 1000, raw["V(in)"][selection][mask], label=f"Phase {params['ph']:g} deg")
    ax.axvspan(160, 165, color="#f4e4b7", alpha=.7, label="5 ms release gap")
    ax.axhline(1.7, color="#444444", linestyle="--", label="Assumed rising threshold")
    ax.set(xlabel="Time (ms)", ylabel="Schmitt input (V)", title="27 nF, 100 pF coupling: gap recovery")
    ax.legend(fontsize=7)
    ax.grid(alpha=.2)
    ax = axes[1, 1]
    gaps = [.005, .01, .015, .02, .025]
    couplings = [0., 50e-12, 100e-12]
    matrix = np.array([[sum(r["gap_and_idle_pass"] for r in measurements["touch_gap"]
                           if r["parameters"]["cf"] == 27e-9 and r["parameters"]["cc"] == cc
                           and r["parameters"]["gap"] == gap) for gap in gaps] for cc in couplings])
    ax.imshow(matrix, vmin=0, vmax=12, cmap="YlGn", aspect="auto")
    for (y, x), value in np.ndenumerate(matrix):
        ax.text(x, y, f"{value}/12", ha="center", va="center",
                color="white" if value >= 9 else "black")
    ax.set(xticks=range(5), xticklabels=[5, 10, 15, 20, 25],
           yticks=range(3), yticklabels=[0, 50, 100], xlabel="Contact gap (ms)",
           ylabel="Mains coupling (pF)", title="27 nF: passing sampled phases")
    fig.suptitle("VW-MTC1 analogue investigation - model results, not hardware measurements")
    path = output / "20261020-Charger-Touch-Investigation-Rev00.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(f"Wrote {path}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("build/analogue-investigation"))
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--analyse-only", action="store_true")
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1] / "VW-MTC1/Simulation/Investigations"
    args.output.mkdir(parents=True, exist_ok=True)
    receipts_path = args.output / "run-receipts.json"
    if not args.analyse_only:
        receipts = []
        for stem, _ in STEMS.values():
            circuit = args.output / (stem + ".cir")
            shutil.copy2(source / circuit.name, circuit)
            start = time.monotonic()
            code, _ = run(circuit, timeout=args.timeout)
            receipts.append({"circuit": circuit.name, "exit_code": code,
                             "seconds": round(time.monotonic() - start, 2),
                             "timeout_seconds": args.timeout,
                             "netlist_sha256": hashlib.sha256(circuit.read_bytes()).hexdigest()})
            receipts_path.write_text(json.dumps(receipts, indent=2), encoding="utf-8")
            if code:
                raise SystemExit(f"Diagnostic run failed: {circuit}; inspect its log before analysing")
    receipts = json.loads(receipts_path.read_text(encoding="utf-8"))
    validate_run_receipts(receipts, [stem + ".cir" for stem, _ in STEMS.values()], args.output)
    report = {
        "sources": {
            "charger": "https://www.analog.com/media/en/technical-documentation/data-sheets/405442xf.pdf",
            "buffer": "https://www.ti.com/lit/ds/symlink/sn74lvc3g17.pdf",
        },
        "runs": receipts,
        "measurements": analyse(args.output),
    }
    model_log = read_log(args.output / (STEMS["charger_ramp"][0] + ".log"))
    model_paths = [Path(line.strip()) for line in model_log.splitlines()
                   if line.strip().lower().endswith("ltc4054-4.2.sub")]
    if len(model_paths) != 1 or not model_paths[0].is_file():
        raise ValueError("Cannot identify the charger model used by LTspice")
    report["model"] = {
        "file": model_paths[0].name,
        "sha256": hashlib.sha256(model_paths[0].read_bytes()).hexdigest(),
        "simulator": model_log.splitlines()[0],
    }
    path = args.output / "investigation-results.json"
    path.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    print(f"Wrote {path}", flush=True)
    plot_results(report, args.output)


if __name__ == "__main__":
    main()
