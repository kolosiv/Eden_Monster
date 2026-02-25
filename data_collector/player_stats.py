"""Player Statistics Module.

Fetches goalie and player statistics from NHL API.
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pydantic import BaseModel
import time

from utils.logger import get_logger

logger = get_logger(__name__)


class GoalieStats(BaseModel):
    """Goalie statistics model."""
    player_id: int
    name: str
    team: str
    team_abbrev: str
    season: str
    games_played: int = 0
    wins: int = 0
    losses: int = 0
    ot_losses: int = 0
    save_percentage: float = 0.0
    goals_against_average: float = 0.0
    shutouts: int = 0
    saves: int = 0
    shots_against: int = 0
    time_on_ice: int = 0  # in minutes
    is_starter: bool = False
    # Recent form
    last_5_sv_pct: float = 0.0
    last_5_gaa: float = 0.0
    days_since_last_game: int = 0


class PlayerStats(BaseModel):
    """Player statistics model (forward/defense)."""
    player_id: int
    name: str
    team: str
    team_abbrev: str
    position: str  # F, D, C, RW, LW
    season: str
    games_played: int = 0
    goals: int = 0
    assists: int = 0
    points: int = 0
    plus_minus: int = 0
    shots: int = 0
    shooting_pct: float = 0.0
    time_on_ice_avg: float = 0.0  # per game
    power_play_points: int = 0
    game_winning_goals: int = 0
    ot_goals: int = 0
    hits: int = 0
    blocked_shots: int = 0
    # Recent form
    last_5_points: int = 0
    points_per_game: float = 0.0


class InjuryInfo(BaseModel):
    """Injury information model."""
    player_id: int
    name: str
    team: str
    team_abbrev: str
    position: str
    injury_status: str  # IR, DTD, Out, etc.
    injury_type: str = ""
    expected_return: Optional[str] = None
    games_missed: int = 0
    impact_score: float = 0.0  # Player importance
    points_per_game: float = 0.0  # Impact measure


class PlayerStatsCollector:
    """Collects player statistics from NHL API.
    
    Fetches goalie stats, skater stats, and injury data.
    
    Example:
        >>> collector = PlayerStatsCollector()
        >>> goalies = collector.fetch_team_goalies("TOR")
        >>> injuries = collector.fetch_team_injuries("BOS")
    """
    
    BASE_URL = "https://api-web.nhle.com"
    STATS_URL = "https://api.nhle.com/stats/rest/en"
    
    def __init__(self):
        """Initialize player stats collector."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json'
        })
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 3600  # 1 hour
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached data if still valid."""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if datetime.now().timestamp() - timestamp < self._cache_ttl:
                return data
        return None
    
    def _set_cache(self, key: str, data: Any) -> None:
        """Cache data with timestamp."""
        self._cache[key] = (data, datetime.now().timestamp())
    
    def _make_request(self, url: str, retries: int = 3) -> Optional[Dict]:
        """Make API request with retry logic."""
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt < retries - 1:
                    time.sleep(1 * (attempt + 1))
        return None
    
    def fetch_team_goalies(
        self,
        team_abbrev: str,
        season: str = None
    ) -> List[GoalieStats]:
        """Fetch goalie statistics for a team.
        
        Args:
            team_abbrev: Team abbreviation (e.g., "TOR")
            season: Season string (e.g., "20232024")
            
        Returns:
            List of GoalieStats
        """
        if not season:
            now = datetime.now()
            season = f"{now.year}{now.year + 1}" if now.month >= 10 else f"{now.year - 1}{now.year}"
        
        cache_key = f"goalies_{team_abbrev}_{season}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        url = f"{self.STATS_URL}/goalie/summary?cayenneExp=seasonId={season}%20and%20teamAbbrevs='{team_abbrev}'"
        
        data = self._make_request(url)
        if not data or 'data' not in data:
            logger.warning(f"No goalie data for {team_abbrev}")
            return []
        
        goalies = []
        for g in data.get('data', []):
            try:
                goalie = GoalieStats(
                    player_id=g.get('playerId', 0),
                    name=f"{g.get('goalieFullName', 'Unknown')}",
                    team=g.get('teamFullName', team_abbrev),
                    team_abbrev=team_abbrev,
                    season=season,
                    games_played=g.get('gamesPlayed', 0),
                    wins=g.get('wins', 0),
                    losses=g.get('losses', 0),
                    ot_losses=g.get('otLosses', 0),
                    save_percentage=g.get('savePct', 0.0),
                    goals_against_average=g.get('goalsAgainstAverage', 0.0),
                    shutouts=g.get('shutouts', 0),
                    saves=g.get('saves', 0),
                    shots_against=g.get('shotsAgainst', 0),
                    time_on_ice=g.get('timeOnIce', 0),
                    is_starter=g.get('gamesPlayed', 0) > 30  # Simple heuristic
                )
                goalies.append(goalie)
            except Exception as e:
                logger.warning(f"Error parsing goalie data: {e}")
        
        # Sort by games played (starter first)
        goalies.sort(key=lambda x: x.games_played, reverse=True)
        
        self._set_cache(cache_key, goalies)
        return goalies
    
    def fetch_team_players(
        self,
        team_abbrev: str,
        season: str = None,
        position: str = None
    ) -> List[PlayerStats]:
        """Fetch player statistics for a team.
        
        Args:
            team_abbrev: Team abbreviation
            season: Season string
            position: Filter by position (F, D)
            
        Returns:
            List of PlayerStats
        """
        if not season:
            now = datetime.now()
            season = f"{now.year}{now.year + 1}" if now.month >= 10 else f"{now.year - 1}{now.year}"
        
        cache_key = f"players_{team_abbrev}_{season}_{position or 'all'}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        position_filter = ""
        if position:
            if position == 'F':
                position_filter = "%20and%20positionCode%20in%20('C','L','R')"
            else:
                position_filter = f"%20and%20positionCode='{position}'"
        
        url = f"{self.STATS_URL}/skater/summary?cayenneExp=seasonId={season}%20and%20teamAbbrevs='{team_abbrev}'{position_filter}"
        
        data = self._make_request(url)
        if not data or 'data' not in data:
            logger.warning(f"No player data for {team_abbrev}")
            return []
        
        players = []
        for p in data.get('data', []):
            try:
                games_played = p.get('gamesPlayed', 1) or 1
                points = p.get('points', 0)
                
                player = PlayerStats(
                    player_id=p.get('playerId', 0),
                    name=p.get('skaterFullName', 'Unknown'),
                    team=p.get('teamFullName', team_abbrev),
                    team_abbrev=team_abbrev,
                    position=p.get('positionCode', 'F'),
                    season=season,
                    games_played=games_played,
                    goals=p.get('goals', 0),
                    assists=p.get('assists', 0),
                    points=points,
                    plus_minus=p.get('plusMinus', 0),
                    shots=p.get('shots', 0),
                    shooting_pct=p.get('shootingPct', 0.0),
                    time_on_ice_avg=p.get('timeOnIcePerGame', 0.0),
                    power_play_points=p.get('ppPoints', 0),
                    game_winning_goals=p.get('gameWinningGoals', 0),
                    ot_goals=p.get('otGoals', 0),
                    points_per_game=points / games_played if games_played > 0 else 0.0
                )
                players.append(player)
            except Exception as e:
                logger.warning(f"Error parsing player data: {e}")
        
        # Sort by points
        players.sort(key=lambda x: x.points, reverse=True)
        
        self._set_cache(cache_key, players)
        return players
    
    def fetch_team_injuries(
        self,
        team_abbrev: str
    ) -> List[InjuryInfo]:
        """Fetch current injury information for a team.
        
        Args:
            team_abbrev: Team abbreviation
            
        Returns:
            List of InjuryInfo
        """
        cache_key = f"injuries_{team_abbrev}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        # NHL API doesn't have official injury endpoint, 
        # we'll create placeholder data structure
        # In production, this would fetch from a reliable injury data source
        injuries = []
        
        self._set_cache(cache_key, injuries)
        return injuries
    
    def fetch_team_top_scorers(
        self,
        team_abbrev: str,
        season: str = None,
        top_n: int = 6
    ) -> List[PlayerStats]:
        """Fetch top N scorers for a team.
        
        Args:
            team_abbrev: Team abbreviation
            season: Season string
            top_n: Number of top scorers
            
        Returns:
            List of top scorers
        """
        players = self.fetch_team_players(team_abbrev, season, position='F')
        return players[:top_n] if players else []
    
    def fetch_team_top_defenders(
        self,
        team_abbrev: str,
        season: str = None,
        top_n: int = 4
    ) -> List[PlayerStats]:
        """Fetch top N defenders for a team.
        
        Args:
            team_abbrev: Team abbreviation
            season: Season string
            top_n: Number of top defenders
            
        Returns:
            List of top defenders
        """
        players = self.fetch_team_players(team_abbrev, season, position='D')
        return players[:top_n] if players else []
    
    def get_starting_goalie(
        self,
        team_abbrev: str,
        season: str = None
    ) -> Optional[GoalieStats]:
        """Get the likely starting goalie for a team.
        
        Args:
            team_abbrev: Team abbreviation
            season: Season string
            
        Returns:
            Starting goalie or None
        """
        goalies = self.fetch_team_goalies(team_abbrev, season)
        if goalies:
            return goalies[0]  # Most games played = starter
        return None
    
    def calculate_team_injury_impact(
        self,
        team_abbrev: str,
        season: str = None
    ) -> Dict[str, float]:
        """Calculate the impact of current injuries on a team.
        
        Args:
            team_abbrev: Team abbreviation
            season: Season string
            
        Returns:
            Dict with impact metrics
        """
        injuries = self.fetch_team_injuries(team_abbrev)
        
        if not injuries:
            return {
                'total_injuries': 0,
                'total_points_lost': 0.0,
                'key_players_out': 0,
                'impact_score': 0.0
            }
        
        total_points = sum(i.points_per_game for i in injuries)
        key_players = sum(1 for i in injuries if i.impact_score > 0.7)
        avg_impact = sum(i.impact_score for i in injuries) / len(injuries) if injuries else 0
        
        return {
            'total_injuries': len(injuries),
            'total_points_lost': total_points,
            'key_players_out': key_players,
            'impact_score': avg_impact
        }
    
    def get_team_offensive_power(
        self,
        team_abbrev: str,
        season: str = None
    ) -> Dict[str, float]:
        """Calculate offensive power based on top 6 forwards.
        
        Args:
            team_abbrev: Team abbreviation
            season: Season string
            
        Returns:
            Dict with offensive metrics
        """
        top_scorers = self.fetch_team_top_scorers(team_abbrev, season, top_n=6)
        
        if not top_scorers:
            return {
                'top6_points': 0,
                'top6_goals': 0,
                'top6_ppg': 0.0,
                'top6_shooting_pct': 0.0
            }
        
        total_points = sum(p.points for p in top_scorers)
        total_goals = sum(p.goals for p in top_scorers)
        avg_ppg = sum(p.points_per_game for p in top_scorers) / len(top_scorers)
        avg_shooting = sum(p.shooting_pct for p in top_scorers) / len(top_scorers)
        
        return {
            'top6_points': total_points,
            'top6_goals': total_goals,
            'top6_ppg': avg_ppg,
            'top6_shooting_pct': avg_shooting
        }
    
    def get_team_defensive_power(
        self,
        team_abbrev: str,
        season: str = None
    ) -> Dict[str, float]:
        """Calculate defensive power based on top 4 defensemen.
        
        Args:
            team_abbrev: Team abbreviation
            season: Season string
            
        Returns:
            Dict with defensive metrics
        """
        top_defenders = self.fetch_team_top_defenders(team_abbrev, season, top_n=4)
        
        if not top_defenders:
            return {
                'top4_points': 0,
                'top4_plus_minus': 0,
                'top4_toi_avg': 0.0,
                'top4_blocked': 0
            }
        
        total_points = sum(p.points for p in top_defenders)
        total_pm = sum(p.plus_minus for p in top_defenders)
        avg_toi = sum(p.time_on_ice_avg for p in top_defenders) / len(top_defenders)
        total_blocked = sum(p.blocked_shots for p in top_defenders)
        
        return {
            'top4_points': total_points,
            'top4_plus_minus': total_pm,
            'top4_toi_avg': avg_toi,
            'top4_blocked': total_blocked
        }
