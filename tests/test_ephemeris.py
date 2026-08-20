"""Golden-value tests against Swiss Ephemeris (src/kpastro/ephemeris.py)."""

from datetime import datetime

import pytest
import swisseph

from kpastro.ephemeris import (
    AYANAMSA_MODES,
    NODES,
    SwissEphemeris,
    default_ephe_path,
    ephemeris_version,
)
from kpastro.vedic import normalize_longitude


class TestEphemerisConfig:
    def test_matches_swisseph_constants(self):
        assert AYANAMSA_MODES["lahiri"] == swisseph.SIDM_LAHIRI
        assert AYANAMSA_MODES["kp"] == swisseph.SIDM_KRISHNAMURTI_VP291
        assert AYANAMSA_MODES["kp_old"] == swisseph.SIDM_KRISHNAMURTI
        assert NODES["mean"] == swisseph.MEAN_NODE
        assert NODES["true"] == swisseph.TRUE_NODE

    def test_default_path_looks_sane(self):
        assert str(default_ephe_path()).replace("\\", "/").endswith(".kpastro/ephe")

    def test_version_string(self):
        assert ephemeris_version().count(".") >= 1


class TestSwissEphemeris:
    def test_data_files_present_on_this_machine(self):
        assert SwissEphemeris().data_files_present is True

    def test_jd_ut_j2000_noon(self):
        jd = SwissEphemeris().jd_ut(datetime(2000, 1, 1, 12, 0, 0))
        assert jd == pytest.approx(2451545.0, abs=1e-3)

    def test_ayanamsa_lahiri_at_j2000(self):
        eph = SwissEphemeris()
        jd = eph.jd_ut(datetime(2000, 1, 1, 12, 0, 0))
        assert eph.ayanamsa(jd) == pytest.approx(23.8571, abs=0.01)

    def test_tropical_sun_j2000(self):
        eph = SwissEphemeris()
        jd = eph.jd_ut(datetime(2000, 1, 1, 12, 0, 0))
        trop = eph.tropical_positions(jd)
        assert trop["Sun"][0] == pytest.approx(280.3689, abs=0.02)

    def test_sidereal_sun_is_tropical_minus_ayanamsa(self):
        eph = SwissEphemeris()
        jd = eph.jd_ut(datetime(2000, 1, 1, 12, 0, 0))
        ayan = eph.ayanamsa(jd)
        trop = eph.tropical_positions(jd)
        sider = eph.sidereal_positions(jd)
        expected = normalize_longitude(trop["Sun"][0] - ayan)
        assert sider["Sun"][0] == pytest.approx(expected, abs=1e-9)

    def test_tropical_and_sidereal_planets(self):
        eph = SwissEphemeris()
        jd = eph.jd_ut(datetime(1990, 1, 15, 9, 0, 0))
        trop = eph.tropical_positions(jd)
        sider = eph.sidereal_positions(jd)
        assert set(trop) == set(sider)
        for name in trop:
            assert 0.0 <= trop[name][0] < 360.0
            assert 0.0 <= sider[name][0] < 360.0

    def test_houses_structure(self):
        eph = SwissEphemeris()
        jd = eph.jd_ut(datetime(2000, 1, 1, 12, 0, 0))
        cusps, asc, mc, armc = eph.houses(jd, 28.6139, 77.2090)
        assert len(cusps) == 12
        assert all(0.0 <= c < 360.0 for c in cusps)
        assert asc == pytest.approx(cusps[0], abs=1e-9)
        assert 0.0 <= asc < 360.0
        assert 0.0 <= mc < 360.0
        assert 0.0 <= armc < 360.0

    def test_mean_vs_true_node_differ(self):
        jd = SwissEphemeris().jd_ut(datetime(2000, 1, 1, 12, 0, 0))
        mean_eph = SwissEphemeris(node="mean")
        true_eph = SwissEphemeris(node="true")
        mean_rahu = mean_eph.tropical_positions(jd)["Rahu"][0]
        true_rahu = true_eph.tropical_positions(jd)["Rahu"][0]
        assert 0.0 <= mean_rahu < 360.0
        assert 0.0 <= true_rahu < 360.0
        assert abs(true_rahu - mean_rahu) > 0.1

    def test_ketu_opposite_rahu(self):
        eph = SwissEphemeris()
        jd = eph.jd_ut(datetime(2000, 1, 1, 12, 0, 0))
        trop = eph.tropical_positions(jd)
        assert normalize_longitude(trop["Ketu"][0]) == pytest.approx(
            normalize_longitude(trop["Rahu"][0] + 180.0), abs=1e-9
        )

    @pytest.mark.parametrize("bad", ["bogus", "", "chitra"])
    def test_unknown_ayanamsa_raises(self, bad):
        with pytest.raises(ValueError):
            SwissEphemeris(ayanamsa=bad)

    def test_unknown_node_raises(self):
        with pytest.raises(ValueError):
            SwissEphemeris(node="draconic")

    def test_multiple_instances_do_not_break(self):
        a = SwissEphemeris(ayanamsa="lahiri")
        b = SwissEphemeris(ayanamsa="kp")
        jd = a.jd_ut(datetime(2000, 1, 1, 12, 0, 0))
        a_lahiri = a.ayanamsa(jd)
        a_kp = b.ayanamsa(jd)
        assert a_lahiri != pytest.approx(a_kp, abs=1e-6)