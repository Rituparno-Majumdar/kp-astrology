"""Pure-Python KP sub-division mathematics.

This module needs **no ephemeris**: everything here is derived from a single
sidereal longitude using the classic KP tables.

Conventions
-----------
* Zodiac is **sidereal** 0°-360°, measured from 0° Aries.
* Every nakshatra spans :math:`13°20'` (800 arc-minutes).
* A nakshatra is divided into **9 unequal sub-lords** whose widths are
  proportional to the Vimshottari mahadasha years:

  .. math::

      \\text{sub span} = \\frac{\\text{lord's years}}{120} \\times 800'

  and the sub-lord sequence starts from the star-lord and runs through the
  Vimshottari order (wrapping).
* The **sub-sub-lord** divides the sub again with the same proportions,
  starting from the sub-lord.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from .constants import (
    NAKSHATRAS,
    SIGN_LORDS,
    SIGNS,
    VIMSHOTTARI_INDEX,
    VIMSHOTTARI_ORDER,
    VIMSHOTTARI_TOTAL_YEARS,
    VIMSHOTTARI_YEARS,
)

#: Nakshatra span in arc-minutes (13°20').
STAR_SPAN_ARCMIN: float = 800.0
#: Nakshatra span in decimal degrees.
STAR_SPAN_DEG: float = STAR_SPAN_ARCMIN / 60.0
#: Pada (quarter) span inside a star: 3°20'.
PADA_SPAN_DEG: float = STAR_SPAN_DEG / 4.0

#: Tolerance (degrees) used when a longitude lands exactly on a sub boundary:
#: values within 1e-9° below a boundary are assigned to the following sub, so
#: exact boundaries (e.g. 273.0 = Jupiter/Saturn edge) resolve deterministically.
#: 1e-9° ~ 3.6e-6 arcseconds, far below any ephemeris precision.
_BOUNDARY_TOL = 1e-9


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def normalize_longitude(lon: float) -> float:
    """Fold a longitude into [0, 360)."""
    lon = lon % 360.0
    # Gather FP rounding that lands exactly on 360.0 (e.g. -1e-14).
    return 0.0 if lon == 360.0 else lon


def sub_span_arcmin(lord: str) -> float:
    """Width of a sub ruled by ``lord`` in arc-minutes.

    ``years / 120 * 800`` e.g. Ketu -> 7/120*800 = 46.67'; Venus -> 133.33'.
    """
    return VIMSHOTTARI_YEARS[lord] * STAR_SPAN_ARCMIN / VIMSHOTTARI_TOTAL_YEARS


def format_longitude(lon: float, arcsec: bool = True) -> str:
    """Render a longitude as ``D°MM'SS"`` (or ``D°MM'`` when ``arcsec`` is False).

    The sign name is not included here so callers can append it.
    """
    lon = normalize_longitude(lon)
    deg = int(lon)
    rem = (lon - deg) * 60.0
    minute = int(rem)
    sec = (rem - minute) * 60.0
    if sec >= 59.95:  # carry rounding overflow (e.g. ... 59' 60.0")
        minute += 1
        sec = 0.0
        if minute == 60:
            deg += 1
            minute = 0
    deg %= 360
    if arcsec:
        return f"{deg}\u00b0{minute:02d}'{sec:04.1f}\""
    return f"{deg}\u00b0{minute:02d}'"


# ---------------------------------------------------------------------------
# Sign (rashi)
# ---------------------------------------------------------------------------

def sign_index(lon: float) -> int:
    """Which of the 12 rashis the longitude falls in (0..11)."""
    return int(normalize_longitude(lon) // 30.0)


def sign_name(lon: float) -> str:
    return SIGNS[sign_index(lon)]


def sign_lord_of_longitude(lon: float) -> str:
    return SIGN_LORDS[sign_name(lon)]


# ---------------------------------------------------------------------------
# Nakshatra (star)
# ---------------------------------------------------------------------------

def star_index(lon: float) -> int:
    """Nakshatra ordinal (0..26) containing the longitude.

    Boundaries are exact multiples of 800' (13°20'), so the lookup is done in
    arc-minute integers to avoid degree-multiplication round-off at the edges
    (e.g. 21*800/60 = 280.0 lands on the wrong side when computed as
    ``21 * 13.333333333333334``).
    """
    idx = int(normalize_longitude(lon) * 60.0 // STAR_SPAN_ARCMIN)
    return min(idx, 26)


def star_name(lon: float) -> str:
    return NAKSHATRAS[star_index(lon)]


def star_lord(lon: float) -> str:
    """Vimshottari star-lord of the nakshatra containing ``lon``."""
    from .constants import star_lord_of_index
    return star_lord_of_index(star_index(lon))


def star_span(lon: float) -> tuple[float, float]:
    """Start and end longitude of the nakshatra containing ``lon`` (degrees)."""
    idx = star_index(lon)
    return idx * STAR_SPAN_DEG, (idx + 1) * STAR_SPAN_DEG


# ---------------------------------------------------------------------------
# Pada (quarter of a star)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PadaInfo:
    """Quarter of a nakshatra (used for navamsa-style reference)."""
    pada: int                 # 1..4
    start_deg: float
    end_deg: float


def pada_info(lon: float) -> PadaInfo:
    idx = star_index(lon)
    start = idx * STAR_SPAN_DEG
    offset = normalize_longitude(lon) - start
    pada = min(int(offset // PADA_SPAN_DEG) + 1, 4)
    return PadaInfo(pada, start + (pada - 1) * PADA_SPAN_DEG, start + pada * PADA_SPAN_DEG)


# ---------------------------------------------------------------------------
# Sub-lord (the heart of KP)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SubInfo:
    """Sub-lord of a longitude inside its nakshatra."""
    lord: str                # sub-lord planet
    index: int               # 0..8 position among the nine subs of the star
    start_deg: float         # absolute start longitude of the sub
    end_deg: float           # absolute end longitude of the sub
    span_arcmin: float


@lru_cache(maxsize=4096)
def sub_divisions(star_idx: int) -> tuple[tuple[str, float, float, float], ...]:
    """The 9 sub-divisions of nakshatra ``star_idx`` (lord, start, end, span').

    Single source of truth for sub tiling: the spans always accumulate to the
    star's 800' (up to FP slop) and every other consumer shares this exact
    arithmetic, so no two code paths can drift.  Boundaries are built from the
    exact arc-minute star start (``star_idx * 800'``) to avoid degree-rounding
    drift at the star edges.
    """
    star_start_arcmin = star_idx * STAR_SPAN_ARCMIN
    start_pos = star_idx % 9
    # Cumulative years must stay integral so the boundary arcminute values are
    # exact rationals (20/3 x years), which keeps two adjacent subs sharing an
    # identical edge instead of drifting by an ulp.
    cum_years = 0.0
    out: list[tuple[str, float, float, float]] = []
    for k in range(9):
        lord = VIMSHOTTARI_ORDER[(start_pos + k) % 9]
        cum_years += VIMSHOTTARI_YEARS[lord]
        span = sub_span_arcmin(lord)
        start_deg = (
            star_start_arcmin + (cum_years - VIMSHOTTARI_YEARS[lord])
            * STAR_SPAN_ARCMIN / VIMSHOTTARI_TOTAL_YEARS
        ) / 60.0
        end_deg = (
            star_start_arcmin + cum_years * STAR_SPAN_ARCMIN / VIMSHOTTARI_TOTAL_YEARS
        ) / 60.0
        out.append(
            (lord, start_deg, end_deg, span)
        )
    return tuple(out)


@lru_cache(maxsize=4096)
def sub_info(lon: float) -> SubInfo:
    """Locate the Vimshottari sub-lord of the given sidereal longitude.

    Deterministic and immutable, so results are cached; repeated lookups for
    the same longitude (e.g. one used as both a planet position and a cusp)
    resolve instantly.
    """
    lon = normalize_longitude(lon)
    idx = star_index(lon)
    # Forward-push exact-boundary longitudes to the next sub, but never past
    # the star's own end (which would overflow the last sub).
    star_end = (idx + 1) * STAR_SPAN_ARCMIN / 60.0
    probe = min(lon + _BOUNDARY_TOL, star_end - 1e-12)
    for k, (lord, start_deg, end_deg, _span) in enumerate(sub_divisions(idx)):
        if start_deg <= probe < end_deg:
            return SubInfo(
                lord=lord,
                index=k,
                start_deg=start_deg,
                end_deg=end_deg,
                span_arcmin=sub_span_arcmin(lord),
            )
    raise ValueError(f"could not resolve sub-lord for longitude {lon}")


def sub_lord(lon: float) -> str:
    return sub_info(lon).lord


# ---------------------------------------------------------------------------
# Sub-sub-lord
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SubSubInfo:
    """Sub-sub-lord: the sub divided again with the same proportions."""
    lord: str
    index: int
    start_deg: float
    end_deg: float
    span_arcmin: float


@lru_cache(maxsize=4096)
def sub_sub_info(lon: float) -> SubSubInfo:
    """Locate the sub-sub-lord of the given sidereal longitude (cached).

    A sub is divided into 9 sub-subs proportionally to the Vimshottari years,
    measured against the **sub's own width** (not the star's 800' span): the
    sub-sub sequence starts at the sub-lord and each sub-sub spans

    .. math::

        \\text{sub-sub span} = \\text{sub span} \\times \\frac{\\text{lord's years}}{120}

    """
    lon = normalize_longitude(lon)
    sub = sub_info(lon)
    probe = min(lon + _BOUNDARY_TOL, sub.end_deg - 1e-12)
    running = 0.0
    for k, (lord, _start_deg, _end_deg, _span) in enumerate(sub_divisions(sub.index)):
        span = sub.span_arcmin * VIMSHOTTARI_YEARS[lord] / VIMSHOTTARI_TOTAL_YEARS
        start_deg = sub.start_deg + running / 60.0
        end_deg = start_deg + span / 60.0
        if start_deg <= probe < end_deg:
            return SubSubInfo(
                lord=lord,
                index=k,
                start_deg=start_deg,
                end_deg=end_deg,
                span_arcmin=span,
            )
        running += span
    raise ValueError(f"could not resolve sub-sub-lord for longitude {lon}")


def sub_sub_lord(lon: float) -> str:
    return sub_sub_info(lon).lord


# ---------------------------------------------------------------------------
# Convenience aggregate
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PointInfo:
    """Full KP breakdown of a sidereal longitude."""
    longitude: float
    sign: str
    sign_lord: str
    sign_degree: float
    star: str
    star_lord: str
    star_index: int
    sub_lord: str
    sub_sub_lord: str
    pada: int


def point_info(lon: float) -> PointInfo:
    lon = normalize_longitude(lon)
    sub = sub_info(lon)
    return PointInfo(
        longitude=lon,
        sign=sign_name(lon),
        sign_lord=sign_lord_of_longitude(lon),
        sign_degree=lon - sign_index(lon) * 30.0,
        star=star_name(lon),
        star_lord=star_lord(lon),
        star_index=star_index(lon),
        sub_lord=sub.lord,
        sub_sub_lord=sub_sub_lord(lon),
        pada=pada_info(lon).pada,
    )