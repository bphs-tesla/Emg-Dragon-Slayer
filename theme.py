"""화면 테마. config.THEME으로 고른다. 새 테마는 THEMES에 항목만 추가하면 된다."""

import config

THEMES = {
    "default": {
        "caption": "드래곤 피하기 (EMG)",
        "screen_bg": (28, 26, 36),
        # 페이즈별 경기장 배경 (위, 아래)
        "arena_bg": [((22, 18, 30), (22, 18, 30))] * 3,
        "bubbles": False,
        "phase_names": ["", "", ""],
        "line": (60, 55, 80),
    },
    "deep_sea": {
        "caption": "용궁 심해 (EMG)",
        "screen_bg": (6, 14, 30),
        "arena_bg": [
            ((40, 130, 170), (12, 55, 100)),  # 1: 얕은 바다
            ((14, 70, 125), (6, 28, 70)),     # 2: 중간 바다
            ((6, 24, 60), (2, 6, 24)),        # 3: 심해
        ],
        "bubbles": True,
        "phase_names": ["얕은 바다", "중간 바다", "심해"],
        "line": (70, 130, 170),
    },
}


def current() -> dict:
    return THEMES.get(config.THEME, THEMES["default"])
