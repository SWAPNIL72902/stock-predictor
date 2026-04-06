import yfinance as yf
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
import os

def calculate_rsi(data, window=14):
    """Calculate Relative Strength Index (RSI)."""
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def fetch_data(ticker="AAPL", period="5y"):
    """Fetches historical stock data from Yahoo Finance."""
    print(f"Fetching data for {ticker}...")
    data = yf.download(ticker, period=period)
    if data.empty:
        raise ValueError(f"No data found for {ticker}")
    return data

def feature_engineering(df):
    """Performs feature engineering on stock data."""
    print("Performing feature engineering...")
    
    # 1. Moving Averages (5, 10 days)
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA10'] = df['Close'].rolling(window=10).mean()
    
    # 2. Daily Returns
    df['Daily_Return'] = df['Close'].pct_change()
    
    # 3. Volume Change
    df['Volume_Change'] = df['Volume'].pct_change()
    
    # 4. RSI (Relative Strength Index)
    df['RSI'] = calculate_rsi(df['Close'], window=14)
    
    # Handle missing values after rolling windows
    df = df.dropna()
    
    return df

def create_target(df):
    """Creates the target variable (1 if next day closing price is higher, else 0)."""
    print("Creating target variable...")
    # Target: If tomorrow's Close > today's Close
    df['Target'] = (df['Close'].shift(-1) > df['Close']).astype(int)
    
    # Drop the very last row as it won't have a target value (next day)
    df = df.dropna()
    
    return df

def train_pipeline(ticker="AAPL"):
    # 1. Fetching Data
    df = fetch_data(ticker)
    
    # 2. Feature Engineering
    df = feature_engineering(df)
    
    # 3. Target Creation
    df = create_target(df)
    
    # Define features and target
    feature_cols = ['MA5', 'MA10', 'Daily_Return', 'Volume_Change', 'RSI']
    X = df[feature_cols]
    y = df['Target']
    
    # 4. Train/Test Split
    # Since it's time-series data, shuffle=False to avoid data leakage
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
    
    # 5. Training (Random Forest)
    print("Training model...")
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # 6. Evaluation
    print("\nEvaluating model...")
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred)
    
    print(f"Accuracy Score: {acc:.4f}")
    print("\nConfusion Matrix:")
    print(cm)
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    # 7. Saving Artifacts
    print("\nSaving artifacts...")
    joblib.dump(model, "stock_model.pkl")
    joblib.dump(feature_cols, "feature_columns.pkl")
    print("Model saved to stock_model.pkl")
    print("Feature names saved to feature_columns.pkl")

if __name__ == "__main__":
    try:
        train_pipeline("AAPL")
    except Exception as e:
        print(f"Error occurred: {e}")
