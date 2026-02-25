"""Risk Calculator for Eden MVP Bankroll Management.

Provides risk analysis including Risk of Ruin, Monte Carlo simulations,
Kelly fraction, and Sharpe ratio calculations.
"""

import math
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Dict, Tuple, Optional, Any

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

from utils.logger import get_logger

if TYPE_CHECKING:
    from bankroll.manager import BankrollManager

logger = get_logger(__name__)


@dataclass
class RiskMetrics:
    """Comprehensive risk metrics for the bankroll.
    
    Attributes:
        risk_of_ruin: Probability of losing X% of bankroll
        risk_of_ruin_50: Probability of losing 50% of bankroll
        risk_of_ruin_100: Probability of going bust
        optimal_kelly: Optimal Kelly fraction
        current_kelly_usage: Current stake as % of optimal Kelly
        sharpe_ratio: Risk-adjusted return metric
        max_drawdown: Maximum historical drawdown
        avg_drawdown: Average drawdown
        variance: Return variance
        expected_growth: Expected long-term growth rate
        monte_carlo_results: Summary of MC simulation
    """
    risk_of_ruin: float = 0.0
    risk_of_ruin_50: float = 0.0
    risk_of_ruin_100: float = 0.0
    optimal_kelly: float = 0.0
    current_kelly_usage: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    avg_drawdown: float = 0.0
    variance: float = 0.0
    expected_growth: float = 0.0
    monte_carlo_results: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'risk_of_ruin': self.risk_of_ruin,
            'risk_of_ruin_50': self.risk_of_ruin_50,
            'risk_of_ruin_100': self.risk_of_ruin_100,
            'optimal_kelly': self.optimal_kelly,
            'current_kelly_usage': self.current_kelly_usage,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'avg_drawdown': self.avg_drawdown,
            'variance': self.variance,
            'expected_growth': self.expected_growth,
            'monte_carlo_results': self.monte_carlo_results
        }


class RiskCalculator:
    """Calculates comprehensive risk metrics for bankroll management.
    
    Features:
    - Risk of Ruin calculation
    - Monte Carlo simulations
    - Kelly Criterion optimization
    - Sharpe ratio calculation
    - Maximum drawdown analysis
    
    Example:
        >>> calc = RiskCalculator(manager)
        >>> metrics = calc.calculate_all_metrics()
        >>> print(f"Risk of Ruin (50%): {metrics.risk_of_ruin_50:.1%}")
    """
    
    def __init__(self, manager: 'BankrollManager'):
        """Initialize RiskCalculator.
        
        Args:
            manager: Parent BankrollManager
        """
        self.manager = manager
    
    def calculate_risk_of_ruin(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        ruin_level: float = 0.5,
        stake_fraction: float = 0.04
    ) -> float:
        """Calculate probability of reaching ruin level.
        
        Uses the gambler's ruin formula adapted for non-even bets.
        
        Args:
            win_rate: Probability of winning (0-1)
            avg_win: Average win amount relative to stake
            avg_loss: Average loss amount relative to stake
            ruin_level: Fraction of bankroll considered ruin (0.5 = 50% loss)
            stake_fraction: Fraction of bankroll staked per bet
            
        Returns:
            Probability of reaching ruin (0-1)
        """
        if win_rate <= 0 or win_rate >= 1:
            return 0.0 if win_rate >= 1 else 1.0
        
        # Calculate edge
        edge = win_rate * avg_win - (1 - win_rate) * avg_loss
        
        if edge <= 0:
            # Negative or zero edge - high risk of ruin
            return min(1.0, 0.5 + abs(edge) * 2)
        
        # Simplified Risk of Ruin formula
        # RoR = ((1 - edge) / (1 + edge)) ^ units_to_ruin
        units_to_ruin = (1 - ruin_level) / stake_fraction
        
        try:
            # Clamp the ratio to avoid math errors
            ratio = max(0.001, min(0.999, (1 - edge) / (1 + edge)))
            ror = math.pow(ratio, units_to_ruin)
            return min(1.0, max(0.0, ror))
        except (ValueError, OverflowError):
            return 0.5
    
    def monte_carlo_simulation(
        self,
        n_simulations: int = 1000,
        n_bets: int = 100,
        win_rate: Optional[float] = None,
        avg_win: float = 0.04,  # 4% profit on win
        avg_loss: float = 1.0,  # 100% loss on hole
        stake_fraction: Optional[float] = None
    ) -> Dict[str, Any]:
        """Run Monte Carlo simulation of future outcomes.
        
        Args:
            n_simulations: Number of simulation runs
            n_bets: Number of bets per simulation
            win_rate: Probability of winning per bet
            avg_win: Average win as fraction of stake
            avg_loss: Average loss as fraction of stake  
            stake_fraction: Stake as fraction of bankroll
            
        Returns:
            Dict with simulation results
        """
        state = self.manager.get_state()
        
        # Use actual stats if available
        if win_rate is None:
            total_bets = state.win_count + state.loss_count
            if total_bets > 0:
                win_rate = state.win_count / total_bets
            else:
                win_rate = 0.85  # Default assumption
        
        if stake_fraction is None:
            stake_fraction = self.manager.profile.base_stake_percent
        
        initial_bankroll = self.manager.current
        final_bankrolls = []
        max_drawdowns = []
        ruin_count = 0
        
        for _ in range(n_simulations):
            bankroll = initial_bankroll
            peak = bankroll
            max_dd = 0
            
            for _ in range(n_bets):
                if bankroll <= 0:
                    ruin_count += 1
                    break
                
                stake = bankroll * stake_fraction
                
                # Simulate bet outcome
                if random.random() < win_rate:
                    # Win
                    bankroll += stake * avg_win
                else:
                    # Loss
                    bankroll -= stake * avg_loss
                
                # Track peak and drawdown
                if bankroll > peak:
                    peak = bankroll
                
                current_dd = (peak - bankroll) / peak if peak > 0 else 0
                max_dd = max(max_dd, current_dd)
            
            final_bankrolls.append(bankroll)
            max_drawdowns.append(max_dd)
        
        if NUMPY_AVAILABLE:
            final_arr = np.array(final_bankrolls)
            dd_arr = np.array(max_drawdowns)
            
            results = {
                'mean_final': float(np.mean(final_arr)),
                'median_final': float(np.median(final_arr)),
                'std_final': float(np.std(final_arr)),
                'percentile_5': float(np.percentile(final_arr, 5)),
                'percentile_25': float(np.percentile(final_arr, 25)),
                'percentile_75': float(np.percentile(final_arr, 75)),
                'percentile_95': float(np.percentile(final_arr, 95)),
                'prob_profit': float(np.mean(final_arr > initial_bankroll)),
                'prob_50_loss': float(np.mean(final_arr < initial_bankroll * 0.5)),
                'prob_ruin': ruin_count / n_simulations,
                'avg_max_drawdown': float(np.mean(dd_arr)),
                'max_max_drawdown': float(np.max(dd_arr)),
                'final_bankrolls': final_bankrolls[:100],  # Sample for charts
                'n_simulations': n_simulations,
                'n_bets': n_bets
            }
        else:
            # Fallback without numpy
            sorted_finals = sorted(final_bankrolls)
            n = len(sorted_finals)
            
            results = {
                'mean_final': sum(final_bankrolls) / n,
                'median_final': sorted_finals[n // 2],
                'std_final': math.sqrt(sum((x - sum(final_bankrolls)/n)**2 for x in final_bankrolls) / n),
                'percentile_5': sorted_finals[int(n * 0.05)],
                'percentile_25': sorted_finals[int(n * 0.25)],
                'percentile_75': sorted_finals[int(n * 0.75)],
                'percentile_95': sorted_finals[int(n * 0.95)],
                'prob_profit': sum(1 for x in final_bankrolls if x > initial_bankroll) / n,
                'prob_50_loss': sum(1 for x in final_bankrolls if x < initial_bankroll * 0.5) / n,
                'prob_ruin': ruin_count / n_simulations,
                'avg_max_drawdown': sum(max_drawdowns) / n,
                'max_max_drawdown': max(max_drawdowns),
                'final_bankrolls': final_bankrolls[:100],
                'n_simulations': n_simulations,
                'n_bets': n_bets
            }
        
        logger.debug(f"Monte Carlo complete: Mean final = ${results['mean_final']:.2f}")
        return results
    
    def calculate_optimal_kelly(
        self,
        win_rate: float,
        odds: float = 1.04  # Typical arb profit ratio
    ) -> float:
        """Calculate optimal Kelly fraction for betting.
        
        Kelly formula: f* = (bp - q) / b
        where b = odds - 1, p = win probability, q = 1 - p
        
        Args:
            win_rate: Probability of winning
            odds: Decimal odds (1.04 = 4% profit)
            
        Returns:
            Optimal fraction of bankroll to stake
        """
        if win_rate <= 0 or win_rate >= 1 or odds <= 1:
            return 0.0
        
        b = odds - 1
        q = 1 - win_rate
        
        kelly = (b * win_rate - q) / b
        
        # Kelly can suggest negative bets, clamp to 0
        return max(0.0, kelly)
    
    def calculate_sharpe_ratio(
        self,
        returns: List[float],
        risk_free_rate: float = 0.02  # 2% annualized
    ) -> float:
        """Calculate Sharpe ratio from historical returns.
        
        Sharpe = (Mean Return - Risk Free Rate) / Std Dev of Returns
        
        Args:
            returns: List of periodic returns
            risk_free_rate: Risk-free rate for comparison
            
        Returns:
            Sharpe ratio (higher is better)
        """
        if len(returns) < 2:
            return 0.0
        
        if NUMPY_AVAILABLE:
            mean_return = np.mean(returns)
            std_return = np.std(returns)
        else:
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            std_return = math.sqrt(variance)
        
        if std_return == 0:
            return 0.0
        
        # Assuming returns are per-bet, annualize (rough approximation)
        # Assume ~250 bets per year
        annualized_return = mean_return * 250
        annualized_std = std_return * math.sqrt(250)
        
        sharpe = (annualized_return - risk_free_rate) / annualized_std
        
        return sharpe
    
    def analyze_drawdowns(
        self,
        bankroll_history: List[float]
    ) -> Dict[str, float]:
        """Analyze drawdown characteristics from history.
        
        Args:
            bankroll_history: List of historical bankroll values
            
        Returns:
            Dict with drawdown analysis
        """
        if len(bankroll_history) < 2:
            return {
                'max_drawdown': 0.0,
                'avg_drawdown': 0.0,
                'max_drawdown_duration': 0,
                'current_drawdown': 0.0
            }
        
        peak = bankroll_history[0]
        max_dd = 0.0
        current_dd = 0.0
        drawdowns = []
        dd_duration = 0
        max_dd_duration = 0
        
        for value in bankroll_history:
            if value > peak:
                peak = value
                if dd_duration > max_dd_duration:
                    max_dd_duration = dd_duration
                dd_duration = 0
            else:
                dd_duration += 1
            
            if peak > 0:
                dd = (peak - value) / peak
                drawdowns.append(dd)
                max_dd = max(max_dd, dd)
                current_dd = dd
        
        return {
            'max_drawdown': max_dd,
            'avg_drawdown': sum(drawdowns) / len(drawdowns) if drawdowns else 0.0,
            'max_drawdown_duration': max_dd_duration,
            'current_drawdown': current_dd
        }
    
    def calculate_all_metrics(
        self,
        run_monte_carlo: bool = True
    ) -> RiskMetrics:
        """Calculate all risk metrics.
        
        Args:
            run_monte_carlo: Whether to run MC simulation
            
        Returns:
            Complete RiskMetrics
        """
        state = self.manager.get_state()
        
        # Get win rate from state
        total_bets = state.win_count + state.loss_count
        win_rate = state.win_rate / 100 if total_bets > 0 else 0.85
        
        # Calculate Risk of Ruin at different levels
        stake_frac = self.manager.profile.base_stake_percent
        ror = self.calculate_risk_of_ruin(
            win_rate=win_rate,
            avg_win=0.04,  # Assume 4% profit on wins
            avg_loss=1.0,  # Full stake loss on holes
            ruin_level=0.5,
            stake_fraction=stake_frac
        )
        ror_50 = ror
        ror_100 = self.calculate_risk_of_ruin(
            win_rate=win_rate,
            avg_win=0.04,
            avg_loss=1.0,
            ruin_level=1.0,
            stake_fraction=stake_frac
        )
        
        # Calculate optimal Kelly
        optimal_kelly = self.calculate_optimal_kelly(win_rate)
        kelly_usage = (stake_frac / optimal_kelly * 100) if optimal_kelly > 0 else 0
        
        # Monte Carlo
        mc_results = {}
        if run_monte_carlo:
            mc_results = self.monte_carlo_simulation(
                n_simulations=500,
                n_bets=50
            )
        
        # Build metrics
        metrics = RiskMetrics(
            risk_of_ruin=ror,
            risk_of_ruin_50=ror_50,
            risk_of_ruin_100=ror_100,
            optimal_kelly=optimal_kelly,
            current_kelly_usage=kelly_usage,
            max_drawdown=state.drawdown_percent,
            monte_carlo_results=mc_results
        )
        
        return metrics
