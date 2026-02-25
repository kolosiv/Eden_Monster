"""Statistics Dashboard Widget for Eden MVP GUI."""

from typing import Dict, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QGroupBox, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# Try to import matplotlib
try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class MetricCard(QFrame):
    """Card widget for displaying a metric."""
    
    def __init__(self, title: str, value: str = "0", color: str = "#00d9ff", parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255,255,255,0.05);
                border-radius: 10px;
                border: 1px solid rgba(255,255,255,0.1);
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(title_label)
        
        self.value_label = QLabel(value)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: bold;")
        layout.addWidget(self.value_label)
        
        self.setMinimumSize(150, 80)
    
    def set_value(self, value: str, color: str = None):
        """Update the displayed value."""
        self.value_label.setText(value)
        if color:
            self.value_label.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: bold;")


class StatsDashboardWidget(QWidget):
    """Dashboard widget for displaying statistics."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.stats: Dict = {}
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI components."""
        main_layout = QVBoxLayout(self)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content = QWidget()
        layout = QVBoxLayout(content)
        
        # Title
        title = QLabel("Statistics Dashboard")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #00d9ff;")
        layout.addWidget(title)
        
        # Metric cards grid
        cards_widget = QWidget()
        cards_layout = QGridLayout(cards_widget)
        cards_layout.setSpacing(15)
        
        self.cards = {}
        metrics = [
            ("Total Bets", "total_bets", "#00d9ff"),
            ("Won", "won", "#2ecc71"),
            ("Lost", "lost", "#e74c3c"),
            ("Pending", "pending", "#f39c12"),
            ("Win Rate", "win_rate", "#00d9ff"),
            ("Hole Rate", "hole_rate", "#e74c3c"),
            ("Total Staked", "total_staked", "#00d9ff"),
            ("Total P/L", "total_profit_loss", "#2ecc71"),
            ("ROI", "roi", "#00d9ff"),
            ("Best Result", "best_result", "#2ecc71"),
            ("Worst Result", "worst_result", "#e74c3c"),
            ("Avg per Bet", "avg_profit_per_bet", "#00d9ff")
        ]
        
        for i, (title, key, color) in enumerate(metrics):
            card = MetricCard(title, "--", color)
            self.cards[key] = card
            cards_layout.addWidget(card, i // 4, i % 4)
        
        layout.addWidget(cards_widget)
        
        # Charts section
        if MATPLOTLIB_AVAILABLE:
            charts_group = QGroupBox("Performance Charts")
            charts_layout = QHBoxLayout(charts_group)
            
            # Win/Loss pie chart
            self.pie_figure = Figure(figsize=(4, 3), facecolor='#1a1a2e')
            self.pie_canvas = FigureCanvas(self.pie_figure)
            charts_layout.addWidget(self.pie_canvas)
            
            # ROI bar chart (placeholder)
            self.bar_figure = Figure(figsize=(4, 3), facecolor='#1a1a2e')
            self.bar_canvas = FigureCanvas(self.bar_figure)
            charts_layout.addWidget(self.bar_canvas)
            
            layout.addWidget(charts_group)
        
        # Strategy performance table
        strat_group = QGroupBox("Strategy Performance")
        strat_layout = QVBoxLayout(strat_group)
        
        self.strategy_labels = {}
        strategies = ["FIXED", "KELLY", "ADAPTIVE"]
        
        strat_header = QHBoxLayout()
        for header in ["Strategy", "Bets", "Win Rate", "P/L"]:
            lbl = QLabel(header)
            lbl.setStyleSheet("font-weight: bold; color: #00d9ff;")
            strat_header.addWidget(lbl)
        strat_layout.addLayout(strat_header)
        
        for strat in strategies:
            row = QHBoxLayout()
            name_lbl = QLabel(strat)
            bets_lbl = QLabel("--")
            wr_lbl = QLabel("--")
            pnl_lbl = QLabel("--")
            
            self.strategy_labels[strat] = {
                'bets': bets_lbl,
                'win_rate': wr_lbl,
                'pnl': pnl_lbl
            }
            
            row.addWidget(name_lbl)
            row.addWidget(bets_lbl)
            row.addWidget(wr_lbl)
            row.addWidget(pnl_lbl)
            strat_layout.addLayout(row)
        
        layout.addWidget(strat_group)
        
        layout.addStretch()
        
        scroll.setWidget(content)
        main_layout.addWidget(scroll)
    
    def set_stats(self, stats: Dict, strategy_perf: Dict = None):
        """Update the displayed statistics."""
        self.stats = stats
        
        # Update metric cards
        self.cards['total_bets'].set_value(str(stats.get('total_bets', 0)))
        self.cards['won'].set_value(str(stats.get('won', 0)), "#2ecc71")
        self.cards['lost'].set_value(str(stats.get('lost', 0)), "#e74c3c")
        self.cards['pending'].set_value(str(stats.get('pending', 0)), "#f39c12")
        
        win_rate = stats.get('win_rate', 0)
        self.cards['win_rate'].set_value(f"{win_rate:.1f}%", 
            "#2ecc71" if win_rate >= 50 else "#e74c3c")
        
        hole_rate = stats.get('hole_rate', 0)
        self.cards['hole_rate'].set_value(f"{hole_rate:.1f}%",
            "#2ecc71" if hole_rate <= 4 else "#e74c3c")
        
        total_staked = stats.get('total_staked', 0)
        self.cards['total_staked'].set_value(f"${total_staked:,.2f}")
        
        pnl = stats.get('total_profit_loss', 0)
        self.cards['total_profit_loss'].set_value(
            f"${pnl:+,.2f}", "#2ecc71" if pnl >= 0 else "#e74c3c")
        
        roi = stats.get('roi', 0)
        self.cards['roi'].set_value(f"{roi:+.2f}%",
            "#2ecc71" if roi >= 0 else "#e74c3c")
        
        best = stats.get('best_result', 0)
        self.cards['best_result'].set_value(f"${best:,.2f}", "#2ecc71")
        
        worst = stats.get('worst_result', 0)
        self.cards['worst_result'].set_value(f"${worst:,.2f}", "#e74c3c")
        
        avg = stats.get('avg_profit_per_bet', 0)
        self.cards['avg_profit_per_bet'].set_value(
            f"${avg:+.2f}", "#2ecc71" if avg >= 0 else "#e74c3c")
        
        # Update charts
        if MATPLOTLIB_AVAILABLE:
            self._update_pie_chart(stats)
            self._update_bar_chart(strategy_perf)
        
        # Update strategy performance
        if strategy_perf:
            for strat, data in strategy_perf.items():
                strat_upper = strat.upper()
                if strat_upper in self.strategy_labels:
                    labels = self.strategy_labels[strat_upper]
                    labels['bets'].setText(str(data.get('total', 0)))
                    labels['win_rate'].setText(f"{data.get('win_rate', 0):.1f}%")
                    
                    pnl = data.get('total_pnl', 0)
                    labels['pnl'].setText(f"${pnl:+.2f}")
                    labels['pnl'].setStyleSheet(
                        f"color: {'#2ecc71' if pnl >= 0 else '#e74c3c'};")
    
    def _update_pie_chart(self, stats: Dict):
        """Update the win/loss pie chart."""
        self.pie_figure.clear()
        ax = self.pie_figure.add_subplot(111)
        
        won = stats.get('won', 0)
        lost = stats.get('lost', 0)
        pending = stats.get('pending', 0)
        
        if won + lost + pending > 0:
            sizes = [won, lost, pending]
            labels = ['Won', 'Lost', 'Pending']
            colors = ['#2ecc71', '#e74c3c', '#f39c12']
            
            # Filter out zeros
            non_zero = [(s, l, c) for s, l, c in zip(sizes, labels, colors) if s > 0]
            if non_zero:
                sizes, labels, colors = zip(*non_zero)
                ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                       textprops={'color': 'white'})
        
        ax.set_title('Bet Outcomes', color='white')
        self.pie_canvas.draw()
    
    def _update_bar_chart(self, strategy_perf: Dict):
        """Update the strategy performance bar chart."""
        self.bar_figure.clear()
        ax = self.bar_figure.add_subplot(111)
        
        if strategy_perf:
            strategies = list(strategy_perf.keys())
            pnls = [strategy_perf[s].get('total_pnl', 0) for s in strategies]
            colors = ['#2ecc71' if p >= 0 else '#e74c3c' for p in pnls]
            
            ax.bar(strategies, pnls, color=colors)
            ax.axhline(y=0, color='white', linewidth=0.5)
            ax.set_ylabel('P/L ($)', color='white')
            ax.tick_params(colors='white')
            for spine in ax.spines.values():
                spine.set_color('white')
        
        ax.set_title('P/L by Strategy', color='white')
        self.bar_canvas.draw()
