import random

import config

from emg import ForceEstimator, calibration_ok, direction, max_level, rest_level


def test_direction_zones():
    lo, hi = config.LEFT_MAX, config.RIGHT_MIN
    assert direction(0.0) == -1
    assert direction(lo - 0.01) == -1
    assert direction(lo) == 0
    assert direction((lo + hi) / 2) == 0
    assert direction(hi) == 0
    assert direction(hi + 0.01) == 1
    assert direction(1.0) == 1


def _noise(sigma, n=400, center=0.0, seed=1):
    rng = random.Random(seed)
    return [center + rng.gauss(0, sigma) for _ in range(n)]


def test_force_scales_between_calibrated_rest_and_max():
    est = ForceEstimator()
    est.update(_noise(2.0))
    lo = est.envelope
    est = ForceEstimator()
    est.update(_noise(100.0))
    hi = est.envelope

    est = ForceEstimator()
    est.calibrate(lo, hi)
    est.update(_noise(2.0))
    assert est.force < 0.05
    est = ForceEstimator()
    est.calibrate(lo, hi)
    est.update(_noise(100.0))
    assert est.force > 0.95
    est = ForceEstimator()
    est.calibrate(lo, hi)
    est.update(_noise(51.0))
    assert 0.4 < est.force < 0.6


def test_dc_offset_does_not_count_as_force():
    est = ForceEstimator()
    est.calibrate(2.0, 100.0)
    est.update(_noise(2.0, center=8000.0))
    assert est.force < 0.05


def test_uncalibrated_force_is_zero():
    est = ForceEstimator()
    est.update(_noise(50.0))
    assert est.force == 0.0


def test_force_is_clamped():
    est = ForceEstimator()
    est.calibrate(2.0, 50.0)
    est.update(_noise(300.0))
    assert est.force == 1.0


def test_calibration_levels_and_validation():
    assert rest_level([1, 2, 3]) == 2
    assert max_level(list(range(11))) == 8  # 상위 5개(6~10)의 평균
    assert calibration_ok(2.0, 100.0)
    assert not calibration_ok(50.0, 55.0)
    assert not calibration_ok(0.0, 0.5)


def test_input_gain_boosts_force_by_ten_percent():
    est = ForceEstimator()
    est.calibrate(0.0, 100.0)
    est.envelope = 50.0
    assert abs(est.force - 0.55) < 1e-9
