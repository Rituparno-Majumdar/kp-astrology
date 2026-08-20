"""Swiss Ephemeris integration.

Positions and cusps are computed with the **Swiss Ephemeris** (`swisseph`,
aka `pyswisseph`) which is arc-second accurate.  All longitudes are converted
to the sidereal zodiac by subtracting the configured ayanamsa.

* Ayanamsa modes: ``lahiri`` (`SE_SIDM_LAHIRI`, the Chitrapaksha zero point
  used by default in KP software), ``kp`` (`SE_SIDM_KRISHNAMURTI_VP291`,
  the modern KP ayanamsa) and ``kp_old`` (`SE_SIDM_KRISHNAMURTI`).
* Node: KP traditionally uses the **mean** node; ``true`` is available.
* Ephemeris files: with the compressed JPL/VSOP files installed (see
  :func:`download_ephemeris`) the full precision Swiss ephemeris is used,
  otherwise the built-in **Moshier** ephemeris (planet error < 1", Moon
  ~0.5") kicks in silently - plenty for KP subdivision work.
"""

from __future__ import annotations

import os
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

import swisseph as swe

from .vedic import normalize_longitude

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

AYANAMSA_MODES: dict[str, int] = {
    "lahiri": swe.SIDM_LAHIRI,                    # 1  - Chitrapaksha / IAE 1985
    "kp": swe.SIDM_KRISHNAMURTI_VP291,            # 45 - modern KP ayanamsa
    "kp_old": swe.SIDM_KRISHNAMURTI,              # 5  - Krishnamurti's table
}

NODES: dict[str, int] = {"mean": swe.MEAN_NODE, "true": swe.TRUE_NODE}

#: Swiss Ephemeris body ids keyed by canonical KP planet name.
SWE_BODY: dict[str, int] = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mars": swe.MARS,
    "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus": swe.VENUS,
    "Saturn": swe.SATURN,
}

#: Order used for output tables (zodiacal, Sun first).
PLANET_OUTPUT_ORDER: tuple[str, ...] = (
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu",
)

#: Files required for full precision (JPL DE431/VSOP87 compressed ephemeris).
EPHEMERIS_FILES: tuple[str, ...] = ("sepl_18.se1", "semo_18.se1", "seas_18.se1")
EPHEMERIS_BASE_URL: str = "https://raw.githubusercontent.com/aloistr/swisseph/master/ephe/"


def default_ephe_path() -> Path:
    return Path.home() / ".kpastro" / "ephe"


def download_ephemeris(target_dir: Optional[Path | str] = None) -> list[Path]:
    """Download the Swiss Ephemeris data files into ``target_dir``.

    Returns the list of paths saved.  Files are fetched from the official
    ``aloistr/swisseph`` mirror of the astro.com release.
    """
    target = Path(target_dir) if target_dir else default_ephe_path()
    target.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for name in EPHEMERIS_FILES:
        dest = target / name
        if dest.exists() and dest.stat().st_size > 0:
            saved.append(dest)
            continue
        url = EPHEMERIS_BASE_URL + name
        with urllib.request.urlopen(url, timeout=60) as resp:
            data = resp.read()
        dest.write_bytes(data)
        saved.append(dest)
    return saved


class SwissEphemeris:
    """Thin, safe wrapper around the (global-state) Swiss Ephemeris engine."""

    def __init__(
        self,
        ayanamsa: str = "lahiri",
        node: str = "mean",
        ephe_path: Optional[Path | str] = None,
    ) -> None:
        if ayanamsa not in AYANAMSA_MODES:
            raise ValueError(
                f"unknown ayanamsa {ayanamsa!r}; choose from {sorted(AYANAMSA_MODES)}"
            )
        if node not in NODES:
            raise ValueError(f"unknown node {node!r}; choose from {sorted(NODES)}")
        self.ayanamsa_mode = ayanamsa
        self.node = node

        path = ephe_path or os.environ.get("SE_EPHE_PATH") or default_ephe_path()
        self.ephe_path = Path(path)
        if self.ephe_path.exists():
            swe.set_ephe_path(str(self.ephe_path))

        # Import-time probing never mutates the engine's sidereal mode.
        self._set_sid_mode()

    # -- engine plumbing --------------------------------------------------

    def _set_sid_mode(self) -> None:
        swe.set_sid_mode(AYANAMSA_MODES[self.ayanamsa_mode])

    @property
    def data_files_present(self) -> bool:
        return all((self.ephe_path / f).is_file() for f in EPHEMERIS_FILES)

    def jd_ut(self, dt: datetime) -> float:
        """Julian date (UT) for a naive-UTC datetime."""
        secs = dt.second + dt.microsecond / 1_000_000.0
        _, jd_ut = swe.utc_to_jd(
            dt.year, dt.month, dt.day, dt.hour, dt.minute, secs, swe.GREG_CAL
        )
        return jd_ut

    def ayanamsa(self, jd_ut: float) -> float:
        """Ayanamsa in degrees at the given Julian date (UT)."""
        self._set_sid_mode()
        return float(swe.get_ayanamsa_ut(jd_ut))

    def _calc(self, jd_ut: float, body: int, with_speed: bool = True):
        flags = swe.FLG_SWIEPH | (swe.FLG_SPEED if with_speed else 0)
        arr, retflag = swe.calc_ut(jd_ut, body, flags)[:2]
        return arr, retflag

    # -- positions --------------------------------------------------------

    def _node_lon(self, jd_ut: float) -> tuple[float, float]:
        body = NODES[self.node]
        arr, _ = self._calc(jd_ut, body)
        return float(arr[0]), float(arr[3])

    def tropical_positions(self, jd_ut: float) -> dict[str, tuple[float, float]]:
        """Tropical geocentric longitudes + daily speeds keyed by planet name."""
        out: dict[str, tuple[float, float]] = {}
        for name, body in SWE_BODY.items():
            arr, _ = self._calc(jd_ut, body)
            out[name] = (float(arr[0]), float(arr[3]))
        rahu_lon, rahu_speed = self._node_lon(jd_ut)
        out["Rahu"] = (rahu_lon, rahu_speed)
        out["Ketu"] = ((rahu_lon + 180.0) % 360.0, rahu_speed)
        return out

    def sidereal_positions(self, jd_ut: float) -> dict[str, tuple[float, float]]:
        ayan = self.ayanamsa(jd_ut)
        return {
            name: (normalize_longitude(lon - ayan), speed)
            for name, (lon, speed) in self.tropical_positions(jd_ut).items()
        }

    # -- houses -----------------------------------------------------------

    def houses(self, jd_ut: float, latitude: float, longitude: float):
        """Placidus house cusps + Ascendant/MC in the sidereal zodiac.

        Returns ``(cusps, asc, mc, armc)`` where ``cusps`` is a 12-element
        list and every angle is sidereal within [0, 360).
        """
        cusps_t, ascmc = swe.houses_ex(jd_ut, latitude, longitude, b"P")
        # pyswisseph returns 12 entries; the pysweph fork returns 13 with an
        # empty slot 0.  Normalise to a 12-element list either way.
        cusps_list = list(cusps_t[1:13] if len(cusps_t) == 13 else cusps_t)
        ayan = self.ayanamsa(jd_ut)
        cusps = [normalize_longitude(c - ayan) for c in cusps_list]
        asc = normalize_longitude(ascmc[0] - ayan)
        mc = normalize_longitude(ascmc[1] - ayan)
        armc = normalize_longitude(ascmc[2] - ayan)
        return cusps, asc, mc, armc


def ephemeris_version() -> str:
    return str(getattr(swe, "version", "unknown"))