"""Match-level feature extraction for ML model.

Extracts features related to the specific matchup between two teams.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from .team_features import TeamFeatures
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MatchFeatures:
    """Container for match-level features."""
    # Team identifiers
    home_team: str
    away_team: str
    
    # Head-to-head
    h2h_games_played: int = 0
    h2h_ot_rate: float = 0.23
    h2h_home_wins: int = 0
    h2h_away_wins: int = 0
    h2h_avg_total_goals: float = 5.4
    
    # Division/Conference
    same_division: bool = False
    same_conference: bool = True
    
    # Time factors
    day_of_week: int = 0  # 0=Monday, 6=Sunday
    month: int = 1
    season_progress: float = 0.5  # 0=start, 1=end
    
    # Rest differential
    rest_differential: int = 0  # home_rest - away_rest
    
    # Implied odds closeness (from betting markets)
    implied_closeness: float = 0.5
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'home_team': self.home_team,
            'away_team': self.away_team,
            'h2h_games_played': self.h2h_games_played,
            'h2h_ot_rate': self.h2h_ot_rate,
            'h2h_home_wins': self.h2h_home_wins,
            'h2h_away_wins': self.h2h_away_wins,
            'h2h_avg_total_goals': self.h2h_avg_total_goals,
            'same_division': self.same_division,
            'same_conference': self.same_conference,
            'day_of_week': self.day_of_week,
            'month': self.month,
            'season_progress': self.season_progress,
            'rest_differential': self.rest_differential,
            'implied_closeness': self.implied_closeness
        }


class MatchFeatureExtractor:
    """Extracts match-level features.
    
    Features extracted:
    - Head-to-head history
    - Division/conference matchup
    - Time factors (day of week, month, season progress)
    - Rest differential
    - Implied odds closeness
    
    Example:
        >>> extractor = MatchFeatureExtractor(storage, api_client)
        >>> features = extractor.extract("TOR", "BOS", "2024-01-15")
    """
    
    # Division mappings
    DIVISIONS = {
        "Atlantic": ["BOS", "BUF", "DET", "FLA", "MTL", "OTT", "TBL", "TOR"],
        "Metropolitan": ["CAR", "CBJ", "NJD", "NYI", "NYR", "PHI", "PIT", "WSH"],
        "Central": ["ARI", "CHI", "COL", "DAL", "MIN", "NSH", "STL", "WPG", "UTA"],
        "Pacific": ["ANA", "CGY", "EDM", "LAK", "SJS", "SEA", "VAN", "VGK"]
    }
    
    CONFERENCES = {
        "Eastern": ["Atlantic", "Metropolitan"],
        "Western": ["Central", "Pacific"]
    }
    
    def __init__(self, storage, api_client=None):
        """Initialize extractor.
        
        Args:
            storage: DataStorage instance
            api_client: NHLAPIClient instance (optional)
        """
        self.storage = storage
        self.api = api_client
    
    def extract(
        self,
        home_team: str,
        away_team: str,
        match_date: str = None,
        odds_home: float = None,
        odds_away: float = None
    ) -> MatchFeatures:
        """Extract features for a match.
        
        Args:
            home_team: Home team abbreviation
            away_team: Away team abbreviation
            match_date: Match date
            odds_home: Home team odds (optional)
            odds_away: Away team odds (optional)
            
        Returns:
            MatchFeatures object
        """
        # Calculate H2H stats
        h2h_stats = self._get_h2h_stats(home_team, away_team, match_date)
        
        # Division/Conference
        same_division = self._same_division(home_team, away_team)
        same_conference = self._same_conference(home_team, away_team)
        
        # Time factors
        if match_date:
            try:
                dt = datetime.fromisoformat(match_date.replace('Z', '+00:00'))
                day_of_week = dt.weekday()
                month = dt.month
                season_progress = self._calculate_season_progress(dt)
            except:
                day_of_week = 0
                month = 1
                season_progress = 0.5
        else:
            day_of_week = datetime.now().weekday()
            month = datetime.now().month
            season_progress = self._calculate_season_progress(datetime.now())
        
        # Implied closeness from odds
        implied_closeness = 0.5
        if odds_home and odds_away:
            implied_home = 1 / odds_home
            implied_away = 1 / odds_away
            total = implied_home + implied_away
            implied_closeness = 1 - abs((implied_home / total) - 0.5) * 2
        
        return MatchFeatures(
            home_team=home_team,
            away_team=away_team,
            h2h_games_played=h2h_stats.get('games_played', 0),
            h2h_ot_rate=h2h_stats.get('ot_rate', 0.23),
            h2h_home_wins=h2h_stats.get('home_wins', 0),
            h2h_away_wins=h2h_stats.get('away_wins', 0),
            h2h_avg_total_goals=h2h_stats.get('avg_total_goals', 5.4),
            same_division=same_division,
            same_conference=same_conference,
            day_of_week=day_of_week,
            month=month,
            season_progress=season_progress,
            implied_closeness=implied_closeness
        )
    
    def _get_h2h_stats(
        self,
        home_team: str,
        away_team: str,
        before_date: str = None,
        limit: int = 10
    ) -> Dict:
        """Get head-to-head statistics."""
        games = self.storage.get_h2h_games(home_team, away_team, limit)
        
        if before_date:
            games = [g for g in games if g['date'] < before_date]
        
        if not games:
            return {
                'games_played': 0,
                'ot_rate': 0.23,
                'home_wins': 0,
                'away_wins': 0,
                'avg_total_goals': 5.4
            }
        
        ot_games = sum(1 for g in games if g['went_to_ot'])
        total_goals = sum(g['home_score'] + g['away_score'] for g in games)
        
        # Count wins for home_team when they were actually home
        home_wins = sum(
            1 for g in games 
            if g['home_team'] == home_team and g['home_score'] > g['away_score']
        )
        # Count wins for home_team when they were away
        home_wins += sum(
            1 for g in games
            if g['away_team'] == home_team and g['away_score'] > g['home_score']
        )
        
        return {
            'games_played': len(games),
            'ot_rate': ot_games / len(games),
            'home_wins': home_wins,
            'away_wins': len(games) - home_wins,
            'avg_total_goals': total_goals / len(games)
        }
    
    def _get_division(self, team: str) -> str:
        """Get division for a team."""
        for division, teams in self.DIVISIONS.items():
            if team in teams:
                return division
        return "Unknown"
    
    def _get_conference(self, team: str) -> str:
        """Get conference for a team."""
        division = self._get_division(team)
        for conf, divs in self.CONFERENCES.items():
            if division in divs:
                return conf
        return "Unknown"
    
    def _same_division(self, team1: str, team2: str) -> bool:
        """Check if two teams are in the same division."""
        return self._get_division(team1) == self._get_division(team2)
    
    def _same_conference(self, team1: str, team2: str) -> bool:
        """Check if two teams are in the same conference."""
        return self._get_conference(team1) == self._get_conference(team2)
    
    def _calculate_season_progress(self, date: datetime) -> float:
        """Calculate season progress (0-1).
        
        NHL regular season: October to April
        0.0 = start of season (October 1)
        1.0 = end of regular season (April 15)
        """
        month = date.month
        day = date.day
        
        # Season starts in October
        if month >= 10:  # October-December
            # October 1 = 0.0, December 31 = ~0.5
            days_from_start = (month - 10) * 30 + day
            total_first_half = 92  # Oct + Nov + Dec
            return min(0.5, days_from_start / total_first_half * 0.5)
        elif month <= 4:  # January-April
            # January 1 = 0.5, April 15 = 1.0
            days_from_jan = (month - 1) * 30 + day
            total_second_half = 105  # Jan + Feb + Mar + Apr
            return 0.5 + min(0.5, days_from_jan / total_second_half * 0.5)
        else:
            # Off-season, return middle value
            return 0.5
    
    def calculate_rest_differential(
        self,
        home_features: TeamFeatures,
        away_features: TeamFeatures
    ) -> int:
        """Calculate rest differential.
        
        Args:
            home_features: Home team features
            away_features: Away team features
            
        Returns:
            Rest differential (positive = home has more rest)
        """
        return home_features.days_rest - away_features.days_rest
