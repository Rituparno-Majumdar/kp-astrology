# Changelog

All notable changes to **kpastro** are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.1] - 2026-08-20

- Add author email to package metadata for the PyPI project page.

## [0.1.0] - 2026-08-20

Initial engine release.

- Swiss Ephemeris backend with Lahiri / KP / KP-old ayanamsa and mean / true node.
- Automatic Moshier fallback when no ephemeris data files are present.
- Nakshatra subdivision math: star-lord, sub-lord and sub-sub-lord chains.
- Placidus house cusps in the sidereal zodiac with full KP lord chains.
- Vimshottari dasha with nested MD/AD/PD birth balances and timelines.
- Significators (Grah & Bhaav Nirdeshan) and ruling planets.
- KP horary: 249-division number system with horary ascendant.
- CLI (`natal`, `horary`, `dasha`, `rulings`, `ayanamsa`, `download-ephemeris`).
- Typed Python API: `BirthInfo`, `compute_chart`, `render_chart` and friends.
- `download-ephemeris` fetches `sepl_18.se1`, `semo_18.se1`, `seas_18.se1` into `~/.kpastro/ephe`.
- PyPI packaging via `pyproject.toml` (Python 3.9+).
