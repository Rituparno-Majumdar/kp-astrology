"""KP significators and ruling planets.

Significators
-------------
A planet is a significator of a house when it connects to it through

1. **Occupation** - the planet sits in the house,
2. **Sign-lordship (ownership)** - it rules the sign whose cusp begins the house,
3. **Star-lord agency** - its nakshatra (star) lord occupies or owns the house
   (a planet delivers the results signified by its star lord).

For judgement KP inverts this: *Bhaav Nirdeshan* collects per house the
occupants, planets in the occupants' stars, the cuspal lord and planets in the
cuspal lord's star - sorted by strength.  The **sub-lord of each cusp** is the
final arbiter of that house's matters.

Ruling planets
--------------
The RPs of a moment are the sign/star/sub lords of the ascendant, the same
three of the Moon, and the day-lord (weekday).
"""

from __future__ import annotations

from dataclasses import dataclass

from .constants import SIGN_LORDS, SIGNS, SIGNS_RULED_BY, WEEKDAY_LORDS
from .vedic import point_info, sign_index, star_lord, sub_lord


# ---------------------------------------------------------------------------
# House geometry (Placidus cusps)
# ---------------------------------------------------------------------------

def house_of_longitude(lon: float, cusps: list[float]) -> int:
    """House (1-12) containing a longitude under Placidus cusps.

    Houses advance counter-clockwise from each cusp to the next; cusp 12 wraps
    to cusp 1 + 360°.
    """
    lon = lon % 360.0
    c0 = cusps[0] % 360.0
    if lon < c0:
        lon += 360.0
    for i, c in enumerate(cusps):
        nxt = cusps[i + 1] if i < 11 else c0 + 360.0
        if c <= lon < nxt:
            return i + 1
    return 12


def house_of_sign(sign_num: int, cusps: list[float]) -> int:
    """House containing the beginning of a sign (sign_num 0..11)."""
    return house_of_longitude(sign_num * 30.0, cusps)


# ---------------------------------------------------------------------------
# Planet -> houses (Grah Nirdeshan)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Signification:
    """A house a planet signifies, and why."""
    house: int
    by_occupation: bool
    by_sign_lordship: bool
    by_star_lord: bool


def planet_significations(
    positions: dict[str, float],
    cusps: list[float],
    star_lords_cache: dict[str, str] | None = None,
) -> dict[str, list[Signification]]:
    """For every planet, the houses it signifies (occupation, lordship, star)."""
    sl = star_lords_cache or {p: star_lord(pos) for p, pos in positions.items()}
    result: dict[str, list[Signification]] = {}
    for planet, lon in positions.items():
        sig_map: dict[int, Signification] = {}

        def add(house: int, flag: str) -> None:
            sig = sig_map.setdefault(house, Signification(house, False, False, False))
            if flag == "occ":
                sig_map[house] = Signification(house, True, sig.by_sign_lordship, sig.by_star_lord)
            elif flag == "own":
                sig_map[house] = Signification(house, sig.by_occupation, True, sig.by_star_lord)
            else:
                sig_map[house] = Signification(house, sig.by_occupation, sig.by_sign_lordship, True)

        add(house_of_longitude(lon, cusps), "occ")
        for sign_name in SIGNS_RULED_BY.get(planet, ()):
            add(house_of_sign(SIGNS.index(sign_name), cusps), "own")

        star_owner = sl[planet]
        if star_owner in positions:
            add(house_of_longitude(positions[star_owner], cusps), "star")
            for sign_name in SIGNS_RULED_BY.get(star_owner, ()):
                add(house_of_sign(SIGNS.index(sign_name), cusps), "star")

        result[planet] = sorted(sig_map.values(), key=lambda s: s.house)
    return result


# ---------------------------------------------------------------------------
# House -> planets (Bhaav Nirdeshan)
# ---------------------------------------------------------------------------

def _planets_in_stars(
    star_lord_name: str,
    positions: dict[str, float],
    star_lords_cache: dict[str, str],
) -> list[str]:
    return [p for p in positions if star_lords_cache.get(p) == star_lord_name]


def house_significations(
    positions: dict[str, float], cusps: list[float]
) -> list[list[tuple[str, int]]]:
    """Per-house significator lists with strength tiers.

    Tier 1 = occupant, 2 = in an occupant's star, 3 = cuspal lord,
    4 = in the cuspal lord's star.
    """
    star_lords_map = {p: star_lord(lon) for p, lon in positions.items()}
    occupants: dict[int, list[str]] = {i + 1: [] for i in range(12)}
    for p, lon in positions.items():
        occupants[house_of_longitude(lon, cusps)].append(p)

    out: list[list[tuple[str, int]]] = []
    for i in range(12):
        house = i + 1
        cuspal_lord = SIGN_LORDS[SIGNS[sign_index(cusps[i])]]
        tiers: list[tuple[str, int]] = []
        seen: set[str] = set()

        def add(planet: str, tier: int) -> None:
            if planet not in seen:
                seen.add(planet)
                tiers.append((planet, tier))

        for occ in occupants[house]:
            add(occ, 1)
        for occ in occupants[house]:
            for p in _planets_in_stars(occ, positions, star_lords_map):
                add(p, 2)
        add(cuspal_lord, 3)
        if cuspal_lord in positions:
            for p in _planets_in_stars(cuspal_lord, positions, star_lords_map):
                add(p, 4)
        out.append(tiers)
    return out


def cusp_sub_lords(cusps: list[float]) -> dict[int, str]:
    """Sub-lord of each house cusp (the KP judge of that house)."""
    return {i + 1: sub_lord(cusps[i]) for i in range(12)}


# ---------------------------------------------------------------------------
# Ruling planets
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RulingPlanet:
    planet: str
    source: str


def ruling_planets(
    ascendant_lon: float,
    moon_lon: float,
    weekday: int,          # python weekday(): 0=Monday .. 6=Sunday
) -> list[RulingPlanet]:
    """Ruling planets of a moment: day lord + ascendant/Moon sign/star/sub lords."""
    asc = point_info(ascendant_lon)
    mon = point_info(moon_lon)
    entries = [
        (WEEKDAY_LORDS[weekday % 7], "day lord"),
        (asc.sign_lord, "asc sign lord"),
        (asc.star_lord, "asc star lord"),
        (asc.sub_lord, "asc sub lord"),
        (mon.sign_lord, "moon sign lord"),
        (mon.star_lord, "moon star lord"),
        (mon.sub_lord, "moon sub lord"),
    ]
    out: list[RulingPlanet] = []
    for planet, source in entries:
        idx = next((i for i, rp in enumerate(out) if rp.planet == planet), None)
        if idx is None:
            out.append(RulingPlanet(planet, source))
        else:
            out[idx] = RulingPlanet(planet, f"{out[idx].source}, {source}")
    return out