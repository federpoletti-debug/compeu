"""UpCloud: GPU server plans from the public price page.

GET https://upcloud.com/pricing/
Each GPU family has a table of plans: "1 x NVIDIA H100 12 cores 240 GB €1.79/h €2.17/h",
the first amount is the spot price, the second the regular (on-demand) price, in euro
per server-hour, excluding taxes. The page shows euro by default.

UpCloud lists one price for every zone, and its GPU servers run in Helsinki (fi-hel2,
per the GPU availability page), so the plans are recorded as one catalogue price.
"""

from __future__ import annotations

import re

import requests

from ..http import TIMEOUT
from ..util import dec
from .base import Fetched, Offer
from .nebius import visible_text

URL = "https://upcloud.com/pricing/"

ROW = re.compile(
    r"(?P<n>\d+) x (?P<gpu>NVIDIA [A-Z0-9][A-Za-z0-9 ]*?) (?P<cores>\d+) cores (?P<ram>\d+) GB "
    r"€(?P<spot>[\d.,]+)/h €(?P<price>[\d.,]+)/h"
)


def extract_rows(page: str) -> list[dict]:
    """One record per GPU plan, with the amounts as printed."""
    rows = {}
    for m in ROW.finditer(visible_text(page)):
        key = (m.group("n"), m.group("gpu"), m.group("cores"), m.group("ram"))
        rows.setdefault(
            key,
            {
                "gpus": int(m.group("n")),
                "gpu": m.group("gpu"),
                "cores": int(m.group("cores")),
                "ram_gb": int(m.group("ram")),
                "spot": m.group("spot"),
                "price": m.group("price"),
            },
        )
    return list(rows.values())


def _eur(amount: str):
    return dec(amount.replace(",", ""))


class UpCloud:
    provider = "upcloud"
    version = 1
    method = "html"

    def fetch(self, http: requests.Session) -> Fetched:
        r = http.get(URL, timeout=TIMEOUT)
        r.raise_for_status()
        rows = extract_rows(r.content.decode("utf-8", errors="replace"))  # euro signs
        problems = [] if rows else ["no GPU plan found on the price page"]
        return Fetched(source_url=URL, records=rows, problems=problems)

    def parse(self, fetched: Fetched) -> list[Offer]:
        offers = []
        for rec in fetched.records:
            sku = f"{rec['gpus']}x {rec['gpu']} {rec['cores']}c {rec['ram_gb']}GB"
            for model, amount in (("on_demand", rec["price"]), ("spot", rec["spot"])):
                offers.append(
                    Offer(
                        sku=sku,
                        gpu_raw=rec["gpu"],
                        gpu_count=rec["gpus"],
                        price=_eur(amount),
                        currency="EUR",
                        unit="hour",
                        pricing_model=model,
                        region="catalogue",
                        extra={"vcpu": rec["cores"], "ram_gb": rec["ram_gb"]},
                    )
                )
        return offers
