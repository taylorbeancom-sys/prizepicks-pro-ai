import streamlit as st
import pandas as pd
import scipy.stats as stats
import time
import pytesseract
from PIL import Image
import re
from datetime import datetime


# Importing custom engines
from advanced_metrics import get_opponent_metrics
from usage_engine import calculate_projected_usage
from prizepicks_engine import fetch_historical_data, train_projection_model
from nba_scraper import scrape_nba_to_supabase
from market_scanner import get_market_consensus
from prizepicks_board_scraper import get_live_prizepicks_board
st.set_page_config(page_title="PrizePicks Pro AI", layout="wide")
st.title("🏀 PrizePicks +EV Pro Engine")

# Load Database
@st.cache_data(ttl=300)
def load_db():
    return fetch_historical_data()

historical_df = load_db()

tab1, tab2, tab3 = st.tabs(["🔍 Single Analysis", "📡 Board Scanner", "📥 Bulk Data Loader"])


# ==========================================
# TAB 1: SINGLE PLAYER ANALYSIS
# ==========================================
with tab1:
    col1, col2, col3 = st.columns(3)
    with col1:
        player_input = st.text_input("Player Name", value="Luka Doncic")
        pp_line = st.number_input("PrizePicks Line", value=29.5)
    with col2:
        opp = st.text_input("Opponent (e.g., WAS)", value="WAS").upper()
        dk_line = st.number_input("DraftKings/FanDuel Line", value=31.5)
    with col3:
        last_game_date = st.date_input("Last Game Date", value=datetime(2026, 4, 1))
        is_b2b = st.checkbox("Is this a Back-to-Back tonight?")

    # DEBUG: Show what's in the database
with st.expander("🛠️ Database Diagnostics"):
    if not historical_df.empty:
        unique_names = historical_df['player_name'].unique()
        st.write(f"Players currently in DB: {', '.join(unique_names)}")
    else:
        st.error("The app thinks the database is empty. Clear cache or re-scrape!")

    if st.button("🚀 Run Advanced Analysis", type="primary"):
        import unicodedata
        
        def simplify(text):
            # This turns 'Dončić' into 'doncic'
            return "".join(c for c in unicodedata.normalize('NFD', str(text)) 
                          if unicodedata.category(c) != 'Mn').lower()

        search_term = simplify(player_input.split()[-1])
        
        # Apply the simplification to every name in the DB to find a match
        p_df = historical_df[historical_df['player_name'].apply(simplify).str.contains(search_term, na=False)]
        
        if not p_df.empty:
            # ... [Rest of your analysis code remains the same] ...
            st.info(f"✅ Found {len(p_df)} games for {player_input}. Analyzing...")
            
            # 2. RUN MODELS & METRICS
            model, historical_std = train_projection_model(p_df)
            d_rat, pace = get_opponent_metrics(opp)
            usage = calculate_projected_usage(p_df, player_input, [])
            
            # 3. GENERATE PREDICTION
            match_df = pd.DataFrame({
                'opponent_def_rating': [d_rat], 'pace': [pace], 
                'usage_rate': [usage], 'minutes_played': [36.5],
                'days_rest': [(datetime.now().date() - last_game_date).days], 
                'is_b2b': [is_b2b]
            })
            
            proj = model.predict(match_df)[0] * (d_rat / 115.0) * (pace / 100.0)
            
            # 4. FETCH MARKET DATA
            with st.spinner("Fetching Market Consensus..."):
                consensus = get_market_consensus(player_input) or dk_line

            # 5. DISPLAY RESULTS
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("AI Projection", f"{proj:.1f}", delta=f"{proj - pp_line:.1f}")
            
            market_diff = round(consensus - pp_line, 1)
            c2.metric("Market Consensus", f"{consensus}", delta=f"{market_diff}")
            
            vol = "High" if p_df['points_scored'].std() > 8 else "Low"
            c3.metric("Volatility", vol)

            # 6. WIN PROBABILITY & KELLY
            prob_over = round(stats.norm.sf(pp_line, loc=proj, scale=historical_std) * 100, 2)
            st.write(f"### 🎯 Win Probability: {prob_over}%")
            st.progress(int(prob_over))
            
            # Kelly Criterion Calculation
            b, p = 2.0, (prob_over / 100)
            kelly = ((b * p) - (1 - p)) / b
            suggestion = max(0, round(kelly * 0.25 * 100, 1))

            # THE VERDICT (Where your error was)
            if (consensus - pp_line >= 1.0) and (prob_over > 55):
                st.success(f"💎 DIAMOND PLAY: AI and Market agree. Suggestion: Bet {suggestion}%")
            elif prob_over > 56:
                st.success(f"🤖 AI EDGE: Suggestion: Bet {suggestion}%")
            else:
                st.error("❌ NO EDGE: Pass on this play.")
        else:
            st.error(f"Player '{player_input}' not found. Check spelling or update in Tab 3.")
from prizepicks_board_scraper import get_live_prizepicks_board

# ==========================================
# TAB 2: LIVE BOARD SCANNER
# ==========================================
with tab2:
    st.markdown("### 📡 Live +EV Board Scanner")
    
    if st.button("🔄 Sync Live Board", type="primary", use_container_width=True):
        with st.spinner("Connecting to PrizePicks..."):
            df_live = get_live_prizepicks_board()
            
            if not df_live.empty:
                st.session_state['live_board'] = df_live
                st.success(f"Found {len(df_live)} active Points lines!")
            else:
                st.error("No lines found. PrizePicks might be blocking the request or the board is empty.")

    # If we have board data, run the AI against every line automatically
    if 'live_board' in st.session_state:
        board = st.session_state['live_board']
        final_picks = []

        for _, row in board.iterrows():
            # Check if we have this player in your Supabase DB
            # We use the fuzzy search we built for 'Dončić'
            name_search = row['player'].split()[-1].lower()
            p_df = historical_df[historical_df['player_name'].str.lower().str.contains(name_search, na=False)]
            
            if not p_df.empty:
                # 🤖 RUN THE AI MATH
                model, s_dev = train_projection_model(p_df)
                # (Assuming you have these helper functions in your code)
                d_rat, pc = get_opponent_metrics(row['opponent']) 
                proj = model.predict(pd.DataFrame([[d_rat, pc, 25.0, 36.0, 2, False]], 
                       columns=['opponent_def_rating', 'pace', 'usage_rate', 'minutes_played', 'days_rest', 'is_b2b']))[0]
                
                # Calculate Win Probability
                prob_over = round(stats.norm.sf(row['line'], loc=proj, scale=s_dev) * 100, 2)
                
                final_picks.append({
                    "Player": row['player'],
                    "Line": row['line'],
                    "AI Projection": round(proj, 1),
                    "Win Prob": f"{prob_over}%",
                    "Edge": round(prob_over - 54.2, 1)
                })

        if final_picks:
            results_df = pd.DataFrame(final_picks).sort_values("Edge", ascending=False)
            st.table(results_df)

# ==========================================
# TAB 3: BULK DATA LOADER
# ==========================================
with tab3:
    st.markdown("### 📥 Bulk Stats Refresh")
    names = st.text_area("Players (One per line)", value="Luka Doncic\nJayson Tatum")
    if st.button("📥 Start Bulk Scrape"):
        for name in names.split('\n'):
            if name.strip():
                st.write(f"Processing {name}...")
                scrape_nba_to_supabase(name.strip())
        st.success("✅ Database Synchronized!")
        st.cache_data.clear()

# ==========================================
# TAB 4: ENTRY SCANNER
# ==========================================

with tab4: # Create a new Tab 4
    st.header("📸 Entry Scanner & Analyzer")
    st.write("Upload a screenshot or paste a PrizePicks shared link to research the whole slip.")

    uploaded_file = st.file_uploader("Upload PrizePicks Screenshot", type=['png', 'jpg', 'jpeg'])
    entry_link = st.text_input("OR Paste Shared Entry Link")

    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, caption="Scanning Entry...", width=300)
        
        # OCR: Convert Image to Text
        raw_text = pytesseract.image_to_string(img)
        
        # LOGIC: Find Players and Lines (e.g., "Luka Doncic 31.5")
        # This regex looks for Name + Number
        found_picks = re.findall(r"([A-Z][a-z]+ [A-Z][a-z]+)\s+([\d.]+)", raw_text)
        
        if found_picks:
            st.success(f"🔍 Found {len(found_picks)} picks in screenshot!")
            for name, line in found_picks:
                st.write(f"**Analyzing {name} (Line: {line})**")
                # Trigger your existing analysis function
                # run_analysis(name, float(line)) 
        else:
            st.error("Could not read picks. Make sure the player names and lines are clear!")

    if entry_link:
        # Link Parsing Logic
        if "prizepicks.com" in entry_link:
            st.info("🔗 Link detected. Attempting to pull entry data...")
            # Here we would use your 'bridge.py' logic to fetch the specific link
