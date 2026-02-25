"""Historical Data Fetcher for Eden MVP.

Fetches and prepares historical NHL data for ML model training.
"""

import json
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import sqlite3

import requests
from pydantic import BaseModel

from utils.logger import get_logger

logger = get_logger(__name__)


# NHL Team Data (simplified for MVP)
NHL_TEAMS = {
    "Boston Bruins": {"division": "Atlantic", "conference": "Eastern"},
    "Buffalo Sabres": {"division": "Atlantic", "conference": "Eastern"},
    "Detroit Red Wings": {"division": "Atlantic", "conference": "Eastern"},
    "Florida Panthers": {"division": "Atlantic", "conference": "Eastern"},
    "Montreal Canadiens": {"division": "Atlantic", "conference": "Eastern"},
    "Ottawa Senators": {"division": "Atlantic", "conference": "Eastern"},
    "Tampa Bay Lightning": {"division": "Atlantic", "conference": "Eastern"},
    "Toronto Maple Leafs": {"division": "Atlantic", "conference": "Eastern"},
    "Carolina Hurricanes": {"division": "Metropolitan", "conference": "Eastern"},
    "Columbus Blue Jackets": {"division": "Metropolitan", "conference": "Eastern"},
    "New Jersey Devils": {"division": "Metropolitan", "conference": "Eastern"},
    "New York Islanders": {"division": "Metropolitan", "conference": "Eastern"},
    "New York Rangers": {"division": "Metropolitan", "conference": "Eastern"},
    "Philadelphia Flyers": {"division": "Metropolitan", "conference": "Eastern"},
    "Pittsburgh Penguins": {"division": "Metropolitan", "conference": "Eastern"},
    "Washington Capitals": {"division": "Metropolitan", "conference": "Eastern"},
    "Arizona Coyotes": {"division": "Central", "conference": "Western"},
    "Chicago Blackhawks": {"division": "Central", "conference": "Western"},
    "Colorado Avalanche": {"division": "Central", "conference": "Western"},
    "Dallas Stars": {"division": "Central", "conference": "Western"},
    "Minnesota Wild": {"division": "Central", "conference": "Western"},
    "Nashville Predators": {"division": "Central", "conference": "Western"},
    "St. Louis Blues": {"division": "Central", "conference": "Western"},
    "Winnipeg Jets": {"division": "Central", "conference": "Western"},
    "Anaheim Ducks": {"division": "Pacific", "conference": "Western"},
    "Calgary Flames": {"division": "Pacific", "conference": "Western"},
    "Edmonton Oilers": {"division": "Pacific", "conference": "Western"},
    "Los Angeles Kings": {"division": "Pacific", "conference": "Western"},
    "San Jose Sharks": {"division": "Pacific", "conference": "Western"},
    "Seattle Kraken": {"division": "Pacific", "conference": "Western"},
    "Vancouver Canucks": {"division": "Pacific", "conference": "Western"},
    "Vegas Golden Knights": {"division": "Pacific", "conference": "Western"},
}


class HistoricalMatch(BaseModel):
    """Historical match data for ML training."""
    match_id: str
    date: str
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    went_to_ot: bool
    ot_winner: Optional[str] = None
    
    # Team stats at time of match
    home_goals_for_avg: float = 0.0
    home_goals_against_avg: float = 0.0
    away_goals_for_avg: float = 0.0
    away_goals_against_avg: float = 0.0
    home_win_rate: float = 0.5
    away_win_rate: float = 0.5
    home_ot_win_rate: float = 0.5
    away_ot_win_rate: float = 0.5
    home_recent_form: float = 0.5
    away_recent_form: float = 0.5
    home_days_rest: int = 2
    away_days_rest: int = 2
    h2h_home_wins: int = 0
    h2h_away_wins: int = 0
    h2h_ot_games: int = 0
    home_special_teams: float = 0.5  # PP% + PK% / 2
    away_special_teams: float = 0.5
    same_division: bool = False
    same_conference: bool = False
    
    # Odds data if available
    home_odds: Optional[float] = None
    away_odds: Optional[float] = None
    implied_ot_prob: Optional[float] = None


class HistoricalDataFetcher:
    """Fetches and prepares historical NHL data for ML training."""
    
    def __init__(self, data_dir: str = "data/historical"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "historical_matches.db"
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize historical data database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS matches (
                    match_id TEXT PRIMARY KEY,
                    date TEXT,
                    home_team TEXT,
                    away_team TEXT,
                    home_goals INTEGER,
                    away_goals INTEGER,
                    went_to_ot INTEGER,
                    ot_winner TEXT,
                    data_json TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(date)
            """)
            conn.commit()
    
    def generate_synthetic_data(self, num_matches: int = 500) -> List[HistoricalMatch]:
        """Generate synthetic historical data for initial training.
        
        This provides realistic-looking data based on NHL statistics.
        In production, this would be replaced with real API data.
        """
        logger.info(f"Generating {num_matches} synthetic historical matches...")
        
        matches = []
        teams = list(NHL_TEAMS.keys())
        
        # Historical OT rate is ~23%
        ot_rate = 0.23
        
        for i in range(num_matches):
            # Random date in past 2 seasons
            days_ago = random.randint(1, 730)
            match_date = datetime.now() - timedelta(days=days_ago)
            
            # Random teams
            home_team = random.choice(teams)
            away_team = random.choice([t for t in teams if t != home_team])
            
            # Check division/conference
            same_div = NHL_TEAMS[home_team]["division"] == NHL_TEAMS[away_team]["division"]
            same_conf = NHL_TEAMS[home_team]["conference"] == NHL_TEAMS[away_team]["conference"]
            
            # Generate team stats (slight home advantage)
            home_gf = 2.5 + random.gauss(0.3, 0.3)
            home_ga = 2.5 + random.gauss(0, 0.3)
            away_gf = 2.5 + random.gauss(0, 0.3)
            away_ga = 2.5 + random.gauss(0.1, 0.3)
            
            home_win_rate = 0.5 + random.gauss(0.05, 0.15)  # Slight home advantage
            away_win_rate = 0.5 + random.gauss(-0.02, 0.15)
            
            # Clamp values
            home_win_rate = max(0.25, min(0.75, home_win_rate))
            away_win_rate = max(0.25, min(0.75, away_win_rate))
            
            # Recent form (0-1)
            home_form = random.betavariate(5, 5)
            away_form = random.betavariate(5, 5)
            
            # Days rest (back-to-back games increase OT likelihood slightly)
            home_rest = random.choices([1, 2, 3, 4, 5], weights=[15, 40, 25, 15, 5])[0]
            away_rest = random.choices([1, 2, 3, 4, 5], weights=[15, 40, 25, 15, 5])[0]
            
            # H2H history
            h2h_games = random.randint(2, 10)
            h2h_home = random.randint(0, h2h_games)
            h2h_away = h2h_games - h2h_home
            h2h_ot = random.randint(0, min(3, h2h_games))
            
            # Special teams
            home_st = 0.5 + random.gauss(0, 0.1)
            away_st = 0.5 + random.gauss(0, 0.1)
            
            # OT win rates
            home_ot_wr = 0.55 + random.gauss(0, 0.1)  # Slight favorite advantage
            away_ot_wr = 0.45 + random.gauss(0, 0.1)
            
            # Determine if game goes to OT
            # Factors that increase OT probability:
            # - Teams are evenly matched (close win rates)
            # - Division rivals
            # - Back-to-back games (fatigue)
            win_diff = abs(home_win_rate - away_win_rate)
            ot_modifier = 1.0
            if win_diff < 0.1:  # Evenly matched
                ot_modifier *= 1.3
            if same_div:
                ot_modifier *= 1.1
            if home_rest == 1 or away_rest == 1:
                ot_modifier *= 1.05
            
            adjusted_ot_rate = min(0.35, ot_rate * ot_modifier)
            went_to_ot = random.random() < adjusted_ot_rate
            
            # Generate score
            if went_to_ot:
                # Tied game going to OT
                tied_score = random.choices([1, 2, 3, 4], weights=[15, 40, 35, 10])[0]
                home_goals = tied_score
                away_goals = tied_score
                
                # Who wins in OT? Factor in OT win rates
                home_ot_prob = (home_ot_wr + home_form * 0.1 + home_win_rate * 0.1) / 1.2
                ot_winner = home_team if random.random() < home_ot_prob else away_team
            else:
                # Regulation result
                # Stronger team more likely to win
                home_strength = home_win_rate + home_form * 0.1 + 0.05  # Home advantage
                home_wins = random.random() < home_strength
                
                if home_wins:
                    home_goals = random.choices([2, 3, 4, 5, 6], weights=[15, 35, 30, 15, 5])[0]
                    away_goals = random.choices([0, 1, 2, 3], weights=[15, 35, 35, 15])[0]
                    if away_goals >= home_goals:
                        away_goals = home_goals - 1
                else:
                    away_goals = random.choices([2, 3, 4, 5, 6], weights=[15, 35, 30, 15, 5])[0]
                    home_goals = random.choices([0, 1, 2, 3], weights=[15, 35, 35, 15])[0]
                    if home_goals >= away_goals:
                        home_goals = away_goals - 1
                
                ot_winner = None
            
            # Generate odds (based on win rates)
            # FIXED: Updated to realistic bookmaker margin (8% instead of 5%)
            home_implied = home_win_rate + 0.02  # Home edge
            away_implied = 1 - home_implied
            margin = 1.08  # FIXED: Realistic 8% bookmaker margin (was 5%)
            
            home_odds = margin / home_implied if home_implied > 0 else 2.0
            away_odds = margin / away_implied if away_implied > 0 else 2.0
            
            match = HistoricalMatch(
                match_id=f"hist_{i:05d}",
                date=match_date.strftime("%Y-%m-%d"),
                home_team=home_team,
                away_team=away_team,
                home_goals=max(0, home_goals),
                away_goals=max(0, away_goals),
                went_to_ot=went_to_ot,
                ot_winner=ot_winner,
                home_goals_for_avg=home_gf,
                home_goals_against_avg=home_ga,
                away_goals_for_avg=away_gf,
                away_goals_against_avg=away_ga,
                home_win_rate=home_win_rate,
                away_win_rate=away_win_rate,
                home_ot_win_rate=home_ot_wr,
                away_ot_win_rate=away_ot_wr,
                home_recent_form=home_form,
                away_recent_form=away_form,
                home_days_rest=home_rest,
                away_days_rest=away_rest,
                h2h_home_wins=h2h_home,
                h2h_away_wins=h2h_away,
                h2h_ot_games=h2h_ot,
                home_special_teams=max(0.3, min(0.7, home_st)),
                away_special_teams=max(0.3, min(0.7, away_st)),
                same_division=same_div,
                same_conference=same_conf,
                home_odds=home_odds,
                away_odds=away_odds,
                implied_ot_prob=adjusted_ot_rate
            )
            matches.append(match)
        
        # Save to database
        self._save_matches(matches)
        
        logger.info(f"Generated {len(matches)} historical matches")
        ot_count = sum(1 for m in matches if m.went_to_ot)
        logger.info(f"OT rate: {ot_count/len(matches):.1%}")
        
        return matches
    
    def _save_matches(self, matches: List[HistoricalMatch]) -> None:
        """Save matches to database."""
        with sqlite3.connect(self.db_path) as conn:
            for match in matches:
                conn.execute("""
                    INSERT OR REPLACE INTO matches
                    (match_id, date, home_team, away_team, home_goals, away_goals,
                     went_to_ot, ot_winner, data_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    match.match_id,
                    match.date,
                    match.home_team,
                    match.away_team,
                    match.home_goals,
                    match.away_goals,
                    1 if match.went_to_ot else 0,
                    match.ot_winner,
                    match.model_dump_json()
                ))
            conn.commit()
    
    def load_matches(self, limit: int = None) -> List[HistoricalMatch]:
        """Load matches from database."""
        with sqlite3.connect(self.db_path) as conn:
            query = "SELECT data_json FROM matches ORDER BY date DESC"
            if limit:
                query += f" LIMIT {limit}"
            
            cursor = conn.execute(query)
            matches = []
            for row in cursor:
                data = json.loads(row[0])
                matches.append(HistoricalMatch(**data))
            
            return matches
    
    def get_training_data(self, num_samples: int = 500) -> Tuple[List[Dict], List[int]]:
        """Get training data in ML-ready format.
        
        Returns:
            X: List of feature dictionaries
            y: List of labels (1 = went to OT, 0 = didn't)
        """
        matches = self.load_matches(num_samples)
        
        if len(matches) < 100:
            logger.info("Insufficient data, generating synthetic matches...")
            matches = self.generate_synthetic_data(num_samples)
        
        X = []
        y = []
        
        for match in matches:
            features = self._extract_features(match)
            X.append(features)
            y.append(1 if match.went_to_ot else 0)
        
        return X, y
    
    def _extract_features(self, match: HistoricalMatch) -> Dict:
        """Extract ML features from a match."""
        return {
            # Team scoring
            "home_gf_avg": match.home_goals_for_avg,
            "home_ga_avg": match.home_goals_against_avg,
            "away_gf_avg": match.away_goals_for_avg,
            "away_ga_avg": match.away_goals_against_avg,
            "goal_diff_home": match.home_goals_for_avg - match.home_goals_against_avg,
            "goal_diff_away": match.away_goals_for_avg - match.away_goals_against_avg,
            
            # Win rates
            "home_win_rate": match.home_win_rate,
            "away_win_rate": match.away_win_rate,
            "win_rate_diff": abs(match.home_win_rate - match.away_win_rate),
            
            # OT history
            "home_ot_win_rate": match.home_ot_win_rate,
            "away_ot_win_rate": match.away_ot_win_rate,
            
            # Form
            "home_form": match.home_recent_form,
            "away_form": match.away_recent_form,
            "form_diff": abs(match.home_recent_form - match.away_recent_form),
            
            # Fatigue
            "home_rest_days": match.home_days_rest,
            "away_rest_days": match.away_days_rest,
            "home_back_to_back": 1 if match.home_days_rest == 1 else 0,
            "away_back_to_back": 1 if match.away_days_rest == 1 else 0,
            
            # H2H
            "h2h_home_dominance": match.h2h_home_wins / max(1, match.h2h_home_wins + match.h2h_away_wins),
            "h2h_ot_rate": match.h2h_ot_games / max(1, match.h2h_home_wins + match.h2h_away_wins),
            
            # Special teams
            "home_special_teams": match.home_special_teams,
            "away_special_teams": match.away_special_teams,
            
            # Division/Conference
            "same_division": 1 if match.same_division else 0,
            "same_conference": 1 if match.same_conference else 0,
            
            # Odds-derived
            "implied_closeness": 1 - abs(1/match.home_odds - 0.5) * 2 if match.home_odds else 0.5,
        }
