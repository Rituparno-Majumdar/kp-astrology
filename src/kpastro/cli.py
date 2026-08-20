"""Command line interface for kpastro.

Subcommands
-----------
natal                compute a complete KP birth chart
horary               KP horary chart from a 1-249 number
dasha                Vimshottari dasha timeline only
rulings              ruling planets for a moment
ayanamsa             ayanamsa value for a date
download-ephemeris   fetch Swiss Ephemeris data files for full precision
"""

from __future__ import annotations

import argparse
import sys
from datetime import date as DateType, time as TimeType

from . import __version__
from .chart import BirthInfo, compute_chart, render_chart
from .dasha import mahadasha_timeline
from .ephemeris import SwissEphemeris, download_ephemeris
from .horary import ascendant_from_kp_number
from .significators import ruling_planets
from .vedic import format_longitude


def _parse_date(arg: str) -> DateType:
    return DateType.fromisoformat(arg)


def _parse_time(arg: str) -> TimeType:
    parts = arg.split(":")
    if len(parts) == 2:
        hh, mm = map(int, parts)
        return TimeType(hh, mm)
    if len(parts) == 3:
        hh, mm, ss = map(int, parts)
        return TimeType(hh, mm, ss)
    raise argparse.ArgumentTypeError("time must be HH:MM or HH:MM:SS")


def cmd_natal(args: argparse.Namespace) -> int:
    birth = BirthInfo(
        date=_parse_date(args.date),
        time=args.time,
        latitude=args.lat,
        longitude=args.lon,
        tz_hours=args.tz,
        place=args.place,
    )
    chart = compute_chart(birth, ayanamsa=args.ayanamsa, node=args.node)
    print(render_chart(chart))
    return 0


def cmd_horary(args: argparse.Namespace) -> int:
    q = ascendant_from_kp_number(args.number)
    birth = BirthInfo(
        date=_parse_date(args.date),
        time=args.time,
        latitude=args.lat,
        longitude=args.lon,
        tz_hours=args.tz,
        place=args.place,
    )
    chart = compute_chart(birth, ayanamsa=args.ayanamsa, node=args.node)
    print("=" * 72)
    print(" KRISHNAMURTI PADDHATI - horary (Prashna)")
    print("=" * 72)
    print(f" KP number : {q['number']}")
    print(f" span      : {format_longitude(q['span'][0])} - {format_longitude(q['span'][1])}")
    print(
        f" Ascendant : {format_longitude(q['ascendant'])} {q['sign']} - "
        f"sign-lord {q['sign_lord']}, star {q['star']} ({q['star_lord']}), "
        f"sub {q['sub_lord']}, sub-sub {q['sub_sub_lord']}"
    )
    print("")
    print(" Moment chart (planets & Placidus cusps for the query instant):")
    print(render_chart(chart))
    return 0


def cmd_dasha(args: argparse.Namespace) -> int:
    birth = BirthInfo(
        date=_parse_date(args.date),
        time=args.time,
        latitude=args.lat,
        longitude=args.lon,
        tz_hours=args.tz,
        place=args.place,
    )
    chart = compute_chart(birth, ayanamsa=args.ayanamsa, node=args.node)
    epoch = birth.utc_datetime()
    print(f" Birth Moon : {args.date} {args.time} (tz {args.tz:+.1f})")
    print(
        f" Balance MD : {chart.balance.mahadasha_lord} "
        f"{format_dash_days(chart.balance)} "
        f"| AD {chart.balance.active_ad_lord} "
        f"| PD {chart.balance.active_pd_lord}"
    )
    print("")
    print(" Mahadashas:")
    for md in chart.mahadashas:
        s, e = md.as_datetimes(epoch)
        tag = "  (balance)" if md is chart.mahadashas[0] else ""
        print(f"  {md.lord:<10} {s:%Y-%m-%d}  {e:%Y-%m-%d}  {md.duration_days:8.1f}d{tag}")
    return 0


def format_dash_days(balance) -> str:
    days = balance.mahadasha_days
    years, rem = divmod(days, 365.25)
    months, rem = divmod(rem, 30.4375)
    return f"{int(years)}y {int(months)}m {rem:.1f}d"


def cmd_rulings(args: argparse.Namespace) -> int:
    chart = compute_chart(
        BirthInfo(
            date=_parse_date(args.date),
            time=args.time,
            latitude=args.lat,
            longitude=args.lon,
            tz_hours=args.tz,
            place=args.place,
        ),
        ayanamsa=args.ayanamsa,
        node=args.node,
    )
    print("Ruling planets (are the day/ascendant/Moon lords):")
    for rp in chart.ruling:
        print(f"  {rp.planet:<10} {rp.source}")
    return 0


def cmd_ayanamsa(args: argparse.Namespace) -> int:
    from datetime import datetime as _dt
    eph = SwissEphemeris(ayanamsa=args.ayanamsa)
    when = _dt.combine(DateType.fromisoformat(args.date), TimeType(12, 0))
    jd = eph.jd_ut(when)
    ayan = eph.ayanamsa(jd)
    print(f" {args.ayanamsa:<7} ayanamsa on {args.date} (12:00 UT) = {format_longitude(ayan)}")
    return 0


def cmd_download(args: argparse.Namespace) -> int:
    target = args.dir or None
    paths = download_ephemeris(target)
    for p in paths:
        print(f"  ok  {p} ({p.stat().st_size:,} bytes)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="kpastro",
        description="Krishnamurti Paddhati (KP) astrology calculations.",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    def add_common(sp: argparse.ArgumentParser, with_number: bool = False) -> None:
        sp.add_argument("--date", default=DateType.today().isoformat(), help="YYYY-MM-DD (default today)")
        sp.add_argument("--time", default="12:00", type=_parse_time, help="HH:MM or HH:MM:SS local (default 12:00)")
        sp.add_argument("--tz", type=float, default=5.5, help="UTC offset in hours (default +5.5)")
        sp.add_argument("--lat", type=float, required=True, help="geographic latitude (deg)")
        sp.add_argument("--lon", type=float, required=True, help="geographic longitude (deg)")
        sp.add_argument("--place", default="", help="place label")
        sp.add_argument("--ayanamsa", choices=("lahiri", "kp", "kp_old"), default="lahiri")
        sp.add_argument("--node", choices=("mean", "true"), default="mean")
        if with_number:
            sp.add_argument("--number", type=int, required=True, help="KP horary number 1-249")

    sp = sub.add_parser("natal", help="complete KP birth chart")
    add_common(sp)
    sp.set_defaults(func=cmd_natal)

    sp = sub.add_parser("horary", help="KP horary chart from a 1-249 number")
    add_common(sp, with_number=True)
    sp.set_defaults(func=cmd_horary)

    sp = sub.add_parser("dasha", help="Vimshottari dasha timeline")
    add_common(sp)
    sp.set_defaults(func=cmd_dasha)

    sp = sub.add_parser("rulings", help="ruling planets of a moment")
    add_common(sp)
    sp.set_defaults(func=cmd_rulings)

    sp = sub.add_parser("ayanamsa", help="ayanamsa value on a date")
    sp.add_argument("--date", default=DateType.today().isoformat(), help="YYYY-MM-DD (default today)")
    sp.add_argument("--ayanamsa", choices=("lahiri", "kp", "kp_old"), default="lahiri")
    sp.set_defaults(func=cmd_ayanamsa)

    sp = sub.add_parser("download-ephemeris", help="download Swiss Ephemeris data files")
    sp.add_argument("--dir", default=None, help="target directory (default ~/.kpastro/ephe)")
    sp.set_defaults(func=cmd_download)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())