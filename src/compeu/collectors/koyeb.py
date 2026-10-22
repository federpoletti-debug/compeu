"""Koyeb: GPU instance prices from its public catalogue API.

GET https://app.koyeb.com/v1/catalog/instances?limit=200 (no authentication)
Each instance type has an hourly price in USD, a GPU block (count, name) and the
regions it can run in. Region codes are cities (fra = Frankfurt, par = Paris) or
groups (eu, na). Koyeb is French (owned by Mistral AI since February 2026), but most
of its GPUs run in North America: each offer keeps its region and country, so the
index counts only the ones located in Europe. Instances with no region (restricted)
are not offered to the public and are skipped.
"""

from __future__ import annotations

import requests

from ..http import TIMEOUT
from ..util import dec
from .base import Fetched, Offer

URL = "https://app.koyeb.com/v1/catalog/instances?limit=200"

# Region code -> country. Group codes are used only when no city code is listed.
COUNTRY = {
    "fra": "DE",
    "par": "FR",
    "eu": "DE",  # the "eu" group is Frankfurt, Falkenstein and Paris
    "was": "US",
    "sfo": "US",
    "dal": "US",
    "rdu": "US",
    "dsm": "US",
    "mci": "US",
    "na": "US",
    "sin": "SG",
    "tyo": "JP",
    "ap": "SG",
}
GROUPS = {"eu", "na", "ap"}


class Koyeb:
    provider = "koyeb"
    version = 1
    method = "api"

    def fetch(self, http: requests.Session) -> Fetched:
        r = http.get(URL, timeout=TIMEOUT)
        r.raise_for_status()
        body = r.json()
        rows = [i for i in body.get("instances", []) if i.get("type") == "gpu" and i.get("gpu")]
        return Fetched(source_url=URL, records=rows)

    def parse(self, fetched: Fetched) -> list[Offer]:
        offers = []
        for rec in fetched.records:
            gpu = rec["gpu"]
            regions = rec.get("regions") or []
            if not regions:
                fetched.problems.append(f"{rec['id']}: no public region (restricted)")
                continue
            if gpu.get("brand") != "nvidia" and "nvidia" not in rec["id"]:
                continue  # non-NVIDIA accelerators are not in the GPU registry
            count = int(gpu.get("count") or 0)
            if count <= 0:
                fetched.problems.append(f"{rec['id']}: no GPU count")
                continue
            cities = [r for r in regions if r not in GROUPS]
            for region in cities or regions:
                country = COUNTRY.get(region)
                if country is None:
                    fetched.problems.append(f"{rec['id']}: unknown region {region}")
                    continue
                offers.append(
                    Offer(
                        sku=rec["id"],
                        gpu_raw=rec.get("description") or rec["id"],
                        gpu_count=count,
                        price=dec(rec["price_hourly"]),
                        currency="USD",
                        unit="hour",
                        region=region,
                        country=country,
                        extra={"vcpu": rec.get("vcpu"), "memory": rec.get("memory")},
                    )
                )
        return offers
