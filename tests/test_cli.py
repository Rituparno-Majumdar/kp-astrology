"""Tests for the kpastro command-line interface (src/kpastro/cli.py)."""

from datetime import date, time as time_of_day

import pytest

from kpastro.chart import BirthInfo
from kpastro.cli import (
    __version__,
    build_parser,
    main,
)

# A valid chart run used across happy-path tests.
COMMON = ["--date", "1990-01-15", "--time", "14:30", "--tz", "5.5",
          "--lat", "28.6139", "--lon", "77.2090", "--place", "New Delhi"]


def _run(capsys, *argv: str) -> str:
    """Run the CLI; asserts success (numeric code) and returns captured stdout."""
    assert main(list(argv)) == 0
    captured = capsys.readouterr()
    return captured.out


def _run_error(*argv: str) -> int:
    """Run the CLI expecting a SystemExit; returns its code."""
    with pytest.raises(SystemExit) as exc:
        main(list(argv))
    return exc.value.code


class TestVersionAndParser:
    def test_version_flag(self, capsys):
        code = _run_error("--version")
        assert code == 0

    def test_no_subcommand_is_an_error(self):
        assert _run_error() == 2

    def test_parser_has_all_documented_subcommands(self):
        parser = build_parser()
        sub = parser._subparsers._group_actions[0].choices
        for name in ("natal", "horary", "dasha", "rulings", "ayanamsa", "download-ephemeris"):
            assert name in sub


class TestHappyPaths:
    def test_natal_exits_zero_and_prints_chart(self, capsys):
        out = _run(capsys, "natal", *COMMON)
        assert "KRISHNAMURTI PADDHATI" in out
        assert "PLANETS" in out and "VIMSHOTTARI DASHA" in out

    def test_horary_exits_zero(self, capsys):
        out = _run(capsys, "horary", "--number", "45", *COMMON)
        assert "KP number : 45" in out
        assert "Ascendant" in out

    def test_dasha_exits_zero(self, capsys):
        out = _run(capsys, "dasha", *COMMON)
        assert "Mahadashas" in out

    def test_rulings_exits_zero(self, capsys):
        out = _run(capsys, "rulings", *COMMON)
        assert "Ruling planets" in out

    def test_ayanamsa_exits_zero(self, capsys):
        out = _run(capsys, "ayanamsa", "--date", "2026-08-20")
        assert "24" in out            # degrees
        assert "\u00b0" in out

    def test_ayanamsa_modes(self, capsys):
        for mode in ("lahiri", "kp", "kp_old"):
            _run(capsys, "ayanamsa", "--date", "2026-08-20", "--ayanamsa", mode)


class TestInvalidInput:
    def test_bad_date_exits_with_usage(self):
        assert _run_error("ayanamsa", "--date", "2026-13-40") == 2

    def test_bad_horary_number_exits_with_usage(self):
        assert _run_error("horary", "--number", "999", *COMMON) == 2

    def test_missing_required_coords_exit_with_usage(self):
        assert _run_error("natal", "--date", "2026-08-20") == 2

    def test_out_of_range_latitude_exits_with_usage(self):
        assert _run_error("natal", "--date", "2026-08-20", "--lat", "95", "--lon", "77") == 2

    def test_out_of_range_longitude_exits_with_usage(self):
        assert _run_error("natal", "--date", "2026-08-20", "--lat", "28", "--lon", "500") == 2

    def test_out_of_range_timezone_exits_with_usage(self):
        assert _run_error("natal", "--date", "2026-08-20", "--lat", "28", "--lon", "77", "--tz", "30") == 2

    def test_malformed_time_exits_with_usage(self):
        assert _run_error("natal", "--date", "2026-08-20", "--lat", "28", "--lon", "77", "--time", "25:99") == 2


class TestPolarLatitude:
    def test_high_latitude_is_rejected_cleanly(self):
        # Placidus is undefined beyond the polar circles; the CLI must report
        # a usage error rather than a swisseph C traceback.
        assert _run_error("natal", "--date", "2026-08-20", "--lat", "70.0", "--lon", "25.0") == 2

    def test_birthinfo_rejects_polar_latitude(self):
        with pytest.raises(ValueError, match="Placidus"):
            BirthInfo(date(1990, 1, 15), time_of_day(12, 0), 70.0, 25.0)

    def test_birthinfo_validates_coords(self):
        with pytest.raises(ValueError):
            BirthInfo(date(1990, 1, 15), time_of_day(12, 0), 120.0, 0.0)
        with pytest.raises(ValueError):
            BirthInfo(date(1990, 1, 15), time_of_day(12, 0), 0.0, 500.0)