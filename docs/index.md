# kpastro

**kpastro** is a precise **Krishnamurti Paddhati (KP)** Vedic astrology engine
written in pure Python, powered by the [Swiss Ephemeris](https://www.astro.com/swisseph/)
for arc-second accuracy. It is available both as a typed Python library and as a
`kpastro` command-line tool.

KP (Prof. K. S. Krishnamurti) refines the 27 nakshatras into **sub-lord** and
**sub-sub-lord** divisions, so every point of a chart carries a precise ruling
chain — *star-lord → sub-lord → sub-sub-lord* — used for dasha timing, event
judgement (significators) and prashna (horary).

```python
from datetime import date, time
from kpastro import BirthInfo, compute_chart, render_chart

birth = BirthInfo(
    date=date(1990, 1, 15), time=time(14, 30),
    latitude=28.6139, longitude=77.2090, tz_hours=5.5, place="New Delhi",
)
chart = compute_chart(birth, ayanamsa="lahiri")
print(render_chart(chart))
```

## Feature overview

| Area | What you get |
|------|--------------|
| Positions | All 9 KP planets (7 grahas + Rahu/Ketu) in the sidereal zodiac with daily speed & retrograde flags |
| Ayanamsa | `lahiri` (Chitrapaksha, KP default), `kp` (modern VP291) and `kp_old` (Krishnamurti's table) |
| Subdivision | Star-lord / sub-lord / sub-sub-lord chains and padas for any longitude |
| Houses | Placidus cusps in the sidereal zodiac, Ascendant/MC/ARMC, planet-to-house placement |
| Dasha | Vimshottari mahadasha/antardasha/pratyantar-dasha with nested birth balances |
| Significators | Grah (planet→house) and Bhaav (house→planet) Nirdeshan with 4-tier strength, cusp sub-lords |
| Ruling planets | Day-lord + Ascendant/Moon sign/star/sub lords |
| Horary | The complete 1–249 KP division system with division-midpoint ascendants |
| Precision | Full JPL/VSOP87 Swiss Ephemeris when data files are installed; silent Moshier fallback otherwise |
| Interfaces | Typed Python API, `python -m kpastro`, and a `kpastro` console script |

## Installation

```bash
pip install kpastro
```

Requires **Python 3.9+**. `pyswisseph` is the only runtime dependency. See
[Installation](installation.md) for the CPython-version caveat and how to
download the full-precision ephemeris files.

## Contents of this documentation

- **[Installation](installation.md)** — install, requirements, ephemeris data files
- **[User guide](user-guide.md)** — the command-line interface in depth
- **[Examples](examples.md)** — real Python API usage
- **[API reference](api-reference.md)** — every public function, class and constant
- **[Mathematics](mathematics.md)** — the KP conventions implemented, with formulas
- **[Development](development.md)** — setting up, testing, releasing
- **[FAQ](faq.md)** — common questions and troubleshooting