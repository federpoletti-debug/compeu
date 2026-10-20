"""What every collector returns, and the contract it follows.

A collector has two halves:

- ``fetch(session)`` talks to the network and returns a :class:`Fetched` with the
  verbatim records that carry prices (the evidence) and the source URL;
- ``parse(fetched)`` turns those records into :class:`Offer` objects, with no I/O,
  so it can be tested on saved responses.

Collectors never fill in a missing value. If a price, a GPU count or a currency is
missing, the record is skipped and reported in ``Fetched.problems``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol

import requests

UNITS_PER_HOUR = {"hour": Decimal(1), "minute": Decimal(60)}


@dataclass
class Fetched:
    source_url: str
    records: list[Any]  # verbatim provider records that carry the prices
    source_sha256: str | None = None  # hash of the full response, when the records are a subset
    source_version: str | None = None  # provider-side version id, when the source has one
    problems: list[str] = field(default_factory=list)


@dataclass
class Offer:
    sku: str
    gpu_raw: str
    gpu_count: int
    price: Decimal
    currency: str
    unit: str  # "hour" or "minute": price is per instance per unit
    pricing_model: str = "on_demand"  # on_demand | spot | dynamic
    region: str | None = None  # provider region id; "catalogue" for region-less prices
    country: str | None = None
    extra: dict = field(default_factory=dict)

    def per_gpu_hour(self) -> Decimal:
        if self.gpu_count <= 0:
            raise ValueError(f"{self.sku}: gpu_count must be positive")
        return self.price * UNITS_PER_HOUR[self.unit] / self.gpu_count


class Collector(Protocol):
    provider: str
    version: int
    method: str  # api | html

    def fetch(self, http: requests.Session) -> Fetched: ...

    def parse(self, fetched: Fetched) -> list[Offer]: ...
