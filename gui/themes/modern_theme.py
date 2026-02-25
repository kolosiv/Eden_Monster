"""Premium Modern Theme System for Eden Analytics Pro v2.2.0."""

from dataclasses import dataclass
from typing import Dict, Optional
from enum import Enum


class ThemeType(Enum):
    DARK = "dark"
    LIGHT = "light"


@dataclass
class ColorPalette:
    """Color palette definition."""
    background: str
    surface: str
    surface_light: str
    card: str
    primary: str
    secondary: str
    accent: str
    success: str
    warning: str
    error: str
    text: str
    text_secondary: str
    text_muted: str
    border: str
    shadow: str
    gradient_start: str
    gradient_end: str
    glow: str


# Premium Dark Theme - Gold and Deep Blue
PREMIUM_DARK = ColorPalette(
    background='#0F0F1A',
    surface='#1A1A2E',
    surface_light='#252538',
    card='#1E1E32',
    primary='#FFD700',  # Gold
    secondary='#00D9FF',  # Cyan accent
    accent='#00D9FF',
    success='#00FF88',  # Bright green
    warning='#FFB800',  # Amber
    error='#FF4757',  # Red
    text='#FFFFFF',
    text_secondary='#B4B4C8',
    text_muted='#6B6B80',
    border='#2D2D44',
    shadow='rgba(0, 0, 0, 0.5)',
    gradient_start='#FFD700',
    gradient_end='#00D9FF',
    glow='rgba(255, 215, 0, 0.3)'
)

# Premium Light Theme
PREMIUM_LIGHT = ColorPalette(
    background='#FFFFFF',
    surface='#F8F9FA',
    surface_light='#F0F2F5',
    card='#FFFFFF',
    primary='#DAA520',  # Darker gold for light theme
    secondary='#0099CC',
    accent='#0099CC',
    success='#28A745',
    warning='#FFC107',
    error='#DC3545',
    text='#1A1A1A',
    text_secondary='#6C757D',
    text_muted='#9E9E9E',
    border='#DEE2E6',
    shadow='rgba(0, 0, 0, 0.1)',
    gradient_start='#DAA520',
    gradient_end='#0099CC',
    glow='rgba(218, 165, 32, 0.2)'
)

# Keep backward compatibility
DARK_PALETTE = PREMIUM_DARK
LIGHT_PALETTE = PREMIUM_LIGHT


# Glassmorphism effect styles
GLASS_EFFECT = """
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
"""

GLASS_EFFECT_LIGHT = """
    background: rgba(255, 255, 255, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.3);
    border-radius: 16px;
"""

# Neumorphism effect styles
NEURO_EFFECT_DARK = """
    background: linear-gradient(145deg, #1e1e2e, #1a1a28);
    box-shadow: 8px 8px 16px #0a0a0f, -8px -8px 16px #2e2e3d;
    border-radius: 20px;
"""

NEURO_EFFECT_LIGHT = """
    background: linear-gradient(145deg, #ffffff, #e6e6e6);
    box-shadow: 8px 8px 16px #c9c9c9, -8px -8px 16px #ffffff;
    border-radius: 20px;
"""


# Premium Animation Keyframes
ANIMATIONS = {
    'fade_in': """
        /* Fade in animation */
    """,
    'slide_in': """
        /* Slide in animation */
    """,
    'glow_pulse': """
        /* Glow pulse animation */
    """,
    'shimmer': """
        /* Shimmer animation */
    """,
}


class ModernTheme:
    """Modern theme manager for Eden Analytics Pro."""
    
    # Fonts
    FONT_FAMILY = "'Segoe UI', 'SF Pro Display', 'Roboto', sans-serif"
    FONT_MONO = "'JetBrains Mono', 'Consolas', 'Monaco', monospace"
    
    # Sizing
    BORDER_RADIUS_SM = "4px"
    BORDER_RADIUS = "8px"
    BORDER_RADIUS_LG = "12px"
    BORDER_RADIUS_XL = "16px"
    BORDER_RADIUS_XXL = "20px"
    
    # Spacing
    SPACING_XS = "4px"
    SPACING_SM = "8px"
    SPACING = "12px"
    SPACING_MD = "16px"
    SPACING_LG = "24px"
    SPACING_XL = "32px"
    
    # Premium Shadows
    SHADOW_SM = "0 2px 4px rgba(0,0,0,0.1)"
    SHADOW = "0 4px 12px rgba(0,0,0,0.15)"
    SHADOW_LG = "0 8px 24px rgba(0,0,0,0.2)"
    SHADOW_XL = "0 12px 48px rgba(0,0,0,0.25)"
    SHADOW_GLOW = "0 0 30px rgba(255, 215, 0, 0.3)"
    
    # Animation durations
    TRANSITION_FAST = "0.15s"
    TRANSITION = "0.25s"
    TRANSITION_SLOW = "0.4s"
    
    def __init__(self, theme_type: ThemeType = ThemeType.DARK):
        self.theme_type = theme_type
        self.palette = PREMIUM_DARK if theme_type == ThemeType.DARK else PREMIUM_LIGHT
    
    def set_theme(self, theme_type: ThemeType):
        """Switch theme."""
        self.theme_type = theme_type
        self.palette = PREMIUM_DARK if theme_type == ThemeType.DARK else PREMIUM_LIGHT
    
    def toggle_theme(self):
        """Toggle between dark and light theme."""
        if self.theme_type == ThemeType.DARK:
            self.set_theme(ThemeType.LIGHT)
        else:
            self.set_theme(ThemeType.DARK)
    
    def get_glass_effect(self) -> str:
        """Get glassmorphism effect for current theme."""
        return GLASS_EFFECT if self.theme_type == ThemeType.DARK else GLASS_EFFECT_LIGHT
    
    def get_neuro_effect(self) -> str:
        """Get neumorphism effect for current theme."""
        return NEURO_EFFECT_DARK if self.theme_type == ThemeType.DARK else NEURO_EFFECT_LIGHT
    
    def get_main_stylesheet(self) -> str:
        """Generate the main application stylesheet."""
        p = self.palette
        return f"""
            /* ===== GLOBAL STYLES ===== */
            QMainWindow, QWidget {{
                background-color: {p.background};
                color: {p.text};
                font-family: {self.FONT_FAMILY};
                font-size: 13px;
            }}
            
            /* ===== PREMIUM SCROLLBARS ===== */
            QScrollBar:vertical {{
                background-color: {p.surface};
                width: 12px;
                margin: 4px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {p.primary}, stop:1 {p.secondary});
                min-height: 30px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {p.secondary}, stop:1 {p.primary});
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background-color: {p.surface};
                height: 12px;
                margin: 4px;
                border-radius: 6px;
            }}
            QScrollBar::handle:horizontal {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {p.primary}, stop:1 {p.secondary});
                min-width: 30px;
                border-radius: 6px;
            }}
            
            /* ===== LABELS ===== */
            QLabel {{
                color: {p.text};
                background: transparent;
            }}
            
            /* ===== PREMIUM BUTTONS ===== */
            QPushButton {{
                background-color: {p.surface_light};
                color: {p.text};
                border: 1px solid {p.border};
                padding: 12px 24px;
                border-radius: {self.BORDER_RADIUS_LG};
                font-weight: 600;
                font-size: 14px;
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
            QPushButton:disabled {{
                background-color: {p.surface};
                color: {p.text_muted};
                border: 1px solid {p.border};
            }}
            
            /* ===== PRIMARY BUTTON ===== */
            QPushButton[class="primary"] {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {p.primary}, stop:1 {p.secondary});
                color: #000000;
                border: none;
                font-weight: 700;
            }}
            QPushButton[class="primary"]:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {p.secondary}, stop:1 {p.primary});
            }}
            
            /* ===== PREMIUM INPUT FIELDS ===== */
            QLineEdit, QTextEdit, QPlainTextEdit {{
                background-color: {p.surface};
                color: {p.text};
                border: 2px solid {p.border};
                padding: 14px 18px;
                border-radius: {self.BORDER_RADIUS_LG};
                selection-background-color: {p.primary};
                font-size: 14px;
            }}
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
                border-color: {p.primary};
                background-color: {p.card};
            }}
            QLineEdit::placeholder {{
                color: {p.text_muted};
            }}
            
            /* ===== SPIN BOXES ===== */
            QSpinBox, QDoubleSpinBox {{
                background-color: {p.surface};
                color: {p.text};
                border: 2px solid {p.border};
                padding: 10px 14px;
                border-radius: {self.BORDER_RADIUS_LG};
                font-size: 14px;
            }}
            QSpinBox:focus, QDoubleSpinBox:focus {{
                border-color: {p.primary};
            }}
            QSpinBox::up-button, QDoubleSpinBox::up-button,
            QSpinBox::down-button, QDoubleSpinBox::down-button {{
                background-color: {p.surface_light};
                border: none;
                width: 24px;
                border-radius: 4px;
            }}
            QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
            QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
                background-color: {p.primary};
            }}
            
            /* ===== COMBO BOXES ===== */
            QComboBox {{
                background-color: {p.surface};
                color: {p.text};
                border: 2px solid {p.border};
                padding: 10px 14px;
                border-radius: {self.BORDER_RADIUS_LG};
                font-size: 14px;
            }}
            QComboBox:focus {{
                border-color: {p.primary};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 32px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {p.surface};
                color: {p.text};
                selection-background-color: {p.primary};
                selection-color: #000000;
                border: 1px solid {p.border};
                border-radius: {self.BORDER_RADIUS};
                padding: 4px;
            }}
            
            /* ===== PREMIUM TAB WIDGET ===== */
            QTabWidget::pane {{
                border: 1px solid {p.border};
                border-radius: {self.BORDER_RADIUS_LG};
                background-color: {p.surface};
                padding: 8px;
            }}
            QTabBar::tab {{
                background-color: transparent;
                color: {p.text_secondary};
                padding: 14px 28px;
                margin-right: 4px;
                border-top-left-radius: {self.BORDER_RADIUS_LG};
                border-top-right-radius: {self.BORDER_RADIUS_LG};
                font-weight: 600;
                font-size: 14px;
            }}
            QTabBar::tab:selected {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {p.primary}, stop:1 {p.secondary});
                color: #000000;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {p.surface_light};
                color: {p.text};
            }}
            
            /* ===== GROUP BOX ===== */
            QGroupBox {{
                border: 1px solid {p.border};
                border-radius: {self.BORDER_RADIUS_LG};
                margin-top: 20px;
                padding: 20px;
                padding-top: 28px;
                background-color: {p.surface};
            }}
            QGroupBox::title {{
                color: {p.primary};
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 16px;
                padding: 0 12px;
                font-weight: 700;
                font-size: 14px;
            }}
            
            /* ===== PREMIUM TABLES ===== */
            QTableWidget, QTableView {{
                background-color: {p.surface};
                gridline-color: {p.border};
                border: 1px solid {p.border};
                border-radius: {self.BORDER_RADIUS_LG};
                selection-background-color: rgba({self._hex_to_rgb(p.primary)}, 0.2);
            }}
            QTableWidget::item, QTableView::item {{
                padding: 12px 16px;
                border-bottom: 1px solid {p.border};
            }}
            QTableWidget::item:selected, QTableView::item:selected {{
                background-color: rgba({self._hex_to_rgb(p.primary)}, 0.2);
                color: {p.text};
            }}
            QTableWidget::item:hover, QTableView::item:hover {{
                background-color: rgba({self._hex_to_rgb(p.primary)}, 0.1);
            }}
            QHeaderView::section {{
                background-color: {p.card};
                color: {p.text_secondary};
                padding: 14px 16px;
                border: none;
                border-bottom: 2px solid {p.primary};
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 1px;
                font-size: 12px;
            }}
            
            /* ===== PREMIUM PROGRESS BAR ===== */
            QProgressBar {{
                background-color: {p.surface};
                border: none;
                border-radius: {self.BORDER_RADIUS};
                height: 20px;
                text-align: center;
                color: {p.text};
                font-weight: 600;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {p.primary}, stop:0.5 {p.secondary}, stop:1 {p.success});
                border-radius: {self.BORDER_RADIUS};
            }}
            
            /* ===== SLIDERS ===== */
            QSlider::groove:horizontal {{
                background-color: {p.surface_light};
                height: 8px;
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {p.primary}, stop:1 {p.secondary});
                width: 22px;
                height: 22px;
                margin: -7px 0;
                border-radius: 11px;
            }}
            QSlider::handle:horizontal:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {p.secondary}, stop:1 {p.primary});
            }}
            
            /* ===== CHECKBOXES ===== */
            QCheckBox {{
                spacing: 10px;
                color: {p.text};
                font-size: 14px;
            }}
            QCheckBox::indicator {{
                width: 22px;
                height: 22px;
                border-radius: 6px;
                border: 2px solid {p.border};
                background-color: {p.surface};
            }}
            QCheckBox::indicator:checked {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {p.primary}, stop:1 {p.secondary});
                border: none;
            }}
            
            /* ===== RADIO BUTTONS ===== */
            QRadioButton {{
                spacing: 10px;
                color: {p.text};
                font-size: 14px;
            }}
            QRadioButton::indicator {{
                width: 22px;
                height: 22px;
                border-radius: 11px;
                border: 2px solid {p.border};
                background-color: {p.surface};
            }}
            QRadioButton::indicator:checked {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {p.primary}, stop:1 {p.secondary});
                border: none;
            }}
            
            /* ===== PREMIUM MENU ===== */
            QMenu {{
                background-color: {p.surface};
                border: 1px solid {p.border};
                border-radius: {self.BORDER_RADIUS_LG};
                padding: 8px;
            }}
            QMenu::item {{
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 14px;
            }}
            QMenu::item:selected {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {p.primary}, stop:1 {p.secondary});
                color: #000000;
            }}
            
            /* ===== STATUS BAR ===== */
            QStatusBar {{
                background-color: {p.surface};
                border-top: 1px solid {p.border};
                padding: 8px 16px;
                font-size: 13px;
            }}
            
            /* ===== TOOLTIPS ===== */
            QToolTip {{
                background-color: {p.card};
                color: {p.text};
                border: 1px solid {p.border};
                border-radius: {self.BORDER_RADIUS};
                padding: 10px 14px;
                font-size: 13px;
            }}
            
            /* ===== MESSAGE BOX ===== */
            QMessageBox {{
                background-color: {p.surface};
            }}
            QMessageBox QLabel {{
                color: {p.text};
                font-size: 14px;
            }}
            
            /* ===== SPLITTER ===== */
            QSplitter::handle {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {p.primary}, stop:1 {p.secondary});
                border-radius: 2px;
            }}
            QSplitter::handle:horizontal {{
                width: 4px;
            }}
            QSplitter::handle:vertical {{
                height: 4px;
            }}
        """
    
    def _hex_to_rgb(self, hex_color: str) -> str:
        """Convert hex color to RGB values."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            return f"{r}, {g}, {b}"
        return "255, 255, 255"
    
    def get_card_style(self, elevated: bool = False, glass: bool = False) -> str:
        """Get style for card widgets."""
        p = self.palette
        if glass:
            return f"""
                background: rgba({self._hex_to_rgb(p.surface)}, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: {self.BORDER_RADIUS_XL};
                padding: {self.SPACING_MD};
            """
        return f"""
            background-color: {p.surface};
            border-radius: {self.BORDER_RADIUS_XL};
            border: 1px solid {p.border};
            padding: {self.SPACING_MD};
        """
    
    def get_stat_card_style(self, color: str = None, glow: bool = False) -> str:
        """Get style for stat cards with optional glow effect."""
        p = self.palette
        accent = color or p.primary
        glow_style = f"box-shadow: 0 0 30px rgba({self._hex_to_rgb(accent)}, 0.3);" if glow else ""
        return f"""
            QFrame {{
                background-color: {p.surface};
                border-radius: {self.BORDER_RADIUS_XL};
                border-left: 4px solid {accent};
                padding: {self.SPACING_MD};
                {glow_style}
            }}
        """
    
    def get_premium_button_style(self, style: str = 'primary') -> str:
        """Get premium button styles."""
        p = self.palette
        styles = {
            'primary': f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 {p.primary}, stop:1 {p.secondary});
                    color: #000000;
                    border: none;
                    border-radius: {self.BORDER_RADIUS_LG};
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
            """,
            'secondary': f"""
                QPushButton {{
                    background: transparent;
                    color: {p.text};
                    border: 2px solid {p.primary};
                    border-radius: {self.BORDER_RADIUS_LG};
                    padding: 12px 24px;
                    font-size: 14px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: rgba({self._hex_to_rgb(p.primary)}, 0.1);
                    border-color: {p.secondary};
                }}
            """,
            'ghost': f"""
                QPushButton {{
                    background: rgba(255, 255, 255, 0.05);
                    color: {p.text};
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: {self.BORDER_RADIUS_LG};
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
                    border-radius: {self.BORDER_RADIUS_LG};
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
                    border-radius: {self.BORDER_RADIUS_LG};
                    padding: 12px 24px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: #00ff99;
                }}
            """
        }
        return styles.get(style, styles['primary'])


# Global theme instance
_current_theme: Optional[ModernTheme] = None


def get_theme() -> ModernTheme:
    """Get the current theme instance."""
    global _current_theme
    if _current_theme is None:
        _current_theme = ModernTheme(ThemeType.DARK)
    return _current_theme


def set_theme(theme_type: ThemeType):
    """Set the global theme."""
    global _current_theme
    if _current_theme is None:
        _current_theme = ModernTheme(theme_type)
    else:
        _current_theme.set_theme(theme_type)


# Logo paths configuration
LOGO_PATHS = {
    'full': 'gui/assets/branding/eden_logo_full.png',
    'icon': 'gui/assets/branding/eden_logo_icon.png',
    'horizontal': 'gui/assets/branding/eden_logo_horizontal.png',
    'dark': 'gui/assets/branding/eden_logo_dark.png'
}

BRANDING_ASSETS = {
    'intro_video': 'gui/assets/branding/eden_intro_animation.mp4',
    'app_icon_ico': 'gui/assets/branding/eden.ico',
    'app_icon_icns': 'gui/assets/branding/eden.icns'
}


def get_logo_path(theme: str = 'light', style: str = 'horizontal') -> str:
    """Get appropriate logo path based on theme and style."""
    import os
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent.parent
    
    if theme == 'dark' and style != 'icon':
        logo_key = 'dark'
    else:
        logo_key = style if style in LOGO_PATHS else 'horizontal'
    
    logo_rel_path = LOGO_PATHS.get(logo_key, LOGO_PATHS['horizontal'])
    return str(project_root / logo_rel_path)


def get_branding_asset(asset_name: str) -> str:
    """Get path to a branding asset."""
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent.parent
    asset_rel_path = BRANDING_ASSETS.get(asset_name, '')
    return str(project_root / asset_rel_path)


__all__ = ['ModernTheme', 'ThemeType', 'ColorPalette', 'get_theme', 'set_theme',
           'DARK_PALETTE', 'LIGHT_PALETTE', 'PREMIUM_DARK', 'PREMIUM_LIGHT',
           'GLASS_EFFECT', 'NEURO_EFFECT_DARK', 'ANIMATIONS',
           'LOGO_PATHS', 'get_logo_path', 'get_branding_asset', 'BRANDING_ASSETS']
