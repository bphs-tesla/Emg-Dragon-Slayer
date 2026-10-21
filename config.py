"""게임 설정값 모음. 난이도·반응 속도·화면 크기는 여기서 바꾼다."""

# ---- 센서 입력 (emg.py) ----
LEFT_MAX = 0.3   # 힘 0~LEFT_MAX: 왼쪽 이동
RIGHT_MIN = 0.7  # 힘 RIGHT_MIN~100%: 오른쪽 이동 (그 사이는 정지)
EMG_WINDOW = 300  # 힘 세기를 계산할 최근 샘플 수. 작을수록 반응이 빠르고 떨림이 늘어난다
EMG_ALPHA = 0.25  # 힘 세기 부드럽게 이어주는 정도. 클수록 빠르게 따라간다
MIN_SAMPLES = 20  # 이만큼 모여야 힘 세기를 계산한다
CALIB_MIN_RATIO = 1.5  # 측정 성공 조건: 최대 진폭이 휴식 진폭의 이 배수 이상
CALIB_MIN_SPAN = 1.0   # 측정 성공 조건: 최대와 휴식 진폭 차이가 이 값 이상
INPUT_GAIN = 1.1  # 입력 증폭. 현재 힘을 측정 기준보다 이만큼 크게 보고 힘 세기를 계산한다 (측정 자체는 그대로)
SERIAL_BAUD = 115200

# ---- 측정 화면 (measure.py, main.py) ----
COUNTDOWN_SECONDS = 3  # 측정 전 카운트다운. 이 동안 들어온 값은 버린다
CALIB_SECONDS = 3.0    # 최소/최대를 각각 재는 시간
WINDOW_SECONDS = 0.2   # 값 하나를 만드는 창 길이. 3초 측정이면 값 15개를 모은다
MAX_TOP_N = 5          # 최대 힘 = 모은 값 중 상위 이만큼의 평균 (잡음이 한 번 튄 값을 막는다)
SIGNAL_LOSS_SECONDS = 0.6  # 이만큼 샘플이 연속으로 없으면 신호 끊김으로 보고 이 단계를 다시 잰다
FAKE_RAMP = 4.0      # 키보드 모드에서 힘이 목표값으로 움직이는 속도(초당)

# ---- 효과음 (sfx.py) ----
SFX_ENABLED = True  # M 키로 켜고 끌 수 있다
SFX_VOLUME = 0.6    # 전체 음량 (0~1)
SFX_VOLUMES = {"shoot": 0.4, "fire": 0.4, "type": 0.5}  # 이벤트별 음량 (0~1). 적지 않은 이벤트는 1.0

# ---- 배경 멜로디 (music.py) ----
MUSIC_ENABLED = True  # M 키로 효과음과 함께 켜고 끌 수 있다
MUSIC_VOLUME = 0.35   # 음악 음량 (0~1). 효과음보다 작게 두는 게 좋다

# ---- 화면 (main.py) ----
FULLSCREEN = True  # 전체 화면으로 시작. F11로 켜고 끌 수 있다. 화면 비율은 유지하고 남는 곳은 검게 둔다
GAME_TITLE = "EMG: Dragon Slayer"
BOOTH = "PSC x TESLA 연합부스"  # 타이틀 화면의 제목 아래 줄
TITLE_SPACING = 6   # 타이틀 제목의 글자 사이 간격(픽셀)
BOOTH_SPACING = 5   # 제목 아래 줄의 글자 사이 간격(픽셀)
CREDIT = "made by 조재민"
NAME_MAX = 8  # 이름 최대 글자 수
LEADERBOARD_SIZE = 20  # 리더보드에 남기는 기록 수
THEME = "deep_sea"  # theme.py의 THEMES 이름. 원래 모습은 "default"
# 캐릭터 선택창에 보이는 이름. hero_1.png부터 차례로 붙고, 모자라는 칸은 "용사 N"으로 나온다.
HERO_NAMES: list[str] = ["먀먀(박미아T)","백설기(박설희T)","짭지찬(박지환)","BBK(변보경T)","'에겐'(이동건)","밤톨(박승호T)","베로니카(정수연T)","이제훈(양진철T)","은혜민주주의공화국(김은혜T)","민주주의(구민주T)","유부남(유태훈T)","물리(신효성T)","포근해(김근해T)"]  # 예: ["하나", "두리", "세나"]
# 캐릭터마다 지는 순간 결과 화면에 보여줄 한마디. HERO_NAMES와 같은 순서로 적고, ""이면 아무것도 안 보여준다.
HERO_DEFEAT_MESSAGES: list[str] = ["이걸 죽니?", "", "PSC 부장이 탄핵되었습니다.", "지금 돌아가신 겁니까?", "테슬라 부장이 탄핵되었습니다.", "어……………..", "", "", "", "민주주의가 죽었습니다. 공산주의가 이겼습니다.", "죽었다.(쇳소리로)", ""]  # 예: ["아쉽다...", "", "다음엔 이긴다!"]
FPS = 60
PANEL_W = 360  # 인게임 오른쪽 리더보드 칸 너비
HEART_SIZE = 32
FIRE_DRAW_W, FIRE_DRAW_H = 38, 56  # 불 그림 크기. 충돌 판정(FIRE_W/H)보다 크게 그려 여유를 준다
BOSS_DRAW_H = 230  # 보스 그림 최대 높이 (폭은 BOSS_WING_W)

# ---- 경기장 (game.py) ----
ARENA_W = 560
ARENA_H = 720

# ---- 플레이어 ----
PLAYER_W, PLAYER_H = 44, 56
PLAYER_Y = 590  # 플레이어 중심 y
PLAYER_SPEED = 260.0  # 초당 픽셀
SHOT_INTERVAL = 0.25  # 총알 발사 간격(초)
BULLET_W, BULLET_H = 36, 36  # 그림 최대 크기이자 충돌 판정 크기
BULLET_SPEED = 560.0
MAX_LIVES = 5
INVULN_SECONDS = 2.0  # 불에 맞은 뒤 무적 시간

# ---- 보스 ----
BOSS_Y = 180  # 상단 가운데에 고정된 보스의 중심 y
BOSS_BODY_W, BOSS_BODY_H = 340, 130  # 총알이 맞는 범위(머리와 양쪽 발톱 안쪽까지)
BOSS_WING_W = 520  # 보스 그림 폭이자 불이 나오는 날개 폭
BOSS_MAX_HP = 120  # 총알 맞는 횟수

# ---- 불 투사체 ----
FIRE_W, FIRE_H = 26, 38
FIRE_HIT_SHRINK = 11  # 불 충돌 판정을 그림보다 작게 (판정 = FIRE_W,H에서 이만큼 뺀 크기)
# 보스 체력을 3등분해 앞에서부터 페이즈 1, 2, 3.
# interval: 불을 떨어뜨리는 주기(초), count: 한 번에 떨어뜨리는 불 개수(위치는 모두 무작위),
# speed: 불이 보스 아래에서 나와 떨어지기 시작할 때의 속도(초당 픽셀). 내려갈수록 FIRE_GRAVITY만큼 빨라진다,
# bolt_interval: 빠른 총알 주기(초), meteor_interval: 운석 주기(초). 0이면 안 쓴다.
BOSS_PHASES = [
    {"interval": 0.7, "speed": 130.0, "count": 1, "bolt_interval": 0.0, "meteor_interval": 0.0},
    {"interval": 0.5, "speed": 150.0, "count": 2, "bolt_interval": 2.2, "meteor_interval": 0.0},
    {"interval": 0.46, "speed": 170.0, "count": 2, "bolt_interval": 1.6, "meteor_interval": 3.5},
]
# 쉬움: 불이 적고 느리고, 빠른 총알은 3페이즈에만, 운석은 없다.
EASY_PHASES = [
    {"interval": 1.0, "speed": 110.0, "count": 1, "bolt_interval": 0.0, "meteor_interval": 0.0},
    {"interval": 0.8, "speed": 120.0, "count": 1, "bolt_interval": 0.0, "meteor_interval": 0.0},
    {"interval": 0.7, "speed": 130.0, "count": 2, "bolt_interval": 3.5, "meteor_interval": 0.0},
]
# 불은 보스 아래에서 나와 중력처럼 서서히 빨라진다. 먼저 나온 불이 더 빨라서 불 사이가 벌어진다.
# 속도 = sqrt(시작 속도² + 2 × FIRE_GRAVITY × 보스 아래에서 내려온 거리). 클수록 빠르게 가속한다.
FIRE_GRAVITY = 80.0
# 난이도. 어려움이 위의 BOSS_PHASES와 FIRE_GRAVITY(원래 패턴), 쉬움은 EASY_PHASES와 아래 gravity를 쓴다.
DIFFICULTIES = {
    "easy": {"label": "쉬움", "desc": "불이 적고 느려요. 운석은 없어요", "phases": EASY_PHASES, "gravity": 60.0},
    "hard": {"label": "어려움", "desc": "불이 많고 빨라요. 운석도 떨어져요", "phases": BOSS_PHASES, "gravity": FIRE_GRAVITY},
}
DEFAULT_DIFFICULTY = "hard"
FIRE_MIN_GAP = 80  # 한 번에 나오는 불끼리 가로로 최소 이만큼 떨어뜨린다
FIRE_SPAWN_JITTER = 110  # 불이 보스 몸 안쪽 이만큼 위에서 제각각 나와 떨어진다 (한 줄로 안 보이게)

# ---- 운석 (3페이즈) ----
METEOR_SIZE = 76          # 그림 지름
METEOR_HIT_SHRINK = 18    # 충돌 판정은 그림보다 이만큼 작다 (둥글어서 모서리가 비는 만큼)
METEOR_START_SPEED = 150.0  # 화면 위에서 나올 때 속도(초당 픽셀)
METEOR_GRAVITY = 70.0     # 내려오면서 빨라지는 정도
METEOR_DRIFT = 45.0       # 옆으로 흐르는 최대 속도. 살짝 비스듬히 떨어진다
METEOR_FIRST_DELAY = 2.0  # 3페이즈가 시작하고 첫 운석까지 기다리는 시간

# ---- 빠른 총알 (2페이즈부터) ----
BOLT_W, BOLT_H = 8, 48  # 충돌 판정. 불보다 훨씬 작다
BOLT_SPEED = 1100.0
BOLT_WARN_SECONDS = 0.9  # 총알이 나가기 전에 수직 경고선을 보여주는 시간
BOLT_AIM_SPREAD = 80  # 경고선이 플레이어 위치에서 좌우로 이만큼까지 벗어난다
PHASE_BANNER_SECONDS = 1.5  # 페이즈가 바뀔 때 "PHASE N"을 보여주는 시간
