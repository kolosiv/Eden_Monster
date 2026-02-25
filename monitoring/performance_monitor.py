"""Performance Monitor Module.

Monitors model performance in real-time.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import deque
import json

import numpy as np

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PredictionRecord:
    """Record of a single prediction."""
    timestamp: datetime
    match_id: str
    predicted_ot_prob: float
    predicted_hole_prob: float
    actual_went_ot: Optional[bool] = None
    actual_hole: Optional[bool] = None
    confidence: float = 0.0
    model_version: str = ""


@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot."""
    timestamp: datetime
    window_size: int
    accuracy: float
    precision: float
    recall: float
    auc_roc: float
    brier_score: float
    hole_accuracy: float
    avg_confidence: float
    total_predictions: int
    correct_predictions: int


class PerformanceMonitor:
    """Monitors model performance in real-time.
    
    Tracks:
    - Rolling accuracy over different windows
    - Prediction vs actual outcomes
    - Hole risk accuracy
    - Calibration metrics
    
    Example:
        >>> monitor = PerformanceMonitor(db_manager)
        >>> monitor.record_prediction(match_id, ot_prob, hole_prob)
        >>> monitor.record_outcome(match_id, went_ot=True, was_hole=False)
        >>> metrics = monitor.get_current_metrics()
    """
    
    def __init__(
        self,
        db_manager=None,
        max_records: int = 1000
    ):
        """Initialize performance monitor.
        
        Args:
            db_manager: Optional database manager for persistence
            max_records: Maximum records to keep in memory
        """
        self.db = db_manager
        self.max_records = max_records
        
        # In-memory storage
        self.predictions: deque = deque(maxlen=max_records)
        self.metrics_history: List[PerformanceMetrics] = []
        
        # Rolling windows
        self.windows = [50, 100, 200]
    
    def record_prediction(
        self,
        match_id: str,
        ot_prob: float,
        hole_prob: float,
        confidence: float = 0.0,
        model_version: str = ""
    ) -> None:
        """Record a new prediction.
        
        Args:
            match_id: Match identifier
            ot_prob: Predicted OT probability
            hole_prob: Predicted hole probability
            confidence: Prediction confidence
            model_version: Model version used
        """
        record = PredictionRecord(
            timestamp=datetime.now(),
            match_id=match_id,
            predicted_ot_prob=ot_prob,
            predicted_hole_prob=hole_prob,
            confidence=confidence,
            model_version=model_version
        )
        
        self.predictions.append(record)
        logger.debug(f"Recorded prediction for {match_id}: OT={ot_prob:.2%}, Hole={hole_prob:.2%}")
        
        # Save to database if available
        if self.db:
            self._save_prediction_to_db(record)
    
    def record_outcome(
        self,
        match_id: str,
        went_ot: bool,
        was_hole: bool = False
    ) -> bool:
        """Record the actual outcome for a match.
        
        Args:
            match_id: Match identifier
            went_ot: Whether match went to OT
            was_hole: Whether it was a hole (weak team won OT)
            
        Returns:
            True if record was found and updated
        """
        for record in self.predictions:
            if record.match_id == match_id:
                record.actual_went_ot = went_ot
                record.actual_hole = was_hole
                logger.debug(f"Updated outcome for {match_id}: OT={went_ot}, Hole={was_hole}")
                
                # Update database
                if self.db:
                    self._update_outcome_in_db(match_id, went_ot, was_hole)
                
                return True
        
        logger.warning(f"Prediction record not found for {match_id}")
        return False
    
    def get_rolling_metrics(
        self,
        window_size: int = 100
    ) -> PerformanceMetrics:
        """Calculate rolling performance metrics.
        
        Args:
            window_size: Number of recent predictions to consider
            
        Returns:
            PerformanceMetrics for the window
        """
        # Get predictions with outcomes
        completed = [
            p for p in list(self.predictions)[-window_size:]
            if p.actual_went_ot is not None
        ]
        
        if not completed:
            return PerformanceMetrics(
                timestamp=datetime.now(),
                window_size=window_size,
                accuracy=0.0,
                precision=0.0,
                recall=0.0,
                auc_roc=0.5,
                brier_score=0.25,
                hole_accuracy=0.0,
                avg_confidence=0.0,
                total_predictions=0,
                correct_predictions=0
            )
        
        # Calculate metrics
        y_true = [1 if p.actual_went_ot else 0 for p in completed]
        y_pred = [1 if p.predicted_ot_prob > 0.5 else 0 for p in completed]
        y_prob = [p.predicted_ot_prob for p in completed]
        
        # Accuracy
        correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
        accuracy = correct / len(y_true)
        
        # Precision/Recall for OT prediction
        true_positives = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
        predicted_positives = sum(y_pred)
        actual_positives = sum(y_true)
        
        precision = true_positives / predicted_positives if predicted_positives > 0 else 0
        recall = true_positives / actual_positives if actual_positives > 0 else 0
        
        # Brier score
        brier = np.mean([(t - p) ** 2 for t, p in zip(y_true, y_prob)])
        
        # AUC-ROC (approximate)
        try:
            from sklearn.metrics import roc_auc_score
            auc = roc_auc_score(y_true, y_prob)
        except:
            auc = 0.5
        
        # Hole accuracy
        hole_predictions = [
            (p.predicted_hole_prob < 0.04, p.actual_hole)
            for p in completed
            if p.actual_hole is not None
        ]
        if hole_predictions:
            hole_correct = sum(1 for pred_safe, actual in hole_predictions if pred_safe != actual)
            hole_accuracy = 1 - (hole_correct / len(hole_predictions))
        else:
            hole_accuracy = 0.0
        
        # Average confidence
        avg_conf = np.mean([p.confidence for p in completed])
        
        return PerformanceMetrics(
            timestamp=datetime.now(),
            window_size=window_size,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            auc_roc=auc,
            brier_score=brier,
            hole_accuracy=hole_accuracy,
            avg_confidence=avg_conf,
            total_predictions=len(completed),
            correct_predictions=correct
        )
    
    def get_all_rolling_metrics(self) -> Dict[int, PerformanceMetrics]:
        """Get metrics for all configured windows.
        
        Returns:
            Dict mapping window size to metrics
        """
        return {
            window: self.get_rolling_metrics(window)
            for window in self.windows
        }
    
    def get_trend(
        self,
        metric: str = 'accuracy',
        window: int = 100,
        periods: int = 10
    ) -> List[float]:
        """Get trend of a metric over time.
        
        Args:
            metric: Metric name to track
            window: Window size for each point
            periods: Number of periods to calculate
            
        Returns:
            List of metric values over time
        """
        completed = [
            p for p in self.predictions
            if p.actual_went_ot is not None
        ]
        
        if len(completed) < window:
            return []
        
        trend = []
        step = max(1, len(completed) // periods)
        
        for i in range(0, len(completed) - window + 1, step):
            subset = completed[i:i + window]
            
            if metric == 'accuracy':
                correct = sum(
                    1 for p in subset
                    if (p.predicted_ot_prob > 0.5) == p.actual_went_ot
                )
                trend.append(correct / len(subset))
            elif metric == 'hole_rate':
                holes = sum(1 for p in subset if p.actual_hole)
                trend.append(holes / len(subset))
        
        return trend
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive performance report.
        
        Returns:
            Dict with report data
        """
        all_metrics = self.get_all_rolling_metrics()
        
        completed = [
            p for p in self.predictions
            if p.actual_went_ot is not None
        ]
        
        # Calculate overall statistics
        total_predictions = len(self.predictions)
        completed_predictions = len(completed)
        pending_predictions = total_predictions - completed_predictions
        
        # Hole statistics
        total_holes = sum(1 for p in completed if p.actual_hole)
        predicted_safe = sum(
            1 for p in completed
            if p.predicted_hole_prob < 0.04
        )
        holes_in_safe = sum(
            1 for p in completed
            if p.predicted_hole_prob < 0.04 and p.actual_hole
        )
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_predictions': total_predictions,
                'completed': completed_predictions,
                'pending': pending_predictions,
                'total_holes': total_holes,
                'hole_rate': total_holes / completed_predictions if completed_predictions else 0
            },
            'rolling_metrics': {
                str(k): {
                    'accuracy': v.accuracy,
                    'precision': v.precision,
                    'recall': v.recall,
                    'auc_roc': v.auc_roc,
                    'brier_score': v.brier_score,
                    'hole_accuracy': v.hole_accuracy
                }
                for k, v in all_metrics.items()
            },
            'hole_analysis': {
                'predicted_safe': predicted_safe,
                'holes_in_safe': holes_in_safe,
                'safe_accuracy': 1 - (holes_in_safe / predicted_safe) if predicted_safe else 0
            },
            'trends': {
                'accuracy': self.get_trend('accuracy', 50, 10),
                'hole_rate': self.get_trend('hole_rate', 50, 10)
            }
        }
        
        return report
    
    def _save_prediction_to_db(self, record: PredictionRecord) -> None:
        """Save prediction to database."""
        if not self.db:
            return
        
        try:
            self.db.insert_model_performance({
                'timestamp': record.timestamp.isoformat(),
                'match_id': record.match_id,
                'predicted_ot_prob': record.predicted_ot_prob,
                'predicted_hole_prob': record.predicted_hole_prob,
                'confidence': record.confidence,
                'model_version': record.model_version
            })
        except Exception as e:
            logger.warning(f"Failed to save prediction to DB: {e}")
    
    def _update_outcome_in_db(self, match_id: str, went_ot: bool, was_hole: bool) -> None:
        """Update outcome in database."""
        if not self.db:
            return
        
        try:
            self.db.update_model_performance_outcome(
                match_id, went_ot, was_hole
            )
        except Exception as e:
            logger.warning(f"Failed to update outcome in DB: {e}")
    
    def load_from_db(self, days: int = 30) -> None:
        """Load recent predictions from database.
        
        Args:
            days: Number of days of history to load
        """
        if not self.db:
            return
        
        try:
            start_date = (datetime.now() - timedelta(days=days)).isoformat()
            records = self.db.get_model_performance_history(start_date=start_date)
            
            for r in records:
                self.predictions.append(PredictionRecord(
                    timestamp=datetime.fromisoformat(r['timestamp']),
                    match_id=r['match_id'],
                    predicted_ot_prob=r['predicted_ot_prob'],
                    predicted_hole_prob=r['predicted_hole_prob'],
                    actual_went_ot=r.get('actual_went_ot'),
                    actual_hole=r.get('actual_hole'),
                    confidence=r.get('confidence', 0),
                    model_version=r.get('model_version', '')
                ))
            
            logger.info(f"Loaded {len(records)} predictions from database")
        except Exception as e:
            logger.warning(f"Failed to load predictions from DB: {e}")
