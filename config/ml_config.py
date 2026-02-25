"""ML Model Configuration for Eden MVP Phase 2.

Centralized configuration for all ML-related settings.
"""

import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any

from utils.logger import get_logger

logger = get_logger(__name__)


CONFIG_FILE = Path("config/ml_settings.json")


@dataclass
class DataCollectionConfig:
    """Configuration for data collection."""
    # Seasons to collect
    seasons: List[str] = field(default_factory=lambda: ["20232024", "20242025"])
    
    # NHL API settings
    nhl_api_rate_limit: float = 0.5  # seconds between requests
    cache_enabled: bool = True
    cache_ttl_hours: int = 6
    
    # Collection schedule
    auto_collect: bool = True
    collection_interval_hours: int = 12
    
    # Data retention
    keep_seasons: int = 3


@dataclass
class FeatureConfig:
    """Configuration for feature engineering."""
    # Team features
    recent_games_for_form: int = 10
    recent_games_for_goals: int = 20
    
    # Match features
    h2h_games_limit: int = 10
    
    # Feature selection
    use_feature_selection: bool = False
    feature_importance_threshold: float = 0.01


@dataclass
class TrainingConfig:
    """Configuration for model training."""
    # Data split
    test_size: float = 0.2
    validation_size: float = 0.1
    random_state: int = 42
    
    # Cross-validation
    cv_folds: int = 5
    
    # Models to train
    train_random_forest: bool = True
    train_xgboost: bool = True
    train_lightgbm: bool = True
    train_logistic: bool = False
    
    # Hyperparameter tuning
    use_hyperparameter_tuning: bool = True
    tuning_method: str = "random"  # "random" or "grid"
    n_iter_random_search: int = 20
    
    # Ensemble
    use_ensemble: bool = True
    ensemble_voting: str = "soft"  # "soft" or "hard"
    
    # Calibration
    use_calibration: bool = True
    calibration_method: str = "isotonic"  # "isotonic" or "sigmoid"


@dataclass
class PredictionConfig:
    """Configuration for predictions."""
    # Model selection
    model_type: str = "ensemble"  # "ensemble", "random_forest", "xgboost", "lgbm", "poisson"
    fallback_to_poisson: bool = True
    
    # Thresholds
    min_confidence: float = 0.5
    max_hole_probability: float = 0.04
    
    # OT parameters
    base_ot_rate: float = 0.23
    favorite_ot_advantage: float = 0.55


@dataclass
class RetrainingConfig:
    """Configuration for automatic retraining."""
    # Schedule
    enabled: bool = True
    interval_days: int = 7
    min_new_samples: int = 50
    
    # Performance thresholds
    min_auc_threshold: float = 0.55
    max_brier_threshold: float = 0.30
    min_accuracy_threshold: float = 0.55
    
    # Versioning
    keep_model_versions: int = 5


@dataclass 
class ABTestingConfig:
    """Configuration for A/B testing."""
    enabled: bool = True
    min_predictions_for_analysis: int = 50
    significance_level: float = 0.05


@dataclass
class MLConfig:
    """Master configuration for ML system."""
    data_collection: DataCollectionConfig = field(default_factory=DataCollectionConfig)
    features: FeatureConfig = field(default_factory=FeatureConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    prediction: PredictionConfig = field(default_factory=PredictionConfig)
    retraining: RetrainingConfig = field(default_factory=RetrainingConfig)
    ab_testing: ABTestingConfig = field(default_factory=ABTestingConfig)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def save(self, path: Path = None) -> None:
        """Save configuration to file."""
        path = path or CONFIG_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        
        logger.info(f"Configuration saved to {path}")
    
    @classmethod
    def load(cls, path: Path = None) -> 'MLConfig':
        """Load configuration from file."""
        path = path or CONFIG_FILE
        
        if not path.exists():
            logger.info("No config file found, using defaults")
            return cls()
        
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            
            config = cls(
                data_collection=DataCollectionConfig(**data.get('data_collection', {})),
                features=FeatureConfig(**data.get('features', {})),
                training=TrainingConfig(**data.get('training', {})),
                prediction=PredictionConfig(**data.get('prediction', {})),
                retraining=RetrainingConfig(**data.get('retraining', {})),
                ab_testing=ABTestingConfig(**data.get('ab_testing', {}))
            )
            
            logger.info(f"Configuration loaded from {path}")
            return config
            
        except Exception as e:
            logger.warning(f"Error loading config: {e}, using defaults")
            return cls()
    
    @classmethod
    def get_default(cls) -> 'MLConfig':
        """Get default configuration."""
        return cls()


# Global config instance
_config: Optional[MLConfig] = None


def get_ml_config() -> MLConfig:
    """Get the global ML configuration."""
    global _config
    if _config is None:
        _config = MLConfig.load()
    return _config


def reload_ml_config() -> MLConfig:
    """Reload configuration from file."""
    global _config
    _config = MLConfig.load()
    return _config


def save_ml_config(config: MLConfig = None) -> None:
    """Save configuration to file."""
    global _config
    if config:
        _config = config
    if _config:
        _config.save()


# Convenience functions
def get_data_collection_config() -> DataCollectionConfig:
    """Get data collection configuration."""
    return get_ml_config().data_collection


def get_training_config() -> TrainingConfig:
    """Get training configuration."""
    return get_ml_config().training


def get_prediction_config() -> PredictionConfig:
    """Get prediction configuration."""
    return get_ml_config().prediction


def get_retraining_config() -> RetrainingConfig:
    """Get retraining configuration."""
    return get_ml_config().retraining
