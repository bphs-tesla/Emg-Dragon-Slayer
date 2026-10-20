"""배경 멜로디. assets/music/ 의 `title`, `battle` 파일(.wav .ogg .mp3)을 화면에 맞춰 반복 재생한다.

파일이 없으면 조용히 넘어간다. 곡이 이미 나오고 있으면 다시 시작하지 않고 이어서 들려준다.
"""

import os

import pygame

import config
import paths

MUSIC_DIR = os.path.join(paths.resource_dir(), "assets", "music")
EXTENSIONS = (".ogg", ".mp3", ".wav")

# 화면 -> 곡 이름. None이면 음악을 멈춘다 (결과 화면은 이기고 진 효과음이 대신 나온다)
SCREEN_TRACKS = {
    "sensor": "title",
    "title": "title",
    "howto": "title",
    "name": "title",
    "select": "title",
    "calib": "title",
    "play": "battle",
    "result": None,
}


class Music:
    def __init__(self, folder: str = MUSIC_DIR, volume: float | None = None):
        self.folder = folder
        self.volume = config.MUSIC_VOLUME if volume is None else volume
        self.muted = not config.MUSIC_ENABLED
        self.current: str | None = None
        self.available = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self.available = True
        except pygame.error:  # 소리 장치가 없으면 음악 없이 진행한다
            return
        self._apply_volume()

    def _apply_volume(self) -> None:
        if self.available:
            pygame.mixer.music.set_volume(0.0 if self.muted else max(0.0, min(1.0, self.volume)))

    def _find(self, name: str) -> str | None:
        for ext in EXTENSIONS:
            path = os.path.join(self.folder, name + ext)
            if os.path.isfile(path):
                return path
        return None

    def play(self, name: str | None) -> None:
        """name 곡을 반복해서 튼다. 이미 나오는 곡이면 그대로 두고, None이거나 파일이 없으면 멈춘다."""
        if not self.available or name == self.current:
            return
        self.current = name
        pygame.mixer.music.fadeout(400)
        path = self._find(name) if name else None
        if not path:
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play(loops=-1, fade_ms=600)
        except pygame.error:
            self.current = None  # 깨진 파일은 건너뛴다
            return
        self._apply_volume()

    def set_muted(self, muted: bool) -> None:
        self.muted = muted
        self._apply_volume()
