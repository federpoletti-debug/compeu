"""CloudFerro: GPU virtual machine prices from the public pricing tables.

GET https://cloudferro.com/pricing/pricing-tables/<cloud>/virtual-machines-vm-with-gpu/
One page per cloud: WAW3-1, WAW3-2 and WAW4-1 in Warsaw, LCJ1-1 in Łódź. A page holds
HTML tables, each under a heading ("Virtual Machines with GPU in Passthrough mode",
"Virtual Machines with shared GPU", "Spot GPU Virtual Machines"). The first row of a
table names its columns ("VM Name", "#vCores", "RAM (GB)", "Virtual", "vGPU RAM", ...,
"Price 1H", or "Available VM" ... "per hour" on older pages); the order changes between
pages, so it is read from that row. Prices
are in euro excluding VAT; "Price 1H" is the pay-per-use price per hour, written with
a decimal comma.

Only whole GPUs count. A flavour is kept when
- it is a passthrough flavour (its table is headed "Passthrough", or its "Virtual"
  column says "no") and its name gives the model and the number of GPUs: h100.2 is
  two H100, gpu.h200x4 four H200, gpu.h200 one; or
- its "Virtual" column gives the full card ("full L40S", "FULL RTX 6000 PRO"): one GPU.
Fractions of a card (1/2, 1/4, 1/8) are skipped. Flavours named "spot." are spot
prices.

The Frankfurt table (FRA1-3) lists gpu.a100 without saying whether the VM gets a
whole card, so Frankfurt is not read until CloudFerro confirms it.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

import requests

from ..http import TIMEOUT
from ..util import dec
from .base import Fetched, Offer

INDEX_URL = "https://cloudferro.com/pricing/pricing-tables/"
PAGE = "https://cloudferro.com/pricing/pricing-tables/{slug}/virtual-machines-vm-with-gpu/"

# cloud id -> (page slug, country of its data centre)
CLOUDS = {
    "waw3-1": ("waw3-1-cloud", "PL"),
    "waw3-2": ("waw3-2-cloud", "PL"),
    "waw4-1": ("waw4-1-cloud", "PL"),
    "lcj1-1": ("lcj1-1", "PL"),
}

MODELS = {
    "h100": "NVIDIA H100",
    "h200": "NVIDIA H200",
    "b200": "NVIDIA B200",
    "a100": "NVIDIA A100",
    "l40s": "NVIDIA L40S",
}
# h100.1, h100.4, gpu.h100*, gpu.h100x2*, gpu.h200, gpu.h200x4, gpu.h200.x8, gpu.l40sx2
PASSTHROUGH = re.compile(r"^(?:gpu\.)?(?P<model>[a-z]\d{2,3}s?)(?:(?:\.x?|x)(?P<n>\d+))?\*?$")
FULL_CARD = re.compile(r"^full\s+(?P<model>.+)$", re.I)
AMOUNT = re.compile(r"^\d+(?:\.\d+)?$")
NAME_HEADERS = ("vm name", "vn name", "available vm")


class _Tables(HTMLParser):
    """The tables of a page as lists of cell texts, each with the heading above it."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[dict] = []
        self._heading = ""
        self._h: list[str] | None = None
        self._table: dict | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag in ("h1", "h2", "h3", "h4") and self._table is None:
            self._h = []
        elif tag == "table":
            self._table = {"heading": self._heading, "rows": []}
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []
        elif tag == "br" and self._cell is not None:
            self._cell.append(" ")

    def handle_endtag(self, tag):
        if tag in ("h1", "h2", "h3", "h4") and self._h is not None:
            self._heading = " ".join("".join(self._h).split())
            self._h = None
        elif tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            self._table["rows"].append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)
        elif self._h is not None:
            self._h.append(data)


def _column(header: list[str], test) -> int | None:
    for i, name in enumerate(header):
        if test(name.lower()):
            return i
    return None


def extract_rows(page: str, cloud: str) -> list[dict]:
    """One record per flavour row of every GPU table, cells as printed."""
    parser = _Tables()
    parser.feed(page)
    rows = []
    for table in parser.tables:
        head_at = next(
            (i for i, r in enumerate(table["rows"]) if r and r[0].lower() in NAME_HEADERS),
            None,
        )
        if head_at is None:
            continue
        header = table["rows"][head_at]
        price = _column(header, lambda n: n in ("price 1h", "per hour"))
        virtual = _column(header, lambda n: n.startswith("virtual"))
        vram = _column(header, lambda n: "vgpu ram" in n)
        if price is None:
            continue
        for r in table["rows"][head_at + 1 :]:
            if len(r) != len(header) or not r[0]:
                continue
            rows.append(
                {
                    "cloud": cloud,
                    "heading": table["heading"],
                    "name": r[0],
                    "virtual": r[virtual] if virtual is not None else "",
                    "vram_gb": r[vram] if vram is not None else "",
                    "price": r[price],
                }
            )
    return rows


def _amount(text: str):
    s = text.replace("\xa0", "").replace(" ", "")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    return dec(s) if AMOUNT.match(s) else None


def _gpus(rec: dict) -> tuple[str, int] | None:
    """(raw GPU name, number of GPUs) for a whole-GPU flavour, None for anything else."""
    name = rec["name"].lower().removeprefix("spot.")
    full = FULL_CARD.match(rec["virtual"])
    if full:
        return f"NVIDIA {full.group('model')}", 1
    passthrough = "passthrough" in rec["heading"].lower() or rec["virtual"].lower() == "no"
    m = PASSTHROUGH.match(name)
    if passthrough and m and m.group("model") in MODELS:
        return MODELS[m.group("model")], int(m.group("n") or 1)
    return None


class CloudFerro:
    provider = "cloudferro"
    version = 1
    method = "html"

    def fetch(self, http: requests.Session) -> Fetched:
        rows, problems, errors = [], [], []
        for cloud, (slug, _) in CLOUDS.items():
            url = PAGE.format(slug=slug)
            try:
                r = http.get(url, timeout=TIMEOUT)
                r.raise_for_status()
            except requests.RequestException as e:
                errors.append(e)
                problems.append(f"{cloud}: {type(e).__name__}: {e}")
                continue
            found = extract_rows(r.content.decode("utf-8", errors="replace"), cloud)
            if not found:
                problems.append(f"{cloud}: no GPU price table found")
            rows += found
        if not rows and errors:
            raise errors[0]
        return Fetched(source_url=INDEX_URL, records=rows, problems=problems)

    def parse(self, fetched: Fetched) -> list[Offer]:
        offers = []
        for rec in fetched.records:
            gpus = _gpus(rec)
            if gpus is None:
                continue  # a fraction of a card, or a flavour that does not say
            price = _amount(rec["price"])
            if price is None or price <= 0:
                where = f"{rec['cloud']} {rec['name']}"
                fetched.problems.append(f"{where}: price {rec['price']!r} not read")
                continue
            gpu_raw, count = gpus
            vram = _amount(rec["vram_gb"]) if rec["vram_gb"] else None  # all the VM's GPUs
            spot = rec["name"].lower().startswith("spot.")
            offers.append(
                Offer(
                    sku=rec["name"],
                    gpu_raw=gpu_raw,
                    gpu_count=count,
                    price=price,
                    currency="EUR",
                    unit="hour",
                    pricing_model="spot" if spot else "on_demand",
                    region=rec["cloud"],
                    country=CLOUDS[rec["cloud"]][1],
                    extra={"gpu_memory_gb": str(vram / count)} if vram is not None else {},
                )
            )
        return offers
