"""EMG 입력 소스. 게임은 read()로 새 샘플 목록만 가져간다."""

import math
import random
import threading
import time
from collections import deque


class FakeSource:
    """센서 없이 개발·리허설용. 힘(force)에 비례하는 진폭의 잡음을 만든다."""

    connected = True

    def __init__(self, rate_hz=1000, base_noise=2.0, scale=100.0, rng=None, clock=time.monotonic):
        self.rate_hz = rate_hz
        self.base_noise = base_noise
        self.scale = scale
        self.force = 0.0
        self._rng = rng or random.Random()
        self._clock = clock
        self._last = 0.0

    def start(self) -> None:
        self._last = self._clock()

    def stop(self) -> None:
        pass

    def set_force(self, force: float) -> None:
        self.force = max(0.0, min(1.2, force))

    def read(self) -> list[float]:
        now = self._clock()
        n = int((now - self._last) * self.rate_hz)
        if n <= 0:
            return []
        self._last += n / self.rate_hz
        sigma = self.base_noise + self.force * self.scale
        return [self._rng.gauss(0.0, sigma) for _ in range(n)]


def _open_serial(port: str, baud: int):
    import serial

    return serial.Serial(port, baud, timeout=0.1)


def list_ports() -> list[str]:
    from serial.tools import list_ports as lp

    return [p.device for p in lp.comports()]


class SerialSource:
    """SpikerBox의 4바이트 프레임 스트림을 백그라운드 스레드로 읽어 CH1 값만 모은다.

    프레임: 첫 바이트만 최상위 비트가 1이고 나머지 3바이트는 0이다.
    CH1 = ((b1 & 0x7F) << 7) | (b2 & 0x7F)
    """

    FRAME = 4

    def __init__(self, port: str, baud: int = 115200, retry_seconds: float = 2.0, serial_factory=None):
        self.port = port
        self.baud = baud
        self.retry_seconds = retry_seconds
        self.connected = False
        self.bad_bytes = 0
        self._factory = serial_factory or _open_serial
        self._buffer: deque[float] = deque()
        self._pending = b""  # 프레임이 읽기 경계에 걸렸을 때 다음 읽기로 넘기는 나머지
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)

    def read(self) -> list[float]:
        with self._lock:
            out = list(self._buffer)
            self._buffer.clear()
        return out

    def _handle_bytes(self, chunk: bytes) -> None:
        data = self._pending + chunk
        values = []
        i = 0
        while i < len(data):
            if not data[i] & 0x80:
                self.bad_bytes += 1
                i += 1
                continue
            if i + self.FRAME > len(data):
                break
            b1, b2, b3, b4 = data[i:i + self.FRAME]
            if (b2 | b3 | b4) & 0x80:
                self.bad_bytes += 1
                i += 1
                continue
            values.append(float(((b1 & 0x7F) << 7) | (b2 & 0x7F)))
            i += self.FRAME
        self._pending = data[i:]
        if values:
            with self._lock:
                self._buffer.extend(values)

    def _run(self) -> None:
        # serial.SerialException은 OSError의 하위 클래스라 함께 잡힌다.
        while not self._stop.is_set():
            try:
                ser = self._factory(self.port, self.baud)
            except OSError:
                self.connected = False
                self._stop.wait(self.retry_seconds)
                continue
            self.connected = True
            self._pending = b""
            try:
                with ser:
                    while not self._stop.is_set():
                        chunk = ser.read(ser.in_waiting or 1)
                        if chunk:
                            self._handle_bytes(chunk)
            except OSError:
                pass
            self.connected = False
            self._stop.wait(self.retry_seconds)
