import json
import hashlib
import numpy as np
import pytest

from vw_mtc1.investigation import step_parameters, termination_metrics, touch_pair_metrics, validate_run_receipts


@pytest.mark.parametrize("fault", [None, "failed", "changed", "missing"])
def test_reanalysis_requires_successful_unchanged_inputs(tmp_path, fault):
    circuit = tmp_path / "probe.cir"
    circuit.write_bytes(b"fixture")
    receipts = [{"circuit": circuit.name, "exit_code": 0,
                 "netlist_sha256": hashlib.sha256(circuit.read_bytes()).hexdigest()}]
    if fault == "failed":
        receipts[0]["exit_code"] = 1
    elif fault == "changed":
        circuit.write_bytes(b"changed")
    elif fault == "missing":
        receipts = []
    if fault is None:
        validate_run_receipts(receipts, [circuit.name], tmp_path)
    else:
        with pytest.raises(ValueError):
            validate_run_receipts(receipts, [circuit.name], tmp_path)


def test_step_order_comes_from_log():
    assert step_parameters(".step rp=10000 tmax=1e-05\n.step rp=2000 tmax=0.001\n") == [
        {"rp": 10000., "tmax": 1e-5}, {"rp": 2000., "tmax": .001},
    ]
    with pytest.raises(ValueError):
        step_parameters(".step unsupported-record")


@pytest.mark.parametrize("fraction,status", [(.07, "FAIL"), (.1, "PASS"), (.13, "FAIL")])
def test_termination_ratio_does_not_turn_a_low_current_into_a_pass(fraction, status):
    t = np.arange(0, 1.10001, .0001)
    current = np.where(t < .5, .4, np.where(t < 1, .4 * fraction, 0))
    prog = current * 2490 / 1000
    result = termination_metrics(t, current, prog, 2490, (.1, .2), .6)
    assert result["termination_fraction"] == pytest.approx(fraction)
    assert result["datasheet_ratio_check"] == status
    assert result["observed_current_to_prog_ratio"] == pytest.approx(1000)


def test_no_cutoff_is_rejected():
    t = np.linspace(0, 2, 10001)
    with pytest.raises(ValueError):
        termination_metrics(t, np.full_like(t, .4), np.full_like(t, 1.), 2490, (.1, .2), .5)


def pair_trace(spans, supply=3.3):
    t = np.arange(0, .27001, .0001)
    out = np.full_like(t, supply)
    for start, end in spans:
        out[(t >= start) & (t < end)] = 0
    return t, np.full_like(t, 1.5), out


@pytest.mark.parametrize("onset_delay", [.0005, .0095])
def test_two_contact_onsets_with_a_high_gap_pass(onset_delay):
    t, vin, out = pair_trace([(.140 + onset_delay, .163), (.165 + onset_delay, .19)])
    result = touch_pair_metrics(t, vin, out, .005)
    assert result["gap_resolved"] and result["gap_and_idle_pass"]
    assert result["contact_onsets"] == [1, 1]
    assert json.loads(json.dumps(result, allow_nan=False)) == result


def test_merged_contact_fails():
    t, vin, out = pair_trace([(.1405, .19)])
    result = touch_pair_metrics(t, vin, out, .005)
    assert not result["gap_resolved"]
    assert not result["high_during_gap"]


def test_two_chatter_pulses_are_not_two_contacts():
    t, vin, out = pair_trace([(.1405, .142), (.143, .19)])
    result = touch_pair_metrics(t, vin, out, .005)
    assert result["pair_pulses"] == 2
    assert not result["gap_resolved"]


def test_idle_noise_fails_even_when_gap_is_resolved():
    t, vin, out = pair_trace([(.05, .055), (.1405, .163), (.1655, .19)], supply=3.)
    result = touch_pair_metrics(t, vin, out, .005, supply=3.)
    assert result["gap_resolved"]
    assert result["idle_pulses"] == 1
    assert not result["gap_and_idle_pass"]
