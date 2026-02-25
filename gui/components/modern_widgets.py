"""Premium Modern Custom Widgets for Eden Analytics Pro v2.2.0."""

from typing import Optional, List, Callable
from PyQt6.QtWidgets import (
    QWidget, QPushButton, QFrame, QLabel, QVBoxLayout, QHBoxLayout,
    QLineEdit, QGraphicsDropShadowEffect, QSizePolicy, QProgressBar,
    QStackedWidget, QApplication, QGraphicsOpacityEffect, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, QTimer,
    QPoint, QSize, QRect, QParallelAnimationGroup, QSequentialAnimationGroup
)
from PyQt6.QtGui import (
    QColor, QPainter, QPainterPath, QLinearGradient, QFont,
    QBrush, QPen, QIcon
)

from gui.themes.modern_theme import get_theme


# ============================================================================
# PREMIUM BUTTON COMPONENTS
# ============================================================================

class PremiumButton(QPushButton):
    """Premium styled button with gradient, glow effects, and animations."""
    
    def __init__(self, text: str = "", icon: QIcon = None, 
                 style: str = 'primary', parent=None):
        super().__init__(text, parent)
        self._style = style
        self._hover = False
        
        if icon:
            self.setIcon(icon)
            self.setIconSize(QSize(20, 20))
        
        self.setMinimumHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()
        self._add_shadow()
    
    def _add_shadow(self):
        """Add premium shadow effect."""
        shadow = QGraphicsDropShadowEffect(self)
        theme = get_theme()
        if self._style == 'primary':
            shadow.setBlurRadius(20)
            shadow.setColor(QColor(255, 215, 0, 100))
            shadow.setOffset(0, 4)
        else:
            shadow.setBlurRadius(15)
            shadow.setColor(QColor(0, 0, 0, 60))
            shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)
    
    def _update_style(self):
        theme = get_theme()
        p = theme.palette
        
        styles = {
            'primary': f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 {p.primary}, stop:1 {p.secondary});
                    color: #000000;
                    border: none;
                    border-radius: 12px;
                    padding: 14px 28px;
                    font-size: 14px;
                    font-weight: 700;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 {p.secondary}, stop:1 {p.primary});
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
                    padding: 12px 24px;
                    font-size: 14px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: rgba({theme._hex_to_rgb(p.primary)}, 0.15);
                    border-color: {p.secondary};
                }}
                QPushButton:pressed {{
                    background: rgba({theme._hex_to_rgb(p.primary)}, 0.25);
                }}
            """,
            'ghost': f"""
                QPushButton {{
                    background: rgba(255, 255, 255, 0.05);
                    color: {p.text};
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 12px;
                    padding: 12px 24px;
                }}
                QPushButton:hover {{
                    background: rgba(255, 255, 255, 0.1);
                    border-color: {p.primary};
                }}
            """,
            'danger': f"""
                QPushButton {{
                    background: {p.error};
                    color: white;
                    border: none;
                    border-radius: 12px;
                    padding: 12px 24px;
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
                    padding: 12px 24px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: #00ff99;
                }}
            """
        }
        
        self.setStyleSheet(styles.get(self._style, styles['primary']))


class ModernButton(QPushButton):
    """Modern styled button with hover effects and optional gradient."""
    
    def __init__(self, text: str = "", icon: QIcon = None, 
                 primary: bool = False, parent=None):
        super().__init__(text, parent)
        self.primary = primary
        self._hover = False
        
        if icon:
            self.setIcon(icon)
        
        self.setMinimumHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)
    
    def _update_style(self):
        theme = get_theme()
        p = theme.palette
        
        if self.primary:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {p.primary}, stop:1 {p.secondary});
                    color: #000000;
                    border: none;
                    padding: 14px 28px;
                    border-radius: 12px;
                    font-weight: 700;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {p.secondary}, stop:1 {p.primary});
                }}
                QPushButton:pressed {{
                    padding: 15px 27px 13px 29px;
                }}
                QPushButton:disabled {{
                    background: {p.surface_light};
                    color: {p.text_muted};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {p.surface_light};
                    color: {p.text};
                    border: 1px solid {p.border};
                    padding: 14px 24px;
                    border-radius: 12px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {p.primary}, stop:1 {p.secondary});
                    color: #000000;
                    border: none;
                }}
                QPushButton:pressed {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {p.secondary}, stop:1 {p.primary});
                }}
            """)


# ============================================================================
# PREMIUM CARD COMPONENTS
# ============================================================================

class ModernCard(QFrame):
    """Premium card-style container with glassmorphism and shadow effects."""
    
    clicked = pyqtSignal()
    
    def __init__(self, title: str = "", parent=None, clickable: bool = False,
                 glass: bool = False):
        super().__init__(parent)
        self.title = title
        self._clickable = clickable
        self._glass = glass
        self._hover = False
        
        self._setup_ui()
        self._apply_style()
        
        if clickable:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(16)
        
        if self.title:
            self.title_label = QLabel(self.title)
            theme = get_theme()
            p = theme.palette
            self.title_label.setStyleSheet(f"""
                font-size: 18px;
                font-weight: 700;
                color: {p.primary};
                letter-spacing: 0.5px;
            """)
            self.layout.addWidget(self.title_label)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.content_widget)
    
    def _apply_style(self):
        theme = get_theme()
        p = theme.palette
        
        if self._glass:
            self.setStyleSheet(f"""
                ModernCard {{
                    background: rgba({theme._hex_to_rgb(p.surface)}, 0.7);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 16px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                ModernCard {{
                    background-color: {p.surface};
                    border-radius: 16px;
                    border: 1px solid {p.border};
                }}
                ModernCard:hover {{
                    border-color: {p.primary};
                }}
            """)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 6)
        self.setGraphicsEffect(shadow)
    
    def add_widget(self, widget: QWidget):
        """Add widget to card content."""
        self.content_layout.addWidget(widget)
    
    def mousePressEvent(self, event):
        if self._clickable:
            self.clicked.emit()
        super().mousePressEvent(event)


class PremiumStatsCard(QFrame):
    """Premium stat card with icon, value, trend, and glow effects."""
    
    def __init__(self, title: str, value: str, icon: str = "📊",
                 trend: float = None, color: str = None, parent=None):
        super().__init__(parent)
        self.setObjectName("premiumStatsCard")
        self._title = title
        self._value = value
        self._icon = icon
        self._trend = trend
        self._color = color
        
        self._setup_ui()
    
    def _setup_ui(self):
        theme = get_theme()
        p = theme.palette
        accent = self._color or p.primary
        
        self.setStyleSheet(f"""
            #premiumStatsCard {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {p.surface}, stop:1 {p.card});
                border-radius: 16px;
                border-left: 4px solid {accent};
            }}
            #premiumStatsCard:hover {{
                border: 1px solid rgba({theme._hex_to_rgb(accent)}, 0.5);
                border-left: 4px solid {accent};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        
        # Header with icon
        header = QHBoxLayout()
        
        # Icon with glow background
        icon_container = QFrame()
        icon_container.setFixedSize(56, 56)
        icon_container.setStyleSheet(f"""
            QFrame {{
                background: qradialgradient(
                    cx:0.5, cy:0.5, radius:0.5,
                    fx:0.5, fy:0.5,
                    stop:0 rgba({theme._hex_to_rgb(accent)}, 0.3),
                    stop:1 transparent
                );
                border-radius: 28px;
            }}
        """)
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_label = QLabel(self._icon)
        icon_label.setStyleSheet("font-size: 28px; background: transparent;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.addWidget(icon_label)
        header.addWidget(icon_container)
        header.addStretch()
        
        # Trend indicator
        if self._trend is not None:
            trend_color = p.success if self._trend >= 0 else p.error
            trend_icon = "▲" if self._trend >= 0 else "▼"
            trend_label = QLabel(f"{trend_icon} {abs(self._trend):.1f}%")
            trend_label.setStyleSheet(f"""
                QLabel {{
                    color: {trend_color};
                    font-size: 13px;
                    font-weight: 700;
                    background: rgba({theme._hex_to_rgb(trend_color)}, 0.15);
                    padding: 6px 12px;
                    border-radius: 12px;
                }}
            """)
            header.addWidget(trend_label)
        
        layout.addLayout(header)
        
        # Value with gradient text effect
        self.value_label = QLabel(self._value)
        self.value_label.setStyleSheet(f"""
            QLabel {{
                font-size: 36px;
                font-weight: 900;
                color: {p.text};
                letter-spacing: -1px;
            }}
        """)
        layout.addWidget(self.value_label)
        
        # Title
        title_label = QLabel(self._title)
        title_label.setStyleSheet(f"""
            QLabel {{
                font-size: 13px;
                color: {p.text_secondary};
                text-transform: uppercase;
                letter-spacing: 1.5px;
                font-weight: 600;
            }}
        """)
        layout.addWidget(title_label)
        
        # Add premium shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 8)
        self.setGraphicsEffect(shadow)
        
        self.setMinimumHeight(140)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    
    def update_value(self, value: str, trend: float = None):
        """Update the displayed value with animation."""
        self._value = value
        self._trend = trend
        
        # Rebuild UI
        while self.layout().count():
            item = self.layout().takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
        self._setup_ui()
    
    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())


# Backward compatible alias
StatCard = PremiumStatsCard


# ============================================================================
# PREMIUM INPUT COMPONENTS
# ============================================================================

class PremiumInput(QWidget):
    """Premium input field with floating label and focus animations."""
    
    textChanged = pyqtSignal(str)
    
    def __init__(self, label: str = "", placeholder: str = "", parent=None):
        super().__init__(parent)
        self._label = label
        self._placeholder = placeholder
        
        self._setup_ui()
    
    def _setup_ui(self):
        theme = get_theme()
        p = theme.palette
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Label
        if self._label:
            label = QLabel(self._label)
            label.setStyleSheet(f"""
                color: {p.text_secondary};
                font-size: 13px;
                font-weight: 600;
                letter-spacing: 0.5px;
            """)
            layout.addWidget(label)
        
        # Input
        self.input = QLineEdit()
        self.input.setPlaceholderText(self._placeholder)
        self.input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {p.surface};
                color: {p.text};
                border: 2px solid {p.border};
                padding: 14px 18px;
                border-radius: 12px;
                font-size: 14px;
                selection-background-color: {p.primary};
            }}
            QLineEdit:focus {{
                border-color: {p.primary};
                background-color: {p.card};
            }}
            QLineEdit::placeholder {{
                color: {p.text_muted};
            }}
        """)
        self.input.textChanged.connect(self.textChanged.emit)
        layout.addWidget(self.input)
    
    def text(self) -> str:
        return self.input.text()
    
    def setText(self, text: str):
        self.input.setText(text)


# Backward compatible alias
ModernInput = PremiumInput


# ============================================================================
# PREMIUM PROGRESS COMPONENTS
# ============================================================================

class PremiumProgressBar(QProgressBar):
    """Premium animated gradient progress bar with shimmer effect."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._animation = None
        self.setTextVisible(True)
        self.setMinimumHeight(24)
        self._apply_style()
    
    def _apply_style(self):
        theme = get_theme()
        p = theme.palette
        
        self.setStyleSheet(f"""
            QProgressBar {{
                background-color: {p.surface};
                border: none;
                border-radius: 12px;
                text-align: center;
                color: #000000;
                font-weight: 700;
                font-size: 12px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {p.primary}, stop:0.5 {p.secondary}, stop:1 {p.success});
                border-radius: 12px;
            }}
        """)
    
    def animate_to(self, value: int, duration: int = 500):
        """Animate progress to a value."""
        if self._animation:
            self._animation.stop()
        
        self._animation = QPropertyAnimation(self, b"value")
        self._animation.setDuration(duration)
        self._animation.setStartValue(self.value())
        self._animation.setEndValue(value)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.start()


# Backward compatible alias
ModernProgressBar = PremiumProgressBar


# ============================================================================
# PREMIUM SWITCH COMPONENT
# ============================================================================

class ModernSwitch(QWidget):
    """Premium iOS-style toggle switch with smooth animation."""
    
    toggled = pyqtSignal(bool)
    
    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self._circle_pos = 4 if not checked else 28
        
        self.setFixedSize(54, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self._animation = QPropertyAnimation(self, b"circlePos")
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    @property
    def circlePos(self):
        return self._circle_pos
    
    @circlePos.setter
    def circlePos(self, pos):
        self._circle_pos = pos
        self.update()
    
    def isChecked(self) -> bool:
        return self._checked
    
    def setChecked(self, checked: bool):
        self._checked = checked
        end_pos = 28 if checked else 4
        self._animation.setStartValue(self._circle_pos)
        self._animation.setEndValue(end_pos)
        self._animation.start()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        theme = get_theme()
        p = theme.palette
        
        # Background with gradient when checked
        if self._checked:
            gradient = QLinearGradient(0, 0, 54, 0)
            gradient.setColorAt(0, QColor(p.primary))
            gradient.setColorAt(1, QColor(p.secondary))
            painter.setBrush(QBrush(gradient))
        else:
            painter.setBrush(QBrush(QColor(p.surface_light)))
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, 54, 30, 15, 15)
        
        # Circle with shadow effect
        painter.setBrush(QBrush(QColor("white")))
        painter.drawEllipse(int(self._circle_pos), 3, 24, 24)
    
    def mousePressEvent(self, event):
        self._checked = not self._checked
        self.setChecked(self._checked)
        self.toggled.emit(self._checked)


# ============================================================================
# PREMIUM TOAST NOTIFICATIONS
# ============================================================================

class PremiumToast(QFrame):
    """Premium toast notification with smooth animations."""
    
    def __init__(self, message: str, type: str = "info", duration: int = 3000, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool |
                           Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._message = message
        self._type = type
        self._duration = duration
        
        self._setup_ui()
        self._setup_animation()
    
    def _setup_ui(self):
        theme = get_theme()
        p = theme.palette
        
        # Type-based colors and icons
        colors = {
            "info": p.secondary,
            "success": p.success,
            "warning": p.warning,
            "error": p.error
        }
        icons = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌"
        }
        
        color = colors.get(self._type, p.secondary)
        icon = icons.get(self._type, "ℹ️")
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: rgba({theme._hex_to_rgb(p.card)}, 0.95);
                border: 2px solid {color};
                border-radius: 14px;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)
        
        # Icon
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 24px; background: transparent;")
        layout.addWidget(icon_label)
        
        # Message
        message_label = QLabel(self._message)
        message_label.setStyleSheet(f"""
            color: {p.text};
            font-size: 14px;
            font-weight: 500;
            background: transparent;
        """)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)
        
        # Premium shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 8)
        self.setGraphicsEffect(shadow)
        
        self.setMinimumWidth(320)
        self.setMaximumWidth(450)
    
    def _setup_animation(self):
        """Setup fade in/out animations."""
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        # Fade in
        self.fade_in = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in.setDuration(300)
        self.fade_in.setStartValue(0)
        self.fade_in.setEndValue(1)
        self.fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Auto-hide timer
        QTimer.singleShot(self._duration, self._fade_out)
        
        self.fade_in.start()
    
    def _fade_out(self):
        """Fade out and close."""
        self.fade_out_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out_anim.setDuration(300)
        self.fade_out_anim.setStartValue(1)
        self.fade_out_anim.setEndValue(0)
        self.fade_out_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self.fade_out_anim.finished.connect(self._cleanup)
        self.fade_out_anim.start()
    
    def _cleanup(self):
        self.close()
        self.deleteLater()


# Backward compatible alias
ToastNotification = PremiumToast


class NotificationManager:
    """Manages toast notifications with stacking."""
    
    _instance = None
    _notifications: List[PremiumToast] = []
    
    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def show(self, message: str, type: str = "info", duration: int = 3000):
        """Show a notification."""
        app = QApplication.instance()
        if app:
            windows = app.topLevelWidgets()
            for window in windows:
                if window.isVisible() and hasattr(window, 'isActiveWindow'):
                    toast = PremiumToast(message, type, duration, window)
                    
                    # Position at top-right with stacking
                    x = window.width() - toast.sizeHint().width() - 24
                    y = 24 + len(self._notifications) * 90
                    toast.move(x, y)
                    toast.show()
                    
                    self._notifications.append(toast)
                    
                    # Clean up after duration
                    QTimer.singleShot(duration + 400, lambda t=toast: self._remove(t))
                    break
    
    def _remove(self, toast: PremiumToast):
        if toast in self._notifications:
            self._notifications.remove(toast)


def show_notification(message: str, type: str = "info", duration: int = 3000):
    """Convenience function to show notifications."""
    NotificationManager.instance().show(message, type, duration)


# ============================================================================
# SKELETON LOADER COMPONENT
# ============================================================================

class SkeletonLoader(QFrame):
    """Premium skeleton loading placeholder with shimmer animation."""
    
    def __init__(self, width: int = 200, height: int = 20, parent=None):
        super().__init__(parent)
        self.setFixedSize(width, height)
        self._apply_style()
        
        # Shimmer animation timer
        self._shimmer_offset = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_shimmer)
        self._timer.start(50)
    
    def _apply_style(self):
        theme = get_theme()
        p = theme.palette
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {p.surface_light};
                border-radius: 8px;
            }}
        """)
    
    def _update_shimmer(self):
        self._shimmer_offset = (self._shimmer_offset + 10) % (self.width() + 200)
        self.update()
    
    def paintEvent(self, event):
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw shimmer effect
        gradient = QLinearGradient(self._shimmer_offset - 100, 0, 
                                    self._shimmer_offset + 100, 0)
        gradient.setColorAt(0, QColor(255, 255, 255, 0))
        gradient.setColorAt(0.5, QColor(255, 255, 255, 30))
        gradient.setColorAt(1, QColor(255, 255, 255, 0))
        
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 8, 8)
        painter.fillPath(path, gradient)
    
    def stop(self):
        """Stop shimmer animation."""
        self._timer.stop()


# ============================================================================
# PREMIUM TABLE WIDGET
# ============================================================================

class PremiumTable(QTableWidget):
    """Premium styled table with hover effects and smooth scrolling."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._apply_style()
        self._configure()
    
    def _apply_style(self):
        theme = get_theme()
        p = theme.palette
        
        self.setStyleSheet(f"""
            QTableWidget {{
                background-color: {p.surface};
                border: 1px solid {p.border};
                border-radius: 12px;
                gridline-color: {p.border};
                color: {p.text};
                selection-background-color: rgba({theme._hex_to_rgb(p.primary)}, 0.2);
            }}
            QTableWidget::item {{
                padding: 14px 16px;
                border-bottom: 1px solid {p.border};
            }}
            QTableWidget::item:hover {{
                background-color: rgba({theme._hex_to_rgb(p.primary)}, 0.1);
            }}
            QTableWidget::item:selected {{
                background-color: rgba({theme._hex_to_rgb(p.primary)}, 0.2);
            }}
            QHeaderView::section {{
                background-color: {p.card};
                color: {p.text_secondary};
                padding: 16px;
                border: none;
                border-bottom: 2px solid {p.primary};
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 1px;
                font-size: 12px;
            }}
            QScrollBar:vertical {{
                background-color: {p.surface};
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {p.primary}, stop:1 {p.secondary});
                border-radius: 6px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {p.secondary}, stop:1 {p.primary});
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
    
    def _configure(self):
        """Configure table behavior."""
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'PremiumButton', 'ModernButton', 'ModernCard', 'PremiumStatsCard', 'StatCard',
    'PremiumInput', 'ModernInput', 'PremiumProgressBar', 'ModernProgressBar',
    'ModernSwitch', 'PremiumToast', 'ToastNotification', 'NotificationManager',
    'show_notification', 'SkeletonLoader', 'PremiumTable'
]
