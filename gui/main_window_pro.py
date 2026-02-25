"""Premium Modern Main Window for Eden Analytics Pro v3.0.0 Monster Edition with Sidebar Navigation."""

import sys
from pathlib import Path
from typing import Optional, List, Dict

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QStatusBar, QPushButton, QLabel, QFrame, QApplication, QMessageBox,
    QSplitter, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QFont, QKeySequence, QIcon, QShortcut, QColor

import yaml

# Import theme
from gui.themes.modern_theme import ModernTheme, ThemeType, get_theme, set_theme, get_logo_path

# Import pages
from gui.pages.dashboard_page import DashboardPage
from gui.pages.ml_models_page import MLModelsPage
from gui.pages.live_scores_page import LiveScoresPage
from gui.pages.injuries_page import InjuriesPage

# Import existing widgets
from gui.widgets.arbitrage_table import ArbitrageTableWidget
from gui.widgets.match_details import MatchDetailsWidget
from gui.widgets.history_table import HistoryTableWidget
from gui.widgets.stats_dashboard import StatsDashboardWidget
from gui.widgets.backtest_panel import BacktestPanelWidget
from gui.widgets.settings_panel import SettingsPanelWidget
from gui.widgets.bankroll_panel import BankrollPanelWidget

# Import components
from gui.components.modern_widgets import ModernButton, PremiumButton, show_notification
from gui.dialogs.about_dialog import AboutDialog
from gui.splash_screen import SplashScreen, show_splash_screen
from gui.system_tray import SystemTrayManager

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

# Import localization
from localization import t, set_language

logger = get_logger(__name__)


class PremiumSidebarButton(QPushButton):
    """Premium styled sidebar navigation button with glow effects."""
    
    def __init__(self, icon: str, text: str, page_name: str, parent=None):
        super().__init__(f"  {icon}  {text}", parent)
        self.page_name = page_name
        self._selected = False
        
        self.setCheckable(True)
        self.setFixedHeight(54)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()
    
    def _update_style(self):
        theme = get_theme()
        p = theme.palette
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {p.text_secondary};
                border: none;
                text-align: left;
                padding-left: 20px;
                font-size: 15px;
                font-weight: 500;
                border-radius: 12px;
                margin: 3px 12px;
            }}
            QPushButton:hover {{
                background: rgba({theme._hex_to_rgb(p.primary)}, 0.1);
                color: {p.text};
                border-left: 3px solid {p.primary};
                padding-left: 17px;
            }}
            QPushButton:checked {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba({theme._hex_to_rgb(p.primary)}, 0.25),
                    stop:1 transparent);
                color: {p.primary};
                border-left: 3px solid {p.primary};
                padding-left: 17px;
                font-weight: 700;
            }}
        """)


# Backward compatible alias
SidebarButton = PremiumSidebarButton


class FetchWorker(QThread):
    """Worker thread for fetching opportunities."""
    
    progress = pyqtSignal(str)
    finished = pyqtSignal(list)
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
                
                try:
                    self.app.db.insert_match(analysis.model_dump())
                except:
                    pass
            
            self.progress.emit("Analysis complete!")
            self.finished.emit(analyses)
            
        except Exception as e:
            self.error.emit(str(e))


class EdenMainWindowPro(QMainWindow):
    """Modern main window with sidebar navigation."""
    
    def __init__(self):
        super().__init__()
        
        self.config = {}
        self.analyses: List[MatchAnalysis] = []
        self.fetch_worker: Optional[FetchWorker] = None
        self.theme = get_theme()
        
        self._load_config()
        self._init_components()
        self._setup_ui()
        self._setup_shortcuts()
        self._setup_system_tray()
        
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
        
        # Set language
        gui_config = self.config.get('gui', {})
        language = gui_config.get('language', 'en')
        set_language(language)
    
    def _init_components(self):
        """Initialize core components."""
        api_config = self.config.get('api', {}).get('the_odds_api', {})
        bankroll_config = self.config.get('bankroll', {})
        risk_config = self.config.get('risk', {})
        db_config = self.config.get('database', {})
        
        # Database
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
        
        # Bankroll Manager
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
        
        # Stake calculator
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
    
    def _setup_ui(self):
        """Setup the premium user interface."""
        self.setWindowTitle("🏒 Eden Analytics Pro v3.0.0 Monster Edition")
        self.setMinimumSize(1500, 950)
        
        # Set window icon
        import os
        icon_path = get_logo_path('dark', 'icon')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Apply theme
        self.setStyleSheet(self.theme.get_main_stylesheet())
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar
        sidebar = self._create_sidebar()
        main_layout.addWidget(sidebar)
        
        # Main content area
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Header
        header = self._create_header()
        content_layout.addWidget(header)
        
        # Stacked widget for pages
        self.pages = QStackedWidget()
        self._create_pages()
        content_layout.addWidget(self.pages)
        
        main_layout.addWidget(content_area, stretch=1)
        
        # Status bar
        self._setup_status_bar()
    
    def _create_sidebar(self) -> QWidget:
        """Create premium sidebar navigation with glow effects."""
        sidebar = QFrame()
        sidebar.setObjectName("premiumSidebar")
        sidebar.setFixedWidth(280)
        
        theme = get_theme()
        p = theme.palette
        
        sidebar.setStyleSheet(f"""
            #premiumSidebar {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {p.surface}, stop:1 {p.background});
                border-right: 1px solid {p.border};
            }}
        """)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # Premium Logo/Brand Section
        brand = QFrame()
        brand.setObjectName("brandSection")
        brand.setFixedHeight(100)
        brand.setCursor(Qt.CursorShape.PointingHandCursor)
        brand.setStyleSheet(f"""
            #brandSection {{
                background: transparent;
                border-bottom: 1px solid {p.border};
                margin-bottom: 12px;
            }}
        """)
        
        brand_layout = QVBoxLayout(brand)
        brand_layout.setContentsMargins(20, 16, 20, 16)
        brand_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Logo container with glow
        logo_container = QHBoxLayout()
        logo_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        import os
        logo_path = get_logo_path('dark', 'icon')
        logo = QLabel()
        if os.path.exists(logo_path):
            from PyQt6.QtGui import QPixmap
            pixmap = QPixmap(logo_path)
            scaled = pixmap.scaled(56, 56, Qt.AspectRatioMode.KeepAspectRatio, 
                                   Qt.TransformationMode.SmoothTransformation)
            logo.setPixmap(scaled)
        else:
            logo.setText("🏒")
            logo.setStyleSheet("font-size: 40px;")
        logo_container.addWidget(logo)
        brand_layout.addLayout(logo_container)
        
        # App name with gradient style
        app_name = QLabel("EDEN ANALYTICS PRO")
        app_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        app_name.setStyleSheet(f"""
            QLabel {{
                color: {p.primary};
                font-size: 14px;
                font-weight: 900;
                letter-spacing: 2px;
                margin-top: 8px;
            }}
        """)
        brand_layout.addWidget(app_name)
        
        # Make brand clickable to go to dashboard
        brand.mousePressEvent = lambda e: self._navigate_to("dashboard")
        
        layout.addWidget(brand)
        layout.addSpacing(8)
        
        # Navigation buttons
        self.nav_buttons = []
        
        nav_items = [
            ("🏠", t("menu.dashboard"), "dashboard"),
            ("🎯", t("menu.arbitrage"), "arbitrage"),
            ("🏥", "Injuries", "injuries"),  # New injuries page
            ("📊", t("menu.statistics"), "statistics"),
            ("🤖", t("menu.ml_models"), "ml_models"),
            ("🏒", t("menu.live_scores"), "live_scores"),
            ("📜", t("menu.history"), "history"),
            ("🧪", t("menu.backtest"), "backtest"),
            ("💰", t("menu.bankroll"), "bankroll"),
        ]
        
        for icon, text, page in nav_items:
            btn = PremiumSidebarButton(icon, text, page)
            btn.clicked.connect(lambda checked, p=page: self._navigate_to(p))
            self.nav_buttons.append(btn)
            layout.addWidget(btn)
        
        layout.addStretch()
        
        # Divider
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background-color: {p.border}; margin: 8px 16px;")
        layout.addWidget(divider)
        
        # Settings button
        settings_btn = PremiumSidebarButton("⚙️", t("menu.settings"), "settings")
        settings_btn.clicked.connect(lambda: self._navigate_to("settings"))
        self.nav_buttons.append(settings_btn)
        layout.addWidget(settings_btn)
        
        # Theme toggle with premium styling
        self.theme_btn = QPushButton("🌙  Dark Mode")
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {p.text_secondary};
                border: none;
                padding: 14px 20px;
                text-align: left;
                font-size: 14px;
                font-weight: 500;
                border-radius: 12px;
                margin: 3px 12px;
            }}
            QPushButton:hover {{
                background: rgba({theme._hex_to_rgb(p.secondary)}, 0.1);
                color: {p.text};
            }}
        """)
        self.theme_btn.clicked.connect(self._toggle_theme)
        layout.addWidget(self.theme_btn)
        
        # Version label with premium styling
        version_container = QFrame()
        version_container.setStyleSheet(f"""
            QFrame {{
                background: rgba({theme._hex_to_rgb(p.primary)}, 0.05);
                border-radius: 8px;
                margin: 8px 16px 16px 16px;
            }}
        """)
        version_layout = QHBoxLayout(version_container)
        version_layout.setContentsMargins(12, 8, 12, 8)
        
        version = QLabel("v3.0.0 Monster")
        version.setStyleSheet(f"""
            color: {p.primary}; 
            font-size: 11px; 
            font-weight: 700;
        """)
        version_layout.addWidget(version)
        version_layout.addStretch()
        
        status_dot = QLabel("●")
        status_dot.setStyleSheet(f"color: {p.success}; font-size: 10px;")
        version_layout.addWidget(status_dot)
        
        layout.addWidget(version_container)
        
        return sidebar
    
    def _create_header(self) -> QWidget:
        """Create premium top header bar."""
        header = QFrame()
        header.setObjectName("premiumHeader")
        header.setFixedHeight(72)
        
        theme = get_theme()
        p = theme.palette
        
        header.setStyleSheet(f"""
            #premiumHeader {{
                background-color: {p.surface};
                border-bottom: 1px solid {p.border};
            }}
        """)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(32, 0, 32, 0)
        
        # Page title with premium styling
        self.page_title = QLabel("Dashboard")
        self.page_title.setStyleSheet(f"""
            color: {p.text}; 
            font-size: 24px; 
            font-weight: 800;
            letter-spacing: -0.5px;
        """)
        layout.addWidget(self.page_title)
        
        layout.addStretch()
        
        # Premium Fetch button
        self.fetch_btn = PremiumButton("🔄  " + t("arbitrage.fetch"), style='primary')
        self.fetch_btn.clicked.connect(self._on_fetch)
        layout.addWidget(self.fetch_btn)
        
        layout.addSpacing(12)
        
        # Premium About button with glow
        about_btn = QPushButton("ℹ️")
        about_btn.setFixedSize(44, 44)
        about_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        about_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba({theme._hex_to_rgb(p.primary)}, 0.1);
                border: 1px solid rgba({theme._hex_to_rgb(p.primary)}, 0.2);
                border-radius: 22px;
                font-size: 18px;
            }}
            QPushButton:hover {{
                background: rgba({theme._hex_to_rgb(p.primary)}, 0.2);
                border-color: {p.primary};
            }}
        """)
        about_btn.clicked.connect(self._show_about)
        layout.addWidget(about_btn)
        
        return header
    
    def _create_pages(self):
        """Create all pages."""
        # Dashboard (index 0)
        self.dashboard_page = DashboardPage()
        self.dashboard_page.navigate_to.connect(self._navigate_to)
        self.pages.addWidget(self.dashboard_page)
        
        # Arbitrage (index 1)
        arb_page = QWidget()
        arb_layout = QHBoxLayout(arb_page)
        arb_layout.setContentsMargins(16, 16, 16, 16)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.arb_table = ArbitrageTableWidget()
        self.arb_table.opportunity_selected.connect(self._on_opportunity_selected)
        splitter.addWidget(self.arb_table)
        
        self.match_details = MatchDetailsWidget()
        splitter.addWidget(self.match_details)
        
        splitter.setSizes([600, 400])
        arb_layout.addWidget(splitter)
        
        self.pages.addWidget(arb_page)
        
        # Injuries (index 2)
        self.injuries_page = InjuriesPage()
        db_path = Path(__file__).parent.parent / "data" / "nhl_historical.db"
        self.injuries_page.set_database_path(str(db_path))
        self.pages.addWidget(self.injuries_page)
        
        # History (index 3)
        self.history_table = HistoryTableWidget()
        self.pages.addWidget(self.history_table)
        
        # Statistics (index 4)
        self.stats_dashboard = StatsDashboardWidget()
        self.pages.addWidget(self.stats_dashboard)
        
        # ML Models (index 5)
        self.ml_models_page = MLModelsPage()
        self.pages.addWidget(self.ml_models_page)
        
        # Live Scores (index 6)
        self.live_scores_page = LiveScoresPage()
        self.pages.addWidget(self.live_scores_page)
        
        # Backtest (index 7)
        self.backtest_panel = BacktestPanelWidget()
        self.pages.addWidget(self.backtest_panel)
        
        # Bankroll (index 8)
        self.bankroll_panel = BankrollPanelWidget()
        self.bankroll_panel.set_bankroll_manager(self.bankroll_manager)
        self.pages.addWidget(self.bankroll_panel)
        
        # Settings (index 9)
        config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        self.settings_panel = SettingsPanelWidget(str(config_path))
        self.settings_panel.settings_changed.connect(self._on_settings_changed)
        self.pages.addWidget(self.settings_panel)
        
        # Set default page
        self._navigate_to("dashboard")
    
    def _setup_status_bar(self):
        """Setup premium status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        theme = get_theme()
        p = theme.palette
        
        self.status_bar.setStyleSheet(f"""
            QStatusBar {{
                background-color: {p.surface};
                border-top: 1px solid {p.border};
                padding: 8px 16px;
                font-size: 13px;
            }}
            QStatusBar::item {{
                border: none;
            }}
        """)
        
        # Mode label with premium styling
        self.mode_label = QLabel("🎮 Demo Mode" if self.demo_mode else "🌐 Live Mode")
        self.mode_label.setStyleSheet(f"""
            QLabel {{
                background: rgba({theme._hex_to_rgb(p.secondary if self.demo_mode else p.success)}, 0.15);
                color: {p.secondary if self.demo_mode else p.success};
                padding: 4px 12px;
                border-radius: 8px;
                font-weight: 600;
            }}
        """)
        self.status_bar.addPermanentWidget(self.mode_label)
        
        # Bankroll label with premium styling
        self.bankroll_label = QLabel(f"💰 ${self.stake_calc.config.bankroll:,.2f}")
        self.bankroll_label.setStyleSheet(f"""
            QLabel {{
                background: rgba({theme._hex_to_rgb(p.primary)}, 0.15);
                color: {p.primary};
                padding: 4px 12px;
                border-radius: 8px;
                font-weight: 700;
            }}
        """)
        self.status_bar.addPermanentWidget(self.bankroll_label)
        
        self.status_bar.showMessage("✨ " + t("common.loading") + " Ready.")
    
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        shortcuts = [
            ("Ctrl+F", self._on_fetch),
            ("Ctrl+H", lambda: self._navigate_to("history")),
            ("Ctrl+S", lambda: self._navigate_to("settings")),
            ("Ctrl+R", self._refresh_current),
            ("Ctrl+T", self._toggle_theme),
            ("Ctrl+Q", self.close),
            ("F5", self._refresh_current),
            ("F1", self._show_about),
            ("Ctrl+1", lambda: self._navigate_to("dashboard")),
            ("Ctrl+2", lambda: self._navigate_to("arbitrage")),
            ("Ctrl+3", lambda: self._navigate_to("history")),
            ("Ctrl+4", lambda: self._navigate_to("statistics")),
        ]
        
        for key, callback in shortcuts:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(callback)
    
    def _setup_system_tray(self):
        """Setup system tray icon."""
        self.tray_manager = SystemTrayManager(self)
        self.tray_manager.show_requested.connect(self.show)
        self.tray_manager.hide_requested.connect(self.hide)
        self.tray_manager.arbitrage_requested.connect(lambda: (self._navigate_to("arbitrage"), self._on_fetch()))
        self.tray_manager.stats_requested.connect(lambda: self._navigate_to("statistics"))
        self.tray_manager.settings_requested.connect(lambda: self._navigate_to("settings"))
        self.tray_manager.quit_requested.connect(self.close)
        self.tray_manager.show()
    
    def _navigate_to(self, page: str):
        """Navigate to a page."""
        page_map = {
            "dashboard": (0, t("menu.dashboard")),
            "arbitrage": (1, t("menu.arbitrage")),
            "injuries": (2, "🏥 Injuries Tracker"),
            "history": (3, t("menu.history")),
            "statistics": (4, t("menu.statistics")),
            "ml_models": (5, t("menu.ml_models")),
            "live_scores": (6, t("menu.live_scores")),
            "backtest": (7, t("menu.backtest")),
            "bankroll": (8, t("menu.bankroll")),
            "settings": (9, t("menu.settings")),
        }
        
        if page in page_map:
            index, title = page_map[page]
            self.pages.setCurrentIndex(index)
            self.page_title.setText(title)
            
            # Update nav buttons
            for btn in self.nav_buttons:
                btn.setChecked(btn.page_name == page)
            
            # Load data for specific pages
            if page == "injuries":
                self.injuries_page.load_injuries()
            elif page == "history":
                self._load_history()
            elif page == "statistics":
                self._load_statistics()
    
    def _toggle_theme(self):
        """Toggle between dark and light theme."""
        if self.theme.theme_type == ThemeType.DARK:
            set_theme(ThemeType.LIGHT)
            self.theme_btn.setText("☀️ Light Mode")
        else:
            set_theme(ThemeType.DARK)
            self.theme_btn.setText("🌙 Dark Mode")
        
        self.theme = get_theme()
        self.setStyleSheet(self.theme.get_main_stylesheet())
        
        show_notification("Theme changed", "info")
    
    def _refresh_current(self):
        """Refresh current page data."""
        current_index = self.pages.currentIndex()
        
        if current_index == 1:  # Arbitrage
            self._on_fetch()
        elif current_index == 2:  # Injuries
            self.injuries_page.load_injuries()
        elif current_index == 3:  # History
            self._load_history()
        elif current_index == 4:  # Statistics
            self._load_statistics()
    
    def _on_fetch(self):
        """Fetch arbitrage opportunities."""
        if self.fetch_worker and self.fetch_worker.isRunning():
            return
        
        self.fetch_btn.setEnabled(False)
        self.status_bar.showMessage(t("arbitrage.analyzing"))
        
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
            t("arbitrage.found", count=len(analyses)) + f", {bet_count} recommended."
        )
        
        # System tray notification
        if analyses and bet_count > 0:
            best = max(analyses, key=lambda x: x.roi)
            self.tray_manager.notify_opportunity(
                f"{best.home_team} vs {best.away_team}",
                best.roi * 100
            )
        
        if not analyses:
            show_notification(t("arbitrage.no_opportunities"), "info")
    
    def _on_fetch_error(self, error: str):
        """Handle fetch error."""
        self.fetch_btn.setEnabled(True)
        self.status_bar.showMessage(f"{t('common.error')}: {error}")
        show_notification(f"Error: {error}", "error")
    
    def _on_opportunity_selected(self, match_id: str):
        """Handle opportunity selection."""
        for analysis in self.analyses:
            if analysis.match_id == match_id:
                self.match_details.set_analysis(analysis)
                break
    
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
        self.mode_label.setText("🎮 Demo Mode" if self.demo_mode else "🌐 Live Mode")
        
        self._init_components()
        self.bankroll_label.setText(f"💰 ${self.stake_calc.config.bankroll:,.2f}")
        
        if hasattr(self, 'bankroll_panel'):
            self.bankroll_panel.set_bankroll_manager(self.bankroll_manager)
        
        show_notification(t("settings.saved"), "success")
    
    def _show_about(self):
        """Show about dialog."""
        dialog = AboutDialog(self)
        dialog.exec()
    
    def closeEvent(self, event):
        """Handle window close."""
        # Hide to tray instead of closing
        gui_config = self.config.get('gui', {})
        if gui_config.get('minimize_to_tray', False):
            event.ignore()
            self.hide()
            self.tray_manager.set_window_visible(False)
            return
        
        # Stop workers
        if self.fetch_worker and self.fetch_worker.isRunning():
            self.fetch_worker.terminate()
            self.fetch_worker.wait()
        
        self.refresh_timer.stop()
        self.tray_manager.hide()
        event.accept()


def run_gui_pro():
    """Run the premium GUI application with splash screen."""
    # Required for QWebEngineView to work properly
    from PyQt6.QtCore import Qt
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    
    app = QApplication(sys.argv)
    
    app.setApplicationName("Eden Analytics Pro")
    app.setOrganizationName("Eden Analytics")
    app.setApplicationVersion("3.0.0")
    
    # Create main window
    window = None
    
    def show_main_window():
        nonlocal window
        window = EdenMainWindowPro()
        window.show()
    
    # Show splash screen
    splash = show_splash_screen(app, show_main_window, duration=2500)
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(run_gui_pro())
