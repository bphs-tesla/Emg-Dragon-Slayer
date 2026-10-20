from measure import COUNTDOWN, DONE, ERR_LOST, ERR_RANGE, INTRO, MAX, MEASURING, MIN, Measurement


def run(m, seconds, n_samples=10, envelope=2.0, dt=0.05):
    for _ in range(round(seconds / dt)):
        m.update(dt, n_samples, envelope)


def test_intro_waits_for_start():
    m = Measurement()
    run(m, 5)
    assert m.phase == INTRO
    m.start()
    assert (m.phase, m.stage) == (COUNTDOWN, MIN)


def test_countdown_discards_values_then_measures():
    m = Measurement(started=True)
    run(m, 2.9, envelope=99.0)
    assert m.phase == COUNTDOWN and not m.values and m.last_value is None
    run(m, 0.2)
    assert m.phase == MEASURING


def test_full_run_computes_mean_and_top_five_mean():
    m = Measurement(started=True)
    run(m, 3.0 + 3.0 + 0.1, envelope=2.0)
    assert (m.phase, m.stage) == (COUNTDOWN, MAX)
    run(m, 3.0)
    for env in [10, 20, 30, 40, 50] * 3:  # 창 15개
        run(m, 0.2, envelope=env)
    assert m.phase == DONE
    assert m.lo == 2.0
    assert m.hi == 46.0 and m.error == ""  # 상위 5개: 50,50,50,40,40


def test_small_range_restarts_from_min_with_error():
    m = Measurement(started=True)
    run(m, 6.1, envelope=2.0)
    run(m, 6.1, envelope=2.2)
    assert (m.phase, m.stage, m.error) == (COUNTDOWN, MIN, ERR_RANGE)
    assert not m.values


def test_signal_loss_restarts_current_stage():
    m = Measurement(started=True)
    run(m, 3.0)
    run(m, 1.0, n_samples=5)
    assert m.values
    run(m, 0.8, n_samples=0)  # 0.6초 넘게 샘플 없음
    assert (m.phase, m.stage, m.error) == (COUNTDOWN, MIN, ERR_LOST)
    assert not m.values


def test_short_gaps_do_not_count_as_loss():
    m = Measurement(started=True)
    run(m, 3.0)
    run(m, 0.4, n_samples=0)  # 창 2개 비어 있음
    run(m, 0.4, n_samples=5)
    assert m.phase == MEASURING and m.error == ""
