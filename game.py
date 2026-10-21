"""전투 규칙. 플레이어와 보스를 묶어 투사체 이동과 충돌을 처리한다.

화면 그리기는 main.py가 맡고 여기서는 위치와 충돌만 계산한다.
"""

import math
import random

import pygame

from boss import Boss, Meteor
from config import (
    ARENA_H,
    ARENA_W,
    BOLT_SPEED,
    BOSS_BODY_H,
    BOSS_Y,
    BULLET_SPEED,
    DEFAULT_DIFFICULTY,
    DIFFICULTIES,
    FIRE_GRAVITY,
    FIRE_HIT_SHRINK,
    METEOR_GRAVITY,
    METEOR_HIT_SHRINK,
    PHASE_BANNER_SECONDS,
)
from player import Player

FIRE_ORIGIN_Y = BOSS_Y + BOSS_BODY_H / 2  # 불이 나오는 보스 몸 아래쪽 가장자리


def fire_speed(y: float, start_speed: float, gravity: float = FIRE_GRAVITY) -> float:
    """불이 보스 아래에서 출발해 y 높이까지 내려왔을 때의 속도. 위치만으로 정해져 불마다 따로 저장할 게 없다."""
    return math.sqrt(start_speed**2 + 2 * gravity * max(0.0, y - FIRE_ORIGIN_Y))


PLAYING, WON, LOST = "playing", "won", "lost"


class Battle:
    def __init__(self, rng: random.Random | None = None, difficulty: str = DEFAULT_DIFFICULTY):
        self.difficulty = difficulty
        self.gravity = DIFFICULTIES[difficulty]["gravity"]
        self.player = Player()
        self.boss = Boss(rng, DIFFICULTIES[difficulty]["phases"])
        self.bullets: list[pygame.Rect] = []
        self.fires: list[pygame.Rect] = []
        self.meteors: list[Meteor] = []  # 3페이즈에 가끔 떨어지는 큰 운석
        self.bolts: list[pygame.Rect] = []  # 2페이즈부터 나오는 빠른 총알
        self._bolt_sweeps: list[pygame.Rect] = []  # 이번 프레임에 총알이 지나간 영역 (빨라서 통과하지 않게)
        self.state = PLAYING
        self.time = 0.0
        self.events: list[str] = []  # 이번에 일어난 일들. 효과음을 틀 쪽(main.py)이 가져가 비운다
        self.banner = 0.0  # 페이즈가 바뀐 직후 "PHASE N"을 보여주는 남은 시간

    def update(self, dt: float, direction: int) -> None:
        if self.state != PLAYING:
            return
        self.time += dt
        self.banner = max(0.0, self.banner - dt)
        shots = self.player.update(dt, direction)
        if shots:
            self.events.append("shoot")
        self.bullets += shots
        new_fires = self.boss.update(dt, self.player.x)
        if new_fires:
            self.events.append("fire")
        self.fires += new_fires
        self.bolts += self.boss.pop_bolts()
        self.meteors += self.boss.pop_meteors()
        self.events += self.boss.events
        self.boss.events.clear()
        self._move_projectiles(dt)
        self._collide()

    def _move_projectiles(self, dt: float) -> None:
        for b in self.bullets:
            b.y -= round(BULLET_SPEED * dt)
        self.bullets = [b for b in self.bullets if b.bottom > 0]
        speed = self.boss.config["speed"]
        for f in self.fires:
            f.y += round(fire_speed(f.y, speed, self.gravity) * dt)
        self.fires = [f for f in self.fires if f.top < ARENA_H]
        for m in self.meteors:
            m.vy += METEOR_GRAVITY * dt
            m.x += m.vx * dt
            m.y += m.vy * dt
        self.meteors = [m for m in self.meteors if m.rect.top < ARENA_H and -200 < m.x < ARENA_W + 200]
        move = round(BOLT_SPEED * dt)
        self._bolt_sweeps = []
        for b in self.bolts:
            self._bolt_sweeps.append(pygame.Rect(b.x, b.y, b.w, b.h + move))
            b.y += move
        self.bolts = [b for b in self.bolts if b.top < ARENA_H]

    def _collide(self) -> None:
        boss_rect = self.boss.rect
        hits = [b for b in self.bullets if boss_rect.colliderect(b)]
        if hits:
            self.bullets = [b for b in self.bullets if b not in hits]
            before = self.boss.phase
            self.events.append("boss_hit")
            self.boss.hit(len(hits))
            if self.boss.alive and self.boss.phase != before:
                self.banner = PHASE_BANNER_SECONDS
                self.events.append("phase")
            if not self.boss.alive:
                self.state = WON
                self.events.append("win")
                return

        if not self.player.vulnerable:
            return
        player_rect = self.player.rect
        for f in self.fires:
            if player_rect.colliderect(f.inflate(-FIRE_HIT_SHRINK, -FIRE_HIT_SHRINK)):
                self.fires.remove(f)
                self._damage_player()
                return
        for m in self.meteors:
            if player_rect.colliderect(m.rect.inflate(-METEOR_HIT_SHRINK, -METEOR_HIT_SHRINK)):
                self.meteors.remove(m)
                self._damage_player()
                return
        for sweep in self._bolt_sweeps:
            if player_rect.colliderect(sweep):
                self._damage_player()
                return

    def _damage_player(self) -> None:
        self.player.hit()
        self.events.append("player_hit")
        if not self.player.alive:
            self.state = LOST
            self.events.append("lose")
