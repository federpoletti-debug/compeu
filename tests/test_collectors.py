"""Parsers tested on trimmed copies of real responses (October 2026)."""

from decimal import Decimal

from compeu.collectors import (
    aws,
    azure,
    exoscale,
    hetzner,
    lyceum,
    nebius,
    ovhcloud,
    runpod,
    scaleway,
    seeweb,
    verda,
)
from compeu.collectors.base import Fetched


def test_scaleway_per_minute_price():
    rec = {
        "sku": "/instance/server/h100_sxm_8_80g/fr-par-2",
        "product_category": "Instance",
        "product": "H100-SXM-8-80G",
        "locality": {"zone": "fr-par-2"},
        "price": {"retail_price": {"currency_code": "EUR", "units": 0, "nanos": 422180000}},
        "properties": {"hardware": {"gpu": {"count": 8, "type": "H100-SXM"}}},
        "unit_of_measure": {"unit": "minute", "size": 1},
        "status": "general_availability",
    }
    beta = dict(rec, status="beta", product="X")
    f = Fetched("u", [rec, beta])
    [o] = scaleway.Scaleway().parse(f)
    assert o.price == Decimal("0.42218") and o.unit == "minute" and o.country == "FR"
    assert o.per_gpu_hour() == Decimal("3.166350")
    assert any("beta" in p for p in f.problems)


def test_ovhcloud_price_scale_and_ai_products_excluded():
    inst = {
        "planCode": "h100-760.consumption",
        "blobs": {"technical": {"gpu": {"model": "NVIDIA Hopper H100", "number": 2}}},
        "pricings": [{"intervalUnit": "hour", "price": 560000000}],
    }
    notebook = dict(inst, planCode="ai-notebook.h100-1-gpu.hour.consumption")
    assert ovhcloud._is_gpu_instance(inst) and not ovhcloud._is_gpu_instance(notebook)
    [o] = ovhcloud.OVHcloud().parse(Fetched("u", [{"currency": "EUR", "addon": inst}]))
    assert o.sku == "h100-760" and o.price == Decimal("5.6") and o.per_gpu_hour() == Decimal("2.8")


def test_verda_on_demand_and_spot():
    rec = {
        "instance_type": "1H100.80S.30V",
        "name": "H100 SXM5 80GB",
        "model": "H100",
        "gpu": {"number_of_gpus": 1},
        "price_per_hour": "4.382",
        "spot_price": "2.191",
        "dynamic_price": None,
        "currency": "usd",
    }
    offers = verda.Verda().parse(Fetched("u", [rec]))
    assert {(o.pricing_model, o.price, o.currency) for o in offers} == {
        ("on_demand", Decimal("4.382"), "USD"),
        ("spot", Decimal("2.191"), "USD"),
    }


def test_verda_missing_currency_is_skipped_not_guessed():
    rec = {"instance_type": "x", "gpu": {"number_of_gpus": 1}, "price_per_hour": "1"}
    f = Fetched("u", [rec])
    assert verda.Verda().parse(f) == [] and f.problems


def test_exoscale_joins_price_and_type_per_zone():
    t = {"family": "gpu3", "size": "medium", "gpus": 2, "zones": ["de-fra-1", "ch-gva-2"]}
    f = Fetched(
        "u",
        [
            {"type": t, "price_key": "running_gpu3_medium", "price": "2.09070000"},
            {"type": dict(t, family="gpub300"), "price_key": "running_gpub300_huge", "price": None},
        ],
    )
    offers = exoscale.Exoscale().parse(f)
    assert [o.country for o in offers] == ["DE", "CH"]
    assert offers[0].per_gpu_hour() == Decimal("1.04535")
    assert any("without a price" in p for p in f.problems)


HETZNER_PAGE = """
<p class="hero">Get your server with GPU from Hetzner: NVIDIA RTX GPUs hosted in the EU</p>
<div class="baremetal-product">
  <span class="text-display-8">GEX131</span>
  <ho-price-container class="text-price-4" product-key="ROBOT_1747+ROBOT_1266" price-type="hourly">
    <span class="visually-hidden">$ 2.7224 per hour, excl. VAT</span>
  </ho-price-container>
  <p class="text-copy-3"><strong>24</strong> Cores ▪ Intel® Xeon® Gold 5412U</p>
  <p class="text-copy-3">NVIDIA RTX PRO™ 6000 Blackwell Max-Q </p>
  <a id="order-button" data-event-category="CTA" data-event-action="Order GEX131">Configure</a>
</div>
<div class="baremetal-product">
  <span class="text-display-8"><span class="baremetal-label-new">New</span> GEX430</span>
  <ho-price-container product-key="ROBOT_1769+ROBOT_1266" price-type="hourly"></ho-price-container>
  <p class="text-copy-3"><strong>4x</strong> NVIDIA RTX PRO™ 6000 Blackwell Max-Q </p>
  <a id="order-button" data-event-category="CTA" data-event-action="Order GEX430">Configure</a>
</div>
"""

HETZNER_PRICES = {
    "ROBOT_1747": {
        "locations": [
            {"datacenter": "FSN1", "active": True, "prices": {
                "hourly": {"EUR": "2.399500", "USD": "2.719700"},
                "monthly": {"EUR": "1497.30", "USD": "1697.10"},
                "setup": {"EUR": "1499.00", "USD": "1699.00"}}},
            {"datacenter": "NBG1", "active": False, "prices": {
                "hourly": {"EUR": "2.399500", "USD": "2.719700"}}},
        ]
    },
    "ROBOT_1266": {
        "locations": [
            {"datacenter": "ALL", "active": True, "prices": {
                "hourly": {"EUR": "0.002700", "USD": "0.003000"},
                "monthly": {"EUR": "1.70", "USD": "1.90"}}},
        ]
    },
}  # fmt: skip


def test_hetzner_cards_name_gpu_count_and_products():
    # The hero text above the cards also says NVIDIA: it must not be taken as a spec.
    assert hetzner.extract_cards(HETZNER_PAGE) == [
        {
            "name": "GEX131",
            "gpu": "NVIDIA RTX PRO™ 6000 Blackwell Max-Q",
            "gpu_count": 1,
            "components": ["ROBOT_1747", "ROBOT_1266"],
        },
        {
            "name": "GEX430",
            "gpu": "NVIDIA RTX PRO™ 6000 Blackwell Max-Q",
            "gpu_count": 4,
            "components": ["ROBOT_1769", "ROBOT_1266"],
        },
    ]


def test_hetzner_joins_page_and_price_file_in_euro():
    # The page here prints dollars, as it does for US visitors; the euro price
    # comes from the price file, so the result does not depend on the visitor.
    cards = hetzner.extract_cards(HETZNER_PAGE)[:1]
    f = Fetched("u", [{"cards": cards, "products": HETZNER_PRICES}])
    [o] = hetzner.Hetzner().parse(f)  # NBG1 is inactive, HEL1 absent: only Falkenstein
    assert (o.region, o.currency, o.price) == ("fsn", "EUR", Decimal("2.4022"))
    assert o.extra["setup_fee_eur"] == Decimal("1499.00")
    assert o.extra["monthly_cap_eur"] == Decimal("1499.00")


def test_hetzner_four_gpu_server_is_priced_per_gpu():
    cards = hetzner.extract_cards(HETZNER_PAGE)[1:]
    products = {
        "ROBOT_1769": {"locations": [{"datacenter": "HEL1", "active": True,
                                      "prices": {"hourly": {"EUR": "5.764900"}}}]},
        "ROBOT_1266": HETZNER_PRICES["ROBOT_1266"],
    }  # fmt: skip
    [o] = hetzner.Hetzner().parse(Fetched("u", [{"cards": cards, "products": products}]))
    assert (o.region, o.gpu_count, o.price) == ("hel", 4, Decimal("5.7676"))
    assert o.per_gpu_hour() == Decimal("1.4419")


def test_hetzner_missing_product_is_reported_not_priced():
    cards = hetzner.extract_cards(HETZNER_PAGE)[:1]
    f = Fetched("u", [{"cards": cards, "products": {"ROBOT_1266": HETZNER_PRICES["ROBOT_1266"]}}])
    assert hetzner.Hetzner().parse(f) == []
    assert any("ROBOT_1747" in p for p in f.problems)


def test_hetzner_changed_markup_records_nothing():
    f = Fetched("u", [{"cards": hetzner.extract_cards("<html>redesigned</html>"), "products": {}}])
    assert hetzner.Hetzner().parse(f) == []


def test_azure_sku_table_and_spot():
    base = {
        "armSkuName": "Standard_ND96isr_H100_v5",
        "retailPrice": 127.816,
        "currencyCode": "USD",
        "meterName": "ND96isr H100 v5",
        "armRegionName": "westeurope",
        "productName": "Virtual Machines NDsr H100 v5 Series",
        "unitOfMeasure": "1 Hour",
        "type": "Consumption",
    }
    spot = dict(base, meterName="ND96isr H100 v5 Spot", retailPrice=40.0)
    unknown = dict(base, armSkuName="Standard_ND999_Future_v9")
    f = Fetched("u", [base, spot, unknown])
    offers = azure.Azure().parse(f)
    assert [(o.pricing_model, o.per_gpu_hour()) for o in offers] == [
        ("on_demand", Decimal("15.977")),
        ("spot", Decimal("5")),
    ]
    assert offers[0].country == "NL"
    assert any("Future" in p for p in f.problems)
    assert not azure._keep(dict(base, productName="Virtual Machines NDsr H100 v5 Series Windows"))


def test_aws_filters_and_counts():
    row = dict.fromkeys(aws.KEEP_COLUMNS, "")
    row.update(
        {
            "Instance Type": "p5.48xlarge",
            "PricePerUnit": "58.8928",
            "Currency": "USD",
            "Unit": "Hrs",
            "GPU": "8",
            "Region Code": "eu-north-1",
            "TermType": "OnDemand",
            "MarketOption": "OnDemand",
            "Tenancy": "Shared",
            "Operating System": "Linux",
            "Pre Installed S/W": "NA",
            "CapacityStatus": "Used",
            "License Model": "No License required",
        }
    )
    assert aws._keep(row)
    assert not aws._keep(dict(row, MarketOption="CapacityBlock"))
    assert not aws._keep(dict(row, PricePerUnit="0.0000"))
    [o] = aws.AWS().parse(Fetched("u", [row]))
    assert o.per_gpu_hour() == Decimal("7.3616") and o.country == "SE"


def test_runpod_zero_price_means_not_offered():
    g = {
        "id": "NVIDIA H100 PCIe",
        "securePrice": 2.39,
        "communityPrice": 0,
        "secureSpotPrice": None,
        "communitySpotPrice": None,
    }
    [o] = runpod.RunPod().parse(Fetched("u", [g]))
    assert o.price == Decimal("2.39") and o.region == "global"


def test_runpod_flags_placeholder_and_skips_mig():
    g = {
        "id": "AMD Instinct MI300X OAM",
        "securePrice": 2.39,
        "communityPrice": 0.5,
        "secureSpotPrice": None,
        "communitySpotPrice": None,
    }
    mig = dict(g, id="NVIDIA B300 SXM6 AC MIG 1g.34gb")
    f = Fetched("u", [g, mig])
    offers = runpod.RunPod().parse(f)
    assert {o.extra["cloud"]: o.extra["flag"] for o in offers} == {
        "secure": None,
        "community": "suspect_placeholder",
    }
    assert any("MIG" in p for p in f.problems)


NEBIUS_TEXT = """<table>
<tr><td>NVIDIA GB200 NVL72</td><td>112</td><td>800</td><td>-</td><td>Contact us</td></tr>
<tr><td>NVIDIA HGX H100</td><td>16</td><td>200</td><td>from $0.79</td><td>$4.50</td></tr>
<tr><td>NVIDIA L40S with Intel CPU</td><td>8-40</td><td>32-160</td>
<td>from $0.74**</td><td>from $1.55</td></tr></table>"""


def test_nebius_rows_skip_contact_us_and_keep_per_gpu_prices():
    rows = nebius.extract_rows(NEBIUS_TEXT)
    assert rows == [
        {"name": "NVIDIA HGX H100", "on_demand": "4.50", "preemptible": "0.79"},
        {"name": "NVIDIA L40S with Intel CPU", "on_demand": "1.55", "preemptible": "0.74"},
    ]
    offers = nebius.Nebius().parse(Fetched("u", rows))
    assert {(o.sku, o.pricing_model, o.price) for o in offers} == {
        ("NVIDIA HGX H100", "on_demand", Decimal("4.50")),
        ("NVIDIA HGX H100", "spot", Decimal("0.79")),
        ("NVIDIA L40S with Intel CPU", "on_demand", Decimal("1.55")),
        ("NVIDIA L40S with Intel CPU", "spot", Decimal("0.74")),
    }
    assert all(o.currency == "USD" and o.region == "catalogue" for o in offers)


LYCEUM_TEXT = """<div>NVIDIA H100</div><span>80 GB</span> On demand $4.69 Spot $2.39 On demand $4.69
<div>NVIDIA L40S</div><span>48 GB</span> On demand $1.99 On demand $1.99 Spot Not offered"""


def test_lyceum_on_demand_and_optional_spot():
    rows = lyceum.extract_rows(LYCEUM_TEXT)
    assert [(r["name"], r["on_demand"], r["spot"]) for r in rows] == [
        ("NVIDIA H100", "4.69", "2.39"),
        ("NVIDIA L40S", "1.99", None),
    ]
    offers = lyceum.Lyceum().parse(Fetched("u", rows))
    assert [(o.sku, o.pricing_model) for o in offers] == [
        ("NVIDIA H100", "on_demand"),
        ("NVIDIA H100", "spot"),
        ("NVIDIA L40S", "on_demand"),
    ]


SEEWEB_PAGE = """<div id="gpu1" class="cardType"><h2><span>CLOUD GPU</span>
<span class="cardname">NVIDIA H100</span></h2></div>
<div id="gpu9" class="cardType featured"><h2><span class="cardname">NVIDIA H200</span></h2></div>
<div id="gpu11" class="cardType"><h2><span class="cardname">NVIDIA B200</span></h2></div>"""
SEEWEB_BUNDLE = 'x={"CLOUDECS7H":0.63,"CLOUDGPU1H":1.89,"CLOUDGPU9H":2.6,"CLOUDGPU10H":1.25}'


def test_seeweb_joins_cards_with_per_gpu_rates():
    recs = seeweb.extract(SEEWEB_PAGE, SEEWEB_BUNDLE)
    assert recs == [
        {"card": "gpu1", "name": "NVIDIA H100", "rate_eur": "1.89"},
        {"card": "gpu9", "name": "NVIDIA H200", "rate_eur": "2.6"},
        {"card": "gpu11", "name": "NVIDIA B200", "rate_eur": None},
    ]
    f = Fetched("u", recs)
    offers = seeweb.Seeweb().parse(f)
    assert [(o.gpu_raw, o.per_gpu_hour(), o.currency) for o in offers] == [
        ("NVIDIA H100", Decimal("1.89"), "EUR"),
        ("NVIDIA H200", Decimal("2.6"), "EUR"),
    ]
    assert any("gpu11" in p for p in f.problems)  # a card without a rate is reported


# ---- UpCloud, IONOS, Leafcloud, Koyeb (added 22 Oct 2026, evening)

from compeu import registry  # noqa: E402
from compeu.collectors import ionos, koyeb, leafcloud, upcloud  # noqa: E402

UPCLOUD_PAGE = """<h3>GPU Servers with NVIDIA H100 GPUs</h3><table><tr><th>GPU</th>
<th>CPU cores</th>
<th>RAM</th>
<th>Spot Price</th>
<th>Price</th></tr>
<tr><td>1 x NVIDIA H100</td>
<td>12 cores</td>
<td>240 GB</td>
<td>€1.79/h</td>
<td>€2.17/h</td></tr>
<tr><td>8 x NVIDIA H100</td>
<td>96 cores</td>
<td>1920 GB</td>
<td>€14.32/h</td>
<td>€17.36/h</td></tr>
<tr><td>1 x NVIDIA RTX PRO 6000</td>
<td>16 cores</td>
<td>80 GB</td>
<td>€0.87/h</td>
<td>€1.65/h</td></tr>
</table><p>Monthly from €1,814/mo</p>"""


def test_upcloud_reads_spot_and_regular_prices():
    rows = upcloud.extract_rows(UPCLOUD_PAGE)
    assert [(r["gpus"], r["gpu"], r["price"]) for r in rows] == [
        (1, "NVIDIA H100", "2.17"),
        (8, "NVIDIA H100", "17.36"),
        (1, "NVIDIA RTX PRO 6000", "1.65"),
    ]
    offers = upcloud.UpCloud().parse(Fetched("u", rows))
    od = [o for o in offers if o.pricing_model == "on_demand"]
    assert [str(o.per_gpu_hour()) for o in od] == ["2.17", "2.17", "1.65"]
    assert {o.pricing_model for o in offers} == {"on_demand", "spot"}
    assert all(o.currency == "EUR" and o.region == "catalogue" for o in offers)


IONOS_PAGE = """<table><tr><th>GPU VM-Typ</th>
<th>GPU-Typ</th>
<th>Anzahl GPUs</th>
<th>Dedizierte vCPUs</th>
<th>RAM</th>
<th>Speicher</th>
<th>Preis pro Stunde (Pay-as-you-go)</th></tr>
<tr><td>H200 – S</td>
<td>H200 PCIe</td>
<td>1</td>
<td>15</td>
<td>267 GiB</td>
<td>1.024 GB</td>
<td>3 €</td></tr>
<tr><td>H200 – XL</td>
<td>H200 PCIe</td>
<td>8</td>
<td>127</td>
<td>2.136 GiB</td>
<td>4.096 GB</td>
<td>24 €</td></tr>
</table>"""


def test_ionos_reads_german_table():
    rows = ionos.extract_rows(IONOS_PAGE)
    assert [(r["type"], r["gpus"], r["price"]) for r in rows] == [
        ("H200 – S", 1, "3"),
        ("H200 – XL", 8, "24"),
    ]
    offers = ionos.Ionos().parse(Fetched("u", rows))
    assert [str(o.per_gpu_hour()) for o in offers] == ["3", "3"]
    assert offers[0].gpu_raw == "H200 PCIe" and offers[0].currency == "EUR"


LEAF_PAGE = """<table><tr><th>Provider</th>
<th>RTX 6000 (96GB)</th>
<th>H100 (80GB)</th>
<th>A100 (80GB)</th>
<th>A30 (24GB)</th>
<th>Region</th></tr>
<tr><td>RunPod Region-uniform pricing</td>
<td>$2.09</td>
<td>$2.89</td>
<td>$1.59</td>
<td>Unavailable</td>
<td>Secure Cloud (EU DCs)</td></tr>
<tr><td>Leafcloud Full VM included</td>
<td>€1.99</td>
<td>€3.15</td>
<td>€1.61</td>
<td>€0.60</td>
<td>ams-1 (Amsterdam)</td></tr>
</table>"""


def test_leafcloud_takes_only_its_own_row():
    rows = leafcloud.extract_rows(LEAF_PAGE)
    assert [(r["gpu"], r["price"]) for r in rows] == [
        ("NVIDIA RTX 6000", "1.99"),
        ("NVIDIA H100", "3.15"),
        ("NVIDIA A100", "1.61"),
        ("NVIDIA A30", "0.60"),
    ]
    offers = leafcloud.Leafcloud().parse(Fetched("u", rows))
    assert all(o.country == "NL" and o.region == "ams-1" and o.gpu_count == 1 for o in offers)
    assert (
        registry.normalize_gpu(offers[0].gpu_raw).model == "rtx-pro-6000"
    )  # 96 GB: the Blackwell card


def test_leafcloud_refuses_a_misaligned_table():
    broken = LEAF_PAGE.replace("<td>€0.60</td>", "")
    assert leafcloud.extract_rows(broken) == []


KOYEB = [
    {
        "id": "gpu-nvidia-rtx-4000-sff-ada",
        "description": "NVIDIA RTX 4000 SFF Ada",
        "type": "gpu",
        "price_hourly": "0.50",
        "regions": ["fra", "eu"],
        "gpu": {"count": 1, "brand": "nvidia"},
    },
    {
        "id": "2-gpu-nvidia-h100",
        "description": "2x NVIDIA H100",
        "type": "gpu",
        "price_hourly": "5.0",
        "regions": ["na"],
        "gpu": {"count": 2, "brand": "nvidia"},
    },
    {
        "id": "gpu-nvidia-b200",
        "description": "NVIDIA B200",
        "type": "gpu",
        "price_hourly": "5.50",
        "regions": [],
        "gpu": {"count": 1, "brand": "nvidia"},
    },
]


def test_koyeb_keeps_regions_and_skips_restricted():
    f = Fetched("u", KOYEB)
    offers = koyeb.Koyeb().parse(f)
    assert [(o.sku, o.region, o.country) for o in offers] == [
        ("gpu-nvidia-rtx-4000-sff-ada", "fra", "DE"),
        ("2-gpu-nvidia-h100", "na", "US"),
    ]
    assert str(offers[1].per_gpu_hour()) == "2.5"
    assert any("restricted" in p for p in f.problems)
