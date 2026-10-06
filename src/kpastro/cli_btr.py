"""Command-line interface for birth-time rectification (kpastro-btr).

Loads life events from a JSON file and scores candidate birth times within an
approximate window using Krishnamurti Paddhati (KP) rectification heuristics.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date as DateType, datetime, time as TimeType
from pathlib import Path
from typing import Any, Optional

from . import __version__
from .chart import BirthInfo
from .cli import _date_arg, _parse_time
from .rectification import (
    IdentityInfo,
    LifeEvent,
    rectify,
    render_rectification,
)


def _parse_datetime_or_time(arg: str) -> datetime | TimeType:
    """Parse either an ISO datetime (YYYY-MM-DD HH:MM[:SS]) or a bare time (HH:MM[:SS])."""
    try:
        return datetime.fromisoformat(arg)
    except ValueError:
        pass
    if " " in arg:
        parts = arg.split(" ", 1)
        try:
            d = DateType.fromisoformat(parts[0])
            t = _parse_time(parts[1])
            return datetime.combine(d, t)
        except Exception:
            pass
    return _parse_time(arg)


def load_events_json(
    source: str | Path,
) -> tuple[list[LifeEvent], dict[str, Any], dict[str, Any]]:
    """Load life events and optional birth/scan defaults from a JSON file or stream.

    The JSON root may be:
    * a list of event objects: ``[{"date": "...", "primary": 10, ...}, ...]``
    * an object with an ``"events"`` array: ``{"events": [...], "birth": {...}}``

    Each event must contain:
    * ``date``: event date in ``YYYY-MM-DD`` format
    * ``primary`` (or ``primary_house`` / ``house``): integer house (1-12)

    Optional event fields:
    * ``secondary`` (or ``secondary_houses``): integer or list of integers (1-12)
    * ``label`` (or ``name`` / ``description``): event label string
    * ``time``: event time of day (default noon)

    Returns:
        tuple of (events_list, birth_defaults, scan_defaults)
    """
    if str(source) == "-":
        content = sys.stdin.read()
    else:
        path = Path(source)
        if not path.is_file():
            raise ValueError(f"events file not found: {source}")
        content = path.read_text(encoding="utf-8")

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in events file: {exc}") from None

    birth_defaults: dict[str, Any] = {}
    scan_defaults: dict[str, Any] = {}

    if isinstance(data, list):
        raw_events = data
    elif isinstance(data, dict):
        if "events" not in data or not isinstance(data["events"], list):
            raise ValueError(
                "JSON object must contain an 'events' list"
            )
        raw_events = data["events"]
        if "birth" in data and isinstance(data["birth"], dict):
            birth_defaults = data["birth"]
        for key in ("window", "window_min", "step", "step_min", "ayanamsa", "node", "use_rp", "siblings"):
            if key in data:
                scan_defaults[key] = data[key]
    else:
        raise ValueError("JSON root must be a list or an object with an 'events' list")

    if not raw_events:
        raise ValueError("at least one LifeEvent is required in events JSON")

    events: list[LifeEvent] = []
    for idx, item in enumerate(raw_events, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"event #{idx} is not a JSON object")

        # Date parsing
        date_raw = item.get("date") or item.get("event_date")
        if not date_raw:
            raise ValueError(f"event #{idx} is missing required 'date'")
        try:
            ev_date = DateType.fromisoformat(str(date_raw))
        except ValueError:
            raise ValueError(
                f"event #{idx} has invalid date {date_raw!r}; use YYYY-MM-DD"
            ) from None

        # Primary house parsing
        primary_raw = item.get("primary")
        if primary_raw is None:
            primary_raw = item.get("primary_house")
        if primary_raw is None:
            primary_raw = item.get("house")
        if primary_raw is None:
            raise ValueError(f"event #{idx} is missing required 'primary' house")
        try:
            primary = int(primary_raw)
        except (TypeError, ValueError):
            raise ValueError(
                f"event #{idx} primary house must be an integer, got {primary_raw!r}"
            ) from None

        # Secondary houses parsing
        secondary_raw = item.get("secondary")
        if secondary_raw is None:
            secondary_raw = item.get("secondary_houses")
        if secondary_raw is None:
            secondary_tuple: tuple[int, ...] = ()
        elif isinstance(secondary_raw, (int, str)):
            try:
                secondary_tuple = (int(secondary_raw),)
            except ValueError:
                raise ValueError(
                    f"event #{idx} invalid secondary house {secondary_raw!r}"
                ) from None
        elif isinstance(secondary_raw, (list, tuple)):
            try:
                secondary_tuple = tuple(int(h) for h in secondary_raw)
            except (TypeError, ValueError):
                raise ValueError(
                    f"event #{idx} secondary houses must be integers, got {secondary_raw!r}"
                ) from None
        else:
            raise ValueError(
                f"event #{idx} unexpected secondary houses format: {type(secondary_raw).__name__}"
            )

        # Label parsing
        label = str(item.get("label") or item.get("name") or item.get("description") or f"Event {idx}")

        # Optional time
        ev_time = TimeType(12, 0)
        if "time" in item and item["time"]:
            try:
                ev_time = _parse_time(str(item["time"]))
            except argparse.ArgumentTypeError as exc:
                raise ValueError(f"event #{idx}: {exc}") from None

        events.append(
            LifeEvent(
                date=ev_date,
                primary=primary,
                secondary=secondary_tuple,
                label=label,
                time=ev_time,
            )
        )

    return events, birth_defaults, scan_defaults


def add_btr_arguments(p: argparse.ArgumentParser) -> None:
    """Register BTR CLI options onto an argument parser."""
    p.add_argument(
        "events",
        nargs="?",
        default=None,
        help="path to JSON file containing life events (or '-' for stdin)",
    )
    p.add_argument(
        "--events",
        dest="events_file",
        default=None,
        help="path to JSON file containing life events (alternative to positional)",
    )

    # Birth parameters
    p.add_argument(
        "--date",
        type=_date_arg,
        default=None,
        help="approximate birth date (YYYY-MM-DD)",
    )
    p.add_argument(
        "--time",
        type=_parse_time,
        default=None,
        help="approximate local birth time (HH:MM or HH:MM:SS, default 12:00)",
    )
    p.add_argument(
        "--tz",
        type=float,
        default=None,
        help="UTC offset in hours (default +5.5 or from JSON)",
    )
    p.add_argument(
        "--lat",
        type=float,
        default=None,
        help="geographic latitude in degrees",
    )
    p.add_argument(
        "--lon",
        type=float,
        default=None,
        help="geographic longitude in degrees",
    )
    p.add_argument(
        "--place",
        default=None,
        help="place label (default empty)",
    )

    # Rectification scan window
    p.add_argument(
        "--window",
        "--window-min",
        dest="window_min",
        type=float,
        default=None,
        help="rectification search window (+/- minutes around approx time, default 60.0)",
    )
    p.add_argument(
        "--step",
        "--step-min",
        dest="step_min",
        type=float,
        default=None,
        help="search step in minutes (default 1.0)",
    )

    # Calculation options
    p.add_argument(
        "--ayanamsa",
        choices=("lahiri", "kp", "kp_old"),
        default=None,
        help="ayanamsa system (default lahiri)",
    )
    p.add_argument(
        "--node",
        choices=("true", "mean"),
        default=None,
        help="lunar node calculation (default true)",
    )
    p.add_argument(
        "--use-rp",
        "--rp",
        dest="use_rp",
        action="store_true",
        default=None,
        help="apply ruling planets test against analysis time",
    )
    p.add_argument(
        "--analysis-time",
        type=_parse_datetime_or_time,
        default=None,
        help="moment used for ruling planets test (default current time)",
    )
    p.add_argument(
        "--siblings",
        type=int,
        default=None,
        help="number of siblings for weak identity hint (3rd house check)",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=12,
        help="maximum candidate rows rendered in summary table (default 12)",
    )


def build_btr_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser for kpastro-btr."""
    p = argparse.ArgumentParser(
        prog="kpastro-btr",
        description="KP birth-time rectification (BTR) from dated life events.",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    add_btr_arguments(p)
    return p


def run_btr(args: argparse.Namespace) -> int:
    """Execute birth-time rectification from parsed arguments."""
    events_path = args.events_file or args.events
    if not events_path:
        raise ValueError("events JSON file is required (pass as argument or via --events)")

    events, birth_def, scan_def = load_events_json(events_path)

    # Resolve birth date
    b_date = args.date
    if b_date is None and "date" in birth_def:
        b_date = _date_arg(str(birth_def["date"]))
    if b_date is None:
        raise ValueError("birth date is required (--date YYYY-MM-DD or in JSON)")

    # Resolve birth time
    b_time = args.time
    if b_time is None and "time" in birth_def:
        b_time = _parse_time(str(birth_def["time"]))
    if b_time is None:
        b_time = TimeType(12, 0)

    # Resolve latitude
    b_lat = args.lat
    if b_lat is None and ("lat" in birth_def or "latitude" in birth_def):
        b_lat = float(birth_def.get("lat", birth_def.get("latitude")))
    if b_lat is None:
        raise ValueError("geographic latitude is required (--lat DEG or in JSON)")

    # Resolve longitude
    b_lon = args.lon
    if b_lon is None and ("lon" in birth_def or "longitude" in birth_def):
        b_lon = float(birth_def.get("lon", birth_def.get("longitude")))
    if b_lon is None:
        raise ValueError("geographic longitude is required (--lon DEG or in JSON)")

    # Resolve timezone
    b_tz = args.tz
    if b_tz is None and ("tz" in birth_def or "tz_hours" in birth_def):
        b_tz = float(birth_def.get("tz", birth_def.get("tz_hours")))
    if b_tz is None:
        b_tz = 5.5

    # Resolve place
    b_place = args.place
    if b_place is None:
        b_place = str(birth_def.get("place", ""))

    # Resolve scan parameters
    window_min = args.window_min
    if window_min is None:
        window_min = float(scan_def.get("window_min", scan_def.get("window", 60.0)))

    step_min = args.step_min
    if step_min is None:
        step_min = float(scan_def.get("step_min", scan_def.get("step", 1.0)))

    ayanamsa = args.ayanamsa or scan_def.get("ayanamsa", "lahiri")
    node = args.node or scan_def.get("node", "true")

    use_rp = args.use_rp
    if use_rp is None:
        use_rp = bool(scan_def.get("use_rp", False))

    siblings = args.siblings
    if siblings is None and "siblings" in scan_def:
        siblings = int(scan_def["siblings"])

    identity = IdentityInfo(siblings=siblings) if siblings is not None else None

    birth = BirthInfo(
        date=b_date,
        time=b_time,
        latitude=b_lat,
        longitude=b_lon,
        tz_hours=b_tz,
        place=b_place,
    )

    result = rectify(
        birth=birth,
        approx_time=b_time,
        events=events,
        window_min=window_min,
        step_min=step_min,
        use_rp=use_rp,
        analysis_time=args.analysis_time,
        identity=identity,
        ayanamsa=ayanamsa,
        node=node,
    )

    print(render_rectification(result, birth, limit=args.limit))
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point for kpastro-btr."""
    parser = build_btr_parser()
    args = parser.parse_args(argv)
    try:
        return run_btr(args)
    except ValueError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
