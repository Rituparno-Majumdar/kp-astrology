"""kpastro - a precise Krishnamurti Paddhati (KP) astrology engine.

Highlights
----------
* Swiss Ephemeris backend (arc-second accuracy) for planets, ayanamsa and
  Placidus cusps, with an automatic Moshier fallback when no data files exist.
* Pure-Python KP subdivision math: nakshatra, sub-lord, sub-sub-lord.
* Vimshottari dasha with nested birth balances (MD/AD/PD).
* Planet -> house and house -> planet significators, ruling planets.
* KP horary: the 249-division number system.
* Birth-time rectification from dated life events, with posterior bands.
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
from .rectification import (  # noqa: F401
    CredibleInterval,
    CandidateScore,
    EventScore,
    EventTransit,
    IdentityInfo,
    LifeEvent,
    RectificationResult,
    TransitConfirmation,
    aspects_from_house,
    credible_interval,
    house_significator_sets,
    rectify,
    render_rectification,
    score_candidate,
    transit_confirmation,
)
from .significators import (  # noqa: F401
    RulingPlanet,
    house_significations,
    planet_significations,
    ruling_planets,
)
from .vedic import format_longitude, point_info, sub_info, sub_sub_info  # noqa: F401

from importlib.metadata import PackageNotFoundError, version

__version__ = "0.3.0"
try:
    __version__ = version("kpastro")
except PackageNotFoundError:
    pass

__all__ = [
    "Balance",
    "BirthInfo",
    "CandidateScore",
    "Chart",
    "CredibleInterval",
    "EventScore",
    "EventTransit",
    "HoraryDiv",
    "IdentityInfo",
    "LifeEvent",
    "Period",
    "RectificationResult",
    "RulingPlanet",
    "SwissEphemeris",
    "TransitConfirmation",
    "antardashas_of",
    "ascendant_from_kp_number",
    "aspects_from_house",
    "compute_chart",
    "credible_interval",
    "current_periods",
    "dasha_balance",
    "download_ephemeris",
    "ephemeris_version",
    "format_longitude",
    "house_significations",
    "house_significator_sets",
    "kp_divisions",
    "kp_number_for_longitude",
    "mahadasha_timeline",
    "planet_significations",
    "point_info",
    "rectify",
    "render_chart",
    "render_rectification",
    "ruling_planets",
    "score_candidate",
    "sub_info",
    "sub_sub_info",
    "transit_confirmation",
]