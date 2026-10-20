"""Static site build: ledger + registry -> dist/.

Everything the site shows is computed here from the ledger, at build time. The
page gets one JSON document (embedded in the HTML and also published at
data/latest.json); the browser only draws it. There is no server and no
database: a static host is enough.

    uv run ceresio build            # dist/ for a static host
    uv run ceresio build --single   # one self-contained HTML file (for previews)
"""

from __future__ import annotations

import csv
import io
import json
import re
import shutil
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import __version__, fx, index, ledger, registry
from .util import money, root, utc_now


def settings() -> dict:
    """Public site settings (site/site.yaml): repository, contact, base URL, schedule."""
    with (root() / "site" / "site.yaml").open(encoding="utf-8") as f:
        return yaml.safe_load(f)


THREE_CDN = "https://cdn.jsdelivr.net/npm/three@0.169.0/build/three.module.min.js"
JS_ORDER = ["format.js", "charts.js", "map3d.js", "main.js"]


# ------------------------------------------------------------------ data model


def _eur(obs: dict) -> str | None:
    try:
        value, _ = index.quote_eur(obs)
    except fx.MissingRate:
        return None
    return money(value.quantize(Decimal("0.0001")), 4)


def _health(runs: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for r in runs:
        for res in r["results"]:
            h = out.setdefault(res["provider"], {"failed_streak": 0, "runs": 0, "ok_runs": 0})
            h["runs"] += 1
            h["last_run"] = r["started_at"]
            h["last_status"] = res["status"]
            if res["status"] == "ok":
                h["ok_runs"] += 1
                h["failed_streak"] = 0
                h["last_ok"] = r["started_at"]
                h["offers"] = res.get("offers", 0)
                h["notes"] = res.get("problems_total", 0)
                h["source_version"] = res.get("source_version")
            else:
                h["failed_streak"] += 1
                h["last_error"] = res.get("error")
    return out


def build_data() -> dict:
    runs = ledger.runs()
    fixings = ledger.fixings()
    method = registry.methodology()
    rule = registry.rule()
    classes = registry.classifications()
    today = runs[-1]["started_at"][:10] if runs else utc_now().date().isoformat()
    states = index.provider_states(today, runs)
    health = _health(runs)

    # Latest offers per provider (from its latest successful run), priced in EUR.
    offers = []
    for pid, st in sorted(states.items()):
        for o in st.observations:
            if o["gpu"] == "unmapped":
                continue
            offers.append(
                {
                    "provider": pid,
                    "sku": o["sku"],
                    "gpu": o["gpu"],
                    "variant": o["variant"],
                    "gpu_raw": o["gpu_raw"],
                    "gpu_count": o["gpu_count"],
                    "region": o["region"],
                    "country": o["country"],
                    "model": o["pricing_model"],
                    "native": o["gpu_hour"],
                    "currency": o["currency"],
                    "eur": _eur(o),
                    "observed_at": o["observed_at"],
                    "method": o["method"],
                    "tier": o["tier"],
                    "class": o["class"],
                    "extra": o.get("extra"),
                }
            )

    # Fixing series per index id.
    series: dict[str, list] = defaultdict(list)
    latest: dict[str, dict] = {}
    for f in fixings:
        series[f["index"]].append(
            [f["date"], f.get("value") if f["status"] == "published" else None]
        )
        latest[f["index"]] = f
    defs = {d["id"]: d for d in method["indices"]}
    boards = []
    for d in method["indices"]:
        f = latest.get(d["id"])
        prev = [v for _, v in series.get(d["id"], [])[:-1] if v is not None]
        boards.append(
            {
                "id": d["id"],
                "name": d["name"],
                "gpu": d["gpu"],
                "basket": d["basket"],
                "headline": d.get("headline", False),
                "min": d["min_constituents"],
                "status": f["status"] if f else "not_started",
                "date": f["date"] if f else None,
                "value": f.get("value") if f else None,
                "previous": prev[-1] if prev else None,
                "constituents": f["constituents"] if f else [],
                "excluded": f["excluded"] if f else [],
                "reason": f.get("reason") if f else None,
            }
        )
    cov_id = method["coverage"]["id"]
    cov = latest.get(cov_id)

    providers = []
    for pid, p in registry.providers().items():
        c = classes[pid]
        col = p.get("collection") or {}
        providers.append(
            {
                "id": pid,
                "name": p["name"],
                "aka": p.get("aka"),
                "website": p.get("website"),
                "status": c.status,
                "provisional": c.provisional,
                "criteria": c.criteria,
                "legal_entity": p.get("legal_entity"),
                "controller": p.get("ultimate_controller"),
                "disclosures": p.get("disclosures", []),
                "hq": p.get("hq"),
                "sites": p.get("sites", []),
                "scope": p.get("scope", "europe"),
                "collection": {
                    "method": col.get("method"),
                    "status": col.get("status"),
                    "note": " ".join((col.get("note") or "").split()),
                    "source": col.get("source"),
                    "catalogue_in_scope": col.get("catalogue_in_scope", False),
                },
                "evidence": p.get("evidence", []),
                "health": health.get(pid),
            }
        )

    gpus = {
        m["id"]: {k: m[k] for k in ("label", "vendor", "arch", "memory_gb", "tier")}
        for m in registry.gpu_models()["models"]
    }
    fx_rows = fx.rates()
    obs_count = sum(r["observations"]["count"] for r in runs)
    return {
        "version": __version__,
        "generated_at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "schedule": settings()["schedule"],
        "repo": settings()["repo"],
        "site": settings(),
        "today": today,
        "methodology": {
            "id": method["id"],
            "effective_from": method["effective_from"],
            "staleness_days": method["staleness_days"],
            "aggregation": method["aggregation"],
            "provider_quote": method["provider_quote"],
            "scope": method["location_scope"]["label"],
            "scope_countries": method["location_scope"]["countries"],
            "baskets": method["baskets"],
            "indices": list(defs.values()),
        },
        "rule": {
            "id": rule["id"],
            "countries": rule["countries"],
            "criteria": rule["criteria"],
            "outcomes": rule["outcomes"],
            "effective_from": rule["effective_from"],
        },
        "boards": boards,
        "series": dict(series),
        "coverage": cov,
        "coverage_series": series.get(cov_id, []),
        "providers": providers,
        "offers": offers,
        "gpus": gpus,
        "fx": fx_rows[-1] if fx_rows else None,
        "ledger": {
            "runs": len(runs),
            "observations": obs_count,
            "fixings": len(fixings),
            "first_run": runs[0]["started_at"] if runs else None,
            "last_run": runs[-1]["started_at"] if runs else None,
            "runs_head": runs[-1]["hash"] if runs else None,
            "fixings_head": fixings[-1]["hash"] if fixings else None,
        },
    }


# ------------------------------------------------------------------ downloads


def _csv(rows: list[dict], fields: list[str]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def write_downloads(data: dict, out: Path) -> None:
    d = out / "data"
    d.mkdir(parents=True, exist_ok=True)
    (d / "latest.json").write_text(json.dumps(data, indent=1, ensure_ascii=False), "utf-8")
    flat = []
    for f in ledger.fixings():
        flat.append(
            {
                "date": f["date"],
                "index": f["index"],
                "status": f["status"],
                "value_eur": f.get("value") or "",
                "methodology": f["methodology"],
                "constituents": len(f.get("constituents", []))
                if f["type"] == "index"
                else f.get("value"),
                "hash": f["hash"],
            }
        )
    (d / "fixings.csv").write_text(_csv(flat, list(flat[0]) if flat else ["date"]), "utf-8")
    fields = [
        "provider",
        "sku",
        "gpu",
        "variant",
        "gpu_count",
        "region",
        "country",
        "model",
        "native",
        "currency",
        "eur",
        "observed_at",
        "method",
        "tier",
        "class",
    ]
    (d / "offers-latest.csv").write_text(_csv(data["offers"], fields), "utf-8")
    shutil.copy2(
        ledger.fixings_file(), d / "fixings.jsonl"
    ) if ledger.fixings_file().exists() else None


# ------------------------------------------------------------------ pages


def _env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(root() / "site" / "templates"),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["eur"] = lambda v: "—" if v is None else f"€{Decimal(v):,.2f}"
    return env


LOCAL_IMPORT = re.compile(r"^import\s+.*?from\s+['\"]\./[^'\"]+['\"];?\s*$", re.M)


def _bundle_js(static: Path, three_url: str) -> str:
    """Concatenate the page's ES modules into one module (local imports removed)."""
    parts = []
    for name in JS_ORDER:
        src = (static / "js" / name).read_text(encoding="utf-8")
        src = LOCAL_IMPORT.sub("", src)
        src = re.sub(r"^export\s+(?=(async\s+)?(function|const|class|let))", "", src, flags=re.M)
        parts.append(f"// ---- {name}\n{src}")
    js = "\n".join(parts)
    # One import of three for the whole bundle, at the top.
    js = re.sub(r"^import\s+\*\s+as\s+THREE\s+from\s+['\"][^'\"]+['\"];?\s*$", "", js, flags=re.M)
    return f"import * as THREE from '{three_url}';\n{js}"


def build(out_dir: str = "dist", single: bool = False) -> Path:
    out = root() / out_dir
    static = root() / "site" / "static"
    data = build_data()
    env = _env()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    data_json = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    geo = (static / "geo" / "europe-dots.json").read_text(encoding="utf-8")

    if single:
        css = (static / "css" / "site.css").read_text(encoding="utf-8")
        css = re.sub(r"@font-face\s*{[^}]*}", "", css)  # fonts come from Google Fonts in previews
        html = env.get_template("index.html").render(
            data=data,
            data_json=data_json,
            single=True,
            inline_css=css,
            inline_js=_bundle_js(static, THREE_CDN),
            geo_json=geo,
            prefix="",
        )
        target = out / "ceresio-index.html"
        target.write_text(html, encoding="utf-8")
        return target

    shutil.copytree(static, out / "static")
    for page, tpl, prefix in [
        ("index.html", "index.html", ""),
        ("methodology/index.html", "methodology.html", "../"),
        ("data/index.html", "data.html", "../"),
    ]:
        target = out / page
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            env.get_template(tpl).render(
                data=data, data_json=data_json, single=False, prefix=prefix, geo_json=None
            ),
            encoding="utf-8",
        )
    write_downloads(data, out)
    (out / ".nojekyll").write_text("", encoding="utf-8")
    return out
