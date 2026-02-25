"""Fonbet API Integration for Eden Analytics Pro.

Primary bookmaker integration for fetching NHL odds from Fonbet.
Supports both fonbet.ru (Russian) and fonbet.by (Belarusian) endpoints.

Features:
- Real-time NHL odds fetching
- Odds caching for performance
- Team name normalization (RU/EN)
- Multiple market support (H2H, totals, handicaps)
"""

import time
import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from functools import wraps

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FonbetOdds:
    """Represents odds data from Fonbet."""
    event_id: str
    home_team: str
    away_team: str
    league: str
    start_time: Optional[datetime]
    odds_home: Optional[float] = None
    odds_away: Optional[float] = None
    odds_draw: Optional[float] = None
    over_5_5: Optional[float] = None
    under_5_5: Optional[float] = None
    handicap_home: Optional[float] = None
    handicap_away: Optional[float] = None
    handicap_value: Optional[float] = None
    last_update: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'event_id': self.event_id,
            'home_team': self.home_team,
            'away_team': self.away_team,
            'league': self.league,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'odds': {
                'home_win': self.odds_home,
                'away_win': self.odds_away,
                'draw': self.odds_draw,
                'over_5_5': self.over_5_5,
                'under_5_5': self.under_5_5,
            },
            'last_update': self.last_update.isoformat()
        }


class FonbetAPI:
    """Fonbet API client for fetching hockey odds.
    
    Fonbet is a major Russian/CIS bookmaker with comprehensive NHL coverage.
    This client fetches odds from their public API endpoints.
    
    Example:
        >>> api = FonbetAPI()
        >>> events = api.get_nhl_odds()
        >>> for event in events:
        ...     print(f"{event.home_team} vs {event.away_team}: {event.odds_home}/{event.odds_away}")
    """
    
    # API endpoints
    ENDPOINTS = {
        'ru': {
            'base': 'https://line.fonbet.ru/api',
            'events': '/events/list',
            'live': '/live/list',
        },
        'by': {
            'base': 'https://line.fonbet.by/api',
            'events': '/events/list',
            'live': '/live/list',
        }
    }
    
    # NHL league identifiers in Fonbet
    NHL_LEAGUE_IDS = [14917, 18521]  # NHL regular, playoffs
    NHL_LEAGUE_NAMES = ['NHL', 'НХЛ', 'National Hockey League']
    
    # Team name mappings (Russian -> English)
    TEAM_NAME_MAPPINGS = {
        # Atlantic Division
        'бостон': 'Boston Bruins',
        'бостон брюинз': 'Boston Bruins',
        'буффало': 'Buffalo Sabres',
        'буффало сейбрз': 'Buffalo Sabres',
        'детройт': 'Detroit Red Wings',
        'детройт ред уингз': 'Detroit Red Wings',
        'флорида': 'Florida Panthers',
        'флорида пантерз': 'Florida Panthers',
        'монреаль': 'Montreal Canadiens',
        'монреаль канадиенс': 'Montreal Canadiens',
        'оттава': 'Ottawa Senators',
        'оттава сенаторз': 'Ottawa Senators',
        'тампа': 'Tampa Bay Lightning',
        'тампа бэй': 'Tampa Bay Lightning',
        'торонто': 'Toronto Maple Leafs',
        'торонто мэйпл лифс': 'Toronto Maple Leafs',
        
        # Metropolitan Division
        'каролина': 'Carolina Hurricanes',
        'каролина харрикейнз': 'Carolina Hurricanes',
        'коламбус': 'Columbus Blue Jackets',
        'коламбус блю джекетс': 'Columbus Blue Jackets',
        'нью-джерси': 'New Jersey Devils',
        'нью-джерси девилз': 'New Jersey Devils',
        'айлендерс': 'New York Islanders',
        'нью-йорк айлендерс': 'New York Islanders',
        'рейнджерс': 'New York Rangers',
        'нью-йорк рейнджерс': 'New York Rangers',
        'филадельфия': 'Philadelphia Flyers',
        'филадельфия флайерз': 'Philadelphia Flyers',
        'питтсбург': 'Pittsburgh Penguins',
        'питтсбург пингвинз': 'Pittsburgh Penguins',
        'вашингтон': 'Washington Capitals',
        'вашингтон кэпиталз': 'Washington Capitals',
        
        # Central Division
        'аризона': 'Arizona Coyotes',
        'аризона койотис': 'Arizona Coyotes',
        'юта': 'Utah Hockey Club',
        'чикаго': 'Chicago Blackhawks',
        'чикаго блэкхокс': 'Chicago Blackhawks',
        'колорадо': 'Colorado Avalanche',
        'колорадо эвеланш': 'Colorado Avalanche',
        'даллас': 'Dallas Stars',
        'даллас старз': 'Dallas Stars',
        'миннесота': 'Minnesota Wild',
        'миннесота уайлд': 'Minnesota Wild',
        'нэшвилл': 'Nashville Predators',
        'нэшвилл предаторз': 'Nashville Predators',
        'сент-луис': 'St. Louis Blues',
        'сент-луис блюз': 'St. Louis Blues',
        'виннипег': 'Winnipeg Jets',
        'виннипег джетс': 'Winnipeg Jets',
        
        # Pacific Division
        'анахайм': 'Anaheim Ducks',
        'анахайм дакс': 'Anaheim Ducks',
        'калгари': 'Calgary Flames',
        'калгари флэймз': 'Calgary Flames',
        'эдмонтон': 'Edmonton Oilers',
        'эдмонтон ойлерз': 'Edmonton Oilers',
        'лос-анджелес': 'Los Angeles Kings',
        'лос-анджелес кингз': 'Los Angeles Kings',
        'сан-хосе': 'San Jose Sharks',
        'сан-хосе шаркс': 'San Jose Sharks',
        'сиэтл': 'Seattle Kraken',
        'сиэтл кракен': 'Seattle Kraken',
        'ванкувер': 'Vancouver Canucks',
        'ванкувер кэнакс': 'Vancouver Canucks',
        'вегас': 'Vegas Golden Knights',
        'вегас голден найтс': 'Vegas Golden Knights',
    }
    
    def __init__(self, region: str = 'ru', cache_duration: int = 60):
        """Initialize Fonbet API client.
        
        Args:
            region: API region ('ru' or 'by')
            cache_duration: Cache duration in seconds
        """
        self.region = region
        self.endpoints = self.ENDPOINTS.get(region, self.ENDPOINTS['ru'])
        self.base_url = self.endpoints['base']
        self.cache_duration = cache_duration
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
        })
        
        self._cache: Dict[str, tuple] = {}
        self._last_request = 0.0
        self._min_request_interval = 1.0  # Rate limiting
        
        logger.info(f"FonbetAPI initialized (region: {region})")
    
    def _rate_limit(self):
        """Apply rate limiting between requests."""
        elapsed = time.time() - self._last_request
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request = time.time()
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Get data from cache if valid."""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_duration):
                return data
        return None
    
    def _set_cache(self, key: str, data: Any):
        """Store data in cache."""
        self._cache[key] = (data, datetime.now())
    
    def clear_cache(self):
        """Clear all cached data."""
        self._cache.clear()
        logger.info("Fonbet cache cleared")
    
    def _api_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make API request with error handling.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            JSON response or None
        """
        self._rate_limit()
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.Timeout:
            logger.warning(f"Fonbet request timeout: {endpoint}")
        except requests.exceptions.HTTPError as e:
            logger.warning(f"Fonbet HTTP error: {e}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Fonbet request error: {e}")
        except json.JSONDecodeError:
            logger.warning(f"Fonbet JSON decode error: {endpoint}")
        
        return None
    
    def get_hockey_events(self) -> List[Dict]:
        """Get all hockey events from Fonbet.
        
        Returns:
            List of hockey event dictionaries
        """
        # Check cache
        cached = self._get_cached('hockey_events')
        if cached:
            logger.debug("Using cached hockey events")
            return cached
        
        params = {
            'sport': '2',  # Hockey sport ID
            'level': 'main',
            'lang': 'ru',
        }
        
        data = self._api_request(self.endpoints['events'], params)
        
        if not data:
            return []
        
        events = self._parse_events(data)
        
        # Cache results
        self._set_cache('hockey_events', events)
        
        return events
    
    def _parse_events(self, data: Dict) -> List[Dict]:
        """Parse events from API response.
        
        Args:
            data: Raw API response
            
        Returns:
            List of parsed event dictionaries
        """
        events = []
        
        # Handle different response formats
        events_list = data.get('events', data.get('result', {}).get('events', []))
        
        for event in events_list:
            try:
                event_info = {
                    'id': str(event.get('id', '')),
                    'home_team': event.get('team1', event.get('name1', '')),
                    'away_team': event.get('team2', event.get('name2', '')),
                    'league': event.get('sportKind', {}).get('name', 
                              event.get('league', {}).get('name', 'Hockey')),
                    'start_time': self._parse_timestamp(event.get('startTime')),
                    'odds': self._extract_odds(event),
                }
                
                events.append(event_info)
                
            except Exception as e:
                logger.debug(f"Error parsing event: {e}")
                continue
        
        return events
    
    def _parse_timestamp(self, timestamp: Any) -> Optional[datetime]:
        """Parse timestamp from various formats."""
        if not timestamp:
            return None
        
        try:
            if isinstance(timestamp, (int, float)):
                return datetime.fromtimestamp(timestamp)
            elif isinstance(timestamp, str):
                return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except (ValueError, OSError):
            pass
        
        return None
    
    def _extract_odds(self, event: Dict) -> Dict:
        """Extract odds from event data.
        
        Args:
            event: Event dictionary
            
        Returns:
            Dictionary of odds values
        """
        odds = {
            'home_win': None,
            'away_win': None,
            'draw': None,
            'over_5_5': None,
            'under_5_5': None,
        }
        
        try:
            # Fonbet stores odds in 'factors' or 'markets' array
            factors = event.get('factors', event.get('markets', []))
            
            if isinstance(factors, list):
                for factor in factors:
                    self._process_factor(factor, odds)
            elif isinstance(factors, dict):
                for key, factor in factors.items():
                    self._process_factor(factor, odds)
        
        except Exception as e:
            logger.debug(f"Error extracting odds: {e}")
        
        return odds
    
    def _process_factor(self, factor: Dict, odds: Dict):
        """Process a single factor/market and update odds dict."""
        factor_name = str(factor.get('name', factor.get('type', ''))).lower()
        factor_value = factor.get('value', factor.get('odds'))
        
        if factor_value is None:
            return
        
        try:
            factor_value = float(factor_value)
        except (TypeError, ValueError):
            return
        
        # Match outcomes (Russian and English)
        if any(x in factor_name for x in ['п1', 'win1', '1x2_1', 'home']):
            odds['home_win'] = factor_value
        elif any(x in factor_name for x in ['п2', 'win2', '1x2_2', 'away']):
            odds['away_win'] = factor_value
        elif any(x in factor_name for x in ['х', 'draw', '1x2_x']):
            odds['draw'] = factor_value
        elif 'тб' in factor_name and '5.5' in factor_name:
            odds['over_5_5'] = factor_value
        elif 'тм' in factor_name and '5.5' in factor_name:
            odds['under_5_5'] = factor_value
        elif 'over' in factor_name and '5.5' in factor_name:
            odds['over_5_5'] = factor_value
        elif 'under' in factor_name and '5.5' in factor_name:
            odds['under_5_5'] = factor_value
    
    def get_nhl_odds(self) -> List[FonbetOdds]:
        """Get NHL-specific odds.
        
        Returns:
            List of FonbetOdds objects for NHL matches
        """
        # Check cache
        cached = self._get_cached('nhl_odds')
        if cached:
            logger.debug("Using cached NHL odds")
            return cached
        
        all_events = self.get_hockey_events()
        
        # Filter for NHL
        nhl_events = []
        for event in all_events:
            league = event.get('league', '').upper()
            if any(nhl in league for nhl in ['NHL', 'НХЛ', 'NATIONAL HOCKEY']):
                nhl_odds = FonbetOdds(
                    event_id=event['id'],
                    home_team=self.normalize_team_name(event['home_team']),
                    away_team=self.normalize_team_name(event['away_team']),
                    league='NHL',
                    start_time=event['start_time'],
                    odds_home=event['odds'].get('home_win'),
                    odds_away=event['odds'].get('away_win'),
                    odds_draw=event['odds'].get('draw'),
                    over_5_5=event['odds'].get('over_5_5'),
                    under_5_5=event['odds'].get('under_5_5'),
                )
                nhl_events.append(nhl_odds)
        
        # Cache results
        self._set_cache('nhl_odds', nhl_events)
        
        logger.info(f"Fetched {len(nhl_events)} NHL matches from Fonbet")
        
        return nhl_events
    
    def get_odds_for_match(self, home_team: str, away_team: str) -> Optional[FonbetOdds]:
        """Get odds for a specific match.
        
        Args:
            home_team: Home team name
            away_team: Away team name
            
        Returns:
            FonbetOdds object if found, None otherwise
        """
        events = self.get_nhl_odds()
        
        home_norm = self.normalize_team_name(home_team)
        away_norm = self.normalize_team_name(away_team)
        
        for event in events:
            if (self._teams_match(event.home_team, home_norm) and
                self._teams_match(event.away_team, away_norm)):
                return event
        
        return None
    
    def _teams_match(self, team1: str, team2: str) -> bool:
        """Check if two team names match."""
        t1 = team1.lower().strip()
        t2 = team2.lower().strip()
        
        # Direct match
        if t1 == t2:
            return True
        
        # Partial match (one contains the other)
        if t1 in t2 or t2 in t1:
            return True
        
        # Check if city names match
        t1_parts = t1.split()
        t2_parts = t2.split()
        if t1_parts and t2_parts:
            if t1_parts[0] == t2_parts[0]:  # Same city
                return True
        
        return False
    
    def normalize_team_name(self, name: str) -> str:
        """Normalize team name to English format.
        
        Args:
            name: Team name (Russian or English)
            
        Returns:
            Normalized English team name
        """
        if not name:
            return name
        
        # Clean up
        name_lower = name.lower().strip()
        name_lower = name_lower.replace('хк ', '').replace('hc ', '')
        
        # Check mappings
        if name_lower in self.TEAM_NAME_MAPPINGS:
            return self.TEAM_NAME_MAPPINGS[name_lower]
        
        # Check partial matches
        for ru_name, en_name in self.TEAM_NAME_MAPPINGS.items():
            if ru_name in name_lower or name_lower in ru_name:
                return en_name
        
        # Return original if no mapping found
        return name


class FonbetOddsMonitor:
    """Monitor Fonbet odds with history tracking.
    
    Provides real-time odds monitoring with caching and
    odds movement tracking for arbitrage detection.
    
    Example:
        >>> monitor = FonbetOddsMonitor()
        >>> odds = monitor.update_odds()
        >>> for match in odds:
        ...     print(f"{match.home_team}: {match.odds_home}")
    """
    
    def __init__(self, region: str = 'ru', cache_duration: int = 60):
        """Initialize odds monitor.
        
        Args:
            region: API region
            cache_duration: Cache duration in seconds
        """
        self.api = FonbetAPI(region=region, cache_duration=cache_duration)
        self.last_update: Optional[datetime] = None
        self.odds_history: List[Dict] = []
        self.max_history = 100
    
    def update_odds(self) -> List[FonbetOdds]:
        """Fetch and update odds from Fonbet.
        
        Returns:
            List of current NHL odds
        """
        logger.info("Updating odds from Fonbet...")
        
        odds = self.api.get_nhl_odds()
        self.last_update = datetime.now()
        
        # Store in history
        self.odds_history.append({
            'timestamp': self.last_update,
            'odds_count': len(odds),
            'odds': [o.to_dict() for o in odds]
        })
        
        # Trim history
        if len(self.odds_history) > self.max_history:
            self.odds_history = self.odds_history[-self.max_history:]
        
        logger.info(f"✅ Fetched {len(odds)} NHL matches from Fonbet")
        
        return odds
    
    def get_cached_odds(self, max_age_seconds: int = 60) -> Optional[List[FonbetOdds]]:
        """Get cached odds if recent enough.
        
        Args:
            max_age_seconds: Maximum age of cached data
            
        Returns:
            Cached odds or None if stale
        """
        if not self.last_update:
            return None
        
        age = (datetime.now() - self.last_update).total_seconds()
        if age > max_age_seconds:
            return None
        
        return self.api.get_nhl_odds()
    
    def get_odds_or_update(self, max_age_seconds: int = 60) -> List[FonbetOdds]:
        """Get cached odds or fetch new ones.
        
        Args:
            max_age_seconds: Maximum age of acceptable cached data
            
        Returns:
            List of current NHL odds
        """
        cached = self.get_cached_odds(max_age_seconds)
        if cached:
            return cached
        return self.update_odds()
    
    def get_odds_movement(self, event_id: str) -> List[Dict]:
        """Get odds movement history for an event.
        
        Args:
            event_id: Fonbet event ID
            
        Returns:
            List of odds snapshots over time
        """
        movements = []
        
        for entry in self.odds_history:
            for odds in entry['odds']:
                if odds['event_id'] == event_id:
                    movements.append({
                        'timestamp': entry['timestamp'],
                        'odds': odds['odds']
                    })
                    break
        
        return movements
    
    def clear_cache(self):
        """Clear all cached data."""
        self.api.clear_cache()
        self.odds_history.clear()
        self.last_update = None
        logger.info("Fonbet monitor cache cleared")


# Module-level convenience function
def get_nhl_odds() -> List[FonbetOdds]:
    """Quick function to fetch current NHL odds from Fonbet.
    
    Returns:
        List of current NHL odds
    """
    api = FonbetAPI()
    return api.get_nhl_odds()
