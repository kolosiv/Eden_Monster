"""Splash Screen for Eden Analytics Pro with Animated Intro Video.

Eden Intro V2 - "The Golden Apple Game"
Duration: 10 seconds
Features: Hockey gameplay, player competition, money explosion
Scenario:
  1. Golden Eden tree above hockey rink (0-2s)
  2. Golden apple falls onto ice (2-3s)
  3. Three hockey players battle for the apple (3-5s)
  4. One player shoots powerful slapshot (5-7s)
  5. Money explosion from goal (7-9s)
  6. "EDEN ANALYTICS PRO" text appears (9-10s)
"""

import os
import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QProgressBar,
    QGraphicsOpacityEffect, QApplication
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPixmap, QImage

from gui.themes.modern_theme import get_theme, get_logo_path

# Setup logger for splash screen
logger = logging.getLogger("eden.splash_screen")

# Try to import OpenCV for video playback
CV2_AVAILABLE = False
CV2_ERROR = None
try:
    import cv2
    CV2_AVAILABLE = True
    logger.info(f"OpenCV loaded successfully (version: {cv2.__version__})")
except ImportError as e:
    CV2_ERROR = str(e)
    logger.warning(f"OpenCV not available: {e}. Video playback will be disabled.")
except Exception as e:
    CV2_ERROR = str(e)
    logger.error(f"Error loading OpenCV: {e}")

VERSION = "3.0.0"

class SplashScreen(QWidget):
    """Modern splash screen with animated intro video."""
    
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._progress = 0
        self._video_playing = False
        self._video_capture = None
        self._video_timer = None
        self._skip_video = False
        
        # Eden Intro V2 - "The Golden Apple Game" (10 seconds)
        self.video_path = Path(__file__).parent / "assets" / "branding" / "eden_intro_v2.mp4"
        
        self._setup_ui()
        
        # Center on screen
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2
        )
    
    def _setup_ui(self):
        self.setFixedSize(640, 480)
        
        theme = get_theme()
        p = theme.palette
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Main container with gradient background
        self.container = QWidget()
        self.container.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {p.gradient_start}, stop:1 {p.gradient_end});
                border-radius: 20px;
            }}
        """)
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(20, 20, 20, 20)
        container_layout.setSpacing(10)
        
        # Video/Logo display area
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setFixedSize(600, 340)
        self.video_label.setStyleSheet("background-color: transparent; border-radius: 12px;")
        container_layout.addWidget(self.video_label)
        
        # App name (shown below video or as fallback)
        self.name_label = QLabel("Eden Analytics Pro")
        self.name_label.setStyleSheet("""
            color: white;
            font-size: 28px;
            font-weight: bold;
        """)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.name_label)
        
        # Tagline
        tagline = QLabel("Hockey Arbitrage Intelligence")
        tagline.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 13px;")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(tagline)
        
        # Skip hint
        self.skip_label = QLabel("Press any key or click to skip")
        self.skip_label.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 11px;")
        self.skip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.skip_label.setVisible(False)
        container_layout.addWidget(self.skip_label)
        
        # Loading text
        self.loading_label = QLabel("Initializing...")
        self.loading_label.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 12px;")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.loading_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: rgba(255,255,255,0.2);
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: white;
                border-radius: 3px;
            }}
        """)
        container_layout.addWidget(self.progress_bar)
        
        # Version
        version = QLabel(f"Version {VERSION}")
        version.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 11px;")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(version)
        
        layout.addWidget(self.container)
        
        # Opacity effect for fade animations
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(0)
        self.setGraphicsEffect(self.opacity_effect)
        
        # Show static logo initially
        self._show_static_logo()
    
    def _show_static_logo(self):
        """Show static logo as fallback."""
        logo_path = get_logo_path('dark', 'horizontal')
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            scaled = pixmap.scaled(
                500, 280,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.video_label.setPixmap(scaled)
        else:
            # Fallback to emoji
            self.video_label.setText("🏒💰")
            self.video_label.setStyleSheet("""
                font-size: 96px;
                background-color: transparent;
            """)
    
    def play_intro_video(self):
        """Start playing the intro video."""
        # Check OpenCV availability
        if not CV2_AVAILABLE:
            logger.warning(f"Cannot play video: OpenCV not available. Error: {CV2_ERROR}")
            logger.info("Tip: Install opencv-python with: pip install opencv-python>=4.8.0")
            self._show_static_logo()
            return False
        
        # Check video file existence
        if not self.video_path.exists():
            logger.error(f"Video file not found: {self.video_path}")
            logger.info(f"Expected path: {self.video_path.absolute()}")
            self._show_static_logo()
            return False
        
        # Check video file size and permissions
        try:
            file_size = self.video_path.stat().st_size
            logger.info(f"Video file found: {self.video_path} (size: {file_size / 1024 / 1024:.2f} MB)")
            
            if file_size < 1000:  # Less than 1KB - likely corrupted
                logger.error(f"Video file appears corrupted (size: {file_size} bytes)")
                self._show_static_logo()
                return False
        except Exception as e:
            logger.error(f"Cannot access video file: {e}")
            self._show_static_logo()
            return False
        
        try:
            import cv2
            logger.info(f"Opening video capture for: {self.video_path}")
            
            self._video_capture = cv2.VideoCapture(str(self.video_path))
            
            if not self._video_capture.isOpened():
                logger.error("Failed to open video file with OpenCV VideoCapture")
                logger.info("Possible causes: unsupported codec, corrupted file, or missing codecs")
                self._show_static_logo()
                return False
            
            # Get video properties for debugging
            width = int(self._video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self._video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self._video_capture.get(cv2.CAP_PROP_FPS) or 30
            frame_count = int(self._video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            
            logger.info(f"Video properties: {width}x{height}, {fps:.1f} FPS, "
                       f"{frame_count} frames, {duration:.1f}s duration")
            
            # Test read first frame
            ret, test_frame = self._video_capture.read()
            if not ret:
                logger.error("Cannot read first frame from video")
                self._video_capture.release()
                self._show_static_logo()
                return False
            
            # Reset to beginning
            self._video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            
            self._video_playing = True
            self.skip_label.setVisible(True)
            self.name_label.setVisible(False)
            
            # Calculate frame delay from FPS
            frame_delay = max(int(1000 / fps), 16)  # At least ~60fps cap
            logger.info(f"Starting video playback with {frame_delay}ms frame delay")
            
            # Timer for video frame updates
            self._video_timer = QTimer()
            self._video_timer.timeout.connect(self._update_video_frame)
            self._video_timer.start(frame_delay)
            
            return True
            
        except Exception as e:
            logger.error(f"Video playback error: {e}", exc_info=True)
            self._show_static_logo()
            return False
    
    def _update_video_frame(self):
        """Update video frame."""
        if not self._video_capture or self._skip_video:
            self._stop_video()
            return
        
        try:
            import cv2
            ret, frame = self._video_capture.read()
            if not ret:
                # Video ended
                logger.debug("Video playback completed")
                self._stop_video()
                return
            
            # Convert frame to QImage
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            
            # Create a copy of the data to avoid memory issues
            q_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
            pixmap = QPixmap.fromImage(q_image)
            
            # Scale to fit
            scaled = pixmap.scaled(
                600, 340,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.video_label.setPixmap(scaled)
            
        except Exception as e:
            logger.error(f"Error updating video frame: {e}")
            self._stop_video()
    
    def _stop_video(self):
        """Stop video playback."""
        self._video_playing = False
        
        if self._video_timer:
            self._video_timer.stop()
            self._video_timer = None
        
        if self._video_capture:
            self._video_capture.release()
            self._video_capture = None
        
        self.skip_label.setVisible(False)
        self.name_label.setVisible(True)
        self._show_static_logo()
    
    def skip_video(self):
        """Skip the intro video."""
        self._skip_video = True
        self._stop_video()
    
    def keyPressEvent(self, event):
        """Handle key press to skip video."""
        if self._video_playing:
            self.skip_video()
        super().keyPressEvent(event)
    
    def mousePressEvent(self, event):
        """Handle mouse click to skip video."""
        if self._video_playing:
            self.skip_video()
        super().mousePressEvent(event)
    
    def show_with_fade(self, duration: int = 500):
        """Show splash screen with fade-in animation."""
        self.show()
        
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(duration)
        self.fade_animation.setStartValue(0)
        self.fade_animation.setEndValue(1)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_animation.start()
    
    def close_with_fade(self, duration: int = 500):
        """Close splash screen with fade-out animation."""
        self._stop_video()  # Ensure video is stopped
        
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(duration)
        self.fade_animation.setStartValue(1)
        self.fade_animation.setEndValue(0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self.fade_animation.finished.connect(self.close)
        self.fade_animation.start()
    
    def set_progress(self, value: int, message: str = None):
        """Update progress bar and message."""
        self._progress = value
        self.progress_bar.setValue(value)
        
        if message:
            self.loading_label.setText(message)
    
    def increment_progress(self, amount: int = 10, message: str = None):
        """Increment progress."""
        self.set_progress(min(100, self._progress + amount), message)
    
    def closeEvent(self, event):
        """Handle close event."""
        self._stop_video()
        super().closeEvent(event)


def show_splash_screen(app: QApplication, callback=None, duration: int = 10000):
    """Show splash screen with animated intro and run callback after duration.
    
    Args:
        app: QApplication instance
        callback: Function to call after splash (typically shows main window)
        duration: How long to show splash in milliseconds (default 10s for V2 video)
    """
    splash = SplashScreen()
    splash.show_with_fade()
    
    # Try to play intro video
    video_started = splash.play_intro_video()
    
    # Adjust duration if video is not playing
    if not video_started:
        duration = 2500
    
    # Simulate loading progress
    loading_steps = [
        (10, "Loading configuration..."),
        (25, "Initializing database..."),
        (40, "Loading ML models..."),
        (55, "Connecting to API..."),
        (70, "Setting up GUI..."),
        (85, "Almost ready..."),
        (100, "Welcome!")
    ]
    
    current_step = [0]
    
    def update_progress():
        if current_step[0] < len(loading_steps):
            value, message = loading_steps[current_step[0]]
            splash.set_progress(value, message)
            current_step[0] += 1
    
    # Timer for progress updates
    progress_timer = QTimer()
    progress_timer.timeout.connect(update_progress)
    progress_timer.start(duration // len(loading_steps))
    
    # Timer to close splash and run callback
    def finish():
        progress_timer.stop()
        splash.close_with_fade()
        
        if callback:
            QTimer.singleShot(500, callback)
    
    QTimer.singleShot(duration, finish)
    
    return splash


__all__ = ['SplashScreen', 'show_splash_screen', 'VERSION']
