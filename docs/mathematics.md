# Mathematics — the KP conventions implemented

This page documents exactly what `kpastro` computes and the formulas behind
each layer, so results can be validated against published tables.

## The zodiac

- Everything is **sidereal**: `sidereal = tropical − ayanamsa`.
- Degrees run `0–360` from **0° Aries**, normalized to `[0, 360)` everywhere.
- **Ayanamsa** modes:

  | Mode | Swiss Ephemeris id | Reference |
  |------|--------------------|-----------|
  | `lahiri` | `SE_SIDM_LAHIRI` (1) | Chitrapaksha, the Lahiri/IAE 1985 zero point |
  | `kp` | `SE_SIDM_KRISHNAMURTI_VP291` (45) | Modern KP ayanamsa |
  | `kp_old` | `SE_SIDM_KRISHNAMURTI` (5) | Krishnamurti's original table |

  In 2026 the Lahiri ayanamsa is ≈ **24.14°**.

- **Node**: KP traditionally uses the **mean** node; the `true` node is available.

## Nakshatras and subdivisions

- 27 nakshatras of **13°20' = 800'** each: `star_index(lon) = floor(lon / 13.3333)`.
- **Star-lord** of star `i` is `NAKSHATRA_LORDS_BASE[i % 9]` (the 9-planet
  Vimshottari cycle repeats every 9 stars).
- **Sub-lords**: each star splits into **9 unequal** subdivisions proportional to
  the Vimshottari years:

  ```
  sub span (arcmin) = (lord's years / 120) * 800'
  ```

  The sequence starts at the star-lord and cycles through the Vimshottari order.

- **Sub-sub-lords**: the sub is divided again with the same proportion rule,
  starting from the sub-lord.

- **Pada** (quarter): each star is divided into 4 padas of **3°20'**.

## Vimshottari dasha

Fixed 120-year cycle (1 year = **365.25 days**):

| Ketu | Venus | Sun | Moon | Mars | Rahu | Jupiter | Saturn | Mercury |
|------|-------|-----|------|------|------|---------|--------|---------|
| 7 | 20 | 6 | 10 | 7 | 18 | 16 | 19 | 17 |

The mahadasha of the **birth Moon's star-lord** is running at birth. Only the
*fraction of the star not yet traversed* is lived as the balance:

```
MD_bal = (star_end   − Moon) / star * Y_star * 365.25     # days
AD_bal = (sub_end    − Moon) / star * Y_star * 365.25     # days
PD_bal = (subsub_end − Moon) / star * Y_star * 365.25     # days
```

where `star = 13°20'`, `star_end`/`sub_end`/`subsub_end` are the ends of the
Moon's star/sub/sub-sub, and `Y_star` is the star-lord's mahadasha years.

Every later full sub-period width:

```
parent−child period = years(parent) * years(child) / 120 * 365.25  days
```

`current_periods()` locates MD, AD and PD by counting days from the birth epoch,
with the birth AD/PD balances only applied to the opening periods.

## Significators (Nirdeshan)

A planet **signifies** a house by:

1. **Occupation** — it sits in the house.
2. **Sign-lordship** — it rules the sign whose cusp begins the house.
3. **Star-lord agency** — its (nakshatra) star-lord occupies or owns the house;
   a planet delivers the results signified by its star-lord.

For judgement, **Bhaav Nirdeshan** ranks per house (strength tiers):

| Tier | Meaning |
|------|---------|
| 1 | Occupant of the house |
| 2 | A planet in an occupant's star |
| 3 | The cuspal lord |
| 4 | A planet in the cuspal lord's star |

The **sub-lord of a house cusp** (`cusp_sub_lords`) is the final arbiter of
that house's matters.

## Ruling planets

The ruling planets (RPs) of a moment are the sign / star / sub lords of the
**ascendant**, the same three of the **Moon**, and the **day-lord** (weekday).
`ruling_planets()` deduplicates and merges their sources.

## KP horary — why 249 divisions

- 27 stars × 9 sub-lords = **243 subs** from 0° Aries.
- Six of the twelve sign boundaries fall *inside* a sub. They split that sub in
  two: the sub-lord is unchanged but the **sign changes**.
- Result: **243 + 6 = 249** numbered divisions.

A querent's number *n* (1–249) selects division *n*; the **horary ascendant is
the division's midpoint**:

```
asc(n) = (division_start + division_end) / 2
```

## Houses

Placidus cusps come from the Swiss Ephemeris (`swe.houses_ex(jd, lat, lon, "P")`)
and are converted to the sidereal zodiac. House assignment walks counter-clockwise
from each cusp to the next, wrapping from cusp 12 to cusp 1 + 360°.

## Precision

| Situation | Accuracy |
|-----------|----------|
| No data files (default) | Moshier ephemeris: planets < 1", Moon ≈ 0.5" |
| `*.se1` files present | Full compressed VSOP87 / JPL DE431 Swiss Ephemeris |