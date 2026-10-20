import os
import struct
import wave

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

import config
import sfx
from game import Battle


def _tone(path, n=800):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(22050)
        w.writeframes(b"".join(struct.pack("<h", 3000 if i % 40 < 20 else -3000) for i in range(n)))


def test_loads_files_by_event_name_and_variants(tmp_path):
    _tone(tmp_path / "shoot.wav")
    _tone(tmp_path / "shoot_2.wav")
    _tone(tmp_path / "win.wav")
    (tmp_path / "lose.wav").write_bytes(b"not audio")  # 깨진 파일
    (tmp_path / "unknown.wav").write_bytes(b"x")  # 이벤트 이름이 아니면 무시
    s = sfx.Sfx(str(tmp_path), volumes={"shoot": 0.5}, master=1.0)
    if not s.available:
        return  # 소리 장치가 없는 환경
    assert len(s.sounds["shoot"]) == 2 and "win" in s.sounds
    assert "lose" not in s.sounds and "unknown" not in s.sounds
    assert abs(s.sounds["shoot"][0].get_volume() - 0.5) < 0.02
    s.play("shoot")
    s.play("nothing")  # 없는 이벤트도 괜찮다


def test_missing_folder_and_mute_are_silent(tmp_path):
    s = sfx.Sfx(str(tmp_path / "nope"))
    s.play("shoot")
    assert s.toggle_mute() is True and s.toggle_mute() is False


def test_battle_reports_events():
    b = Battle()
    b.update(0.01, 0)
    assert "shoot" in b.events
    b.events.clear()
    b.boss.hp = config.BOSS_MAX_HP * 2 // 3 + 1
    b.bullets = [pygame.Rect(b.boss.rect.centerx, b.boss.rect.centery, 4, 4)]
    b.update(0.01, 0)
    assert "boss_hit" in b.events and "phase" in b.events
    b.events.clear()
    b.boss.hp = 1
    b.bullets = [pygame.Rect(b.boss.rect.centerx, b.boss.rect.centery, 4, 4)]
    b.update(0.01, 0)
    assert "win" in b.events


def test_player_hit_and_lose_events():
    b = Battle()
    b.boss._fire_cd = 99
    b.boss._bolt_cd = 99
    for _ in range(config.MAX_LIVES):
        b.player.invuln = 0
        b.fires = [pygame.Rect(b.player.rect.x, b.player.rect.y, config.FIRE_W, config.FIRE_H)]
        b.update(0.01, 0)
    assert b.events.count("player_hit") == config.MAX_LIVES
    assert "lose" in b.events


def test_bolt_events_come_from_the_boss():
    b = Battle()
    b.boss.hp = config.BOSS_MAX_HP // 2
    seen = set()
    for _ in range(400):
        b.player.invuln = 99
        b.boss.hp = config.BOSS_MAX_HP // 2
        b.bullets.clear()
        b.update(0.05, 0)
        seen |= set(b.events)
        b.events.clear()
    assert {"bolt_warn", "bolt"} <= seen


def test_boss_dropping_fire_reports_fire_event():
    b = Battle()
    b.boss._fire_cd = 0
    b.update(0.01, 0)
    assert "fire" in b.events


def test_event_does_not_pick_up_files_of_a_longer_name(tmp_path):
    _tone(tmp_path / "bolt_warn.wav")
    _tone(tmp_path / "bolt_2.wav")
    s = sfx.Sfx(str(tmp_path))
    if not s.available:
        return
    assert len(s.sounds["bolt"]) == 1  # bolt_2만. bolt_warn은 bolt의 소리가 아니다
    assert len(s.sounds["bolt_warn"]) == 1
