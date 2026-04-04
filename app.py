import streamlit as st
import pandas as pd
import scipy.stats as stats
import time
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
# TAB 2: LIVE BOARD SCANNER (UPGRADED)
# ==========================================
with tab2:
    st.markdown("### 📡 Live +EV Board Scanner")
    
    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.info("Click the button below to pull every active NBA line from PrizePicks.")
    with col_b:
        if st.button("🔄 Sync Live Board", use_container_width=True, type="primary"):
            live_board_df = get_live_prizepicks_board()
            st.session_state['live_board'] = live_board_df

    if 'live_board' in st.session_state:
        board = st.session_state['live_board']
        st.write(f"Found **{len(board)}** active Points lines.")
        
        results = []
        missing_players = []

        for _, row in board.iterrows():
            p_name = row['player']
            # Search database for the player
            p_df = historical_df[historical_df['player_name'].str.contains(p_name.split()[-1], case=False, na=False)]
            
            if p_df.empty:
                missing_players.append(p_name)
                continue
            
            # Run the AI logic
            model, s_dev = train_projection_model(p_df)
            d_rat, pc = get_opponent_metrics(row['opponent'])
            u = calculate_projected_usage(p_df, p_name, [])
            
            m_df = pd.DataFrame({'opponent_def_rating': [d_rat], 'pace': [pc], 'usage_rate': [u], 'minutes_played': [36.0], 'days_rest': [2], 'is_b2b': [False]})
            proj = model.predict(m_df)[0] * (d_rat / 115.0) * (pc / 100.0)
            
            prob_o = round(stats.norm.sf(row['line'], loc=proj, scale=s_dev) * 100, 2)
            prob_u = round(stats.norm.cdf(row['line'], loc=proj, scale=s_dev) * 100, 2)
            
            results.append({
                "Player": p_name,
                "Line": row['line'],
                "AI Proj": round(proj, 1),
                "Play": "OVER" if prob_o > prob_u else "UNDER",
                "Win %": max(prob_o, prob_u),
                "Edge": round(max(prob_o, prob_u) - 54.2, 2)
            })

        if results:
            res_df = pd.DataFrame(results).sort_values("Edge", ascending=False)
            st.dataframe(res_df, use_container_width=True)
        
        if missing_players:
            with st.expander(f"⚠️ {len(missing_players)} Players Missing Data"):
                st.write("The following players are on the board but not in your database. Go to Tab 3 to scrape them:")
                st.write(", ".join(missing_players[:15]) + "...")

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
