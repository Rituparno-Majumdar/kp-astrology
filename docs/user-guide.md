# User guide — the command line

`kpastro` is a console script that performs every KP calculation the library
offers. It can also be run as `python -m kpastro` — the two are equivalent:

```bash
kpastro <subcommand> [options]
python -m kpastro <subcommand> [options]
```

## Global options

| Option | Meaning |
|--------|---------|
| `--version` | Print the installed version and exit |
| `-h`, `--help` | Show help for the tool or a subcommand |

```bash
kpastro --help            # list subcommands
kpastro natal --help      # show all options of the natal subcommand
```

## Common chart options

Every chart subcommand (`natal`, `horary`, `dasha`, `rulings`) accepts the same
set of "instant + place" options:

| Option | Default | Meaning |
|--------|---------|---------|
| `--date DATE` | today | Birth/event date as `YYYY-MM-DD` |
| `--time TIME` | `12:00` | Local time as `HH:MM` or `HH:MM:SS` |
| `--tz HOURS` | `+5.5` | UTC offset in hours (India is `5.5`) |
| `--lat LAT` | — (required) | Geographic latitude in decimal degrees |
| `--lon LON` | — (required) | Geographic longitude in decimal degrees |
| `--place TEXT` | `""` | Free-text place label shown in output |
| `--ayanamsa MODE` | `lahiri` | One of `lahiri`, `kp`, `kp_old` |
| `--node MODE` | `mean` | Node: `mean` (KP traditional) or `true` |

### Ayanamsa modes

| Value | Swiss Ephemeris mode | Notes |
|-------|----------------------|-------|
| `lahiri` | `SE_SIDM_LAHIRI` | Chitrapaksha zero point — the default used by most KP software |
| `kp` | `SE_SIDM_KRISHNAMURTI_VP291` | The modern KP ayanamsa (VP291) |
| `kp_old` | `SE_SIDM_KRISHNAMURTI` | Krishnamurti's original table |

## `kpastro natal` — complete KP birth chart

Full birth chart: planets, house cusps, significators, ruling planets and the
Vimshottari timeline, rendered as text tables.

```bash
kpastro natal \
    --date 1990-01-15 --time 14:30 --tz 5.5 \
    --lat 28.6139 --lon 77.2090 --place "New Delhi"
```

Output sections:

1. **Header** — date/time, coordinates, tz, ayanamsa mode + value, Ascendant & MC.
2. **Planets** — sidereal longitude, sign, star, sub, sub-sub, house, retrograde flag.
3. **House cusps** — Placidus cusps in the sidereal zodiac with KP lord chains.
4. **Significators** — Bhaav Nirdeshan: the planets of each house with strength tiers.
5. **Ruling planets** — day-lord and the Ascendant/Moon sign/star/sub lords.
6. **Vimshottari dasha** — mahadasha timeline and the MD/AD/PD running at birth.

## `kpastro horary` — KP prashna from a 1–249 number

The KP horary ascendant is the midpoint of the querent's division. `kpastro`
prints that ascendant with its full lord chain, then the complete moment chart.

```bash
kpastro horary --number 45 \
    --date 2026-08-20 --time 10:30 --tz 5.5 \
    --lat 28.61 --lon 77.20
```

`--number` must be an integer **1–249**.

## `kpastro dasha` — Vimshottari timeline only

Prints the birth Moon's dasha balance and every mahadasha with start/end dates
(1 dasha year = 365.25 days).

```bash
kpastro dasha --date 1990-01-15 --time 14:30 --tz 5.5 --lat 28.6139 --lon 77.2090
```

## `kpastro rulings` — ruling planets of a moment

The seven potential RPs (deduplicated): weekday lord + the sign/star/sub lords
of the ascendant and of the Moon.

```bash
kpastro rulings --date 2026-08-20 --time 10:30 --tz 5.5 --lat 28.61 --lon 77.20
```

## `kpastro ayanamsa` — the ayanamsa value on a date

```bash
kpastro ayanamsa --date 2026-08-20
kpastro ayanamsa --date 2026-08-20 --ayanamsa kp
```

Prints the ayanamsa (at 12:00 UT on that date) in `D°MM'SS"`.

## `kpastro download-ephemeris` — full-precision data files

```bash
kpastro download-ephemeris
kpastro download-ephemeris --dir C:/ephe
```

Downloads `sepl_18.se1`, `semo_18.se1`, `seas_18.se1` into `~/.kpastro/ephe`
(or `--dir`). Subsequent calculations automatically use them. Already-present,
non-empty files are skipped.

## Examples cookbook

```bash
# A chart with the modern KP ayanamsa and the true node
kpastro natal --date 1988-12-09 --time 09:15 --tz 5.5 \
    --lat 19.0760 --lon 72.8777 --place "Mumbai" --ayanamsa kp --node true

# The same birth but only the dasha view
kpastro dasha --date 1988-12-09 --time 09:15 --tz 5.5 --lat 19.0760 --lon 72.8777

# A horary from the querent's number 132
kpastro horary --number 132 --date 2026-08-20 --time 10:30 --tz 5.5 \
    --lat 28.61 --lon 77.20 --place "Delhi"
```

## Exit codes

Subcommands return `0` on success. Errors (invalid dates, out-of-range horary
numbers, unknown ayanamsa mode, missing required `--lat`/`--lon`) are reported
with a usage message and a non-zero exit code, so the CLI is safe to script.