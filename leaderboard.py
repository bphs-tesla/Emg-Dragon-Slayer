"""기록. 이긴 사람이 먼저(클리어 시간이 짧은 순, 같으면 남은 목숨이 많은 순),
진 사람은 그 뒤에 오래 버틴 순으로 상위 20명만 남긴다."""

import json
import os

import paths
from config import LEADERBOARD_SIZE

PATH = os.path.join(paths.data_dir(), "leaderboard.json")


def _key(entry: dict) -> tuple:
    if entry["won"]:
        return (0, entry["time"], -entry["lives"])
    return (1, -entry["time"], 0)


def load(path: str = PATH) -> list[dict]:
    """파일이 없거나 깨졌으면 빈 기록으로 시작한다. won이 없는 예전 기록은 승리로 본다."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        entries = [
            {
                "name": str(e["name"]),
                "time": float(e["time"]),
                "lives": int(e["lives"]),
                "won": bool(e.get("won", True)),
            }
            for e in data
        ]
    except (OSError, ValueError, KeyError, TypeError):
        return []
    return sorted(entries, key=_key)[:LEADERBOARD_SIZE]


def save(entries: list[dict], path: str = PATH) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
    except OSError:
        pass  # 저장이 안 돼도 게임은 계속된다


def add(entries: list[dict], name: str, time: float, lives: int, won: bool = True) -> tuple[list[dict], int | None]:
    """새 기록을 넣은 목록과 그 순위(0부터)를 돌려준다. 20위 밖이면 순위는 None이다.

    이긴 기록은 time이 클리어 시간, 진 기록은 버틴 시간이다. 시간은 0.1초 단위로 맞춰 비교하고,
    같은 조건이면 먼저 끝낸 사람이 위다.
    """
    entry = {"name": name, "time": round(time, 1), "lives": lives, "won": won}
    ranked = sorted(entries + [entry], key=_key)[:LEADERBOARD_SIZE]  # 정렬이 안정적이라 새 기록이 동점 뒤로 간다
    rank = next((i for i, e in enumerate(ranked) if e is entry), None)
    return ranked, rank
