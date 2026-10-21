# EMG 드래곤 피하기

근육 힘으로 조종하는 pygame 슈팅 게임. 드래곤이 떨어뜨리는 불을 피하며 총알로 체력을 깎으면 승리.

## 실행

```
uv run main.py                 # 센서 없이 키보드 모드
uv run main.py --list-ports    # 센서 포트 찾기
uv run main.py --port <포트>   # SpikerBox 연결
uv run main.py --windowed      # 창 모드로 시작 (F11로 전환)
uv run main.py --debug         # 개발자용: 바로 게임 플레이 (--hero N으로 캐릭터, --difficulty easy|hard로 난이도)
uv run pytest                  # 테스트
```

## 화면 순서

타이틀(배경 이미지 `assets/ui/title_bg.jpg`) → How to Play(팔 그림과 자동 플레이 예시) → 이름 입력 → 캐릭터 선택 → 힘 최소/최대 측정 → 게임 → 결과 → 타이틀.

- 게임 화면 오른쪽에 리더보드가 있다. 이긴 사람이 먼저(클리어 시간이 짧은 순, 같으면 남은 목숨이 많은 순), 진 사람은 그 뒤에 오래 버틴 순으로 20명까지 남고 `leaderboard.json`에 저장된다. 쉬움과 어려움 기록은 따로 쌓인다.
- 이름을 넣은 뒤 난이도(쉬움/어려움)를 고른다. 어려움이 원래 패턴이고, 쉬움은 `config.py`의 `EASY_PHASES`와 `DIFFICULTIES`로 조절한다.
- 모든 화면에서 `Enter`로 다음으로, `Esc`로 종료한다. 전체 화면으로 시작하고 `F11`로 창 모드와 오갈 수 있다. 창 모드로 시작하려면 `--windowed`(또는 `config.py`의 `FULLSCREEN = False`)를 쓴다. 창 모드에서는 창 크기를 마우스로 바꿀 수 있고 화면 비율은 유지된다.

## 센서 고르기

명령줄 없이 실행해도(예: exe 더블클릭) 연결된 센서를 찾아 쓴다.

- 지난번에 쓴 포트가 꽂혀 있으면 물어보지 않고 바로 연결한다. (`settings.json`에 저장된다)
- SpikerBox로 보이는 USB 포트가 딱 하나면 바로 연결한다.
- 센서가 없거나 후보가 여러 개면 시작할 때 "센서를 선택해주세요" 화면이 나온다. `↑` `↓`로 고르고 `Enter`, `R`은 다시 찾기. 마지막 줄은 키보드 모드다. 이 화면에서 센서를 꽂아도 목록이 저절로 갱신된다.
- 타이틀 화면에서 `S`를 누르면 언제든 다시 고를 수 있다. 왼쪽 위에 지금 연결된 센서가 보인다.
- `--port COM3`으로 직접 지정하거나 `--keyboard`로 키보드 모드로 바로 시작할 수도 있다.

## exe로 만들기

맥에서는 Windows용 exe를 만들 수 없다. Windows 컴퓨터에서 `build_exe.bat`을 실행하면(uv가 설치돼 있어야 한다) `dist\EMG-Dragon-Slayer\EMG-Dragon-Slayer.exe`가 만들어진다. 이 폴더를 통째로 옮겨서 쓴다. Windows 컴퓨터가 없으면 GitHub에 올리고 Actions 탭에서 `build-windows`를 실행해 만들어진 파일을 내려받는다(`.github/workflows/build-windows.yml`).

**자동 릴리즈:** `v`로 시작하는 태그를 올리면 Windows에서 exe를 만들고, 점검(`--selftest`)이 통과하면 GitHub Releases에 `EMG-Dragon-Slayer-v1.0.0-windows.zip`으로 자동 게시한다. 변경 내용은 자동으로 정리된다.

```
git tag v1.0.0
git push origin v1.0.0
```

- `uv run pyinstaller --noconfirm --clean EMG-Dragon-Slayer.spec` : 폴더 모양(기본, 켜질 때 빠름). 파일 하나짜리는 `ONEFILE=1`을 붙이면 되지만 켤 때마다 압축을 풀어서 느리다.
- 점검: `EMG-Dragon-Slayer.exe --selftest`가 모든 화면을 한 번씩 그려 보고 끝난다(그림, 글꼴, 소리가 제대로 들어갔는지 확인). 실패하면 종료 코드가 0이 아니다.
- 기록(`leaderboard.json`)과 센서 설정(`settings.json`)은 exe 파일 옆에 저장된다. 그 폴더에 쓸 수 없으면 사용자 폴더(`.emg-dragon-slayer`)에 저장한다.
- 캐릭터 이름, 패배 메시지, 난이도 같은 `config.py` 값은 exe 안에 들어가므로 바꾸면 다시 만들어야 한다.

## 디버그 모드

`--debug`로 실행하면 타이틀부터 캐릭터 선택까지 건너뛰고 바로 플레이한다. 리더보드에는 기록이 남지 않는다.

- `1` `2` `3`: 보스 체력을 해당 페이즈가 시작하는 지점으로 바꾼다.
- 결과 화면에서 `Enter`: 바로 새 판 시작.
- 키보드 모드는 힘 측정도 건너뛴다. 센서(`--port`)를 같이 쓰면 힘 측정은 그대로 한다.

## 조작

- 힘 0~20% 왼쪽, 20~80% 정지, 80~100% 오른쪽.
- 키보드 모드: 측정 중 최대는 `Space` 누르기, 게임 중에는 `←` 힘 빼기 / `→` 힘 세게.
- 이름 입력: 최대 8자, `Backspace`로 지우고 `Enter`로 확인.
- 캐릭터 선택: `←` `→` `Enter`. 캐릭터 이름은 `config.py`의 `HERO_NAMES`에 적는다. 비워 두면 "용사 N"으로 나온다. 지는 순간 보여줄 한마디는 `HERO_DEFEAT_MESSAGES`에 같은 순서로 적고, `""`이면 아무것도 안 나온다.

## 효과음

`assets/sfx/`에 아래 이름의 파일(`.wav` `.ogg` `.mp3`)을 넣으면 그 순간에 재생된다. 파일이 없는 이벤트는 조용히 넘어간다. `shoot_2.wav`처럼 `이름_뒤에붙이기`로 여러 개 넣으면 그중 하나를 무작위로 튼다.

| 파일 이름 | 언제 |
|---|---|
| `shoot` | 플레이어 총알이 나갈 때 |
| `fire` | 보스가 불을 떨어뜨릴 때 |
| `boss_hit` | 총알이 보스에 맞을 때 |
| `player_hit` | 플레이어가 불이나 빠른 총알에 맞을 때 |
| `phase` | 보스 페이즈가 넘어갈 때 |
| `meteor` | 운석이 나타날 때 |
| `bolt_warn` | 빠른 총알 경고선이 나올 때 |
| `bolt` | 빠른 총알이 발사될 때 |
| `win` | 이겼을 때 |
| `lose` | 졌을 때 |
| `confirm` | Enter로 다음 화면으로 넘어갈 때 |
| `select` | 캐릭터 선택에서 ← → 를 누를 때 |
| `type` | 이름을 입력할 때 |
| `tick` | 측정 카운트다운 3, 2, 1 |
| `measure_done` | 힘 측정이 끝났을 때 |

부드러운 기본 효과음은 `uv run python tools/make_sfx.py`로 만든다(이미 있는 파일은 건드리지 않고, `--force`를 주면 전부 다시 만든다). 직접 만든 파일을 같은 이름으로 넣으면 그게 쓰인다.

`M` 키로 소리를 끄고 켠다(이름 입력 중에는 글자로 쓰인다). 전체/이벤트별 음량과 기본 켜짐 여부는 `config.py`의 `SFX_VOLUME`, `SFX_VOLUMES`, `SFX_ENABLED`에서 바꾼다.

## 배경 멜로디

`assets/music/`의 `title`(타이틀~힘 측정, 차분함)과 `battle`(게임 중, 긴장감) 파일(`.wav` `.ogg` `.mp3`)이 화면에 맞춰 반복 재생된다. 결과 화면에서는 멈추고 이기고 진 효과음이 나온다. 기본 곡은 `uv run python tools/make_music.py`로 만든다(`--force`를 주면 전부 다시 만든다). 직접 만든 곡을 같은 이름으로 넣으면 그게 쓰인다. 음량은 `config.py`의 `MUSIC_VOLUME`, `M` 키는 효과음과 음악을 함께 끄고 켠다.

## 에셋 (없으면 임시 도형)

- `assets/boss/boss.png`
- `assets/characters/hero_1.png`, `hero_2.png` ... (개수만큼 선택 화면에 나온다)
- `assets/projectiles/fireball.png`, `assets/projectiles/bullet.png`
- `assets/ui/heart.png`, `assets/ui/heart_empty.png` (없으면 heart.png를 어둡게 사용)

밸런스 값(보스 체력, 불 속도 등)은 `game.py` 위쪽 상수에서 바꾼다.
