import importlib
import json
from pathlib import Path
import shutil

from vw_mtc1 import common


def test_importing_schematic_generator_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "LT", str(tmp_path))
    importlib.import_module("vw_mtc1.make_asc")
    assert list(tmp_path.iterdir()) == []


def test_importing_summary_generator_writes_nothing(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[1] / "VW-MTC1/Simulation"
    results = tmp_path / "results.json"
    shutil.copy2(source / "results.json", results)
    shutil.copy2(source / "LTspice/sim00_mosfet_model_check.log", tmp_path)
    before = results.read_bytes()
    monkeypatch.setattr(common, "ROOT", str(tmp_path))
    monkeypatch.setattr(common, "RESULTS", str(results))
    monkeypatch.setattr(common, "LT", str(tmp_path))
    importlib.import_module("vw_mtc1.make_summary")
    assert results.read_bytes() == before
    assert not (tmp_path / "Simulation_Summary.md").exists()


def test_schematic_build(tmp_path, monkeypatch):
    from vw_mtc1 import make_asc
    monkeypatch.setattr(make_asc, "LT", str(tmp_path))
    make_asc.main()
    paths = sorted(tmp_path.glob("*.asc"))
    assert len(paths) == 2
    for path in paths:
        data = path.read_bytes()
        assert data.startswith(b"Version 4\r\n")
        assert b"SYMBOL " in data and b"TEXT " in data


def test_summary_build_reads_measurements_and_preserves_other_results(tmp_path, monkeypatch):
    from vw_mtc1 import make_summary
    source = Path(__file__).resolve().parents[1] / "VW-MTC1/Simulation"
    results = tmp_path / "results.json"
    shutil.copy2(source / "results.json", results)
    shutil.copy2(source / "LTspice/sim00_mosfet_model_check.log", tmp_path)
    original = json.loads(results.read_text())
    monkeypatch.setattr(make_summary, "ROOT", str(tmp_path))
    monkeypatch.setattr(make_summary, "RESULTS", str(results))
    monkeypatch.setattr(make_summary, "LT", str(tmp_path))
    make_summary.main()
    generated = json.loads(results.read_text())
    for key in original:
        if key != "SIM00_mosfet_models":
            assert generated[key] == original[key]
    summary = (tmp_path / "Simulation_Summary.md").read_text(encoding="utf-8")
    assert summary.startswith("# VW-MTC1 Simulation Summary")
    assert "FAIL" in summary
    assert "SIM07" in summary
