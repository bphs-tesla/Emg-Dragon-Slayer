"""귀에 덜 거슬리는 부드러운 효과음을 만들어 assets/sfx/ 에 저장한다.

    uv run python tools/make_sfx.py            # 없는 파일만 만든다 (직접 넣은 파일은 건드리지 않는다)
    uv run python tools/make_sfx.py --force    # 전부 다시 만든다
    uv run python tools/make_sfx.py --only phase  # 골라서 다시 만든다

소리를 바꾸고 싶으면 아래 SOUNDS의 숫자를 고치거나, 같은 이름의 파일을 assets/sfx/에 직접 넣으면 된다.
"""

import argparse
import math
import os
import random
import re
import struct
import sys
import wave

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sfx  # noqa: E402  이벤트 이름 목록을 함께 쓴다

RATE = 22050
OUT = sfx.SFX_DIR
rng = random.Random(1)


def tone(freq_from, freq_to, seconds, wave_type="square", volume=0.5, decay=3.0):
    """주파수가 freq_from에서 freq_to로 움직이는 소리. decay가 클수록 빨리 작아진다."""
    n = int(RATE * seconds)
    out, phase = [], 0.0
    for i in range(n):
        t = i / n
        freq = freq_from + (freq_to - freq_from) * t
        phase += freq / RATE
        p = phase % 1.0
        if wave_type == "square":
            v = 1.0 if p < 0.5 else -1.0
        elif wave_type == "triangle":
            v = 4 * abs(p - 0.5) - 1
        elif wave_type == "sine":
            v = math.sin(2 * math.pi * p)
        elif wave_type == "saw":
            v = 2 * p - 1
        else:  # noise
            v = rng.uniform(-1, 1)
        attack = min(1.0, i / (RATE * 0.0025))  # 시작할 때 딱 소리가 나지 않게
        out.append(v * volume * attack * math.exp(-decay * t))
    return out


def silence(seconds):
    return [0.0] * int(RATE * seconds)


def mix(*parts):
    n = max(len(p) for p in parts)
    return [sum(p[i] for p in parts if i < len(p)) for i in range(n)]


def seq(*parts):
    out = []
    for p in parts:
        out += p
    return out


def notes(freqs, each, wave_type="square", volume=0.4, decay=2.0):
    return seq(*[tone(f, f, each, wave_type, volume, decay) for f in freqs])


def soft(freq_from, freq_to, seconds, volume=0.4, decay=3.0):
    """부드러운 종소리 같은 소리. 사인파에 2~4배음을 섞어 먹먹하지 않게 한다."""
    out = [0.0] * int(RATE * seconds)
    for mult, share in ((1, 1.0), (2, 0.42), (3, 0.2), (4, 0.08)):  # 배음이 풍부할수록 또렷하다
        part = tone(freq_from * mult, freq_to * mult, seconds, "sine", volume * share, decay)
        out = [a + b for a, b in zip(out, part)]
    return out


def soft_notes(freqs, each, volume=0.35, decay=1.5):
    return seq(*[soft(f, f, each, volume, decay) for f in freqs])


def gong(freq, seconds, volume=0.4, decay=3.0):
    """울림이 긴 징 소리. 배음을 정수배가 아니게 섞어 금속 느낌을 낸다."""
    out = [0.0] * int(RATE * seconds)
    for mult, share in ((1.0, 1.0), (2.76, 0.5), (5.4, 0.25), (8.9, 0.1)):
        part = tone(freq * mult, freq * mult, seconds, "sine", volume * share, decay * (1 + 0.25 * mult))
        out = [a + b for a, b in zip(out, part)]
    return out


def lowpass(samples, cutoff=9500.0):
    """아주 높은 고음(치직거림)만 살짝 깎는다. 너무 낮추면 소리가 먹먹해진다."""
    a = 1 - math.exp(-2 * math.pi * cutoff / RATE)
    out, y = [], 0.0
    for x in samples:
        y += a * (x - y)
        out.append(y)
    return out


C5, E5, G5, C6 = 523, 659, 784, 1047
E6, G6 = 1319, 1568

# 부드러운 종소리 같은 음이 중심이고, 맞는 소리는 노이즈 없이 낮은 "툭" 소리로 했다.
# 자주 나오는 소리(shoot, fire, type)는 더 작고 짧다.
SOUNDS = {
    "shoot": lambda: soft(600, 420, 0.05, 0.22, 4),
    "fire": lambda: soft(260, 160, 0.1, 0.2, 3),
    "boss_hit": lambda: mix(soft(180, 70, 0.1, 0.4, 4), soft(400, 300, 0.06, 0.12, 5)),
    "player_hit": lambda: mix(soft(300, 110, 0.25, 0.45, 3), soft(150, 60, 0.12, 0.25, 6)),
    # 위로 차오르는 소리가 부풀다가 징 소리로 터진다 (보스 페이즈가 바뀌는 순간)
    "phase": lambda: seq(
        mix(soft(220, 880, 0.3, 0.07, -0.7), soft(110, 440, 0.3, 0.045, -0.7)),
        mix(gong(130, 0.9, 0.17, 3.0), soft(260, 260, 0.5, 0.07, 4)),
    ),
    # 낮게 내려앉는 울림 (운석이 위에서 나타남)
    "meteor": lambda: mix(soft(330, 90, 0.4, 0.3, 2.5), soft(165, 60, 0.4, 0.2, 2.5)),
    "bolt_warn": lambda: seq(soft(740, 740, 0.07, 0.25, 2), silence(0.06), soft(740, 740, 0.07, 0.25, 2)),
    "bolt": lambda: soft(1000, 300, 0.08, 0.22, 4),
    "win": lambda: seq(soft_notes([C5, E5, G5], 0.1, 0.3, 1.2), soft(C6, C6, 0.45, 0.3, 2.5)),
    "lose": lambda: seq(soft_notes([440, 349, 294], 0.15, 0.33, 1.2), soft(147, 110, 0.5, 0.33, 2.5)),
    "confirm": lambda: soft(520, 700, 0.07, 0.25, 3),
    "select": lambda: soft(480, 480, 0.035, 0.2, 4),
    "type": lambda: soft(700, 680, 0.02, 0.12, 5),
    "tick": lambda: soft(620, 620, 0.06, 0.26, 3),
    "measure_done": lambda: soft_notes([E5, 988], 0.1, 0.3, 2),
}


def write(path, samples):
    samples = lowpass(samples)
    fade = int(RATE * 0.01)  # 끝에서 뚝 끊기는 소리(딱 소리)가 나지 않게
    for i in range(min(fade, len(samples))):
        samples[-1 - i] *= i / fade
    peak = max(1e-9, max(abs(s) for s in samples))
    scale = min(1.0, 0.8 / peak)  # 크기는 위에서 정한 volume을 따르고, 넘칠 때만 줄인다
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s * scale)) * 32767)) for s in samples))


def main():
    parser = argparse.ArgumentParser(description="8비트 효과음 만들기")
    parser.add_argument("--force", action="store_true", help="이미 있는 파일도 다시 만든다")
    parser.add_argument("--only", nargs="+", metavar="이름", help="이 이름들만 다시 만든다 (예: --only phase)")
    args = parser.parse_args()
    os.makedirs(OUT, exist_ok=True)
    missing = set(sfx.EVENTS) - set(SOUNDS)
    assert not missing, f"만들지 않은 효과음: {missing}"
    for name, make in SOUNDS.items():
        if args.only and name not in args.only:
            continue
        existing = [f for f in os.listdir(OUT) if re.match(rf"^{name}(_\d+)?\.(wav|ogg|mp3)$", f)]
        if existing and not args.force and not args.only:
            print(f"건너뜀 {name} (이미 {existing[0]} 있음)")
            continue
        write(os.path.join(OUT, f"{name}.wav"), make())
        print(f"만듦 {name}.wav")


if __name__ == "__main__":
    main()
