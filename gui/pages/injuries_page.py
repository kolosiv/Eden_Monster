"""NHL Injuries Page for Eden Analytics Pro v3.0.0 Monster Edition.

Displays current NHL injuries with filtering, statistics and refresh functionality.
"""

import os
from typing import Optional, Dict, List
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea,
    QFrame, QLabel, QPushButton, QSizePolicy, QGraphicsDropShadowEffect,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QSpacerItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor

from gui.themes.modern_theme import get_theme
from gui.components.modern_widgets import ModernCard, PremiumButton, ModernButton

# Import injury parser
try:
    from data.injury_parser import InjuryParser, PlayerInjury
    INJURY_PARSER_AVAILABLE = True
except ImportError:
    INJURY_PARSER_AVAILABLE = False


class InjuryStatsCard(QFrame):
    """Card displaying injury statistics."""
    
    def __init__(self, title: str, value: str, icon: str = "🏥", color: str = None, parent=None):
        super().__init__(parent)
        self.setObjectName("injuryStatsCard")
        self._setup_ui(title, value, icon, color)
    
    def _setup_ui(self, title: str, value: str, icon: str, color: str):
        theme = get_theme()
        p = theme.palette
        
        bg_color = color or p.surface_light
        
        self.setStyleSheet(f"""
            #injuryStatsCard {{
                background-color: {bg_color};
                border-radius: 16px;
                border: 1px solid {p.border};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)
        
        # Icon and title
        header = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"font-size: 24px; background: transparent;")
        header.addWidget(icon_label)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            color: {p.text_secondary};
            font-size: 13px;
            font-weight: 500;
            background: transparent;
        """)
        header.addWidget(title_label)
        header.addStretch()
        layout.addLayout(header)
        
        # Value
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"""
            color: {p.text};
            font-size: 32px;
            font-weight: 700;
            background: transparent;
        """)
        layout.addWidget(self.value_label)
        
        # Shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)
        
        self.setMinimumWidth(180)
        self.setMinimumHeight(110)
    
    def update_value(self, value: str):
        """Update the displayed value."""
        self.value_label.setText(value)


class InjuryFilterBar(QFrame):
    """Filter bar for injury data."""
    
    filter_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("filterBar")
        self._setup_ui()
    
    def _setup_ui(self):
        theme = get_theme()
        p = theme.palette
        
        self.setStyleSheet(f"""
            #filterBar {{
                background-color: {p.surface};
                border-radius: 12px;
                border: 1px solid {p.border};
            }}
            QComboBox {{
                background-color: {p.surface_light};
                color: {p.text};
                border: 1px solid {p.border};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                min-width: 150px;
            }}
            QComboBox:hover {{
                border-color: {p.primary};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {p.surface_light};
                color: {p.text};
                selection-background-color: {p.primary};
                border: 1px solid {p.border};
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)
        
        # Team filter
        team_label = QLabel("🏒 Team:")
        team_label.setStyleSheet(f"color: {p.text}; font-size: 13px; font-weight: 500;")
        layout.addWidget(team_label)
        
        self.team_filter = QComboBox()
        self.team_filter.addItem("All Teams", "all")
        self._populate_teams()
        self.team_filter.currentIndexChanged.connect(self.filter_changed.emit)
        layout.addWidget(self.team_filter)
        
        layout.addSpacing(20)
        
        # Status filter
        status_label = QLabel("📋 Status:")
        status_label.setStyleSheet(f"color: {p.text}; font-size: 13px; font-weight: 500;")
        layout.addWidget(status_label)
        
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All Statuses", "Day-to-Day", "IR", "LTIR", "Out", "GTD"])
        self.status_filter.currentIndexChanged.connect(self.filter_changed.emit)
        layout.addWidget(self.status_filter)
        
        layout.addStretch()
        
        # Last updated label
        self.last_updated = QLabel("Last updated: Never")
        self.last_updated.setStyleSheet(f"""
            color: {p.text_secondary};
            font-size: 12px;
        """)
        layout.addWidget(self.last_updated)
    
    def _populate_teams(self):
        """Populate team filter with NHL teams."""
        teams = [
            ('ANA', 'Anaheim Ducks'), ('ARI', 'Arizona Coyotes'), ('BOS', 'Boston Bruins'),
            ('BUF', 'Buffalo Sabres'), ('CGY', 'Calgary Flames'), ('CAR', 'Carolina Hurricanes'),
            ('CHI', 'Chicago Blackhawks'), ('COL', 'Colorado Avalanche'), ('CBJ', 'Columbus Blue Jackets'),
            ('DAL', 'Dallas Stars'), ('DET', 'Detroit Red Wings'), ('EDM', 'Edmonton Oilers'),
            ('FLA', 'Florida Panthers'), ('LAK', 'Los Angeles Kings'), ('MIN', 'Minnesota Wild'),
            ('MTL', 'Montreal Canadiens'), ('NSH', 'Nashville Predators'), ('NJD', 'New Jersey Devils'),
            ('NYI', 'New York Islanders'), ('NYR', 'New York Rangers'), ('OTT', 'Ottawa Senators'),
            ('PHI', 'Philadelphia Flyers'), ('PIT', 'Pittsburgh Penguins'), ('SJS', 'San Jose Sharks'),
            ('SEA', 'Seattle Kraken'), ('STL', 'St. Louis Blues'), ('TBL', 'Tampa Bay Lightning'),
            ('TOR', 'Toronto Maple Leafs'), ('UTA', 'Utah Hockey Club'), ('VAN', 'Vancouver Canucks'),
            ('VGK', 'Vegas Golden Knights'), ('WSH', 'Washington Capitals'), ('WPG', 'Winnipeg Jets')
        ]
        for abbrev, name in teams:
            self.team_filter.addItem(f"{abbrev} - {name}", abbrev)
    
    def get_team_filter(self) -> str:
        """Get current team filter value."""
        return self.team_filter.currentData() or "all"
    
    def get_status_filter(self) -> str:
        """Get current status filter value."""
        status = self.status_filter.currentText()
        return status if status != "All Statuses" else "all"
    
    def update_last_refresh(self):
        """Update last refresh timestamp."""
        now = datetime.now().strftime("%H:%M:%S")
        self.last_updated.setText(f"Last updated: {now}")


class InjuriesTable(QTableWidget):
    """Table displaying NHL injuries."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        theme = get_theme()
        p = theme.palette
        
        # Set columns
        self.setColumnCount(7)
        self.setHorizontalHeaderLabels([
            "Player", "Team", "Position", "Injury Type", "Status", "Impact", "Games Missed"
        ])
        
        # Style
        self.setStyleSheet(f"""
            QTableWidget {{
                background-color: {p.surface};
                color: {p.text};
                border: none;
                border-radius: 12px;
                gridline-color: {p.border};
                font-size: 13px;
            }}
            QTableWidget::item {{
                padding: 12px 8px;
                border-bottom: 1px solid {p.border};
            }}
            QTableWidget::item:selected {{
                background-color: rgba(255, 215, 0, 0.15);
            }}
            QHeaderView::section {{
                background-color: {p.surface_light};
                color: {p.text};
                padding: 12px 8px;
                border: none;
                border-bottom: 2px solid {p.primary};
                font-weight: 600;
                font-size: 12px;
            }}
            QScrollBar:vertical {{
                background: {p.surface};
                width: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: {p.text_secondary};
                border-radius: 5px;
                min-height: 30px;
            }}
        """)
        
        # Configure header
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Player
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)   # Team
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)   # Position
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch) # Injury Type
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)   # Status
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)   # Impact
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)   # Games Missed
        
        self.setColumnWidth(1, 80)   # Team
        self.setColumnWidth(2, 70)   # Position
        self.setColumnWidth(4, 120)  # Status
        self.setColumnWidth(5, 100)  # Impact
        self.setColumnWidth(6, 100)  # Games Missed
        
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    
    def load_injuries(self, injuries: List[Dict], team_filter: str = "all", status_filter: str = "all"):
        """Load injuries into table with filtering."""
        theme = get_theme()
        p = theme.palette
        
        # Filter injuries
        filtered = injuries
        if team_filter != "all":
            filtered = [i for i in filtered if i.get('team') == team_filter]
        if status_filter != "all":
            status_map = {
                "Day-to-Day": "DTD", "IR": "IR", "LTIR": "LTIR", 
                "Out": "OUT", "GTD": "GTD"
            }
            status_code = status_map.get(status_filter, status_filter)
            filtered = [i for i in filtered if i.get('status') == status_code]
        
        self.setRowCount(len(filtered))
        
        for row, injury in enumerate(filtered):
            # Player name
            player_item = QTableWidgetItem(injury.get('player_name', 'Unknown'))
            player_item.setForeground(QColor(p.text))
            self.setItem(row, 0, player_item)
            
            # Team
            team_item = QTableWidgetItem(injury.get('team', ''))
            team_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row, 1, team_item)
            
            # Position
            pos_item = QTableWidgetItem(injury.get('position', ''))
            pos_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row, 2, pos_item)
            
            # Injury Type
            type_item = QTableWidgetItem(injury.get('injury_type', 'Unknown'))
            self.setItem(row, 3, type_item)
            
            # Status with color coding
            status = injury.get('status', 'Unknown')
            status_display = {
                'DTD': '🟡 Day-to-Day',
                'IR': '🔴 IR',
                'LTIR': '⚫ LTIR',
                'OUT': '🔴 Out',
                'GTD': '🟠 GTD',
                'SUSP': '🟣 Suspended'
            }.get(status, status)
            status_item = QTableWidgetItem(status_display)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row, 4, status_item)
            
            # Impact rating with color
            impact = injury.get('impact_rating', 0)
            impact_item = QTableWidgetItem(f"{'⭐' * int(impact/2)} {impact:.1f}")
            if impact >= 8:
                impact_item.setForeground(QColor("#FF4444"))
            elif impact >= 6:
                impact_item.setForeground(QColor("#FFA500"))
            else:
                impact_item.setForeground(QColor("#FFD700"))
            impact_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row, 5, impact_item)
            
            # Games missed
            games = injury.get('games_missed', 0)
            games_item = QTableWidgetItem(str(games))
            games_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row, 6, games_item)
        
        return len(filtered)


class InjuriesPage(QWidget):
    """Main injuries tracking page for Eden Analytics Pro."""
    
    refresh_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("injuriesPage")
        
        self._injuries = []
        self._stats = {}
        self._db_path = None
        self._auto_refresh_timer = None
        
        self._setup_ui()
        self._setup_auto_refresh()
    
    def _setup_ui(self):
        theme = get_theme()
        p = theme.palette
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_layout = QVBoxLayout()
        title = QLabel("🏥 NHL Injuries Tracker")
        title.setStyleSheet(f"""
            color: {p.text};
            font-size: 28px;
            font-weight: 700;
        """)
        title_layout.addWidget(title)
        
        subtitle = QLabel("Monitor player injuries affecting predictions • Model v5.0 Integration")
        subtitle.setStyleSheet(f"""
            color: {p.text_secondary};
            font-size: 14px;
        """)
        title_layout.addWidget(subtitle)
        header_layout.addLayout(title_layout)
        
        header_layout.addStretch()
        
        # Refresh button
        self.refresh_btn = PremiumButton("🔄  Refresh Data")
        self.refresh_btn.setFixedWidth(160)
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        header_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Stats cards
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)
        
        self.total_card = InjuryStatsCard("Total Injuries", "0", "🏥")
        stats_layout.addWidget(self.total_card)
        
        self.high_impact_card = InjuryStatsCard("High Impact", "0", "⚠️", color="rgba(255, 68, 68, 0.15)")
        stats_layout.addWidget(self.high_impact_card)
        
        self.ir_card = InjuryStatsCard("On IR", "0", "🔴")
        stats_layout.addWidget(self.ir_card)
        
        self.dtd_card = InjuryStatsCard("Day-to-Day", "0", "🟡")
        stats_layout.addWidget(self.dtd_card)
        
        self.teams_affected_card = InjuryStatsCard("Teams Affected", "0", "🏒")
        stats_layout.addWidget(self.teams_affected_card)
        
        layout.addLayout(stats_layout)
        
        # Filter bar
        self.filter_bar = InjuryFilterBar()
        self.filter_bar.filter_changed.connect(self._apply_filters)
        layout.addWidget(self.filter_bar)
        
        # Injuries table
        self.injuries_table = InjuriesTable()
        layout.addWidget(self.injuries_table, 1)
        
        # Model impact info
        model_info = QFrame()
        model_info.setObjectName("modelInfo")
        model_info.setStyleSheet(f"""
            #modelInfo {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(255, 215, 0, 0.1), stop:1 rgba(255, 140, 0, 0.1));
                border-radius: 12px;
                border: 1px solid rgba(255, 215, 0, 0.3);
            }}
        """)
        model_layout = QHBoxLayout(model_info)
        model_layout.setContentsMargins(16, 12, 16, 12)
        
        info_icon = QLabel("🤖")
        info_icon.setStyleSheet("font-size: 20px;")
        model_layout.addWidget(info_icon)
        
        info_text = QLabel(
            "<b>Model v5.0 Integration:</b> Injuries are automatically factored into predictions. "
            "12 injury-based features enhance accuracy by ~3-5%. High-impact injuries (⭐7+) "
            "significantly affect team performance projections."
        )
        info_text.setStyleSheet(f"color: {p.text}; font-size: 13px;")
        info_text.setWordWrap(True)
        model_layout.addWidget(info_text, 1)
        
        layout.addWidget(model_info)
    
    def _setup_auto_refresh(self):
        """Setup automatic refresh timer (every 5 minutes)."""
        self._auto_refresh_timer = QTimer(self)
        self._auto_refresh_timer.timeout.connect(self._on_refresh_clicked)
        self._auto_refresh_timer.start(300000)  # 5 minutes
    
    def set_database_path(self, db_path: str):
        """Set the database path for injury data."""
        self._db_path = db_path
        self.load_injuries()
    
    def load_injuries(self):
        """Load injuries from database."""
        if not self._db_path or not INJURY_PARSER_AVAILABLE:
            return
        
        try:
            parser = InjuryParser(self._db_path)
            self._injuries = parser.get_all_injuries()
            self._stats = parser.get_injury_stats()
            self._update_display()
            self.filter_bar.update_last_refresh()
        except Exception as e:
            print(f"Error loading injuries: {e}")
    
    def _update_display(self):
        """Update all display elements."""
        # Update stats cards
        self.total_card.update_value(str(self._stats.get('total_active', 0)))
        self.high_impact_card.update_value(str(self._stats.get('high_impact', 0)))
        
        by_status = self._stats.get('by_status', {})
        ir_count = by_status.get('IR', 0) + by_status.get('LTIR', 0)
        self.ir_card.update_value(str(ir_count))
        self.dtd_card.update_value(str(by_status.get('DTD', 0)))
        
        teams_affected = len(self._stats.get('most_injuries', []))
        self.teams_affected_card.update_value(str(teams_affected))
        
        # Update table
        self._apply_filters()
    
    def _apply_filters(self):
        """Apply current filters to table."""
        team = self.filter_bar.get_team_filter()
        status = self.filter_bar.get_status_filter()
        count = self.injuries_table.load_injuries(self._injuries, team, status)
    
    def _on_refresh_clicked(self):
        """Handle refresh button click."""
        if not self._db_path or not INJURY_PARSER_AVAILABLE:
            return
        
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("⏳ Refreshing...")
        
        try:
            parser = InjuryParser(self._db_path)
            parser.update_injuries()
            self.load_injuries()
        except Exception as e:
            print(f"Error refreshing injuries: {e}")
        finally:
            self.refresh_btn.setEnabled(True)
            self.refresh_btn.setText("🔄  Refresh Data")
        
        self.refresh_requested.emit()
    
    def get_team_injuries(self, team: str) -> List[Dict]:
        """Get injuries for a specific team."""
        return [i for i in self._injuries if i.get('team') == team]
    
    def get_high_impact_injuries(self) -> List[Dict]:
        """Get all high-impact injuries (7+)."""
        return [i for i in self._injuries if i.get('impact_rating', 0) >= 7.0]
