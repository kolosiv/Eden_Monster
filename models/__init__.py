"""Models Module for Eden MVP v3.1.0 Monster Edition - Trust & Reliability.

Includes overtime prediction models and ML components.
v3.1.0: Added ReliableModelTrainer with all critical fixes.
"""

from .overtime_predictor import OvertimePredictor, OTPrediction, TeamStats
from .overtime_predictor_ml import OvertimePredictorML, MLOTPrediction, MLTeamStats
from .ml_overtime_predictor import EnhancedMLPredictor, MLPredictionResult
from .model_v5_predictor import ModelV5Predictor, ModelV5Prediction, get_model_v5_predictor

# v3.1.0: Import reliable trainer
try:
    from .model_trainer_v3 import (
        ReliableModelTrainer,
        TrainingConfigV3,
        TrainingResultV3
    )
    RELIABLE_TRAINER_AVAILABLE = True
except ImportError:
    RELIABLE_TRAINER_AVAILABLE = False
    ReliableModelTrainer = None

__all__ = [
    'OvertimePredictor', 'OTPrediction', 'TeamStats',
    'OvertimePredictorML', 'MLOTPrediction', 'MLTeamStats',
    'EnhancedMLPredictor', 'MLPredictionResult',
    'ModelV5Predictor', 'ModelV5Prediction', 'get_model_v5_predictor',
    # v3.1.0 additions
    'ReliableModelTrainer', 'TrainingConfigV3', 'TrainingResultV3',
    'RELIABLE_TRAINER_AVAILABLE'
]
