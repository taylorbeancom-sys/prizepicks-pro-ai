import requests
import pandas as pd

def get_live_prizepicks_board():
    # This is the direct endpoint for their live projections
    url = "https://api.prizepicks.com/projections"
    
    # These headers are CRITICAL to prevent getting blocked
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://app.prizepicks.com/"
    }
    
    params = {
        "league_id": "7", # 7 is NBA
        "per_page": "250",
        "single_stat": "True"
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        # 1. Build a 'Map' of Player IDs to Names
        # PrizePicks separates the 'Names' from the 'Lines' in their data
        players_map = {}
        for item in data.get('included', []):
            if item['type'] == 'new_player':
                players_map[item['id']] = item['attributes']['name']
        
        # 2. Extract the actual Points lines
        lines = []
        for entry in data.get('data', []):
            attr = entry['attributes']
            # We only want 'Points' for now to match your database
            if attr.get('stat_type') == "Points":
                player_id = entry['relationships']['new_player']['data']['id']
                lines.append({
                    "player": players_map.get(player_id, "Unknown"),
                    "line": float(attr['line_score']),
                    "opponent": attr.get('description', 'NBA')
                })
        
        return pd.DataFrame(lines)
    
    except Exception as e:
        print(f"Scraper Error: {e}")
        return pd.DataFrame()
