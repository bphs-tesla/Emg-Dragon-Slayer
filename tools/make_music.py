"""배경 멜로디를 만들어 assets/music/ 에 저장한다. 처음부터 끝까지 이어 붙여도 끊기지 않는 반복(루프) 곡이다.

    uv run python tools/make_music.py            # 없는 곡만 만든다 (직접 넣은 파일은 건드리지 않는다)
    uv run python tools/make_music.py --force    # 전부 다시 만든다

title  : 타이틀부터 힘 측정까지, 차분한 분위기
battle : 게임 중, 조금 긴장감 있게

같은 이름(.wav .ogg .mp3)의 파일을 assets/music/에 직접 넣어도 된다.
"""

import argparse
import math
import os
import struct
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_sfx as m  # noqa: E402  소리를 만드는 도구를 같이 쓴다

RATE = m.RATE
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "music")


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


class Track:
    """beat 단위로 음을 올려 두는 악보. 끝을 넘는 소리는 처음으로 돌아가 이어져서 반복할 때 끊기지 않는다."""

    def __init__(self, bpm, bars):
        self.beat = 60.0 / bpm
        self.bars = bars
        self.length = int(RATE * self.beat * 4 * bars)
        self.buf = [0.0] * self.length

    def note(self, beat_pos, midi, beats, volume, decay=2.0, kind="soft"):
        seconds = max(0.03, beats * self.beat)
        if kind == "kick":
            samples = m.soft(hz(midi) * 2.2, hz(midi), seconds, volume, decay)
        else:
            samples = m.soft(hz(midi), hz(midi), seconds, volume, decay)
        start = int(beat_pos * self.beat * RATE)
        for i, v in enumerate(samples):
            self.buf[(start + i) % self.length] += v

    def save(self, path, peak=0.5):
        samples = m.lowpass(self.buf, 7500.0)
        top = max(1e-9, max(abs(s) for s in samples))
        scale = peak / top
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s * scale)) * 32767)) for s in samples))


# 화음(MIDI 음 번호). 마지막 값이 으뜸음이다.
AM, F, C, G, EM, E = (
    (57, 60, 64, 45), (53, 57, 60, 41), (60, 64, 67, 48), (55, 59, 62, 43), (52, 55, 59, 40), (52, 56, 59, 40),
)


def title():
    """느긋한 단조 곡: 깔리는 화음, 흐르는 아르페지오, 느린 멜로디."""
    t = Track(bpm=84, bars=8)
    chords = [AM, F, C, G, AM, F, G, AM]
    for bar, ch in enumerate(chords):
        b0 = bar * 4
        for tone in ch[:3]:  # 길게 깔리는 화음
            t.note(b0, tone, 4.0, 0.07, 0.7)
        t.note(b0, ch[3], 1.6, 0.16, 1.6)  # 낮은 음
        t.note(b0 + 2, ch[3], 1.6, 0.12, 1.6)
        tones = [ch[0], ch[1], ch[2], ch[0] + 12]
        for i, idx in enumerate([0, 1, 2, 3, 2, 1, 2, 1]):  # 여덟 번 흐르는 음
            t.note(b0 + i * 0.5, tones[idx] + 12, 0.9, 0.07, 2.2)
    melody = [
        (0, 0, 76, 1.5), (0, 1.5, 74, 0.5), (0, 2, 72, 1), (0, 3, 69, 1),
        (1, 0, 72, 2), (1, 2, 69, 1), (1, 3, 67, 1),
        (2, 0, 76, 1.5), (2, 1.5, 79, 0.5), (2, 2, 76, 1), (2, 3, 72, 1),
        (3, 0, 74, 3), (3, 3, 72, 1),
        (4, 0, 69, 1), (4, 1, 72, 1), (4, 2, 76, 2),
        (5, 0, 77, 1.5), (5, 1.5, 76, 0.5), (5, 2, 72, 2),
        (6, 0, 74, 1), (6, 1, 79, 1), (6, 2, 76, 1), (6, 3, 74, 1),
        (7, 0, 69, 4),
    ]
    for bar, pos, midi, beats in melody:
        t.note(bar * 4 + pos, midi, beats * 0.95, 0.15, 1.1)
    return t


def battle():
    """빠른 박자의 단조 곡: 달리는 낮은 음, 부드러운 쿵쿵, 반짝이는 아르페지오, 또렷한 멜로디."""
    t = Track(bpm=132, bars=8)
    chords = [AM, AM, F, G, AM, F, G, E]
    for bar, ch in enumerate(chords):
        b0 = bar * 4
        root = ch[3] + 0  # 으뜸음 (낮은 음)
        for i, off in enumerate([0, 0, 12, 0, 0, 0, 12, 0]):  # 달리는 낮은 음
            t.note(b0 + i * 0.5, root + off, 0.45, 0.14, 2.5)
        for beat in range(4):  # 부드러운 쿵
            t.note(b0 + beat, 38, 0.3, 0.22, 4.0, kind="kick")
        tones = [ch[0], ch[1], ch[2], ch[0] + 12, ch[1] + 12]
        for i, idx in enumerate([0, 1, 2, 3, 4, 3, 2, 1, 0, 1, 2, 3, 4, 3, 2, 4]):  # 열여섯 번 반짝이는 음
            t.note(b0 + i * 0.25, tones[idx] + 12, 0.45, 0.045, 3.0)
    melody = [
        (0, 0, 81, 0.75), (0, 0.75, 79, 0.75), (0, 1.5, 76, 0.5), (0, 2, 79, 2),
        (1, 0, 81, 0.75), (1, 0.75, 79, 0.75), (1, 1.5, 76, 0.5), (1, 2, 79, 2),
        (2, 0, 77, 0.75), (2, 0.75, 76, 0.75), (2, 1.5, 72, 0.5), (2, 2, 77, 2),
        (3, 0, 79, 0.75), (3, 0.75, 74, 0.75), (3, 1.5, 71, 0.5), (3, 2, 79, 2),
        (4, 0, 81, 0.75), (4, 0.75, 84, 0.75), (4, 1.5, 83, 0.5), (4, 2, 81, 2),
        (5, 0, 77, 0.75), (5, 0.75, 81, 0.75), (5, 1.5, 79, 0.5), (5, 2, 77, 2),
        (6, 0, 79, 0.75), (6, 0.75, 83, 0.75), (6, 1.5, 81, 0.5), (6, 2, 79, 2),
        (7, 0, 76, 1), (7, 1, 80, 1), (7, 2, 83, 2),
    ]
    for bar, pos, midi, beats in melody:
        t.note(bar * 4 + pos, midi, beats * 0.95, 0.12, 1.0)
    return t


TRACKS = {"title": title, "battle": battle}


def main():
    parser = argparse.ArgumentParser(description="배경 멜로디 만들기")
    parser.add_argument("--force", action="store_true", help="이미 있는 곡도 다시 만든다")
    args = parser.parse_args()
    os.makedirs(OUT, exist_ok=True)
    for name, make in TRACKS.items():
        existing = [f for f in os.listdir(OUT) if f.rsplit(".", 1)[0] == name and f.endswith((".wav", ".ogg", ".mp3"))]
        if existing and not args.force:
            print(f"건너뜀 {name} (이미 {existing[0]} 있음)")
            continue
        track = make()
        track.save(os.path.join(OUT, f"{name}.wav"))
        print(f"만듦 {name}.wav ({track.length / RATE:.1f}초)")


if __name__ == "__main__":
    main()
