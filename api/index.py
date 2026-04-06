import os
import joblib
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional, List

from flask import Flask, render_template, request, jsonify, send_from_directory, url_for
from jose import JWTError, jwt
from passlib.context import CryptContext
import requests
from textblob import TextBlob
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# --- VERCEL PATH FIX ---
# Flask needs absolute paths in serverless environments
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

def get_current_user(token, db):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None: return None
        return db.query(UserDB).filter(UserDB.username == username).first()
    except JWTError:
        return None

# --- FLASK APP INITIALIZATION ---
app = Flask(__name__, 
            template_folder=TEMPLATE_DIR, 
            static_folder=STATIC_DIR,
            static_url_path='/static')

# --- ML Artifacts ---
try:
    MODEL = joblib.load(os.path.join(BASE_DIR, "stock_model.pkl"))
    FEATURE_COLS = joblib.load(os.path.join(BASE_DIR, "feature_columns.pkl"))
except:
    MODEL, FEATURE_COLS = None, None

# --- PAGE ROUTES ---
@app.route("/")
def login_page():
    return render_template("login.html")

@app.route("/signup")
def signup_page():
    return render_template("signup.html")

@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")

@app.route("/analytics")
def analytics_page():
    return render_template("analytics.html")

@app.route("/settings")
def settings_page():
    return render_template("settings.html")

# --- API ROUTES ---
@app.route("/api/signup", methods=['POST'])
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

@app.route("/api/login", methods=['POST'])
def login():
    data = request.get_json()
    db = SessionLocal()
    user = db.query(UserDB).filter(UserDB.username == data['username']).first()
    if not user or not pwd_context.verify(data['password'], user.hashed_password):
        db.close()
        return jsonify({"detail": "Invalid credentials"}), 401
    token = create_access_token({"sub": data['username']})
    db.close()
    return jsonify({"access_token": token, "token_type": "bearer"})

# Required for Vercel
app.debug = False
# No app.run() here
