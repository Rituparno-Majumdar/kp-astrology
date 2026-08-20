# FAQ

## Accuracy and data

**Q: How accurate are the positions if I don't download anything?**

The Swiss Ephemeris' built-in **Moshier** ephemeris is used automatically —
planets to about 1 arc-second, Moon about 0.5". This is well within what KP
sub-lord work needs (the finest sub is ~1°06' wide at minimum).

**Q: How do I get full precision?**

Run `kpastro download-ephemeris` once. It places `sepl_18.se1`, `semo_18.se1`
and `seas_18.se1` in `~/.kpastro/ephe`, after which all calculations use the
full compressed VSOP87 / JPL DE431 ephemeris. Set `SE_EPHE_PATH` to use a
different directory.

**Q: Why did pip try to compile `pyswisseph`?**

On CPython 3.12+ official `pyswisseph` wheels are not published, so pip builds
from source. Install a C compiler first, or see the
[installation notes](installation.md).

## KP questions

**Q: Which ayanamsa should I use?**

`lahiri` is the KP default and the de facto standard for KP software. `kp`
(the modern VP291 value) and `kp_old` (Krishnamurti's original table) are
available for comparison.

**Q: Why does my chart list 9 "planets"?**

KP works with the seven classical grahas plus the two lunar nodes: Rahu and
Ketu. Rahu's longitude is the lunar node; Ketu is fixed at Rahu + 180°.

**Q: What are "significators"?**

The houses a planet connects to by occupation, sign-lordship and star-lord
agency. `house_significations` gives the reverse (Bhaav Nirdeshan): for each
house, the planets judging it, ranked by the 4-tier strength system. The
**cusp's sub-lord** is the final word for that house.

**Q: Why are there 249 horary divisions and not 243?**

27 stars × 9 subs = 243, but six zodiac sign boundaries fall *inside* a sub and
split it, yielding 249 numbered divisions. The horary ascendant is the midpoint
of the chosen division.

## Usage

**Q: `kpastro` isn't on PATH after install.**

On some setups scripts land outside `PATH` (e.g. `%APPDATA%\Python\...\Scripts`
on Windows). Add that directory to `PATH`, or use `python -m kpastro` which
always works.

**Q: My birth timezone has DST — does `kpastro` handle it?**

No — `tz_hours` is treated as a fixed UTC offset. Convert to the correct
standard offset yourself (e.g. `5.5` for IST year-round; for DST regions pass
the offset effective on the birth date).

## Versioning

**Q: Why does `kpastro.__version__` differ from what I installed?**

It shouldn't — it is read from installed metadata. If you hold an editable
install of an older checkout, uninstall the editable install and
`pip install --upgrade kpastro` to match the index.

## Support

Open an issue at the
[issue tracker](https://github.com/Rituparno-Majumdar/kp-astrology/issues)
with the exact command/code, expected vs actual output, and your
`kpastro ayanamsa --date <date>` output if positions are involved.