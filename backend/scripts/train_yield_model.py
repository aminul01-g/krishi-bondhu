#!/usr/bin/env python3
"""
Train a Random Forest yield prediction model on synthetic data.

Generates realistic synthetic training data for Bangladeshi crops and saves
a trained scikit-learn RandomForestRegressor to backend/models/yield_model.pkl.

Usage:
    cd backend
    python scripts/train_yield_model.py

Output:
    models/yield_model.pkl  — serialized model
    Prints MAE, RMSE, R² on a held-out test set.
"""

import os
import sys
import numpy as np
import pandas as pd
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Generate synthetic training data
# ---------------------------------------------------------------------------

def generate_synthetic_data(n_samples: int = 500, seed: int = 42) -> pd.DataFrame:
    """
    Generate realistic synthetic yield data for Bangladeshi crops.

    Features:
        ndvi                  — Normalized Difference Vegetation Index (0.2–0.9)
        rainfall_mm           — Seasonal cumulative rainfall (200–2000 mm)
        temp_mean             — Average temperature during growing season (20–35 °C)
        humidity              — Average relative humidity (50–95 %)
        historical_avg_yield  — Average yield from farmer's past 3 seasons (0–15 t/bigha)
        input_cost_normalized — Normalised input expenditure (0–1)

    Target:
        yield_tons_per_bigha  — Crop yield in tons per bigha
    """
    rng = np.random.RandomState(seed)

    # Crop-specific base yields (tons/bigha)
    crop_bases = {"rice": 3.5, "wheat": 2.8, "potato": 12.0, "mango": 1.5, "jute": 2.0}
    crops = list(crop_bases.keys())
    crop_labels = rng.choice(crops, size=n_samples)

    ndvi = rng.uniform(0.2, 0.9, n_samples)
    rainfall_mm = rng.uniform(200, 2000, n_samples)
    temp_mean = rng.uniform(20, 35, n_samples)
    humidity = rng.uniform(50, 95, n_samples)
    input_cost_normalized = rng.uniform(0.0, 1.0, n_samples)

    # Generate yield with realistic relationships
    yields = []
    historical_avgs = []
    for i in range(n_samples):
        base = crop_bases[crop_labels[i]]

        # NDVI strongly positively correlated with yield
        ndvi_effect = (ndvi[i] - 0.5) * base * 0.6

        # Rainfall: sweet-spot curve (too little or too much hurts)
        optimal_rain = 800 if crop_labels[i] != "rice" else 1200
        rain_effect = -abs(rainfall_mm[i] - optimal_rain) / 2000 * base * 0.3

        # Temperature: moderate is best
        temp_effect = -abs(temp_mean[i] - 27) / 15 * base * 0.2

        # Input cost: higher investment → higher yield (diminishing returns)
        input_effect = input_cost_normalized[i] ** 0.5 * base * 0.25

        # Noise
        noise = rng.normal(0, base * 0.08)

        y = max(0.1, base + ndvi_effect + rain_effect + temp_effect + input_effect + noise)
        yields.append(round(y, 2))

        # Historical average is a noisy version of actual yield
        hist = max(0.1, y + rng.normal(0, base * 0.15))
        historical_avgs.append(round(hist, 2))

    return pd.DataFrame({
        "crop": crop_labels,
        "ndvi": np.round(ndvi, 4),
        "rainfall_mm": np.round(rainfall_mm, 1),
        "temp_mean": np.round(temp_mean, 1),
        "humidity": np.round(humidity, 1),
        "historical_avg_yield": historical_avgs,
        "input_cost_normalized": np.round(input_cost_normalized, 3),
        "yield_tons_per_bigha": yields,
    })


# ---------------------------------------------------------------------------
# 2. Train and evaluate
# ---------------------------------------------------------------------------

def main() -> None:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.preprocessing import LabelEncoder
    import joblib

    print("=" * 60)
    print("KrishiBondhu — Yield Prediction Model Training")
    print("=" * 60)

    # Generate data
    df = generate_synthetic_data(n_samples=500)
    print(f"\nGenerated {len(df)} synthetic samples for crops: {df['crop'].unique().tolist()}")

    # Encode crop names
    le = LabelEncoder()
    df["crop_encoded"] = le.fit_transform(df["crop"])

    feature_cols = [
        "crop_encoded", "ndvi", "rainfall_mm", "temp_mean",
        "humidity", "historical_avg_yield", "input_cost_normalized",
    ]
    X = df[feature_cols].values
    y = df["yield_tons_per_bigha"].values

    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Train
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=12,
        min_samples_split=5,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    print(f"\n--- Test Metrics ---")
    print(f"  MAE  : {mae:.3f} tons/bigha")
    print(f"  RMSE : {rmse:.3f} tons/bigha")
    print(f"  R²   : {r2:.3f}")

    # Feature importance
    print(f"\n--- Feature Importances ---")
    for name, imp in sorted(zip(feature_cols, model.feature_importances_), key=lambda x: -x[1]):
        print(f"  {name:30s} : {imp:.4f}")

    # Save model + label encoder
    models_dir = Path(__file__).resolve().parent.parent / "models"
    models_dir.mkdir(exist_ok=True)
    model_path = models_dir / "yield_model.pkl"

    bundle = {
        "model": model,
        "label_encoder": le,
        "feature_cols": feature_cols,
        "crop_classes": le.classes_.tolist(),
    }
    joblib.dump(bundle, model_path)
    print(f"\n✅ Model saved to: {model_path}")
    print(f"   Crop classes: {le.classes_.tolist()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
