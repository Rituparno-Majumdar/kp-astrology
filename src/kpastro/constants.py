"""Core constants for Krishnamurti Paddhati (KP) astrology.

All tables here follow the conventions codified by Prof. K. S. Krishnamurti
(the *Krishnamurti Paddhati*, "System of the Prophet of KP").
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Planets and the Vimshottari sequence
# ---------------------------------------------------------------------------

#: The nine grahas in Vimshottari order (also the order nakshatra lords cycle in).
VIMSHOTTARI_ORDER: tuple[str, ...] = (
    "Ketu", "Venus", "Sun", "Moon", "Mars",
    "Rahu", "Jupiter", "Saturn", "Mercury",
)

#: Mahadasha years of each planet; the sum is 120 (``Vimshottari``).
#: These proportions also size the sub-lord / sub-sub-lord divisions.
VIMSHOTTARI_YEARS: dict[str, int] = {
    "Ketu": 7,
    "Venus": 20,
    "Sun": 6,
    "Moon": 10,
    "Mars": 7,
    "Rahu": 18,
    "Jupiter": 16,
    "Saturn": 19,
    "Mercury": 17,
}

#: Position (0-8) of each planet inside the Vimshottari order.
VIMSHOTTARI_INDEX: dict[str, int] = {p: i for i, p in enumerate(VIMSHOTTARI_ORDER)}

#: Total Vimshottari period in years.
VIMSHOTTARI_TOTAL_YEARS: int = 120

#: Short symbols used for compact chart output.
PLANET_ABBR: dict[str, str] = {
    "Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me",
    "Jupiter": "Ju", "Venus": "Ve", "Saturn": "Sa", "Rahu": "Ra", "Ketu": "Ke",
}

# ---------------------------------------------------------------------------
# Zodiac signs
# ---------------------------------------------------------------------------

SIGNS: tuple[str, ...] = (
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
)

#: Sign-lord of every rashi (the first of the two classic KP lords).
SIGN_LORDS: dict[str, str] = {
    "Aries": "Mars",
    "Taurus": "Venus",
    "Gemini": "Mercury",
    "Cancer": "Moon",
    "Leo": "Sun",
    "Virgo": "Mercury",
    "Libra": "Venus",
    "Scorpio": "Mars",
    "Sagittarius": "Jupiter",
    "Capricorn": "Saturn",
    "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}

#: Signs (rashis) ruled by each planet.  Rahu and Ketu own no rashis.
SIGNS_RULED_BY: dict[str, tuple[str, ...]] = {
    "Sun": ("Leo",),
    "Moon": ("Cancer",),
    "Mars": ("Aries", "Scorpio"),
    "Mercury": ("Gemini", "Virgo"),
    "Jupiter": ("Sagittarius", "Pisces"),
    "Venus": ("Taurus", "Libra"),
    "Saturn": ("Capricorn", "Aquarius"),
    "Rahu": (),
    "Ketu": (),
}

# ---------------------------------------------------------------------------
# Nakshatras
# ---------------------------------------------------------------------------

#: The 27 nakshatras in zodiacal order from Ashwini to Revati.
NAKSHATRAS: tuple[str, ...] = (
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha",
    "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha",
    "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada",
    "Uttara Bhadrapada", "Revati",
)

#: Star-lord of nakshatra ``i`` is ``NAKSHATRA_LORDS[i % 9]``.
NAKSHATRA_LORDS_BASE: tuple[str, ...] = (
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury",
)

#: Weekday -> lord (KP day-lord used by the Ruling Planets).
WEEKDAY_LORDS: tuple[str, ...] = (
    "Moon",      # Monday
    "Mars",      # Tuesday
    "Mercury",   # Wednesday
    "Jupiter",   # Thursday
    "Venus",     # Friday
    "Saturn",    # Saturday
    "Sun",       # Sunday
)


def star_lord_of_index(idx: int) -> str:
    """Return the Vimshottari star-lord of nakshatra ``idx`` (0..26)."""
    return NAKSHATRA_LORDS_BASE[idx % 9]