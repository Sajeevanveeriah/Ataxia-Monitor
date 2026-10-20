import numpy as np
import pytest

from vw_mtc1.waveform import low_intervals, moving_average


@pytest.mark.parametrize("levels,intervals", [
    ([3.3, 3.3, 3.3, 3.3], []),
    ([0, 0, 0, 0], [(0, 3)]),
    ([0, 3.3, 0, 3.3], [(0, 1), (2, 3)]),
    ([3.3, 0, 0, 0], [(1, 3)]),
    ([1.65, 1.65, 0, 3.3], [(2, 3)]),
])
def test_contact_pulses(levels, intervals):
    assert low_intervals(np.arange(4), np.array(levels)) == intervals


@pytest.mark.parametrize("width", [.01, 1., 2.])
def test_smoothing_preserves_dc_at_both_edges(width):
    t, y = moving_average(np.array([0., 1., 2.]), np.array([3.3, 3.3, 3.3]), width, dt=.1)
    assert len(t) == len(y) == 20
    np.testing.assert_allclose(y, 3.3)


def test_smoothing_reduces_alternating_noise():
    source_t = np.arange(20, dtype=float)
    source_y = np.tile([0., 2.], 10)
    _, y = moving_average(source_t, source_y, win=2, dt=1)
    np.testing.assert_allclose(y[1:], 1)
