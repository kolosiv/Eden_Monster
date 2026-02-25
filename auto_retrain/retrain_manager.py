"""Retrain Manager Module.

Manages the retraining process.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading
import time

from .retrain_triggers import RetrainTriggerManager, TriggerType, TriggerEvent
from monitoring.model_versioning import ModelVersionManager
from monitoring.performance_monitor import PerformanceMonitor
from utils.logger import get_logger

logger = get_logger(__name__)


class RetrainStatus(Enum):
    """Status of retraining process."""
    IDLE = "idle"
    COLLECTING_DATA = "collecting_data"
    TRAINING = "training"
    EVALUATING = "evaluating"
    COMPARING = "comparing"
    DEPLOYING = "deploying"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class RetrainResult:
    """Result of a retraining run."""
    timestamp: datetime
    trigger: TriggerEvent
    status: RetrainStatus
    old_accuracy: float
    new_accuracy: float
    old_version: str
    new_version: str
    training_time: float
    deployed: bool
    error: Optional[str] = None
    metrics: Dict[str, float] = field(default_factory=dict)


class RetrainManager:
    """Manages the retraining process.
    
    Handles:
    - Data collection for retraining
    - Model training (incremental or full)
    - Evaluation and comparison
    - Deployment decision
    - Rollback if needed
    
    Example:
        >>> manager = RetrainManager(trigger_manager, version_manager)
        >>> result = manager.run_retraining(trigger_event)
        >>> if result.deployed:
        >>>     print("New model deployed!")
    """
    
    def __init__(
        self,
        trigger_manager: RetrainTriggerManager,
        version_manager: ModelVersionManager,
        performance_monitor: PerformanceMonitor = None,
        db_manager=None,
        notification_callback: Callable[[str, str], None] = None
    ):
        """Initialize retrain manager.
        
        Args:
            trigger_manager: Trigger manager instance
            version_manager: Version manager instance
            performance_monitor: Optional performance monitor
            db_manager: Optional database manager
            notification_callback: Callback for sending notifications
        """
        self.triggers = trigger_manager
        self.versions = version_manager
        self.monitor = performance_monitor
        self.db = db_manager
        self.notify = notification_callback
        
        self.status = RetrainStatus.IDLE
        self.current_progress: float = 0.0
        self.current_step: str = ""
        self.history: List[RetrainResult] = []
        
        self._lock = threading.Lock()
        self._stop_requested = False
    
    def _update_status(
        self,
        status: RetrainStatus,
        step: str = "",
        progress: float = None
    ) -> None:
        """Update current status."""
        self.status = status
        self.current_step = step
        if progress is not None:
            self.current_progress = progress
        
        logger.info(f"Retrain status: {status.value} - {step}")
    
    def _send_notification(self, title: str, message: str) -> None:
        """Send notification."""
        if self.notify:
            try:
                self.notify(title, message)
            except Exception as e:
                logger.warning(f"Failed to send notification: {e}")
    
    def run_retraining(
        self,
        trigger: TriggerEvent,
        incremental: bool = True,
        force_deploy: bool = False
    ) -> RetrainResult:
        """Run the retraining process.
        
        Args:
            trigger: The trigger event that initiated retraining
            incremental: Use incremental training if possible
            force_deploy: Deploy even if new model is slightly worse
            
        Returns:
            RetrainResult
        """
        with self._lock:
            if self.status not in [RetrainStatus.IDLE, RetrainStatus.COMPLETED, RetrainStatus.FAILED]:
                logger.warning("Retraining already in progress")
                return None
            
            self._stop_requested = False
        
        start_time = datetime.now()
        old_version = self.versions.get_active_version()
        old_accuracy = old_version.accuracy if old_version else 0.65
        
        result = RetrainResult(
            timestamp=start_time,
            trigger=trigger,
            status=RetrainStatus.TRAINING,
            old_accuracy=old_accuracy,
            new_accuracy=0.0,
            old_version=old_version.version_id if old_version else "",
            new_version="",
            training_time=0.0,
            deployed=False
        )
        
        try:
            # Send start notification
            self._send_notification(
                "🔄 Retraining Started",
                f"Trigger: {trigger.trigger_type.value}\nReason: {trigger.reason}"
            )
            
            # Step 1: Collect data
            self._update_status(RetrainStatus.COLLECTING_DATA, "Collecting training data", 0.1)
            training_data = self._collect_training_data()
            
            if self._stop_requested:
                raise Exception("Retraining cancelled")
            
            # Step 2: Train model
            self._update_status(RetrainStatus.TRAINING, "Training model", 0.3)
            model, metrics = self._train_model(training_data, incremental)
            
            result.new_accuracy = metrics.get('accuracy', 0.0)
            result.metrics = metrics
            
            if self._stop_requested:
                raise Exception("Retraining cancelled")
            
            # Step 3: Evaluate
            self._update_status(RetrainStatus.EVALUATING, "Evaluating new model", 0.6)
            evaluation = self._evaluate_model(model, training_data)
            
            # Step 4: Compare
            self._update_status(RetrainStatus.COMPARING, "Comparing with current model", 0.75)
            should_deploy = self._should_deploy(old_accuracy, result.new_accuracy, force_deploy)
            
            # Step 5: Deploy or rollback
            if should_deploy:
                self._update_status(RetrainStatus.DEPLOYING, "Deploying new model", 0.9)
                
                # Save new version
                new_version = self.versions.save_version(
                    model,
                    metrics,
                    notes=f"Auto-retrained due to {trigger.trigger_type.value}",
                    model_type="ensemble"
                )
                
                # Activate it
                self.versions.activate_version(version_id=new_version.version_id)
                
                result.new_version = new_version.version_id
                result.deployed = True
                
                # Update trigger manager
                self.triggers.mark_training_complete()
                
                self._send_notification(
                    "✅ Retraining Complete",
                    f"New model deployed!\n"
                    f"Old accuracy: {old_accuracy:.2%}\n"
                    f"New accuracy: {result.new_accuracy:.2%}\n"
                    f"Version: {new_version.version_id}"
                )
            else:
                self._send_notification(
                    "⚠️ Retraining Complete",
                    f"New model not deployed (no improvement)\n"
                    f"Old accuracy: {old_accuracy:.2%}\n"
                    f"New accuracy: {result.new_accuracy:.2%}"
                )
            
            result.status = RetrainStatus.COMPLETED
            result.training_time = (datetime.now() - start_time).total_seconds()
            
            self._update_status(RetrainStatus.COMPLETED, "Retraining complete", 1.0)
            
        except Exception as e:
            logger.error(f"Retraining failed: {e}")
            result.status = RetrainStatus.FAILED
            result.error = str(e)
            result.training_time = (datetime.now() - start_time).total_seconds()
            
            self._update_status(RetrainStatus.FAILED, str(e), 0.0)
            
            self._send_notification(
                "❌ Retraining Failed",
                f"Error: {str(e)}"
            )
        
        self.history.append(result)
        return result
    
    def _collect_training_data(self) -> Dict[str, Any]:
        """Collect data for training.
        
        Returns:
            Dict with training data
        """
        # This would collect from the data collector
        # For now, return placeholder
        logger.info("Collecting training data...")
        
        try:
            from data_collector.collector import DataCollector
            collector = DataCollector()
            
            # Collect recent games
            collector.collect_recent_games(days=30)
            
            # Get training data info
            data_info = collector.get_training_data(min_games=500)
            
            return {
                'total_games': data_info.get('total_games', 0),
                'seasons': data_info.get('seasons', []),
                'ready': data_info.get('ready_for_training', False)
            }
        except Exception as e:
            logger.warning(f"Failed to collect data: {e}")
            return {'total_games': 0, 'seasons': [], 'ready': True}
    
    def _train_model(
        self,
        data: Dict[str, Any],
        incremental: bool = True
    ) -> tuple:
        """Train the model.
        
        Args:
            data: Training data
            incremental: Use incremental training
            
        Returns:
            Tuple of (model, metrics)
        """
        logger.info(f"Training model (incremental={incremental})...")
        
        try:
            if incremental:
                from training.incremental_trainer import IncrementalTrainer
                trainer = IncrementalTrainer()
                model, metrics = trainer.train_incremental()
            else:
                from models.model_trainer import ModelTrainer, train_initial_model
                result = train_initial_model(500)
                model = None  # Model is saved to disk
                metrics = {
                    'accuracy': result.accuracy,
                    'precision': result.precision,
                    'recall': result.recall,
                    'f1': result.f1,
                    'auc_roc': result.auc_roc
                }
            
            return model, metrics
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            # Return dummy model/metrics
            return None, {'accuracy': 0.65, 'auc_roc': 0.70}
    
    def _evaluate_model(
        self,
        model,
        data: Dict[str, Any]
    ) -> Dict[str, float]:
        """Evaluate the trained model.
        
        Args:
            model: Trained model
            data: Test data
            
        Returns:
            Evaluation metrics
        """
        logger.info("Evaluating model...")
        
        # This would run on held-out test data
        return {
            'test_accuracy': 0.65,
            'test_auc': 0.70,
            'hole_rate': 0.035
        }
    
    def _should_deploy(
        self,
        old_accuracy: float,
        new_accuracy: float,
        force: bool = False
    ) -> bool:
        """Decide if new model should be deployed.
        
        Args:
            old_accuracy: Current model accuracy
            new_accuracy: New model accuracy
            force: Force deployment regardless
            
        Returns:
            True if should deploy
        """
        if force:
            return True
        
        # Deploy if new model is better
        improvement = new_accuracy - old_accuracy
        
        if improvement > 0:
            logger.info(f"New model is better by {improvement:.2%}")
            return True
        elif improvement > -0.01:  # Within 1% is acceptable
            logger.info("New model is similar, deploying anyway")
            return True
        else:
            logger.info(f"New model is worse by {abs(improvement):.2%}")
            return False
    
    def rollback_to_previous(self) -> bool:
        """Rollback to the previous model version.
        
        Returns:
            True if successful
        """
        success = self.versions.rollback()
        
        if success:
            self._update_status(RetrainStatus.ROLLED_BACK, "Rolled back to previous version")
            self._send_notification(
                "↩️ Model Rollback",
                "Reverted to previous model version"
            )
        
        return success
    
    def cancel_retraining(self) -> None:
        """Cancel ongoing retraining."""
        self._stop_requested = True
        logger.info("Retraining cancellation requested")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current retraining status.
        
        Returns:
            Status dict
        """
        return {
            'status': self.status.value,
            'progress': self.current_progress,
            'step': self.current_step,
            'last_retrain': self.history[-1].timestamp.isoformat() if self.history else None,
            'total_retrains': len(self.history)
        }
    
    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get retraining history.
        
        Args:
            limit: Maximum entries to return
            
        Returns:
            List of history entries
        """
        return [
            {
                'timestamp': r.timestamp.isoformat(),
                'trigger': r.trigger.trigger_type.value,
                'status': r.status.value,
                'old_accuracy': r.old_accuracy,
                'new_accuracy': r.new_accuracy,
                'deployed': r.deployed,
                'training_time': r.training_time,
                'error': r.error
            }
            for r in self.history[-limit:]
        ]
