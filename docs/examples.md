# Examples — Python API

All examples below assume:

```python
from datetime import date, datetime, time, timedelta
from kpastro import (
    BirthInfo, compute_chart, render_chart,
    kp_divisions, ascendant_from_kp_number, kp_number_for_longitude,
    dasha_balance, current_periods, planet_significations,
    house_significations, ruling_planets, point_info,
    LifeEvent, IdentityInfo, rectify, render_rectification,
    transit_confirmation,
    download_ephemeris,
)
```

## 1. A complete birth chart

```python
birth = BirthInfo(
    date=date(1990, 1, 15), time=time(14, 30),
    latitude=28.6139, longitude=77.2090,
    tz_hours=5.5, place="New Delhi",
)
chart = compute_chart(birth, ayanamsa="lahiri")
print(render_chart(chart))
```

`chart` is a `Chart` — you can ignore the text rendering and use the data
directly:

```python
for p in chart.planets:
    print(f"{p.name:8} {p.sign:10} star {p.star:16} sub {p.sub_lord:8} "
          f"house {p.house:2} retro {'R' if p.retrograde else '.'}")

print("Cusp 1 sub-lord:", chart.cusp_sublords[1])
print("Ascendant:", chart.ascendant, "deg", "| MC:", chart.midheaven, "deg")
print("At birth:",
      chart.current[1].lord, "/", chart.current[2].lord, "/", chart.current[3].lord)
```

### Typed access to every layer

```python
balance = chart.balance
print(f"Maha-dasha: {balance.mahadasha_lord} "
      f"({balance.mahadasha_years:.2f} y / {balance.mahadasha_days:.1f} d) "
      f"in {balance.nakshatra}")

for house, tiers in enumerate(chart.house_significators, start=1):
    sig = ", ".join(f"{pl}({t})" for pl, t in tiers) or "—"
    print(f"H{house:>2}: {sig}")
```

## 2. Reuse one engine across many charts

The Swiss Ephemeris holds process-global state, so constructing one
`SwissEphemeris` and passing it in is both faster and cleaner:

```python
from kpastro import SwissEphemeris

eph = SwissEphemeris(ayanamsa="lahiri", node="mean")

charts = [
    compute_chart(BirthInfo(date(1990,1,15), time(14,30), 28.6139, 77.2090, 5.5, "New Delhi"), eph=eph),
    compute_chart(BirthInfo(date(1988,12,9), time(9,15), 19.0760, 72.8777, 5.5, "Mumbai"), eph=eph),
]
```

## 3. Vimshottari dasha

```python
from datetime import datetime, timedelta

moon = compute_chart(birth).planet_lon["Moon"]

bal = dasha_balance(moon)
print(f"{bal.mahadasha_lord}: MD {bal.mahadasha_days:.0f}d "
      f"| AD {bal.active_ad_lord} {bal.active_ad_days:.0f}d "
      f"| PD {bal.active_pd_lord} {bal.active_pd_days:.0f}d")

epoch = datetime(1990, 1, 15, 14, 30) - timedelta(hours=5.5)
active = current_periods(moon, epoch, datetime(2026, 1, 1, 12, 0))
print(f"On 2026-01-01: MD {active[1].lord}, AD {active[2].lord}, PD {active[3].lord}")
```

## 4. KP horary (prashna)

```python
q = ascendant_from_kp_number(45)
print(f"Number {q['number']}: asc {q['ascendant']:.4f} deg {q['sign']} "
      f"star {q['star']} ({q['star_lord']}), sub {q['sub_lord']}")

division_count = len(kp_divisions())      # exactly 249
back = kp_number_for_longitude(q["ascendant"])
print(division_count, "divisions;", back, "contains the midpoint")
```

## 5. Sub-division math without an ephemeris

Everything below uses only a sidereal longitude:

```python
info = point_info(48.9167)     # e.g. 18 Cancer 55
print(info.star, info.sub_lord, info.sub_sub_lord, "pada", info.pada)
```

## 6. Ruling planets

```python
rps = ruling_planets(chart.ascendant, chart.planet_lon["Moon"], 2)  # 2 = Wednesday
for rp in rps:
    print(f"{rp.planet:<10} {rp.source}")
```

## 7. Significators (Grah Nirdeshan)

```python
sig = planet_significations(chart.planet_lon, [c.longitude for c in chart.cusps])
for planet, entries in sig.items():
    why = []
    if any(e.by_occupation for e in entries): why.append("occupies")
    if any(e.by_sign_lordship for e in entries): why.append("owns")
    if any(e.by_star_lord for e in entries): why.append("star-lord")
    print(f"{planet:8} -> houses {[e.house for e in entries]} ({', '.join(why)})")
```

## 8. Full precision live

```python
paths = download_ephemeris()
print("Data files:", [p.name for p in paths])
```

After the files are present, all computations silently use the full-precision
VSOP87 / JPL DE431 ephemeris.

## 9. Birth-time rectification

Only the approximate birth time is known. Dated life events are mapped to the
KP houses they fell into, and the scanner finds the most probable minute:

```python
from kpastro import BirthInfo, LifeEvent, IdentityInfo, rectify, render_rectification

birth = BirthInfo(
    date(1990, 1, 15), time(14, 30),   # approximate time
    28.6139, 77.2090, 5.5, "New Delhi",
)

events = [
    LifeEvent(date(1995, 9, 3),  2, (), "School admission"),
    LifeEvent(date(2007, 4, 1),  4, (), "Joined college"),
    LifeEvent(date(2013, 2, 14), 4, (), "First job"),
    LifeEvent(date(2018, 1, 20), 7, (), "Marriage"),
]

result = rectify(birth, time(14, 30), events,
                 window_min=60, step_min=1,
                 use_rp=True,
                 identity=IdentityInfo(siblings=1),
                 analysis_time=datetime(2026, 1, 1, 12, 0))

print(render_rectification(result, birth))

# Typed access instead of the text report:
best = result.best
print(f"Best birth time: {best.lsl} total={best.total:.2f} strikes={best.strikes}")
ci = result.credible
# credible._ut fields are UTC datetimes; convert to local (IST here) for display
tz = timedelta(hours=birth.tz_hours)
print(f"Credible range: {(ci.start_ut + tz):%H:%M} - {(ci.end_ut + tz):%H:%M} "
      f"local ({ci.mass:.0%} mass)")
# every ranked candidate, in order
for c in result.candidates[:5]:
    print(f"{c.offset_minutes:+5.0f} min  {c.lsl:<8} total={c.total:.2f}")
```

`events` need only be dated and judged to a primary house (1–12) plus optional
secondary houses. Add `transit_confirmation` for the Jupiter/Saturn
cross-check:

```python
conf = transit_confirmation(best.jd_ut, birth.latitude, birth.longitude,
                            events, tz_hours=birth.tz_hours)
print(f"Jupiter/Saturn transit confirmations: {conf.matched}/{conf.total}")
```