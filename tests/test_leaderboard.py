import json

import config
from leaderboard import add, load, save


def test_sorted_by_time_then_lives_and_rank_reported():
    entries, _ = add([], "가", 30.0, 2)
    entries, _ = add(entries, "나", 20.0, 1)
    entries, rank = add(entries, "다", 20.0, 4)
    assert [e["name"] for e in entries] == ["다", "나", "가"]
    assert rank == 0


def test_same_time_and_lives_keeps_earlier_clear_first():
    entries, _ = add([], "먼저", 20.04, 3)
    entries, rank = add(entries, "나중", 20.0, 3)  # 0.1초 단위로 맞추면 같은 시간
    assert [e["name"] for e in entries] == ["먼저", "나중"] and rank == 1


def test_only_top_20_kept():
    entries = []
    for i in range(25):
        entries, _ = add(entries, str(i), 100.0 - i, 3)
    assert len(entries) == config.LEADERBOARD_SIZE
    entries, rank = add(entries, "꼴찌", 999.0, 1)
    assert rank is None and all(e["name"] != "꼴찌" for e in entries)


def test_save_and_load_roundtrip_and_bad_file(tmp_path):
    path = str(tmp_path / "lb.json")
    entries, _ = add([], "이름", 12.3, 4)
    save(entries, path)
    assert load(path) == entries
    (tmp_path / "bad.json").write_text("not json")
    assert load(str(tmp_path / "bad.json")) == []
    assert load(str(tmp_path / "missing.json")) == []
    (tmp_path / "wrong.json").write_text(json.dumps([{"name": "x"}]))
    assert load(str(tmp_path / "wrong.json")) == []


def test_wins_come_first_then_losses_by_longest_survival():
    entries, _ = add([], "진1", 30.0, 0, won=False)
    entries, _ = add(entries, "진2", 50.0, 0, won=False)
    entries, _ = add(entries, "승", 99.0, 1, won=True)  # 느려도 이긴 사람이 위
    entries, rank = add(entries, "진3", 40.0, 0, won=False)
    assert [e["name"] for e in entries] == ["승", "진2", "진3", "진1"]
    assert rank == 2


def test_losses_do_not_push_out_wins_when_full():
    entries = []
    for i in range(config.LEADERBOARD_SIZE):
        entries, _ = add(entries, f"승{i}", 100.0 + i, 3, won=True)
    entries, rank = add(entries, "진", 500.0, 0, won=False)
    assert rank is None and all(e["won"] for e in entries)


def test_old_records_without_won_load_as_wins(tmp_path):
    path = tmp_path / "old.json"
    path.write_text(json.dumps([{"name": "예전", "time": 33.3, "lives": 2}]))
    assert load(str(path))[0]["won"] is True
