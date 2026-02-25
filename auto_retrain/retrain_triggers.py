"""Retraining Triggers Module.

Defines and monitors triggers for automatic retraining.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json

from utils.logger import get_logger

logger = get_logger(__name__)


class TriggerType(Enum):
    """Types of retraining triggers."""
    ACCURACY = "accuracy"  # Accuracy drops below threshold
    TIME = "time"  # N days since last training
    DATA = "data"  # N new games accumulated
    DEGRADATION = "degradation"  # Model degradation detected
    MANUAL = "manual"  # User-requested


@dataclass
class TriggerConfig:
    """Configuration for a single trigger."""
    trigger_type: TriggerType
    enabled: bool = True
    threshold: float = 0.0
    interval_days: int = 7
    data_count: int = 100
    last_triggered: Optional[datetime] = None
    description: str = ""


@dataclass
class TriggerEvent:
    """Record of a trigger event."""
    timestamp: datetime
    trigger_type: TriggerType
    reason: str
    current_value: Any
    threshold_value: Any
    action_taken: str = ""


class RetrainTriggerManager:
    """Manages retraining triggers.
    
    Monitors various conditions and triggers retraining when needed:
    - Accuracy below threshold
    - Time since last training
    - New data accumulated
    - Model degradation detected
    
    Example:
        >>> manager = RetrainTriggerManager(config)
        >>> if manager.should_retrain():
        >>>     trigger = manager.get_triggered()
        >>>     retrain_model()
    """
    
    def __init__(
        self,
        accuracy_threshold: float = 0.62,
        time_threshold_days: int = 7,
        data_threshold: int = 100,
        db_manager=None
    ):
        """Initialize trigger manager.
        
        Args:
            accuracy_threshold: Minimum accuracy before retrain
            time_threshold_days: Days before time-based retrain
            data_threshold: New games before data-based retrain
            db_manager: Optional database manager
        """
        self.db = db_manager
        
        # Initialize triggers
        self.triggers: Dict[TriggerType, TriggerConfig] = {
            TriggerType.ACCURACY: TriggerConfig(
                trigger_type=TriggerType.ACCURACY,
                threshold=accuracy_threshold,
                description="Retrain when accuracy drops below threshold"
            ),
            TriggerType.TIME: TriggerConfig(
                trigger_type=TriggerType.TIME,
                interval_days=time_threshold_days,
                description=f"Retrain every {time_threshold_days} days"
            ),
            TriggerType.DATA: TriggerConfig(
                trigger_type=TriggerType.DATA,
                data_count=data_threshold,
                description=f"Retrain when {data_threshold} new games available"
            ),
            TriggerType.DEGRADATION: TriggerConfig(
                trigger_type=TriggerType.DEGRADATION,
                description="Retrain when model degradation detected"
            ),
            TriggerType.MANUAL: TriggerConfig(
                trigger_type=TriggerType.MANUAL,
                description="Manual retraining request"
            )
        }
        
        self.events: List[TriggerEvent] = []
        self.last_training_time: Optional[datetime] = None
        self.games_since_training: int = 0
        self.current_accuracy: float = 0.65
        self.degradation_detected: bool = False
        self.manual_trigger_requested: bool = False
    
    def configure_trigger(
        self,
        trigger_type: TriggerType,
        enabled: bool = None,
        threshold: float = None,
        interval_days: int = None,
        data_count: int = None
    ) -> None:
        """Configure a specific trigger.
        
        Args:
            trigger_type: Type of trigger to configure
            enabled: Whether trigger is enabled
            threshold: Threshold value (for accuracy)
            interval_days: Days interval (for time)
            data_count: Game count (for data)
        """
        if trigger_type not in self.triggers:
            return
        
        config = self.triggers[trigger_type]
        
        if enabled is not None:
            config.enabled = enabled
        if threshold is not None:
            config.threshold = threshold
        if interval_days is not None:
            config.interval_days = interval_days
        if data_count is not None:
            config.data_count = data_count
        
        logger.info(f"Configured trigger {trigger_type.value}")
    
    def update_metrics(
        self,
        accuracy: float = None,
        new_games: int = 0,
        degradation: bool = False
    ) -> None:
        """Update current metrics.
        
        Args:
            accuracy: Current model accuracy
            new_games: Number of new games since last update
            degradation: Whether degradation was detected
        """
        if accuracy is not None:
            self.current_accuracy = accuracy
        
        self.games_since_training += new_games
        self.degradation_detected = degradation
    
    def request_manual_retrain(self) -> None:
        """Request manual retraining."""
        self.manual_trigger_requested = True
        logger.info("Manual retraining requested")
    
    def check_accuracy_trigger(self) -> Optional[TriggerEvent]:
        """Check if accuracy trigger should fire.
        
        Returns:
            TriggerEvent if triggered, None otherwise
        """
        config = self.triggers[TriggerType.ACCURACY]
        
        if not config.enabled:
            return None
        
        if self.current_accuracy < config.threshold:
            event = TriggerEvent(
                timestamp=datetime.now(),
                trigger_type=TriggerType.ACCURACY,
                reason=f"Accuracy {self.current_accuracy:.2%} below threshold {config.threshold:.2%}",
                current_value=self.current_accuracy,
                threshold_value=config.threshold
            )
            self.events.append(event)
            return event
        
        return None
    
    def check_time_trigger(self) -> Optional[TriggerEvent]:
        """Check if time trigger should fire.
        
        Returns:
            TriggerEvent if triggered, None otherwise
        """
        config = self.triggers[TriggerType.TIME]
        
        if not config.enabled:
            return None
        
        if self.last_training_time is None:
            return None
        
        days_since = (datetime.now() - self.last_training_time).days
        
        if days_since >= config.interval_days:
            event = TriggerEvent(
                timestamp=datetime.now(),
                trigger_type=TriggerType.TIME,
                reason=f"{days_since} days since last training (threshold: {config.interval_days})",
                current_value=days_since,
                threshold_value=config.interval_days
            )
            self.events.append(event)
            return event
        
        return None
    
    def check_data_trigger(self) -> Optional[TriggerEvent]:
        """Check if data trigger should fire.
        
        Returns:
            TriggerEvent if triggered, None otherwise
        """
        config = self.triggers[TriggerType.DATA]
        
        if not config.enabled:
            return None
        
        if self.games_since_training >= config.data_count:
            event = TriggerEvent(
                timestamp=datetime.now(),
                trigger_type=TriggerType.DATA,
                reason=f"{self.games_since_training} new games (threshold: {config.data_count})",
                current_value=self.games_since_training,
                threshold_value=config.data_count
            )
            self.events.append(event)
            return event
        
        return None
    
    def check_degradation_trigger(self) -> Optional[TriggerEvent]:
        """Check if degradation trigger should fire.
        
        Returns:
            TriggerEvent if triggered, None otherwise
        """
        config = self.triggers[TriggerType.DEGRADATION]
        
        if not config.enabled:
            return None
        
        if self.degradation_detected:
            event = TriggerEvent(
                timestamp=datetime.now(),
                trigger_type=TriggerType.DEGRADATION,
                reason="Model degradation detected by monitoring system",
                current_value=True,
                threshold_value=False
            )
            self.events.append(event)
            return event
        
        return None
    
    def check_manual_trigger(self) -> Optional[TriggerEvent]:
        """Check if manual trigger is active.
        
        Returns:
            TriggerEvent if triggered, None otherwise
        """
        if self.manual_trigger_requested:
            event = TriggerEvent(
                timestamp=datetime.now(),
                trigger_type=TriggerType.MANUAL,
                reason="Manual retraining requested by user",
                current_value=True,
                threshold_value=None
            )
            self.events.append(event)
            self.manual_trigger_requested = False
            return event
        
        return None
    
    def check_all_triggers(self) -> List[TriggerEvent]:
        """Check all triggers.
        
        Returns:
            List of triggered events
        """
        triggered = []
        
        checks = [
            self.check_manual_trigger,
            self.check_degradation_trigger,
            self.check_accuracy_trigger,
            self.check_time_trigger,
            self.check_data_trigger
        ]
        
        for check in checks:
            event = check()
            if event:
                triggered.append(event)
        
        return triggered
    
    def should_retrain(self) -> bool:
        """Check if any trigger indicates retraining is needed.
        
        Returns:
            True if retraining should occur
        """
        triggered = self.check_all_triggers()
        return len(triggered) > 0
    
    def get_trigger_priority(self) -> Optional[TriggerEvent]:
        """Get the highest priority trigger.
        
        Priority order: Manual > Degradation > Accuracy > Time > Data
        
        Returns:
            Highest priority trigger event or None
        """
        triggered = self.check_all_triggers()
        
        if not triggered:
            return None
        
        # Priority order
        priority = [
            TriggerType.MANUAL,
            TriggerType.DEGRADATION,
            TriggerType.ACCURACY,
            TriggerType.TIME,
            TriggerType.DATA
        ]
        
        for p in priority:
            for event in triggered:
                if event.trigger_type == p:
                    return event
        
        return triggered[0]
    
    def mark_training_complete(self) -> None:
        """Mark that training has completed."""
        self.last_training_time = datetime.now()
        self.games_since_training = 0
        self.degradation_detected = False
        self.manual_trigger_requested = False
        
        # Update last triggered for all triggers
        for config in self.triggers.values():
            config.last_triggered = datetime.now()
        
        logger.info("Training completed, triggers reset")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current trigger status.
        
        Returns:
            Dict with trigger status information
        """
        status = {
            'last_training': self.last_training_time.isoformat() if self.last_training_time else None,
            'games_since_training': self.games_since_training,
            'current_accuracy': self.current_accuracy,
            'degradation_detected': self.degradation_detected,
            'manual_requested': self.manual_trigger_requested,
            'triggers': {}
        }
        
        for trigger_type, config in self.triggers.items():
            status['triggers'][trigger_type.value] = {
                'enabled': config.enabled,
                'threshold': config.threshold,
                'interval_days': config.interval_days,
                'data_count': config.data_count,
                'last_triggered': config.last_triggered.isoformat() if config.last_triggered else None
            }
        
        return status
    
    def save_config(self, path: str) -> None:
        """Save trigger configuration to file.
        
        Args:
            path: File path
        """
        config = {
            'triggers': {
                t.value: {
                    'enabled': c.enabled,
                    'threshold': c.threshold,
                    'interval_days': c.interval_days,
                    'data_count': c.data_count
                }
                for t, c in self.triggers.items()
            },
            'last_training': self.last_training_time.isoformat() if self.last_training_time else None,
            'games_since_training': self.games_since_training
        }
        
        with open(path, 'w') as f:
            json.dump(config, f, indent=2)
    
    def load_config(self, path: str) -> None:
        """Load trigger configuration from file.
        
        Args:
            path: File path
        """
        try:
            with open(path, 'r') as f:
                config = json.load(f)
            
            for trigger_name, settings in config.get('triggers', {}).items():
                trigger_type = TriggerType(trigger_name)
                if trigger_type in self.triggers:
                    self.configure_trigger(
                        trigger_type,
                        enabled=settings.get('enabled'),
                        threshold=settings.get('threshold'),
                        interval_days=settings.get('interval_days'),
                        data_count=settings.get('data_count')
                    )
            
            if config.get('last_training'):
                self.last_training_time = datetime.fromisoformat(config['last_training'])
            
            self.games_since_training = config.get('games_since_training', 0)
            
            logger.info("Loaded trigger configuration")
            
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
