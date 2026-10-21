"""AWS: official Price List bulk API (no authentication).

Docs: https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/using-the-aws-price-list-bulk-api.html
1. GET .../offers/v1.0/aws/AmazonEC2/current/region_index.json -> current version per region
2. GET .../offers/v1.0/aws/AmazonEC2/<version>/<region>/index.csv (about 180 MB each)

A region file is downloaded only when AWS publishes a new version; otherwise the
GPU rows extracted from the same version last time are reused (stored in
state/aws/). The run log records the version id, so every price can be traced
back to the exact AWS publication.
"""

from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path

import requests

from .. import registry
from ..http import TIMEOUT
from ..util import dec, root
from .base import Fetched, Offer

BASE = "https://pricing.us-east-1.amazonaws.com"
INDEX_URL = f"{BASE}/offers/v1.0/aws/AmazonEC2/current/region_index.json"
# Regions served by a different price-list partition (European Sovereign Cloud).
OTHER_PARTITION = {"eusc-de-east-1"}

# Instance family -> GPU name. GPU count comes from AWS's own "GPU" column.
FAMILY_GPU = {
    "p4d": "A100 40GB SXM",
    "p4de": "A100 80GB SXM",
    "p5": "H100 SXM",
    "p5e": "H200 SXM",
    "p5en": "H200 SXM",
    "p6-b200": "B200",
    "p6-b300": "B300",
    "p6e-gb200": "GB200",
    "g6e": "L40S",
    "g6": "L4",
    "g5": "A10G",
    "g4dn": "T4",
    "p3": "V100 SXM",
    "p3dn": "V100 SXM",
}
KEEP_COLUMNS = (
    "SKU",
    "Instance Type",
    "PricePerUnit",
    "Currency",
    "Unit",
    "GPU",
    "GPU Memory",
    "Location",
    "Region Code",
    "TermType",
    "MarketOption",
    "Tenancy",
    "Operating System",
    "Pre Installed S/W",
    "CapacityStatus",
    "License Model",
)


def _family(instance_type: str) -> str:
    return instance_type.split(".")[0]


def _is_gpu_family(instance_type: str) -> bool:
    return _family(instance_type)[:1] in ("p", "g") and not _family(instance_type).endswith("g")


def _keep(row: dict) -> bool:
    return (
        row["TermType"] == "OnDemand"
        and row["MarketOption"] == "OnDemand"
        and row["Tenancy"] == "Shared"
        and row["Operating System"] == "Linux"
        and row["Pre Installed S/W"] == "NA"
        and row["CapacityStatus"] == "Used"
        and row["License Model"] == "No License required"
        and row["Unit"] == "Hrs"
        and row["GPU"] not in ("", "0", "NA")
        and _is_gpu_family(row["Instance Type"])
        and dec(row["PricePerUnit"]) > 0
    )


def extract_gpu_rows(csv_path: Path) -> list[dict]:
    """Stream one region offer file and keep the on-demand Linux GPU rows."""
    rows = []
    with csv_path.open(encoding="utf-8", newline="") as f:
        for _ in range(5):  # metadata lines before the header
            f.readline()
        for row in csv.DictReader(f):
            if _keep(row):
                rows.append({k: row[k] for k in KEEP_COLUMNS})
    return rows


class AWS:
    provider = "aws"
    version = 1
    method = "api"

    def __init__(self, state_dir: Path | None = None):
        self.state_dir = state_dir or root() / "state" / "aws"

    def regions(self) -> list[str]:
        sites = registry.providers()["aws"]["sites"]
        return [s["id"] for s in sites if s["id"] not in OTHER_PARTITION]

    def fetch(self, http: requests.Session) -> Fetched:
        r = http.get(INDEX_URL, timeout=TIMEOUT)
        r.raise_for_status()
        index = r.json()["regions"]
        records, versions, problems = [], {}, []
        self.state_dir.mkdir(parents=True, exist_ok=True)
        for region in self.regions():
            if region not in index:
                problems.append(f"{region}: not in the AWS region index")
                continue
            version_url = index[region]["currentVersionUrl"]
            version = version_url.split("/")[-3]
            versions[region] = version
            cache = self.state_dir / f"{region}.json"
            cached = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else None
            if cached and cached["version"] == version:
                rows = cached["rows"]
            else:
                rows = self._download(http, version_url.replace("index.json", "index.csv"))
                cache.write_text(
                    json.dumps({"version": version, "rows": rows}, indent=0),
                    encoding="utf-8",
                    newline="\n",
                )
            records += rows
        return Fetched(
            source_url=INDEX_URL,
            records=records,
            source_version=json.dumps(versions, sort_keys=True),
            problems=problems,
        )

    def _download(self, http: requests.Session, path: str) -> list[dict]:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "offer.csv"
            with http.get(BASE + path, stream=True, timeout=TIMEOUT) as r:
                r.raise_for_status()
                with target.open("wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
            return extract_gpu_rows(target)

    def parse(self, fetched: Fetched) -> list[Offer]:
        offers, unmapped = [], set()
        for row in fetched.records:
            itype = row["Instance Type"]
            gpu = FAMILY_GPU.get(_family(itype))
            if gpu is None:
                unmapped.add(_family(itype))
                continue
            region = row["Region Code"]
            offers.append(
                Offer(
                    sku=itype,
                    gpu_raw=gpu,
                    gpu_count=int(row["GPU"]),
                    price=dec(row["PricePerUnit"]),
                    currency=row["Currency"],
                    unit="hour",
                    region=region,
                    country=registry.site_country("aws", region),
                    extra={"gpu_memory": row["GPU Memory"]},
                )
            )
        fetched.problems += [f"{f}: instance family not in the GPU table" for f in sorted(unmapped)]
        return offers
