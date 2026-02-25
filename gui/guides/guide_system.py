"""Interactive Guide System for Eden Analytics Pro v2.4.0."""

from typing import List, Dict, Optional, Callable
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGraphicsDropShadowEffect, QApplication
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from gui.themes.modern_theme import get_theme


class GuideOverlay(QWidget):
    """Interactive guide overlay with step-by-step instructions."""
    
    guide_completed = pyqtSignal()
    step_changed = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.current_step = 0
        self.steps = []
        self._animations = []
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Semi-transparent background
        self.bg_frame = QFrame()
        self.bg_frame.setStyleSheet("""
            QFrame {
                background: rgba(10, 10, 20, 0.85);
            }
        """)
        main_layout.addWidget(self.bg_frame)
        
        # Center the guide card
        bg_layout = QVBoxLayout(self.bg_frame)
        bg_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Guide card
        self.guide_card = QFrame()
        self.guide_card.setObjectName("guideCard")
        self.guide_card.setStyleSheet("""
            #guideCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255, 215, 0, 0.95),
                    stop:1 rgba(0, 217, 255, 0.95));
                border: 3px solid rgba(255, 255, 255, 0.3);
                border-radius: 24px;
            }
        """)
        self.guide_card.setMinimumWidth(500)
        self.guide_card.setMaximumWidth(600)
        self.guide_card.setMinimumHeight(300)
        
        card_layout = QVBoxLayout(self.guide_card)
        card_layout.setSpacing(20)
        card_layout.setContentsMargins(40, 35, 40, 35)
        
        # Step indicator
        self.step_indicator = QLabel()
        self.step_indicator.setStyleSheet("""
            QLabel {
                color: rgba(0, 0, 0, 0.5);
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 1px;
                text-transform: uppercase;
            }
        """)
        card_layout.addWidget(self.step_indicator)
        
        # Title
        self.title_label = QLabel()
        self.title_label.setStyleSheet("""
            QLabel {
                color: #000000;
                font-size: 28px;
                font-weight: 900;
                letter-spacing: -0.5px;
                line-height: 1.2;
            }
        """)
        self.title_label.setWordWrap(True)
        card_layout.addWidget(self.title_label)
        
        # Description
        self.desc_label = QLabel()
        self.desc_label.setStyleSheet("""
            QLabel {
                color: #1A1A2E;
                font-size: 16px;
                font-weight: 400;
                line-height: 1.6;
            }
        """)
        self.desc_label.setWordWrap(True)
        card_layout.addWidget(self.desc_label)
        
        card_layout.addStretch()
        
        # Progress bar
        progress_container = QFrame()
        progress_layout = QHBoxLayout(progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(6)
        
        self.progress_dots = []
        for i in range(10):  # Max 10 steps
            dot = QLabel("●")
            dot.setStyleSheet("color: rgba(0, 0, 0, 0.2); font-size: 10px;")
            self.progress_dots.append(dot)
            progress_layout.addWidget(dot)
        
        progress_layout.addStretch()
        card_layout.addWidget(progress_container)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(16)
        
        # Skip button
        self.skip_btn = QPushButton("Пропустить")
        self.skip_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 0, 0, 0.15);
                color: #000000;
                border: 2px solid rgba(0, 0, 0, 0.3);
                border-radius: 12px;
                padding: 14px 28px;
                font-size: 15px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(0, 0, 0, 0.25);
                border-color: rgba(0, 0, 0, 0.5);
            }
        """)
        self.skip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.skip_btn.clicked.connect(self.close_guide)
        
        # Back button
        self.back_btn = QPushButton("← Назад")
        self.back_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #000000;
                border: none;
                padding: 14px 20px;
                font-size: 15px;
                font-weight: 600;
            }
            QPushButton:hover {
                text-decoration: underline;
            }
        """)
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.clicked.connect(self.prev_step)
        
        # Next button
        self.next_btn = QPushButton("Далее →")
        self.next_btn.setStyleSheet("""
            QPushButton {
                background: #000000;
                color: #FFD700;
                border: none;
                border-radius: 12px;
                padding: 14px 36px;
                font-size: 15px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #1A1A2E;
            }
        """)
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.clicked.connect(self.next_step)
        
        button_layout.addWidget(self.skip_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.back_btn)
        button_layout.addWidget(self.next_btn)
        
        card_layout.addLayout(button_layout)
        
        bg_layout.addWidget(self.guide_card)
        
        # Add shadow to card
        shadow = QGraphicsDropShadowEffect(self.guide_card)
        shadow.setBlurRadius(60)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 20)
        self.guide_card.setGraphicsEffect(shadow)
    
    def set_steps(self, steps: List[Dict]):
        """Set guide steps.
        
        steps: List of {'title': str, 'description': str}
        """
        self.steps = steps
        self.current_step = 0
        
        # Update progress dots visibility
        for i, dot in enumerate(self.progress_dots):
            dot.setVisible(i < len(steps))
        
        self.show_step()
    
    def show_step(self):
        """Display current step."""
        if self.current_step >= len(self.steps):
            self.close_guide()
            return
        
        step = self.steps[self.current_step]
        
        # Update content
        self.step_indicator.setText(f"ШАГ {self.current_step + 1} ИЗ {len(self.steps)}")
        self.title_label.setText(step.get('title', ''))
        self.desc_label.setText(step.get('description', ''))
        
        # Update progress dots
        for i, dot in enumerate(self.progress_dots[:len(self.steps)]):
            if i < self.current_step:
                dot.setStyleSheet("color: rgba(0, 0, 0, 0.6); font-size: 10px;")
            elif i == self.current_step:
                dot.setStyleSheet("color: #000000; font-size: 12px;")
            else:
                dot.setStyleSheet("color: rgba(0, 0, 0, 0.2); font-size: 10px;")
        
        # Update buttons
        self.back_btn.setVisible(self.current_step > 0)
        
        if self.current_step == len(self.steps) - 1:
            self.next_btn.setText("Завершить ✓")
        else:
            self.next_btn.setText("Далее →")
        
        self.step_changed.emit(self.current_step)
    
    def next_step(self):
        """Go to next step."""
        self.current_step += 1
        if self.current_step >= len(self.steps):
            self.close_guide()
        else:
            self.show_step()
    
    def prev_step(self):
        """Go to previous step."""
        if self.current_step > 0:
            self.current_step -= 1
            self.show_step()
    
    def close_guide(self):
        """Close the guide overlay."""
        self.guide_completed.emit()
        self.close()
    
    def showEvent(self, event):
        """Handle show event."""
        super().showEvent(event)
        # Resize to parent
        if self.parent():
            self.resize(self.parent().size())
            self.move(0, 0)


class GuideButton(QPushButton):
    """Stylish guide button for each page."""
    
    def __init__(self, text: str = "❓ Гайд", parent=None):
        super().__init__(text, parent)
        self._setup_style()
    
    def _setup_style(self):
        """Apply premium styling."""
        self.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FFD700, stop:1 #00D9FF);
                color: #000000;
                border: none;
                border-radius: 20px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00D9FF, stop:1 #FFD700);
            }
            QPushButton:pressed {
                padding: 13px 23px 11px 25px;
            }
        """)
        self.setFixedHeight(44)
        self.setMinimumWidth(100)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Add shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(255, 215, 0, 100))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)


class GuideManager:
    """Manager for guide system across the application."""
    
    _instance = None
    _guides_shown = set()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.auto_show_guides = True
        self._overlay = None
    
    def show_guide(self, parent: QWidget, steps: List[Dict],
                   guide_id: str = None, force: bool = False):
        """Show a guide overlay.
        
        Args:
            parent: Parent widget
            steps: List of guide steps
            guide_id: Unique identifier for the guide
            force: Show even if previously shown
        """
        # Check if already shown
        if guide_id and guide_id in self._guides_shown and not force:
            return
        
        # Create and show overlay
        self._overlay = GuideOverlay(parent)
        self._overlay.set_steps(steps)
        
        if guide_id:
            self._overlay.guide_completed.connect(
                lambda: self._mark_shown(guide_id)
            )
        
        self._overlay.show()
    
    def _mark_shown(self, guide_id: str):
        """Mark a guide as shown."""
        self._guides_shown.add(guide_id)
    
    def reset_guides(self):
        """Reset all shown guides."""
        self._guides_shown.clear()
    
    def is_guide_shown(self, guide_id: str) -> bool:
        """Check if a guide has been shown."""
        return guide_id in self._guides_shown


# Singleton instance
_guide_manager = None

def get_guide_manager() -> GuideManager:
    """Get the singleton guide manager."""
    global _guide_manager
    if _guide_manager is None:
        _guide_manager = GuideManager()
    return _guide_manager


__all__ = ['GuideOverlay', 'GuideButton', 'GuideManager', 'get_guide_manager']
