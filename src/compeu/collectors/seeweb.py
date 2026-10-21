"""Seeweb: GPU cloud servers, from the public product page and its price list.

The product page https://www.seeweb.it/en/products/cloud-server-gpu shows one card
per GPU (id "gpu<N>", with the GPU name). The page's script computes each card's
price as a per-GPU hourly rate times the number of GPUs chosen; the rates sit in a
price list inside that script, as "CLOUDGPU<N>H": <euro per GPU-hour>. This
collector joins the two by <N>. Prices are in euro, excluding VAT; Seeweb's data
centres are in Italy (Frosinone and Milan), so they count as one catalogue price.

Spot instances (the script charges 40% of the hourly rate) are not recorded: they
are derived by a formula, not listed.
"""

from __future__ import annotations

import html
import re

import requests

from ..http import TIMEOUT
from ..util import dec
from .base import Fetched, Offer

URL = "https://www.seeweb.it/en/products/cloud-server-gpu"
BASE = "https://www.seeweb.it"

CARD = re.compile(r'id="gpu(?P<n>\d+)"[^>]*>.*?class="cardname">(?P<name>[^<]+)<', re.S)
SCRIPT = re.compile(r'<script[^>]+src="(?P<src>/assets/bundle\.js[^"]*)"')
RATE = re.compile(r'"CLOUDGPU(?P<n>\d+)H":(?P<rate>[\d.]+)')


def extract(page: str, bundle: str) -> list[dict]:
    """GPU name and per-GPU hourly rate for every card that has a rate."""
    names = {m.group("n"): html.unescape(m.group("name")).strip() for m in CARD.finditer(page)}
    rates = {m.group("n"): m.group("rate") for m in RATE.finditer(bundle)}
    return [
        {"card": f"gpu{n}", "name": names[n], "rate_eur": rates.get(n)}
        for n in sorted(names, key=int)
    ]


class Seeweb:
    provider = "seeweb"
    version = 1
    method = "html"

    def fetch(self, http: requests.Session) -> Fetched:
        page = http.get(URL, timeout=TIMEOUT)
        page.raise_for_status()
        script = SCRIPT.search(page.text)
        if not script:
            return Fetched(source_url=URL, records=[], problems=["price script not found"])
        bundle = http.get(BASE + html.unescape(script.group("src")), timeout=TIMEOUT)
        bundle.raise_for_status()
        return Fetched(source_url=URL, records=extract(page.text, bundle.text))

    def parse(self, fetched: Fetched) -> list[Offer]:
        offers = []
        for rec in fetched.records:
            if not rec.get("rate_eur"):
                fetched.problems.append(f"{rec['card']} ({rec['name']}): no rate in the price list")
                continue
            offers.append(
                Offer(
                    sku=rec["card"],
                    gpu_raw=rec["name"],
                    gpu_count=1,  # the rate is per GPU-hour
                    price=dec(rec["rate_eur"]),
                    currency="EUR",
                    unit="hour",
                    region="catalogue",
                )
            )
        return offers
