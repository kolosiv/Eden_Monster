"""NHL Live Scores Module for Eden Analytics Pro.

Fetches real-time NHL game scores and status from the official NHL API.
"""

import requests
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from utils.logger import get_logger

logger = get_logger(__name__)


class GameState(Enum):
    """Game state enumeration."""
    LIVE = "LIVE"
    FINAL = "FINAL"
    SCHEDULED = "FUT"
    PREGAME = "PRE"
    CRITICAL = "CRIT"  # Last 5 minutes
    OFF = "OFF"  # Intermission
    POSTPONED = "PPD"
    

@dataclass
class GameInfo:
    """Represents a single NHL game."""
    game_id: int
    home_team: str
    away_team: str
    home_team_full: str
    away_team_full: str
    home_score: int = 0
    away_score: int = 0
    status: GameState = GameState.SCHEDULED
    period: int = 0
    period_descriptor: str = ""
    time_remaining: str = ""
    start_time_utc: str = ""
    venue: str = ""
    is_overtime: bool = False
    is_shootout: bool = False
    
    @property
    def display_status(self) -> str:
        """Get display-friendly status string."""
        if self.status == GameState.LIVE:
            if self.is_shootout:
                return "SO"
            elif self.is_overtime:
                return "OT"
            elif self.period_descriptor:
                return f"P{self.period}"
            return "LIVE"
        elif self.status == GameState.FINAL:
            if self.is_shootout:
                return "FINAL/SO"
            elif self.is_overtime:
                return "FINAL/OT"
            return "FINAL"
        elif self.status == GameState.OFF:
            return f"INT {self.period}"
        return self.status.value


class NHLLiveScores:
    """Fetches live NHL scores from the official NHL API."""
    
    def __init__(self):
        self.base_url = "https://api-web.nhle.com/v1"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
        })
        self._cache: Dict[str, Any] = {}
        self._cache_time: Optional[datetime] = None
        self.cache_duration = 15  # seconds
    
    def get_todays_games(self, use_cache: bool = True) -> List[GameInfo]:
        """Get all games for today.
        
        Args:
            use_cache: Whether to use cached data if available
            
        Returns:
            List of GameInfo objects for today's games
        """
        # Check cache
        if use_cache and self._is_cache_valid():
            return self._cache.get('games', [])
        
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        url = f"{self.base_url}/schedule/{today}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            games = []
            if 'gameWeek' in data:
                for day in data['gameWeek']:
                    if day.get('date') == today and 'games' in day:
                        for game in day['games']:
                            parsed = self._parse_game(game)
                            if parsed:
                                games.append(parsed)
            
            # Update cache
            self._cache['games'] = games
            self._cache_time = datetime.now(timezone.utc)
            
            logger.info(f"Fetched {len(games)} NHL games for today")
            return games
            
        except requests.RequestException as e:
            logger.error(f"Error fetching live scores: {e}")
            return self._cache.get('games', [])
        except Exception as e:
            logger.error(f"Unexpected error fetching live scores: {e}")
            return []
    
    def _parse_game(self, game_data: Dict) -> Optional[GameInfo]:
        """Parse game data from API response."""
        try:
            game_id = game_data.get('id', 0)
            
            # Teams
            home_team = game_data.get('homeTeam', {})
            away_team = game_data.get('awayTeam', {})
            
            home_abbrev = home_team.get('abbrev', 'UNK')
            away_abbrev = away_team.get('abbrev', 'UNK')
            
            # Handle team names - use placeName or name
            home_full = home_team.get('placeName', {})
            away_full = away_team.get('placeName', {})
            
            if isinstance(home_full, dict):
                home_full = home_full.get('default', home_abbrev)
            if isinstance(away_full, dict):
                away_full = away_full.get('default', away_abbrev)
            
            # Scores
            home_score = home_team.get('score', 0) or 0
            away_score = away_team.get('score', 0) or 0
            
            # Game state
            game_state_str = game_data.get('gameState', 'FUT')
            try:
                status = GameState(game_state_str)
            except ValueError:
                status = GameState.SCHEDULED
            
            # Period info
            period = game_data.get('period', 0) or 0
            period_descriptor = game_data.get('periodDescriptor', {})
            if isinstance(period_descriptor, dict):
                period_type = period_descriptor.get('periodType', '')
            else:
                period_type = ''
            
            is_overtime = period > 3 or period_type in ('OT', 'SO')
            is_shootout = period_type == 'SO'
            
            # Clock/time
            clock = game_data.get('clock', {})
            if isinstance(clock, dict):
                time_remaining = clock.get('timeRemaining', '')
                in_intermission = clock.get('inIntermission', False)
                if in_intermission:
                    status = GameState.OFF
            else:
                time_remaining = ''
            
            # Start time
            start_time = game_data.get('startTimeUTC', '')
            
            # Venue
            venue = game_data.get('venue', {})
            if isinstance(venue, dict):
                venue_name = venue.get('default', '')
            else:
                venue_name = str(venue) if venue else ''
            
            return GameInfo(
                game_id=game_id,
                home_team=home_abbrev,
                away_team=away_abbrev,
                home_team_full=str(home_full),
                away_team_full=str(away_full),
                home_score=home_score,
                away_score=away_score,
                status=status,
                period=period,
                period_descriptor=period_type,
                time_remaining=time_remaining,
                start_time_utc=start_time,
                venue=venue_name,
                is_overtime=is_overtime,
                is_shootout=is_shootout,
            )
            
        except Exception as e:
            logger.error(f"Error parsing game data: {e}")
            return None
    
    def get_game_details(self, game_id: int) -> Optional[Dict]:
        """Get detailed game information including boxscore.
        
        Args:
            game_id: NHL game ID
            
        Returns:
            Game details dict or None if error
        """
        url = f"{self.base_url}/gamecenter/{game_id}/boxscore"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching game details for {game_id}: {e}")
            return None
    
    def get_live_games(self) -> List[GameInfo]:
        """Get only currently live games.
        
        Returns:
            List of GameInfo for games currently in progress
        """
        games = self.get_todays_games()
        return [g for g in games if g.status in (GameState.LIVE, GameState.CRITICAL, GameState.OFF)]
    
    def get_final_games(self) -> List[GameInfo]:
        """Get only completed games.
        
        Returns:
            List of GameInfo for finished games
        """
        games = self.get_todays_games()
        return [g for g in games if g.status == GameState.FINAL]
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self._cache_time:
            return False
        elapsed = (datetime.now(timezone.utc) - self._cache_time).total_seconds()
        return elapsed < self.cache_duration
    
    def clear_cache(self):
        """Clear the cache."""
        self._cache.clear()
        self._cache_time = None
    
    def get_schedule(self, date: str = None) -> List[GameInfo]:
        """Get games for a specific date.
        
        Args:
            date: Date in YYYY-MM-DD format, defaults to today
            
        Returns:
            List of GameInfo for that date
        """
        if date is None:
            return self.get_todays_games(use_cache=False)
        
        url = f"{self.base_url}/schedule/{date}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            games = []
            if 'gameWeek' in data:
                for day in data['gameWeek']:
                    if day.get('date') == date and 'games' in day:
                        for game in day['games']:
                            parsed = self._parse_game(game)
                            if parsed:
                                games.append(parsed)
            
            return games
            
        except Exception as e:
            logger.error(f"Error fetching schedule for {date}: {e}")
            return []


# Module-level instance for convenience
_live_scores: Optional[NHLLiveScores] = None


def get_live_scores() -> NHLLiveScores:
    """Get the global live scores instance."""
    global _live_scores
    if _live_scores is None:
        _live_scores = NHLLiveScores()
    return _live_scores


__all__ = ['NHLLiveScores', 'GameInfo', 'GameState', 'get_live_scores']
