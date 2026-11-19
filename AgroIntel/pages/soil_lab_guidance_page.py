from __future__ import annotations

import pandas as pd
import streamlit as st

from field_report import build_field_report_pdf
from soil_analysis import SOIL_TYPES, analyze_soil_report
from soil_guidance import CROPS_BY_REGION, GUIDANCE, OTHER_REGION, REGIONS, get_guidance

context = st.session_state["_agrointel_context"]
results = context["results"]
data = context["data"]
dataset_source = context["dataset_source"]
raw_csv = context["raw_csv"]
result = st.session_state.get("recommendation_result")

st.markdown("#### Crop-specific soil lab guidance")
st.write("Use ratings from your Soil Health Card or laboratory report. For listed contexts, the app displays the published baseline package as a reference; local soil-test instructions take precedence.")
crop_options = sorted(
    {item for crops in CROPS_BY_REGION.values() for item in crops}
    | {label.replace("_", " ").lower() for label in results.labels}
)
current_crop = ({"pigeonpeas": "pigeon pea"}.get(result["crop"], result["crop"]).replace("_", " ").lower() if result else "")
default_crop = current_crop if current_crop in crop_options else "cotton"
default_guidance = next((item for item in GUIDANCE if item["crop"] == default_crop), None)
default_region = default_guidance["region"] if default_guidance else OTHER_REGION
with st.form("soil_lab_analysis"):
    region_col, crop_col, ph_col = st.columns([1.25, 1, 0.8])
    with region_col:
        soil_region = st.selectbox("Maharashtra region / production context", REGIONS, index=REGIONS.index(default_region))
    with crop_col:
        soil_crop = st.selectbox("Planned crop", crop_options, index=crop_options.index(default_crop))
    with ph_col:
        lab_ph = st.number_input("Soil pH from report", min_value=0.0, max_value=14.0,
                                 value=float(result["values"]["ph"] if result else 6.5), step=0.1)
    st.caption("Copy each rating exactly as shown on the lab report. Missing results are recorded as not tested. Ratings are not converted into nutrient doses.")
    rating_options = ["Select from report", "Not tested", "Very low", "Low", "Medium", "High", "Very high"]
    analyzer_ratings = (
        st.session_state.get("soil_health_result", {}).get("values", {}).get("lab_ratings", {})
    )
    rating_cols = st.columns(3)
    lab_ratings = {
        nutrient: rating_cols[index].selectbox(
            f"Soil lab rating · {nutrient}",
            rating_options,
            index=rating_options.index(analyzer_ratings[nutrient])
            if analyzer_ratings.get(nutrient) in rating_options else 0,
        )
        for index, nutrient in enumerate(("N", "P", "K"))
    }
    lab_ph_note = st.text_input("pH amendment or interpretation stated by the lab (optional)")
    analyze_soil = st.form_submit_button("Analyze lab ratings", type="primary")

if analyze_soil:
    selected_guidance = get_guidance(soil_crop, soil_region)
    if selected_guidance is None:
        st.session_state["soil_lab_result"] = {"guidance": None, "crop": soil_crop, "region": soil_region}
    else:
        st.session_state["soil_lab_result"] = {
            "guidance": selected_guidance, "crop": soil_crop, "region": soil_region,
            "ratings": {key: (value if value in ("Very low", "Low", "Medium", "High", "Very high") else "Not tested") for key, value in lab_ratings.items()},
            "base_rates": selected_guidance["rates"], "pH": lab_ph,
            "pH_note": lab_ph_note.strip(),
        }

soil_result = st.session_state.get("soil_lab_result")
if soil_result:
    if soil_result["guidance"] is None:
        st.warning("There is no verified published recommendation configured for this crop and region. No nutrient dose was calculated. Use the crop-specific recommendation on your local Soil Health Card or ask the district KVK.")
    else:
        guidance = soil_result["guidance"]
        st.markdown(f"**Reference context:** {guidance['context']}")
        table_rows = []
        rating_key = {"N": "N", "P₂O₅": "P", "K₂O": "K"}
        for nutrient in ("N", "P₂O₅", "K₂O"):
            rating = soil_result["ratings"][rating_key[nutrient]]
            base_rate = soil_result["base_rates"][nutrient]
            table_rows.append({
                "Nutrient": nutrient,
                "Lab rating": rating,
                "Published baseline reference (kg/ha)": base_rate,
            })
        st.dataframe(pd.DataFrame(table_rows), hide_index=True, width="stretch")
        ph_status = "acidic" if soil_result["pH"] < 7 else "alkaline" if soil_result["pH"] > 7 else "neutral"
        st.caption(f"Lab pH entered: {soil_result['pH']:.1f} ({ph_status}). pH suitability and amendments are crop-, soil-, and lab-method-specific; the app does not infer lime or gypsum dose.")
        if soil_result["pH_note"]:
            st.info(f"Lab pH note: {soil_result['pH_note']}")
        st.warning("This is a published baseline reference, not a soil-rating-adjusted dose or STCR prescription. Follow your current Soil Health Card and confirm with the district KVK before applying nutrients.")
        st.markdown(f"Source: [{guidance['source']}]({guidance['url']})")

with st.expander("Advanced soil report analyzer", expanded=False):
    st.write("Enter values from a soil report for a rule-based screening summary inspired by the reference project.")
    st.warning("This copied threshold set is not crop-, region-, or laboratory-method calibrated. It is a screening aid, not a fertilizer prescription. Use your Soil Health Card or local KVK for action rates.")
    st.caption("The numeric count starts at 0 when all readings are inside the reference bands. To verify it changes, set numeric Nitrogen to 40 and leave the other default values unchanged; expect 1 of 9 numeric checks. A Low lab-rating selection is reported separately and does not alter this numeric count.")
    with st.form("reference_soil_analyzer"):
        st.markdown("**Primary soil measurements**")
        primary_cols = st.columns(4)
        soil_values = {
            "nitrogen": primary_cols[0].number_input("Nitrogen (N)", min_value=0.0, max_value=5000.0, value=90.0),
            "phosphorus": primary_cols[1].number_input("Phosphorus (P)", min_value=0.0, max_value=5000.0, value=42.0),
            "potassium": primary_cols[2].number_input("Potassium (K)", min_value=0.0, max_value=5000.0, value=43.0),
            "ph": primary_cols[3].number_input("Soil pH", min_value=0.0, max_value=14.0, value=6.5, step=0.1),
        }
        st.caption("Enter N/P/K as reported; this reference framework does not specify or convert their units. The fixed cutoffs below are copied as-is and may not match your lab method.")
        st.markdown("**Soil lab rating categories**")
        st.caption("Copy each category exactly from your lab report. These categories are separate from the numeric analyzer inputs and are never inferred from them.")
        lab_rating_cols = st.columns(3)
        category_options = ["Not entered", "Very low", "Low", "Medium", "High", "Very high"]
        analyzer_lab_ratings = {
            nutrient: lab_rating_cols[index].selectbox(
                f"Lab rating · {nutrient}", category_options, index=0,
            )
            for index, nutrient in enumerate(("N", "P", "K"))
        }
        detail_cols = st.columns(5)
        soil_values.update({
            "moisture": detail_cols[0].number_input("Moisture (%)", min_value=0.0, max_value=100.0, value=30.0),
            "organic_carbon": detail_cols[1].number_input("Organic carbon (%)", min_value=0.0, max_value=100.0, value=0.8, step=0.1),
            "ec": detail_cols[2].number_input("EC (dS/m)", min_value=0.0, max_value=100.0, value=0.5, step=0.1),
            "zinc": detail_cols[3].number_input("Zinc (ppm)", min_value=0.0, max_value=10000.0, value=1.0, step=0.1),
            "iron": detail_cols[4].number_input("Iron (ppm)", min_value=0.0, max_value=10000.0, value=5.0, step=0.1),
            "soil_type": st.selectbox("Soil type", SOIL_TYPES),
        })
        soil_report_submitted = st.form_submit_button("Analyze soil report", type="primary", width="stretch")

    if soil_report_submitted:
        health_report = analyze_soil_report(soil_values)
        health_report["values"]["lab_ratings"] = {
            nutrient: rating for nutrient, rating in analyzer_lab_ratings.items()
            if rating != "Not entered"
        }
        st.session_state["soil_health_result"] = health_report

    health_report = st.session_state.get("soil_health_result")
    if health_report:
        numeric_col, rating_col = st.columns(2)
        numeric_col.metric(
            "Numeric measurements outside reference bands",
            f"{health_report['flag_count']} / {health_report.get('check_count', 9)}",
        )
        lab_ratings = health_report.get("values", {}).get("lab_ratings", {})
        low_ratings = [
            nutrient for nutrient, rating in lab_ratings.items()
            if rating in {"Very low", "Low"}
        ]
        rating_col.metric("Lab ratings recorded Low / Very low", len(low_ratings))
        if low_ratings:
            st.caption("Low / very low ratings copied from the lab report: " + ", ".join(low_ratings) + ". They are shown separately and do not change the numeric rule count.")
        if health_report.get("flagged_measurements"):
            st.caption("Numeric checks outside the bands: " + ", ".join(health_report["flagged_measurements"]) + ".")
        st.info(health_report["summary"])
        st.markdown("**Findings**")
        st.markdown("\n".join(f"- {finding}" for finding in health_report["findings"]))
        advice_col, irrigation_col = st.columns(2)
        with advice_col:
            st.markdown("**Nutrient / amendment notes**")
            st.markdown("\n".join(f"- {note}" for note in health_report["fertilizer_notes"]))
        with irrigation_col:
            st.markdown("**Water and soil notes**")
            st.markdown("\n".join(f"- {note}" for note in health_report["irrigation_notes"] + health_report["soil_notes"]))
        st.caption(health_report["limitations"])
        st.download_button(
            "Download soil analysis report (PDF)",
            data=build_field_report_pdf({"soil_health_analysis": health_report}),
            file_name="soil_analysis_report.pdf",
            mime="application/pdf",
            width="stretch",
        )
