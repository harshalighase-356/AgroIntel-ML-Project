"""Transparent comparison with reported district crop area records."""

from __future__ import annotations

import re

import pandas as pd


REQUIRED_COLUMNS = {
    "fiscal_year", "district_as_per_source", "crop", "season", "area"
}

# Exact aliases only: a failed match is reported as unavailable, never as zero.
CROP_ALIASES = {
    "rice": {"rice", "paddy"},
    "maize": {"maize", "corn"},
    "chickpea": {"chickpea", "gram", "bengal gram"},
    "kidneybeans": {"kidney bean", "kidney beans", "rajma"},
    "pigeonpeas": {"pigeon pea", "pigeonpeas", "tur", "arhar"},
    "mothbeans": {"moth bean", "moth beans"},
    "mungbean": {"mung bean", "mungbean", "moong", "green gram"},
    "blackgram": {"black gram", "blackgram", "urad"},
    "lentil": {"lentil", "masoor"},
    "pomegranate": {"pomegranate"},
    "banana": {"banana"},
    "mango": {"mango"},
    "grapes": {"grape", "grapes"},
    "watermelon": {"watermelon"},
    "muskmelon": {"muskmelon"},
    "apple": {"apple"},
    "orange": {"orange"},
    "papaya": {"papaya"},
    "coconut": {"coconut"},
    "cotton": {"cotton"},
    "jute": {"jute"},
    "coffee": {"coffee"},
    "sorghum": {"sorghum", "jowar"},
    "millet": {"millet", "bajra", "pearl millet"},
    "sugarcane": {"sugarcane"},
    "soybean": {"soybean", "soya bean"},
    "groundnut": {"groundnut", "peanut"},
    "sunflower": {"sunflower"},
}


def _key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).strip().lower()).strip()


_SOURCE_TO_LABEL = {
    _key(alias): label
    for label, aliases in CROP_ALIASES.items()
    for alias in aliases
}

DISTRICT_ALIASES = {
    "ahmednagar": "ahilyanagar",
    "aurangabad": "chhatrapati sambhajinagar",
}


def _district_key(value: object) -> str:
    key = _key(value)
    return DISTRICT_ALIASES.get(key, key)


def validate_statistics(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize a district-season-crop statistics CSV."""
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError("Missing columns: " + ", ".join(missing))
    clean = frame.copy()
    for column in ("fiscal_year", "district_as_per_source", "crop", "season"):
        clean[column] = clean[column].astype("string").str.strip()
    clean["area"] = pd.to_numeric(clean["area"], errors="coerce")
    clean = clean.dropna(subset=["fiscal_year", "district_as_per_source", "crop", "season", "area"])
    clean = clean[(clean["district_as_per_source"] != "") & (clean["crop"] != "")]
    clean = clean[~clean["district_as_per_source"].str.casefold().isin({"state total", "maharashtra total"})]
    if clean.empty:
        raise ValueError("No usable district crop area rows were found.")
    if (clean["area"] < 0).any():
        raise ValueError("Area values cannot be negative.")
    return clean


def district_season_summary(
    frame: pd.DataFrame, district: str, season: str, year: str | None = None
) -> dict | None:
    """Return the latest observed crop-area records for one district/season."""
    subset = frame[
        frame["district_as_per_source"].map(_district_key).eq(_district_key(district))
        & frame["season"].map(_key).eq(_key(season))
    ].copy()
    if year is not None:
        subset = subset[subset["fiscal_year"].astype(str).eq(str(year))]
    elif not subset.empty:
        year = sorted(subset["fiscal_year"].astype(str).unique())[-1]
        subset = subset[subset["fiscal_year"].astype(str).eq(year)]
    if subset.empty:
        return None
    # Keep raw crop names because source nomenclature can differ from the model.
    grouped = subset.groupby("crop", as_index=False)["area"].sum()
    grouped = grouped.sort_values(["area", "crop"], ascending=[False, True]).reset_index(drop=True)
    total_area = float(grouped["area"].sum())
    rows = []
    for rank, row in enumerate(grouped.itertuples(index=False), start=1):
        rows.append({
            "crop": str(row.crop),
            "area_ha": float(row.area),
            "share": float(row.area) / total_area if total_area > 0 else 0.0,
            "rank": rank,
        })
    return {"year": str(year), "rows": rows, "total_area_ha": total_area}


def compare_suggestion(summary: dict | None, suggested_crop: str) -> dict:
    """Describe support/conflict from recorded area without inferring from absence."""
    label = _key(suggested_crop).replace(" ", "")
    aliases = CROP_ALIASES.get(label)
    if summary is None:
        return {"status": "unavailable", "reason": "No matching district and season records were loaded."}
    if not aliases:
        return {"status": "unmapped", "reason": "This model label has no verified alias in the statistics."}
    alias_keys = {_key(alias) for alias in aliases}
    match = next((row for row in summary["rows"] if _key(row["crop"]) in alias_keys), None)
    if match is None:
        return {"status": "unreported", "reason": "The dataset has no matching crop row for this district and season. Missing rows are not treated as zero area."}
    if match["area_ha"] <= 0:
        return {"status": "zero", "record": match, "reason": "The source explicitly reports zero area for this crop in this year and season."}
    if match["rank"] > 3:
        return {"status": "low_area", "record": match, "reason": "The crop is recorded, but its reported area is below the three largest recorded crops for this district and season."}
    return {"status": "aligned", "record": match, "reason": "The crop appears among the three largest reported crop areas for this district and season."}
