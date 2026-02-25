"""Analysis module for Eden MVP v3.0.1.

Contains match analysis, stake calculation, and betting validation functionality.
"""

from .match_analyzer import MatchAnalyzer
from .stake_calculator import StakeCalculator

# NEW: Betting validator for limit checks
try:
    from .betting_validator import (
        BettingValidator, BetValidation, BetValidationStatus,
        BookmakerLimits, DEFAULT_BOOKMAKER_LIMITS
    )
    VALIDATOR_AVAILABLE = True
except ImportError:
    VALIDATOR_AVAILABLE = False
    BettingValidator = None

__all__ = [
    "MatchAnalyzer", 
    "StakeCalculator",
    # Validator components
    "BettingValidator",
    "BetValidation",
    "BetValidationStatus",
    "BookmakerLimits",
    "DEFAULT_BOOKMAKER_LIMITS",
    "VALIDATOR_AVAILABLE"
]
