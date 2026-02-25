"""About Dialog for Eden Analytics Pro."""

import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QFont, QPixmap

from gui.themes.modern_theme import get_theme, get_logo_path
from gui.components.modern_widgets import ModernButton


class AboutDialog(QDialog):
    """Professional About dialog."""
    
    VERSION = "2.1.1"
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Eden Analytics Pro")
        self.setFixedSize(480, 560)
        self.setModal(True)
        
        self._setup_ui()
    
    def _setup_ui(self):
        theme = get_theme()
        p = theme.palette
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {p.surface};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        # Logo
        logo = QLabel()
        logo_path = get_logo_path('dark', 'full')
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            scaled = pixmap.scaled(280, 120, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
            logo.setPixmap(scaled)
        else:
            logo.setText("🏒")
            logo.setStyleSheet("font-size: 64px;")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)
        
        # App Name
        name = QLabel("Eden Analytics Pro")
        name.setStyleSheet(f"""
            font-size: 28px;
            font-weight: bold;
            color: {p.primary};
        """)
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name)
        
        # Tagline
        tagline = QLabel("Hockey Arbitrage Intelligence")
        tagline.setStyleSheet(f"color: {p.text_secondary}; font-size: 14px;")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tagline)
        
        # Version
        version = QLabel(f"Version {self.VERSION}")
        version.setStyleSheet(f"""
            color: {p.text_muted};
            font-size: 12px;
            padding: 8px 16px;
            background-color: {p.surface_light};
            border-radius: 12px;
        """)
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version, alignment=Qt.AlignmentFlag.AlignCenter)
        
        layout.addSpacing(20)
        
        # Description
        description = QLabel(
            "Eden Analytics Pro is a comprehensive hockey betting analysis system "
            "featuring ML-powered predictions, arbitrage detection, and smart "
            "bankroll management."
        )
        description.setWordWrap(True)
        description.setStyleSheet(f"color: {p.text_secondary}; font-size: 13px;")
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(description)
        
        # Features list
        features_frame = QFrame()
        features_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {p.surface_light};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        features_layout = QVBoxLayout(features_frame)
        features_layout.setSpacing(8)
        
        features = [
            "🤖 ML-Powered Overtime Prediction",
            "📊 Real-time Arbitrage Detection", 
            "💰 Smart Bankroll Management",
            "📈 Performance Analytics",
            "🔔 Telegram Bot Integration"
        ]
        
        for feature in features:
            lbl = QLabel(feature)
            lbl.setStyleSheet(f"color: {p.text}; font-size: 12px;")
            features_layout.addWidget(lbl)
        
        layout.addWidget(features_frame)
        
        layout.addStretch()
        
        # Links
        links_layout = QHBoxLayout()
        links_layout.setSpacing(16)
        
        github_btn = QPushButton("GitHub")
        github_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        github_btn.setStyleSheet(f"""
            QPushButton {{
                color: {p.primary};
                background: transparent;
                border: none;
                text-decoration: underline;
            }}
            QPushButton:hover {{
                color: {p.secondary};
            }}
        """)
        github_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com")))
        links_layout.addWidget(github_btn)
        
        docs_btn = QPushButton("Documentation")
        docs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        docs_btn.setStyleSheet(github_btn.styleSheet())
        links_layout.addWidget(docs_btn)
        
        support_btn = QPushButton("Support")
        support_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        support_btn.setStyleSheet(github_btn.styleSheet())
        links_layout.addWidget(support_btn)
        
        layout.addLayout(links_layout)
        
        # Copyright
        copyright = QLabel("© 2026 Eden Analytics Pro. All rights reserved.")
        copyright.setStyleSheet(f"color: {p.text_muted}; font-size: 11px;")
        copyright.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(copyright)
        
        # Close button
        close_btn = ModernButton("Close", primary=True)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)


__all__ = ['AboutDialog']
