#!/usr/bin/env python3
"""
Train Prophet price-forecast models per crop.

Phase 1 — realistic history. Generates a seasonal price series (base + annual
sine + modest noise, clipped to a realistic band) instead of an unbounded
random walk. To train on REAL wholesale prices, drop daily CSVs named
`<crop>.csv` (columns: ds, y) into the folder pointed to by MARKET_TRAIN_CSV_DIR.

Models saved to backend/models/market_<crop>.pkl
"""
import os
import numpy as np
import pandas as pd

CROPS = ["rice", "potato", "onion", "tomato", "brinjal", "cabbage", "chili"]

CROP_BASE = {
    "rice": 65, "potato": 22, "onion": 55, "tomato": 40,
    "brinjal": 35, "cabbage": 35, "chili": 200,
}


def generate_synthetic_history(crop: str, days: int = 365, seed: int = 0) -> pd.DataFrame:
    """Seasonal price history: base + annual sine + modest noise (clipped)."""
    rng = np.random.RandomState(seed)
    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=days, freq="D")
    base = CROP_BASE.get(crop, 60.0)
    day_of_year = dates.dayofyear.values
    seasonality = base * 0.15 * np.sin(2 * np.pi * (day_of_year - 60) / 365)
    noise = rng.normal(0, base * 0.03, size=days)
    prices = base + seasonality + noise
    prices = np.clip(prices, base * 0.5, base * 1.8)
    return pd.DataFrame({"ds": dates, "y": np.round(prices, 2)})


def load_real_history(crop: str, csv_dir: str) -> pd.DataFrame:
    path = os.path.join(csv_dir, f"{crop}.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    if "ds" not in df.columns or "y" not in df.columns:
        raise ValueError(f"{path} must have columns 'ds' and 'y'")
    return df


def train_and_save_model(crop: str, csv_dir: str = None) -> None:
    from prophet import Prophet  # lazy import; only needed when actually training
    if csv_dir:
        df = load_real_history(crop, csv_dir)
        source = f"REAL csv ({csv_dir}/{crop}.csv)"
    else:
        df = generate_synthetic_history(crop, seed=abs(hash(crop)) % 1000)
        source = "synthetic seasonal (no real DAM history supplied)"

    print(f"Training model for: {crop}  [{source}]  samples={len(df)}")

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        changepoint_prior_scale=0.05,
    )
    model.fit(df)

    models_dir = os.path.join("backend", "models")
    os.makedirs(models_dir, exist_ok=True)
    with open(os.path.join(models_dir, f"market_{crop}.pkl"), "wb") as f:
        import pickle
        pickle.dump(model, f)
    print(f"  -> saved market_{crop}.pkl")


if __name__ == "__main__":
    csv_dir = os.getenv("MARKET_TRAIN_CSV_DIR")
    print("Starting market price model training"
          + (f" (real history from {csv_dir})" if csv_dir else " (simulated seasonal history)"))
    for crop in CROPS:
        train_and_save_model(crop, csv_dir)
    print("Market price models trained and saved successfully.")
