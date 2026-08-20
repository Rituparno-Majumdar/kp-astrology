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


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def normalize_longitude(lon: float) -> float:
    """Fold a longitude into [0, 360)."""
    return lon % 360.0


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
    """Nakshatra ordinal (0..26) containing the longitude."""
    return int(normalize_longitude(lon) // STAR_SPAN_DEG)


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
def sub_info(lon: float) -> SubInfo:
    """Locate the Vimshottari sub-lord of the given sidereal longitude.

    Deterministic and immutable, so results are cached; repeated lookups for
    the same longitude (e.g. one used as both a planet position and a cusp)
    resolve instantly.
    """
    lon = normalize_longitude(lon)
    idx = star_index(lon)
    star_start = idx * STAR_SPAN_DEG
    offset_arcmin = (lon - star_start) * 60.0
    start_pos = idx % 9
    running = 0.0
    for k in range(9):
        lord = VIMSHOTTARI_ORDER[(start_pos + k) % 9]
        span = sub_span_arcmin(lord)
        if offset_arcmin < running + span:
            return SubInfo(
                lord=lord,
                index=k,
                start_deg=star_start + running / 60.0,
                end_deg=star_start + (running + span) / 60.0,
                span_arcmin=span,
            )
        running += span
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
    """Locate the sub-sub-lord of the given sidereal longitude (cached)."""
    lon = normalize_longitude(lon)
    sub = sub_info(lon)
    offset_arcmin = (lon - sub.start_deg) * 60.0
    start_pos = VIMSHOTTARI_INDEX[sub.lord]
    running = 0.0
    for k in range(9):
        lord = VIMSHOTTARI_ORDER[(start_pos + k) % 9]
        span = sub_span_arcmin(lord)
        if offset_arcmin < running + span:
            return SubSubInfo(
                lord=lord,
                index=k,
                start_deg=sub.start_deg + running / 60.0,
                end_deg=sub.start_deg + (running + span) / 60.0,
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