import cloudscraper
import pandas as pd
import streamlit as st

def get_live_prizepicks_board():
    # Use cloudscraper instead of regular requests
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )
    
    url = "https://api.prizepicks.com/projections"
    params = {"league_id": "7", "per_page": "250", "single_stat": "true"}

    try:
        response = scraper.get(url, params=params, timeout=15)
        
        # DIAGNOSTIC: Show the error if blocked
        if response.status_code == 403:
            st.error("🚫 Access Denied: PrizePicks is blocking the Streamlit Cloud server.")
            st.info("💡 Try running the app locally on your laptop—it usually works on home Wi-Fi!")
            return pd.DataFrame()

        data = response.json()
        
        # Map IDs to names and stat types
        players = {i['id']: i['attributes']['name'] for i in data['included'] if i['type'] == 'new_player'}
        stats = {i['id']: i['attributes']['display_name'] for i in data['included'] if i['type'] == 'stat_type'}
        
        # LOGGING: See what stats are live today
        # st.write(f"Live Stats found: {list(set(stats.values()))}")

        lines = []
        for entry in data['data']:
            s_id = entry['relationships']['stat_type']['data']['id']
            stat_name = stats.get(s_id, "Unknown")
            
            # Match 'Points' exactly (Check if they changed it to 'PTS' or 'Points (Full Game)')
            if "Points" in stat_name:
                p_id = entry['relationships']['new_player']['data']['id']
                lines.append({
                    "player": players.get(p_id, "Unknown"),
                    "line": float(entry['attributes']['line_score']),
                    "opponent": entry['attributes'].get('description', 'NBA')
                })
        
        return pd.DataFrame(lines)
    except Exception as e:
        st.error(f"⚠️ Scraper Error: {e}")
        return pd.DataFrame()
