import yfinance as yf
import pandas as pd
import numpy as np
import joblib

def calculate_rsi(data, window=14):
    """Calculate Relative Strength Index (RSI)."""
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def generate_features(ticker: str):
    """Fetches latest data and generates the same features used during training."""
    # Fetch 60 days to ensure enough data for MAs and RSI calculations
    data = yf.download(ticker, period="60d", interval="1d")
    if data.empty:
        return None, "No data found for this ticker"
    
    df = data.copy()
    
    # 1. Moving Averages (5, 10 days)
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA10'] = df['Close'].rolling(window=10).mean()
    
    # 2. Daily Returns
    df['Daily_Return'] = df['Close'].pct_change()
    
    # 3. Volume Change
    df['Volume_Change'] = df['Volume'].pct_change()
    
    # 4. RSI (Relative Strength Index)
    df['RSI'] = calculate_rsi(df['Close'], window=14)
    
    # Take the VERY LAST row for prediction
    latest_features = df.iloc[-1:].copy()
    
    # Handle missing values
    if latest_features.isnull().values.any():
        return None, "Latest data contains missing values (possibly due to rolling window)"
    
    return latest_features, None

def load_prediction_artifacts():
    """Loads the model and the feature columns."""
    try:
        model = joblib.load("stock_model.pkl")
        feature_columns = joblib.load("feature_columns.pkl")
        return model, feature_columns
    except Exception as e:
        print(f"Error loading model/features: {e}")
        return None, None
