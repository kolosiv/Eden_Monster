"""Bookmakers module for Eden Analytics Pro.

Supports fetching odds from various bookmakers.
Primary: Fonbet (fonbet.ru/fonbet.by)
Secondary: Belarusian bookmakers (Betera, Winline, MarafonBet)
"""

from .belarusian import BelarusianBookmakers

# Import Fonbet API (primary bookmaker)
try:
    from .fonbet_api import FonbetAPI, FonbetOddsMonitor, FonbetOdds, get_nhl_odds
    FONBET_AVAILABLE = True
except ImportError as e:
    FONBET_AVAILABLE = False
    FonbetAPI = None
    FonbetOddsMonitor = None
    FonbetOdds = None
    get_nhl_odds = None

__all__ = [
    'BelarusianBookmakers',
    'FonbetAPI',
    'FonbetOddsMonitor',
    'FonbetOdds',
    'get_nhl_odds',
    'FONBET_AVAILABLE',
]
