"""evroc: the on-demand price of its GPU virtual machines, from the public GPU page.

GET https://evroc.com/campaigns/gpu-vm/
The page gives one on-demand price per GPU-hour in euro, "On-demand GPU VM From €8 /
hour / GPU", next to a lower price for a 36-month reservation that the index does not
use. "From" is the cheapest on-demand price, which is the one quote the index takes
per provider. The GPU model is read from the page title ("NVIDIA B200 GPU VMs"): the
body also names the H100, but only to compare with it. The page says that no data
leaves the EU, but not which data centre runs the VMs, so the price is recorded as one
catalogue price.
"""

from __future__ import annotations

import re

import requests

from ..http import TIMEOUT
from ..util import dec
from .base import Fetched, Offer
from .nebius import visible_text

URL = "https://evroc.com/campaigns/gpu-vm/"

ON_DEMAND = re.compile(r"On-demand GPU VM From €\s?(?P<price>\d+(?:[.,]\d+)?) / hour / GPU", re.I)
TITLE = re.compile(r"<title[^>]*>\s*NVIDIA (?P<model>[A-Z]{1,2}\d{2,3}[A-Z]?) GPU VMs?\b", re.I)


def extract_rows(page: str) -> tuple[list[dict], list[str]]:
    """The on-demand price per GPU-hour and the GPU it is for, or the reason it is missing."""
    prices = {m.group("price") for m in ON_DEMAND.finditer(visible_text(page))}
    title = TITLE.search(page)
    if len(prices) != 1:
        return [], [f"expected one on-demand price per GPU-hour, found {sorted(prices)}"]
    if not title:
        return [], ["GPU model not found in the page title"]
    return [{"gpu": f"NVIDIA {title.group('model').upper()}", "price": prices.pop()}], []


class Evroc:
    provider = "evroc"
    version = 1
    method = "html"

    def fetch(self, http: requests.Session) -> Fetched:
        r = http.get(URL, timeout=TIMEOUT)
        r.raise_for_status()
        rows, problems = extract_rows(r.content.decode("utf-8", errors="replace"))  # euro signs
        return Fetched(source_url=URL, records=rows, problems=problems)

    def parse(self, fetched: Fetched) -> list[Offer]:
        return [
            Offer(
                sku="gpu-vm-on-demand",
                gpu_raw=rec["gpu"],
                gpu_count=1,  # the price is per GPU
                price=dec(rec["price"].replace(",", ".")),
                currency="EUR",
                unit="hour",
                region="catalogue",
            )
            for rec in fetched.records
        ]
