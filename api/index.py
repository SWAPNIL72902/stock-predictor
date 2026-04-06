import os
import joblib
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional, List

from flask import Flask, render_template, request, jsonify, url_for
from jose import JWTError, jwt
from passlib.context import CryptContext
import requests
from textblob import TextBlob
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# --- VERCEL PATH FIX ---
# Flask needs absolute paths in serverless environments to find templates/static
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# --- CONFIGURATION ---
SECRET_KEY = os.environ.get("SECRET_KEY", "your-very-secret-key-12345")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
# Vercel /tmp is the only writable directory
SQLALCHEMY_DATABASE_URL = "sqlite:////tmp/users.db"
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "e9b7e28caeb74456b4d38b637164d08f")

# Ticker Corrector
TICKER_CORRECTOR = {"RELAINCE.NS": "RELIANCE.NS", "RELAINCE": "RELIANCE.NS"}
TICKER_MAP = {"AAPL": "Apple Inc", "TSLA": "Tesla", "MSFT": "Microsoft", "GOOGL": "Google", "RELIANCE.NS": "Reliance Industries"}

# --- DATABASE SETUP ---
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

class PredictionHistory(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    ticker = Column(String)
    prediction = Column(String)
    confidence = Column(String)
    timestamp = Column(String)

Base.metadata.create_all(bind=engine)

# --- SECURITY ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        pass # Handle closing in routes

def get_current_user_from_request():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    token = auth_header.split(' ')[1]
    db = SessionLocal()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username: return None
        return db.query(UserDB).filter(UserDB.username == username).first()
    except:
        return None
    finally:
        db.close()

# --- ML UTILS ---
def calculate_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def generate_features(ticker: str):
    ticker = TICKER_CORRECTOR.get(ticker.upper(), ticker.upper())
    try:
        data = yf.download(ticker, period="60d", interval="1d", auto_adjust=True)
        if data.empty: return None, f"No data found for {ticker}."
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA10'] = df['Close'].rolling(window=10).mean()
        df['Daily_Return'] = df['Close'].pct_change()
        df['Volume_Change'] = df['Volume'].pct_change()
        df['RSI'] = calculate_rsi(df['Close'], window=14)
        df = df.replace([float('inf'), float('-inf')], 0).fillna(method='ffill').fillna(0)
        return df.iloc[-1:].copy(), None
    except Exception as e: return None, str(e)

# --- FLASK APP ---
app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR, static_url_path='/static')

# Load ML Artifacts
try:
    MODEL = joblib.load(os.path.join(BASE_DIR, "stock_model.pkl"))
    FEATURE_COLS = joblib.load(os.path.join(BASE_DIR, "feature_columns.pkl"))
except:
    MODEL, FEATURE_COLS = None, None

# --- PAGE ROUTES ---
@app.route("/")
def login_page(): return render_template("login.html")

@app.route("/signup")
def signup_page(): return render_template("signup.html")

@app.route("/dashboard")
def dashboard_page(): return render_template("dashboard.html")

@app.route("/analytics")
def analytics_page(): return render_template("analytics.html")

@app.route("/settings")
def settings_page(): return render_template("settings.html")

# --- API ROUTES ---
@app.route("/login", methods=['POST'])
def login():
    data = request.get_json()
    db = SessionLocal()
    user = db.query(UserDB).filter(UserDB.username == data['username']).first()
    if not user or not pwd_context.verify(data['password'], user.hashed_password):
        db.close()
        return jsonify({"detail": "Invalid credentials"}), 401
    token = create_access_token({"sub": user.username})
    db.close()
    return jsonify({"access_token": token, "token_type": "bearer"})

@app.route("/signup", methods=['POST'])
def signup():
    data = request.get_json()
    db = SessionLocal()
    if db.query(UserDB).filter(UserDB.username == data['username']).first():
        db.close()
        return jsonify({"detail": "Username taken"}), 400
    hashed_pwd = pwd_context.hash(data['password'])
    new_user = UserDB(username=data['username'], hashed_password=hashed_pwd)
    db.add(new_user)
    db.commit()
    token = create_access_token({"sub": data['username']})
    db.close()
    return jsonify({"access_token": token, "token_type": "bearer"})

@app.route("/stock-data")
def get_stock_data():
    ticker = request.args.get('ticker', 'AAPL').upper()
    ticker = TICKER_CORRECTOR.get(ticker, ticker)
    try:
        data = yf.download(ticker, period="30d", interval="1d", auto_adjust=True)
        if data.empty: return jsonify({"detail": "Ticker not found"}), 404
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        return jsonify({
            "dates": [d.strftime("%Y-%m-%d") for d in df.index],
            "prices": [round(float(p), 2) for p in df['Close']],
            "last_price": round(float(df['Close'].iloc[-1]), 2),
            "currency": "₹" if ticker.endswith(".NS") else "$"
        })
    except Exception as e: return jsonify({"detail": str(e)}), 500

@app.route("/predict", methods=['POST'])
def predict():
    user = get_current_user_from_request()
    if not user: return jsonify({"detail": "Unauthorized"}), 401
    ticker = request.args.get('ticker', 'AAPL').upper()
    ticker = TICKER_CORRECTOR.get(ticker, ticker)
    if not MODEL: return jsonify({"detail": "Model not loaded"}), 500
    
    df, err = generate_features(ticker)
    if err: return jsonify({"detail": err}), 400
    
    try:
        technical_up_prob = float(MODEL.predict_proba(df[FEATURE_COLS])[0][1])
        pred_text = "UP" if technical_up_prob >= 0.5 else "DOWN"
        
        # News Sentiment (simplified for speed)
        company_name = TICKER_MAP.get(ticker, ticker)
        sentiment_label = "Neutral"
        articles = []
        try:
            url = f"https://newsapi.org/v2/everything?q={company_name}&sortBy=publishedAt&pageSize=3&apiKey={NEWS_API_KEY}"
            res = requests.get(url, timeout=2).json()
            arts = res.get("articles", [])
            if arts:
                scores = [TextBlob(a.get('title','')).sentiment.polarity for a in arts]
                avg = sum(scores)/len(scores)
                sentiment_label = "Positive" if avg > 0.1 else "Negative" if avg < -0.1 else "Neutral"
                articles = [{"title": a.get('title'), "source": a.get('source', {}).get('name'), "sentiment_label": "Positive" if TextBlob(a.get('title','')).sentiment.polarity > 0.05 else "Neutral"} for a in arts]
        except: pass

        return jsonify({
            "ticker": ticker, "prediction": pred_text, "confidence": round(technical_up_prob, 4),
            "sentiment_label": sentiment_label, "news": articles, "last_updated": datetime.now().strftime("%Y-%m-%d")
        })
    except Exception as e: return jsonify({"detail": str(e)}), 500

# Vercel entry
app.debug = False
