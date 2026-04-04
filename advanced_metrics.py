from nba_api.stats.endpoints import leaguedashteamstats
from nba_api.stats.static import teams

def get_opponent_metrics(abbr):
    try:
        team = [t for t in teams.get_teams() if t['abbreviation'] == abbr][0]
        df = leaguedashteamstats.LeagueDashTeamStats(measure_type_detailed_defense='Advanced').get_data_frames()[0]
        row = df[df['TEAM_NAME'] == team['full_name']]
        return row['DEF_RATING'].values[0], row['PACE'].values[0]
    except:
        return 115.0, 100.0 # League Average