"""Transparent, bounded district context for Maharashtra crop ranking.

The underlying classifier has no district feature. This module applies a small
regional-practice prior after inference; it does not claim to estimate yield or
agronomic suitability.
"""

from __future__ import annotations

DISTRICT_REGIONS = {
    "Vidarbha": ["Akola", "Amravati", "Bhandara", "Buldhana", "Chandrapur", "Gadchiroli", "Gondia", "Nagpur", "Wardha", "Washim", "Yavatmal"],
    "Marathwada": ["Beed", "Dharashiv", "Hingoli", "Jalna", "Latur", "Nanded", "Parbhani", "Chhatrapati Sambhajinagar"],
    "Western Maharashtra": ["Ahmednagar", "Kolhapur", "Pune", "Sangli", "Satara", "Solapur"],
    "Khandesh / North Maharashtra": ["Dhule", "Jalgaon", "Nandurbar", "Nashik"],
    "Konkan": ["Mumbai City", "Mumbai Suburban", "Palghar", "Raigad", "Ratnagiri", "Sindhudurg", "Thane"],
}

# Crop labels named in ICAR's regional Maharashtra Kharif advisory (2025),
# mapped to this app's classifier vocabulary where possible. This is an
# advisory-coverage prior, not measured district crop prevalence.
KHARIF_ADVISORY_CROPS = {
    "Vidarbha": {"rice", "maize", "cotton", "soybean", "pigeonpeas", "mungbean", "blackgram", "sorghum"},
    "Marathwada": {"maize", "cotton", "pigeonpeas", "soybean", "sorghum"},
    "Western Maharashtra": {"rice", "maize", "cotton", "soybean", "chickpea", "sorghum"},
    "Khandesh / North Maharashtra": {"cotton", "soybean", "maize", "pigeonpeas", "sorghum"},
    "Konkan": {"rice", "maize", "mungbean", "blackgram"},
}

DISTRICTS = sorted(district for districts in DISTRICT_REGIONS.values() for district in districts)
REGION_BY_DISTRICT = {district: region for region, districts in DISTRICT_REGIONS.items() for district in districts}


def is_in_regional_kharif_advisory(crop: str, district: str) -> bool:
    """Whether the crop label is covered by the district region's advisory list."""
    region = REGION_BY_DISTRICT[district]
    normalized_crop = str(crop).strip().lower().replace(" ", "_")
    return normalized_crop in KHARIF_ADVISORY_CROPS[region]


def rank_with_district_prior(
    labels: list[str], model_scores, district: str, season: str, strength: float = 0.08
):
    """Apply the dated advisory prior only for its supported season."""
    region = REGION_BY_DISTRICT[district]
    if len(labels) != len(model_scores):
        raise ValueError("The crop labels and model scores must have the same length.")
    strength = max(0.0, min(float(strength), 0.15))
    baseline = [max(0.0, float(score)) for score in model_scores]
    if season != "Kharif" or strength <= 0:
        total = sum(baseline)
        return region, baseline, [score / total for score in baseline] if total else baseline, False

    crops = KHARIF_ADVISORY_CROPS[region]
    factors = [1.0 + strength if str(label).strip().lower().replace(" ", "_") in crops else 1.0 - strength
               for label in labels]
    adjusted = [score * factor for score, factor in zip(baseline, factors)]
    total = sum(adjusted)
    normalized = [score / total for score in adjusted] if total else [0.0 for _ in adjusted]
    return region, baseline, normalized, True
