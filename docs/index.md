---
description: A precise Krishnamurti Paddhati (KP) Vedic astrology engine in pure Python, powered by the Swiss Ephemeris for arc-second accuracy. Compare kpastro with generalist libraries and API-only tools.
---

# kpastro

**kpastro** is a precise Krishnamurti Paddhati (KP) Vedic astrology engine in pure Python, powered by the Swiss Ephemeris for arc-second accuracy. It is available both as a typed Python library and as a `kpastro` command-line tool.

KP (Prof. K. S. Krishnamurti) refines the 27 nakshatras into **sub-lord** and **sub-sub-lord** divisions, so every point of a chart carries a precise ruling chain — *star-lord → sub-lord → sub-sub-lord* — used for dasha timing, event judgement (significators) and prashna (horary).

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

| Area | kpastro | Generalist Libraries | API-only Tools |
|------|---------|----------------------|----------------|
| **KP Specialization** | **High (249-Division)** | Low/None | Variable |
| **Precision** | **Arc-second (Swiss Ephemeris)** | Variable | High |
| **Deployment** | **Offline-first (No API)** | Varies | Requires Internet |
| **Integrability** | **Designed as an engine** | Complex/Bloated | Locked to Cloud |

## Feature comparison: kpastro vs alternatives

| Capability | kpastro | vedicastro | ndastro-engine | OpAstro | kpastro.ai |
|------------|---------|------------|----------------|---------|------------|
| **249-sub division** | ✅ Full | ⚠️ Basic | ⚠️ Basic | ❌ None | ✅ Full |
| **Ayanamsa modes** | Lahiri, KP (VP291), KP-old | Lahiri only | Lahiri only | Lahiri only | Varies |
| **Swiss Ephemeris** | ✅ Full (optional download) | ✅ Full | ✅ Full | ✅ Full | Variable |
| **Vimshottari dasha** | ✅ MD/AD/PD with birth balances | ✅ 3 levels | ✅ 3 levels | ✅ 3 levels | ✅ 3 levels |
| **Birth-time rectification** | ✅ Scoring ±60 min | ❌ Not published | ❌ Not published | ❌ Not published | ✅ AI-powered |
| **CLI + Python API** | ✅ Both | ✅ API-only | ✅ API-only | ✅ CLI + API | ✅ API-only |
| **Offline-first** | ✅ Yes | ⚠️ Depends | ⚠️ Depends | ❌ No | ⚠️ Depends |
| **Pricing** | Free (MIT) | MIT | Apache-2.0 | Open-core | Varies |

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
- **[Examples](examples.md)** — real Python API usage, including birth-time rectification
- **[API reference](api-reference.md)** — every public function, class and constant
- **[Mathematics](mathematics.md)** — the KP conventions implemented, with formulas
- **[Development](development.md)** — setting up, tests, releasing
- **[FAQ](faq.md)** — common questions and troubleshooting