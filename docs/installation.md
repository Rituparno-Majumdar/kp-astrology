# Installation

## Requirements

- **Python 3.9 or newer** (3.9–3.13 are tested in CI; 3.14 is supported but CI
  coverage may lag the release cycle).
- One runtime dependency: [`pyswisseph>=2.10.3`](https://pypi.org/project/pyswisseph/)
  (the official Python binding of the Swiss Ephemeris).

## Install from PyPI

```bash
pip install kpastro
```

This installs the `kpastro` package and the `kpastro` console script.

### A note about CPython versions and `pyswisseph` wheels

`pyswisseph` publishes pre-built binary wheels only for CPython up to **3.11**.
On newer CPython releases (3.12+, including 3.13/3.14) pip will attempt to build
`pyswisseph` from source, which needs a working **C compiler** (MSVC on Windows,
`gcc`/`clang` on Linux/macOS). If you hit a build error:

1. Install a C compiler toolchain first, then retry `pip install kpastro`.
2. Or use a pre-built environment where a compiler is available.
3. Or install `pyswisseph` yourself from a wheel source that covers your Python
   version before installing `kpastro`.

## Install from the source repository (development)

```bash
git clone https://github.com/Rituparno-Majumdar/kp-astrology
cd kp-astrology
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate      # macOS / Linux

pip install -e ".[dev]"          # editable install + pytest
```

See [Development](development.md) for the full contributor workflow.

## Full-precision ephemeris data files

**kpastro works out of the box** using the Swiss Ephemeris' built-in *Moshier*
ephemeris (planet error < 1", Moon ~0.5"). That is more than adequate for KP
sub-lord work.

To unlock the full compressed **VSOP87 / JPL DE431** precision:

```bash
kpastro download-ephemeris
# or
python -m kpastro download-ephemeris
```

This downloads three files into `~/.kpastro/ephe/`:

| File | Content |
|------|---------|
| `sepl_18.se1` | planetary (VSOP87 / DE431) positions |
| `semo_18.se1` | lunar (DE431) positions |
| `seas_18.se1` | asteroidal (mainly Chebychev asteroids) |

The engine automatically picks the files up when it sees the `~/.kpastro/ephe`
directory, or the directory named by the `SE_EPHE_PATH` environment variable:

```bash
# positional: point kpastro at a custom data directory
set SE_EPHE_PATH=C:\swisseph\ephe        # Windows
export SE_EPHE_PATH=/usr/share/ephe      # macOS / Linux
```

You can also download programmatically and target another directory:

```python
from kpastro import download_ephemeris

paths = download_ephemeris("C:/ephe")     # or leave it out for the default
print(paths)                              # [PosixPath(...sepl_18.se1), ...]
```

## Verify the install

```bash
kpastro --version              # prints e.g. kpastro 0.3.0
kpastro ayanamsa --date 2026-08-20
python -c "import kpastro; print(kpastro.__version__)"
```