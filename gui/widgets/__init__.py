"""GUI Widgets for Eden MVP."""
from .arbitrage_table import ArbitrageTableWidget
from .match_details import MatchDetailsWidget
from .history_table import HistoryTableWidget
from .stats_dashboard import StatsDashboardWidget
from .backtest_panel import BacktestPanelWidget
from .settings_panel import SettingsPanelWidget
from .bankroll_panel import BankrollPanelWidget

__all__ = [
    'ArbitrageTableWidget',
    'MatchDetailsWidget', 
    'HistoryTableWidget',
    'StatsDashboardWidget',
    'BacktestPanelWidget',
    'SettingsPanelWidget',
    'BankrollPanelWidget'
]
