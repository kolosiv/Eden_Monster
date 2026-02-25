"""Core module for Eden MVP v3.1.0.

Contains odds fetching, arbitrage finding, live scores, and reliability validation.
"""

from .odds_fetcher import OddsFetcher
from .arbitrage_finder import ArbitrageFinder
from .live_scores import NHLLiveScores, GameInfo, GameState, get_live_scores

# v3.1.0: Import reliability validator
try:
    from .reliability_validator import (
        ReliabilityValidator,
        BookmakerMargin,
        NHLRuleChanges,
        BLACKLISTED_FEATURES,
        DataQualityReport,
        CVPipelineValidator,
        get_reliability_validator,
        validate_bet_safety,
        get_trust_level_assessment
    )
    VALIDATOR_AVAILABLE = True
except ImportError:
    VALIDATOR_AVAILABLE = False
    ReliabilityValidator = None
    BookmakerMargin = None

__all__ = [
    "OddsFetcher",
    "ArbitrageFinder",
    "NHLLiveScores",
    "GameInfo",
    "GameState",
    "get_live_scores",
    # v3.1.0 additions
    "ReliabilityValidator",
    "BookmakerMargin",
    "NHLRuleChanges",
    "BLACKLISTED_FEATURES",
    "DataQualityReport",
    "CVPipelineValidator",
    "get_reliability_validator",
    "validate_bet_safety",
    "get_trust_level_assessment",
    "VALIDATOR_AVAILABLE",
]
