import random

import pygame

import config
from config import ARENA_W
from game import Battle, LOST, PLAYING, WON


def make():
    return Battle(rng=random.Random(0))


def test_player_stays_inside_arena():
    b = make()
    for _ in range(300):
        b.update(0.05, -1)
    assert b.player.x == config.PLAYER_W / 2
    for _ in range(300):
        b.update(0.05, 1)
    assert b.player.x == ARENA_W - config.PLAYER_W / 2


def test_player_stays_when_direction_zero():
    b = make()
    x = b.player.x
    b.update(0.5, 0)
    assert b.player.x == x


def test_player_shoots_automatically():
    b = make()
    b.update(0.01, 0)
    assert len(b.bullets) == 1


def test_bullet_hit_damages_boss_and_is_removed():
    b = make()
    b.bullets = [pygame.Rect(int(b.boss.x), b.boss.rect.centery, 8, 20)]
    b.fires = []
    hp = b.boss.hp
    b._collide()
    assert b.boss.hp == hp - 1
    assert b.bullets == []


def test_boss_dies_means_win():
    b = make()
    b.boss.hp = 1
    b.bullets = [pygame.Rect(int(b.boss.x), b.boss.rect.centery, 8, 20)]
    b._collide()
    assert b.state == WON


def _fire_on_player(b):
    p = b.player.rect
    b.fires = [pygame.Rect(p.x, p.y, config.FIRE_W, config.FIRE_H)]


def test_fire_hit_costs_life_and_grants_invulnerability():
    b = make()
    _fire_on_player(b)
    b._collide()
    assert b.player.lives == config.MAX_LIVES - 1
    assert b.player.invuln == config.INVULN_SECONDS
    assert b.fires == []

    _fire_on_player(b)
    b._collide()
    assert b.player.lives == config.MAX_LIVES - 1  # 무적 중에는 닳지 않는다


def test_invulnerability_expires_after_two_seconds():
    b = make()
    _fire_on_player(b)
    b._collide()
    b.update(2.01, 0)
    assert b.player.invuln == 0.0


def test_losing_all_lives_means_loss_and_freezes_game():
    b = make()
    b.player.lives = 1
    _fire_on_player(b)
    b._collide()
    assert b.state == LOST
    x = b.player.x
    b.update(1.0, 1)
    assert b.player.x == x


def test_fire_falls_and_leaves_arena():
    b = make()
    b.fires = [pygame.Rect(0, config.ARENA_H - 5, config.FIRE_W, config.FIRE_H)]
    b._move_projectiles(0.1)
    assert b.fires == []


def test_fires_spawn_over_time_and_game_keeps_playing():
    b = make()
    for _ in range(120):
        b.update(1 / 60, 0)
    assert b.state in (PLAYING, LOST)
    assert b.time > 1.9


def test_crossing_a_phase_shows_banner_and_speeds_fire():
    b = make()
    b.boss.hp = config.BOSS_MAX_HP * 2 // 3 + 1  # 페이즈 1 마지막 체력
    b.bullets = [pygame.Rect(b.boss.rect.centerx, b.boss.rect.centery, 4, 4)]
    b.update(0.01, 0)
    assert b.boss.phase == 1 and b.banner > 0
    b.fires = [pygame.Rect(0, 0, config.FIRE_W, config.FIRE_H)]
    b.update(0.5, 0)
    assert b.fires[0].y == round(config.BOSS_PHASES[1]["speed"] * 0.5)


def test_fast_bolt_hits_player_even_with_a_big_frame_step():
    b = make()
    p = b.player
    b.bolts = [pygame.Rect(int(p.x), p.rect.top - 200, config.BOLT_W, config.BOLT_H)]
    b.update(0.1, 0)  # 1100px/s * 0.1s = 110px
    for _ in range(5):
        b.update(0.1, 0)
    assert p.lives == config.MAX_LIVES - 1


def test_bolt_misses_player_in_another_column():
    b = make()
    b.bolts = [pygame.Rect(10, 100, config.BOLT_W, config.BOLT_H)]
    for _ in range(30):
        b.update(0.05, 0)
    assert b.player.lives == config.MAX_LIVES and not b.bolts


def test_fires_speed_up_as_they_fall_so_gaps_open():
    b = make()
    b.boss._fire_cd = 99  # 새 불이 나오지 않게
    b.boss._bolt_cd = 99
    older = pygame.Rect(100, 300, config.FIRE_W, config.FIRE_H)
    newer = pygame.Rect(100, 232, config.FIRE_W, config.FIRE_H)  # 68px 뒤
    b.fires = [older, newer]
    gap = older.y - newer.y
    for _ in range(10):
        b.update(0.05, 0)
    assert older.y - newer.y > gap



def _third_phase_battle():
    b = make()
    b.boss._fire_cd = 99
    b.boss._bolt_cd = 99
    return b


def test_meteors_only_fall_in_phase_three():
    for hp, expect in ((config.BOSS_MAX_HP, False), (config.BOSS_MAX_HP * 2 // 3, False), (config.BOSS_MAX_HP // 3, True)):
        b = _third_phase_battle()
        seen = False
        for _ in range(400):
            b.boss.hp = hp
            b.player.invuln = 99
            b.bullets.clear()
            b.update(0.05, 0)
            seen = seen or bool(b.meteors)
        assert seen is expect


def test_meteor_is_big_accelerates_and_hurts():
    from boss import Meteor

    b = _third_phase_battle()
    m = Meteor(b.player.x, 0.0)
    assert m.rect.width == config.METEOR_SIZE > 2 * config.FIRE_W
    b.meteors = [m]
    v0 = m.vy
    b.update(0.5, 0)
    assert m.vy > v0 and m.y > 0
    for _ in range(100):
        b.update(0.05, 0)
        if b.player.lives < config.MAX_LIVES:
            break
    assert b.player.lives == config.MAX_LIVES - 1 and not b.meteors


def test_meteor_leaves_the_arena_when_missed():
    from boss import Meteor

    b = _third_phase_battle()
    b.player.x = 30
    b.meteors = [Meteor(config.ARENA_W - 100, 0.0)]
    for _ in range(200):
        b.update(0.05, 0)
        b.player.x = 30
    assert not b.meteors and b.player.lives == config.MAX_LIVES


def test_easy_difficulty_is_gentler_than_hard():
    easy, hard = config.DIFFICULTIES["easy"], config.DIFFICULTIES["hard"]
    assert hard["phases"] is config.BOSS_PHASES and len(easy["phases"]) == len(hard["phases"])
    for e, h in zip(easy["phases"], hard["phases"]):
        assert e["interval"] >= h["interval"] and e["speed"] <= h["speed"] and e["count"] <= h["count"]
    assert not any(p["meteor_interval"] for p in easy["phases"]) and easy["gravity"] <= hard["gravity"]
    assert Battle(difficulty="easy").gravity == easy["gravity"] and make().boss.phases is config.BOSS_PHASES
