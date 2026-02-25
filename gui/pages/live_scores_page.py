"""Live Scores Page for Eden Analytics Pro v2.4.0.

Displays real-time NHL game scores with auto-refresh functionality.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QGridLayout, QCheckBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont

from gui.themes.modern_theme import get_theme
from localization import t
from core.live_scores import NHLLiveScores, GameInfo, GameState
from utils.logger import get_logger

# Import guide system
try:
    from gui.guides.guide_system import GuideButton, GuideOverlay
    from gui.guides.guide_content import LIVE_SCORES_GUIDE
    from gui.animations.animations import AnimationManager
    GUIDES_AVAILABLE = True
except ImportError:
    GUIDES_AVAILABLE = False

logger = get_logger(__name__)


class GameCardWidget(QFrame):
    """Widget displaying a single game's information."""
    
    clicked = pyqtSignal(int)  # game_id
    
    def __init__(self, game: GameInfo, parent=None):
        super().__init__(parent)
        self.game = game
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the game card UI."""
        self.setObjectName("gameCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        theme = get_theme()
        p = theme.palette
        
        # Card styling based on game state
        if self.game.status == GameState.LIVE:
            border_color = "#FF4757"  # Red for live
            glow = "rgba(255, 71, 87, 0.3)"
        elif self.game.status == GameState.FINAL:
            border_color = p.text_secondary
            glow = "transparent"
        else:
            border_color = p.primary
            glow = "transparent"
        
        self.setStyleSheet(f"""
            #gameCard {{
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid {border_color};
                border-radius: 16px;
                padding: 16px;
            }}
            #gameCard:hover {{
                background: rgba(255, 255, 255, 0.08);
                border: 2px solid {border_color};
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Away team section
        away_section = self._create_team_section(
            self.game.away_team,
            self.game.away_team_full,
            self.game.away_score,
            is_winner=self.game.away_score > self.game.home_score and self.game.status == GameState.FINAL
        )
        layout.addLayout(away_section)
        
        # Center section (status/score)
        center_section = self._create_center_section()
        layout.addLayout(center_section)
        
        # Home team section
        home_section = self._create_team_section(
            self.game.home_team,
            self.game.home_team_full,
            self.game.home_score,
            is_winner=self.game.home_score > self.game.away_score and self.game.status == GameState.FINAL
        )
        layout.addLayout(home_section)
    
    def _create_team_section(self, abbrev: str, full_name: str, score: int, is_winner: bool = False) -> QVBoxLayout:
        """Create a team section with logo placeholder, name, and score."""
        theme = get_theme()
        p = theme.palette
        
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)
        
        # Team abbreviation (acts as logo placeholder)
        abbrev_label = QLabel(abbrev)
        abbrev_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        weight = "900" if is_winner else "700"
        abbrev_label.setStyleSheet(f"""
            QLabel {{
                font-size: 28px;
                font-weight: {weight};
                color: {p.primary if is_winner else p.text};
            }}
        """)
        layout.addWidget(abbrev_label)
        
        # Score
        score_label = QLabel(str(score))
        score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        score_color = p.primary if is_winner else p.text
        score_label.setStyleSheet(f"""
            QLabel {{
                font-size: 42px;
                font-weight: 900;
                color: {score_color};
            }}
        """)
        layout.addWidget(score_label)
        
        # Full team name
        name_label = QLabel(full_name[:15] + "..." if len(full_name) > 15 else full_name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet(f"""
            QLabel {{
                font-size: 12px;
                color: {p.text_secondary};
            }}
        """)
        layout.addWidget(name_label)
        
        return layout
    
    def _create_center_section(self) -> QVBoxLayout:
        """Create center section with game status."""
        theme = get_theme()
        p = theme.palette
        
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)
        
        # Status badge
        status_label = QLabel(self._get_status_text())
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        status_color, status_bg = self._get_status_colors()
        status_label.setStyleSheet(f"""
            QLabel {{
                background: {status_bg};
                color: {status_color};
                padding: 6px 16px;
                border-radius: 12px;
                font-size: 13px;
                font-weight: 700;
            }}
        """)
        layout.addWidget(status_label)
        
        # VS label
        vs_label = QLabel("VS")
        vs_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vs_label.setStyleSheet(f"""
            QLabel {{
                font-size: 16px;
                font-weight: 600;
                color: {p.text_secondary};
                margin: 8px 0;
            }}
        """)
        layout.addWidget(vs_label)
        
        # Period/Time info for live games
        if self.game.status in (GameState.LIVE, GameState.OFF, GameState.CRITICAL):
            time_info = QLabel(self._get_time_info())
            time_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
            time_info.setStyleSheet(f"""
                QLabel {{
                    font-size: 14px;
                    font-weight: 600;
                    color: #00FF88;
                }}
            """)
            layout.addWidget(time_info)
        elif self.game.status == GameState.SCHEDULED:
            # Show start time
            start_time = self._format_start_time()
            time_label = QLabel(start_time)
            time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            time_label.setStyleSheet(f"""
                QLabel {{
                    font-size: 14px;
                    color: {p.text_secondary};
                }}
            """)
            layout.addWidget(time_label)
        
        return layout
    
    def _get_status_text(self) -> str:
        """Get localized status text."""
        if self.game.status == GameState.LIVE:
            return f"🔴 {t('live_scores.live')}"
        elif self.game.status == GameState.FINAL:
            suffix = ""
            if self.game.is_shootout:
                suffix = f"/{t('live_scores.so')}"
            elif self.game.is_overtime:
                suffix = f"/{t('live_scores.ot')}"
            return f"{t('live_scores.final')}{suffix}"
        elif self.game.status == GameState.OFF:
            return t('live_scores.intermission')
        elif self.game.status == GameState.POSTPONED:
            return t('live_scores.postponed')
        return t('live_scores.scheduled')
    
    def _get_status_colors(self) -> tuple:
        """Get status colors (text, background)."""
        if self.game.status == GameState.LIVE:
            return "#FF4757", "rgba(255, 71, 87, 0.2)"
        elif self.game.status == GameState.FINAL:
            return "#B4B4C8", "rgba(180, 180, 200, 0.15)"
        elif self.game.status == GameState.OFF:
            return "#FFD700", "rgba(255, 215, 0, 0.2)"
        return "#00D9FF", "rgba(0, 217, 255, 0.15)"
    
    def _get_time_info(self) -> str:
        """Get period and time remaining info."""
        period = self.game.period
        time_rem = self.game.time_remaining
        
        if self.game.is_shootout:
            return t('live_scores.shootout')
        elif self.game.is_overtime:
            return f"{t('live_scores.overtime')} {time_rem}"
        elif self.game.status == GameState.OFF:
            return f"{t('live_scores.intermission')} {period}"
        elif period > 0:
            return f"{t('live_scores.period')} {period} • {time_rem}"
        return time_rem
    
    def _format_start_time(self) -> str:
        """Format start time for display."""
        from datetime import datetime
        try:
            if self.game.start_time_utc:
                dt = datetime.fromisoformat(self.game.start_time_utc.replace('Z', '+00:00'))
                return dt.strftime('%H:%M')
        except:
            pass
        return ""
    
    def mousePressEvent(self, event):
        """Handle click to emit game_id."""
        self.clicked.emit(self.game.game_id)
        super().mousePressEvent(event)
    
    def update_game(self, game: GameInfo):
        """Update the game data and refresh display."""
        self.game = game
        # Clear and rebuild
        while self.layout().count():
            item = self.layout().takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
        
        self._setup_ui()
    
    def _clear_layout(self, layout):
        """Recursively clear a layout."""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())


class LiveScoresPage(QWidget):
    """Live scores page with real-time NHL game updates."""
    
    def __init__(self):
        super().__init__()
        self.live_scores = NHLLiveScores()
        self.auto_refresh = True
        self.refresh_interval = 30  # seconds
        self.game_cards: dict = {}  # game_id -> GameCardWidget
        
        self._init_ui()
        self._start_auto_refresh()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
        header = self._create_header()
        layout.addWidget(header)
        
        # Controls bar
        controls = self._create_controls()
        layout.addWidget(controls)
        
        # Games scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
        """)
        
        # Games container
        self.games_container = QWidget()
        self.games_layout = QVBoxLayout(self.games_container)
        self.games_layout.setSpacing(16)
        self.games_layout.setContentsMargins(0, 0, 0, 0)
        self.games_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll.setWidget(self.games_container)
        layout.addWidget(scroll)
        
        # Initial load
        self._refresh_scores()
    
    def _create_header(self) -> QFrame:
        """Create page header with guide button."""
        theme = get_theme()
        p = theme.palette
        
        header = QFrame()
        main_layout = QVBoxLayout(header)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Title row with guide button
        title_row = QHBoxLayout()
        title_row.setSpacing(20)
        
        # Title with icon
        title = QLabel(f"🏒 {t('live_scores.title')}")
        title.setStyleSheet(f"""
            QLabel {{
                font-size: 32px;
                font-weight: 900;
                color: {p.primary};
                letter-spacing: 0.5px;
            }}
        """)
        title_row.addWidget(title)
        title_row.addStretch()
        
        # Guide button
        if GUIDES_AVAILABLE:
            self.guide_btn = GuideButton("❓ Гайд")
            self.guide_btn.clicked.connect(self._show_guide)
            title_row.addWidget(self.guide_btn)
        
        main_layout.addLayout(title_row)
        
        # Subtitle
        subtitle = QLabel(t('live_scores.subtitle'))
        subtitle.setStyleSheet(f"""
            QLabel {{
                font-size: 14px;
                color: {p.text_secondary};
            }}
        """)
        main_layout.addWidget(subtitle)
        
        return header
    
    def _create_controls(self) -> QFrame:
        """Create control bar with refresh button and auto-refresh toggle."""
        theme = get_theme()
        p = theme.palette
        
        controls = QFrame()
        layout = QHBoxLayout(controls)
        layout.setContentsMargins(0, 10, 0, 10)
        
        # Refresh button
        self.refresh_btn = QPushButton(f"🔄 {t('live_scores.refresh')}")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self._refresh_scores)
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {p.primary}, stop:1 {p.secondary});
                color: #000000;
                border: none;
                border-radius: 12px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {p.secondary}, stop:1 {p.primary});
            }}
            QPushButton:disabled {{
                background: {p.border};
                color: {p.text_secondary};
            }}
        """)
        layout.addWidget(self.refresh_btn)
        
        # Auto-refresh toggle
        self.auto_refresh_check = QCheckBox(t('live_scores.auto_refresh'))
        self.auto_refresh_check.setChecked(self.auto_refresh)
        self.auto_refresh_check.stateChanged.connect(self._toggle_auto_refresh)
        self.auto_refresh_check.setCursor(Qt.CursorShape.PointingHandCursor)
        self.auto_refresh_check.setStyleSheet(f"""
            QCheckBox {{
                color: {p.text};
                font-size: 14px;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 2px solid {p.border};
                background: transparent;
            }}
            QCheckBox::indicator:checked {{
                background: {p.primary};
                border-color: {p.primary};
            }}
            QCheckBox::indicator:hover {{
                border-color: {p.primary};
            }}
        """)
        layout.addWidget(self.auto_refresh_check)
        
        layout.addStretch()
        
        # Last updated label
        self.last_updated_label = QLabel("")
        self.last_updated_label.setStyleSheet(f"""
            QLabel {{
                font-size: 12px;
                color: {p.text_secondary};
            }}
        """)
        layout.addWidget(self.last_updated_label)
        
        return controls
    
    def _refresh_scores(self):
        """Refresh live scores data."""
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText(f"⏳ {t('live_scores.loading_games')}")
        
        try:
            # Clear cache and fetch fresh data
            self.live_scores.clear_cache()
            games = self.live_scores.get_todays_games(use_cache=False)
            
            self._update_games_display(games)
            
            # Update last updated timestamp
            from datetime import datetime
            now = datetime.now().strftime('%H:%M:%S')
            self.last_updated_label.setText(f"{t('live_scores.last_updated')}: {now}")
            
        except Exception as e:
            logger.error(f"Error refreshing scores: {e}")
            self._show_error_message()
        
        finally:
            self.refresh_btn.setEnabled(True)
            self.refresh_btn.setText(f"🔄 {t('live_scores.refresh')}")
    
    def _update_games_display(self, games: list):
        """Update the games display."""
        theme = get_theme()
        p = theme.palette
        
        # If no games, show message
        if not games:
            self._clear_games_layout()
            
            no_games_label = QLabel(f"📅 {t('live_scores.no_games')}")
            no_games_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_games_label.setStyleSheet(f"""
                QLabel {{
                    font-size: 18px;
                    color: {p.text_secondary};
                    padding: 40px;
                }}
            """)
            self.games_layout.addWidget(no_games_label)
            return
        
        # Sort games: live first, then scheduled, then final
        def sort_key(g):
            if g.status in (GameState.LIVE, GameState.CRITICAL, GameState.OFF):
                return (0, g.start_time_utc)
            elif g.status == GameState.SCHEDULED:
                return (1, g.start_time_utc)
            return (2, g.start_time_utc)
        
        games.sort(key=sort_key)
        
        # Check if we need to rebuild or just update
        current_game_ids = set(self.game_cards.keys())
        new_game_ids = {g.game_id for g in games}
        
        if current_game_ids != new_game_ids:
            # Rebuild entirely
            self._clear_games_layout()
            self.game_cards.clear()
            
            for game in games:
                card = GameCardWidget(game)
                card.clicked.connect(self._on_game_clicked)
                self.game_cards[game.game_id] = card
                self.games_layout.addWidget(card)
        else:
            # Just update existing cards
            for game in games:
                if game.game_id in self.game_cards:
                    self.game_cards[game.game_id].update_game(game)
        
        # Add stretch at end
        self.games_layout.addStretch()
    
    def _clear_games_layout(self):
        """Clear all items from games layout."""
        while self.games_layout.count():
            item = self.games_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def _show_error_message(self):
        """Show error message in the games area."""
        theme = get_theme()
        p = theme.palette
        
        self._clear_games_layout()
        
        error_label = QLabel(f"⚠️ {t('live_scores.connection_error')}")
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_label.setStyleSheet(f"""
            QLabel {{
                font-size: 16px;
                color: {p.error};
                padding: 40px;
            }}
        """)
        self.games_layout.addWidget(error_label)
    
    def _on_game_clicked(self, game_id: int):
        """Handle game card click."""
        logger.info(f"Game clicked: {game_id}")
        # Could open detailed view in future
    
    def _toggle_auto_refresh(self, state):
        """Toggle auto-refresh on/off."""
        self.auto_refresh = bool(state)
        if self.auto_refresh:
            self.timer.start(self.refresh_interval * 1000)
            logger.info("Auto-refresh enabled")
        else:
            self.timer.stop()
            logger.info("Auto-refresh disabled")
    
    def _start_auto_refresh(self):
        """Start the auto-refresh timer."""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_scores)
        if self.auto_refresh:
            self.timer.start(self.refresh_interval * 1000)
    
    def showEvent(self, event):
        """Called when page becomes visible."""
        super().showEvent(event)
        # Refresh when page is shown
        self._refresh_scores()
    
    def hideEvent(self, event):
        """Called when page is hidden."""
        super().hideEvent(event)
        # Could pause timer here if needed
    
    def _show_guide(self):
        """Show the interactive guide overlay."""
        if not GUIDES_AVAILABLE:
            return
        
        try:
            guide = GuideOverlay(self)
            guide.set_steps(LIVE_SCORES_GUIDE)
            guide.show()
            guide.resize(self.size())
        except Exception:
            pass  # Guide failures shouldn't break the UI


__all__ = ['LiveScoresPage']
