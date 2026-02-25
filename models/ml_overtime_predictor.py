"""Enhanced ML Overtime Predictor.

New predictor class using ensemble model with fallback to Poisson.
"""

import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

import numpy as np
from pydantic import BaseModel, Field

from utils.logger import get_logger
from models.overtime_predictor import OvertimePredictor, OTPrediction, TeamStats

logger = get_logger(__name__)

# Try importing ML dependencies
try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# Model paths
MODEL_DIR = Path("models")
ENSEMBLE_MODEL_PATH = MODEL_DIR / "saved" / "ensemble_model.pkl"
DEFAULT_MODEL_PATH = MODEL_DIR / "overtime_model.pkl"
DEFAULT_SCALER_PATH = MODEL_DIR / "overtime_scaler.pkl"


class MLPredictionResult(BaseModel):
    """Enhanced ML prediction result."""
    match_id: str = ""
    ot_probability: float = Field(ge=0, le=1)
    strong_ot_win_prob: float = Field(ge=0, le=1)
    weak_ot_win_prob: float = Field(ge=0, le=1)
    hole_probability: float = Field(ge=0, le=1)
    confidence: float = Field(default=0.5, ge=0, le=1)
    expected_score: Tuple[float, float] = (0.0, 0.0)
    reasoning: str = ""
    
    # ML specific
    model_used: str = "ensemble"
    model_version: str = ""
    feature_importance: Dict[str, float] = Field(default_factory=dict)
    prediction_variance: float = 0.0  # Uncertainty from ensemble
    
    # Fallback info
    used_fallback: bool = False
    fallback_reason: str = ""


@dataclass
class MLPredictorConfig:
    """Configuration for ML overtime predictor."""
    # Model paths
    model_path: str = str(DEFAULT_MODEL_PATH)
    scaler_path: str = str(DEFAULT_SCALER_PATH)
    ensemble_path: str = str(ENSEMBLE_MODEL_PATH)
    
    # Prediction settings
    use_ensemble: bool = True
    fallback_to_poisson: bool = True
    min_confidence_threshold: float = 0.5
    
    # OT parameters
    base_ot_rate: float = 0.23
    favorite_ot_advantage: float = 0.55


class EnhancedMLPredictor:
    """Enhanced ML Overtime Predictor with ensemble support.
    
    Features:
    - Ensemble model (RF + XGBoost + LightGBM)
    - Automatic fallback to Poisson model
    - Confidence scoring with prediction variance
    - Feature importance analysis
    
    Example:
        >>> predictor = EnhancedMLPredictor()
        >>> result = predictor.predict(strong_stats, weak_stats)
        >>> print(f"Hole probability: {result.hole_probability:.2%}")
    """
    
    # Feature names matching training
    FEATURE_NAMES = [
        "home_win_rate_recent", "home_goals_for_avg", "home_goals_against_avg",
        "home_home_win_rate", "home_days_rest", "home_back_to_back",
        "home_ot_win_rate", "home_power_play_pct", "home_penalty_kill_pct", "home_streak",
        "away_win_rate_recent", "away_goals_for_avg", "away_goals_against_avg",
        "away_away_win_rate", "away_days_rest", "away_back_to_back",
        "away_ot_win_rate", "away_power_play_pct", "away_penalty_kill_pct", "away_streak",
        "win_rate_diff", "goal_diff_diff", "rest_differential", "ot_win_rate_diff",
        "h2h_ot_rate", "same_division", "same_conference", "implied_closeness"
    ]
    
    def __init__(self, config: Optional[MLPredictorConfig] = None):
        """Initialize predictor.
        
        Args:
            config: Predictor configuration
        """
        self.config = config or MLPredictorConfig()
        
        # Model components
        self.model = None
        self.scaler = None
        self.ensemble = None
        self.is_loaded = False
        self.model_version = ""
        
        # Fallback predictor
        self.poisson_predictor = OvertimePredictor()
        
        # Load models
        self._load_models()
    
    def _load_models(self) -> bool:
        """Load trained models from disk."""
        if not SKLEARN_AVAILABLE:
            logger.warning("sklearn not available, will use Poisson fallback")
            return False
        
        # Try ensemble first
        if self.config.use_ensemble and Path(self.config.ensemble_path).exists():
            try:
                from training.ensemble import EnsemblePredictor
                self.ensemble = EnsemblePredictor.load(self.config.ensemble_path)
                self.is_loaded = True
                self.model_version = "ensemble"
                logger.info("Loaded ensemble model")
                return True
            except Exception as e:
                logger.warning(f"Could not load ensemble: {e}")
        
        # Fall back to single model
        model_path = Path(self.config.model_path)
        scaler_path = Path(self.config.scaler_path)
        
        if model_path.exists() and scaler_path.exists():
            try:
                with open(model_path, 'rb') as f:
                    self.model = pickle.load(f)
                with open(scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                self.is_loaded = True
                self.model_version = "single_model"
                logger.info("Loaded single ML model")
                return True
            except Exception as e:
                logger.error(f"Error loading model: {e}")
        else:
            logger.info("No trained model found, will use Poisson fallback")
        
        return False
    
    def reload_models(self) -> bool:
        """Reload models from disk."""
        self.is_loaded = False
        return self._load_models()
    
    def extract_features(
        self,
        strong_stats: Dict[str, Any],
        weak_stats: Dict[str, Any],
        is_strong_home: bool = True,
        h2h_ot_rate: float = 0.23,
        same_division: bool = False,
        same_conference: bool = True,
        implied_closeness: float = 0.5
    ) -> np.ndarray:
        """Extract features from team stats.
        
        Args:
            strong_stats: Strong team statistics dict
            weak_stats: Weak team statistics dict
            is_strong_home: Whether strong team is home
            h2h_ot_rate: Head-to-head OT rate
            same_division: Same division flag
            same_conference: Same conference flag
            implied_closeness: Odds-implied closeness
            
        Returns:
            Feature array
        """
        if is_strong_home:
            home = strong_stats
            away = weak_stats
        else:
            home = weak_stats
            away = strong_stats
        
        features = {
            "home_win_rate_recent": home.get('win_rate', 0.5),
            "home_goals_for_avg": home.get('goals_for_avg', 2.7),
            "home_goals_against_avg": home.get('goals_against_avg', 2.7),
            "home_home_win_rate": home.get('home_win_rate', 0.55),
            "home_days_rest": home.get('days_rest', 2),
            "home_back_to_back": 1 if home.get('days_rest', 2) == 1 else 0,
            "home_ot_win_rate": home.get('ot_win_rate', 0.5),
            "home_power_play_pct": home.get('power_play_pct', 0.2),
            "home_penalty_kill_pct": home.get('penalty_kill_pct', 0.8),
            "home_streak": home.get('streak', 0),
            
            "away_win_rate_recent": away.get('win_rate', 0.5),
            "away_goals_for_avg": away.get('goals_for_avg', 2.7),
            "away_goals_against_avg": away.get('goals_against_avg', 2.7),
            "away_away_win_rate": away.get('away_win_rate', 0.45),
            "away_days_rest": away.get('days_rest', 2),
            "away_back_to_back": 1 if away.get('days_rest', 2) == 1 else 0,
            "away_ot_win_rate": away.get('ot_win_rate', 0.5),
            "away_power_play_pct": away.get('power_play_pct', 0.2),
            "away_penalty_kill_pct": away.get('penalty_kill_pct', 0.8),
            "away_streak": away.get('streak', 0),
            
            "win_rate_diff": abs(home.get('win_rate', 0.5) - away.get('win_rate', 0.5)),
            "goal_diff_diff": abs(
                (home.get('goals_for_avg', 2.7) - home.get('goals_against_avg', 2.7)) -
                (away.get('goals_for_avg', 2.7) - away.get('goals_against_avg', 2.7))
            ),
            "rest_differential": home.get('days_rest', 2) - away.get('days_rest', 2),
            "ot_win_rate_diff": home.get('ot_win_rate', 0.5) - away.get('ot_win_rate', 0.5),
            
            "h2h_ot_rate": h2h_ot_rate,
            "same_division": 1 if same_division else 0,
            "same_conference": 1 if same_conference else 0,
            "implied_closeness": implied_closeness
        }
        
        return np.array([[features[name] for name in self.FEATURE_NAMES]])
    
    def predict(
        self,
        strong_stats: Dict[str, Any],
        weak_stats: Dict[str, Any],
        match_id: str = "",
        is_strong_home: bool = True,
        h2h_ot_rate: float = 0.23,
        same_division: bool = False,
        same_conference: bool = True,
        odds_strong: float = None,
        odds_weak: float = None
    ) -> MLPredictionResult:
        """Predict overtime probability and hole risk.
        
        Args:
            strong_stats: Strong team statistics
            weak_stats: Weak team statistics
            match_id: Match identifier
            is_strong_home: Whether strong team is home
            h2h_ot_rate: Head-to-head OT rate
            same_division: Same division flag
            same_conference: Same conference flag
            odds_strong: Betting odds for strong team
            odds_weak: Betting odds for weak team
            
        Returns:
            MLPredictionResult with predictions
        """
        # Calculate implied closeness from odds
        implied_closeness = 0.5
        if odds_strong and odds_weak:
            implied_strong = 1 / odds_strong
            implied_closeness = 1 - abs(implied_strong - 0.5) * 2
        
        # Try ML prediction
        if self.is_loaded:
            try:
                result = self._predict_ml(
                    strong_stats, weak_stats, match_id,
                    is_strong_home, h2h_ot_rate,
                    same_division, same_conference, implied_closeness
                )
                return result
            except Exception as e:
                logger.warning(f"ML prediction failed: {e}")
                if not self.config.fallback_to_poisson:
                    raise
        
        # Fallback to Poisson
        return self._predict_poisson_fallback(
            strong_stats, weak_stats, match_id, odds_strong, odds_weak
        )
    
    def _predict_ml(
        self,
        strong_stats: Dict[str, Any],
        weak_stats: Dict[str, Any],
        match_id: str,
        is_strong_home: bool,
        h2h_ot_rate: float,
        same_division: bool,
        same_conference: bool,
        implied_closeness: float
    ) -> MLPredictionResult:
        """Make ML-based prediction."""
        # Extract features
        X = self.extract_features(
            strong_stats, weak_stats, is_strong_home,
            h2h_ot_rate, same_division, same_conference, implied_closeness
        )
        
        # Scale features
        if self.scaler:
            X_scaled = self.scaler.transform(X)
        else:
            X_scaled = X
        
        # Get prediction
        if self.ensemble:
            proba = self.ensemble.predict_proba(X_scaled)
            ot_probability = proba[0, 1]
            variance = self.ensemble.get_prediction_variance(X_scaled)[0]
        else:
            proba = self.model.predict_proba(X_scaled)
            ot_probability = proba[0, 1]
            variance = 0.0
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            ot_probability, variance, X[0]
        )
        
        # Calculate OT win probabilities
        strong_ot_win, weak_ot_win = self._calculate_ot_winners(
            strong_stats, weak_stats, X[0]
        )
        
        # Hole probability
        hole_probability = ot_probability * weak_ot_win
        
        # Feature importance
        feature_importance = {}
        if self.model and hasattr(self.model, 'feature_importances_'):
            for name, imp in zip(self.FEATURE_NAMES, self.model.feature_importances_):
                feature_importance[name] = float(imp)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            ot_probability, hole_probability, confidence,
            strong_stats, weak_stats, X[0]
        )
        
        return MLPredictionResult(
            match_id=match_id,
            ot_probability=ot_probability,
            strong_ot_win_prob=ot_probability * strong_ot_win,
            weak_ot_win_prob=ot_probability * weak_ot_win,
            hole_probability=hole_probability,
            confidence=confidence,
            expected_score=(
                strong_stats.get('goals_for_avg', 2.7),
                weak_stats.get('goals_for_avg', 2.5)
            ),
            reasoning=reasoning,
            model_used=self.model_version,
            model_version=self.model_version,
            feature_importance=feature_importance,
            prediction_variance=variance,
            used_fallback=False
        )
    
    def _predict_poisson_fallback(
        self,
        strong_stats: Dict[str, Any],
        weak_stats: Dict[str, Any],
        match_id: str,
        odds_strong: float = None,
        odds_weak: float = None
    ) -> MLPredictionResult:
        """Fallback to Poisson-based prediction."""
        logger.info("Using Poisson fallback for prediction")
        
        # Use odds-based prediction if available
        if odds_strong and odds_weak:
            pred = self.poisson_predictor.predict_from_odds(
                odds_strong, odds_weak, match_id
            )
        else:
            # Create TeamStats from dict
            strong = TeamStats(
                team_name=strong_stats.get('team_name', 'Strong'),
                goals_scored=strong_stats.get('goals_for_avg', 2.7) * 20,
                goals_conceded=strong_stats.get('goals_against_avg', 2.5) * 20,
                games_played=20,
                ot_wins=int(strong_stats.get('ot_win_rate', 0.5) * 5),
                ot_losses=5 - int(strong_stats.get('ot_win_rate', 0.5) * 5),
                recent_form=strong_stats.get('recent_form', 0.5)
            )
            weak = TeamStats(
                team_name=weak_stats.get('team_name', 'Weak'),
                goals_scored=weak_stats.get('goals_for_avg', 2.5) * 20,
                goals_conceded=weak_stats.get('goals_against_avg', 2.7) * 20,
                games_played=20,
                ot_wins=int(weak_stats.get('ot_win_rate', 0.5) * 5),
                ot_losses=5 - int(weak_stats.get('ot_win_rate', 0.5) * 5),
                recent_form=weak_stats.get('recent_form', 0.5)
            )
            pred = self.poisson_predictor.predict(strong, weak, match_id)
        
        return MLPredictionResult(
            match_id=match_id,
            ot_probability=pred.ot_probability,
            strong_ot_win_prob=pred.strong_ot_win_prob,
            weak_ot_win_prob=pred.weak_ot_win_prob,
            hole_probability=pred.hole_probability,
            confidence=pred.confidence * 0.8,  # Lower confidence for fallback
            expected_score=pred.expected_score,
            reasoning=f"[Poisson Fallback] {pred.reasoning}",
            model_used="poisson_fallback",
            model_version="poisson",
            used_fallback=True,
            fallback_reason="ML model not available or prediction failed"
        )
    
    def _calculate_confidence(
        self,
        ot_probability: float,
        variance: float,
        features: np.ndarray
    ) -> float:
        """Calculate prediction confidence."""
        # Base confidence from probability distance from 0.5
        base_confidence = 2 * abs(ot_probability - 0.5)
        
        # Reduce confidence if high variance (disagreement between models)
        variance_penalty = min(0.2, variance * 2)
        
        # Boost confidence if teams are evenly matched (more predictable OT)
        win_rate_diff = features[20]  # win_rate_diff feature
        if win_rate_diff < 0.1:
            base_confidence *= 1.1
        
        confidence = base_confidence - variance_penalty
        return max(0.4, min(0.95, confidence))
    
    def _calculate_ot_winners(
        self,
        strong_stats: Dict[str, Any],
        weak_stats: Dict[str, Any],
        features: np.ndarray
    ) -> Tuple[float, float]:
        """Calculate OT win probabilities."""
        base_strong = self.config.favorite_ot_advantage
        
        # Adjust for OT history
        ot_diff = strong_stats.get('ot_win_rate', 0.5) - weak_stats.get('ot_win_rate', 0.5)
        ot_adj = ot_diff * 0.2
        
        # Adjust for form
        form_adj = (strong_stats.get('recent_form', 0.5) - weak_stats.get('recent_form', 0.5)) * 0.1
        
        # Adjust for fatigue
        fatigue_adj = 0
        if strong_stats.get('days_rest', 2) == 1:
            fatigue_adj -= 0.05
        if weak_stats.get('days_rest', 2) == 1:
            fatigue_adj += 0.05
        
        strong_ot = min(0.70, max(0.35, base_strong + ot_adj + form_adj + fatigue_adj))
        weak_ot = 1 - strong_ot
        
        return strong_ot, weak_ot
    
    def _generate_reasoning(
        self,
        ot_prob: float,
        hole_prob: float,
        confidence: float,
        strong_stats: Dict[str, Any],
        weak_stats: Dict[str, Any],
        features: np.ndarray
    ) -> str:
        """Generate human-readable reasoning."""
        reasons = [f"[{self.model_version}]"]
        
        # OT probability
        if ot_prob > 0.28:
            reasons.append(f"HIGH OT risk ({ot_prob:.1%})")
        elif ot_prob < 0.20:
            reasons.append(f"LOW OT risk ({ot_prob:.1%})")
        else:
            reasons.append(f"Average OT risk ({ot_prob:.1%})")
        
        # Hole probability
        if hole_prob > 0.05:
            reasons.append(f"⚠️ HIGH HOLE: {hole_prob:.1%}")
        elif hole_prob > 0.04:
            reasons.append(f"⚡ MODERATE hole: {hole_prob:.1%}")
        else:
            reasons.append(f"✅ LOW hole: {hole_prob:.1%}")
        
        # Key factors
        win_rate_diff = features[20]
        if win_rate_diff < 0.08:
            reasons.append("Evenly matched teams")
        
        if features[25]:  # same_division
            reasons.append("Division rivalry")
        
        if features[5] or features[15]:  # back_to_back
            reasons.append("Fatigue factor")
        
        return " | ".join(reasons)
    
    def predict_from_odds(
        self,
        odds_strong: float,
        odds_weak: float,
        match_id: str = ""
    ) -> MLPredictionResult:
        """Predict from odds alone (when team stats not available)."""
        # Derive approximate stats from odds
        implied_strong = 1 / odds_strong
        implied_weak = 1 / odds_weak
        total = implied_strong + implied_weak
        p_strong = implied_strong / total
        
        strong_stats = {
            'win_rate': p_strong,
            'goals_for_avg': 2.7 + (p_strong - 0.5),
            'goals_against_avg': 2.7 - (p_strong - 0.5) * 0.5,
            'recent_form': 0.5 + (p_strong - 0.5) * 0.3,
            'ot_win_rate': 0.55,
            'days_rest': 2
        }
        
        weak_stats = {
            'win_rate': 1 - p_strong,
            'goals_for_avg': 2.7 - (p_strong - 0.5) * 0.5,
            'goals_against_avg': 2.7 + (p_strong - 0.5),
            'recent_form': 0.5 - (p_strong - 0.5) * 0.2,
            'ot_win_rate': 0.45,
            'days_rest': 2
        }
        
        result = self.predict(
            strong_stats, weak_stats, match_id,
            odds_strong=odds_strong, odds_weak=odds_weak
        )
        
        result.confidence = min(result.confidence, 0.6)
        result.reasoning = "[odds-only] " + result.reasoning
        
        return result
    
    def is_safe_bet(
        self,
        prediction: MLPredictionResult,
        max_hole_prob: float = 0.04
    ) -> bool:
        """Check if bet is safe based on hole probability."""
        return prediction.hole_probability <= max_hole_prob
    
    @property
    def model_info(self) -> Dict[str, Any]:
        """Get model information."""
        return {
            'is_loaded': self.is_loaded,
            'model_version': self.model_version,
            'model_type': 'ensemble' if self.ensemble else 'single',
            'feature_count': len(self.FEATURE_NAMES),
            'fallback_enabled': self.config.fallback_to_poisson
        }
