import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from supabase import create_client, Client

SUPABASE_URL = "https://ogoskeocotuxekkwbesa.supabase.co"
SUPABASE_KEY = "sb_publishable_HBkc3_JYSmjCwjf10aCVpQ_sQO9a4EN"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_historical_data():
    res = supabase.table('player_historical_stats').select('*').execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

def train_projection_model(df):
    # Fill gaps from schema changes
    df['days_rest'] = df['days_rest'].fillna(2)
    df['is_b2b'] = df['is_b2b'].fillna(False)
    
    features = ['opponent_def_rating', 'pace', 'usage_rate', 'minutes_played', 'days_rest', 'is_b2b']
    X = df[features]
    y = df['points_scored']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    std = np.std(y_test - model.predict(X_test))
    return model, std