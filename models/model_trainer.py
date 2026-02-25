"""Model Trainer for Eden MVP ML Overtime Predictor.

Trains and evaluates RandomForest model on historical data.
"""

import pickle
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import numpy as np

from utils.logger import get_logger

logger = get_logger(__name__)

# Try importing sklearn
try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score, f1_score,
        roc_auc_score, classification_report, confusion_matrix
    )
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.error("scikit-learn not installed. Run: pip install scikit-learn")


@dataclass
class TrainingConfig:
    """Configuration for model training."""
    model_path: str = "models/overtime_model.pkl"
    scaler_path: str = "models/overtime_scaler.pkl"
    n_estimators: int = 100
    max_depth: int = 10
    min_samples_split: int = 5
    min_samples_leaf: int = 2
    test_size: float = 0.2
    random_state: int = 42
    use_cross_validation: bool = True
    cv_folds: int = 5


@dataclass 
class TrainingResult:
    """Result of model training."""
    accuracy: float
    precision: float
    recall: float
    f1: float
    auc_roc: float
    cv_scores: Optional[List[float]] = None
    feature_importance: Dict[str, float] = None
    confusion_matrix: Optional[np.ndarray] = None
    training_time: float = 0.0


class ModelTrainer:
    """Trains ML model for overtime prediction."""
    
    FEATURE_NAMES = [
        "home_gf_avg", "home_ga_avg", "away_gf_avg", "away_ga_avg",
        "goal_diff_home", "goal_diff_away", "home_win_rate", "away_win_rate",
        "win_rate_diff", "home_ot_win_rate", "away_ot_win_rate",
        "home_form", "away_form", "form_diff",
        "home_rest_days", "away_rest_days", "home_back_to_back", "away_back_to_back",
        "h2h_ot_rate", "home_special_teams", "away_special_teams",
        "same_division", "same_conference", "implied_closeness"
    ]
    
    def __init__(self, config: Optional[TrainingConfig] = None):
        """Initialize trainer."""
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn is required for training. Install with: pip install scikit-learn")
        
        self.config = config or TrainingConfig()
        self.model = None
        self.scaler = None
    
    def prepare_data(
        self,
        X: List[Dict],
        y: List[int]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare data for training.
        
        Args:
            X: List of feature dictionaries
            y: List of labels (1 = OT, 0 = no OT)
            
        Returns:
            X_array, y_array as numpy arrays
        """
        # Convert dicts to array
        X_array = np.array([
            [d.get(name, 0) for name in self.FEATURE_NAMES]
            for d in X
        ])
        y_array = np.array(y)
        
        logger.info(f"Prepared {len(X_array)} samples with {len(self.FEATURE_NAMES)} features")
        logger.info(f"Class distribution: OT={sum(y_array)}, No OT={len(y_array)-sum(y_array)}")
        
        return X_array, y_array
    
    def train(
        self,
        X: List[Dict],
        y: List[int],
        save_model: bool = True
    ) -> TrainingResult:
        """Train the ML model.
        
        Args:
            X: Feature dictionaries
            y: Labels
            save_model: Whether to save the trained model
            
        Returns:
            TrainingResult with metrics
        """
        start_time = datetime.now()
        logger.info("Starting model training...")
        
        # Prepare data
        X_array, y_array = self.prepare_data(X, y)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_array, y_array,
            test_size=self.config.test_size,
            random_state=self.config.random_state,
            stratify=y_array  # Maintain class ratio
        )
        
        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train RandomForest
        self.model = RandomForestClassifier(
            n_estimators=self.config.n_estimators,
            max_depth=self.config.max_depth,
            min_samples_split=self.config.min_samples_split,
            min_samples_leaf=self.config.min_samples_leaf,
            random_state=self.config.random_state,
            class_weight='balanced',  # Handle class imbalance
            n_jobs=-1
        )
        
        logger.info("Training RandomForest classifier...")
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test_scaled)
        y_proba = self.model.predict_proba(X_test_scaled)[:, 1]
        
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        auc = roc_auc_score(y_test, y_proba)
        
        # Cross-validation
        cv_scores = None
        if self.config.use_cross_validation:
            logger.info(f"Running {self.config.cv_folds}-fold cross-validation...")
            X_scaled_full = self.scaler.fit_transform(X_array)
            cv_scores = cross_val_score(
                self.model, X_scaled_full, y_array,
                cv=self.config.cv_folds, scoring='roc_auc'
            ).tolist()
            logger.info(f"CV AUC scores: {[f'{s:.3f}' for s in cv_scores]}")
            logger.info(f"CV AUC mean: {np.mean(cv_scores):.3f} (+/- {np.std(cv_scores):.3f})")
        
        # Feature importance
        feature_importance = dict(zip(
            self.FEATURE_NAMES,
            self.model.feature_importances_
        ))
        
        # Sort by importance
        sorted_features = sorted(
            feature_importance.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        logger.info("Top 10 important features:")
        for name, imp in sorted_features[:10]:
            logger.info(f"  {name}: {imp:.4f}")
        
        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        
        training_time = (datetime.now() - start_time).total_seconds()
        
        result = TrainingResult(
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1=f1,
            auc_roc=auc,
            cv_scores=cv_scores,
            feature_importance=feature_importance,
            confusion_matrix=cm,
            training_time=training_time
        )
        
        logger.info(f"\nTraining completed in {training_time:.1f}s")
        logger.info(f"Accuracy: {accuracy:.3f}")
        logger.info(f"Precision: {precision:.3f}")
        logger.info(f"Recall: {recall:.3f}")
        logger.info(f"F1 Score: {f1:.3f}")
        logger.info(f"AUC-ROC: {auc:.3f}")
        
        # Save model
        if save_model:
            self._save_model()
        
        return result
    
    def _save_model(self) -> None:
        """Save trained model and scaler."""
        model_path = Path(self.config.model_path)
        scaler_path = Path(self.config.scaler_path)
        
        # Ensure directory exists
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
        
        Args:
            X: Feature dictionaries
            y: Labels (OT occurred or not)
            actual_ot_winners: Who won in OT ('home', 'away', or None)
            
        Returns:
            Dict with hole probability metrics
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        X_array, y_array = self.prepare_data(X, y)
        X_scaled = self.scaler.transform(X_array)
        
        # Get predicted OT probabilities
        ot_probs = self.model.predict_proba(X_scaled)[:, 1]
        
        # Simulate hole probability calculation
        # Assuming weak team wins OT ~45% of time when OT occurs
        weak_ot_win_rate = 0.45
        hole_probs = ot_probs * weak_ot_win_rate
        
        # Calculate metrics
        avg_predicted_hole = np.mean(hole_probs)
        
        # Compare to actual holes (if OT data available)
        actual_holes = 0
        if actual_ot_winners:
            for i, (went_ot, winner) in enumerate(zip(y, actual_ot_winners)):
                if went_ot and winner == 'away':  # Weak team won
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


def train_initial_model(num_samples: int = 500) -> TrainingResult:
    """Convenience function to train initial model.
    
    Args:
        num_samples: Number of samples to generate/use
        
    Returns:
        TrainingResult
    """
    from data.historical_data_fetcher import HistoricalDataFetcher
    
    logger.info("="*50)
    logger.info("TRAINING INITIAL ML MODEL")
    logger.info("="*50)
    
    # Fetch/generate data
    fetcher = HistoricalDataFetcher()
    X, y = fetcher.get_training_data(num_samples)
    
    # Train model
    trainer = ModelTrainer()
    result = trainer.train(X, y)
    
    # Evaluate hole probability
    trainer.evaluate_hole_probability(X, y)
    
    logger.info("="*50)
    logger.info("TRAINING COMPLETE")
    logger.info("="*50)
    
    return result


if __name__ == "__main__":
    # Train model when run directly
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    train_initial_model(500)
