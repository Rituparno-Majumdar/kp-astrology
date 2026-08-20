"""Vimshottari Dasha.

The mahadasha sequence is fixed: ``Ketu 7, Venus 20, Sun 6, Moon 10, Mars 7,
Rahu 18, Jupiter 16, Saturn 19, Mercury 17`` (120 years total).

The period running at birth is the mahadasha of the **star-lord** of the birth
Moon.  Only the fraction of the nakshatra *not yet traversed* is lived as the
balance of that period, and the full sequence then continues.

Balances are computed at **three nested levels**, each anchored to the birth
Moon:

.. math::

    MD_{bal} = \\frac{star_{end} - Moon}{star} \\cdot Y_{star} \\cdot 365.25

    AD_{bal} = \\frac{sub_{end} - Moon}{star} \\cdot Y_{star} \\cdot 365.25

    PD_{bal} = \\frac{subsub_{end} - Moon}{star} \\cdot Y_{star} \\cdot 365.25

where ``star`` is the 13°20' nakshatra span and the active sub / sub-sub lords
are those of the birth Moon's longitude.  Every full sub-period afterwards has
width ``Y_parent * Y_child / 120`` years (1 year = 365.25 days).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache

from .constants import (
    NAKSHATRAS,
    VIMSHOTTARI_INDEX,
    VIMSHOTTARI_ORDER,
    VIMSHOTTARI_TOTAL_YEARS,
    VIMSHOTTARI_YEARS,
)
from .vedic import STAR_SPAN_DEG, sub_info, sub_sub_info, star_index, star_lord

#: Days in one dasha year (the convention used by KP software).
DAYS_PER_YEAR: float = 365.25

#: Days of one full Vimshottari cycle.
CYCLE_DAYS: float = VIMSHOTTARI_TOTAL_YEARS * DAYS_PER_YEAR

_NINTH = 9


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Balance:
    """Nested dasha balances at a birth moment, anchored to the birth Moon."""
    mahadasha_lord: str
    mahadasha_years: float
    mahadasha_days: float
    active_ad_lord: str
    active_ad_days: float
    active_pd_lord: str
    active_pd_days: float
    nakshatra: str
    nakshatra_index: int


@dataclass(frozen=True)
class Period:
    """A dasha period with offsets measured in days from the epoch."""
    lord: str
    start_days: float
    end_days: float
    level: int                      # 1 mahadasha, 2 antardasha, 3 pratyantar

    @property
    def duration_days(self) -> float:
        return self.end_days - self.start_days

    @property
    def duration_years(self) -> float:
        return self.duration_days / DAYS_PER_YEAR

    def as_datetimes(self, epoch: datetime) -> tuple[datetime, datetime]:
        return (
            epoch + timedelta(days=self.start_days),
            epoch + timedelta(days=self.end_days),
        )


def period_days(parent_lord: str, child_lord: str) -> float:
    """Full length (days) of a sub-period of ``parent_lord`` ruled by ``child_lord``."""
    return (
        VIMSHOTTARI_YEARS[parent_lord]
        * VIMSHOTTARI_YEARS[child_lord]
        / VIMSHOTTARI_TOTAL_YEARS
        * DAYS_PER_YEAR
    )


def mahadasha_days(lord: str) -> float:
    return VIMSHOTTARI_YEARS[lord] * DAYS_PER_YEAR


# ---------------------------------------------------------------------------
# Balance at birth
# ---------------------------------------------------------------------------

@lru_cache(maxsize=4096)
def dasha_balance(moon_longitude: float) -> Balance:
    """All nested balances from the sidereal birth Moon longitude (cached)."""
    idx = star_index(moon_longitude)
    star_start = idx * STAR_SPAN_DEG
    star = STAR_SPAN_DEG

    sub = sub_info(moon_longitude)
    subsub = sub_sub_info(moon_longitude)

    md_lord = star_lord(moon_longitude)
    md_days = (star_start + star - moon_longitude) / star * VIMSHOTTARI_YEARS[md_lord] * DAYS_PER_YEAR
    ad_days = (sub.end_deg - moon_longitude) / star * VIMSHOTTARI_YEARS[md_lord] * DAYS_PER_YEAR
    pd_days = (subsub.end_deg - moon_longitude) / star * VIMSHOTTARI_YEARS[md_lord] * DAYS_PER_YEAR

    return Balance(
        mahadasha_lord=md_lord,
        mahadasha_years=md_days / DAYS_PER_YEAR,
        mahadasha_days=md_days,
        active_ad_lord=sub.lord,
        active_ad_days=ad_days,
        active_pd_lord=subsub.lord,
        active_pd_days=pd_days,
        nakshatra=NAKSHATRAS[idx],
        nakshatra_index=idx,
    )


# ---------------------------------------------------------------------------
# Sub-period generation
# ---------------------------------------------------------------------------

def _subperiods(
    parent_lord: str,
    parent_days: float,
    level: int,
    start_anchor: str | None = None,
    first_dur: float | None = None,
) -> list[Period]:
    """Generate the nine sub-periods of a parent dasha.

    ``start_anchor`` overrides the usual "start from the parent lord" rule and
    ``first_dur`` truncates the opening period (both used for a partial
    balance-anchored parent).  Runs out at ``parent_days``.
    """
    pos = VIMSHOTTARI_INDEX[start_anchor or parent_lord]
    out: list[Period] = []
    offset = 0.0
    for k in range(_NINTH):
        lord = VIMSHOTTARI_ORDER[(pos + k) % 9]
        if k == 0 and first_dur is not None:
            dur = first_dur
        else:
            dur = period_days(parent_lord, lord)
        if offset + dur > parent_days:
            dur = max(parent_days - offset, 0.0)
        if dur > 0:
            out.append(Period(lord, offset, offset + dur, level))
        offset += dur
    return out


def mahadasha_timeline(moon_longitude: float, epochs: int = 1) -> list[Period]:
    """All mahadashas from birth (opening one is the balance) over cycles."""
    bal = dasha_balance(moon_longitude)
    periods: list[Period] = []
    offset = 0.0
    pos = bal.nakshatra_index % 9
    for _ in range(epochs):
        for k in range(_NINTH):
            lord = VIMSHOTTARI_ORDER[(pos + k) % 9]
            dur = bal.mahadasha_days if (k == 0 and _ == 0 and lord == bal.mahadasha_lord) else mahadasha_days(lord)
            periods.append(Period(lord, offset, offset + dur, 1))
            offset += dur
        pos = (pos + _NINTH) % 9
    return periods


def antardashas_of(period: Period, balance: Balance | None = None) -> list[Period]:
    """Antardashas inside a mahadasha.

    For the opening (balance) mahadasha the sequence begins at the birth Moon's
    sub-lord and is truncated to the AD balance; otherwise it begins at the
    mahadasha lord with full AD periods.
    """
    partial = balance is not None and period.lord == balance.mahadasha_lord
    return _subperiods(
        period.lord,
        period.duration_days,
        2,
        start_anchor=balance.active_ad_lord if partial else None,
        first_dur=balance.active_ad_days if partial else None,
    )


def pratyantardashas_of(ad: Period, balance: Balance | None = None, md_is_partial: bool = False) -> list[Period]:
    """Pratyantardashas inside an antardasha (refined only for the birth AD)."""
    most_refined = balance is not None and md_is_partial and ad.start_days == 0
    return _subperiods(
        ad.lord,
        ad.duration_days,
        3,
        start_anchor=balance.active_pd_lord if most_refined else None,
        first_dur=balance.active_pd_days if most_refined else None,
    )


def _locate(periods: list[Period], offset_days: float) -> Period | None:
    for p in periods:
        if p.start_days <= offset_days < p.end_days:
            return p
    return None


def current_periods(
    moon_longitude: float,
    epoch: datetime,
    instant: datetime,
    depth: int = 3,
) -> dict[int, Period]:
    """Active mahadasha (1), antardasha (2) and pratyantar (3) at ``instant``."""
    days = (instant - epoch).total_seconds() / 86400.0
    bal = dasha_balance(moon_longitude)
    md = _locate(mahadasha_timeline(moon_longitude), days)
    if md is None:
        raise ValueError("instant is outside the mahadasha timeline")
    result: dict[int, Period] = {1: md}

    ads = antardashas_of(md, bal)
    ad = _locate(ads, days - md.start_days)
    if ad is None:
        raise ValueError("instant is outside the antardasha timeline")
    result[2] = ad

    if depth >= 3:
        pds = pratyantardashas_of(ad, bal, md_is_partial=md.start_days == 0)
        pd = _locate(pds, days - md.start_days - ad.start_days)
        if pd is not None:
            result[3] = pd
    return result


def format_days(days: float) -> str:
    """Render days as ``Yy Mm Dd`` (year = 365.25 days, month = 30.4375 days)."""
    years, rem = divmod(days, 365.25)
    months, rem = divmod(rem, 365.25 / 12.0)
    days_f, _ = divmod(rem, 1.0)
    return f"{int(years)}y {int(months)}m {days_f:.0f}d"