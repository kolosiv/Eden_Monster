"""Demo Data Generator for Eden MVP.

Provides realistic mock NHL odds data for testing without API key.
"""

from datetime import datetime, timedelta
from typing import List
import random
import uuid

from core.odds_fetcher import MatchOdds, OddsData


# NHL Teams for demo
NHL_TEAMS = [
    ("Boston Bruins", "BOS"),
    ("Toronto Maple Leafs", "TOR"),
    ("Tampa Bay Lightning", "TBL"),
    ("Florida Panthers", "FLA"),
    ("New York Rangers", "NYR"),
    ("Carolina Hurricanes", "CAR"),
    ("New Jersey Devils", "NJD"),
    ("Vegas Golden Knights", "VGK"),
    ("Colorado Avalanche", "COL"),
    ("Dallas Stars", "DAL"),
    ("Edmonton Oilers", "EDM"),
    ("Winnipeg Jets", "WPG"),
    ("Minnesota Wild", "MIN"),
    ("Los Angeles Kings", "LAK"),
]

# Bookmakers
BOOKMAKERS = [
    "DraftKings", "FanDuel", "BetMGM", "Caesars", "PointsBet",
    "BetRivers", "Unibet", "Bet365", "Pinnacle", "Bovada"
]


def generate_demo_matches(num_matches: int = 6) -> List[MatchOdds]:
    """Generate realistic demo NHL match data with some arbitrage opportunities.
    
    Args:
        num_matches: Number of matches to generate (default 6)
        
    Returns:
        List of MatchOdds with bookmaker odds, including some arb opportunities
    """
    matches = []
    used_teams = set()
    
    # Shuffle teams
    teams = NHL_TEAMS.copy()
    random.shuffle(teams)
    
    for i in range(min(num_matches, len(teams) // 2)):
        home_team = teams[i * 2][0]
        away_team = teams[i * 2 + 1][0]
        
        # Create base odds - slight home advantage
        home_implied = random.uniform(0.42, 0.58)
        away_implied = 1 - home_implied
        
        # Base decimal odds
        base_home_odds = 1 / home_implied
        base_away_odds = 1 / away_implied
        
        bookmaker_odds = []
        
        # Generate odds for each bookmaker with variance
        for j, bookmaker in enumerate(random.sample(BOOKMAKERS, random.randint(5, 8))):
            # Add some variance (bookmaker margin + random variance)
            margin = random.uniform(0.02, 0.06)  # 2-6% margin
            variance = random.uniform(-0.08, 0.08)
            
            home_odds = base_home_odds * (1 - margin/2 + variance)
            away_odds = base_away_odds * (1 - margin/2 - variance)
            
            # Ensure odds are reasonable
            home_odds = max(1.15, min(5.5, home_odds))
            away_odds = max(1.15, min(5.5, away_odds))
            
            odds_data = OddsData(
                bookmaker=bookmaker,
                market="h2h",
                team_home=home_team,
                team_away=away_team,
                odds_home=round(home_odds, 2),
                odds_away=round(away_odds, 2),
                odds_draw=None,  # NHL doesn't have draws in h2h
                last_update=datetime.now() - timedelta(minutes=random.randint(1, 30))
            )
            bookmaker_odds.append(odds_data)
        
        # For first 2 matches, create strong arbitrage opportunities
        # These will have higher ROI and favorable odds structure for demonstration
        if i < 2:
            # Find highest home and away odds
            best_home_idx = max(range(len(bookmaker_odds)), key=lambda x: bookmaker_odds[x].odds_home)
            best_away_idx = max(range(len(bookmaker_odds)), key=lambda x: bookmaker_odds[x].odds_away)
            
            # Create strong arbitrage - boost odds significantly
            # For a "good" hockey arb, we want high favorite odds and moderate underdog odds
            bookmaker_odds[best_home_idx].odds_home *= random.uniform(1.06, 1.10)
            bookmaker_odds[best_away_idx].odds_away *= random.uniform(1.06, 1.10)
            
            bookmaker_odds[best_home_idx].odds_home = round(bookmaker_odds[best_home_idx].odds_home, 2)
            bookmaker_odds[best_away_idx].odds_away = round(bookmaker_odds[best_away_idx].odds_away, 2)
        
        # For match 3, create a borderline opportunity (CAUTION territory)
        elif i == 2:
            best_home_idx = max(range(len(bookmaker_odds)), key=lambda x: bookmaker_odds[x].odds_home)
            best_away_idx = max(range(len(bookmaker_odds)), key=lambda x: bookmaker_odds[x].odds_away)
            
            bookmaker_odds[best_home_idx].odds_home *= 1.04
            bookmaker_odds[best_away_idx].odds_away *= 1.04
            
            bookmaker_odds[best_home_idx].odds_home = round(bookmaker_odds[best_home_idx].odds_home, 2)
            bookmaker_odds[best_away_idx].odds_away = round(bookmaker_odds[best_away_idx].odds_away, 2)
        
        match = MatchOdds(
            match_id=str(uuid.uuid4())[:12],
            sport="icehockey_nhl",
            league="NHL",
            commence_time=datetime.now() + timedelta(hours=random.randint(2, 72)),
            team_home=home_team,
            team_away=away_team,
            bookmaker_odds=bookmaker_odds
        )
        matches.append(match)
    
    return matches


def get_demo_rate_limits() -> dict:
    """Get mock rate limit status."""
    return {
        "requests_remaining": 499,
        "requests_used": 1
    }
