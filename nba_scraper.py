import pandas as pd
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.static import players
from supabase import create_client, Client
import time

SUPABASE_URL = "https://ogoskeocotuxekkwbesa.supabase.co"
SUPABASE_KEY = "sb_secret_bq7wEtQKTgXebOH4hH7OrQ_X-j-LMbi" # Get from Project Settings -> API

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def scrape_nba_to_supabase(player_name):
    p_info = players.find_players_by_full_name(player_name)
    if not p_info: return
    
    p_id, p_real_name = p_info[0]['id'], p_info[0]['full_name']
    df = playergamelog.PlayerGameLog(player_id=p_id, season="2023-24").get_data_frames()[0]
    
    # Rest Calculations
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    df = df.sort_values('GAME_DATE')
    df['days_rest'] = df['GAME_DATE'].diff().dt.days.fillna(4)
    df['is_b2b'] = df['days_rest'] == 1
    
    upload_data = []
    for _, row in df.iterrows():
        try:
            mins = float(str(row['MIN']).split(':')[0]) + (float(str(row['MIN']).split(':')[1])/60) if ':' in str(row['MIN']) else float(row['MIN'])
            usage = (float(row['FGA']) + (0.44 * float(row['FTA'])) + float(row['TOV'])) / (mins or 1)
            upload_data.append({
                'player_name': p_real_name, 'points_scored': float(row['PTS']),
                'minutes_played': round(mins, 1), 'opponent_def_rating': 115.0, 
                'pace': 100.0, 'usage_rate': round(usage * 10, 2),
                'days_rest': int(row['days_rest']), 'is_b2b': bool(row['is_b2b'])
            })
        except: continue
    
    supabase.table('player_historical_stats').delete().eq('player_name', p_real_name).execute()
    supabase.table('player_historical_stats').insert(upload_data).execute()
