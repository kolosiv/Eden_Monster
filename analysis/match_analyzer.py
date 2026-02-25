"""Match Analyzer Module for Eden MVP.

Comprehensive match analysis combining arbitrage, OT prediction, and risk assessment.
Now supports ML-based OT prediction with Poisson fallback.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union
from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field

from core.arbitrage_finder import ArbitrageOpportunity, ArbitrageType
from models.overtime_predictor import OTPrediction, TeamStats, OvertimePredictor
from utils.logger import get_logger

logger = get_logger(__name__)

# Try to import ML predictor
try:
    from models.overtime_predictor_ml import (
        OvertimePredictorML, MLTeamStats, MLOTPrediction
    )
    ML_PREDICTOR_AVAILABLE = True
except ImportError:
    ML_PREDICTOR_AVAILABLE = False
    logger.info("ML predictor not available, using Poisson model only")


class Recommendation(str, Enum):
    """Betting recommendation."""
    BET = "bet"
    SKIP = "skip"
    CAUTION = "caution"


class RiskLevel(str, Enum):
    """Risk level classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class MatchAnalysis(BaseModel):
    """Complete analysis result for a match.
    
    Attributes:
        match_id: Unique match identifier
        team_strong: Strong team name
        team_weak: Weak team name
        commence_time: Match start time
        arbitrage: Arbitrage opportunity details
        ot_prediction: Overtime prediction
        expected_value: Expected value per unit
        risk_level: Overall risk classification
        recommendation: Betting recommendation
        reasoning: Human-readable analysis
        stakes: Recommended stake amounts
    """
    match_id: str
    team_strong: str
    team_weak: str
    commence_time: Optional[str] = None
    
    # Arbitrage data
    odds_strong: float
    odds_weak_reg: float
    bookmaker_strong: str
    bookmaker_weak: str
    arb_roi: float
    arb_percentage: float
    
    # OT prediction
    ot_probability: float
    hole_probability: float
    ot_confidence: float
    
    # Analysis results
    expected_value: float
    risk_level: RiskLevel
    recommendation: Recommendation
    confidence_score: float = Field(ge=0, le=1)
    reasoning: List[str] = Field(default_factory=list)
    
    # Suggested stakes (populated by StakeCalculator)
    stake_strong: float = 0.0
    stake_weak: float = 0.0
    total_stake: float = 0.0
    potential_profit: float = 0.0


@dataclass 
class AnalyzerConfig:
    """Configuration for match analyzer."""
    max_hole_probability: float = 0.04  # 4%
    min_roi: float = 0.02  # 2%
    min_confidence: float = 0.5
    ev_threshold: float = 0.0  # Minimum expected value
    max_odds_difference: float = 0.5
    use_ml_predictor: bool = True  # Use ML model if available


class MatchAnalyzer:
    """Comprehensive match analysis engine.
    
    Combines:
    - Arbitrage opportunity detection
    - Overtime probability prediction
    - Risk assessment
    - Expected value calculation
    - Filtering logic
    - Recommendation generation
    
    Example:
        >>> analyzer = MatchAnalyzer(config)
        >>> analysis = analyzer.analyze(arbitrage_opp, team_stats)
        >>> if analysis.recommendation == Recommendation.BET:
        ...     print(f"Place bet! EV: {analysis.expected_value:.2%}")
    """
    
    def __init__(self, config: Optional[AnalyzerConfig] = None):
        """Initialize MatchAnalyzer.
        
        Args:
            config: Analyzer configuration
        """
        self.config = config or AnalyzerConfig()
        
        # Initialize OT predictor - prefer ML if available and configured
        self.ml_predictor = None
        self.using_ml = False
        
        if self.config.use_ml_predictor and ML_PREDICTOR_AVAILABLE:
            try:
                self.ml_predictor = OvertimePredictorML()
                if self.ml_predictor.is_loaded:
                    self.using_ml = True
                    logger.info("Using ML-based OT predictor")
                else:
                    logger.info("ML model not trained, using Poisson fallback")
            except Exception as e:
                logger.warning(f"Failed to load ML predictor: {e}")
        
        # Always have Poisson as fallback
        self.ot_predictor = OvertimePredictor()
        
    def calculate_expected_value(
        self,
        odds_strong: float,
        odds_weak: float,
        p_strong_match: float,
        p_weak_reg: float,
        p_loss_both: float
    ) -> float:
        """Calculate expected value per unit stake.
        
        EV = P(strong wins) * (profit from strong) 
           + P(weak wins reg) * (profit from weak)
           - P(loss both) * (total stake)
        
        For arbitrage distribution where total stake = 1:
        
        Args:
            odds_strong: Odds for strong team match win
            odds_weak: Odds for weak team regulation win
            p_strong_match: Probability strong team wins match
            p_weak_reg: Probability weak team wins in regulation
            p_loss_both: Probability both bets lose (hole)
            
        Returns:
            Expected value per unit stake
        """
        # Calculate stake distribution for equal payout
        inv_s = 1 / odds_strong
        inv_w = 1 / odds_weak
        total_inv = inv_s + inv_w
        
        stake_s = inv_s / total_inv
        stake_w = inv_w / total_inv
        
        # Payout equals stake * odds - total stake
        payout = stake_s * odds_strong  # = stake_w * odds_weak for arbitrage
        
        # Expected value
        ev = (
            p_strong_match * (payout - 1) +
            p_weak_reg * (payout - 1) -
            p_loss_both * 1.0
        )
        
        return ev
    
    def calculate_risk_adjusted_ev(
        self,
        ev: float,
        hole_probability: float,
        confidence: float
    ) -> float:
        """Calculate risk-adjusted expected value.
        
        Applies penalty for high hole probability and low confidence.
        
        Args:
            ev: Base expected value
            hole_probability: Hole probability
            confidence: Prediction confidence
            
        Returns:
            Risk-adjusted expected value
        """
        # Hole risk penalty
        hole_penalty = hole_probability * 2  # Double penalty for hole risk
        
        # Confidence adjustment
        confidence_factor = 0.5 + (confidence * 0.5)  # Range 0.5 to 1.0
        
        risk_adjusted_ev = (ev - hole_penalty) * confidence_factor
        return risk_adjusted_ev
    
    def assess_risk_level(
        self,
        hole_probability: float,
        ot_probability: float,
        confidence: float
    ) -> RiskLevel:
        """Assess overall risk level.
        
        Args:
            hole_probability: Probability of losing both bets
            ot_probability: Probability of overtime
            confidence: Prediction confidence
            
        Returns:
            Risk level classification
        """
        # Risk scoring
        risk_score = 0
        
        # Hole probability risk
        if hole_probability > 0.06:
            risk_score += 3
        elif hole_probability > 0.05:
            risk_score += 2
        elif hole_probability > 0.04:
            risk_score += 1
            
        # High OT probability increases risk
        if ot_probability > 0.28:
            risk_score += 2
        elif ot_probability > 0.25:
            risk_score += 1
            
        # Low confidence increases risk
        if confidence < 0.4:
            risk_score += 2
        elif confidence < 0.6:
            risk_score += 1
            
        # Classify risk level
        if risk_score >= 5:
            return RiskLevel.EXTREME
        elif risk_score >= 3:
            return RiskLevel.HIGH
        elif risk_score >= 1:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW
    
    def generate_recommendation(
        self,
        arb_roi: float,
        ev: float,
        hole_probability: float,
        risk_level: RiskLevel,
        confidence: float
    ) -> Tuple[Recommendation, List[str]]:
        """Generate betting recommendation with reasoning.
        
        Args:
            arb_roi: Arbitrage ROI
            ev: Expected value
            hole_probability: Hole probability
            risk_level: Risk level
            confidence: Prediction confidence
            
        Returns:
            Tuple of (recommendation, list of reasons)
        """
        reasons = []
        
        # Check minimum ROI
        if arb_roi < self.config.min_roi:
            reasons.append(f"❌ ROI ({arb_roi:.2%}) below minimum ({self.config.min_roi:.2%})")
        else:
            reasons.append(f"✅ ROI ({arb_roi:.2%}) meets threshold")
        
        # Check hole probability
        if hole_probability > self.config.max_hole_probability:
            reasons.append(
                f"❌ Hole probability ({hole_probability:.2%}) exceeds max "
                f"({self.config.max_hole_probability:.2%})"
            )
        else:
            reasons.append(f"✅ Hole probability ({hole_probability:.2%}) acceptable")
        
        # Check expected value
        if ev < self.config.ev_threshold:
            reasons.append(f"❌ Expected value ({ev:.4f}) is negative/low")
        else:
            reasons.append(f"✅ Positive expected value ({ev:.4f})")
        
        # Check confidence
        if confidence < self.config.min_confidence:
            reasons.append(f"⚠️ Low prediction confidence ({confidence:.2%})")
        
        # Check risk level
        if risk_level in [RiskLevel.HIGH, RiskLevel.EXTREME]:
            reasons.append(f"⚠️ {risk_level.value.upper()} risk level")
        
        # Make recommendation
        if (
            arb_roi >= self.config.min_roi and
            hole_probability <= self.config.max_hole_probability and
            ev >= self.config.ev_threshold and
            risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]
        ):
            return Recommendation.BET, reasons
        elif (
            arb_roi >= self.config.min_roi * 0.5 and
            hole_probability <= self.config.max_hole_probability * 1.25 and
            risk_level != RiskLevel.EXTREME
        ):
            return Recommendation.CAUTION, reasons
        else:
            return Recommendation.SKIP, reasons
    
    def analyze(
        self,
        arb_opportunity: ArbitrageOpportunity,
        strong_stats: Optional[TeamStats] = None,
        weak_stats: Optional[TeamStats] = None,
        ml_strong_stats: Optional['MLTeamStats'] = None,
        ml_weak_stats: Optional['MLTeamStats'] = None
    ) -> MatchAnalysis:
        """Perform comprehensive match analysis.
        
        Args:
            arb_opportunity: Detected arbitrage opportunity
            strong_stats: Optional Poisson model statistics for strong team
            weak_stats: Optional Poisson model statistics for weak team
            ml_strong_stats: Optional ML model statistics for strong team
            ml_weak_stats: Optional ML model statistics for weak team
            
        Returns:
            Complete MatchAnalysis object
        """
        logger.debug(f"Analyzing match: {arb_opportunity.match_id}")
        
        # Get OT prediction - prefer ML model if available
        ot_prediction = None
        
        if self.using_ml and self.ml_predictor:
            try:
                if ml_strong_stats and ml_weak_stats:
                    ml_pred = self.ml_predictor.predict(
                        ml_strong_stats, ml_weak_stats, 
                        arb_opportunity.match_id,
                        odds_strong=arb_opportunity.odds_strong,
                        odds_weak=arb_opportunity.odds_weak_reg
                    )
                else:
                    ml_pred = self.ml_predictor.predict_from_odds(
                        arb_opportunity.odds_strong,
                        arb_opportunity.odds_weak_reg,
                        arb_opportunity.match_id
                    )
                
                # Convert ML prediction to standard format
                ot_prediction = OTPrediction(
                    match_id=ml_pred.match_id,
                    ot_probability=ml_pred.ot_probability,
                    strong_ot_win_prob=ml_pred.strong_ot_win_prob,
                    weak_ot_win_prob=ml_pred.weak_ot_win_prob,
                    hole_probability=ml_pred.hole_probability,
                    confidence=ml_pred.confidence,
                    expected_score=ml_pred.expected_score,
                    reasoning=ml_pred.reasoning
                )
                logger.debug(f"Using ML prediction: hole={ml_pred.hole_probability:.2%}")
            except Exception as e:
                logger.warning(f"ML prediction failed, using fallback: {e}")
                ot_prediction = None
        
        # Fallback to Poisson model
        if ot_prediction is None:
            if strong_stats and weak_stats:
                ot_prediction = self.ot_predictor.predict(
                    strong_stats, weak_stats, arb_opportunity.match_id
                )
            else:
                # Use odds-based prediction if no stats available
                ot_prediction = self.ot_predictor.predict_from_odds(
                    arb_opportunity.odds_strong,
                    arb_opportunity.odds_weak_reg,
                    arb_opportunity.match_id
                )
        
        # Calculate probabilities with PROPER normalization
        # CRITICAL FIX: Removed magic 0.8 coefficient, probabilities now sum to 1
        #
        # Probability space:
        # 1. P(strong wins match) = P(strong wins reg) + P(OT) * P(strong wins OT)
        # 2. P(weak wins reg) = directly from OT prediction
        # 3. P(hole) = P(OT) * P(weak wins OT) = already in ot_prediction.hole_probability
        #
        p_ot = ot_prediction.ot_probability
        p_hole = ot_prediction.hole_probability  # P(OT) * P(weak wins OT)
        
        # Remove bookmaker vig from implied probabilities (use realistic 8% margin)
        BOOKMAKER_MARGIN = 1.08  # Realistic margin for NHL (was 1.05)
        implied_strong_raw = 1 / arb_opportunity.odds_strong
        implied_weak_raw = 1 / arb_opportunity.odds_weak_reg
        total_implied = implied_strong_raw + implied_weak_raw
        
        # Remove vig (normalize to true probabilities)
        p_strong_true = implied_strong_raw / total_implied
        p_weak_true = implied_weak_raw / total_implied
        
        # P(weak wins in regulation) - estimate from true probability minus OT contribution
        # True weak win probability includes both regulation wins and OT wins
        p_weak_reg = max(0.01, p_weak_true - p_hole)  # Regulation only
        
        # P(strong wins match) = all non-weak-win scenarios
        # Strong wins if: (1) strong wins in regulation, or (2) game goes to OT and strong wins OT
        p_strong_match = 1 - p_weak_reg - p_hole
        
        # Sanity check: probabilities must sum to 1
        total_prob = p_strong_match + p_weak_reg + p_hole
        if abs(total_prob - 1.0) > 0.01:
            logger.warning(f"Probability normalization issue: sum={total_prob:.4f}, normalizing...")
            # Normalize to ensure sum = 1
            p_strong_match = p_strong_match / total_prob
            p_weak_reg = p_weak_reg / total_prob
            p_hole = p_hole / total_prob
        
        # Store for debugging
        p_loss_both = p_hole
        
        # Calculate expected value
        ev = self.calculate_expected_value(
            arb_opportunity.odds_strong,
            arb_opportunity.odds_weak_reg,
            p_strong_match,
            p_weak_reg,
            p_loss_both
        )
        
        # Assess risk
        risk_level = self.assess_risk_level(
            ot_prediction.hole_probability,
            ot_prediction.ot_probability,
            ot_prediction.confidence
        )
        
        # Generate recommendation
        recommendation, reasoning = self.generate_recommendation(
            arb_opportunity.roi,
            ev,
            ot_prediction.hole_probability,
            risk_level,
            ot_prediction.confidence
        )
        
        # Calculate confidence score
        confidence_score = (
            ot_prediction.confidence * 0.5 +
            (1 - ot_prediction.hole_probability / 0.1) * 0.3 +
            min(arb_opportunity.roi / 0.05, 1.0) * 0.2
        )
        confidence_score = max(0, min(1, confidence_score))
        
        # Add OT prediction reasoning
        reasoning.append(ot_prediction.reasoning)
        
        analysis = MatchAnalysis(
            match_id=arb_opportunity.match_id,
            team_strong=arb_opportunity.team_home,  # Assumes home is strong for now
            team_weak=arb_opportunity.team_away,
            commence_time=arb_opportunity.commence_time,
            odds_strong=arb_opportunity.odds_strong,
            odds_weak_reg=arb_opportunity.odds_weak_reg,
            bookmaker_strong=arb_opportunity.bookmaker_strong,
            bookmaker_weak=arb_opportunity.bookmaker_weak,
            arb_roi=arb_opportunity.roi,
            arb_percentage=arb_opportunity.arb_percentage,
            ot_probability=ot_prediction.ot_probability,
            hole_probability=ot_prediction.hole_probability,
            ot_confidence=ot_prediction.confidence,
            expected_value=ev,
            risk_level=risk_level,
            recommendation=recommendation,
            confidence_score=confidence_score,
            reasoning=reasoning
        )
        
        logger.info(
            f"Analysis complete for {arb_opportunity.match_id}: "
            f"Recommendation={recommendation.value}, EV={ev:.4f}, "
            f"Risk={risk_level.value}"
        )
        
        return analysis
    
    def analyze_multiple(
        self,
        opportunities: List[ArbitrageOpportunity],
        team_stats: Optional[Dict[str, TeamStats]] = None
    ) -> List[MatchAnalysis]:
        """Analyze multiple arbitrage opportunities.
        
        Args:
            opportunities: List of arbitrage opportunities
            team_stats: Optional dict mapping team names to stats
            
        Returns:
            List of MatchAnalysis objects
        """
        analyses = []
        team_stats = team_stats or {}
        
        for opp in opportunities:
            strong_stats = team_stats.get(opp.team_home)
            weak_stats = team_stats.get(opp.team_away)
            
            try:
                analysis = self.analyze(opp, strong_stats, weak_stats)
                analyses.append(analysis)
            except Exception as e:
                logger.error(f"Error analyzing {opp.match_id}: {e}")
                continue
        
        return analyses
    
    def filter_recommendations(
        self,
        analyses: List[MatchAnalysis],
        recommendation: Optional[Recommendation] = None,
        max_risk: Optional[RiskLevel] = None
    ) -> List[MatchAnalysis]:
        """Filter analyses by criteria.
        
        Args:
            analyses: List of analyses to filter
            recommendation: Filter by recommendation type
            max_risk: Maximum acceptable risk level
            
        Returns:
            Filtered list of analyses
        """
        filtered = analyses
        
        if recommendation:
            filtered = [a for a in filtered if a.recommendation == recommendation]
            
        if max_risk:
            risk_order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.EXTREME]
            max_idx = risk_order.index(max_risk)
            filtered = [a for a in filtered if risk_order.index(a.risk_level) <= max_idx]
        
        return filtered
    
    def rank_opportunities(
        self,
        analyses: List[MatchAnalysis],
        sort_by: str = "ev"
    ) -> List[MatchAnalysis]:
        """Rank opportunities by specified metric.
        
        Args:
            analyses: List of analyses to rank
            sort_by: Metric to sort by (ev, roi, confidence, risk)
            
        Returns:
            Sorted list of analyses
        """
        if sort_by == "ev":
            return sorted(analyses, key=lambda x: x.expected_value, reverse=True)
        elif sort_by == "roi":
            return sorted(analyses, key=lambda x: x.arb_roi, reverse=True)
        elif sort_by == "confidence":
            return sorted(analyses, key=lambda x: x.confidence_score, reverse=True)
        elif sort_by == "risk":
            risk_order = {
                RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1,
                RiskLevel.HIGH: 2, RiskLevel.EXTREME: 3
            }
            return sorted(analyses, key=lambda x: risk_order[x.risk_level])
        return analyses
