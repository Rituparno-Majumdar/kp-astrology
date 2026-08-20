"""Golden-value tests for Vimshottari dasha balances and timelines (src/kpastro/dasha.py)."""

from datetime import datetime

import pytest

from kpastro.vedic import STAR_SPAN_DEG
from kpastro.dasha import (
    DAYS_PER_YEAR,
    VIMSHOTTARI_TOTAL_YEARS,
    Balance,
    Period,
    antardashas_of,
    current_periods,
    dasha_balance,
    format_days,
    mahadasha_days,
    mahadasha_timeline,
    period_days,
    pratyantardashas_of,
)

VIMSHOTTARI_ORDER = ("Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury")


class TestDashaBalance:
    def test_balance_at_10_degrees(self):
        b = dasha_balance(10.0)
        assert isinstance(b, Balance)
        assert b.mahadasha_lord == "Ketu"
        assert b.mahadasha_years == pytest.approx(1.75, rel=1e-9)
        assert b.mahadasha_days == pytest.approx(1.75 * 365.25, rel=1e-9)
        assert b.active_ad_lord == "Saturn"
        assert b.active_pd_lord == "Saturn"
        assert b.nakshatra == "Ashwini"
        assert b.nakshatra_index == 0

    def test_balance_at_zero(self):
        b = dasha_balance(0.0)
        assert b.mahadasha_lord == "Ketu"
        assert b.mahadasha_years == pytest.approx(7.0, rel=1e-12)
        assert b.mahadasha_days == pytest.approx(7 * 365.25, rel=1e-12)

    def test_balance_at_star_boundary(self):
        """Moon exactly at Ashwini end / Bharani start -> Venus, full 20 years.

        The task cited ``13.3333333333`` but that constant lies a fraction below
        the exact 800/60 star boundary, so it stays in Ashwini (Ketu, ~0 years).
        We use the exact boundary 800/60.0 to test the intended case.
        """
        boundary = 800 / 60.0
        assert boundary == STAR_SPAN_DEG
        b = dasha_balance(boundary)
        assert b.mahadasha_lord == "Venus"
        assert b.mahadasha_years == pytest.approx(20.0, rel=1e-12)
        assert b.mahadasha_days == pytest.approx(20 * 365.25, rel=1e-12)
        assert b.nakshatra == "Bharani"

    def test_consistency_days_from_years(self):
        b = dasha_balance(10.0)
        assert b.mahadasha_days == pytest.approx(b.mahadasha_years * 365.25, rel=1e-12)


class TestMahadashaTimeline:
    def test_one_cycle_has_nine_periods(self):
        md = mahadasha_timeline(10.0)
        assert len(md) == 9

    def test_first_period_matches_balance(self):
        bal = dasha_balance(10.0)
        md = mahadasha_timeline(10.0)
        assert md[0].lord == bal.mahadasha_lord == "Ketu"
        assert md[0].duration_days == pytest.approx(bal.mahadasha_days, abs=1e-6)

    def test_subsequent_periods_are_full(self):
        md = mahadasha_timeline(10.0)
        for p in md[1:]:
            assert p.duration_days == pytest.approx(mahadasha_days(p.lord), abs=1e-6)

    def test_cycle_sums_to_full_vimshottari(self):
        bal = dasha_balance(10.0)
        md = mahadasha_timeline(10.0)
        total = sum(p.duration_days for p in md)
        expected = VIMSHOTTARI_TOTAL_YEARS * 365.25 - (
            mahadasha_days(bal.mahadasha_lord) - bal.mahadasha_days
        )
        assert total == pytest.approx(expected, abs=1e-6)

    def test_periods_are_contiguous_within_cycle(self):
        md = mahadasha_timeline(10.0)
        for i in range(len(md) - 1):
            assert md[i].end_days == pytest.approx(md[i + 1].start_days, abs=1e-9)


class TestAntardashas:
    def test_partial_mahadasha_opens_at_active_ad(self):
        """For the birth (partial) MD the AD chain starts at the active AD lord.

        The task spec expected 9 ADs, but `_subperiods` only emits periods with
        non-zero duration inside the (truncated) parent, so a partial MD carries
        just the periods that fit its remaining length.  We assert the invariants.
        """
        bal = dasha_balance(10.0)
        md = mahadasha_timeline(10.0)
        ads = antardashas_of(md[0], bal)
        assert ads[0].lord == bal.active_ad_lord == "Saturn"
        assert ads[0].duration_days == pytest.approx(bal.active_ad_days, abs=1e-6)
        assert ads[-1].end_days == pytest.approx(md[0].duration_days, abs=1e-6)
        assert sum(a.duration_days for a in ads) == pytest.approx(md[0].duration_days, abs=1e-6)
        assert all(a.start_days < a.end_days for a in ads)

    def test_full_mahadasha_has_nine_full_antardashas(self):
        md = mahadasha_timeline(10.0)
        venus_md = md[1]  # a full (non-partial) mahadasha
        ads = antardashas_of(venus_md)
        assert len(ads) == 9
        assert ads[0].lord == "Venus"
        assert sum(a.duration_days for a in ads) == pytest.approx(venus_md.duration_days, abs=1e-6)


class TestPratyantardashas:
    def test_partial_ad_invariant(self):
        bal = dasha_balance(10.0)
        md = mahadasha_timeline(10.0)
        ads = antardashas_of(md[0], bal)
        pds = pratyantardashas_of(ads[0], bal, md_is_partial=True)
        assert pds[0].lord == bal.active_pd_lord == "Saturn"
        assert pds[0].duration_days == pytest.approx(bal.active_pd_days, abs=1e-6)
        assert pds[-1].end_days == pytest.approx(ads[0].end_days, abs=1e-6)


class TestCurrentPeriods:
    def test_at_epoch_matches_balance(self):
        epoch = datetime(2000, 1, 1, 12, 0, 0)
        bal = dasha_balance(10.0)
        cur = current_periods(10.0, epoch, epoch, depth=3)
        assert cur[1].lord == bal.mahadasha_lord
        assert cur[2].lord == bal.active_ad_lord
        assert cur[3].lord == bal.active_pd_lord

    def test_period_days_formula(self):
        assert period_days("Venus", "Venus") == pytest.approx(20 * 20 / 120 * 365.25, rel=1e-12)
        assert period_days("Ketu", "Saturn") == pytest.approx(7 * 19 / 120 * 365.25, rel=1e-12)

    def test_format_days(self):
        assert "1y" in format_days(639.1875)  # 639.1875 = 1.75 * 365.25
        assert format_days(0.0) == "0y 0m 0d"

    def test_period_datetime_roundtrip(self):
        day = DAYS_PER_YEAR
        epoch = datetime(2000, 1, 1, 12, 0, 0)
        p = Period("Ketu", 0.0, day, 1)
        start, end = p.as_datetimes(epoch)
        assert (end - start).days == 365  # timedelta .days truncates; close enough
        assert (end - start).total_seconds() == pytest.approx(day * 86400.0, rel=1e-12)