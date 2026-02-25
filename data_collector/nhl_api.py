"""NHL API Client for data collection.

Fetches historical game data, team statistics, and player statistics
from the NHL Stats API and alternative sources.
"""

import json
import hashlib
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

import requests

from utils.logger import get_logger

logger = get_logger(__name__)


# NHL API Base URLs (new API since 2023)
NHL_API_BASE = "https://api-web.nhle.com/v1"
NHL_STATS_API = "https://api.nhle.com/stats/rest/en"

# Cache settings
CACHE_DIR = Path("data/cache/nhl")
CACHE_TTL_HOURS = 6


@dataclass
class NHLGame:
    """Represents an NHL game."""
    game_id: str
    date: str
    home_team: str
    away_team: str
    home_team_id: int
    away_team_id: int
    home_score: int
    away_score: int
    period: str  # "REG", "OT", "SO"
    game_state: str
    home_shots: int = 0
    away_shots: int = 0
    season: str = ""
    game_type: str = ""  # "2" = regular season, "3" = playoffs


@dataclass  
class NHLTeamStats:
    """Team statistics for a season."""
    team_id: int
    team_name: str
    season: str
    games_played: int = 0
    wins: int = 0
    losses: int = 0
    ot_losses: int = 0
    points: int = 0
    goals_for: int = 0
    goals_against: int = 0
    power_play_pct: float = 0.0
    penalty_kill_pct: float = 0.0
    shots_per_game: float = 0.0
    shots_against_per_game: float = 0.0
    faceoff_win_pct: float = 0.0


@dataclass
class CacheEntry:
    """Cache entry with TTL."""
    data: Any
    timestamp: datetime
    ttl_hours: int = CACHE_TTL_HOURS
    
    def is_valid(self) -> bool:
        """Check if cache entry is still valid."""
        age = datetime.now() - self.timestamp
        return age < timedelta(hours=self.ttl_hours)


class NHLAPIClient:
    """NHL API Client for fetching historical data.
    
    Uses the new NHL API (api-web.nhle.com) as primary source
    with caching to avoid excessive API calls.
    
    Example:
        >>> client = NHLAPIClient()
        >>> games = client.fetch_games_for_season("20232024")
        >>> team_stats = client.fetch_team_stats("20232024")
    """
    
    # NHL Team abbreviations to full names
    TEAM_ABBREV = {
        "ANA": "Anaheim Ducks", "ARI": "Arizona Coyotes", "BOS": "Boston Bruins",
        "BUF": "Buffalo Sabres", "CGY": "Calgary Flames", "CAR": "Carolina Hurricanes",
        "CHI": "Chicago Blackhawks", "COL": "Colorado Avalanche", "CBJ": "Columbus Blue Jackets",
        "DAL": "Dallas Stars", "DET": "Detroit Red Wings", "EDM": "Edmonton Oilers",
        "FLA": "Florida Panthers", "LAK": "Los Angeles Kings", "MIN": "Minnesota Wild",
        "MTL": "Montreal Canadiens", "NSH": "Nashville Predators", "NJD": "New Jersey Devils",
        "NYI": "New York Islanders", "NYR": "New York Rangers", "OTT": "Ottawa Senators",
        "PHI": "Philadelphia Flyers", "PIT": "Pittsburgh Penguins", "SJS": "San Jose Sharks",
        "SEA": "Seattle Kraken", "STL": "St. Louis Blues", "TBL": "Tampa Bay Lightning",
        "TOR": "Toronto Maple Leafs", "UTA": "Utah Hockey Club", "VAN": "Vancouver Canucks",
        "VGK": "Vegas Golden Knights", "WSH": "Washington Capitals", "WPG": "Winnipeg Jets"
    }
    
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
    
    def __init__(self, cache_enabled: bool = True, rate_limit_delay: float = 0.5):
        """Initialize NHL API client.
        
        Args:
            cache_enabled: Enable response caching
            rate_limit_delay: Delay between API calls (seconds)
        """
        self.cache_enabled = cache_enabled
        self.rate_limit_delay = rate_limit_delay
        self._cache: Dict[str, CacheEntry] = {}
        self._last_request_time = 0
        
        # Ensure cache directory exists
        if cache_enabled:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            self._load_disk_cache()
    
    def _load_disk_cache(self) -> None:
        """Load cache from disk."""
        cache_file = CACHE_DIR / "api_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    for key, entry in data.items():
                        self._cache[key] = CacheEntry(
                            data=entry['data'],
                            timestamp=datetime.fromisoformat(entry['timestamp']),
                            ttl_hours=entry.get('ttl_hours', CACHE_TTL_HOURS)
                        )
                logger.info(f"Loaded {len(self._cache)} cached entries")
            except Exception as e:
                logger.warning(f"Could not load cache: {e}")
    
    def _save_disk_cache(self) -> None:
        """Save cache to disk."""
        if not self.cache_enabled:
            return
        
        cache_file = CACHE_DIR / "api_cache.json"
        try:
            data = {}
            for key, entry in self._cache.items():
                if entry.is_valid():
                    data[key] = {
                        'data': entry.data,
                        'timestamp': entry.timestamp.isoformat(),
                        'ttl_hours': entry.ttl_hours
                    }
            with open(cache_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.warning(f"Could not save cache: {e}")
    
    def _get_cache_key(self, endpoint: str, params: Dict = None) -> str:
        """Generate cache key for request."""
        key_str = endpoint + str(sorted(params.items()) if params else "")
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _rate_limit(self) -> None:
        """Implement rate limiting."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = time.time()
    
    def _request(
        self,
        endpoint: str,
        base_url: str = NHL_API_BASE,
        params: Dict = None,
        cache_ttl: int = CACHE_TTL_HOURS
    ) -> Optional[Dict]:
        """Make API request with caching and error handling.
        
        Args:
            endpoint: API endpoint
            base_url: Base URL to use
            params: Query parameters
            cache_ttl: Cache TTL in hours
            
        Returns:
            JSON response or None on error
        """
        cache_key = self._get_cache_key(f"{base_url}{endpoint}", params)
        
        # Check cache
        if self.cache_enabled and cache_key in self._cache:
            entry = self._cache[cache_key]
            if entry.is_valid():
                logger.debug(f"Cache hit for {endpoint}")
                return entry.data
        
        # Rate limit
        self._rate_limit()
        
        url = f"{base_url}{endpoint}"
        
        try:
            logger.debug(f"Fetching: {url}")
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 429:
                logger.warning("Rate limited, waiting 60 seconds...")
                time.sleep(60)
                return self._request(endpoint, base_url, params, cache_ttl)
            
            response.raise_for_status()
            data = response.json()
            
            # Cache response
            if self.cache_enabled:
                self._cache[cache_key] = CacheEntry(
                    data=data,
                    timestamp=datetime.now(),
                    ttl_hours=cache_ttl
                )
                self._save_disk_cache()
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return None
    
    def fetch_schedule(
        self,
        start_date: str,
        end_date: str
    ) -> List[NHLGame]:
        """Fetch game schedule for date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of NHLGame objects
        """
        games = []
        
        # Parse dates
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        # Fetch day by day (API limitation)
        current = start
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            endpoint = f"/schedule/{date_str}"
            
            data = self._request(endpoint)
            if data and 'gameWeek' in data:
                for day in data['gameWeek']:
                    for game in day.get('games', []):
                        parsed = self._parse_game(game)
                        if parsed:
                            games.append(parsed)
            
            current += timedelta(days=1)
        
        logger.info(f"Fetched {len(games)} games from {start_date} to {end_date}")
        return games
    
    def fetch_games_for_season(
        self,
        season: str = "20242025",
        game_type: str = "2"  # Regular season
    ) -> List[NHLGame]:
        """Fetch all games for a season.
        
        Args:
            season: Season string (e.g., "20232024")
            game_type: Game type ("2" = regular, "3" = playoffs)
            
        Returns:
            List of NHLGame objects
        """
        games = []
        
        # Calculate season date range
        start_year = int(season[:4])
        
        if game_type == "2":  # Regular season
            start_date = f"{start_year}-10-01"
            end_date = f"{start_year + 1}-04-30"
        else:  # Playoffs
            start_date = f"{start_year + 1}-04-01"
            end_date = f"{start_year + 1}-06-30"
        
        # Limit to current date if in future
        today = datetime.now().strftime("%Y-%m-%d")
        if end_date > today:
            end_date = today
        
        games = self.fetch_schedule(start_date, end_date)
        
        # Filter by game type and completed games
        filtered = [g for g in games if g.game_state in ("FINAL", "OFF")]
        
        logger.info(f"Found {len(filtered)} completed games for season {season}")
        return filtered
    
    def _parse_game(self, game_data: Dict) -> Optional[NHLGame]:
        """Parse game data from API response.
        
        Args:
            game_data: Raw game data from API
            
        Returns:
            NHLGame object or None
        """
        try:
            game_id = str(game_data.get('id', ''))
            
            home_team = game_data.get('homeTeam', {})
            away_team = game_data.get('awayTeam', {})
            
            # Determine period (regulation, OT, SO)
            period = "REG"
            period_desc = game_data.get('periodDescriptor', {})
            if period_desc:
                period_type = period_desc.get('periodType', '')
                if period_type == 'OT':
                    period = 'OT'
                elif period_type == 'SO':
                    period = 'SO'
                elif period_desc.get('number', 3) > 3:
                    period = 'OT'
            
            return NHLGame(
                game_id=game_id,
                date=game_data.get('gameDate', ''),
                home_team=home_team.get('abbrev', ''),
                away_team=away_team.get('abbrev', ''),
                home_team_id=home_team.get('id', 0),
                away_team_id=away_team.get('id', 0),
                home_score=home_team.get('score', 0),
                away_score=away_team.get('score', 0),
                period=period,
                game_state=game_data.get('gameState', ''),
                season=str(game_data.get('season', '')),
                game_type=str(game_data.get('gameType', ''))
            )
        except Exception as e:
            logger.warning(f"Could not parse game: {e}")
            return None
    
    def fetch_team_stats(self, season: str = "20242025") -> List[NHLTeamStats]:
        """Fetch team statistics for a season.
        
        Args:
            season: Season string
            
        Returns:
            List of NHLTeamStats objects
        """
        endpoint = f"/standings/{season}"
        data = self._request(endpoint)
        
        stats = []
        if data and 'standings' in data:
            for team_data in data['standings']:
                try:
                    stats.append(NHLTeamStats(
                        team_id=team_data.get('teamAbbrev', {}).get('default', 0),
                        team_name=team_data.get('teamName', {}).get('default', ''),
                        season=season,
                        games_played=team_data.get('gamesPlayed', 0),
                        wins=team_data.get('wins', 0),
                        losses=team_data.get('losses', 0),
                        ot_losses=team_data.get('otLosses', 0),
                        points=team_data.get('points', 0),
                        goals_for=team_data.get('goalFor', 0),
                        goals_against=team_data.get('goalAgainst', 0)
                    ))
                except Exception as e:
                    logger.warning(f"Could not parse team stats: {e}")
        
        logger.info(f"Fetched stats for {len(stats)} teams")
        return stats
    
    def fetch_team_schedule(
        self,
        team_abbrev: str,
        season: str = "20242025"
    ) -> List[NHLGame]:
        """Fetch schedule for a specific team.
        
        Args:
            team_abbrev: Team abbreviation (e.g., "TOR")
            season: Season string
            
        Returns:
            List of NHLGame objects
        """
        endpoint = f"/club-schedule-season/{team_abbrev}/{season}"
        data = self._request(endpoint)
        
        games = []
        if data and 'games' in data:
            for game in data['games']:
                parsed = self._parse_game(game)
                if parsed and parsed.game_state in ("FINAL", "OFF"):
                    games.append(parsed)
        
        return games
    
    def fetch_game_details(self, game_id: str) -> Optional[Dict]:
        """Fetch detailed game information.
        
        Args:
            game_id: Game ID
            
        Returns:
            Game details dict
        """
        endpoint = f"/gamecenter/{game_id}/boxscore"
        return self._request(endpoint)
    
    def get_team_division(self, team_abbrev: str) -> str:
        """Get division for a team."""
        for division, teams in self.DIVISIONS.items():
            if team_abbrev in teams:
                return division
        return "Unknown"
    
    def get_team_conference(self, team_abbrev: str) -> str:
        """Get conference for a team."""
        division = self.get_team_division(team_abbrev)
        for conf, divs in self.CONFERENCES.items():
            if division in divs:
                return conf
        return "Unknown"
    
    def are_same_division(self, team1: str, team2: str) -> bool:
        """Check if two teams are in the same division."""
        return self.get_team_division(team1) == self.get_team_division(team2)
    
    def are_same_conference(self, team1: str, team2: str) -> bool:
        """Check if two teams are in the same conference."""
        return self.get_team_conference(team1) == self.get_team_conference(team2)
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
        cache_file = CACHE_DIR / "api_cache.json"
        if cache_file.exists():
            cache_file.unlink()
        logger.info("Cache cleared")
