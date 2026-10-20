import numpy as np
import pytest

from vw_mtc1.touch import event_metrics


def stimulus():
    t = np.arange(.0004, .115, .0005)
    state = np.zeros(len(t), dtype=int)
    for start, stop in ((.02, .022), (.05, .07), (.075, .095)):
        state[(t >= start + .0015) & (t < stop + .0015)] = 7
    valid = t >= .005
    return t, valid, state


def test_separate_contacts_all_three_channels():
    for channel in range(3):
        result = event_metrics(*stimulus(), channel)
        assert result["gap_pair_pass"]
        assert result["short_contact_pass"]
        assert result["release_delay_ms"] < 5


def test_merged_pair_is_not_counted_as_two_contacts():
    t, valid, state = stimulus()
    state[(t >= .0515) & (t < .0965)] = 7
    assert not event_metrics(t, valid, state, 0)["gap_pair_pass"]


def test_chatter_in_first_touch_does_not_substitute_for_second_touch():
    t, valid, state = stimulus()
    state[t >= .075] = 0
    state[(t >= .06) & (t < .062)] = 0
    assert not event_metrics(t, valid, state, 0)["gap_pair_pass"]


def test_invalid_acquisition_is_not_an_open_gap():
    t, valid, state = stimulus()
    valid[(t >= .07) & (t < .075)] = False
    assert not event_metrics(t, valid, state, 0)["gap_pair_pass"]


def test_idle_false_pulse_rejects_otherwise_good_pair():
    t, valid, state = stimulus()
    state[(t >= .04) & (t < .042)] = 1
    result = event_metrics(t, valid, state, 0)
    assert not result["gap_pair_pass"]
    assert result["idle_or_extra_events"] == 2


def test_contact_has_to_be_released_in_the_actual_gap():
    t, valid, state = stimulus()
    state[(t >= .0715) & (t < .075)] = 7
    assert not event_metrics(t, valid, state, 0)["gap_pair_pass"]


def test_premature_release_during_a_held_contact_is_a_failure():
    t, valid, state = stimulus()
    state[(t >= .06) & (t < .075)] = 0
    assert not event_metrics(t, valid, state, 0)["gap_pair_pass"]


def test_short_pulse_can_be_reported_after_contact_ends_with_bounded_delay():
    t, valid, state = stimulus()
    state[t < .03] = 0
    state[(t >= .0225) & (t < .0245)] = 7
    result = event_metrics(t, valid, state, 0)
    assert result["short_contact_pass"]
    assert 2.5 <= result["short_onset_delay_ms"] < 3


def test_bad_time_axis_and_channel_rejected():
    t, valid, state = stimulus()
    with pytest.raises(ValueError):
        event_metrics(t[::-1], valid, state, 0)
    with pytest.raises(ValueError):
        event_metrics(t, valid, state, 3)
