import requests
import pandas as pd

def get_live_prizepicks_board(sport_id=7): # 7 is the ID for NBA
    url = "https://api.prizepicks.com/projections"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    
    params = {
        "league_id": sport_id,
        "per_page": "250",
        "state_code": "OK", # You can change this to your state
        "single_stat": "True"
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        # Mapping IDs to Names
        players = {item['id']: item['attributes']['name'] for item in data['included'] if item['type'] == 'new_player'}
        stats = {item['id']: item['attributes']['display_name'] for item in data['included'] if item['type'] == 'stat_type'}
        
        board = []
        for proj in data['data']:
            player_id = proj['relationships']['new_player']['data']['id']
            stat_id = proj['relationships']['stat_type']['data']['id']
            
            # We only care about "Points" for our current model
            if stats.get(stat_id) == "Points":
                board.append({
                    "player": players.get(player_id),
                    "line": float(proj['attributes']['line_score']),
                    "opponent": proj['attributes']['description'] # Usually the team abbr
                })
        
        return pd.DataFrame(board)
    except Exception as e:
        print(f"Error fetching PrizePicks board: {e}")
        return pd.DataFrame()