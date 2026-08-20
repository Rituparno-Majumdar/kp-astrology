"""Runnable demo: a KP natal chart and a KP horary number, printed to stdout.

Run from anywhere inside the project:

    python examples/demo.py

or after ``pip install -e .`` from any directory.
"""

from datetime import date, time

from kpastro import (
    BirthInfo,
    ascendant_from_kp_number,
    compute_chart,
    kp_divisions,
    render_chart,
)


def main() -> None:
    print("KP NATAL CHART - New Delhi, 1990-01-15 14:30 IST")
    print("=" * 72)
    birth = BirthInfo(
        date=date(1990, 1, 15),
        time=time(14, 30),
        latitude=28.6139,
        longitude=77.2090,
        tz_hours=5.5,
        place="New Delhi",
    )
    chart = compute_chart(birth, ayanamsa="lahiri")
    print(render_chart(chart))
    print()

    print("KP HORARY (Prashna) - number 45, 2026-08-20 10:30 IST")
    print("=" * 72)
    q = ascendant_from_kp_number(45)
    print(
        f"KP number {q['number']}: ascendant {q['ascendant']:.4f} deg "
        f"({q['sign']}), star {q['star']} ({q['star_lord']}), "
        f"sub {q['sub_lord']}, sub-sub {q['sub_sub_lord']}"
    )
    print(f"Total KP divisions in the zodiac: {len(kp_divisions())}")
    print()


if __name__ == "__main__":
    main()
