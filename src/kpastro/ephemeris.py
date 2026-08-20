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
import threading
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

#: Sidereal mode last applied to the (process-global) Swiss Ephemeris engine.
_applied_sid_mode: int | None = None

#: Guards the global ayanamsa mode against interleaving by concurrent users.
_LOCK = threading.Lock()

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


#: Minimum plausible size (bytes) of a compressed ephemeris file.  The three
#: files in the aloistr/swisseph mirror are ~220 KB - 1.3 MB; anything far
#: below 100 KB is an HTML error page, not a valid ephemeris.  (Truncated
#: transfers are already rejected by urllib's IncompleteRead at read time.)
_EPHE_MIN_BYTES = 100_000


def download_ephemeris(target_dir: Optional[Path | str] = None) -> list[Path]:
    """Download the Swiss Ephemeris data files into ``target_dir``.

    Returns the list of paths saved.  Files are fetched from the official
    ``aloistr/swisseph`` mirror of the astro.com release.  Downloads are
    written atomically (temp file + rename) and validated by size, so a
    truncated or corrupt file is never treated as valid on a later run.
    """
    target = Path(target_dir) if target_dir else default_ephe_path()
    target.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for name in EPHEMERIS_FILES:
        dest = target / name
        if dest.exists() and dest.stat().st_size >= _EPHE_MIN_BYTES:
            saved.append(dest)
            continue
        url = EPHEMERIS_BASE_URL + name
        with urllib.request.urlopen(url, timeout=60) as resp:
            data = resp.read()
        if len(data) < _EPHE_MIN_BYTES:
            raise OSError(
                f"downloaded {name} is only {len(data)} bytes (< {_EPHE_MIN_BYTES}); "
                f"refusing to keep a truncated or error response"
            )
        tmp = dest.with_suffix(dest.suffix + ".part")
        tmp.write_bytes(data)
        os.replace(tmp, dest)
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

        self._set_sid_mode()

    # -- engine plumbing --------------------------------------------------

    def _set_sid_mode(self) -> None:
        global _applied_sid_mode
        # The Swiss Ephemeris holds process-global sidereal state; apply it
        # once and only re-apply when the mode actually changes so tight
        # multi-chart loops make zero redundant C calls. The tracker is
        # module-global because instances share the engine's global state, and
        # the lock keeps concurrent callers from interleaving apply/read.
        mode = AYANAMSA_MODES[self.ayanamsa_mode]
        with _LOCK:
            if mode != _applied_sid_mode:
                swe.set_sid_mode(mode)
                _applied_sid_mode = mode

    @property
    def data_files_present(self) -> bool:
        return all(
            (self.ephe_path / f).is_file()
            and (self.ephe_path / f).stat().st_size >= _EPHE_MIN_BYTES
            for f in EPHEMERIS_FILES
        )

    @property
    def precision(self) -> str:
        """``"full"`` with JPL/VSOP data files installed, else ``"moshier"``."""
        return "full" if self.data_files_present else "moshier"

    def _jd_ut_calendar(self, dt: datetime) -> int:
        # Julian calendar applies before 1582-10-15, Gregorian after.
        gregorian_start = datetime(1582, 10, 15)
        return swe.GREG_CAL if dt >= gregorian_start else swe.JUL_CAL

    def jd_ut(self, dt: datetime) -> float:
        """Julian date (UT) for a naive-UTC datetime.

        The calendar (Julian vs Gregorian) is chosen from the date, and the
        helper tolerates both 2- and 3-tuple ``utc_to_jd`` returns across
        pyswisseph versions.
        """
        secs = dt.second + dt.microsecond / 1_000_000.0
        res = swe.utc_to_jd(
            dt.year, dt.month, dt.day, dt.hour, dt.minute, secs, self._jd_ut_calendar(dt)
        )
        # Modern pyswisseph: (retval, jd_ut); older builds append jd_et too.
        jd_ut = res[-1] if len(res) >= 2 else res[0]
        return jd_ut

    def ayanamsa(self, jd_ut: float) -> float:
        """Ayanamsa in degrees at the given Julian date (UT)."""
        self._set_sid_mode()
        return float(swe.get_ayanamsa_ut(jd_ut))

    def _calc(self, jd_ut: float, body: int, with_speed: bool = True):
        flags = swe.FLG_SWIEPH | (swe.FLG_SPEED if with_speed else 0)
        arr, retflag = swe.calc_ut(jd_ut, body, flags)[:2]
        return arr, retflag

    def body(self, jd_ut: float, name: str) -> tuple[float, float]:
        """Sidereal longitude + daily speed of one canonical body (incl. nodes).

        Avoids recomputing the whole chart when only one body is needed.
        """
        ayan = self.ayanamsa(jd_ut)
        if name in ("Rahu", "Ketu"):
            lon, speed = self._node_lon(jd_ut)
            if name == "Ketu":
                lon = (lon + 180.0) % 360.0
            return normalize_longitude(lon - ayan), speed
        arr, _ = self._calc(jd_ut, SWE_BODY[name])
        return normalize_longitude(arr[0] - ayan), float(arr[3])

    def close(self) -> None:
        """Release the ephemeris data files held by the global engine.

        Safe to call more than once; the engine, being process-global, is
        shared by all instances so this only frees the file handles.
        """
        swe.close()

    def __enter__(self) -> "SwissEphemeris":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

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