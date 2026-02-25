"""Odds Fetcher Module for Eden MVP.

Fetches NHL odds from The Odds API and Belarusian bookmakers with caching and error handling.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

import requests
from pydantic import BaseModel, Field, validator

from utils.logger import get_logger

logger = get_logger(__name__)

# Try to import Fonbet API (primary bookmaker)
try:
    from core.bookmakers.fonbet_api import FonbetAPI, FonbetOddsMonitor, FonbetOdds
    FONBET_AVAILABLE = True
except ImportError:
    FONBET_AVAILABLE = False
    FonbetOddsMonitor = None
    logger.info("Fonbet API module not available")

# Try to import Belarusian bookmakers
try:
    from core.bookmakers.belarusian import BelarusianBookmakers, BookmakerOdds
    BELARUSIAN_AVAILABLE = True
except ImportError:
    BELARUSIAN_AVAILABLE = False
    logger.info("Belarusian bookmakers module not available")


class Market(str, Enum):
    """Betting market types."""
    H2H = "h2h"
    SPREADS = "spreads"
    TOTALS = "totals"


class OddsData(BaseModel):
    """Model for odds data from a bookmaker."""
    bookmaker: str
    market: str
    team_home: str
    team_away: str
    odds_home: float = Field(gt=1.0)
    odds_away: float = Field(gt=1.0)
    odds_draw: Optional[float] = Field(default=None, gt=1.0)
    last_update: datetime
    
    @validator('odds_home', 'odds_away', 'odds_draw', pre=True)
    def validate_odds(cls, v):
        """Ensure odds are valid decimal odds."""
        if v is None:
            return v
        if v <= 1.0:
            raise ValueError("Odds must be greater than 1.0")
        return float(v)


class MatchOdds(BaseModel):
    """Model for a match with all available odds."""
    match_id: str
    sport: str
    league: str
    commence_time: datetime
    team_home: str
    team_away: str
    bookmaker_odds: List[OddsData] = Field(default_factory=list)
    
    def get_best_odds(self, market: str = "h2h") -> Dict[str, Any]:
        """Get the best odds for each outcome across all bookmakers."""
        best_home = {"odds": 0, "bookmaker": None}
        best_away = {"odds": 0, "bookmaker": None}
        best_draw = {"odds": 0, "bookmaker": None}
        
        for odds in self.bookmaker_odds:
            if odds.market != market:
                continue
            if odds.odds_home > best_home["odds"]:
                best_home = {"odds": odds.odds_home, "bookmaker": odds.bookmaker}
            if odds.odds_away > best_away["odds"]:
                best_away = {"odds": odds.odds_away, "bookmaker": odds.bookmaker}
            if odds.odds_draw and odds.odds_draw > best_draw["odds"]:
                best_draw = {"odds": odds.odds_draw, "bookmaker": odds.bookmaker}
        
        return {
            "home": best_home,
            "away": best_away,
            "draw": best_draw if best_draw["bookmaker"] else None
        }


@dataclass
class CacheEntry:
    """Cache entry for odds data."""
    data: Any
    timestamp: datetime
    ttl_minutes: int = 15
    
    def is_valid(self) -> bool:
        """Check if cache entry is still valid."""
        return datetime.now() - self.timestamp < timedelta(minutes=self.ttl_minutes)


class OddsFetcher:
    """Fetches NHL odds from multiple sources.
    
    Primary: Fonbet (fonbet.ru/fonbet.by)
    Secondary: The Odds API, Belarusian bookmakers
    
    Features:
    - Fonbet as primary bookmaker (best CIS coverage)
    - Support for multiple markets (h2h, spreads, totals)
    - Automatic caching to minimize API calls
    - Rate limiting and error handling
    - Structured data output with Pydantic models
    - Integration with Belarusian bookmakers (Betera, Winline, MarafonBet)
    
    Attributes:
        api_key: The Odds API key
        base_url: API base URL
        sport: Sport key (default: icehockey_nhl)
        
    Example:
        >>> fetcher = OddsFetcher(api_key="your_key")
        >>> matches = fetcher.fetch_all_odds()  # Uses Fonbet as primary
        >>> for match in matches:
        ...     print(f"{match.team_home} vs {match.team_away}")
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.the-odds-api.com/v4",
        sport: str = "icehockey_nhl",
        regions: str = "us,eu",
        cache_ttl: int = 15,
        use_belarusian_bookmakers: bool = True,
        use_fonbet: bool = True,
        fonbet_region: str = 'ru',
    ):
        """Initialize OddsFetcher.
        
        Args:
            api_key: The Odds API key
            base_url: API base URL
            sport: Sport key
            regions: Comma-separated region codes
            cache_ttl: Cache time-to-live in minutes
            use_belarusian_bookmakers: Whether to fetch from Belarusian bookmakers
            use_fonbet: Whether to use Fonbet as primary bookmaker
            fonbet_region: Fonbet region ('ru' or 'by')
        """
        self.api_key = api_key
        self.base_url = base_url
        self.sport = sport
        self.regions = regions
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._last_request_time: Optional[datetime] = None
        self._requests_remaining: Optional[int] = None
        self._requests_used: Optional[int] = None
        
        # Initialize Fonbet as primary bookmaker
        self._fonbet_monitor: Optional['FonbetOddsMonitor'] = None
        self._use_fonbet = use_fonbet
        
        if use_fonbet and FONBET_AVAILABLE:
            try:
                self._fonbet_monitor = FonbetOddsMonitor(
                    region=fonbet_region,
                    cache_duration=cache_ttl * 60
                )
                logger.info(f"✅ Fonbet integration enabled (primary bookmaker, region: {fonbet_region})")
            except Exception as e:
                logger.warning(f"Failed to initialize Fonbet: {e}")
        
        # Initialize Belarusian bookmakers if available
        self._belarusian_bookmakers: Optional['BelarusianBookmakers'] = None
        self._use_belarusian = use_belarusian_bookmakers
        
        if use_belarusian_bookmakers and BELARUSIAN_AVAILABLE:
            try:
                self._belarusian_bookmakers = BelarusianBookmakers(cache_duration=cache_ttl * 60)
                logger.info("Belarusian bookmakers integration enabled (secondary)")
            except Exception as e:
                logger.warning(f"Failed to initialize Belarusian bookmakers: {e}")
        
    def _get_cache_key(self, markets: str) -> str:
        """Generate cache key for request."""
        return f"{self.sport}_{markets}_{self.regions}"
    
    def _update_rate_limits(self, headers: Dict) -> None:
        """Update rate limit info from response headers."""
        self._requests_remaining = headers.get("x-requests-remaining")
        self._requests_used = headers.get("x-requests-used")
        if self._requests_remaining:
            self._requests_remaining = int(self._requests_remaining)
        if self._requests_used:
            self._requests_used = int(self._requests_used)
            
    def get_rate_limit_status(self) -> Dict[str, Optional[int]]:
        """Get current rate limit status."""
        return {
            "requests_remaining": self._requests_remaining,
            "requests_used": self._requests_used
        }
    
    def fetch_odds(
        self,
        markets: str = "h2h",
        use_cache: bool = True,
    ) -> List[MatchOdds]:
        """Fetch NHL odds from The Odds API.
        
        Args:
            markets: Comma-separated market types (h2h, spreads, totals)
            use_cache: Whether to use cached data if available
            
        Returns:
            List of MatchOdds objects containing all available odds
            
        Raises:
            ValueError: If API key is missing or invalid
            requests.RequestException: If API request fails
        """
        if not self.api_key or self.api_key == "YOUR_API_KEY_HERE":
            raise ValueError(
                "API key not configured. Please add your The Odds API key to config.yaml"
            )
        
        # Check cache
        cache_key = self._get_cache_key(markets)
        if use_cache and cache_key in self._cache:
            entry = self._cache[cache_key]
            if entry.is_valid():
                logger.debug(f"Using cached odds data (age: {datetime.now() - entry.timestamp})")
                return entry.data
        
        # Build request
        url = f"{self.base_url}/sports/{self.sport}/odds"
        params = {
            "apiKey": self.api_key,
            "regions": self.regions,
            "markets": markets,
            "oddsFormat": "decimal",
        }
        
        logger.info(f"Fetching odds from The Odds API for {self.sport}")
        
        try:
            response = requests.get(url, params=params, timeout=30)
            self._update_rate_limits(response.headers)
            self._last_request_time = datetime.now()
            
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Received {len(data)} matches from API")
            logger.debug(f"Rate limits - Remaining: {self._requests_remaining}, Used: {self._requests_used}")
            
            # Parse response
            matches = self._parse_odds_response(data, markets)
            
            # Update cache
            self._cache[cache_key] = CacheEntry(
                data=matches,
                timestamp=datetime.now(),
                ttl_minutes=self.cache_ttl
            )
            
            return matches
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise ValueError("Invalid API key. Please check your The Odds API key.")
            elif e.response.status_code == 429:
                logger.warning("Rate limit exceeded. Please wait before making more requests.")
                raise
            else:
                logger.error(f"HTTP error fetching odds: {e}")
                raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching odds: {e}")
            raise
    
    def _parse_odds_response(
        self,
        data: List[Dict],
        markets: str
    ) -> List[MatchOdds]:
        """Parse API response into MatchOdds objects.
        
        Args:
            data: Raw API response data
            markets: Requested markets
            
        Returns:
            List of MatchOdds objects
        """
        matches = []
        market_list = markets.split(",")
        
        for event in data:
            try:
                bookmaker_odds = []
                
                for bookmaker in event.get("bookmakers", []):
                    for market in bookmaker.get("markets", []):
                        if market["key"] not in market_list:
                            continue
                            
                        outcomes = {o["name"]: o["price"] for o in market["outcomes"]}
                        
                        # Handle different market types
                        if market["key"] == "h2h":
                            odds_data = OddsData(
                                bookmaker=bookmaker["title"],
                                market=market["key"],
                                team_home=event["home_team"],
                                team_away=event["away_team"],
                                odds_home=outcomes.get(event["home_team"], 0),
                                odds_away=outcomes.get(event["away_team"], 0),
                                odds_draw=outcomes.get("Draw"),
                                last_update=datetime.fromisoformat(
                                    bookmaker["last_update"].replace("Z", "+00:00")
                                )
                            )
                            bookmaker_odds.append(odds_data)
                
                match = MatchOdds(
                    match_id=event["id"],
                    sport=event["sport_key"],
                    league=event["sport_title"],
                    commence_time=datetime.fromisoformat(
                        event["commence_time"].replace("Z", "+00:00")
                    ),
                    team_home=event["home_team"],
                    team_away=event["away_team"],
                    bookmaker_odds=bookmaker_odds
                )
                matches.append(match)
                
            except Exception as e:
                logger.warning(f"Error parsing match {event.get('id', 'unknown')}: {e}")
                continue
        
        return matches
    
    def fetch_sports(self) -> List[Dict]:
        """Fetch list of available sports.
        
        Returns:
            List of sport dictionaries with keys and titles
        """
        if not self.api_key or self.api_key == "YOUR_API_KEY_HERE":
            raise ValueError("API key not configured")
            
        url = f"{self.base_url}/sports"
        params = {"apiKey": self.api_key}
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching sports list: {e}")
            raise
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
        if self._fonbet_monitor:
            self._fonbet_monitor.clear_cache()
        if self._belarusian_bookmakers:
            self._belarusian_bookmakers.clear_cache()
        logger.info("Cache cleared")
    
    def fetch_fonbet_odds(self) -> List[MatchOdds]:
        """Fetch odds from Fonbet (primary bookmaker).
        
        Returns:
            List of MatchOdds objects from Fonbet
        """
        if not self._fonbet_monitor:
            logger.warning("Fonbet not available")
            return []
        
        try:
            # Fetch from Fonbet
            fonbet_odds = self._fonbet_monitor.get_odds_or_update(max_age_seconds=60)
            
            # Convert to MatchOdds format
            matches = []
            
            for odds in fonbet_odds:
                match = MatchOdds(
                    match_id=f"fonbet_{odds.event_id}",
                    sport=self.sport,
                    league=odds.league,
                    commence_time=odds.start_time or datetime.now(),
                    team_home=odds.home_team,
                    team_away=odds.away_team,
                    bookmaker_odds=[
                        OddsData(
                            bookmaker="Fonbet",
                            market="h2h",
                            team_home=odds.home_team,
                            team_away=odds.away_team,
                            odds_home=odds.odds_home or 0,
                            odds_away=odds.odds_away or 0,
                            odds_draw=odds.odds_draw,
                            last_update=odds.last_update
                        )
                    ]
                )
                matches.append(match)
            
            logger.info(f"✅ Fetched {len(matches)} matches from Fonbet (primary)")
            return matches
            
        except Exception as e:
            logger.error(f"Error fetching Fonbet odds: {e}")
            return []
    
    def fetch_belarusian_odds(
        self,
        bookmakers: Optional[List[str]] = None
    ) -> List[MatchOdds]:
        """Fetch odds from Belarusian bookmakers.
        
        Args:
            bookmakers: List of bookmaker keys to fetch from.
                       None for all enabled bookmakers.
                       Valid keys: betera, fonbet, winline, marathonbet
        
        Returns:
            List of MatchOdds objects with Belarusian bookmaker odds
        """
        if not self._belarusian_bookmakers:
            logger.warning("Belarusian bookmakers not available")
            return []
        
        try:
            # Fetch from Belarusian bookmakers
            all_odds = self._belarusian_bookmakers.fetch_all_odds(bookmakers)
            
            # Convert to MatchOdds format
            matches = []
            
            # Group by match
            match_dict: Dict[str, MatchOdds] = {}
            
            for bk_key, odds_list in all_odds.items():
                for bk_odds in odds_list:
                    # Create unique match identifier
                    match_key = f"{bk_odds.home_team}_{bk_odds.away_team}"
                    
                    if match_key not in match_dict:
                        match_dict[match_key] = MatchOdds(
                            match_id=f"by_{hash(match_key) % 100000}",
                            sport=self.sport,
                            league=bk_odds.league or "Hockey",
                            commence_time=bk_odds.match_time or datetime.now(),
                            team_home=bk_odds.home_team,
                            team_away=bk_odds.away_team,
                            bookmaker_odds=[]
                        )
                    
                    # Add bookmaker odds
                    match_dict[match_key].bookmaker_odds.append(OddsData(
                        bookmaker=bk_odds.bookmaker,
                        market="h2h",
                        team_home=bk_odds.home_team,
                        team_away=bk_odds.away_team,
                        odds_home=bk_odds.odds_home,
                        odds_away=bk_odds.odds_away,
                        odds_draw=bk_odds.odds_draw,
                        last_update=bk_odds.last_update
                    ))
            
            matches = list(match_dict.values())
            logger.info(f"Fetched {len(matches)} matches from Belarusian bookmakers")
            return matches
            
        except Exception as e:
            logger.error(f"Error fetching Belarusian odds: {e}")
            return []
    
    def fetch_all_odds(
        self,
        markets: str = "h2h",
        include_belarusian: bool = True,
        include_fonbet: bool = True,
        use_cache: bool = True
    ) -> List[MatchOdds]:
        """Fetch odds from all available sources.
        
        Priority order:
        1. Fonbet (primary bookmaker)
        2. The Odds API
        3. Belarusian bookmakers (Betera, Winline, MarafonBet)
        
        Args:
            markets: Comma-separated market types (h2h, spreads, totals)
            include_belarusian: Whether to include Belarusian bookmakers
            include_fonbet: Whether to include Fonbet (primary)
            use_cache: Whether to use cached data if available
            
        Returns:
            Combined list of MatchOdds from all sources
        """
        all_matches = []
        
        # 1. Fetch from Fonbet (PRIMARY)
        if include_fonbet and self._use_fonbet:
            try:
                logger.info("\n=== Fetching from Fonbet (Primary) ===")
                fonbet_matches = self.fetch_fonbet_odds()
                all_matches.extend(fonbet_matches)
            except Exception as e:
                logger.error(f"Error fetching from Fonbet: {e}")
        
        # 2. Fetch from The Odds API (secondary)
        try:
            logger.info("\n=== Fetching from The Odds API (Secondary) ===")
            api_matches = self.fetch_odds(markets=markets, use_cache=use_cache)
            
            # Merge with existing matches
            existing_keys = {f"{m.team_home}_{m.team_away}" for m in all_matches}
            
            for api_match in api_matches:
                match_key = f"{api_match.team_home}_{api_match.team_away}"
                
                if match_key in existing_keys:
                    # Merge bookmaker odds into existing match
                    for existing in all_matches:
                        if f"{existing.team_home}_{existing.team_away}" == match_key:
                            existing.bookmaker_odds.extend(api_match.bookmaker_odds)
                            break
                else:
                    all_matches.append(api_match)
            
            logger.info(f"Total matches after The Odds API: {len(all_matches)}")
            
        except ValueError as e:
            # API key issue - just log and continue
            logger.warning(f"The Odds API not available: {e}")
        except Exception as e:
            logger.error(f"Error fetching from The Odds API: {e}")
        
        # 3. Fetch from Belarusian bookmakers (secondary)
        if include_belarusian and self._use_belarusian:
            try:
                logger.info("\n=== Fetching from Belarusian bookmakers ===")
                by_matches = self.fetch_belarusian_odds()
                
                # Merge with existing matches or add new ones
                existing_keys = {f"{m.team_home}_{m.team_away}" for m in all_matches}
                
                for by_match in by_matches:
                    match_key = f"{by_match.team_home}_{by_match.team_away}"
                    
                    if match_key in existing_keys:
                        # Find and merge bookmaker odds
                        for existing in all_matches:
                            if f"{existing.team_home}_{existing.team_away}" == match_key:
                                existing.bookmaker_odds.extend(by_match.bookmaker_odds)
                                break
                    else:
                        all_matches.append(by_match)
                
                logger.info(f"Total matches after Belarusian integration: {len(all_matches)}")
                
            except Exception as e:
                logger.error(f"Error fetching Belarusian odds: {e}")
        
        logger.info(f"\n✅ Total matches fetched from all sources: {len(all_matches)}")
        
        return all_matches
    
    def get_available_bookmakers(self) -> Dict[str, List[Dict]]:
        """Get list of all available bookmakers.
        
        Returns:
            Dictionary with 'primary', 'api', and 'belarusian' bookmaker lists
        """
        result = {
            'primary': [],
            'api': [
                {'key': 'odds_api', 'name': 'The Odds API', 'regions': self.regions}
            ],
            'belarusian': []
        }
        
        # Primary bookmaker (Fonbet)
        if self._fonbet_monitor:
            result['primary'] = [
                {'key': 'fonbet', 'name': 'Fonbet', 'priority': 1, 'status': 'enabled'}
            ]
        
        if self._belarusian_bookmakers:
            result['belarusian'] = self._belarusian_bookmakers.get_available_bookmakers()
        
        return result
