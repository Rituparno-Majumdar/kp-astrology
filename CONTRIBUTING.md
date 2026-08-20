# Contributing to kpastro

Thanks for your interest in contributing to the KP astrology engine. This guide covers setup, tests, style and pull requests.

## Setting up a development environment

Requires Python 3.9+.

```bash
# clone and enter the repo, then:
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Optionally download the Swiss Ephemeris data files for full-precision calculations:

```bash
python -m kpastro download-ephemeris
```

## Running the tests

```bash
python -m pytest
```

Tests live in `tests/` and use pytest. Keep new tests focused on a single unit
of behaviour (subdivision math, dasha balances, horary divisions, CLI output).

## Code style

- Follow [PEP 8](https://peps.python.org/pep-0008/); 88-column lines are preferred.
- Keep the pure-Python KP math (`vedic.py`, `dasha.py`) free of I/O and side effects.
- Module docstrings explain the *convention* being implemented (see `vedic.py`).
- No third-party runtime deps beyond `pyswisseph`.

## Pull request guidelines

1. Create a branch: `git checkout -b feature/your-feature`.
2. Make your change and add tests covering it.
3. Run `python -m pytest` and make sure the full suite passes.
4. Keep the change scoped; describe *why* in the PR body.
5. Do not commit Swiss Ephemeris data files (`*.se1`) or build artifacts.

## Reporting issues

Include the exact command or code snippet, expected vs. actual output, and your
`python -m kpastro ayanamsa --date <date>` output if the issue involves
positions. File issues at the
[issue tracker](https://github.com/Rituparno-Majumdar/kp-astrology/issues).
