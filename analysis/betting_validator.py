"""Betting Validator for Eden MVP v3.0.1.

Validates betting conditions and adds realistic limit checks.

CRITICAL FIX: This addresses the issue of not accounting for:
1. Betting limits at bookmakers
2. Arbitrage window timing
3. Account restrictions
4. Realistic market conditions
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime, timedelta

from pydantic import BaseModel, Field
from utils.logger import get_logger

logger = get_logger(__name__)


class BetValidationStatus(str, Enum):
    """Validation result status."""
    VALID = "valid"
    LIMIT_EXCEEDED = "limit_exceeded"
    ACCOUNT_RESTRICTED = "account_restricted"
    ARB_WINDOW_EXPIRED = "arb_window_expired"
    LOW_LIQUIDITY = "low_liquidity"
    HIGH_SLIPPAGE_RISK = "high_slippage_risk"
    INVALID_ODDS = "invalid_odds"


@dataclass
class BookmakerLimits:
    """Betting limits for a specific bookmaker.
    
    These are realistic limits for Belarusian and international bookmakers.
    """
    bookmaker: str
    max_bet_nhl: float = 500.0  # Max single bet in USD
    max_daily_nhl: float = 2000.0  # Max daily volume
    max_arb_bet: float = 200.0  # Reduced limit for suspicious patterns
    min_bet: float = 1.0
    accepts_arb: bool = True  # Some bookmakers void arbitrage bets
    restriction_risk: float = 0.3  # Probability of account restriction after winning


# Default limits for common bookmakers
DEFAULT_BOOKMAKER_LIMITS = {
    "betera": BookmakerLimits("betera", max_bet_nhl=400, max_arb_bet=150, restriction_risk=0.25),
    "fonbet": BookmakerLimits("fonbet", max_bet_nhl=800, max_arb_bet=300, restriction_risk=0.20),
    "winline": BookmakerLimits("winline", max_bet_nhl=500, max_arb_bet=200, restriction_risk=0.30),
    "1xbet": BookmakerLimits("1xbet", max_bet_nhl=1000, max_arb_bet=400, restriction_risk=0.15),
    "pinnacle": BookmakerLimits("pinnacle", max_bet_nhl=2000, max_arb_bet=1500, restriction_risk=0.05),
    "marathon": BookmakerLimits("marathon", max_bet_nhl=600, max_arb_bet=250, restriction_risk=0.20),
    "default": BookmakerLimits("default", max_bet_nhl=300, max_arb_bet=100, restriction_risk=0.35),
}


class BetValidation(BaseModel):
    """Result of bet validation."""
    status: BetValidationStatus
    is_valid: bool
    max_allowed_stake: float = 0.0
    adjusted_stake: float = 0.0
    warnings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    risk_factors: Dict[str, float] = Field(default_factory=dict)


class BettingValidator:
    """Validates betting conditions with realistic limits.
    
    CRITICAL FIX: This adds proper validation for:
    - Betting limits by bookmaker
    - Arbitrage timing windows (typically <5 minutes)
    - Slippage risk on odds movement
    - Account restriction probability
    - Market liquidity
    """
    
    # Arbitrage typically expires within this window
    ARB_EXPIRY_SECONDS = 300  # 5 minutes
    
    # Slippage increases with bet size
    SLIPPAGE_THRESHOLD_USD = 200  # Above this, slippage risk increases
    
    def __init__(
        self,
        bookmaker_limits: Optional[Dict[str, BookmakerLimits]] = None,
        daily_volume_tracker: Optional[Dict[str, float]] = None
    ):
        """Initialize validator.
        
        Args:
            bookmaker_limits: Custom limits by bookmaker
            daily_volume_tracker: Current daily volume by bookmaker
        """
        self.limits = bookmaker_limits or DEFAULT_BOOKMAKER_LIMITS
        self.daily_volume = daily_volume_tracker or {}
        self.arb_detected_time: Optional[datetime] = None
    
    def get_limits(self, bookmaker: str) -> BookmakerLimits:
        """Get limits for a bookmaker."""
        bookmaker_lower = bookmaker.lower()
        return self.limits.get(bookmaker_lower, self.limits["default"])
    
    def validate_bet(
        self,
        bookmaker: str,
        stake: float,
        odds: float,
        is_arbitrage: bool = True,
        arb_detected_at: Optional[datetime] = None
    ) -> BetValidation:
        """Validate a single bet against limits and conditions.
        
        Args:
            bookmaker: Bookmaker name
            stake: Proposed stake amount
            odds: Current odds
            is_arbitrage: Whether this is part of an arbitrage
            arb_detected_at: When the arb opportunity was detected
            
        Returns:
            BetValidation with status and recommendations
        """
        warnings = []
        recommendations = []
        risk_factors = {}
        
        limits = self.get_limits(bookmaker)
        
        # 1. Check basic limits
        max_allowed = limits.max_arb_bet if is_arbitrage else limits.max_bet_nhl
        
        if stake < limits.min_bet:
            return BetValidation(
                status=BetValidationStatus.INVALID_ODDS,
                is_valid=False,
                max_allowed_stake=max_allowed,
                warnings=[f"Stake ${stake:.2f} below minimum ${limits.min_bet:.2f}"]
            )
        
        if stake > max_allowed:
            warnings.append(
                f"Stake ${stake:.2f} exceeds max ${max_allowed:.2f} for {bookmaker}"
            )
            return BetValidation(
                status=BetValidationStatus.LIMIT_EXCEEDED,
                is_valid=False,
                max_allowed_stake=max_allowed,
                adjusted_stake=max_allowed,
                warnings=warnings,
                recommendations=[f"Reduce stake to ${max_allowed:.2f}"]
            )
        
        # 2. Check daily volume
        current_daily = self.daily_volume.get(bookmaker.lower(), 0)
        if current_daily + stake > limits.max_daily_nhl:
            remaining = max(0, limits.max_daily_nhl - current_daily)
            warnings.append(
                f"Daily limit near: ${current_daily:.0f} of ${limits.max_daily_nhl:.0f} used"
            )
            if remaining < stake:
                return BetValidation(
                    status=BetValidationStatus.LIMIT_EXCEEDED,
                    is_valid=False,
                    max_allowed_stake=remaining,
                    adjusted_stake=remaining,
                    warnings=warnings
                )
        
        # 3. Check arbitrage timing
        if is_arbitrage and arb_detected_at:
            elapsed = (datetime.now() - arb_detected_at).total_seconds()
            if elapsed > self.ARB_EXPIRY_SECONDS:
                return BetValidation(
                    status=BetValidationStatus.ARB_WINDOW_EXPIRED,
                    is_valid=False,
                    warnings=[f"Arbitrage opportunity expired ({elapsed:.0f}s > {self.ARB_EXPIRY_SECONDS}s)"],
                    recommendations=["Re-check odds before placing bet"]
                )
            elif elapsed > self.ARB_EXPIRY_SECONDS * 0.7:
                warnings.append(f"Arbitrage window closing ({elapsed:.0f}s)")
                risk_factors["timing_risk"] = elapsed / self.ARB_EXPIRY_SECONDS
        
        # 4. Check slippage risk
        if stake > self.SLIPPAGE_THRESHOLD_USD:
            slippage_risk = (stake - self.SLIPPAGE_THRESHOLD_USD) / stake * 0.5
            risk_factors["slippage_risk"] = slippage_risk
            if slippage_risk > 0.1:
                warnings.append(
                    f"High slippage risk ({slippage_risk:.1%}) for large stake"
                )
                recommendations.append("Consider splitting into smaller bets")
        
        # 5. Check account restriction risk
        if limits.restriction_risk > 0.2:
            risk_factors["restriction_risk"] = limits.restriction_risk
            warnings.append(
                f"{bookmaker} has {limits.restriction_risk:.0%} restriction risk after winning"
            )
        
        # 6. Validate odds
        if odds < 1.01 or odds > 20:
            return BetValidation(
                status=BetValidationStatus.INVALID_ODDS,
                is_valid=False,
                warnings=[f"Suspicious odds: {odds}"]
            )
        
        # All checks passed
        return BetValidation(
            status=BetValidationStatus.VALID,
            is_valid=True,
            max_allowed_stake=max_allowed,
            adjusted_stake=stake,
            warnings=warnings,
            recommendations=recommendations,
            risk_factors=risk_factors
        )
    
    def validate_arbitrage(
        self,
        bookmaker_strong: str,
        bookmaker_weak: str,
        stake_strong: float,
        stake_weak: float,
        odds_strong: float,
        odds_weak: float,
        arb_detected_at: Optional[datetime] = None
    ) -> Tuple[BetValidation, BetValidation, Dict]:
        """Validate an arbitrage bet pair.
        
        Args:
            bookmaker_strong: Bookmaker for strong team bet
            bookmaker_weak: Bookmaker for weak team bet
            stake_strong: Stake on strong team
            stake_weak: Stake on weak team
            odds_strong: Odds for strong team
            odds_weak: Odds for weak team
            arb_detected_at: When opportunity was detected
            
        Returns:
            Tuple of (strong_validation, weak_validation, summary)
        """
        # Validate each leg
        strong_val = self.validate_bet(
            bookmaker_strong, stake_strong, odds_strong,
            is_arbitrage=True, arb_detected_at=arb_detected_at
        )
        
        weak_val = self.validate_bet(
            bookmaker_weak, stake_weak, odds_weak,
            is_arbitrage=True, arb_detected_at=arb_detected_at
        )
        
        # Calculate adjusted stakes if limits exceeded
        summary = {
            "both_valid": strong_val.is_valid and weak_val.is_valid,
            "total_original_stake": stake_strong + stake_weak,
            "all_warnings": strong_val.warnings + weak_val.warnings,
            "all_recommendations": strong_val.recommendations + weak_val.recommendations,
        }
        
        if not summary["both_valid"]:
            # Recalculate with adjusted stakes
            adj_strong = strong_val.adjusted_stake or strong_val.max_allowed_stake
            adj_weak = weak_val.adjusted_stake or weak_val.max_allowed_stake
            
            # Maintain arbitrage ratio
            original_ratio = stake_strong / (stake_strong + stake_weak) if stake_strong + stake_weak > 0 else 0.5
            
            # Use the more restrictive limit
            max_total = min(
                adj_strong / original_ratio if original_ratio > 0 else 0,
                adj_weak / (1 - original_ratio) if original_ratio < 1 else 0
            )
            
            summary["adjusted_total_stake"] = max_total
            summary["adjusted_strong_stake"] = max_total * original_ratio
            summary["adjusted_weak_stake"] = max_total * (1 - original_ratio)
        else:
            summary["adjusted_total_stake"] = stake_strong + stake_weak
            summary["adjusted_strong_stake"] = stake_strong
            summary["adjusted_weak_stake"] = stake_weak
        
        return strong_val, weak_val, summary
    
    def update_daily_volume(self, bookmaker: str, amount: float) -> None:
        """Update daily betting volume for a bookmaker."""
        key = bookmaker.lower()
        self.daily_volume[key] = self.daily_volume.get(key, 0) + amount
    
    def reset_daily_volume(self) -> None:
        """Reset daily volume (call at midnight)."""
        self.daily_volume.clear()
    
    def get_safe_stake_recommendation(
        self,
        bookmaker_strong: str,
        bookmaker_weak: str,
        target_roi: float = 0.03
    ) -> Dict:
        """Get recommended safe stake based on limits.
        
        Returns conservative stake recommendations that account for
        limits and restriction risk.
        """
        limits_strong = self.get_limits(bookmaker_strong)
        limits_weak = self.get_limits(bookmaker_weak)
        
        # Use the more conservative limit
        max_arb = min(limits_strong.max_arb_bet, limits_weak.max_arb_bet)
        
        # Further reduce based on restriction risk
        risk_multiplier = 1 - max(limits_strong.restriction_risk, limits_weak.restriction_risk)
        
        # Recommended stake
        safe_stake = max_arb * risk_multiplier * 0.7  # 70% of adjusted max
        
        return {
            "recommended_total_stake": safe_stake,
            "max_single_bet": max_arb,
            "risk_adjusted_max": max_arb * risk_multiplier,
            "expected_profit": safe_stake * target_roi,
            "warnings": [
                f"Max arbitrage bet: ${max_arb:.0f}",
                f"Risk adjustment: {risk_multiplier:.0%}",
                f"Using 70% of adjusted max for safety"
            ]
        }


# Export
__all__ = [
    'BettingValidator',
    'BetValidation', 
    'BetValidationStatus',
    'BookmakerLimits',
    'DEFAULT_BOOKMAKER_LIMITS'
]
