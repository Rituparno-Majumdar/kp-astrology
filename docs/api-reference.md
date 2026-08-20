# API reference

This page documents every public name of `kpastro`. The **package root**
re-exports the most useful symbols; the per-module sections cover the rest.

```python
import kpastro          # convenient public API
from kpastro import *   # names listed under __all__
```

## Package root (`kpastro`)

### Types

| Name | Kind | Purpose |
|------|------|---------|
| `BirthInfo` | dataclass | Birth/event details (date, time, place, tz) |
| `Chart` | dataclass | Every computed KP layer, ready to render or inspect |
| `Balance` | dataclass | Nested dasha balances anchored to the birth Moon |
| `Period` | dataclass | A dasha period (lord + start/end offsets in days + level) |
| `HoraryDiv` | dataclass | One of the 249 KP horary divisions |
| `RulingPlanet` | dataclass | A ruling planet and the sources it was found through |
| `LifeEvent` | dataclass | A dated life event mapped to KP houses (rectification input) |
| `IdentityInfo` | dataclass | Optional sibling hint for rectification |
| `CandidateScore` | dataclass | Full score of one candidate birth instant |
| `EventScore` | dataclass | Per-event breakdown of a candidate's score |
| `RectificationResult` | dataclass | Full rectification scan, best candidate, credible interval |
| `CredibleInterval` | dataclass | The posterior time-range around the best candidate |
| `TransitConfirmation` | dataclass | Jupiter/Saturn transit cross-check over the events |
| `EventTransit` | dataclass | Whether transit Jupiter/Saturn confirmed one event |
| `SwissEphemeris` | class | Thin wrapper around the Swiss Ephemeris engine |
| `vedic` | module | The pure-Python subdivision math (re-exported) |

### Functions

| Name | Purpose |
|------|---------|
| `compute_chart(birth, ayanamsa="lahiri", node="mean", eph=None) -> Chart` | Compute every KP layer for a birth chart |
| `render_chart(chart) -> str` | Human-readable multi-section chart text |
| `dasha_balance(moon_longitude) -> Balance` | Nested balances from the sidereal birth Moon |
| `mahadasha_timeline(moon_longitude, epochs=1) -> list[Period]` | All mahadashas from birth |
| `antardashas_of(period, balance=None) -> list[Period]` | The nine antardashas of a mahadasha |
| `current_periods(moon_longitude, epoch, instant, depth=3) -> dict[int, Period]` | MD/AD/PD active at an instant |
| `kp_divisions() -> list[HoraryDiv]` | The 249 KP divisions of the zodiac |
| `ascendant_from_kp_number(n) -> dict` | Horary ascendant (division midpoint) + lord chain |
| `kp_number_for_longitude(lon) -> int | None` | Inverse: which division contains a longitude |
| `planet_significations(positions, cusps) -> dict[str, list[Signification]]` | Grah Nirdeshan |
| `house_significations(positions, cusps) -> list[list[tuple[str, int]]]` | Bhaav Nirdeshan with tiers |
| `ruling_planets(ascendant_lon, moon_lon, weekday) -> list[RulingPlanet]` | RPs of a moment |
| `rectify(birth, approx_time, events, window_min=60, step_min=1, ...)` | Scan for the most probable birth time (see below) |
| `score_candidate(jd_ut, lat, lon, events, ...) -> CandidateScore` | Score a single candidate instant |
| `aspects_from_house(house, planet) -> set[int]` | Houses aspected by a planet in a given house |
| `house_significator_sets(positions, cusps) -> (dict, dict)` | Rectification-flavour per-house significators |
| `transit_confirmation(jd_ut, lat, lon, events, ...) -> TransitConfirmation` | Jupiter/Saturn transit cross-check |
| `credible_interval(candidates, target_mass=0.75) -> CredibleInterval` | Post-process the candidate scores into a time range |
| `render_rectification(result, birth, limit=12) -> str` | Human-readable rectification report |
| `point_info(lon) -> PointInfo` | Full KP breakdown of one sidereal longitude |
| `sub_info(lon) -> SubInfo` / `sub_sub_info(lon) -> SubSubInfo` | Sub-lord chain lookup |
| `format_longitude(lon, arcsec=True) -> str` | Render `D°MM'SS"` |
| `download_ephemeris(target_dir=None) -> list[Path]` | Fetch the Swiss Ephemeris data files |
| `ephemeris_version() -> str` | Installed Swiss Ephemeris engine version |

### Constants

`kpastro.__version__` (str), matching the installed distribution version.

<br>

---

## `kpastro.constants`

Static KP tables and a small helper. All are frozen data.

| Name | Type | Meaning |
|------|------|---------|
| `VIMSHOTTARI_ORDER` | `tuple[str, ...]` | Ketu, Venus, Sun, Moon, Mars, Rahu, Jupiter, Saturn, Mercury |
| `VIMSHOTTARI_YEARS` | `dict[str, int]` | Mahadasha years per planet (sum 120) |
| `VIMSHOTTARI_INDEX` | `dict[str, int]` | Position (0–8) of each planet in the order |
| `VIMSHOTTARI_TOTAL_YEARS` | `int` | `120` |
| `PLANET_ABBR` | `dict[str, str]` | Short symbols: `Sun → "Su"`, `Moon → "Mo"`, ... |
| `SIGNS` | `tuple[str, ...]` | 12 rashis from Aries |
| `SIGN_LORDS` | `dict[str, str]` | Sign-lord of each rashi |
| `SIGNS_RULED_BY` | `dict[str, tuple[str, ...]]` | Rashis ruled by each planet (Rahu/Ketu: `()` ) |
| `NAKSHATRAS` | `tuple[str, ...]` | The 27 nakshatras, Ashwini → Revati |
| `NAKSHATRA_LORDS_BASE` | `tuple[str, ...]` | Star-lord of star `i` is `i % 9` |
| `WEEKDAY_LORDS` | `tuple[str, ...]` | Monday → Sunday lords (Moon, Mars, Mercury, Jupiter, Venus, Saturn, Sun) |

**Function** — `star_lord_of_index(idx: int) -> str`: Vimshottari star-lord of
nakshatra `idx` (0–26).

<br>

---

## `kpastro.vedic` — pure-Python KP subdivision math

No ephemeris is needed: everything derives from a single sidereal longitude.

### Module constants

| Name | Meaning |
|------|---------|
| `STAR_SPAN_ARCMIN` | `800.0` — nakshatra span in arc-minutes (13°20') |
| `STAR_SPAN_DEG` | `13.333...`° — nakshatra span in degrees |
| `PADA_SPAN_DEG` | `3.333...`° — pada (quarter) span |

### Functions

- `normalize_longitude(lon) -> float` — fold into `[0, 360)`.
- `sub_span_arcmin(lord) -> float` — sub width: `years/120 * 800'`.
- `format_longitude(lon, arcsec=True) -> str` — `D°MM'SS"`, or `D°MM'` without seconds.
- `sign_index(lon) -> int`, `sign_name(lon) -> str`, `sign_lord_of_longitude(lon) -> str`.
- `star_index(lon) -> int` (0–26), `star_name(lon) -> str`, `star_lord(lon) -> str`,
  `star_span(lon) -> tuple[float, float]` (start, end of the star).
- `pada_info(lon) -> PadaInfo` — quarter (`pada`, `start_deg`, `end_deg`).
- `sub_info(lon) -> SubInfo` — sub-lord within the star (`lord`, `index`, `start_deg`,
  `end_deg`, `span_arcmin`).
- `sub_lord(lon) -> str`, `sub_sub_lord(lon) -> str`.
- `sub_sub_info(lon) -> SubSubInfo` — sub divided again with the same proportions.
- `point_info(lon) -> PointInfo` — aggregated breakdown (see table below).

### Data types

```
PadaInfo(lon)    -> pada, start_deg, end_deg
SubInfo(lon)     -> lord, index, start_deg, end_deg, span_arcmin
SubSubInfo(lon)  -> lord, index, start_deg, end_deg, span_arcmin
PointInfo(lon)   -> longitude, sign, sign_lord, sign_degree, star, star_lord,
                    star_index, sub_lord, sub_sub_lord, pada
```

<br>

---

## `kpastro.ephemeris` — Swiss Ephemeris integration

### Module constants

| Name | Meaning |
|------|---------|
| `AYANAMSA_MODES` | `{"lahiri": SE_SIDM_LAHIRI, "kp": SE_SIDM_KRISHNAMURTI_VP291, "kp_old": SE_SIDM_KRISHNAMURTI}` |
| `NODES` | `{"mean": MEAN_NODE, "true": TRUE_NODE}` |
| `SWE_BODY` | Swiss body ids for Sun → Saturn |
| `PLANET_OUTPUT_ORDER` | Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu |
| `EPHEMERIS_FILES` | `("sepl_18.se1", "semo_18.se1", "seas_18.se1")` |
| `EPHEMERIS_BASE_URL` | Official aloistr/swisseph ephe mirror |

### `default_ephe_path() -> Path`

`~/.kpastro/ephe` — where data files live by default.

### `download_ephemeris(target_dir=None) -> list[Path]`

Downloads the three `*.se1` files (skipping any already present and non-empty)
into `target_dir` or the default path, returning the saved paths.

### `ephemeris_version() -> str`

The version string of the linked Swiss Ephemeris engine (e.g. `"2.10.03"`).

### `class SwissEphemeris(ayanamsa="lahiri", node="mean", ephe_path=None)`

A safe, reusable wrapper around the (process-global) Swiss Ephemeris engine.

- Raises `ValueError` for unknown ayanamsa/node values.
- The ephemeris path resolves as `ephe_path` → `SE_EPHE_PATH` env var →
  `~/.kpastro/ephe`; if the directory exists it is registered with the engine.
- `data_files_present -> bool` — are all three `*.se1` files present?
- `jd_ut(dt: datetime) -> float` — Julian date (UT) for a naive-UTC datetime.
- `ayanamsa(jd_ut) -> float` — ayanamsa in degrees (sidereal mode is re-applied).
- `tropical_positions(jd_ut) -> dict[str, (lon, speed)]` — geocentric, tropical.
- `sidereal_positions(jd_ut) -> dict[str, (lon, speed)]` — ayanamsa subtracted.
- `houses(jd_ut, lat, lon) -> (cusps, asc, mc, armc)` — Placidus cusps and angles,
  everything normalized to the sidereal zodiac; `cusps` is always 12 entries
  (handles both the 12-element `pyswisseph` and 13-element `pysweph` layouts).

Ketu's longitude is defined as Rahu + 180° (standard practice).

<br>

---

## `kpastro.chart` — the full KP chart

### `BirthInfo`

```python
BirthInfo(date, time, latitude, longitude, tz_hours=0.0, place="")
```

- `date: datetime.date`, `time: datetime.time` — **local** wall-clock time.
- `tz_hours: float` — UTC offset (India: `5.5`; negative west of Greenwich).
- `.utc_datetime() -> datetime` — converts local → UTC (`local - timedelta(hours=tz)`).

### `PlanetPos`

```
name, longitude (sidereal, deg), house (1–12), sign, sign_degree, sign_lord,
star, star_lord, sub_lord, sub_sub_lord, pada, speed_deg_day, retrograde
```

### `CuspPos`

```
house, longitude (sidereal, deg), sign, sign_lord, star, star_lord, sub_lord, sub_sub_lord
```

### `Chart`

`compute_chart` returns a `Chart` whose fields give typed access to every layer:

| Field | Type | Meaning |
|-------|------|---------|
| `birth` | `BirthInfo` | Input details |
| `jd_ut` | `float` | Julian date used |
| `ayanamsa` | `float` | Ayanamsa value in degrees |
| `ayanamsa_mode` | `str` / `node` | `str` — the modes used |
| `planets` | `list[PlanetPos]` | All 9 planets |
| `cusps` | `list[CuspPos]` | 12 Placidus cusps |
| `ascendant` / `midheaven` / `armc` | `float` | Sidereal angles |
| `planet_lon` | `dict[str, float]` | Planet → sidereal longitude |
| `balance` | `Balance` | Moon-anchored dasha balances |
| `mahadashas` | `list[Period]` | Full mahadasha timeline |
| `current` | `dict[int, Period]` | MD(1)/AD(2)/PD(3) at the birth instant |
| `planet_significators` | `dict[str, list[Signification]]` | Grah Nirdeshan |
| `house_significators` | `list[list[tuple[str, int]]]` | Bhaav Nirdeshan with tiers |
| `cusp_sublords` | `dict[int, str]` | Sub-lord of each house cusp |
| `ruling` | `list[RulingPlanet]` | RPs of the birth moment |

### Functions

- `compute_chart(birth, ayanamsa="lahiri", node="mean", eph=None) -> Chart` —
  every KP layer in one call. Reuse a single `SwissEphemeris` across many charts
  via `eph=` to avoid re-registering the engine.
- `render_chart(chart) -> str` — the full multi-section text chart.
- `render_planets(chart)`, `render_cusps(chart)`, `render_significators(chart)`,
  `render_ruling(chart)`, `render_dasha(chart) -> str` — individual sections.

<br>

---

## `kpastro.dasha` — Vimshottari dasha

The mahadasha sequence is fixed: Ketu 7, Venus 20, Sun 6, Moon 10, Mars 7,
Rahu 18, Jupiter 16, Saturn 19, Mercury 17 (120 years). 1 dasha year = 365.25 days.

### Constants

`DAYS_PER_YEAR = 365.25`, `CYCLE_DAYS = 120 * DAYS_PER_YEAR`.

### `Balance`

```
mahadasha_lord, mahadasha_years, mahadasha_days,
active_ad_lord, active_ad_days, active_pd_lord, active_pd_days,
nakshatra, nakshatra_index
```

### `Period`

```
lord, start_days, end_days, level          # level 1=MD, 2=AD, 3=PD
.duration_days / .duration_years           # properties
.as_datetimes(epoch: datetime) -> (start, end)
```

### Functions

- `period_days(parent_lord, child_lord) -> float` — full sub-period length:
  `years(parent) * years(child) / 120 * 365.25`.
- `mahadasha_days(lord) -> float` — `years(lord) * 365.25`.
- `dasha_balance(moon_longitude) -> Balance` — nested balances from the sidereal
  birth Moon longitude (MD anchored to the star, AD to the sub, PD to the sub-sub).
- `mahadasha_timeline(moon_longitude, epochs=1) -> list[Period]` — all mahadashas
  from birth, the opening one truncated to the balance; `epochs` repeats full cycles.
- `antardashas_of(period, balance=None) -> list[Period]` — the nine antardashas.
  For the opening (balance) mahadasha, starts at the Moon's sub-lord and the first
  AD is truncated to the AD balance.
- `pratyantardashas_of(ad, balance=None, md_is_partial=False) -> list[Period]` —
  the nine pratyantardashas of an antardasha (refined only for the birth AD).
- `current_periods(moon_longitude, epoch, instant, depth=3) -> dict[int, Period]` —
  active MD(1)/AD(2)/PD(3) at `instant`. Raises `ValueError` if the instant falls
  outside the timelines.
- `format_days(days) -> str` — `Yy Mm Dd` (year 365.25d, month 30.4375d).

<br>

---

## `kpastro.significators`

Significator rules: a planet signifies a house by **occupation**, by
**sign-lordship** (owning the sign on the cusp), and by **star-lord agency**
(its star-lord occupies or owns the house). RPs are the day-lord and the
Ascendant/Moon sign/star/sub lords.

### Functions

- `house_of_longitude(lon, cusps) -> int` — house 1–12 containing a longitude
  (cusps listed in order; house 12 wraps to cusp 1 + 360°).
- `house_of_sign(sign_num, cusps) -> int` — house containing the start of sign 0–11.
- `planet_significations(positions, cusps, star_lords_cache=None) -> dict[str, list[Signification]]`
  — every house each planet signifies and why (`by_occupation`, `by_sign_lordship`,
  `by_star_lord` booleans).
- `house_significations(positions, cusps) -> list[list[tuple[str, int]]]` —
  per-house planets with tiers: **1** occupant, **2** in an occupant's star,
  **3** cuspal lord, **4** in the cuspal lord's star.
- `cusp_sub_lords(cusps) -> dict[int, str]` — the KP judge of each house.
- `ruling_planets(ascendant_lon, moon_lon, weekday) -> list[RulingPlanet]` —
  weekday: `datetime.weekday()` convention, 0=Monday … 6=Sunday. Sources merge
  (a planet that is both day-lord and asc-sign-lord has both sources listed).

### Types

```
Signification(house, by_occupation, by_sign_lordship, by_star_lord)
RulingPlanet(planet, source)      # source e.g. "day lord", "asc sign lord, asc star lord"
```

<br>

---

## `kpastro.rectification` — birth-time rectification

Recovers an approximate/unknown birth time from dated **life events** judged to
fall in specific KP houses. Ported from the classic KP "time of birth" web tool
and rebased on the Swiss Ephemeris. It is an **API feature** (not yet a CLI
subcommand).

### `LifeEvent`

```python
LifeEvent(date, primary, secondary=(), label="", time=time(12, 0))
```

- `date: datetime.date` — when the event happened (default moment is local noon).
- `primary: int` — the main KP house (1–12) the event fell into.
- `secondary: tuple[int, ...]` — extra houses the event also connected to.
- `label: str` — free text shown in reports (e.g. "Marriage").
- `.jd_ut(tz_hours, eph) -> float` — the event moment as a Julian date (UT).

### `IdentityInfo`

```python
IdentityInfo(siblings=None)
```

A weak biographical hint: with siblings, house 3 is expected to be occupied; an
only child usually has it empty. `None` disables the hint.

### Scoring

For every candidate minute `score_candidate` computes the KP significator set
of each house (cusp sub-lord + occupants and their star-lords + aspecting
planets and their star-lords) and the lagna sub-lord (LSL):

```
total = lsl_score + 0.5 * dasha_score + rp_score + identity_score
```

- **LSL** — +2 when the LSL is a significator of the event's primary house, +1
  per secondary house it appears in, all scaled by the specificity weight
  `max(0, min(1, (12 − n) / 9))` where `n` is how many houses the LSL
  signifies (a "common" significator's testimony is weak).
- **Dasha** — the mahadasha / antardasha / pratyantar lords running at the
  event (anchored to the candidate birth moment) add `1 / 1 / 0.5` for a
  primary-house hit and a quarter of that for a secondary-house hit. Events with
  `dasha_score < 1` are reported as **strikes**.
- **RP** — +1 if the LSL is in the classic five-lord ruling-planet set of the
  analysis moment (day lord + asc/moon sign and star lords; optional).
- **Identity** — +0.25 if the sibling hint is satisfied (optional).

### Functions

- `rectify(birth, approx_time, events, window_min=60.0, step_min=1.0, *,
  use_rp=False, analysis_time=None, identity=None, ayanamsa="lahiri",
  node="true", eph=None) -> RectificationResult` — scans
  `±window_min` minutes around `approx_time` (a `datetime` or a `time` combined
  with `birth.date`) in `step_min` steps and ranks every candidate.
- `score_candidate(jd_ut, latitude, longitude, events, tz_hours=0.0,
  rp_set=None, identity=None, eph=None, approx_jd=None, event_jds=None) -> CandidateScore` —
  score one candidate instant directly.
- `aspects_from_house(house, planet) -> set[int]` — houses aspected by a planet
  sitting in a house (KP aspects: everyone takes the 7th; Mars adds 4th/8th,
  Jupiter 5th/9th, Saturn 3rd/10th).
- `house_significator_sets(positions, cusps, star_lord_cache=None)
  -> (sets, house_map)` — the rectification-flavour per-house significators.
- `transit_confirmation(jd_ut, latitude, longitude, events, tz_hours=0.0,
  eph=None) -> TransitConfirmation` — counts how often transit Jupiter/Saturn
  sit in a longitude whose star- or sign-lord is a significator of the event's
  primary house (2 × `len(events)` checks; not folded into the score).
- `credible_interval(candidates, target_mass=0.75) -> CredibleInterval` —
  softmax over the scores (temperature 1.5), then the smallest contiguous time
  span holding the target posterior mass.
- `render_rectification(result, birth, limit=12) -> str` — the report.

Rectification uses the **true** node by default (matching the reference tool);
pass `node="mean"` for the traditional KP convention.

### Output types

```
CandidateScore(jd_ut, offset_minutes, lsl, specificity, n_significating_houses,
               lsl_score, dasha_score, rp_score, identity_score, total,
               strikes, events)
EventScore(label, date, primary, secondary, lsl_score, lsl_hit, dasha_score,
           dasha_hit, mahadasha_lord, antardasha_lord, pratyantar_lord)
RectificationResult(approx_ut, candidates, best, credible, settings, events)
CredibleInterval(start_ut, end_ut, peak_ut, mass, spread_minutes)
TransitConfirmation(matched, total, per_event)
EventTransit(label, date, jupiter, saturn)
```

<br>

---

## `kpastro.horary` — the 249-division KP number system

27 nakshatras × 9 sub-lords = 243 subs; six sign boundaries fall *inside* a sub
and split it, giving exactly **249** numbered divisions from 0° Aries.

- `MAX_HORARY_NUMBER = 249`.
- `kp_divisions() -> list[HoraryDiv]` — 249 divisions in ascending zodiacal order.
- `ascendant_from_kp_number(n) -> dict` — `{"number", "ascendant" (division
  midpoint), "span" (start, end), "sign", "sign_lord", "star", "star_lord",
  "sub_lord", "sub_sub_lord", "pada"}`. Raises `ValueError` if `n` is outside 1–249.
- `kp_number_for_longitude(lon) -> int | None` — which division contains a longitude.

### `HoraryDiv`

```
number, start_deg, end_deg, sign, sign_lord, star, star_lord, sub_lord
.mid_deg  # (start + end)/2, used as the horary ascendant
```

<br>

---

## `kpastro.cli` — the command line

- `build_parser() -> argparse.ArgumentParser`
- `main(argv=None) -> int`

Entry points: `kpastro` console script (see `pyproject.toml`) and
`python -m kpastro` (`kpastro/__main__.py`). Subcommands: `natal`, `horary`,
`dasha`, `rulings`, `ayanamsa`, `download-ephemeris` — see the
[user guide](user-guide.md).