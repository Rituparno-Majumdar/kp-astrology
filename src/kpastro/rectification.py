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
then turned into a **credible interval** via a softmax (temperature 1.5) so
the honest headline is a range of times, not a single minute.

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
from datetime import date as DateType, datetime, time as TimeType, timedelta
from typing import Iterable, Optional

from .constants import SIGN_LORDS, WEEKDAY_LORDS
from .dasha import current_periods
from .ephemeris import SwissEphemeris
from .significators import house_of_longitude
from .vedic import sign_name, star_lord, sub_lord

#: The nine grahas in KP output order.
PLANETS: tuple[str, ...] = (
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu",
)

#: Julian date of 2000-01-01 12:00 UT (the J2000 epoch).
_J2000_JD: float = 2451545.0
_J2000_UTC_NOON = datetime(2000, 1, 1, 12, 0)

#: Transit planets checked by :func:`transit_confirmation`.
TRANSIT_PLANETS: tuple[str, str] = ("Jupiter", "Saturn")


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
    """A posterior interval over candidate times (softmax temperature 1.5)."""

    start_ut: datetime
    end_ut: datetime
    peak_ut: datetime            # candidate with the highest score
    mass: float                  # posterior weight covered by [start, end]
    spread_minutes: float


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

    * the house cusp's **sub-lord** (the KP house lord),
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
) -> set[str]:
    """Classic five-lord RP set of a moment (day + asc/moon sign and star lords)."""
    positions, cusps, asc = _chart_for(jd_ut, latitude, longitude, eph)
    moon_lon = positions["Moon"]
    # Julian-day weekday with 0 = Sunday (the reference algorithm's formula).
    js_weekday = math.floor(jd_ut + 1.5) % 7
    day_lord = WEEKDAY_LORDS[(js_weekday + 6) % 7]  # WEEKDAY_LORDS is Monday-first
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
) -> CandidateScore:
    """Score a single candidate birth instant against the events.

    ``events`` are the judged life events; ``tz_hours`` converts their local
    dates to UTC.  ``rp_set`` and ``identity`` are optional weak signals.
    """
    eph = eph or SwissEphemeris()
    events = tuple(events)
    if not events:
        raise ValueError("at least one LifeEvent is required")
    if event_jds is None:
        event_jds = tuple(ev.jd_ut(tz_hours, eph) for ev in events)
    if len(event_jds) != len(events):
        raise ValueError("event_jds must align one-to-one with events")

    positions, cusps, asc = _chart_for(jd_ut, latitude, longitude, eph)
    star_cache = {p: star_lord(lon) for p, lon in positions.items()}
    sigs, house_map = house_significator_sets(positions, cusps, star_cache)

    lsl = sub_lord(asc)
    n_sig = sum(1 for house_set in sigs.values() if lsl in house_set)
    spec = min(1.0, max(0.0, (12 - n_sig) / 9.0))

    epoch = _datetime_from_jd(jd_ut)
    moon_lon = positions["Moon"]

    event_scores: list[EventScore] = []
    lsl_total = 0.0
    dasha_total = 0.0
    for ev, ev_jd in zip(events, event_jds):
        ev_lsl = 0.0
        if ev.primary:
            if lsl in sigs[ev.primary]:
                ev_lsl += 2.0
            for h in ev.secondary:
                if lsl in sigs[h]:
                    ev_lsl += 1.0
        ev_lsl *= spec
        lsl_total += ev_lsl

        ev_dash = 0.0
        md = ad = pd = ""
        try:
            per = current_periods(moon_lon, epoch, _datetime_from_jd(ev_jd), depth=3)
            md = per[1].lord
            ad = per[2].lord
            pd = per.get(3).lord if per.get(3) is not None else ""
        except ValueError:
            pass  # event before birth or beyond the timeline: no dasha testimony
        for lord, weight in ((md, 1.0), (ad, 1.0), (pd, 0.5)):
            if not lord:
                continue
            if ev.primary and lord in sigs[ev.primary]:
                ev_dash += weight
            elif ev.secondary and any(lord in sigs[h] for h in ev.secondary):
                ev_dash += 0.25
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

    rp_score = 1.0 if rp_set is not None and lsl in rp_set else 0.0

    identity_score = 0.0
    if identity is not None and identity.siblings is not None:
        occ3 = sum(1 for house in house_map.values() if house == 3)
        if identity.siblings > 0 and occ3 >= 1:
            identity_score += 0.25
        if identity.siblings == 0 and occ3 == 0:
            identity_score += 0.25

    strikes = sum(1 for es in event_scores if es.dasha_score < 1.0)
    total = lsl_total + 0.5 * dasha_total + rp_score + identity_score
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
        if not 1 <= ev.primary <= 12:
            raise ValueError(f"event {ev!r} has an invalid primary house")
        if any(not 1 <= h <= 12 for h in ev.secondary):
            raise ValueError(f"event {ev!r} has an invalid secondary house")

    local_approx = _coerce_local(approx_time, birth)
    approx_ut = local_approx - timedelta(hours=birth.tz_hours)
    approx_jd = eph.jd_ut(approx_ut)
    event_jds = tuple(ev.jd_ut(birth.tz_hours, eph) for ev in events)

    rp_set = None
    if use_rp:
        an_local = _coerce_local(analysis_time or datetime.utcnow(), birth)
        an_jd = eph.jd_ut(an_local - timedelta(hours=birth.tz_hours))
        rp_set = _ruling_planet_set(an_jd, birth.latitude, birth.longitude, eph)

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
            )
        )

    candidates.sort(
        key=lambda c: (-c.total, -c.lsl_score, abs(c.offset_minutes))
    )

    best = candidates[0]
    credible = credible_interval(candidates)
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
    scores = [c.total for c in cands]
    peak = max(scores)
    weights = [math.exp((s - peak) / 1.5) for s in scores]
    total = sum(weights)
    prob_by_jd = {c.jd_ut: w / total for c, w in zip(cands, weights)}

    order = sorted(range(len(cands)), key=lambda i: weights[i], reverse=True)
    taken: list[int] = []
    acc = 0.0
    for i in order:
        taken.append(i)
        acc += weights[i] / total
        if acc >= target_mass:
            break

    jds = [cands[i].jd_ut for i in taken]
    lo, hi = min(jds), max(jds)
    mass = sum(
        p for jd, p in prob_by_jd.items() if lo - 1e-9 <= jd <= hi + 1e-9
    )
    return CredibleInterval(
        start_ut=_datetime_from_jd(lo),
        end_ut=_datetime_from_jd(hi),
        peak_ut=_datetime_from_jd(cands[order[0]].jd_ut),
        mass=mass,
        spread_minutes=(hi - lo) * 1440.0,
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
        f" Credible range ({ci.mass:.0%} mass): "
        f"{_fmt_full(_dt_local(ci.start_ut, tz))} - {_fmt_full(_dt_local(ci.end_ut, tz))}   "
        f"peak {_fmt_full(_dt_local(ci.peak_ut, tz))}   (spread {ci.spread_minutes:.0f} min)"
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