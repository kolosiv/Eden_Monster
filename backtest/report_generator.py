"""Report Generator for Eden MVP Backtesting.

Generates HTML and PDF reports with charts.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import io
import base64

from backtest.backtester import BacktestResult, BacktestBet
from utils.logger import get_logger

logger = get_logger(__name__)

# Try importing matplotlib
try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger.warning("matplotlib not available. Install with: pip install matplotlib")


class ReportGenerator:
    """Generates backtest reports with charts."""
    
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_html_report(
        self,
        result: BacktestResult,
        filename: str = None
    ) -> str:
        """Generate HTML report with embedded charts.
        
        Args:
            result: Backtest result
            filename: Output filename (auto-generated if None)
            
        Returns:
            Path to generated report
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backtest_report_{timestamp}.html"
        
        # Generate charts
        equity_chart = self._generate_equity_chart(result) if MATPLOTLIB_AVAILABLE else ""
        monthly_chart = self._generate_monthly_chart(result) if MATPLOTLIB_AVAILABLE else ""
        distribution_chart = self._generate_distribution_chart(result) if MATPLOTLIB_AVAILABLE else ""
        hole_chart = self._generate_hole_analysis_chart(result) if MATPLOTLIB_AVAILABLE else ""
        
        # Generate HTML
        html = self._generate_html(
            result, equity_chart, monthly_chart, distribution_chart, hole_chart
        )
        
        # Save
        filepath = self.output_dir / filename
        with open(filepath, 'w') as f:
            f.write(html)
        
        logger.info(f"Report saved to {filepath}")
        return str(filepath)
    
    def _generate_equity_chart(self, result: BacktestResult) -> str:
        """Generate equity curve chart."""
        if not result.equity_curve:
            return ""
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        dates = [datetime.strptime(d, "%Y-%m-%d") for d, _ in result.equity_curve]
        values = [v for _, v in result.equity_curve]
        
        ax.plot(dates, values, 'b-', linewidth=2, label='Bankroll')
        ax.axhline(y=result.initial_bankroll, color='gray', linestyle='--', alpha=0.5, label='Initial')
        
        ax.fill_between(dates, result.initial_bankroll, values, 
                        where=[v >= result.initial_bankroll for v in values],
                        color='green', alpha=0.3)
        ax.fill_between(dates, result.initial_bankroll, values,
                        where=[v < result.initial_bankroll for v in values],
                        color='red', alpha=0.3)
        
        ax.set_title('Equity Curve', fontsize=14, fontweight='bold')
        ax.set_xlabel('Date')
        ax.set_ylabel('Bankroll ($)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        return self._fig_to_base64(fig)
    
    def _generate_monthly_chart(self, result: BacktestResult) -> str:
        """Generate monthly returns bar chart."""
        if not result.monthly_returns:
            return ""
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        months = list(result.monthly_returns.keys())
        returns = list(result.monthly_returns.values())
        
        colors = ['green' if r >= 0 else 'red' for r in returns]
        
        bars = ax.bar(months, returns, color=colors, alpha=0.7)
        
        ax.axhline(y=0, color='black', linewidth=0.5)
        ax.set_title('Monthly Returns', fontsize=14, fontweight='bold')
        ax.set_xlabel('Month')
        ax.set_ylabel('Profit/Loss ($)')
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        return self._fig_to_base64(fig)
    
    def _generate_distribution_chart(self, result: BacktestResult) -> str:
        """Generate profit/loss distribution histogram."""
        if not result.bets:
            return ""
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        profits = [b.profit_loss for b in result.bets]
        
        ax.hist(profits, bins=30, color='blue', alpha=0.7, edgecolor='black')
        ax.axvline(x=0, color='red', linestyle='--', linewidth=2)
        ax.axvline(x=sum(profits)/len(profits), color='green', linestyle='--', 
                   linewidth=2, label=f'Mean: ${sum(profits)/len(profits):.2f}')
        
        ax.set_title('Profit/Loss Distribution', fontsize=14, fontweight='bold')
        ax.set_xlabel('Profit/Loss ($)')
        ax.set_ylabel('Frequency')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        return self._fig_to_base64(fig)
    
    def _generate_hole_analysis_chart(self, result: BacktestResult) -> str:
        """Generate hole probability analysis chart."""
        if not result.bets:
            return ""
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Predicted vs Actual hole rates
        predicted_probs = [b.predicted_hole_prob for b in result.bets]
        actual_holes = [1 if b.actual_hole else 0 for b in result.bets]
        
        # Scatter plot
        colors = ['red' if h else 'green' for h in actual_holes]
        ax1.scatter(range(len(predicted_probs)), predicted_probs, c=colors, alpha=0.5, s=20)
        ax1.axhline(y=0.04, color='orange', linestyle='--', label='4% threshold')
        ax1.set_title('Predicted Hole Probability vs Actual', fontsize=12, fontweight='bold')
        ax1.set_xlabel('Bet Number')
        ax1.set_ylabel('Predicted Hole Probability')
        ax1.legend(['Threshold', 'Actual Hole', 'No Hole'])
        ax1.grid(True, alpha=0.3)
        
        # Pie chart of outcomes
        outcomes = {
            'Win (Strong)': sum(1 for b in result.bets if b.outcome.value == 'win_strong'),
            'Win (Weak Reg)': sum(1 for b in result.bets if b.outcome.value == 'win_weak_reg'),
            'Hole': result.holes
        }
        
        colors = ['#2ecc71', '#3498db', '#e74c3c']
        ax2.pie(outcomes.values(), labels=outcomes.keys(), colors=colors,
                autopct='%1.1f%%', startangle=90)
        ax2.set_title('Bet Outcomes Distribution', fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        
        return self._fig_to_base64(fig)
    
    def _fig_to_base64(self, fig) -> str:
        """Convert matplotlib figure to base64 string."""
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        img_str = base64.b64encode(buffer.read()).decode()
        plt.close(fig)
        return f'data:image/png;base64,{img_str}'
    
    def _generate_html(self, result: BacktestResult, equity_chart: str,
                       monthly_chart: str, distribution_chart: str, hole_chart: str) -> str:
        """Generate full HTML report."""
        
        # Summary metrics
        pnl_color = 'green' if result.total_profit_loss >= 0 else 'red'
        roi_color = 'green' if result.roi_percentage >= 0 else 'red'
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Eden MVP Backtest Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        h1 {{
            text-align: center;
            color: #00d9ff;
            margin-bottom: 30px;
            font-size: 2.5em;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .metric-card {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .metric-card h3 {{ color: #888; font-size: 0.9em; margin-bottom: 10px; }}
        .metric-card .value {{ font-size: 1.8em; font-weight: bold; }}
        .metric-card .value.positive {{ color: #2ecc71; }}
        .metric-card .value.negative {{ color: #e74c3c; }}
        .metric-card .value.neutral {{ color: #00d9ff; }}
        .chart-section {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 30px;
        }}
        .chart-section h2 {{
            color: #00d9ff;
            margin-bottom: 20px;
            border-bottom: 2px solid rgba(0,217,255,0.3);
            padding-bottom: 10px;
        }}
        .chart-section img {{ width: 100%; border-radius: 10px; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        th {{ background: rgba(0,217,255,0.1); color: #00d9ff; }}
        tr:hover {{ background: rgba(255,255,255,0.05); }}
        .positive {{ color: #2ecc71; }}
        .negative {{ color: #e74c3c; }}
        footer {{ text-align: center; margin-top: 40px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏒 Eden MVP Backtest Report</h1>
        
        <div class="summary-grid">
            <div class="metric-card">
                <h3>Period</h3>
                <div class="value neutral">{result.start_date} to {result.end_date}</div>
            </div>
            <div class="metric-card">
                <h3>Total Bets</h3>
                <div class="value neutral">{result.total_bets}</div>
            </div>
            <div class="metric-card">
                <h3>Win Rate</h3>
                <div class="value {'positive' if result.win_rate >= 50 else 'negative'}">{result.win_rate:.1f}%</div>
            </div>
            <div class="metric-card">
                <h3>Hole Rate</h3>
                <div class="value {'positive' if result.hole_rate <= 4 else 'negative'}">{result.hole_rate:.1f}%</div>
            </div>
            <div class="metric-card">
                <h3>Initial Bankroll</h3>
                <div class="value neutral">${result.initial_bankroll:,.2f}</div>
            </div>
            <div class="metric-card">
                <h3>Final Bankroll</h3>
                <div class="value {'positive' if result.final_bankroll >= result.initial_bankroll else 'negative'}">${result.final_bankroll:,.2f}</div>
            </div>
            <div class="metric-card">
                <h3>Total P/L</h3>
                <div class="value {'positive' if result.total_profit_loss >= 0 else 'negative'}">${result.total_profit_loss:+,.2f}</div>
            </div>
            <div class="metric-card">
                <h3>ROI</h3>
                <div class="value {'positive' if result.roi_percentage >= 0 else 'negative'}">{result.roi_percentage:+.2f}%</div>
            </div>
            <div class="metric-card">
                <h3>Sharpe Ratio</h3>
                <div class="value {'positive' if result.sharpe_ratio >= 1 else 'neutral'}">{result.sharpe_ratio:.2f}</div>
            </div>
            <div class="metric-card">
                <h3>Max Drawdown</h3>
                <div class="value negative">${result.max_drawdown:.2f} ({result.max_drawdown_pct:.1f}%)</div>
            </div>
        </div>
        
        {f'<div class="chart-section"><h2>📈 Equity Curve</h2><img src="{equity_chart}" alt="Equity Curve"></div>' if equity_chart else ''}
        
        {f'<div class="chart-section"><h2>📅 Monthly Returns</h2><img src="{monthly_chart}" alt="Monthly Returns"></div>' if monthly_chart else ''}
        
        {f'<div class="chart-section"><h2>🎯 Profit/Loss Distribution</h2><img src="{distribution_chart}" alt="P/L Distribution"></div>' if distribution_chart else ''}
        
        {f'<div class="chart-section"><h2>🕳️ Hole Probability Analysis</h2><img src="{hole_chart}" alt="Hole Analysis"></div>' if hole_chart else ''}
        
        <div class="chart-section">
            <h2>📊 Recent Bets</h2>
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Match</th>
                        <th>ROI</th>
                        <th>Hole Prob</th>
                        <th>Stake</th>
                        <th>Outcome</th>
                        <th>P/L</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(self._generate_bet_row(b) for b in result.bets[-50:])}
                </tbody>
            </table>
        </div>
        
        <footer>
            <p>Generated by Eden MVP Backtesting System | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </footer>
    </div>
</body>
</html>
"""
        return html
    
    def _generate_bet_row(self, bet: BacktestBet) -> str:
        """Generate table row for a bet."""
        pnl_class = 'positive' if bet.profit_loss >= 0 else 'negative'
        outcome_display = {
            'win_strong': '✅ Win (Strong)',
            'win_weak_reg': '✅ Win (Weak)',
            'hole': '❌ HOLE',
            'skipped': '⏭️ Skipped'
        }.get(bet.outcome.value, bet.outcome.value)
        
        return f"""
            <tr>
                <td>{bet.date}</td>
                <td>{bet.home_team} vs {bet.away_team}</td>
                <td>{bet.arb_roi:.2f}%</td>
                <td>{bet.predicted_hole_prob:.2%}</td>
                <td>${bet.total_stake:.2f}</td>
                <td>{outcome_display}</td>
                <td class="{pnl_class}">${bet.profit_loss:+.2f}</td>
            </tr>
        """
    
    def export_to_csv(self, result: BacktestResult, filename: str = None) -> str:
        """Export bet history to CSV."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backtest_bets_{timestamp}.csv"
        
        filepath = self.output_dir / filename
        
        with open(filepath, 'w') as f:
            # Header
            f.write("Date,Home Team,Away Team,ARB ROI,Predicted Hole,Actual OT,"
                   "Actual Hole,Stake,P/L,Bankroll After,Outcome\n")
            
            # Data
            for bet in result.bets:
                f.write(f"{bet.date},{bet.home_team},{bet.away_team},"
                       f"{bet.arb_roi:.2f},{bet.predicted_hole_prob:.4f},"
                       f"{bet.actual_ot},{bet.actual_hole},"
                       f"{bet.total_stake:.2f},{bet.profit_loss:.2f},"
                       f"{bet.bankroll_after:.2f},{bet.outcome.value}\n")
        
        logger.info(f"CSV exported to {filepath}")
        return str(filepath)
    
    def export_to_json(self, result: BacktestResult, filename: str = None) -> str:
        """Export full results to JSON."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backtest_results_{timestamp}.json"
        
        filepath = self.output_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(result.model_dump(), f, indent=2, default=str)
        
        logger.info(f"JSON exported to {filepath}")
        return str(filepath)
