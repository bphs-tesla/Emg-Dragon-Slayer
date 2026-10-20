"""효과음. assets/sfx/ 에 이벤트 이름으로 된 파일을 넣으면 그 순간에 재생된다. 파일이 없으면 조용히 넘어간다.

파일 이름은 `이름.wav`/`.ogg`/`.mp3`이고, `이름_2.wav`처럼 `_숫자`를 붙여 여러 개 넣으면 그중 하나를 무작위로 틀어 준다.
"""

import os
import random
import re

import pygame

import config
import paths

SFX_DIR = os.path.join(paths.resource_dir(), "assets", "sfx")
EXTENSIONS = (".wav", ".ogg", ".mp3")

# 이벤트 이름과 언제 나오는지 (README와 같은 내용)
EVENTS = {
    "shoot": "플레이어 총알이 나갈 때",
    "fire": "보스가 불을 떨어뜨릴 때",
    "boss_hit": "총알이 보스에 맞을 때",
    "player_hit": "플레이어가 불이나 빠른 총알에 맞을 때",
    "phase": "보스 페이즈가 넘어갈 때",
    "meteor": "운석이 나타날 때",
    "bolt_warn": "빠른 총알 경고선이 나올 때",
    "bolt": "빠른 총알이 발사될 때",
    "win": "이겼을 때",
    "lose": "졌을 때",
    "confirm": "Enter로 다음 화면으로 넘어갈 때",
    "select": "캐릭터 선택에서 ← → 를 누를 때",
    "type": "이름을 입력할 때",
    "tick": "측정 카운트다운 3, 2, 1",
    "measure_done": "힘 측정이 끝났을 때",
}


class Sfx:
    def __init__(self, folder: str = SFX_DIR, volumes: dict | None = None, master: float | None = None):
        self.sounds: dict[str, list[pygame.mixer.Sound]] = {}
        self.muted = not config.SFX_ENABLED
        self.available = False
        self._volumes = config.SFX_VOLUMES if volumes is None else volumes
        self._master = config.SFX_VOLUME if master is None else master
        self._rng = random.Random()
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self.available = True
        except pygame.error:  # 소리 장치가 없으면 효과음 없이 진행한다
            return
        self._load(folder)

    def _load(self, folder: str) -> None:
        for name in EVENTS:
            sounds = []
            variant = re.compile(rf"^{re.escape(name)}(_\d+)?({'|'.join(re.escape(e) for e in EXTENSIONS)})$")  # bolt가 bolt_warn을 가져가지 않게
            paths = sorted(os.path.join(folder, f) for f in os.listdir(folder) if variant.match(f)) if os.path.isdir(folder) else []
            for path in paths:
                try:
                    sound = pygame.mixer.Sound(path)
                except pygame.error:
                    continue  # 깨진 파일은 건너뛴다
                sound.set_volume(max(0.0, min(1.0, self._volumes.get(name, 1.0) * self._master)))
                sounds.append(sound)
            if sounds:
                self.sounds[name] = sounds

    def play(self, name: str) -> None:
        if self.muted or not self.available:
            return
        options = self.sounds.get(name)
        if options:
            self._rng.choice(options).play()

    def toggle_mute(self) -> bool:
        self.muted = not self.muted
        return self.muted
