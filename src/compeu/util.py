"""Small shared helpers: paths, hashing, canonical JSON, time, decimals."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path
from typing import Any


def root() -> Path:
    """Repository root. Override with COMPEU_ROOT (used by tests)."""
    env = os.environ.get("COMPEU_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2]


def utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def canonical_json(obj: Any) -> str:
    """One stable serialisation, so the same record always hashes the same way."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def dec(value: Any) -> Decimal:
    """Decimal from a provider value. Floats go through str() to avoid binary noise."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(str(value).strip())


def money(value: Decimal, places: int = 6) -> str:
    """Fixed-point string for the ledger (never a float)."""
    q = Decimal(1).scaleb(-places)
    return format(value.quantize(q, rounding=ROUND_HALF_EVEN).normalize(), "f")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
