"""Model Management Panel for Eden MVP GUI.

Provides interface for managing ML models, training, and evaluation.
"""

from typing import Dict, Optional, Any
from datetime import datetime

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
        QLabel, QPushButton, QProgressBar, QComboBox,
        QTextEdit, QTableWidget, QTableWidgetItem,
        QSpinBox, QDoubleSpinBox, QCheckBox, QTabWidget,
        QMessageBox, QHeaderView
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
    from PyQt6.QtGui import QColor
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

from utils.logger import get_logger

logger = get_logger(__name__)


if PYQT_AVAILABLE:
    
    class DataCollectionWorker(QThread):
        """Worker thread for data collection."""
        progress = pyqtSignal(str, int)
        finished = pyqtSignal(dict)
        error = pyqtSignal(str)
        
        def __init__(self, seasons=None):
            super().__init__()
            self.seasons = seasons
        
        def run(self):
            try:
                from data_collector import DataCollector
                collector = DataCollector()
                
                self.progress.emit("Initializing...", 0)
                collector.storage.initialize()
                
                total = 0
                for i, season in enumerate(self.seasons or ["20232024", "20242025"]):
                    self.progress.emit(f"Collecting {season}...", int((i / 2) * 100))
                    count = collector.collect_season(season)
                    total += count
                
                self.progress.emit("Complete", 100)
                self.finished.emit({'games_collected': total})
                
            except Exception as e:
                self.error.emit(str(e))
    
    
    class TrainingWorker(QThread):
        """Worker thread for model training."""
        progress = pyqtSignal(str, int)
        finished = pyqtSignal(dict)
        error = pyqtSignal(str)
        
        def run(self):
            try:
                from data_collector import DataStorage
                from features import FeatureEngineer
                from training import EnhancedModelTrainer
                
                storage = DataStorage()
                storage.initialize()
                
                self.progress.emit("Loading data...", 10)
                
                # Get games
                all_games = []
                for season in ["20232024", "20242025"]:
                    games = storage.get_games_for_season(season)
                    all_games.extend(games)
                
                if len(all_games) < 100:
                    self.error.emit(f"Insufficient data: {len(all_games)} games")
                    return
                
                self.progress.emit("Extracting features...", 30)
                
                engineer = FeatureEngineer(storage)
                X, y, _ = engineer.extract_training_data(all_games)
                
                self.progress.emit("Training models...", 50)
                
                trainer = EnhancedModelTrainer()
                results = trainer.train_all(X, y)
                
                self.progress.emit("Saving model...", 90)
                
                trainer.save_best_model()
                
                self.progress.emit("Complete", 100)
                
                result_data = {
                    'best_model': trainer.best_model_name,
                    'accuracy': results[trainer.best_model_name].accuracy,
                    'auc_roc': results[trainer.best_model_name].auc_roc,
                    'training_samples': len(X)
                }
                self.finished.emit(result_data)
                
            except Exception as e:
                logger.error(f"Training error: {e}")
                self.error.emit(str(e))
    
    
    class ModelManagementPanel(QWidget):
        """Panel for managing ML models.
        
        Features:
        - View current model status
        - Collect new data from NHL API
        - Train/retrain models
        - View model performance metrics
        - Compare ML vs Poisson models
        - A/B testing results
        """
        
        def __init__(self, parent=None):
            super().__init__(parent)
            self._setup_ui()
            self._load_status()
            
            # Workers
            self.collection_worker = None
            self.training_worker = None
        
        def _setup_ui(self):
            """Set up the UI."""
            layout = QVBoxLayout(self)
            
            # Tab widget for different sections
            tabs = QTabWidget()
            
            # Status tab
            status_tab = self._create_status_tab()
            tabs.addTab(status_tab, "Model Status")
            
            # Data collection tab
            data_tab = self._create_data_tab()
            tabs.addTab(data_tab, "Data Collection")
            
            # Training tab
            training_tab = self._create_training_tab()
            tabs.addTab(training_tab, "Training")
            
            # Comparison tab
            comparison_tab = self._create_comparison_tab()
            tabs.addTab(comparison_tab, "Model Comparison")
            
            layout.addWidget(tabs)
        
        def _create_status_tab(self) -> QWidget:
            """Create model status tab."""
            widget = QWidget()
            layout = QVBoxLayout(widget)
            
            # Current model info
            model_group = QGroupBox("Current Model")
            model_layout = QVBoxLayout(model_group)
            
            self.model_status_label = QLabel("Loading...")
            self.model_version_label = QLabel("")
            self.model_accuracy_label = QLabel("")
            self.model_auc_label = QLabel("")
            
            model_layout.addWidget(self.model_status_label)
            model_layout.addWidget(self.model_version_label)
            model_layout.addWidget(self.model_accuracy_label)
            model_layout.addWidget(self.model_auc_label)
            
            layout.addWidget(model_group)
            
            # Feature importance
            importance_group = QGroupBox("Top Features")
            importance_layout = QVBoxLayout(importance_group)
            
            self.importance_table = QTableWidget()
            self.importance_table.setColumnCount(2)
            self.importance_table.setHorizontalHeaderLabels(["Feature", "Importance"])
            self.importance_table.horizontalHeader().setStretchLastSection(True)
            
            importance_layout.addWidget(self.importance_table)
            layout.addWidget(importance_group)
            
            # Refresh button
            refresh_btn = QPushButton("Refresh Status")
            refresh_btn.clicked.connect(self._load_status)
            layout.addWidget(refresh_btn)
            
            layout.addStretch()
            return widget
        
        def _create_data_tab(self) -> QWidget:
            """Create data collection tab."""
            widget = QWidget()
            layout = QVBoxLayout(widget)
            
            # Data status
            status_group = QGroupBox("Data Status")
            status_layout = QVBoxLayout(status_group)
            
            self.data_count_label = QLabel("Games in database: Loading...")
            self.data_latest_label = QLabel("Latest game: Loading...")
            
            status_layout.addWidget(self.data_count_label)
            status_layout.addWidget(self.data_latest_label)
            
            layout.addWidget(status_group)
            
            # Collection settings
            settings_group = QGroupBox("Collection Settings")
            settings_layout = QVBoxLayout(settings_group)
            
            season_layout = QHBoxLayout()
            season_layout.addWidget(QLabel("Seasons:"))
            self.season_combo = QComboBox()
            self.season_combo.addItems(["20232024, 20242025", "20242025 only", "Last 7 days"])
            season_layout.addWidget(self.season_combo)
            settings_layout.addLayout(season_layout)
            
            layout.addWidget(settings_group)
            
            # Progress
            self.collection_progress = QProgressBar()
            self.collection_progress.setValue(0)
            layout.addWidget(self.collection_progress)
            
            self.collection_status_label = QLabel("")
            layout.addWidget(self.collection_status_label)
            
            # Buttons
            btn_layout = QHBoxLayout()
            
            self.collect_btn = QPushButton("Collect Data")
            self.collect_btn.clicked.connect(self._start_collection)
            btn_layout.addWidget(self.collect_btn)
            
            layout.addLayout(btn_layout)
            layout.addStretch()
            
            return widget
        
        def _create_training_tab(self) -> QWidget:
            """Create training tab."""
            widget = QWidget()
            layout = QVBoxLayout(widget)
            
            # Training settings
            settings_group = QGroupBox("Training Settings")
            settings_layout = QVBoxLayout(settings_group)
            
            # Models to train
            self.train_rf_check = QCheckBox("RandomForest")
            self.train_rf_check.setChecked(True)
            self.train_xgb_check = QCheckBox("XGBoost")
            self.train_xgb_check.setChecked(True)
            self.train_lgbm_check = QCheckBox("LightGBM")
            self.train_lgbm_check.setChecked(True)
            
            settings_layout.addWidget(self.train_rf_check)
            settings_layout.addWidget(self.train_xgb_check)
            settings_layout.addWidget(self.train_lgbm_check)
            
            # Hyperparameter tuning
            self.hyperparam_check = QCheckBox("Enable hyperparameter tuning")
            self.hyperparam_check.setChecked(True)
            settings_layout.addWidget(self.hyperparam_check)
            
            layout.addWidget(settings_group)
            
            # Progress
            self.training_progress = QProgressBar()
            self.training_progress.setValue(0)
            layout.addWidget(self.training_progress)
            
            self.training_status_label = QLabel("")
            layout.addWidget(self.training_status_label)
            
            # Results
            results_group = QGroupBox("Training Results")
            results_layout = QVBoxLayout(results_group)
            
            self.results_text = QTextEdit()
            self.results_text.setReadOnly(True)
            self.results_text.setMaximumHeight(150)
            results_layout.addWidget(self.results_text)
            
            layout.addWidget(results_group)
            
            # Buttons
            btn_layout = QHBoxLayout()
            
            self.train_btn = QPushButton("Train Models")
            self.train_btn.clicked.connect(self._start_training)
            btn_layout.addWidget(self.train_btn)
            
            layout.addLayout(btn_layout)
            layout.addStretch()
            
            return widget
        
        def _create_comparison_tab(self) -> QWidget:
            """Create model comparison tab."""
            widget = QWidget()
            layout = QVBoxLayout(widget)
            
            # Model selector
            selector_layout = QHBoxLayout()
            selector_layout.addWidget(QLabel("Active Model:"))
            
            self.model_selector = QComboBox()
            self.model_selector.addItems(["ML Ensemble", "ML RandomForest", "Poisson", "Auto"])
            self.model_selector.currentIndexChanged.connect(self._on_model_changed)
            selector_layout.addWidget(self.model_selector)
            
            layout.addLayout(selector_layout)
            
            # Comparison table
            comparison_group = QGroupBox("ML vs Poisson Comparison")
            comparison_layout = QVBoxLayout(comparison_group)
            
            self.comparison_table = QTableWidget()
            self.comparison_table.setColumnCount(3)
            self.comparison_table.setHorizontalHeaderLabels(["Metric", "ML Model", "Poisson"])
            self.comparison_table.setRowCount(5)
            
            metrics = ["Accuracy", "AUC-ROC", "Brier Score", "Avg Hole Pred", "Actual Hole Rate"]
            for i, metric in enumerate(metrics):
                self.comparison_table.setItem(i, 0, QTableWidgetItem(metric))
                self.comparison_table.setItem(i, 1, QTableWidgetItem("-"))
                self.comparison_table.setItem(i, 2, QTableWidgetItem("-"))
            
            comparison_layout.addWidget(self.comparison_table)
            layout.addWidget(comparison_group)
            
            # A/B Test results
            ab_group = QGroupBox("A/B Test Results")
            ab_layout = QVBoxLayout(ab_group)
            
            self.ab_result_label = QLabel("No A/B test data available")
            self.ab_recommendation_label = QLabel("")
            
            ab_layout.addWidget(self.ab_result_label)
            ab_layout.addWidget(self.ab_recommendation_label)
            
            run_ab_btn = QPushButton("Run A/B Analysis")
            run_ab_btn.clicked.connect(self._run_ab_analysis)
            ab_layout.addWidget(run_ab_btn)
            
            layout.addWidget(ab_group)
            
            layout.addStretch()
            return widget
        
        def _load_status(self):
            """Load current model status."""
            try:
                from models.ml_overtime_predictor import EnhancedMLPredictor
                
                predictor = EnhancedMLPredictor()
                
                if predictor.is_loaded:
                    self.model_status_label.setText("✅ Model loaded")
                    self.model_status_label.setStyleSheet("color: green;")
                    self.model_version_label.setText(f"Version: {predictor.model_version}")
                else:
                    self.model_status_label.setText("❌ No model loaded")
                    self.model_status_label.setStyleSheet("color: red;")
                    self.model_version_label.setText("Using Poisson fallback")
                
                # Load data status
                from data_collector import DataStorage
                storage = DataStorage()
                storage.initialize()
                
                count = storage.get_game_count()
                latest = storage.get_latest_game_date()
                
                self.data_count_label.setText(f"Games in database: {count}")
                self.data_latest_label.setText(f"Latest game: {latest or 'None'}")
                
            except Exception as e:
                logger.error(f"Error loading status: {e}")
                self.model_status_label.setText("Error loading status")
        
        def _start_collection(self):
            """Start data collection."""
            self.collect_btn.setEnabled(False)
            self.collection_progress.setValue(0)
            self.collection_status_label.setText("Starting collection...")
            
            # Determine seasons based on selection
            selection = self.season_combo.currentText()
            if "only" in selection:
                seasons = ["20242025"]
            elif "7 days" in selection:
                seasons = None  # Will use recent collection
            else:
                seasons = ["20232024", "20242025"]
            
            self.collection_worker = DataCollectionWorker(seasons)
            self.collection_worker.progress.connect(self._on_collection_progress)
            self.collection_worker.finished.connect(self._on_collection_finished)
            self.collection_worker.error.connect(self._on_collection_error)
            self.collection_worker.start()
        
        def _on_collection_progress(self, status: str, progress: int):
            """Handle collection progress update."""
            self.collection_status_label.setText(status)
            self.collection_progress.setValue(progress)
        
        def _on_collection_finished(self, result: dict):
            """Handle collection completion."""
            self.collect_btn.setEnabled(True)
            self.collection_status_label.setText(
                f"Collection complete: {result.get('games_collected', 0)} games"
            )
            self._load_status()
        
        def _on_collection_error(self, error: str):
            """Handle collection error."""
            self.collect_btn.setEnabled(True)
            self.collection_status_label.setText(f"Error: {error}")
            QMessageBox.warning(self, "Collection Error", error)
        
        def _start_training(self):
            """Start model training."""
            self.train_btn.setEnabled(False)
            self.training_progress.setValue(0)
            self.training_status_label.setText("Starting training...")
            self.results_text.clear()
            
            self.training_worker = TrainingWorker()
            self.training_worker.progress.connect(self._on_training_progress)
            self.training_worker.finished.connect(self._on_training_finished)
            self.training_worker.error.connect(self._on_training_error)
            self.training_worker.start()
        
        def _on_training_progress(self, status: str, progress: int):
            """Handle training progress update."""
            self.training_status_label.setText(status)
            self.training_progress.setValue(progress)
        
        def _on_training_finished(self, result: dict):
            """Handle training completion."""
            self.train_btn.setEnabled(True)
            self.training_status_label.setText("Training complete!")
            
            results_text = f"""
Best Model: {result.get('best_model', 'unknown')}
Accuracy: {result.get('accuracy', 0):.1%}
AUC-ROC: {result.get('auc_roc', 0):.3f}
Training Samples: {result.get('training_samples', 0)}
"""
            self.results_text.setText(results_text)
            self._load_status()
        
        def _on_training_error(self, error: str):
            """Handle training error."""
            self.train_btn.setEnabled(True)
            self.training_status_label.setText(f"Error: {error}")
            QMessageBox.warning(self, "Training Error", error)
        
        def _on_model_changed(self, index: int):
            """Handle model selection change."""
            model_names = ["ensemble", "random_forest", "poisson", "auto"]
            selected = model_names[index]
            logger.info(f"Model selection changed to: {selected}")
            # TODO: Update predictor configuration
        
        def _run_ab_analysis(self):
            """Run A/B test analysis."""
            try:
                from evaluation import ABTester
                
                tester = ABTester()
                result = tester.analyze()
                
                self.ab_result_label.setText(
                    f"Predictions: {result.total_predictions} | "
                    f"ML Accuracy: {result.ml_ot_accuracy:.1%} | "
                    f"Poisson Accuracy: {result.poisson_ot_accuracy:.1%}"
                )
                
                rec_text = f"Recommended: {result.recommended_model.upper()}"
                if result.is_significant:
                    rec_text += " (statistically significant)"
                self.ab_recommendation_label.setText(rec_text)
                
                if result.recommended_model == "ml":
                    self.ab_recommendation_label.setStyleSheet("color: green;")
                else:
                    self.ab_recommendation_label.setStyleSheet("color: orange;")
                
            except Exception as e:
                logger.error(f"A/B analysis error: {e}")
                self.ab_result_label.setText(f"Error: {e}")

else:
    # Fallback if PyQt6 not available
    class ModelManagementPanel:
        def __init__(self, *args, **kwargs):
            raise ImportError("PyQt6 is required for GUI components")
