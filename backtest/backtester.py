"""Backtesting Engine for Eden MVP.

Tests betting strategy on historical data.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import math

from pydantic import BaseModel, Field

from backtest.historical_odds import HistoricalOddsProvider, HistoricalOdds
from models.overtime_predictor_ml import OvertimePredictorML, MLTeamStats
from models.overtime_predictor import OvertimePredictor
from analysis.stake_calculator import StakeCalculator, StakeConfig, StakingStrategy
from utils.logger import get_logger

logger = get_logger(__name__)


class BetOutcome(str, Enum):
    """Outcome of a bet."""
    WIN_STRONG = "win_strong"  # Strong team won match
    WIN_WEAK_REG = "win_weak_reg"  # Weak team won in regulation
    HOLE = "hole"  # Weak team won in OT (both bets lose)
    SKIPPED = "skipped"


class BacktestBet(BaseModel):
    """Single bet in backtest."""
    match_id: str
    date: str
    home_team: str
    away_team: str
    
    # Arbitrage info
    arb_roi: float
    predicted_hole_prob: float
    predicted_ot_prob: float
    confidence: float
    
    # Stakes
    stake_strong: float
    stake_weak: float
    total_stake: float
    
    # Result
    outcome: BetOutcome
    profit_loss: float
    bankroll_after: float
    
    # Match result
    actual_ot: bool
    actual_hole: bool  # Weak team won in OT


class BacktestResult(BaseModel):
    """Complete backtest result."""
    # Config
    start_date: str
    end_date: str
    initial_bankroll: float
    num_matches: int
    strategy: str
    max_hole_threshold: float
    
    # Results
    total_bets: int
    won: int
    lost: int
    holes: int
    skipped: int
    
    # Financial
    final_bankroll: float
    total_profit_loss: float
    total_staked: float
    roi_percentage: float
    
    # Risk metrics
    win_rate: float
    hole_rate: float
    actual_hole_rate: float  # In entire dataset
    predicted_hole_accuracy: float
    
    # Advanced metrics
    sharpe_ratio: Optional[float] = None
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    avg_profit_per_bet: float = 0.0
    best_day: float = 0.0
    worst_day: float = 0.0
    
    # Equity curve
    equity_curve: List[Tuple[str, float]] = Field(default_factory=list)
    monthly_returns: Dict[str, float] = Field(default_factory=dict)
    
    # Individual bets
    bets: List[BacktestBet] = Field(default_factory=list)


@dataclass
class BacktestConfig:
    """Configuration for backtesting."""
    initial_bankroll: float = 1000.0
    max_hole_probability: float = 0.04  # 4%
    min_roi: float = 0.02  # 2%
    min_confidence: float = 0.5
    staking_strategy: StakingStrategy = StakingStrategy.ADAPTIVE
    use_ml_predictor: bool = True
    num_matches: int = 200
    risk_free_rate: float = 0.04  # For Sharpe ratio calculation


class Backtester:
    """Backtesting engine for Eden MVP strategy."""
    
    def __init__(self, config: Optional[BacktestConfig] = None):
        """Initialize backtester."""
        self.config = config or BacktestConfig()
        
        # Initialize components
        self.odds_provider = HistoricalOddsProvider()
        
        # Use ML predictor if available
        if self.config.use_ml_predictor:
            try:
                self.predictor = OvertimePredictorML()
                logger.info("Using ML-based OT predictor")
            except Exception as e:
                logger.warning(f"ML predictor failed: {e}, using Poisson")
                self.predictor = OvertimePredictor()
        else:
            self.predictor = OvertimePredictor()
        
        # Stake calculator
        self.stake_calc = StakeCalculator(
            config=StakeConfig(
                bankroll=self.config.initial_bankroll,
                default_stake_percent=0.04,
                max_stake_percent=0.10
            )
        )
    
    def run(
        self,
        matches: List[HistoricalOdds] = None,
        verbose: bool = True
    ) -> BacktestResult:
        """Run backtest on historical data.
        
        Args:
            matches: Historical matches to test on (or generate if None)
            verbose: Print progress
            
        Returns:
            BacktestResult with all metrics
        """
        logger.info("="*50)
        logger.info("STARTING BACKTEST")
        logger.info("="*50)
        
        # Get historical data
        if matches is None:
            matches = self.odds_provider.generate_historical_odds(
                num_matches=self.config.num_matches,
                arb_rate=0.08  # ~8% arb opportunities
            )
        
        # Filter to arbitrage matches only
        arb_matches = [m for m in matches if m.has_arbitrage]
        
        if not arb_matches:
            logger.warning("No arbitrage opportunities found in data")
            return self._empty_result()
        
        logger.info(f"Found {len(arb_matches)} arbitrage opportunities in {len(matches)} matches")
        
        # Initialize tracking
        bankroll = self.config.initial_bankroll
        bets = []
        equity_curve = [(matches[0].date, bankroll)]
        
        total_staked = 0
        holes = 0
        wins = 0
        losses = 0
        skipped = 0
        
        daily_pnl = {}
        peak_bankroll = bankroll
        max_drawdown = 0
        
        # Process each arbitrage opportunity
        for match in arb_matches:
            # Create prediction
            if hasattr(self.predictor, 'predict_from_odds'):
                prediction = self.predictor.predict_from_odds(
                    match.home_h2h_odds,
                    match.away_h2h_odds,
                    match.match_id
                )
            else:
                prediction = self.predictor.predict_from_odds(
                    match.home_h2h_odds,
                    match.away_h2h_odds,
                    match.match_id
                )
            
            # Check if bet meets criteria
            if prediction.hole_probability > self.config.max_hole_probability:
                skipped += 1
                continue
            
            if match.arb_roi < self.config.min_roi * 100:  # Convert to percentage
                skipped += 1
                continue
            
            if prediction.confidence < self.config.min_confidence:
                skipped += 1
                continue
            
            # Calculate stakes
            stake_pct = self._calculate_stake_percentage(
                match.arb_roi,
                prediction.hole_probability,
                prediction.confidence
            )
            total_stake = bankroll * stake_pct
            total_stake = min(total_stake, bankroll * 0.10)  # Max 10%
            
            # Distribute stakes for equal payout
            inv_strong = 1 / match.home_h2h_odds
            inv_weak = 1 / match.away_h2h_odds
            total_inv = inv_strong + inv_weak
            
            stake_strong = total_stake * (inv_strong / total_inv)
            stake_weak = total_stake * (inv_weak / total_inv)
            
            # Determine outcome
            outcome, profit = self._determine_outcome(
                match, stake_strong, stake_weak, total_stake
            )
            
            actual_hole = match.went_to_ot and match.ot_winner == "away"
            
            if outcome == BetOutcome.HOLE:
                holes += 1
                losses += 1
            elif outcome in [BetOutcome.WIN_STRONG, BetOutcome.WIN_WEAK_REG]:
                wins += 1
            
            # Update bankroll
            bankroll += profit
            total_staked += total_stake
            
            # Track equity
            equity_curve.append((match.date, bankroll))
            
            # Daily P/L
            if match.date not in daily_pnl:
                daily_pnl[match.date] = 0
            daily_pnl[match.date] += profit
            
            # Drawdown
            if bankroll > peak_bankroll:
                peak_bankroll = bankroll
            drawdown = peak_bankroll - bankroll
            if drawdown > max_drawdown:
                max_drawdown = drawdown
            
            # Record bet
            bet = BacktestBet(
                match_id=match.match_id,
                date=match.date,
                home_team=match.home_team,
                away_team=match.away_team,
                arb_roi=match.arb_roi,
                predicted_hole_prob=prediction.hole_probability,
                predicted_ot_prob=prediction.ot_probability,
                confidence=prediction.confidence,
                stake_strong=stake_strong,
                stake_weak=stake_weak,
                total_stake=total_stake,
                outcome=outcome,
                profit_loss=profit,
                bankroll_after=bankroll,
                actual_ot=match.went_to_ot,
                actual_hole=actual_hole
            )
            bets.append(bet)
            
            if verbose and len(bets) % 20 == 0:
                logger.info(f"Processed {len(bets)} bets, Bankroll: ${bankroll:.2f}")
        
        # Calculate final metrics
        total_bets = len(bets)
        total_pnl = bankroll - self.config.initial_bankroll
        roi = (total_pnl / self.config.initial_bankroll) * 100 if self.config.initial_bankroll > 0 else 0
        
        # Win rate
        win_rate = (wins / total_bets * 100) if total_bets > 0 else 0
        
        # Hole rate (among bets made)
        hole_rate = (holes / total_bets * 100) if total_bets > 0 else 0
        
        # Actual hole rate in entire dataset
        actual_holes_dataset = sum(1 for m in matches if m.went_to_ot and m.ot_winner == "away")
        actual_hole_rate = (actual_holes_dataset / len(matches) * 100) if matches else 0
        
        # Prediction accuracy
        correctly_predicted = sum(
            1 for b in bets 
            if (b.predicted_hole_prob <= 0.04 and not b.actual_hole) or
               (b.predicted_hole_prob > 0.04 and b.actual_hole)
        )
        pred_accuracy = (correctly_predicted / total_bets * 100) if total_bets > 0 else 0
        
        # Monthly returns
        monthly = {}
        for bet in bets:
            month = bet.date[:7]  # YYYY-MM
            if month not in monthly:
                monthly[month] = 0
            monthly[month] += bet.profit_loss
        
        # Sharpe ratio (annualized)
        if bets:
            returns = [b.profit_loss / b.total_stake for b in bets]
            avg_return = sum(returns) / len(returns)
            std_return = math.sqrt(sum((r - avg_return)**2 for r in returns) / len(returns))
            if std_return > 0:
                # Annualize (assume ~100 bets/year)
                sharpe = (avg_return - self.config.risk_free_rate / 100) / std_return * math.sqrt(100)
            else:
                sharpe = 0
        else:
            sharpe = 0
        
        result = BacktestResult(
            start_date=matches[0].date if matches else "",
            end_date=matches[-1].date if matches else "",
            initial_bankroll=self.config.initial_bankroll,
            num_matches=len(matches),
            strategy=self.config.staking_strategy.value,
            max_hole_threshold=self.config.max_hole_probability,
            total_bets=total_bets,
            won=wins,
            lost=losses,
            holes=holes,
            skipped=skipped,
            final_bankroll=bankroll,
            total_profit_loss=total_pnl,
            total_staked=total_staked,
            roi_percentage=roi,
            win_rate=win_rate,
            hole_rate=hole_rate,
            actual_hole_rate=actual_hole_rate,
            predicted_hole_accuracy=pred_accuracy,
            sharpe_ratio=sharpe,
            max_drawdown=max_drawdown,
            max_drawdown_pct=(max_drawdown / self.config.initial_bankroll * 100) if self.config.initial_bankroll > 0 else 0,
            avg_profit_per_bet=(total_pnl / total_bets) if total_bets > 0 else 0,
            best_day=max(daily_pnl.values()) if daily_pnl else 0,
            worst_day=min(daily_pnl.values()) if daily_pnl else 0,
            equity_curve=equity_curve,
            monthly_returns=monthly,
            bets=bets
        )
        
        self._print_summary(result)
        
        return result
    
    def _calculate_stake_percentage(
        self,
        arb_roi: float,
        hole_prob: float,
        confidence: float
    ) -> float:
        """Calculate stake percentage based on opportunity."""
        # Base stake
        base = 0.04  # 4%
        
        # Adjust for ROI (higher ROI = more stake)
        roi_factor = min(1.5, arb_roi / 2)  # Max 50% boost
        
        # Adjust for hole risk (lower hole = more stake)
        hole_factor = 1.5 - (hole_prob / self.config.max_hole_probability)
        
        # Adjust for confidence
        conf_factor = 0.5 + confidence * 0.5
        
        stake = base * roi_factor * hole_factor * conf_factor
        return max(0.02, min(0.10, stake))
    
    def _determine_outcome(
        self,
        match: HistoricalOdds,
        stake_strong: float,
        stake_weak: float,
        total_stake: float
    ) -> Tuple[BetOutcome, float]:
        """Determine outcome and profit/loss."""
        if match.went_to_ot:
            if match.ot_winner == "away":
                # HOLE - weak team won in OT, both bets lose
                return BetOutcome.HOLE, -total_stake
            else:
                # Strong team won in OT (wins "match winner" bet)
                payout = stake_strong * match.home_h2h_odds
                profit = payout - total_stake
                return BetOutcome.WIN_STRONG, profit
        else:
            # Regulation result
            if match.home_goals > match.away_goals:
                # Home (strong) won in regulation
                payout = stake_strong * match.home_h2h_odds
                profit = payout - total_stake
                return BetOutcome.WIN_STRONG, profit
            else:
                # Away (weak) won in regulation
                payout = stake_weak * match.away_h2h_odds
                profit = payout - total_stake
                return BetOutcome.WIN_WEAK_REG, profit
    
    def _empty_result(self) -> BacktestResult:
        """Return empty result when no data."""
        return BacktestResult(
            start_date="",
            end_date="",
            initial_bankroll=self.config.initial_bankroll,
            num_matches=0,
            strategy=self.config.staking_strategy.value,
            max_hole_threshold=self.config.max_hole_probability,
            total_bets=0,
            won=0,
            lost=0,
            holes=0,
            skipped=0,
            final_bankroll=self.config.initial_bankroll,
            total_profit_loss=0,
            total_staked=0,
            roi_percentage=0,
            win_rate=0,
            hole_rate=0,
            actual_hole_rate=0,
            predicted_hole_accuracy=0
        )
    
    def _print_summary(self, result: BacktestResult) -> None:
        """Print backtest summary."""
        logger.info("="*50)
        logger.info("BACKTEST RESULTS")
        logger.info("="*50)
        logger.info(f"Period: {result.start_date} to {result.end_date}")
        logger.info(f"Matches analyzed: {result.num_matches}")
        logger.info(f"Bets placed: {result.total_bets} (Skipped: {result.skipped})")
        logger.info(f"")
        logger.info(f"Win/Loss: {result.won}W / {result.lost}L")
        logger.info(f"Win Rate: {result.win_rate:.1f}%")
        logger.info(f"Holes: {result.holes} ({result.hole_rate:.1f}%)")
        logger.info(f"")
        logger.info(f"Initial Bankroll: ${result.initial_bankroll:.2f}")
        logger.info(f"Final Bankroll: ${result.final_bankroll:.2f}")
        logger.info(f"Total P/L: ${result.total_profit_loss:+.2f}")
        logger.info(f"ROI: {result.roi_percentage:+.2f}%")
        logger.info(f"")
        logger.info(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
        logger.info(f"Max Drawdown: ${result.max_drawdown:.2f} ({result.max_drawdown_pct:.1f}%)")
        logger.info(f"Avg Profit/Bet: ${result.avg_profit_per_bet:.2f}")
        logger.info("="*50)


def run_backtest(
    num_matches: int = 200,
    max_hole: float = 0.04,
    use_ml: bool = True
) -> BacktestResult:
    """Convenience function to run backtest."""
    config = BacktestConfig(
        num_matches=num_matches,
        max_hole_probability=max_hole,
        use_ml_predictor=use_ml
    )
    backtester = Backtester(config)
    return backtester.run()


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    result = run_backtest(300)
