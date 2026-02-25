"""ML Models Page for Eden Analytics Pro v3.0.0 Monster Edition."""

from typing import Optional, Dict, List
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QScrollArea,
    QFrame, QLabel, QPushButton, QGroupBox, QGridLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QComboBox, QSpinBox, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer

from gui.themes.modern_theme import get_theme
from gui.components.modern_widgets import ModernButton, ModernCard, StatCard, ModernProgressBar
from gui.components.charts import ModelPerformanceChart, GaugeChart, PLOTLY_AVAILABLE

# Import guide system
try:
    from gui.guides.guide_system import GuideButton, GuideOverlay
    from gui.guides.guide_content import ML_MODELS_GUIDE
    from gui.animations.animations import AnimationManager
    GUIDES_AVAILABLE = True
except ImportError:
    GUIDES_AVAILABLE = False


class TrainingWorker(QThread):
    """Worker thread for model training."""
    
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, config: Dict):
        super().__init__()
        self.config = config
    
    def run(self):
        try:
            self.progress.emit(10, "Loading training data...")
            
            # Import training modules
            from data.historical_data_fetcher import HistoricalDataFetcher
            from models.model_trainer import ModelTrainer, TrainingConfig
            
            self.progress.emit(30, "Preparing data...")
            
            fetcher = HistoricalDataFetcher()
            features, labels = fetcher.get_training_data(
                num_matches=self.config.get('num_matches', 1000)
            )
            
            self.progress.emit(50, "Training model...")
            
            config = TrainingConfig(
                n_estimators=self.config.get('n_estimators', 200),
                max_depth=self.config.get('max_depth', 10),
                cv_folds=self.config.get('cv_folds', 5)
            )
            
            trainer = ModelTrainer(config=config)
            X, y = trainer.prepare_data(features, labels)
            
            self.progress.emit(70, "Evaluating model...")
            
            result = trainer.train(X, y)
            
            self.progress.emit(90, "Saving model...")
            
            self.progress.emit(100, "Complete!")
            
            self.finished.emit({
                'accuracy': result.accuracy,
                'precision': result.precision,
                'recall': result.recall,
                'f1': result.f1_score,
                'auc_roc': result.auc_roc,
                'cv_mean': result.cv_mean,
                'cv_std': result.cv_std,
                'feature_importance': result.feature_importances,
                'training_time': result.training_time
            })
            
        except Exception as e:
            self.error.emit(str(e))


class MLModelsPage(QWidget):
    """ML Models management page."""
    
    model_updated = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._training_worker = None
        self._setup_ui()
    
    def _setup_ui(self):
        theme = get_theme()
        p = theme.palette
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)  # Increased margins
        layout.setSpacing(20)
        
        # Header row with guide button
        header_row = QHBoxLayout()
        header_row.setSpacing(20)
        
        header = QLabel("🤖 ML Модели")
        header.setStyleSheet(f"""
            font-size: 32px;
            font-weight: 900;
            color: {p.primary};
            letter-spacing: 0.5px;
        """)
        header_row.addWidget(header)
        header_row.addStretch()
        
        # Guide button
        if GUIDES_AVAILABLE:
            self.guide_btn = GuideButton("❓ Гайд")
            self.guide_btn.clicked.connect(self._show_guide)
            header_row.addWidget(self.guide_btn)
        
        layout.addLayout(header_row)
        
        # Tabs
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {p.border};
                border-radius: 8px;
                background: {p.surface};
            }}
            QTabBar::tab {{
                padding: 10px 20px;
                margin-right: 4px;
                background: {p.surface_light};
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }}
            QTabBar::tab:selected {{
                background: {p.primary};
                color: white;
            }}
        """)
        
        # Tab 1: Model Overview
        tabs.addTab(self._create_overview_tab(), "📊 Overview")
        
        # Tab 2: Training
        tabs.addTab(self._create_training_tab(), "🎓 Training")
        
        # Tab 3: Performance History
        tabs.addTab(self._create_history_tab(), "📈 History")
        
        # Tab 4: Auto-Retrain
        tabs.addTab(self._create_auto_retrain_tab(), "🔄 Auto-Retrain")
        
        layout.addWidget(tabs)
    
    def _create_overview_tab(self) -> QWidget:
        """Create model overview tab."""
        theme = get_theme()
        p = theme.palette
        
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)
        
        # Stats Row
        stats_layout = QHBoxLayout()
        
        self.stat_accuracy = StatCard("Model Accuracy", "N/A", "🎯", color=p.success)
        self.stat_precision = StatCard("Precision", "N/A", "📏", color=p.primary)
        self.stat_recall = StatCard("Recall", "N/A", "🔍", color=p.secondary)
        self.stat_f1 = StatCard("F1 Score", "N/A", "⚡", color=p.warning)
        
        stats_layout.addWidget(self.stat_accuracy)
        stats_layout.addWidget(self.stat_precision)
        stats_layout.addWidget(self.stat_recall)
        stats_layout.addWidget(self.stat_f1)
        
        layout.addLayout(stats_layout)
        
        # Model Info Card
        info_card = ModernCard("Current Model")
        info_layout = QGridLayout()
        
        self.model_version_label = QLabel("Version: Not trained")
        self.model_date_label = QLabel("Last trained: N/A")
        self.model_samples_label = QLabel("Training samples: N/A")
        self.model_features_label = QLabel("Features: 24")
        
        for lbl in [self.model_version_label, self.model_date_label, 
                    self.model_samples_label, self.model_features_label]:
            lbl.setStyleSheet(f"color: {p.text}; font-size: 14px; padding: 8px;")
        
        info_layout.addWidget(self.model_version_label, 0, 0)
        info_layout.addWidget(self.model_date_label, 0, 1)
        info_layout.addWidget(self.model_samples_label, 1, 0)
        info_layout.addWidget(self.model_features_label, 1, 1)
        
        info_card.content_layout.addLayout(info_layout)
        layout.addWidget(info_card)
        
        # Performance Chart
        if PLOTLY_AVAILABLE:
            chart_card = ModernCard("Model Performance")
            self.performance_chart = ModelPerformanceChart()
            chart_card.add_widget(self.performance_chart)
            layout.addWidget(chart_card)
        
        # Feature Importance
        importance_card = ModernCard("Feature Importance (Top 10)")
        self.importance_table = QTableWidget()
        self.importance_table.setColumnCount(2)
        self.importance_table.setHorizontalHeaderLabels(["Feature", "Importance"])
        self.importance_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.importance_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.importance_table.setColumnWidth(1, 150)
        self.importance_table.setAlternatingRowColors(True)
        importance_card.add_widget(self.importance_table)
        layout.addWidget(importance_card)
        
        return tab
    
    def _create_training_tab(self) -> QWidget:
        """Create model training tab."""
        theme = get_theme()
        p = theme.palette
        
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)
        
        # Training Configuration
        config_card = ModernCard("Training Configuration")
        config_layout = QGridLayout()
        
        # Number of samples
        config_layout.addWidget(QLabel("Training Samples:"), 0, 0)
        self.samples_spin = QSpinBox()
        self.samples_spin.setRange(500, 10000)
        self.samples_spin.setValue(2000)
        self.samples_spin.setSingleStep(500)
        config_layout.addWidget(self.samples_spin, 0, 1)
        
        # Number of trees
        config_layout.addWidget(QLabel("Number of Trees:"), 1, 0)
        self.trees_spin = QSpinBox()
        self.trees_spin.setRange(50, 500)
        self.trees_spin.setValue(200)
        self.trees_spin.setSingleStep(50)
        config_layout.addWidget(self.trees_spin, 1, 1)
        
        # Max depth
        config_layout.addWidget(QLabel("Max Depth:"), 2, 0)
        self.depth_spin = QSpinBox()
        self.depth_spin.setRange(3, 20)
        self.depth_spin.setValue(10)
        config_layout.addWidget(self.depth_spin, 2, 1)
        
        # CV folds
        config_layout.addWidget(QLabel("CV Folds:"), 3, 0)
        self.cv_spin = QSpinBox()
        self.cv_spin.setRange(3, 10)
        self.cv_spin.setValue(5)
        config_layout.addWidget(self.cv_spin, 3, 1)
        
        config_card.content_layout.addLayout(config_layout)
        layout.addWidget(config_card)
        
        # Training Progress
        progress_card = ModernCard("Training Progress")
        progress_layout = QVBoxLayout()
        
        self.training_progress = ModernProgressBar()
        self.training_progress.setValue(0)
        progress_layout.addWidget(self.training_progress)
        
        self.training_status = QLabel("Ready to train")
        self.training_status.setStyleSheet(f"color: {p.text_secondary};")
        self.training_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self.training_status)
        
        progress_card.content_layout.addLayout(progress_layout)
        layout.addWidget(progress_card)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.train_btn = ModernButton("🎓 Start Training", primary=True)
        self.train_btn.clicked.connect(self._start_training)
        btn_layout.addWidget(self.train_btn)
        
        self.cancel_btn = ModernButton("❌ Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_training)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
        
        # Results Card
        self.results_card = ModernCard("Training Results")
        self.results_card.setVisible(False)
        
        self.results_layout = QGridLayout()
        self.results_card.content_layout.addLayout(self.results_layout)
        layout.addWidget(self.results_card)
        
        layout.addStretch()
        
        return tab
    
    def _create_history_tab(self) -> QWidget:
        """Create performance history tab."""
        theme = get_theme()
        p = theme.palette
        
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # History Table
        history_card = ModernCard("Model Version History")
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels([
            "Version", "Date", "Accuracy", "F1 Score", "Samples", "Status"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history_table.setAlternatingRowColors(True)
        
        history_card.add_widget(self.history_table)
        layout.addWidget(history_card)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        refresh_btn = ModernButton("🔄 Refresh")
        refresh_btn.clicked.connect(self._load_history)
        btn_layout.addWidget(refresh_btn)
        
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        return tab
    
    def _create_auto_retrain_tab(self) -> QWidget:
        """Create auto-retrain configuration tab."""
        theme = get_theme()
        p = theme.palette
        
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)
        
        # Auto-Retrain Status
        status_card = ModernCard("Auto-Retrain Status")
        status_layout = QHBoxLayout()
        
        self.auto_retrain_status = QLabel("⚪ Disabled")
        self.auto_retrain_status.setStyleSheet(f"font-size: 16px; color: {p.text};")
        status_layout.addWidget(self.auto_retrain_status)
        
        status_layout.addStretch()
        
        self.enable_auto_btn = ModernButton("Enable Auto-Retrain", primary=True)
        self.enable_auto_btn.clicked.connect(self._toggle_auto_retrain)
        status_layout.addWidget(self.enable_auto_btn)
        
        status_card.content_layout.addLayout(status_layout)
        layout.addWidget(status_card)
        
        # Triggers Configuration
        triggers_card = ModernCard("Retrain Triggers")
        triggers_layout = QGridLayout()
        
        # Accuracy threshold
        triggers_layout.addWidget(QLabel("Accuracy drops below:"), 0, 0)
        self.accuracy_threshold = QSpinBox()
        self.accuracy_threshold.setRange(50, 90)
        self.accuracy_threshold.setValue(70)
        self.accuracy_threshold.setSuffix("%")
        triggers_layout.addWidget(self.accuracy_threshold, 0, 1)
        
        # Time-based
        triggers_layout.addWidget(QLabel("Retrain every:"), 1, 0)
        self.retrain_interval = QComboBox()
        self.retrain_interval.addItems(["Never", "Daily", "Weekly", "Monthly"])
        self.retrain_interval.setCurrentIndex(2)
        triggers_layout.addWidget(self.retrain_interval, 1, 1)
        
        # New data threshold
        triggers_layout.addWidget(QLabel("New matches threshold:"), 2, 0)
        self.data_threshold = QSpinBox()
        self.data_threshold.setRange(50, 500)
        self.data_threshold.setValue(100)
        triggers_layout.addWidget(self.data_threshold, 2, 1)
        
        triggers_card.content_layout.addLayout(triggers_layout)
        layout.addWidget(triggers_card)
        
        # Recent Retraining Events
        events_card = ModernCard("Recent Retraining Events")
        self.events_table = QTableWidget()
        self.events_table.setColumnCount(4)
        self.events_table.setHorizontalHeaderLabels([
            "Date", "Trigger", "Old Accuracy", "New Accuracy"
        ])
        self.events_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        events_card.add_widget(self.events_table)
        layout.addWidget(events_card)
        
        layout.addStretch()
        
        return tab
    
    def _start_training(self):
        """Start model training."""
        self.train_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.training_progress.setValue(0)
        self.training_status.setText("Starting training...")
        
        config = {
            'num_matches': self.samples_spin.value(),
            'n_estimators': self.trees_spin.value(),
            'max_depth': self.depth_spin.value(),
            'cv_folds': self.cv_spin.value()
        }
        
        self._training_worker = TrainingWorker(config)
        self._training_worker.progress.connect(self._on_training_progress)
        self._training_worker.finished.connect(self._on_training_finished)
        self._training_worker.error.connect(self._on_training_error)
        self._training_worker.start()
    
    def _cancel_training(self):
        """Cancel training."""
        if self._training_worker and self._training_worker.isRunning():
            self._training_worker.terminate()
            self._training_worker.wait()
        
        self.train_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.training_status.setText("Training cancelled")
    
    def _on_training_progress(self, value: int, message: str):
        """Handle training progress update."""
        self.training_progress.animate_to(value)
        self.training_status.setText(message)
    
    def _on_training_finished(self, result: Dict):
        """Handle training completion."""
        self.train_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.training_status.setText("Training complete!")
        
        # Show results
        self.results_card.setVisible(True)
        
        # Clear previous results
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        theme = get_theme()
        p = theme.palette
        
        metrics = [
            ("Accuracy", f"{result['accuracy']*100:.2f}%"),
            ("Precision", f"{result['precision']*100:.2f}%"),
            ("Recall", f"{result['recall']*100:.2f}%"),
            ("F1 Score", f"{result['f1']*100:.2f}%"),
            ("AUC-ROC", f"{result['auc_roc']:.4f}"),
            ("CV Mean", f"{result['cv_mean']*100:.2f}%"),
            ("Training Time", f"{result['training_time']:.1f}s")
        ]
        
        for i, (name, value) in enumerate(metrics):
            name_label = QLabel(name)
            name_label.setStyleSheet(f"color: {p.text_secondary};")
            value_label = QLabel(value)
            value_label.setStyleSheet(f"color: {p.text}; font-weight: bold;")
            
            self.results_layout.addWidget(name_label, i // 4, (i % 4) * 2)
            self.results_layout.addWidget(value_label, i // 4, (i % 4) * 2 + 1)
        
        # Update overview stats
        self._update_overview(result)
        
        # Emit signal
        self.model_updated.emit()
        
        QMessageBox.information(self, "Training Complete",
            f"Model training completed successfully!\n\n"
            f"Accuracy: {result['accuracy']*100:.2f}%\n"
            f"F1 Score: {result['f1']*100:.2f}%")
    
    def _on_training_error(self, error: str):
        """Handle training error."""
        self.train_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.training_status.setText(f"Error: {error}")
        
        QMessageBox.critical(self, "Training Error", f"Training failed:\n{error}")
    
    def _update_overview(self, result: Dict):
        """Update overview tab with new results."""
        self.stat_accuracy.update_value(f"{result['accuracy']*100:.1f}%")
        self.stat_precision.update_value(f"{result['precision']*100:.1f}%")
        self.stat_recall.update_value(f"{result['recall']*100:.1f}%")
        self.stat_f1.update_value(f"{result['f1']*100:.1f}%")
        
        self.model_version_label.setText(f"Version: {datetime.now().strftime('%Y%m%d_%H%M')}")
        self.model_date_label.setText(f"Last trained: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        self.model_samples_label.setText(f"Training samples: {self.samples_spin.value()}")
        
        # Update feature importance table
        if 'feature_importance' in result:
            importance = result['feature_importance']
            sorted_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:10]
            
            self.importance_table.setRowCount(len(sorted_features))
            for i, (feature, importance) in enumerate(sorted_features):
                self.importance_table.setItem(i, 0, QTableWidgetItem(feature))
                self.importance_table.setItem(i, 1, QTableWidgetItem(f"{importance:.4f}"))
    
    def _load_history(self):
        """Load model version history."""
        # This would load from database
        pass
    
    def _toggle_auto_retrain(self):
        """Toggle auto-retrain feature."""
        theme = get_theme()
        p = theme.palette
        
        if "Disable" in self.enable_auto_btn.text():
            self.auto_retrain_status.setText("⚪ Disabled")
            self.enable_auto_btn.setText("Enable Auto-Retrain")
        else:
            self.auto_retrain_status.setText("🟢 Enabled")
            self.enable_auto_btn.setText("Disable Auto-Retrain")
    
    def _show_guide(self):
        """Show the interactive guide overlay."""
        if not GUIDES_AVAILABLE:
            return
        
        try:
            guide = GuideOverlay(self)
            guide.set_steps(ML_MODELS_GUIDE)
            guide.show()
            guide.resize(self.size())
        except Exception:
            pass  # Guide failures shouldn't break the UI
    
    def load_model_v5_metrics(self):
        """Load and display Model v5.0 metrics."""
        try:
            from models.model_v5_predictor import get_model_v5_predictor
            
            predictor = get_model_v5_predictor()
            metrics = predictor.get_model_metrics()
            
            # Update stats
            self.stat_accuracy.update_value(f"{metrics['accuracy']*100:.1f}%")
            self.stat_precision.update_value(f"{metrics['precision']*100:.1f}%")
            self.stat_recall.update_value(f"{metrics['recall']*100:.1f}%")
            self.stat_f1.update_value(f"{metrics['f1_score']*100:.1f}%")
            
            # Update model info
            self.model_version_label.setText(f"Version: v{metrics['version']} Monster Edition")
            self.model_date_label.setText(f"Last trained: {metrics.get('trained_at', 'N/A')[:10]}")
            self.model_samples_label.setText(f"Training samples: 7,860 games (2019-2026)")
            self.model_features_label.setText(f"Features: {metrics['feature_count']} (incl. 12 injury features)")
            
            # Update feature importance with v5.0 top features
            top_features = [
                ("points_pct_diff", 0.0823),
                ("goal_diff_diff", 0.0756),
                ("ot_game_pct_avg", 0.0689),
                ("recent_form_diff", 0.0634),
                ("special_teams_diff", 0.0598),
                ("combined_offense", 0.0521),
                ("home_injury_impact", 0.0467),
                ("away_injury_impact", 0.0445),
                ("home_ot_win_rate", 0.0412),
                ("scoring_closeness", 0.0389),
            ]
            
            self.importance_table.setRowCount(len(top_features))
            for i, (feature, importance) in enumerate(top_features):
                self.importance_table.setItem(i, 0, QTableWidgetItem(feature))
                self.importance_table.setItem(i, 1, QTableWidgetItem(f"{importance:.4f}"))
            
        except Exception as e:
            print(f"Error loading model v5 metrics: {e}")
    
    def showEvent(self, event):
        """Load model metrics when page is shown."""
        super().showEvent(event)
        self.load_model_v5_metrics()


__all__ = ['MLModelsPage']
