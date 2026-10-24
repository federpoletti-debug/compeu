import json
import re
import shutil
from pathlib import Path

from compeu import site

REPO = Path(__file__).resolve().parents[1]


def _with_site_and_ledger(root: Path) -> None:
    shutil.copytree(REPO / "site", root / "site")
    shutil.copytree(REPO / "ledger", root / "ledger")


def test_build_publishes_every_artboard_with_live_data(tmp_root):
    _with_site_and_ledger(tmp_root)
    out = site.build("dist")
    data = site.build_data()
    for _, folder, _ in site.PAGES:
        html = (out / folder / "index.html").read_text(encoding="utf-8")
        assert "/_blob/" not in html
        # artboard links in the markup are rewritten at build time; the ones the logic
        # computes are rewritten by dcrun.js from this table
        assert re.search(r'dcrun\.mount\(.*"Why\.dc\.html":"[^"]*why/"', html)
        markup = re.search(
            r'<script type="application/json" id="dc-template">(.*?)</script>', html, re.S
        ).group(1)
        assert ".dc.html" not in markup
        template = re.search(
            r'<script type="application/json" id="dc-template">(.*?)</script>', html, re.S
        )
        json.loads(template.group(1))
        live = json.loads(re.search(r"^const D = (\{.*\});$", html, re.M).group(1))
        assert live["asOf"] == data["today"]
        assert [b["id"] for b in live["boards"]] == [b["id"] for b in data["boards"]]
        for ref in re.findall(r'(?:src|href)="([^"#:]+)"', html):
            target = (out / folder / ref).resolve()
            assert target.exists() or (target / "index.html").exists(), (
                f"{folder or 'home'}: {ref} is missing"
            )
    assert (out / "data" / "latest.json").exists()
    assert (out / "data" / "index.html").read_text(encoding="utf-8").count("../fixings/") >= 1
    assert "fixings/" in (out / "sitemap.xml").read_text(encoding="utf-8")


def test_design_data_matches_the_fixings(tmp_root):
    _with_site_and_ledger(tmp_root)
    data = site.build_data()
    live = site.design_data(data)
    for board, b in zip(live["boards"], data["boards"], strict=True):
        assert board["v"] == (float(b["value"]) if b["value"] else None)
        assert len(board["c"]) == len(b["constituents"])
    # one row per provider, and every map site belongs to a known provider
    ids = {p["id"] for p in live["providers"]}
    assert len(ids) == len(data["providers"])
    assert {s["p"] for s in live["sites"]} <= ids
    # never a price that is not in the offers: every cell is a real offer
    offers = {
        (o["provider"], o["gpu"], round(float(o["eur"]), 2))
        for o in data["offers"]
        if o["eur"] is not None
    }
    for pid, cells in live["cells"].items():
        for gpu, cell in cells.items():
            assert (pid, gpu, cell[0]) in offers


def test_index_days_keep_gaps_and_name_the_quotes():
    from compeu.site import index_days

    def fix(day, value, quotes, status="published", method="index/2"):
        return {
            "date": day,
            "index": "CSX-H100",
            "status": status,
            "value": value,
            "methodology": method,
            "constituents": [{"provider": p, "quote_eur": q} for p, q in quotes],
        }

    days = index_days(
        [
            fix("2026-10-20", "2.8665", [("verda", "4.0"), ("ovhcloud", "2.8")], method="index/1"),
            {"date": "2026-10-20", "index": "CSC-FRONTIER", "type": "coverage", "value": "3/9"},
            fix("2026-10-21", None, [("ovhcloud", "2.9")], status="insufficient"),
            fix("2026-10-22", "3.4228", [("scaleway", "1.89"), ("evroc", "4.2")]),
        ]
    )
    assert list(days) == ["CSX-H100"]
    first, gap, third = days["CSX-H100"]
    assert first == ["2026-10-20", 2.8665, 2.8, 4.0, 2, "index/1", ["ovhcloud", "verda"]]
    # no fixing that day: the date stays, the value stays empty
    assert gap == ["2026-10-21", None, 2.9, 2.9, 1, "index/2", ["ovhcloud"]]
    assert third == ["2026-10-22", 3.4228, 1.89, 4.2, 2, "index/2", ["evroc", "scaleway"]]
