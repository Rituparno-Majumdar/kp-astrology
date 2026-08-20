# Changelog

All notable changes to **kpastro** are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed

- **Sub-sub-lord division bug** — the sub-sub was scaled against the star's
  800' span instead of the sub's own width, so `sub_sub_lord == sub_lord` for
  every interior longitude and the pratyantar-dasha level duplicated the
  antardasha. Now correctly scaled (regression tests included).
- **Dasha balance for un-normalised Moons** — `dasha_balance` folded a raw
  longitude such as `-0.1` into a 459-year Mercury mahadasha; the Moon is now
  normalised at entry.
- **Exact-boundary stability** — star/sub boundaries are built from exact
  arc-minute cumulative sums, so a longitude exactly on an edge (e.g. 280.0°)
  resolves deterministically to the following star/sub instead of drifting by
  an ulp. Sub-lord/sub-sub lookup also gets a boundary tolerance and can no
  longer raise inside the last arc of a nakshatra, and `format_longitude` no
  longer prints `59'60"`.
- **Chart day-lord** — computed from the local civil weekday (`birth.date`),
  not the UTC weekday, so charts near midnight no longer report the wrong
  ruling day-lord.
- **Significators** — house significator sets now include sign-lordship
  (ownership); the cuspal sub-lord ("final arbiter") is surfaced in rendering.
- **Rectification honesty** — the "credible interval" is renamed in prose to
  a **posterior band**: it is now the shortest contiguous span holding the
  target mass (a descriptive softmax band, documented as *not* a statistical
  credible interval), its peak is chosen with the same tie-break as `best`,
  and the temperature/target mass are emitted.
- **Rectification validation** — events dated before birth are rejected with a
  clear `ValueError` instead of being silently half-scored; `LifeEvent`
  validates houses (1-12) at construction; one shared validator is used by
  `rectify`/`score_candidate`/`transit_confirmation`.
- **Robustness** — `BirthInfo` validates date, lat/lon and tz and rejects
  polar latitudes (Placidus undefined); `download_ephemeris` writes atomically
  and refuses truncated/error responses; the global sidereal mode is guarded
  by a lock; pre-1582 dates use the Julian calendar; `jd_ut` tolerates both
  `pyswisseph` return arities.

### Changed

- CLI: malformed dates, out-of-range horary numbers and coordinates now exit
  with usage (code 2) instead of a raw traceback; `kp_number_for_longitude`
  always returns a division (longitudes are normalised).
- Performance: rectification hoists the slow planets/star lords out of the
  per-minute loop (only Moon + houses are recomputed per candidate); a shared
  `SCORING` block names every heuristic weight.
- Tests: CLI suite added (previously 0% covered), coverage floor of 85%
  enforced via `pytest-cov`, plus golden sub-sub, boundary, ayanamsa-mode,
  snapshot-equivalence and single-event regression tests.
- CI matrix widened to CPython 3.9-3.13; `mkdocs build --strict` passes; docs
  version/matrix claims corrected.

## [0.2.0] - 2026-08-20

- **New: birth-time rectification** (`kpastro.rectification`) — the classic KP
  "time of birth" method, ported from the reference web tool and rebased on the
  Swiss Ephemeris. Given an approximate birth time and dated life events mapped
  to KP houses, it scans a window minute-by-minute and scores every candidate
  by lagna sub-lord hit rate, Vimshottari dasha confirmation, the optional
  ruling-planet test and an optional sibling (identity) hint.
- Output is a ranked candidate list plus a **credible interval** (softmax over
  scores, temperature 1.5) so the headline is an honest time *range*, and a
  Jupiter/Saturn **transit confirmation** cross-check.
- New public names: `rectify`, `score_candidate`, `LifeEvent`, `IdentityInfo`,
  `CandidateScore`, `EventScore`, `RectificationResult`, `CredibleInterval`,
  `TransitConfirmation`, `EventTransit`, `aspects_from_house`,
  `house_significator_sets`, `transit_confirmation`, `credible_interval`,
  `render_rectification`.
- Docs: rectification covered in the feature table, examples, mathematics and
  API reference.

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
