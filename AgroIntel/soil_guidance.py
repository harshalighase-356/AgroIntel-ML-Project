"""Source-backed Maharashtra crop nutrient guidance.

Only crop, region, and production contexts with a published recommendation are
included. Soil ratings must come from the farmer's lab/Soil Health Card; this
module never infers a nutrient rating from the crop recommendation dataset.
"""

from __future__ import annotations


GUIDANCE = [
    {
        "crop": "cotton",
        "region": "Vidarbha · rainfed hybrid cotton",
        "rates": {"N": 50, "P₂O₅": 25, "K₂O": 25},
        "context": "PDKV recommends this rate for hybrid cotton under rainfed conditions. Confirm variety and planting system with the local KVK.",
        "source": "PDKV Akola · Cotton fertilizer management",
        "url": "https://www.pdkv.ac.in/?page_id=4211",
    },
    {
        "crop": "rice",
        "region": "Eastern Vidarbha · medium soil",
        "rates": {"N": 125, "P₂O₅": 62.5, "K₂O": 62.5},
        "context": "PDKV lists this fertilizer dose for rice on medium soil in Eastern Vidarbha.",
        "source": "PDKV Akola · Department of Soil Science",
        "url": "https://www.pdkv.ac.in/?page_id=3297",
    },
    {
        "crop": "wheat",
        "region": "Western Maharashtra · plain zone",
        "rates": {"N": 120, "P₂O₅": 60, "K₂O": 40},
        "context": "PDKV lists this dose with 10 t FYM/ha for wheat in iron-deficient soils of the Western Maharashtra plain zone. The iron amendment itself is not calculated here.",
        "source": "PDKV Akola · AICRP on Micro and Secondary Nutrients",
        "url": "https://www.pdkv.ac.in/?page_id=4742",
    },
    {
        "crop": "chickpea",
        "region": "Maharashtra · medium-deep black soil",
        "rates": {"N": 20, "P₂O₅": 50, "K₂O": 30},
        "context": "PDKV lists this fertilizer dose for chickpea on zinc-deficient medium-deep black soil. Do not apply the linked zinc treatment unless the lab confirms deficiency.",
        "source": "PDKV Akola · AICRP on Micro and Secondary Nutrients",
        "url": "https://www.pdkv.ac.in/?page_id=4742",
    },
    {
        "crop": "rabi sorghum",
        "region": "Western Maharashtra · medium-deep black soil",
        "rates": {"N": 80, "P₂O₅": 40, "K₂O": 40},
        "context": "PDKV lists this dose with 5 t FYM/ha for rabi sorghum in zinc-deficient medium-deep black soils of Western Maharashtra. The zinc treatment is not calculated here.",
        "source": "PDKV Akola · AICRP on Micro and Secondary Nutrients",
        "url": "https://www.pdkv.ac.in/?page_id=4742",
    },
]

OTHER_REGION = "Other / outside listed source context"
REGIONS = list(dict.fromkeys([*(item["region"] for item in GUIDANCE), OTHER_REGION]))
CROPS_BY_REGION = {
    region: [item["crop"] for item in GUIDANCE if item["region"] == region]
    for region in REGIONS
}
CROPS_BY_REGION[OTHER_REGION] = sorted({item["crop"] for item in GUIDANCE})


def get_guidance(crop: str, region: str) -> dict | None:
    """Return the exact published package for a crop-region pair, if present."""
    return next(
        (item for item in GUIDANCE if item["crop"] == crop and item["region"] == region),
        None,
    )


