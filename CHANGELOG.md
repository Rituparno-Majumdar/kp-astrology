# Changelog

All notable changes to **kpastro** are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.5] - 2026-08-20

- Fix: multiple `SwissEphemeris` instances with different ayanamsa modes no longer
  override each other. The sidereal mode is process-global engine state, so the
  "apply only on change" optimisation now tracks the mode actually applied to the
  engine at module level instead of per instance.

## [0.1.4] - 2026-08-20

- Performance: memoize the KP horary division table; `kp_number_for_longitude` now
  uses binary search (measured ~3600x faster), `ascendant_from_kp_number` ~195x faster,
  full `compute_chart` ~830 -> ~1070 charts/s.
- Cache deterministic subdivision/dasha math (`sub_info`, `sub_sub_info`, `dasha_balance`).
- Re-apply the Swiss Ephemeris sidereal mode only when it changes.
- Host documentation on GitHub Pages: `.github/workflows/docs.yml` deploys the MkDocs
  site on every `main` push / release tag; page: https://rituparno-majumdar.github.io/kp-astrology/.

## [0.1.3] - 2026-08-20

- Add in-depth documentation: `docs/` user guide, API reference, worked examples,
  mathematics and FAQ (MkDocs site buildable via the `docs` extra; shipped in the sdist).
- Add `MANIFEST.in`; add `Documentation` project URL and `docs` install extra.

## [0.1.2] - 2026-08-20

- Derive `kpastro.__version__` from installed package metadata so runtime version always matches the PyPI release.

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
