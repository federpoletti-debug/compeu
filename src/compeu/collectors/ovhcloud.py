"""OVHcloud: public order catalogue for Public Cloud (no authentication).

GET https://api.ovh.com/1.0/order/catalog/public/cloud?ovhSubsidiary=FR
GPU instance flavours are addons named "<flavour>.consumption" with a
blobs.technical.gpu block. Prices are integers in 1e-8 of the catalogue currency,
per hour, excluding VAT. AI Notebook / Training / Deploy products (planCodes
starting with "ai-" or "quantum-") are managed services, not instances, and are
left out.
"""

from __future__ import annotations

import re
from decimal import Decimal

import requests

from ..http import TIMEOUT
from ..util import sha256_bytes
from .base import Fetched, Offer

URL = "https://api.ovh.com/1.0/order/catalog/public/cloud?ovhSubsidiary=FR"
PRICE_SCALE = Decimal(10**8)
INSTANCE_PLAN = re.compile(r"^[a-z0-9-]+\.consumption$")


class OVHcloud:
    provider = "ovhcloud"
    version = 1
    method = "api"

    def fetch(self, http: requests.Session) -> Fetched:
        r = http.get(URL, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        currency = data["locale"]["currencyCode"]
        records = [
            {"currency": currency, "addon": a} for a in data["addons"] if _is_gpu_instance(a)
        ]
        return Fetched(source_url=URL, records=records, source_sha256=sha256_bytes(r.content))

    def parse(self, fetched: Fetched) -> list[Offer]:
        offers = []
        for rec in fetched.records:
            a = rec["addon"]
            gpu = a["blobs"]["technical"]["gpu"]
            hourly = [p for p in a.get("pricings", []) if p.get("intervalUnit") == "hour"]
            if len(hourly) != 1 or not gpu.get("number") or not gpu.get("model"):
                fetched.problems.append(f"{a['planCode']}: no single hourly price or GPU data")
                continue
            offers.append(
                Offer(
                    sku=a["planCode"].removesuffix(".consumption"),
                    gpu_raw=gpu["model"],
                    gpu_count=int(gpu["number"]),
                    price=Decimal(hourly[0]["price"]) / PRICE_SCALE,
                    currency=rec["currency"],
                    unit="hour",
                    region="catalogue",
                    extra={"gpu_memory_gb": (gpu.get("memory") or {}).get("size")},
                )
            )
        return offers


def _is_gpu_instance(a: dict) -> bool:
    code = a.get("planCode", "")
    if code.startswith(("ai-", "quantum-")) or not INSTANCE_PLAN.match(code):
        return False
    tech = (a.get("blobs") or {}).get("technical") or {}
    return bool(tech.get("gpu"))
