"""kpastro - a precise Krishnamurti Paddhati (KP) astrology engine.

Highlights
----------
* Swiss Ephemeris backend (arc-second accuracy) for planets, ayanamsa and
  Placidus cusps, with an automatic Moshier fallback when no data files exist.
* Pure-Python KP subdivision math: nakshatra, sub-lord, sub-sub-lord.
* Vimshottari dasha with nested birth balances (MD/AD/PD).
* Planet -> house and house -> planet significators, ruling planets.
* KP horary: the 249-division number system.
"""

from . import vedic  # noqa: F401
from .dasha import (  # noqa: F401
    Balance,
    Period,
    antardashas_of,
    current_periods,
    dasha_balance,
    mahadasha_timeline,
)
from .ephemeris import SwissEphemeris, download_ephemeris, ephemeris_version  # noqa: F401
from .chart import (  # noqa: F401
    BirthInfo,
    Chart,
    compute_chart,
    render_chart,
)
from .horary import (  # noqa: F401
    HoraryDiv,
    ascendant_from_kp_number,
    kp_divisions,
    kp_number_for_longitude,
)
from .significators import (  # noqa: F401
    RulingPlanet,
    house_significations,
    planet_significations,
    ruling_planets,
)
from .vedic import format_longitude, point_info, sub_info, sub_sub_info  # noqa: F401

__version__ = "0.1.0"

__all__ = [
    "Balance",
    "BirthInfo",
    "Chart",
    "HoraryDiv",
    "Period",
    "RulingPlanet",
    "SwissEphemeris",
    "antardashas_of",
    "ascendant_from_kp_number",
    "compute_chart",
    "current_periods",
    "dasha_balance",
    "download_ephemeris",
    "ephemeris_version",
    "format_longitude",
    "house_significations",
    "kp_divisions",
    "kp_number_for_longitude",
    "mahadasha_timeline",
    "planet_significations",
    "point_info",
    "render_chart",
    "ruling_planets",
    "sub_info",
    "sub_sub_info",
    "vedic",
]