from decimal import Decimal

import pytest

from compeu import fx, index, ledger


def _fx(tmp_root, day="2026-10-19", usd="1.12"):
    ledger.append_lines(
        fx.fx_file(), [{"date": day, "rates": {"USD": usd, "CHF": "0.93", "GBP": "0.87"}}]
    )
    fx.rates.cache_clear()


def _obs(
    provider,
    run,
    gpu_hour,
    ccy="EUR",
    gpu="h100",
    cls="sovereign",
    region="fr-par-2",
    country="FR",
    model="on_demand",
    day="2026-10-20",
):
    return {
        "run": run,
        "observed_at": f"{day}T05:00:00Z",
        "provider": provider,
        "offer": f"{provider}:{gpu}:{region}:{model}",
        "region": region,
        "country": country,
        "gpu": gpu,
        "pricing_model": model,
        "gpu_hour": gpu_hour,
        "currency": ccy,
        "tier": 1,
        "class": cls,
    }


def _run(run, day, ok, failed=()):
    results = [{"provider": p, "status": "ok"} for p in ok]
    results += [{"provider": p, "status": "failed"} for p in failed]
    return {"run": run, "started_at": f"{day}T05:00:00Z", "results": results}


H100 = {"id": "T", "basket": "sovereign", "gpu": "h100", "min_constituents": 3}


def test_median_of_cheapest_quote_per_provider(tmp_root):
    _fx(tmp_root)
    obs = [
        _obs("scaleway", "r1", "2.90"),
        _obs("scaleway", "r1", "3.50"),  # second SKU of the same provider: one vote only
        _obs("ovhcloud", "r1", "2.80", region="catalogue", country=None),
        _obs("verda", "r1", "4.48", ccy="USD", region="catalogue", country=None),  # 4.00 EUR
    ]
    states = index.provider_states(
        "2026-10-20", [_run("r1", "2026-10-20", ["scaleway", "ovhcloud", "verda"])], obs
    )
    f = index.fixing("2026-10-20", H100, states)
    assert f["status"] == "published"
    assert f["value"] == "2.9"
    quotes = {c["provider"]: Decimal(c["quote_eur"]) for c in f["constituents"]}
    assert quotes == {"scaleway": Decimal("2.9"), "ovhcloud": Decimal("2.8"), "verda": Decimal("4")}


def test_too_few_constituents_publishes_a_gap_not_a_number(tmp_root):
    _fx(tmp_root)
    obs = [_obs("scaleway", "r1", "2.9"), _obs("ovhcloud", "r1", "2.8", region="catalogue")]
    states = index.provider_states(
        "2026-10-20", [_run("r1", "2026-10-20", ["scaleway", "ovhcloud"])], obs
    )
    f = index.fixing("2026-10-20", H100, states)
    assert f["status"] == "insufficient_data" and f["value"] is None


def test_failed_run_falls_back_to_last_good_run_until_stale(tmp_root):
    _fx(tmp_root, "2026-10-10")
    _fx(tmp_root, "2026-10-14")
    runs = [_run("r1", "2026-10-10", ["scaleway"]), _run("r2", "2026-10-14", [], ["scaleway"])]
    obs = [_obs("scaleway", "r1", "2.9", day="2026-10-10")]
    fresh = index.provider_states("2026-10-12", runs, obs)
    stale = index.provider_states("2026-10-14", runs, obs)
    assert fresh["scaleway"].run == "r1"
    f = index.fixing("2026-10-14", dict(H100, min_constituents=1), stale)
    assert f["status"] == "insufficient_data"
    assert f["excluded"] == [{"provider": "scaleway", "reason": "stale", "last_run": "r1"}]


def test_delisted_offer_is_not_carried_forward(tmp_root):
    _fx(tmp_root)
    runs = [_run("r1", "2026-10-19", ["scaleway"]), _run("r2", "2026-10-20", ["scaleway"])]
    obs = [
        _obs("scaleway", "r1", "1.00", day="2026-10-19"),
        _obs("scaleway", "r2", "3.00", gpu="l40s"),
    ]
    states = index.provider_states("2026-10-20", runs, obs)
    f = index.fixing("2026-10-20", dict(H100, min_constituents=1), states)
    assert f["constituents"] == []


@pytest.mark.parametrize(
    ("change", "kept"),
    [
        ({}, True),
        ({"pricing_model": "spot"}, False),
        ({"class": "non_sovereign"}, False),
        ({"class": "under_review"}, False),
        ({"country": "GB", "region": "uksouth"}, False),
        ({"country": "US", "region": "us-east-1"}, False),
        ({"region": "global", "country": None}, False),
    ],
)
def test_eligibility(change, kept):
    from compeu import registry

    method = registry.methodology()
    o = dict(_obs("scaleway", "r", "1"), **change)
    assert index.eligible(o, "h100", method, method["baskets"]["sovereign"]) is kept


def test_hyperscaler_basket_only_takes_listed_providers():
    from compeu import registry

    method = registry.methodology()
    basket = method["baskets"]["hyperscaler"]
    aws = _obs("aws", "r", "6", cls="non_sovereign", region="eu-north-1", country="SE")
    runpod = dict(aws, provider="runpod")
    assert index.eligible(aws, "h100", method, basket)
    assert not index.eligible(runpod, "h100", method, basket)


def test_fx_refuses_a_stale_rate(tmp_root):
    _fx(tmp_root, "2026-10-01")
    with pytest.raises(fx.MissingRate):
        fx.rate_on("2026-10-20", "USD")
    assert fx.rate_on("2026-10-03", "USD") == (Decimal("1.12"), "2026-10-01")


def test_publish_never_rewrites_a_fixing(tmp_root, monkeypatch):
    calls = iter(
        [[{"date": "d", "index": "X", "value": "1"}], [{"date": "d", "index": "X", "value": "2"}]]
    )
    monkeypatch.setattr(index, "compute_day", lambda day: next(calls))
    assert len(index.publish("d")) == 1
    assert index.publish("d") == []
    assert [f["value"] for f in ledger.fixings()] == ["1"]
