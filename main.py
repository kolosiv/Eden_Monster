#!/usr/bin/env python3
"""Eden MVP - Hockey Arbitrage Betting System.

Console-based application for finding and analyzing NHL arbitrage opportunities.

Usage:
    python main.py
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, IntPrompt, FloatPrompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.layout import Layout
from rich.text import Text
from rich import box

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.odds_fetcher import OddsFetcher
from core.arbitrage_finder import ArbitrageFinder, ArbitrageConfig, ArbitrageOpportunity
from core.demo_data import generate_demo_matches, get_demo_rate_limits
from models.overtime_predictor import OvertimePredictor, TeamStats
from analysis.match_analyzer import MatchAnalyzer, AnalyzerConfig, Recommendation, RiskLevel
from analysis.stake_calculator import StakeCalculator, StakeConfig, StakingStrategy
from database.db_manager import DatabaseManager
from utils.logger import setup_logger, get_logger
from utils.helpers import format_currency, format_percentage

# Initialize console
console = Console()

# Load configuration
CONFIG_PATH = Path(__file__).parent / "config" / "config.yaml"


def load_config() -> Dict[str, Any]:
    """Load configuration from YAML file."""
    try:
        with open(CONFIG_PATH, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        console.print("[red]Error: config.yaml not found![/red]")
        console.print(f"Please create {CONFIG_PATH}")
        sys.exit(1)
    except yaml.YAMLError as e:
        console.print(f"[red]Error parsing config.yaml: {e}[/red]")
        sys.exit(1)


def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to YAML file."""
    with open(CONFIG_PATH, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)


class EdenMVP:
    """Main application class for Eden MVP."""
    
    def __init__(self):
        """Initialize Eden MVP application."""
        self.config = load_config()
        
        # Setup logging
        log_config = self.config.get('logging', {})
        setup_logger(
            level=log_config.get('level', 'INFO'),
            log_dir=log_config.get('log_dir', 'logs'),
            console_output=False  # Don't mix with Rich output
        )
        self.logger = get_logger("main")
        
        # Initialize components
        self._init_components()
        
    def _init_components(self) -> None:
        """Initialize all system components."""
        api_config = self.config.get('api', {}).get('the_odds_api', {})
        bankroll_config = self.config.get('bankroll', {})
        risk_config = self.config.get('risk', {})
        db_config = self.config.get('database', {})
        
        # Check demo mode
        self.demo_mode = self.config.get('demo_mode', False)
        
        # Odds fetcher
        self.odds_fetcher = OddsFetcher(
            api_key=api_config.get('key', ''),
            base_url=api_config.get('base_url', 'https://api.the-odds-api.com/v4'),
            sport=api_config.get('sport', 'icehockey_nhl'),
            regions=api_config.get('regions', 'us,eu'),
            cache_ttl=self.config.get('cache', {}).get('ttl_minutes', 15)
        )
        
        # Arbitrage finder
        self.arb_finder = ArbitrageFinder(
            config=ArbitrageConfig(
                min_roi=risk_config.get('min_roi', 0.02),
                include_three_way=True
            )
        )
        
        # Match analyzer
        self.analyzer = MatchAnalyzer(
            config=AnalyzerConfig(
                max_hole_probability=risk_config.get('max_hole_probability', 0.04),
                min_roi=risk_config.get('min_roi', 0.02)
            )
        )
        
        # Stake calculator
        self.stake_calc = StakeCalculator(
            config=StakeConfig(
                bankroll=bankroll_config.get('total', 1000),
                min_stake_percent=bankroll_config.get('min_stake_percent', 0.02),
                max_stake_percent=bankroll_config.get('max_stake_percent', 0.10),
                default_stake_percent=bankroll_config.get('default_stake_percent', 0.04),
                kelly_shrink=risk_config.get('kelly_shrink', 0.5)
            )
        )
        
        # Database
        self.db = DatabaseManager(db_config.get('path', 'eden_mvp.db'))
        self.db.initialize()
        
        self.logger.info("Eden MVP initialized successfully")
    
    def show_header(self) -> None:
        """Display application header."""
        header = """
[bold cyan]╔═══════════════════════════════════════════════════════════════╗
║                     EDEN MVP                                  ║
║            Hockey Arbitrage Betting System                    ║
╚═══════════════════════════════════════════════════════════════╝[/bold cyan]
"""
        console.print(header)
        
        # Show demo mode indicator
        if self.demo_mode:
            console.print("[bold yellow]🎮 DEMO MODE[/bold yellow] - Using simulated data (no API key required)\n")
        
        # Show current settings
        bankroll = self.stake_calc.config.bankroll
        min_roi = self.analyzer.config.min_roi
        max_hole = self.analyzer.config.max_hole_probability
        
        console.print(f"[dim]Bankroll: {format_currency(bankroll)} | "
                     f"Min ROI: {format_percentage(min_roi)} | "
                     f"Max Hole: {format_percentage(max_hole)}[/dim]\n")
    
    def show_menu(self) -> str:
        """Display main menu and get user choice."""
        menu = Table(show_header=False, box=box.ROUNDED, expand=False)
        menu.add_column("Option", style="cyan")
        menu.add_column("Description")
        
        menu.add_row("1", "🔍 Fetch Current Arbitrage Opportunities")
        menu.add_row("2", "📊 Analyze Specific Match")
        menu.add_row("3", "📜 View Betting History")
        menu.add_row("4", "📈 Show Statistics")
        menu.add_row("5", "⚙️  Update Configuration")
        menu.add_row("6", "💾 Record Bet Result")
        menu.add_row("0", "🚪 Exit")
        
        console.print(menu)
        console.print()
        
        return Prompt.ask("Select option", choices=["0", "1", "2", "3", "4", "5", "6"])
    
    def fetch_opportunities(self) -> None:
        """Fetch and display current arbitrage opportunities."""
        console.print("\n[bold]Fetching NHL Odds...[/bold]\n")
        
        # Demo mode - use generated data
        if self.demo_mode:
            console.print("[yellow]Using demo data with simulated NHL matches...[/yellow]\n")
            matches = generate_demo_matches(6)
            rate_limit = get_demo_rate_limits()
        else:
            # Check API key
            api_key = self.config.get('api', {}).get('the_odds_api', {}).get('key', '')
            if not api_key or api_key == "YOUR_API_KEY_HERE":
                console.print(Panel(
                    "[red]API key not configured![/red]\n\n"
                    "Please add your The Odds API key to config/config.yaml\n"
                    "Get your free key at: https://the-odds-api.com/\n\n"
                    "[green]TIP:[/green] Set 'demo_mode: true' in config.yaml to test without API key",
                    title="Configuration Required"
                ))
                return
            
            try:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task("Fetching odds from The Odds API...", total=None)
                    matches = self.odds_fetcher.fetch_odds(markets="h2h")
                    progress.update(task, description=f"Found {len(matches)} matches")
                rate_limit = self.odds_fetcher.get_rate_limit_status()
            except ValueError as e:
                console.print(f"[red]Error: {e}[/red]")
                return
            except Exception as e:
                self.logger.error(f"Error fetching opportunities: {e}")
                console.print(f"[red]Error fetching data: {e}[/red]")
                return
            
        if not matches:
            console.print("[yellow]No matches found. NHL might be in off-season.[/yellow]")
            return
        
        # Find arbitrage opportunities
        console.print(f"\n[bold]Analyzing {len(matches)} matches for arbitrage opportunities...[/bold]\n")
        opportunities = self.arb_finder.find_arbitrage(matches)
        
        if not opportunities:
            console.print("[yellow]No arbitrage opportunities found at this time.[/yellow]")
            console.print("[dim]Tip: Try again later as odds change frequently.[/dim]")
            return
        
        # Analyze each opportunity
        analyses = []
        for opp in opportunities:
            analysis = self.analyzer.analyze(opp)
            stake_result = self.stake_calc.calculate(analysis, StakingStrategy.ADAPTIVE)
            
            # Add stakes to analysis
            analysis.stake_strong = stake_result.stake_strong
            analysis.stake_weak = stake_result.stake_weak
            analysis.total_stake = stake_result.total_stake
            analysis.potential_profit = stake_result.potential_profit
            
            analyses.append(analysis)
            
            # Save to database
            self.db.insert_match(analysis.model_dump())
        
        # Display results
        self._display_opportunities(analyses)
        
        # Show API usage
        if rate_limit and rate_limit.get('requests_remaining'):
            console.print(f"\n[dim]API requests remaining: {rate_limit['requests_remaining']}[/dim]")
    
    def _display_opportunities(self, analyses: list) -> None:
        """Display analyzed opportunities in a table."""
        # Group by recommendation
        bet_ops = [a for a in analyses if a.recommendation == Recommendation.BET]
        caution_ops = [a for a in analyses if a.recommendation == Recommendation.CAUTION]
        skip_ops = [a for a in analyses if a.recommendation == Recommendation.SKIP]
        
        if bet_ops:
            console.print("\n[bold green]✅ RECOMMENDED BETS[/bold green]")
            self._display_opportunity_table(bet_ops, "green")
        
        if caution_ops:
            console.print("\n[bold yellow]⚠️  PROCEED WITH CAUTION[/bold yellow]")
            self._display_opportunity_table(caution_ops, "yellow")
        
        if skip_ops and Confirm.ask("\nShow skipped opportunities?", default=False):
            console.print("\n[bold red]❌ SKIPPED[/bold red]")
            self._display_opportunity_table(skip_ops, "red")
    
    def _display_opportunity_table(self, analyses: list, color: str) -> None:
        """Display opportunities in a formatted table."""
        table = Table(box=box.ROUNDED, expand=True)
        
        table.add_column("Match", style="bold")
        table.add_column("ROI", justify="right")
        table.add_column("Hole %", justify="right")
        table.add_column("EV", justify="right")
        table.add_column("Risk", justify="center")
        table.add_column("Stake", justify="right")
        table.add_column("Profit", justify="right")
        table.add_column("Bookmakers")
        
        for a in analyses[:10]:  # Limit to 10
            # Format risk level with color
            risk_colors = {
                RiskLevel.LOW: "green",
                RiskLevel.MEDIUM: "yellow",
                RiskLevel.HIGH: "red",
                RiskLevel.EXTREME: "bold red"
            }
            risk_style = risk_colors.get(a.risk_level, "white")
            
            table.add_row(
                f"{a.team_strong}\nvs {a.team_weak}",
                f"[{color}]{format_percentage(a.arb_roi)}[/{color}]",
                f"{format_percentage(a.hole_probability)}",
                f"{a.expected_value:.4f}",
                f"[{risk_style}]{a.risk_level.value.upper()}[/{risk_style}]",
                format_currency(a.total_stake),
                format_currency(a.potential_profit),
                f"Strong: {a.bookmaker_strong}\nWeak: {a.bookmaker_weak}"
            )
        
        console.print(table)
        
        # Show reasoning for top pick
        if analyses:
            top = analyses[0]
            console.print(f"\n[bold]Top Pick Analysis:[/bold]")
            for reason in top.reasoning[:5]:
                console.print(f"  • {reason}")
    
    def analyze_match(self) -> None:
        """Analyze a specific match by ID."""
        console.print("\n[bold]Analyze Specific Match[/bold]\n")
        
        # Get recent matches from DB
        recent = self.db.get_recent_matches(10)
        
        if recent:
            console.print("[dim]Recent matches in database:[/dim]")
            for i, m in enumerate(recent[:5], 1):
                console.print(f"  {i}. {m['team_strong']} vs {m['team_weak']} ({m['match_id'][:8]}...)")
        
        match_id = Prompt.ask("\nEnter match ID (or partial)")
        
        # Find match
        match = self.db.get_match(match_id)
        
        if not match:
            # Try partial match
            for m in recent:
                if match_id in m['match_id']:
                    match = m
                    break
        
        if not match:
            console.print("[yellow]Match not found. Try fetching opportunities first.[/yellow]")
            return
        
        # Display detailed analysis
        self._display_match_details(match)
    
    def _display_match_details(self, match: Dict) -> None:
        """Display detailed match analysis."""
        panel_content = f"""
[bold]{match['team_strong']} vs {match['team_weak']}[/bold]

[cyan]Odds:[/cyan]
  Strong ({match['bookmaker_strong']}): {match['odds_strong']:.2f}
  Weak Reg ({match['bookmaker_weak']}): {match['odds_weak_reg']:.2f}

[cyan]Arbitrage Analysis:[/cyan]
  ROI: {format_percentage(match.get('arb_roi', 0))}
  Arbitrage %: {format_percentage(match.get('arb_percentage', 0))}

[cyan]OT Prediction:[/cyan]
  OT Probability: {format_percentage(match.get('ot_probability', 0))}
  Hole Probability: {format_percentage(match.get('hole_probability', 0))}
  
[cyan]Risk Assessment:[/cyan]
  Expected Value: {match.get('expected_value', 0):.4f}
  Risk Level: {match.get('risk_level', 'N/A')}
  Confidence: {format_percentage(match.get('confidence_score', 0))}
  
[cyan]Recommendation:[/cyan] {match.get('recommendation', 'N/A').upper()}
"""
        console.print(Panel(panel_content, title="Match Analysis", border_style="cyan"))
        
        # Calculate stakes
        if Confirm.ask("\nCalculate stakes for this match?"):
            bankroll = self.stake_calc.config.bankroll
            strategy = Prompt.ask(
                "Select strategy",
                choices=["fixed", "kelly", "adaptive"],
                default="adaptive"
            )
            
            # Create mock analysis for stake calculation
            from analysis.match_analyzer import MatchAnalysis
            analysis = MatchAnalysis(
                match_id=match['match_id'],
                team_strong=match['team_strong'],
                team_weak=match['team_weak'],
                odds_strong=match['odds_strong'],
                odds_weak_reg=match['odds_weak_reg'],
                bookmaker_strong=match['bookmaker_strong'],
                bookmaker_weak=match['bookmaker_weak'],
                arb_roi=match.get('arb_roi', 0),
                arb_percentage=match.get('arb_percentage', 0),
                ot_probability=match.get('ot_probability', 0),
                hole_probability=match.get('hole_probability', 0),
                ot_confidence=match.get('confidence_score', 0.5),
                expected_value=match.get('expected_value', 0),
                risk_level=RiskLevel(match.get('risk_level', 'medium')),
                recommendation=Recommendation(match.get('recommendation', 'skip')),
                confidence_score=match.get('confidence_score', 0.5)
            )
            
            strategy_enum = StakingStrategy(strategy)
            result = self.stake_calc.calculate(analysis, strategy_enum)
            
            stake_panel = f"""
[bold]Stake Calculation ({strategy.upper()} Strategy)[/bold]

Bankroll: {format_currency(bankroll)}

[cyan]Stakes:[/cyan]
  Strong Team: {format_currency(result.stake_strong)} @ {match['odds_strong']:.2f}
  Weak Team Reg: {format_currency(result.stake_weak)} @ {match['odds_weak_reg']:.2f}
  Total Stake: {format_currency(result.total_stake)}

[cyan]Potential Outcomes:[/cyan]
  If Strong Wins: {format_currency(result.profit_if_strong_wins)} profit
  If Weak Wins Reg: {format_currency(result.profit_if_weak_wins)} profit
  If Hole (Weak OT): {format_currency(-result.loss_if_hole)} loss
"""
            console.print(Panel(stake_panel, title="Stake Recommendation", border_style="green"))
    
    def view_history(self) -> None:
        """Display betting history."""
        console.print("\n[bold]Betting History[/bold]\n")
        
        history = self.db.get_betting_history(20)
        
        if not history:
            console.print("[yellow]No betting history found.[/yellow]")
            return
        
        table = Table(box=box.ROUNDED, expand=True)
        table.add_column("Date", style="dim")
        table.add_column("Match")
        table.add_column("Strategy")
        table.add_column("Stake", justify="right")
        table.add_column("Status", justify="center")
        table.add_column("P/L", justify="right")
        
        for h in history:
            # Format status with color
            status = h.get('status', 'pending')
            status_style = {
                'won': '[green]WON[/green]',
                'lost': '[red]LOST[/red]',
                'pending': '[yellow]PENDING[/yellow]'
            }.get(status, status)
            
            # Format P/L
            pnl = h.get('profit_loss')
            if pnl is not None:
                pnl_str = format_currency(pnl)
                if pnl >= 0:
                    pnl_str = f"[green]+{pnl_str[1:]}[/green]"
                else:
                    pnl_str = f"[red]{pnl_str}[/red]"
            else:
                pnl_str = "-"
            
            table.add_row(
                h.get('created_at', '')[:10],
                f"{h.get('team_strong', 'N/A')}\nvs {h.get('team_weak', 'N/A')}",
                h.get('strategy', 'N/A'),
                format_currency(h.get('total_stake', 0)),
                status_style,
                pnl_str
            )
        
        console.print(table)
    
    def show_statistics(self) -> None:
        """Display comprehensive statistics."""
        console.print("\n[bold]Statistics Dashboard[/bold]\n")
        
        stats = self.db.get_statistics()
        
        # Overall performance
        perf_panel = f"""
[bold cyan]Overall Performance[/bold cyan]

Total Bets: {stats['total_bets']}
  ├─ Won: [green]{stats['won']}[/green]
  ├─ Lost: [red]{stats['lost']}[/red]
  └─ Pending: [yellow]{stats['pending']}[/yellow]

Win Rate: {stats['win_rate']:.1f}%
Hole Rate: {stats['hole_rate']:.1f}%

[bold cyan]Financial Summary[/bold cyan]

Total Staked: {format_currency(stats['total_staked'])}
Total P/L: {format_currency(stats['total_profit_loss'])}
ROI: {stats['roi']:.2f}%

Best Result: {format_currency(stats['best_result'])}
Worst Result: {format_currency(stats['worst_result'])}
Avg per Bet: {format_currency(stats['avg_profit_per_bet'])}
"""
        console.print(Panel(perf_panel, title="Statistics", border_style="cyan"))
        
        # Strategy performance
        strat_perf = self.db.get_strategy_performance()
        if strat_perf:
            console.print("\n[bold]Performance by Strategy[/bold]")
            
            strat_table = Table(box=box.ROUNDED)
            strat_table.add_column("Strategy")
            strat_table.add_column("Bets", justify="right")
            strat_table.add_column("Win Rate", justify="right")
            strat_table.add_column("P/L", justify="right")
            
            for strat, data in strat_perf.items():
                pnl = data['total_pnl']
                pnl_str = f"[green]{format_currency(pnl)}[/green]" if pnl >= 0 else f"[red]{format_currency(pnl)}[/red]"
                
                strat_table.add_row(
                    strat.upper(),
                    str(data['total']),
                    f"{data['win_rate']:.1f}%",
                    pnl_str
                )
            
            console.print(strat_table)
    
    def update_config(self) -> None:
        """Update configuration settings."""
        console.print("\n[bold]Configuration Settings[/bold]\n")
        
        while True:
            config_menu = Table(show_header=False, box=box.ROUNDED)
            config_menu.add_column("Option", style="cyan")
            config_menu.add_column("Current Value")
            config_menu.add_column("Description")
            
            bankroll = self.stake_calc.config.bankroll
            min_roi = self.analyzer.config.min_roi
            max_hole = self.analyzer.config.max_hole_probability
            default_stake = self.stake_calc.config.default_stake_percent
            
            config_menu.add_row("1", format_currency(bankroll), "Bankroll")
            config_menu.add_row("2", format_percentage(min_roi), "Minimum ROI")
            config_menu.add_row("3", format_percentage(max_hole), "Max Hole Probability")
            config_menu.add_row("4", format_percentage(default_stake), "Default Stake %")
            config_menu.add_row("5", "***", "API Key")
            config_menu.add_row("0", "", "Back to Main Menu")
            
            console.print(config_menu)
            
            choice = Prompt.ask("\nSelect setting to update", choices=["0", "1", "2", "3", "4", "5"])
            
            if choice == "0":
                break
            elif choice == "1":
                new_val = FloatPrompt.ask("Enter new bankroll", default=bankroll)
                self.stake_calc.update_bankroll(new_val)
                self.config['bankroll']['total'] = new_val
                save_config(self.config)
                console.print(f"[green]Bankroll updated to {format_currency(new_val)}[/green]")
            elif choice == "2":
                new_val = FloatPrompt.ask("Enter min ROI (decimal)", default=min_roi)
                self.analyzer.config.min_roi = new_val
                self.config['risk']['min_roi'] = new_val
                save_config(self.config)
                console.print(f"[green]Min ROI updated to {format_percentage(new_val)}[/green]")
            elif choice == "3":
                new_val = FloatPrompt.ask("Enter max hole probability (decimal)", default=max_hole)
                self.analyzer.config.max_hole_probability = new_val
                self.config['risk']['max_hole_probability'] = new_val
                save_config(self.config)
                console.print(f"[green]Max hole probability updated to {format_percentage(new_val)}[/green]")
            elif choice == "4":
                new_val = FloatPrompt.ask("Enter default stake % (decimal)", default=default_stake)
                self.stake_calc.config.default_stake_percent = new_val
                self.config['bankroll']['default_stake_percent'] = new_val
                save_config(self.config)
                console.print(f"[green]Default stake updated to {format_percentage(new_val)}[/green]")
            elif choice == "5":
                new_key = Prompt.ask("Enter new API key")
                self.config['api']['the_odds_api']['key'] = new_key
                self.odds_fetcher.api_key = new_key
                save_config(self.config)
                console.print("[green]API key updated[/green]")
    
    def record_result(self) -> None:
        """Record the result of a pending bet."""
        console.print("\n[bold]Record Bet Result[/bold]\n")
        
        pending = self.db.get_pending_bets()
        
        if not pending:
            console.print("[yellow]No pending bets to record.[/yellow]")
            return
        
        console.print("[bold]Pending Bets:[/bold]")
        for i, bet in enumerate(pending, 1):
            match = self.db.get_match(bet['match_id'])
            if match:
                console.print(f"  {i}. {match['team_strong']} vs {match['team_weak']} - "
                            f"Stake: {format_currency(bet['total_stake'])}")
        
        idx = IntPrompt.ask("Select bet number", default=1) - 1
        if idx < 0 or idx >= len(pending):
            console.print("[red]Invalid selection[/red]")
            return
        
        bet = pending[idx]
        
        outcome = Prompt.ask(
            "What was the outcome?",
            choices=["strong_win", "weak_win_reg", "hole"]
        )
        
        # Calculate profit/loss
        if outcome == "hole":
            pnl = -bet['total_stake']
        else:
            pnl = bet['potential_profit']
        
        # Update bankroll
        new_bankroll = self.stake_calc.config.bankroll + pnl
        
        # Record result
        self.db.insert_result({
            'bet_id': bet['id'],
            'match_id': bet['match_id'],
            'actual_outcome': outcome,
            'profit_loss': pnl,
            'final_bankroll': new_bankroll
        })
        
        # Update bankroll
        self.stake_calc.update_bankroll(new_bankroll)
        self.config['bankroll']['total'] = new_bankroll
        save_config(self.config)
        
        if pnl >= 0:
            console.print(f"[green]Result recorded: +{format_currency(pnl)} profit![/green]")
        else:
            console.print(f"[red]Result recorded: {format_currency(pnl)} loss[/red]")
        
        console.print(f"New bankroll: {format_currency(new_bankroll)}")
    
    def run(self) -> None:
        """Run the main application loop."""
        try:
            while True:
                console.clear()
                self.show_header()
                choice = self.show_menu()
                
                if choice == "0":
                    console.print("\n[bold cyan]Thanks for using Eden MVP! Good luck! 🏒[/bold cyan]\n")
                    break
                elif choice == "1":
                    self.fetch_opportunities()
                elif choice == "2":
                    self.analyze_match()
                elif choice == "3":
                    self.view_history()
                elif choice == "4":
                    self.show_statistics()
                elif choice == "5":
                    self.update_config()
                elif choice == "6":
                    self.record_result()
                
                Prompt.ask("\nPress Enter to continue")
                
        except KeyboardInterrupt:
            console.print("\n[bold cyan]Goodbye![/bold cyan]\n")


def main():
    """Main entry point."""
    app = EdenMVP()
    app.run()


if __name__ == "__main__":
    main()
