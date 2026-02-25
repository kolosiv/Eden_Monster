"""ML-Based Overtime Predictor for Eden MVP.

Uses RandomForest classifier with 16+ features for improved OT prediction.
Target: Reduce hole probability from ~6% to 3-4%.
"""

import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import numpy as np
from pydantic import BaseModel, Field

from utils.logger import get_logger

logger = get_logger(__name__)

# Try importing sklearn, with fallback
try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available. ML predictor will use fallback.")


# NHL Historical Constants
NHL_AVG_OT_RATE = 0.23
NHL_FAVORITE_OT_WIN_RATE = 0.55
NHL_AVG_GOALS_PER_GAME = 2.7


class MLTeamStats(BaseModel):
    """Extended team statistics for ML prediction."""
    team_name: str
    
    # Basic stats
    goals_for_avg: float = Field(default=2.7, ge=0)
    goals_against_avg: float = Field(default=2.7, ge=0)
    win_rate: float = Field(default=0.5, ge=0, le=1)
    
    # OT performance
    ot_win_rate: float = Field(default=0.5, ge=0, le=1)
    ot_games_played: int = Field(default=5, ge=0)
    
    # Recent form (last 10 games)
    recent_form: float = Field(default=0.5, ge=0, le=1)
    goals_last_5: float = Field(default=2.7, ge=0)
    
    # Fatigue
    days_rest: int = Field(default=2, ge=1, le=10)
    games_last_7_days: int = Field(default=2, ge=0, le=7)
    
    # Home/Away splits
    home_win_rate: float = Field(default=0.55, ge=0, le=1)
    away_win_rate: float = Field(default=0.45, ge=0, le=1)
    
    # Special teams
    powerplay_pct: float = Field(default=0.2, ge=0, le=0.5)
    penalty_kill_pct: float = Field(default=0.8, ge=0.5, le=1.0)
    
    @property
    def special_teams_rating(self) -> float:
        """Combined special teams effectiveness."""
        return (self.powerplay_pct + self.penalty_kill_pct) / 2
    
    @property
    def goal_differential(self) -> float:
        """Goal differential per game."""
        return self.goals_for_avg - self.goals_against_avg


class MLOTPrediction(BaseModel):
    """ML-based overtime prediction result."""
    match_id: str = ""
    ot_probability: float = Field(ge=0, le=1)
    strong_ot_win_prob: float = Field(ge=0, le=1)
    weak_ot_win_prob: float = Field(ge=0, le=1)
    hole_probability: float = Field(ge=0, le=1)
    confidence: float = Field(default=0.5, ge=0, le=1)
    expected_score: Tuple[float, float] = (0.0, 0.0)
    reasoning: str = ""
    model_used: str = "ml_random_forest"
    feature_importance: Dict[str, float] = Field(default_factory=dict)


@dataclass
class MLPredictorConfig:
    """Configuration for ML OT predictor."""
    model_path: str = "models/overtime_model.pkl"
    scaler_path: str = "models/overtime_scaler.pkl"
    base_ot_rate: float = NHL_AVG_OT_RATE
    favorite_ot_advantage: float = NHL_FAVORITE_OT_WIN_RATE
    min_confidence: float = 0.6
    use_ensemble: bool = False


class OvertimePredictorML:
    """ML-based overtime predictor using RandomForest.
    
    Features (16+):
    1. home_gf_avg - Home team goals for average
    2. home_ga_avg - Home team goals against average
    3. away_gf_avg - Away team goals for average
    4. away_ga_avg - Away team goals against average
    5. goal_diff_home - Home team goal differential
    6. goal_diff_away - Away team goal differential
    7. home_win_rate - Home team overall win rate
    8. away_win_rate - Away team overall win rate
    9. win_rate_diff - Absolute difference in win rates
    10. home_ot_win_rate - Home team OT win rate
    11. away_ot_win_rate - Away team OT win rate
    12. home_form - Home team recent form (0-1)
    13. away_form - Away team recent form (0-1)
    14. form_diff - Difference in recent form
    15. home_rest_days - Home team days of rest
    16. away_rest_days - Away team days of rest
    17. home_back_to_back - Is home team on back-to-back?
    18. away_back_to_back - Is away team on back-to-back?
    19. h2h_ot_rate - Historical OT rate in H2H
    20. home_special_teams - Home team special teams rating
    21. away_special_teams - Away team special teams rating
    22. same_division - Are teams in same division?
    23. same_conference - Are teams in same conference?
    24. implied_closeness - How close the odds are (from betting markets)
    """
    
    FEATURE_NAMES = [
        "home_gf_avg", "home_ga_avg", "away_gf_avg", "away_ga_avg",
        "goal_diff_home", "goal_diff_away", "home_win_rate", "away_win_rate",
        "win_rate_diff", "home_ot_win_rate", "away_ot_win_rate",
        "home_form", "away_form", "form_diff",
        "home_rest_days", "away_rest_days", "home_back_to_back", "away_back_to_back",
        "h2h_ot_rate", "home_special_teams", "away_special_teams",
        "same_division", "same_conference", "implied_closeness"
    ]
    
    def __init__(self, config: Optional[MLPredictorConfig] = None):
        """Initialize ML OT predictor."""
        self.config = config or MLPredictorConfig()
        self.model = None
        self.scaler = None
        self.is_loaded = False
        
        # Try to load existing model
        self._load_model()
    
    def _load_model(self) -> bool:
        """Load trained model from disk."""
        if not SKLEARN_AVAILABLE:
            logger.warning("sklearn not available, cannot load model")
            return False
        
        model_path = Path(self.config.model_path)
        scaler_path = Path(self.config.scaler_path)
        
        if model_path.exists() and scaler_path.exists():
            try:
                with open(model_path, 'rb') as f:
                    self.model = pickle.load(f)
                with open(scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                self.is_loaded = True
                logger.info("ML model loaded successfully")
                return True
            except Exception as e:
                logger.error(f"Error loading model: {e}")
        else:
            logger.info("No trained model found. Use ModelTrainer to train.")
        
        return False
    
    def extract_features(
        self,
        strong_stats: MLTeamStats,
        weak_stats: MLTeamStats,
        is_strong_home: bool = True,
        h2h_ot_rate: float = 0.23,
        same_division: bool = False,
        same_conference: bool = True,
        implied_closeness: float = 0.5
    ) -> Dict[str, float]:
        """Extract features from team stats."""
        if is_strong_home:
            home_stats = strong_stats
            away_stats = weak_stats
        else:
            home_stats = weak_stats
            away_stats = strong_stats
        
        return {
            "home_gf_avg": home_stats.goals_for_avg,
            "home_ga_avg": home_stats.goals_against_avg,
            "away_gf_avg": away_stats.goals_for_avg,
            "away_ga_avg": away_stats.goals_against_avg,
            "goal_diff_home": home_stats.goal_differential,
            "goal_diff_away": away_stats.goal_differential,
            "home_win_rate": home_stats.win_rate,
            "away_win_rate": away_stats.win_rate,
            "win_rate_diff": abs(home_stats.win_rate - away_stats.win_rate),
            "home_ot_win_rate": home_stats.ot_win_rate,
            "away_ot_win_rate": away_stats.ot_win_rate,
            "home_form": home_stats.recent_form,
            "away_form": away_stats.recent_form,
            "form_diff": abs(home_stats.recent_form - away_stats.recent_form),
            "home_rest_days": home_stats.days_rest,
            "away_rest_days": away_stats.days_rest,
            "home_back_to_back": 1 if home_stats.days_rest == 1 else 0,
            "away_back_to_back": 1 if away_stats.days_rest == 1 else 0,
            "h2h_ot_rate": h2h_ot_rate,
            "home_special_teams": home_stats.special_teams_rating,
            "away_special_teams": away_stats.special_teams_rating,
            "same_division": 1 if same_division else 0,
            "same_conference": 1 if same_conference else 0,
            "implied_closeness": implied_closeness
        }
    
    def _features_to_array(self, features: Dict[str, float]) -> np.ndarray:
        """Convert feature dict to numpy array."""
        return np.array([[features[name] for name in self.FEATURE_NAMES]])
    
    def predict(
        self,
        strong_stats: MLTeamStats,
        weak_stats: MLTeamStats,
        match_id: str = "",
        is_strong_home: bool = True,
        h2h_ot_rate: float = 0.23,
        same_division: bool = False,
        same_conference: bool = True,
        odds_strong: float = None,
        odds_weak: float = None
    ) -> MLOTPrediction:
        """Predict overtime probability and outcomes.
        
        Args:
            strong_stats: Statistics for the strong/favorite team
            weak_stats: Statistics for the weak/underdog team
            match_id: Match identifier
            is_strong_home: Whether strong team is home
            h2h_ot_rate: Historical H2H OT rate
            same_division: Same division flag
            same_conference: Same conference flag
            odds_strong: Betting odds for strong team
            odds_weak: Betting odds for weak team
            
        Returns:
            MLOTPrediction with all probability estimates
        """
        # Calculate implied closeness from odds
        implied_closeness = 0.5
        if odds_strong and odds_weak:
            implied_strong = 1 / odds_strong
            implied_closeness = 1 - abs(implied_strong - 0.5) * 2
        
        # Extract features
        features = self.extract_features(
            strong_stats, weak_stats, is_strong_home,
            h2h_ot_rate, same_division, same_conference, implied_closeness
        )
        
        # Predict using ML model or fallback
        if self.is_loaded and SKLEARN_AVAILABLE:
            ot_probability, confidence = self._predict_ml(features)
            model_used = "ml_random_forest"
        else:
            ot_probability, confidence = self._predict_statistical(features)
            model_used = "statistical_fallback"
        
        # Calculate OT win probabilities
        strong_ot_win, weak_ot_win = self._calculate_ot_winners(
            strong_stats, weak_stats, features
        )
        
        # HOLE probability = P(OT) * P(weak wins OT)
        hole_probability = ot_probability * weak_ot_win
        
        # Expected score
        exp_strong = strong_stats.goals_for_avg * (1 + strong_stats.recent_form * 0.1)
        exp_weak = weak_stats.goals_for_avg * (1 - 0.05)  # Slight disadvantage
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            features, ot_probability, hole_probability, 
            strong_stats, weak_stats, model_used
        )
        
        # Get feature importance if model is loaded
        feature_importance = {}
        if self.is_loaded and hasattr(self.model, 'feature_importances_'):
            for name, imp in zip(self.FEATURE_NAMES, self.model.feature_importances_):
                feature_importance[name] = float(imp)
        
        logger.info(
            f"ML Prediction - OT: {ot_probability:.2%}, Hole: {hole_probability:.2%}, "
            f"Model: {model_used}"
        )
        
        return MLOTPrediction(
            match_id=match_id,
            ot_probability=ot_probability,
            strong_ot_win_prob=ot_probability * strong_ot_win,
            weak_ot_win_prob=ot_probability * weak_ot_win,
            hole_probability=hole_probability,
            confidence=confidence,
            expected_score=(exp_strong, exp_weak),
            reasoning=reasoning,
            model_used=model_used,
            feature_importance=feature_importance
        )
    
    def _predict_ml(self, features: Dict[str, float]) -> Tuple[float, float]:
        """Predict using ML model."""
        X = self._features_to_array(features)
        X_scaled = self.scaler.transform(X)
        
        # Get probability from RandomForest
        proba = self.model.predict_proba(X_scaled)[0]
        ot_probability = proba[1]  # Probability of class 1 (OT)
        
        # Confidence based on probability distance from 0.5
        # and model's internal metrics
        base_confidence = 2 * abs(ot_probability - 0.5)
        
        # Boost confidence if features are strong indicators
        if features["win_rate_diff"] < 0.1:  # Evenly matched
            base_confidence *= 1.1
        
        confidence = min(0.95, max(0.5, base_confidence))
        
        return ot_probability, confidence
    
    def _predict_statistical(self, features: Dict[str, float]) -> Tuple[float, float]:
        """Statistical fallback when ML model not available."""
        base_ot = self.config.base_ot_rate
        
        # Adjust based on key features
        modifier = 1.0
        
        # Evenly matched teams -> higher OT probability
        if features["win_rate_diff"] < 0.1:
            modifier *= 1.25
        elif features["win_rate_diff"] > 0.2:
            modifier *= 0.85
        
        # Division games tend to be closer
        if features["same_division"]:
            modifier *= 1.1
        
        # Back-to-back games (fatigue)
        if features["home_back_to_back"] or features["away_back_to_back"]:
            modifier *= 1.05
        
        # Close odds
        if features["implied_closeness"] > 0.7:
            modifier *= 1.15
        
        ot_probability = min(0.40, max(0.15, base_ot * modifier))
        confidence = 0.6  # Lower confidence for statistical method
        
        return ot_probability, confidence
    
    def _calculate_ot_winners(
        self,
        strong_stats: MLTeamStats,
        weak_stats: MLTeamStats,
        features: Dict[str, float]
    ) -> Tuple[float, float]:
        """Calculate OT win probabilities for each team.
        
        The strong team has historical advantage (~55%) in OT,
        but this is adjusted by:
        - Each team's OT win rate history
        - Recent form
        - Fatigue (back-to-back games)
        """
        # Base advantage for strong team
        base_strong = self.config.favorite_ot_advantage
        
        # Adjust for historical OT performance
        ot_history_adj = (strong_stats.ot_win_rate - weak_stats.ot_win_rate) * 0.2
        
        # Adjust for form
        form_adj = (strong_stats.recent_form - weak_stats.recent_form) * 0.1
        
        # Adjust for fatigue (tired team is disadvantaged in OT)
        fatigue_adj = 0
        if strong_stats.days_rest == 1 and weak_stats.days_rest > 1:
            fatigue_adj = -0.05  # Strong team tired
        elif weak_stats.days_rest == 1 and strong_stats.days_rest > 1:
            fatigue_adj = 0.05  # Weak team tired
        
        strong_ot_win = min(0.70, max(0.35, base_strong + ot_history_adj + form_adj + fatigue_adj))
        weak_ot_win = 1 - strong_ot_win
        
        return strong_ot_win, weak_ot_win
    
    def _generate_reasoning(
        self,
        features: Dict[str, float],
        ot_prob: float,
        hole_prob: float,
        strong: MLTeamStats,
        weak: MLTeamStats,
        model_used: str
    ) -> str:
        """Generate human-readable reasoning."""
        reasons = []
        
        # Model info
        reasons.append(f"[{model_used}]")
        
        # OT probability analysis
        if ot_prob > 0.28:
            reasons.append(f"HIGH OT risk ({ot_prob:.1%}) - closely matched teams")
        elif ot_prob < 0.20:
            reasons.append(f"LOW OT risk ({ot_prob:.1%}) - clear favorite")
        else:
            reasons.append(f"Average OT risk ({ot_prob:.1%})")
        
        # Hole risk
        if hole_prob > 0.05:
            reasons.append(f"⚠️ HIGH HOLE RISK: {hole_prob:.1%}")
        elif hole_prob > 0.04:
            reasons.append(f"⚡ MODERATE hole risk: {hole_prob:.1%}")
        else:
            reasons.append(f"✅ LOW hole risk: {hole_prob:.1%}")
        
        # Key factors
        if features["win_rate_diff"] < 0.08:
            reasons.append("Teams evenly matched")
        
        if features["same_division"]:
            reasons.append("Division rivalry (higher intensity)")
        
        if features["home_back_to_back"] or features["away_back_to_back"]:
            reasons.append("Fatigue factor (back-to-back)")
        
        if strong.recent_form > 0.65:
            reasons.append(f"Strong team in good form ({strong.recent_form:.0%})")
        
        if weak.ot_win_rate > 0.55:
            reasons.append(f"⚠️ Weak team good in OT ({weak.ot_win_rate:.0%})")
        
        return " | ".join(reasons)
    
    def predict_from_odds(
        self,
        odds_strong: float,
        odds_weak: float,
        match_id: str = ""
    ) -> MLOTPrediction:
        """Create prediction from odds alone when team stats unavailable."""
        # Derive implied probabilities
        implied_strong = 1 / odds_strong
        implied_weak = 1 / odds_weak
        total = implied_strong + implied_weak
        
        p_strong = implied_strong / total
        closeness = 1 - abs(p_strong - 0.5) * 2
        
        # Create synthetic stats from odds
        strong_stats = MLTeamStats(
            team_name="Strong",
            win_rate=p_strong,
            goals_for_avg=2.7 + (p_strong - 0.5),
            goals_against_avg=2.7 - (p_strong - 0.5) * 0.5,
            recent_form=0.5 + (p_strong - 0.5) * 0.3
        )
        weak_stats = MLTeamStats(
            team_name="Weak",
            win_rate=1 - p_strong,
            goals_for_avg=2.7 - (p_strong - 0.5) * 0.5,
            goals_against_avg=2.7 + (p_strong - 0.5),
            recent_form=0.5 - (p_strong - 0.5) * 0.2
        )
        
        prediction = self.predict(
            strong_stats, weak_stats, match_id,
            odds_strong=odds_strong, odds_weak=odds_weak
        )
        prediction.confidence = min(prediction.confidence, 0.6)  # Lower confidence
        prediction.reasoning = "[odds-only prediction] " + prediction.reasoning
        
        return prediction
    
    def is_safe_bet(self, prediction: MLOTPrediction, max_hole_prob: float = 0.04) -> bool:
        """Check if bet is safe based on hole probability."""
        return prediction.hole_probability <= max_hole_prob
