"""드래곤 보스. 상단 가운데에 고정돼 있고 체력이 줄어 페이즈가 넘어갈 때마다 불이 많고 빠르게 떨어진다."""

import random

import pygame

from config import (
    ARENA_W,
    BOSS_BODY_H,
    BOSS_BODY_W,
    BOSS_MAX_HP,
    BOLT_AIM_SPREAD,
    METEOR_DRIFT,
    METEOR_FIRST_DELAY,
    METEOR_SIZE,
    METEOR_START_SPEED,
    BOLT_H,
    BOLT_W,
    BOLT_WARN_SECONDS,
    BOSS_PHASES,
    BOSS_WING_W,
    BOSS_Y,
    FIRE_H,
    FIRE_MIN_GAP,
    FIRE_SPAWN_JITTER,
    FIRE_W,
)


class Meteor:
    """큼직하게 비스듬히 떨어지는 운석. 위치와 속도를 직접 들고 있다."""

    def __init__(self, x: float, vx: float):
        self.x = x
        self.y = -METEOR_SIZE / 2.0
        self.vx = vx
        self.vy = METEOR_START_SPEED

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(0, 0, METEOR_SIZE, METEOR_SIZE).move(int(self.x - METEOR_SIZE / 2), int(self.y - METEOR_SIZE / 2))


class Boss:
    def __init__(self, rng: random.Random | None = None):
        self._rng = rng or random.Random()
        self.x = ARENA_W / 2
        self.hp = BOSS_MAX_HP
        self._fire_cd = 1.0
        self._bolt_cd = 2.0
        self.warnings: list[list[float]] = []  # [x, 남은 시간]: 곧 빠른 총알이 지나갈 자리
        self._ready: list[pygame.Rect] = []
        self._meteor_cd = METEOR_FIRST_DELAY
        self._new_meteors: list[Meteor] = []
        self.events: list[str] = []  # 효과음용: "bolt_warn", "bolt"

    @property
    def rect(self) -> pygame.Rect:
        """총알이 맞는 몸통."""
        return pygame.Rect(0, 0, BOSS_BODY_W, BOSS_BODY_H).move(
            int(self.x - BOSS_BODY_W / 2), int(BOSS_Y - BOSS_BODY_H / 2)
        )

    @property
    def alive(self) -> bool:
        return self.hp > 0

    @property
    def phase(self) -> int:
        """0부터 시작하는 페이즈. 체력을 BOSS_PHASES 개수만큼 등분해 줄어든 만큼 넘어간다."""
        n = len(BOSS_PHASES)
        return min(n - 1, int((1.0 - self.hp / BOSS_MAX_HP) * n))

    @property
    def config(self) -> dict:
        return BOSS_PHASES[self.phase]

    def update(self, dt: float, target_x: float | None = None) -> list[pygame.Rect]:
        """이번에 새로 떨어뜨린 불을 돌려준다. target_x는 빠른 총알이 노리는 플레이어 위치다."""
        cfg = self.config
        self._update_bolts(dt, cfg, target_x)
        self._update_meteors(dt, cfg)
        self._fire_cd -= dt
        if self._fire_cd > 0:
            return []
        self._fire_cd += cfg["interval"]
        fy = BOSS_Y + BOSS_BODY_H / 2  # 보스 몸 아래쪽 가장자리
        xs: list[float] = []
        for _ in range(cfg["count"]):
            x = self._rng.uniform(FIRE_W, ARENA_W - FIRE_W)
            for _ in range(8):  # 같은 때 나오는 불끼리는 겹쳐 보이지 않게 띄운다
                if all(abs(x - o) >= FIRE_MIN_GAP for o in xs):
                    break
                x = self._rng.uniform(FIRE_W, ARENA_W - FIRE_W)
            xs.append(x)
        return [
            pygame.Rect(int(x - FIRE_W / 2), int(fy - self._rng.uniform(0, FIRE_SPAWN_JITTER)), FIRE_W, FIRE_H)
            for x in xs
        ]

    def _update_bolts(self, dt: float, cfg: dict, target_x: float | None) -> None:
        for w in self.warnings:
            w[1] -= dt
        for w in [w for w in self.warnings if w[1] <= 0]:
            self.warnings.remove(w)
            top = int(BOSS_Y + BOSS_BODY_H / 2)
            self._ready.append(pygame.Rect(int(w[0] - BOLT_W / 2), top, BOLT_W, BOLT_H))
            self.events.append("bolt")
        if not cfg["bolt_interval"]:
            return
        self._bolt_cd -= dt
        if self._bolt_cd > 0:
            return
        self._bolt_cd += cfg["bolt_interval"]
        x = self._rng.uniform(40, ARENA_W - 40)
        if target_x is not None:
            x = target_x + self._rng.uniform(-BOLT_AIM_SPREAD, BOLT_AIM_SPREAD)
        self.warnings.append([max(20.0, min(ARENA_W - 20.0, x)), BOLT_WARN_SECONDS])
        self.events.append("bolt_warn")

    def _update_meteors(self, dt: float, cfg: dict) -> None:
        if not cfg.get("meteor_interval"):
            self._meteor_cd = METEOR_FIRST_DELAY  # 그 페이즈가 아니면 다음 페이즈 시작에 맞춰 기다린다
            return
        self._meteor_cd -= dt
        if self._meteor_cd > 0:
            return
        self._meteor_cd += cfg["meteor_interval"]
        x = self._rng.uniform(METEOR_SIZE, ARENA_W - METEOR_SIZE)
        self._new_meteors.append(Meteor(x, self._rng.uniform(-METEOR_DRIFT, METEOR_DRIFT)))
        self.events.append("meteor")

    def pop_meteors(self) -> list["Meteor"]:
        ready, self._new_meteors = self._new_meteors, []
        return ready

    def pop_bolts(self) -> list[pygame.Rect]:
        """경고가 끝나 이제 발사된 빠른 총알들."""
        ready, self._ready = self._ready, []
        return ready

    def hit(self, damage: int = 1) -> None:
        self.hp = max(0, self.hp - damage)
