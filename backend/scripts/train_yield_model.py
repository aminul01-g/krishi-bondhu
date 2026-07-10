#!/usr/bin/env python3
"""
Train a Random Forest yield prediction model.

Phase 1 — agronomy-grounded training data.

The model learns *real relationships* (NDVI, water availability, temperature,
historical yield, input level) instead of uniform random noise. If a real
labeled dataset is available, point YIELD_TRAIN_CSV at it (columns:
crop, ndvi, rainfall_mm, temp_mean, humidity, historical_avg_yield,
input_cost_normalized, yield_tons_per_bigha) and it will be used directly.

Output: backend/models/yield_model.pkl
"""
import os
import sys
import numpy as np
import pandas as pd
from pathlib import Path

CROP_BASES = {"rice": 3.5, "wheat": 2.8, "potato": 12.0, "mango": 1.5, "jute": 2.0}
CROPS = list(CROP_BASES.keys())


def generate_agronomy_data(n_samples: int = 800, seed: int = 42) -> pd.DataFrame:
    """Synthetic but agronomy-grounded training data for Bangladeshi crops."""
    rng = np.random.RandomState(seed)
    crop_labels = rng.choice(CROPS, size=n_samples)

    # Features drawn from realistic ranges.
    ndvi = rng.uniform(0.3, 0.85, n_samples)
    rainfall_mm = rng.uniform(200, 2000, n_samples)
    temp_mean = rng.uniform(20, 35, n_samples)
    humidity = rng.uniform(50, 95, n_samples)
    input_cost = rng.uniform(0.0, 1.0, n_samples)

    yields = []
    historical = []
    for i in range(n_samples):
        base = CROP_BASES[crop_labels[i]]
        optimal_rain = 1200 if crop_labels[i] == "rice" else 800

        ndvi_norm = (ndvi[i] - 0.2) / 0.7  # 0..1
        # NDVI is the dominant driver; weather/input add bounded, mild variation.
        water_factor = max(0.85, 1.0 - abs(rainfall_mm[i] - optimal_rain) / optimal_rain * 0.15)
        temp_factor = max(0.9, 1.0 - abs(temp_mean[i] - 27.0) / 20.0 * 0.1)
        input_factor = 0.85 + 0.15 * np.sqrt(input_cost[i])

        # Historical yield is a plausible fraction of the eventual yield.
        true_y = base * (0.2 + 0.8 * ndvi_norm) * water_factor * temp_factor * input_factor
        hist = max(0.1, true_y * rng.uniform(0.8, 1.05))
        historical.append(round(hist, 2))

        noise = rng.normal(0, base * 0.04)
        y = max(0.1, true_y * (0.7 + 0.3 * (hist / base)) + noise)
        yields.append(round(y, 2))

    return pd.DataFrame({
        "crop": crop_labels,
        "ndvi": np.round(ndvi, 4),
        "rainfall_mm": np.round(rainfall_mm, 1),
        "temp_mean": np.round(temp_mean, 1),
        "humidity": np.round(humidity, 1),
        "historical_avg_yield": historical,
        "input_cost_normalized": np.round(input_cost, 3),
        "yield_tons_per_bigha": yields,
    })


def load_real_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = ["crop", "ndvi", "rainfall_mm", "temp_mean", "humidity",
                "historical_avg_yield", "input_cost_normalized", "yield_tons_per_bigha"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")
    return df[required]


def main() -> None:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.preprocessing import LabelEncoder
    import joblib

    csv_path = os.getenv("YIELD_TRAIN_CSV")
    if csv_path and os.path.exists(csv_path):
        print(f"Loading REAL training data from {csv_path}")
        df = load_real_csv(csv_path)
    else:
        print("Generating agronomy-grounded synthetic training data "
              "(set YIELD_TRAIN_CSV to use real labeled data).")
        df = generate_agronomy_data(n_samples=800)

    print(f"Samples: {len(df)}  Crops: {sorted(df['crop'].unique().tolist())}")

    le = LabelEncoder()
    df["crop_encoded"] = le.fit_transform(df["crop"])

    feature_cols = ["crop_encoded", "ndvi", "rainfall_mm", "temp_mean",
                    "humidity", "historical_avg_yield", "input_cost_normalized"]
    X = df[feature_cols].values
    y = df["yield_tons_per_bigha"].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestRegressor(n_estimators=120, max_depth=14,
                                  min_samples_split=5, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print(f"\n--- Test Metrics ---")
    print(f"  MAE : {mean_absolute_error(y_test, y_pred):.3f} tons/bigha")
    print(f"  RMSE: {np.sqrt(mean_squared_error(y_test, y_pred)):.3f} tons/bigha")
    print(f"  R²  : {r2_score(y_test, y_pred):.3f}")

    print("\n--- Feature Importances ---")
    for name, imp in sorted(zip(feature_cols, model.feature_importances_), key=lambda x: -x[1]):
        print(f"  {name:24s} : {imp:.4f}")

    models_dir = Path(__file__).resolve().parent.parent / "models"
    models_dir.mkdir(exist_ok=True)
    bundle = {"model": model, "label_encoder": le, "feature_cols": feature_cols,
              "crop_classes": le.classes_.tolist(), "agronomy_grounded": True}
    joblib.dump(bundle, models_dir / "yield_model.pkl")
    print(f"\n✅ Model saved to: {models_dir / 'yield_model.pkl'}")


if __name__ == "__main__":
    main()
