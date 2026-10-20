import random

import config
from boss import Boss
from player import Player


def test_player_moves_clamps_and_fires():
    p = Player()
    x = p.x
    shots = p.update(0.1, 1)
    assert p.x == x + config.PLAYER_SPEED * 0.1
    assert len(shots) == 1
    assert p.update(0.01, 0) == []  # 발사 간격 전에는 쏘지 않는다
    for _ in range(100):
        p.update(0.1, -1)
    assert p.x == config.PLAYER_W / 2


def test_player_hit_starts_invulnerability_and_death():
    p = Player()
    assert p.vulnerable and p.alive
    p.hit()
    assert p.lives == config.MAX_LIVES - 1
    assert not p.vulnerable
    p.update(config.INVULN_SECONDS + 0.01, 0)
    assert p.vulnerable
    p.lives = 1
    p.hit()
    assert not p.alive


def test_boss_stays_fixed_at_top_center():
    b = Boss(random.Random(0))
    rect = b.rect
    for _ in range(1000):
        b.update(0.05)
    assert b.x == config.ARENA_W / 2
    assert b.rect == rect


def test_boss_drops_fire_under_wings():
    b = Boss(random.Random(0))
    fires = []
    for _ in range(200):
        fires += b.update(0.05)
    assert fires
    assert all(0 <= f.centerx <= config.ARENA_W for f in fires)


def test_boss_phase_follows_hp_in_thirds():
    b = Boss()
    m = config.BOSS_MAX_HP
    assert b.phase == 0
    b.hp = m * 2 // 3 + 1
    assert b.phase == 0
    b.hp = m * 2 // 3
    assert b.phase == 1
    b.hp = m // 3
    assert b.phase == 2
    b.hp = 1
    assert b.phase == 2


def test_later_phases_drop_more_fire_per_drop():
    counts = []
    for hp in (config.BOSS_MAX_HP, config.BOSS_MAX_HP * 2 // 3, config.BOSS_MAX_HP // 3):
        b = Boss(random.Random(0))
        b.hp = hp
        counts.append(len(b.update(1.5)))
    assert counts == [p["count"] for p in config.BOSS_PHASES]


def test_boss_hit_never_goes_below_zero():
    b = Boss()
    b.hit(config.BOSS_MAX_HP + 10)
    assert b.hp == 0 and not b.alive
    assert b.phase == len(config.BOSS_PHASES) - 1


def _bolt_boss(hp):
    b = Boss(random.Random(1))
    b.hp = hp
    return b


def test_no_bolts_in_phase_one():
    b = _bolt_boss(config.BOSS_MAX_HP)
    for _ in range(400):
        b.update(0.05, 280)
    assert not b.warnings and not b.pop_bolts()


def test_bolt_warns_first_then_fires_at_the_warned_column():
    b = _bolt_boss(config.BOSS_MAX_HP // 2)  # 2페이즈
    warned = None
    for _ in range(400):
        b.update(0.05, 280)
        if b.warnings and warned is None:
            warned = b.warnings[0][0]
            assert abs(warned - 280) <= config.BOLT_AIM_SPREAD + 1
            assert not b.pop_bolts()  # 경고 중에는 총알이 없다
        bolts = b.pop_bolts()
        if bolts:
            assert warned is not None
            assert bolts[0].centerx == int(warned - config.BOLT_W / 2) + config.BOLT_W // 2 or abs(bolts[0].centerx - warned) <= 1
            return
    raise AssertionError("총알이 나오지 않았다")
