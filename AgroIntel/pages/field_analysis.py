from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

from app_storage import append_history, read_history
from district_context import (
    DISTRICTS,
    KHARIF_ADVISORY_CROPS,
    REGION_BY_DISTRICT,
    rank_with_district_prior,
)
from field_report import build_field_report_pdf
from modeling import FEATURES
from district_statistics import compare_suggestion, district_season_summary, validate_statistics

st.markdown('<div id="analysis-start"></div>', unsafe_allow_html=True)
context = st.session_state["_agrointel_context"]
results = context["results"]
data = context["data"]
dataset_source = context["dataset_source"]
raw_csv = context["raw_csv"]
result = st.session_state.get("recommendation_result")

stats_path = Path(__file__).resolve().parents[1] / "data" / "maharashtra_district_crop_stats.csv"
with st.expander("Local crop records (district × crop × season)", expanded=False):
    stats_upload = st.file_uploader(
        "Load Maharashtra district crop statistics CSV",
        type=["csv"],
        key="district_crop_stats_upload",
        help="Expected fields: fiscal_year, district_as_per_source, crop, season, area (hectares).",
    )
    demo_path = Path(__file__).resolve().parents[1] / "examples" / "sample_district_crop_stats_demo.csv"
    if demo_path.exists():
        st.download_button(
            "Download synthetic demo CSV",
            data=demo_path.read_bytes(),
            file_name=demo_path.name,
            mime="text/csv",
            help="Contains invented values only; upload it to exercise the comparison warning, not for farming decisions.",
        )
    stats_bytes = stats_upload.getvalue() if stats_upload else (stats_path.read_bytes() if stats_path.exists() else None)
    stats_frame = None
    stats_name = None
    stats_is_demo = False
    if stats_bytes:
        try:
            stats_frame = validate_statistics(pd.read_csv(pd.io.common.BytesIO(stats_bytes)))
            stats_name = stats_upload.name if stats_upload else stats_path.name
            note_column = stats_frame.get("note", pd.Series("", index=stats_frame.index)).astype("string")
            stats_is_demo = bool(note_column.str.contains("synthetic demo", case=False, na=False).any())
            st.caption(f"Loaded {len(stats_frame):,} district crop records from {stats_name}.")
            if stats_is_demo:
                st.warning("Synthetic demo records are active. The displayed areas are invented for software demonstration and must not guide crop decisions.")
        except (ValueError, pd.errors.ParserError, UnicodeDecodeError) as error:
            st.error(f"Could not read district crop statistics: {error}")
    else:
        st.info("No district statistics are loaded. Upload the official district × season × crop CSV to compare recommendations with observed local crop area.")
    if stats_frame is not None:
        st.caption("Load the statistics before submitting the field analysis so the selected suggestion is checked against the local records.")
    st.caption("Suggested source: [Ministry of Agriculture district, season and crop-wise area statistics for Maharashtra](https://dataful.in/datasets/5632/). Area describes recorded cultivation, not crop suitability. Omitted records are treated as unknown, never as zero.")

st.subheader("Explore a field")
st.write("Enter soil and local weather values to get a crop suggestion and a quick soil snapshot.")
chosen = st.selectbox("Recommendation model", ["Auto Select Best Model", *results.models.keys()])
selected_model = results.metrics.iloc[0]["Model"] if chosen == "Auto Select Best Model" else chosen
st.caption(f"Selected model: **{selected_model}**")
with st.form("recommendation"):
    field_col, district_col = st.columns(2)
    field_name = field_col.text_input("Field name or ID", placeholder="e.g. North field")
    district = district_col.selectbox("District (Maharashtra)", DISTRICTS, index=DISTRICTS.index("Pune"))
    season_col, influence_col = st.columns(2)
    season = season_col.selectbox("Planned growing season", ["Kharif", "Rabi", "Summer"])
    influence = influence_col.slider("District context influence (%)", 0, 15, 8, 1,
                                     help="This only scales the dated regional Kharif advisory prior. It cannot make the model district-trained.")
    st.caption("District context is an advisory-based regional nudge for Kharif. Rabi and Summer use the model ranking without a district adjustment because a matching validated crop prior is not configured.")
    st.markdown("**Crop model inputs**")
    st.caption("Enter values in the same format as the training dataset. These NPK numbers are model inputs, not soil-lab deficiency ratings.")
    soil_columns = st.columns(4)
    values = {}
    limits = {"N": (0, 300), "P": (0, 300), "K": (0, 300), "temperature": (-10, 60),
              "humidity": (0, 100), "ph": (0, 14), "rainfall": (0, 5000)}
    defaults = {"N": 90, "P": 42, "K": 43, "temperature": 25, "humidity": 80, "ph": 6.5, "rainfall": 200}
    input_labels = {
        "N": "Nitrogen (N)", "P": "Phosphorus (P)", "K": "Potassium (K)", "ph": "Soil pH",
        "temperature": "Temperature (°C)", "humidity": "Humidity (%)", "rainfall": "Rainfall (mm)",
    }
    for index, feature in enumerate(("N", "P", "K", "ph")):
        lo, hi = limits[feature]
        values[feature] = soil_columns[index].number_input(input_labels[feature], min_value=float(lo), max_value=float(hi), value=float(defaults[feature]))
    st.markdown("**Local climate**")
    climate_columns = st.columns(3)
    for index, feature in enumerate(("temperature", "humidity", "rainfall")):
        lo, hi = limits[feature]
        values[feature] = climate_columns[index].number_input(input_labels[feature], min_value=float(lo), max_value=float(hi), value=float(defaults[feature]))
    submitted = st.form_submit_button("Analyze soil & recommend crop", type="primary", width="stretch")

with st.expander("How district context affects the ranking"):
    st.write(f"{district} is mapped to the **{REGION_BY_DISTRICT[district]}** advisory region. For Kharif only, crops named in that region's ICAR advisory receive a relative multiplier of 1 + influence; other model labels receive 1 − influence. Scores are then normalized for ranking. Set influence to 0% for the classifier-only ranking.")
    st.caption("This is regional advisory coverage, not a measured crop-area share for the selected district. The available advisory is from 2025 and applies to Kharif; it does not replace current district or KVK guidance.")
    st.markdown("Source: [ICAR Kharif Agro-Advisory for Farmers 2025](https://www.icar.gov.in/sites/default/files/Circulars/ICAR%20En-Kharif%20Agro-Advisories%20for%20Farmers%202025.pdf)")

if submitted:
    input_row = pd.DataFrame([values], columns=FEATURES)
    estimator = results.models[selected_model]
    raw_prediction_index = int(estimator.predict(input_row)[0])
    model_scores = estimator.predict_proba(input_row)[0]
    district_region, original_scores, adjusted_scores, context_applied = rank_with_district_prior(
        results.labels, model_scores, district, season, influence / 100
    )
    prediction_index = max(range(len(adjusted_scores)), key=adjusted_scores.__getitem__)
    normalized_crop = results.labels[prediction_index].strip().lower().replace(" ", "_")
    district_crop_in_advisory = normalized_crop in KHARIF_ADVISORY_CROPS[district_region]
    local_stats = district_season_summary(stats_frame, district, season) if stats_frame is not None else None
    local_comparison = compare_suggestion(local_stats, results.labels[prediction_index])
    alternative_indices = [int(index) for index in sorted(range(len(adjusted_scores)), key=adjusted_scores.__getitem__, reverse=True)
                           if int(index) != prediction_index][:3]
    st.session_state["recommendation_result"] = {
        "crop": results.labels[prediction_index],
        "model_crop": results.labels[raw_prediction_index],
        "model": selected_model,
        "field_name": field_name.strip() or "Unnamed field",
        "district": district,
        "district_region": district_region,
        "season": season,
        "district_context_applied": context_applied,
        "district_context_influence": influence if context_applied else 0,
        "district_crop_in_advisory": district_crop_in_advisory,
        "local_crop_statistics": local_stats,
        "local_crop_comparison": local_comparison,
        "local_crop_statistics_source": stats_name,
        "local_crop_statistics_is_demo": stats_is_demo,
        "district_adjusted_score": adjusted_scores[prediction_index],
        "values": values,
        "alternatives": [
            {"Crop option": results.labels[index].replace("_", " ").title(),
             "District-adjusted rank score": f"{adjusted_scores[index]:.1%}",
             "Original model score": f"{original_scores[index]:.1%}"}
            for index in alternative_indices
        ],
        "dataset": {
            "source": dataset_source,
            "sha256": hashlib.sha256(raw_csv).hexdigest(),
            "rows": results.data_summary["usable_rows"],
            "crop_classes": results.data_summary["crop_classes"],
            "training_split": "Stratified 80/20, random seed 42",
        },
        "model_metrics": results.metrics.set_index("Model").loc[selected_model].to_dict(),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "out_of_range": [feature for feature, value in values.items()
                         if value < results.data_summary["ranges"][feature][0]
                         or value > results.data_summary["ranges"][feature][1]],
    }

result = st.session_state.get("recommendation_result")
if result and not {"district_region", "season", "district_context_applied", "district_crop_in_advisory"}.issubset(result):
    # Discard results created by an earlier app version before district ranking.
    st.session_state.pop("recommendation_result", None)
    result = None
if result:
    st.divider()
    st.markdown("#### Suggested crop")
    st.success(f"🌾 **{result['crop'].replace('_', ' ').title()}**")
    st.caption(f"{result['district']} district · {result['district_region']} context · {result['model']} model")
    if result["district_context_applied"]:
        st.info(f"The model's unadjusted top crop was **{result['model_crop'].replace('_', ' ').title()}**. The regional advisory prior was applied at {result['district_context_influence']}% influence. The adjusted score ({result['district_adjusted_score']:.1%}) is not a probability of success or a measured suitability score; the model itself was not trained with district data.")
    else:
        st.info(f"The model's top crop is **{result['model_crop'].replace('_', ' ').title()}**. No district adjustment was applied for {result['season']}; a validated season-specific crop prior is not configured. The score ({result['district_adjusted_score']:.1%}) is a model ranking score, not a probability of success.")
    st.caption("Kharif context comes from ICAR's 2025 Maharashtra Kharif agro-advisory and reflects advisory crop coverage, not district crop area or measured suitability. Verify current advisories, irrigation, local market, and soil tests before acting.")
    if result["season"] == "Kharif" and not result["district_crop_in_advisory"]:
        st.warning(f"{result['crop'].replace('_', ' ').title()} is not listed in the ICAR Kharif crop coverage for {result['district_region']}. This is a general-dataset model result, not a locally verified recommendation. The omission does not prove the crop cannot grow there; check with the district KVK before planting.")
    local_comparison = result.get("local_crop_comparison", {"status": "unavailable", "reason": "Local statistics are not available for this saved recommendation."})
    local_stats = result.get("local_crop_statistics")
    st.markdown("#### Check against local crop records")
    if local_stats:
        st.caption(f"{result['district']} · {result['season']} · {local_stats['year']} · {result.get('local_crop_statistics_source') or 'uploaded statistics'} · area in hectares")
        if result.get("local_crop_statistics_is_demo"):
            st.warning("DEMO ONLY: these are invented sample values, not Raigad crop statistics. Use them only to confirm the conflict display works.")
        top_local = pd.DataFrame(local_stats["rows"][:5])
        top_local = top_local.rename(columns={"crop": "Reported crop", "area_ha": "Area (ha)", "share": "Share of reported area", "rank": "Area rank"})
        top_local["Share of reported area"] = top_local["Share of reported area"].map(lambda value: f"{value:.1%}")
        st.dataframe(top_local, hide_index=True, width="stretch")
        if local_comparison["status"] == "zero":
            st.warning(f"Conflict with local records: {local_comparison['reason']} Reported area: {local_comparison['record']['area_ha']:,.1f} ha. Verify the source coverage and consult the local KVK; this does not prove the crop cannot grow here.")
        elif local_comparison["status"] == "low_area":
            record = local_comparison["record"]
            st.warning(f"Potential conflict with local records: {result['crop'].replace('_', ' ').title()} is recorded at {record['area_ha']:,.1f} ha (rank {record['rank']}; {record['share']:.1%} of reported crop area). The model suggestion differs from the dominant recorded pattern; confirm local conditions before planting.")
        elif local_comparison["status"] == "aligned":
            st.success(f"Local records are consistent with this suggestion: it ranks #{local_comparison['record']['rank']} by reported area ({local_comparison['record']['area_ha']:,.1f} ha). Historical cultivation is not proof of suitability for this field.")
        else:
            st.info(f"Local record check: {local_comparison['reason']}")
    else:
        st.info(f"Local record check unavailable: {local_comparison['reason']}")
    if result.get("out_of_range"):
        st.warning("One or more inputs are outside the training data range: " + ", ".join(result["out_of_range"]) + ". This recommendation is an extrapolation and may be unreliable.")
    with st.expander("See other model-ranked crop options"):
        st.dataframe(pd.DataFrame(result["alternatives"]), hide_index=True, width="stretch")
        st.caption("Adjusted ranking scores combine the model score with the advisory prior only when supported. Original model scores are shown for comparison; neither score estimates harvest success.")

    soil_result = st.session_state.get("soil_lab_result")
    report = {
        "field": {
            "name": result["field_name"],
            "district_or_location": result["district"],
            "created_at": result["created_at"],
        },
        "crop_recommendation": result["crop"],
        "unadjusted_model_crop": result["model_crop"],
        "district_region_context": result["district_region"],
        "season": result["season"],
        "district_context_applied": result["district_context_applied"],
        "district_context_influence": result["district_context_influence"],
        "district_crop_in_advisory": result["district_crop_in_advisory"],
        "local_crop_statistics": result.get("local_crop_statistics"),
        "local_crop_comparison": result.get("local_crop_comparison"),
        "local_crop_statistics_source": result.get("local_crop_statistics_source"),
        "local_crop_statistics_is_demo": result.get("local_crop_statistics_is_demo", False),
        "district_adjusted_rank_score": f"{result['district_adjusted_score']:.1%}",
        "selected_model": result["model"],
        "model_input_values": result["values"],
        "model_ranked_alternatives": result["alternatives"],
        "dataset": result["dataset"],
        "selected_model_metrics": {key: float(value) for key, value in result["model_metrics"].items()},
        "soil_lab_analysis": soil_result if soil_result and not soil_result.get("incomplete") else None,
        "soil_health_analysis": st.session_state.get("soil_health_result"),
    }
    report_col, save_col = st.columns(2)
    report_col.download_button(
        "Download field report (PDF)",
        data=build_field_report_pdf(report),
        file_name=f"{result['field_name'].replace(' ', '_')}_field_report.pdf",
        mime="application/pdf",
        width="stretch",
    )
    if save_col.button("Save field to history", type="secondary", width="stretch"):
        try:
            append_history(report)
            st.success(f"Saved {result['field_name']} to local field history.")
        except (OSError, sqlite3.Error) as error:
            st.error(f"Could not save field history: {error}")

    try:
        saved_history = read_history()
    except (json.JSONDecodeError, OSError, ValueError, sqlite3.Error) as error:
        st.error(f"Field history could not be read: {error}")
        saved_history = []
    if saved_history:
        st.markdown("#### Field history")
        history_fields = sorted({item.get("field", {}).get("name", "Unnamed field") for item in saved_history})
        selected_field = st.selectbox("Compare saved visits for field", history_fields)
        field_visits = [item for item in saved_history if item.get("field", {}).get("name") == selected_field]
        history_rows = []
        for visit in field_visits:
            row = {
                "Date": visit.get("field", {}).get("created_at", "")[:10],
                "District": visit.get("field", {}).get("district_or_location", ""),
                "Season": visit.get("season", ""),
                "Recommended crop": visit.get("crop_recommendation", ""),
                "Original model top crop": visit.get("unadjusted_model_crop", ""),
                "District prior": (f"Applied ({visit.get('district_context_influence', 0)}%)"
                                   if visit.get("district_context_applied") else "Not applied"),
                "In regional Kharif advisory": visit.get("district_crop_in_advisory", "Unknown"),
                "Model": visit.get("selected_model", ""),
            }
            row.update(visit.get("model_input_values", {}))
            history_rows.append(row)
        history_frame = pd.DataFrame(history_rows)
        st.dataframe(history_frame, hide_index=True, width="stretch")
        trend_feature = st.selectbox(
            "Trend input over time",
            ["N", "P", "K", "ph", "temperature", "humidity", "rainfall"],
            format_func=lambda key: input_labels[key],
        )
        trend_frame = pd.DataFrame({
            "Date": [item.get("field", {}).get("created_at", "")[:10] for item in field_visits],
            input_labels[trend_feature]: [item.get("model_input_values", {}).get(trend_feature) for item in field_visits],
        }).dropna().set_index("Date")
        st.line_chart(trend_frame)
