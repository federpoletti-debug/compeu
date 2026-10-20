"""RunPod: public GraphQL API, gpuTypes query (no authentication).

POST https://api.runpod.io/graphql
RunPod is a global marketplace: prices are per GPU-hour in USD and not tied to a
location, so offers are recorded with region "global" and never enter a European
basket. Shown on the site as a global reference.
"""

from __future__ import annotations

import requests

from ..http import TIMEOUT
from ..util import dec
from .base import Fetched, Offer

URL = "https://api.runpod.io/graphql"
QUERY = """
query GpuTypes {
  gpuTypes {
    id displayName memoryInGb
    securePrice communityPrice secureSpotPrice communitySpotPrice
  }
}
"""
# RunPod returns exactly 0.50 for some GPU types whose other price is several times higher
# (e.g. MI300X: secure 2.39, community 0.50), which looks like a default value rather than a
# real listing. Such prices are recorded with a flag and kept out of comparisons.
PLACEHOLDER = 0.5
FIELDS = {
    "securePrice": ("secure", "on_demand"),
    "communityPrice": ("community", "on_demand"),
    "secureSpotPrice": ("secure", "spot"),
    "communitySpotPrice": ("community", "spot"),
}


class RunPod:
    provider = "runpod"
    version = 1
    method = "api"

    def fetch(self, http: requests.Session) -> Fetched:
        r = http.post(URL, json={"query": QUERY}, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        if data.get("errors"):
            raise RuntimeError(f"GraphQL errors: {data['errors']}")
        return Fetched(source_url=URL, records=data["data"]["gpuTypes"])

    def parse(self, fetched: Fetched) -> list[Offer]:
        offers = []
        for g in fetched.records:
            if "MIG" in g["id"]:
                fetched.problems.append(f"{g['id']}: a MIG slice, not a whole GPU, skipped")
                continue
            for field, (cloud, model) in FIELDS.items():
                value = g.get(field)
                if not value:  # null or 0 means "not offered", never a free GPU
                    continue
                offers.append(
                    Offer(
                        sku=f"{g['id']} ({cloud})",
                        gpu_raw=g["id"],
                        gpu_count=1,
                        price=dec(value),
                        currency="USD",
                        unit="hour",
                        pricing_model=model,
                        region="global",
                        extra={
                            "cloud": cloud,
                            "gpu_memory_gb": g.get("memoryInGb"),
                            "flag": _placeholder_flag(g, field),
                        },
                    )
                )
        return offers


def _placeholder_flag(g: dict, field: str) -> str | None:
    """Flag a price of exactly 0.50 when the same GPU's other price is at least twice as high."""
    if g.get(field) != PLACEHOLDER:
        return None
    other = g.get("securePrice") if field.startswith("community") else g.get("communityPrice")
    if other and other >= 2 * PLACEHOLDER:
        return "suspect_placeholder"
    return None
