"""Command line: `uv run ceresio <command>`.

daily      fx + collect + fix: what the scheduled job runs every day
collect    run the collectors once (--only scaleway,azure to restrict)
fx         append new ECB reference rates
fix        publish today's fixings (or --date YYYY-MM-DD) if not already published
build      generate the static site into dist/
verify     check hash chains and observation integrity (--against REF adds the git check)
classify   print each provider's sovereignty status and the criteria behind it
alerts     list providers whose collection failed N runs in a row (exit 1 if any)
"""

from __future__ import annotations

import argparse
import sys

from . import fx, ledger, registry
from .http import session, use_system_trust_store
from .util import utc_now


def _collect(args) -> int:
    from .collect import run

    only = args.only.split(",") if args.only else None
    rec = run(session(), only=only)
    for r in rec["results"]:
        extra = r.get("error") or (
            f"{r.get('problems_total', 0)} note(s)" if r.get("problems") else ""
        )
        print(f"  {r['provider']:<12} {r['status']:<7} {r['offers']:>4} offers  {extra}")
    print(f"run {rec['run']}: {rec['observations']['count']} observations")
    return 0 if any(r["status"] == "ok" for r in rec["results"]) else 1


def _fx(_args) -> int:
    print(f"ECB: {fx.update(session())} new date(s)")
    return 0


def _fix(args) -> int:
    from .index import publish

    day = args.date or utc_now().date().isoformat()
    for f in publish(day):
        shown = f.get("value") if f["status"] == "published" else f["status"]
        print(f"  {f['index']:<14} {shown}")
    return 0


def _build(args) -> int:
    from .site import build

    out = build(args.out, single=args.single)
    print(f"site written to {out}")
    return 0


def _verify(args) -> int:
    errors = ledger.verify()
    if args.against:
        errors += ledger.verify_append_only(args.against)
    for e in errors:
        print("  ERROR", e)
    print("ledger OK" if not errors else f"{len(errors)} problem(s)")
    return 1 if errors else 0


def _classify(_args) -> int:
    for pid, c in registry.classifications().items():
        marks = " ".join(f"{k['id']}={k['result']}" for k in c.criteria)
        prov = " (provisional)" if c.provisional else ""
        print(f"  {pid:<17} {c.status:<14} {marks}{prov}")
    return 0


def _alerts(args) -> int:
    streak: dict[str, int] = {}
    last_error: dict[str, str] = {}
    for run in ledger.runs():
        for r in run["results"]:
            if r["status"] == "ok":
                streak[r["provider"]] = 0
            else:
                streak[r["provider"]] = streak.get(r["provider"], 0) + 1
                last_error[r["provider"]] = r.get("error", "")
    failing = {p: n for p, n in streak.items() if n >= args.streak}
    for p, n in sorted(failing.items()):
        print(f"- **{p}**: failed {n} run(s) in a row. Last error: `{last_error[p][:300]}`")
    return 1 if failing else 0


def _daily(args) -> int:
    _fx(args)
    code = _collect(args)
    _fix(args)
    return code


def main(argv: list[str] | None = None) -> int:
    use_system_trust_store()
    p = argparse.ArgumentParser(
        prog="ceresio", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn in [
        ("daily", _daily),
        ("collect", _collect),
        ("fx", _fx),
        ("fix", _fix),
        ("build", _build),
        ("verify", _verify),
        ("classify", _classify),
        ("alerts", _alerts),
    ]:
        sp = sub.add_parser(name)
        sp.set_defaults(fn=fn)
        if name in ("collect", "daily"):
            sp.add_argument("--only", help="comma-separated provider ids")
        if name in ("fix", "daily"):
            sp.add_argument("--date", help="fixing day, YYYY-MM-DD (default: today, UTC)")
        if name == "build":
            sp.add_argument("--out", default="dist")
            sp.add_argument("--single", action="store_true", help="one self-contained HTML file")
        if name == "alerts":
            sp.add_argument("--streak", type=int, default=2)
        if name == "verify":
            sp.add_argument("--against", help="git ref the ledger must extend, e.g. origin/main")
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
