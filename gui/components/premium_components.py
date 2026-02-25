"""Premium UI Components with Fixed Spacing and Modern Design for Eden Analytics Pro v2.4.0."""

from typing import Optional, List, Callable
from PyQt6.QtWidgets import (
    QWidget, QPushButton, QFrame, QLabel, QVBoxLayout, QHBoxLayout,
    QGraphicsDropShadowEffect, QSizePolicy, QGraphicsOpacityEffect
)
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, QTimer,
    QPoint, QSize, QRect, QParallelAnimationGroup
)
from PyQt6.QtGui import QColor, QFont

from gui.themes.modern_theme import get_theme


class PremiumButton(QPushButton):
    """Premium styled button with gradient, proper spacing, and animations."""
    
    def __init__(self, text: str = "", icon=None, style: str = "primary", parent=None):
        super().__init__(text, parent)
        self._style = style
        self._hover = False
        
        if icon:
            self.setIcon(icon)
            self.setIconSize(QSize(22, 22))
        
        # Increased minimum sizes for better spacing
        self.setMinimumHeight(48)
        self.setMinimumWidth(140)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()
        self._add_shadow()
    
    def _add_shadow(self):
        """Add premium shadow effect."""
        shadow = QGraphicsDropShadowEffect(self)
        theme = get_theme()
        if self._style == 'primary':
            shadow.setBlurRadius(25)
            shadow.setColor(QColor(255, 215, 0, 120))
            shadow.setOffset(0, 5)
        else:
            shadow.setBlurRadius(20)
            shadow.setColor(QColor(0, 0, 0, 80))
            shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)
    
    def _update_style(self):
        theme = get_theme()
        p = theme.palette
        
        styles = {
            'primary': f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #FFD700, stop:1 #00D9FF);
                    color: #000000;
                    border: none;
                    border-radius: 12px;
                    padding: 14px 28px;
                    font-size: 15px;
                    font-weight: 600;
                    letter-spacing: 0.5px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #00D9FF, stop:1 #FFD700);
                }}
                QPushButton:pressed {{
                    padding: 15px 27px 13px 29px;
                }}
                QPushButton:disabled {{
                    background: {p.surface_light};
                    color: {p.text_muted};
                }}
            """,
            'secondary': f"""
                QPushButton {{
                    background: transparent;
                    color: {p.text};
                    border: 2px solid {p.primary};
                    border-radius: 12px;
                    padding: 13px 26px;
                    font-size: 14px;
                    font-weight: 600;
                    letter-spacing: 0.3px;
                }}
                QPushButton:hover {{
                    background: rgba(255, 215, 0, 0.15);
                    border-color: #00D9FF;
                }}
                QPushButton:pressed {{
                    background: rgba(255, 215, 0, 0.25);
                }}
            """,
            'ghost': f"""
                QPushButton {{
                    background: rgba(255, 255, 255, 0.05);
                    color: {p.text};
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 12px;
                    padding: 13px 26px;
                    font-size: 14px;
                    letter-spacing: 0.3px;
                }}
                QPushButton:hover {{
                    background: rgba(255, 255, 255, 0.12);
                    border-color: {p.primary};
                }}
            """,
            'danger': f"""
                QPushButton {{
                    background: {p.error};
                    color: white;
                    border: none;
                    border-radius: 12px;
                    padding: 13px 26px;
                    font-size: 14px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: #ff6b6b;
                }}
            """,
            'success': f"""
                QPushButton {{
                    background: {p.success};
                    color: #000000;
                    border: none;
                    border-radius: 12px;
                    padding: 13px 26px;
                    font-size: 14px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: #00ff99;
                }}
            """
        }
        
        self.setStyleSheet(styles.get(self._style, styles['primary']))


class PremiumStatsCard(QFrame):
    """Premium stat card with icon, value, trend, proper spacing and glow effects."""
    
    def __init__(self, title: str, value: str, icon: str = "📊",
                 trend: str = None, color: str = None, parent=None):
        super().__init__(parent)
        self.setObjectName("statsCard")
        self._title = title
        self._value = value
        self._icon = icon
        self._trend = trend
        self._color = color
        
        # Increased minimum size for better spacing
        self.setMinimumHeight(160)
        self.setMinimumWidth(240)
        
        self._setup_ui()
    
    def _setup_ui(self):
        theme = get_theme()
        p = theme.palette
        accent = self._color or p.primary
        
        self.setStyleSheet(f"""
            #statsCard {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {p.surface}, stop:1 {p.card});
                border-radius: 20px;
                border-left: 4px solid {accent};
            }}
            #statsCard:hover {{
                border: 1px solid rgba(255, 215, 0, 0.3);
                border-left: 4px solid {accent};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(14)  # Increased spacing
        layout.setContentsMargins(26, 26, 26, 26)  # Increased margins
        
        # Icon with proper size
        icon_label = QLabel(self._icon)
        icon_label.setStyleSheet(f"""
            QLabel {{
                font-size: 38px;
                color: {accent};
                min-height: 45px;
                background: transparent;
            }}
        """)
        layout.addWidget(icon_label)
        
        # Title with proper spacing
        title_label = QLabel(self._title)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: #B4B4C8;
                font-size: 14px;
                font-weight: 500;
                letter-spacing: 0.5px;
                margin-top: 8px;
                min-height: 20px;
            }}
        """)
        title_label.setWordWrap(True)
        layout.addWidget(title_label)
        
        # Value with proper size
        value_label = QLabel(str(self._value))
        value_label.setStyleSheet(f"""
            QLabel {{
                color: #FFFFFF;
                font-size: 34px;
                font-weight: 900;
                margin-top: 6px;
                min-height: 45px;
                letter-spacing: -0.5px;
            }}
        """)
        self._value_label = value_label
        layout.addWidget(value_label)
        
        # Trend indicator
        if self._trend:
            trend_color = "#00FF88" if self._trend.startswith("+") else "#FF5555"
            trend_label = QLabel(self._trend)
            trend_label.setStyleSheet(f"""
                QLabel {{
                    color: {trend_color};
                    font-size: 13px;
                    font-weight: 600;
                    margin-top: 6px;
                    min-height: 18px;
                }}
            """)
            layout.addWidget(trend_label)
        
        layout.addStretch()
        
        # Add premium shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 8)
        self.setGraphicsEffect(shadow)
    
    def update_value(self, value: str):
        """Update the displayed value."""
        self._value_label.setText(str(value))


class PremiumCard(QFrame):
    """Premium card with glassmorphism, proper spacing, and hover effects."""
    
    clicked = pyqtSignal()
    
    def __init__(self, title: str = "", parent=None, clickable: bool = False):
        super().__init__(parent)
        self.setObjectName("premiumCard")
        self.title = title
        self._clickable = clickable
        
        self._setup_ui()
        
        if clickable:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def _setup_ui(self):
        theme = get_theme()
        p = theme.palette
        
        self.setStyleSheet(f"""
            #premiumCard {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(30, 30, 45, 0.95), stop:1 rgba(20, 20, 35, 0.95));
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 20px;
            }}
            #premiumCard:hover {{
                border-color: rgba(255, 215, 0, 0.3);
            }}
        """)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(28, 28, 28, 28)  # Generous margins
        self.main_layout.setSpacing(18)  # Good spacing
        
        if self.title:
            self.title_label = QLabel(self.title)
            self.title_label.setStyleSheet(f"""
                QLabel {{
                    font-size: 20px;
                    font-weight: 700;
                    color: {p.primary};
                    letter-spacing: 0.5px;
                    min-height: 28px;
                    padding-bottom: 8px;
                }}
            """)
            self.main_layout.addWidget(self.title_label)
        
        # Content area
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(12)
        self.main_layout.addWidget(self.content_widget)
        
        # Premium shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(35)
        shadow.setColor(QColor(0, 0, 0, 70))
        shadow.setOffset(0, 10)
        self.setGraphicsEffect(shadow)
    
    def add_widget(self, widget: QWidget):
        """Add widget to card content."""
        self.content_layout.addWidget(widget)
    
    def mousePressEvent(self, event):
        if self._clickable:
            self.clicked.emit()
        super().mousePressEvent(event)


class PremiumSectionHeader(QWidget):
    """Premium section header with title and optional action button."""
    
    def __init__(self, title: str, action_text: str = None, parent=None):
        super().__init__(parent)
        self._setup_ui(title, action_text)
    
    def _setup_ui(self, title: str, action_text: str):
        theme = get_theme()
        p = theme.palette
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 16)  # Vertical padding
        layout.setSpacing(16)
        
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            QLabel {{
                font-size: 22px;
                font-weight: 700;
                color: {p.text};
                letter-spacing: 0.3px;
            }}
        """)
        layout.addWidget(title_label)
        layout.addStretch()
        
        # Action button
        if action_text:
            action_btn = QPushButton(action_text)
            action_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {p.primary};
                    border: none;
                    font-size: 14px;
                    font-weight: 600;
                    padding: 8px 16px;
                }}
                QPushButton:hover {{
                    color: {p.secondary};
                    text-decoration: underline;
                }}
            """)
            action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.action_btn = action_btn
            layout.addWidget(action_btn)


class PremiumInfoBadge(QFrame):
    """Premium info badge for displaying status or counts."""
    
    def __init__(self, text: str, style: str = "primary", parent=None):
        super().__init__(parent)
        self.setObjectName("infoBadge")
        self._setup_ui(text, style)
    
    def _setup_ui(self, text: str, style: str):
        theme = get_theme()
        p = theme.palette
        
        colors = {
            'primary': (p.primary, "#000000"),
            'success': (p.success, "#000000"),
            'warning': (p.warning, "#000000"),
            'danger': (p.error, "#FFFFFF"),
            'info': (p.secondary, "#000000"),
        }
        
        bg_color, text_color = colors.get(style, colors['primary'])
        
        self.setStyleSheet(f"""
            #infoBadge {{
                background: {bg_color};
                border-radius: 12px;
                padding: 6px 14px;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        
        label = QLabel(text)
        label.setStyleSheet(f"""
            QLabel {{
                color: {text_color};
                font-size: 13px;
                font-weight: 600;
                letter-spacing: 0.3px;
            }}
        """)
        layout.addWidget(label)
        self._label = label
    
    def update_text(self, text: str):
        """Update badge text."""
        self._label.setText(text)


class PremiumDivider(QFrame):
    """Premium horizontal divider with gradient."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(1)
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 transparent, stop:0.2 rgba(255, 215, 0, 0.3),
                    stop:0.8 rgba(0, 217, 255, 0.3), stop:1 transparent);
            }
        """)


class PremiumLoadingSpinner(QWidget):
    """Premium animated loading spinner."""
    
    def __init__(self, size: int = 48, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._angle = 0
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._timer.start(50)
        
        self._setup_style()
    
    def _setup_style(self):
        self.setStyleSheet("""
            QWidget {
                background: transparent;
            }
        """)
    
    def _rotate(self):
        self._angle = (self._angle + 10) % 360
        self.update()
    
    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QPen, QConicalGradient
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Create gradient
        gradient = QConicalGradient(self.width() / 2, self.height() / 2, self._angle)
        gradient.setColorAt(0, QColor("#FFD700"))
        gradient.setColorAt(0.5, QColor("#00D9FF"))
        gradient.setColorAt(1, QColor(255, 215, 0, 0))
        
        # Draw arc
        pen = QPen(gradient, 4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        margin = 4
        painter.drawArc(margin, margin, self.width() - 2 * margin,
                       self.height() - 2 * margin, 0, 270 * 16)
    
    def stop(self):
        """Stop the spinner animation."""
        self._timer.stop()
    
    def start(self):
        """Start the spinner animation."""
        self._timer.start(50)


# Export all components
__all__ = [
    'PremiumButton',
    'PremiumStatsCard',
    'PremiumCard',
    'PremiumSectionHeader',
    'PremiumInfoBadge',
    'PremiumDivider',
    'PremiumLoadingSpinner',
]
