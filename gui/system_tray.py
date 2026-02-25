"""System Tray Integration for Eden Analytics Pro."""

from typing import Optional, Callable
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor
from PyQt6.QtCore import pyqtSignal, QObject, Qt

from utils.logger import get_logger

logger = get_logger(__name__)


class SystemTrayManager(QObject):
    """Manages system tray icon and menu."""
    
    # Signals
    show_requested = pyqtSignal()
    hide_requested = pyqtSignal()
    arbitrage_requested = pyqtSignal()
    stats_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tray_icon: Optional[QSystemTrayIcon] = None
        self.menu: Optional[QMenu] = None
        self._is_visible = True
        
        self._setup_tray()
    
    def _setup_tray(self):
        """Setup system tray icon and menu."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray not available")
            return
        
        # Create tray icon
        self.tray_icon = QSystemTrayIcon(self._create_icon(), self.parent())
        self.tray_icon.setToolTip("Eden Analytics Pro")
        
        # Create menu
        self.menu = QMenu()
        self._setup_menu()
        
        self.tray_icon.setContextMenu(self.menu)
        
        # Connect signals
        self.tray_icon.activated.connect(self._on_tray_activated)
    
    def _create_icon(self) -> QIcon:
        """Create tray icon from branding assets."""
        import os
        from pathlib import Path
        
        # Try to load the branding icon
        icon_path = Path(__file__).parent / "assets" / "branding" / "eden_logo_icon.png"
        
        if os.path.exists(icon_path):
            pixmap = QPixmap(str(icon_path))
            scaled = pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
            return QIcon(scaled)
        
        # Fallback: Create a simple icon programmatically
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))  # Transparent
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw hockey puck icon
        painter.setBrush(QColor("#6C63FF"))
        painter.setPen(QColor("#00D4FF"))
        painter.drawEllipse(4, 4, 24, 24)
        
        # Draw "E" for Eden
        painter.setPen(QColor("white"))
        from PyQt6.QtGui import QFont
        font = QFont("Arial", 14, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), 0x84, "E")  # AlignCenter
        
        painter.end()
        
        return QIcon(pixmap)
    
    def _setup_menu(self):
        """Setup context menu."""
        # Show/Hide action
        self.show_action = QAction("Show Window", self.menu)
        self.show_action.triggered.connect(self._toggle_window)
        self.menu.addAction(self.show_action)
        
        self.menu.addSeparator()
        
        # Quick actions
        arbitrage_action = QAction("🔍 Find Arbitrage", self.menu)
        arbitrage_action.triggered.connect(self.arbitrage_requested.emit)
        self.menu.addAction(arbitrage_action)
        
        stats_action = QAction("📊 View Stats", self.menu)
        stats_action.triggered.connect(self.stats_requested.emit)
        self.menu.addAction(stats_action)
        
        settings_action = QAction("⚙️ Settings", self.menu)
        settings_action.triggered.connect(self.settings_requested.emit)
        self.menu.addAction(settings_action)
        
        self.menu.addSeparator()
        
        # Quit
        quit_action = QAction("❌ Quit", self.menu)
        quit_action.triggered.connect(self.quit_requested.emit)
        self.menu.addAction(quit_action)
    
    def _toggle_window(self):
        """Toggle window visibility."""
        if self._is_visible:
            self.hide_requested.emit()
            self.show_action.setText("Show Window")
        else:
            self.show_requested.emit()
            self.show_action.setText("Hide Window")
        
        self._is_visible = not self._is_visible
    
    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._toggle_window()
    
    def show(self):
        """Show tray icon."""
        if self.tray_icon:
            self.tray_icon.show()
            logger.info("System tray icon shown")
    
    def hide(self):
        """Hide tray icon."""
        if self.tray_icon:
            self.tray_icon.hide()
    
    def show_notification(self, title: str, message: str, 
                         icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information,
                         duration: int = 3000):
        """Show a notification balloon.
        
        Args:
            title: Notification title
            message: Notification message
            icon: Icon type (Information, Warning, Critical)
            duration: Display duration in milliseconds
        """
        if self.tray_icon:
            self.tray_icon.showMessage(title, message, icon, duration)
            logger.debug(f"Tray notification: {title}")
    
    def notify_opportunity(self, match: str, roi: float):
        """Show arbitrage opportunity notification."""
        self.show_notification(
            "🎯 Arbitrage Found!",
            f"{match}\nROI: {roi:.2f}%",
            QSystemTrayIcon.MessageIcon.Information
        )
    
    def notify_bet_result(self, won: bool, profit: float):
        """Show bet result notification."""
        if won:
            self.show_notification(
                "✅ Bet Won!",
                f"Profit: ${profit:.2f}",
                QSystemTrayIcon.MessageIcon.Information
            )
        else:
            self.show_notification(
                "❌ Bet Lost",
                f"Loss: ${abs(profit):.2f}",
                QSystemTrayIcon.MessageIcon.Warning
            )
    
    def set_window_visible(self, visible: bool):
        """Update internal visibility state."""
        self._is_visible = visible
        if self.show_action:
            self.show_action.setText("Hide Window" if visible else "Show Window")


__all__ = ['SystemTrayManager']
