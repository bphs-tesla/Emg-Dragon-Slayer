import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

import config
import game

config.FULLSCREEN = False  # 화면 없는 테스트 환경
from main import App
from source import FakeSource


def test_screens_follow_the_order_and_every_screen_draws(monkeypatch):
    monkeypatch.setattr("main.leaderboard.save", lambda entries, path=None, **kw: None)
    app = App(FakeSource())
    app.source.start()  # start 전에 읽으면 부팅 이후 시간만큼 샘플을 만든다
    app.entries = []
    order = ["title", "howto", "name", "select", "calib"]
    assert app.state == order[0]
    app.draw()
    app.handle_key(pygame.K_RETURN)
    assert app.state == "howto"
    for _ in range(120):
        app.update(1 / 60, pygame.key.get_pressed())
    app.draw()
    app.handle_key(pygame.K_RETURN)
    assert app.state == "name"
    app.handle_key(pygame.K_RETURN)  # 이름이 비어 있으면 못 넘어간다
    assert app.state == "name"
    app.on_text("조재민")
    app.draw()
    app.handle_key(pygame.K_RETURN)
    assert app.state == "difficulty" and app.name == "조재민"
    app.draw()
    app.handle_key(pygame.K_RETURN)
    assert app.state == "select"
    app.draw()
    app.handle_key(pygame.K_RETURN)
    assert app.state == "calib"
    app.draw()


def test_name_input_limits_and_backspace():
    app = App(FakeSource())
    app.go("name")
    app.on_text("가" * (config.NAME_MAX + 5))
    assert len(app.name) == config.NAME_MAX
    app.handle_key(pygame.K_BACKSPACE)
    assert len(app.name) == config.NAME_MAX - 1
    app.composing = "ㅎ"  # 조합 중에는 Backspace를 입력기에 맡긴다
    app.handle_key(pygame.K_BACKSPACE)
    assert len(app.name) == config.NAME_MAX - 1


def test_text_input_ignored_outside_name_screen():
    app = App(FakeSource())
    app.on_text("abc")
    assert app.name == ""


def test_win_records_and_result_returns_to_title(monkeypatch):
    saved = []
    monkeypatch.setattr("main.leaderboard.save", lambda entries, path=None, **kw: saved.append(list(entries)))
    app = App(FakeSource())
    app.entries = []
    app.name = "승자"
    app.go("play")
    app.battle.boss.hp = 0
    app.battle.state = "won"
    app.battle.time = 42.04
    app.finish_battle()
    assert app.state == "result" and app.rank == 0
    assert app.entries[0]["name"] == "승자" and app.entries[0]["time"] == 42.0
    app.draw()
    app.handle_key(pygame.K_RETURN)
    assert app.state == "title" and app.name == "" and app.rank is None


def test_loss_is_recorded_with_survival_time(monkeypatch):
    monkeypatch.setattr("main.leaderboard.save", lambda entries, path=None, **kw: None)
    app = App(FakeSource())
    app.entries = []
    app.name = "패자"
    app.go("play")
    app.battle.state = "lost"
    app.battle.time = 37.04
    app.finish_battle()
    assert app.state == "result" and app.rank == 0
    assert app.entries[0]["won"] is False and app.entries[0]["time"] == 37.0
    app.draw()


def test_debug_mode_skips_to_play_and_does_not_record(monkeypatch):
    saved = []
    monkeypatch.setattr("main.leaderboard.save", lambda entries, path=None, **kw: saved.append(entries))
    app = App(FakeSource(), debug=True, hero=2)
    assert app.state == "play" and app.hero == 2 and app.est.calibrated
    app.handle_key(pygame.K_3)
    assert app.battle.boss.phase == 2
    app.handle_key(pygame.K_2)
    assert app.battle.boss.phase == 1
    app.handle_key(pygame.K_1)
    assert app.battle.boss.phase == 0
    app.draw()
    app.battle.state = "won"
    app.finish_battle()
    assert app.state == "result" and not saved and app.rank is None
    app.draw()
    app.handle_key(pygame.K_RETURN)
    assert app.state == "play" and app.battle.state == "playing"


def test_debug_hero_is_clamped():
    assert App(FakeSource(), debug=True, hero=99).hero == App(FakeSource(), debug=True).assets.hero_count - 1


def test_debug_mode_idle_keys_stay_in_the_stay_zone():
    import time

    import emg

    app = App(FakeSource(), debug=True)
    app.source.start()
    for _ in range(90):  # 아무 키도 안 누르고 1.5초 (가짜 센서는 실제 시간으로 샘플을 만든다)
        time.sleep(1 / 60)
        app.update(1 / 60, pygame.key.get_pressed())
    assert emg.direction(app.est.force) == 0


def test_hero_defeat_message_by_index(monkeypatch):
    import main

    monkeypatch.setattr(main, "HERO_DEFEAT_MESSAGES", ["아쉽다...", "", "  "])
    assert main.hero_defeat_message(0) == "아쉽다..."
    assert main.hero_defeat_message(1) == ""  # 비워 두면 없음
    assert main.hero_defeat_message(2) == ""  # 공백만 있어도 없음
    assert main.hero_defeat_message(9) == ""  # 목록보다 뒤 캐릭터도 없음


def test_defeat_message_is_drawn_on_loss_only(monkeypatch):
    import main

    monkeypatch.setattr(main, "HERO_DEFEAT_MESSAGES", ["다음엔 이긴다!"])
    monkeypatch.setattr("main.leaderboard.save", lambda entries, path=None, **kw: None)
    app = App(FakeSource())
    app.entries = []
    app.hero = 0
    app.go("play")
    app.battle.state = "lost"
    app.finish_battle()
    app.draw()  # 글자가 그려져도 죽지 않는다
    app.battle.state = "won"
    app.draw()


def test_title_screen_draws_with_and_without_background(monkeypatch):
    app = App(FakeSource())
    assert app.assets.title_bg is not None and app.title_heroes
    app.draw()
    app.assets.title_bg = None
    app.assets.title_boss = None
    app.title_heroes = []
    app.draw()


def test_difficulty_choice_changes_battle_and_keeps_boards_separate(monkeypatch):
    saved = {}
    monkeypatch.setattr("main.leaderboard.save", lambda entries, path=None, difficulty="hard": saved.update({difficulty: list(entries)}))
    app = App(FakeSource())
    app._boards = {"easy": [], "hard": []}
    app.entries = app._boards["hard"]
    app.go("difficulty")
    app.draw()
    app.handle_key(pygame.K_UP)
    assert app.difficulty == "easy" and app.entries is app._boards["easy"]
    app.handle_key(pygame.K_RETURN)
    assert app.state == "select"
    app.start_calibration()
    app.est.calibrate(0.0, 1.0)
    app.battle = game.Battle(difficulty=app.difficulty)
    assert app.battle.boss.phases is config.DIFFICULTIES["easy"]["phases"]
    app.name = "쉬운이"
    app.battle.state = game.WON
    app.battle.time = 50.0
    app.finish_battle()
    assert saved["easy"][0]["name"] == "쉬운이" and "hard" not in saved
    app.set_difficulty("hard")
    assert app.entries == []
    app.draw_leaderboard()
