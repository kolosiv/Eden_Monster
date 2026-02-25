"""Model Trainer v2 for Eden MVP - With Critical Fixes.

CRITICAL FIXES APPLIED:
1. Uses TimeSeriesSplit instead of regular k-fold CV (fixes look-ahead bias)
2. Trains on REAL NHL data instead of synthetic data
3. Validates data quality before training
4. Proper train/test temporal split with gap
5. More conservative hyperparameters to prevent overfitting

This addresses the issues identified in the model analysis.
"""

import pickle
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

import numpy as np

from utils.logger import get_logger

logger = get_logger(__name__)

# Try importing sklearn
try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import TimeSeriesSplit, cross_val_score
    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score, f1_score,
        roc_auc_score, classification_report, confusion_matrix
    )
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.error("scikit-learn not installed. Run: pip install scikit-learn")


@dataclass
class TrainingConfigV2:
    """Configuration for model training v2.
    
    CHANGES:
    - Reduced n_estimators and max_depth to prevent overfitting
    - Added temporal_gap to prevent data leakage
    - Use TimeSeriesSplit by default
    """
    model_path: str = "models/overtime_model_v2.pkl"
    scaler_path: str = "models/overtime_scaler_v2.pkl"
    n_estimators: int = 80  # Reduced from 100 to prevent overfitting
    max_depth: int = 8  # Reduced from 10 to prevent overfitting
    min_samples_split: int = 10  # Increased from 5
    min_samples_leaf: int = 5  # Increased from 2
    test_size: float = 0.2
    random_state: int = 42
    use_time_series_cv: bool = True  # CRITICAL FIX: Use temporal CV
    cv_folds: int = 5
    temporal_gap: int = 10  # Gap between train and test (in games)
    min_data_quality_score: float = 0.6  # Minimum acceptable data quality


@dataclass 
class TrainingResultV2:
    """Result of model training with additional validation info."""
    accuracy: float
    precision: float
    recall: float
    f1: float
    auc_roc: float
    cv_scores: Optional[List[float]] = None
    cv_mean: float = 0.0
    cv_std: float = 0.0
    feature_importance: Dict[str, float] = None
    confusion_matrix: Optional[np.ndarray] = None
    training_time: float = 0.0
    data_quality_score: float = 0.0
    ot_rate_in_data: float = 0.0
    warnings: List[str] = field(default_factory=list)
    train_accuracy: float = 0.0  # To detect overfitting


class ModelTrainerV2:
    """ML Model Trainer v2 with critical fixes.
    
    CRITICAL FIXES:
    1. TimeSeriesSplit for temporal cross-validation
    2. Real NHL data only (no synthetic)
    3. Data quality validation
    4. Overfitting detection
    5. Removed 'implied_closeness' feature (potential leakage)
    """
    
    # Feature names - REMOVED implied_closeness (potential leakage)
    FEATURE_NAMES = [
        "home_gf_avg", "home_ga_avg", "away_gf_avg", "away_ga_avg",
        "goal_diff_home", "goal_diff_away", "home_win_rate", "away_win_rate",
        "win_rate_diff", "win_rate_closeness",  # Replaced implied_closeness
        "home_ot_win_rate", "away_ot_win_rate",
        "home_form", "away_form", "form_diff",
        "home_rest_days", "away_rest_days", "home_back_to_back", "away_back_to_back",
        "h2h_ot_rate", "home_special_teams", "away_special_teams",
        "same_division", "same_conference"
    ]
    
    def __init__(self, config: Optional[TrainingConfigV2] = None):
        """Initialize trainer with v2 config."""
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn is required. Install with: pip install scikit-learn")
        
        self.config = config or TrainingConfigV2()
        self.model = None
        self.scaler = None
    
    def prepare_data(
        self,
        X: List[Dict],
        y: List[int]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare data for training."""
        X_array = np.array([
            [d.get(name, 0) for name in self.FEATURE_NAMES]
            for d in X
        ])
        y_array = np.array(y)
        
        logger.info(f"Prepared {len(X_array)} samples with {len(self.FEATURE_NAMES)} features")
        
        ot_count = sum(y_array)
        ot_rate = ot_count / len(y_array)
        logger.info(f"Class distribution: OT={ot_count} ({ot_rate:.1%}), No OT={len(y_array)-ot_count}")
        
        # Validate OT rate
        if ot_rate < 0.15 or ot_rate > 0.30:
            logger.warning(
                f"OT rate {ot_rate:.1%} outside expected range (15-30%). "
                "Data quality may be compromised."
            )
        
        return X_array, y_array
    
    def _temporal_train_test_split(
        self,
        X: np.ndarray,
        y: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Split data temporally (earlier data for train, later for test).
        
        CRITICAL FIX: This ensures no future data leaks into training.
        """
        n_samples = len(X)
        n_test = int(n_samples * self.config.test_size)
        n_train = n_samples - n_test - self.config.temporal_gap
        
        # Train on earlier data, test on later data
        X_train = X[:n_train]
        y_train = y[:n_train]
        X_test = X[n_train + self.config.temporal_gap:]
        y_test = y[n_train + self.config.temporal_gap:]
        
        logger.info(f"Temporal split: {len(X_train)} train, {len(X_test)} test, gap={self.config.temporal_gap}")
        
        return X_train, X_test, y_train, y_test
    
    def train(
        self,
        X: List[Dict],
        y: List[int],
        data_quality_score: float = 1.0,
        save_model: bool = True
    ) -> TrainingResultV2:
        """Train the ML model with critical fixes.
        
        Args:
            X: Feature dictionaries (from REAL data only)
            y: Labels (1 = OT, 0 = no OT)
            data_quality_score: Quality score from data validation
            save_model: Whether to save the trained model
            
        Returns:
            TrainingResultV2 with comprehensive metrics
        """
        start_time = datetime.now()
        warnings = []
        
        logger.info("="*60)
        logger.info("TRAINING MODEL v2 (WITH CRITICAL FIXES)")
        logger.info("="*60)
        
        # Check data quality
        if data_quality_score < self.config.min_data_quality_score:
            warnings.append(
                f"WARNING: Data quality score {data_quality_score:.2f} below threshold "
                f"{self.config.min_data_quality_score}. Results may be unreliable."
            )
            logger.warning(warnings[-1])
        
        # Prepare data
        X_array, y_array = self.prepare_data(X, y)
        ot_rate = sum(y_array) / len(y_array)
        
        # CRITICAL FIX: Temporal train/test split
        X_train, X_test, y_train, y_test = self._temporal_train_test_split(X_array, y_array)
        
        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train RandomForest with conservative hyperparameters
        self.model = RandomForestClassifier(
            n_estimators=self.config.n_estimators,
            max_depth=self.config.max_depth,
            min_samples_split=self.config.min_samples_split,
            min_samples_leaf=self.config.min_samples_leaf,
            random_state=self.config.random_state,
            class_weight='balanced',
            n_jobs=-1
        )
        
        logger.info("Training RandomForest classifier...")
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate on train (to detect overfitting)
        y_train_pred = self.model.predict(X_train_scaled)
        train_accuracy = accuracy_score(y_train, y_train_pred)
        
        # Evaluate on test
        y_pred = self.model.predict(X_test_scaled)
        y_proba = self.model.predict_proba(X_test_scaled)[:, 1]
        
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        
        # Handle AUC-ROC (may fail if only one class in test)
        try:
            auc = roc_auc_score(y_test, y_proba)
        except ValueError:
            auc = 0.5
            warnings.append("WARNING: Could not compute AUC-ROC (single class in test set)")
        
        # OVERFITTING CHECK
        if train_accuracy > accuracy + 0.15:
            warnings.append(
                f"WARNING: Possible overfitting detected! "
                f"Train accuracy ({train_accuracy:.1%}) >> Test accuracy ({accuracy:.1%})"
            )
            logger.warning(warnings[-1])
        
        # CRITICAL FIX: TimeSeriesSplit cross-validation
        cv_scores = None
        cv_mean = 0.0
        cv_std = 0.0
        
        if self.config.use_time_series_cv:
            logger.info(f"Running {self.config.cv_folds}-fold TimeSeriesSplit cross-validation...")
            
            tscv = TimeSeriesSplit(n_splits=self.config.cv_folds)
            X_scaled_full = self.scaler.fit_transform(X_array)
            
            cv_scores = cross_val_score(
                self.model, X_scaled_full, y_array,
                cv=tscv, scoring='roc_auc'
            ).tolist()
            
            cv_mean = np.mean(cv_scores)
            cv_std = np.std(cv_scores)
            
            logger.info(f"TimeSeriesSplit CV AUC scores: {[f'{s:.3f}' for s in cv_scores]}")
            logger.info(f"CV AUC mean: {cv_mean:.3f} (+/- {cv_std:.3f})")
            
            # Check for high variance (unstable model)
            if cv_std > 0.1:
                warnings.append(
                    f"WARNING: High CV variance (std={cv_std:.3f}). Model may be unstable."
                )
        
        # Feature importance
        feature_importance = dict(zip(
            self.FEATURE_NAMES,
            self.model.feature_importances_
        ))
        
        sorted_features = sorted(
            feature_importance.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        logger.info("\nTop 10 important features:")
        for name, imp in sorted_features[:10]:
            logger.info(f"  {name}: {imp:.4f}")
        
        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        
        training_time = (datetime.now() - start_time).total_seconds()
        
        result = TrainingResultV2(
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1=f1,
            auc_roc=auc,
            cv_scores=cv_scores,
            cv_mean=cv_mean,
            cv_std=cv_std,
            feature_importance=feature_importance,
            confusion_matrix=cm,
            training_time=training_time,
            data_quality_score=data_quality_score,
            ot_rate_in_data=ot_rate,
            warnings=warnings,
            train_accuracy=train_accuracy
        )
        
        logger.info(f"\n{'='*60}")
        logger.info("TRAINING RESULTS")
        logger.info(f"{'='*60}")
        logger.info(f"Training time: {training_time:.1f}s")
        logger.info(f"Train Accuracy: {train_accuracy:.3f}")
        logger.info(f"Test Accuracy: {accuracy:.3f}")
        logger.info(f"Precision: {precision:.3f}")
        logger.info(f"Recall: {recall:.3f}")
        logger.info(f"F1 Score: {f1:.3f}")
        logger.info(f"AUC-ROC: {auc:.3f}")
        if cv_scores:
            logger.info(f"CV AUC (TimeSeriesSplit): {cv_mean:.3f} ± {cv_std:.3f}")
        logger.info(f"Data quality score: {data_quality_score:.2f}")
        logger.info(f"OT rate in data: {ot_rate:.1%}")
        
        if warnings:
            logger.warning(f"\n{len(warnings)} warnings during training:")
            for w in warnings:
                logger.warning(f"  - {w}")
        
        # Save model
        if save_model:
            self._save_model()
        
        return result
    
    def _save_model(self) -> None:
        """Save trained model and scaler."""
        model_path = Path(self.config.model_path)
        scaler_path = Path(self.config.scaler_path)
        
        model_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(model_path, 'wb') as f:
            pickle.dump(self.model, f)
        
        with open(scaler_path, 'wb') as f:
            pickle.dump(self.scaler, f)
        
        logger.info(f"Model saved to {model_path}")
        logger.info(f"Scaler saved to {scaler_path}")
    
    def evaluate_hole_probability(
        self,
        X: List[Dict],
        y: List[int],
        actual_ot_winners: List[Optional[str]] = None
    ) -> Dict:
        """Evaluate model's ability to identify low-hole opportunities.
        
        FIXED: Uses dynamic OT win rate instead of fixed 45%.
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        X_array, y_array = self.prepare_data(X, y)
        X_scaled = self.scaler.transform(X_array)
        
        # Get predicted OT probabilities
        ot_probs = self.model.predict_proba(X_scaled)[:, 1]
        
        # FIXED: Dynamic weak team OT win rate based on feature values
        # Weak team is less likely to win OT when there's a big skill gap
        hole_probs = []
        for i, features in enumerate(X):
            ot_prob = ot_probs[i]
            
            # Dynamic calculation based on win rate difference
            win_rate_diff = features.get('win_rate_diff', 0)
            # Weak team OT win rate decreases with larger skill gap
            # Base: 50%, reduced by skill difference
            weak_ot_win_rate = max(0.35, 0.50 - win_rate_diff * 0.5)
            
            hole_prob = ot_prob * weak_ot_win_rate
            hole_probs.append(hole_prob)
        
        hole_probs = np.array(hole_probs)
        
        # Calculate metrics
        avg_predicted_hole = np.mean(hole_probs)
        
        # Compare to actual holes
        actual_holes = 0
        if actual_ot_winners:
            for i, (went_ot, winner) in enumerate(zip(y, actual_ot_winners)):
                if went_ot and winner == 'away':
                    actual_holes += 1
        
        actual_hole_rate = actual_holes / len(y) if y else 0
        
        # Count predictions under threshold
        safe_threshold = 0.04
        predictions_under_4pct = np.sum(hole_probs < safe_threshold) / len(hole_probs)
        
        results = {
            "avg_predicted_hole_prob": float(avg_predicted_hole),
            "actual_hole_rate": float(actual_hole_rate),
            "predictions_under_4pct": float(predictions_under_4pct),
            "min_hole_prob": float(np.min(hole_probs)),
            "max_hole_prob": float(np.max(hole_probs)),
            "std_hole_prob": float(np.std(hole_probs))
        }
        
        logger.info(f"Hole probability analysis:")
        logger.info(f"  Average predicted: {avg_predicted_hole:.2%}")
        logger.info(f"  Actual rate: {actual_hole_rate:.2%}")
        logger.info(f"  Predictions <4%: {predictions_under_4pct:.1%}")
        
        return results


def train_model_v2(num_samples: int = 5000) -> TrainingResultV2:
    """Train model v2 on REAL NHL data.
    
    CRITICAL: This uses REAL data from nhl_historical.db.
    NO synthetic data is used.
    
    Args:
        num_samples: Number of real games to use
        
    Returns:
        TrainingResultV2 with comprehensive metrics
    """
    from data.real_data_fetcher import RealNHLDataFetcher
    
    logger.info("="*60)
    logger.info("TRAINING ML MODEL v2 ON REAL NHL DATA")
    logger.info("="*60)
    
    # Fetch REAL data
    fetcher = RealNHLDataFetcher()
    
    # Get statistics
    stats = fetcher.get_statistics()
    logger.info(f"Database statistics:")
    logger.info(f"  Total games: {stats.get('total_games', 0)}")
    logger.info(f"  OT rate: {stats.get('ot_rate', 0):.1%}")
    logger.info(f"  Seasons: {stats.get('seasons', [])}")
    
    # Get training data with validation
    X, y, metrics = fetcher.get_training_data(num_samples, validate=True)
    
    # Train model
    trainer = ModelTrainerV2()
    result = trainer.train(X, y, data_quality_score=metrics.data_quality_score)
    
    # Evaluate hole probability
    trainer.evaluate_hole_probability(X, y)
    
    logger.info("="*60)
    logger.info("TRAINING COMPLETE")
    logger.info("="*60)
    
    return result


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    train_model_v2(5000)
