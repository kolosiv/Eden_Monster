"""Premium Dashboard Page for Eden Analytics Pro v3.0.0 Monster Edition."""

from typing import Optional, Dict, List
from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea,
    QFrame, QLabel, QPushButton, QSizePolicy, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPixmap, QColor, QLinearGradient, QPainter

from gui.themes.modern_theme import get_theme, get_logo_path
from gui.components.modern_widgets import (
    PremiumStatsCard, ModernCard, PremiumButton, ModernButton, SkeletonLoader
)
from gui.components.charts import BankrollChart, ROIChart, WinRateChart, PLOTLY_AVAILABLE

# Import guide system
try:
    from gui.guides.guide_system import GuideButton, GuideOverlay
    from gui.guides.guide_content import DASHBOARD_GUIDE
    from gui.animations.animations import AnimationManager
    GUIDES_AVAILABLE = True
except ImportError:
    GUIDES_AVAILABLE = False


class PremiumHeader(QFrame):
    """Premium animated header with gradient background."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("premiumHeader")
        self._setup_ui()
    
    def _setup_ui(self):
        import os
        theme = get_theme()
        p = theme.palette
        
        self.setStyleSheet(f"""
            #premiumHeader {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {p.primary}, stop:0.5 {p.secondary}, stop:1 {p.primary});
                border-radius: 20px;
                min-height: 140px;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        
        # Logo
        logo_path = get_logo_path('dark', 'horizontal')
        if os.path.exists(logo_path):
            logo_label = QLabel()
            pixmap = QPixmap(logo_path)
            scaled = pixmap.scaled(200, 90, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled)
            logo_label.setStyleSheet("background: transparent;")
            layout.addWidget(logo_label)
            layout.addSpacing(24)
        
        # Welcome text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(8)
        
        welcome = QLabel("Welcome to Eden Analytics Pro")
        welcome.setStyleSheet("""
            color: #000000;
            font-size: 32px;
            font-weight: 900;
            letter-spacing: -0.5px;
            background: transparent;
        """)
        text_layout.addWidget(welcome)
        
        subtitle = QLabel("🏒 Your intelligent hockey betting companion")
        subtitle.setStyleSheet("""
            color: rgba(0, 0, 0, 0.7);
            font-size: 16px;
            font-weight: 500;
            background: transparent;
        """)
        text_layout.addWidget(subtitle)
        
        # Status indicator
        status_container = QHBoxLayout()
        status_dot = QLabel("●")
        status_dot.setStyleSheet("color: #00FF88; font-size: 12px; background: transparent;")
        status_label = QLabel("System Online")
        status_label.setStyleSheet("""
            color: rgba(0, 0, 0, 0.6);
            font-size: 13px;
            font-weight: 600;
            background: transparent;
        """)
        status_container.addWidget(status_dot)
        status_container.addWidget(status_label)
        status_container.addStretch()
        text_layout.addLayout(status_container)
        
        layout.addLayout(text_layout)
        layout.addStretch()
        
        # Add premium shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(255, 215, 0, 100))
        shadow.setOffset(0, 10)
        self.setGraphicsEffect(shadow)


class QuickActionButton(QPushButton):
    """Premium quick action button with hover effects."""
    
    def __init__(self, icon: str, text: str, page: str, parent=None):
        super().__init__(f"{icon}  {text}", parent)
        self.page = page
        self._setup_style()
    
    def _setup_style(self):
        theme = get_theme()
        p = theme.palette
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {p.surface_light};
                color: {p.text};
                border: 1px solid {p.border};
                padding: 14px 20px;
                border-radius: 12px;
                text-align: left;
                font-size: 14px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {p.primary}, stop:1 {p.secondary});
                color: #000000;
                border: none;
            }}
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(50)


class ActivityItem(QFrame):
    """Premium activity list item."""
    
    def __init__(self, icon: str, description: str, time_str: str, 
                 item_type: str = "default", parent=None):
        super().__init__(parent)
        self._setup_ui(icon, description, time_str, item_type)
    
    def _setup_ui(self, icon: str, description: str, time_str: str, item_type: str):
        theme = get_theme()
        p = theme.palette
        
        type_colors = {
            'bet': p.secondary,
            'win': p.success,
            'loss': p.error,
            'arbitrage': p.primary,
            'model': p.warning,
            'default': p.text_muted
        }
        accent = type_colors.get(item_type, p.text_muted)
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {p.surface_light};
                border-radius: 12px;
                border-left: 3px solid {accent};
            }}
            QFrame:hover {{
                background-color: rgba({theme._hex_to_rgb(p.primary)}, 0.1);
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        
        # Icon
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 20px; background: transparent;")
        icon_label.setFixedWidth(32)
        layout.addWidget(icon_label)
        
        # Description
        desc_label = QLabel(description)
        desc_label.setStyleSheet(f"color: {p.text}; font-size: 13px; background: transparent;")
        layout.addWidget(desc_label, stretch=1)
        
        # Time
        time_label = QLabel(time_str)
        time_label.setStyleSheet(f"color: {p.text_muted}; font-size: 12px; background: transparent;")
        layout.addWidget(time_label)


class AlertItem(QFrame):
    """Premium alert item."""
    
    def __init__(self, message: str, alert_type: str = "info", parent=None):
        super().__init__(parent)
        self._setup_ui(message, alert_type)
    
    def _setup_ui(self, message: str, alert_type: str):
        theme = get_theme()
        p = theme.palette
        
        colors = {
            'info': p.secondary,
            'success': p.success,
            'warning': p.warning,
            'error': p.error
        }
        icons = {
            'info': 'ℹ️',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌'
        }
        
        color = colors.get(alert_type, p.secondary)
        icon = icons.get(alert_type, 'ℹ️')
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: rgba({theme._hex_to_rgb(color)}, 0.1);
                border-left: 3px solid {color};
                border-radius: 8px;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("background: transparent;")
        layout.addWidget(icon_label)
        
        msg_label = QLabel(message)
        msg_label.setStyleSheet(f"color: {p.text}; font-size: 13px; background: transparent;")
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label, stretch=1)


class DashboardPage(QWidget):
    """Premium main dashboard page with stats, charts, and activity."""
    
    # Signals
    navigate_to = pyqtSignal(str)
    refresh_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._stats = {}
        self._history = []
        self._animations = []
        
        self._setup_ui()
        
        # Animate entrance on first show
        QTimer.singleShot(100, self._animate_entrance)
    
    def _setup_ui(self):
        theme = get_theme()
        p = theme.palette
        
        # Main scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{ 
                border: none; 
                background: transparent; 
            }}
        """)
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 32, 32, 32)  # Increased margins
        layout.setSpacing(28)
        
        # Title row with guide button
        title_row = QHBoxLayout()
        title_row.setSpacing(20)
        
        title_label = QLabel("🏠 Панель управления")
        title_label.setStyleSheet(f"""
            QLabel {{
                font-size: 32px;
                font-weight: 900;
                color: {p.primary};
                letter-spacing: 0.5px;
            }}
        """)
        title_row.addWidget(title_label)
        title_row.addStretch()
        
        # Guide button
        if GUIDES_AVAILABLE:
            self.guide_btn = GuideButton("❓ Гайд")
            self.guide_btn.clicked.connect(self._show_guide)
            title_row.addWidget(self.guide_btn)
        
        layout.addLayout(title_row)
        
        # Premium Header
        header = PremiumHeader()
        layout.addWidget(header)
        
        # Stats Row
        stats_row = self._create_stats_row()
        layout.addLayout(stats_row)
        
        # Charts Row
        charts_row = self._create_charts_row()
        layout.addLayout(charts_row)
        
        # Bottom Row (Recent Activity + Quick Actions)
        bottom_row = self._create_bottom_row()
        layout.addLayout(bottom_row)
        
        layout.addStretch()
        
        scroll.setWidget(content)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
    
    def _create_stats_row(self) -> QHBoxLayout:
        """Create the premium stats cards row."""
        layout = QHBoxLayout()
        layout.setSpacing(20)
        
        theme = get_theme()
        p = theme.palette
        
        # Create premium stat cards
        self.stat_profit = PremiumStatsCard(
            "Total Profit", "$0.00", "💰", color=p.success
        )
        self.stat_roi = PremiumStatsCard(
            "ROI", "0.0%", "📈", color=p.secondary
        )
        self.stat_win_rate = PremiumStatsCard(
            "Win Rate", "0.0%", "🎯", color=p.primary
        )
        self.stat_active_bets = PremiumStatsCard(
            "Active Bets", "0", "🎲", color=p.warning
        )
        
        layout.addWidget(self.stat_profit)
        layout.addWidget(self.stat_roi)
        layout.addWidget(self.stat_win_rate)
        layout.addWidget(self.stat_active_bets)
        
        return layout
    
    def _create_charts_row(self) -> QHBoxLayout:
        """Create the charts row with premium styling."""
        layout = QHBoxLayout()
        layout.setSpacing(20)
        
        # Bankroll Chart Card
        bankroll_card = ModernCard("📊 Bankroll Growth")
        self.bankroll_chart = BankrollChart()
        bankroll_card.add_widget(self.bankroll_chart)
        layout.addWidget(bankroll_card, stretch=2)
        
        # ROI Chart Card
        roi_card = ModernCard("📈 ROI by Period")
        self.roi_chart = ROIChart()
        roi_card.add_widget(self.roi_chart)
        layout.addWidget(roi_card, stretch=1)
        
        return layout
    
    def _create_bottom_row(self) -> QHBoxLayout:
        """Create the bottom row with activity and quick actions."""
        layout = QHBoxLayout()
        layout.setSpacing(20)
        
        # Recent Activity Card
        activity_card = ModernCard("🕒 Recent Activity")
        self.activity_layout = QVBoxLayout()
        self.activity_layout.setSpacing(10)
        
        # Placeholder for activity items
        self.no_activity_label = QLabel("No recent activity")
        self.no_activity_label.setStyleSheet(f"""
            color: {get_theme().palette.text_muted}; 
            padding: 24px;
            font-size: 14px;
        """)
        self.no_activity_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.activity_layout.addWidget(self.no_activity_label)
        
        activity_card.content_layout.addLayout(self.activity_layout)
        layout.addWidget(activity_card, stretch=2)
        
        # Right side column
        side_layout = QVBoxLayout()
        side_layout.setSpacing(20)
        
        # Quick Actions Card
        actions_card = ModernCard("⚡ Quick Actions")
        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(10)
        
        actions = [
            ("🔍", "Find Arbitrage", "arbitrage"),
            ("📜", "View History", "history"),
            ("📊", "Analytics", "statistics"),
            ("🤖", "ML Models", "ml_models"),
            ("⚙️", "Settings", "settings")
        ]
        
        for icon, text, page in actions:
            btn = QuickActionButton(icon, text, page)
            btn.clicked.connect(lambda checked, p=page: self.navigate_to.emit(p))
            actions_layout.addWidget(btn)
        
        actions_card.content_layout.addLayout(actions_layout)
        side_layout.addWidget(actions_card)
        
        # Alerts Card
        alerts_card = ModernCard("🔔 Alerts")
        self.alerts_layout = QVBoxLayout()
        self.alerts_layout.setSpacing(10)
        
        self.no_alerts_label = QLabel("No alerts")
        self.no_alerts_label.setStyleSheet(f"""
            color: {get_theme().palette.text_muted}; 
            padding: 20px;
            font-size: 14px;
        """)
        self.no_alerts_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.alerts_layout.addWidget(self.no_alerts_label)
        
        alerts_card.content_layout.addLayout(self.alerts_layout)
        side_layout.addWidget(alerts_card)
        
        layout.addLayout(side_layout, stretch=1)
        
        return layout
    
    def update_stats(self, stats: Dict):
        """Update dashboard statistics with animations."""
        self._stats = stats
        
        profit = stats.get('total_profit', 0)
        roi = stats.get('roi', 0)
        win_rate = stats.get('win_rate', 0)
        active_bets = stats.get('active_bets', 0)
        
        # Get trends if available
        profit_trend = stats.get('profit_trend', None)
        roi_trend = stats.get('roi_trend', None)
        win_rate_trend = stats.get('win_rate_trend', None)
        
        # Update stat cards
        self.stat_profit.update_value(f"${profit:,.2f}", profit_trend)
        self.stat_roi.update_value(f"{roi:.1f}%", roi_trend)
        self.stat_win_rate.update_value(f"{win_rate:.1f}%", win_rate_trend)
        self.stat_active_bets.update_value(str(active_bets), None)
    
    def update_charts(self, bankroll_history: List[Dict], roi_data: List[Dict]):
        """Update dashboard charts."""
        if bankroll_history:
            self.bankroll_chart.update_data(bankroll_history)
        
        if roi_data:
            self.roi_chart.update_data(roi_data)
    
    def update_activity(self, activity: List[Dict]):
        """Update recent activity list with premium styling."""
        # Clear existing
        while self.activity_layout.count():
            item = self.activity_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not activity:
            self.no_activity_label = QLabel("No recent activity")
            self.no_activity_label.setStyleSheet(f"""
                color: {get_theme().palette.text_muted}; 
                padding: 24px;
                font-size: 14px;
            """)
            self.no_activity_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.activity_layout.addWidget(self.no_activity_label)
            return
        
        type_icons = {
            'bet': '🎲',
            'win': '✅',
            'loss': '❌',
            'arbitrage': '🔍',
            'model': '🤖'
        }
        
        for item in activity[:8]:  # Show last 8
            icon = type_icons.get(item.get('type', 'bet'), '📌')
            activity_item = ActivityItem(
                icon,
                item.get('description', 'Activity'),
                item.get('time', ''),
                item.get('type', 'default')
            )
            self.activity_layout.addWidget(activity_item)
    
    def add_alert(self, message: str, alert_type: str = "info"):
        """Add a premium alert to the dashboard."""
        # Remove "no alerts" label if present
        if hasattr(self, 'no_alerts_label') and self.no_alerts_label:
            self.no_alerts_label.deleteLater()
            self.no_alerts_label = None
        
        alert = AlertItem(message, alert_type)
        self.alerts_layout.addWidget(alert)
    
    def _animate_entrance(self):
        """Animate page entrance with smooth fade-in and slide effects."""
        if not GUIDES_AVAILABLE:
            return
        
        try:
            # Animate stat cards with staggered fade
            stat_widgets = [
                self.stat_profit,
                self.stat_roi,
                self.stat_win_rate,
                self.stat_active_bets
            ]
            
            for i, widget in enumerate(stat_widgets):
                QTimer.singleShot(i * 80, lambda w=widget: AnimationManager.fade_in(w, 400))
            
        except Exception:
            pass  # Animation failures shouldn't break the UI
    
    def _show_guide(self):
        """Show the interactive guide overlay."""
        if not GUIDES_AVAILABLE:
            return
        
        try:
            guide = GuideOverlay(self)
            guide.set_steps(DASHBOARD_GUIDE)
            guide.show()
            guide.resize(self.size())
        except Exception:
            pass  # Guide failures shouldn't break the UI


__all__ = ['DashboardPage', 'PremiumHeader', 'QuickActionButton', 'ActivityItem', 'AlertItem']
