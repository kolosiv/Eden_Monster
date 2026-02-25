"""Dynamic Stake Adjuster for Eden MVP Bankroll Management.

Automatically adjusts stake sizes based on bankroll state and risk profile.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Dict, Any
from enum import Enum

from utils.logger import get_logger

if TYPE_CHECKING:
    from bankroll.manager import BankrollManager

logger = get_logger(__name__)


class AdjustmentReason(str, Enum):
    """Reasons for stake adjustment."""
    NORMAL = "normal"
    PROFIT_BOOST = "profit_boost"  # Increase due to bankroll growth
    DRAWDOWN_REDUCTION = "drawdown_reduction"  # Decrease due to drawdown
    EMERGENCY_PROTECTION = "emergency_protection"  # Emergency stake reduction
    HIGH_CONFIDENCE = "high_confidence"  # Increase for high confidence bet
    LOW_CONFIDENCE = "low_confidence"  # Decrease for low confidence bet
    HIGH_RISK = "high_risk"  # Decrease for high risk opportunity


@dataclass
class AdjustmentResult:
    """Result of stake adjustment calculation.
    
    Attributes:
        base_stake_percent: Original stake percentage
        adjusted_stake_percent: Adjusted stake percentage
        stake_amount: Absolute stake amount
        adjustment_factor: Multiplier applied
        reason: Primary reason for adjustment
        is_emergency: Whether emergency mode is active
        min_stake: Minimum allowed stake
        max_stake: Maximum allowed stake
        warnings: List of warning messages
    """
    base_stake_percent: float
    adjusted_stake_percent: float
    stake_amount: float
    adjustment_factor: float
    reason: AdjustmentReason
    is_emergency: bool
    min_stake: float
    max_stake: float
    warnings: list
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'base_stake_percent': self.base_stake_percent,
            'adjusted_stake_percent': self.adjusted_stake_percent,
            'stake_amount': self.stake_amount,
            'adjustment_factor': self.adjustment_factor,
            'reason': self.reason.value,
            'is_emergency': self.is_emergency,
            'min_stake': self.min_stake,
            'max_stake': self.max_stake,
            'warnings': self.warnings
        }


class StakeAdjuster:
    """Dynamically adjusts stakes based on bankroll state and profile.
    
    Rules:
    1. Increase stakes when bankroll grows (e.g., +10% bankroll → +5% stake)
    2. Decrease stakes during drawdown (e.g., -10% bankroll → -15% stake)
    3. Emergency protection: reduce to minimum if drawdown > threshold
    4. Smooth adjustment: gradual changes, not sudden jumps
    5. Respect min/max limits from profile
    
    Example:
        >>> adjuster = StakeAdjuster(manager)
        >>> result = adjuster.calculate_adjusted_stake(analysis)
        >>> print(f"Stake: ${result.stake_amount:.2f} ({result.reason.value})")
    """
    
    def __init__(self, manager: 'BankrollManager'):
        """Initialize StakeAdjuster.
        
        Args:
            manager: Parent BankrollManager
        """
        self.manager = manager
        self._last_adjustment_factor = 1.0  # For smoothing
    
    def calculate_adjusted_stake(
        self,
        analysis=None,
        base_stake_percent: Optional[float] = None
    ) -> AdjustmentResult:
        """Calculate the adjusted stake based on current conditions.
        
        Args:
            analysis: Optional MatchAnalysis for context
            base_stake_percent: Override base stake percentage
            
        Returns:
            AdjustmentResult with recommended stake
        """
        profile = self.manager.profile
        state = self.manager.get_state()
        
        base_pct = base_stake_percent or profile.base_stake_percent
        
        warnings = []
        adjustment_factor = 1.0
        primary_reason = AdjustmentReason.NORMAL
        is_emergency = False
        
        # 1. Check for emergency mode
        if self.manager.is_emergency_mode():
            is_emergency = True
            adjustment_factor = profile.emergency_stake_reduction
            primary_reason = AdjustmentReason.EMERGENCY_PROTECTION
            warnings.append(
                f"⚠️ EMERGENCY: Drawdown {state.drawdown_percent:.1f}% exceeds "
                f"{profile.emergency_drawdown_threshold}% threshold"
            )
        else:
            # 2. Calculate growth/drawdown adjustment
            bankroll_change = (state.current - state.initial) / state.initial
            
            if bankroll_change > 0:
                # Profit - increase stakes proportionally (but less aggressively)
                profit_boost = bankroll_change * profile.profit_stake_increase_rate
                profit_boost = min(profit_boost, profile.max_stake_increase)  # Cap increase
                adjustment_factor *= (1 + profit_boost)
                if profit_boost > 0.05:
                    primary_reason = AdjustmentReason.PROFIT_BOOST
            
            # 3. Drawdown reduction (more aggressive than profit increase)
            if state.drawdown_percent > profile.drawdown_stake_reduction_start:
                drawdown_factor = state.drawdown_percent / 100
                reduction = drawdown_factor * profile.drawdown_stake_reduction_rate
                reduction = min(reduction, 1 - profile.min_stake_percent / base_pct)  # Don't go below min
                adjustment_factor *= (1 - reduction)
                primary_reason = AdjustmentReason.DRAWDOWN_REDUCTION
                
                if state.drawdown_percent > 15:
                    warnings.append(
                        f"⚠️ High drawdown ({state.drawdown_percent:.1f}%): "
                        f"Stakes reduced by {reduction*100:.0f}%"
                    )
        
        # 4. Analysis-based adjustments
        if analysis is not None:
            # Confidence adjustment
            confidence = getattr(analysis, 'confidence_score', 0.5)
            if confidence > 0.8:
                adjustment_factor *= 1.1
                if primary_reason == AdjustmentReason.NORMAL:
                    primary_reason = AdjustmentReason.HIGH_CONFIDENCE
            elif confidence < 0.4:
                adjustment_factor *= 0.8
                if primary_reason == AdjustmentReason.NORMAL:
                    primary_reason = AdjustmentReason.LOW_CONFIDENCE
            
            # Risk level adjustment
            risk_level = str(getattr(analysis, 'risk_level', 'MEDIUM')).upper()
            if 'EXTREME' in risk_level:
                adjustment_factor *= 0.5
                primary_reason = AdjustmentReason.HIGH_RISK
                warnings.append("⚠️ EXTREME risk level - stake halved")
            elif 'HIGH' in risk_level:
                adjustment_factor *= 0.75
                if primary_reason == AdjustmentReason.NORMAL:
                    primary_reason = AdjustmentReason.HIGH_RISK
            elif 'LOW' in risk_level:
                adjustment_factor *= 1.1
        
        # 5. Apply smoothing to prevent sudden changes
        smoothing_factor = 0.7  # Weight towards new value
        smoothed_factor = (
            smoothing_factor * adjustment_factor +
            (1 - smoothing_factor) * self._last_adjustment_factor
        )
        self._last_adjustment_factor = smoothed_factor
        
        # 6. Calculate final stake
        adjusted_pct = base_pct * smoothed_factor
        
        # 7. Apply min/max limits
        min_pct = profile.min_stake_percent
        max_pct = profile.max_stake_percent
        
        if adjusted_pct < min_pct:
            adjusted_pct = min_pct
            warnings.append(f"Stake clamped to minimum: {min_pct*100:.1f}%")
        elif adjusted_pct > max_pct:
            adjusted_pct = max_pct
            warnings.append(f"Stake clamped to maximum: {max_pct*100:.1f}%")
        
        # Calculate absolute amounts
        bankroll = state.current
        stake_amount = bankroll * adjusted_pct
        min_stake = bankroll * min_pct
        max_stake = bankroll * max_pct
        
        result = AdjustmentResult(
            base_stake_percent=base_pct,
            adjusted_stake_percent=adjusted_pct,
            stake_amount=stake_amount,
            adjustment_factor=smoothed_factor,
            reason=primary_reason,
            is_emergency=is_emergency,
            min_stake=min_stake,
            max_stake=max_stake,
            warnings=warnings
        )
        
        logger.debug(
            f"Stake adjusted: {base_pct*100:.1f}% -> {adjusted_pct*100:.1f}% "
            f"(factor: {smoothed_factor:.2f}, reason: {primary_reason.value})"
        )
        
        return result
    
    def get_stake_for_amount(
        self,
        target_amount: float,
        analysis=None
    ) -> AdjustmentResult:
        """Calculate adjustment result for a target stake amount.
        
        Args:
            target_amount: Desired stake amount
            analysis: Optional analysis for context
            
        Returns:
            AdjustmentResult (may differ from target due to limits)
        """
        bankroll = self.manager.current
        if bankroll <= 0:
            raise ValueError("Bankroll must be positive")
        
        target_pct = target_amount / bankroll
        return self.calculate_adjusted_stake(analysis, base_stake_percent=target_pct)
    
    def is_stake_safe(
        self,
        stake_amount: float,
        analysis=None
    ) -> tuple:
        """Check if a stake amount is within safe limits.
        
        Args:
            stake_amount: Amount to check
            analysis: Optional analysis for context
            
        Returns:
            Tuple of (is_safe, warnings)
        """
        result = self.get_stake_for_amount(stake_amount, analysis)
        
        is_safe = (
            result.stake_amount >= result.min_stake and
            result.stake_amount <= result.max_stake and
            not result.is_emergency
        )
        
        return is_safe, result.warnings
    
    def reset_smoothing(self) -> None:
        """Reset the smoothing factor to default."""
        self._last_adjustment_factor = 1.0
