"""Modern components for Eden Analytics Pro v2.4.0."""

from gui.components.modern_widgets import (
    ModernButton, ModernCard, StatCard, ModernProgressBar,
    ModernSwitch, ModernInput, ToastNotification, NotificationManager,
    show_notification
)

from gui.components.charts import (
    PlotlyChart, BankrollChart, ROIChart, WinRateChart,
    ModelPerformanceChart, ArbitrageHeatmap, ProfitDistributionChart,
    GaugeChart, InteractiveROIChart, AccuracyChart, 
    FeatureImportanceChart, LiveOddsChart, PLOTLY_AVAILABLE
)

# Premium components with improved spacing
from gui.components.premium_components import (
    PremiumButton, PremiumStatsCard, PremiumCard,
    PremiumSectionHeader, PremiumInfoBadge, PremiumDivider,
    PremiumLoadingSpinner
)

__all__ = [
    # Modern widgets
    'ModernButton', 'ModernCard', 'StatCard', 'ModernProgressBar',
    'ModernSwitch', 'ModernInput', 'ToastNotification', 'NotificationManager',
    'show_notification',
    # Charts
    'PlotlyChart', 'BankrollChart', 'ROIChart', 'WinRateChart',
    'ModelPerformanceChart', 'ArbitrageHeatmap', 'ProfitDistributionChart',
    'GaugeChart', 'InteractiveROIChart', 'AccuracyChart',
    'FeatureImportanceChart', 'LiveOddsChart', 'PLOTLY_AVAILABLE',
    # Premium components
    'PremiumButton', 'PremiumStatsCard', 'PremiumCard',
    'PremiumSectionHeader', 'PremiumInfoBadge', 'PremiumDivider',
    'PremiumLoadingSpinner'
]
