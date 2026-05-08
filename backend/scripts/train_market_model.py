import pandas as pd
import numpy as np
from prophet import Prophet
import pickle
import os
from datetime import datetime, timedelta

# Define common crops for the system
CROPS = ["rice", "potato", "onion", "tomato", "brinjal", "cabbage", "chili"]

def generate_synthetic_history(crop: str, days: int = 365):
    """
    Generates a realistic price history for a crop based on seasonal patterns.
    """
    dates = pd.date_range(start=datetime.now() - timedelta(days=days), periods=days)

    # Base price + seasonality (sine wave) + noise
    # Seasonal effect: Price peaks during off-season (winter/summer)
    base_price = 60.0 if crop == "rice" else 80.0
    seasonal_amplitude = 20.0

    # Day of year for seasonality
    day_of_year = np.arange(days)
    seasonality = seasonal_amplitude * np.sin(2 * np.pi * day_of_year / 365)

    # Random walk component for realistic drift
    noise = np.cumsum(np.random.randn(days) * 2)

    prices = base_price + seasonality + noise
    prices = np.clip(prices, 20, 300) # Keep prices realistic

    return pd.DataFrame({'ds': dates, 'y': prices})

def train_and_save_model(crop: str):
    """
    Trains a Prophet model for a specific crop and saves it.
    """
    print(f"Training model for: {crop}")
    df = generate_synthetic_history(crop)

    # Initialize Prophet with settings suitable for agricultural prices
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        changepoint_prior_scale=0.05
    )
    model.fit(df)

    # Save model to disk
    model_path = f"backend/models/market_{crop}.pkl"
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)

    print(f"Model saved to {model_path}")

if __name__ == "__main__":
    print("Starting market price model training...")
    for crop in CROPS:
        train_and_save_model(crop)
    print("Market price models trained and saved successfully.")
