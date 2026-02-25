"""Overtime Predictor Module for Eden MVP.

Predicts overtime probability and outcomes for hockey matches.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
from enum import Enum

from pydantic import BaseModel, Field
import math

from utils.logger import get_logger

logger = get_logger(__name__)


# NHL Historical Constants
NHL_AVG_OT_RATE = 0.23  # ~23% of NHL games go to OT
NHL_AVG_GOALS_PER_GAME = 2.7  # Average goals per team
NHL_FAVORITE_OT_WIN_RATE = 0.55  # Favorites win ~55% of OT games


class TeamStats(BaseModel):
    """Team statistics for OT prediction.
    
    Attributes:
        goals_scored: Total goals scored
        goals_conceded: Total goals conceded
        games_played: Number of games played
        ot_wins: Overtime wins
        ot_losses: Overtime losses
        recent_form: Recent form rating (0-1)
        home_games: Number of home games
        away_games: Number of away games
    """
    team_name: str
    goals_scored: float = Field(ge=0)
    goals_conceded: float = Field(ge=0)
    games_played: int = Field(ge=1)
    ot_wins: int = Field(default=0, ge=0)
    ot_losses: int = Field(default=0, ge=0)
    recent_form: float = Field(default=0.5, ge=0, le=1)
    home_advantage: float = Field(default=0.0, ge=-0.2, le=0.2)
    
    @property
    def goals_per_game(self) -> float:
        """Calculate average goals scored per game."""
        return self.goals_scored / self.games_played
    
    @property
    def goals_against_per_game(self) -> float:
        """Calculate average goals against per game."""
        return self.goals_conceded / self.games_played
    
    @property
    def ot_win_rate(self) -> float:
        """Calculate OT win rate."""
        total_ot = self.ot_wins + self.ot_losses
        if total_ot == 0:
            return 0.5  # Default to 50% if no OT history
        return self.ot_wins / total_ot
    
    @property
    def attack_strength(self) -> float:
        """Calculate attack strength relative to league average."""
        return self.goals_per_game / NHL_AVG_GOALS_PER_GAME
    
    @property
    def defense_strength(self) -> float:
        """Calculate defense strength (lower is better)."""
        return self.goals_against_per_game / NHL_AVG_GOALS_PER_GAME


class OTPrediction(BaseModel):
    """Overtime prediction result.
    
    Attributes:
        match_id: Match identifier
        ot_probability: Probability of game going to OT
        strong_ot_win_prob: Probability strong team wins in OT
        weak_ot_win_prob: Probability weak team wins in OT (HOLE)
        hole_probability: Probability of losing both bets (weak wins OT)
        confidence: Prediction confidence (0-1)
        expected_score: Expected score tuple (strong, weak)
    """
    match_id: str = ""
    ot_probability: float = Field(ge=0, le=1)
    strong_ot_win_prob: float = Field(ge=0, le=1)
    weak_ot_win_prob: float = Field(ge=0, le=1)
    hole_probability: float = Field(ge=0, le=1)
    confidence: float = Field(default=0.5, ge=0, le=1)
    expected_score: Tuple[float, float] = (0.0, 0.0)
    reasoning: str = ""


@dataclass
class OTPredictorConfig:
    """Configuration for OT predictor."""
    base_ot_rate: float = NHL_AVG_OT_RATE
    favorite_ot_advantage: float = NHL_FAVORITE_OT_WIN_RATE
    confidence_threshold: float = 0.7
    league_avg_goals: float = NHL_AVG_GOALS_PER_GAME
    max_goals_matrix: int = 7  # For Poisson calculation


class OvertimePredictor:
    """Predicts overtime probability and outcomes.
    
    Uses a statistical model based on:
    - Team goal-scoring patterns (Poisson distribution)
    - Historical OT performance
    - Recent form adjustments
    - Home/away factors
    
    The key output is the "hole" probability - the chance that
    the underdog wins in OT, causing both bets to lose.
    
    Target: Reduce hole probability from ~6% to 3-4%
    
    Example:
        >>> predictor = OvertimePredictor()
        >>> strong = TeamStats(team_name="Team A", goals_scored=100, ...)
        >>> weak = TeamStats(team_name="Team B", goals_scored=80, ...)
        >>> prediction = predictor.predict(strong, weak)
        >>> print(f"Hole probability: {prediction.hole_probability:.2%}")
    """
    
    def __init__(self, config: Optional[OTPredictorConfig] = None):
        """Initialize OvertimePredictor.
        
        Args:
            config: Predictor configuration
        """
        self.config = config or OTPredictorConfig()
        
    def _poisson_probability(self, k: int, lambda_: float) -> float:
        """Calculate Poisson probability P(X=k) = (λ^k * e^-λ) / k!
        
        Args:
            k: Number of events (goals)
            lambda_: Expected number of events
            
        Returns:
            Probability of exactly k events
        """
        if lambda_ <= 0:
            return 1.0 if k == 0 else 0.0
        return (math.pow(lambda_, k) * math.exp(-lambda_)) / math.factorial(k)
    
    def _calculate_expected_goals(
        self,
        team_attack: float,
        opponent_defense: float
    ) -> float:
        """Calculate expected goals for a team.
        
        Expected Goals = Attack Strength × Opponent Defense × League Average
        
        Args:
            team_attack: Team's attack strength
            opponent_defense: Opponent's defense strength
            
        Returns:
            Expected goals for the team
        """
        return team_attack * opponent_defense * self.config.league_avg_goals
    
    def _calculate_draw_probability(
        self,
        exp_goals_strong: float,
        exp_goals_weak: float
    ) -> float:
        """Calculate probability of draw in regulation using Poisson.
        
        P(draw) = Σ P(strong scores i) × P(weak scores i) for i = 0 to max
        
        Args:
            exp_goals_strong: Expected goals for strong team
            exp_goals_weak: Expected goals for weak team
            
        Returns:
            Probability of draw in regulation
        """
        draw_prob = 0.0
        max_goals = self.config.max_goals_matrix
        
        for i in range(max_goals + 1):
            p_strong_i = self._poisson_probability(i, exp_goals_strong)
            p_weak_i = self._poisson_probability(i, exp_goals_weak)
            draw_prob += p_strong_i * p_weak_i
            
        return draw_prob
    
    def _calculate_regulation_probs(
        self,
        exp_goals_strong: float,
        exp_goals_weak: float
    ) -> Dict[str, float]:
        """Calculate regulation time outcome probabilities.
        
        Args:
            exp_goals_strong: Expected goals for strong team
            exp_goals_weak: Expected goals for weak team
            
        Returns:
            Dict with probabilities for strong_win, weak_win, draw
        """
        max_goals = self.config.max_goals_matrix
        
        p_strong_win = 0.0
        p_weak_win = 0.0
        p_draw = 0.0
        
        for i in range(max_goals + 1):
            p_strong_i = self._poisson_probability(i, exp_goals_strong)
            for j in range(max_goals + 1):
                p_weak_j = self._poisson_probability(j, exp_goals_weak)
                joint_prob = p_strong_i * p_weak_j
                
                if i > j:
                    p_strong_win += joint_prob
                elif i < j:
                    p_weak_win += joint_prob
                else:
                    p_draw += joint_prob
        
        # Normalize to account for truncation
        total = p_strong_win + p_weak_win + p_draw
        if total > 0:
            return {
                "strong_win": p_strong_win / total,
                "weak_win": p_weak_win / total,
                "draw": p_draw / total
            }
        return {"strong_win": 0.33, "weak_win": 0.33, "draw": 0.34}
    
    def _calculate_ot_win_probability(
        self,
        strong_stats: TeamStats,
        weak_stats: TeamStats
    ) -> Tuple[float, float]:
        """Calculate OT win probabilities for each team.
        
        Based on:
        - Historical OT win rates
        - Team form
        - Skill differential
        
        Args:
            strong_stats: Strong team statistics
            weak_stats: Weak team statistics
            
        Returns:
            Tuple of (strong_ot_win_prob, weak_ot_win_prob)
        """
        # Base OT win rates from history
        strong_ot_base = strong_stats.ot_win_rate
        weak_ot_base = weak_stats.ot_win_rate
        
        # Adjust for skill differential
        skill_diff = (strong_stats.attack_strength - weak_stats.attack_strength)
        skill_adjustment = skill_diff * 0.1  # 10% per unit of skill difference
        
        # Adjust for recent form
        form_diff = strong_stats.recent_form - weak_stats.recent_form
        form_adjustment = form_diff * 0.05  # 5% per unit of form difference
        
        # Calculate adjusted probabilities
        strong_ot_prob = min(0.95, max(0.05, 
            self.config.favorite_ot_advantage + skill_adjustment + form_adjustment
        ))
        weak_ot_prob = 1 - strong_ot_prob
        
        return strong_ot_prob, weak_ot_prob
    
    def _calculate_confidence(
        self,
        strong_stats: TeamStats,
        weak_stats: TeamStats,
        draw_prob: float
    ) -> float:
        """Calculate prediction confidence.
        
        Based on:
        - Sample size (games played)
        - Consistency of predictions
        - How close draw probability is to average
        
        Args:
            strong_stats: Strong team statistics
            weak_stats: Weak team statistics
            draw_prob: Calculated draw probability
            
        Returns:
            Confidence score (0-1)
        """
        # Sample size factor
        min_games = min(strong_stats.games_played, weak_stats.games_played)
        sample_factor = min(1.0, min_games / 20)  # Full confidence at 20+ games
        
        # OT history factor
        total_ot = (strong_stats.ot_wins + strong_stats.ot_losses + 
                    weak_stats.ot_wins + weak_stats.ot_losses)
        ot_history_factor = min(1.0, total_ot / 10)  # Full confidence at 10+ OT games
        
        # Draw probability reasonableness factor
        draw_diff = abs(draw_prob - self.config.base_ot_rate)
        draw_factor = max(0.5, 1 - draw_diff * 2)
        
        # Weighted average
        confidence = (sample_factor * 0.4 + ot_history_factor * 0.3 + draw_factor * 0.3)
        return confidence
    
    def predict(
        self,
        strong_stats: TeamStats,
        weak_stats: TeamStats,
        match_id: str = ""
    ) -> OTPrediction:
        """Predict overtime probability and outcomes.
        
        Args:
            strong_stats: Statistics for the strong team (favorite)
            weak_stats: Statistics for the weak team (underdog)
            match_id: Optional match identifier
            
        Returns:
            OTPrediction with all probability estimates
        """
        logger.debug(f"Predicting OT for match: {match_id}")
        
        # Calculate expected goals
        exp_goals_strong = self._calculate_expected_goals(
            strong_stats.attack_strength,
            weak_stats.defense_strength
        )
        exp_goals_weak = self._calculate_expected_goals(
            weak_stats.attack_strength,
            strong_stats.defense_strength
        )
        
        # Calculate regulation probabilities
        reg_probs = self._calculate_regulation_probs(exp_goals_strong, exp_goals_weak)
        ot_probability = reg_probs["draw"]
        
        # Calculate OT win probabilities
        strong_ot_win, weak_ot_win = self._calculate_ot_win_probability(
            strong_stats, weak_stats
        )
        
        # Calculate HOLE probability (weak team wins in OT = both bets lose)
        hole_probability = ot_probability * weak_ot_win
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            strong_stats, weak_stats, ot_probability
        )
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            strong_stats, weak_stats,
            ot_probability, hole_probability, confidence
        )
        
        logger.info(
            f"OT Prediction - OT Prob: {ot_probability:.2%}, "
            f"Hole Prob: {hole_probability:.2%}, Confidence: {confidence:.2%}"
        )
        
        return OTPrediction(
            match_id=match_id,
            ot_probability=ot_probability,
            strong_ot_win_prob=ot_probability * strong_ot_win,
            weak_ot_win_prob=hole_probability,
            hole_probability=hole_probability,
            confidence=confidence,
            expected_score=(exp_goals_strong, exp_goals_weak),
            reasoning=reasoning
        )
    
    def _generate_reasoning(
        self,
        strong: TeamStats,
        weak: TeamStats,
        ot_prob: float,
        hole_prob: float,
        confidence: float
    ) -> str:
        """Generate human-readable reasoning for prediction.
        
        Args:
            strong: Strong team stats
            weak: Weak team stats
            ot_prob: OT probability
            hole_prob: Hole probability
            confidence: Confidence score
            
        Returns:
            Reasoning string
        """
        reasons = []
        
        # OT probability analysis
        if ot_prob > 0.25:
            reasons.append(f"High OT probability ({ot_prob:.1%}) - teams are closely matched")
        elif ot_prob < 0.20:
            reasons.append(f"Low OT probability ({ot_prob:.1%}) - clear favorite expected")
        else:
            reasons.append(f"Average OT probability ({ot_prob:.1%})")
        
        # Hole risk analysis
        if hole_prob > 0.05:
            reasons.append(f"⚠️ HIGH RISK: Hole probability ({hole_prob:.1%}) exceeds 5%")
        elif hole_prob > 0.04:
            reasons.append(f"⚡ MODERATE RISK: Hole probability at {hole_prob:.1%}")
        else:
            reasons.append(f"✅ LOW RISK: Hole probability ({hole_prob:.1%}) is acceptable")
        
        # Form analysis
        form_diff = strong.recent_form - weak.recent_form
        if form_diff > 0.2:
            reasons.append("Strong team in better recent form")
        elif form_diff < -0.1:
            reasons.append("⚠️ Weak team in better recent form")
        
        # OT history
        if strong.ot_win_rate > 0.6:
            reasons.append(f"Strong team good in OT ({strong.ot_win_rate:.0%} win rate)")
        if weak.ot_win_rate > 0.5:
            reasons.append(f"⚠️ Weak team decent in OT ({weak.ot_win_rate:.0%} win rate)")
        
        return " | ".join(reasons)
    
    def is_safe_bet(
        self,
        prediction: OTPrediction,
        max_hole_prob: float = 0.04
    ) -> bool:
        """Check if a bet is safe based on hole probability.
        
        Args:
            prediction: OT prediction
            max_hole_prob: Maximum acceptable hole probability
            
        Returns:
            True if bet is considered safe
        """
        return prediction.hole_probability <= max_hole_prob
    
    def predict_from_odds(
        self,
        odds_strong: float,
        odds_weak: float,
        match_id: str = ""
    ) -> OTPrediction:
        """Create a basic prediction from odds alone.
        
        Uses implied probabilities when team stats aren't available.
        
        Args:
            odds_strong: Odds for strong team
            odds_weak: Odds for weak team
            match_id: Match identifier
            
        Returns:
            OTPrediction based on odds analysis
        """
        # Derive implied probabilities
        implied_strong = 1 / odds_strong
        implied_weak = 1 / odds_weak
        total = implied_strong + implied_weak
        
        # Remove vig
        p_strong = implied_strong / total
        p_weak = implied_weak / total
        
        # Estimate draw probability based on how close the teams are
        closeness = 1 - abs(p_strong - p_weak)
        ot_probability = self.config.base_ot_rate * (0.5 + closeness * 0.5)
        
        # Estimate OT win rates based on match strength
        strong_ot_win = self.config.favorite_ot_advantage * (1 + (p_strong - 0.5) * 0.2)
        weak_ot_win = 1 - strong_ot_win
        
        hole_probability = ot_probability * weak_ot_win
        
        return OTPrediction(
            match_id=match_id,
            ot_probability=ot_probability,
            strong_ot_win_prob=ot_probability * strong_ot_win,
            weak_ot_win_prob=hole_probability,
            hole_probability=hole_probability,
            confidence=0.5,  # Lower confidence without stats
            expected_score=(0, 0),
            reasoning=f"Prediction from odds only - Limited confidence"
        )
