from __future__ import annotations

import pandas as pd
import seaborn as sns
import streamlit as st
from matplotlib import pyplot as plt

context = st.session_state["_agrointel_context"]
results = context["results"]
data = context["data"]
dataset_source = context["dataset_source"]
raw_csv = context["raw_csv"]
result = st.session_state.get("recommendation_result")

st.subheader("Model comparison")
metric_columns = st.columns(len(results.metrics))
for column, row in zip(metric_columns, results.metrics.itertuples(index=False)):
    column.metric(row.Model, f"{row[1]:.1%}", "held-out test accuracy")
with st.expander("View full comparison and cross-validation scores"):
    display_metrics = results.metrics.copy()
    for column in ("Test accuracy", "Train CV mean", "Train CV std"):
        display_metrics[column] = display_metrics[column].map(lambda value: f"{value:.1%}")
    st.dataframe(display_metrics, hide_index=True, width="stretch")
    st.caption("Auto selection uses mean accuracy from three-fold stratified CV repeated twice on the training portion (six fits per model). Test accuracy uses one untouched stratified holdout split. CV standard deviation describes fold-to-fold variation, not a confidence interval.")

with st.expander("Advanced evaluation: precision, recall, and F1"):
    for name, report in results.reports.items():
        st.markdown(f"**{name}**")
        rows = [{"Crop": crop, **values} for crop, values in report.items() if crop in results.labels]
        table = pd.DataFrame(rows)
        for column in ("precision", "recall", "f1-score"):
            table[column] = table[column].map(lambda value: f"{value:.3f}")
        st.dataframe(table, hide_index=True, width="stretch")

with st.expander("Advanced evaluation: confusion matrices"):
    for name, matrix in results.confusion_matrices.items():
        st.markdown(f"**{name}**")
        fig, ax = plt.subplots(figsize=(max(6, len(results.labels) * 0.55), max(4, len(results.labels) * 0.45)))
        sns.heatmap(matrix, annot=len(results.labels) <= 12, fmt="d", cmap="Greens",
                    xticklabels=results.labels, yticklabels=results.labels, ax=ax)
        ax.set_xlabel("Predicted crop")
        ax.set_ylabel("Actual crop")
        plt.xticks(rotation=45, ha="right")
        st.pyplot(fig, width="stretch")
        plt.close(fig)
