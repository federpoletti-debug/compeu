import pytest

from compeu import registry


@pytest.mark.parametrize(
    ("raw", "model", "variant"),
    [
        ("H100-SXM", "h100", "sxm"),
        ("NVIDIA Hopper H100", "h100", None),
        ("H100 NVL", "h100", "nvl"),
        ("NVIDIA H100 PCIe", "h100", "pcie"),
        ("NVIDIA Hopper H200 nvlink", "h200", "sxm"),
        ("GB300 SXM6 288GB", "gb300", "sxm"),
        ("1x B300 SXM6 268GB", "b300", "sxm"),
        ("A100 80GB PCIe", "a100", "pcie"),
        ("A10G", "a10", None),
        ("NVIDIA RTX PRO™ 6000 Blackwell Max-Q", "rtx-pro-6000", None),
        ("NVIDIA RTX PRO™ 4000 Blackwell SFF Edition", "rtx-pro-4000", None),
        ("NVIDIA RTX 4000 SFF Ada Generation", "rtx-4000-ada", None),
        ("NVIDIA RTX A4000", "rtx-a4000", None),
        ("Quadro-RTX5000", "quadro-rtx-5000", None),
        ("NVIDIA Ada Lovelace L40S", "l40s", None),
        ("NVIDIA Ada Lovelace L4", "l4", None),
        ("NVIDIA GeForce RTX 3080 Ti", "rtx-3080ti", None),
        ("AMD Instinct MI300X OAM", "mi300x", None),
        ("Some Future Accelerator X1", "unmapped", None),
    ],
)
def test_normalize_gpu(raw, model, variant):
    m = registry.normalize_gpu(raw)
    assert (m.model, m.variant) == (model, variant)


def _provider(seat="FR", ctrl="FR", extra=False, contested=False):
    return {
        "id": "x",
        "legal_entity": {"name": "X SAS", "country": seat},
        "ultimate_controller": {
            "country": ctrl,
            "extraterritorial_law": extra,
            "contested": contested,
        },
    }


def test_sovereign_when_all_criteria_pass():
    assert registry.classify(_provider()).status == "sovereign"


def test_swiss_counts_as_sovereign():
    assert registry.classify(_provider("CH", "CH")).status == "sovereign"


def test_eu_seat_with_us_parent_is_not_sovereign():
    # The AWS European Sovereign Cloud case: German entity, US parent.
    c = registry.classify(_provider("DE", "US", True))
    assert c.status == "non_sovereign"
    assert {k["id"]: k["result"] for k in c.criteria}["seat"] == "pass"


def test_uk_is_outside_the_rule():
    assert registry.classify(_provider("GB", "GB")).status == "non_sovereign"


def test_contested_control_is_under_review():
    assert registry.classify(_provider(contested=True)).status == "under_review"


def test_unknown_fact_is_under_review():
    assert registry.classify(_provider(extra="unknown")).status == "under_review"


def test_registry_statuses_match_expectations():
    c = registry.classifications()
    assert c["scaleway"].status == "sovereign"
    assert c["ovhcloud"].status == "sovereign"
    assert c["aws"].status == "non_sovereign"
    assert c["azure"].status == "non_sovereign"
    assert c["exoscale"].status == "under_review"


def test_every_collected_provider_has_sites_or_a_scope():
    # A collected provider needs a place for its prices: published sites, a global
    # scope, or a catalogue the registry marks as its European price list.
    for p in registry.providers().values():
        col = p.get("collection") or {}
        if col.get("method") in ("api", "html"):
            placed = p.get("sites") or p.get("scope") == "global" or col.get("catalogue_in_scope")
            assert placed, p["id"]


def test_new_providers_classify_as_expected():
    c = registry.classifications()
    assert c["seeweb"].status == "sovereign" and c["seeweb"].provisional
    assert c["stackit"].status == "sovereign"
    assert c["swisscom"].status == "sovereign"
    assert c["gcore"].status == "under_review"
    assert c["nebius"].status == "under_review"  # counted in index/2 by decision, rule unchanged


def test_country_codes_are_strings():
    """YAML 1.1 reads a bare NO (Norway) as false: every code must stay a string."""
    for p in registry.providers().values():
        for s in p.get("sites") or []:
            assert isinstance(s["country"], str), (p["id"], s)
            assert isinstance(s["id"], str), (p["id"], s)
        for fact in ("legal_entity", "ultimate_controller"):
            assert isinstance((p.get(fact) or {}).get("country", ""), str), p["id"]
    method = registry.methodology()
    assert all(isinstance(c, str) for c in method["location_scope"]["countries"])
    assert "NO" in method["location_scope"]["countries"]
    assert all(isinstance(c, str) for c in registry.rule()["countries"])
