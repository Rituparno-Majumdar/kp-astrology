"""Birth-time rectification (the KP "time of birth" method).

Given an approximate birth time and a handful of dated **life events** whose KP
house mappings the astrologer has judged, the rectifier scans a small time
window minute-by-minute and scores every candidate birth time against the
events.

The algorithm is a faithful port of the classic KP web rectification tool
("timeofbirth", P. Simon / V. Shankara) and follows the same logic:

* **Lagna sub-lord (LSL)** -- the sub-lord of the ascendant is the final judge
  of the chart.  When it is a significator of the houses an event fell into,
  that candidate time is rewarded (+2 per primary house, +1 per secondary
  house).  A **specificity weight** discounts "common" significators: if the
  LSL appears in the significator sets of many houses its testimony is weak
  (``1 - (n - 3)/9``, clamped to [0, 1]).
* **Vimshottari dasha** -- the mahadasha / antardasha / pratyantar lords
  running at each event must also signify the event's houses (full weight
  ``1 / 1 / 0.5`` for the primary house, a quarter of that for any secondary
  house).  Every event the dasha fails to confirm is reported as a **strike**.
* **Ruling planets** (optional) -- the LSL should belong to the classic
  five-lord ruling-planet set of the analysis (question) moment (+1).
* **Identity hint** (optional) -- a person with siblings tends to have the
  3rd house occupied; an only child usually has it empty (+0.25, weak).

The total score is ``lsl + 0.5 * dasha + rp + identity``.  The score curve is
then turned into a **posterior band** (historically called "credible
interval") via a softmax (temperature 1.5); it is the shortest contiguous
time span holding a target share of the mass.  Note this is NOT a statistical
credible interval -- there is no likelihood or prior -- it is a descriptive
band over the scanned 1-minute grid that reports which minutes dominate the
score.

Remarks on faithfulness
-----------------------
* Planet positions, cusps and the ayanamsa come from the Swiss Ephemeris
  (arc-second accurate) rather than the browser trigonometry of the original
  tool, so the scores are more precise, not less.
* The dasha periods at each event are anchored to the *candidate* birth
  moment and that moment's Moon, exactly as the reference implementation does.
* The rectification RP set is the classic five-lord set (day lord + asc/moon
  sign and star lords); kpastro's general :func:`~kpastro.ruling_planets`
  also adds the sub lords, which is not used here.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date as DateType, datetime, time as TimeType, timedelta, timezone
from typing import Iterable, Optional

from .constants import SIGN_LORDS, WEEKDAY_LORDS
from .dasha import current_periods
from .ephemeris import SwissEphemeris
from .significators import house_of_longitude
from .vedic import normalize_longitude, sign_name, star_lord, sub_lord

#: The nine grahas in KP output order.
PLANETS: tuple[str, ...] = (
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu",
)

#: Julian date of 2000-01-01 12:00 UT (the J2000 epoch).
_J2000_JD: float = 2451545.0
_J2000_UTC_NOON = datetime(2000, 1, 1, 12, 0)

#: Transit planets checked by :func:`transit_confirmation`.
TRANSIT_PLANETS: tuple[str, str] = ("Jupiter", "Saturn")

#: Score weights of the rectification heuristic, extracted so they are named
#: and auditable.  Values match the classic KP "timeofbirth" port; they are
#: heuristics, not calibrated against a held-out dataset.
SCORING: dict[str, float] = {
    # LSL (lagna sub-lord) testimony for the event's primary / secondary houses.
    "lsl_primary": 2.0,
    "lsl_secondary": 1.0,
    # Specificity discount: 1 - (n_signifying_houses - 3) / 9, clamped [0, 1].
    "specificity_floor_index": 3.0,
    "specificity_scale": 9.0,
    # Dasha confirmations: full weight for MD and AD, half for PD.
    "dasha_md_ad_weight": 1.0,
    "dasha_pd_weight": 0.5,
    # Any dasha lord matching a *secondary* house counts a quarter weight.
    "dasha_secondary_weight": 0.25,
    # Dasha testimony share of the total: total = lsl + share * dasha + ...
    "dasha_share": 0.5,
    # Ruling-planet bonus and weak identity (siblings) hint.
    "rp_bonus": 1.0,
    "identity_bonus": 0.25,
    # Posterior-band softmax temperature and target mass.
    "softmax_temperature": 1.5,
    "target_mass": 0.75,
}


# ---------------------------------------------------------------------------
# Input types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LifeEvent:
    """A dated event whose KP house mapping has been judged.

    ``primary`` is the main KP house the event fell into (1-12);
    ``secondary`` lists any extra houses it also connected to.  ``time`` is
    the local time of day used for the event moment (default noon, which is
    more than precise enough for dasha and transit checks).
    """

    date: DateType
    primary: int
    secondary: tuple[int, ...] = ()
    label: str = ""
    time: TimeType = TimeType(12, 0)

    def __post_init__(self) -> None:
        try:
            datetime.combine(self.date, self.time)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"event {self!r} has an invalid date/time") from exc
        validate_houses(self.primary, self.secondary)

    def jd_ut(self, tz_hours: float, eph: SwissEphemeris) -> float:
        """Julian date (UT) of the event moment."""
        local = datetime.combine(self.date, self.time)
        return eph.jd_ut(local - timedelta(hours=tz_hours))


@dataclass(frozen=True)
class IdentityInfo:
    """Optional biographical hints used as a weak additional signal."""

    siblings: Optional[int] = None  # number of siblings; None disables the hint


# ---------------------------------------------------------------------------
# Output types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EventScore:
    """Per-event breakdown of a candidate's score."""

    label: str
    date: DateType
    primary: int
    secondary: tuple[int, ...]
    lsl_score: float            # LSL contribution for this event (specificity applied)
    lsl_hit: bool               # the LSL signified the event's houses
    dasha_score: float          # dasha contribution for this event
    dasha_hit: bool             # at least one full-weight dasha confirmation
    mahadasha_lord: str = ""
    antardasha_lord: str = ""
    pratyantar_lord: str = ""


@dataclass(frozen=True)
class CandidateScore:
    """The full score of one candidate birth instant."""

    jd_ut: float
    offset_minutes: float        # minutes the candidate is from the approximation
    lsl: str                     # lagna sub-lord of this candidate
    specificity: float           # 1 - (n_sig - 3)/9 clamped to [0, 1]
    n_significating_houses: int  # how many houses the LSL signifies
    lsl_score: float
    dasha_score: float
    rp_score: float
    identity_score: float
    total: float
    strikes: int                 # events with dasha_score < 1 (no primary hit)
    events: tuple[EventScore, ...]


@dataclass(frozen=True)
class CredibleInterval:
    """Shortest contiguous time band holding `target_mass` of the softmax mass.

    This is a descriptive posterior band over the scanned minute grid (see
    :func:`credible_interval`) -- NOT a statistical credible interval: there is
    no likelihood or prior.  ``mass >= target_mass`` holds by construction.
    """

    start_ut: datetime
    end_ut: datetime
    peak_ut: datetime            # candidate with the highest score
    mass: float                  # posterior weight covered by [start, end]
    spread_minutes: float
    temperature: float = 1.5     # softmax temperature used to build the mass
    target_mass: float = 0.75    # requested mass share


@dataclass(frozen=True)
class EventTransit:
    """Whether transit Jupiter / Saturn confirmed an event's house."""

    label: str
    date: DateType
    jupiter: bool
    saturn: bool


@dataclass(frozen=True)
class TransitConfirmation:
    """Cross-check that transit Jupiter/Saturn confirmed the events."""

    matched: int
    total: int                   # 2 planets x len(events)
    per_event: tuple[EventTransit, ...]


@dataclass(frozen=True)
class RectificationResult:
    """Everything the scan produced, with candidates sorted best-first."""

    approx_ut: datetime
    candidates: tuple[CandidateScore, ...]
    best: CandidateScore
    credible: CredibleInterval
    settings: dict
    events: tuple[LifeEvent, ...]
    transit: Optional[TransitConfirmation] = None   # Jupiter/Saturn cross-check


# ---------------------------------------------------------------------------
# Validation + shared ordering
# ---------------------------------------------------------------------------

def validate_houses(primary: int, secondary: tuple[int, ...]) -> None:
    """Raise :class:`ValueError` unless the house numbers are 1..12.

    Used by :class:`LifeEvent` construction and by the scan functions so every
    entry path shares one validator.
    """
    if not 1 <= primary <= 12:
        raise ValueError(f"invalid primary house {primary!r}: must be 1-12")
    for h in secondary:
        if not 1 <= h <= 12:
            raise ValueError(f"invalid secondary house {h!r}: must be 1-12")


def _candidate_sort_key(c: "CandidateScore") -> tuple:
    """Single, deterministic ordering shared by ``best`` and the posterior band."""
    return (-c.total, -c.lsl_score, abs(c.offset_minutes))


# ---------------------------------------------------------------------------
# KP significator sets (the reference algorithm's computeSignificators)
# ---------------------------------------------------------------------------

def aspects_from_house(house: int, planet: str) -> set[int]:
    """Houses (1-12) aspected by a planet occupying ``house``.

    Every planet aspects the 7th house from itself; Venus, Moon, Mercury,
    Rahu and Ketu add nothing beyond it.  Mars adds the 4th, 7th and 8th;
    Jupiter the 5th, 7th and 9th; Saturn the 3rd, 7th and 10th.
    """
    out = {((house + 5) % 12) + 1}
    if planet == "Jupiter":
        for offset in (4, 6, 8):
            out.add(((house - 1 + offset) % 12) + 1)
    elif planet == "Mars":
        for offset in (3, 6, 7):
            out.add(((house - 1 + offset) % 12) + 1)
    elif planet == "Saturn":
        for offset in (2, 6, 9):
            out.add(((house - 1 + offset) % 12) + 1)
    return out


def house_significator_sets(
    positions: dict[str, float],
    cusps: list[float],
    star_lord_cache: Optional[dict[str, str]] = None,
) -> tuple[dict[int, frozenset[str]], dict[str, int]]:
    """KP significators of every house (rectification flavour).

    For each of the 12 houses:

    * the house cusp's **sub-lord** (the KP house lord) and **sign-lord**
      (ownership -- primary in Bhaav Nirdeshan),
    * every planet **occupying** the house, and its **star-lord**,
    * every planet **aspecting** the house (by KP aspect), and its star-lord.

    Returns ``(sets, house_map)`` where ``sets[h]`` is the frozen set of
    significator planets and ``house_map`` gives the house (1-12) each planet
    occupies.
    """
    slc = star_lord_cache or {p: star_lord(lon) for p, lon in positions.items()}
    house_map = {p: house_of_longitude(lon, cusps) for p, lon in positions.items()}

    sets: dict[int, set[str]] = {h: set() for h in range(1, 13)}
    for h in range(1, 13):
        sets[h].add(sub_lord(cusps[h - 1]))
        sets[h].add(SIGN_LORDS[sign_name(cusps[h - 1])])
    for planet, house in house_map.items():
        sets[house].add(planet)
        sets[house].add(slc[planet])
    for planet, house in house_map.items():
        for target in aspects_from_house(house, planet):
            sets[target].add(planet)
            sets[target].add(slc[planet])
    return {h: frozenset(s) for h, s in sets.items()}, house_map


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _datetime_from_jd(jd_ut: float) -> datetime:
    """Naive UTC datetime corresponding to a Julian date."""
    return _J2000_UTC_NOON + timedelta(days=jd_ut - _J2000_JD)


def _coerce_local(value: datetime | TimeType, birth) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.combine(birth.date, value)


def _chart_for(
    jd_ut: float,
    latitude: float,
    longitude: float,
    eph: SwissEphemeris,
) -> tuple[dict[str, float], list[float], float]:
    """Lean astro snapshot: sidereal positions, Placidus cusps, ascendant."""
    sider = eph.sidereal_positions(jd_ut)
    cusps, asc, _mc, _armc = eph.houses(jd_ut, latitude, longitude)
    positions = {name: lon for name, (lon, _speed) in sider.items()}
    return positions, cusps, asc


def _ruling_planet_set(
    jd_ut: float,
    latitude: float,
    longitude: float,
    eph: SwissEphemeris,
    tz_hours: float = 0.0,
) -> set[str]:
    """Classic five-lord RP set of a moment (day + asc/moon sign and star lords).

    The day-lord follows the **local** civil weekday at the moment, computed
    from ``tz_hours``, not the UTC weekday.
    """
    positions, cusps, asc = _chart_for(jd_ut, latitude, longitude, eph)
    moon_lon = positions["Moon"]
    local = _datetime_from_jd(jd_ut) + timedelta(hours=tz_hours)
    day_lord = WEEKDAY_LORDS[local.weekday() % 7]  # WEEKDAY_LORDS is Monday-first
    return {
        day_lord,
        SIGN_LORDS[sign_name(moon_lon)],
        star_lord(moon_lon),
        SIGN_LORDS[sign_name(asc)],
        star_lord(asc),
    }


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _scan_snapshot(
    jd_ut: float,
    eph: SwissEphemeris,
) -> tuple[float, dict[str, tuple[float, float]], dict[str, str]]:
    """Precompute what is constant across a ±60 minute scan.

    Only the Moon and the house cusps/ascendant change meaningfully across the
    scan window; the other planets move less than their sub-lord resolution.
    Returns ``(ayanamsa, slow positions sidereal+speed, star-lord cache)`` so a
    candidate needs only a Moon position + house computation per minute instead
    of a full 9-body ephemeris recalculation.
    """
    slow: dict[str, tuple[float, float]] = {}
    star_cache: dict[str, str] = {}
    for name, (lon, speed) in eph.tropical_positions(jd_ut).items():
        if name == "Moon":
            continue
        sid = normalize_longitude(lon - eph.ayanamsa(jd_ut))
        slow[name] = (sid, speed)
        star_cache[name] = star_lord(sid)
    return eph.ayanamsa(jd_ut), slow, star_cache


def score_candidate(
    jd_ut: float,
    latitude: float,
    longitude: float,
    events: Iterable[LifeEvent],
    tz_hours: float = 0.0,
    rp_set: Optional[set[str]] = None,
    identity: Optional[IdentityInfo] = None,
    eph: Optional[SwissEphemeris] = None,
    approx_jd: Optional[float] = None,
    event_jds: Optional[tuple[float, ...]] = None,
    _snapshot: Optional[tuple[float, dict[str, tuple[float, float]], dict[str, str]]] = None,
) -> CandidateScore:
    """Score a single candidate birth instant against the events.

    ``events`` are the judged life events; ``tz_hours`` converts their local
    dates to UTC.  ``rp_set`` and ``identity`` are optional weak signals.
    ``_snapshot`` is an internal optimisation supplied by :func:`rectify`; it
    pre-seeds the slow planets and star lords so each candidate only
    recomputes Moon + houses.
    """
    eph = eph or SwissEphemeris()
    events = tuple(events)
    if not events:
        raise ValueError("at least one LifeEvent is required")
    if event_jds is None:
        event_jds = tuple(ev.jd_ut(tz_hours, eph) for ev in events)
    if len(event_jds) != len(events):
        raise ValueError("event_jds must align one-to-one with events")
    for ev, ev_jd in zip(events, event_jds):
        if ev_jd < jd_ut:
            raise ValueError(
                f"event {ev!r} (jd {ev_jd:.2f}) predates the candidate birth "
                f"time (jd {jd_ut:.2f}); the dasha timeline cannot reach it"
            )

    if _snapshot is not None:
        _ayan, slow_positions, star_cache = _snapshot
        cusps, asc, _mc, _armc = eph.houses(jd_ut, latitude, longitude)
        moon_lon, _moon_speed = eph.body(jd_ut, "Moon")
        positions = {name: lon for name, (lon, _speed) in slow_positions.items()}
        positions["Moon"] = moon_lon
        star_cache = dict(star_cache)
        star_cache["Moon"] = star_lord(moon_lon)
    else:
        positions, cusps, asc = _chart_for(jd_ut, latitude, longitude, eph)
        moon_lon = positions["Moon"]
        star_cache = {p: star_lord(lon) for p, lon in positions.items()}

    sigs, house_map = house_significator_sets(positions, cusps, star_cache)

    lsl = sub_lord(asc)
    n_sig = sum(1 for house_set in sigs.values() if lsl in house_set)
    spec = min(1.0, max(0.0, (12 - n_sig) / SCORING["specificity_scale"]))

    epoch = _datetime_from_jd(jd_ut)

    event_scores: list[EventScore] = []
    lsl_total = 0.0
    dasha_total = 0.0
    for ev, ev_jd in zip(events, event_jds):
        ev_lsl = 0.0
        if ev.primary:
            if lsl in sigs.get(ev.primary, frozenset()):
                ev_lsl += SCORING["lsl_primary"]
            for h in ev.secondary:
                if lsl in sigs.get(h, frozenset()):
                    ev_lsl += SCORING["lsl_secondary"]
        ev_lsl *= spec
        lsl_total += ev_lsl

        ev_dash = 0.0
        md = ad = pd = ""
        try:
            per = current_periods(moon_lon, epoch, _datetime_from_jd(ev_jd), depth=3)
            md = per[1].lord
            ad = per[2].lord
            pd = per.get(3).lord if per.get(3) is not None else ""
        except ValueError as exc:
            raise ValueError(
                f"event {ev!r} lies outside the dasha timeline of the candidate "
                f"birth time: {exc}"
            ) from exc
        for lord, weight in (
            (md, SCORING["dasha_md_ad_weight"]),
            (ad, SCORING["dasha_md_ad_weight"]),
            (pd, SCORING["dasha_pd_weight"]),
        ):
            if not lord:
                continue
            if ev.primary and lord in sigs.get(ev.primary, frozenset()):
                ev_dash += weight
            elif ev.secondary and any(lord in sigs.get(h, frozenset()) for h in ev.secondary):
                ev_dash += SCORING["dasha_secondary_weight"]
        dasha_total += ev_dash

        event_scores.append(
            EventScore(
                label=ev.label,
                date=ev.date,
                primary=ev.primary,
                secondary=ev.secondary,
                lsl_score=ev_lsl,
                lsl_hit=ev_lsl > 0.0,
                dasha_score=ev_dash,
                dasha_hit=ev_dash >= 1.0,
                mahadasha_lord=md,
                antardasha_lord=ad,
                pratyantar_lord=pd,
            )
        )

    rp_score = SCORING["rp_bonus"] if rp_set is not None and lsl in rp_set else 0.0

    identity_score = 0.0
    if identity is not None and identity.siblings is not None:
        occ3 = sum(1 for house in house_map.values() if house == 3)
        if identity.siblings > 0 and occ3 >= 1:
            identity_score += SCORING["identity_bonus"]
        if identity.siblings == 0 and occ3 == 0:
            identity_score += SCORING["identity_bonus"]

    strikes = sum(1 for es in event_scores if es.dasha_score < 1.0)
    total = (
        lsl_total
        + SCORING["dasha_share"] * dasha_total
        + rp_score
        + identity_score
    )
    offset = 0.0 if approx_jd is None else (jd_ut - approx_jd) * 1440.0

    return CandidateScore(
        jd_ut=jd_ut,
        offset_minutes=offset,
        lsl=lsl,
        specificity=spec,
        n_significating_houses=n_sig,
        lsl_score=lsl_total,
        dasha_score=dasha_total,
        rp_score=rp_score,
        identity_score=identity_score,
        total=total,
        strikes=strikes,
        events=tuple(event_scores),
    )


def rectify(
    birth,
    approx_time: datetime | TimeType,
    events: Iterable[LifeEvent],
    window_min: float = 60.0,
    step_min: float = 1.0,
    *,
    use_rp: bool = False,
    analysis_time: Optional[datetime | TimeType] = None,
    identity: Optional[IdentityInfo] = None,
    ayanamsa: str = "lahiri",
    node: str = "true",
    eph: Optional[SwissEphemeris] = None,
) -> RectificationResult:
    """Scan ``±window_min`` around the approximate birth time and rank candidates.

    ``approx_time`` and ``analysis_time`` are in the birth's local timezone; a
    bare ``time`` is combined with ``birth.date``.  If ``analysis_time`` is
    omitted the current moment is used.  Setting ``use_rp=True`` adds the
    ruling-planet test against the analysis moment's classic five-lord set.
    """
    eph = eph or SwissEphemeris(ayanamsa=ayanamsa, node=node)
    events = tuple(events)
    if not events:
        raise ValueError("at least one LifeEvent is required")
    for ev in events:
        validate_houses(ev.primary, ev.secondary)

    local_approx = _coerce_local(approx_time, birth)
    approx_ut = local_approx - timedelta(hours=birth.tz_hours)
    approx_jd = eph.jd_ut(approx_ut)
    event_jds = tuple(ev.jd_ut(birth.tz_hours, eph) for ev in events)
    earliest_candidate = approx_jd - window_min / 1440.0
    for ev, ev_jd in zip(events, event_jds):
        if ev_jd < earliest_candidate:
            raise ValueError(
                f"event {ev!r} ({ev.date}) predates the earliest candidate birth "
                f"time; the dasha timeline cannot reach it"
            )

    rp_set = None
    if use_rp:
        an_local = _coerce_local(
            analysis_time or datetime.now(timezone.utc).replace(tzinfo=None), birth
        )
        an_jd = eph.jd_ut(an_local - timedelta(hours=birth.tz_hours))
        rp_set = _ruling_planet_set(
            an_jd, birth.latitude, birth.longitude, eph, birth.tz_hours
        )

    snapshot = _scan_snapshot(approx_jd, eph)
    n_steps = max(1, round(window_min * 2.0 / step_min))
    candidates: list[CandidateScore] = []
    for s in range(n_steps + 1):
        cand_jd = approx_jd - window_min / 1440.0 + (s * step_min) / 1440.0
        candidates.append(
            score_candidate(
                cand_jd,
                birth.latitude,
                birth.longitude,
                events,
                tz_hours=birth.tz_hours,
                rp_set=rp_set,
                identity=identity,
                eph=eph,
                approx_jd=approx_jd,
                event_jds=event_jds,
                _snapshot=snapshot,
            )
        )

    candidates.sort(key=_candidate_sort_key)

    best = candidates[0]
    credible = credible_interval(candidates)
    transit = transit_confirmation(
        best.jd_ut,
        birth.latitude,
        birth.longitude,
        events,
        tz_hours=birth.tz_hours,
        eph=eph,
    )
    return RectificationResult(
        approx_ut=approx_ut,
        candidates=tuple(candidates),
        best=best,
        credible=credible,
        settings={
            "window_min": window_min,
            "step_min": step_min,
            "use_rp": use_rp,
            "ayanamsa": ayanamsa,
            "node": node,
            "candidates": len(candidates),
        },
        events=events,
        transit=transit,
    )


# ---------------------------------------------------------------------------
# Cross-checks
# ---------------------------------------------------------------------------

def transit_confirmation(
    jd_ut: float,
    latitude: float,
    longitude: float,
    events: Iterable[LifeEvent],
    tz_hours: float = 0.0,
    eph: Optional[SwissEphemeris] = None,
) -> TransitConfirmation:
    """Count how often transit Jupiter/Saturn confirm the events' primary houses.

    A major event tends to manifest when Jupiter or Saturn transits a
    longitude whose **star-lord or sign-lord** is a significator of the
    event's house.  This is a cross-check and is deliberately *not* folded
    into the ranking score.
    """
    eph = eph or SwissEphemeris()
    events = tuple(events)
    positions, cusps, _asc = _chart_for(jd_ut, latitude, longitude, eph)
    star_cache = {p: star_lord(lon) for p, lon in positions.items()}
    sigs, _ = house_significator_sets(positions, cusps, star_cache)

    matched = 0
    total = 0
    per_event: list[EventTransit] = []
    for ev in events:
        ev_jd = ev.jd_ut(tz_hours, eph)
        transit = eph.sidereal_positions(ev_jd)
        house_set = sigs.get(ev.primary, frozenset())
        hits: list[bool] = []
        for planet in TRANSIT_PLANETS:
            total += 1
            lon = transit[planet][0]
            hit = bool(house_set) and (
                star_lord(lon) in house_set or SIGN_LORDS[sign_name(lon)] in house_set
            )
            if hit:
                matched += 1
            hits.append(hit)
        per_event.append(EventTransit(ev.label, ev.date, hits[0], hits[1]))
    return TransitConfirmation(matched, total, tuple(per_event))


def credible_interval(
    candidates: Iterable[CandidateScore],
    target_mass: float = 0.75,
) -> CredibleInterval:
    """Smallest time span holding ~``target_mass`` of the softmax posterior.

    Scores are converted to probabilities ``exp((score - max) / 1.5)``
    normalised over the whole scan.  The highest-scoring candidates are taken
    until the target mass accumulates; the interval is the span of their
    times, and the reported mass is re-measured over all candidates inside it.
    """
    cands = tuple(candidates)
    if not cands:
        raise ValueError("no candidates to build a credible interval from")
    temperature = float(SCORING["softmax_temperature"])
    target_mass = float(target_mass or SCORING["target_mass"])

    scores = [c.total for c in cands]
    peak = max(scores)
    weights = [math.exp((s - peak) / temperature) for s in scores]
    total = sum(weights)
    probs = [w / total for w in weights]

    # Time-ordered + cumulative weight for the single sliding pass.
    order = sorted(range(len(cands)), key=lambda i: cands[i].jd_ut)
    acc = 0.0
    j = 0
    best_span = math.inf
    best_lo = best_hi = None
    best_mass = 0.0
    for i in range(len(order)):
        while j < len(order) and acc < target_mass:
            acc += probs[order[j]]
            j += 1
        if acc >= target_mass:
            lo_idx, hi_idx = i, j - 1
            span = cands[order[hi_idx]].jd_ut - cands[order[lo_idx]].jd_ut
            if span < best_span - 1e-12 or (
                abs(span - best_span) <= 1e-12 and acc > best_mass
            ):
                best_span = span
                best_lo, best_hi, best_mass = lo_idx, hi_idx, acc
        acc -= probs[order[i]]

    if best_lo is None:
        # target_mass impossible (single candidate or mass < requested share).
        best_lo, best_hi = 0, len(order) - 1
        best_mass = 1.0

    # The band must contain the peak candidate (the highest-scored minute), so
    # expand the chosen window outward to include it.
    peak_cand = sorted(cands, key=_candidate_sort_key)[0]
    peak_pos = order.index(cands.index(peak_cand))
    if peak_pos < best_lo:
        best_lo = peak_pos
    elif peak_pos > best_hi:
        best_hi = peak_pos

    lo_jd = cands[order[best_lo]].jd_ut
    hi_jd = cands[order[best_hi]].jd_ut
    mass = sum(
        probs[idx]
        for idx in order
        if lo_jd - 1e-9 <= cands[idx].jd_ut <= hi_jd + 1e-9
    )

    return CredibleInterval(
        start_ut=_datetime_from_jd(lo_jd),
        end_ut=_datetime_from_jd(hi_jd),
        peak_ut=_datetime_from_jd(peak_cand.jd_ut),
        mass=mass,
        spread_minutes=(hi_jd - lo_jd) * 1440.0,
        temperature=temperature,
        target_mass=target_mass,
    )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def format_offset(minutes: float) -> str:
    """Render a signed offset as ``+12m`` / ``-3m``."""
    sign = "+" if minutes >= 0 else "-"
    value = round(abs(minutes))
    return f"{sign}{value}m"


def render_rectification(result: RectificationResult, birth, limit: int = 12) -> str:
    """Human-readable summary of a :class:`RectificationResult`."""
    tz = birth.tz_hours
    cfg = result.settings
    out = []
    out.append("=" * 72)
    out.append(" KP BIRTH-TIME RECTIFICATION")
    out.append("=" * 72)
    out.append(
        f" Reference: {birth.date} local @ {birth.place or '-'} (lat {birth.latitude:.4f}, "
        f"lon {birth.longitude:.4f})"
    )
    out.append(
        f" Window +/-{cfg['window_min']:g} min, step {cfg['step_min']:g} min, "
        f"{cfg['candidates']} candidates"
    )
    out.append(
        f" Ayanamsa: {cfg['ayanamsa']}   node: {cfg['node']}   "
        f"RP test: {'yes' if cfg['use_rp'] else 'no'}   events: {len(result.events)}"
    )
    out.append("")

    ci = result.credible
    out.append(
        f" Posterior band ({ci.mass:.0%} mass of {ci.target_mass:.0%} target, "
        f"T={ci.temperature:g}): "
        f"{_fmt_full(_dt_local(ci.start_ut, tz))} - {_fmt_full(_dt_local(ci.end_ut, tz))}   "
        f"peak {_fmt_full(_dt_local(ci.peak_ut, tz))}   (spread {ci.spread_minutes:.0f} min)"
    )
    out.append(
        "   (descriptive softmax band over the scanned grid, NOT a statistical "
        "credible interval)"
    )
    out.append("")

    out.append(
        "  #  Local  Offset    LSL        Spec   LSL  Dasha  RP  ID  Strikes  Total"
    )
    out.append("-" * len(out[-1]))
    for i, c in enumerate(result.candidates[:limit], start=1):
        out.append(
            f" {i:>2}  {_fmt_hm(_jd_local(c.jd_ut, tz))} "
            f"{format_offset(c.offset_minutes):>6}   {c.lsl:<9} {c.specificity:4.2f} "
            f"{c.lsl_score:4.1f}  {c.dasha_score:5.1f}  "
            f"{c.rp_score:.0f}  {c.identity_score:4.2f}  {c.strikes:>3}      {c.total:5.2f}"
        )
    out.append("")

    b = result.best
    out.append(
        f" Best candidate: {_fmt_full(_jd_local(b.jd_ut, tz))}   "
        f"LSL {b.lsl} (signifies {b.n_significating_houses}/12 houses, spec {b.specificity:.2f})"
    )
    out.append(
        f" Score: LSL {b.lsl_score:.2f}  +  0.5*dasha {b.dasha_score:.2f}  "
        f"+  RP {b.rp_score:.0f}  +  identity {b.identity_score:.2f}  =  {b.total:.2f}"
    )
    out.append("")
    out.append(" Event breakdown of the best candidate:")
    header = f" {'Event':<24} {'Date':<12} {'Houses':<14} {'LSL':>6} {'MD':>9} {'AD':>9} {'PD':>9} {'Dash':>6}"
    out.append(header)
    out.append("-" * len(header))
    for es in b.events:
        houses = str(es.primary) + "".join(f",{h}" for h in es.secondary)
        out.append(
            f" {(es.label or 'event'):<24} {es.date:%Y-%m-%d} "
            f"{houses:<14} {es.lsl_score:6.1f} "
            f"{es.mahadasha_lord:>9} {es.antardasha_lord:>9} {es.pratyantar_lord:>9} "
            f"{'hit' if es.dasha_hit else 'miss':>6}"
        )
    out.append("")

    if result.transit is not None:
        t = result.transit
        out.append(" Jupiter/Saturn transit cross-check (independent of the score):")
        out.append(f"  confirmed {t.matched}/{t.total} transit tests")
        for et in t.per_event:
            out.append(
                f"    {(et.label or 'event'):<24} {et.date:%Y-%m-%d}  "
                f"Jupiter {'yes' if et.jupiter else 'no'}, "
                f"Saturn {'yes' if et.saturn else 'no'}"
            )
        out.append("")
    out.append("=" * 72)
    return "\n".join(out)


def _jd_local(jd_ut: float, tz_hours: float) -> datetime:
    return _datetime_from_jd(jd_ut) + timedelta(hours=tz_hours)


def _dt_local(ut: datetime, tz_hours: float) -> datetime:
    return ut + timedelta(hours=tz_hours)


def _fmt_full(local: datetime) -> str:
    return f"{local:%Y-%m-%d %H:%M}"


def _fmt_hm(local: datetime) -> str:
    return f"{local:%H:%M}"