"""Smooth Animation System for Eden Analytics Pro v2.4.0."""

from typing import Optional, Callable
from PyQt6.QtCore import (
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup,
    QSequentialAnimationGroup, QPoint, QRect, QSize, QTimer, pyqtSignal, QObject
)
from PyQt6.QtWidgets import QWidget, QGraphicsOpacityEffect
from PyQt6.QtGui import QColor


class AnimationManager:
    """Manage UI animations for smooth transitions and effects."""
    
    # Store active animations to prevent garbage collection
    _active_animations = []
    
    @staticmethod
    def _store_animation(animation):
        """Store animation reference to prevent garbage collection."""
        AnimationManager._active_animations.append(animation)
        # Clean up finished animations
        animation.finished.connect(
            lambda: AnimationManager._cleanup_animation(animation)
        )
    
    @staticmethod
    def _cleanup_animation(animation):
        """Remove finished animation from storage."""
        if animation in AnimationManager._active_animations:
            AnimationManager._active_animations.remove(animation)
    
    @staticmethod
    def fade_in(widget: QWidget, duration: int = 300, 
                callback: Callable = None) -> QPropertyAnimation:
        """Fade in animation with smooth easing."""
        # Create opacity effect
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        
        animation = QPropertyAnimation(effect, b"opacity")
        animation.setDuration(duration)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        if callback:
            animation.finished.connect(callback)
        
        AnimationManager._store_animation(animation)
        animation.start()
        
        return animation
    
    @staticmethod
    def fade_out(widget: QWidget, duration: int = 300,
                 callback: Callable = None) -> QPropertyAnimation:
        """Fade out animation with smooth easing."""
        effect = widget.graphicsEffect()
        if not effect or not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
        
        animation = QPropertyAnimation(effect, b"opacity")
        animation.setDuration(duration)
        animation.setStartValue(1.0)
        animation.setEndValue(0.0)
        animation.setEasingCurve(QEasingCurve.Type.InCubic)
        
        if callback:
            animation.finished.connect(callback)
        
        AnimationManager._store_animation(animation)
        animation.start()
        
        return animation
    
    @staticmethod
    def slide_in(widget: QWidget, direction: str = "left",
                 duration: int = 400, distance: int = 100) -> QPropertyAnimation:
        """Slide in animation from specified direction."""
        animation = QPropertyAnimation(widget, b"pos")
        animation.setDuration(duration)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        current_pos = widget.pos()
        
        if direction == "left":
            start_pos = QPoint(current_pos.x() - distance, current_pos.y())
        elif direction == "right":
            start_pos = QPoint(current_pos.x() + distance, current_pos.y())
        elif direction == "top":
            start_pos = QPoint(current_pos.x(), current_pos.y() - distance)
        else:  # bottom
            start_pos = QPoint(current_pos.x(), current_pos.y() + distance)
        
        animation.setStartValue(start_pos)
        animation.setEndValue(current_pos)
        
        AnimationManager._store_animation(animation)
        animation.start()
        
        return animation
    
    @staticmethod
    def slide_out(widget: QWidget, direction: str = "left",
                  duration: int = 400, distance: int = 100,
                  callback: Callable = None) -> QPropertyAnimation:
        """Slide out animation in specified direction."""
        animation = QPropertyAnimation(widget, b"pos")
        animation.setDuration(duration)
        animation.setEasingCurve(QEasingCurve.Type.InCubic)
        
        current_pos = widget.pos()
        
        if direction == "left":
            end_pos = QPoint(current_pos.x() - distance, current_pos.y())
        elif direction == "right":
            end_pos = QPoint(current_pos.x() + distance, current_pos.y())
        elif direction == "top":
            end_pos = QPoint(current_pos.x(), current_pos.y() - distance)
        else:  # bottom
            end_pos = QPoint(current_pos.x(), current_pos.y() + distance)
        
        animation.setStartValue(current_pos)
        animation.setEndValue(end_pos)
        
        if callback:
            animation.finished.connect(callback)
        
        AnimationManager._store_animation(animation)
        animation.start()
        
        return animation
    
    @staticmethod
    def pulse(widget: QWidget, duration: int = 1000,
              min_opacity: float = 0.6) -> QPropertyAnimation:
        """Pulse animation for attention/loading states."""
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        
        animation = QPropertyAnimation(effect, b"opacity")
        animation.setDuration(duration)
        animation.setStartValue(1.0)
        animation.setKeyValueAt(0.5, min_opacity)
        animation.setEndValue(1.0)
        animation.setLoopCount(-1)  # Infinite loop
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        AnimationManager._store_animation(animation)
        animation.start()
        
        return animation
    
    @staticmethod
    def scale_in(widget: QWidget, duration: int = 350,
                 start_scale: float = 0.8) -> QPropertyAnimation:
        """Scale in animation with elastic bounce."""
        animation = QPropertyAnimation(widget, b"geometry")
        animation.setDuration(duration)
        animation.setEasingCurve(QEasingCurve.Type.OutBack)
        
        end_rect = widget.geometry()
        center = end_rect.center()
        
        # Calculate scaled start rect
        start_width = int(end_rect.width() * start_scale)
        start_height = int(end_rect.height() * start_scale)
        start_rect = QRect(
            center.x() - start_width // 2,
            center.y() - start_height // 2,
            start_width,
            start_height
        )
        
        animation.setStartValue(start_rect)
        animation.setEndValue(end_rect)
        
        AnimationManager._store_animation(animation)
        animation.start()
        
        return animation
    
    @staticmethod
    def bounce(widget: QWidget, duration: int = 600,
               bounce_height: int = 20) -> QSequentialAnimationGroup:
        """Bounce animation for notifications or alerts."""
        group = QSequentialAnimationGroup()
        
        current_pos = widget.pos()
        
        # Bounce up
        up_anim = QPropertyAnimation(widget, b"pos")
        up_anim.setDuration(duration // 3)
        up_anim.setStartValue(current_pos)
        up_anim.setEndValue(QPoint(current_pos.x(), current_pos.y() - bounce_height))
        up_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        # Bounce down
        down_anim = QPropertyAnimation(widget, b"pos")
        down_anim.setDuration(duration // 3)
        down_anim.setStartValue(QPoint(current_pos.x(), current_pos.y() - bounce_height))
        down_anim.setEndValue(QPoint(current_pos.x(), current_pos.y() + 5))
        down_anim.setEasingCurve(QEasingCurve.Type.InQuad)
        
        # Settle
        settle_anim = QPropertyAnimation(widget, b"pos")
        settle_anim.setDuration(duration // 3)
        settle_anim.setStartValue(QPoint(current_pos.x(), current_pos.y() + 5))
        settle_anim.setEndValue(current_pos)
        settle_anim.setEasingCurve(QEasingCurve.Type.OutBounce)
        
        group.addAnimation(up_anim)
        group.addAnimation(down_anim)
        group.addAnimation(settle_anim)
        
        AnimationManager._store_animation(group)
        group.start()
        
        return group
    
    @staticmethod
    def shake(widget: QWidget, duration: int = 500,
              amplitude: int = 10) -> QSequentialAnimationGroup:
        """Shake animation for error states."""
        group = QSequentialAnimationGroup()
        
        current_pos = widget.pos()
        step_duration = duration // 6
        
        positions = [
            current_pos,
            QPoint(current_pos.x() - amplitude, current_pos.y()),
            QPoint(current_pos.x() + amplitude, current_pos.y()),
            QPoint(current_pos.x() - amplitude // 2, current_pos.y()),
            QPoint(current_pos.x() + amplitude // 2, current_pos.y()),
            current_pos
        ]
        
        for i in range(len(positions) - 1):
            anim = QPropertyAnimation(widget, b"pos")
            anim.setDuration(step_duration)
            anim.setStartValue(positions[i])
            anim.setEndValue(positions[i + 1])
            anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
            group.addAnimation(anim)
        
        AnimationManager._store_animation(group)
        group.start()
        
        return group
    
    @staticmethod
    def staggered_fade_in(widgets: list, duration: int = 300,
                          stagger_delay: int = 50) -> QParallelAnimationGroup:
        """Staggered fade in for multiple widgets."""
        group = QParallelAnimationGroup()
        
        for i, widget in enumerate(widgets):
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
            effect.setOpacity(0)
            
            anim = QPropertyAnimation(effect, b"opacity")
            anim.setDuration(duration)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            
            # Delay start based on index
            QTimer.singleShot(i * stagger_delay, anim.start)
            
            group.addAnimation(anim)
        
        AnimationManager._store_animation(group)
        
        return group


class PageTransition(QObject):
    """Page transition manager for smooth navigation."""
    
    transition_complete = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_page = None
        self._next_page = None
    
    def transition(self, from_widget: QWidget, to_widget: QWidget,
                   transition_type: str = "fade", duration: int = 300):
        """Perform page transition animation."""
        self._current_page = from_widget
        self._next_page = to_widget
        
        if transition_type == "fade":
            self._fade_transition(duration)
        elif transition_type == "slide_left":
            self._slide_transition("left", duration)
        elif transition_type == "slide_right":
            self._slide_transition("right", duration)
        elif transition_type == "slide_up":
            self._slide_transition("top", duration)
        elif transition_type == "slide_down":
            self._slide_transition("bottom", duration)
        else:
            # Default instant transition
            from_widget.hide()
            to_widget.show()
            self.transition_complete.emit()
    
    def _fade_transition(self, duration: int):
        """Fade transition between pages."""
        # Fade out current
        AnimationManager.fade_out(
            self._current_page,
            duration // 2,
            callback=self._on_fade_out_complete
        )
    
    def _on_fade_out_complete(self):
        """Handle fade out completion."""
        self._current_page.hide()
        self._next_page.show()
        AnimationManager.fade_in(
            self._next_page,
            duration=200,
            callback=lambda: self.transition_complete.emit()
        )
    
    def _slide_transition(self, direction: str, duration: int):
        """Slide transition between pages."""
        # Show next page
        self._next_page.show()
        
        # Slide out current and slide in next
        AnimationManager.slide_out(
            self._current_page,
            direction,
            duration // 2,
            callback=lambda: self._current_page.hide()
        )
        
        # Opposite direction for incoming
        opposite = {
            "left": "right",
            "right": "left",
            "top": "bottom",
            "bottom": "top"
        }
        
        AnimationManager.slide_in(
            self._next_page,
            opposite.get(direction, "right"),
            duration
        )
        
        QTimer.singleShot(duration, lambda: self.transition_complete.emit())


# Export
__all__ = ['AnimationManager', 'PageTransition']
