"""Lyceum: on-demand and spot GPU prices from the public pricing page.

GET https://lyceum.technology/resources/pricing/
The GPU compute table lists, per GPU, its memory and the on-demand and spot
prices in USD per GPU-hour ("NVIDIA H100 80 GB On demand $4.69 Spot $2.39").
Lyceum runs in European regions only (Central, Northern, Southern and Western
Europe), so the prices are recorded as one catalogue price.
"""

from __future__ import annotations

import re

import requests

from ..http import TIMEOUT
from ..util import dec
from .base import Fetched, Offer
from .nebius import visible_text

URL = "https://lyceum.technology/resources/pricing/"

# The spot part is optional: for some GPUs the page repeats the on-demand price
# before "Spot Not offered".
ROW = re.compile(
    r"(?P<name>NVIDIA [A-Z0-9]+(?: [A-Z0-9]+)?) (?P<mem>\d+) GB "
    r"On demand \$(?P<od>[\d.]+)(?: Spot (?:\$(?P<spot>[\d.]+)|Not offered))?"
)


def extract_rows(page: str) -> list[dict]:
    rows: dict[str, dict] = {}
    for m in ROW.finditer(visible_text(page)):
        rows.setdefault(
            m.group("name"),
            {
                "name": m.group("name"),
                "memory_gb": int(m.group("mem")),
                "on_demand": m.group("od"),
                "spot": m.group("spot"),
            },
        )
    return list(rows.values())


class Lyceum:
    provider = "lyceum"
    version = 1
    method = "html"

    def fetch(self, http: requests.Session) -> Fetched:
        r = http.get(URL, timeout=TIMEOUT)
        r.raise_for_status()
        return Fetched(source_url=URL, records=extract_rows(r.text))

    def parse(self, fetched: Fetched) -> list[Offer]:
        offers = []
        for rec in fetched.records:
            for model, value in (("on_demand", rec["on_demand"]), ("spot", rec.get("spot"))):
                if not value:
                    continue
                offers.append(
                    Offer(
                        sku=rec["name"],
                        gpu_raw=rec["name"],
                        gpu_count=1,  # prices are per GPU-hour
                        price=dec(value),
                        currency="USD",
                        unit="hour",
                        pricing_model=model,
                        region="catalogue",
                        extra={"gpu_memory_gb": rec.get("memory_gb")},
                    )
                )
        return offers
