"""IONOS: Cloud GPU VM prices from the public product page.

GET https://cloud.ionos.de/cloud-gpu-vm
The German page lists the GPU VM types with their hourly pay-as-you-go price in euro:
"H200 – S  H200 PCIe  1  15  267 GiB  1.024 GB  3 €" (type, GPU, number of GPUs,
dedicated vCPUs, RAM, storage, price per hour). Amounts use German number format.
IONOS hosts these VMs in Germany only, so the prices are recorded as one catalogue
price.
"""

from __future__ import annotations

import re

import requests

from ..http import TIMEOUT
from ..util import dec
from .base import Fetched, Offer
from .nebius import visible_text

URL = "https://cloud.ionos.de/cloud-gpu-vm"

ROW = re.compile(
    r"(?P<type>[A-Z]\d{3,4} [–-] [A-Z]{1,3}) (?P<gpu>[A-Z]\d{3,4}[A-Za-z ]*?) (?P<n>\d+) "
    r"(?P<vcpu>\d+) [\d.,]+ GiB [\d.,]+ (?:GB|TB) (?P<price>\d[\d.]*(?:,\d+)?) €"
)


def extract_rows(page: str) -> list[dict]:
    """One record per GPU VM type, with the price as printed."""
    rows = {}
    for m in ROW.finditer(visible_text(page)):
        rows.setdefault(
            m.group("type"),
            {
                "type": m.group("type"),
                "gpu": m.group("gpu").strip(),
                "gpus": int(m.group("n")),
                "vcpu": int(m.group("vcpu")),
                "price": m.group("price"),
            },
        )
    return list(rows.values())


def _german(amount: str):
    return dec(amount.replace(".", "").replace(",", "."))


class Ionos:
    provider = "ionos"
    version = 1
    method = "html"

    def fetch(self, http: requests.Session) -> Fetched:
        r = http.get(URL, timeout=TIMEOUT, headers={"Accept-Language": "de"})
        r.raise_for_status()
        rows = extract_rows(r.content.decode("utf-8", errors="replace"))  # euro signs, dashes
        problems = [] if rows else ["no GPU VM type found on the product page"]
        return Fetched(source_url=URL, records=rows, problems=problems)

    def parse(self, fetched: Fetched) -> list[Offer]:
        return [
            Offer(
                sku=rec["type"],
                gpu_raw=rec["gpu"],
                gpu_count=rec["gpus"],
                price=_german(rec["price"]),
                currency="EUR",
                unit="hour",
                region="catalogue",
                extra={"vcpu": rec["vcpu"]},
            )
            for rec in fetched.records
        ]
