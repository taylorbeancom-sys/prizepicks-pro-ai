import requests
import pandas as pd

def get_live_prizepicks_board():
    url = "https://api.prizepicks.com/projections"
    
    # "Stealth" Headers to make the request look like a real Chrome browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://app.prizepicks.com/",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    params = {
        "league_id": "7", # 7 is NBA
        "per_page": "250",
        "single_stat": "true"
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        
        # Check for block (403) or error
        if response.status_code != 200:
            print(f"❌ API Access Denied (Status {response.status_code}). PrizePicks may be blocking the cloud IP.")
            return pd.DataFrame()

        data = response.json()
        
        # 1. Build Mappings (Names and Stat Types)
        players_map = {}
        stat_map = {}
        
        for item in data.get('included', []):
            if item['type'] == 'new_player':
                players_map[item['id']] = item['attributes']['name']
            if item['type'] == 'stat_type':
                stat_map[item['id']] = item['attributes']['display_name']
        
        # 2. Extract Data
        lines = []
        for entry in data.get('data', []):
            attr = entry['attributes']
            relationships = entry.get('relationships', {})
            
            # Find the stat name using the ID from relationships
            stat_id = relationships.get('stat_type', {}).get('data', {}).get('id')
            stat_name = stat_map.get(stat_id, "Unknown")
            
            # We only target 'Points' to match your AI model
            if stat_name == "Points":
                p_id = relationships.get('new_player', {}).get('data', {}).get('id')
                lines.append({
                    "player": players_map.get(p_id, "Unknown"),
                    "line": float(attr['line_score']),
                    "opponent": attr.get('description', 'NBA')
                })
        
        return pd.DataFrame(lines)
    
    except Exception as e:
        print(f"⚠️ Board Scraper Error: {e}")
        return pd.DataFrame()
