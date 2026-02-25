"""Model Degradation Detector Module.

Detects when model performance is degrading.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from .performance_monitor import PerformanceMonitor, PerformanceMetrics
from utils.logger import get_logger

logger = get_logger(__name__)


class DegradationType(Enum):
    """Types of model degradation."""
    ACCURACY_DROP = "accuracy_drop"
    CALIBRATION_DRIFT = "calibration_drift"
    CONCEPT_DRIFT = "concept_drift"
    PREDICTION_BIAS = "prediction_bias"
    HOLE_INCREASE = "hole_increase"


@dataclass
class DegradationAlert:
    """Alert for model degradation."""
    timestamp: datetime
    degradation_type: DegradationType
    severity: str  # "low", "medium", "high"
    current_value: float
    baseline_value: float
    threshold: float
    message: str
    recommend_retrain: bool = False


@dataclass
class DegradationConfig:
    """Configuration for degradation detection."""
    # Accuracy thresholds
    accuracy_drop_threshold: float = 0.05  # 5% drop
    accuracy_critical_threshold: float = 0.10  # 10% drop
    baseline_accuracy: float = 0.65  # Expected baseline
    
    # Calibration thresholds
    brier_score_threshold: float = 0.30
    calibration_deviation: float = 0.10
    
    # Hole risk thresholds
    hole_rate_threshold: float = 0.05  # 5% hole rate
    hole_rate_critical: float = 0.08  # 8% hole rate
    
    # Minimum samples for detection
    min_samples: int = 50
    
    # Detection windows
    short_window: int = 50
    long_window: int = 200
    
    # Significance level for statistical tests
    significance_level: float = 0.05


class DegradationDetector:
    """Detects model performance degradation.
    
    Monitors for:
    - Accuracy drops
    - Calibration drift
    - Concept drift
    - Prediction bias
    - Increased hole rates
    
    Example:
        >>> detector = DegradationDetector(monitor)
        >>> alerts = detector.check_degradation()
        >>> if alerts:
        >>>     detector.recommend_action(alerts)
    """
    
    def __init__(
        self,
        monitor: PerformanceMonitor,
        config: Optional[DegradationConfig] = None
    ):
        """Initialize degradation detector.
        
        Args:
            monitor: Performance monitor instance
            config: Detection configuration
        """
        self.monitor = monitor
        self.config = config or DegradationConfig()
        self.alerts: List[DegradationAlert] = []
        self.baseline_metrics: Optional[PerformanceMetrics] = None
    
    def set_baseline(
        self,
        metrics: Optional[PerformanceMetrics] = None
    ) -> None:
        """Set baseline metrics for comparison.
        
        Args:
            metrics: Baseline metrics (uses long window if not provided)
        """
        if metrics:
            self.baseline_metrics = metrics
        else:
            self.baseline_metrics = self.monitor.get_rolling_metrics(
                self.config.long_window
            )
        
        logger.info(f"Baseline set: accuracy={self.baseline_metrics.accuracy:.3f}")
    
    def check_accuracy_drop(self) -> Optional[DegradationAlert]:
        """Check for accuracy degradation.
        
        Returns:
            Alert if degradation detected, None otherwise
        """
        current = self.monitor.get_rolling_metrics(self.config.short_window)
        
        if current.total_predictions < self.config.min_samples:
            return None
        
        baseline_acc = (
            self.baseline_metrics.accuracy if self.baseline_metrics
            else self.config.baseline_accuracy
        )
        
        accuracy_drop = baseline_acc - current.accuracy
        
        if accuracy_drop >= self.config.accuracy_critical_threshold:
            return DegradationAlert(
                timestamp=datetime.now(),
                degradation_type=DegradationType.ACCURACY_DROP,
                severity="high",
                current_value=current.accuracy,
                baseline_value=baseline_acc,
                threshold=self.config.accuracy_critical_threshold,
                message=f"Critical accuracy drop: {accuracy_drop:.2%} below baseline",
                recommend_retrain=True
            )
        elif accuracy_drop >= self.config.accuracy_drop_threshold:
            return DegradationAlert(
                timestamp=datetime.now(),
                degradation_type=DegradationType.ACCURACY_DROP,
                severity="medium",
                current_value=current.accuracy,
                baseline_value=baseline_acc,
                threshold=self.config.accuracy_drop_threshold,
                message=f"Accuracy drop detected: {accuracy_drop:.2%} below baseline",
                recommend_retrain=accuracy_drop >= self.config.accuracy_drop_threshold * 1.5
            )
        
        return None
    
    def check_calibration_drift(self) -> Optional[DegradationAlert]:
        """Check for calibration drift (Brier score increase).
        
        Returns:
            Alert if drift detected, None otherwise
        """
        current = self.monitor.get_rolling_metrics(self.config.short_window)
        
        if current.total_predictions < self.config.min_samples:
            return None
        
        if current.brier_score > self.config.brier_score_threshold:
            return DegradationAlert(
                timestamp=datetime.now(),
                degradation_type=DegradationType.CALIBRATION_DRIFT,
                severity="medium" if current.brier_score < 0.35 else "high",
                current_value=current.brier_score,
                baseline_value=0.25,  # Expected for well-calibrated model
                threshold=self.config.brier_score_threshold,
                message=f"Calibration drift: Brier score {current.brier_score:.3f}",
                recommend_retrain=current.brier_score > 0.35
            )
        
        return None
    
    def check_hole_rate_increase(self) -> Optional[DegradationAlert]:
        """Check for increased hole rate.
        
        Returns:
            Alert if hole rate is too high, None otherwise
        """
        completed = [
            p for p in list(self.monitor.predictions)[-self.config.short_window:]
            if p.actual_hole is not None
        ]
        
        if len(completed) < self.config.min_samples:
            return None
        
        # Calculate hole rate
        total_holes = sum(1 for p in completed if p.actual_hole)
        hole_rate = total_holes / len(completed)
        
        if hole_rate >= self.config.hole_rate_critical:
            return DegradationAlert(
                timestamp=datetime.now(),
                degradation_type=DegradationType.HOLE_INCREASE,
                severity="high",
                current_value=hole_rate,
                baseline_value=0.038,  # Expected ~3.8%
                threshold=self.config.hole_rate_critical,
                message=f"Critical hole rate: {hole_rate:.2%} of predictions resulted in holes",
                recommend_retrain=True
            )
        elif hole_rate >= self.config.hole_rate_threshold:
            return DegradationAlert(
                timestamp=datetime.now(),
                degradation_type=DegradationType.HOLE_INCREASE,
                severity="medium",
                current_value=hole_rate,
                baseline_value=0.038,
                threshold=self.config.hole_rate_threshold,
                message=f"Elevated hole rate: {hole_rate:.2%}",
                recommend_retrain=False
            )
        
        return None
    
    def check_prediction_bias(self) -> Optional[DegradationAlert]:
        """Check for prediction bias (always predicting one class).
        
        Returns:
            Alert if bias detected, None otherwise
        """
        recent = list(self.monitor.predictions)[-self.config.short_window:]
        
        if len(recent) < self.config.min_samples:
            return None
        
        # Calculate prediction distribution
        ot_predictions = sum(1 for p in recent if p.predicted_ot_prob > 0.5)
        ot_rate = ot_predictions / len(recent)
        
        # Expected OT rate is around 20-25%
        expected_ot_rate = 0.23
        
        # Check for significant deviation
        deviation = abs(ot_rate - expected_ot_rate)
        
        if deviation > 0.15:  # More than 15% deviation
            return DegradationAlert(
                timestamp=datetime.now(),
                degradation_type=DegradationType.PREDICTION_BIAS,
                severity="medium",
                current_value=ot_rate,
                baseline_value=expected_ot_rate,
                threshold=0.15,
                message=f"Prediction bias detected: {ot_rate:.2%} OT predictions vs expected {expected_ot_rate:.2%}",
                recommend_retrain=deviation > 0.20
            )
        
        return None
    
    def check_concept_drift(
        self,
        window1_size: int = None,
        window2_size: int = None
    ) -> Optional[DegradationAlert]:
        """Check for concept drift using statistical test.
        
        Compares recent performance to older performance using
        a simple proportion test.
        
        Args:
            window1_size: Recent window size
            window2_size: Older window size
            
        Returns:
            Alert if drift detected, None otherwise
        """
        window1_size = window1_size or self.config.short_window
        window2_size = window2_size or self.config.long_window
        
        completed = [
            p for p in self.monitor.predictions
            if p.actual_went_ot is not None
        ]
        
        if len(completed) < window1_size + window2_size:
            return None
        
        # Split into recent and older
        recent = completed[-window1_size:]
        older = completed[-(window1_size + window2_size):-window1_size]
        
        # Calculate accuracies
        recent_correct = sum(
            1 for p in recent
            if (p.predicted_ot_prob > 0.5) == p.actual_went_ot
        )
        older_correct = sum(
            1 for p in older
            if (p.predicted_ot_prob > 0.5) == p.actual_went_ot
        )
        
        recent_acc = recent_correct / len(recent)
        older_acc = older_correct / len(older)
        
        # Simple proportion test
        pooled = (recent_correct + older_correct) / (len(recent) + len(older))
        se = np.sqrt(pooled * (1 - pooled) * (1/len(recent) + 1/len(older)))
        
        if se > 0:
            z_score = abs(recent_acc - older_acc) / se
        else:
            z_score = 0
        
        # z > 1.96 suggests significant difference at 0.05 level
        if z_score > 2.576:  # 0.01 significance
            return DegradationAlert(
                timestamp=datetime.now(),
                degradation_type=DegradationType.CONCEPT_DRIFT,
                severity="high",
                current_value=recent_acc,
                baseline_value=older_acc,
                threshold=2.576,
                message=f"Concept drift detected: accuracy changed from {older_acc:.2%} to {recent_acc:.2%} (z={z_score:.2f})",
                recommend_retrain=True
            )
        elif z_score > 1.96:  # 0.05 significance
            return DegradationAlert(
                timestamp=datetime.now(),
                degradation_type=DegradationType.CONCEPT_DRIFT,
                severity="medium",
                current_value=recent_acc,
                baseline_value=older_acc,
                threshold=1.96,
                message=f"Potential concept drift: accuracy changed from {older_acc:.2%} to {recent_acc:.2%} (z={z_score:.2f})",
                recommend_retrain=False
            )
        
        return None
    
    def check_all(self) -> List[DegradationAlert]:
        """Run all degradation checks.
        
        Returns:
            List of alerts (empty if no degradation)
        """
        checks = [
            self.check_accuracy_drop,
            self.check_calibration_drift,
            self.check_hole_rate_increase,
            self.check_prediction_bias,
            self.check_concept_drift
        ]
        
        alerts = []
        for check in checks:
            alert = check()
            if alert:
                alerts.append(alert)
                self.alerts.append(alert)
        
        if alerts:
            logger.warning(f"Detected {len(alerts)} degradation alert(s)")
        
        return alerts
    
    def should_retrain(self, alerts: List[DegradationAlert] = None) -> bool:
        """Determine if model should be retrained.
        
        Args:
            alerts: List of alerts to consider
            
        Returns:
            True if retraining is recommended
        """
        alerts = alerts or self.alerts
        
        # Any high severity alert recommends retrain
        high_severity = [a for a in alerts if a.severity == "high"]
        if high_severity:
            return True
        
        # Multiple medium severity alerts recommend retrain
        medium_severity = [a for a in alerts if a.severity == "medium"]
        if len(medium_severity) >= 2:
            return True
        
        # Explicit retrain recommendation
        if any(a.recommend_retrain for a in alerts):
            return True
        
        return False
    
    def recommend_action(
        self,
        alerts: List[DegradationAlert] = None
    ) -> Dict[str, Any]:
        """Recommend action based on alerts.
        
        Args:
            alerts: List of alerts to consider
            
        Returns:
            Dict with recommended actions
        """
        alerts = alerts or self.alerts
        
        if not alerts:
            return {
                'action': 'none',
                'message': 'No degradation detected',
                'retrain': False
            }
        
        should_retrain = self.should_retrain(alerts)
        
        # Determine priority action
        high_alerts = [a for a in alerts if a.severity == "high"]
        
        if high_alerts:
            primary_issue = high_alerts[0].degradation_type.value
        else:
            primary_issue = alerts[0].degradation_type.value
        
        return {
            'action': 'retrain' if should_retrain else 'monitor',
            'message': f"Primary issue: {primary_issue}",
            'retrain': should_retrain,
            'urgency': 'high' if high_alerts else 'medium',
            'alerts_count': len(alerts),
            'issues': [a.degradation_type.value for a in alerts]
        }
    
    def clear_alerts(self) -> None:
        """Clear all alerts."""
        self.alerts = []
