#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List

OUT_PATH = Path("data/ops/us_holidays.json")

def nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> date:
    """weekday: 0=Mon..6=Sun, n>=1"""
    d = date(year, month, 1)
    while d.weekday() != weekday:
        d += timedelta(days=1)
    return d + timedelta(days=7*(n-1))

def last_weekday_of_month(year: int, month: int, weekday: int) -> date:
    d = date(year, month+1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
    while d.weekday() != weekday:
        d -= timedelta(days=1)
    return d

def observed_if_weekend(d: date) -> date:
    # If holiday falls Sat => observed Fri, Sun => observed Mon
    if d.weekday() == 5:
        return d - timedelta(days=1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d

def thanksgiving(year: int) -> date:
    # 4th Thursday in November
    return nth_weekday_of_month(year, 11, weekday=3, n=4)

@dataclass
class HolidaySet:
    include_good_friday: bool = True  # optional

def easter_sunday(year: int) -> date:
    # Anonymous Gregorian algorithm (Meeus/Jones/Butcher)
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19*a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2*e + 2*i - h - k) % 7
    m = (a + 11*h + 22*l) // 451
    month = (h + l - 7*m + 114) // 31
    day = ((h + l - 7*m + 114) % 31) + 1
    return date(year, month, day)

def good_friday(year: int) -> date:
    return easter_sunday(year) - timedelta(days=2)

def generate_year(year: int, opts: HolidaySet) -> List[str]:
    days: List[date] = []

    # Fixed-date (observed)
    days.append(observed_if_weekend(date(year, 1, 1)))   # New Year's Day
    days.append(nth_weekday_of_month(year, 1, 0, 3))     # MLK Day: 3rd Mon Jan
    days.append(nth_weekday_of_month(year, 2, 0, 3))     # Washington: 3rd Mon Feb

    if opts.include_good_friday:
        days.append(good_friday(year))                  # Good Friday (market holiday)

    days.append(last_weekday_of_month(year, 5, 0))       # Memorial Day: last Mon May
    days.append(observed_if_weekend(date(year, 6, 19)))  # Juneteenth
    days.append(observed_if_weekend(date(year, 7, 4)))   # Independence Day
    days.append(nth_weekday_of_month(year, 9, 0, 1))     # Labor Day: 1st Mon Sep
    days.append(thanksgiving(year))                      # Thanksgiving: 4th Thu Nov
    days.append(observed_if_weekend(date(year, 12, 25))) # Christmas

    # unique + sort
    uniq = sorted({d for d in days})
    return [d.isoformat() for d in uniq]

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Generate NYSE/Nasdaq holiday dates (rule-based)")
    ap.add_argument("--year", type=int, default=date.today().year)
    ap.add_argument("--years", type=int, default=2, help="How many years to generate starting at --year")
    ap.add_argument("--no-good-friday", action="store_true")
    ap.add_argument("--out", default=str(OUT_PATH))
    args = ap.parse_args()

    opts = HolidaySet(include_good_friday=not args.no_good_friday)

    start = args.year
    years = {}
    for y in range(start, start + args.years):
        years[str(y)] = generate_year(y, opts)

    doc: Dict[str, object] = {
        "source": "rule_based",
        "notes": "Generated automatically (observed holidays). Good Friday optional.",
        "years": years,
    }

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"written: {outp} (years={list(years.keys())})")

if __name__ == "__main__":
    main()
