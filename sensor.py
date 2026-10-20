"""센서(SpikerBox) 연결 고르기. 컴퓨터에 꽂힌 USB 시리얼 포트를 찾아 목록으로 보여주고, 마지막으로 쓴 포트는 기억한다.

실행할 때마다 포트 이름(COM3 등)이 달라질 수 있어서 명령줄 없이도 고를 수 있어야 한다.
"""

import json
import os
from dataclasses import dataclass

import paths

SETTINGS_PATH = os.path.join(paths.data_dir(), "settings.json")

# SpikerBox가 보통 쓰는 USB 칩 제조사 번호(아두이노, CH340, FTDI, CP210x)와 설명에 들어가는 말
KNOWN_VIDS = {0x2341, 0x2A03, 0x1A86, 0x0403, 0x10C4}
KNOWN_WORDS = ("arduino", "spiker", "backyard", "ch340", "usb serial", "usb-serial", "usb2.0-serial")
SKIP_WORDS = ("bluetooth", "debug-console", "incoming-port", "modem")  # 센서일 수 없는 포트


@dataclass
class Port:
    device: str
    description: str
    likely: bool  # SpikerBox일 가능성이 높다

    @property
    def label(self) -> str:
        return f"{self.device}  ·  {self.description}" if self.description and self.description != "n/a" else self.device


def scan() -> list[Port]:
    """연결된 시리얼 포트 목록. USB로 꽂힌 것이 있으면 그것만, 없으면 블루투스 같은 걸 뺀 나머지를 보여준다."""
    try:
        from serial.tools import list_ports as lp

        found = lp.comports()
    except Exception:  # pyserial이 없거나 장치를 못 읽어도 게임은 켜져야 한다
        return []
    ports = []
    for p in found:
        text = f"{p.device} {p.description or ''} {p.manufacturer or ''}".lower()
        if any(w in text for w in SKIP_WORDS):
            continue
        likely = (p.vid in KNOWN_VIDS) or any(w in text for w in KNOWN_WORDS)
        ports.append((Port(p.device, p.description or "", likely), p.vid is not None))
    usb = [port for port, has_vid in ports if has_vid]
    chosen = usb or [port for port, _ in ports]
    return sorted(chosen, key=lambda p: (not p.likely, p.device))


def load_settings(path: str = SETTINGS_PATH) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(settings: dict, path: str = SETTINGS_PATH) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def auto_pick(ports: list[Port], saved: str | None) -> str | None:
    """물어보지 않고 바로 연결해도 되는 포트. 애매하면(후보가 여러 개거나 없으면) None으로 사용자에게 묻는다."""
    if saved and any(p.device == saved for p in ports):
        return saved
    likely = [p for p in ports if p.likely]
    if len(likely) == 1:
        return likely[0].device
    if not likely and len(ports) == 1:
        return ports[0].device
    return None
