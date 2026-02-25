"""Settings Panel Widget for Eden MVP GUI."""

import yaml
from pathlib import Path
from typing import Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QGroupBox, QPushButton, QSpinBox, QDoubleSpinBox,
    QCheckBox, QLineEdit, QMessageBox, QScrollArea, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class SettingsPanelWidget(QWidget):
    """Panel widget for application settings."""
    
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, config_path: str = None, parent=None):
        super().__init__(parent)
        self.config_path = Path(config_path) if config_path else Path("config/config.yaml")
        self.config: Dict[str, Any] = {}
        self._setup_ui()
        self.load_config()
    
    def _setup_ui(self):
        """Setup the UI components."""
        main_layout = QVBoxLayout(self)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content = QWidget()
        layout = QVBoxLayout(content)
        
        # Title
        title = QLabel("⚙️ Settings")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #00d9ff;")
        layout.addWidget(title)
        
        # Demo Mode
        demo_group = QGroupBox("Mode")
        demo_layout = QHBoxLayout(demo_group)
        
        self.demo_mode_check = QCheckBox("Demo Mode (use simulated data)")
        demo_layout.addWidget(self.demo_mode_check)
        
        layout.addWidget(demo_group)
        
        # API Settings
        api_group = QGroupBox("API Configuration")
        api_layout = QGridLayout(api_group)
        
        api_layout.addWidget(QLabel("The Odds API Key:"), 0, 0)
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Enter your API key")
        api_layout.addWidget(self.api_key_input, 0, 1)
        
        self.show_key_check = QCheckBox("Show")
        self.show_key_check.toggled.connect(self._toggle_key_visibility)
        api_layout.addWidget(self.show_key_check, 0, 2)
        
        api_layout.addWidget(QLabel("Sport:"), 1, 0)
        self.sport_combo = QComboBox()
        self.sport_combo.addItems(["icehockey_nhl", "icehockey_ahl", "icehockey_khl"])
        api_layout.addWidget(self.sport_combo, 1, 1)
        
        api_layout.addWidget(QLabel("Regions:"), 2, 0)
        self.regions_input = QLineEdit()
        self.regions_input.setPlaceholderText("us,eu")
        api_layout.addWidget(self.regions_input, 2, 1)
        
        layout.addWidget(api_group)
        
        # Bankroll Settings
        bankroll_group = QGroupBox("Bankroll Settings")
        bankroll_layout = QGridLayout(bankroll_group)
        
        bankroll_layout.addWidget(QLabel("Total Bankroll ($):"), 0, 0)
        self.bankroll_spin = QDoubleSpinBox()
        self.bankroll_spin.setRange(100, 1000000)
        self.bankroll_spin.setValue(1000)
        self.bankroll_spin.setDecimals(2)
        bankroll_layout.addWidget(self.bankroll_spin, 0, 1)
        
        bankroll_layout.addWidget(QLabel("Min Stake (%):"), 1, 0)
        self.min_stake_spin = QDoubleSpinBox()
        self.min_stake_spin.setRange(0.5, 20)
        self.min_stake_spin.setValue(2)
        self.min_stake_spin.setDecimals(1)
        bankroll_layout.addWidget(self.min_stake_spin, 1, 1)
        
        bankroll_layout.addWidget(QLabel("Max Stake (%):"), 2, 0)
        self.max_stake_spin = QDoubleSpinBox()
        self.max_stake_spin.setRange(1, 50)
        self.max_stake_spin.setValue(10)
        self.max_stake_spin.setDecimals(1)
        bankroll_layout.addWidget(self.max_stake_spin, 2, 1)
        
        bankroll_layout.addWidget(QLabel("Default Stake (%):"), 3, 0)
        self.default_stake_spin = QDoubleSpinBox()
        self.default_stake_spin.setRange(0.5, 20)
        self.default_stake_spin.setValue(4)
        self.default_stake_spin.setDecimals(1)
        bankroll_layout.addWidget(self.default_stake_spin, 3, 1)
        
        layout.addWidget(bankroll_group)
        
        # Risk Settings
        risk_group = QGroupBox("Risk Parameters")
        risk_layout = QGridLayout(risk_group)
        
        risk_layout.addWidget(QLabel("Max Hole Probability (%):"), 0, 0)
        self.max_hole_spin = QDoubleSpinBox()
        self.max_hole_spin.setRange(1, 50)  # Increased max from 10% to 50% for more flexibility
        self.max_hole_spin.setValue(4)
        self.max_hole_spin.setDecimals(1)
        risk_layout.addWidget(self.max_hole_spin, 0, 1)
        
        risk_layout.addWidget(QLabel("Min ROI (%):"), 1, 0)
        self.min_roi_spin = QDoubleSpinBox()
        self.min_roi_spin.setRange(0.5, 10)
        self.min_roi_spin.setValue(2)
        self.min_roi_spin.setDecimals(1)
        risk_layout.addWidget(self.min_roi_spin, 1, 1)
        
        risk_layout.addWidget(QLabel("Kelly Shrink Factor:"), 2, 0)
        self.kelly_shrink_spin = QDoubleSpinBox()
        self.kelly_shrink_spin.setRange(0.1, 1.0)
        self.kelly_shrink_spin.setValue(0.5)
        self.kelly_shrink_spin.setDecimals(2)
        risk_layout.addWidget(self.kelly_shrink_spin, 2, 1)
        
        layout.addWidget(risk_group)
        
        # OT Model Settings
        ot_group = QGroupBox("OT Prediction Model")
        ot_layout = QGridLayout(ot_group)
        
        self.use_ml_check = QCheckBox("Use ML Model (if trained)")
        self.use_ml_check.setChecked(True)
        ot_layout.addWidget(self.use_ml_check, 0, 0, 1, 2)
        
        ot_layout.addWidget(QLabel("Base OT Rate (%):"), 1, 0)
        self.base_ot_spin = QDoubleSpinBox()
        self.base_ot_spin.setRange(15, 35)
        self.base_ot_spin.setValue(23)
        self.base_ot_spin.setDecimals(1)
        ot_layout.addWidget(self.base_ot_spin, 1, 1)
        
        ot_layout.addWidget(QLabel("Favorite OT Advantage (%):"), 2, 0)
        self.fav_ot_spin = QDoubleSpinBox()
        self.fav_ot_spin.setRange(50, 70)
        self.fav_ot_spin.setValue(55)
        self.fav_ot_spin.setDecimals(1)
        ot_layout.addWidget(self.fav_ot_spin, 2, 1)
        
        layout.addWidget(ot_group)
        
        # Logging Settings
        log_group = QGroupBox("Logging")
        log_layout = QGridLayout(log_group)
        
        log_layout.addWidget(QLabel("Log Level:"), 0, 0)
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        log_layout.addWidget(self.log_level_combo, 0, 1)
        
        layout.addWidget(log_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("💾 Save Settings")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                padding: 10px 20px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #27ae60; }
        """)
        self.save_btn.clicked.connect(self.save_config)
        btn_layout.addWidget(self.save_btn)
        
        self.reset_btn = QPushButton("🔄 Reset to Defaults")
        self.reset_btn.clicked.connect(self.reset_to_defaults)
        btn_layout.addWidget(self.reset_btn)
        
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        # Status
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        scroll.setWidget(content)
        main_layout.addWidget(scroll)
    
    def _toggle_key_visibility(self, checked: bool):
        """Toggle API key visibility."""
        mode = QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        self.api_key_input.setEchoMode(mode)
    
    def load_config(self):
        """Load configuration from file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    self.config = yaml.safe_load(f) or {}
                self._update_ui_from_config()
                self.status_label.setText("Configuration loaded.")
                self.status_label.setStyleSheet("color: #888;")
            else:
                self.status_label.setText("No config file found. Using defaults.")
                self.status_label.setStyleSheet("color: #f39c12;")
        except Exception as e:
            self.status_label.setText(f"Error loading config: {e}")
            self.status_label.setStyleSheet("color: #e74c3c;")
    
    def _update_ui_from_config(self):
        """Update UI elements from loaded config."""
        # Demo mode
        self.demo_mode_check.setChecked(self.config.get('demo_mode', True))
        
        # API
        api_config = self.config.get('api', {}).get('the_odds_api', {})
        key = api_config.get('key', '')
        if key != 'YOUR_API_KEY_HERE':
            self.api_key_input.setText(key)
        self.sport_combo.setCurrentText(api_config.get('sport', 'icehockey_nhl'))
        self.regions_input.setText(api_config.get('regions', 'us,eu'))
        
        # Bankroll
        bankroll = self.config.get('bankroll', {})
        self.bankroll_spin.setValue(bankroll.get('total', 1000))
        self.min_stake_spin.setValue(bankroll.get('min_stake_percent', 2))
        self.max_stake_spin.setValue(bankroll.get('max_stake_percent', 10))
        self.default_stake_spin.setValue(bankroll.get('default_stake_percent', 4))
        
        # Risk
        risk = self.config.get('risk', {})
        self.max_hole_spin.setValue(risk.get('max_hole_probability', 0.04) * 100)
        self.min_roi_spin.setValue(risk.get('min_roi', 0.02) * 100)
        self.kelly_shrink_spin.setValue(risk.get('kelly_shrink', 0.5))
        
        # OT Model
        ot_model = self.config.get('ot_model', {})
        self.base_ot_spin.setValue(ot_model.get('base_ot_rate', 0.23) * 100)
        self.fav_ot_spin.setValue(ot_model.get('favorite_ot_advantage', 0.55) * 100)
        
        # Logging
        log_level = self.config.get('logging', {}).get('level', 'INFO')
        idx = self.log_level_combo.findText(log_level)
        if idx >= 0:
            self.log_level_combo.setCurrentIndex(idx)
    
    def save_config(self):
        """Save configuration to file."""
        try:
            # Update config dict from UI
            self.config['demo_mode'] = self.demo_mode_check.isChecked()
            
            if 'api' not in self.config:
                self.config['api'] = {'the_odds_api': {}}
            api = self.config['api']['the_odds_api']
            api['key'] = self.api_key_input.text() or 'YOUR_API_KEY_HERE'
            api['sport'] = self.sport_combo.currentText()
            api['regions'] = self.regions_input.text()
            
            if 'bankroll' not in self.config:
                self.config['bankroll'] = {}
            self.config['bankroll']['total'] = self.bankroll_spin.value()
            self.config['bankroll']['min_stake_percent'] = self.min_stake_spin.value()
            self.config['bankroll']['max_stake_percent'] = self.max_stake_spin.value()
            self.config['bankroll']['default_stake_percent'] = self.default_stake_spin.value()
            
            if 'risk' not in self.config:
                self.config['risk'] = {}
            self.config['risk']['max_hole_probability'] = self.max_hole_spin.value() / 100
            self.config['risk']['min_roi'] = self.min_roi_spin.value() / 100
            self.config['risk']['kelly_shrink'] = self.kelly_shrink_spin.value()
            
            if 'ot_model' not in self.config:
                self.config['ot_model'] = {}
            self.config['ot_model']['base_ot_rate'] = self.base_ot_spin.value() / 100
            self.config['ot_model']['favorite_ot_advantage'] = self.fav_ot_spin.value() / 100
            
            if 'logging' not in self.config:
                self.config['logging'] = {}
            self.config['logging']['level'] = self.log_level_combo.currentText()
            
            # Save to file
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
            
            self.status_label.setText("✅ Settings saved successfully!")
            self.status_label.setStyleSheet("color: #2ecc71;")
            
            self.settings_changed.emit(self.config)
            
        except Exception as e:
            self.status_label.setText(f"❌ Error saving: {e}")
            self.status_label.setStyleSheet("color: #e74c3c;")
            QMessageBox.critical(self, "Save Error", str(e))
    
    def reset_to_defaults(self):
        """Reset settings to defaults."""
        reply = QMessageBox.question(
            self, "Reset Settings",
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.demo_mode_check.setChecked(True)
            self.api_key_input.clear()
            self.sport_combo.setCurrentText("icehockey_nhl")
            self.regions_input.setText("us,eu")
            self.bankroll_spin.setValue(1000)
            self.min_stake_spin.setValue(2)
            self.max_stake_spin.setValue(10)
            self.default_stake_spin.setValue(4)
            self.max_hole_spin.setValue(4)
            self.min_roi_spin.setValue(2)
            self.kelly_shrink_spin.setValue(0.5)
            self.base_ot_spin.setValue(23)
            self.fav_ot_spin.setValue(55)
            self.log_level_combo.setCurrentText("INFO")
            self.use_ml_check.setChecked(True)
            
            self.status_label.setText("Settings reset to defaults.")
            self.status_label.setStyleSheet("color: #f39c12;")
    
    def get_config(self) -> Dict[str, Any]:
        """Get current config dict."""
        return self.config.copy()
