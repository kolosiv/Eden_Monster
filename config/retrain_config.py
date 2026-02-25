"""Retrain Configuration Module.

Configuration for automatic retraining.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RetrainConfig:
    """Configuration for auto-retraining system.
    
    Attributes:
        enabled: Whether auto-retrain is enabled
        accuracy_threshold: Minimum accuracy before retrain
        time_threshold_days: Days before time-based retrain
        data_threshold_games: New games before data-based retrain
        schedule: Schedule type ('weekly', 'monthly', or cron)
        schedule_day: Day for weekly schedule (e.g., 'sunday')
        schedule_hour: Hour for scheduled retraining
        use_incremental: Use incremental training when possible
        min_samples_for_retrain: Minimum samples needed for retraining
        max_training_samples: Maximum samples to use
        notification_enabled: Send notifications for retrain events
        rollback_on_worse: Auto-rollback if new model is worse
        ab_test_enabled: Enable A/B testing for new models
        ab_test_days: Days to run A/B test
    """
    # Enable/disable
    enabled: bool = True
    
    # Trigger thresholds
    accuracy_threshold: float = 0.62
    time_threshold_days: int = 7
    data_threshold_games: int = 100
    degradation_threshold: float = 0.05
    
    # Schedule
    schedule: str = "weekly"  # 'weekly', 'monthly', 'daily', or cron syntax
    schedule_day: str = "sunday"
    schedule_hour: int = 3
    check_interval_minutes: int = 60
    
    # Training options
    use_incremental: bool = True
    min_samples_for_retrain: int = 200
    max_training_samples: int = 2000
    validation_split: float = 0.15
    
    # Notifications
    notification_enabled: bool = True
    notify_on_start: bool = True
    notify_on_complete: bool = True
    notify_on_failure: bool = True
    notify_on_rollback: bool = True
    
    # Safety
    rollback_on_worse: bool = True
    min_improvement_to_deploy: float = -0.01  # Accept up to 1% worse
    
    # A/B testing
    ab_test_enabled: bool = False
    ab_test_days: int = 3
    ab_test_traffic_split: float = 0.5  # 50% to new model
    
    # Advanced
    bayesian_tuning: bool = False
    bayesian_trials: int = 50
    include_neural_network: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RetrainConfig':
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})
    
    def validate(self) -> bool:
        """Validate configuration values.
        
        Returns:
            True if valid
        """
        errors = []
        
        if self.accuracy_threshold < 0.5 or self.accuracy_threshold > 1.0:
            errors.append(f"accuracy_threshold must be 0.5-1.0, got {self.accuracy_threshold}")
        
        if self.time_threshold_days < 1:
            errors.append(f"time_threshold_days must be >= 1, got {self.time_threshold_days}")
        
        if self.data_threshold_games < 10:
            errors.append(f"data_threshold_games must be >= 10, got {self.data_threshold_games}")
        
        if self.schedule not in ['weekly', 'monthly', 'daily'] and not self.schedule.startswith('cron:'):
            errors.append(f"Invalid schedule: {self.schedule}")
        
        if self.schedule_hour < 0 or self.schedule_hour > 23:
            errors.append(f"schedule_hour must be 0-23, got {self.schedule_hour}")
        
        if errors:
            for error in errors:
                logger.error(f"Config validation error: {error}")
            return False
        
        return True


class RetrainConfigManager:
    """Manages retrain configuration persistence.
    
    Example:
        >>> manager = RetrainConfigManager()
        >>> config = manager.get_config()
        >>> config.accuracy_threshold = 0.65
        >>> manager.save_config(config)
    """
    
    DEFAULT_PATH = Path("config/retrain_settings.json")
    
    def __init__(self, config_path: str = None):
        """Initialize config manager.
        
        Args:
            config_path: Path to config file
        """
        self.config_path = Path(config_path) if config_path else self.DEFAULT_PATH
        self.config: Optional[RetrainConfig] = None
    
    def get_config(self) -> RetrainConfig:
        """Get current configuration.
        
        Returns:
            RetrainConfig instance
        """
        if self.config is None:
            self.load_config()
        
        return self.config
    
    def load_config(self) -> RetrainConfig:
        """Load configuration from file.
        
        Returns:
            RetrainConfig instance
        """
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                self.config = RetrainConfig.from_dict(data)
                logger.info(f"Loaded retrain config from {self.config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config: {e}")
                self.config = RetrainConfig()
        else:
            self.config = RetrainConfig()
        
        return self.config
    
    def save_config(self, config: RetrainConfig = None) -> bool:
        """Save configuration to file.
        
        Args:
            config: Configuration to save (uses current if not provided)
            
        Returns:
            True if saved successfully
        """
        config = config or self.config
        
        if config is None:
            logger.error("No configuration to save")
            return False
        
        if not config.validate():
            logger.error("Invalid configuration, not saving")
            return False
        
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                json.dump(config.to_dict(), f, indent=2)
            
            self.config = config
            logger.info(f"Saved retrain config to {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False
    
    def update_config(self, **kwargs) -> RetrainConfig:
        """Update specific config values.
        
        Args:
            **kwargs: Config values to update
            
        Returns:
            Updated config
        """
        config = self.get_config()
        
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
            else:
                logger.warning(f"Unknown config key: {key}")
        
        self.save_config(config)
        return config
    
    def reset_to_defaults(self) -> RetrainConfig:
        """Reset configuration to defaults.
        
        Returns:
            Default config
        """
        self.config = RetrainConfig()
        self.save_config()
        return self.config


# Global configuration instance
_config_manager = None


def get_retrain_config() -> RetrainConfig:
    """Get the global retrain configuration.
    
    Returns:
        RetrainConfig instance
    """
    global _config_manager
    
    if _config_manager is None:
        _config_manager = RetrainConfigManager()
    
    return _config_manager.get_config()


def save_retrain_config(config: RetrainConfig) -> bool:
    """Save retrain configuration.
    
    Args:
        config: Configuration to save
        
    Returns:
        True if successful
    """
    global _config_manager
    
    if _config_manager is None:
        _config_manager = RetrainConfigManager()
    
    return _config_manager.save_config(config)
