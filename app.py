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
    res = supabase.table("player_historical_stats").select("*").execute()
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
# --- TAB 1: SINGLE PLAYER ---
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        p_name = st.text_input("Search Player", "Luka Doncic")
        line_val = st.number_input("Line", value=30.5)
    with col2:
        opp = st.text_input("Opponent", "GSW")
    
    # This button must be aligned with col1 and col2
    if st.button("Run AI Analysis"):
        # SAFETY CHECK: Stop if the database is empty
        if historical_df.empty:
            st.warning("⚠️ Your database is empty! Go to the 'Bulk Loader' tab and add some players first.")
        else:
            # Simplified Analysis Logic
            search = simplify(p_name.split()[-1])
            
            # Ensure the column actually exists in your Supabase data
            if 'player_name' in historical_df.columns:
                p_df = historical_df[historical_df['player_name'].apply(simplify).str.contains(search)]
                
                if not p_df.empty:
                    # Calculates a simple average for the demo; replace with your ML model later
                    render_optimizer_card(p_name, line_val, p_df['points_scored'].mean(), 58.2)
                else:
                    st.error(f"Player '{p_name}' not found in your current records.")
            else:
                st.error("Column 'player_name' missing. Check your Supabase table headers!")

# --- TAB 2: LIVE OPTIMIZER ---
with tab2:
    st.subheader("🔥 Today's High-Edge NBA Props")
    live_board = load_live_board()
    
    if not live_board.empty:
        # Loop through every player currently on the PrizePicks board
        for _, row in live_board.iterrows():
            name = row['player_name']
            line = row['line']
            
            # Find this player's historical stats in your database
            search = simplify(name.split()[-1])
            p_hist = historical_df[historical_df['player_name'].apply(simplify).str.contains(search)]
            
            if not p_hist.empty:
                if not p_hist.empty:
                try:
                    # 🤖 MACHINE LEARNING MODEL
                    # Using the columns you have in Supabase: pts, mins, def_rating, pace
                    X = p_hist[['opponent_def_rating', 'pace', 'minutes_played']]
                    y = p_hist['points_scored']
                    
                    model = LinearRegression().fit(X, y)
                    std_dev = y.std() if len(y) > 1 else 5.0
                    
                    # PREDICT: Assume a standard NBA game (112 Defense, 100 Pace, 34 Mins)
                    # You can eventually make these dynamic!
                    real_proj = model.predict([[112.0, 100.0, 34.0]])[0]
                    
                    # CALCULATE WIN PROB: Using Normal Distribution (The "Pro" way)
                    # This calculates the chance of scoring MORE than the line
                    win_prob = round(stats.norm.sf(float(line), loc=real_proj, scale=std_dev) * 100, 1)
                    
                    render_optimizer_card(name, line, real_proj, win_prob)
                except Exception as e:
                    st.error(f"AI Error for {name}: {e}")
            else:
                # If you haven't bulk-loaded this player yet
                st.info(f"⏳ {name} is on the board, but his stats aren't in Supabase. Go to Bulk Loader!")
    else:
        st.warning("📡 No live lines found in 'live_board'. Run bridge.py on your laptop to sync the PrizePicks board!")

# --- TAB 3: BULK LOADER ---
with tab3:
    st.header("📥 NBA Bulk Data Loader")
    st.write("Search for any player to pull their recent games into your Supabase database.")
    
    target_player = st.text_input("Enter Player Name (e.g., Jayson Tatum)")
    
    if st.button("Fetch & Save Stats"):
        if target_player:
            with st.spinner(f"🏀 Fetching data for {target_player}..."):
                try:
                    from nba_api.stats.static import players
                    from nba_api.stats.endpoints import playergamelog
                    
                    # 1. Find the Player ID
                    nba_players = players.find_players_by_full_name(target_player)
                    
                    if nba_players:
                        p_id = nba_players[0]['id']
                        # 2. Get their 50 most recent games
                        log = playergamelog.PlayerGameLog(player_id=p_id).get_data_frames()[0]
                        
                        # 3. Format for your 'player_historical_stats' table
                        new_rows = []
                        for _, row in log.head(50).iterrows():
                            new_rows.append({
                                "player_name": target_player,
                                "points_scored": row['PTS'],
                                "minutes_played": int(row['MIN']),
                                "opponent_def_rating": 112.5, # Standard NBA Avg
                                "pace": 100.2,               # Standard NBA Avg
                                "game_date": row['GAME_DATE']
                            })
                        
                        # 4. Push to Supabase
                        supabase.table("player_historical_stats").upsert(new_rows).execute()
                        
                        st.success(f"✅ Successfully loaded {len(new_rows)} games for {target_player}!")
                        st.balloons()
                        st.info("💡 Important: Click 'Clear App Cache' below to make these stats show up in the Analysis tab.")
                    else:
                        st.error("Player not found in NBA records. Check the spelling!")
                except Exception as e:
                    st.error(f"Error fetching stats: {e}")
        else:
            st.warning("Please enter a name first.")

    st.divider()
    st.write("### System Admin")
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
