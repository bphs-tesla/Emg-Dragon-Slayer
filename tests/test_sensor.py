import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from types import SimpleNamespace

import pygame

import config
import sensor
from main import App
from sensor import Port, auto_pick
from source import FakeSource, SerialSource


def fake_port(device, description="", vid=None, manufacturer=""):
    return SimpleNamespace(device=device, description=description, vid=vid, manufacturer=manufacturer)


def patch_comports(monkeypatch, ports):
    import serial.tools.list_ports as lp

    monkeypatch.setattr(lp, "comports", lambda: ports)


def test_scan_prefers_usb_ports_and_marks_likely(monkeypatch):
    patch_comports(monkeypatch, [
        fake_port("COM1", "통신 포트"),
        fake_port("COM7", "USB Serial Device", vid=0x1A86),
        fake_port("COM4", "기타 USB 장치", vid=0x9999),
        fake_port("/dev/cu.Bluetooth-Incoming-Port", "n/a"),
    ])
    ports = sensor.scan()
    assert [p.device for p in ports] == ["COM7", "COM4"]  # 추천이 먼저, COM1(USB 아님)과 블루투스는 빠진다
    assert ports[0].likely and not ports[1].likely


def test_scan_falls_back_to_non_usb_ports_when_none_are_usb(monkeypatch):
    patch_comports(monkeypatch, [fake_port("COM3", "통신 포트"), fake_port("/dev/cu.debug-console", "n/a")])
    assert [p.device for p in sensor.scan()] == ["COM3"]


def test_auto_pick_rules():
    sure = Port("COM7", "Arduino", True)
    other = Port("COM4", "기타", False)
    assert auto_pick([sure, other], None) == "COM7"          # 추천이 하나면 바로
    assert auto_pick([sure, Port("COM8", "Arduino", True)], None) is None  # 추천이 둘이면 물어본다
    assert auto_pick([sure, other], "COM4") == "COM4"        # 지난번에 쓴 포트가 있으면 그것
    assert auto_pick([sure], "COM9") == "COM7"               # 지난번 포트가 없어졌으면 다시 판단
    assert auto_pick([other], None) == "COM4"                # 후보가 하나뿐이면 바로
    assert auto_pick([other, Port("COM5", "기타2", False)], None) is None
    assert auto_pick([], None) is None


def test_settings_roundtrip_and_bad_file(tmp_path):
    path = str(tmp_path / "s.json")
    assert sensor.load_settings(path) == {}
    sensor.save_settings({"port": "COM3"}, path)
    assert sensor.load_settings(path) == {"port": "COM3"}
    (tmp_path / "bad.json").write_text("zzz")
    assert sensor.load_settings(str(tmp_path / "bad.json")) == {}


def new_app(monkeypatch, tmp_path, ports, saved=None):
    config.FULLSCREEN = False
    path = str(tmp_path / "settings.json")
    monkeypatch.setattr(sensor, "SETTINGS_PATH", path)
    monkeypatch.setattr(sensor, "load_settings", lambda p=path: saved or {})
    store = {}
    monkeypatch.setattr(sensor, "save_settings", lambda s, p=path: store.update(s))
    monkeypatch.setattr(sensor, "scan", lambda: ports)
    return App(FakeSource(), ask_sensor=True), store


def test_one_clear_sensor_connects_automatically_and_is_remembered(monkeypatch, tmp_path):
    app, store = new_app(monkeypatch, tmp_path, [Port("COM7", "Arduino", True)])
    assert app.state == "title" and isinstance(app.source, SerialSource) and app.source.port == "COM7"
    assert store["port"] == "COM7" and not app.fake


def test_saved_port_is_used_without_asking(monkeypatch, tmp_path):
    ports = [Port("COM7", "Arduino", True), Port("COM8", "Arduino", True)]
    app, _ = new_app(monkeypatch, tmp_path, ports, saved={"port": "COM8"})
    assert app.state == "title" and app.source.port == "COM8"


def test_no_sensor_or_several_sensors_show_the_chooser(monkeypatch, tmp_path):
    app, _ = new_app(monkeypatch, tmp_path, [])
    assert app.state == "sensor" and app.fake
    app.draw()
    ports = [Port("COM7", "Arduino", True), Port("COM8", "Arduino", True)]
    app, _ = new_app(monkeypatch, tmp_path, ports)
    assert app.state == "sensor"
    app.draw()


def test_chooser_selects_a_port_or_keyboard_mode(monkeypatch, tmp_path):
    ports = [Port("COM7", "Arduino", True), Port("COM8", "Arduino", True)]
    app, store = new_app(monkeypatch, tmp_path, ports)
    app.handle_key(pygame.K_DOWN)
    app.handle_key(pygame.K_RETURN)
    assert app.state == "title" and app.source.port == "COM8" and store["port"] == "COM8"
    app.handle_key(pygame.K_s)  # 타이틀에서 S로 다시 고른다
    assert app.state == "sensor"
    app.handle_key(pygame.K_DOWN)  # 지금 쓰는 COM8에서 한 칸 아래 = 마지막 줄 = 키보드 모드
    app.handle_key(pygame.K_RETURN)
    assert app.state == "title" and app.fake and app.sensor_label == "키보드 모드"
    app.draw()


def test_chooser_keeps_selection_when_the_list_changes(monkeypatch, tmp_path):
    ports = [Port("COM7", "Arduino", True), Port("COM8", "Arduino", True)]
    app, _ = new_app(monkeypatch, tmp_path, ports)
    app.handle_key(pygame.K_DOWN)
    monkeypatch.setattr(sensor, "scan", lambda: [Port("COM6", "새 센서", False)] + ports)
    app.source.start()
    app.update(1.1, pygame.key.get_pressed())
    assert app.sensor_ports[app.sensor_sel].device == "COM8"


def test_switching_source_after_start_stops_the_old_one(monkeypatch, tmp_path):
    app, _ = new_app(monkeypatch, tmp_path, [])
    calls = []
    old = app.source
    old.stop = lambda: calls.append("stop")
    app._started = True
    app.use_keyboard()
    assert calls == ["stop"] and app.source is not old


def test_selftest_draws_every_screen():
    config.FULLSCREEN = False
    App(FakeSource()).selftest()
