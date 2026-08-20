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

from .constants import VIMSHOTTARI_ORDER, VIMSHOTTARI_YEARS
from .vedic import (
    STAR_SPAN_DEG,
    point_info,
    sign_index,
    sign_lord_of_longitude,
    sign_name,
    star_index,
    star_name,
    star_lord,
    sub_info,
    sub_lord,
    sub_sub_lord,
)

MAX_HORARY_NUMBER = 249


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
    """Generate all 249 divisions in ascending zodiacal order."""
    subs: list[tuple[float, float, int, str]] = []
    for sidx in range(27):
        star_start = sidx * STAR_SPAN_DEG
        pos = sidx % 9
        run = 0.0
        for k in range(9):
            lord = VIMSHOTTARI_ORDER[(pos + k) % 9]
            span = VIMSHOTTARI_YEARS[lord] * (800.0 / 60.0) / 120.0
            subs.append((star_start + run, star_start + run + span, sidx, lord))
            run += span

    divisions: list[HoraryDiv] = []
    num = 0
    for start, end, sidx, sub_owner in subs:
        boundaries = [b for b in (30.0 * k for k in range(1, 12))
                      if start + 1e-9 < b < end - 1e-9]
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
    return divisions


def ascendant_from_kp_number(n: int) -> dict:
    """The horary ascendant (division midpoint) and its full KP lord chain.

    Returns a dict with ``ascendant`` (sidereal longitude), the division span
    and the sign / star / sub / sub-sub breakdown.
    """
    if not 1 <= n <= MAX_HORARY_NUMBER:
        raise ValueError(f"KP horary number must be within 1-{MAX_HORARY_NUMBER}")
    div = kp_divisions()[n - 1]
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


def kp_number_for_longitude(lon: float) -> int | None:
    """Inverse lookup: which KP horary division contains this sidereal longitude."""
    lon = lon % 360.0
    for div in kp_divisions():
        if div.start_deg - 1e-9 <= lon < div.end_deg + 1e-9:
            return div.number
    return None