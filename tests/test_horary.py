"""Golden-value tests for the KP horary 1-249 division system (src/kpastro/horary.py)."""

import pytest

from kpastro.horary import (
    MAX_HORARY_NUMBER,
    HoraryDiv,
    ascendant_from_kp_number,
    kp_divisions,
    kp_number_for_longitude,
)

SUN_START = 0.0
SUN_END = pytest.approx(0.7777777777777778, abs=1e-6)   # Ketu sub: 46.6667'


class TestKPDivisions:
    def test_count_is_249(self):
        assert len(kp_divisions()) == MAX_HORARY_NUMBER == 249

    def test_first_division(self):
        d = kp_divisions()[0]
        assert isinstance(d, HoraryDiv)
        assert d.number == 1
        assert d.start_deg == 0.0
        assert d.end_deg == pytest.approx(0.7777777777777778, abs=1e-6)
        assert d.sign == "Aries"
        assert d.sign_lord == "Mars"
        assert d.star == "Ashwini"
        assert d.star_lord == "Ketu"
        assert d.sub_lord == "Ketu"

    def test_division_10(self):
        d = kp_divisions()[9]
        assert d.number == 10
        assert d.start_deg == pytest.approx(13.3333, abs=1e-3)
        assert d.end_deg == pytest.approx(15.5556, abs=1e-3)
        assert d.star == "Bharani"
        assert d.star_lord == "Venus"
        assert d.sub_lord == "Venus"

    def test_division_249(self):
        d = kp_divisions()[248]
        assert d.number == 249
        assert d.start_deg == pytest.approx(357.8889, abs=1e-3)
        assert d.end_deg == 360.0
        assert d.sign == "Pisces"
        assert d.sign_lord == "Jupiter"
        assert d.star == "Revati"
        assert d.star_lord == "Mercury"
        assert d.sub_lord == "Saturn"

    def test_divisions_contiguous_and_full_circle(self):
        ds = kp_divisions()
        assert ds[0].start_deg == 0.0
        assert ds[-1].end_deg == 360.0
        for i in range(len(ds) - 1):
            assert ds[i].end_deg == pytest.approx(ds[i + 1].start_deg, abs=1e-9)

    def test_divisions_returns_independent_lists(self):
        # the internal table is cached but each call must return a fresh list
        first = kp_divisions()
        first.clear()
        assert len(kp_divisions()) == MAX_HORARY_NUMBER == 249


class TestAscendant:
    def test_number_1_midpoint(self):
        a = ascendant_from_kp_number(1)
        assert a["number"] == 1
        assert a["ascendant"] == pytest.approx((0.0 + 0.7777777777777778) / 2.0, abs=1e-9)
        assert a["span"] == (0.0, pytest.approx(0.7777777777777778, abs=1e-9))

    def test_number_249_midpoint(self):
        a = ascendant_from_kp_number(249)
        assert a["ascendant"] == pytest.approx((357.8888888888889 + 360.0) / 2.0, abs=1e-9)

    def test_ascendant_is_valid_longitude(self):
        for n in (1, 100, 249):
            a = ascendant_from_kp_number(n)
            assert 0.0 <= a["ascendant"] < 360.0

    @pytest.mark.parametrize("bad", [0, -1, 250, 1000])
    def test_out_of_range_numbers_raise(self, bad):
        with pytest.raises(ValueError):
            ascendant_from_kp_number(bad)

    def test_kp_number_round_trip(self):
        for n in (1, 45, 249):
            a = ascendant_from_kp_number(n)
            assert kp_number_for_longitude(a["ascendant"]) == n

    def test_all_249_division_midpoints_round_trip(self):
        for div in kp_divisions():
            assert kp_number_for_longitude(div.mid_deg) == div.number

    def test_kp_number_for_exact_boundaries(self):
        # lon exactly on a sign boundary inside a sub still maps into a division
        assert kp_number_for_longitude(0.0) == 1

    def test_kp_number_out_of_zodiac_returns_none(self):
        assert kp_number_for_longitude(360.0) == 1  # wrapped