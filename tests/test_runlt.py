import subprocess
from unittest.mock import Mock

import pytest

from vw_mtc1 import runlt


@pytest.fixture
def simulation(tmp_path, monkeypatch):
    circuit = tmp_path / "test.cir"
    circuit.write_text("* test\n.end\n")
    process = Mock()
    process.wait.return_value = 0
    monkeypatch.setattr(runlt.subprocess, "Popen", Mock(return_value=process))
    monkeypatch.setattr(runlt, "find_ltspice", lambda executable=None: "fake-ltspice")
    return circuit, process


def test_missing_log_is_failure(simulation):
    circuit, _ = simulation
    assert runlt.run(circuit)[0] != 0


def test_stale_log_is_failure(simulation):
    circuit, _ = simulation
    circuit.with_suffix(".log").write_text("old successful run")
    assert runlt.run(circuit)[0] != 0


@pytest.mark.parametrize("message", ["Error: unknown device", "Singular matrix", "Time step too small", 'Measurement "t90" FAIL\'ed'])
def test_log_failures_are_not_success(simulation, message):
    circuit, process = simulation
    def finish(**kwargs):
        circuit.with_suffix(".log").write_text(message)
        return 0
    process.wait.side_effect = finish
    assert runlt.run(circuit)[0] != 0


def test_error_word_in_circuit_name_is_not_failure(simulation):
    circuit, process = simulation
    def finish(**kwargs):
        circuit.with_suffix(".log").write_text("Circuit: error_budget.cir\nTotal elapsed time: 1 second")
        return 0
    process.wait.side_effect = finish
    assert runlt.run(circuit)[0] == 0


def test_process_exit_code_is_propagated(simulation):
    circuit, process = simulation
    process.wait.return_value = 7
    assert runlt.run(circuit)[0] == 7


def test_timeout_kills_and_reaps_its_child(simulation):
    circuit, process = simulation
    process.wait.side_effect = [subprocess.TimeoutExpired("ltspice", .1), -9]
    assert runlt.run(circuit, timeout=.1)[0] == 2
    process.kill.assert_called_once_with()
    assert process.wait.call_count == 2


@pytest.mark.parametrize("encoding", ["latin-1", "utf-16-le", "utf-16", "utf-16-be", "utf-8-sig"])
def test_read_log_encodings(tmp_path, encoding):
    path = tmp_path / "test.log"
    payload = "Error: test".encode(encoding)
    path.write_bytes(b"\xfe\xff" + payload if encoding == "utf-16-be" else payload)
    assert runlt.read_log(path) == "Error: test"


def test_executable_override_and_environment(monkeypatch):
    monkeypatch.setenv("LTSPICE_EXE", "/custom/simulator")
    assert runlt.find_ltspice() == "/custom/simulator"
    assert runlt.find_ltspice("/explicit/simulator") == "/explicit/simulator"


def test_executable_path_search(monkeypatch):
    monkeypatch.delenv("LTSPICE_EXE", raising=False)
    monkeypatch.setattr(runlt.shutil, "which", lambda name: "/bin/ltspice")
    assert runlt.find_ltspice() == "/bin/ltspice"


def test_missing_executable_has_actionable_message(monkeypatch):
    for name in ("LTSPICE_EXE", "LOCALAPPDATA", "ProgramFiles"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(runlt.shutil, "which", lambda name: None)
    with pytest.raises(FileNotFoundError, match="LTSPICE_EXE"):
        runlt.find_ltspice()


def test_standard_windows_location(tmp_path, monkeypatch):
    executable = tmp_path / "Programs/ADI/LTspice/LTspice.exe"
    executable.parent.mkdir(parents=True)
    executable.touch()
    monkeypatch.delenv("LTSPICE_EXE", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(runlt.shutil, "which", lambda name: None)
    assert runlt.find_ltspice() == str(executable)


@pytest.mark.parametrize("timeout", [0, -1, float('nan'), float('inf')])
def test_invalid_timeout_and_missing_circuit(simulation, timeout):
    circuit, _ = simulation
    with pytest.raises(ValueError):
        runlt.run(circuit, timeout=timeout)
    with pytest.raises(FileNotFoundError):
        runlt.run(circuit.with_name("missing.cir"))
