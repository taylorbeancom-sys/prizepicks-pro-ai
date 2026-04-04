import pandas as pd

def calculate_projected_usage(historical_df, player_name, injured_teammates):
    """
    Calculates a 5-game rolling usage average and applies an injury spike.
    """
    print(f"\n--- Calculating Usage for {player_name} ---")
    
    # 1. Get the 5-game rolling average from our Supabase data
    recent_games = historical_df.tail(5)
    baseline_usage = recent_games['usage_rate'].mean()
    
    print(f"Baseline 5-Game Usage Rate: {baseline_usage:.2f}")

    # 2. The Injury Impact Dictionary
    impact_matrix = {
        "Luka Doncic": {
            "Kyrie Irving": 0.15,  
            "Dereck Lively": 0.02, 
            "PJ Washington": 0.05
        },
        "Jayson Tatum": {
            "Jaylen Brown": 0.12,
            "Kristaps Porzingis": 0.08
        }
    }

    # 3. Apply the Spikes
    projected_usage = baseline_usage
    
    if player_name in impact_matrix:
        for teammate in injured_teammates:
            if teammate in impact_matrix[player_name]:
                spike_percentage = impact_matrix[player_name][teammate]
                boost = baseline_usage * spike_percentage
                projected_usage += boost
                print(f"🚨 INJURY ALERT: {teammate} is OUT. Usage spikes by {spike_percentage*100}% (+{boost:.2f})")
    
    print(f"🔥 FINAL PROJECTED USAGE TONIGHT: {projected_usage:.2f}")
    return projected_usage

if __name__ == "__main__":
    fake_recent_data = pd.DataFrame({
        'usage_rate': [31.5, 30.2, 33.1, 29.8, 32.4]
    })
    calculate_projected_usage(fake_recent_data, "Luka Doncic", injured_teammates=[])