"""Static site build: ledger + registry -> dist/.

The pages are designed in Claude Design (the canvas linked in CLAUDE.md). Each page
is an artboard file in site/design/; src/compeu/dc.py reads it, and this module puts
it on the site: live data from the ledger replaces the artboard's data snapshot,
uploaded pictures become files in site/static/, and site/static/js/dcrun.js renders
the page in the browser. Everything shown is computed here at build time: there is
no server and no database, a static host is enough.

    uv run compeu build            # dist/ for a static host
"""

from __future__ import annotations

import csv
import io
import json
import math
import re
import shutil
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import __version__, dc, fx, index, ledger, registry
from .util import money, root, utc_now


def settings() -> dict:
    """Public site settings (site/site.yaml): repository, contact, base URL, schedule."""
    with (root() / "site" / "site.yaml").open(encoding="utf-8") as f:
        return yaml.safe_load(f)


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


# ------------------------------------------------------------------ design data

# The artboards' map uses a Lambert azimuthal equal-area projection centred on
# Europe (52N 10E), in km; the dot map in site/static/geo uses the same one.
_R, _LAT0, _LON0 = 6371.0072, math.radians(52), math.radians(10)
MAP_GPUS = ["gb300", "b300", "b200", "h200", "h100", "mi300x", "a100", "rtx-pro-6000", "l40s", "l4"]


def _laea(lon: float, lat: float) -> list[int]:
    lam, phi = math.radians(lon), math.radians(lat)
    d = lam - _LON0
    k = math.sqrt(
        2 / (1 + math.sin(_LAT0) * math.sin(phi) + math.cos(_LAT0) * math.cos(phi) * math.cos(d))
    )
    x = _R * k * math.cos(phi) * math.sin(d)
    y = _R * k * (math.cos(_LAT0) * math.sin(phi) - math.sin(_LAT0) * math.cos(phi) * math.cos(d))
    return [round(x), round(y)]


def _short(h: str | None) -> str:
    return (h or "")[7:19]


def _cells(data: dict, prov: dict, in_scope, usable) -> dict[str, dict]:
    """Cheapest usable on-demand price per provider and GPU, in euro per GPU-hour."""
    cells: dict[str, dict] = {}
    for o in data["offers"]:
        p = prov[o["provider"]]
        if not usable(o) or o["gpu"] not in MAP_GPUS:
            continue
        if p["scope"] != "global" and not in_scope(o):
            continue
        c = cells.setdefault(o["provider"], {})
        cur = c.get(o["gpu"])
        if cur is None or float(o["eur"]) < cur[0]:
            c[o["gpu"]] = [round(float(o["eur"]), 2), o["sku"], o["region"], o["gpu_count"]]
    return cells


def _sites(data: dict, usable) -> list[dict]:
    frontier = {g for g, m in data["gpus"].items() if m["tier"] == "frontier"}
    sites = []
    for p in data["providers"]:
        if p["scope"] == "global":
            continue
        for s in p["sites"]:
            here = [
                o
                for o in data["offers"]
                if o["provider"] == p["id"]
                and usable(o)
                and (
                    o["region"] in ("catalogue", s["id"])
                    or (o["region"] or "").startswith(s["id"] + "-")
                )
            ]

            def best(pred, here=here):
                v = [float(o["eur"]) for o in here if pred(o)]
                return round(min(v), 2) if v else None

            x, y = _laea(s["lon"], s["lat"])
            sites.append(
                {
                    "p": p["id"],
                    "c": s["city"],
                    "cc": s["country"],
                    "x": x,
                    "y": y,
                    "h100": best(lambda o: o["gpu"] == "h100"),
                    "h200": best(lambda o: o["gpu"] == "h200"),
                    "b200": best(lambda o: o["gpu"] == "b200"),
                    "a100": best(lambda o: o["gpu"] == "a100"),
                    "l40s": best(lambda o: o["gpu"] == "l40s"),
                    "fr": best(lambda o: o["gpu"] in frontier),
                }
            )
    return sites


def _provider(p: dict, decided: dict) -> dict:
    ctl, ent, hq, h = (
        p["controller"] or {},
        p["legal_entity"] or {},
        p.get("hq") or {},
        p["health"] or {},
    )
    return {
        "id": p["id"],
        "n": p["name"],
        "aka": p.get("aka"),
        "web": p.get("website"),
        "st": p["status"],
        "prov": p["provisional"],
        "dec": decided.get(p["id"]),
        "ent": [ent.get("name"), ent.get("country"), ent.get("city")],
        "ctl": [ctl.get("name"), ctl.get("country")],
        "contested": bool(ctl.get("contested")),
        "why": " ".join((ctl.get("note") or "").split()) or None,
        "disc": [" ".join(d.split()) for d in p["disclosures"]],
        "crit": {c["id"]: c["result"] for c in p["criteria"]},
        "m": p["collection"]["method"],
        "cs": p["collection"]["status"],
        "cn": p["collection"]["note"],
        "src": p["collection"]["source"],
        "hq": _laea(hq["lon"], hq["lat"]) if hq.get("lon") is not None else [None, None],
        "hqc": hq.get("city"),
        "us": ctl.get("country") == "US",
        "ok": (h.get("last_ok") or "")[:16].replace("T", " ") or None,
        "offers": h.get("offers"),
        "global": p["scope"] == "global",
        "nsites": len(p["sites"]),
        "ev": [[e["claim"], e["url"]] for e in p["evidence"]],
    }


def index_days(fixes: list[dict]) -> dict[str, list]:
    """One point per price index and day, for the market chart.

    [date, value, low, high, quotes, methodology, providers]: value is the day's
    fixing, low and high the cheapest and dearest constituent quote, quotes how many
    there were and providers whose. A day without a published fixing keeps its date
    with no value, so the gap shows.
    """
    days: dict[str, list] = defaultdict(list)
    for f in fixes:
        if f.get("type") == "coverage" or str(f["index"]).startswith("CSC"):
            continue
        cons = [c for c in f.get("constituents") or [] if c.get("quote_eur")]
        quotes = [float(c["quote_eur"]) for c in cons]
        published = f.get("status") == "published" and f.get("value") is not None
        days[f["index"]].append(
            [
                f["date"],
                float(f["value"]) if published else None,
                min(quotes) if quotes else None,
                max(quotes) if quotes else None,
                len(quotes),
                f.get("methodology"),
                sorted(c["provider"] for c in cons),
            ]
        )
    return dict(days)


def design_data(data: dict) -> dict:
    """The compact data the artboards' logic reads (its `const D`), from build_data()."""
    prov = {p["id"]: p for p in data["providers"]}
    scope = set(data["methodology"]["scope_countries"])
    decided = {}
    for b in data["methodology"]["baskets"].values():
        for d in b.get("include_under_review") or []:
            reason = " ".join(str(d.get("reason", "")).split())
            decided[d["provider"]] = {"on": str(d.get("decided")), "why": reason}

    def in_scope(o: dict) -> bool:
        if o["region"] == "catalogue":
            return bool(prov[o["provider"]]["collection"]["catalogue_in_scope"])
        return o["country"] in scope

    def usable(o: dict) -> bool:
        flagged = (o.get("extra") or {}).get("flag")
        return o["model"] == "on_demand" and o["eur"] is not None and not flagged

    boards = [
        {
            "id": b["id"],
            "n": b["name"],
            "g": b["gpu"],
            "b": b["basket"],
            "min": b["min"],
            "st": b["status"],
            "d": b["date"],
            "v": float(b["value"]) if b["value"] else None,
            "prev": float(b["previous"]) if b.get("previous") else None,
            "c": [[c["provider"], float(c["quote_eur"]), c["native"]] for c in b["constituents"]],
            "why": b["reason"],
        }
        for b in data["boards"]
    ]
    series = {
        k: [[d, float(v) if v is not None else None] for d, v in vals]
        for k, vals in data["series"].items()
        if not k.startswith("CSC")
    }
    fixes = ledger.fixings()
    last_day = fixes[-1]["date"] if fixes else None
    days = index_days(fixes)
    versions = []
    for path in sorted((registry.registry_dir() / "methodology").glob("index-v*.yaml")):
        m = yaml.safe_load(path.read_text(encoding="utf-8"))
        versions.append({"id": m["id"], "from": str(m["effective_from"])})
    try:
        rate, rate_day = fx.rate_on(data["today"], "USD")
        usd = [str(rate), rate_day]
    except fx.MissingRate:
        usd = [None, None]
    cov = data["coverage"] or {}
    return {
        "asOf": data["today"],
        "method": data["methodology"]["id"],
        "versions": versions,
        "lastRun": data["ledger"]["last_run"],
        "nRuns": data["ledger"]["runs"],
        "obs": data["ledger"]["observations"],
        "nFix": len(fixes),
        "fixHead": _short(fixes[-1]["hash"]) if fixes else "",
        "chain": [
            {
                "d": f["date"],
                "i": f["index"],
                "v": f.get("value"),
                "h": _short(f["hash"]),
                "p": _short(f["prev"]),
            }
            for f in fixes[-8:]
        ],
        "seals": {
            f["index"]: [_short(f["hash"]), _short(f["prev"])]
            for f in fixes
            if f["date"] == last_day
        },
        "usd": usd,
        "days": days,
        "cov": cov.get("value"),
        "covList": cov.get("providers"),
        "boards": boards,
        "series": series,
        "providers": [_provider(p, decided) for p in data["providers"]],
        "cells": _cells(data, prov, in_scope, usable),
        "sites": _sites(data, usable),
        "gpus": {
            g: [data["gpus"][g]["label"], data["gpus"][g]["tier"]]
            for g in MAP_GPUS
            if g in data["gpus"]
        },
    }


# ------------------------------------------------------------------ pages

# Artboards in site/design/, the folder each one is published in, and its description.
PAGES = [
    (
        "Main.dc.html",
        "",
        "The daily price of AI compute that Europe controls: sovereign European GPU clouds "
        "against the US hyperscalers, with every source and rule in the open.",
    ),
    (
        "Why.dc.html",
        "why/",
        "Why European AI needs compute that Europe controls: who owns the cloud, how far US "
        "law reaches, and five questions to ask any provider.",
    ),
    (
        "Index.dc.html",
        "fixings/",
        "Every CompEU fixing: daily median GPU prices for sovereign European clouds and US "
        "hyperscalers, with history, constituents and the raw prices.",
    ),
    (
        "Methodology.dc.html",
        "methodology/",
        "How CompEU decides who is sovereign and how public prices become one daily fixing: "
        "the rules, the versions and the limits.",
    ),
]
BLOB = re.compile(r"^/_blob/([0-9a-f]{32})$")
ARTBOARD_LINK = re.compile(r"^([A-Za-z0-9_-]+\.dc\.html)(#.*)?$")
IMG_CONST = re.compile(r"^const IMG = (.*?);$", re.M)


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(root() / "site" / "templates"),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _assets() -> dict:
    with (root() / "site" / "design" / "assets.yaml").open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _json_script(value) -> str:
    """JSON that is safe inside a <script> element."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def _images(board: dc.Artboard, assets: dict, prefix: str) -> None:
    """Responsive sources and loading hints for the uploaded pictures."""
    for el in dc.elements(board.template):
        m = BLOB.match(el[1].get("src", "")) if el[0] == "img" else None
        if not m:
            continue
        a = assets.get(m.group(1), {})
        if a.get("srcset"):
            el[1]["srcset"] = ", ".join(prefix + "static/" + s for s in a["srcset"])
            el[1]["sizes"] = a["sizes"]
        el[1]["loading"] = a.get("loading", "lazy")
        el[1]["decoding"] = "async"
        if a.get("loading") == "eager":
            el[1]["fetchpriority"] = "high"


def page(
    name: str, folder: str, description: str, live: dict, assets: dict, env: Environment
) -> str:
    """One artboard as a finished HTML page, with live data in place of its snapshot."""
    board = dc.parse((root() / "site" / "design" / name).read_text(encoding="utf-8"))
    dc.hover_classes(board)
    prefix = "../" * folder.count("/")
    folders = {n: f for n, f, _ in PAGES}

    def static(asset_id: str) -> str:
        if asset_id not in assets:
            raise dc.ParseError(f"{name}: /_blob/{asset_id} is not in site/design/assets.yaml")
        return prefix + "static/" + assets[asset_id]["file"]

    def url(value: str) -> str:
        m = BLOB.match(value)
        if m:
            return static(m.group(1))
        m = ARTBOARD_LINK.match(value)
        if m:
            if m.group(1) not in folders:
                raise dc.ParseError(f"{name}: link to {m.group(1)}, which is not a page")
            return ((prefix + folders[m.group(1)]) or "./") + (m.group(2) or "")
        return value

    used = [
        m.group(1)
        for el in dc.elements(board.template)
        if el[0] == "img" and (m := BLOB.match(el[1].get("src", "")))
    ]
    _images(board, assets, prefix)
    dc.map_urls(board, url)
    img = IMG_CONST.search(board.logic)
    if not img:
        raise dc.ParseError(f"{name}: const IMG not found in the logic")
    pictures = {k: static(BLOB.match(v).group(1)) for k, v in json.loads(img.group(1)).items()}
    logic = dc.replace_const(board.logic, "IMG", pictures)
    logic = dc.replace_const(logic, "D", live).replace("</script", "<\\/script")
    s = settings()
    # Preload the picture at the top of this page, if it has one.
    hero = None
    a = next(
        (
            assets[i]
            for i in used
            if assets.get(i, {}).get("loading") == "eager" and assets[i].get("srcset")
        ),
        None,
    )
    if a:
        hero = {
            "href": prefix + "static/" + a["file"],
            "srcset": ", ".join(prefix + "static/" + x for x in a["srcset"]),
            "sizes": a["sizes"],
        }
    return env.get_template("page.html").render(
        title=board.title,
        description=description,
        canonical=s["base_url"] + folder,
        base_url=s["base_url"],
        prefix=prefix,
        style=board.style + "\n" + board.hover_css,
        template_json=_json_script(board.template),
        logic=logic,
        live=live,
        pages={n: (prefix + f) or "./" for n, f, _ in PAGES},
        pages_json=_json_script({n: (prefix + f) or "./" for n, f, _ in PAGES}),
        hero=hero,
    )


def build(out_dir: str = "dist") -> Path:
    out = root() / out_dir
    data = build_data()
    live = design_data(data)
    env = _env()
    assets = _assets()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    shutil.copytree(root() / "site" / "static", out / "static")
    for name, folder, description in PAGES:
        target = out / folder / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page(name, folder, description, live, assets, env), encoding="utf-8")
    write_downloads(data, out)
    # The old data page moved to /fixings/; the downloads stay in /data/.
    moved = env.get_template("moved.html").render(to="../fixings/")
    (out / "data" / "index.html").write_text(moved, encoding="utf-8")
    base = settings()["base_url"]
    sitemap = env.get_template("sitemap.xml").render(
        base=base, pages=[f for _, f, _ in PAGES], day=data["today"]
    )
    (out / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    (out / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {base}sitemap.xml\n", encoding="utf-8"
    )
    (out / ".nojekyll").write_text("", encoding="utf-8")
    return out
