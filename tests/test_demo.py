from demo import Demo
from game import PLAYING


def test_demo_runs_forever_and_stays_in_arena():
    d = Demo()
    for _ in range(60 * 90):
        d.update(1 / 60)
        assert d.battle.state == PLAYING
        assert 0.0 <= d.force <= 1.0


def test_demo_dodges_most_fire():
    d = Demo()
    hits = 0
    lives = d.battle.player.lives
    for _ in range(60 * 60):
        d.update(1 / 60)
        now = d.battle.player.lives
        if now < lives:
            hits += lives - now
        lives = now
    assert hits <= 8  # 1분 동안 가끔 맞는 정도 (사람보다 잘 피하는 봇)
