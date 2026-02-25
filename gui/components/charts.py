"""Interactive Charts using Plotly for Eden Analytics Pro."""

from typing import List, Dict, Optional, Any
import json
from datetime import datetime, timedelta

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl

from gui.themes.modern_theme import get_theme

# Check for plotly
try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


class PlotlyChart(QWidget):
    """Base class for Plotly charts embedded in PyQt6."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(300)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)
    
    def _get_theme_config(self) -> Dict:
        """Get Plotly theme configuration based on current theme."""
        theme = get_theme()
        p = theme.palette
        
        return {
            'paper_bgcolor': p.surface,
            'plot_bgcolor': p.surface,
            'font': {'color': p.text, 'family': 'Segoe UI, sans-serif'},
            'colorway': [p.primary, p.secondary, p.success, p.warning, p.error, p.accent],
            'xaxis': {
                'gridcolor': p.border,
                'linecolor': p.border,
                'tickfont': {'color': p.text_secondary}
            },
            'yaxis': {
                'gridcolor': p.border,
                'linecolor': p.border,
                'tickfont': {'color': p.text_secondary}
            }
        }
    
    def render_figure(self, fig: Any):
        """Render a Plotly figure to the web view."""
        if not PLOTLY_AVAILABLE:
            self._show_fallback("Plotly not installed")
            return
        
        # Apply theme
        theme_config = self._get_theme_config()
        fig.update_layout(**theme_config)
        
        # Convert to HTML
        html = fig.to_html(include_plotlyjs='cdn', full_html=True)
        self.web_view.setHtml(html)
    
    def _show_fallback(self, message: str):
        """Show fallback message when Plotly unavailable."""
        theme = get_theme()
        p = theme.palette
        html = f"""
        <html>
        <body style="background-color: {p.surface}; color: {p.text_secondary}; 
                     display: flex; align-items: center; justify-content: center; 
                     height: 100vh; font-family: 'Segoe UI', sans-serif;">
            <div style="text-align: center;">
                <p style="font-size: 48px;">📊</p>
                <p>{message}</p>
                <p style="font-size: 12px;">Install plotly: pip install plotly</p>
            </div>
        </body>
        </html>
        """
        self.web_view.setHtml(html)


class BankrollChart(PlotlyChart):
    """Bankroll growth chart."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def update_data(self, data: List[Dict]):
        """Update chart with bankroll history.
        
        data: List of {'date': datetime, 'bankroll': float, 'profit': float}
        """
        if not PLOTLY_AVAILABLE or not data:
            self._show_fallback("No data available")
            return
        
        theme = get_theme()
        p = theme.palette
        
        dates = [d.get('date', datetime.now()) for d in data]
        bankrolls = [d.get('bankroll', 0) for d in data]
        
        fig = go.Figure()
        
        # Main line
        fig.add_trace(go.Scatter(
            x=dates,
            y=bankrolls,
            mode='lines',
            name='Bankroll',
            line=dict(color=p.primary, width=3),
            fill='tozeroy',
            fillcolor=f'rgba(108, 99, 255, 0.1)'
        ))
        
        # Starting line
        if bankrolls:
            fig.add_hline(y=bankrolls[0], line_dash="dash", 
                         line_color=p.text_muted, 
                         annotation_text="Initial")
        
        fig.update_layout(
            title='Bankroll Growth',
            xaxis_title='Date',
            yaxis_title='Bankroll ($)',
            hovermode='x unified',
            showlegend=False,
            margin=dict(l=50, r=30, t=50, b=50)
        )
        
        self.render_figure(fig)


class ROIChart(PlotlyChart):
    """ROI distribution chart."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def update_data(self, data: List[Dict]):
        """Update chart with ROI data.
        
        data: List of {'period': str, 'roi': float}
        """
        if not PLOTLY_AVAILABLE or not data:
            self._show_fallback("No data available")
            return
        
        theme = get_theme()
        p = theme.palette
        
        periods = [d.get('period', '') for d in data]
        rois = [d.get('roi', 0) for d in data]
        
        colors = [p.success if r >= 0 else p.error for r in rois]
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=periods,
            y=rois,
            marker_color=colors,
            text=[f"{r:.1f}%" for r in rois],
            textposition='outside'
        ))
        
        fig.add_hline(y=0, line_color=p.text_muted)
        
        fig.update_layout(
            title='ROI by Period',
            xaxis_title='Period',
            yaxis_title='ROI (%)',
            showlegend=False,
            margin=dict(l=50, r=30, t=50, b=50)
        )
        
        self.render_figure(fig)


class WinRateChart(PlotlyChart):
    """Win rate over time chart."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def update_data(self, data: List[Dict]):
        """Update chart with win rate data.
        
        data: List of {'date': datetime, 'win_rate': float, 'hole_rate': float}
        """
        if not PLOTLY_AVAILABLE or not data:
            self._show_fallback("No data available")
            return
        
        theme = get_theme()
        p = theme.palette
        
        dates = [d.get('date', datetime.now()) for d in data]
        win_rates = [d.get('win_rate', 0) * 100 for d in data]
        hole_rates = [d.get('hole_rate', 0) * 100 for d in data]
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=dates, y=win_rates,
            mode='lines+markers',
            name='Win Rate',
            line=dict(color=p.success, width=2),
            fill='tozeroy',
            fillcolor=f'rgba(0, 230, 118, 0.1)'
        ))
        
        fig.add_trace(go.Scatter(
            x=dates, y=hole_rates,
            mode='lines+markers',
            name='Hole Rate',
            line=dict(color=p.error, width=2)
        ))
        
        fig.update_layout(
            title='Performance Over Time',
            xaxis_title='Date',
            yaxis_title='Rate (%)',
            hovermode='x unified',
            legend=dict(orientation='h', yanchor='bottom', y=1.02),
            margin=dict(l=50, r=30, t=80, b=50)
        )
        
        self.render_figure(fig)


class ModelPerformanceChart(PlotlyChart):
    """ML Model performance comparison chart."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def update_data(self, data: List[Dict]):
        """Update chart with model metrics.
        
        data: List of {'model': str, 'accuracy': float, 'precision': float, 'recall': float}
        """
        if not PLOTLY_AVAILABLE or not data:
            self._show_fallback("No data available")
            return
        
        theme = get_theme()
        p = theme.palette
        
        models = [d.get('model', 'Unknown') for d in data]
        metrics = ['Accuracy', 'Precision', 'Recall', 'F1']
        
        fig = go.Figure()
        
        for i, metric in enumerate(metrics):
            values = [d.get(metric.lower(), 0) * 100 for d in data]
            fig.add_trace(go.Bar(
                name=metric,
                x=models,
                y=values,
                text=[f"{v:.1f}%" for v in values],
                textposition='auto'
            ))
        
        fig.update_layout(
            title='Model Performance Comparison',
            xaxis_title='Model',
            yaxis_title='Score (%)',
            barmode='group',
            legend=dict(orientation='h', yanchor='bottom', y=1.02),
            margin=dict(l=50, r=30, t=80, b=50)
        )
        
        self.render_figure(fig)


class ArbitrageHeatmap(PlotlyChart):
    """Arbitrage opportunities heatmap by day/hour."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def update_data(self, data: List[Dict]):
        """Update chart with arbitrage timing data.
        
        data: List of {'day': int (0-6), 'hour': int (0-23), 'count': int}
        """
        if not PLOTLY_AVAILABLE or not data:
            self._show_fallback("No data available")
            return
        
        theme = get_theme()
        p = theme.palette
        
        # Create 7x24 matrix
        import numpy as np
        matrix = np.zeros((7, 24))
        
        for d in data:
            day = d.get('day', 0)
            hour = d.get('hour', 0)
            count = d.get('count', 0)
            if 0 <= day < 7 and 0 <= hour < 24:
                matrix[day][hour] = count
        
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        hours = [f"{h:02d}:00" for h in range(24)]
        
        fig = go.Figure(data=go.Heatmap(
            z=matrix,
            x=hours,
            y=days,
            colorscale=[[0, p.surface], [0.5, p.secondary], [1, p.primary]],
            hoverongaps=False
        ))
        
        fig.update_layout(
            title='Arbitrage Opportunities by Time',
            xaxis_title='Hour',
            yaxis_title='Day',
            margin=dict(l=50, r=30, t=50, b=50)
        )
        
        self.render_figure(fig)


class ProfitDistributionChart(PlotlyChart):
    """Profit/Loss distribution histogram."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def update_data(self, profits: List[float]):
        """Update chart with profit values."""
        if not PLOTLY_AVAILABLE or not profits:
            self._show_fallback("No data available")
            return
        
        theme = get_theme()
        p = theme.palette
        
        fig = go.Figure()
        
        fig.add_trace(go.Histogram(
            x=profits,
            nbinsx=30,
            marker_color=p.primary,
            opacity=0.8
        ))
        
        fig.add_vline(x=0, line_dash="dash", line_color=p.text_muted)
        
        # Add mean line
        import statistics
        mean_profit = statistics.mean(profits)
        fig.add_vline(x=mean_profit, line_dash="dot", 
                     line_color=p.success if mean_profit >= 0 else p.error,
                     annotation_text=f"Mean: ${mean_profit:.2f}")
        
        fig.update_layout(
            title='Profit/Loss Distribution',
            xaxis_title='Profit ($)',
            yaxis_title='Frequency',
            showlegend=False,
            margin=dict(l=50, r=30, t=50, b=50)
        )
        
        self.render_figure(fig)


class GaugeChart(PlotlyChart):
    """Gauge chart for displaying metrics."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(200)
    
    def update_data(self, value: float, title: str = "Metric", 
                   min_val: float = 0, max_val: float = 100,
                   thresholds: List[float] = None):
        """Update gauge with value.
        
        thresholds: [low, medium, high] boundaries
        """
        if not PLOTLY_AVAILABLE:
            self._show_fallback("No data available")
            return
        
        theme = get_theme()
        p = theme.palette
        
        if thresholds is None:
            thresholds = [max_val * 0.33, max_val * 0.66, max_val]
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=value,
            title={'text': title, 'font': {'size': 16}},
            gauge={
                'axis': {'range': [min_val, max_val]},
                'bar': {'color': p.primary},
                'bgcolor': p.surface_light,
                'borderwidth': 0,
                'steps': [
                    {'range': [min_val, thresholds[0]], 'color': p.error},
                    {'range': [thresholds[0], thresholds[1]], 'color': p.warning},
                    {'range': [thresholds[1], max_val], 'color': p.success}
                ],
                'threshold': {
                    'line': {'color': p.text, 'width': 2},
                    'thickness': 0.75,
                    'value': value
                }
            }
        ))
        
        fig.update_layout(
            margin=dict(l=30, r=30, t=60, b=30),
            height=200
        )
        
        self.render_figure(fig)


class InteractiveROIChart(PlotlyChart):
    """Interactive ROI dynamics chart with smooth animations."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(400)
    
    def create_roi_chart(self, data: Dict):
        """Create ROI over time chart.
        
        data: {'dates': list, 'roi': list}
        """
        if not PLOTLY_AVAILABLE or not data:
            self._show_fallback("Данные недоступны")
            return
        
        theme = get_theme()
        p = theme.palette
        
        dates = data.get('dates', [])
        roi_values = data.get('roi', [])
        
        fig = go.Figure()
        
        # Main ROI line with gradient fill
        fig.add_trace(go.Scatter(
            x=dates,
            y=roi_values,
            mode='lines+markers',
            name='ROI',
            line=dict(color='#FFD700', width=3, shape='spline'),
            marker=dict(size=10, color='#00D9FF', 
                       line=dict(width=2, color='#FFFFFF')),
            fill='tozeroy',
            fillcolor='rgba(255, 215, 0, 0.15)',
            hovertemplate='<b>%{x}</b><br>ROI: %{y:.2f}%<extra></extra>'
        ))
        
        # Average line
        if roi_values:
            avg_roi = sum(roi_values) / len(roi_values)
            fig.add_hline(
                y=avg_roi,
                line_dash="dot",
                line_color='rgba(0, 217, 255, 0.5)',
                annotation_text=f"Среднее: {avg_roi:.2f}%",
                annotation_position="top right"
            )
        
        fig.update_layout(
            title=dict(
                text='📈 ROI Динамика',
                font=dict(size=22, color='#FFD700'),
                x=0.02
            ),
            xaxis_title='Дата',
            yaxis_title='ROI (%)',
            hovermode='x unified',
            showlegend=False,
            margin=dict(l=60, r=40, t=80, b=60),
            xaxis=dict(
                showgrid=True,
                gridcolor='rgba(255, 255, 255, 0.05)',
                tickfont=dict(size=12)
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(255, 255, 255, 0.05)',
                tickfont=dict(size=12),
                ticksuffix='%'
            )
        )
        
        self.render_figure(fig)


class AccuracyChart(PlotlyChart):
    """Model accuracy chart with multiple visualizations."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(500)
    
    def create_accuracy_chart(self, data: Dict):
        """Create model accuracy visualization.
        
        data: {
            'models': list of model names,
            'accuracy': list of accuracy values,
            'confusion_matrix': 2D list [[TN, FP], [FN, TP]]
        }
        """
        if not PLOTLY_AVAILABLE or not data:
            self._show_fallback("Данные недоступны")
            return
        
        theme = get_theme()
        p = theme.palette
        
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=(
                '<b>Точность по моделям</b>',
                '<b>Матрица ошибок</b>'
            ),
            specs=[[{'type': 'bar'}, {'type': 'heatmap'}]],
            horizontal_spacing=0.12
        )
        
        models = data.get('models', ['RandomForest', 'XGBoost', 'LightGBM', 'Neural Net'])
        accuracy = data.get('accuracy', [86.04, 84.5, 85.2, 83.8])
        
        # Bar chart with gradient colors
        colors = ['#FFD700', '#00D9FF', '#00FF88', '#FF6B6B']
        
        fig.add_trace(
            go.Bar(
                x=models,
                y=accuracy,
                marker=dict(
                    color=colors[:len(models)],
                    line=dict(width=2, color='rgba(255, 255, 255, 0.3)')
                ),
                text=[f'{x:.2f}%' for x in accuracy],
                textposition='outside',
                textfont=dict(size=14, color='#FFFFFF'),
                hovertemplate='<b>%{x}</b><br>Точность: %{y:.2f}%<extra></extra>'
            ),
            row=1, col=1
        )
        
        # Confusion matrix
        cm = data.get('confusion_matrix', [[850, 150], [140, 860]])
        
        fig.add_trace(
            go.Heatmap(
                z=cm,
                x=['Нет OT', 'OT'],
                y=['Нет OT', 'OT'],
                colorscale=[
                    [0, 'rgba(0, 0, 0, 0.3)'],
                    [0.5, '#00D9FF'],
                    [1, '#FFD700']
                ],
                text=[[str(v) for v in row] for row in cm],
                texttemplate='%{text}',
                textfont={"size": 18, "color": "#FFFFFF"},
                showscale=False,
                hovertemplate='Факт: %{y}<br>Предсказание: %{x}<br>Кол-во: %{z}<extra></extra>'
            ),
            row=1, col=2
        )
        
        # Update layout
        fig.update_layout(
            showlegend=False,
            height=450,
            margin=dict(l=60, r=40, t=80, b=60),
            font=dict(family='Segoe UI', color='#FFFFFF')
        )
        
        # Update axes for bar chart
        fig.update_xaxes(
            tickfont=dict(size=12),
            row=1, col=1
        )
        fig.update_yaxes(
            tickfont=dict(size=12),
            title_text='Точность (%)',
            range=[75, 100],
            row=1, col=1
        )
        
        # Update axes for heatmap
        fig.update_xaxes(
            title_text='Предсказание',
            tickfont=dict(size=12),
            row=1, col=2
        )
        fig.update_yaxes(
            title_text='Факт',
            tickfont=dict(size=12),
            row=1, col=2
        )
        
        self.render_figure(fig)


class FeatureImportanceChart(PlotlyChart):
    """Feature importance visualization chart."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(400)
    
    def update_data(self, features: List[str], importance: List[float]):
        """Update chart with feature importance data."""
        if not PLOTLY_AVAILABLE or not features:
            self._show_fallback("Данные недоступны")
            return
        
        theme = get_theme()
        p = theme.palette
        
        # Sort by importance
        sorted_pairs = sorted(zip(importance, features), reverse=True)[:15]
        importance_sorted, features_sorted = zip(*sorted_pairs)
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=list(importance_sorted),
            y=list(features_sorted),
            orientation='h',
            marker=dict(
                color=list(importance_sorted),
                colorscale=[
                    [0, 'rgba(0, 217, 255, 0.6)'],
                    [0.5, '#FFD700'],
                    [1, '#FF6B6B']
                ],
                line=dict(width=1, color='rgba(255, 255, 255, 0.2)')
            ),
            text=[f'{v:.3f}' for v in importance_sorted],
            textposition='outside',
            textfont=dict(size=11, color='#FFFFFF'),
            hovertemplate='<b>%{y}</b><br>Важность: %{x:.4f}<extra></extra>'
        ))
        
        fig.update_layout(
            title=dict(
                text='🎯 Важность признаков',
                font=dict(size=20, color='#FFD700'),
                x=0.02
            ),
            xaxis_title='Важность',
            yaxis_title='',
            showlegend=False,
            margin=dict(l=200, r=60, t=80, b=60),
            height=450
        )
        
        fig.update_yaxes(tickfont=dict(size=11))
        
        self.render_figure(fig)


class LiveOddsChart(PlotlyChart):
    """Real-time odds movement chart."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(350)
    
    def update_data(self, data: Dict):
        """Update with odds movement data.
        
        data: {
            'times': list of timestamps,
            'home_odds': list,
            'away_odds': list,
            'home_team': str,
            'away_team': str
        }
        """
        if not PLOTLY_AVAILABLE or not data:
            self._show_fallback("Данные недоступны")
            return
        
        theme = get_theme()
        p = theme.palette
        
        times = data.get('times', [])
        home_odds = data.get('home_odds', [])
        away_odds = data.get('away_odds', [])
        home_team = data.get('home_team', 'Home')
        away_team = data.get('away_team', 'Away')
        
        fig = go.Figure()
        
        # Home team odds
        fig.add_trace(go.Scatter(
            x=times,
            y=home_odds,
            mode='lines+markers',
            name=home_team,
            line=dict(color='#FFD700', width=2),
            marker=dict(size=6),
            hovertemplate=f'<b>{home_team}</b><br>Коэф: %{{y:.2f}}<extra></extra>'
        ))
        
        # Away team odds
        fig.add_trace(go.Scatter(
            x=times,
            y=away_odds,
            mode='lines+markers',
            name=away_team,
            line=dict(color='#00D9FF', width=2),
            marker=dict(size=6),
            hovertemplate=f'<b>{away_team}</b><br>Коэф: %{{y:.2f}}<extra></extra>'
        ))
        
        fig.update_layout(
            title=dict(
                text='📊 Движение коэффициентов',
                font=dict(size=18, color='#FFD700'),
                x=0.02
            ),
            xaxis_title='Время',
            yaxis_title='Коэффициент',
            hovermode='x unified',
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1
            ),
            margin=dict(l=60, r=40, t=80, b=60)
        )
        
        self.render_figure(fig)


__all__ = [
    'PlotlyChart', 'BankrollChart', 'ROIChart', 'WinRateChart',
    'ModelPerformanceChart', 'ArbitrageHeatmap', 'ProfitDistributionChart',
    'GaugeChart', 'InteractiveROIChart', 'AccuracyChart', 
    'FeatureImportanceChart', 'LiveOddsChart', 'PLOTLY_AVAILABLE'
]
