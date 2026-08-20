# Development

Guide for building, testing and releasing **kpastro**. See also the
[CONTRIBUTING guide](https://github.com/Rituparno-Majumdar/kp-astrology/blob/main/CONTRIBUTING.md)
for contributor etiquette.

## Project layout

```
kp-astrology/
  src/kpastro/
    __init__.py       public API surface + version
    __main__.py       python -m kpastro entry point
    constants.py      Vimshottari tables, signs, nakshatras, sign-lords
    vedic.py          pure-Python KP subdivision math (star / sub / sub-sub)
    ephemeris.py      Swiss Ephemeris wrapper, ayanamsa, houses, downloads
    chart.py          BirthInfo, compute_chart, render_chart
    dasha.py          Vimshottari balances, timelines, sub-periods
    significators.py  Grah & Bhaav Nirdeshan, ruling planets
    rectification.py  birth-time rectification (KP "time of birth" method)
    horary.py         the 249-division KP number system
    cli.py            argparse CLI (natal / horary / dasha / ayanamsa / ...)
  tests/              pytest suite
  examples/demo.py    runnable demo
  docs/               documentation (this site, MkDocs)
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate                  # Windows
# source .venv/bin/activate            # macOS / Linux
pip install -e ".[dev]"                # package + pytest
pip install -e ".[docs]"               # optional: MkDocs to build the docs site
```

## Testing

```bash
python -m pytest                        # full suite
python -m pytest tests/test_vedic.py    # single module
```

The suite covers subdivision math, dasha balances, horary divisions, chart
construction and CLI output. Keep new tests focused on one unit of behaviour.

## Building the documentation site

```bash
pip install -e ".[docs]"
mkdocs build            # static site in site/
mkdocs serve            # live preview at http://127.0.0.1:8000
mkdocs gh-deploy        # publish to https://rituparno-majumdar.github.io/kp-astrology/
```

The docs are deployed **automatically** by `.github/workflows/docs.yml` on every
push to `main` and on every `v*` release tag.

## Building and checking the distribution

```bash
pip install build twine
python -m build                        # sdist + wheel in dist/
python -m twine check dist/*           # metadata/README validation
```

The sdist ships the `docs/` tree and the changelog/contributing guides.

## Releasing (PyPI)

Releases are **tag-triggered** — `.github/workflows/publish.yml` builds and
uploads to PyPI whenever a `v*` tag is pushed. There is no manual twine step.

```bash
# 1. bump the version (keep pyproject.toml and CHANGELOG.md in sync)
code pyproject.toml CHANGELOG.md

# 2. commit and push the bump
git add pyproject.toml CHANGELOG.md src/kpastro/__init__.py
git commit -m "Release 0.1.3: ..."
git push

# 3. tag the release and push the tag — this triggers the publish workflow
git tag v0.1.3
git push origin v0.1.3

# 4. watch the workflow
gh run list --workflow="Publish to PyPI" --limit 1

# 5. verify on PyPI
pip install --upgrade kpastro
python -c "import kpastro; print(kpastro.__version__)"
```

Notes on releasing:

- The **PyPI push is irreversible** for a given filename — you cannot overwrite
  `kpastro-0.1.3` once uploaded, so always bump the version for a new push.
- `kpastro.__version__` is derived from installed distribution metadata, so the
  runtime version always matches the release.
- The publish workflow uses the repo secret `PYPI_API_TOKEN` (Trusted
  Publishing can be adopted later if preferred).

## Continuous integration

`.github/workflows/ci.yml` runs the test suite on Ubuntu and Windows across
CPython 3.9–3.13 on every push to `main` and on pull requests, including the
full-precision ephemeris download and a CLI smoke test.