"""Rule-based soil report framework adapted from the reference analyzer."""

from __future__ import annotations


SOIL_TYPES = [
    "Black Cotton Soil", "Laterite Soil", "Alluvial", "Coastal Soil",
    "Coastal Alluvial Soil", "Red Loamy Soil", "Red & Sandy Soil",
    "Red & Yellow Soil", "Black + Laterite Mixed",
]


def analyze_soil_report(values: dict) -> dict:
    """Apply the reference project's fixed rules and return a structured report."""
    findings: list[str] = []
    flagged_measurements: list[str] = []
    fertilizer: list[str] = []
    irrigation: list[str] = []
    soil_advice: list[str] = []

    n, p, k = values["nitrogen"], values["phosphorus"], values["potassium"]
    if n < 50:
        flagged_measurements.append("Nitrogen (N)")
        findings.append("Nitrogen is below the reference analyzer's threshold (<50).")
        fertilizer.append("Check the laboratory recommendation before applying a nitrogen source such as urea or ammonium sulphate.")
    elif n > 120:
        flagged_measurements.append("Nitrogen (N)")
        findings.append("Nitrogen is above the reference analyzer's threshold (>120).")
        fertilizer.append("Avoid adding nitrogen until the crop-specific soil report is reviewed.")
    else:
        findings.append("Nitrogen is within the reference analyzer's band (50–120).")

    if p < 40:
        flagged_measurements.append("Phosphorus (P)")
        findings.append("Phosphorus is below the reference analyzer's threshold (<40).")
        fertilizer.append("Check the laboratory recommendation before applying a phosphorus source such as DAP or SSP.")
    elif p > 80:
        flagged_measurements.append("Phosphorus (P)")
        findings.append("Phosphorus is above the reference analyzer's threshold (>80).")
        fertilizer.append("Avoid additional phosphorus until the crop-specific soil report is reviewed.")
    else:
        findings.append("Phosphorus is within the reference analyzer's band (40–80).")

    if k < 40:
        flagged_measurements.append("Potassium (K)")
        findings.append("Potassium is below the reference analyzer's threshold (<40).")
        fertilizer.append("Check the laboratory recommendation before applying potash/MOP.")
    elif k > 100:
        flagged_measurements.append("Potassium (K)")
        findings.append("Potassium is above the reference analyzer's threshold (>100).")
        fertilizer.append("Avoid additional potassium until the crop-specific soil report is reviewed.")
    else:
        findings.append("Potassium is within the reference analyzer's band (40–100).")

    ph = values["ph"]
    if ph < 6:
        flagged_measurements.append("Soil pH")
        findings.append("Soil pH is acidic (<6).")
        fertilizer.append("Ask the local soil laboratory for a crop-specific lime recommendation; this app does not calculate an amendment dose.")
    elif ph > 7.5:
        flagged_measurements.append("Soil pH")
        findings.append("Soil pH is alkaline (>7.5).")
        fertilizer.append("Ask the local soil laboratory for a crop-specific amendment recommendation; this app does not calculate a gypsum dose.")
    else:
        findings.append("Soil pH is between 6 and 7.5.")

    moisture = values["moisture"]
    if moisture < 20:
        flagged_measurements.append("Soil moisture")
        findings.append("Soil moisture is below 20%; the crop may face water stress.")
        irrigation.append("Review irrigation timing and the crop's water requirement.")
    elif moisture > 60:
        flagged_measurements.append("Soil moisture")
        findings.append("Soil moisture is above 60%; check for waterlogging and drainage issues.")
        irrigation.append("Check field drainage and delay irrigation if the crop and soil conditions allow.")
    else:
        findings.append("Soil moisture is within the reference analyzer's 20–60% band.")
        irrigation.append("Review the current irrigation schedule against crop stage and local weather.")

    organic_carbon = values["organic_carbon"]
    if organic_carbon < 0.5:
        flagged_measurements.append("Organic carbon")
        findings.append("Organic carbon is below 0.5%.")
        fertilizer.append("Consider organic matter options such as farmyard manure or compost, guided by local recommendations.")
    elif organic_carbon > 1.5:
        flagged_measurements.append("Organic carbon")
        findings.append("Organic carbon is above 1.5% in this rule set.")
    else:
        findings.append("Organic carbon is within the reference analyzer's 0.5–1.5% band.")

    if values["ec"] > 1:
        flagged_measurements.append("Electrical conductivity (EC)")
        findings.append("Electrical conductivity is above 1 dS/m; salinity may need review.")
        soil_advice.append("Review irrigation water quality and drainage with a local soil specialist.")
    else:
        findings.append("Electrical conductivity is at or below 1 dS/m in this rule set.")

    if values["zinc"] < 0.6:
        flagged_measurements.append("Zinc")
        findings.append("Zinc is below 0.6 ppm in this rule set.")
        fertilizer.append("Use the lab's crop-specific zinc recommendation; do not infer a zinc-sulphate dose from this flag.")
    else:
        findings.append("Zinc is at or above 0.6 ppm in this rule set.")

    if values["iron"] < 4.5:
        flagged_measurements.append("Iron")
        findings.append("Iron is below 4.5 ppm in this rule set.")
        fertilizer.append("Confirm iron deficiency and the treatment with a soil or plant-tissue laboratory.")
    else:
        findings.append("Iron is at or above 4.5 ppm in this rule set.")

    soil_type = values["soil_type"]
    soil_advice.append({
        "Black Cotton Soil": "This soil can retain water; monitor drainage and avoid unnecessary irrigation.",
        "Laterite Soil": "Review organic matter and nutrient management using local soil guidance.",
        "Red & Sandy Soil": "Monitor water retention and drainage; use local advice for organic matter management.",
        "Coastal Soil": "Monitor salinity and drainage, especially where irrigation water quality is a concern.",
        "Coastal Alluvial Soil": "Monitor salinity and drainage, especially where irrigation water quality is a concern.",
        "Alluvial": "Use soil-test results and crop guidance to maintain balanced nutrient management.",
    }.get(soil_type, "Use soil-test results and local recommendations for this soil type."))

    flag_count = len(flagged_measurements)
    check_count = 9
    summary = (
        f"No numeric measurements fell outside the {check_count} reference bands."
        if flag_count == 0
        else f"{flag_count} of {check_count} numeric measurements fell outside the reference bands; review with the soil laboratory or local KVK."
    )
    return {
        "values": values,
        "flag_count": flag_count,
        "check_count": check_count,
        "flagged_measurements": flagged_measurements,
        "findings": findings,
        "fertilizer_notes": fertilizer or ["No nutrient flag from this rule set; continue to follow the crop-specific soil report."],
        "irrigation_notes": irrigation,
        "soil_notes": soil_advice,
        "summary": summary,
        "limitations": "Rule-based screening copied from the reference framework. Thresholds are not crop-, region-, or lab-method calibrated and are not a fertilizer prescription.",
    }
