"""How to Play 화면에서 보여주는 자동 플레이. 불을 피하는 간단한 봇이 실제 전투 규칙으로 움직인다."""

import random

import emg
from config import ARENA_W, BOSS_MAX_HP, FAKE_RAMP, FIRE_GRAVITY, PLAYER_SPEED
from game import Battle, PLAYING, fire_speed

LOOK_AHEAD = 260  # 플레이어 위로 이만큼 안에 있는 불을 피할 대상으로 본다
SAFE_GAP = 52     # 불과 이만큼 떨어진 곳이면 안전하게 본다
DEAD_ZONE = 14    # 목표 위치와 이만큼 가까우면 멈춘다
PATH_MARGIN = 34  # 이동하는 길 양옆으로 이만큼 안에 위험이 있으면 지나가지 않는다


class Demo:
    def __init__(self, rng: random.Random | None = None):
        self._rng = rng or random.Random(3)
        self.battle = Battle(self._rng)
        self.force = 0.5  # 게이지에 보이는 힘. 봇이 정한 목표값으로 천천히 움직인다

    def _threats(self) -> list[tuple[float, float]]:
        """(가로 위치, 플레이어 줄에 닿기까지 남은 시간) 목록. 불, 경고선, 날아가는 총알이 대상이다."""
        b = self.battle
        top = b.player.rect.top
        v0 = b.boss.config["speed"]
        g = FIRE_GRAVITY
        out = []
        for f in b.fires:
            if f.bottom > 0 and f.top < top and top - f.bottom < LOOK_AHEAD:
                # 가속하며 내려오므로 도착까지 걸리는 시간 = (도착 때 속도 - 지금 속도) / 중력
                t = (fire_speed(top - f.bottom + f.y, v0) - fire_speed(f.y, v0)) / g
                out.append((f.centerx, max(0.0, t)))
        out += [(w[0], w[1] + 0.05) for w in b.boss.warnings]
        out += [(bolt.centerx, 0.0) for bolt in b.bolts if bolt.bottom < top]
        return out

    def _target_force(self) -> float:
        """가까이 오는 위험을 피해 갈 수 있는 가장 안전한 자리로 가도록 힘을 정한다."""
        px = self.battle.player.rect.centerx
        threats = self._threats()
        if not threats:
            target = ARENA_W / 2  # 할 일이 없으면 가운데로 돌아간다
        else:
            def score(x: int) -> float:
                gap = min(abs(x - tx) for tx, _ in threats)
                travel = abs(x - px) / PLAYER_SPEED
                lo, hi = min(px, x) - PATH_MARGIN, max(px, x) + PATH_MARGIN
                blocked = sum(1 for tx, t in threats if lo <= tx <= hi and t < travel + 0.25)
                return min(gap, SAFE_GAP) * 4 - abs(x - px) * 0.2 - blocked * 400
            target = max(range(40, ARENA_W - 39, 10), key=score)
        if px < target - DEAD_ZONE:
            return 0.95
        if px > target + DEAD_ZONE:
            return 0.05
        return 0.5

    def update(self, dt: float) -> None:
        step = FAKE_RAMP * 3 * dt  # 봇은 사람보다 힘을 빨리 바꾼다
        self.force += max(-step, min(step, self._target_force() - self.force))
        self.battle.update(dt, emg.direction(self.force))
        self.battle.events.clear()  # 예시 화면은 소리를 내지 않는다
        # 보여주기용이라 끝나지 않게, 가장 어려운 3페이즈 전에 새 판을 시작한다
        if self.battle.state != PLAYING or self.battle.boss.phase >= 2 or self.battle.boss.hp < BOSS_MAX_HP * 0.1:
            self.battle = Battle(self._rng)
