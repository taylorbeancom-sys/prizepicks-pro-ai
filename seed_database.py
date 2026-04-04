import pandas as pd
import numpy as np
from supabase import create_client, Client

# === PASTE YOUR URL AND KEY HERE ===
SUPABASE_URL = "https://ogoskeocotuxekkwbesa.supabase.co"
SUPABASE_KEY = "sb_publishable_HBkc3_JYSmjCwjf10aCVpQ_sQO9a4EN"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def seed_fake_data():
    print("Generating 100 games of dummy data...")
    np.random.seed(42)
    
    # Generate 100 rows of fake game stats
    data = []
    for _ in range(100):
        row = {
            'player_name': 'Luka Doncic',
            'opponent_def_rating': round(np.random.uniform(105, 120), 1),
            'pace': round(np.random.uniform(95, 105), 1),
            'usage_rate': round(np.random.uniform(25, 35), 1),
            'minutes_played': round(np.random.uniform(30, 40), 1),
            'points_scored': round(np.random.normal(28, 6), 1)
        }
        data.append(row)

    print("Uploading to Supabase...")
    
    # Supabase allows bulk inserts! We pass the whole list of dictionaries.
    response = supabase.table('player_historical_stats').insert(data).execute()
    
    print(f"Success! Uploaded {len(response.data)} rows to the database.")

if __name__ == "__main__":
    seed_fake_data()