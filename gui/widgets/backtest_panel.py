"""Backtest Panel Widget for Eden MVP GUI."""

from typing import Optional
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QGroupBox, QPushButton, QSpinBox, QDoubleSpinBox,
    QCheckBox, QProgressBar, QTextEdit, QMessageBox, QFileDialog,
    QScrollArea, QComboBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from backtest.backtester import Backtester, BacktestConfig, BacktestResult
from backtest.report_generator import ReportGenerator
from analysis.stake_calculator import StakingStrategy


class BacktestWorker(QThread):
    """Worker thread for running backtest."""
    
    progress = pyqtSignal(str)
    finished = pyqtSignal(object)  # BacktestResult
    error = pyqtSignal(str)
    
    def __init__(self, config: BacktestConfig):
        super().__init__()
        self.config = config
    
    def run(self):
        try:
            self.progress.emit("Initializing backtester...")
            backtester = Backtester(self.config)
            
            self.progress.emit("Generating historical data...")
            result = backtester.run(verbose=False)
            
            self.progress.emit("Backtest complete!")
            self.finished.emit(result)
            
        except Exception as e:
            self.error.emit(str(e))


class BacktestPanelWidget(QWidget):
    """Panel widget for backtesting configuration and results."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_result: Optional[BacktestResult] = None
        self.worker: Optional[BacktestWorker] = None
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI components."""
        main_layout = QVBoxLayout(self)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content = QWidget()
        layout = QVBoxLayout(content)
        
        # Title
        title = QLabel("Backtesting")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #00d9ff;")
        layout.addWidget(title)
        
        # Configuration
        config_group = QGroupBox("Configuration")
        config_layout = QGridLayout(config_group)
        
        # Number of matches
        config_layout.addWidget(QLabel("Number of Matches:"), 0, 0)
        self.num_matches_spin = QSpinBox()
        self.num_matches_spin.setRange(50, 1000)
        self.num_matches_spin.setValue(200)
        self.num_matches_spin.setSingleStep(50)
        config_layout.addWidget(self.num_matches_spin, 0, 1)
        
        # Initial bankroll
        config_layout.addWidget(QLabel("Initial Bankroll ($):"), 1, 0)
        self.bankroll_spin = QDoubleSpinBox()
        self.bankroll_spin.setRange(100, 100000)
        self.bankroll_spin.setValue(1000)
        self.bankroll_spin.setDecimals(2)
        config_layout.addWidget(self.bankroll_spin, 1, 1)
        
        # Max hole probability
        config_layout.addWidget(QLabel("Max Hole Probability (%):"), 2, 0)
        self.max_hole_spin = QDoubleSpinBox()
        self.max_hole_spin.setRange(1, 50)  # Increased max from 10% to 50% for more flexibility
        self.max_hole_spin.setValue(4)
        self.max_hole_spin.setDecimals(1)
        self.max_hole_spin.setSingleStep(0.5)
        config_layout.addWidget(self.max_hole_spin, 2, 1)
        
        # Min ROI
        config_layout.addWidget(QLabel("Min ROI (%):"), 3, 0)
        self.min_roi_spin = QDoubleSpinBox()
        self.min_roi_spin.setRange(0.5, 10)
        self.min_roi_spin.setValue(2)
        self.min_roi_spin.setDecimals(1)
        self.min_roi_spin.setSingleStep(0.5)
        config_layout.addWidget(self.min_roi_spin, 3, 1)
        
        # Strategy
        config_layout.addWidget(QLabel("Staking Strategy:"), 4, 0)
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["adaptive", "kelly", "fixed"])
        config_layout.addWidget(self.strategy_combo, 4, 1)
        
        # Use ML predictor
        self.use_ml_check = QCheckBox("Use ML Predictor")
        self.use_ml_check.setChecked(True)
        config_layout.addWidget(self.use_ml_check, 5, 0, 1, 2)
        
        layout.addWidget(config_group)
        
        # Run button
        btn_layout = QHBoxLayout()
        self.run_btn = QPushButton("🚀 Run Backtest")
        self.run_btn.setStyleSheet("""
            QPushButton {
                background-color: #00d9ff;
                color: black;
                padding: 10px 20px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #00b8d9; }
            QPushButton:disabled { background-color: #666; }
        """)
        self.run_btn.clicked.connect(self._run_backtest)
        btn_layout.addWidget(self.run_btn)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        btn_layout.addWidget(self.progress_bar)
        
        layout.addLayout(btn_layout)
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888;")
        layout.addWidget(self.status_label)
        
        # Results
        self.results_group = QGroupBox("Results")
        self.results_group.setVisible(False)
        results_layout = QGridLayout(self.results_group)
        
        self.result_labels = {}
        metrics = [
            ("Total Bets", "total_bets"), ("Won", "won"), 
            ("Lost", "lost"), ("Holes", "holes"),
            ("Win Rate", "win_rate"), ("Hole Rate", "hole_rate"),
            ("Final Bankroll", "final_bankroll"), ("P/L", "total_profit_loss"),
            ("ROI", "roi_percentage"), ("Sharpe Ratio", "sharpe_ratio"),
            ("Max Drawdown", "max_drawdown"), ("Avg Profit/Bet", "avg_profit_per_bet")
        ]
        
        for i, (label, key) in enumerate(metrics):
            results_layout.addWidget(QLabel(f"{label}:"), i // 2, (i % 2) * 2)
            value_label = QLabel("--")
            value_label.setStyleSheet("font-weight: bold;")
            self.result_labels[key] = value_label
            results_layout.addWidget(value_label, i // 2, (i % 2) * 2 + 1)
        
        layout.addWidget(self.results_group)
        
        # Export buttons
        export_layout = QHBoxLayout()
        
        self.export_html_btn = QPushButton("📊 Export HTML Report")
        self.export_html_btn.setEnabled(False)
        self.export_html_btn.clicked.connect(self._export_html)
        export_layout.addWidget(self.export_html_btn)
        
        self.export_csv_btn = QPushButton("📄 Export CSV")
        self.export_csv_btn.setEnabled(False)
        self.export_csv_btn.clicked.connect(self._export_csv)
        export_layout.addWidget(self.export_csv_btn)
        
        layout.addLayout(export_layout)
        
        # Log output
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
        
        layout.addStretch()
        
        scroll.setWidget(content)
        main_layout.addWidget(scroll)
    
    def _run_backtest(self):
        """Start the backtest."""
        if self.worker and self.worker.isRunning():
            return
        
        # Build config
        config = BacktestConfig(
            initial_bankroll=self.bankroll_spin.value(),
            max_hole_probability=self.max_hole_spin.value() / 100,
            min_roi=self.min_roi_spin.value() / 100,
            staking_strategy=StakingStrategy(self.strategy_combo.currentText()),
            use_ml_predictor=self.use_ml_check.isChecked(),
            num_matches=self.num_matches_spin.value()
        )
        
        # Update UI
        self.run_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.results_group.setVisible(False)
        self.log_text.clear()
        
        # Start worker
        self.worker = BacktestWorker(config)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()
    
    def _on_progress(self, message: str):
        """Handle progress update."""
        self.status_label.setText(message)
        self.log_text.append(message)
    
    def _on_finished(self, result: BacktestResult):
        """Handle backtest completion."""
        self.current_result = result
        
        self.run_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.results_group.setVisible(True)
        self.export_html_btn.setEnabled(True)
        self.export_csv_btn.setEnabled(True)
        
        # Update result labels
        self.result_labels['total_bets'].setText(str(result.total_bets))
        self.result_labels['won'].setText(str(result.won))
        self.result_labels['lost'].setText(str(result.lost))
        self.result_labels['holes'].setText(str(result.holes))
        
        self.result_labels['win_rate'].setText(f"{result.win_rate:.1f}%")
        self.result_labels['win_rate'].setStyleSheet(
            f"color: {'#2ecc71' if result.win_rate >= 50 else '#e74c3c'}; font-weight: bold;")
        
        self.result_labels['hole_rate'].setText(f"{result.hole_rate:.1f}%")
        self.result_labels['hole_rate'].setStyleSheet(
            f"color: {'#2ecc71' if result.hole_rate <= 4 else '#e74c3c'}; font-weight: bold;")
        
        self.result_labels['final_bankroll'].setText(f"${result.final_bankroll:,.2f}")
        self.result_labels['total_profit_loss'].setText(f"${result.total_profit_loss:+,.2f}")
        self.result_labels['total_profit_loss'].setStyleSheet(
            f"color: {'#2ecc71' if result.total_profit_loss >= 0 else '#e74c3c'}; font-weight: bold;")
        
        self.result_labels['roi_percentage'].setText(f"{result.roi_percentage:+.2f}%")
        self.result_labels['roi_percentage'].setStyleSheet(
            f"color: {'#2ecc71' if result.roi_percentage >= 0 else '#e74c3c'}; font-weight: bold;")
        
        self.result_labels['sharpe_ratio'].setText(f"{result.sharpe_ratio:.2f}")
        self.result_labels['max_drawdown'].setText(f"${result.max_drawdown:.2f}")
        self.result_labels['avg_profit_per_bet'].setText(f"${result.avg_profit_per_bet:.2f}")
        
        self.log_text.append(f"\n=== BACKTEST COMPLETE ===")
        self.log_text.append(f"ROI: {result.roi_percentage:+.2f}%")
        self.log_text.append(f"Win Rate: {result.win_rate:.1f}%")
        self.log_text.append(f"Hole Rate: {result.hole_rate:.1f}%")
        
        self.status_label.setText("Backtest complete!")
        self.status_label.setStyleSheet("color: #2ecc71;")
    
    def _on_error(self, error: str):
        """Handle backtest error."""
        self.run_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Error: {error}")
        self.status_label.setStyleSheet("color: #e74c3c;")
        self.log_text.append(f"ERROR: {error}")
        
        QMessageBox.critical(self, "Backtest Error", f"Error running backtest:\n{error}")
    
    def _export_html(self):
        """Export results to HTML report."""
        if not self.current_result:
            return
        
        try:
            generator = ReportGenerator()
            filepath = generator.generate_html_report(self.current_result)
            
            QMessageBox.information(self, "Export Complete", 
                f"HTML report saved to:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))
    
    def _export_csv(self):
        """Export results to CSV."""
        if not self.current_result:
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export to CSV", "backtest_results.csv", "CSV Files (*.csv)"
        )
        
        if filename:
            try:
                generator = ReportGenerator()
                filepath = generator.export_to_csv(self.current_result, Path(filename).name)
                
                QMessageBox.information(self, "Export Complete",
                    f"CSV exported to:\n{filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))
