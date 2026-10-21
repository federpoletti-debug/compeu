"""Nebius: on-demand GPU prices from the public price page.

GET https://nebius.com/prices
The page lists one row per GPU: name, vCPUs, RAM, a preemptible price ("from $0.79")
and an on-demand price per GPU-hour ("$4.50"), in USD. Rows sold only on request
("Contact us") have no price and are skipped. Prices are the same in every Nebius
region, so they are recorded as one catalogue price.

The parser reads the visible text, not the page layout: a row is recognised by
the GPU name followed by its numbers and dollar amounts. If no row is found the
run reports no prices, and nothing is guessed.
"""

from __future__ import annotations

import html
import re

import requests

from ..http import TIMEOUT
from ..util import dec
from .base import Fetched, Offer

URL = "https://nebius.com/prices"

ROW = re.compile(
    r"(?P<name>NVIDIA (?:HGX |GB)?[A-Z0-9]+(?: [A-Z0-9]+)*?(?: with (?:Intel|AMD) CPU)?)\s+"
    r"(?P<vcpu>\d+(?:-\d+)?)\s+(?P<ram>\d+(?:-\d+)?)\s+"
    r"(?:from \$(?P<pre>[\d.]+)\**|-)\s+"
    r"(?:from )?\$(?P<od>[\d.]+)"
)
TAGS = re.compile(r"<[^>]+>")
SCRIPTS = re.compile(r"<script.*?</script>|<style.*?</style>", re.S)


def visible_text(page: str) -> str:
    return " ".join(html.unescape(TAGS.sub(" ", SCRIPTS.sub(" ", page))).split())


def extract_rows(page: str) -> list[dict]:
    """One record per priced GPU row, verbatim amounts. Duplicate rows are kept once."""
    rows: dict[str, dict] = {}
    for m in ROW.finditer(visible_text(page)):
        rows.setdefault(
            m.group("name"),
            {"name": m.group("name"), "on_demand": m.group("od"), "preemptible": m.group("pre")},
        )
    return list(rows.values())


class Nebius:
    provider = "nebius"
    version = 1
    method = "html"

    def fetch(self, http: requests.Session) -> Fetched:
        r = http.get(URL, timeout=TIMEOUT)
        r.raise_for_status()
        return Fetched(source_url=URL, records=extract_rows(r.text))

    def parse(self, fetched: Fetched) -> list[Offer]:
        offers = []
        for rec in fetched.records:
            for model, value in (("on_demand", rec["on_demand"]), ("spot", rec.get("preemptible"))):
                if not value:
                    continue
                offers.append(
                    Offer(
                        sku=rec["name"],
                        gpu_raw=rec["name"],
                        gpu_count=1,  # Nebius lists prices per GPU-hour
                        price=dec(value),
                        currency="USD",
                        unit="hour",
                        pricing_model=model,
                        region="catalogue",
                    )
                )
        return offers
