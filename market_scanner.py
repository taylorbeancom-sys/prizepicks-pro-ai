import requests

API_KEY = "39bd8d002fe2304e805889b6874624ff" 
# From the email you just got

def get_market_consensus(player_name):
    url = f"https://api.the-odds-api.com/v4/sports/basketball_nba/events"
    params = {'apiKey': API_KEY, 'regions': 'us', 'markets': 'player_points'}
    
    try:
        data = requests.get(url, params=params).json()
        lines = []
        for event in data:
            # Note: This is a simplified loop; real API responses may require nested drilling
            for book in event.get('bookmakers', []):
                for mkt in book.get('markets', []):
                    for outcome in mkt.get('outcomes', []):
                        if player_name.lower() in outcome['description'].lower():
                            lines.append(float(outcome['point']))
        return round(sum(lines)/len(lines), 1) if lines else None
    except: return None