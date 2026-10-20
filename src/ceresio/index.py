"""Index calculation: from ledger observations to daily fixings.

For a fixing day D and an index definition:

1. For each provider, take the observations of its latest *successful* run on or
   before the end of D. Offers that disappeared from the provider's list are gone
   with that run; old offers are never carried forward.
2. If that run is older than the staleness window, the provider is excluded and
   listed as stale.
3. Keep eligible offers: pricing model, GPU model, location scope, basket.
4. Provider quote = cheapest per-GPU-hour price in EUR (ECB rate of the run date).
5. Index = median of quotes, published only with at least `min_constituents`.
   Otherwise the fixing says "insufficient_data" and has no value.

A fixing, once written for (day, index), is final: it is never recalculated.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_EVEN, Decimal

from . import fx, ledger, registry
from .util import money


@dataclass
class ProviderState:
    provider: str
    run: str  # run id of the latest successful collection on or before the day
    run_date: str
    observations: list[dict] = field(default_factory=list)


def provider_states(
    day: str, runs: list[dict] | None = None, observations: list[dict] | None = None
) -> dict[str, ProviderState]:
    """Latest successful run per provider up to the end of `day` (UTC)."""
    runs = ledger.runs() if runs is None else runs
    observations = list(ledger.iter_observations()) if observations is None else observations
    latest: dict[str, ProviderState] = {}
    for r in runs:
        run_date = r["started_at"][:10]
        if run_date > day:
            continue
        for res in r["results"]:
            if res["status"] == "ok":
                latest[res["provider"]] = ProviderState(res["provider"], r["run"], run_date)
    wanted = {(s.provider, s.run): s for s in latest.values()}
    for o in observations:
        s = wanted.get((o["provider"], o["run"]))
        if s is not None:
            s.observations.append(o)
    return latest


def _in_scope(obs: dict, scope: set[str]) -> bool:
    if obs.get("region") == "catalogue":
        return registry.catalogue_in_scope(registry.providers()[obs["provider"]])
    return obs.get("country") in scope


def _in_basket(provider: str, status: str, basket: dict) -> bool:
    if status != basket["status"]:
        return False
    members = basket.get("providers")
    return members is None or provider in members


def eligible(
    obs: dict, gpu: str | None, method: dict, basket: dict, tier: str | None = None
) -> bool:
    scope = set(method["location_scope"]["countries"])
    if obs["pricing_model"] != method["eligibility"]["pricing_model"]:
        return False
    if obs["tier"] < method["eligibility"]["min_tier"]:
        return False
    if gpu is not None and obs["gpu"] != gpu:
        return False
    if tier is not None and (registry.gpu_info(obs["gpu"]) or {}).get("tier") != tier:
        return False
    return _in_scope(obs, scope) and _in_basket(obs["provider"], obs["class"], basket)


def quote_eur(obs: dict) -> tuple[Decimal, dict]:
    amount, rate_date = fx.to_eur(
        Decimal(obs["gpu_hour"]), obs["currency"], obs["observed_at"][:10]
    )
    return amount, {"currency": obs["currency"], "rate_date": rate_date}


def _round(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)


def fixing(
    day: str,
    index_def: dict,
    states: dict[str, ProviderState],
    method_id: str = registry.CURRENT_METHODOLOGY,
) -> dict:
    method = registry.methodology(method_id)
    basket = method["baskets"][index_def["basket"]]
    stale_before = (date.fromisoformat(day) - timedelta(days=method["staleness_days"])).isoformat()
    constituents, excluded = [], []
    for provider, state in sorted(states.items()):
        offers = [o for o in state.observations if eligible(o, index_def["gpu"], method, basket)]
        if not offers:
            continue
        if state.run_date < stale_before:
            excluded.append({"provider": provider, "reason": "stale", "last_run": state.run})
            continue
        priced = []
        for o in offers:
            try:
                eur, conv = quote_eur(o)
            except fx.MissingRate as e:
                excluded.append({"provider": provider, "reason": f"fx: {e}"})
                break
            priced.append((eur, o, conv))
        else:
            eur, best, conv = min(priced, key=lambda t: t[0])
            constituents.append(
                {
                    "provider": provider,
                    "quote_eur": money(_round(eur), 4),
                    "offer": best["offer"],
                    "native": f"{best['gpu_hour']} {best['currency']}",
                    "fx_date": conv["rate_date"],
                    "run": state.run,
                    "offers_considered": len(offers),
                }
            )
    rec = {
        "type": "index",
        "date": day,
        "index": index_def["id"],
        "methodology": method_id,
        "rule": basket["rule"],
        "constituents": constituents,
        "excluded": excluded,
        "min_constituents": index_def["min_constituents"],
    }
    if len(constituents) >= index_def["min_constituents"]:
        values = [Decimal(c["quote_eur"]) for c in constituents]
        rec.update(
            status="published",
            value=money(_round(statistics.median(values)), 4),
            currency="EUR",
            unit="GPU-hour",
        )
    else:
        rec.update(
            status="insufficient_data",
            value=None,
            reason=f"{len(constituents)} fresh constituent(s), "
            f"{index_def['min_constituents']} required",
        )
    return rec


def coverage(
    day: str, states: dict[str, ProviderState], method_id: str = registry.CURRENT_METHODOLOGY
) -> dict:
    """Share of sovereign providers (all of them, with or without data) that publicly list
    a frontier GPU on demand in Europe."""
    method = registry.methodology(method_id)
    cov = method["coverage"]
    basket = method["baskets"][cov["basket"]]
    stale_before = (date.fromisoformat(day) - timedelta(days=method["staleness_days"])).isoformat()
    classes = registry.classifications(basket["rule"])
    members = sorted(p for p, c in classes.items() if c.status == basket["status"])
    listing = {}
    for p in members:
        s = states.get(p)
        if s is None or s.run_date < stale_before:
            listing[p] = None  # unknown: no fresh public data
            continue
        models = sorted(
            {
                o["gpu"]
                for o in s.observations
                if eligible(o, None, method, basket, tier=cov["tier"])
            }
        )
        listing[p] = models
    with_frontier = [p for p, m in listing.items() if m]
    return {
        "type": "coverage",
        "date": day,
        "index": cov["id"],
        "methodology": method_id,
        "rule": basket["rule"],
        "status": "published",
        "value": f"{len(with_frontier)}/{len(members)}",
        "share": money(Decimal(len(with_frontier)) / Decimal(len(members)), 4) if members else None,
        "providers": {p: listing[p] for p in members},
    }


def compute_day(day: str, method_id: str = registry.CURRENT_METHODOLOGY) -> list[dict]:
    states = provider_states(day)
    method = registry.methodology(method_id)
    out = [fixing(day, d, states, method_id) for d in method["indices"]]
    out.append(coverage(day, states, method_id))
    return out


def publish(day: str) -> list[dict]:
    """Write fixings for `day` that are not already in the ledger. Returns those written."""
    done = {(f["date"], f["index"]) for f in ledger.fixings()}
    written = []
    for rec in compute_day(day):
        if (rec["date"], rec["index"]) in done:
            continue
        written.append(ledger.append_chained(ledger.fixings_file(), rec))
    return written
