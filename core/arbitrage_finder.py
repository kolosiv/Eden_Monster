"""Arbitrage Finder Module for Eden MVP.

Finds arbitrage opportunities in hockey betting markets.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum

from pydantic import BaseModel, Field

from core.odds_fetcher import MatchOdds, OddsData
from utils.logger import get_logger

logger = get_logger(__name__)


class ArbitrageType(str, Enum):
    """Types of arbitrage opportunities."""
    TWO_WAY = "two_way"  # Regulation+OT vs Regulation
    THREE_WAY = "three_way"  # Home, Draw, Away
    CROSS_MARKET = "cross_market"  # Different bookmakers


class ArbitrageOpportunity(BaseModel):
    """Model for an arbitrage opportunity.
    
    Attributes:
        match_id: Unique match identifier
        team_home: Home team name
        team_away: Away team name
        arb_type: Type of arbitrage
        arb_percentage: Arbitrage percentage (positive = profit)
        roi: Return on investment
        odds_strong: Odds for strong team (match winner)
        odds_weak_reg: Odds for weak team (regulation)
        bookmaker_strong: Bookmaker for strong team bet
        bookmaker_weak: Bookmaker for weak team bet
        confidence: Confidence score (0-1)
    """
    match_id: str
    team_home: str
    team_away: str
    arb_type: ArbitrageType
    arb_percentage: float
    roi: float
    odds_strong: float
    odds_weak_reg: float
    bookmaker_strong: str
    bookmaker_weak: str
    odds_draw: Optional[float] = None
    bookmaker_draw: Optional[str] = None
    confidence: float = Field(default=0.5, ge=0, le=1)
    commence_time: Optional[str] = None
    
    def is_profitable(self) -> bool:
        """Check if arbitrage is profitable."""
        return self.arb_percentage > 0 or self.roi > 0


@dataclass
class ArbitrageConfig:
    """Configuration for arbitrage finding."""
    min_roi: float = 0.02  # 2% minimum ROI
    min_arb_percentage: float = 0.0  # 0% minimum arb percentage
    max_odds_difference: float = 0.5  # Maximum acceptable odds difference
    include_three_way: bool = True  # Include 3-way markets
    min_bookmakers: int = 2  # Minimum number of bookmakers


class ArbitrageFinder:
    """Finds arbitrage opportunities in betting markets.
    
    Supports:
    - 2-way arbitrage (Regulation+OT vs Regulation only)
    - 3-way arbitrage (Home, Draw, Away)
    - Cross-bookmaker arbitrage detection
    
    The main focus is on 2-way hockey arbitrage where:
    - Bet 1: Strong team wins match (regulation or OT)
    - Bet 2: Weak team wins in regulation time
    
    Risk: "Hole" scenario where weak team wins in OT (both bets lose)
    
    Example:
        >>> finder = ArbitrageFinder(config)
        >>> opportunities = finder.find_arbitrage(matches)
        >>> for opp in opportunities:
        ...     print(f"ROI: {opp.roi:.2%}")
    """
    
    def __init__(self, config: Optional[ArbitrageConfig] = None):
        """Initialize ArbitrageFinder.
        
        Args:
            config: Arbitrage configuration settings
        """
        self.config = config or ArbitrageConfig()
        
    def calculate_arb_percentage(
        self,
        odds_1: float,
        odds_2: float,
        odds_3: Optional[float] = None
    ) -> float:
        """Calculate arbitrage percentage.
        
        For 2-way: arb% = 1 - (1/odds_1 + 1/odds_2)
        For 3-way: arb% = 1 - (1/odds_1 + 1/odds_2 + 1/odds_3)
        
        Positive value indicates arbitrage opportunity.
        
        Args:
            odds_1: First odds value
            odds_2: Second odds value
            odds_3: Third odds value (for 3-way)
            
        Returns:
            Arbitrage percentage (positive = profit potential)
        """
        if odds_1 <= 1 or odds_2 <= 1:
            return -1.0
            
        total_implied = (1 / odds_1) + (1 / odds_2)
        
        if odds_3 and odds_3 > 1:
            total_implied += (1 / odds_3)
            
        arb_percentage = 1 - total_implied
        return arb_percentage
    
    def calculate_roi(self, arb_percentage: float) -> float:
        """Calculate ROI from arbitrage percentage.
        
        ROI = arb_percentage / (1 - arb_percentage)
        
        Args:
            arb_percentage: Arbitrage percentage
            
        Returns:
            Return on investment as decimal
        """
        if arb_percentage >= 1:
            return 0.0
        return arb_percentage / (1 - arb_percentage) if arb_percentage > -1 else -1.0
    
    def find_two_way_arbitrage(
        self,
        match: MatchOdds
    ) -> List[ArbitrageOpportunity]:
        """Find 2-way arbitrage opportunities for a match.
        
        Looks for the best combination of:
        - Strong team match winner (any bookmaker)
        - Weak team regulation winner (any bookmaker)
        
        Args:
            match: Match with bookmaker odds
            
        Returns:
            List of arbitrage opportunities found
        """
        opportunities = []
        h2h_odds = [o for o in match.bookmaker_odds if o.market == "h2h"]
        
        if len(h2h_odds) < self.config.min_bookmakers:
            return opportunities
            
        # Get all possible combinations of bookmakers
        best_opp = None
        best_roi = -float('inf')
        
        for odds_strong in h2h_odds:
            for odds_weak in h2h_odds:
                # Strong team could be home or away (lower odds = favorite)
                # Determine which team is strong based on odds
                
                # Try home as strong
                arb_pct = self.calculate_arb_percentage(
                    odds_strong.odds_home,  # Strong match winner
                    odds_weak.odds_away  # Weak regulation winner
                )
                roi = self.calculate_roi(arb_pct)
                
                if roi > best_roi and roi >= self.config.min_roi:
                    best_roi = roi
                    best_opp = ArbitrageOpportunity(
                        match_id=match.match_id,
                        team_home=match.team_home,
                        team_away=match.team_away,
                        arb_type=ArbitrageType.TWO_WAY,
                        arb_percentage=arb_pct,
                        roi=roi,
                        odds_strong=odds_strong.odds_home,
                        odds_weak_reg=odds_weak.odds_away,
                        bookmaker_strong=odds_strong.bookmaker,
                        bookmaker_weak=odds_weak.bookmaker,
                        commence_time=match.commence_time.isoformat()
                    )
                
                # Try away as strong
                arb_pct = self.calculate_arb_percentage(
                    odds_strong.odds_away,  # Strong match winner
                    odds_weak.odds_home  # Weak regulation winner
                )
                roi = self.calculate_roi(arb_pct)
                
                if roi > best_roi and roi >= self.config.min_roi:
                    best_roi = roi
                    best_opp = ArbitrageOpportunity(
                        match_id=match.match_id,
                        team_home=match.team_home,
                        team_away=match.team_away,
                        arb_type=ArbitrageType.TWO_WAY,
                        arb_percentage=arb_pct,
                        roi=roi,
                        odds_strong=odds_strong.odds_away,
                        odds_weak_reg=odds_weak.odds_home,
                        bookmaker_strong=odds_strong.bookmaker,
                        bookmaker_weak=odds_weak.bookmaker,
                        commence_time=match.commence_time.isoformat()
                    )
        
        if best_opp:
            opportunities.append(best_opp)
            
        return opportunities
    
    def find_three_way_arbitrage(
        self,
        match: MatchOdds
    ) -> List[ArbitrageOpportunity]:
        """Find 3-way arbitrage opportunities for a match.
        
        Looks for opportunities in home/draw/away markets.
        
        Args:
            match: Match with bookmaker odds
            
        Returns:
            List of arbitrage opportunities found
        """
        if not self.config.include_three_way:
            return []
            
        opportunities = []
        h2h_odds = [o for o in match.bookmaker_odds if o.market == "h2h" and o.odds_draw]
        
        if len(h2h_odds) < self.config.min_bookmakers:
            return opportunities
        
        best_opp = None
        best_roi = -float('inf')
        
        # Find best odds for each outcome across all bookmakers
        best_home = max(h2h_odds, key=lambda x: x.odds_home)
        best_away = max(h2h_odds, key=lambda x: x.odds_away)
        best_draw = max(
            [o for o in h2h_odds if o.odds_draw],
            key=lambda x: x.odds_draw or 0,
            default=None
        )
        
        if not best_draw:
            return opportunities
            
        arb_pct = self.calculate_arb_percentage(
            best_home.odds_home,
            best_away.odds_away,
            best_draw.odds_draw
        )
        roi = self.calculate_roi(arb_pct)
        
        if roi >= self.config.min_roi:
            opp = ArbitrageOpportunity(
                match_id=match.match_id,
                team_home=match.team_home,
                team_away=match.team_away,
                arb_type=ArbitrageType.THREE_WAY,
                arb_percentage=arb_pct,
                roi=roi,
                odds_strong=best_home.odds_home,
                odds_weak_reg=best_away.odds_away,
                odds_draw=best_draw.odds_draw,
                bookmaker_strong=best_home.bookmaker,
                bookmaker_weak=best_away.bookmaker,
                bookmaker_draw=best_draw.bookmaker,
                commence_time=match.commence_time.isoformat()
            )
            opportunities.append(opp)
            
        return opportunities
    
    def find_arbitrage(
        self,
        matches: List[MatchOdds],
        include_two_way: bool = True,
        include_three_way: bool = True
    ) -> List[ArbitrageOpportunity]:
        """Find all arbitrage opportunities across matches.
        
        Args:
            matches: List of matches with odds
            include_two_way: Include 2-way arbitrage search
            include_three_way: Include 3-way arbitrage search
            
        Returns:
            List of all arbitrage opportunities, sorted by ROI
        """
        all_opportunities = []
        
        for match in matches:
            try:
                if include_two_way:
                    two_way = self.find_two_way_arbitrage(match)
                    all_opportunities.extend(two_way)
                    
                if include_three_way:
                    three_way = self.find_three_way_arbitrage(match)
                    all_opportunities.extend(three_way)
                    
            except Exception as e:
                logger.warning(f"Error finding arbitrage for {match.match_id}: {e}")
                continue
        
        # Sort by ROI descending
        all_opportunities.sort(key=lambda x: x.roi, reverse=True)
        
        logger.info(f"Found {len(all_opportunities)} arbitrage opportunities")
        return all_opportunities
    
    def filter_by_roi(
        self,
        opportunities: List[ArbitrageOpportunity],
        min_roi: float
    ) -> List[ArbitrageOpportunity]:
        """Filter opportunities by minimum ROI.
        
        Args:
            opportunities: List of opportunities to filter
            min_roi: Minimum ROI threshold
            
        Returns:
            Filtered list of opportunities
        """
        return [opp for opp in opportunities if opp.roi >= min_roi]
    
    def get_best_opportunities(
        self,
        opportunities: List[ArbitrageOpportunity],
        top_n: int = 5
    ) -> List[ArbitrageOpportunity]:
        """Get top N best arbitrage opportunities.
        
        Args:
            opportunities: List of opportunities
            top_n: Number of top opportunities to return
            
        Returns:
            Top N opportunities sorted by ROI
        """
        sorted_opps = sorted(opportunities, key=lambda x: x.roi, reverse=True)
        return sorted_opps[:top_n]
