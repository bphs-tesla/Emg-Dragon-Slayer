"""근육 힘으로 조종하는 드래곤 피하기 슈팅 게임.

실행: uv run main.py               센서 없이 키보드로 (FakeSource)
      uv run main.py --port 포트   SpikerBox 연결
      uv run main.py --list-ports  연결 가능한 포트 보기
"""

import argparse
import glob
import math
import os
import random
import re
import sys

import pygame

import config
import emg
import demo
import game
import leaderboard
import measure
import music
import paths
import sensor
import sfx
import theme
from config import (
    BOSS_DRAW_H,
    BOOTH,
    BOOTH_SPACING,
    CREDIT,
    FAKE_RAMP,
    FIRE_DRAW_H,
    FIRE_DRAW_W,
    FPS,
    GAME_TITLE,
    HEART_SIZE,
    HERO_DEFEAT_MESSAGES,
    HERO_NAMES,
    NAME_MAX,
    TITLE_SPACING,
    PANEL_W,
    SERIAL_BAUD,
)
from source import FakeSource, SerialSource, list_ports

WIN_W, WIN_H = config.ARENA_W + PANEL_W, config.ARENA_H
ASSET_DIR = os.path.join(paths.resource_dir(), "assets")


HERO_BIG_W, HERO_BIG_H = 200, 260  # 선택창에서 크게 보여주는 캐릭터
BULLET_BIG = 160
ARM_SIZE = (116, 66)  # How to Play의 팔 그림
HERO_COLORS = [(230, 90, 80), (90, 160, 240), (110, 200, 120), (240, 190, 70), (190, 120, 230)]
# How to Play 화면 설명. (제목, 줄글)
HOW_TO_PLAY = [
    ("움직이기", "힘을 완전히 빼면 왼쪽, 적당히 주면 제자리, 세게 주면 오른쪽으로 움직여요."),
    ("공격하기", "총알은 자동으로 나가요. 움직이면서 드래곤에게 맞히기만 하세요."),
    ("피하기", "떨어지는 불에 맞으면 하트가 하나씩 줄고, 5개를 모두 잃으면 패배예요."),
    ("이기기", "드래곤 체력을 모두 깎으면 승리! 빨리 깨고 하트가 많이 남을수록 순위가 올라가요."),
]
GALMURI_FONT = os.path.join(ASSET_DIR, "fonts", "Galmuri11.ttf")
GALMURI9_FONT = os.path.join(ASSET_DIR, "fonts", "Galmuri9.ttf")
FONT_NAMES = ["applesdgothicneo", "applegothic", "malgungothic", "nanumgothic", "notosanscjkkr"]
FONT_FALLBACK = "/System/Library/Fonts/AppleSDGothicNeo.ttc"


def natural_key(path: str) -> list:
    """파일 이름의 숫자를 숫자로 비교한다. (hero_10이 hero_2보다 뒤에 오게)"""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", os.path.basename(path))]


def load_font_path() -> str | None:
    if os.path.exists(GALMURI_FONT):
        return GALMURI_FONT
    for name in FONT_NAMES:
        path = pygame.font.match_font(name)
        if path:
            return path
    return FONT_FALLBACK if os.path.exists(FONT_FALLBACK) else None


def load_cover(path: str, size: tuple[int, int]) -> pygame.Surface | None:
    """화면을 빈틈없이 덮도록 비율을 유지해 키우고 가운데를 잘라낸다."""
    if not os.path.exists(path):
        return None
    try:
        img = pygame.image.load(path).convert()
    except pygame.error:
        return None
    scale = max(size[0] / img.get_width(), size[1] / img.get_height())
    img = pygame.transform.smoothscale(img, (round(img.get_width() * scale), round(img.get_height() * scale)))
    x, y = (img.get_width() - size[0]) // 2, (img.get_height() - size[1]) // 2
    return img.subsurface((x, y, *size)).copy()


def load_image(path: str, size: tuple[int, int]) -> pygame.Surface | None:
    """투명 여백을 잘라내고 비율을 유지한 채 size 안에 꽉 차게 줄인다."""
    if not os.path.exists(path):
        return None
    img = pygame.image.load(path).convert_alpha()
    img = img.subsurface(img.get_bounding_rect(min_alpha=10))  # 배경이 alpha 1로 깔린 이미지도 있다
    scale = min(size[0] / img.get_width(), size[1] / img.get_height())
    return pygame.transform.smoothscale(img, (round(img.get_width() * scale), round(img.get_height() * scale)))


class Assets:
    """assets/characters, assets/projectiles의 이미지를 읽고, 없는 건 None으로 둔다."""

    def __init__(self):
        chars = os.path.join(ASSET_DIR, "characters")
        ui_dir = os.path.join(ASSET_DIR, "ui")
        shots = os.path.join(ASSET_DIR, "projectiles")
        self.boss = load_image(os.path.join(ASSET_DIR, "boss", "boss.png"), (config.BOSS_WING_W, BOSS_DRAW_H))
        hero_files = sorted(glob.glob(os.path.join(chars, "hero_*.png")), key=natural_key)  # hero_2 다음 hero_10
        self.heroes = [load_image(p, (config.PLAYER_W, config.PLAYER_H)) for p in hero_files]
        # hero_N.png의 짝은 bullet_N.png. 용사 파일이 없으면 순번(1, 2, ...)을 쓴다.
        ids = [os.path.basename(p)[len("hero_"):-len(".png")] for p in hero_files] or [
            str(i + 1) for i in range(len(HERO_COLORS))
        ]
        bullet_size = (config.BULLET_W, config.BULLET_H)
        self.bullet = load_image(os.path.join(shots, "bullet.png"), bullet_size)  # 짝이 없을 때 공통으로 쓴다
        self.bullets = [load_image(os.path.join(shots, f"bullet_{i}.png"), bullet_size) for i in ids]
        # 캐릭터 선택창에서 크게 보여주는 그림
        self.heroes_big = [load_image(p, (HERO_BIG_W, HERO_BIG_H)) for p in hero_files]
        self.bullet_big = load_image(os.path.join(shots, "bullet.png"), (BULLET_BIG, BULLET_BIG))
        self.bullets_big = [load_image(os.path.join(shots, f"bullet_{i}.png"), (BULLET_BIG, BULLET_BIG)) for i in ids]
        # 타이틀 화면용: 배경, 큰 용, 아래에 늘어세울 캐릭터
        self.title_bg = load_cover(os.path.join(ui_dir, "title_bg.jpg"), (WIN_W, WIN_H))
        self.title_boss = load_image(os.path.join(ASSET_DIR, "boss", "boss.png"), (780, 360))
        self.fire = load_image(os.path.join(shots, "fireball.png"), (FIRE_DRAW_W, FIRE_DRAW_H))
        ui = ui_dir
        self.heart = load_image(os.path.join(ui, "heart.png"), (HEART_SIZE, HEART_SIZE))
        self.heart_small = load_image(os.path.join(ui, "heart.png"), (18, 18))
        self.arm_relax = load_image(os.path.join(ui, "arm_relax.png"), ARM_SIZE)  # 힘 뺀 팔
        self.arm_flex = load_image(os.path.join(ui, "arm_flex.png"), ARM_SIZE)    # 힘 준 팔
        self.heart_empty = load_image(os.path.join(ui, "heart_empty.png"), (HEART_SIZE, HEART_SIZE))
        if self.heart and not self.heart_empty:
            self.heart_empty = self.heart.copy()
            self.heart_empty.fill((70, 70, 70, 255), special_flags=pygame.BLEND_RGBA_MULT)

    @property
    def hero_count(self) -> int:
        return len(self.heroes) or len(HERO_COLORS)

    def bullet_big_for(self, hero: int) -> pygame.Surface | None:
        return (self.bullets_big[hero] if hero < len(self.bullets_big) else None) or self.bullet_big

    def bullet_for(self, hero: int) -> pygame.Surface | None:
        return self.bullets[hero] or self.bullet


def hero_name(index: int) -> str:
    name = HERO_NAMES[index].strip() if index < len(HERO_NAMES) else ""
    return name or f"용사 {index + 1}"


def draw_bubbles(surf, bubbles, t: float) -> None:
    w, h = surf.get_size()
    for bx, by, speed, r in bubbles:
        y = (by - speed * t) % (h + 20) - 10
        pygame.draw.circle(surf, (150, 215, 235), (int(bx + math.sin(t + by) * 6), int(y)), r, 1)


def make_bubbles(w: int, h: int, n: int, seed: int = 7) -> list[tuple[float, float, float, int]]:
    rng = random.Random(seed)  # 거품 위치는 고정된 난수로 정해 매번 같게 한다
    return [(rng.uniform(0, w), rng.uniform(0, h), rng.uniform(15, 45), rng.randint(2, 6)) for _ in range(n)]


def gradient(size: tuple[int, int], top, bottom) -> pygame.Surface:
    surf = pygame.Surface(size)
    for y in range(size[1]):
        t = y / max(1, size[1] - 1)
        pygame.draw.line(surf, tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)), (0, y), (size[0], y))
    return surf


def hero_defeat_message(index: int) -> str:
    """캐릭터별 패배 메시지. 적지 않았거나 공백이면 빈 문자열."""
    return HERO_DEFEAT_MESSAGES[index].strip() if index < len(HERO_DEFEAT_MESSAGES) else ""


def wrap(text: str, font: pygame.font.Font, width: int) -> list[str]:
    """띄어쓰기 단위로 줄을 나눈다. 한 단어가 한 줄보다 길 때만 글자 단위로 자른다."""
    lines, line = [], ""
    for word in text.split(" "):
        trial = f"{line} {word}" if line else word
        if font.size(trial)[0] <= width:
            line = trial
            continue
        if line:
            lines.append(line)
        line = ""
        for ch in word:
            if font.size(line + ch)[0] > width and line:
                lines.append(line)
                line = ch
            else:
                line += ch
    return lines + [line] if line else lines


def draw_text(surf, s, font, color, pos, anchor="topleft"):
    img = font.render(s, False, color)  # 도트 폰트라 안티앨리어싱을 끄면 또렷하다
    surf.blit(img, img.get_rect(**{anchor: pos}))


def draw_spaced(surf, s, font, color, center, spacing=0) -> None:
    """글자 사이를 spacing만큼 벌려서 가운데 맞춰 그린다."""
    widths = [font.size(ch)[0] for ch in s]
    x = center[0] - (sum(widths) + spacing * (len(s) - 1)) // 2
    for ch, w in zip(s, widths):
        img = font.render(ch, False, color)
        surf.blit(img, img.get_rect(midleft=(x, center[1])))
        x += w + spacing


def draw_heart(surf, cx, cy, size, color):
    r = size // 4
    pygame.draw.circle(surf, color, (cx - r, cy - r // 2), r)
    pygame.draw.circle(surf, color, (cx + r, cy - r // 2), r)
    pygame.draw.polygon(surf, color, [(cx - 2 * r, cy - r // 4), (cx + 2 * r, cy - r // 4), (cx, cy + 2 * r)])


def draw_hero(surf, rect, index, assets):
    img = assets.heroes[index] if index < len(assets.heroes) else None
    if img:
        surf.blit(img, img.get_rect(center=rect.center))
        return
    color = HERO_COLORS[index % len(HERO_COLORS)]
    cx = rect.centerx
    pygame.draw.circle(surf, (245, 215, 180), (cx, rect.top + 13), 11)
    pygame.draw.rect(surf, color, (cx - 12, rect.top + 25, 24, 22), border_radius=4)
    pygame.draw.rect(surf, (60, 50, 70), (cx - 10, rect.top + 47, 8, 9))
    pygame.draw.rect(surf, (60, 50, 70), (cx + 2, rect.top + 47, 8, 9))
    pygame.draw.rect(surf, (210, 210, 225), (cx + 14, rect.top + 4, 4, 30))  # 검
    pygame.draw.polygon(surf, (210, 210, 225), [(cx + 12, rect.top + 4), (cx + 20, rect.top + 4), (cx + 16, rect.top - 4)])


def draw_boss(surf, cx, cy, assets):
    if assets.boss:
        surf.blit(assets.boss, assets.boss.get_rect(center=(cx, cy)))
        return
    half = config.BOSS_WING_W // 2
    red, dark = (170, 40, 45), (110, 25, 35)
    pygame.draw.polygon(surf, dark, [(cx - 50, cy - 20), (cx - half, cy - 60), (cx - half + 40, cy + 70), (cx - 40, cy + 40)])
    pygame.draw.polygon(surf, dark, [(cx + 50, cy - 20), (cx + half, cy - 60), (cx + half - 40, cy + 70), (cx + 40, cy + 40)])
    pygame.draw.ellipse(surf, red, (cx - 60, cy - 50, 120, 120))
    pygame.draw.polygon(surf, (230, 210, 170), [(cx - 48, cy - 40), (cx - 30, cy - 85), (cx - 18, cy - 45)])
    pygame.draw.polygon(surf, (230, 210, 170), [(cx + 48, cy - 40), (cx + 30, cy - 85), (cx + 18, cy - 45)])
    for sx in (-1, 1):
        pygame.draw.polygon(surf, (255, 220, 60), [(cx + sx * 12, cy - 12), (cx + sx * 36, cy - 22), (cx + sx * 30, cy - 4)])
    pygame.draw.rect(surf, (60, 15, 20), (cx - 22, cy + 28, 44, 12), border_radius=4)


def draw_fire(surf, rect, assets):
    if assets.fire:
        surf.blit(assets.fire, assets.fire.get_rect(center=rect.center))
        return
    cx, w = rect.centerx, rect.w
    pygame.draw.polygon(surf, (255, 110, 30), [(cx, rect.top), (rect.left, rect.bottom - w // 2), (rect.right, rect.bottom - w // 2)])
    pygame.draw.circle(surf, (255, 110, 30), (cx, rect.bottom - w // 2), w // 2)
    pygame.draw.circle(surf, (255, 210, 80), (cx, rect.bottom - w // 2), w // 4)


def draw_bolt_warning(surf, x: float, remaining: float) -> None:
    """빠른 총알이 지나갈 자리를 위에서 아래로 깜빡이는 붉은 선으로 미리 보여준다."""
    flash = 0.5 + 0.5 * math.sin(remaining * 28)
    band = pygame.Surface((config.BOLT_W * 3, config.ARENA_H), pygame.SRCALPHA)
    band.fill((255, 60, 60, int(40 + 70 * flash)))
    top = config.BOSS_Y + config.BOSS_BODY_H // 2
    surf.blit(band, (int(x - band.get_width() / 2), top), (0, 0, band.get_width(), config.ARENA_H - top))
    pygame.draw.line(surf, (255, 120, 110), (x, top), (x, config.ARENA_H), 2)
    pygame.draw.polygon(surf, (255, 230, 120), [(x, top + 40), (x - 12, top + 18), (x + 12, top + 18)])


def draw_meteor(surf, m, t: float) -> None:
    """푸른 불꽃 꼬리를 단 바위. 따로 그림 파일 없이 도형으로 그린다."""
    cx, cy, r = int(m.x), int(m.y), config.METEOR_SIZE // 2
    # 꼬리: 날아오는 반대쪽으로 흩어지며 어두워지는 불꽃 덩어리들. 색을 더해서(밝게 겹쳐서) 불처럼 보이게 한다
    glow = pygame.Surface((r * 6, r * 8))
    gx, gy = glow.get_width() // 2, glow.get_height() - r * 2
    norm = math.hypot(m.vx, m.vy) or 1.0
    for i in range(13, -1, -1):  # 꼬리 끝부터 그려야 머리 쪽이 위에 온다
        k = i / 13
        fade = (1 - k) ** 1.3
        flick = math.sin(t * 18 + i * 1.7) * r * 0.18
        px = gx - m.vx / norm * i * r * 0.4 + flick
        py = gy - m.vy / norm * i * r * 0.4
        color = (int((120 - 90 * k) * fade), int((220 - 90 * k) * fade), int(255 * fade))  # 하늘색에서 짙은 파랑으로
        pygame.draw.circle(glow, color, (int(px), int(py)), max(3, int(r * (1.0 - 0.75 * k))))
    surf.blit(glow, (cx - gx, cy - gy), special_flags=pygame.BLEND_RGB_ADD)
    pygame.draw.circle(surf, (110, 215, 255), (cx, cy), r + 3)  # 푸른 빛 테두리
    pygame.draw.circle(surf, (50, 72, 120), (cx, cy), r)
    pygame.draw.circle(surf, (88, 122, 178), (cx - r // 4, cy - r // 4), r * 2 // 3)
    ang = t * 1.5 + m.y * 0.01  # 구덩이가 돌아가며 구르는 느낌
    for k, (dist, size) in enumerate(((0.45, 0.2), (0.62, 0.14), (0.25, 0.12))):
        a = ang + k * 2.1
        pygame.draw.circle(surf, (28, 42, 80), (cx + int(math.cos(a) * r * dist), cy + int(math.sin(a) * r * dist)), max(2, int(r * size)))


def draw_bolt(surf, rect) -> None:
    """작은 판정에 맞춰 가늘고 밝은 침 모양으로 그린다."""
    pygame.draw.rect(surf, (255, 90, 90), rect.inflate(6, 0), border_radius=4)
    pygame.draw.rect(surf, (255, 245, 220), rect, border_radius=3)


class App:
    def __init__(self, source, debug: bool = False, hero: int = 0, ask_sensor: bool = False, difficulty: str = config.DEFAULT_DIFFICULTY):
        pygame.init()
        pygame.display.set_caption(GAME_TITLE)
        # SCALED: 창이나 화면 크기에 맞춰 비율을 유지하며 키운다. 창 모드는 크기를 마우스로 바꿀 수 있다
        flags = pygame.SCALED | (pygame.FULLSCREEN if config.FULLSCREEN else pygame.RESIZABLE)
        if os.environ.get("SDL_VIDEODRIVER") == "dummy":  # 화면 없는 테스트 환경
            flags = 0
        self.screen = pygame.display.set_mode((WIN_W, WIN_H), flags)
        self.arena = pygame.Surface((config.ARENA_W, config.ARENA_H))
        font_path = load_font_path()
        # 갈무리는 도트 폰트라 11(Galmuri9는 9)의 배수 크기에서만 또렷하다
        small_path = GALMURI9_FONT if os.path.exists(GALMURI9_FONT) else font_path
        self.f_title = pygame.font.Font(font_path, 44)
        self.f_logo = pygame.font.Font(font_path, 66)
        self.f_tiny = pygame.font.Font(font_path, 11)
        self.f_huge = pygame.font.Font(font_path, 165)
        self.f_big = pygame.font.Font(font_path, 33)
        self.f_body = pygame.font.Font(font_path, 22)
        self.f_small = pygame.font.Font(small_path, 18)
        self.assets = Assets()
        th = theme.current()
        self.backdrops = [gradient((config.ARENA_W, config.ARENA_H), *c) for c in th["arena_bg"]]
        self.bubbles = make_bubbles(config.ARENA_W, config.ARENA_H, 28)
        self.screen_bubbles = make_bubbles(WIN_W, WIN_H, 40, seed=11)
        self.demo_arena = pygame.Surface((config.ARENA_W, config.ARENA_H))
        self.title_heroes = [
            pygame.transform.smoothscale(img, (round(img.get_width() * 86 / img.get_height()), 86))
            for img in self.assets.heroes_big
            if img
        ]

        self.source = source
        self._started = False  # run()에서 센서 읽기를 시작했는지
        self.sensor_label = "키보드 모드" if isinstance(source, FakeSource) else getattr(source, "port", "센서")
        self.sensor_ports: list[sensor.Port] = []
        self.sensor_sel = 0
        self._scan_t = 0.0
        self.fake = isinstance(source, FakeSource)
        self.fake_force = 0.0
        self.est = emg.ForceEstimator()

        # 화면 순서: title -> howto -> name -> difficulty -> select -> calib -> play -> result -> title
        self.state = "title"
        self.measure = measure.Measurement(started=True)
        self.hero = 0
        self.difficulty = difficulty
        self.battle = game.Battle(difficulty=difficulty)
        self.demo = demo.Demo()
        self.name = ""
        self.composing = ""  # 한글 조합 중인 글자
        self._boards = {d: leaderboard.load(difficulty=d) for d in config.DIFFICULTIES}  # 난이도마다 따로 쌓는 기록
        self.entries = self._boards[difficulty]
        self.rank: int | None = None
        self.sfx = sfx.Sfx()
        self.music = music.Music()
        if not debug:
            self.music.play(music.SCREEN_TRACKS["title"])
        self._last_tick = 0
        self.running = True
        self.debug = debug  # 개발자용: 타이틀~캐릭터 선택을 건너뛰고 바로 플레이한다. 기록은 남기지 않는다
        if debug:
            self.start_debug(hero)
        elif ask_sensor:
            self._boot_sensor()

    # ---- 입력 ----
    # ---- 센서 고르기 ----
    def _boot_sensor(self):
        """저장해 둔 포트나 확실한 후보가 하나뿐이면 바로 연결하고, 애매하면 센서 선택 화면을 먼저 보여준다."""
        ports = sensor.scan()
        pick = sensor.auto_pick(ports, sensor.load_settings().get("port"))
        if pick:
            self.use_port(pick)
        else:
            self.sensor_ports = ports
            self.sensor_sel = 0
            self.go("sensor")

    def set_source(self, new):
        """센서를 바꾼다. 이미 읽고 있었다면 옛 센서는 끄고 새 센서를 켠다."""
        if self._started:
            self.source.stop()
        self.source = new
        self.fake = isinstance(new, FakeSource)
        self.fake_force = 0.0
        self.est = emg.ForceEstimator()
        if self._started:
            new.start()

    def use_port(self, device: str):
        self.set_source(SerialSource(device, SERIAL_BAUD))
        self.sensor_label = device
        settings = sensor.load_settings()
        settings["port"] = device  # 다음 실행 때 물어보지 않고 이 포트로 연결한다
        sensor.save_settings(settings)

    def use_keyboard(self):
        self.set_source(FakeSource())
        self.sensor_label = "키보드 모드"

    def _rescan_sensors(self):
        chosen = self.sensor_ports[self.sensor_sel].device if self.sensor_sel < len(self.sensor_ports) else None
        self.sensor_ports = sensor.scan()
        devices = [p.device for p in self.sensor_ports]
        if chosen in devices:
            self.sensor_sel = devices.index(chosen)
        else:
            self.sensor_sel = min(self.sensor_sel, len(self.sensor_ports))  # 목록이 바뀌면 키보드 모드 줄(마지막)에 머문다

    def go(self, state: str):
        if state == "name":
            pygame.key.start_text_input()
        elif self.state == "name":
            pygame.key.stop_text_input()
        self.state = state
        self.music.play(music.SCREEN_TRACKS.get(state))

    def handle_key(self, key):
        if key == pygame.K_ESCAPE:
            self.running = False
        elif key == pygame.K_F11:
            pygame.display.toggle_fullscreen()
        elif key == pygame.K_m and self.state != "name":  # 이름 입력 중에는 글자로 쓰인다
            self.music.set_muted(self.sfx.toggle_mute())  # 효과음과 음악을 함께 켜고 끈다
        elif self.state == "sensor":
            rows = len(self.sensor_ports) + 1  # 마지막 줄은 키보드 모드
            if key in (pygame.K_UP, pygame.K_LEFT):
                self.sensor_sel = (self.sensor_sel - 1) % rows
                self.sfx.play("select")
            elif key in (pygame.K_DOWN, pygame.K_RIGHT):
                self.sensor_sel = (self.sensor_sel + 1) % rows
                self.sfx.play("select")
            elif key == pygame.K_r:
                self._rescan_sensors()
            elif key == pygame.K_RETURN:
                if self.sensor_sel < len(self.sensor_ports):
                    self.use_port(self.sensor_ports[self.sensor_sel].device)
                else:
                    self.use_keyboard()
                self.sfx.play("confirm")
                self.go("title")
        elif self.state == "title" and key == pygame.K_s:
            self._rescan_sensors()
            self.go("sensor")
        elif self.state == "title" and key == pygame.K_RETURN:
            self.sfx.play("confirm")
            self.go("howto")
        elif self.state == "howto" and key == pygame.K_RETURN:
            self.sfx.play("confirm")
            self.go("name")
        elif self.state == "name":
            if self.composing:  # 조합 중인 키는 입력기가 처리한다
                return
            if key == pygame.K_BACKSPACE:
                self.name = self.name[:-1]
            elif key == pygame.K_RETURN and self.name.strip():
                self.name = self.name.strip()
                self.sfx.play("confirm")
                self.go("difficulty")
        elif self.state == "difficulty":
            keys = list(config.DIFFICULTIES)
            if key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
                step = -1 if key in (pygame.K_LEFT, pygame.K_UP) else 1
                self.set_difficulty(keys[(keys.index(self.difficulty) + step) % len(keys)])
                self.sfx.play("select")
            elif key == pygame.K_RETURN:
                self.sfx.play("confirm")
                self.go("select")
        elif self.debug and self.state == "play" and key in (pygame.K_1, pygame.K_2, pygame.K_3):
            n = len(config.BOSS_PHASES)  # 보스 체력을 해당 페이즈가 시작하는 지점으로
            self.battle.boss.hp = config.BOSS_MAX_HP * (n - (key - pygame.K_1)) // n
        elif self.state == "select":
            n = self.assets.hero_count
            if key == pygame.K_LEFT:
                self.hero = (self.hero - 1) % n
                self.sfx.play("select")
            elif key == pygame.K_RIGHT:
                self.hero = (self.hero + 1) % n
                self.sfx.play("select")
            elif key == pygame.K_RETURN:
                self.sfx.play("confirm")
                self.start_calibration()
        elif self.state == "result":
            if key == pygame.K_RETURN and self.debug:
                self.battle = game.Battle(difficulty=self.difficulty)
                self.go("play")
            elif key == pygame.K_RETURN:  # 다음 사람을 위해 처음 화면으로
                self.name = ""
                self.rank = None
                self.sfx.play("confirm")
                self.go("title")

    def on_text(self, text: str):
        if self.state != "name":
            return
        for ch in text:
            if ch.isprintable() and len(self.name) < NAME_MAX:
                self.name += ch
                self.sfx.play("type")

    def set_difficulty(self, difficulty: str):
        """난이도를 바꾸면 오른쪽 리더보드도 그 난이도의 기록으로 바뀐다."""
        self._boards[self.difficulty] = self.entries
        self.difficulty = difficulty
        self.entries = self._boards[difficulty]

    def start_calibration(self):
        """안내 화면 없이 바로 카운트다운부터 시작한다."""
        self.go("calib")
        self.measure = measure.Measurement(started=True)

    def fake_target(self, keys) -> float:
        if self.state == "calib":
            return 1.0 if keys[pygame.K_SPACE] else 0.0
        if keys[pygame.K_LEFT]:
            return 0.0
        if keys[pygame.K_RIGHT]:
            return 1.0
        return 0.5

    # ---- 갱신 ----
    def update(self, dt, keys):
        if self.state == "sensor":  # 센서를 꽂는 걸 바로 알아보도록 주기적으로 다시 찾는다
            self._scan_t += dt
            if self._scan_t >= 1.0:
                self._scan_t = 0.0
                self._rescan_sensors()
        if self.fake:
            step = FAKE_RAMP * dt
            target = self.fake_target(keys)
            self.fake_force += max(-step, min(step, target - self.fake_force))
            self.source.set_force(self.fake_force)
        samples = self.source.read()
        self.est.update(samples)

        if self.state == "calib":
            self.update_calibration(dt, len(samples))
        elif self.state == "howto":
            self.demo.update(dt)
        elif self.state == "play":
            move = emg.direction(self.est.force) if self.source.connected else 0
            self.battle.update(dt, move)
            for event in self.battle.events:
                self.sfx.play(event)
            self.battle.events.clear()
            if self.battle.state != game.PLAYING:
                self.finish_battle()

    def start_debug(self, hero: int):
        self.name = "DEV"
        self.hero = max(0, min(self.assets.hero_count - 1, hero))
        if self.fake:  # 키보드 모드는 측정을 건너뛰고 가짜 센서 값에 맞춘다
            self.est.calibrate(self.source.base_noise, self.source.base_noise + self.source.scale)  # 가짜 센서가 낼 수 있는 진폭 범위
            self.battle = game.Battle(difficulty=self.difficulty)
            self.go("play")
        else:  # 센서가 있으면 측정은 그대로 한다
            self.start_calibration()

    def finish_battle(self):
        if not self.debug:  # 이긴 판은 클리어 시간, 진 판은 버틴 시간으로 기록한다
            self.entries, self.rank = leaderboard.add(
                self.entries, self.name, self.battle.time, self.battle.player.lives, self.battle.state == game.WON
            )
            leaderboard.save(self.entries, difficulty=self.difficulty)
        self.go("result")

    def update_calibration(self, dt, n_samples):
        m = self.measure
        m.update(dt, n_samples, self.est.envelope)
        tick = math.ceil(m.countdown_left) if m.phase == measure.COUNTDOWN else 0
        if tick and tick != self._last_tick:
            self.sfx.play("tick")
        self._last_tick = tick
        if m.done:
            self.sfx.play("measure_done")
            self.est.calibrate(m.lo, m.hi)
            self.battle = game.Battle(difficulty=self.difficulty)
            self.go("play")

    # ---- 그리기 ----
    def draw(self):
        self.screen.fill(theme.current()["screen_bg"])
        if self.state in ("play", "result"):
            self.draw_arena(self.arena, self.battle, self.hero, self.est.force, self.source.connected)
            self.screen.blit(self.arena, (0, 0))
            self.draw_leaderboard()
            if self.state == "result":
                self.draw_result()
        else:
            if theme.current()["bubbles"] and not (self.state == "title" and self.assets.title_bg):
                draw_bubbles(self.screen, self.screen_bubbles, pygame.time.get_ticks() / 1000)
            getattr(self, f"draw_{self.state}")()
        pygame.display.flip()

    def draw_sensor(self):
        cx = WIN_W // 2
        draw_text(self.screen, "센서를 선택해주세요", self.f_title, (240, 240, 245), (cx, 100), "center")
        has_sensor = bool(self.sensor_ports)
        msg = "목록에서 센서를 고르세요" if has_sensor else "연결된 센서가 없어요. USB로 연결하면 여기에 나타나요"
        draw_text(self.screen, msg, self.f_body, (190, 210, 230) if has_sensor else (255, 190, 110), (cx, 160), "center")
        rows = [(p.label, p.likely) for p in self.sensor_ports] + [("키보드 모드 (센서 없이)", False)]
        for i, (label, likely) in enumerate(rows):
            box = pygame.Rect(0, 0, 640, 56)
            box.center = (cx, 250 + i * 70)
            on = i == self.sensor_sel
            pygame.draw.rect(self.screen, (60, 56, 40) if on else (30, 38, 58), box, border_radius=12)
            pygame.draw.rect(self.screen, (255, 200, 90) if on else (60, 78, 104), box, 3 if on else 2, border_radius=12)
            font = self._fit_font(label, 520)
            draw_text(self.screen, label, font, (255, 255, 255) if on else (215, 225, 240), (box.left + 22, box.centery), "midleft")
            if likely:
                draw_text(self.screen, "추천", self.f_small, (120, 230, 150), (box.right - 22, box.centery), "midright")
        draw_text(self.screen, "↑ ↓ 로 고르고 Enter   ·   R: 다시 찾기", self.f_small, (150, 170, 190), (cx, WIN_H - 60), "center")

    def draw_title(self):
        cx = WIN_W // 2
        t = pygame.time.get_ticks() / 1000
        a = self.assets
        if a.title_bg:
            self.screen.blit(a.title_bg, (0, 0))
        if a.title_boss:
            self.screen.blit(a.title_boss, a.title_boss.get_rect(center=(cx, 175 + int(math.sin(t * 1.2) * 4))))
        # 제목은 배경 위에서 읽히도록 검은 그림자를 깐다. 글자 사이도 조금 벌린다
        for text, font, y, color, gap in (
            (GAME_TITLE, self.f_logo, 425, (255, 255, 255), TITLE_SPACING),
            (BOOTH, self.f_big, 495, (190, 225, 255), BOOTH_SPACING),
        ):
            for dx, dy in ((-3, 3), (3, 3), (0, 4)):
                draw_spaced(self.screen, text, font, (0, 10, 30), (cx + dx, y + dy), gap)
            draw_spaced(self.screen, text, font, color, (cx, y), gap)
        # 만든 사람 표기는 눈에 안 띄게 작고 어둡게
        draw_spaced(self.screen, CREDIT, self.f_tiny, (120, 160, 210), (cx, 538), 2)
        # 화면 모드와 센서 설정 안내 (게임 설명 전에 한 번 더 바꿀 수 있게)
        draw_text(self.screen, "F11: 전체 화면 / 창 모드", self.f_small, (120, 160, 210), (WIN_W - 14, 12), "topright")
        draw_text(self.screen, f"S: 센서 설정 ({self.sensor_label})", self.f_small, (120, 160, 210), (14, 12), "topleft")
        if int(t / 0.6) % 2 == 0:
            draw_spaced(self.screen, "Enter를 눌러 시작", self.f_body, (255, 200, 90), (cx, 584), 2)
        n = len(self.title_heroes)  # 캐릭터들이 제목 아래에 한 줄로 서서 살짝 들썩인다
        if n:
            step = min(76, (WIN_W - 40) / n)
            for i, img in enumerate(self.title_heroes):
                x = cx + (i - (n - 1) / 2) * step
                bob = int(abs(math.sin(t * 2.4 + i * 0.7)) * 8)
                self.screen.blit(img, img.get_rect(midbottom=(x, WIN_H - 14 - bob)))

    def draw_arm_cards(self, y: int) -> int:
        """힘 세기에 따른 이동을 팔 그림으로 보여준다. 오른쪽 예시 화면의 힘과 같은 칸이 켜진다."""
        zone = emg.direction(self.demo.force)
        cards = [
            (-1, self.assets.arm_relax, "힘 빼기", "왼쪽으로"),
            (0, None, "적당히", "제자리"),
            (1, self.assets.arm_flex, "세게", "오른쪽으로"),
        ]
        w, h, gap = 138, 124, 12
        for i, (z, img, top, bottom) in enumerate(cards):
            card = pygame.Rect(40 + i * (w + gap), y, w, h)
            on = z == zone
            pygame.draw.rect(self.screen, (60, 56, 40) if on else (30, 38, 58), card, border_radius=12)
            pygame.draw.rect(self.screen, (255, 200, 90) if on else (60, 78, 104), card, 3 if on else 2, border_radius=12)
            if img:
                self.screen.blit(img, img.get_rect(center=(card.centerx, card.top + 40)))
            else:  # 팔 그림이 없는 "적당히"는 정지 표시
                pygame.draw.rect(self.screen, (225, 232, 240), (card.centerx - 18, card.top + 22, 36, 36), border_radius=4)
            color = (255, 215, 90) if on else (225, 232, 240)
            draw_text(self.screen, top, self.f_small, color, (card.centerx, card.top + 82), "center")
            draw_text(self.screen, bottom, self.f_small, color, (card.centerx, card.top + 102), "center")
        return y + h

    def draw_howto(self):
        draw_text(self.screen, "How to Play", self.f_title, (240, 240, 245), (40, 36))
        y = 110
        for i, (head, body) in enumerate(HOW_TO_PLAY, 1):
            draw_text(self.screen, f"{i}. {head}", self.f_big, (255, 200, 90), (40, y))
            y += 40
            for line in wrap(body, self.f_body, 450):
                draw_text(self.screen, line, self.f_body, (225, 232, 240), (40, y))
                y += 28
            y += 14
            if i == 1:
                y = self.draw_arm_cards(y - 4) + 14
        scale = 0.7
        size = (int(config.ARENA_W * scale), int(config.ARENA_H * scale))
        pos = (WIN_W - size[0] - 24, 96)
        self.draw_arena(self.demo_arena, self.demo.battle, self.hero, self.demo.force, True)
        self.screen.blit(pygame.transform.smoothscale(self.demo_arena, size), pos)
        pygame.draw.rect(self.screen, theme.current()["line"], (*pos, *size), 2)
        draw_text(self.screen, "게임 화면 예시", self.f_small, (160, 180, 200), (pos[0] + size[0] // 2, pos[1] + size[1] + 18), "center")
        draw_text(self.screen, "Enter: 다음", self.f_body, (255, 200, 90), (WIN_W - 24, WIN_H - 40), "bottomright")

    def draw_name(self):
        cx = WIN_W // 2
        draw_text(self.screen, "이름을 입력해주세요", self.f_title, (240, 240, 245), (cx, 190), "center")
        box = pygame.Rect(0, 0, 520, 90)
        box.center = (cx, 330)
        pygame.draw.rect(self.screen, (40, 38, 54), box, border_radius=16)
        pygame.draw.rect(self.screen, (255, 200, 90), box, 3, border_radius=16)
        typed = self.f_title.render(self.name, False, (255, 255, 255))
        comp = self.f_title.render(self.composing, False, (255, 200, 90))
        total = typed.get_width() + comp.get_width()
        x = box.centerx - total // 2
        self.screen.blit(typed, (x, box.centery - typed.get_height() // 2))
        self.screen.blit(comp, (x + typed.get_width(), box.centery - comp.get_height() // 2))
        if comp.get_width():
            pygame.draw.line(self.screen, (255, 200, 90), (x + typed.get_width(), box.centery + 24), (x + total, box.centery + 24), 2)
        if int(pygame.time.get_ticks() / 500) % 2 == 0:
            cur_x = x + total + 4
            pygame.draw.line(self.screen, (240, 240, 245), (cur_x, box.centery - 24), (cur_x, box.centery + 24), 3)
        draw_text(self.screen, f"{len(self.name) + len(self.composing)} / {NAME_MAX}", self.f_small, (160, 160, 180), (box.right - 12, box.bottom + 14), "topright")
        draw_text(self.screen, "Enter로 확인", self.f_body, (160, 160, 180), (cx, 470), "center")

    def _fit_font(self, text: str, width: int):
        """width 안에 들어가는 가장 큰 글꼴. 전부 넘치면 가장 작은 것."""
        fonts = (self.f_body, self.f_small, self.f_tiny)
        return next((f for f in fonts if f.size(text)[0] <= width), fonts[-1])

    def _draw_hearts(self, cx: int, cy: int, n: int) -> None:
        size, gap = 16, 18
        for i in range(n):
            x = cx + int((i - (n - 1) / 2) * gap)
            if self.assets.heart_small:
                self.screen.blit(self.assets.heart_small, self.assets.heart_small.get_rect(center=(x, cy)))
            else:
                draw_heart(self.screen, x, cy, size, (235, 70, 95))

    def _draw_podium_circle(self, rank: int, cx: int, cy: int, r: int, ring: tuple) -> None:
        """1~3위를 동그라미로 보여준다. 1위는 가운데에 크게, 이름과 기록을 안에 적고 왕관을 씌운다."""
        entry = self.entries[rank] if rank < len(self.entries) else None
        mine = entry is not None and rank == self.rank
        pygame.draw.circle(self.screen, (30, 38, 62), (cx, cy), r)
        pygame.draw.circle(self.screen, (255, 215, 90) if mine else ring, (cx, cy), r, 4 if mine else 3)
        if rank:  # 2위, 3위는 동그라미 위에 번호
            draw_text(self.screen, str(rank + 1), self.f_big, ring, (cx, cy - r - 20), "center")
        if entry is None:
            return
        word, word_color = ("성공", (255, 215, 90)) if entry["won"] else ("패배", (210, 90, 70))
        time_text = f"{entry['time']:.1f}초 만에"
        inner = r * 2 - 22
        if rank == 0:
            name_font = self._fit_font(entry["name"], inner)
            draw_text(self.screen, entry["name"], name_font, (255, 255, 255), (cx, cy - 36), "center")
            draw_text(self.screen, time_text, self.f_small, (225, 232, 240), (cx, cy - 10), "center")
            draw_text(self.screen, word, self.f_small, word_color, (cx, cy + 12), "center")
            self._draw_hearts(cx, cy + 40, entry["lives"] if entry["won"] else 0)
            # 왕관
            top = cy - r - 4
            pygame.draw.polygon(self.screen, (255, 215, 90), [(cx - 30, top + 4), (cx - 34, top - 28), (cx - 14, top - 12), (cx, top - 36), (cx + 14, top - 12), (cx + 34, top - 28), (cx + 30, top + 4)])
            pygame.draw.polygon(self.screen, (170, 120, 30), [(cx - 30, top + 4), (cx - 34, top - 28), (cx - 14, top - 12), (cx, top - 36), (cx + 14, top - 12), (cx + 34, top - 28), (cx + 30, top + 4)], 2)
        else:
            draw_text(self.screen, f"{entry['time']:.1f}초", self.f_small, (225, 232, 240), (cx, cy - 18), "center")
            draw_text(self.screen, word, self.f_small, word_color, (cx, cy + 2), "center")
            self._draw_hearts(cx, cy + 26, entry["lives"])
            name_font = self._fit_font(entry["name"], 150)
            draw_text(self.screen, entry["name"], name_font, (255, 255, 255), (cx, cy + r + 16), "center")

    def draw_leaderboard(self):
        x0 = config.ARENA_W
        mid = x0 + PANEL_W // 2
        panel = pygame.Rect(x0, 0, PANEL_W, WIN_H)
        pygame.draw.rect(self.screen, theme.current()["screen_bg"], panel)
        pygame.draw.line(self.screen, theme.current()["line"], (x0, 0), (x0, WIN_H), 2)
        draw_text(self.screen, "Leaderboard", self.f_big, (240, 240, 245), (mid, 30), "center")
        label = config.DIFFICULTIES[self.difficulty]["label"]  # 1위 왕관(가운데)을 가리지 않게 왼쪽 빈자리에 알약 모양으로
        color = (255, 200, 90) if self.difficulty == "hard" else (140, 220, 200)
        pill = pygame.Rect(0, 0, 76, 26)
        pill.center = (x0 + 58, 80)
        pygame.draw.rect(self.screen, (30, 38, 58), pill, border_radius=13)
        pygame.draw.rect(self.screen, color, pill, 2, border_radius=13)
        draw_text(self.screen, label, self.f_small, color, pill.center, "center")
        if self.debug:
            draw_text(self.screen, "DEBUG  1/2/3: 페이즈  Enter: 다시", self.f_small, (255, 120, 120), (mid, WIN_H - 14), "center")
        if not self.entries:
            draw_text(self.screen, "아직 기록이 없어요", self.f_body, (120, 140, 160), (mid, 140), "center")
            return
        # 시상대: 2위 - 1위 - 3위
        self._draw_podium_circle(1, x0 + 62, 190, 48, (200, 210, 225))
        self._draw_podium_circle(2, x0 + PANEL_W - 62, 190, 48, (205, 140, 90))
        self._draw_podium_circle(0, mid, 160, 68, (255, 215, 90))
        # 4위부터는 한 줄씩
        for i in range(3, len(self.entries)):
            e = self.entries[i]
            y = 308 + (i - 3) * 23
            mine = i == self.rank
            color = (255, 215, 90) if mine else (225, 232, 240)
            if mine:
                pygame.draw.rect(self.screen, (60, 56, 30), (x0 + 8, y - 3, PANEL_W - 16, 23), border_radius=6)
            draw_text(self.screen, f"{i + 1}", self.f_small, color, (x0 + 32, y), "topright")
            draw_text(self.screen, e["name"], self.f_small, color, (x0 + 44, y))
            word, word_color = ("성공", (255, 215, 90)) if e["won"] else ("패배", (210, 90, 70))
            wx = x0 + PANEL_W - 14
            draw_text(self.screen, word, self.f_small, word_color, (wx, y), "topright")
            wx -= self.f_small.size(word)[0] + 8
            lives = str(e["lives"])  # 남은 하트
            draw_text(self.screen, lives, self.f_small, color, (wx, y), "topright")
            wx -= self.f_small.size(lives)[0] + 3
            heart = self.assets.heart_small
            if heart:
                self.screen.blit(heart, heart.get_rect(midright=(wx, y + 9)))
            else:
                draw_heart(self.screen, wx - 8, y + 9, 16, (235, 70, 95))
            wx -= 22
            draw_text(self.screen, f"{e['time']:.1f}초", self.f_small, color, (wx, y), "topright")

    def draw_arena(self, a, b, hero, force, connected):
        th = theme.current()
        a.blit(self.backdrops[b.boss.phase], (0, 0))
        if th["bubbles"]:
            draw_bubbles(a, self.bubbles, pygame.time.get_ticks() / 1000)
        pygame.draw.line(a, th["line"], (0, config.PLAYER_Y + config.PLAYER_H // 2 + 6), (config.ARENA_W, config.PLAYER_Y + config.PLAYER_H // 2 + 6))

        for w in b.boss.warnings:
            draw_bolt_warning(a, w[0], w[1])
        draw_boss(a, round(b.boss.x), config.BOSS_Y, self.assets)
        for f in b.fires:  # 보스 몸에서 나오는 모습이 보이도록 보스 위에 그린다
            draw_fire(a, f, self.assets)
        for bolt in b.bolts:
            draw_bolt(a, bolt)
        for meteor in b.meteors:
            draw_meteor(a, meteor, pygame.time.get_ticks() / 1000)
        draw_text(a, "보스 체력", self.f_small, (230, 230, 235), (20, 10))
        pygame.draw.rect(a, (60, 30, 35), (20, 34, 300, 22), border_radius=6)
        pygame.draw.rect(a, (220, 60, 60), (20, 34, int(300 * b.boss.hp / config.BOSS_MAX_HP), 22), border_radius=6)
        pygame.draw.rect(a, (230, 230, 235), (20, 34, 300, 22), 2, border_radius=6)
        for i in range(config.MAX_LIVES):
            alive = i < b.player.lives
            img = self.assets.heart if alive else self.assets.heart_empty
            if img:
                a.blit(img, img.get_rect(center=(350 + i * 40, 42)))
            else:
                draw_heart(a, 350 + i * 40, 42, HEART_SIZE, (235, 70, 95) if alive else (70, 55, 70))

        bullet_img = self.assets.bullet_for(hero)
        for bl in b.bullets:
            if bullet_img:
                a.blit(bullet_img, bullet_img.get_rect(center=bl.center))
            else:
                pygame.draw.rect(a, (120, 230, 255), bl, border_radius=3)
        if int(b.player.invuln * 10) % 2 == 0:
            draw_hero(a, b.player.rect, hero, self.assets)
        if b.banner > 0:
            name = theme.current()["phase_names"][b.boss.phase]
            draw_text(a, f"PHASE {b.boss.phase + 1}" + (f" · {name}" if name else ""), self.f_title, (255, 200, 90), (config.ARENA_W // 2, 400), "center")
        self.draw_gauge(a, force, connected)

    def draw_gauge(self, surf, force, connected):
        x, y, w, h = 20, 650, config.ARENA_W - 40, 44
        zone = emg.direction(force)
        edges = [0, emg.LEFT_MAX, emg.RIGHT_MIN, 1.0]
        labels = [("LEFT", -1), ("STAY", 0), ("RIGHT", 1)]
        for i, (name, z) in enumerate(labels):
            seg = pygame.Rect(x + int(w * edges[i]), y, int(w * (edges[i + 1] - edges[i])), h)
            on = connected and zone == z
            pygame.draw.rect(surf, (70, 110, 170) if on else (45, 45, 62), seg)
            pygame.draw.rect(surf, (200, 200, 215), seg, 2)
            draw_text(surf, name, self.f_body, (240, 240, 245), seg.center, "center")
        mx = x + int(w * force)
        pygame.draw.rect(surf, (255, 200, 60), (mx - 3, y - 8, 6, h + 16), border_radius=3)
        draw_text(surf, f"힘 {int(force * 100)}%", self.f_small, (200, 200, 215), (x, y - 28))
        if not connected:
            draw_text(surf, "센서 연결 안 됨", self.f_small, (255, 110, 110), (x + w, y - 28), "topright")

    def draw_calib(self):
        m = self.measure
        cx = WIN_W // 2
        panel = pygame.Rect(0, 0, 700, 300)
        panel.center = (cx, WIN_H // 2)
        pygame.draw.rect(self.screen, (40, 38, 54), panel, border_radius=16)
        pygame.draw.rect(self.screen, (70, 66, 92), panel, 2, border_radius=16)

        if m.phase == measure.INTRO:
            draw_text(self.screen, "근전도 측정", self.f_title, (240, 240, 245), (cx, 90), "center")
            draw_text(self.screen, "Enter를 눌러 시작하세요", self.f_big, (255, 200, 90), (cx, panel.centery - 20), "center")
            draw_text(self.screen, "힘 빼기(최소), 힘 주기(최대) 순서로 자동으로 측정합니다.", self.f_body, (215, 215, 225), (cx, panel.centery + 30), "center")
        else:
            draw_text(self.screen, measure.HUD_TITLES[m.stage], self.f_title, (240, 240, 245), (cx, 90), "center")
            draw_text(self.screen, measure.PANEL_TITLES[m.stage], self.f_big, (255, 255, 255), (cx, panel.top + 45), "center")
            if m.error:
                draw_text(self.screen, m.error, self.f_body, (255, 110, 110), (cx, panel.top + 90), "center")
            if m.phase == measure.COUNTDOWN:
                draw_text(self.screen, str(math.ceil(m.countdown_left)), self.f_huge, (255, 200, 90), (cx, panel.top + 185), "center")
            else:
                bar = pygame.Rect(0, 0, 600, 28)
                bar.center = (cx, panel.top + 160)
                pygame.draw.rect(self.screen, (28, 26, 36), bar, border_radius=14)
                fill = bar.copy()
                fill.width = int(bar.width * m.progress)
                if fill.width > 0:
                    pygame.draw.rect(self.screen, (240, 120, 170), fill, border_radius=14)
                draw_text(self.screen, "측정 중...", self.f_body, (215, 215, 225), (cx, panel.top + 205), "center")
                if m.last_value is not None:
                    draw_text(self.screen, f"현재 {m.last_value:.1f}", self.f_small, (160, 160, 180), (cx, panel.top + 245), "center")

        if self.fake:
            draw_text(self.screen, "[키보드 모드] 최대 측정은 Space를 누르고 있으세요", self.f_small, (140, 140, 160), (cx, WIN_H - 60), "center")
        if not self.source.connected:
            draw_text(self.screen, "센서 연결 안 됨 - 포트를 확인하세요", self.f_body, (255, 110, 110), (cx, WIN_H - 100), "center")

    def draw_difficulty(self):
        cx = WIN_W // 2
        draw_text(self.screen, "난이도를 선택해주세요", self.f_title, (240, 240, 245), (cx, 120), "center")
        for i, (key, d) in enumerate(config.DIFFICULTIES.items()):
            box = pygame.Rect(0, 0, 560, 130)
            box.center = (cx, 280 + i * 160)
            on = key == self.difficulty
            pygame.draw.rect(self.screen, (60, 56, 40) if on else (30, 38, 58), box, border_radius=16)
            pygame.draw.rect(self.screen, (255, 200, 90) if on else (60, 78, 104), box, 4 if on else 2, border_radius=16)
            draw_text(self.screen, d["label"], self.f_title, (255, 255, 255) if on else (190, 205, 225), (cx, box.centery - 22), "center")
            draw_text(self.screen, d["desc"], self.f_small, (200, 210, 225) if on else (140, 155, 180), (cx, box.centery + 30), "center")
        draw_text(self.screen, "기록은 난이도마다 따로 쌓여요", self.f_small, (160, 160, 180), (cx, 590), "center")
        draw_text(self.screen, "↑ ↓ 로 고르고 Enter로 확인", self.f_body, (160, 160, 180), (cx, WIN_H - 70), "center")

    def draw_select(self):
        cx = WIN_W // 2
        n = self.assets.hero_count
        draw_text(self.screen, "캐릭터를 선택해주세요", self.f_title, (240, 240, 245), (cx, 90), "center")

        card = pygame.Rect(0, 0, 520, 420)
        card.center = (cx, 340)
        pygame.draw.rect(self.screen, (40, 38, 54), card, border_radius=18)
        pygame.draw.rect(self.screen, (255, 200, 90), card, 3, border_radius=18)

        hero_c = (cx - 110, card.top + 175)
        big = self.assets.heroes_big[self.hero] if self.hero < len(self.assets.heroes_big) else None
        if big:
            self.screen.blit(big, big.get_rect(center=hero_c))
        else:  # 그림이 없으면 작은 도형을 4배로 키운다
            tmp = pygame.Surface((config.PLAYER_W, config.PLAYER_H + 12), pygame.SRCALPHA)
            draw_hero(tmp, pygame.Rect(0, 8, config.PLAYER_W, config.PLAYER_H), self.hero, self.assets)
            tmp = pygame.transform.scale(tmp, (tmp.get_width() * 4, tmp.get_height() * 4))
            self.screen.blit(tmp, tmp.get_rect(center=hero_c))

        bullet_c = (cx + 145, card.top + 175)
        bullet = self.assets.bullet_big_for(self.hero)
        if bullet:
            self.screen.blit(bullet, bullet.get_rect(center=bullet_c))
        else:
            pygame.draw.circle(self.screen, (255, 240, 150), bullet_c, 24)
        draw_text(self.screen, "무기", self.f_small, (160, 160, 180), (bullet_c[0], card.top + 275), "center")

        name = hero_name(self.hero)  # 긴 이름은 한 단계 작은 글자로
        font = next((f for f in (self.f_title, self.f_big, self.f_body) if f.size(name)[0] <= card.width - 40), self.f_body)
        draw_text(self.screen, name, font, (255, 255, 255), (cx, card.bottom - 70), "center")
        draw_text(self.screen, f"{self.hero + 1} / {n}", self.f_small, (160, 160, 180), (cx, card.bottom - 30), "center")

        for sign in (-1, 1):  # 좌우 화살표
            ax, ay = cx + sign * 320, card.centery
            pygame.draw.polygon(self.screen, (255, 200, 90), [(ax - sign * 20, ay - 28), (ax - sign * 20, ay + 28), (ax + sign * 20, ay)])
        for i in range(n):  # 위치 점
            dx = cx + int((i - (n - 1) / 2) * 26)
            on = i == self.hero
            pygame.draw.circle(self.screen, (255, 200, 90) if on else (80, 78, 100), (dx, card.bottom + 36), 7 if on else 5)
        draw_text(self.screen, "← → 로 고르고 Enter로 시작", self.f_body, (160, 160, 180), (cx, WIN_H - 70), "center")

    def draw_result(self):
        won = self.battle.state == game.WON
        shade = pygame.Surface((config.ARENA_W, config.ARENA_H), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 160))
        self.screen.blit(shade, (0, 0))
        cx = config.ARENA_W // 2
        draw_text(self.screen, "승리!" if won else "패배...", self.f_title, (255, 215, 90) if won else (240, 100, 100), (cx, 230), "center")
        if won:
            detail = f"걸린 시간 {self.battle.time:.1f}초 (♥{self.battle.player.lives})"
        else:
            detail = f"{self.battle.time:.1f}초 버텼어요"
        draw_text(self.screen, detail, self.f_body, (230, 230, 235), (cx, 290), "center")
        if self.rank is not None:
            draw_text(self.screen, f"{self.rank + 1}위!", self.f_big, (255, 215, 90), (cx, 345), "center")
        elif not self.debug:
            draw_text(self.screen, "순위권 밖이에요", self.f_body, (200, 200, 215), (cx, 345), "center")
        y = 400
        message = "" if won else hero_defeat_message(self.hero)
        if message:  # 캐릭터가 지고 나서 하는 말
            for line in wrap(f"\"{message}\"", self.f_body, config.ARENA_W - 100):
                draw_text(self.screen, line, self.f_body, (255, 200, 200), (cx, y), "center")
                y += 30
            y += 24
        else:
            y = 430
        for i, line in enumerate(["Enter: 처음 화면으로", "Esc: 종료"]):
            draw_text(self.screen, line, self.f_body, (200, 200, 215), (cx, y + i * 32), "center")

    def selftest(self) -> None:
        """모든 화면을 한 번씩 그려 본다. exe로 묶은 뒤 파일(그림, 글꼴, 소리)이 제대로 들어갔는지 확인할 때 쓴다."""
        self.source.start()  # FakeSource는 start 전에 읽으면 부팅 이후 시간만큼 샘플을 만든다
        for state in ("title", "howto", "name", "difficulty", "select", "calib", "play", "sensor", "result"):
            if state == "result":
                self.battle.state = "lost"
            self.go(state)
            for _ in range(3):
                self.update(1 / 60, pygame.key.get_pressed())
                self.draw()
        assert self.assets.title_bg and self.assets.heroes and self.assets.boss, "assets를 찾지 못했어요"
        assert pygame.font.Font(load_font_path(), 20), "글꼴을 찾지 못했어요"
        self.source.stop()

    def run(self):
        clock = pygame.time.Clock()
        self.source.start()
        self._started = True
        try:
            while self.running:
                dt = min(clock.tick(FPS) / 1000.0, 0.1)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                    elif event.type == pygame.KEYDOWN:
                        self.handle_key(event.key)
                    elif event.type == pygame.TEXTINPUT:
                        self.composing = ""
                        self.on_text(event.text)
                    elif event.type == pygame.TEXTEDITING:
                        self.composing = event.text
                self.update(dt, pygame.key.get_pressed())
                self.draw()
        finally:
            self.source.stop()
            pygame.quit()


def main():
    parser = argparse.ArgumentParser(description="EMG 드래곤 피하기")
    parser.add_argument("--port", help="SpikerBox 시리얼 포트. 없으면 키보드 모드")
    parser.add_argument("--baud", type=int, default=SERIAL_BAUD)
    parser.add_argument("--list-ports", action="store_true")
    parser.add_argument("--keyboard", action="store_true", help="센서를 고르지 않고 키보드 모드로 시작")
    parser.add_argument("--selftest", action="store_true", help="모든 화면을 한 번씩 그려 보고 끝낸다 (exe 점검용)")
    parser.add_argument("--windowed", action="store_true", help="창 모드로 시작 (게임 중에는 F11로 전환)")
    parser.add_argument("--debug", action="store_true", help="개발자용: 바로 게임 플레이 (기록 안 남김, 1/2/3 키로 페이즈 이동)")
    parser.add_argument("--difficulty", choices=list(config.DIFFICULTIES), default=config.DEFAULT_DIFFICULTY, help="--debug에서 쓸 난이도")
    parser.add_argument("--hero", type=int, default=1, help="--debug에서 쓸 캐릭터 번호 (1부터)")
    args = parser.parse_args()

    if args.list_ports:
        print("\n".join(list_ports()) or "연결된 포트가 없습니다")
        return
    if args.windowed:
        config.FULLSCREEN = False
    if args.selftest:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        App(FakeSource()).selftest()
        print("OK: 모든 화면을 그렸어요")
        return
    if args.port:
        source, ask = SerialSource(args.port, args.baud), False
    else:
        source = FakeSource()
        # 명령줄에 센서를 안 줬으면 연결된 센서를 찾아 고르게 한다 (exe로 더블클릭해도 쓸 수 있게)
        ask = not (args.keyboard or args.debug)
    App(source, debug=args.debug, hero=args.hero - 1, ask_sensor=ask, difficulty=args.difficulty).run()


if __name__ == "__main__":
    sys.exit(main())
