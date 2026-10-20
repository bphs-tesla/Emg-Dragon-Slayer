"""파일 위치. 소스로 실행할 때와 exe(PyInstaller)로 묶었을 때 모두 맞게 찾는다.

resource_dir: 게임에 들어 있는 읽기 전용 파일(assets)이 있는 곳
data_dir    : 기록(leaderboard.json)과 센서 설정(settings.json)을 저장하는 곳. exe 파일 옆이고,
              쓸 수 없는 곳(예: Program Files)이면 사용자 폴더로 넘어간다.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FROZEN = getattr(sys, "frozen", False)


def resource_dir() -> str:
    return getattr(sys, "_MEIPASS", HERE)


def data_dir() -> str:
    base = os.path.dirname(os.path.abspath(sys.executable)) if FROZEN else HERE
    if os.access(base, os.W_OK):
        return base
    fallback = os.path.join(os.path.expanduser("~"), ".emg-dragon-slayer")
    os.makedirs(fallback, exist_ok=True)
    return fallback
