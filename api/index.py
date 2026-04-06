import os
import joblib
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import requests
from textblob import TextBlob
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# --- CONFIGURATION ---
SECRET_KEY = os.environ.get("SECRET_KEY", "your-very-secret-key-12345")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
# For Vercel, tmp directory is writable. Persistent storage should use a real DB.
# For now, keeping it as is but moving to /tmp/ for sqlite if needed, 
# or just letting it be in the root if Vercel allows (they don't for sqlite usually).
# Vercel serverless functions are read-only except for /tmp.
SQLALCHEMY_DATABASE_URL = "sqlite:////tmp/users.db"
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "e9b7e28caeb74456b4d38b637164d08f")

# Ticker Corrector (Typo mapping)
TICKER_CORRECTOR = {
    "RELAINCE.NS": "RELIANCE.NS",
    "RELAINCE": "RELIANCE.NS",
}

# Ticker to Company Map (For news)
TICKER_MAP = {
    "AAPL": "Apple Inc",
    "TSLA": "Tesla",
    "MSFT": "Microsoft",
    "GOOGL": "Google",
    "RELIANCE.NS": "Reliance Industries",
    "TCS.NS": "Tata Consultancy Services",
    "INFY.NS": "Infosys",
    "HDFCBANK.NS": "HDFC Bank",
    "ADANIENT.NS": "Adani Enterprises"
}

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
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

class UserCreate(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None: raise HTTPException(status_code=401)
        user = db.query(UserDB).filter(UserDB.username == username).first()
        if user is None: raise HTTPException(status_code=401)
        return user
    except JWTError:
        raise HTTPException(status_code=401)

# --- ML & DATA UTILS (STABLE VERSION) ---
def calculate_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def generate_features(ticker: str):
    ticker = TICKER_CORRECTOR.get(ticker.upper(), ticker.upper())
    print(f"DEBUG: Generating features for {ticker}...")
    try:
        data = yf.download(ticker, period="60d", interval="1d", auto_adjust=True)
        if data.empty:
            return None, f"No data found for {ticker}."
        
        df = data.copy()
        
        # Flatten MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Core Features (Must match trainer)
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA10'] = df['Close'].rolling(window=10).mean()
        df['Daily_Return'] = df['Close'].pct_change()
        df['Volume_Change'] = df['Volume'].pct_change()
        df['RSI'] = calculate_rsi(df['Close'], window=14)
        
        # Handle Inf and NaN
        df = df.replace([float('inf'), float('-inf')], 0)
        df = df.fillna(method='ffill').fillna(0)
        
        latest = df.iloc[-1:].copy()
        print(f"DEBUG: Latest row shape: {latest.shape}")
        return latest, None
    except Exception as e:
        print(f"ERROR in generate_features: {e}")
        return None, str(e)

# --- FASTAPI APP ---
app = FastAPI(title="StockPredict Stability Engine")

# Mount Static Files and Templates
# Use absolute paths relative to project root
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.mount("/static", StaticFiles(directory=os.path.join(ROOT_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(ROOT_DIR, "templates"))

# Load ML Artifacts (Failsafe)
MODEL_PATH = os.path.join(ROOT_DIR, "stock_model.pkl")
FEATURES_PATH = os.path.join(ROOT_DIR, "feature_columns.pkl")

try:
    MODEL = joblib.load(MODEL_PATH)
    FEATURE_COLS = joblib.load(FEATURES_PATH)
    print(f"DEBUG: Model loaded. Features: {FEATURE_COLS}")
except Exception as e:
    MODEL, FEATURE_COLS = None, None
    print(f"ERROR Loading Model: {e}")

# --- PAGE ROUTES ---
@app.get("/")
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/signup")
async def signup_page(request: Request):
    return templates.TemplateResponse(request=request, name="signup.html")

@app.get("/dashboard")
async def dashboard_page(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")

@app.get("/analytics")
async def analytics_page(request: Request):
    return templates.TemplateResponse(request=request, name="analytics.html")

@app.get("/settings")
async def settings_page(request: Request):
    return templates.TemplateResponse(request=request, name="settings.html")

# --- API ROUTES ---
@app.get("/news")
async def get_news(ticker: str):
    """Fetch real-time news from NewsAPI in a failsafe manner."""
    ticker = TICKER_CORRECTOR.get(ticker.upper(), ticker.upper())
    print(f"DEBUG: Fetching news for {ticker}...")
    try:
        company_name = TICKER_MAP.get(ticker, ticker)
        url = f"https://newsapi.org/v2/everything?q={company_name}&sortBy=publishedAt&pageSize=5&apiKey={NEWS_API_KEY}"
        
        # Safe request with short timeout
        response = requests.get(url, timeout=3)
        
        if response.status_code != 200:
            print(f"DEBUG: NewsAPI Error: Status {response.status_code}")
            return {"sentiment_score": 0, "sentiment_label": "Neutral", "articles": []}
            
        json_data = response.json()
        articles = json_data.get("articles", [])
        
        if not articles:
            print("DEBUG: No articles found for this ticker.")
            return {"sentiment_score": 0, "sentiment_label": "Neutral", "articles": []}
        
        analyzed_news = []
        scores = []
        
        for art in articles[:5]:
            # Combine title + description
            text = f"{art.get('title', '')} {art.get('description', '')}"
            polarity = TextBlob(text).sentiment.polarity
            scores.append(polarity)
            
            analyzed_news.append({
                "title": art.get("title", "Breaking News"),
                "source": art.get("source", {}).get("name", "NewsAPI"),
                "date": art.get("publishedAt", "Today")[:10],
                "sentiment_label": "Positive" if polarity > 0.1 else "Negative" if polarity < -0.1 else "Neutral"
            })
            
        avg_score = sum(scores) / len(scores) if scores else 0
        label = "Positive" if avg_score > 0.1 else "Negative" if avg_score < -0.1 else "Neutral"
        
        print(f"DEBUG: {ticker} News Processed. Sentiment: {label} ({avg_score:.2f}) - Count: {len(articles)}")
        
        return {
            "sentiment_score": round(avg_score, 2),
            "sentiment_label": label,
            "articles": analyzed_news[:3]
        }
    except Exception as e:
        print(f"CRITICAL NewsAPI Exception for {ticker}: {e}")
        return {"sentiment_score": 0, "sentiment_label": "Neutral", "articles": []}

@app.get("/stock-data")
async def get_stock_data(ticker: str):
    ticker = TICKER_CORRECTOR.get(ticker.upper(), ticker.upper())
    print(f"DEBUG: Request /stock-data for {ticker}")
    try:
        # Use a more reliable way to fetch data if possible, but keeping yfinance for now
        data = yf.download(ticker, period="30d", interval="1d", auto_adjust=True)
        if data.empty:
            raise HTTPException(status_code=404, detail="Ticker not found")
        
        # Consistent column access
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        response = {
            "dates": [d.strftime("%Y-%m-%d") for d in df.index],
            "prices": [round(float(p), 2) for p in df['Close']],
            "last_price": round(float(df['Close'].iloc[-1]), 2),
            "currency": "₹" if ticker.endswith(".NS") else "$"
        }
        return response
    except Exception as e:
        print(f"ERROR /stock-data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/signup", response_model=Token)
async def signup(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(UserDB).filter(UserDB.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username taken")
    hashed_pwd = pwd_context.hash(user.password)
    new_user = UserDB(username=user.username, hashed_password=hashed_pwd)
    db.add(new_user)
    db.commit()
    return {"access_token": create_access_token({"sub": user.username}), "token_type": "bearer"}

@app.post("/login", response_model=Token)
async def login(login_data: UserCreate, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.username == login_data.username).first()
    if not user or not pwd_context.verify(login_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": create_access_token({"sub": login_data.username}), "token_type": "bearer"}

@app.post("/predict")
async def predict(ticker: str, db: Session = Depends(get_db), current_user: UserDB = Depends(get_current_user)):
    ticker = TICKER_CORRECTOR.get(ticker.upper(), ticker.upper())
    print(f"DEBUG: Processing prediction for {ticker}")
    if not MODEL: raise HTTPException(status_code=500, detail="Model not loaded on server")
    
    df, err = generate_features(ticker)
    if err: raise HTTPException(status_code=400, detail=err)
    
    try:
        # 1. Technical Prediction
        X_pred = df[FEATURE_COLS]
        technical_up_prob = float(MODEL.predict_proba(X_pred)[0][1]) # Prob of UP
        
        # 2. News Sentiment Integration
        sentiment_data = await get_news(ticker)
        sentiment_score = float(sentiment_data.get("sentiment_score", 0)) # -1 to +1
        
        # 3. Hybrid Fusion Logic (70% Technical, 30% Sentiment)
        # Convert sentiment (-1 to 1) to a 0-1 scale for the ensemble
        norm_sentiment = (sentiment_score + 1) / 2
        
        final_up_score = (technical_up_prob * 0.7) + (norm_sentiment * 0.3)
        
        # Determine Final Label
        pred_text = "UP" if final_up_score >= 0.5 else "DOWN"
        
        # Calculate Confidence (Distance from 0.5 baseline)
        conf_score = final_up_score if final_up_score >= 0.5 else (1 - final_up_score)
        
        # Store to history
        db.add(PredictionHistory(
            user_id=current_user.id, ticker=ticker, prediction=pred_text,
            confidence=f"{conf_score*100:.1f}%", timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        db.commit()
        
        print(f"DEBUG: {ticker} Ensemble -> Tech: {technical_up_prob:.2f}, Sent: {sentiment_score:.2f}, Final: {final_up_score:.2f}")

        return {
            "ticker": ticker,
            "prediction": pred_text,
            "confidence": round(float(conf_score), 4),
            "sentiment_score": round(sentiment_score, 2),
            "sentiment_label": sentiment_data.get("sentiment_label", "Neutral"),
            "news": sentiment_data.get("articles", []),
            "last_updated": df.index[-1].strftime("%Y-%m-%d")
        }
    except Exception as e:
        print(f"ERROR during prediction: {e}")
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

# This handler is required for Vercel
# Vercel's Python runtime expects "app" to be the FastAPI instance
# If it's named something else, you'd need the vercel.json rewrite to point to it.
