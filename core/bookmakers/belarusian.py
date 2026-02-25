"""Belarusian Bookmakers Module for Eden Analytics Pro.

Fetches hockey odds from Belarusian bookmakers:
- Betera (betera.by)
- Fonbet (fonbet.by)
- Winline (winline.by)
- MarafonBet (marathonbet.by)
"""

import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from functools import wraps
import requests

from utils.logger import get_logger

logger = get_logger(__name__)

# Try to import BeautifulSoup for web scraping
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    logger.warning("BeautifulSoup not available. Install with: pip install beautifulsoup4")


@dataclass
class BookmakerOdds:
    """Represents odds from a single bookmaker."""
    bookmaker: str
    bookmaker_key: str
    home_team: str
    away_team: str
    odds_home: float
    odds_away: float
    odds_draw: Optional[float] = None
    match_time: Optional[datetime] = None
    league: str = "Hockey"
    last_update: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'bookmaker': self.bookmaker,
            'bookmaker_key': self.bookmaker_key,
            'home_team': self.home_team,
            'away_team': self.away_team,
            'odds_home': self.odds_home,
            'odds_away': self.odds_away,
            'odds_draw': self.odds_draw,
            'match_time': self.match_time.isoformat() if self.match_time else None,
            'league': self.league,
            'last_update': self.last_update.isoformat()
        }


class OddsCache:
    """Simple cache for odds data."""
    
    def __init__(self, cache_duration: int = 300):
        """Initialize cache.
        
        Args:
            cache_duration: Cache duration in seconds (default: 5 minutes)
        """
        self.cache: Dict[str, tuple] = {}
        self.cache_duration = cache_duration
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached data if still valid."""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_duration):
                return data
        return None
    
    def set(self, key: str, data: Any) -> None:
        """Store data in cache."""
        self.cache[key] = (data, datetime.now())
    
    def clear(self) -> None:
        """Clear all cache."""
        self.cache.clear()


def rate_limit(seconds: float = 2.0):
    """Decorator to rate limit API/scraping calls."""
    def decorator(func):
        last_called = [0.0]
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            if elapsed < seconds:
                time.sleep(seconds - elapsed)
            result = func(*args, **kwargs)
            last_called[0] = time.time()
            return result
        return wrapper
    return decorator


class BelarusianBookmakers:
    """Fetches odds from Belarusian bookmakers.
    
    Supported bookmakers:
    - Betera (betera.by) - Leading Belarusian bookmaker
    - Fonbet (fonbet.by) - Russian bookmaker with BY branch
    - Winline (winline.by) - Popular in CIS region
    - MarafonBet (marathonbet.by) - International with BY presence
    """
    
    BOOKMAKERS = {
        'betera': {
            'name': 'Betera',
            'url': 'https://betera.by',
            'api_url': 'https://betera.by/api/sports/hockey/events',
            'hockey_url': 'https://betera.by/sport/hockey',
            'enabled': True,
            'country': 'Belarus'
        },
        'fonbet': {
            'name': 'Fonbet BY',
            'url': 'https://fonbet.by',
            'api_url': 'https://fonbet.by/live/sports/api/v2/events',
            'hockey_url': 'https://fonbet.by/sports/hockey',
            'enabled': True,
            'country': 'Belarus'
        },
        'winline': {
            'name': 'Winline BY',
            'url': 'https://winline.by',
            'api_url': 'https://winline.by/api/v2/events',
            'hockey_url': 'https://winline.by/sports/hockey',
            'enabled': True,
            'country': 'Belarus'
        },
        'marathonbet': {
            'name': 'MarafonBet',
            'url': 'https://marathonbet.by',
            'api_url': 'https://marathonbet.by/api/events',
            'hockey_url': 'https://marathonbet.by/en/betting/Ice+Hockey',
            'enabled': True,
            'country': 'Belarus'
        }
    }
    
    def __init__(self, cache_duration: int = 300, rate_limit_seconds: float = 3.0):
        """Initialize Belarusian bookmakers fetcher.
        
        Args:
            cache_duration: Cache duration in seconds (default: 5 minutes)
            rate_limit_seconds: Minimum seconds between requests (default: 3)
        """
        self.cache = OddsCache(cache_duration)
        self.rate_limit_seconds = rate_limit_seconds
        self._last_request_time = 0.0
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        })
        
        logger.info(f"BelarusianBookmakers initialized with {len(self.BOOKMAKERS)} bookmakers")
    
    def _wait_rate_limit(self) -> None:
        """Wait to respect rate limiting."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_seconds:
            time.sleep(self.rate_limit_seconds - elapsed)
        self._last_request_time = time.time()
    
    def fetch_betera_odds(self) -> List[BookmakerOdds]:
        """Fetch odds from Betera.
        
        Returns:
            List of BookmakerOdds objects
        """
        cache_key = 'betera_odds'
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.debug("Using cached Betera odds")
            return cached
        
        matches = []
        
        try:
            self._wait_rate_limit()
            logger.info("Fetching odds from Betera...")
            
            # Try API endpoint first
            try:
                api_url = "https://betera.by/api/v1/sports/events?sport=hockey"
                response = self.session.get(api_url, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    matches = self._parse_betera_api(data)
                    logger.info(f"Betera API: {len(matches)} hockey matches found")
            except Exception as api_error:
                logger.debug(f"Betera API not available: {api_error}")
            
            # Fallback to web scraping if API fails
            if not matches and BS4_AVAILABLE:
                matches = self._scrape_betera()
            
            self.cache.set(cache_key, matches)
            return matches
            
        except Exception as e:
            logger.error(f"Error fetching Betera odds: {e}")
            return []
    
    def _parse_betera_api(self, data: Dict) -> List[BookmakerOdds]:
        """Parse Betera API response."""
        matches = []
        
        try:
            events = data.get('events', data.get('data', []))
            
            for event in events:
                if not isinstance(event, dict):
                    continue
                
                # Extract teams
                home_team = event.get('home', event.get('team1', ''))
                away_team = event.get('away', event.get('team2', ''))
                
                if not home_team or not away_team:
                    continue
                
                # Extract odds
                odds = event.get('odds', event.get('markets', {}))
                
                if isinstance(odds, dict):
                    odds_home = float(odds.get('1', odds.get('home', 0)))
                    odds_away = float(odds.get('2', odds.get('away', 0)))
                    odds_draw = odds.get('X', odds.get('draw'))
                    if odds_draw:
                        odds_draw = float(odds_draw)
                elif isinstance(odds, list) and len(odds) >= 2:
                    odds_home = float(odds[0].get('value', 0))
                    odds_away = float(odds[1].get('value', 0))
                    odds_draw = float(odds[2].get('value', 0)) if len(odds) > 2 else None
                else:
                    continue
                
                if odds_home > 1 and odds_away > 1:
                    matches.append(BookmakerOdds(
                        bookmaker='Betera',
                        bookmaker_key='betera',
                        home_team=home_team,
                        away_team=away_team,
                        odds_home=odds_home,
                        odds_away=odds_away,
                        odds_draw=odds_draw,
                        league=event.get('league', 'Hockey'),
                        match_time=self._parse_datetime(event.get('start_time', event.get('date')))
                    ))
                    
        except Exception as e:
            logger.warning(f"Error parsing Betera API data: {e}")
        
        return matches
    
    def _scrape_betera(self) -> List[BookmakerOdds]:
        """Scrape Betera website for odds."""
        matches = []
        
        try:
            url = self.BOOKMAKERS['betera']['hockey_url']
            response = self.session.get(url, timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"Betera scrape failed: {response.status_code}")
                return matches
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find event rows (structure varies by site)
            event_elements = soup.find_all('div', class_=['event', 'match', 'game-row'])
            
            for elem in event_elements:
                try:
                    teams = elem.find_all('span', class_=['team-name', 'competitor'])
                    if len(teams) >= 2:
                        home_team = teams[0].get_text(strip=True)
                        away_team = teams[1].get_text(strip=True)
                        
                        odds_elements = elem.find_all('span', class_=['odds', 'coeff', 'odd-value'])
                        if len(odds_elements) >= 2:
                            odds_home = float(odds_elements[0].get_text(strip=True).replace(',', '.'))
                            odds_away = float(odds_elements[1].get_text(strip=True).replace(',', '.'))
                            
                            if odds_home > 1 and odds_away > 1:
                                matches.append(BookmakerOdds(
                                    bookmaker='Betera',
                                    bookmaker_key='betera',
                                    home_team=home_team,
                                    away_team=away_team,
                                    odds_home=odds_home,
                                    odds_away=odds_away
                                ))
                except Exception as e:
                    continue
                    
        except Exception as e:
            logger.error(f"Error scraping Betera: {e}")
        
        logger.info(f"Betera scrape: {len(matches)} matches found")
        return matches
    
    def fetch_fonbet_odds(self) -> List[BookmakerOdds]:
        """Fetch odds from Fonbet BY.
        
        Returns:
            List of BookmakerOdds objects
        """
        cache_key = 'fonbet_odds'
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.debug("Using cached Fonbet odds")
            return cached
        
        matches = []
        
        try:
            self._wait_rate_limit()
            logger.info("Fetching odds from Fonbet BY...")
            
            # Fonbet has a known API structure
            api_url = "https://fonbet.by/live/api/v2/events"
            params = {
                'sportId': 2,  # Hockey
                'lang': 'ru'
            }
            
            try:
                response = self.session.get(api_url, params=params, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    matches = self._parse_fonbet_api(data)
                    logger.info(f"Fonbet API: {len(matches)} hockey matches found")
            except Exception as api_error:
                logger.debug(f"Fonbet API not available: {api_error}")
                
                # Fallback to scraping
                if BS4_AVAILABLE:
                    matches = self._scrape_generic(
                        self.BOOKMAKERS['fonbet']['hockey_url'],
                        'Fonbet BY',
                        'fonbet'
                    )
            
            self.cache.set(cache_key, matches)
            return matches
            
        except Exception as e:
            logger.error(f"Error fetching Fonbet odds: {e}")
            return []
    
    def _parse_fonbet_api(self, data: Dict) -> List[BookmakerOdds]:
        """Parse Fonbet API response."""
        matches = []
        
        try:
            events = data.get('events', data.get('sports', []))
            
            for event in events:
                if not isinstance(event, dict):
                    continue
                
                home_team = event.get('team1', event.get('home', ''))
                away_team = event.get('team2', event.get('away', ''))
                
                if not home_team or not away_team:
                    continue
                
                # Extract main market odds
                markets = event.get('markets', event.get('odds', []))
                odds_home, odds_away, odds_draw = 0, 0, None
                
                for market in markets:
                    if isinstance(market, dict):
                        market_type = market.get('type', market.get('name', ''))
                        if market_type in ['1X2', 'RESULT', 'WINNER']:
                            outcomes = market.get('outcomes', market.get('selections', []))
                            for outcome in outcomes:
                                name = outcome.get('name', outcome.get('label', ''))
                                price = float(outcome.get('price', outcome.get('odds', 0)))
                                
                                if name in ['1', 'Home', home_team]:
                                    odds_home = price
                                elif name in ['2', 'Away', away_team]:
                                    odds_away = price
                                elif name in ['X', 'Draw']:
                                    odds_draw = price
                
                if odds_home > 1 and odds_away > 1:
                    matches.append(BookmakerOdds(
                        bookmaker='Fonbet BY',
                        bookmaker_key='fonbet',
                        home_team=home_team,
                        away_team=away_team,
                        odds_home=odds_home,
                        odds_away=odds_away,
                        odds_draw=odds_draw,
                        league=event.get('league', event.get('competition', 'Hockey'))
                    ))
                    
        except Exception as e:
            logger.warning(f"Error parsing Fonbet API data: {e}")
        
        return matches
    
    def fetch_winline_odds(self) -> List[BookmakerOdds]:
        """Fetch odds from Winline BY.
        
        Returns:
            List of BookmakerOdds objects
        """
        cache_key = 'winline_odds'
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.debug("Using cached Winline odds")
            return cached
        
        matches = []
        
        try:
            self._wait_rate_limit()
            logger.info("Fetching odds from Winline BY...")
            
            # Try API endpoint
            api_url = "https://winline.by/api/v2/events"
            params = {
                'sport': 'hockey',
                'format': 'json'
            }
            
            try:
                response = self.session.get(api_url, params=params, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    matches = self._parse_generic_api(data, 'Winline BY', 'winline')
                    logger.info(f"Winline API: {len(matches)} hockey matches found")
            except Exception as api_error:
                logger.debug(f"Winline API not available: {api_error}")
                
                # Fallback to scraping
                if BS4_AVAILABLE:
                    matches = self._scrape_generic(
                        self.BOOKMAKERS['winline']['hockey_url'],
                        'Winline BY',
                        'winline'
                    )
            
            self.cache.set(cache_key, matches)
            return matches
            
        except Exception as e:
            logger.error(f"Error fetching Winline odds: {e}")
            return []
    
    def fetch_marathonbet_odds(self) -> List[BookmakerOdds]:
        """Fetch odds from MarafonBet (MarathonBet BY).
        
        Returns:
            List of BookmakerOdds objects
        """
        cache_key = 'marathonbet_odds'
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.debug("Using cached MarafonBet odds")
            return cached
        
        matches = []
        
        try:
            self._wait_rate_limit()
            logger.info("Fetching odds from MarafonBet...")
            
            # Marathon typically has API
            api_url = "https://marathonbet.by/api/events/tree"
            params = {
                'categoryId': 3,  # Hockey
                'language': 'en'
            }
            
            try:
                response = self.session.get(api_url, params=params, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    matches = self._parse_generic_api(data, 'MarafonBet', 'marathonbet')
                    logger.info(f"MarafonBet API: {len(matches)} hockey matches found")
            except Exception as api_error:
                logger.debug(f"MarafonBet API not available: {api_error}")
                
                # Fallback to scraping
                if BS4_AVAILABLE:
                    matches = self._scrape_generic(
                        self.BOOKMAKERS['marathonbet']['hockey_url'],
                        'MarafonBet',
                        'marathonbet'
                    )
            
            self.cache.set(cache_key, matches)
            return matches
            
        except Exception as e:
            logger.error(f"Error fetching MarafonBet odds: {e}")
            return []
    
    def _parse_generic_api(self, data: Dict, bookmaker_name: str, bookmaker_key: str) -> List[BookmakerOdds]:
        """Parse generic API response format."""
        matches = []
        
        try:
            # Handle various API response structures
            events = data.get('events', data.get('data', data.get('matches', [])))
            
            if not isinstance(events, list):
                events = [events] if events else []
            
            for event in events:
                if not isinstance(event, dict):
                    continue
                
                # Try different field names
                home_team = (event.get('home') or event.get('team1') or 
                            event.get('homeTeam') or event.get('participants', [{}])[0].get('name', ''))
                away_team = (event.get('away') or event.get('team2') or 
                            event.get('awayTeam') or event.get('participants', [{}])[-1].get('name', ''))
                
                if not home_team or not away_team:
                    continue
                
                # Extract odds
                odds = event.get('odds', event.get('markets', {}))
                odds_home = 0
                odds_away = 0
                odds_draw = None
                
                if isinstance(odds, dict):
                    odds_home = float(odds.get('1', odds.get('home', odds.get('homeWin', 0))))
                    odds_away = float(odds.get('2', odds.get('away', odds.get('awayWin', 0))))
                    draw_val = odds.get('X', odds.get('draw'))
                    if draw_val:
                        odds_draw = float(draw_val)
                elif isinstance(odds, list) and len(odds) >= 2:
                    for odd in odds:
                        if isinstance(odd, dict):
                            name = str(odd.get('name', odd.get('type', ''))).lower()
                            value = float(odd.get('value', odd.get('price', odd.get('odds', 0))))
                            if '1' in name or 'home' in name:
                                odds_home = value
                            elif '2' in name or 'away' in name:
                                odds_away = value
                            elif 'x' in name or 'draw' in name:
                                odds_draw = value
                
                if odds_home > 1 and odds_away > 1:
                    matches.append(BookmakerOdds(
                        bookmaker=bookmaker_name,
                        bookmaker_key=bookmaker_key,
                        home_team=home_team,
                        away_team=away_team,
                        odds_home=odds_home,
                        odds_away=odds_away,
                        odds_draw=odds_draw,
                        league=event.get('league', event.get('competition', 'Hockey'))
                    ))
                    
        except Exception as e:
            logger.warning(f"Error parsing {bookmaker_name} API data: {e}")
        
        return matches
    
    def _scrape_generic(self, url: str, bookmaker_name: str, bookmaker_key: str) -> List[BookmakerOdds]:
        """Generic web scraping for bookmaker odds."""
        matches = []
        
        if not BS4_AVAILABLE:
            logger.warning(f"Cannot scrape {bookmaker_name}: BeautifulSoup not available")
            return matches
        
        try:
            response = self.session.get(url, timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"{bookmaker_name} scrape failed: {response.status_code}")
                return matches
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Generic selector patterns for betting sites
            selectors = [
                ('div', {'class': ['event-row', 'match-row', 'game', 'event']}),
                ('tr', {'class': ['event-row', 'match']}),
                ('article', {'class': ['event', 'match']}),
            ]
            
            for tag, attrs in selectors:
                elements = soup.find_all(tag, attrs)
                if elements:
                    for elem in elements:
                        match = self._extract_match_from_element(elem, bookmaker_name, bookmaker_key)
                        if match:
                            matches.append(match)
                    break
            
        except Exception as e:
            logger.error(f"Error scraping {bookmaker_name}: {e}")
        
        logger.info(f"{bookmaker_name} scrape: {len(matches)} matches found")
        return matches
    
    def _extract_match_from_element(self, elem, bookmaker_name: str, bookmaker_key: str) -> Optional[BookmakerOdds]:
        """Extract match data from HTML element."""
        try:
            # Try to find team names
            team_selectors = [
                ('span', 'team-name'),
                ('div', 'team'),
                ('span', 'competitor'),
                ('a', 'participant'),
            ]
            
            teams = []
            for tag, cls in team_selectors:
                teams = elem.find_all(tag, class_=cls)
                if len(teams) >= 2:
                    break
            
            if len(teams) < 2:
                return None
            
            home_team = teams[0].get_text(strip=True)
            away_team = teams[1].get_text(strip=True)
            
            if not home_team or not away_team:
                return None
            
            # Find odds
            odds_selectors = [
                ('span', 'odds'),
                ('span', 'odd-value'),
                ('div', 'coefficient'),
                ('button', 'odd'),
            ]
            
            odds_elements = []
            for tag, cls in odds_selectors:
                odds_elements = elem.find_all(tag, class_=cls)
                if len(odds_elements) >= 2:
                    break
            
            if len(odds_elements) < 2:
                return None
            
            odds_home = float(odds_elements[0].get_text(strip=True).replace(',', '.'))
            odds_away = float(odds_elements[1].get_text(strip=True).replace(',', '.'))
            
            if odds_home > 1 and odds_away > 1:
                return BookmakerOdds(
                    bookmaker=bookmaker_name,
                    bookmaker_key=bookmaker_key,
                    home_team=home_team,
                    away_team=away_team,
                    odds_home=odds_home,
                    odds_away=odds_away
                )
                
        except Exception:
            pass
        
        return None
    
    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string to datetime object."""
        if not dt_str:
            return None
        
        formats = [
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%d.%m.%Y %H:%M',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(dt_str.split('+')[0].split('.')[0], fmt)
            except ValueError:
                continue
        
        return None
    
    def fetch_all_odds(self, bookmakers: Optional[List[str]] = None) -> Dict[str, List[BookmakerOdds]]:
        """Fetch odds from all (or specified) Belarusian bookmakers.
        
        Args:
            bookmakers: List of bookmaker keys to fetch from. 
                       None for all enabled bookmakers.
        
        Returns:
            Dictionary mapping bookmaker key to list of BookmakerOdds
        """
        all_odds = {}
        
        if bookmakers is None:
            bookmakers = [k for k, v in self.BOOKMAKERS.items() if v.get('enabled', True)]
        
        fetch_methods = {
            'betera': self.fetch_betera_odds,
            'fonbet': self.fetch_fonbet_odds,
            'winline': self.fetch_winline_odds,
            'marathonbet': self.fetch_marathonbet_odds,
        }
        
        for bk_key in bookmakers:
            if bk_key in fetch_methods:
                try:
                    odds = fetch_methods[bk_key]()
                    all_odds[bk_key] = odds
                    logger.info(f"Fetched {len(odds)} matches from {bk_key}")
                except Exception as e:
                    logger.error(f"Failed to fetch from {bk_key}: {e}")
                    all_odds[bk_key] = []
        
        total = sum(len(v) for v in all_odds.values())
        logger.info(f"Total matches fetched from Belarusian bookmakers: {total}")
        
        return all_odds
    
    def get_combined_odds(self) -> List[Dict[str, Any]]:
        """Get combined odds from all bookmakers for matching events.
        
        Returns:
            List of events with odds from multiple bookmakers
        """
        all_odds = self.fetch_all_odds()
        
        # Group by match (using team names as key)
        matches: Dict[str, Dict[str, Any]] = {}
        
        for bk_key, odds_list in all_odds.items():
            for odds in odds_list:
                # Normalize team names for matching
                match_key = self._normalize_match_key(odds.home_team, odds.away_team)
                
                if match_key not in matches:
                    matches[match_key] = {
                        'home_team': odds.home_team,
                        'away_team': odds.away_team,
                        'match_time': odds.match_time,
                        'league': odds.league,
                        'bookmakers': {}
                    }
                
                matches[match_key]['bookmakers'][bk_key] = {
                    'bookmaker_name': odds.bookmaker,
                    'odds_home': odds.odds_home,
                    'odds_away': odds.odds_away,
                    'odds_draw': odds.odds_draw,
                    'last_update': odds.last_update.isoformat()
                }
        
        return list(matches.values())
    
    def _normalize_match_key(self, home: str, away: str) -> str:
        """Normalize team names to create consistent match keys."""
        # Simple normalization: lowercase, remove extra spaces
        home_normalized = ' '.join(home.lower().split())
        away_normalized = ' '.join(away.lower().split())
        return f"{home_normalized} vs {away_normalized}"
    
    def get_available_bookmakers(self) -> List[Dict[str, str]]:
        """Get list of available Belarusian bookmakers.
        
        Returns:
            List of bookmaker info dictionaries
        """
        return [
            {
                'key': key,
                'name': info['name'],
                'url': info['url'],
                'country': info['country'],
                'enabled': info['enabled']
            }
            for key, info in self.BOOKMAKERS.items()
        ]
    
    def clear_cache(self) -> None:
        """Clear all cached odds data."""
        self.cache.clear()
        logger.info("Belarusian bookmakers cache cleared")


# Convenience function for testing
def test_belarusian_bookmakers():
    """Test function to verify bookmaker fetching."""
    bk = BelarusianBookmakers()
    
    print("Available Belarusian Bookmakers:")
    for info in bk.get_available_bookmakers():
        print(f"  - {info['name']} ({info['key']}): {info['url']}")
    
    print("\nFetching odds from all bookmakers...")
    all_odds = bk.fetch_all_odds()
    
    for bk_key, odds_list in all_odds.items():
        print(f"\n{bk_key}: {len(odds_list)} matches")
        for odds in odds_list[:3]:  # Show first 3
            print(f"  {odds.home_team} vs {odds.away_team}: "
                  f"{odds.odds_home:.2f} / {odds.odds_away:.2f}")


if __name__ == '__main__':
    test_belarusian_bookmakers()
