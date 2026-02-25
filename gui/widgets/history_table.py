"""History Table Widget for Eden MVP GUI."""

from typing import List, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QHeaderView, QAbstractItemView,
    QFrame, QDateEdit, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QBrush

import csv
from pathlib import Path
from datetime import datetime


class HistoryTableWidget(QWidget):
    """Table widget for displaying betting history."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.history: List[Dict] = []
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Filter bar
        filter_frame = QFrame()
        filter_layout = QHBoxLayout(filter_frame)
        
        filter_layout.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Won", "Lost", "Pending"])
        self.status_filter.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.status_filter)
        
        filter_layout.addWidget(QLabel("From:"))
        self.from_date = QDateEdit()
        self.from_date.setDate(QDate.currentDate().addMonths(-3))
        self.from_date.setCalendarPopup(True)
        self.from_date.dateChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.from_date)
        
        filter_layout.addWidget(QLabel("To:"))
        self.to_date = QDateEdit()
        self.to_date.setDate(QDate.currentDate())
        self.to_date.setCalendarPopup(True)
        self.to_date.dateChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.to_date)
        
        filter_layout.addStretch()
        
        self.export_btn = QPushButton("Export CSV")
        self.export_btn.clicked.connect(self._export_csv)
        filter_layout.addWidget(self.export_btn)
        
        layout.addWidget(filter_frame)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Date", "Match", "Strategy", "Stake", "Status", "P/L", "Bankroll"
        ])
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.table)
        
        # Summary
        summary_frame = QFrame()
        summary_layout = QHBoxLayout(summary_frame)
        
        self.total_label = QLabel("Total: 0 bets")
        self.pnl_label = QLabel("P/L: $0.00")
        self.winrate_label = QLabel("Win Rate: 0%")
        
        summary_layout.addWidget(self.total_label)
        summary_layout.addWidget(self.pnl_label)
        summary_layout.addWidget(self.winrate_label)
        summary_layout.addStretch()
        
        layout.addWidget(summary_frame)
    
    def set_data(self, history: List[Dict]):
        """Set the betting history to display."""
        self.history = history
        self._apply_filters()
    
    def _apply_filters(self, _=None):
        """Apply current filters and refresh table."""
        filtered = self.history[:]
        
        # Status filter
        status_filter = self.status_filter.currentText().lower()
        if status_filter != "all":
            filtered = [h for h in filtered if h.get('status', '').lower() == status_filter]
        
        # Date filter
        from_date = self.from_date.date().toPyDate()
        to_date = self.to_date.date().toPyDate()
        
        def parse_date(d):
            try:
                return datetime.strptime(d[:10], "%Y-%m-%d").date()
            except:
                return from_date
        
        filtered = [
            h for h in filtered 
            if from_date <= parse_date(h.get('created_at', '')) <= to_date
        ]
        
        self._populate_table(filtered)
        self._update_summary(filtered)
    
    def _populate_table(self, history: List[Dict]):
        """Populate the table with history."""
        self.table.setRowCount(len(history))
        
        for row, h in enumerate(history):
            # Date
            date_str = h.get('created_at', '')[:10]
            self.table.setItem(row, 0, QTableWidgetItem(date_str))
            
            # Match
            match = f"{h.get('team_strong', 'N/A')} vs {h.get('team_weak', 'N/A')}"
            self.table.setItem(row, 1, QTableWidgetItem(match))
            
            # Strategy
            self.table.setItem(row, 2, QTableWidgetItem(h.get('strategy', 'N/A')))
            
            # Stake
            stake = h.get('total_stake', 0)
            stake_item = QTableWidgetItem(f"${stake:.2f}")
            stake_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 3, stake_item)
            
            # Status
            status = h.get('status', 'pending')
            status_item = QTableWidgetItem(status.upper())
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            if status == 'won':
                status_item.setForeground(QBrush(QColor("#2ecc71")))
            elif status == 'lost':
                status_item.setForeground(QBrush(QColor("#e74c3c")))
            else:
                status_item.setForeground(QBrush(QColor("#f39c12")))
            
            self.table.setItem(row, 4, status_item)
            
            # P/L
            pnl = h.get('profit_loss', 0) or 0
            pnl_item = QTableWidgetItem(f"${pnl:+.2f}")
            pnl_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if pnl > 0:
                pnl_item.setForeground(QBrush(QColor("#2ecc71")))
            elif pnl < 0:
                pnl_item.setForeground(QBrush(QColor("#e74c3c")))
            self.table.setItem(row, 5, pnl_item)
            
            # Bankroll
            bankroll = h.get('bankroll_after', h.get('final_bankroll', 0)) or 0
            bankroll_item = QTableWidgetItem(f"${bankroll:.2f}")
            bankroll_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 6, bankroll_item)
    
    def _update_summary(self, history: List[Dict]):
        """Update summary labels."""
        total = len(history)
        won = sum(1 for h in history if h.get('status') == 'won')
        pnl = sum(h.get('profit_loss', 0) or 0 for h in history)
        
        self.total_label.setText(f"Total: {total} bets")
        
        pnl_color = "#2ecc71" if pnl >= 0 else "#e74c3c"
        self.pnl_label.setText(f"P/L: ${pnl:+.2f}")
        self.pnl_label.setStyleSheet(f"color: {pnl_color}; font-weight: bold;")
        
        completed = sum(1 for h in history if h.get('status') in ['won', 'lost'])
        winrate = (won / completed * 100) if completed > 0 else 0
        self.winrate_label.setText(f"Win Rate: {winrate:.1f}%")
    
    def _export_csv(self):
        """Export history to CSV file."""
        if not self.history:
            QMessageBox.warning(self, "Export", "No data to export.")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export to CSV", 
            f"betting_history_{datetime.now().strftime('%Y%m%d')}.csv",
            "CSV Files (*.csv)"
        )
        
        if filename:
            try:
                with open(filename, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=[
                        'created_at', 'team_strong', 'team_weak', 'strategy',
                        'total_stake', 'status', 'profit_loss'
                    ])
                    writer.writeheader()
                    writer.writerows(self.history)
                
                QMessageBox.information(self, "Export", f"Exported to {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))
