"""Hetzner: GPU dedicated servers (GEX line) from the public product page.

Hetzner GPU servers are dedicated machines sold through Robot, not Hetzner Cloud,
so the Cloud API (/v1/pricing) has no GPU prices. The product page carries the
prices in structured elements (<ho-price-container price-type="hourly">) with an
accessible text such as "€ 2.4022 per hour, excl. VAT". This collector reads only
those elements and the spec grid; if the markup changes and a field cannot be
found, the product is reported as a problem and no price is recorded.

Billing: hourly with a monthly cap, plus a one-time setup fee (kept in `extra`).
"""

from __future__ import annotations

import html
import re

import requests

from ..http import TIMEOUT
from ..util import dec
from .base import Fetched, Offer

URL = "https://www.hetzner.com/dedicated-rootserver/matrix-gpu/"

CARD_SPLIT = 'class="overflow-hidden product-wrapper gpu-wrapper'
NAME = re.compile(r'product-text-name">\s*([A-Z]+\d+[A-Z]*)\s*<')
HOURLY = re.compile(r'price-type="hourly".*?visually-hidden">\s*€\s*([\d.,]+)\s+per hour', re.S)
MONTHLY = re.compile(r'visually-hidden">\s*€\s*([\d.,]+)\s+per month')
SETUP = re.compile(r"€\s*([\d.,]+)\s+one-time setup fee")
GRID = re.compile(
    r'grid-header-name">\s*([A-Z]+\d+[A-Z]*)\s*<.*?item-d grid-data-text">\s*([^<]+?)\s*<', re.S
)


def _amount(text: str) -> str:
    return text.replace(",", "")  # "1,499.00" -> "1499.00" (page uses English formatting)


class Hetzner:
    provider = "hetzner"
    version = 1
    method = "html"

    def fetch(self, http: requests.Session) -> Fetched:
        r = http.get(URL, timeout=TIMEOUT)
        r.raise_for_status()
        return Fetched(source_url=URL, records=extract(r.text))

    def parse(self, fetched: Fetched) -> list[Offer]:
        offers = []
        for rec in fetched.records:
            missing = [k for k in ("name", "gpu", "hourly_eur") if not rec.get(k)]
            if missing:
                fetched.problems.append(f"{rec.get('name', '?')}: missing {', '.join(missing)}")
                continue
            offers.append(
                Offer(
                    sku=rec["name"],
                    gpu_raw=rec["gpu"],
                    gpu_count=1,
                    price=dec(rec["hourly_eur"]),
                    currency="EUR",
                    unit="hour",
                    region="catalogue",
                    extra={
                        "monthly_cap_eur": rec.get("monthly_eur"),
                        "setup_fee_eur": rec.get("setup_fee_eur"),
                    },
                )
            )
        return offers


def extract(page: str) -> list[dict]:
    """Pull name, GPU and prices for every GEX card. Verbatim strings, no conversion."""
    gpus = {name: html.unescape(gpu).strip() for name, gpu in GRID.findall(page)}
    records = []
    for card in page.split(CARD_SPLIT)[1:]:
        name = NAME.search(card)
        hourly = HOURLY.search(card)
        monthly = MONTHLY.search(card)
        setup = SETUP.search(card)
        n = name.group(1) if name else None
        records.append(
            {
                "name": n,
                "gpu": gpus.get(n) if n else None,
                "hourly_eur": _amount(hourly.group(1)) if hourly else None,
                "monthly_eur": _amount(monthly.group(1)) if monthly else None,
                "setup_fee_eur": _amount(setup.group(1)) if setup else None,
            }
        )
    return records
