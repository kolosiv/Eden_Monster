"""Bankroll Manager for Eden MVP.

Tracks bankroll, calculates drawdown, and provides stake recommendations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from pydantic import BaseModel, Field

from utils.logger import get_logger
from bankroll.profiles import BankrollProfile, ProfileType, get_profile
from bankroll.risk_calculator import RiskCalculator, RiskMetrics
from bankroll.stake_adjuster import StakeAdjuster, AdjustmentResult

logger = get_logger(__name__)


class BankrollState(BaseModel):
    """Current state of the bankroll.
    
    Attributes:
        current: Current bankroll amount
        initial: Initial bankroll amount
        peak: Peak bankroll achieved
        drawdown: Current drawdown from peak
        drawdown_percent: Drawdown as percentage
        total_profit: Total profit/loss from initial
        roi: Return on investment percentage
        num_bets: Total number of bets placed
        win_count: Number of winning bets
        loss_count: Number of losing bets
        last_updated: Timestamp of last update
    """
    current: float = Field(ge=0)
    initial: float = Field(ge=0)
    peak: float = Field(ge=0)
    drawdown: float = Field(ge=0, default=0.0)
    drawdown_percent: float = Field(ge=0, le=100, default=0.0)
    total_profit: float = 0.0
    roi: float = 0.0
    num_bets: int = Field(ge=0, default=0)
    win_count: int = Field(ge=0, default=0)
    loss_count: int = Field(ge=0, default=0)
    last_updated: datetime = Field(default_factory=datetime.now)
    
    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage."""
        total = self.win_count + self.loss_count
        return (self.win_count / total * 100) if total > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'current': self.current,
            'initial': self.initial,
            'peak': self.peak,
            'drawdown': self.drawdown,
            'drawdown_percent': self.drawdown_percent,
            'total_profit': self.total_profit,
            'roi': self.roi,
            'num_bets': self.num_bets,
            'win_count': self.win_count,
            'loss_count': self.loss_count,
            'win_rate': self.win_rate,
            'last_updated': self.last_updated.isoformat()
        }


class BankrollManager:
    """Manages bankroll tracking, risk analysis, and stake recommendations.
    
    Features:
    - Track current, initial, and peak bankroll
    - Calculate drawdown and ROI
    - Recommend stake sizes based on profile
    - Integration with risk calculator and stake adjuster
    - Database persistence for history
    
    Example:
        >>> manager = BankrollManager(initial_bankroll=1000)
        >>> state = manager.get_state()
        >>> recommended_stake = manager.get_recommended_stake(analysis)
    """
    
    def __init__(
        self,
        initial_bankroll: float = 1000.0,
        profile: ProfileType = ProfileType.MODERATE,
        db_manager=None
    ):
        """Initialize BankrollManager.
        
        Args:
            initial_bankroll: Starting bankroll amount
            profile: Risk profile to use
            db_manager: DatabaseManager for persistence
        """
        self.db_manager = db_manager
        self.profile = get_profile(profile)
        
        # Initialize state
        self._current = initial_bankroll
        self._initial = initial_bankroll
        self._peak = initial_bankroll
        self._num_bets = 0
        self._win_count = 0
        self._loss_count = 0
        self._history: List[Dict[str, Any]] = []
        
        # Initialize components
        self.risk_calculator = RiskCalculator(self)
        self.stake_adjuster = StakeAdjuster(self)
        
        # Load from database if available
        if db_manager:
            self._load_from_database()
        
        logger.info(
            f"BankrollManager initialized: ${initial_bankroll:.2f}, "
            f"profile={profile.value}"
        )
    
    def _load_from_database(self) -> None:
        """Load bankroll state from database."""
        if not self.db_manager:
            return
        
        try:
            history = self.db_manager.get_bankroll_history(limit=1)
            if history:
                latest = history[0]
                self._current = latest.get('bankroll', self._initial)
                self._peak = max(self._peak, self._current)
                logger.info(f"Loaded bankroll from database: ${self._current:.2f}")
        except Exception as e:
            logger.warning(f"Could not load bankroll history: {e}")
    
    @property
    def current(self) -> float:
        """Current bankroll amount."""
        return self._current
    
    @property
    def initial(self) -> float:
        """Initial bankroll amount."""
        return self._initial
    
    @property
    def peak(self) -> float:
        """Peak bankroll achieved."""
        return self._peak
    
    @property
    def drawdown(self) -> float:
        """Current drawdown from peak (absolute)."""
        return max(0, self._peak - self._current)
    
    @property
    def drawdown_percent(self) -> float:
        """Current drawdown as percentage of peak."""
        if self._peak <= 0:
            return 0.0
        return (self.drawdown / self._peak) * 100
    
    @property
    def total_profit(self) -> float:
        """Total profit/loss from initial."""
        return self._current - self._initial
    
    @property
    def roi(self) -> float:
        """Return on investment percentage."""
        if self._initial <= 0:
            return 0.0
        return (self.total_profit / self._initial) * 100
    
    def get_state(self) -> BankrollState:
        """Get current bankroll state.
        
        Returns:
            BankrollState with current metrics
        """
        return BankrollState(
            current=self._current,
            initial=self._initial,
            peak=self._peak,
            drawdown=self.drawdown,
            drawdown_percent=self.drawdown_percent,
            total_profit=self.total_profit,
            roi=self.roi,
            num_bets=self._num_bets,
            win_count=self._win_count,
            loss_count=self._loss_count,
            last_updated=datetime.now()
        )
    
    def update_bankroll(
        self,
        new_amount: float,
        is_win: Optional[bool] = None,
        notes: str = ""
    ) -> BankrollState:
        """Update bankroll to new amount.
        
        Args:
            new_amount: New bankroll value
            is_win: Whether this was a winning bet (for tracking)
            notes: Optional notes for the update
            
        Returns:
            Updated BankrollState
        """
        if new_amount < 0:
            raise ValueError("Bankroll cannot be negative")
        
        old_amount = self._current
        self._current = new_amount
        
        # Update peak if new high
        if new_amount > self._peak:
            self._peak = new_amount
        
        # Track wins/losses
        if is_win is not None:
            self._num_bets += 1
            if is_win:
                self._win_count += 1
            else:
                self._loss_count += 1
        
        # Record history
        history_entry = {
            'timestamp': datetime.now(),
            'bankroll': new_amount,
            'change': new_amount - old_amount,
            'drawdown': self.drawdown_percent,
            'profile': self.profile.type.value,
            'notes': notes
        }
        self._history.append(history_entry)
        
        # Save to database
        if self.db_manager:
            try:
                self.db_manager.insert_bankroll_history(history_entry)
            except Exception as e:
                logger.warning(f"Failed to save bankroll history: {e}")
        
        state = self.get_state()
        logger.info(
            f"Bankroll updated: ${old_amount:.2f} -> ${new_amount:.2f} "
            f"(Drawdown: {state.drawdown_percent:.1f}%)"
        )
        
        return state
    
    def record_bet_result(
        self,
        stake: float,
        profit_loss: float,
        is_hole: bool = False
    ) -> BankrollState:
        """Record the result of a bet.
        
        Args:
            stake: Total stake amount
            profit_loss: Profit (positive) or loss (negative)
            is_hole: Whether this was a "hole" loss
            
        Returns:
            Updated BankrollState
        """
        new_amount = self._current + profit_loss
        is_win = profit_loss > 0
        
        notes = "Hole loss" if is_hole else ("Win" if is_win else "Loss")
        notes += f" | Stake: ${stake:.2f} | P/L: ${profit_loss:.2f}"
        
        return self.update_bankroll(new_amount, is_win=is_win, notes=notes)
    
    def get_recommended_stake(
        self,
        analysis=None,
        base_stake_percent: Optional[float] = None
    ) -> AdjustmentResult:
        """Get recommended stake based on current state and profile.
        
        Args:
            analysis: MatchAnalysis for context (optional)
            base_stake_percent: Override base stake percentage
            
        Returns:
            AdjustmentResult with recommended stake
        """
        return self.stake_adjuster.calculate_adjusted_stake(
            analysis=analysis,
            base_stake_percent=base_stake_percent
        )
    
    def get_risk_metrics(self) -> RiskMetrics:
        """Get comprehensive risk metrics.
        
        Returns:
            RiskMetrics with calculated values
        """
        return self.risk_calculator.calculate_all_metrics()
    
    def set_profile(self, profile: ProfileType) -> None:
        """Change the risk profile.
        
        Args:
            profile: New profile to use
        """
        self.profile = get_profile(profile)
        logger.info(f"Profile changed to: {profile.value}")
    
    def reset_to_initial(self) -> BankrollState:
        """Reset bankroll to initial amount.
        
        Returns:
            Reset BankrollState
        """
        self._current = self._initial
        self._peak = self._initial
        self._num_bets = 0
        self._win_count = 0
        self._loss_count = 0
        self._history = []
        
        return self.get_state()
    
    def set_initial_bankroll(self, amount: float) -> BankrollState:
        """Set a new initial bankroll amount.
        
        Args:
            amount: New initial bankroll
            
        Returns:
            Updated BankrollState
        """
        if amount <= 0:
            raise ValueError("Bankroll must be positive")
        
        self._initial = amount
        self._current = amount
        self._peak = amount
        
        return self.get_state()
    
    def get_history(
        self,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get bankroll history.
        
        Args:
            limit: Maximum records to return
            
        Returns:
            List of history entries
        """
        if self.db_manager:
            return self.db_manager.get_bankroll_history(limit=limit)
        return self._history[-limit:]
    
    def is_emergency_mode(self) -> bool:
        """Check if emergency protection should be active.
        
        Returns:
            True if drawdown exceeds emergency threshold
        """
        return self.drawdown_percent >= self.profile.emergency_drawdown_threshold
    
    def get_status_summary(self) -> str:
        """Get a human-readable status summary.
        
        Returns:
            Formatted status string
        """
        state = self.get_state()
        
        status = "=== BANKROLL STATUS ==="
        status += f"\nCurrent: ${state.current:,.2f}"
        status += f"\nInitial: ${state.initial:,.2f}"
        status += f"\nPeak: ${state.peak:,.2f}"
        status += f"\n\nDrawdown: ${state.drawdown:,.2f} ({state.drawdown_percent:.1f}%)"
        status += f"\nTotal P/L: ${state.total_profit:,.2f} ({state.roi:.1f}% ROI)"
        status += f"\n\nBets: {state.num_bets} (W: {state.win_count}, L: {state.loss_count})"
        status += f"\nWin Rate: {state.win_rate:.1f}%"
        status += f"\n\nProfile: {self.profile.type.value.title()}"
        
        if self.is_emergency_mode():
            status += "\n\n⚠️ EMERGENCY MODE ACTIVE"
        
        return status
