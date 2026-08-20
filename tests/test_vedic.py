"""Golden-value tests for the pure-Python KP subdivision math (src/kpastro/vedic.py)."""

import pytest

from kpastro.vedic import (
    STAR_SPAN_DEG,
    PadaInfo,
    PointInfo,
    SubInfo,
    SubSubInfo,
    format_longitude,
    normalize_longitude,
    pada_info,
    point_info,
    sign_index,
    sign_lord_of_longitude,
    sign_name,
    star_index,
    star_lord,
    star_name,
    star_span,
    sub_info,
    sub_lord,
    sub_span_arcmin,
    sub_sub_info,
    sub_sub_lord,
    sub_divisions,
)

VIMSHOTTARI_ORDER = ("Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury")


class TestSubSpans:
    """Sub widths derive from the Vimshottari years: span = years / 120 * 800'."""

    @pytest.mark.parametrize(
        ("lord", "span"),
        [
            ("Ketu", 46.6667),
            ("Venus", 133.3333),
            ("Sun", 40.0),
            ("Moon", 66.6667),
            ("Mars", 46.6667),
            ("Rahu", 120.0),
            ("Jupiter", 106.6667),
            ("Saturn", 126.6667),
            ("Mercury", 113.3333),
        ],
    )
    def test_sub_span_arcmin(self, lord, span):
        assert sub_span_arcmin(lord) == pytest.approx(span, rel=1e-6)

    def test_spans_fill_an_exact_star(self):
        total = sum(sub_span_arcmin(l) for l in VIMSHOTTARI_ORDER)
        assert total == pytest.approx(800.0, rel=1e-9)


class TestStarLordTable:
    """The 27 nakshatra star-lords cycle through the Vimshottari order 3x.

    The task spec suggested calling ``star_lord(i * 13.3333333333)``, but that
    literal sits fractionally below the STAR_SPAN_DEG boundary (13.333333333333334)
    so it resolves to the *previous* star at every index.  We probe the star
    midpoint instead (guaranteed interior) to test the same lord table.
    """

    EXPECTED = VIMSHOTTARI_ORDER * 3

    def test_all_27_stars(self):
        for i, expected in enumerate(self.EXPECTED):
            mid = i * STAR_SPAN_DEG + STAR_SPAN_DEG / 2.0
            assert star_index(mid) == i
            assert star_lord(mid) == expected

    def test_star_index_boundaries(self):
        assert star_index(0.0) == 0
        assert star_index(STAR_SPAN_DEG - 1e-9) == 0
        assert star_index(STAR_SPAN_DEG) == 1
        assert star_index(26 * STAR_SPAN_DEG) == 26
        assert star_index(360.0) == 0  # wraps


class TestSubInfo:
    def test_zero_longitude_starts_kp_subdivision(self):
        s = sub_info(0.0)
        assert isinstance(s, SubInfo)
        assert s.lord == "Ketu"
        assert s.index == 0
        assert s.start_deg == 0.0
        assert s.end_deg == pytest.approx(0.777777777777778, abs=1e-6)
        assert s.span_arcmin == pytest.approx(46.6667, rel=1e-6)

    def test_three_degrees_on_venus_sun_boundary(self):
        """180' = end of the Venus sub inside Ashwini -> resolves to Sun (start 3.0)."""
        s = sub_info(3.0)
        assert s.lord == "Sun"
        assert s.index == 2
        assert s.start_deg == pytest.approx(3.0, abs=1e-9)
        # the defining consistency invariant: start <= lon < end
        assert s.start_deg <= 3.0 < s.end_deg

    def test_consistency_invariant_across_zodiac(self):
        # note: 80.0 is exactly a sub boundary (end of the Mars sub) so it is
        # deliberately excluded; boundaries are covered by test_three_degrees...
        for lon in (0.5, 1.0, 3.0, 12.0, 30.0, 55.5, 79.5, 80.5, 150.0, 200.5, 359.999):
            s = sub_info(lon)
            assert s.start_deg <= lon < s.end_deg
            assert s.span_arcmin == pytest.approx(sub_span_arcmin(s.lord), rel=1e-12)
            assert s.start_deg < s.end_deg

    def test_sub_lord_shortcut(self):
        assert sub_lord(0.0) == "Ketu"
        # 200.0 is the Swati/Vishakha star boundary -> belongs to Vishakha
        # whose first sub is Jupiter; 200.5 is interior to the same sub.
        assert sub_lord(200.0) == "Jupiter"
        assert sub_lord(200.5) == "Jupiter"


class TestSubSubInfo:
    def test_subsub_contained_in_sub(self):
        for lon in (0.5, 1.0, 3.0, 12.0, 30.0, 200.5, 359.999):
            s = sub_info(lon)
            ss = sub_sub_info(lon)
            assert isinstance(ss, SubSubInfo)
            assert s.start_deg - 1e-9 <= ss.start_deg
            assert ss.end_deg <= s.end_deg + 1e-9
            assert ss.start_deg <= lon < ss.end_deg

    def test_zero_longitude(self):
        # Ketu sub spans 46.667'; at the sub's own start the first sub-sub is
        # Ketu again, but only 46.667 * 7 / 120 = 2.722' wide (the sub-sub is
        # scaled to the SUB's width, not the star's 800').
        ss = sub_sub_info(0.0)
        assert ss.lord == "Ketu"
        assert ss.span_arcmin == pytest.approx(46.666666666666664 * 7 / 120, rel=1e-9)
        assert sub_sub_lord(0.0) == "Ketu"

    def test_subsub_lord_golden_values(self):
        # Golden values inside the Sun sub of Ashwini (3°00' - 3°40'):
        # sub-subs open at the sub-lord (Sun 2'), then Moon 2'-5'20", ...
        assert sub_sub_lord(3.05) == "Moon"   # offset 3'  -> Moon
        assert sub_sub_lord(3.1) == "Mars"    # offset 6'  -> Mars
        assert sub_sub_lord(3.6) == "Venus"   # offset 36' -> Venus (last)
        # Inside the Moon sub (3°40' - 4°46'40"): Moon, Mars, Rahu, Jupiter ...
        assert sub_sub_lord(4.0) == "Jupiter"
        # The sub-sub must genuinely differ from the sub for interior points
        # (this is THE regression test for the sub-sub == sub-sub bug).
        assert sub_sub_lord(4.0) != sub_lord(4.0)
        assert sub_sub_lord(10.0) != sub_lord(10.0)   # Ketu vs Saturn


class TestSignHelpers:
    def test_sign_index_and_names(self):
        assert sign_index(0.0) == 0
        assert sign_index(29.999) == 0
        assert sign_index(30.0) == 1
        assert sign_index(350.0) == 11
        assert sign_name(200.0) == "Libra"
        assert sign_lord_of_longitude(200.0) == "Venus"
        assert sign_name(360.0) == "Aries"  # wraps to sign 0 via normalize

    def test_star_span_function(self):
        start, end = star_span(10.0)
        assert start == pytest.approx(0.0, abs=1e-9)
        assert end == pytest.approx(STAR_SPAN_DEG, abs=1e-9)

    def test_pada_info(self):
        p = pada_info(0.0)
        assert isinstance(p, PadaInfo)
        assert p.pada == 1
        # interior points (10.0 is exactly the pada 3/4 boundary -> 3, so avoid it)
        assert pada_info(1.0).pada == 1
        assert pada_info(4.0).pada == 2
        assert pada_info(8.0).pada == 3
        assert pada_info(12.0).pada == 4
        p4 = pada_info(12.0)
        assert p4.start_deg == pytest.approx(10.0, abs=1e-9)
        assert p4.end_deg == pytest.approx(13.333333333333334, abs=1e-9)

    def test_normalize_longitude(self):
        assert normalize_longitude(360.0) == 0.0
        assert normalize_longitude(-30.0) == 330.0
        assert normalize_longitude(400.0) == 40.0


class TestFormatting:
    def test_format_longitude_10_5(self):
        s = format_longitude(10.5)
        assert "10" in s
        assert "\u00b0" in s
        assert s.startswith("10\u00b030'")

    def test_format_longitude_zero(self):
        assert format_longitude(0.0).startswith("0")

    def test_format_no_arcsec(self):
        assert format_longitude(10.5, arcsec=False) == "10\u00b030'"


class TestPointInfo:
    def test_longitude_200(self):
        p = point_info(200.0)
        assert isinstance(p, PointInfo)
        assert p.longitude == 200.0
        assert p.sign == "Libra"
        assert p.sign_lord == "Venus"
        assert p.star == "Vishakha"   # 200.0 is the Swati/Vishakha boundary
        assert p.star_lord == "Jupiter"
        assert p.star_index == 15
        assert p.sub_lord == sub_lord(200.0)
        assert p.sub_sub_lord == sub_sub_lord(200.0)
        assert 1 <= p.pada <= 4

    def test_point_info_interior_same_star(self):
        p = point_info(199.5)
        assert p.star == "Swati"
        assert p.star_lord == "Rahu"

    def test_point_info_normalizes(self):
        p = point_info(560.0)  # 560 - 360 = 200
        assert p.longitude == 200.0
        assert p.sign == "Libra"


class TestSubDivisions:
    def test_nine_subs_per_star_contiguous(self):
        for sidx in range(27):
            subs = sub_divisions(sidx)
            assert len(subs) == 9
            for k in range(9):
                lord, start, end, span = subs[k]
                assert start < end
                if k > 0:
                    assert subs[k - 1][2] == pytest.approx(start, abs=1e-9)
                    assert subs[k - 1][3] == pytest.approx(sub_span_arcmin(subs[k - 1][0]), rel=1e-12)

    def test_star_starts_clean_and_end_at_360(self):
        assert sub_divisions(0)[0][1] == 0.0
        assert sub_divisions(26)[-1][2] == pytest.approx(360.0, abs=1e-12)

    def test_sub_info_and_divisions_share_edges(self):
        # sub_info must never disagree with sub_divisions on an interior point.
        for sidx in range(27):
            for lord, start, end, _span in sub_divisions(sidx):
                mid = (start + end) / 2.0
                s = sub_info(mid)
                assert s.lord == lord
                assert s.start_deg == pytest.approx(start, abs=1e-9)

    def test_exact_star_boundaries_belong_to_next_star(self):
        for i in range(1, 27):
            boundary = i * STAR_SPAN_DEG
            assert star_index(boundary) == i
            assert sub_info(boundary).index == 0  # first sub of the next star


class TestBoundaryRobustness:
    def test_format_longitude_carries_without_60s(self):
        assert format_longitude(33.333333333333332) == "33\u00b020'00.0\""
        assert format_longitude(359.9999999) == "0\u00b000'00.0\""

    def test_normalize_folds_360_and_negative_junk(self):
        assert normalize_longitude(360.0) == 0.0
        assert normalize_longitude(-1e-14) == 0.0
        assert normalize_longitude(-0.1) == pytest.approx(359.9, rel=1e-12)

    def test_no_crash_inside_nakshatra_tail(self):
        # The last wave before each star end must still resolve (FP-safe).
        for i in range(27):
            end = i * STAR_SPAN_DEG + STAR_SPAN_DEG - 1e-10
            s = sub_info(end)
            assert s.start_deg <= end < s.end_deg