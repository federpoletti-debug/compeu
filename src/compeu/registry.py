"""Registry: providers, GPU models, sovereignty rules and index methodology.

The sovereignty status of a provider is always computed here from registry facts
and a versioned rule, never stored as a hand-typed label.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from .util import root

CURRENT_RULE = "sovereignty/1"
CURRENT_METHODOLOGY = "index/2"


def _load(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def registry_dir() -> Path:
    return root() / "registry"


@cache
def providers() -> dict[str, dict]:
    data = _load(registry_dir() / "providers.yaml")
    out = {p["id"]: p for p in data["providers"]}
    if len(out) != len(data["providers"]):
        raise ValueError("duplicate provider id in registry/providers.yaml")
    return out


@cache
def rule(rule_id: str = CURRENT_RULE) -> dict:
    name = rule_id.replace("/", "-v") + ".yaml"
    return _load(registry_dir() / "rules" / name)


@cache
def methodology(method_id: str = CURRENT_METHODOLOGY) -> dict:
    name = method_id.replace("/", "-v") + ".yaml"
    return _load(registry_dir() / "methodology" / name)


def methodology_for(day: str) -> str:
    """Id of the methodology in force on `day`: the latest whose effective_from <= day."""
    best = None
    for path in sorted((registry_dir() / "methodology").glob("index-v*.yaml")):
        m = _load(path)
        if str(m["effective_from"]) <= day and (best is None or str(m["effective_from"]) > best[0]):
            best = (str(m["effective_from"]), m["id"])
    if best is None:
        raise ValueError(f"no methodology in force on {day}")
    return best[1]


@cache
def gpu_models() -> dict:
    return _load(registry_dir() / "gpus.yaml")


# --------------------------------------------------------------------------- GPUs


@dataclass(frozen=True)
class GpuMatch:
    model: str  # canonical id, or "unmapped"
    variant: str | None


def normalize_gpu(raw: str) -> GpuMatch:
    """Map a provider's GPU name to a canonical model. Unknown names stay unmapped."""
    text = raw.lower().replace("™", "").replace("_", " ")
    cat = gpu_models()
    model = "unmapped"
    for m in cat["models"]:
        if any(re.search(p, text) for p in m["match"]):
            model = m["id"]
            break
    variant = None
    for v in cat["variants"]:
        if any(re.search(p, text) for p in v["match"]):
            variant = v["id"]
            break
    return GpuMatch(model, variant)


def gpu_info(model_id: str) -> dict | None:
    for m in gpu_models()["models"]:
        if m["id"] == model_id:
            return m
    return None


# ------------------------------------------------------------------- sovereignty

PASS, FAIL, UNKNOWN = "pass", "fail", "unknown"


@dataclass
class Classification:
    provider: str
    status: str  # sovereign | non_sovereign | under_review
    rule: str
    criteria: list[dict] = field(default_factory=list)
    provisional: bool = False

    def as_dict(self) -> dict:
        return {
            "provider": self.provider,
            "status": self.status,
            "rule": self.rule,
            "criteria": self.criteria,
            "provisional": self.provisional,
        }


def classify(provider: dict, rule_id: str = CURRENT_RULE) -> Classification:
    """Apply a sovereignty rule to a provider's registry facts."""
    r = rule(rule_id)
    if r["id"] != rule_id:
        raise ValueError(f"rule file id {r['id']!r} does not match {rule_id!r}")
    zone = set(r["countries"])
    entity = provider.get("legal_entity") or {}
    ctrl = provider.get("ultimate_controller") or {}

    def in_zone(country: str | None) -> str:
        if not country or country == "unknown":
            return UNKNOWN
        return PASS if country in zone else FAIL

    seat = in_zone(entity.get("country"))
    control = in_zone(ctrl.get("country"))
    extra = ctrl.get("extraterritorial_law")
    no_extra = UNKNOWN if extra in (None, "unknown") else (FAIL if extra else PASS)
    if ctrl.get("contested"):
        # A contested control fact can neither pass nor fail: it needs review.
        control = UNKNOWN

    results = {"seat": seat, "control": control, "no_extraterritorial": no_extra}
    criteria = []
    for c in r["criteria"]:
        criteria.append({"id": c["id"], "question": c["question"], "result": results[c["id"]]})

    values = set(results.values())
    if FAIL in values:
        status = "non_sovereign"
    elif UNKNOWN in values:
        status = "under_review"
    else:
        status = "sovereign"
    provisional = any((x or {}).get("confidence") == "provisional" for x in (entity, ctrl))
    return Classification(provider["id"], status, rule_id, criteria, provisional)


@cache
def classifications(rule_id: str = CURRENT_RULE) -> dict[str, Classification]:
    return {pid: classify(p, rule_id) for pid, p in providers().items()}


def location_scope(method_id: str = CURRENT_METHODOLOGY) -> set[str]:
    return set(methodology(method_id)["location_scope"]["countries"])


def catalogue_in_scope(provider: dict) -> bool:
    """Whether a provider's region-less catalogue price counts as a European price.

    Set explicitly in the registry (`collection.catalogue_in_scope`) with a reason,
    never inferred.
    """
    return bool((provider.get("collection") or {}).get("catalogue_in_scope"))


def site_country(provider_id: str, region: str | None) -> str | None:
    if not region:
        return None
    for s in providers()[provider_id].get("sites") or []:
        if s["id"] == region:
            return s["country"]
    return None
