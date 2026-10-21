"""Parsers tested on trimmed copies of real responses (October 2026)."""

from decimal import Decimal

from compeu.collectors import aws, azure, exoscale, hetzner, ovhcloud, runpod, scaleway, verda
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
