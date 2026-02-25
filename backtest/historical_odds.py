"""Historical Odds Provider for Eden MVP Backtesting.

Provides historical odds data for backtesting.
"""

import json
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

from pydantic import BaseModel

from utils.logger import get_logger

logger = get_logger(__name__)


class HistoricalOdds(BaseModel):
    """Historical odds for a match."""
    match_id: str
    date: str
    home_team: str
    away_team: str
    
    # Match winner odds (h2h)
    home_h2h_odds: float
    away_h2h_odds: float
    draw_odds: Optional[float] = None  # For 3-way
    
    # Multiple bookmakers
    bookmakers: Dict[str, Dict[str, float]] = {}
    
    # Actual result
    home_goals: Optional[int] = None
    away_goals: Optional[int] = None
    went_to_ot: bool = False
    ot_winner: Optional[str] = None  # 'home' or 'away'
    
    # Arbitrage info if found
    has_arbitrage: bool = False
    arb_roi: Optional[float] = None
    best_home_book: Optional[str] = None
    best_away_book: Optional[str] = None


class HistoricalOddsProvider:
    """Provides historical odds for backtesting.
    
    Can either use real historical data or generate synthetic data
    based on realistic NHL patterns.
    """
    
    BOOKMAKERS = [
        "DraftKings", "FanDuel", "BetMGM", "Caesars",
        "PointsBet", "Barstool", "WynnBET", "BetRivers"
    ]
    
    NHL_TEAMS = [
        "Boston Bruins", "Toronto Maple Leafs", "Tampa Bay Lightning",
        "Florida Panthers", "Colorado Avalanche", "Vegas Golden Knights",
        "Edmonton Oilers", "Dallas Stars", "Carolina Hurricanes",
        "New York Rangers", "New Jersey Devils", "Winnipeg Jets"
    ]
    
    def __init__(self, data_path: str = "data/historical_odds"):
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)
    
    def generate_historical_odds(
        self,
        num_matches: int = 200,
        start_date: datetime = None,
        arb_rate: float = 0.05  # ~5% of matches have arbitrage
    ) -> List[HistoricalOdds]:
        """Generate synthetic historical odds data.
        
        Creates realistic NHL odds with occasional arbitrage opportunities.
        """
        logger.info(f"Generating {num_matches} historical matches with odds...")
        
        if start_date is None:
            start_date = datetime.now() - timedelta(days=365)
        
        matches = []
        
        for i in range(num_matches):
            # Random date
            days_offset = random.randint(0, 365)
            match_date = start_date + timedelta(days=days_offset)
            
            # Random teams
            home_team = random.choice(self.NHL_TEAMS)
            away_team = random.choice([t for t in self.NHL_TEAMS if t != home_team])
            
            # Generate base probability (home team)
            # NHL home advantage is ~55%
            true_home_prob = 0.55 + random.gauss(0, 0.1)
            true_home_prob = max(0.35, min(0.70, true_home_prob))
            true_away_prob = 1 - true_home_prob
            
            # Generate bookmaker odds with vig (~5-8%)
            bookmaker_odds = {}
            base_vig = 0.05 + random.random() * 0.03
            
            best_home_odds = 0
            best_away_odds = 0
            best_home_book = None
            best_away_book = None
            
            for book in self.BOOKMAKERS:
                # Add variance to each bookmaker
                book_variance = random.gauss(0, 0.02)
                
                home_implied = true_home_prob + book_variance + base_vig / 2
                away_implied = true_away_prob - book_variance + base_vig / 2
                
                home_odds = 1 / max(0.1, home_implied)
                away_odds = 1 / max(0.1, away_implied)
                
                # Slight adjustments for market inefficiency
                if random.random() < 0.2:  # 20% chance of better odds
                    if random.random() < 0.5:
                        home_odds *= 1.02 + random.random() * 0.03
                    else:
                        away_odds *= 1.02 + random.random() * 0.03
                
                bookmaker_odds[book] = {
                    "home": round(home_odds, 2),
                    "away": round(away_odds, 2)
                }
                
                if home_odds > best_home_odds:
                    best_home_odds = home_odds
                    best_home_book = book
                if away_odds > best_away_odds:
                    best_away_odds = away_odds
                    best_away_book = book
            
            # Check for arbitrage
            arb_pct = (1 / best_home_odds + 1 / best_away_odds)
            has_arb = arb_pct < 1.0
            arb_roi = (1 / arb_pct - 1) * 100 if has_arb else 0
            
            # Force some arbitrage opportunities for testing
            if not has_arb and random.random() < arb_rate:
                # Create artificial arb
                boost = 1.03 + random.random() * 0.02
                if random.random() < 0.5:
                    bookmaker_odds[best_home_book]["home"] *= boost
                    best_home_odds *= boost
                else:
                    bookmaker_odds[best_away_book]["away"] *= boost
                    best_away_odds *= boost
                
                arb_pct = (1 / best_home_odds + 1 / best_away_odds)
                has_arb = arb_pct < 1.0
                arb_roi = (1 / arb_pct - 1) * 100 if has_arb else 0
            
            # Simulate match result
            went_to_ot = random.random() < 0.23  # 23% OT rate
            
            if went_to_ot:
                # Tied score
                score = random.choices([1, 2, 3, 4], weights=[10, 40, 40, 10])[0]
                home_goals = score
                away_goals = score
                
                # OT winner (favorite ~55%)
                ot_winner = "home" if random.random() < (true_home_prob + 0.05) else "away"
            else:
                # Regulation winner
                home_wins = random.random() < true_home_prob
                
                if home_wins:
                    home_goals = random.choices([2, 3, 4, 5, 6], weights=[15, 35, 30, 15, 5])[0]
                    away_goals = random.randint(0, home_goals - 1)
                else:
                    away_goals = random.choices([2, 3, 4, 5, 6], weights=[15, 35, 30, 15, 5])[0]
                    home_goals = random.randint(0, away_goals - 1)
                
                ot_winner = None
            
            match = HistoricalOdds(
                match_id=f"hist_{match_date.strftime('%Y%m%d')}_{i:03d}",
                date=match_date.strftime("%Y-%m-%d"),
                home_team=home_team,
                away_team=away_team,
                home_h2h_odds=best_home_odds,
                away_h2h_odds=best_away_odds,
                bookmakers=bookmaker_odds,
                home_goals=home_goals,
                away_goals=away_goals,
                went_to_ot=went_to_ot,
                ot_winner=ot_winner,
                has_arbitrage=has_arb,
                arb_roi=arb_roi if has_arb else None,
                best_home_book=best_home_book,
                best_away_book=best_away_book
            )
            matches.append(match)
        
        # Sort by date
        matches.sort(key=lambda x: x.date)
        
        arb_count = sum(1 for m in matches if m.has_arbitrage)
        ot_count = sum(1 for m in matches if m.went_to_ot)
        
        logger.info(f"Generated {len(matches)} matches")
        logger.info(f"Arbitrage opportunities: {arb_count} ({arb_count/len(matches):.1%})")
        logger.info(f"OT games: {ot_count} ({ot_count/len(matches):.1%})")
        
        # Save to file
        self._save_odds(matches)
        
        return matches
    
    def _save_odds(self, matches: List[HistoricalOdds]) -> None:
        """Save odds to JSON file."""
        filepath = self.data_path / "historical_odds.json"
        data = [m.model_dump() for m in matches]
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved historical odds to {filepath}")
    
    def load_odds(self) -> List[HistoricalOdds]:
        """Load historical odds from file."""
        filepath = self.data_path / "historical_odds.json"
        
        if not filepath.exists():
            logger.info("No historical odds found, generating...")
            return self.generate_historical_odds()
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        return [HistoricalOdds(**d) for d in data]
    
    def get_arbitrage_matches(self) -> List[HistoricalOdds]:
        """Get only matches with arbitrage opportunities."""
        all_matches = self.load_odds()
        return [m for m in all_matches if m.has_arbitrage]
