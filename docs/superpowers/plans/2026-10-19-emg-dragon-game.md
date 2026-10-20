# EMG 드래곤 피하기 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 근전도(EMG) 센서의 힘 세기로 좌우 이동하며 드래곤 보스의 불을 피하고 총알로 보스 체력을 깎는 pygame 게임을 완성한다.

**Architecture:** `source.py`(센서 원시 샘플)는 그대로 두고, `emg.py`가 샘플을 0~1 힘 세기와 이동 방향으로 바꾼다. `game.py`는 화면 없이 전투 규칙만 계산하고, `main.py`가 pygame 화면·상태 전환·에셋 로딩을 맡는다. 센서가 없을 때는 `FakeSource`를 키보드로 조종한다.

**Tech Stack:** Python 3.12, pygame 2.6, pyserial, pytest, uv

**Spec:** 별도 설계 문서 없음. 2026-10-19 대화에서 합의한 내용과 사용자의 손그림 스케치 2장(화면 구성, 캐릭터 선택)이 기준이며, 아래 Global Constraints에 정리했다.

## Global Constraints

- 근전도 힘 0~20%는 왼쪽 이동, 20~80%는 정지, 80~100%는 오른쪽 이동. 플레이어는 좌우로만 움직인다.
- 플레이어 총알은 자동으로 계속 발사된다. 보스 체력이 0이 되면 승리.
- 보스는 불 투사체를 위에서 아래로 떨어뜨린다. 불에 맞으면 하트가 하나 줄고 2초 동안 무적이며 플레이어가 깜빡인다. 하트 5개를 모두 잃으면 패배.
- 게임 시작 전에 힘 최소(완전히 뺌)와 최대를 재는 측정 단계를 둔다.
- 화면은 왼쪽 "How to Play", 오른쪽 게임 화면으로 나뉘고, 게임 화면 아래에 LEFT / STAY / RIGHT 게이지가 있다. 상단에 보스 체력바와 하트 5개가 있다.
- 시작 전에 "SELECT A PLAYER" 화면에서 용사를 고른다.
- 에셋은 `assets/characters/`(보스, 용사)와 `assets/projectiles/`(불, 총알) 두 폴더로 나눠서 사용자가 올린다. 에셋이 없으면 임시 도형으로 그린다.
- `source.py`는 수정하지 않는다. 센서는 `read()`로 새 샘플 목록을 돌려주는 방식 그대로 쓴다.
- Python >= 3.12, 의존성은 pygame과 pyserial만 쓴다.

## 현재 상태와 열린 결정

`emg.py`, `game.py`, `main.py`, `tests/test_emg.py`, `tests/test_game.py`는 구현돼 있고 테스트 16개가 통과한다. 아직 커밋은 한 번도 없다. 사용자가 정하지 않아서 임시로 둔 값은 다음과 같고, 바꾸려면 아래 태스크와 별개로 요청이 필요하다.

- 불은 날개 폭 안의 랜덤한 위치에서 떨어진다. 정해진 세로줄(레인) 방식은 스케치가 엇갈려서 확정하지 못했다.
- 용사 이름은 "용사 1~5"이다. 스케치의 글씨를 읽지 못했다.
- 결과 화면은 승패 문구와 Enter/C/Esc 안내만 있다.
- 캐릭터 선택은 키보드로만 한다.

## Review Focus

- 센서 연결이 끊긴 채로 플레이: 플레이어가 한쪽으로 흘러가지 않고 멈춘다. (Task 2)
- 시리얼 프레임에 중심값(예: 8000) 편차가 있어도 힘 세기가 0 근처로 나온다. (Task 2)
- 에셋 파일이 깨졌거나 일부만 올라왔을 때 게임이 죽지 않고 그 자리는 임시 도형으로 나온다. (Task 3)
- 창을 끌거나 멈췄다가 돌아와 프레임 간격이 0.1초로 크게 튀어도 총알이 보스를 통과하지 않는다. (Task 4)
- 불 두 개가 같은 프레임에 겹쳐 맞아도 하트는 한 번에 하나만 줄고 0 아래로 내려가지 않는다. (Task 4)

---

### Task 1: 기존 구현 커밋

**Files:**
- Modify: `.gitignore` (필요하면 `.pytest_cache/` 추가)

**Interfaces:**
- Consumes: 없음
- Produces: 이후 태스크가 쌓일 첫 커밋

- [x] **Step 1: `emg.py` 구현** — `direction(force: float) -> int`, `ForceEstimator(window=300, alpha=0.25)`(`update(samples) -> float`, `calibrate(lo, hi)`, `force`), `rest_level`, `max_level`, `calibration_ok`.
- [x] **Step 2: `game.py` 구현** — `Battle(rng=None)`(`update(dt, direction)`, `state`, `lives`, `boss_hp`, `invuln`, `bullets`, `fires`, `player_rect`, `boss_rect`), 상수 `BOSS_MAX_HP=80`, `MAX_LIVES=5`, `INVULN_SECONDS=2.0`.
- [x] **Step 3: `main.py` 구현** — `App(source)`, 상태 `calib → select → play → result`, `Assets`, CLI `--port`, `--list-ports`.
- [x] **Step 4: 테스트 통과 확인**

Run: `uv run pytest -q`
Expected: `16 passed`

- [ ] **Step 5: `.gitignore`에 `.pytest_cache/` 추가 후 커밋**

```bash
git add .gitignore .python-version pyproject.toml uv.lock README.md source.py main.py emg.py game.py tests assets docs
git commit -m "feat: EMG 드래곤 피하기 게임 구현"
```

---

### Task 2: 센서 경로와 연결 끊김 검증

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/test_sensor_path.py`
- Modify: `main.py` (테스트가 실패할 때만)

**Interfaces:**
- Consumes: `SerialSource(port, baud=115200, retry_seconds=2.0, serial_factory=None)`의 `_handle_bytes(chunk: bytes)`와 `read() -> list[float]`, `ForceEstimator`, `App(source)`의 `update(dt, keys)`와 `state`, `battle`, `est`
- Produces: 실제 센서 프레임 형식으로 힘 세기가 계산된다는 보증

- [ ] **Step 1: `tests/conftest.py`** — 모듈 로드 전에 `os.environ.setdefault("SDL_VIDEODRIVER", "dummy")`를 설정한다.
- [ ] **Step 2: 실패하는 테스트 작성** (`tests/test_sensor_path.py`)

```python
def frame(value: int) -> bytes:
    return bytes([0x80 | (value >> 7) & 0x7F, value & 0x7F, 0, 0])

def test_serial_frames_with_dc_offset_drive_force():
    # 중심 8000에서 진폭 5(휴식)와 진폭 300(최대)로 흔들리는 프레임을 SerialSource에 넣고
    # ForceEstimator.calibrate(휴식 envelope, 최대 envelope) 뒤 같은 입력이 force < 0.05 / force > 0.95를 내는지

def test_disconnected_source_does_not_move_player():
    # connected=False인 스텁 소스로 App을 만들고 state="play", est.calibrate(2.0, 100.0)로 맞춘 뒤
    # 1초 update 해도 battle.player_x가 처음 값과 같다 (envelope 0 = 왼쪽 구간이어도 멈춰야 한다)
```

- [ ] **Step 3: 실행해서 실패 여부 확인**

Run: `uv run pytest tests/test_sensor_path.py -v`
Expected: 두 번째 테스트는 현재 `main.py`가 `self.source.connected`를 확인하므로 PASS할 수 있다. 첫 번째가 실패하면 `emg.py`의 `ForceEstimator`를 고친다.

- [ ] **Step 4: 실패한 테스트를 통과시키는 최소 수정**
- [ ] **Step 5: 전체 테스트 확인 후 커밋**

Run: `uv run pytest -q`
Expected: 전부 PASS

```bash
git add tests main.py emg.py
git commit -m "test: 시리얼 프레임 경로와 센서 끊김 동작 검증"
```

---

### Task 3: 에셋 로딩 안정화

**Files:**
- Modify: `main.py` (`load_image`, `Assets.__init__`, `draw_hero`)
- Create: `tests/test_assets.py`

**Interfaces:**
- Consumes: `main.Assets`, `main.load_image`
- Produces: `Assets(asset_dir: str = ASSET_DIR)`. `heroes: list[pygame.Surface | None]`이고 깨진 파일은 `None`으로 남는다. `hero_count`는 `len(heroes)`이고 용사 파일이 없으면 5이다. `load_image`는 파일이 없거나 깨졌을 때 `None`을 돌려준다.

- [ ] **Step 1: 실패하는 테스트 작성** (`tests/test_assets.py`, `tmp_path`에 `characters/`, `projectiles/` 생성)
  - `test_empty_dir_uses_placeholders`: `Assets(str(tmp_path))`의 `boss`, `fire`, `bullet`이 `None`이고 `hero_count == 5`
  - `test_hero_images_set_hero_count`: `pygame.image.save`로 만든 `hero_1.png`, `hero_2.png`가 있으면 `hero_count == 2`이고 `heroes`가 모두 `Surface`
  - `test_corrupt_image_falls_back`: `hero_1.png`에 `b"junk"`를 쓰면 예외 없이 `heroes[0] is None`
- [ ] **Step 2: 실행해서 실패 확인**

Run: `uv run pytest tests/test_assets.py -v`
Expected: FAIL (`Assets`가 `asset_dir`를 받지 않음)

- [ ] **Step 3: 구현** — `Assets.__init__(self, asset_dir: str = ASSET_DIR)`로 바꾸고, `load_image`는 `pygame.error`를 잡아 `None`을 반환한다. 용사는 파일마다 `load_image`를 호출하고 `None`도 목록에 유지한다. 이미지는 `convert_alpha()`가 필요하니 테스트는 `pygame.display.set_mode((1, 1))`을 먼저 호출한다.
- [ ] **Step 4: 통과 확인**

Run: `uv run pytest -q`
Expected: 전부 PASS

- [ ] **Step 5: 커밋**

```bash
git add main.py tests/test_assets.py
git commit -m "fix: 에셋 파일이 없거나 깨져도 임시 도형으로 대체"
```

---

### Task 4: 전투 견고성 테스트 고정

**Files:**
- Modify: `tests/test_game.py`
- Modify: `game.py` (테스트가 실패할 때만)

**Interfaces:**
- Consumes: `Battle.update(dt, direction)`, `Battle._collide()`, `game.INVULN_SECONDS`, `game.MAX_LIVES`
- Produces: 프레임 간격이 커도, 겹친 불에 맞아도 규칙이 유지된다는 보증

- [ ] **Step 1: 테스트 작성** (`tests/test_game.py`에 추가)
  - `test_large_dt_does_not_tunnel_bullet_through_boss`: 보스 몸통 아래 40px에 총알을 두고 `update(0.1, 0)` 후 `boss_hp < BOSS_MAX_HP`
  - `test_two_overlapping_fires_cost_one_life`: 플레이어 위에 불 두 개를 겹쳐 두고 `_collide()` 후 `lives == MAX_LIVES - 1`
  - `test_lives_never_negative`: `lives = 1`에서 같은 상황 후 `lives == 0`이고 `state == LOST`
- [ ] **Step 2: 실행**

Run: `uv run pytest tests/test_game.py -v`
Expected: 현재 구현에서는 PASS(동작 고정). 실패하면 `game.py`를 고친다.

- [ ] **Step 3: 전체 확인 후 커밋**

```bash
git add tests/test_game.py game.py
git commit -m "test: 큰 프레임 간격과 겹친 불 충돌 동작 고정"
```

---

### Task 5: 실제 센서로 조정하고 문서 마무리

**Files:**
- Modify: `emg.py`(`ForceEstimator`의 `window`, `alpha` 기본값), `game.py` 위쪽 상수, `README.md`

**Interfaces:**
- Consumes: `uv run main.py --list-ports`, `uv run main.py --port <포트>`
- Produces: 실제 센서에서 정지·좌·우가 의도대로 나오는 기본값

자동 테스트로 확인할 수 없는 작업이라 직접 실행해서 확인한다.

- [ ] **Step 1: 포트 확인**

Run: `uv run main.py --list-ports`
Expected: SpikerBox 포트가 한 줄로 나온다.

- [ ] **Step 2: 센서 모드로 실행해 측정 화면까지 확인**

Run: `uv run main.py --port <포트>`
Expected: "센서 연결 안 됨"이 뜨지 않고, 힘을 주면 "현재 근전도 세기" 막대가 오른다. 힘을 빼면 내려간다.

- [ ] **Step 3: 측정 후 게임에서 구간 확인** — 완전히 힘 뺌 → 왼쪽으로 이동, 중간 → 정지, 최대 → 오른쪽으로 이동. 반응이 너무 느리거나 떨리면 `ForceEstimator`의 `window`(작을수록 빠름)와 `alpha`(클수록 빠름)를 조정하고 `uv run pytest -q`로 회귀가 없는지 본다.
- [ ] **Step 4: 난이도 확인** — 한 판이 대략 30~60초 안에 끝나는지 본다. 아니면 `BOSS_MAX_HP`, `FIRE_INTERVAL`, `FIRE_SPEED`를 조정한다.
- [ ] **Step 5: `README.md`에 조정한 값과 센서 사용 시 주의점을 한 줄씩 반영하고 커밋**

```bash
git add emg.py game.py README.md
git commit -m "tune: 실제 센서 기준으로 반응 속도와 난이도 조정"
```
