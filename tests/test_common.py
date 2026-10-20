import json

import matplotlib.pyplot as plt
import numpy as np
import pytest

from vw_mtc1 import common


@pytest.mark.parametrize("passed,status", [(True, "PASS"), (False, "FAIL"), (None, "INFO"), (np.bool_(True), "PASS")])
def test_check_serialises_numpy_scalars(passed, status):
    result = common.check(np.float64(3.3), "V", "3.0 to 3.6", passed, "fixture")
    assert result["result"] == status
    assert json.loads(json.dumps(result))["value"] == 3.3


def test_updates_preserve_other_simulations(tmp_path, monkeypatch):
    path = tmp_path / "results.json"
    monkeypatch.setattr(common, "RESULTS", str(path))
    common.update_results("A", {"value": 1})
    common.update_results("B", {"value": 2})
    common.update_results("A", {"value": 3})
    assert json.loads(path.read_text()) == {"A": {"value": 3}, "B": {"value": 2}}


def test_serialisation_failure_preserves_existing_results(tmp_path, monkeypatch):
    path = tmp_path / "results.json"
    original = b'{"previous": {"value": 3.3}}'
    path.write_bytes(original)
    monkeypatch.setattr(common, "RESULTS", str(path))
    with pytest.raises(TypeError):
        common.update_results("new", {"invalid": object()})
    assert path.read_bytes() == original


def test_savefig_creates_missing_plot_directory(tmp_path, monkeypatch):
    folder = tmp_path / "new" / "Plots"
    monkeypatch.setattr(common, "PLOTS", str(folder))
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    common.savefig(fig, "test.png")
    assert (folder / "test.png").read_bytes().startswith(b"\x89PNG")
    assert not plt.fignum_exists(fig.number)


def test_replace_failure_preserves_results_and_cleans_temporary(tmp_path, monkeypatch):
    path = tmp_path / "results.json"
    path.write_text('{"A": 1}')
    monkeypatch.setattr(common, "RESULTS", str(path))
    def denied(*args):
        raise PermissionError("fixture")
    monkeypatch.setattr(common.os, "replace", denied)
    with pytest.raises(PermissionError):
        common.update_results("B", 2)
    assert path.read_text() == '{"A": 1}'
    assert list(tmp_path.iterdir()) == [path]


def test_nonfinite_results_do_not_replace_evidence(tmp_path, monkeypatch):
    path = tmp_path / "results.json"
    path.write_text('{"A": 1}')
    monkeypatch.setattr(common, "RESULTS", str(path))
    with pytest.raises(ValueError):
        common.update_results("B", float("nan"))
    assert path.read_text() == '{"A": 1}'
