# kpastro

A precise Krishnamurti Paddhati (KP) Vedic astrology engine in pure Python, powered by the Swiss Ephemeris for arc-second accuracy.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/)
[![Krishnamurti Paddhati](https://img.shields.io/badge/Krishnamurti%20Paddhati-Vedic%20Jyotish-6a3d9a.svg)](https://en.wikipedia.org/wiki/Krishnamurti_Paddhati)
[![Status](https://img.shields.io/badge/status-active-brightgreen.svg)](https://github.com/Rituparno-Majumdar/kp-astrology)
[![Swiss Ephemeris powered](https://img.shields.io/badge/powered%20by-Swiss%20Ephemeris-orange.svg)](https://www.astro.com/swisseph/)

---

## What is KP Astrology?

Krishnamurti Paddhati (KP) is a stellar system of Vedic astrology developed by Prof. K. S. Krishnamurti that refines the 27 nakshatras into smaller **sub-lord** and **sub-sub-lord** divisions, so every chart point carries a precise ruling chain: *star-lord, sub-lord, sub-sub-lord*. Because a birth Moon sits inside one of 249 narrow zodiacal divisions, KP timing (Vimshottari dasha) and event judgment (significators, horary) reach a granularity classical jyotish does not.

**Why Swiss Ephemeris precision** — the engine computes every planet and house cusp with the industry-standard Swiss Ephemeris (arc-second accurate), then converts to the sidereal zodiac with a configurable ayanamsa. A silent Moshier fallback keeps the package working even with no data files installed; downloading the official ephemeris files unlocks full JPL/VSOP87 precision.

## Key features

- **Ayanamsa** — Lahiri (Chitrapaksha, KP default), KP (`SE_SIDM_KRISHNAMURTI_VP291`) and KP-old (Krishnamurti's table).
- **Nakshatra subdivision** — star-lord, sub-lord and sub-sub-lord chains for every planet and house cusp.
- **Placidus cusps** — computed sidereally from the Swiss Ephemeris, with full KP lord chains on each cusp.
- **Vimshottari dasha** — mahadasha / antardasha / pratyantar-dasha with birth balances computed at all three levels (MD/AD/PD).
- **Significators** — Grah and Bhaav Nirdeshan: house and planet significators with 4-tier ranking.
- **Ruling planets** — day-lord, ascendant-lord and Moon-lord for the moment.
- **KP horary** — the 1-249 division number system with the horary ascendant taken as the division midpoint.
- **CLI + Python API** — everything available as a typed library *and* as a `kpastro` command-line tool.

## Install

Requires **Python 3.9+**.

```bash
# editable install for development
pip install -e .

# with the dev/test extras
pip install -e .[dev]
```

`pyswisseph` is the only runtime dependency. On very new CPython releases a source build may be needed; ensure a C compiler is available (or install a pre-built wheel) if the binary wheel is not yet published.

## Quick start (CLI)

```bash
# Complete KP birth chart (New Delhi)
python -m kpastro natal --date 1990-01-15 --time 14:30 --tz 5.5 \
    --lat 28.6139 --lon 77.2090 --place "New Delhi"

# KP horary (Prashna) from number 45
python -m kpastro horary --number 45 --date 2026-08-20 --time 10:30 \
    --tz 5.5 --lat 28.61 --lon 77.20

# Ayanamsa value on a date
python -m kpastro ayanamsa --date 2026-08-20

# Download the Swiss Ephemeris data files for full precision
python -m kpastro download-ephemeris
```

Other subcommands: `dasha`, `rulings`. Run `python -m kpastro --help` for all options.

## Python API

```python
from datetime import date, time
from kpastro import BirthInfo, compute_chart, render_chart, ascendant_from_kp_number

birth = BirthInfo(
    date=date(1990, 1, 15), time=time(14, 30),
    latitude=28.6139, longitude=77.2090,
    tz_hours=5.5, place="New Delhi",
)
chart = compute_chart(birth, ayanamsa="lahiri")
print(render_chart(chart))

# KP horary: all 249 divisions, or the ascendant for one number
divs = kp_divisions()                 # list of 249 HoraryDiv
q = ascendant_from_kp_number(45)      # dict with ascendant + lord chain
```

`chart.planets`, `chart.cusps`, `chart.balance`, `chart.mahadashas`, `chart.current`,
`chart.planet_significators` and `chart.ruling` give typed access to every KP layer.

## The mathematics

**Ayanamsa** — the sidereal zodiac is the tropical zodiac minus the ayanamsa:

```text
sidereal longitude = tropical longitude - ayanamsa
```

The Chitrapaksha (Lahiri) zero point anchors the sidereal origin to the star Spica (Chitra) at 0° Libra. Lahiri and KP modes differ only in the exact reference and precession model used; around **2026 the ayanamsa is approximately 24.14°**.

**Nakshatra** — the zodiac is divided into 27 nakshatras of **13°20' = 800'** each.

**Sub-lords** — each nakshatra is split into 9 sub-lords whose spans are proportional to the Vimshottari years:

```text
sub span (arcmin) = (lord's years / 120) * 800'
```

The sub-lord sequence starts at the star-lord and cycles through the Vimshottari order; the sub-sub-lord divides the sub again with the same proportions.

**Vimshottari years** — the total cycle is 120 years:

| Planet | Years |
|--------|-------|
| Ketu   | 7     |
| Venus  | 20    |
| Sun    | 6     |
| Moon   | 10    |
| Mars   | 7     |
| Rahu   | 18    |
| Jupiter| 16    |
| Saturn | 19    |
| Mercury| 17    |

**Nakshatra lord mapping** — the star-lord of nakshatra `i` (0-26) is:

```text
star_lord(i) = VIMSHOTTARI_ORDER[i % 9]
```

so the 9-planet Vimshottari cycle repeats every 9 nakshatras: Ketu, Venus, Sun, Moon, Mars, Rahu, Jupiter, Saturn, Mercury, then repeats.

**Dasha balance at birth** — anchored to the birth Moon's nakshatra (span `star` = 13°20'), with 1 year = 365.25 days:

```text
MD_bal  = (star_end   - Moon) / star * Y_star * 365.25   # mahadasha balance
AD_bal  = (sub_end    - Moon) / star * Y_star * 365.25   # antardasha balance
PD_bal  = (subsub_end - Moon) / star * Y_star * 365.25   # pratyantar-dasha balance
```

where `star_end` is the end of the Moon's nakshatra, `sub_end` / `subsub_end` the ends of the Moon's sub / sub-sub, and `Y_star` the mahadasha years of the star-lord. Every subsequent sub-period is `Y_parent * Y_child / 120` years.

**Why 249 divisions for horary** — 27 nakshatras × 9 sub-lords = 243 subs. Six of the twelve sign boundaries fall *inside* a sub and split it in two (the sub-lord is unchanged but the sign changes), giving exactly **249 numbered KP divisions** from 0° Aries. A querent's number 1-249 selects division *n*; the horary ascendant is that division's midpoint.

## Accuracy & data files

- **Moshier fallback (default, no downloads)** — planets to about **1 arc-second**, Moon about **0.5"**. More than adequate for KP sub-lord work.
- **Full Swiss Ephemeris precision** — run `python -m kpastro download-ephemeris` (or `download_ephemeris()`), which places `sepl_18.se1`, `semo_18.se1` and `seas_18.se1` into `~/.kpastro/ephe`. The engine then uses the compressed **VSOP87 / JPL DE431** ephemeris at full precision. The files are also picked up from `SE_EPHE_PATH`.

## Project layout

```
src/kpastro/
  __init__.py       public API surface + version
  __main__.py       python -m kpastro entry point
  constants.py      Vimshottari tables, signs, nakshatras, sign-lords
  vedic.py          pure-Python KP subdivision math (star / sub / sub-sub)
  ephemeris.py      Swiss Ephemeris wrapper, ayanamsa, houses, downloads
  chart.py          BirthInfo, compute_chart, render_chart
  dasha.py          Vimshottari balances, timelines, sub-periods
  significators.py  Grah & Bhaav Nirdeshan, ruling planets
  horary.py         the 249-division KP number system
  cli.py            argparse CLI (natal / horary / dasha / ayanamsa / ...)
```

## Roadmap

- [ ] Full dasha view with all 120 sub-periods and transit overlays.
- [ ] Navamsa and other vargas in the KP scheme.
- [ ] KP year (KPY) and Saturn-return timing helpers.
- [ ] Western-style event chart export (JSON / CSV).
- [ ] Optional TinyDB/Pandas output and Jupyter notebooks.
- [ ] Contribution-driven: more ayanamsa modes, house systems, node options.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, tests and style. Feedback and pull requests are welcome — file issues at the [issue tracker](https://github.com/Rituparno-Majumdar/kp-astrology/issues).

## License

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 Rituparno Majumdar.

## Disclaimer

This software is provided for **educational and scientific** purposes only. Astrological interpretations are not scientific predictions, and nothing here should be used to make financial, medical or legal decisions.
