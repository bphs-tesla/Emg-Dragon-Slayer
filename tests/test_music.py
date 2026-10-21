import os
import struct
import wave

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

import config
import music
from main import App
from source import FakeSource


def _wav(path, n=2205):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(22050)
        w.writeframes(b"".join(struct.pack("<h", 2000 if i % 50 < 25 else -2000) for i in range(n)))


def test_plays_by_name_keeps_same_track_and_skips_missing(tmp_path):
    _wav(tmp_path / "title.wav")
    _wav(tmp_path / "battle.wav")
    m = music.Music(str(tmp_path), volume=0.5)
    if not m.available:
        return  # 소리 장치가 없는 환경
    m.play("title")
    assert m.current == "title" and pygame.mixer.music.get_busy()
    m.play("title")  # 같은 곡이면 다시 시작하지 않는다
    assert m.current == "title"
    m.play("battle")
    assert m.current == "battle"
    m.play("missing")  # 없는 곡은 조용히
    assert m.current == "missing"
    m.play(None)
    assert m.current is None


def test_broken_file_does_not_crash(tmp_path):
    (tmp_path / "title.wav").write_bytes(b"not audio")
    m = music.Music(str(tmp_path))
    m.play("title")
    m.play("title")


def test_mute_sets_volume_to_zero(tmp_path):
    m = music.Music(str(tmp_path), volume=0.5)
    if not m.available:
        return
    m.set_muted(True)
    assert pygame.mixer.music.get_volume() == 0.0
    m.set_muted(False)
    assert abs(pygame.mixer.music.get_volume() - 0.5) < 0.02


def test_screens_pick_tracks():
    for screen in ("title", "howto", "name", "select", "calib"):
        assert music.SCREEN_TRACKS[screen] == "title"
    assert music.SCREEN_TRACKS["play"] == "battle"
    assert music.SCREEN_TRACKS["result"] is None


def test_app_switches_music_with_screens(monkeypatch):
    config.FULLSCREEN = False
    monkeypatch.setattr("main.leaderboard.save", lambda entries, path=None, **kw: None)
    app = App(FakeSource())
    if not app.music.available:
        return
    assert app.music.current == "title"
    app.go("play")
    assert app.music.current == "battle"
    app.battle.state = "lost"
    app.finish_battle()
    assert app.music.current is None
    app.handle_key(pygame.K_m)  # M 키는 음악도 함께 끈다
    assert app.music.muted and app.sfx.muted
