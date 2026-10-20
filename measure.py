"""힘 측정 진행 상태. 최소 -> 최대 순서로 카운트다운 후 측정하며, 화면 없이 규칙만 계산한다.

설명 문서: docs/measure-screen.md
"""

import emg
from config import (
    CALIB_SECONDS,
    COUNTDOWN_SECONDS,
    MAX_TOP_N,
    SIGNAL_LOSS_SECONDS,
    WINDOW_SECONDS,
)

INTRO, COUNTDOWN, MEASURING, DONE = "intro", "countdown", "measuring", "done"
MIN, MAX = "min", "max"

HUD_TITLES = {MIN: "힘 측정 1/2 · 힘 빼기", MAX: "힘 측정 2/2 · 최대 힘"}
PANEL_TITLES = {MIN: "힘을 빼세요", MAX: "최대한 힘을 주세요!"}
ERR_LOST = "신호 끊김, 다시 측정합니다"
ERR_RANGE = "측정 실패, 다시 측정합니다"


class Measurement:
    def __init__(self, started: bool = False):
        self.needed = round(CALIB_SECONDS / WINDOW_SECONDS)
        self.loss_windows = round(SIGNAL_LOSS_SECONDS / WINDOW_SECONDS)
        self.error = ""
        self.last_value: float | None = None  # 가장 최근에 받은 센서 값 (화면 표시용)
        self.lo = 0.0
        self.hi = 0.0
        self._lo_values: list[float] = []
        self._begin(MIN)
        if not started:
            self.phase = INTRO

    @property
    def done(self) -> bool:
        return self.phase == DONE

    @property
    def countdown_left(self) -> float:
        return max(0.0, COUNTDOWN_SECONDS - self._t)

    @property
    def progress(self) -> float:
        return min(1.0, len(self.values) / self.needed)

    def start(self) -> None:
        if self.phase == INTRO:
            self.phase = COUNTDOWN

    def _begin(self, stage: str) -> None:
        """stage의 카운트다운부터 다시 시작한다. 모은 값은 모두 버린다."""
        self.stage = stage
        self.phase = COUNTDOWN
        self.values: list[float] = []
        self._t = 0.0
        self._win_t = 0.0
        self._win_samples = 0
        self._empty_run = 0

    def update(self, dt: float, n_samples: int, envelope: float) -> None:
        """n_samples는 이번 프레임에 센서에서 새로 받은 샘플 수, envelope는 그때의 힘 진폭."""
        if self.phase in (INTRO, DONE):
            return
        if self.phase == COUNTDOWN:
            self._t += dt
            if self._t >= COUNTDOWN_SECONDS:  # 카운트다운 동안 들어온 값은 버린다
                self.phase = MEASURING
                self._win_t = 0.0
                self._win_samples = 0
            return
        self._win_t += dt
        self._win_samples += n_samples
        while self.phase == MEASURING and self._win_t >= WINDOW_SECONDS:
            self._win_t -= WINDOW_SECONDS
            if not self._close_window(envelope):
                break
            self._win_samples = 0

    def _close_window(self, envelope: float) -> bool:
        if self._win_samples == 0:  # 샘플이 없던 창은 개수에 넣지 않는다
            self._empty_run += 1
            if self._empty_run >= self.loss_windows:
                self.error = ERR_LOST
                self._begin(self.stage)
                return False
            return True
        self._empty_run = 0
        self.last_value = envelope
        self.values.append(envelope)
        if len(self.values) >= self.needed:
            self._finish_stage()
            return False
        return True

    def _finish_stage(self) -> None:
        if self.stage == MIN:
            self._lo_values = self.values
            self._begin(MAX)
            return
        lo = emg.rest_level(self._lo_values)
        hi = emg.max_level(self.values, MAX_TOP_N)
        if emg.calibration_ok(lo, hi):
            self.lo, self.hi = lo, hi
            self.error = ""
            self.phase = DONE
        else:
            self.error = ERR_RANGE
            self._begin(MIN)
