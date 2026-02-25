"""Core module for Eden MVP.

Contains odds fetching, arbitrage finding, and live scores functionality.
"""

from .odds_fetcher import OddsFetcher
from .arbitrage_finder import ArbitrageFinder
from .live_scores import NHLLiveScores, GameInfo, GameState, get_live_scores

__all__ = [
    "OddsFetcher",
    "ArbitrageFinder",
    "NHLLiveScores",
    "GameInfo",
    "GameState",
    "get_live_scores",
]
