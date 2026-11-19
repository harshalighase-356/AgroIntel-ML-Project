"""Download the standard crop recommendation sample dataset into data/."""

from pathlib import Path
from io import BytesIO
import os
from urllib.request import Request, urlopen

DATA_DIR = Path(__file__).parent / "data"
DESTINATION = DATA_DIR / "Crop_recommendation.csv"
SOURCE = "https://raw.githubusercontent.com/gabbygab1233/Crop-Recommender/main/Crop_recommendation.csv"


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    request = Request(SOURCE, headers={"User-Agent": "AgroIntel-crop-project/1.0"})
    try:
        with urlopen(request, timeout=30) as response:
            content = response.read()
    except Exception as exc:
        raise SystemExit(f"Dataset download failed: {exc}\nDownload the CSV manually and save it to {DESTINATION}")

    try:
        import pandas as pd
        frame = pd.read_csv(BytesIO(content))
        required = {"N", "P", "K", "temperature", "humidity", "ph", "rainfall", "label"}
        if not required.issubset(frame.columns) or len(frame) < 100 or frame["label"].nunique() < 2:
            raise ValueError("missing required columns or insufficient rows/classes")
    except Exception as exc:
        raise SystemExit(f"Downloaded file failed dataset validation: {exc}") from exc
    temporary = DESTINATION.with_suffix(".csv.tmp")
    temporary.write_bytes(content)
    os.replace(temporary, DESTINATION)
    print(f"Saved dataset to {DESTINATION} ({len(content):,} bytes)")


if __name__ == "__main__":
    main()
