import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
import pytesseract
from PIL import Image
import re
import unicodedata
from scipy import stats
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression

# ==========================================
# 1. CONFIG & THEME (PlayerProps.ai Aesthetic)
# ==========================================
st.set_page_config(page_title="PrizePicks Pro AI", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0f0a1e; color: #ffffff; }
    [data-testid="stHeader"] { background: rgba(0,0,0,0); }
    
    /* Player Card Styling */
    .player-card {
        background: linear-gradient(145deg, #1e1635, #140e26);
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 20px;
        border: 1px solid #3d2b7a;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    
    /* Implied Chance Badge */
    .chance-badge {
        background-color: #2d1b4e;
        border-radius: 12px;
        padding: 12px;
        text-align: center;
        border: 1px solid #7c4dff;
        min-width: 120px;
    }
    
    .percentage { font-size: 26px; font-weight: bold; color: #bb86fc; }
    .stat-label { font-size: 12px; color: #a0a0a0; text-transform: uppercase; }
    .val-box { font-size: 18px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. DATA CONNECTIONS
# ==========================================
url = "https://ogoskeocotuxekkwbesa.supabase.co"
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

@st.cache_data(ttl=600)
def load_historical_data():
    res = supabase.table("player_stats").select("*").execute()
    return pd.DataFrame(res.data)

@st.cache_data(ttl=60)
def load_live_board():
    res = supabase.table("live_board").select("*").execute()
    return pd.DataFrame(res.data)

historical_df = load_historical_data()

# ==========================================
# 3. UTILITY FUNCTIONS
# ==========================================
def simplify(text):
    return "".join(c for c in unicodedata.normalize('NFD', str(text)) 
                  if unicodedata.category(c) != 'Mn').lower()

def calculate_hit_rate(name, line, n_games=10):
    p_df = historical_df[historical_df['player_name'].apply(simplify).str.contains(simplify(name))]
    if p_df.empty: return 0
    recent = p_df.sort_values('game_date', ascending=False).head(n_games)
    hits = len(recent[recent['points_scored'] > line])
    return int((hits / len(recent)) * 100)

def render_optimizer_card(name, line, proj, prob):
    color = "#00e676" if prob > 54.2 else "#ff4d4d"
    direction = "OVER" if proj > line else "UNDER"
    l5 = calculate_hit_rate(name, line, 5)
    l10 = calculate_hit_rate(name, line, 10)
    diff = round(proj - line, 1)

    st.markdown(f"""
        <div class="player-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h2 style="margin:0; color: #ffffff;">{name}</h2>
                    <p style="color: #bb86fc; margin:0; font-weight: bold;">NBA • {direction} {line} PTS</p>
                </div>
                <div class="chance-badge">
                    <span class="stat-label">Implied Chance</span><br>
                    <span class="percentage" style="color: {color};">{prob}%</span><br>
                    <span style="font-size: 14px; color: {color}; font-weight: bold;">{direction}</span>
                </div>
            </div>
            <hr style="border: 0.5px solid #3d2b7a; margin: 15px 0;">
            <div style="display: flex; justify-content: space-between; text-align: center;">
                <div><span class="stat-label">AI Proj</span><br><span class="val-box">{round(proj, 1)}</span></div>
                <div><span class="stat-label">L5 Hit</span><br><span class="val-box">{l5}%</span></div>
                <div><span class="stat-label">L10 Hit</span><br><span class="val-box">{l10}%</span></div>
                <div><span class="stat-label">Diff</span><br><span class="val-box" style="color: {color};">{diff}</span></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# 4. MAIN UI LAYOUT
# ==========================================
st.title("🎯 PrizePicks Pro AI Optimizer")
tab1, tab2, tab3, tab4 = st.tabs(["🚀 Analysis", "📡 Live Optimizer", "📥 Bulk Loader", "📸 OCR Scanner"])

# --- TAB 1: SINGLE PLAYER ---
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        p_name = st.text_input("Search Player", "Luka Doncic")
        line_val = st.number_input("Line", value=30.5)
    with col2:
        opp = st.text_input("Opponent", "GSW")
        if st.button("Run AI Analysis"):
            # Simplified Analysis Logic
            search = simplify(p_name.split()[-1])
            p_df = historical_df[historical_df['player_name'].apply(simplify).str.contains(search)]
            if not p_df.empty:
                render_optimizer_card(p_name, line_val, p_df['points_scored'].mean(), 58.2)
            else:
                st.error("Player not found in database.")

# --- TAB 2: LIVE OPTIMIZER (The PlayerProps.ai Look) ---
with tab2:
    st.subheader("Today's High-Edge Props")
    live_board = load_live_board()
    if not live_board.empty:
        for _, row in live_board.iterrows():
            # Mocking projection for UI demo - replace with your model.predict()
            render_optimizer_card(row['player_name'], row['line'], row['line'] + 1.2, 56.4)
    else:
        st.info("No live lines found. Ensure bridge.py is running on your laptop!")

# --- TAB 3: DATA ADMIN ---
with tab3:
    st.write("Manage your Supabase records here.")
    if st.button("Clear App Cache"):
        st.cache_data.clear()
        st.success("Cache cleared!")

# --- TAB 4: OCR SCANNER ---
with tab4:
    st.header("📸 Smart Entry Scanner")
    uploaded_file = st.file_uploader("Upload PrizePicks Screenshot", type=['png', 'jpg', 'jpeg'])

    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, caption="Scanning...", width=400)
        
        raw_text = pytesseract.image_to_string(img)
        found_picks = re.findall(r"([A-Z][a-z]+ [A-Z][a-z]+)\s+([\d.]+)", raw_text)
        
        if found_picks:
            st.success(f"🔍 Detected {len(found_picks)} picks in slip")
            for name, line in found_picks:
                search = simplify(name.split()[-1])
                p_df = historical_df[historical_df['player_name'].apply(simplify).str.contains(search)]
                if not p_df.empty:
                    render_optimizer_card(name, float(line), p_df['points_scored'].mean(), 55.1)
                else:
                    st.warning(f"No history found for {name}. Please Bulk Load stats first.")
