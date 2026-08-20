"""A complete KP chart: compute, then render as professional text tables."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as DateType, datetime, timedelta, time as TimeType

from .constants import PLANET_ABBR
from .dasha import (
    Balance,
    Period,
    antardashas_of,
    current_periods,
    dasha_balance,
    format_days,
    mahadasha_timeline,
)
from .ephemeris import SwissEphemeris
from .significators import (
    Signification,
    cusp_sub_lords,
    house_significations,
    house_of_longitude,
    planet_significations,
    ruling_planets,
)
from .vedic import format_longitude, point_info


@dataclass(frozen=True)
class BirthInfo:
    """Birth / event details. ``time`` is local; ``tz_hours`` is the UTC offset."""
    date: DateType
    time: TimeType
    latitude: float
    longitude: float
    tz_hours: float = 0.0
    place: str = ""

    def utc_datetime(self) -> datetime:
        local = datetime.combine(self.date, self.time)
        return local - timedelta(hours=self.tz_hours)


@dataclass(frozen=True)
class PlanetPos:
    name: str
    longitude: float
    house: int
    sign: str
    sign_degree: float
    sign_lord: str
    star: str
    star_lord: str
    sub_lord: str
    sub_sub_lord: str
    pada: int
    speed_deg_day: float
    retrograde: bool


@dataclass(frozen=True)
class CuspPos:
    house: int
    longitude: float
    sign: str
    sign_lord: str
    star: str
    star_lord: str
    sub_lord: str
    sub_sub_lord: str


@dataclass
class Chart:
    birth: BirthInfo
    jd_ut: float
    ayanamsa: float
    ayanamsa_mode: str
    node: str
    planets: list[PlanetPos]
    cusps: list[CuspPos]
    ascendant: float
    midheaven: float
    armc: float
    planet_lon: dict[str, float]
    balance: Balance
    mahadashas: list[Period]
    current: dict[int, Period]
    planet_significators: dict[str, list[Signification]]
    house_significators: list[list[tuple[str, int]]]
    cusp_sublords: dict[int, str]
    ruling: list = field(default_factory=list)


def compute_chart(
    birth: BirthInfo,
    ayanamsa: str = "lahiri",
    node: str = "mean",
    eph: SwissEphemeris | None = None,
) -> Chart:
    """Compute every KP layer for a birth chart."""
    eph = eph or SwissEphemeris(ayanamsa=ayanamsa, node=node)
    dt_utc = birth.utc_datetime()
    jd = eph.jd_ut(dt_utc)
    ayan = eph.ayanamsa(jd)
    sider = eph.sidereal_positions(jd)
    cusps, asc, mc, armc = eph.houses(jd, birth.latitude, birth.longitude)

    planets: list[PlanetPos] = []
    for name in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn",
                 "Rahu", "Ketu"):
        lon, speed = sider[name]
        info = point_info(lon)
        planets.append(
            PlanetPos(
                name=name,
                longitude=lon,
                house=house_of_longitude(lon, cusps),
                sign=info.sign,
                sign_degree=info.sign_degree,
                sign_lord=info.sign_lord,
                star=info.star,
                star_lord=info.star_lord,
                sub_lord=info.sub_lord,
                sub_sub_lord=info.sub_sub_lord,
                pada=info.pada,
                speed_deg_day=speed,
                retrograde=speed < 0 and name not in ("Rahu", "Ketu"),
            )
        )

    cusp_pos: list[CuspPos] = []
    for i, c in enumerate(cusps):
        info = point_info(c)
        cusp_pos.append(
            CuspPos(
                house=i + 1,
                longitude=c,
                sign=info.sign,
                sign_lord=info.sign_lord,
                star=info.star,
                star_lord=info.star_lord,
                sub_lord=info.sub_lord,
                sub_sub_lord=info.sub_sub_lord,
            )
        )

    moon_lon = sider["Moon"][0]
    balance = dasha_balance(moon_lon)
    mds = mahadasha_timeline(moon_lon)
    current = current_periods(moon_lon, dt_utc, dt_utc, depth=3)

    positions = {name: lon for name, (lon, _) in sider.items()}
    chart = Chart(
        birth=birth,
        jd_ut=jd,
        ayanamsa=ayan,
        ayanamsa_mode=ayanamsa,
        node=node,
        planets=planets,
        cusps=cusp_pos,
        ascendant=asc,
        midheaven=mc,
        armc=armc,
        planet_lon=positions,
        balance=balance,
        mahadashas=mds,
        current=current,
        planet_significators=planet_significations(positions, cusps),
        house_significators=house_significations(positions, cusps),
        cusp_sublords=cusp_sub_lords(cusps),
        ruling=[
            rp
            for rp in ruling_planets(asc, moon_lon, dt_utc.weekday())
        ],
    )
    return chart


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _dms(lon: float) -> str:
    return format_longitude(lon, arcsec=False)


def render_planets(chart: Chart) -> str:
    lines = [
        f" {'Planet':<9} {'Longitude':>10} {'Sign':<12} {'Star':<18} "
        f"{'Sub':<9} {'Sub-Sub':<9} {'House':>5} {'R':>2}"
    ]
    lines.append("-" * len(lines[0]))
    for p in sorted(chart.planets, key=lambda x: x.longitude):
        abbr = PLANET_ABBR[p.name]
        lines.append(
            f" {p.name:<9} {_dms(p.sign_degree) + ' ' + p.sign:<10} {p.sign:<12} "
            f"{p.star:<18} {p.sub_lord:<9} {p.sub_sub_lord:<9} {p.house:>5} "
            f"{'R' if p.retrograde else '.':>2}"
        )
    return "\n".join(lines)


def render_cusps(chart: Chart) -> str:
    lines = [
        f" {'House':>5} {'Cusp':>10} {'Sign':<12} {'Star':<18} {'Sub':<9} {'Sub-Sub':<9}"
    ]
    lines.append("-" * len(lines[0]))
    for c in chart.cusps:
        lines.append(
            f" {c.house:>5} {_dms(c.longitude % 30.0):>10} {c.sign:<12} "
            f"{c.star:<18} {c.sub_lord:<9} {c.sub_sub_lord:<9}"
        )
    return "\n".join(lines)


def render_significators(chart: Chart) -> str:
    lines = [" House  Significators (tier: 1 occupant, 2 occupant-star, 3 cuspal lord, 4 cuspal-star)"]
    lines.append("-" * len(lines[0]))
    for i, tiers in enumerate(chart.house_significators, start=1):
        sig = ", ".join(f"{p}({t})" for p, t in tiers) or "—"
        lines.append(f"  {i:>4}   {sig}")
    return "\n".join(lines)


def render_ruling(chart: Chart) -> str:
    return "\n".join(f"  {rp.planet:<10} {rp.source}" for rp in chart.ruling)


def render_dasha(chart: Chart) -> str:
    epoch = chart.birth.utc_datetime()
    lines = [" Mahadasha timeline (1 yr = 365.25 d):"]
    lines.append("-" * 46)
    lines.append(f" {'Lord':<10} {'Start':>10} {'End':>10} {'Days':>9}")
    for md in chart.mahadashas:
        start, end = md.as_datetimes(epoch)
        lines.append(
            f" {md.lord:<10} {start:%Y-%m-%d} {end:%Y-%m-%d} {md.duration_days:>8.1f}"
        )
    cur = chart.current
    lines.append("")
    lines.append(
        f" At birth: MD {cur[1].lord} ({_days(cur[1])}), "
        f"AD {cur[2].lord} ({_days(cur[2])}), "
        f"PD {cur[3].lord} ({_days(cur[3])})"
    )
    return "\n".join(lines)


def _days(period: Period) -> str:
    return format_days(period.duration_days)


def render_chart(chart: Chart) -> str:
    """Human-readable representation of the full KP chart."""
    birth = chart.birth
    out = []
    out.append("=" * 72)
    out.append(" KRISHNAMURTI PADDHATI  -  birth chart")
    out.append("=" * 72)
    out.append(
        f" {birth.date} {birth.time:%H:%M}  ({birth.latitude:.4f}, {birth.longitude:.4f})"
        f"  tz={birth.tz_hours:+.1f}  {birth.place}".rstrip()
    )
    out.append(
        f" Ayanamsa: {chart.ayanamsa_mode} = {format_longitude(chart.ayanamsa)}  "
        f"node: {chart.node}  |  Asc {format_longitude(chart.ascendant)}  "
        f"MC {format_longitude(chart.midheaven)}"
    )
    out.append("")
    out.append("PLANETS (sidereal, KP subdivision)")
    out.append(render_planets(chart))
    out.append("")
    out.append("HOUSE CUSPS (Placidus, sidereal)")
    out.append(render_cusps(chart))
    out.append("")
    out.append("SIGNIFICATORS (Bhaav Nirdeshan)")
    out.append(render_significators(chart))
    out.append("")
    out.append("RULING PLANETS")
    out.append(render_ruling(chart))
    out.append("")
    out.append("VIMSHOTTARI DASHA")
    out.append(render_dasha(chart))
    out.append("")
    out.append("=" * 72)
    return "\n".join(out)