"""Run the collectors and write what they saw to the ledger.

One run = every collector once. Each offer becomes one observation line; each
run becomes one hash-chained run record that says, per provider, whether the
collection worked, how many offers it read, what went wrong, and where the
verbatim source records are stored. A provider that fails gets a "failed" entry
and no observations: its last good prices stay in the ledger with their old date,
and the index treats them as stale after the methodology's staleness window.
"""

from __future__ import annotations

import os
import subprocess
from datetime import datetime
from decimal import Decimal

import requests

from . import registry
from .collectors import ALL
from .collectors.base import Offer
from .ledger import append_chained, append_lines, observations_file, runs_file, write_snapshot
from .util import iso, money, root, utc_now

MAX_PROBLEMS = 40


def code_version() -> str | None:
    if os.environ.get("GITHUB_SHA"):
        return os.environ["GITHUB_SHA"]
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root(), capture_output=True, text=True, check=True
        )
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def observation(
    run_id: str,
    at: datetime,
    provider: str,
    collector,
    offer: Offer,
    snapshot: str,
    classification: registry.Classification,
) -> dict:
    gpu = registry.normalize_gpu(offer.gpu_raw)
    country = offer.country or registry.site_country(provider, offer.region)
    rec = {
        "run": run_id,
        "observed_at": iso(at),
        "provider": provider,
        "offer": f"{provider}:{offer.sku}:{offer.region or '-'}:{offer.pricing_model}",
        "sku": offer.sku,
        "region": offer.region,
        "country": country,
        "gpu": gpu.model,
        "variant": gpu.variant,
        "gpu_raw": offer.gpu_raw,
        "gpu_count": offer.gpu_count,
        "pricing_model": offer.pricing_model,
        "price": money(offer.price, 8),
        "currency": offer.currency,
        "unit": offer.unit,
        "gpu_hour": money(offer.per_gpu_hour(), 6),
        "tier": 1,
        "method": collector.method,
        "snapshot": snapshot,
        "class": classification.status,
        "rule": classification.rule,
        "collector": f"{provider}/{collector.version}",
    }
    extra = {k: v for k, v in offer.extra.items() if v is not None}
    if extra:
        rec["extra"] = {k: (money(v, 8) if isinstance(v, Decimal) else v) for k, v in extra.items()}
    return rec


def run(http: requests.Session, only: list[str] | None = None, now: datetime | None = None) -> dict:
    started = now or utc_now()
    run_id = started.strftime("%Y%m%dT%H%M%SZ")
    classes = registry.classifications()
    results, observations = [], []
    for name, cls in ALL.items():
        if only and name not in only:
            continue
        collector = cls()
        at = now or utc_now()
        entry: dict = {"provider": name, "method": collector.method}
        fetched = None
        try:
            fetched = collector.fetch(http)
            entry["source"] = fetched.source_url
            offers = collector.parse(fetched)
            if not offers:
                raise RuntimeError("the source answered but no price could be read")
            snapshot = write_snapshot(
                name,
                {
                    "source": fetched.source_url,
                    "source_sha256": fetched.source_sha256,
                    "source_version": fetched.source_version,
                    "records": fetched.records,
                },
            )
            rows = [
                observation(run_id, at, name, collector, o, snapshot, classes[name]) for o in offers
            ]
            unmapped = sorted({r["gpu_raw"] for r in rows if r["gpu"] == "unmapped"})
            observations += rows
            entry.update(status="ok", offers=len(rows), snapshot=snapshot)
            if fetched.source_version:
                entry["source_version"] = fetched.source_version
            problems = fetched.problems + [
                f"{g}: GPU name not in registry/gpus.yaml" for g in unmapped
            ]
            if problems:
                entry["problems"] = problems[:MAX_PROBLEMS]
                entry["problems_total"] = len(problems)
        except Exception as e:  # noqa: BLE001 - every failure is recorded, none is fatal
            entry.update(status="failed", offers=0, error=f"{type(e).__name__}: {e}"[:600])
            if fetched is not None and fetched.problems:
                # Keep the parser's notes: they say what changed at the source.
                entry["problems"] = fetched.problems[:MAX_PROBLEMS]
                entry["problems_total"] = len(fetched.problems)
        results.append(entry)

    month = started.strftime("%Y-%m")
    path = observations_file(month)
    digest = append_lines(path, observations) if observations else None
    record = {
        "run": run_id,
        "started_at": iso(started),
        "finished_at": iso(now or utc_now()),
        "code": code_version(),
        "rule": registry.CURRENT_RULE,
        "results": results,
        "observations": {
            "file": path.relative_to(root()).as_posix(),
            "count": len(observations),
            "sha256": digest,
        },
    }
    return append_chained(runs_file(), record)
