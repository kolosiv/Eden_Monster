"""Stake Calculator Module for Eden MVP.

Calculates optimal betting stakes using various strategies.
Integrates with BankrollManager for dynamic stake adjustment.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple, TYPE_CHECKING
from enum import Enum

from pydantic import BaseModel, Field

from analysis.match_analyzer import MatchAnalysis, Recommendation, RiskLevel
from utils.logger import get_logger

if TYPE_CHECKING:
    from bankroll.manager import BankrollManager

logger = get_logger(__name__)


class StakingStrategy(str, Enum):
    """Available staking strategies."""
    FIXED = "fixed"  # Fixed percentage of bankroll
    KELLY = "kelly"  # Kelly Criterion
    ADAPTIVE = "adaptive"  # Adaptive based on confidence
    ARBITRAGE = "arbitrage"  # Equal payout arbitrage


class StakeResult(BaseModel):
    """Result of stake calculation.
    
    Attributes:
        strategy: Strategy used
        stake_strong: Stake on strong team
        stake_weak: Stake on weak team
        total_stake: Total stake amount
        potential_profit: Expected profit if successful
        risk_amount: Maximum amount at risk
    """
    strategy: StakingStrategy
    stake_strong: float = Field(ge=0)
    stake_weak: float = Field(ge=0)
    total_stake: float = Field(ge=0)
    potential_profit: float
    risk_amount: float = Field(ge=0)
    profit_if_strong_wins: float = 0.0
    profit_if_weak_wins: float = 0.0
    loss_if_hole: float = 0.0


@dataclass
class StakeConfig:
    """Configuration for stake calculator."""
    bankroll: float = 1000.0
    min_stake_percent: float = 0.02  # 2%
    max_stake_percent: float = 0.10  # 10%
    default_stake_percent: float = 0.04  # 4%
    kelly_shrink: float = 0.5  # 50% Kelly
    max_risk_per_bet: float = 0.05  # 5% max risk


class StakeCalculator:
    """Calculates optimal betting stakes.
    
    Supports multiple staking strategies:
    - Fixed percentage: Simple fixed % of bankroll
    - Kelly Criterion: Mathematically optimal sizing
    - Adaptive: Adjusts based on confidence and risk
    - Arbitrage: Equal payout distribution
    - Smart: Uses BankrollManager for dynamic adjustment
    
    Example:
        >>> calc = StakeCalculator(config)
        >>> result = calc.calculate(analysis, StakingStrategy.ADAPTIVE)
        >>> print(f"Stake: ${result.total_stake:.2f}")
    """
    
    def __init__(
        self,
        config: Optional[StakeConfig] = None,
        bankroll_manager: Optional['BankrollManager'] = None
    ):
        """Initialize StakeCalculator.
        
        Args:
            config: Stake calculation configuration
            bankroll_manager: Optional BankrollManager for smart staking
        """
        self.config = config or StakeConfig()
        self._bankroll_manager = bankroll_manager
    
    def set_bankroll_manager(self, manager: 'BankrollManager') -> None:
        """Set the bankroll manager for smart staking.
        
        Args:
            manager: BankrollManager instance
        """
        self._bankroll_manager = manager
        # Sync bankroll from manager
        if manager:
            self.config.bankroll = manager.current
            logger.info(f"StakeCalculator synced with BankrollManager: ${manager.current:.2f}")
        
    def kelly_fraction(
        self,
        probability: float,
        odds: float
    ) -> float:
        """Calculate Kelly Criterion fraction for single bet.
        
        Kelly formula: f* = (bp - q) / b
        where:
            b = decimal odds - 1 (profit per unit)
            p = probability of winning
            q = 1 - p (probability of losing)
        
        Args:
            probability: Probability of winning
            odds: Decimal odds
            
        Returns:
            Optimal fraction of bankroll to stake
        """
        if odds <= 1 or probability <= 0 or probability >= 1:
            return 0.0
            
        b = odds - 1  # Profit per unit bet
        q = 1 - probability
        
        kelly = (b * probability - q) / b
        
        # Apply shrink factor and bounds
        kelly = kelly * self.config.kelly_shrink
        kelly = max(0, min(kelly, self.config.max_stake_percent))
        
        return kelly
    
    def calculate_arbitrage_stakes(
        self,
        total_stake: float,
        odds_strong: float,
        odds_weak: float
    ) -> Tuple[float, float]:
        """Calculate arbitrage stake distribution for equal payout.
        
        Stakes are distributed so that payout is equal regardless
        of which bet wins (excluding hole scenario).
        
        stake_strong / stake_weak = odds_weak / odds_strong
        
        Args:
            total_stake: Total amount to stake
            odds_strong: Odds for strong team
            odds_weak: Odds for weak team
            
        Returns:
            Tuple of (stake_strong, stake_weak)
        """
        inv_s = 1 / odds_strong
        inv_w = 1 / odds_weak
        total_inv = inv_s + inv_w
        
        stake_strong = total_stake * (inv_s / total_inv)
        stake_weak = total_stake * (inv_w / total_inv)
        
        return stake_strong, stake_weak
    
    def calculate_fixed_stake(
        self,
        analysis: MatchAnalysis,
        percentage: Optional[float] = None
    ) -> StakeResult:
        """Calculate stakes using fixed percentage strategy.
        
        Args:
            analysis: Match analysis
            percentage: Stake percentage (uses default if None)
            
        Returns:
            StakeResult with calculated stakes
        """
        pct = percentage or self.config.default_stake_percent
        total_stake = self.config.bankroll * pct
        
        stake_strong, stake_weak = self.calculate_arbitrage_stakes(
            total_stake, analysis.odds_strong, analysis.odds_weak_reg
        )
        
        # Calculate outcomes
        payout = stake_strong * analysis.odds_strong
        profit_if_win = payout - total_stake
        loss_if_hole = total_stake
        
        return StakeResult(
            strategy=StakingStrategy.FIXED,
            stake_strong=round(stake_strong, 2),
            stake_weak=round(stake_weak, 2),
            total_stake=round(total_stake, 2),
            potential_profit=round(profit_if_win, 2),
            risk_amount=round(loss_if_hole, 2),
            profit_if_strong_wins=round(profit_if_win, 2),
            profit_if_weak_wins=round(profit_if_win, 2),
            loss_if_hole=round(loss_if_hole, 2)
        )
    
    def calculate_kelly_stake(
        self,
        analysis: MatchAnalysis
    ) -> StakeResult:
        """Calculate stakes using Kelly Criterion.
        
        Uses modified Kelly for two-legged bet:
        - Calculate Kelly for each leg separately
        - Apply shrink factor for safety
        - Ensure total doesn't exceed max stake
        
        Args:
            analysis: Match analysis
            
        Returns:
            StakeResult with calculated stakes
        """
        # Estimate win probability from implied odds and hole probability
        p_strong = (1 / analysis.odds_strong) / (
            (1 / analysis.odds_strong) + (1 / analysis.odds_weak_reg)
        ) * (1 - analysis.hole_probability)
        p_weak = (1 - analysis.hole_probability - p_strong)
        
        # Calculate Kelly fractions
        f_strong = self.kelly_fraction(p_strong, analysis.odds_strong)
        f_weak = self.kelly_fraction(p_weak, analysis.odds_weak_reg)
        
        # Calculate stakes
        stake_strong = self.config.bankroll * f_strong
        stake_weak = self.config.bankroll * f_weak
        total_stake = stake_strong + stake_weak
        
        # Ensure doesn't exceed max
        if total_stake > self.config.bankroll * self.config.max_stake_percent:
            scale = (self.config.bankroll * self.config.max_stake_percent) / total_stake
            stake_strong *= scale
            stake_weak *= scale
            total_stake = stake_strong + stake_weak
        
        # Calculate outcomes
        payout_strong = stake_strong * analysis.odds_strong
        payout_weak = stake_weak * analysis.odds_weak_reg
        
        return StakeResult(
            strategy=StakingStrategy.KELLY,
            stake_strong=round(stake_strong, 2),
            stake_weak=round(stake_weak, 2),
            total_stake=round(total_stake, 2),
            potential_profit=round(max(payout_strong, payout_weak) - total_stake, 2),
            risk_amount=round(total_stake, 2),
            profit_if_strong_wins=round(payout_strong - total_stake, 2),
            profit_if_weak_wins=round(payout_weak - total_stake, 2),
            loss_if_hole=round(total_stake, 2)
        )
    
    def calculate_adaptive_stake(
        self,
        analysis: MatchAnalysis
    ) -> StakeResult:
        """Calculate stakes using adaptive strategy.
        
        Adjusts stake based on:
        - Confidence score
        - Risk level
        - ROI opportunity
        
        Args:
            analysis: Match analysis
            
        Returns:
            StakeResult with calculated stakes
        """
        base_pct = self.config.default_stake_percent
        
        # Confidence multiplier (0.5 to 1.5)
        confidence_mult = 0.5 + analysis.confidence_score
        
        # Risk adjustment
        risk_mults = {
            RiskLevel.LOW: 1.2,
            RiskLevel.MEDIUM: 1.0,
            RiskLevel.HIGH: 0.6,
            RiskLevel.EXTREME: 0.3
        }
        risk_mult = risk_mults.get(analysis.risk_level, 1.0)
        
        # ROI bonus (higher ROI = slightly larger stake)
        roi_mult = 1.0 + min(analysis.arb_roi * 5, 0.3)  # Max 30% bonus
        
        # Calculate final percentage
        final_pct = base_pct * confidence_mult * risk_mult * roi_mult
        
        # Apply bounds
        final_pct = max(self.config.min_stake_percent, 
                       min(final_pct, self.config.max_stake_percent))
        
        total_stake = self.config.bankroll * final_pct
        
        stake_strong, stake_weak = self.calculate_arbitrage_stakes(
            total_stake, analysis.odds_strong, analysis.odds_weak_reg
        )
        
        # Calculate outcomes
        payout = stake_strong * analysis.odds_strong
        profit_if_win = payout - total_stake
        
        return StakeResult(
            strategy=StakingStrategy.ADAPTIVE,
            stake_strong=round(stake_strong, 2),
            stake_weak=round(stake_weak, 2),
            total_stake=round(total_stake, 2),
            potential_profit=round(profit_if_win, 2),
            risk_amount=round(total_stake, 2),
            profit_if_strong_wins=round(profit_if_win, 2),
            profit_if_weak_wins=round(profit_if_win, 2),
            loss_if_hole=round(total_stake, 2)
        )
    
    def calculate_smart_stake(
        self,
        analysis: MatchAnalysis
    ) -> StakeResult:
        """Calculate stakes using BankrollManager's smart adjustment.
        
        This method integrates with the bankroll manager for:
        - Dynamic stake sizing based on bankroll state
        - Profile-based limits
        - Emergency protection
        - Drawdown-aware adjustment
        
        Args:
            analysis: Match analysis
            
        Returns:
            StakeResult with dynamically adjusted stakes
        """
        if not self._bankroll_manager:
            logger.warning("No BankrollManager set, falling back to adaptive strategy")
            return self.calculate_adaptive_stake(analysis)
        
        # Get recommended stake from bankroll manager
        adjustment = self._bankroll_manager.get_recommended_stake(analysis)
        
        total_stake = adjustment.stake_amount
        
        # Distribute between strong and weak bets
        stake_strong, stake_weak = self.calculate_arbitrage_stakes(
            total_stake, analysis.odds_strong, analysis.odds_weak_reg
        )
        
        # Calculate outcomes
        payout = stake_strong * analysis.odds_strong
        profit_if_win = payout - total_stake
        
        # Add warnings to logger
        for warning in adjustment.warnings:
            logger.warning(warning)
        
        return StakeResult(
            strategy=StakingStrategy.ADAPTIVE,  # Report as adaptive
            stake_strong=round(stake_strong, 2),
            stake_weak=round(stake_weak, 2),
            total_stake=round(total_stake, 2),
            potential_profit=round(profit_if_win, 2),
            risk_amount=round(total_stake, 2),
            profit_if_strong_wins=round(profit_if_win, 2),
            profit_if_weak_wins=round(profit_if_win, 2),
            loss_if_hole=round(total_stake, 2)
        )
    
    def calculate(
        self,
        analysis: MatchAnalysis,
        strategy: StakingStrategy = StakingStrategy.ADAPTIVE,
        use_bankroll_manager: bool = True
    ) -> StakeResult:
        """Calculate stakes using specified strategy.
        
        Args:
            analysis: Match analysis
            strategy: Staking strategy to use
            use_bankroll_manager: Whether to use BankrollManager if available
            
        Returns:
            StakeResult with calculated stakes
        """
        if analysis.recommendation == Recommendation.SKIP:
            logger.debug(f"Skipping stake calculation for {analysis.match_id} - recommendation is SKIP")
            return StakeResult(
                strategy=strategy,
                stake_strong=0,
                stake_weak=0,
                total_stake=0,
                potential_profit=0,
                risk_amount=0
            )
        
        # Use smart staking if bankroll manager is available and enabled
        if use_bankroll_manager and self._bankroll_manager and strategy == StakingStrategy.ADAPTIVE:
            return self.calculate_smart_stake(analysis)
        
        if strategy == StakingStrategy.FIXED:
            return self.calculate_fixed_stake(analysis)
        elif strategy == StakingStrategy.KELLY:
            return self.calculate_kelly_stake(analysis)
        elif strategy == StakingStrategy.ADAPTIVE:
            return self.calculate_adaptive_stake(analysis)
        elif strategy == StakingStrategy.ARBITRAGE:
            return self.calculate_fixed_stake(analysis)  # Same distribution
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
    
    def calculate_all_strategies(
        self,
        analysis: MatchAnalysis
    ) -> Dict[StakingStrategy, StakeResult]:
        """Calculate stakes for all available strategies.
        
        Args:
            analysis: Match analysis
            
        Returns:
            Dict mapping strategy to StakeResult
        """
        return {
            StakingStrategy.FIXED: self.calculate_fixed_stake(analysis),
            StakingStrategy.KELLY: self.calculate_kelly_stake(analysis),
            StakingStrategy.ADAPTIVE: self.calculate_adaptive_stake(analysis)
        }
    
    def update_bankroll(self, new_bankroll: float) -> None:
        """Update bankroll amount.
        
        Args:
            new_bankroll: New bankroll value
        """
        if new_bankroll <= 0:
            raise ValueError("Bankroll must be positive")
        self.config.bankroll = new_bankroll
        logger.info(f"Bankroll updated to ${new_bankroll:.2f}")
    
    def get_bankroll_summary(self) -> Dict:
        """Get current bankroll configuration summary.
        
        Returns:
            Dict with bankroll settings
        """
        return {
            "bankroll": self.config.bankroll,
            "min_stake": self.config.bankroll * self.config.min_stake_percent,
            "max_stake": self.config.bankroll * self.config.max_stake_percent,
            "default_stake": self.config.bankroll * self.config.default_stake_percent,
            "kelly_shrink": self.config.kelly_shrink
        }
