"""Match Details Widget for Eden MVP GUI."""

from typing import Optional, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QGroupBox, QTextEdit, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from analysis.match_analyzer import MatchAnalysis, Recommendation, RiskLevel


class MatchDetailsWidget(QWidget):
    """Widget for displaying detailed match analysis."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_analysis: Optional[MatchAnalysis] = None
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        # Header
        self.header_label = QLabel("Select a match to view details")
        self.header_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.header_label)
        
        # Teams info
        teams_group = QGroupBox("Match Info")
        teams_layout = QGridLayout(teams_group)
        
        self.home_team_label = QLabel("")
        self.away_team_label = QLabel("")
        self.time_label = QLabel("")
        
        teams_layout.addWidget(QLabel("Strong Team:"), 0, 0)
        teams_layout.addWidget(self.home_team_label, 0, 1)
        teams_layout.addWidget(QLabel("Weak Team:"), 1, 0)
        teams_layout.addWidget(self.away_team_label, 1, 1)
        teams_layout.addWidget(QLabel("Time:"), 2, 0)
        teams_layout.addWidget(self.time_label, 2, 1)
        
        content_layout.addWidget(teams_group)
        
        # Odds & Bookmakers
        odds_group = QGroupBox("Odds & Bookmakers")
        odds_layout = QGridLayout(odds_group)
        
        self.strong_odds_label = QLabel("")
        self.weak_odds_label = QLabel("")
        self.strong_book_label = QLabel("")
        self.weak_book_label = QLabel("")
        
        odds_layout.addWidget(QLabel("Strong Team Odds:"), 0, 0)
        odds_layout.addWidget(self.strong_odds_label, 0, 1)
        odds_layout.addWidget(QLabel("Bookmaker:"), 0, 2)
        odds_layout.addWidget(self.strong_book_label, 0, 3)
        odds_layout.addWidget(QLabel("Weak Team Odds:"), 1, 0)
        odds_layout.addWidget(self.weak_odds_label, 1, 1)
        odds_layout.addWidget(QLabel("Bookmaker:"), 1, 2)
        odds_layout.addWidget(self.weak_book_label, 1, 3)
        
        content_layout.addWidget(odds_group)
        
        # Arbitrage Analysis
        arb_group = QGroupBox("Arbitrage Analysis")
        arb_layout = QGridLayout(arb_group)
        
        self.roi_label = QLabel("")
        self.arb_pct_label = QLabel("")
        self.ev_label = QLabel("")
        
        arb_layout.addWidget(QLabel("ROI:"), 0, 0)
        arb_layout.addWidget(self.roi_label, 0, 1)
        arb_layout.addWidget(QLabel("Arbitrage %:"), 1, 0)
        arb_layout.addWidget(self.arb_pct_label, 1, 1)
        arb_layout.addWidget(QLabel("Expected Value:"), 2, 0)
        arb_layout.addWidget(self.ev_label, 2, 1)
        
        content_layout.addWidget(arb_group)
        
        # OT Prediction
        ot_group = QGroupBox("Overtime Prediction")
        ot_layout = QGridLayout(ot_group)
        
        self.ot_prob_label = QLabel("")
        self.hole_prob_label = QLabel("")
        self.confidence_label = QLabel("")
        
        ot_layout.addWidget(QLabel("OT Probability:"), 0, 0)
        ot_layout.addWidget(self.ot_prob_label, 0, 1)
        ot_layout.addWidget(QLabel("Hole Probability:"), 1, 0)
        ot_layout.addWidget(self.hole_prob_label, 1, 1)
        ot_layout.addWidget(QLabel("Confidence:"), 2, 0)
        ot_layout.addWidget(self.confidence_label, 2, 1)
        
        content_layout.addWidget(ot_group)
        
        # Risk & Recommendation
        rec_group = QGroupBox("Risk Assessment")
        rec_layout = QGridLayout(rec_group)
        
        self.risk_label = QLabel("")
        self.rec_label = QLabel("")
        
        rec_layout.addWidget(QLabel("Risk Level:"), 0, 0)
        rec_layout.addWidget(self.risk_label, 0, 1)
        rec_layout.addWidget(QLabel("Recommendation:"), 1, 0)
        rec_layout.addWidget(self.rec_label, 1, 1)
        
        content_layout.addWidget(rec_group)
        
        # Stakes
        stake_group = QGroupBox("Suggested Stakes")
        stake_layout = QGridLayout(stake_group)
        
        self.stake_strong_label = QLabel("")
        self.stake_weak_label = QLabel("")
        self.total_stake_label = QLabel("")
        self.profit_label = QLabel("")
        
        stake_layout.addWidget(QLabel("Stake on Strong:"), 0, 0)
        stake_layout.addWidget(self.stake_strong_label, 0, 1)
        stake_layout.addWidget(QLabel("Stake on Weak:"), 1, 0)
        stake_layout.addWidget(self.stake_weak_label, 1, 1)
        stake_layout.addWidget(QLabel("Total Stake:"), 2, 0)
        stake_layout.addWidget(self.total_stake_label, 2, 1)
        stake_layout.addWidget(QLabel("Potential Profit:"), 3, 0)
        stake_layout.addWidget(self.profit_label, 3, 1)
        
        content_layout.addWidget(stake_group)
        
        # Reasoning
        reasoning_group = QGroupBox("Analysis Reasoning")
        reasoning_layout = QVBoxLayout(reasoning_group)
        
        self.reasoning_text = QTextEdit()
        self.reasoning_text.setReadOnly(True)
        self.reasoning_text.setMaximumHeight(150)
        reasoning_layout.addWidget(self.reasoning_text)
        
        content_layout.addWidget(reasoning_group)
        
        content_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
    
    def set_analysis(self, analysis: MatchAnalysis):
        """Display the given analysis."""
        self.current_analysis = analysis
        
        # Header
        self.header_label.setText(f"{analysis.team_strong} vs {analysis.team_weak}")
        
        # Teams
        self.home_team_label.setText(analysis.team_strong)
        self.away_team_label.setText(analysis.team_weak)
        self.time_label.setText(analysis.commence_time or "N/A")
        
        # Odds
        self.strong_odds_label.setText(f"{analysis.odds_strong:.2f}")
        self.weak_odds_label.setText(f"{analysis.odds_weak_reg:.2f}")
        self.strong_book_label.setText(analysis.bookmaker_strong)
        self.weak_book_label.setText(analysis.bookmaker_weak)
        
        # Arbitrage
        self.roi_label.setText(f"{analysis.arb_roi:.2%}")
        self.roi_label.setStyleSheet("color: #2ecc71; font-weight: bold;")
        self.arb_pct_label.setText(f"{analysis.arb_percentage:.2%}")
        
        ev_color = "#2ecc71" if analysis.expected_value > 0 else "#e74c3c"
        self.ev_label.setText(f"{analysis.expected_value:.4f}")
        self.ev_label.setStyleSheet(f"color: {ev_color}; font-weight: bold;")
        
        # OT
        self.ot_prob_label.setText(f"{analysis.ot_probability:.1%}")
        
        hole_color = self._get_hole_color(analysis.hole_probability)
        self.hole_prob_label.setText(f"{analysis.hole_probability:.2%}")
        self.hole_prob_label.setStyleSheet(f"color: {hole_color}; font-weight: bold;")
        
        self.confidence_label.setText(f"{analysis.ot_confidence:.1%}")
        
        # Risk
        risk_color = self._get_risk_color(analysis.risk_level)
        self.risk_label.setText(analysis.risk_level.value.upper())
        self.risk_label.setStyleSheet(f"color: {risk_color}; font-weight: bold;")
        
        rec_color = self._get_rec_color(analysis.recommendation)
        self.rec_label.setText(analysis.recommendation.value.upper())
        self.rec_label.setStyleSheet(f"color: {rec_color}; font-weight: bold; font-size: 14px;")
        
        # Stakes
        self.stake_strong_label.setText(f"${analysis.stake_strong:.2f}")
        self.stake_weak_label.setText(f"${analysis.stake_weak:.2f}")
        self.total_stake_label.setText(f"${analysis.total_stake:.2f}")
        self.profit_label.setText(f"${analysis.potential_profit:.2f}")
        self.profit_label.setStyleSheet("color: #2ecc71; font-weight: bold;")
        
        # Reasoning
        reasoning_html = "<ul>"
        for reason in analysis.reasoning:
            reasoning_html += f"<li>{reason}</li>"
        reasoning_html += "</ul>"
        self.reasoning_text.setHtml(reasoning_html)
    
    def _get_hole_color(self, hole_prob: float) -> str:
        if hole_prob <= 0.03:
            return "#2ecc71"
        elif hole_prob <= 0.04:
            return "#f39c12"
        elif hole_prob <= 0.05:
            return "#e67e22"
        else:
            return "#e74c3c"
    
    def _get_risk_color(self, risk: RiskLevel) -> str:
        colors = {
            RiskLevel.LOW: "#2ecc71",
            RiskLevel.MEDIUM: "#f39c12",
            RiskLevel.HIGH: "#e74c3c",
            RiskLevel.EXTREME: "#9b59b6"
        }
        return colors.get(risk, "white")
    
    def _get_rec_color(self, rec: Recommendation) -> str:
        colors = {
            Recommendation.BET: "#2ecc71",
            Recommendation.CAUTION: "#f39c12",
            Recommendation.SKIP: "#e74c3c"
        }
        return colors.get(rec, "white")
    
    def clear(self):
        """Clear the display."""
        self.current_analysis = None
        self.header_label.setText("Select a match to view details")
        for label in [self.home_team_label, self.away_team_label, self.time_label,
                      self.strong_odds_label, self.weak_odds_label, 
                      self.strong_book_label, self.weak_book_label,
                      self.roi_label, self.arb_pct_label, self.ev_label,
                      self.ot_prob_label, self.hole_prob_label, self.confidence_label,
                      self.risk_label, self.rec_label,
                      self.stake_strong_label, self.stake_weak_label,
                      self.total_stake_label, self.profit_label]:
            label.setText("")
            label.setStyleSheet("")
        self.reasoning_text.clear()
