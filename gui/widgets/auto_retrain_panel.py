"""Auto Retrain Panel Widget.

GUI panel for managing automatic retraining.
"""

from datetime import datetime
from typing import Optional, Dict, Any

from utils.logger import get_logger

logger = get_logger(__name__)

# Try importing PyQt6
try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
        QLabel, QPushButton, QSpinBox, QDoubleSpinBox,
        QCheckBox, QComboBox, QTableWidget, QTableWidgetItem,
        QProgressBar, QTextEdit, QSplitter, QFrame,
        QHeaderView, QMessageBox
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal
    from PyQt6.QtGui import QColor, QFont
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    logger.warning("PyQt6 not available for auto retrain panel")


if PYQT6_AVAILABLE:
    class AutoRetrainPanel(QWidget):
        """Panel for managing automatic model retraining.
        
        Features:
        - Enable/disable auto-retraining
        - Configure triggers and thresholds
        - View retraining history
        - Trigger manual retraining
        - Monitor current status
        - Rollback to previous version
        """
        
        retrain_requested = pyqtSignal(bool)  # incremental flag
        rollback_requested = pyqtSignal()
        config_changed = pyqtSignal(dict)
        
        def __init__(self, parent=None):
            """Initialize auto retrain panel.
            
            Args:
                parent: Parent widget
            """
            super().__init__(parent)
            
            self.retrain_manager = None
            self.trigger_manager = None
            self.version_manager = None
            
            self._setup_ui()
            self._setup_refresh_timer()
        
        def _setup_ui(self):
            """Set up the UI components."""
            layout = QVBoxLayout(self)
            layout.setSpacing(10)
            
            # Header with status
            header = self._create_header()
            layout.addWidget(header)
            
            # Main content splitter
            splitter = QSplitter(Qt.Orientation.Horizontal)
            
            # Left side: Configuration
            config_widget = self._create_config_section()
            splitter.addWidget(config_widget)
            
            # Right side: Status and history
            status_widget = self._create_status_section()
            splitter.addWidget(status_widget)
            
            splitter.setSizes([400, 600])
            layout.addWidget(splitter)
            
            # Bottom: Actions and progress
            actions = self._create_actions_section()
            layout.addWidget(actions)
        
        def _create_header(self) -> QGroupBox:
            """Create header section with current status."""
            group = QGroupBox("Auto-Retrain Status")
            layout = QHBoxLayout(group)
            
            # Status indicator
            self.status_label = QLabel("● Idle")
            self.status_label.setStyleSheet("color: #4CAF50; font-size: 14px; font-weight: bold;")
            layout.addWidget(self.status_label)
            
            layout.addStretch()
            
            # Current model version
            layout.addWidget(QLabel("Current Model:"))
            self.version_label = QLabel("v1")
            self.version_label.setStyleSheet("color: #2196F3; font-weight: bold;")
            layout.addWidget(self.version_label)
            
            layout.addStretch()
            
            # Last retrain time
            layout.addWidget(QLabel("Last Retrain:"))
            self.last_retrain_label = QLabel("Never")
            layout.addWidget(self.last_retrain_label)
            
            layout.addStretch()
            
            # Next scheduled
            layout.addWidget(QLabel("Next Scheduled:"))
            self.next_scheduled_label = QLabel("-")
            layout.addWidget(self.next_scheduled_label)
            
            return group
        
        def _create_config_section(self) -> QWidget:
            """Create configuration section."""
            widget = QWidget()
            layout = QVBoxLayout(widget)
            
            # Enable/Disable
            enable_group = QGroupBox("Auto-Retrain")
            enable_layout = QVBoxLayout(enable_group)
            
            self.enable_checkbox = QCheckBox("Enable Automatic Retraining")
            self.enable_checkbox.setChecked(True)
            self.enable_checkbox.stateChanged.connect(self._on_config_changed)
            enable_layout.addWidget(self.enable_checkbox)
            
            layout.addWidget(enable_group)
            
            # Triggers configuration
            triggers_group = QGroupBox("Triggers")
            triggers_layout = QVBoxLayout(triggers_group)
            
            # Accuracy threshold
            acc_layout = QHBoxLayout()
            acc_layout.addWidget(QLabel("Accuracy Threshold:"))
            self.accuracy_spin = QDoubleSpinBox()
            self.accuracy_spin.setRange(0.50, 0.80)
            self.accuracy_spin.setSingleStep(0.01)
            self.accuracy_spin.setValue(0.62)
            self.accuracy_spin.valueChanged.connect(self._on_config_changed)
            acc_layout.addWidget(self.accuracy_spin)
            acc_layout.addWidget(QLabel("%"))
            triggers_layout.addLayout(acc_layout)
            
            # Time threshold
            time_layout = QHBoxLayout()
            time_layout.addWidget(QLabel("Time Threshold:"))
            self.time_spin = QSpinBox()
            self.time_spin.setRange(1, 30)
            self.time_spin.setValue(7)
            self.time_spin.valueChanged.connect(self._on_config_changed)
            time_layout.addWidget(self.time_spin)
            time_layout.addWidget(QLabel("days"))
            triggers_layout.addLayout(time_layout)
            
            # Data threshold
            data_layout = QHBoxLayout()
            data_layout.addWidget(QLabel("Data Threshold:"))
            self.data_spin = QSpinBox()
            self.data_spin.setRange(10, 500)
            self.data_spin.setValue(100)
            self.data_spin.valueChanged.connect(self._on_config_changed)
            data_layout.addWidget(self.data_spin)
            data_layout.addWidget(QLabel("games"))
            triggers_layout.addLayout(data_layout)
            
            layout.addWidget(triggers_group)
            
            # Schedule configuration
            schedule_group = QGroupBox("Schedule")
            schedule_layout = QVBoxLayout(schedule_group)
            
            sched_layout = QHBoxLayout()
            sched_layout.addWidget(QLabel("Frequency:"))
            self.schedule_combo = QComboBox()
            self.schedule_combo.addItems(["Weekly", "Daily", "Monthly"])
            self.schedule_combo.currentIndexChanged.connect(self._on_config_changed)
            sched_layout.addWidget(self.schedule_combo)
            schedule_layout.addLayout(sched_layout)
            
            day_layout = QHBoxLayout()
            day_layout.addWidget(QLabel("Day:"))
            self.day_combo = QComboBox()
            self.day_combo.addItems(["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"])
            self.day_combo.currentIndexChanged.connect(self._on_config_changed)
            day_layout.addWidget(self.day_combo)
            schedule_layout.addLayout(day_layout)
            
            hour_layout = QHBoxLayout()
            hour_layout.addWidget(QLabel("Hour:"))
            self.hour_spin = QSpinBox()
            self.hour_spin.setRange(0, 23)
            self.hour_spin.setValue(3)
            self.hour_spin.valueChanged.connect(self._on_config_changed)
            hour_layout.addWidget(self.hour_spin)
            hour_layout.addWidget(QLabel(":00"))
            schedule_layout.addLayout(hour_layout)
            
            layout.addWidget(schedule_group)
            
            # Options
            options_group = QGroupBox("Options")
            options_layout = QVBoxLayout(options_group)
            
            self.incremental_checkbox = QCheckBox("Use Incremental Training")
            self.incremental_checkbox.setChecked(True)
            self.incremental_checkbox.stateChanged.connect(self._on_config_changed)
            options_layout.addWidget(self.incremental_checkbox)
            
            self.notify_checkbox = QCheckBox("Send Notifications")
            self.notify_checkbox.setChecked(True)
            self.notify_checkbox.stateChanged.connect(self._on_config_changed)
            options_layout.addWidget(self.notify_checkbox)
            
            self.rollback_checkbox = QCheckBox("Auto-Rollback if Worse")
            self.rollback_checkbox.setChecked(True)
            self.rollback_checkbox.stateChanged.connect(self._on_config_changed)
            options_layout.addWidget(self.rollback_checkbox)
            
            layout.addWidget(options_group)
            
            layout.addStretch()
            
            return widget
        
        def _create_status_section(self) -> QWidget:
            """Create status and history section."""
            widget = QWidget()
            layout = QVBoxLayout(widget)
            
            # Performance chart placeholder
            perf_group = QGroupBox("Model Performance")
            perf_layout = QVBoxLayout(perf_group)
            
            self.perf_label = QLabel("Accuracy trend will appear here")
            self.perf_label.setStyleSheet("color: #888; padding: 40px;")
            self.perf_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            perf_layout.addWidget(self.perf_label)
            
            # Metrics
            metrics_layout = QHBoxLayout()
            
            self.accuracy_display = QLabel("Accuracy: --")
            metrics_layout.addWidget(self.accuracy_display)
            
            self.auc_display = QLabel("AUC: --")
            metrics_layout.addWidget(self.auc_display)
            
            self.hole_display = QLabel("Hole Rate: --")
            metrics_layout.addWidget(self.hole_display)
            
            perf_layout.addLayout(metrics_layout)
            
            layout.addWidget(perf_group)
            
            # Retraining history
            history_group = QGroupBox("Retraining History")
            history_layout = QVBoxLayout(history_group)
            
            self.history_table = QTableWidget()
            self.history_table.setColumnCount(6)
            self.history_table.setHorizontalHeaderLabels([
                "Date", "Trigger", "Old Acc", "New Acc", "Status", "Deployed"
            ])
            self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            self.history_table.setAlternatingRowColors(True)
            history_layout.addWidget(self.history_table)
            
            layout.addWidget(history_group)
            
            # Logs
            logs_group = QGroupBox("Recent Logs")
            logs_layout = QVBoxLayout(logs_group)
            
            self.logs_text = QTextEdit()
            self.logs_text.setReadOnly(True)
            self.logs_text.setMaximumHeight(100)
            self.logs_text.setStyleSheet("font-family: monospace; font-size: 11px;")
            logs_layout.addWidget(self.logs_text)
            
            layout.addWidget(logs_group)
            
            return widget
        
        def _create_actions_section(self) -> QWidget:
            """Create actions section with buttons and progress."""
            widget = QWidget()
            layout = QVBoxLayout(widget)
            
            # Progress bar
            self.progress_bar = QProgressBar()
            self.progress_bar.setVisible(False)
            layout.addWidget(self.progress_bar)
            
            # Progress label
            self.progress_label = QLabel("")
            self.progress_label.setVisible(False)
            layout.addWidget(self.progress_label)
            
            # Buttons
            buttons_layout = QHBoxLayout()
            
            self.retrain_btn = QPushButton("🔄 Retrain Now")
            self.retrain_btn.clicked.connect(self._on_retrain_clicked)
            self.retrain_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """)
            buttons_layout.addWidget(self.retrain_btn)
            
            self.full_retrain_btn = QPushButton("🔄 Full Retrain")
            self.full_retrain_btn.clicked.connect(self._on_full_retrain_clicked)
            buttons_layout.addWidget(self.full_retrain_btn)
            
            buttons_layout.addStretch()
            
            self.rollback_btn = QPushButton("↩️ Rollback")
            self.rollback_btn.clicked.connect(self._on_rollback_clicked)
            buttons_layout.addWidget(self.rollback_btn)
            
            self.save_config_btn = QPushButton("💾 Save Config")
            self.save_config_btn.clicked.connect(self._on_save_config)
            buttons_layout.addWidget(self.save_config_btn)
            
            layout.addLayout(buttons_layout)
            
            return widget
        
        def _setup_refresh_timer(self):
            """Set up timer for refreshing status."""
            self.refresh_timer = QTimer(self)
            self.refresh_timer.timeout.connect(self._refresh_status)
            self.refresh_timer.start(5000)  # Refresh every 5 seconds
        
        def set_managers(
            self,
            retrain_manager=None,
            trigger_manager=None,
            version_manager=None
        ):
            """Set the manager instances.
            
            Args:
                retrain_manager: RetrainManager instance
                trigger_manager: RetrainTriggerManager instance
                version_manager: ModelVersionManager instance
            """
            self.retrain_manager = retrain_manager
            self.trigger_manager = trigger_manager
            self.version_manager = version_manager
            
            self._refresh_status()
        
        def _refresh_status(self):
            """Refresh displayed status."""
            if self.retrain_manager:
                status = self.retrain_manager.get_status()
                
                # Update status label
                status_text = status.get('status', 'idle')
                if status_text == 'idle':
                    self.status_label.setText("● Idle")
                    self.status_label.setStyleSheet("color: #4CAF50; font-size: 14px; font-weight: bold;")
                elif status_text == 'training':
                    self.status_label.setText("● Training...")
                    self.status_label.setStyleSheet("color: #FF9800; font-size: 14px; font-weight: bold;")
                elif status_text == 'failed':
                    self.status_label.setText("● Failed")
                    self.status_label.setStyleSheet("color: #F44336; font-size: 14px; font-weight: bold;")
                
                # Update progress
                progress = status.get('progress', 0)
                if progress > 0 and progress < 1:
                    self.progress_bar.setVisible(True)
                    self.progress_bar.setValue(int(progress * 100))
                    self.progress_label.setVisible(True)
                    self.progress_label.setText(status.get('step', ''))
                else:
                    self.progress_bar.setVisible(False)
                    self.progress_label.setVisible(False)
                
                # Update history
                history = self.retrain_manager.get_history(10)
                self._update_history_table(history)
            
            if self.version_manager:
                active = self.version_manager.get_active_version()
                if active:
                    self.version_label.setText(f"v{active.version_number}")
                    self.accuracy_display.setText(f"Accuracy: {active.accuracy:.1%}")
                    self.auc_display.setText(f"AUC: {active.auc_roc:.3f}")
                    self.hole_display.setText(f"Hole Rate: {active.hole_rate:.1%}")
        
        def _update_history_table(self, history: list):
            """Update the history table with recent retrains."""
            self.history_table.setRowCount(len(history))
            
            for i, entry in enumerate(history):
                self.history_table.setItem(i, 0, QTableWidgetItem(
                    entry.get('timestamp', '')[:10]
                ))
                self.history_table.setItem(i, 1, QTableWidgetItem(
                    entry.get('trigger', '')
                ))
                self.history_table.setItem(i, 2, QTableWidgetItem(
                    f"{entry.get('old_accuracy', 0):.1%}"
                ))
                self.history_table.setItem(i, 3, QTableWidgetItem(
                    f"{entry.get('new_accuracy', 0):.1%}"
                ))
                
                status_item = QTableWidgetItem(entry.get('status', ''))
                if entry.get('status') == 'completed':
                    status_item.setForeground(QColor('#4CAF50'))
                elif entry.get('status') == 'failed':
                    status_item.setForeground(QColor('#F44336'))
                self.history_table.setItem(i, 4, status_item)
                
                deployed = "✓" if entry.get('deployed') else "✗"
                self.history_table.setItem(i, 5, QTableWidgetItem(deployed))
        
        def _on_config_changed(self):
            """Handle configuration change."""
            config = self._get_current_config()
            self.config_changed.emit(config)
        
        def _get_current_config(self) -> Dict[str, Any]:
            """Get current configuration from UI."""
            return {
                'enabled': self.enable_checkbox.isChecked(),
                'accuracy_threshold': self.accuracy_spin.value(),
                'time_threshold_days': self.time_spin.value(),
                'data_threshold_games': self.data_spin.value(),
                'schedule': self.schedule_combo.currentText().lower(),
                'schedule_day': self.day_combo.currentText().lower(),
                'schedule_hour': self.hour_spin.value(),
                'use_incremental': self.incremental_checkbox.isChecked(),
                'notification_enabled': self.notify_checkbox.isChecked(),
                'rollback_on_worse': self.rollback_checkbox.isChecked()
            }
        
        def _on_retrain_clicked(self):
            """Handle retrain button click."""
            reply = QMessageBox.question(
                self,
                "Confirm Retraining",
                "Start incremental model retraining?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.retrain_requested.emit(True)  # incremental
                self._add_log("Incremental retraining requested")
        
        def _on_full_retrain_clicked(self):
            """Handle full retrain button click."""
            reply = QMessageBox.question(
                self,
                "Confirm Full Retraining",
                "Start full model retraining? This may take longer.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.retrain_requested.emit(False)  # not incremental
                self._add_log("Full retraining requested")
        
        def _on_rollback_clicked(self):
            """Handle rollback button click."""
            reply = QMessageBox.question(
                self,
                "Confirm Rollback",
                "Rollback to the previous model version?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.rollback_requested.emit()
                self._add_log("Rollback requested")
        
        def _on_save_config(self):
            """Save current configuration."""
            config = self._get_current_config()
            self._add_log(f"Configuration saved")
            
            QMessageBox.information(
                self,
                "Configuration Saved",
                "Retrain configuration has been saved."
            )
        
        def _add_log(self, message: str):
            """Add a log message."""
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.logs_text.append(f"[{timestamp}] {message}")


else:
    # Fallback when PyQt6 is not available
    class AutoRetrainPanel:
        def __init__(self, *args, **kwargs):
            raise ImportError("PyQt6 required for AutoRetrainPanel")
