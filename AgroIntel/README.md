# Smart Crop Recommendation and Soil Analysis System

A Streamlit app that trains three multiclass classifiers from the same crop dataset and the same stratified 80/20 split:

- Random Forest
- XGBoost
- K-Nearest Neighbors (with a `StandardScaler` fitted inside its training pipeline)

The app displays held-out accuracy, per-crop precision/recall/F1, confusion matrices, model selection, and crop recommendations. It computes all results from the uploaded data; no illustrative scores are presented as real results. Crop recommendations and soil lab interpretation are presented as separate workflows because model features are not soil-lab ratings.

### District-aware crop ranking

Field analysis asks for a Maharashtra district and planned season. The district maps to one of five regions described by ICAR: Vidarbha, Marathwada, Western Maharashtra, Khandesh/North Maharashtra, or Konkan. For Kharif only, the user may apply a 0–15% regional advisory-coverage prior after the classifier produces its scores. Rabi and Summer use the classifier ranking without a district adjustment because a matching validated prior is not configured. The UI warns when the top crop is outside the selected region's Kharif advisory coverage, and the saved history and PDF retain the original model crop and whether district context was applied. This is a transparent, user-adjustable regional nudge, not a district-trained model, measured district crop-area prior, yield forecast, or calibrated suitability estimate. The region groupings and Kharif crop context follow the [ICAR Kharif Agro-Advisory for Maharashtra (2025)](https://www.icar.gov.in/sites/default/files/Circulars/ICAR%20En-Kharif%20Agro-Advisories%20for%20Farmers%202025.pdf). It is a dated seasonal reference; check current advisories and KVK guidance before acting. Districts outside Maharashtra are not currently covered.

To compare a suggestion with **district × crop × season** records, open **Local crop records** on Field analysis and upload the Maharashtra district APY CSV from [Dataful](https://dataful.in/datasets/5632/) (Ministry of Agriculture and Farmers Welfare / UPAg source). Alternatively, place it at `data/maharashtra_district_crop_stats.csv`; this local file is ignored by Git. Required columns are `fiscal_year`, `district_as_per_source`, `crop`, `season`, and `area`. The app selects the latest year available for the chosen district and season, lists the five largest reported areas, and identifies model suggestions that are explicitly zero or ranked below the three largest reported crops. Exact crop aliases are used; unmatched or omitted crops are marked unreported/unmapped, never assumed to have zero cultivation. This is a historical cultivation-pattern check, not a suitability or yield model, and it does not alter the classifier ranking. The year and source are included in the field PDF.

For a software-only demonstration, upload `examples/sample_district_crop_stats_demo.csv` from **Local crop records**. It contains invented Raigad Kharif areas and deliberately places Jute at rank 5 so a Jute prediction shows the potential-conflict message. The UI and PDF label this as synthetic; do not use its values for agricultural decisions. The screenshot notice on Soil lab guidance about a missing verified crop-region package is a separate workflow from this local-record comparison.

## Crop-specific soil lab guidance

The **Soil lab guidance** page has a separate Soil Health Card workflow. Choose a crop and Maharashtra production context, then enter the N, P, and K ratings exactly as printed on the lab report (for example, Low/Medium/High). The app does not infer deficiencies from the crop classifier's NPK features. For a supported crop-region context, it displays the published baseline dose as a reference only; it does not adjust the dose using broad rating multipliers. Missing results are recorded as not tested. It also records the lab pH and any amendment note written by the lab.

The same page also includes an **Advanced soil report analyzer** inspired by the reference project's fixed NPK, pH, moisture, organic carbon, EC, zinc, iron, and soil-type rules. It reports numeric checks outside the fixed reference bands separately from lab-reported Low/Very low NPK ratings. The default numeric inputs are inside the bands, so zero is expected until a value crosses one; for a software check, set numeric N to 40 and keep the other defaults to see 1/9. Lab ratings do not affect the numeric count. These copied thresholds are not crop-, region-, or lab-method calibrated; use them for screening only and follow the actual Soil Health Card or local KVK guidance for fertilizer/amendment rates.

Each crop recommendation can be downloaded as a PDF field report with the field label, input values, model, dataset source/size and SHA-256, selected-model evaluation scores, soil findings, entered NPK rating categories, and any crop-specific guidance result. **Save field to history** keeps structured history in a local SQLite database at `data/field_history.sqlite3`; transactions protect concurrent saves. Existing `data/field_history.json` data is imported on first read and left in place. Local history is excluded from Git.

The configured packages are intentionally limited to source-backed contexts: rainfed hybrid cotton in Vidarbha, medium-soil rice in Eastern Vidarbha, wheat in the Western Maharashtra plain zone, chickpea and rabi sorghum in specified black-soil conditions. Seasonal 2025 advisory packages were removed because they may be stale. If the selected crop and context do not match, the app does not calculate a nutrient dose. Published values are baseline references, not STCR prescriptions; use the current Soil Health Card recommendation or confirm rates with the district KVK. pH amendment rates are not inferred.

## Complete project process

### Phase 1: Define the project

1. State the goal: predict a crop label from seven soil and climate measurements.
2. Treat this as multiclass classification. The inputs are `N`, `P`, `K`, temperature, humidity, pH, and rainfall; the target is `label`.
3. Set the limitation clearly: a prediction reflects patterns in the dataset and is not a guarantee of field success.

### Phase 2: Prepare the data

1. The project includes the Crop Recommendation dataset at `data/Crop_recommendation.csv` (2,200 records, 22 crop labels, 100 records per crop). The public dataset is listed on [Kaggle](https://www.kaggle.com/datasets/atharvaingle/crop-recommendation-dataset); `download_dataset.py` downloads a CSV mirror into this path.
2. Confirm that it has the required columns listed below and that `label` contains crop names.
3. Inspect row count, crop counts, missing values, duplicate rows, numeric ranges, and suspicious values before training.
4. Record the dataset source and any cleaning decisions for the final report.

### Phase 3: Prepare the Python environment

Follow the detailed Windows setup instructions under **Start the project on Windows** below. Keep the dataset and virtual environment out of source control; `.gitignore` already excludes them.

### Phase 4: Explore and validate the data

1. Check that all seven inputs are numeric and the target has at least two crop classes.
2. Review target class balance. A very small class can make reliable stratified evaluation impossible.
3. Check measurements for impossible values and investigate outliers rather than deleting them automatically.
4. Keep a written summary, including the number of usable rows and classes.

### Phase 5: Train the three models fairly

1. Run the app with `streamlit run app.py`. The local dataset loads automatically, or upload a different CSV.
2. The code validates the required columns and removes unusable rows.
3. It makes one stratified 80/20 train/test split using random seed 42 and reuses it for all models.
4. It fits Random Forest, XGBoost, and KNN separately. KNN's `StandardScaler` is inside its pipeline, so it is fitted on training data only.
5. Do not use the test split to tune parameters. If tuning is needed, use cross-validation within the training data, then evaluate the chosen setup once on the held-out test split.

### Phase 6: Evaluate and choose a model

1. Compare held-out accuracy, per-crop precision, recall, F1-score, and confusion matrices in the app.
2. Consider which crops are confused and whether the errors matter for the project use case; accuracy alone may hide weak performance on smaller classes.
3. Auto selection uses repeated stratified cross-validation on training data, keeping held-out test scores out of model selection. The app reports CV mean and variation, and separately reports one held-out test split. You can also manually select an algorithm for a prediction.
4. Report the split, random seed, metrics, and dataset source. Never copy example scores from a proposal or tutorial as project results.

### Phase 7: Try recommendations

1. Enter plausible values for all seven measurements.
2. Select a model or Auto Select Best Model and submit the form.
3. Compare model predictions for the same input and explain disagreements as model uncertainty.
4. Present recommendations as decision support and consider local season, irrigation, soil tests, and regional advice.

### Phase 8: Verify and document the finished project

1. Try a correctly formatted CSV, a CSV with a missing required column, and a file with missing or nonnumeric values.
2. Confirm that an invalid file receives a helpful error and that a valid file produces metrics and a prediction.
3. Capture screenshots of the app and record actual results only after running it on the chosen dataset.
4. Finish the report with the problem statement, dataset and features, preprocessing, algorithms, evaluation method, actual results, limitations, and future improvements.
5. For a presentation or demonstration, show dataset validation, the model comparison page, a prediction, and the limitations.

## Dataset

Upload a CSV with these exact column names:

`N, P, K, temperature, humidity, ph, rainfall, label`

The common Crop Recommendation dataset uses this format. Place a local copy at `data/Crop_recommendation.csv` if you want to keep it alongside the project; CSV files are ignored by Git.

The downloader fetches a public mirror of the [Crop Recommendation Dataset on Kaggle](https://www.kaggle.com/datasets/atharvaingle/crop-recommendation-dataset). Its copy is available from [gabbygab1233/Crop-Recommender](https://github.com/gabbygab1233/Crop-Recommender/blob/main/Crop_recommendation.csv). The dataset is a teaching dataset; confirm its source terms and limits before using it outside coursework.

## Start the project on Windows

1. Install Python 3.10 or newer. In File Explorer, open the `AgroIntel` folder, click the address bar, type `powershell`, and press Enter.
2. Set up the isolated environment and install packages:

   ```powershell
   .\setup.ps1
   ```

   The setup script stores the virtual environment under your local AppData folder, outside OneDrive, to avoid synced-file locking.

3. Download the sample dataset if it is not already present:

   ```powershell
   & "$env:LOCALAPPDATA\AgroIntel\venv\Scripts\python.exe" download_dataset.py
   ```

   The download command needs an internet connection. If it fails, download the CSV manually from the source link above and save it as `data\Crop_recommendation.csv`.

4. Launch the app:

   ```powershell
   .\run.ps1
   ```

5. Streamlit opens the app in your browser. The local CSV loads automatically. To use another compatible CSV, open **Dataset settings**. Choose **Auto Select Best Model** or Random Forest, XGBoost, or KNN; enter all seven measurements, then click **Analyze soil & recommend crop**.

6. To stop the app, return to PowerShell and press `Ctrl+C`. Next time, open PowerShell in the folder and run `.\run.ps1`.

## Project files

- `app.py` — Streamlit entrypoint, shared dataset/model loading, and the top navigation bar for field analysis, soil guidance, and model performance.
- `pages/field_analysis.py` — field inputs, crop recommendations, PDF reports, and saved field history.
- `pages/soil_lab_guidance_page.py` — crop-specific Soil Health Card guidance and the advanced soil report analyzer.
- `pages/model_performance.py` — model comparison, per-crop metrics, and confusion matrices.
- `app_storage.py` — transactional local field-history storage and legacy JSON import.
- `modeling.py` — validation, one stratified split, three model pipelines, and evaluation metrics.
- `soil_guidance.py` — source-backed Maharashtra crop/context baseline nutrient references.
- `soil_analysis.py` — reference-style rule-based soil report scoring and findings.
- `data/field_history.sqlite3` — local saved field reports (created by the app; ignored by Git).
- `download_dataset.py` — fetches the sample dataset into `data/`.
- `requirements.txt` — Python package dependencies.
- `data/` — local dataset location. The CSV is ignored by Git.

The shared test split is stratified and fixed with random seed 42 so model scores can be compared reproducibly. Exact duplicate records are removed before splitting. Training results are cached by uploaded CSV content. CV standard deviation describes fold variation, not a confidence interval. Accuracy estimates performance on this dataset split; it does not guarantee crop success in the field.
