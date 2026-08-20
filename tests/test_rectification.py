"""Tests for birth-time rectification (src/kpastro/rectification.py)."""

from datetime import date, datetime, time, timedelta

import pytest

from kpastro import BirthInfo, SwissEphemeris
from kpastro.rectification import (
    CredibleInterval,
    IdentityInfo,
    LifeEvent,
    SCORING,
    aspects_from_house,
    credible_interval,
    house_significator_sets,
    rectify,
    render_rectification,
    score_candidate,
    transit_confirmation,
)
from kpastro.significators import house_of_longitude
from kpastro.vedic import star_lord, sub_lord
from kpastro.constants import SIGN_LORDS
from kpastro.vedic import sign_name

DELHI = BirthInfo(date(1990, 1, 15), time(14, 30), 28.6139, 77.2090, 5.5, "Delhi")

EVENTS = (
    LifeEvent(date(1995, 9, 3), 2, (), "School admission"),
    LifeEvent(date(2007, 4, 1), 4, (), "Joined college"),
    LifeEvent(date(2013, 2, 14), 4, (), "First job"),
    LifeEvent(date(2018, 1, 20), 7, (), "Marriage"),
)

_J2000_JD = 2451545.0
_J2000 = datetime(2000, 1, 1, 12)


@pytest.fixture(scope="module")
def eph():
    return SwissEphemeris(ayanamsa="lahiri", node="true")


def dt_from_jd(jd: float) -> datetime:
    return _J2000 + timedelta(days=jd - _J2000_JD)


def snapshot(birth, eph):
    jd = eph.jd_ut(birth.utc_datetime())
    sider = eph.sidereal_positions(jd)
    cusps, asc, _mc, _armc = eph.houses(jd, birth.latitude, birth.longitude)
    positions = {p: lon for p, (lon, _) in sider.items()}
    return positions, cusps, asc


class TestAspectsFromHouse:
    def test_opposition_every_planet(self):
        for planet in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus",
                       "Saturn", "Rahu", "Ketu"):
            for house in range(1, 13):
                assert ((house + 5) % 12) + 1 in aspects_from_house(house, planet)

    def test_jupiter_adds_5_7_9(self):
        for house in range(1, 13):
            expected = {((house + 5) % 12) + 1}
            expected.update(((house - 1 + o) % 12) + 1 for o in (4, 6, 8))
            assert aspects_from_house(house, "Jupiter") == expected

    def test_mars_adds_4_7_8(self):
        for house in range(1, 13):
            expected = {((house + 5) % 12) + 1}
            expected.update(((house - 1 + o) % 12) + 1 for o in (3, 6, 7))
            assert aspects_from_house(house, "Mars") == expected

    def test_saturn_adds_3_7_10(self):
        for house in range(1, 13):
            expected = {((house + 5) % 12) + 1}
            expected.update(((house - 1 + o) % 12) + 1 for o in (2, 6, 9))
            assert aspects_from_house(house, "Saturn") == expected

    def test_wraparound(self):
        # 10 -> 7th=4, 5th=2, 9th=6 (Jupiter aspects 5th/7th/9th)
        assert aspects_from_house(10, "Jupiter") == {2, 4, 6}
        assert aspects_from_house(12, "Sun") == {6}


class TestHouseSignificatorSets:
    def test_all_twelve_houses_present(self, eph):
        positions, cusps, _ = snapshot(DELHI, eph)
        sets, house_map = house_significator_sets(positions, cusps)
        assert set(sets) == set(range(1, 13))
        assert set(house_map) == set(positions)

    def test_cusp_sublord_is_a_significator(self, eph):
        positions, cusps, _ = snapshot(DELHI, eph)
        sets, _ = house_significator_sets(positions, cusps)
        for h in range(1, 13):
            assert sub_lord(cusps[h - 1]) in sets[h]

    def test_occupant_and_its_star_lord_included(self, eph):
        positions, cusps, _ = snapshot(DELHI, eph)
        sets, house_map = house_significator_sets(positions, cusps)
        for planet in positions:
            h = house_map[planet]
            assert planet in sets[h]
            assert star_lord(positions[planet]) in sets[h]

    def test_aspecting_planet_reaches_seventh_house(self, eph):
        positions, cusps, _ = snapshot(DELHI, eph)
        sets, house_map = house_significator_sets(positions, cusps)
        for planet in positions:
            h = house_map[planet]
            seventh = ((h + 5) % 12) + 1
            assert planet in sets[seventh]
            assert star_lord(positions[planet]) in sets[seventh]


class TestLifeEvent:
    def test_jd_ut_midday_default(self, eph):
        ev = LifeEvent(date(1995, 9, 3), 2)
        # 12:00 local IST - 5.5h = 06:30 UT
        expected = eph.jd_ut(datetime(1995, 9, 3, 6, 30))
        assert ev.jd_ut(5.5, eph) == pytest.approx(expected, abs=1e-9)

    def test_jd_ut_with_custom_time(self, eph):
        ev = LifeEvent(date(2013, 2, 14), 4, time=time(9, 15))
        expected = eph.jd_ut(datetime(2013, 2, 14, 3, 45))
        assert ev.jd_ut(5.5, eph) == pytest.approx(expected, abs=1e-9)


class TestScoreCandidate:
    def test_scores_are_deterministic(self, eph):
        jd = eph.jd_ut(DELHI.utc_datetime())
        a = score_candidate(jd, DELHI.latitude, DELHI.longitude, EVENTS,
                            tz_hours=DELHI.tz_hours, eph=eph)
        b = score_candidate(jd, DELHI.latitude, DELHI.longitude, EVENTS,
                            tz_hours=DELHI.tz_hours, eph=eph)
        assert a == b

    def test_total_is_the_defined_weighted_sum(self, eph):
        jd = eph.jd_ut(DELHI.utc_datetime())
        c = score_candidate(jd, DELHI.latitude, DELHI.longitude, EVENTS,
                            tz_hours=DELHI.tz_hours, rp_set={"Saturn"},
                            identity=IdentityInfo(siblings=1), eph=eph)
        assert c.total == pytest.approx(
            c.lsl_score + 0.5 * c.dasha_score + c.rp_score + c.identity_score
        )

    def test_rp_score_present_iff_lsl_in_set(self, eph):
        jd = eph.jd_ut(DELHI.utc_datetime())
        c0 = score_candidate(jd, DELHI.latitude, DELHI.longitude, EVENTS,
                             tz_hours=DELHI.tz_hours, eph=eph)
        assert c0.rp_score == 0.0
        c1 = score_candidate(jd, DELHI.latitude, DELHI.longitude, EVENTS,
                             tz_hours=DELHI.tz_hours, rp_set={c0.lsl}, eph=eph)
        assert c1.rp_score == 1.0
        assert c1.total == pytest.approx(c0.total + 1.0)

    def test_identity_hint_moves_score_only_when_matched(self, eph):
        positions, cusps, _ = snapshot(DELHI, eph)
        occ3 = any(house_of_longitude(lon, cusps) == 3 for lon in positions.values())
        jd = eph.jd_ut(DELHI.utc_datetime())
        ci = score_candidate(jd, DELHI.latitude, DELHI.longitude, EVENTS,
                             tz_hours=DELHI.tz_hours,
                             identity=IdentityInfo(siblings=1 if occ3 else 0),
                             eph=eph)
        assert ci.identity_score == pytest.approx(0.25)
        assert ci.total == pytest.approx(
            score_candidate(jd, DELHI.latitude, DELHI.longitude, EVENTS,
                            tz_hours=DELHI.tz_hours, eph=eph).total + 0.25
        )

    def test_identity_hint_no_op_when_mismatched(self, eph):
        positions, cusps, _ = snapshot(DELHI, eph)
        occ3 = any(house_of_longitude(lon, cusps) == 3 for lon in positions.values())
        jd = eph.jd_ut(DELHI.utc_datetime())
        wrong = IdentityInfo(siblings=0 if occ3 else 1)
        c = score_candidate(jd, DELHI.latitude, DELHI.longitude, EVENTS,
                            tz_hours=DELHI.tz_hours, identity=wrong, eph=eph)
        assert c.identity_score == 0.0

    def test_specificity_bounds(self, eph):
        jd = eph.jd_ut(DELHI.utc_datetime())
        c = score_candidate(jd, DELHI.latitude, DELHI.longitude, EVENTS,
                            tz_hours=DELHI.tz_hours, eph=eph)
        assert 0.0 <= c.specificity <= 1.0
        assert 1 <= c.n_significating_houses <= 12

    def test_event_scores_align_with_events(self, eph):
        jd = eph.jd_ut(DELHI.utc_datetime())
        c = score_candidate(jd, DELHI.latitude, DELHI.longitude, EVENTS,
                            tz_hours=DELHI.tz_hours, eph=eph)
        assert len(c.events) == len(EVENTS)
        assert all(es.dasha_score >= 0.0 for es in c.events)
        assert all(es.dasha_score == 0.0 or es.mahadasha_lord for es in c.events)

    def test_empty_events_raises(self, eph):
        jd = eph.jd_ut(DELHI.utc_datetime())
        with pytest.raises(ValueError):
            score_candidate(jd, DELHI.latitude, DELHI.longitude, [], eph=eph)


class TestRectify:
    def test_candidate_grid_size(self, eph):
        res = rectify(DELHI, time(14, 30), EVENTS, window_min=30, step_min=2,
                      eph=eph, analysis_time=datetime(2026, 1, 1, 12, 0))
        assert len(res.candidates) == round(60 / 2) + 1

    def test_best_is_first_and_consistently_sorted(self, eph):
        res = rectify(DELHI, time(14, 30), EVENTS, window_min=30, step_min=2,
                      eph=eph, analysis_time=datetime(2026, 1, 1, 12, 0))
        assert res.best is res.candidates[0]
        keys = [(-c.total, -c.lsl_score, abs(c.offset_minutes)) for c in res.candidates]
        assert keys == sorted(keys)

    def test_approximation_itself_is_a_candidate(self, eph):
        res = rectify(DELHI, time(14, 30), EVENTS, window_min=30, step_min=2,
                      eph=eph, analysis_time=datetime(2026, 1, 1, 12, 0))
        assert any(c.offset_minutes == 0.0 for c in res.candidates)

    def test_all_offsets_within_window(self, eph):
        res = rectify(DELHI, time(14, 30), EVENTS, window_min=30, step_min=2,
                      eph=eph, analysis_time=datetime(2026, 1, 1, 12, 0))
        for c in res.candidates:
            assert abs(c.offset_minutes) <= 30.0 + 1e-6

    def test_credible_interval_matches_best_candidate(self, eph):
        res = rectify(DELHI, time(14, 30), EVENTS, window_min=30, step_min=2,
                      eph=eph, analysis_time=datetime(2026, 1, 1, 12, 0))
        ci = res.credible
        assert isinstance(ci, CredibleInterval)
        assert ci.mass >= 0.75 - 1e-9
        assert ci.spread_minutes >= 0.0
        assert ci.peak_ut == dt_from_jd(res.best.jd_ut)

    def test_event_validation(self, eph):
        with pytest.raises(ValueError):
            rectify(DELHI, time(14, 30), [LifeEvent(date(1995, 1, 1), 0)], eph=eph)
        with pytest.raises(ValueError):
            rectify(DELHI, time(14, 30), [LifeEvent(date(1995, 1, 1), 13)], eph=eph)
        with pytest.raises(ValueError):
            rectify(DELHI, time(14, 30), [], eph=eph)

    def test_use_rp_still_returns_sane_scores(self, eph):
        res = rectify(DELHI, time(14, 30), EVENTS, window_min=15, step_min=3,
                      eph=eph, use_rp=True,
                      analysis_time=datetime(2026, 1, 1, 12, 0))
        assert all(c.rp_score in (0.0, 1.0) for c in res.candidates)
        assert any(c.rp_score == 1.0 for c in res.candidates)


class TestTransitConfirmation:
    def test_total_is_two_per_event(self, eph):
        tc = transit_confirmation(eph.jd_ut(DELHI.utc_datetime()),
                                  DELHI.latitude, DELHI.longitude, EVENTS,
                                  tz_hours=DELHI.tz_hours, eph=eph)
        assert tc.total == 2 * len(EVENTS)
        assert 0 <= tc.matched <= tc.total
        assert len(tc.per_event) == len(EVENTS)
        for et in tc.per_event:
            assert isinstance(et.jupiter, bool)
            assert isinstance(et.saturn, bool)


class TestCredibleInterval:
    def test_mass_reaches_target(self, eph):
        jd = eph.jd_ut(DELHI.utc_datetime())
        cands = [
            score_candidate(jd + i / 1440, DELHI.latitude, DELHI.longitude, EVENTS,
                            tz_hours=DELHI.tz_hours, eph=eph)
            for i in range(-3, 4)
        ]
        ci = credible_interval(cands)
        assert ci.mass >= 0.75 - 1e-9
        assert ci.spread_minutes >= 0.0
        assert ci.start_ut <= ci.peak_ut <= ci.end_ut

    def test_peak_is_the_maximum_candidate(self, eph):
        jd = eph.jd_ut(DELHI.utc_datetime())
        cands = [
            score_candidate(jd + i / 1440, DELHI.latitude, DELHI.longitude, EVENTS,
                            tz_hours=DELHI.tz_hours, eph=eph)
            for i in range(-3, 4)
        ]
        ci = credible_interval(cands)
        best = max(cands, key=lambda c: c.total)
        assert ci.peak_ut == dt_from_jd(best.jd_ut)

    def test_requires_input(self):
        with pytest.raises(ValueError):
            credible_interval([])


class TestRectificationRegression:
    def test_event_predating_birth_is_rejected(self, eph):
        jd = eph.jd_ut(DELHI.utc_datetime())
        early = LifeEvent(date(1980, 1, 1), 4, (), "before birth")
        with pytest.raises(ValueError, match="predates"):
            score_candidate(jd, DELHI.latitude, DELHI.longitude, [early],
                            tz_hours=DELHI.tz_hours, eph=eph)
        with pytest.raises(ValueError, match="predates"):
            rectify(DELHI, time(14, 30), [early], eph=eph,
                    analysis_time=datetime(2026, 1, 1, 12, 0))

    def test_snapshot_and_full_path_agree(self, eph):
        from kpastro.rectification import _scan_snapshot
        approx = eph.jd_ut(DELHI.utc_datetime())
        event_jds = tuple(e.jd_ut(DELHI.tz_hours, eph) for e in EVENTS)
        snap = _scan_snapshot(approx, eph)
        for jd_off in (-30.0, 0.0, 25.0):
            jd = approx + jd_off / 1440.0
            full = score_candidate(jd, DELHI.latitude, DELHI.longitude, EVENTS,
                                   tz_hours=DELHI.tz_hours, eph=eph,
                                   approx_jd=approx, event_jds=event_jds)
            opt = score_candidate(jd, DELHI.latitude, DELHI.longitude, EVENTS,
                                  tz_hours=DELHI.tz_hours, eph=eph,
                                  approx_jd=approx, event_jds=event_jds,
                                  _snapshot=snap)
            assert (full.total, full.lsl, full.dasha_score) == (opt.total, opt.lsl, opt.dasha_score)

    def test_single_event_scan_runs(self, eph):
        res = rectify(DELHI, time(14, 33), EVENTS[:1], window_min=10, step_min=2,
                      eph=eph, analysis_time=datetime(2026, 1, 1, 12, 0))
        assert len(res.candidates) >= 1
        assert res.best.total >= res.candidates[0].events[0].lsl_score * 0.5

    def test_secondary_house_lsl_is_scored(self, eph):
        jd = eph.jd_ut(DELHI.utc_datetime())
        # LSL-scored secondary hit: force a LifeEvent into a secondary house
        # and confirm scoring works for the branch (determinism only).
        ev = LifeEvent(date(2013, 2, 14), 4, (7,), "job+marriage")
        c = score_candidate(jd + 2 / 1440, DELHI.latitude, DELHI.longitude, [ev],
                            tz_hours=DELHI.tz_hours, eph=eph)
        assert 0.0 <= c.events[0].lsl_score <= 3.0

    def test_life_event_validates_houses(self):
        with pytest.raises(ValueError):
            LifeEvent(date(2013, 2, 14), 13)
        with pytest.raises(ValueError):
            LifeEvent(date(2013, 2, 14), 4, secondary=(0,))
        with pytest.raises(ValueError):
            LifeEvent(date(2013, 2, 14), 4, secondary=(99,))

    def test_house_sets_include_cuspal_sign_lord(self, eph):
        positions, cusps, _ = snapshot(DELHI, eph)
        sets, _ = house_significator_sets(positions, cusps)
        for h in range(1, 13):
            assert SIGN_LORDS[sign_name(cusps[h - 1])] in sets[h]

    def test_scoring_constants_are_named(self):
        for key in ("lsl_primary", "lsl_secondary", "dasha_share",
                    "softmax_temperature", "target_mass"):
            assert float(SCORING[key]) > 0.0


class TestRender:
    def test_report_contains_headline_and_best(self, eph):
        res = rectify(DELHI, time(14, 30), EVENTS, window_min=15, step_min=3,
                      eph=eph, analysis_time=datetime(2026, 1, 1, 12, 0))
        out = render_rectification(res, DELHI)
        assert "RECTIFICATION" in out.replace("\n", "")
        assert "Best candidate" in out
        assert "Posterior band" in out
        for ev in EVENTS:
            assert ev.label in out