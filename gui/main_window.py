"""Main Window for Eden MVP GUI Application."""

import sys
from pathlib import Path
from typing import Optional, List, Dict

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QStatusBar, QToolBar, QPushButton, QLabel, QMessageBox,
    QSplitter, QFrame, QApplication, QProgressDialog
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QFont, QPalette, QColor

import yaml

# Import widgets
from gui.widgets.arbitrage_table import ArbitrageTableWidget
from gui.widgets.match_details import MatchDetailsWidget
from gui.widgets.history_table import HistoryTableWidget
from gui.widgets.stats_dashboard import StatsDashboardWidget
from gui.widgets.backtest_panel import BacktestPanelWidget
from gui.widgets.settings_panel import SettingsPanelWidget
from gui.widgets.bankroll_panel import BankrollPanelWidget

# Import core modules
from core.odds_fetcher import OddsFetcher
from core.arbitrage_finder import ArbitrageFinder, ArbitrageConfig
from core.demo_data import generate_demo_matches
from models.overtime_predictor import OvertimePredictor
from analysis.match_analyzer import MatchAnalyzer, AnalyzerConfig, MatchAnalysis
from analysis.stake_calculator import StakeCalculator, StakeConfig, StakingStrategy
from database.db_manager import DatabaseManager
from utils.logger import setup_logger, get_logger

# Import bankroll management
from bankroll.manager import BankrollManager
from bankroll.profiles import ProfileType

# Import Telegram bot (optional)
try:
    from telegram_bot.bot import TelegramBot
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    TelegramBot = None

logger = get_logger(__name__)


class FetchWorker(QThread):
    """Worker thread for fetching opportunities."""
    
    progress = pyqtSignal(str)
    finished = pyqtSignal(list)  # List of MatchAnalysis
    error = pyqtSignal(str)
    
    def __init__(self, app):
        super().__init__()
        self.app = app
    
    def run(self):
        try:
            self.progress.emit("Fetching NHL odds...")
            
            if self.app.demo_mode:
                matches = generate_demo_matches(8)
            else:
                matches = self.app.odds_fetcher.fetch_odds(markets="h2h")
            
            if not matches:
                self.progress.emit("No matches found.")
                self.finished.emit([])
                return
            
            self.progress.emit(f"Analyzing {len(matches)} matches...")
            opportunities = self.app.arb_finder.find_arbitrage(matches)
            
            if not opportunities:
                self.progress.emit("No arbitrage opportunities found.")
                self.finished.emit([])
                return
            
            self.progress.emit(f"Found {len(opportunities)} opportunities, calculating stakes...")
            
            analyses = []
            for opp in opportunities:
                analysis = self.app.analyzer.analyze(opp)
                stake_result = self.app.stake_calc.calculate(analysis, StakingStrategy.ADAPTIVE)
                
                analysis.stake_strong = stake_result.stake_strong
                analysis.stake_weak = stake_result.stake_weak
                analysis.total_stake = stake_result.total_stake
                analysis.potential_profit = stake_result.potential_profit
                
                analyses.append(analysis)
                
                # Save to database
                try:
                    self.app.db.insert_match(analysis.model_dump())
                except:
                    pass
            
            self.progress.emit(f"Analysis complete!")
            self.finished.emit(analyses)
            
        except Exception as e:
            self.error.emit(str(e))


class EdenMainWindow(QMainWindow):
    """Main window for Eden MVP GUI application."""
    
    def __init__(self):
        super().__init__()
        
        self.config = {}
        self.analyses: List[MatchAnalysis] = []
        self.fetch_worker: Optional[FetchWorker] = None
        
        self._load_config()
        self._init_components()
        self._setup_ui()
        self._setup_style()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._on_fetch)
    
    def _load_config(self):
        """Load configuration."""
        config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")
            self.config = {}
        
        self.demo_mode = self.config.get('demo_mode', True)
    
    def _init_components(self):
        """Initialize core components."""
        api_config = self.config.get('api', {}).get('the_odds_api', {})
        bankroll_config = self.config.get('bankroll', {})
        risk_config = self.config.get('risk', {})
        db_config = self.config.get('database', {})
        telegram_config = self.config.get('telegram', {})
        
        # Database (initialize first for other components)
        self.db = DatabaseManager(db_config.get('path', 'eden_mvp.db'))
        self.db.initialize()
        
        # Odds fetcher
        self.odds_fetcher = OddsFetcher(
            api_key=api_config.get('key', ''),
            base_url=api_config.get('base_url', 'https://api.the-odds-api.com/v4'),
            sport=api_config.get('sport', 'icehockey_nhl'),
            regions=api_config.get('regions', 'us,eu')
        )
        
        # Arbitrage finder
        self.arb_finder = ArbitrageFinder(
            config=ArbitrageConfig(
                min_roi=risk_config.get('min_roi', 0.02),
                include_three_way=True
            )
        )
        
        # Match analyzer
        self.analyzer = MatchAnalyzer(
            config=AnalyzerConfig(
                max_hole_probability=risk_config.get('max_hole_probability', 0.04),
                min_roi=risk_config.get('min_roi', 0.02),
                use_ml_predictor=True
            )
        )
        
        # Bankroll Manager (Phase 1 - Smart Bankroll Management)
        profile_name = bankroll_config.get('profile', 'moderate').lower()
        profile_map = {
            'conservative': ProfileType.CONSERVATIVE,
            'moderate': ProfileType.MODERATE,
            'aggressive': ProfileType.AGGRESSIVE
        }
        self.bankroll_manager = BankrollManager(
            initial_bankroll=bankroll_config.get('total', 1000),
            profile=profile_map.get(profile_name, ProfileType.MODERATE),
            db_manager=self.db
        )
        
        # Stake calculator (integrated with bankroll manager)
        self.stake_calc = StakeCalculator(
            config=StakeConfig(
                bankroll=bankroll_config.get('total', 1000),
                min_stake_percent=bankroll_config.get('min_stake_percent', 0.02),
                max_stake_percent=bankroll_config.get('max_stake_percent', 0.10),
                default_stake_percent=bankroll_config.get('default_stake_percent', 0.04),
                kelly_shrink=risk_config.get('kelly_shrink', 0.5)
            ),
            bankroll_manager=self.bankroll_manager
        )
        
        # Telegram Bot (Phase 1 - Optional)
        self.telegram_bot = None
        if TELEGRAM_AVAILABLE and telegram_config.get('enabled', False):
            try:
                self.telegram_bot = TelegramBot(
                    token=telegram_config.get('bot_token', ''),
                    db_manager=self.db
                )
                if self.telegram_bot.enabled:
                    self.telegram_bot.start_in_thread()
                    logger.info("Telegram bot started")
            except Exception as e:
                logger.warning(f"Failed to start Telegram bot: {e}")
    
    def _setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("🏒 Eden MVP - Hockey Arbitrage System")
        self.setMinimumSize(1200, 800)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header = self._create_header()
        layout.addWidget(header)
        
        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        
        # Tab 1: Find Arbitrage
        arb_tab = QWidget()
        arb_layout = QHBoxLayout(arb_tab)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.arb_table = ArbitrageTableWidget()
        self.arb_table.opportunity_selected.connect(self._on_opportunity_selected)
        splitter.addWidget(self.arb_table)
        
        self.match_details = MatchDetailsWidget()
        splitter.addWidget(self.match_details)
        
        splitter.setSizes([600, 400])
        arb_layout.addWidget(splitter)
        
        self.tabs.addTab(arb_tab, "🔍 Find Arbitrage")
        
        # Tab 2: History
        self.history_table = HistoryTableWidget()
        self.tabs.addTab(self.history_table, "📜 History")
        
        # Tab 3: Statistics
        self.stats_dashboard = StatsDashboardWidget()
        self.tabs.addTab(self.stats_dashboard, "📊 Statistics")
        
        # Tab 4: Backtesting
        self.backtest_panel = BacktestPanelWidget()
        self.tabs.addTab(self.backtest_panel, "🧪 Backtesting")
        
        # Tab 5: Bankroll (Phase 1 - Smart Bankroll Management)
        self.bankroll_panel = BankrollPanelWidget()
        self.bankroll_panel.set_bankroll_manager(self.bankroll_manager)
        self.bankroll_panel.profile_changed.connect(self._on_profile_changed)
        self.tabs.addTab(self.bankroll_panel, "💰 Bankroll")
        
        # Tab 6: Settings
        config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        self.settings_panel = SettingsPanelWidget(str(config_path))
        self.settings_panel.settings_changed.connect(self._on_settings_changed)
        self.tabs.addTab(self.settings_panel, "⚙️ Settings")
        
        self.tabs.currentChanged.connect(self._on_tab_changed)
        
        layout.addWidget(self.tabs)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.mode_label = QLabel("🎮 Demo Mode" if self.demo_mode else "🌐 Live Mode")
        self.status_bar.addPermanentWidget(self.mode_label)
        
        self.bankroll_label = QLabel(f"Bankroll: ${self.stake_calc.config.bankroll:,.2f}")
        self.status_bar.addPermanentWidget(self.bankroll_label)
        
        self.status_bar.showMessage("Ready. Click 'Fetch Opportunities' to start.")
    
    def _create_header(self) -> QWidget:
        """Create the header widget."""
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 217, 255, 0.1);
                border-radius: 10px;
                padding: 10px;
            }
        """)
        
        layout = QHBoxLayout(header)
        
        # Title
        title = QLabel("🏒 Eden MVP")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #00d9ff;")
        layout.addWidget(title)
        
        subtitle = QLabel("Hockey Arbitrage Betting System")
        subtitle.setStyleSheet("color: #888;")
        layout.addWidget(subtitle)
        
        layout.addStretch()
        
        # Fetch button
        self.fetch_btn = QPushButton("🔄 Fetch Opportunities")
        self.fetch_btn.setStyleSheet("""
            QPushButton {
                background-color: #00d9ff;
                color: black;
                padding: 10px 20px;
                font-weight: bold;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #00b8d9; }
            QPushButton:disabled { background-color: #666; color: #999; }
        """)
        self.fetch_btn.clicked.connect(self._on_fetch)
        layout.addWidget(self.fetch_btn)
        
        return header
    
    def _setup_style(self):
        """Setup dark theme."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a2e;
            }
            QWidget {
                background-color: #1a1a2e;
                color: #eee;
            }
            QTabWidget::pane {
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 5px;
            }
            QTabBar::tab {
                background-color: rgba(255,255,255,0.05);
                color: #888;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: rgba(0,217,255,0.2);
                color: #00d9ff;
            }
            QTabBar::tab:hover {
                background-color: rgba(255,255,255,0.1);
            }
            QTableWidget {
                background-color: rgba(255,255,255,0.02);
                gridline-color: rgba(255,255,255,0.1);
                border: none;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: rgba(0,217,255,0.3);
            }
            QHeaderView::section {
                background-color: rgba(0,217,255,0.1);
                color: #00d9ff;
                padding: 8px;
                border: none;
            }
            QGroupBox {
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                color: #00d9ff;
                subcontrol-origin: margin;
                left: 10px;
            }
            QPushButton {
                background-color: rgba(255,255,255,0.1);
                border: 1px solid rgba(255,255,255,0.2);
                padding: 8px 15px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: rgba(255,255,255,0.2);
            }
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                background-color: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.2);
                padding: 5px;
                border-radius: 3px;
            }
            QScrollBar:vertical {
                background-color: rgba(255,255,255,0.05);
                width: 12px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(255,255,255,0.2);
                border-radius: 6px;
                min-height: 20px;
            }
            QStatusBar {
                background-color: rgba(0,0,0,0.3);
            }
        """)
    
    def _on_fetch(self):
        """Fetch arbitrage opportunities."""
        if self.fetch_worker and self.fetch_worker.isRunning():
            return
        
        self.fetch_btn.setEnabled(False)
        self.status_bar.showMessage("Fetching opportunities...")
        
        self.fetch_worker = FetchWorker(self)
        self.fetch_worker.progress.connect(self._on_fetch_progress)
        self.fetch_worker.finished.connect(self._on_fetch_finished)
        self.fetch_worker.error.connect(self._on_fetch_error)
        self.fetch_worker.start()
    
    def _on_fetch_progress(self, message: str):
        """Handle fetch progress."""
        self.status_bar.showMessage(message)
    
    def _on_fetch_finished(self, analyses: List[MatchAnalysis]):
        """Handle fetch completion."""
        self.fetch_btn.setEnabled(True)
        self.analyses = analyses
        
        self.arb_table.set_data(analyses)
        self.match_details.clear()
        
        bet_count = sum(1 for a in analyses if a.recommendation.value == 'bet')
        self.status_bar.showMessage(
            f"Found {len(analyses)} opportunities, {bet_count} recommended."
        )
        
        if not analyses:
            QMessageBox.information(
                self, "No Opportunities",
                "No arbitrage opportunities found at this time.\n"
                "Try again later as odds change frequently."
            )
    
    def _on_fetch_error(self, error: str):
        """Handle fetch error."""
        self.fetch_btn.setEnabled(True)
        self.status_bar.showMessage(f"Error: {error}")
        
        QMessageBox.warning(self, "Fetch Error", f"Error fetching data:\n{error}")
    
    def _on_opportunity_selected(self, match_id: str):
        """Handle opportunity selection."""
        for analysis in self.analyses:
            if analysis.match_id == match_id:
                self.match_details.set_analysis(analysis)
                break
    
    def _on_tab_changed(self, index: int):
        """Handle tab change."""
        tab_name = self.tabs.tabText(index)
        
        if "📜" in tab_name:  # History
            self._load_history()
        elif "📊" in tab_name:  # Statistics
            self._load_statistics()
    
    def _load_history(self):
        """Load betting history."""
        try:
            history = self.db.get_betting_history(100)
            self.history_table.set_data(history)
        except Exception as e:
            logger.error(f"Error loading history: {e}")
    
    def _load_statistics(self):
        """Load statistics."""
        try:
            stats = self.db.get_statistics()
            strat_perf = self.db.get_strategy_performance()
            self.stats_dashboard.set_stats(stats, strat_perf)
        except Exception as e:
            logger.error(f"Error loading stats: {e}")
    
    def _on_settings_changed(self, config: Dict):
        """Handle settings change."""
        self.config = config
        self.demo_mode = config.get('demo_mode', True)
        
        # Update mode label
        self.mode_label.setText("🎮 Demo Mode" if self.demo_mode else "🌐 Live Mode")
        
        # Reinitialize components
        self._init_components()
        
        # Update bankroll label
        self.bankroll_label.setText(f"Bankroll: ${self.stake_calc.config.bankroll:,.2f}")
        
        # Refresh bankroll panel
        if hasattr(self, 'bankroll_panel'):
            self.bankroll_panel.set_bankroll_manager(self.bankroll_manager)
        
        self.status_bar.showMessage("Settings updated. Click 'Fetch' to apply.")
    
    def _on_profile_changed(self, profile_name: str):
        """Handle bankroll profile change."""
        profile_map = {
            'conservative': ProfileType.CONSERVATIVE,
            'moderate': ProfileType.MODERATE,
            'aggressive': ProfileType.AGGRESSIVE
        }
        
        if profile_name in profile_map:
            self.bankroll_manager.set_profile(profile_map[profile_name])
            self.status_bar.showMessage(f"Bankroll profile changed to: {profile_name.title()}")
            
            # Update stake calculator
            self.stake_calc.set_bankroll_manager(self.bankroll_manager)
    
    def closeEvent(self, event):
        """Handle window close."""
        # Stop any running workers
        if self.fetch_worker and self.fetch_worker.isRunning():
            self.fetch_worker.terminate()
            self.fetch_worker.wait()
        
        # Stop Telegram bot
        if self.telegram_bot and self.telegram_bot.is_running:
            self.telegram_bot.stop_thread()
        
        self.refresh_timer.stop()
        event.accept()


def run_gui():
    """Run the GUI application."""
    app = QApplication(sys.argv)
    
    # Set application info
    app.setApplicationName("Eden MVP")
    app.setOrganizationName("Eden")
    
    # Create and show main window
    window = EdenMainWindow()
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(run_gui())
