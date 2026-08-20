"""KP horary (Prashna): the 1-249 number system.

The zodiac contains 27 nakshatras x 9 Vimshottari sub-lords = 243 subs.  Six of
the twelve sign boundaries fall *inside* a sub and split it in two (the sub's
lord stays the same but its zodiac sign changes), which is why a KP horary
chart counts exactly **249** numbered divisions from 0° Aries.

* A querent's number ``n`` (1..249) selects division ``n``.
* The horary ascendant is the **midpoint** of that division.
* Everything else (planets, other cusps, rulers) comes from the moment and
  place of the question, computed with the normal engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from bisect import bisect_right
from functools import lru_cache

from .constants import VIMSHOTTARI_ORDER
from .vedic import (
    normalize_longitude,
    point_info,
    sign_lord_of_longitude,
    sign_name,
    star_lord,
    star_name,
    sub_divisions,
)

MAX_HORARY_NUMBER = 249

#: Tolerance for deciding a sign boundary falls strictly inside a sub.
_BOUNDARY_EPS = 1e-9


@dataclass(frozen=True)
class HoraryDiv:
    """One of the 249 KP horary divisions of the zodiac."""
    number: int
    start_deg: float
    end_deg: float
    sign: str
    sign_lord: str
    star: str
    star_lord: str
    sub_lord: str

    @property
    def mid_deg(self) -> float:
        return (self.start_deg + self.end_deg) / 2.0


def kp_divisions() -> list[HoraryDiv]:
    """Generate all 249 divisions in ascending zodiacal order.

    The table is computed once and cached; each call returns a fresh list
    over the immutable internal table, so callers may not corrupt the cache.
    """
    return list(_divisions_tuple())


@lru_cache(maxsize=None)
def _divisions_tuple() -> tuple[HoraryDiv, ...]:
    subs: list[tuple[float, float, int, str]] = []
    for sidx in range(27):
        for lord, start, end, _span in sub_divisions(sidx):
            subs.append((start, end, sidx, lord))

    divisions: list[HoraryDiv] = []
    num = 0
    for start, end, sidx, sub_owner in subs:
        boundaries = [
            b for b in (30.0 * k for k in range(1, 12))
            if start + _BOUNDARY_EPS < b < end - _BOUNDARY_EPS
        ]
        cursor = start
        for b in boundaries + [end]:
            seg_start, seg_end = cursor, b
            num += 1
            divisions.append(
                HoraryDiv(
                    number=num,
                    start_deg=seg_start,
                    end_deg=seg_end,
                    sign=sign_name(seg_start),
                    sign_lord=sign_lord_of_longitude(seg_start),
                    star=star_name(seg_start),
                    star_lord=star_lord(seg_start),
                    sub_lord=sub_owner,
                )
            )
            cursor = b
    return tuple(divisions)


@lru_cache(maxsize=None)
def _division_starts() -> tuple[float, ...]:
    return tuple(d.start_deg for d in _divisions_tuple())


def ascendant_from_kp_number(n: int) -> dict:
    """The horary ascendant (division midpoint) and its full KP lord chain.

    Returns a dict with ``ascendant`` (sidereal longitude), the division span
    and the sign / star / sub / sub-sub breakdown.
    """
    if not 1 <= n <= MAX_HORARY_NUMBER:
        raise ValueError(f"KP horary number must be within 1-{MAX_HORARY_NUMBER}")
    div = _divisions_tuple()[n - 1]
    mid = div.mid_deg
    info = point_info(mid)
    return {
        "number": n,
        "ascendant": mid,
        "span": (div.start_deg, div.end_deg),
        "sign": info.sign,
        "sign_lord": info.sign_lord,
        "star": info.star,
        "star_lord": info.star_lord,
        "sub_lord": info.sub_lord,
        "sub_sub_lord": info.sub_sub_lord,
        "pada": info.pada,
    }


def kp_number_for_longitude(lon: float) -> int:
    """Inverse lookup: which KP horary division contains this sidereal longitude.

    Uses binary search over the cached division-start table, so a single
    lookup is O(log 249) instead of rescanning the whole zodiac.  Longitudes
    outside [0, 360) are normalised first (the 249 divisions tile the full
    zodiac, so the lookup always succeeds).
    """
    lon = normalize_longitude(lon)
    starts = _division_starts()
    idx = bisect_right(starts, lon) - 1
    return max(idx, 0) + 1