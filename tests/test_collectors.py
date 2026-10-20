"""Parsers tested on trimmed copies of real responses (October 2026)."""

from decimal import Decimal

from ceresio.collectors import aws, azure, exoscale, hetzner, ovhcloud, runpod, scaleway, verda
from ceresio.collectors.base import Fetched


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
<div class="overflow-hidden product-wrapper gpu-wrapper swiper-slide product-1 ">
  <div class="d-flex flex-column product-text-name">
            GEX131
        </div>
  <span class="visually-hidden">€ 1,499.00 per month, excl. VAT</span>
  <ho-price-container class="product-pph-price" product-key="ROBOT_1" price-type="hourly"
     decimals="4"><span class="visually-hidden">€ 2.4022 per hour, excl. VAT</span>
  </ho-price-container>
  <div>+ € 1,499.00 one-time setup fee, excl. VAT</div>
</div>
<div class="gpu-information-grid">
  <div class="item-header-a grid-header-text"><div class="grid-header-name">
            GEX131
        </div> CPU</div>
  <div class="item-d grid-data-text">
        NVIDIA RTX PRO™ 6000 Blackwell Max-Q
    </div>
</div>
"""


def test_hetzner_reads_structured_prices():
    recs = hetzner.extract(HETZNER_PAGE)
    assert recs == [
        {
            "name": "GEX131",
            "gpu": "NVIDIA RTX PRO™ 6000 Blackwell Max-Q",
            "hourly_eur": "2.4022",
            "monthly_eur": "1499.00",
            "setup_fee_eur": "1499.00",
        }
    ]
    [o] = hetzner.Hetzner().parse(Fetched("u", recs))
    assert o.price == Decimal("2.4022") and o.extra["setup_fee_eur"] == "1499.00"


def test_hetzner_changed_markup_records_nothing():
    f = Fetched("u", hetzner.extract("<html>redesigned page</html>"))
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
