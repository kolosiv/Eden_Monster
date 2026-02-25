"""Arbitrage Table Widget for Eden MVP GUI."""

from typing import List, Optional, Callable
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QHeaderView, QAbstractItemView,
    QFrame, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QFont

from analysis.match_analyzer import MatchAnalysis, Recommendation, RiskLevel


class ArbitrageTableWidget(QWidget):
    """Table widget for displaying arbitrage opportunities."""
    
    # Signal emitted when a row is selected
    opportunity_selected = pyqtSignal(str)  # match_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.analyses: List[MatchAnalysis] = []
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Filter bar
        filter_frame = QFrame()
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(5, 5, 5, 5)
        
        filter_layout.addWidget(QLabel("Filter:"))
        
        self.rec_filter = QComboBox()
        self.rec_filter.addItems(["All", "BET", "CAUTION", "SKIP"])
        self.rec_filter.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.rec_filter)
        
        filter_layout.addWidget(QLabel("Risk:"))
        self.risk_filter = QComboBox()
        self.risk_filter.addItems(["All", "LOW", "MEDIUM", "HIGH", "EXTREME"])
        self.risk_filter.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.risk_filter)
        
        filter_layout.addWidget(QLabel("Min ROI %:"))
        self.min_roi_spin = QSpinBox()
        self.min_roi_spin.setRange(0, 20)
        self.min_roi_spin.setValue(2)
        self.min_roi_spin.valueChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.min_roi_spin)
        
        filter_layout.addStretch()
        
        self.count_label = QLabel("0 opportunities")
        filter_layout.addWidget(self.count_label)
        
        layout.addWidget(filter_frame)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Match", "ROI", "Hole %", "OT %", "EV", 
            "Risk", "Rec", "Stake", "Profit"
        ])
        
        # Configure table
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 9):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table.cellClicked.connect(self._on_cell_clicked)
        
        layout.addWidget(self.table)
    
    def set_data(self, analyses: List[MatchAnalysis]):
        """Set the arbitrage opportunities to display."""
        self.analyses = analyses
        self._apply_filters()
    
    def _apply_filters(self, _=None):
        """Apply current filters and refresh table."""
        filtered = self.analyses[:]
        
        # Recommendation filter
        rec_filter = self.rec_filter.currentText()
        if rec_filter != "All":
            filtered = [a for a in filtered if a.recommendation.value.upper() == rec_filter]
        
        # Risk filter
        risk_filter = self.risk_filter.currentText()
        if risk_filter != "All":
            filtered = [a for a in filtered if a.risk_level.value.upper() == risk_filter]
        
        # ROI filter
        min_roi = self.min_roi_spin.value() / 100
        filtered = [a for a in filtered if a.arb_roi >= min_roi]
        
        self._populate_table(filtered)
        self.count_label.setText(f"{len(filtered)} opportunities")
    
    def _populate_table(self, analyses: List[MatchAnalysis]):
        """Populate the table with analyses."""
        self.table.setRowCount(len(analyses))
        
        for row, analysis in enumerate(analyses):
            # Match
            match_item = QTableWidgetItem(f"{analysis.team_strong}\nvs {analysis.team_weak}")
            match_item.setData(Qt.ItemDataRole.UserRole, analysis.match_id)
            self.table.setItem(row, 0, match_item)
            
            # ROI
            roi_item = QTableWidgetItem(f"{analysis.arb_roi:.2%}")
            roi_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            roi_item.setForeground(QBrush(QColor("#2ecc71")))
            self.table.setItem(row, 1, roi_item)
            
            # Hole %
            hole_item = QTableWidgetItem(f"{analysis.hole_probability:.2%}")
            hole_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            hole_color = self._get_hole_color(analysis.hole_probability)
            hole_item.setForeground(QBrush(hole_color))
            self.table.setItem(row, 2, hole_item)
            
            # OT %
            ot_item = QTableWidgetItem(f"{analysis.ot_probability:.1%}")
            ot_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, ot_item)
            
            # EV
            ev_item = QTableWidgetItem(f"{analysis.expected_value:.4f}")
            ev_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            ev_color = QColor("#2ecc71") if analysis.expected_value > 0 else QColor("#e74c3c")
            ev_item.setForeground(QBrush(ev_color))
            self.table.setItem(row, 4, ev_item)
            
            # Risk
            risk_item = QTableWidgetItem(analysis.risk_level.value.upper())
            risk_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            risk_item.setForeground(QBrush(self._get_risk_color(analysis.risk_level)))
            self.table.setItem(row, 5, risk_item)
            
            # Recommendation
            rec_item = QTableWidgetItem(analysis.recommendation.value.upper())
            rec_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            rec_item.setForeground(QBrush(self._get_rec_color(analysis.recommendation)))
            font = rec_item.font()
            font.setBold(True)
            rec_item.setFont(font)
            self.table.setItem(row, 6, rec_item)
            
            # Stake
            stake_item = QTableWidgetItem(f"${analysis.total_stake:.2f}")
            stake_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 7, stake_item)
            
            # Potential Profit
            profit_item = QTableWidgetItem(f"${analysis.potential_profit:.2f}")
            profit_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            profit_item.setForeground(QBrush(QColor("#2ecc71")))
            self.table.setItem(row, 8, profit_item)
        
        self.table.resizeRowsToContents()
    
    def _get_hole_color(self, hole_prob: float) -> QColor:
        """Get color for hole probability."""
        if hole_prob <= 0.03:
            return QColor("#2ecc71")  # Green
        elif hole_prob <= 0.04:
            return QColor("#f39c12")  # Orange
        elif hole_prob <= 0.05:
            return QColor("#e67e22")  # Dark orange
        else:
            return QColor("#e74c3c")  # Red
    
    def _get_risk_color(self, risk: RiskLevel) -> QColor:
        """Get color for risk level."""
        colors = {
            RiskLevel.LOW: QColor("#2ecc71"),
            RiskLevel.MEDIUM: QColor("#f39c12"),
            RiskLevel.HIGH: QColor("#e74c3c"),
            RiskLevel.EXTREME: QColor("#9b59b6")
        }
        return colors.get(risk, QColor("white"))
    
    def _get_rec_color(self, rec: Recommendation) -> QColor:
        """Get color for recommendation."""
        colors = {
            Recommendation.BET: QColor("#2ecc71"),
            Recommendation.CAUTION: QColor("#f39c12"),
            Recommendation.SKIP: QColor("#e74c3c")
        }
        return colors.get(rec, QColor("white"))
    
    def _on_cell_clicked(self, row: int, col: int):
        """Handle cell click."""
        item = self.table.item(row, 0)
        if item:
            match_id = item.data(Qt.ItemDataRole.UserRole)
            self.opportunity_selected.emit(match_id)
