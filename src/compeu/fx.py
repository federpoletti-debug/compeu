"""ECB euro foreign exchange reference rates.

Source: ECB Data Portal, dataset EXR, daily reference rates (published around
16:00 CET on TARGET business days). A rate is "units of currency per 1 EUR", so
an amount in USD converts to EUR as amount / rate.

Rates are appended to ledger/fx/ecb.jsonl one line per date and never rewritten.
"""

from __future__ import annotations

import csv
import io
from datetime import date, timedelta
from decimal import Decimal
from functools import cache

import requests

from .http import TIMEOUT
from .ledger import append_lines, ledger_dir
from .util import read_jsonl

CURRENCIES = ("USD", "CHF", "GBP")
URL = "https://data-api.ecb.europa.eu/service/data/EXR/D.{ccy}.EUR.SP00.A"
FIRST_DATE = "2026-09-01"
MAX_GAP_DAYS = 6  # longest TARGET closure (Easter) is 4 days; beyond this, refuse to convert


def fx_file():
    return ledger_dir() / "fx" / "ecb.jsonl"


def fetch(http: requests.Session, start: str) -> dict[str, dict[str, str]]:
    """Rates by date from `start` (inclusive) to the latest published day."""
    r = http.get(
        URL.format(ccy="+".join(CURRENCIES)),
        params={"startPeriod": start, "format": "csvdata"},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    by_date: dict[str, dict[str, str]] = {}
    for row in csv.DictReader(io.StringIO(r.text)):
        if row["OBS_VALUE"]:
            by_date.setdefault(row["TIME_PERIOD"], {})[row["CURRENCY"]] = row["OBS_VALUE"]
    return by_date


def update(http: requests.Session) -> int:
    """Append any new ECB dates. Returns the number of dates added."""
    rows = read_jsonl(fx_file())
    last = rows[-1]["date"] if rows else None
    start = (date.fromisoformat(last) + timedelta(days=1)).isoformat() if last else FIRST_DATE
    fetched = fetch(http, start)
    new = [
        {"date": d, "rates": fetched[d], "source": "ECB EXR SP00.A"}
        for d in sorted(fetched)
        if (last is None or d > last) and set(fetched[d]) == set(CURRENCIES)
    ]
    if new:
        append_lines(fx_file(), new)
        rates.cache_clear()
    return len(new)


@cache
def rates() -> list[dict]:
    return read_jsonl(fx_file())


class MissingRate(LookupError):
    pass


def rate_on(day: str, currency: str) -> tuple[Decimal, str]:
    """ECB rate for `currency` on the latest date on or before `day`, and that date."""
    if currency == "EUR":
        return Decimal(1), day
    best = None
    for row in rates():
        if row["date"] <= day and currency in row["rates"]:
            best = row
    if best is None:
        raise MissingRate(f"no ECB {currency} rate on or before {day}")
    gap = (date.fromisoformat(day) - date.fromisoformat(best["date"])).days
    if gap > MAX_GAP_DAYS:
        raise MissingRate(f"latest ECB {currency} rate is {gap} days older than {day}")
    return Decimal(best["rates"][currency]), best["date"]


def to_eur(amount: Decimal, currency: str, day: str) -> tuple[Decimal, str]:
    rate, rate_date = rate_on(day, currency)
    return amount / rate, rate_date
