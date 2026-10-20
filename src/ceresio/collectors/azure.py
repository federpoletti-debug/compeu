"""Microsoft Azure: official Retail Prices API (no authentication).

GET https://prices.azure.com/api/retail/prices?$filter=...
Docs: https://learn.microsoft.com/rest/api/cost-management/retail-prices/azure-retail-prices
One query per European region for N-series (GPU) virtual machines, Linux,
pay-as-you-go ("Consumption") and spot. Prices in USD per hour.

The API names the VM size but not its GPUs, so GPU model and count come from the
SKU table below (Azure VM size documentation). A size not in the table is
reported as unmapped and left out of the index; it is never guessed.
"""

from __future__ import annotations

import re

import requests

from .. import registry
from ..http import TIMEOUT
from ..util import dec
from .base import Fetched, Offer

URL = "https://prices.azure.com/api/retail/prices"
API_VERSION = "2023-01-01-preview"

# armSkuName -> (GPU name, GPUs per VM). Fractional-GPU sizes (NVads A10 v5 below
# 36 vCPU, NGads V620) are left out on purpose: the index counts whole GPUs.
SKU_GPUS: dict[str, tuple[str, int]] = {
    "Standard_NC40ads_H100_v5": ("H100 NVL", 1),
    "Standard_NC80adis_H100_v5": ("H100 NVL", 2),
    "Standard_NCC40ads_H100_v5": ("H100 NVL confidential", 1),
    "Standard_ND96isr_H100_v5": ("H100 SXM", 8),
    "Standard_ND96is_H100_v5": ("H100 SXM", 8),
    "Standard_ND96isrf_H100_v5": ("H100 SXM", 8),
    "Standard_ND96isf_H100_v5": ("H100 SXM", 8),
    "Standard_ND96is_flex_H100_v5": ("H100 SXM", 8),
    "Standard_ND96is_noIB_H100_v5": ("H100 SXM", 8),
    "Standard_ND96isr_H200_v5": ("H200 SXM", 8),
    "Standard_ND128isr_GB200_v6": ("GB200", 4),
    "Standard_ND128isr_NDR_GB200_v6": ("GB200", 4),
    "Standard_ND96isr_MI300X_v5": ("MI300X", 8),
    "Standard_ND96is_MI300X_v5": ("MI300X", 8),
    "Standard_ND96asr_v4": ("A100 40GB SXM", 8),
    "Standard_ND96asr_A100_v4": ("A100 40GB SXM", 8),
    "Standard_ND96ams_A100_v4": ("A100 80GB SXM", 8),
    "Standard_ND40rs_v2": ("V100 SXM", 8),
    "Standard_ND40s_v2": ("V100 SXM", 8),
    "Standard_ND96amsr_A100_v4": ("A100 80GB SXM", 8),
    "Standard_NC24ads_A100_v4": ("A100 80GB PCIe", 1),
    "Standard_NC48ads_A100_v4": ("A100 80GB PCIe", 2),
    "Standard_NC96ads_A100_v4": ("A100 80GB PCIe", 4),
    "Standard_NC4as_T4_v3": ("T4", 1),
    "Standard_NC8as_T4_v3": ("T4", 1),
    "Standard_NC16as_T4_v3": ("T4", 1),
    "Standard_NC64as_T4_v3": ("T4", 4),
    "Standard_NV36ads_A10_v5": ("A10", 1),
    "Standard_NV36adms_A10_v5": ("A10", 1),
    "Standard_NV72ads_A10_v5": ("A10", 2),
}
GPU_SKU = re.compile(r"^Standard_N[CDV]")
# Sizes with a fraction of a GPU, or retired graphics GPUs: known, deliberately skipped.
FRACTIONAL_OR_LEGACY = re.compile(
    r"^Standard_(NV(6|12|18)ad[m]?s_A10_v5|NV\d+as_v4|NV\d+s_v3|NV?C?\d+r?_Promo|NG\d+|NV\d+$|NC\d+r?$|NC\d+r?s_v[23])"
)


class Azure:
    provider = "azure"
    version = 1
    method = "api"

    def regions(self) -> list[str]:
        return [s["id"] for s in registry.providers()["azure"]["sites"]]

    def fetch(self, http: requests.Session) -> Fetched:
        records, problems = [], []
        for region in self.regions():
            flt = (
                "serviceName eq 'Virtual Machines' and priceType eq 'Consumption' "
                f"and armRegionName eq '{region}' and startswith(armSkuName, 'Standard_N')"
            )
            url, params = URL, {"api-version": API_VERSION, "$filter": flt}
            while url:
                r = http.get(url, params=params, timeout=TIMEOUT)
                r.raise_for_status()
                data = r.json()
                records += [i for i in data.get("Items", []) if _keep(i)]
                url, params = data.get("NextPageLink"), None
        return Fetched(source_url=URL, records=records, problems=problems)

    def parse(self, fetched: Fetched) -> list[Offer]:
        offers, unmapped = [], set()
        for i in fetched.records:
            sku = i["armSkuName"]
            if sku not in SKU_GPUS:
                if not FRACTIONAL_OR_LEGACY.match(sku):
                    unmapped.add(sku)
                continue
            gpu, count = SKU_GPUS[sku]
            offers.append(
                Offer(
                    sku=sku,
                    gpu_raw=gpu,
                    gpu_count=count,
                    price=dec(i["retailPrice"]),
                    currency=i["currencyCode"],
                    unit="hour",
                    pricing_model="spot" if "Spot" in i["meterName"] else "on_demand",
                    region=i["armRegionName"],
                    country=registry.site_country("azure", i["armRegionName"]),
                )
            )
        fetched.problems += [f"{s}: VM size not in the GPU table" for s in sorted(unmapped)]
        return offers


def _keep(item: dict) -> bool:
    """Linux pay-as-you-go and spot hourly prices of GPU sizes; no Windows, no low priority."""
    return (
        bool(GPU_SKU.match(item.get("armSkuName", "")))
        and "Windows" not in item.get("productName", "")
        and "Low Priority" not in item.get("meterName", "")
        and item.get("unitOfMeasure") == "1 Hour"
        and item.get("type") == "Consumption"
        and float(item.get("retailPrice", 0)) > 0
    )
