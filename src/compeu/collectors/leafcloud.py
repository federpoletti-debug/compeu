"""Leafcloud: hourly GPU prices from the public price page.

GET https://www.leaf.cloud/pricing
The page compares its GPU prices with other clouds in one table: a header row
("Provider RTX 6000 (96GB) H100 (80GB) A100 (80GB) A30 (24GB) Region") and one row
per cloud. The Leafcloud row gives the hourly price of a full VM with one GPU, in
euro excluding VAT, and its region, ams-1 (Amsterdam). This collector reads the
header to know which GPU each amount belongs to, and takes only the Leafcloud row:
the other rows are Leafcloud's view of its competitors, not their price lists.
"""

from __future__ import annotations

import re

import requests

from ..http import TIMEOUT
from ..util import dec
from .base import Fetched, Offer
from .nebius import visible_text

URL = "https://www.leaf.cloud/pricing"

HEADER = re.compile(r"Provider (?P<cols>(?:[A-Z][A-Z0-9 ]*? \(\d+GB\) )+)Region")
COLUMN = re.compile(r"([A-Z][A-Z0-9 ]*?) \((\d+)GB\)")
LEAF_ROW = re.compile(
    r"Leafcloud [A-Za-z ]*?(?P<cells>(?:(?:€ ?[\d.,]+|Unavailable) )+)(?P<region>[a-z]+-\d+)"
)
CELL = re.compile(r"€ ?([\d.,]+)|Unavailable")


def extract_rows(page: str) -> list[dict]:
    """One record per GPU priced in the Leafcloud row, matched to the header by position."""
    text = visible_text(page)
    head = HEADER.search(text)
    row = LEAF_ROW.search(text)
    if not head or not row:
        return []
    columns = COLUMN.findall(head.group("cols"))
    cells = [m.group(1) for m in CELL.finditer(row.group("cells"))]
    if len(columns) != len(cells):
        return []  # the table changed shape: report nothing rather than misalign
    return [
        {
            "gpu": f"NVIDIA {name.strip()}",
            "memory_gb": int(mem),
            "price": cell,
            "region": row.group("region"),
        }
        for (name, mem), cell in zip(columns, cells, strict=True)
        if cell is not None
    ]


class Leafcloud:
    provider = "leafcloud"
    version = 1
    method = "html"

    def fetch(self, http: requests.Session) -> Fetched:
        r = http.get(URL, timeout=TIMEOUT)
        r.raise_for_status()
        rows = extract_rows(r.content.decode("utf-8", errors="replace"))  # euro signs
        problems = [] if rows else ["Leafcloud row or table header not found"]
        return Fetched(source_url=URL, records=rows, problems=problems)

    def parse(self, fetched: Fetched) -> list[Offer]:
        return [
            Offer(
                sku=f"{rec['gpu']} {rec['memory_gb']}GB",
                gpu_raw=f"{rec['gpu']} {rec['memory_gb']}GB",
                gpu_count=1,  # the table prices a full VM with one GPU
                price=dec(rec["price"].replace(",", "")),
                currency="EUR",
                unit="hour",
                region=rec["region"],
                country="NL",  # ams-1 is Leafcloud's Amsterdam region
                extra={"gpu_memory_gb": rec["memory_gb"]},
            )
            for rec in fetched.records
        ]
