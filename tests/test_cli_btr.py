"""Tests for the birth-time rectification CLI (src/kpastro/cli_btr.py)."""

import json
from datetime import date, time as time_of_day
from pathlib import Path

import pytest

from kpastro.cli_btr import (
    build_btr_parser,
    load_events_json,
    main as btr_main,
)
from kpastro.cli import main as kpastro_main

DELHI_ARGS = [
    "--date", "1990-01-15",
    "--time", "14:30",
    "--tz", "5.5",
    "--lat", "28.6139",
    "--lon", "77.2090",
    "--place", "Delhi",
]


@pytest.fixture
def sample_events_file(tmp_path: Path) -> Path:
    data = [
        {"date": "1995-09-03", "primary": 2, "secondary": [], "label": "School admission"},
        {"date": "2007-04-01", "primary": 4, "secondary": [5], "label": "College"},
        {"date": "2013-02-14", "primary": 4, "secondary": [10], "label": "First job"},
        {"date": "2018-01-20", "primary": 7, "secondary": [2, 11], "label": "Marriage"},
    ]
    p = tmp_path / "events.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


@pytest.fixture
def embedded_json_file(tmp_path: Path) -> Path:
    data = {
        "birth": {
            "date": "1990-01-15",
            "time": "14:30",
            "lat": 28.6139,
            "lon": 77.2090,
            "tz": 5.5,
            "place": "Delhi",
        },
        "window_min": 15,
        "step_min": 3,
        "events": [
            {"date": "1995-09-03", "primary": 2, "label": "School admission"},
            {"date": "2007-04-01", "primary_house": 4, "secondary_houses": [5], "label": "College"},
        ],
    }
    p = tmp_path / "embedded.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def _run_btr(capsys, *argv: str) -> str:
    assert btr_main(list(argv)) == 0
    captured = capsys.readouterr()
    return captured.out


def _run_btr_error(*argv: str) -> int:
    with pytest.raises(SystemExit) as exc:
        btr_main(list(argv))
    return exc.value.code


class TestLoadEventsJson:
    def test_load_valid_list(self, sample_events_file: Path):
        events, b_def, s_def = load_events_json(sample_events_file)
        assert len(events) == 4
        assert events[0].date == date(1995, 9, 3)
        assert events[0].primary == 2
        assert events[0].secondary == ()
        assert events[0].label == "School admission"
        assert events[1].secondary == (5,)
        assert events[3].secondary == (2, 11)
        assert b_def == {}
        assert s_def == {}

    def test_load_embedded_object(self, embedded_json_file: Path):
        events, b_def, s_def = load_events_json(embedded_json_file)
        assert len(events) == 2
        assert events[1].primary == 4
        assert events[1].secondary == (5,)
        assert b_def["date"] == "1990-01-15"
        assert b_def["lat"] == 28.6139
        assert s_def["window_min"] == 15
        assert s_def["step_min"] == 3

    def test_secondary_single_int(self, tmp_path: Path):
        p = tmp_path / "single_sec.json"
        p.write_text(json.dumps([{"date": "2000-01-01", "primary": 1, "secondary": 7}]), encoding="utf-8")
        events, _, _ = load_events_json(p)
        assert events[0].secondary == (7,)

    def test_event_optional_time(self, tmp_path: Path):
        p = tmp_path / "timed.json"
        p.write_text(json.dumps([{"date": "2000-01-01", "primary": 1, "time": "15:45"}]), encoding="utf-8")
        events, _, _ = load_events_json(p)
        assert events[0].time == time_of_day(15, 45)

    def test_missing_file_raises(self):
        with pytest.raises(ValueError, match="not found"):
            load_events_json("/nonexistent/path/events.json")

    def test_invalid_json_syntax(self, tmp_path: Path):
        p = tmp_path / "bad.json"
        p.write_text("{not valid json", encoding="utf-8")
        with pytest.raises(ValueError, match="invalid JSON"):
            load_events_json(p)

    def test_empty_events_list_raises(self, tmp_path: Path):
        p = tmp_path / "empty.json"
        p.write_text("[]", encoding="utf-8")
        with pytest.raises(ValueError, match="at least one"):
            load_events_json(p)

    def test_dict_without_events_raises(self, tmp_path: Path):
        p = tmp_path / "no_events.json"
        p.write_text(json.dumps({"some_key": 123}), encoding="utf-8")
        with pytest.raises(ValueError, match="must contain an 'events' list"):
            load_events_json(p)

    def test_invalid_event_structure(self, tmp_path: Path):
        p = tmp_path / "bad_item.json"
        p.write_text(json.dumps(["not a dict"]), encoding="utf-8")
        with pytest.raises(ValueError, match="not a JSON object"):
            load_events_json(p)

    def test_missing_event_date(self, tmp_path: Path):
        p = tmp_path / "no_date.json"
        p.write_text(json.dumps([{"primary": 1}]), encoding="utf-8")
        with pytest.raises(ValueError, match="missing required 'date'"):
            load_events_json(p)

    def test_invalid_event_date_format(self, tmp_path: Path):
        p = tmp_path / "bad_date.json"
        p.write_text(json.dumps([{"date": "03-09-1995", "primary": 1}]), encoding="utf-8")
        with pytest.raises(ValueError, match="invalid date"):
            load_events_json(p)

    def test_missing_primary_house(self, tmp_path: Path):
        p = tmp_path / "no_primary.json"
        p.write_text(json.dumps([{"date": "1995-09-03"}]), encoding="utf-8")
        with pytest.raises(ValueError, match="missing required 'primary'"):
            load_events_json(p)

    def test_invalid_primary_house(self, tmp_path: Path):
        p = tmp_path / "bad_primary.json"
        p.write_text(json.dumps([{"date": "1995-09-03", "primary": 15}]), encoding="utf-8")
        with pytest.raises(ValueError, match="invalid primary house"):
            load_events_json(p)

    def test_invalid_secondary_house(self, tmp_path: Path):
        p = tmp_path / "bad_sec.json"
        p.write_text(json.dumps([{"date": "1995-09-03", "primary": 1, "secondary": ["abc"]}]), encoding="utf-8")
        with pytest.raises(ValueError, match="must be integers"):
            load_events_json(p)


class TestBTRCliHappyPath:
    def test_positional_events_file(self, sample_events_file: Path, capsys):
        out = _run_btr(
            capsys,
            str(sample_events_file),
            *DELHI_ARGS,
            "--window", "15",
            "--step", "3",
        )
        assert "KP BIRTH-TIME RECTIFICATION" in out
        assert "Reference: 1990-01-15 local @ Delhi" in out
        assert "Window +/-15 min, step 3 min" in out
        assert "Best candidate" in out
        assert "Posterior band" in out

    def test_opt_events_flag(self, sample_events_file: Path, capsys):
        out = _run_btr(
            capsys,
            "--events", str(sample_events_file),
            *DELHI_ARGS,
            "--window", "10",
            "--step", "2",
        )
        assert "KP BIRTH-TIME RECTIFICATION" in out
        assert "Best candidate" in out

    def test_embedded_json_auto_config(self, embedded_json_file: Path, capsys):
        out = _run_btr(capsys, str(embedded_json_file))
        assert "KP BIRTH-TIME RECTIFICATION" in out
        assert "Reference: 1990-01-15 local @ Delhi" in out
        assert "Window +/-15 min, step 3 min" in out
        assert "School admission" in out
        assert "College" in out

    def test_ruling_planets_and_identity_options(self, sample_events_file: Path, capsys):
        out = _run_btr(
            capsys,
            str(sample_events_file),
            *DELHI_ARGS,
            "--window", "10",
            "--step", "5",
            "--use-rp",
            "--analysis-time", "2026-08-20 14:30",
            "--siblings", "1",
            "--ayanamsa", "kp",
            "--node", "mean",
            "--limit", "5",
        )
        assert "KP BIRTH-TIME RECTIFICATION" in out
        assert "RP test: yes" in out
        assert "Ayanamsa: kp" in out

    def test_kpastro_btr_subcommand(self, sample_events_file: Path, capsys):
        # Run via `kpastro btr ...`
        assert kpastro_main(["btr", str(sample_events_file), *DELHI_ARGS, "--window", "10", "--step", "5"]) == 0
        captured = capsys.readouterr()
        assert "KP BIRTH-TIME RECTIFICATION" in captured.out


class TestBTRCliErrors:
    def test_missing_events_exits_2(self):
        assert _run_btr_error(*DELHI_ARGS) == 2

    def test_missing_date_exits_2(self, sample_events_file: Path):
        assert _run_btr_error(str(sample_events_file), "--lat", "28.6", "--lon", "77.2") == 2

    def test_missing_coords_exits_2(self, sample_events_file: Path):
        assert _run_btr_error(str(sample_events_file), "--date", "1990-01-15") == 2

    def test_missing_longitude_exits_2(self, sample_events_file: Path):
        assert _run_btr_error(str(sample_events_file), "--date", "1990-01-15", "--lat", "28.6") == 2

    def test_bad_window_exits_2(self, sample_events_file: Path):
        assert _run_btr_error(str(sample_events_file), *DELHI_ARGS, "--window", "not_a_number") == 2


class TestCliBtrEdgeCases:
    def test_parse_datetime_or_time_variants(self):
        from kpastro.cli_btr import _parse_datetime_or_time
        from datetime import datetime
        dt1 = _parse_datetime_or_time("2026-08-20T14:30:00")
        assert isinstance(dt1, datetime)
        assert dt1.hour == 14 and dt1.minute == 30

        dt2 = _parse_datetime_or_time("2026-08-20 15:45")
        assert isinstance(dt2, datetime)
        assert dt2.hour == 15 and dt2.minute == 45

        t = _parse_datetime_or_time("12:34")
        assert isinstance(t, time_of_day)
        assert t.hour == 12 and t.minute == 34

    def test_stdin_input(self, monkeypatch, capsys):
        data = [
            {"date": "1995-09-03", "primary": 2, "label": "Admission"}
        ]
        import io
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(data)))
        out = _run_btr(capsys, "-", *DELHI_ARGS, "--window", "5", "--step", "5")
        assert "KP BIRTH-TIME RECTIFICATION" in out

    def test_secondary_string_number(self, tmp_path: Path):
        p = tmp_path / "str_sec.json"
        p.write_text(json.dumps([{"date": "1995-09-03", "primary": 2, "secondary": "7"}]), encoding="utf-8")
        events, _, _ = load_events_json(p)
        assert events[0].secondary == (7,)

    def test_secondary_invalid_string(self, tmp_path: Path):
        p = tmp_path / "bad_str_sec.json"
        p.write_text(json.dumps([{"date": "1995-09-03", "primary": 2, "secondary": "xyz"}]), encoding="utf-8")
        with pytest.raises(ValueError, match="invalid secondary house"):
            load_events_json(p)

    def test_event_invalid_time_format(self, tmp_path: Path):
        p = tmp_path / "bad_time.json"
        p.write_text(json.dumps([{"date": "1995-09-03", "primary": 2, "time": "not_a_time"}]), encoding="utf-8")
        with pytest.raises(ValueError, match="time must be HH:MM"):
            load_events_json(p)

    def test_secondary_unexpected_type(self, tmp_path: Path):
        p = tmp_path / "dict_sec.json"
        p.write_text(json.dumps([{"date": "1995-09-03", "primary": 2, "secondary": {"house": 3}}]), encoding="utf-8")
        with pytest.raises(ValueError, match="unexpected secondary houses format"):
            load_events_json(p)

    def test_scan_defaults_with_siblings(self, tmp_path: Path, capsys):
        data = {
            "birth": {
                "date": "1990-01-15",
                "time": "14:30",
                "lat": 28.6139,
                "lon": 77.2090,
                "tz": 5.5,
            },
            "siblings": 2,
            "window_min": 5,
            "step_min": 5,
            "events": [
                {"date": "1995-09-03", "primary": 2}
            ],
        }
        p = tmp_path / "siblings.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        out = _run_btr(capsys, str(p))
        assert "KP BIRTH-TIME RECTIFICATION" in out
