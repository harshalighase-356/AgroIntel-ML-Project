from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from modeling import train_and_compare

st.set_page_config(page_title="AgroIntel | Field intelligence", page_icon=":material/agriculture:", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
:root { --forest:#1b5e20; --leaf:#2e7d32; --sage:#81c784; --mint:#eaf5e8; --orange:#ff9800; --ink:#18351d; }
.stApp { background:linear-gradient(180deg,#f4fff4 0%,#f7faf5 52%,#fff 100%); color:var(--ink); font-family:'DM Sans',sans-serif; }
[data-testid="stHeader"] { background:rgba(244,255,244,.88); }

.block-container { max-width:1440px; padding-top:2.2rem; padding-bottom:4rem; }
.brandline { display:flex; align-items:center; gap:10px; color:#2e7d32; font:800 14px 'Manrope',sans-serif; letter-spacing:.14em; text-transform:uppercase; margin-bottom:16px; }
.brandmark { display:grid; place-items:center; height:34px; width:34px; border-radius:11px; background:#1b5e20; color:white; font-size:18px; box-shadow:0 5px 14px #1b5e2030; }
.hero { position:relative; overflow:hidden; padding:38px 42px; margin:0 0 28px; border-radius:24px; color:white; background:linear-gradient(112deg,#123d19 0%,#1b5e20 55%,#367e37 100%); box-shadow:0 18px 42px #1b5e2026; }
.hero:after { content:'🌿'; position:absolute; right:5%; top:10%; font-size:124px; opacity:.12; transform:rotate(-18deg); }
.hero-kicker { color:#c8e6c9; font-size:12px; font-weight:700; letter-spacing:.17em; text-transform:uppercase; }
.hero h1 { position:relative; z-index:1; margin:12px 0 10px; color:white; font:800 clamp(30px,4vw,48px)/1.12 'Manrope',sans-serif; letter-spacing:-.04em; }
.hero p { position:relative; z-index:1; max-width:760px; margin:0; color:#e8f5e9; font-size:16px; line-height:1.65; }
.feature-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin:0 0 26px; }
.feature-card { min-height:116px; padding:20px 22px; border:1px solid #e2eee0; border-radius:17px; background:rgba(255,255,255,.88); box-shadow:0 8px 24px #173f1c0a; }
.feature-icon { display:grid; place-items:center; width:35px; height:35px; margin-bottom:12px; border-radius:11px; background:#eaf5e8; font-size:18px; }
.feature-title { color:#18351d; font:700 15px 'Manrope',sans-serif; margin-bottom:5px; }
.feature-copy { color:#718274; font-size:13px; line-height:1.5; }
h2, h3 { color:#18351d !important; font-family:'Manrope',sans-serif !important; letter-spacing:-.025em; }
[data-testid="stMetric"] { padding:18px 20px; background:white; border:1px solid #e2eee0; border-radius:16px; box-shadow:0 8px 24px #173f1c0a; }
[data-testid="stMetricLabel"] { color:#638066; }
[data-testid="stDataFrame"] { border:1px solid #e2eee0; border-radius:14px; overflow:hidden; }
.stButton button, [data-testid="stFormSubmitButton"] button { border:0; border-radius:12px; background:#ff9800; color:#fff; font-weight:700; padding:.65rem 1.2rem; box-shadow:0 7px 16px #ff980033; transition:transform .18s,background .18s; }
.stButton button:hover, [data-testid="stFormSubmitButton"] button:hover { background:#ed8900; color:white; transform:translateY(-1px); }
[data-testid="stSelectbox"] [data-baseweb="select"] > div, [data-testid="stNumberInput"] input { border-radius:10px; }
[data-testid="stExpander"] { border:1px solid #e2eee0; border-radius:14px; background:#fff; }
[data-testid="stAlert"] { border-radius:14px; }
[data-testid="stTabs"] [data-baseweb="tab-list"] { gap:8px; border-bottom:1px solid #e2eee0; }
[data-testid="stTabs"] [data-baseweb="tab"] { border-radius:10px 10px 0 0; padding:12px 18px; color:#638066; }
[data-testid="stTabs"] [aria-selected="true"] { color:#1b5e20 !important; border-bottom:3px solid #ff9800; }
@media(max-width:700px) { .block-container{padding:1rem .75rem 3rem}.hero{padding:24px 18px;border-radius:18px}.hero:after{right:-2%;top:15%;font-size:82px}.hero p{font-size:14px}.hero h1{font-size:32px}.feature-grid{grid-template-columns:1fr;gap:10px}.feature-card{min-height:auto;padding:16px}.stButton button,[data-testid="stDownloadButton"] button{width:100%} [data-testid="stDataFrame"]{overflow-x:auto} }
</style>
<div class="brandline"><span class="brandmark">🌱</span> AgroIntel <span style="color:#9bb79d;font-weight:500;letter-spacing:0;text-transform:none">/ Crop intelligence</span></div>
<section class="hero"><div class="hero-kicker">Smart farming · Data informed decisions</div><h1>Grow with better<br>crop insights.</h1><p>Compare machine learning models trained on your crop data, explore their performance, and get a recommendation based on soil and climate conditions.</p></section>
""", unsafe_allow_html=True)

st.markdown("""
<div class="feature-grid">
  <div class="feature-card"><div class="feature-icon">🌾</div><div class="feature-title">Crop recommendation</div><div class="feature-copy">Match soil and climate inputs to the best fit from 22 crop classes.</div></div>
  <div class="feature-card"><div class="feature-icon">🧪</div><div class="feature-title">Soil report analysis</div><div class="feature-copy">Review nutrients, pH, moisture, salinity, and soil type.</div></div>
  <div class="feature-card"><div class="feature-icon">📊</div><div class="feature-title">Model insights</div><div class="feature-copy">Compare three trained models and open detailed evaluation when needed.</div></div>
</div>
""", unsafe_allow_html=True)

APP_DIR = Path(__file__).resolve().parent
DEFAULT_DATASET = APP_DIR / "data" / "Crop_recommendation.csv"

@st.cache_data(show_spinner=False, max_entries=8)
def load_and_train(csv_bytes: bytes):
    frame = pd.read_csv(pd.io.common.BytesIO(csv_bytes))
    return frame, train_and_compare(frame)

with st.expander("Dataset settings", expanded=False):
    uploaded = st.file_uploader("Upload a crop recommendation CSV", type=["csv"])
    st.caption("Required columns: N, P, K, temperature, humidity, ph, rainfall, label")
    st.markdown("[Dataset source · Kaggle](https://www.kaggle.com/datasets/atharvaingle/crop-recommendation-dataset)")

if uploaded:
    raw_csv = uploaded.getvalue()
    dataset_source = uploaded.name
elif DEFAULT_DATASET.exists():
    raw_csv = DEFAULT_DATASET.read_bytes()
    dataset_source = str(DEFAULT_DATASET.name)
else:
    st.info("Upload a compatible CSV in Dataset settings to train and compare the models.")
    st.code("py download_dataset.py", language="powershell")
    with st.expander("View CSV template"):
        st.code("N,P,K,temperature,humidity,ph,rainfall,label\n90,42,43,25,80,6.5,200,rice", language="csv")
    st.stop()

if len(raw_csv) > 20 * 1024 * 1024:
    st.error("This CSV is larger than the 20 MB app limit. Reduce the file size or prepare a smaller dataset.")
    st.stop()

try:
    with st.spinner("Loading validated data and evaluating models…"):
        data, results = load_and_train(raw_csv)
except Exception as error:
    st.error(f"Could not train from this file: {error}")
    st.stop()

st.caption(f"{results.data_summary['usable_rows']:,} usable rows · {results.data_summary['crop_classes']} crop classes · stratified holdout evaluation")
with st.expander("Dataset quality summary"):
    st.write(f"{results.data_summary['input_rows']:,} input rows; {results.data_summary['removed_rows']:,} removed for invalid values or exact duplicates ({results.data_summary['duplicate_rows_removed']:,} exact duplicates).")
    outlier_table = pd.DataFrame([{"Feature": feature, "IQR outlier rows (review only)": count}
                                  for feature, count in results.data_summary["statistical_outliers"].items()])
    st.dataframe(outlier_table, hide_index=True, width="stretch")
    st.caption("IQR outliers are surfaced for review and are not removed automatically. Inputs outside observed training ranges are flagged at prediction time; these ranges are not universal agronomic limits.")

st.session_state["_agrointel_context"] = {
    "results": results,
    "data": data,
    "dataset_source": dataset_source,
    "raw_csv": raw_csv,
}

navigation = st.navigation(
    [
        st.Page(
            "pages/field_analysis.py",
            title="Field analysis",
            icon=":material/agriculture:",
            default=True,
        ),
        st.Page(
            "pages/soil_lab_guidance_page.py",
            title="Soil lab guidance",
            icon=":material/science:",
        ),
        st.Page(
            "pages/model_performance.py",
            title="Model performance",
            icon=":material/analytics:",
        ),
    ],
    position="top",
)
navigation.run()
