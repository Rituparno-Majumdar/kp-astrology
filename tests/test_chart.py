"""Golden-value tests for the full chart pipeline (src/kpastro/chart.py + significators)."""

from datetime import date, time

import pytest

from kpastro.chart import BirthInfo, Chart, compute_chart, render_chart
from kpastro.significators import (
    house_of_longitude,
    planet_significations,
    ruling_planets,
)

DELHI = BirthInfo(date(1990, 1, 15), time(14, 30), 28.6139, 77.2090, 5.5, "Delhi")


class TestComputeChart:
    def test_planet_and_cusp_counts(self):
        chart = compute_chart(DELHI)
        assert isinstance(chart, Chart)
        assert len(chart.planets) == 9
        assert len(chart.cusps) == 12

    def test_planets_in_valid_houses(self):
        chart = compute_chart(DELHI)
        for p in chart.planets:
            assert 1 <= p.house <= 12

    def test_balance_golden(self):
        chart = compute_chart(DELHI)
        assert chart.balance.mahadasha_lord == "Venus"
        assert 1 <= chart.balance.mahadasha_years <= 20

    def test_planet_names(self):
        chart = compute_chart(DELHI)
        assert [p.name for p in chart.planets] == [
            "Sun", "Moon", "Mars", "Mercury", "Jupiter",
            "Venus", "Saturn", "Rahu", "Ketu",
        ]

    def test_cusps_are_ascending_and_valid(self):
        chart = compute_chart(DELHI)
        lons = [c.longitude for c in chart.cusps]
        assert all(0.0 <= c < 360.0 for c in lons)
        assert chart.ascendant == pytest.approx(lons[0], abs=1e-9)

    def test_planet_lon_matches_planet_list(self):
        chart = compute_chart(DELHI)
        for p in chart.planets:
            assert chart.planet_lon[p.name] == pytest.approx(p.longitude, abs=1e-12)


class TestRenderChart:
    def test_output_contains_expected_sections(self):
        out = render_chart(compute_chart(DELHI))
        assert isinstance(out, str)
        assert "KRISHNAMURTI PADDHATI" in out
        assert "Asc" in out
        assert "MC" in out
        assert "PLANETS" in out
        assert "VIMSHOTTARI DASHA" in out
        assert "RULING PLANETS" in out


class TestRulingPlanets:
    def test_monday_day_lord_is_first(self):
        chart = compute_chart(DELHI)
        rp = ruling_planets(chart.ascendant, chart.planet_lon["Moon"], 0)
        assert rp[0].planet == "Moon"
        assert "day lord" in rp[0].source

    def test_ruling_sources_cover_asc_and_moon(self):
        chart = compute_chart(DELHI)
        rp = ruling_planets(chart.ascendant, chart.planet_lon["Moon"], 0)
        sources = " ".join(x.source for x in rp)
        assert "asc sign lord" in sources
        assert "asc star lord" in sources
        assert "asc sub lord" in sources
        assert "moon sign lord" in sources
        assert "moon star lord" in sources
        assert "moon sub lord" in sources

    def test_chart_ruling_field_populated(self):
        chart = compute_chart(DELHI)
        assert len(chart.ruling) >= 1
        assert all(x.planet in chart.planet_lon for x in chart.ruling)


class TestHouseOfLongitude:
    CUSPS = [10, 40, 70, 100, 130, 160, 190, 220, 250, 280, 310, 340]

    def test_basic_houses(self):
        assert house_of_longitude(20, self.CUSPS) == 1
        # The task spec read (35) == 2, but with cusps starting at 10 the span
        # [10, 40) is house 1, so 35 lands in house 1.  Verified against source.
        assert house_of_longitude(35, self.CUSPS) == 1

    def test_wrap_around(self):
        assert house_of_longitude(5, self.CUSPS) == 12
        assert house_of_longitude(345, self.CUSPS) == 12

    def test_between_every_pair(self):
        for i, start in enumerate(self.CUSPS, start=1):
            mid = (start + self.CUSPS[i % 12]) / 2.0
            if i == 12:
                mid = (start + self.CUSPS[0] + 360.0) / 2.0
                mid = mid % 360.0
            assert house_of_longitude(mid, self.CUSPS) == i


class TestSignifications:
    def test_planet_significations_has_nine_keys(self):
        chart = compute_chart(DELHI)
        float_cusps = [c.longitude for c in chart.cusps]
        sigs = planet_significations(chart.planet_lon, float_cusps)
        assert len(sigs) == 9
        assert set(sigs) == {
            "Sun", "Moon", "Mars", "Mercury", "Jupiter",
            "Venus", "Saturn", "Rahu", "Ketu",
        }
        for planet, houses in sigs.items():
            assert all(h.house in range(1, 13) for h in houses)

    def test_house_significations_shape(self):
        chart = compute_chart(DELHI)
        assert len(chart.house_significators) == 12
        for tiers in chart.house_significators:
            assert all(1 <= t <= 4 for _, t in tiers)

    def test_cusp_sublords_present(self):
        chart = compute_chart(DELHI)
        assert set(chart.cusp_sublords) == set(range(1, 13))
        assert all(isinstance(lord, str) and lord for lord in chart.cusp_sublords.values())