"""플레이어. 좌우 이동, 자동 발사, 목숨과 무적 시간을 맡는다."""

import pygame

from config import (
    ARENA_W,
    BULLET_H,
    BULLET_W,
    INVULN_SECONDS,
    MAX_LIVES,
    PLAYER_H,
    PLAYER_SPEED,
    PLAYER_W,
    PLAYER_Y,
    SHOT_INTERVAL,
)


class Player:
    def __init__(self):
        self.x = ARENA_W / 2
        self.lives = MAX_LIVES
        self.invuln = 0.0
        self._shot_cd = 0.0

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(0, 0, PLAYER_W, PLAYER_H).move(
            int(self.x - PLAYER_W / 2), int(PLAYER_Y - PLAYER_H / 2)
        )

    @property
    def alive(self) -> bool:
        return self.lives > 0

    @property
    def vulnerable(self) -> bool:
        return self.invuln <= 0

    def update(self, dt: float, direction: int) -> list[pygame.Rect]:
        """이동하고 무적 시간을 줄인다. 이번에 새로 나간 총알을 돌려준다."""
        self.invuln = max(0.0, self.invuln - dt)
        half = PLAYER_W / 2
        self.x = max(half, min(ARENA_W - half, self.x + direction * PLAYER_SPEED * dt))

        self._shot_cd -= dt
        if self._shot_cd > 0:
            return []
        self._shot_cd += SHOT_INTERVAL
        top = int(PLAYER_Y - PLAYER_H / 2)
        return [pygame.Rect(int(self.x - BULLET_W / 2), top - BULLET_H, BULLET_W, BULLET_H)]

    def hit(self) -> None:
        self.lives -= 1
        self.invuln = INVULN_SECONDS
