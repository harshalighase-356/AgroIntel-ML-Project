"""Training and evaluation helpers for crop recommendation models."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import RepeatedStratifiedKFold, cross_val_score, train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler
from xgboost import XGBClassifier

FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
TARGET = "label"
PHYSICAL_BOUNDS = {
    "N": (0, 10000), "P": (0, 10000), "K": (0, 10000),
    "temperature": (-90, 70), "humidity": (0, 100), "ph": (0, 14), "rainfall": (0, 20000),
}


@dataclass
class TrainingResults:
    models: dict
    metrics: pd.DataFrame
    reports: dict
    confusion_matrices: dict
    labels: list[str]
    data_summary: dict


def validate_dataset(data: pd.DataFrame) -> pd.DataFrame:
    """Return a cleaned copy or raise a useful error for an incompatible CSV."""
    missing = [column for column in FEATURES + [TARGET] if column not in data.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))

    clean = data[FEATURES + [TARGET]].copy()
    for column in FEATURES:
        clean[column] = pd.to_numeric(clean[column], errors="coerce")
    clean[TARGET] = clean[TARGET].astype("string").str.strip()
    clean = clean.dropna(subset=FEATURES + [TARGET])
    clean = clean[clean[TARGET] != ""]
    impossible = []
    for feature, (lower, upper) in PHYSICAL_BOUNDS.items():
        invalid_count = int(((clean[feature] < lower) | (clean[feature] > upper)).sum())
        if invalid_count:
            impossible.append(f"{feature}: {invalid_count} value(s) outside {lower} to {upper}")
    if impossible:
        raise ValueError("Physically invalid values found; correct them before training. " + "; ".join(impossible))
    clean = clean.drop_duplicates()
    if clean.empty:
        raise ValueError("No usable rows remain after removing missing or invalid values.")
    if clean[TARGET].nunique() < 2:
        raise ValueError("The dataset must contain at least two crop classes.")
    counts = clean[TARGET].value_counts()
    if counts.min() < 5:
        raise ValueError("Each crop needs at least five unique usable rows for the stratified holdout and cross-validation.")
    if not clean[FEATURES].apply(lambda column: column.map(lambda value: abs(value) != float("inf"))).all().all():
        raise ValueError("Input features must contain finite numeric values.")
    return clean


def train_and_compare(data: pd.DataFrame, test_size: float = 0.2, random_state: int = 42) -> TrainingResults:
    clean = validate_dataset(data)
    X = clean[FEATURES]
    encoder = LabelEncoder()
    y = pd.Series(encoder.fit_transform(clean[TARGET].astype(str)), index=clean.index)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    labels = list(encoder.classes_)
    xgb_multiclass = len(labels) > 2
    estimators = {
        "Random Forest": RandomForestClassifier(n_estimators=300, random_state=random_state, n_jobs=-1),
        "XGBoost": XGBClassifier(
            n_estimators=250,
            max_depth=6,
            learning_rate=0.08,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="multi:softprob" if xgb_multiclass else "binary:logistic",
            **({"num_class": len(labels), "eval_metric": "mlogloss"}
               if xgb_multiclass else {"eval_metric": "logloss"}),
            tree_method="hist",
            random_state=random_state,
            n_jobs=-1,
        ),
        "KNN": Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", KNeighborsClassifier(n_neighbors=min(5, len(X_train)), weights="distance")),
        ]),
    }

    fitted, metric_rows, reports, matrices = {}, [], {}, {}
    fold_count = min(3, int(y_train.value_counts().min()))
    cv = RepeatedStratifiedKFold(n_splits=fold_count, n_repeats=2, random_state=random_state)
    for name, estimator in estimators.items():
        cv_scores = cross_val_score(estimator, X_train, y_train, cv=cv, scoring="accuracy", n_jobs=1)
        estimator.fit(X_train, y_train)
        predicted = estimator.predict(X_test)
        fitted[name] = estimator
        metric_rows.append({"Model": name, "Test accuracy": accuracy_score(y_test, predicted),
                            "Train CV mean": cv_scores.mean(), "Train CV std": cv_scores.std()})
        reports[name] = classification_report(
            y_test, predicted, labels=list(range(len(labels))), target_names=labels,
            output_dict=True, zero_division=0
        )
        matrices[name] = confusion_matrix(y_test, predicted, labels=list(range(len(labels))))

    metrics = pd.DataFrame(metric_rows).sort_values("Train CV mean", ascending=False).reset_index(drop=True)
    # Models emit encoded class indices; expose crop names to the app.
    original = data[FEATURES + [TARGET]].copy()
    valid_rows = original.copy()
    for feature in FEATURES:
        valid_rows[feature] = pd.to_numeric(valid_rows[feature], errors="coerce")
    valid_rows[TARGET] = valid_rows[TARGET].astype("string").str.strip()
    valid_rows = valid_rows.dropna(subset=FEATURES + [TARGET])
    valid_rows = valid_rows[valid_rows[TARGET] != ""]
    duplicate_rows_removed = int(valid_rows.duplicated().sum())
    outlier_counts = {}
    for feature in FEATURES:
        lower_quartile, upper_quartile = clean[feature].quantile([0.25, 0.75])
        spread = upper_quartile - lower_quartile
        outlier_counts[feature] = int(((clean[feature] < lower_quartile - 1.5 * spread)
                                       | (clean[feature] > upper_quartile + 1.5 * spread)).sum())
    summary = {
        "input_rows": len(original), "usable_rows": len(clean),
        "removed_rows": len(original) - len(clean), "duplicate_rows_removed": duplicate_rows_removed,
        "crop_classes": len(labels), "ranges": {feature: [float(clean[feature].min()), float(clean[feature].max())] for feature in FEATURES},
        "statistical_outliers": outlier_counts,
    }
    return TrainingResults(fitted, metrics, reports, matrices, labels, summary)
