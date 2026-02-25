"""Bankroll Panel Widget for Eden MVP GUI.

Displays bankroll status, risk metrics, and Monte Carlo simulation results.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QGroupBox, QProgressBar, QFrame, QScrollArea, QSizePolicy,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette

try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    FigureCanvas = None

from utils.logger import get_logger

logger = get_logger(__name__)


class MetricCard(QFrame):
    """A card displaying a single metric with label and value."""
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 217, 255, 0.1);
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.title_label)
        
        self.value_label = QLabel("--")
        self.value_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self.value_label.setStyleSheet("color: #00d9ff;")
        layout.addWidget(self.value_label)
        
        self.subtitle_label = QLabel("")
        self.subtitle_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(self.subtitle_label)
    
    def set_value(self, value: str, subtitle: str = "", color: str = "#00d9ff"):
        """Set the metric value."""
        self.value_label.setText(value)
        self.value_label.setStyleSheet(f"color: {color};")
        self.subtitle_label.setText(subtitle)


class BankrollPanelWidget(QWidget):
    """Widget for displaying and managing bankroll.
    
    Features:
    - Current bankroll, initial, peak, drawdown display
    - Risk of Ruin probability
    - Monte Carlo simulation results with chart
    - Profile selector
    - Bankroll history chart
    - Recommended stake display
    - Risk warning indicators
    
    Signals:
        profile_changed: Emitted when profile is changed
        bankroll_updated: Emitted when bankroll is manually updated
    """
    
    profile_changed = pyqtSignal(str)
    bankroll_updated = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._bankroll_manager = None
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI components."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Header
        header = self._create_header()
        main_layout.addWidget(header)
        
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(15)
        
        # Metrics cards row
        metrics_row = self._create_metrics_row()
        content_layout.addWidget(metrics_row)
        
        # Risk indicators row
        risk_row = self._create_risk_indicators()
        content_layout.addWidget(risk_row)
        
        # Charts row
        if MATPLOTLIB_AVAILABLE:
            charts_row = self._create_charts_row()
            content_layout.addWidget(charts_row)
        
        # History table
        history_group = self._create_history_table()
        content_layout.addWidget(history_group)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll, 1)
    
    def _create_header(self) -> QWidget:
        """Create the header with title and profile selector."""
        header = QFrame()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("💰 Bankroll Management")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #00d9ff;")
        layout.addWidget(title)
        
        layout.addStretch()
        
        # Profile selector
        profile_label = QLabel("Profile:")
        profile_label.setStyleSheet("color: #aaa;")
        layout.addWidget(profile_label)
        
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(["Conservative", "Moderate", "Aggressive", "Custom"])
        self.profile_combo.setCurrentText("Moderate")
        self.profile_combo.currentTextChanged.connect(self._on_profile_changed)
        self.profile_combo.setStyleSheet("""
            QComboBox {
                background-color: #2a2a4e;
                color: #eee;
                border: 1px solid #444;
                padding: 5px 10px;
                border-radius: 4px;
                min-width: 120px;
            }
        """)
        layout.addWidget(self.profile_combo)
        
        # Run simulation button
        self.sim_btn = QPushButton("🎲 Run Simulation")
        self.sim_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a4a8e;
                color: white;
                padding: 5px 15px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #5a5a9e; }
        """)
        self.sim_btn.clicked.connect(self._run_simulation)
        layout.addWidget(self.sim_btn)
        
        # Refresh button
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #00d9ff;
                color: black;
                padding: 5px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #00b8d9; }
        """)
        self.refresh_btn.clicked.connect(self.refresh_data)
        layout.addWidget(self.refresh_btn)
        
        return header
    
    def _create_metrics_row(self) -> QWidget:
        """Create the row of metric cards."""
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Current Bankroll
        self.card_current = MetricCard("Current Bankroll")
        self.card_current.set_value("$1,000.00")
        layout.addWidget(self.card_current)
        
        # Initial Bankroll
        self.card_initial = MetricCard("Initial Bankroll")
        self.card_initial.set_value("$1,000.00", color="#888")
        layout.addWidget(self.card_initial)
        
        # Peak Bankroll
        self.card_peak = MetricCard("Peak Bankroll")
        self.card_peak.set_value("$1,000.00", color="#4ade80")
        layout.addWidget(self.card_peak)
        
        # Drawdown
        self.card_drawdown = MetricCard("Current Drawdown")
        self.card_drawdown.set_value("0.0%", color="#4ade80")
        layout.addWidget(self.card_drawdown)
        
        # ROI
        self.card_roi = MetricCard("Total ROI")
        self.card_roi.set_value("0.0%")
        layout.addWidget(self.card_roi)
        
        return row
    
    def _create_risk_indicators(self) -> QWidget:
        """Create risk indicator section."""
        group = QGroupBox("Risk Analysis")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #333;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QGridLayout(group)
        layout.setSpacing(15)
        
        # Risk of Ruin
        ror_label = QLabel("Risk of Ruin (50%)")
        ror_label.setStyleSheet("color: #aaa;")
        layout.addWidget(ror_label, 0, 0)
        
        self.ror_progress = QProgressBar()
        self.ror_progress.setRange(0, 100)
        self.ror_progress.setValue(5)
        self.ror_progress.setFormat("%p%")
        self.ror_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #444;
                border-radius: 4px;
                height: 20px;
                background-color: #2a2a4e;
            }
            QProgressBar::chunk {
                background-color: #4ade80;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.ror_progress, 0, 1)
        
        self.ror_value = QLabel("5.0%")
        self.ror_value.setStyleSheet("color: #4ade80; font-weight: bold;")
        layout.addWidget(self.ror_value, 0, 2)
        
        # Optimal Kelly
        kelly_label = QLabel("Optimal Kelly Fraction")
        kelly_label.setStyleSheet("color: #aaa;")
        layout.addWidget(kelly_label, 1, 0)
        
        self.kelly_value = QLabel("8.5%")
        self.kelly_value.setStyleSheet("color: #00d9ff; font-weight: bold;")
        layout.addWidget(self.kelly_value, 1, 1)
        
        kelly_usage_label = QLabel("Kelly Usage")
        kelly_usage_label.setStyleSheet("color: #aaa;")
        layout.addWidget(kelly_usage_label, 1, 2)
        
        self.kelly_usage_value = QLabel("50%")
        self.kelly_usage_value.setStyleSheet("color: #fbbf24; font-weight: bold;")
        layout.addWidget(self.kelly_usage_value, 1, 3)
        
        # Recommended Stake
        stake_label = QLabel("Recommended Stake")
        stake_label.setStyleSheet("color: #aaa;")
        layout.addWidget(stake_label, 2, 0)
        
        self.recommended_stake = QLabel("$40.00 (4.0%)")
        self.recommended_stake.setStyleSheet("color: #00d9ff; font-weight: bold; font-size: 14px;")
        layout.addWidget(self.recommended_stake, 2, 1, 1, 2)
        
        # Emergency warning
        self.emergency_warning = QLabel("🚨 EMERGENCY MODE: Stakes reduced")
        self.emergency_warning.setStyleSheet("""
            QLabel {
                color: #ef4444;
                background-color: rgba(239, 68, 68, 0.2);
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
            }
        """)
        self.emergency_warning.hide()
        layout.addWidget(self.emergency_warning, 3, 0, 1, 4)
        
        return group
    
    def _create_charts_row(self) -> QWidget:
        """Create the charts section."""
        group = QGroupBox("Monte Carlo Simulation")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #333;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout(group)
        
        # Chart canvas
        self.figure = Figure(figsize=(10, 4), facecolor='#1a1a2e')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumHeight(250)
        layout.addWidget(self.canvas)
        
        # Simulation stats
        stats_layout = QHBoxLayout()
        
        self.mc_stats = {
            'median': QLabel("Median: --"),
            'prob_profit': QLabel("P(Profit): --"),
            'prob_loss': QLabel("P(50% Loss): --"),
            'percentile_5': QLabel("5th %ile: --"),
            'percentile_95': QLabel("95th %ile: --")
        }
        
        for label in self.mc_stats.values():
            label.setStyleSheet("color: #aaa;")
            stats_layout.addWidget(label)
        
        layout.addLayout(stats_layout)
        
        return group
    
    def _create_history_table(self) -> QWidget:
        """Create the history table section."""
        group = QGroupBox("Bankroll History")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #333;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout(group)
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels([
            "Date", "Bankroll", "Change", "Drawdown", "Notes"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.history_table.setMaximumHeight(200)
        self.history_table.setStyleSheet("""
            QTableWidget {
                background-color: #1a1a2e;
                border: 1px solid #333;
                gridline-color: #333;
            }
            QHeaderView::section {
                background-color: #2a2a4e;
                padding: 5px;
                border: none;
            }
        """)
        layout.addWidget(self.history_table)
        
        return group
    
    def set_bankroll_manager(self, manager):
        """Set the bankroll manager instance."""
        self._bankroll_manager = manager
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh all displayed data."""
        if not self._bankroll_manager:
            return
        
        try:
            state = self._bankroll_manager.get_state()
            
            # Update metric cards
            self.card_current.set_value(
                f"${state.current:,.2f}",
                f"P/L: ${state.total_profit:+,.2f}"
            )
            
            self.card_initial.set_value(
                f"${state.initial:,.2f}",
                color="#888"
            )
            
            self.card_peak.set_value(
                f"${state.peak:,.2f}",
                color="#4ade80" if state.peak >= state.initial else "#fbbf24"
            )
            
            # Drawdown color coding
            dd_color = "#4ade80"  # Green
            if state.drawdown_percent > 15:
                dd_color = "#ef4444"  # Red
            elif state.drawdown_percent > 10:
                dd_color = "#f97316"  # Orange
            elif state.drawdown_percent > 5:
                dd_color = "#fbbf24"  # Yellow
            
            self.card_drawdown.set_value(
                f"{state.drawdown_percent:.1f}%",
                f"${state.drawdown:,.2f}",
                color=dd_color
            )
            
            # ROI color
            roi_color = "#4ade80" if state.roi >= 0 else "#ef4444"
            self.card_roi.set_value(
                f"{state.roi:+.1f}%",
                f"Win Rate: {state.win_rate:.1f}%",
                color=roi_color
            )
            
            # Update risk indicators
            risk_metrics = self._bankroll_manager.get_risk_metrics()
            
            ror = risk_metrics.risk_of_ruin_50 * 100
            self.ror_progress.setValue(int(min(ror, 100)))
            self.ror_value.setText(f"{ror:.1f}%")
            
            ror_color = "#4ade80" if ror < 10 else ("#fbbf24" if ror < 25 else "#ef4444")
            self.ror_value.setStyleSheet(f"color: {ror_color}; font-weight: bold;")
            self.ror_progress.setStyleSheet(f"""
                QProgressBar {{
                    border: 1px solid #444;
                    border-radius: 4px;
                    height: 20px;
                    background-color: #2a2a4e;
                }}
                QProgressBar::chunk {{
                    background-color: {ror_color};
                    border-radius: 3px;
                }}
            """)
            
            self.kelly_value.setText(f"{risk_metrics.optimal_kelly * 100:.1f}%")
            self.kelly_usage_value.setText(f"{risk_metrics.current_kelly_usage:.0f}%")
            
            # Recommended stake
            stake_result = self._bankroll_manager.get_recommended_stake()
            self.recommended_stake.setText(
                f"${stake_result.stake_amount:.2f} ({stake_result.adjusted_stake_percent * 100:.1f}%)"
            )
            
            # Emergency mode
            if self._bankroll_manager.is_emergency_mode():
                self.emergency_warning.show()
            else:
                self.emergency_warning.hide()
            
            # Update history table
            self._update_history_table()
            
            logger.debug("Bankroll panel data refreshed")
            
        except Exception as e:
            logger.error(f"Error refreshing bankroll data: {e}")
    
    def _update_history_table(self):
        """Update the history table."""
        if not self._bankroll_manager:
            return
        
        history = self._bankroll_manager.get_history(limit=10)
        self.history_table.setRowCount(len(history))
        
        for row, entry in enumerate(history):
            timestamp = entry.get('timestamp', '')
            if isinstance(timestamp, str) and len(timestamp) > 10:
                timestamp = timestamp[:10]
            
            self.history_table.setItem(row, 0, QTableWidgetItem(str(timestamp)))
            self.history_table.setItem(row, 1, QTableWidgetItem(f"${entry.get('bankroll', 0):,.2f}"))
            
            change = entry.get('change', 0)
            change_item = QTableWidgetItem(f"${change:+,.2f}")
            change_item.setForeground(
                QColor("#4ade80") if change >= 0 else QColor("#ef4444")
            )
            self.history_table.setItem(row, 2, change_item)
            
            self.history_table.setItem(row, 3, QTableWidgetItem(f"{entry.get('drawdown', 0):.1f}%"))
            self.history_table.setItem(row, 4, QTableWidgetItem(entry.get('notes', '')[:30]))
    
    def _run_simulation(self):
        """Run Monte Carlo simulation and update chart."""
        if not self._bankroll_manager or not MATPLOTLIB_AVAILABLE:
            return
        
        try:
            self.sim_btn.setEnabled(False)
            self.sim_btn.setText("Running...")
            
            # Run simulation
            risk_metrics = self._bankroll_manager.risk_calculator.calculate_all_metrics(
                run_monte_carlo=True
            )
            mc_results = risk_metrics.monte_carlo_results
            
            if mc_results:
                # Update chart
                self._update_simulation_chart(mc_results)
                
                # Update stats
                self.mc_stats['median'].setText(f"Median: ${mc_results.get('median_final', 0):,.2f}")
                self.mc_stats['prob_profit'].setText(f"P(Profit): {mc_results.get('prob_profit', 0)*100:.1f}%")
                self.mc_stats['prob_loss'].setText(f"P(50% Loss): {mc_results.get('prob_50_loss', 0)*100:.1f}%")
                self.mc_stats['percentile_5'].setText(f"5th %ile: ${mc_results.get('percentile_5', 0):,.2f}")
                self.mc_stats['percentile_95'].setText(f"95th %ile: ${mc_results.get('percentile_95', 0):,.2f}")
            
        except Exception as e:
            logger.error(f"Simulation error: {e}")
            QMessageBox.warning(self, "Error", f"Simulation failed: {e}")
        
        finally:
            self.sim_btn.setEnabled(True)
            self.sim_btn.setText("🎲 Run Simulation")
    
    def _update_simulation_chart(self, mc_results: Dict):
        """Update the Monte Carlo chart."""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#1a1a2e')
        
        # Plot histogram of final bankrolls
        finals = mc_results.get('final_bankrolls', [])
        if finals:
            initial = self._bankroll_manager.initial
            
            ax.hist(finals, bins=30, color='#00d9ff', alpha=0.7, edgecolor='#1a1a2e')
            ax.axvline(initial, color='#fbbf24', linestyle='--', label=f'Initial: ${initial:,.0f}')
            ax.axvline(mc_results.get('median_final', 0), color='#4ade80', linestyle='-', label=f"Median: ${mc_results.get('median_final', 0):,.0f}")
            
            ax.set_xlabel('Final Bankroll ($)', color='#aaa')
            ax.set_ylabel('Frequency', color='#aaa')
            ax.set_title('Monte Carlo Simulation Results', color='#eee')
            ax.tick_params(colors='#888')
            ax.legend(facecolor='#2a2a4e', edgecolor='#444', labelcolor='#eee')
            ax.spines['bottom'].set_color('#444')
            ax.spines['top'].set_color('#444')
            ax.spines['left'].set_color('#444')
            ax.spines['right'].set_color('#444')
        
        self.figure.tight_layout()
        self.canvas.draw()
    
    def _on_profile_changed(self, profile_name: str):
        """Handle profile change."""
        self.profile_changed.emit(profile_name.lower())
        
        if self._bankroll_manager:
            from bankroll.profiles import ProfileType
            profile_map = {
                'conservative': ProfileType.CONSERVATIVE,
                'moderate': ProfileType.MODERATE,
                'aggressive': ProfileType.AGGRESSIVE,
                'custom': ProfileType.CUSTOM
            }
            if profile_name.lower() in profile_map:
                self._bankroll_manager.set_profile(profile_map[profile_name.lower()])
                self.refresh_data()
