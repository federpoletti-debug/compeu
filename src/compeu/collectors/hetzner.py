"""Hetzner: GPU dedicated servers (GEX line).

Hetzner GPU servers are dedicated machines sold through Robot, not Hetzner Cloud,
so the Cloud API (/v1/pricing) has no GPU prices. Two public sources are joined:

1. The GPU product page names each server (GEX45, GEX131...), its GPU, and the
   Robot product ids that make up its price (attribute product-key, for example
   "ROBOT_1747+ROBOT_1266": the server plus its primary IPv4 address).
2. The price file the page itself loads, live_data_prices.json, gives every
   product id's hourly, monthly and setup price per data centre, in EUR and USD.

Version 1 read the euro amounts printed on the page. On 21 Oct 2026 Hetzner
redesigned the page and the run reported no prices (as it should). The page also
prints dollars to US visitors such as GitHub's servers. Version 2 takes names and
GPUs from the stable parts of the page and the euro column of the price file,
whatever the layout or the visitor's country.

A card whose product ids are missing from the price file is reported as a
problem and recorded with no price. Billing: hourly with a monthly cap, plus a
one-time setup fee (both kept in `extra`).
"""

from __future__ import annotations

import html
import re
from decimal import Decimal

import requests

from ..http import TIMEOUT
from ..util import dec
from .base import Fetched, Offer

URL = "https://www.hetzner.com/dedicated-rootserver/matrix-gpu/"
PRICES_URL = "https://www.hetzner.com/_resources/app/data/app/live_data_prices.json"

# The page layout changes (it did on 21 Oct 2026), so cards are found through the
# parts that carry meaning rather than through styling classes: the order button
# that closes each card, the product ids on its price elements, and the spec line
# that names the GPU ("4x NVIDIA RTX PRO 6000 ...").
ORDER = re.compile(r'data-event-action="Order ([A-Z]+\d+[A-Z]*)"')
KEY = re.compile(r'product-key="([A-Z0-9_]+(?:\+[A-Z0-9_]+)*)"')
PARAGRAPH = re.compile(r"<p\b[^>]*>(.*?)</p>", re.S)
GPU_LINE = re.compile(r"^(?:(\d+)\s*x\s+)?((?:NVIDIA|AMD)\b.*)$", re.I)
TAG = re.compile(r"<[^>]+>")
# Hetzner data centre codes -> registry site ids (registry/providers.yaml).
DATACENTRES = {"FSN1": "fsn", "NBG1": "nbg", "HEL1": "hel"}
SHARED = "ALL"  # add-ons such as the IPv4 address are priced once for every location
CURRENCY = "EUR"


def extract_cards(page: str) -> list[dict]:
    """Name, GPU, GPU count and product ids of every server card on the product page.

    Each card ends with its order button; the card's text is everything between the
    previous order button and this one. The GPU line is searched only after the
    card's first price element, so text above the cards cannot be mistaken for a spec.
    """
    cards: dict[str, dict] = {}
    start = 0
    for order in ORDER.finditer(page):
        chunk, start, name = page[start : order.start()], order.end(), order.group(1)
        key = KEY.search(chunk)
        gpu, count = None, None
        if key:
            for para in PARAGRAPH.findall(chunk[key.start() :]):
                text = " ".join(html.unescape(TAG.sub(" ", para)).split())
                line = GPU_LINE.match(text)
                if line:
                    count, gpu = int(line.group(1) or 1), line.group(2).strip()
                    break
        cards.setdefault(
            name,
            {
                "name": name,
                "gpu": gpu,
                "gpu_count": count,
                "components": key.group(1).split("+") if key else [],
            },
        )
    return list(cards.values())


class Hetzner:
    provider = "hetzner"
    version = 2
    method = "api"

    def fetch(self, http: requests.Session) -> Fetched:
        page = http.get(URL, timeout=TIMEOUT)
        page.raise_for_status()
        cards = extract_cards(page.text)
        prices = http.get(PRICES_URL, timeout=TIMEOUT)
        prices.raise_for_status()
        products = prices.json().get("products", {})
        wanted = {c for card in cards for c in card["components"]}
        used = {k: products[k] for k in sorted(wanted) if k in products}
        return Fetched(source_url=PRICES_URL, records=[{"cards": cards, "products": used}])

    def parse(self, fetched: Fetched) -> list[Offer]:
        offers = []
        for rec in fetched.records:
            products = rec["products"]
            for card in rec["cards"]:
                name, gpu, parts = card.get("name"), card.get("gpu"), card.get("components") or []
                count = card.get("gpu_count")
                if not (name and gpu and count and parts):
                    fetched.problems.append(f"{name or '?'}: missing GPU, GPU count or product ids")
                    continue
                missing = [p for p in parts if p not in products]
                if missing:
                    fetched.problems.append(f"{name}: {', '.join(missing)} not in the price file")
                    continue
                for dc, site in DATACENTRES.items():
                    total = _price_at(products, parts, dc)
                    if total is None:
                        continue  # not sold in this data centre
                    offers.append(
                        Offer(
                            sku=name,
                            gpu_raw=gpu,
                            gpu_count=count,
                            price=total["hourly"],
                            currency=CURRENCY,
                            unit="hour",
                            region=site,
                            extra={
                                "monthly_cap_eur": total.get("monthly"),
                                "setup_fee_eur": total.get("setup"),
                                "datacentre": dc,
                            },
                        )
                    )
        return offers


def _price_at(products: dict, parts: list[str], datacentre: str) -> dict | None:
    """Sum the EUR prices of a server's components at one data centre.

    Returns None when the server itself is not offered there (no location entry,
    or an inactive one). Shared add-ons ("ALL") count everywhere.
    """
    total: dict[str, Decimal] = {}
    for part in parts:
        locations = products[part].get("locations") or []
        here = [loc for loc in locations if loc.get("datacenter") in (datacentre, SHARED)]
        if not here or not here[0].get("active", True):
            return None
        for kind, amounts in (here[0].get("prices") or {}).items():
            if kind in ("hourly", "monthly", "setup") and amounts.get(CURRENCY) is not None:
                total[kind] = total.get(kind, Decimal(0)) + dec(amounts[CURRENCY])
    return total if "hourly" in total else None
