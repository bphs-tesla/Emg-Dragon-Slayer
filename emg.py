"""EMG 원시 샘플을 0~1 힘 세기로 바꾸고, 힘 세기를 이동 방향으로 나눈다."""

from collections import deque
from statistics import fmean, pstdev

from config import (
    CALIB_MIN_RATIO as MIN_RATIO,
    CALIB_MIN_SPAN as MIN_SPAN,
    EMG_ALPHA,
    EMG_WINDOW,
    INPUT_GAIN,
    LEFT_MAX,
    MAX_TOP_N,
    MIN_SAMPLES,
    RIGHT_MIN,
)


def direction(force: float) -> int:
    """-1: 왼쪽, 0: 정지, 1: 오른쪽."""
    if force < LEFT_MAX:
        return -1
    if force > RIGHT_MIN:
        return 1
    return 0


def rest_level(values: list[float]) -> float:
    """최소 힘 = 모은 값의 평균."""
    return fmean(values)


def max_level(values: list[float], top_n: int = MAX_TOP_N) -> float:
    """최대 힘 = 모은 값 중 상위 top_n개의 평균. 한 번 튄 잡음이 최대값이 되지 않게 한다."""
    return fmean(sorted(values)[-top_n:])


def calibration_ok(lo: float, hi: float) -> bool:
    return hi - lo >= MIN_SPAN and hi >= lo * MIN_RATIO


class ForceEstimator:
    """최근 샘플의 진폭(표준편차)을 부드럽게 이어 힘 세기로 바꾼다.

    표준편차를 쓰므로 센서 값이 0이 아닌 중심값 근처에서 흔들려도 상관없다.
    """

    def __init__(self, window: int = EMG_WINDOW, alpha: float = EMG_ALPHA):
        self._buf: deque[float] = deque(maxlen=window)
        self.alpha = alpha
        self.envelope = 0.0
        self.lo: float | None = None
        self.hi: float | None = None
        self._started = False

    def update(self, samples: list[float]) -> float:
        self._buf.extend(samples)
        if len(self._buf) >= MIN_SAMPLES:
            raw = pstdev(self._buf)
            if self._started:
                self.envelope += self.alpha * (raw - self.envelope)
            else:
                self.envelope = raw
                self._started = True
        return self.envelope

    def calibrate(self, lo: float, hi: float) -> None:
        self.lo = lo
        self.hi = hi

    @property
    def calibrated(self) -> bool:
        return self.lo is not None and self.hi is not None

    @property
    def force(self) -> float:
        if not self.calibrated:
            return 0.0
        span = self.hi - self.lo
        return max(0.0, min(1.0, (self.envelope * INPUT_GAIN - self.lo) / span))
