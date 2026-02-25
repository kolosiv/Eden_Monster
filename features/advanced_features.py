"""Advanced Features Module.

Extracts advanced team statistics features including Corsi, Fenwick, PDO, etc.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import numpy as np

from data_collector.advanced_stats import AdvancedStatsCollector, AdvancedTeamStats
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AdvancedMatchFeatures:
    """Advanced features for a match."""
    # Shooting/Scoring differentials
    shooting_pct_diff: float = 0.0
    save_pct_diff: float = 0.0
    pdo_diff: float = 0.0
    
    # Possession differentials
    corsi_diff: float = 0.0
    fenwick_diff: float = 0.0
    
    # Physical play differentials
    hits_diff: float = 0.0
    blocked_diff: float = 0.0
    
    # Special teams differential
    special_teams_diff: float = 0.0
    pp_diff: float = 0.0
    pk_diff: float = 0.0
    
    # Face-off differential
    faceoff_diff: float = 0.0
    
    # Luck indicators
    home_luck_status: str = 'normal'
    away_luck_status: str = 'normal'
    home_regression_risk: float = 0.0
    away_regression_risk: float = 0.0


class AdvancedFeatureExtractor:
    """Extracts advanced analytics features for ML models.
    
    Includes:
    - Corsi/Fenwick possession metrics
    - PDO (luck indicator)
    - Shooting/Save percentages
    - Special teams metrics
    - Physical play stats
    - Form/momentum indicators
    
    Example:
        >>> extractor = AdvancedFeatureExtractor()
        >>> features = extractor.extract_all("TOR", "BOS", "20232024")
    """
    
    def __init__(self, stats_collector: Optional[AdvancedStatsCollector] = None):
        """Initialize advanced feature extractor.
        
        Args:
            stats_collector: Optional AdvancedStatsCollector instance
        """
        self.collector = stats_collector or AdvancedStatsCollector()
    
    def extract_match_features(
        self,
        home_team: str,
        away_team: str,
        season: str = None
    ) -> AdvancedMatchFeatures:
        """Extract advanced features for a match.
        
        Args:
            home_team: Home team abbreviation
            away_team: Away team abbreviation
            season: Season string
            
        Returns:
            AdvancedMatchFeatures
        """
        home_stats = self.collector.fetch_team_advanced_stats(home_team, season)
        away_stats = self.collector.fetch_team_advanced_stats(away_team, season)
        
        if not home_stats or not away_stats:
            logger.warning(f"Missing advanced stats for {home_team} vs {away_team}")
            return AdvancedMatchFeatures()
        
        # Get luck analysis
        home_luck = self.collector.get_team_luck_indicator(home_team, season)
        away_luck = self.collector.get_team_luck_indicator(away_team, season)
        
        features = AdvancedMatchFeatures(
            shooting_pct_diff=home_stats.shooting_percentage - away_stats.shooting_percentage,
            save_pct_diff=home_stats.save_percentage - away_stats.save_percentage,
            pdo_diff=home_stats.pdo - away_stats.pdo,
            corsi_diff=home_stats.corsi_for_pct - away_stats.corsi_for_pct,
            fenwick_diff=home_stats.fenwick_for_pct - away_stats.fenwick_for_pct,
            hits_diff=home_stats.hits_per_game - away_stats.hits_per_game,
            blocked_diff=home_stats.blocked_shots_per_game - away_stats.blocked_shots_per_game,
            special_teams_diff=(
                (home_stats.power_play_pct + home_stats.penalty_kill_pct) -
                (away_stats.power_play_pct + away_stats.penalty_kill_pct)
            ),
            pp_diff=home_stats.power_play_pct - away_stats.power_play_pct,
            pk_diff=home_stats.penalty_kill_pct - away_stats.penalty_kill_pct,
            faceoff_diff=home_stats.faceoff_win_pct - away_stats.faceoff_win_pct,
            home_luck_status=home_luck.get('luck_status', 'normal'),
            away_luck_status=away_luck.get('luck_status', 'normal'),
            home_regression_risk=home_luck.get('regression_risk', 0.0),
            away_regression_risk=away_luck.get('regression_risk', 0.0)
        )
        
        return features
    
    def extract_time_based_features(
        self,
        team_abbrev: str,
        season: str = None,
        recent_games: int = 10
    ) -> Dict[str, float]:
        """Extract time-based trend features.
        
        Args:
            team_abbrev: Team abbreviation
            season: Season string
            recent_games: Number of recent games for trends
            
        Returns:
            Dict of time-based features
        """
        stats = self.collector.fetch_team_advanced_stats(team_abbrev, season)
        
        if not stats:
            return {
                'win_rate_trend': 0.0,
                'goals_scored_trend': 0.0,
                'form_momentum': 0.0,
                'season_phase': 0.5  # mid-season
            }
        
        # These would ideally come from actual recent game data
        # Using placeholders based on overall stats
        games_played = stats.games_played
        
        # Determine season phase (0=early, 0.5=mid, 1=late/playoff)
        if games_played < 20:
            season_phase = 0.0
        elif games_played < 60:
            season_phase = 0.5
        else:
            season_phase = 1.0
        
        return {
            'win_rate_trend': 0.0,  # Would calculate from recent results
            'goals_scored_trend': 0.0,
            'form_momentum': 0.0,
            'season_phase': season_phase,
            'games_played': games_played
        }
    
    def extract_all(
        self,
        home_team: str,
        away_team: str,
        season: str = None
    ) -> Dict[str, float]:
        """Extract all advanced features for a match.
        
        Args:
            home_team: Home team abbreviation
            away_team: Away team abbreviation
            season: Season string
            
        Returns:
            Dict of feature name to value
        """
        match_features = self.extract_match_features(home_team, away_team, season)
        home_time_features = self.extract_time_based_features(home_team, season)
        away_time_features = self.extract_time_based_features(away_team, season)
        
        # Get raw stats for additional features
        home_stats = self.collector.fetch_team_advanced_stats(home_team, season)
        away_stats = self.collector.fetch_team_advanced_stats(away_team, season)
        
        features = {
            # Differentials from match features
            'shooting_pct_diff': match_features.shooting_pct_diff,
            'save_pct_diff': match_features.save_pct_diff,
            'pdo_diff': match_features.pdo_diff,
            'corsi_diff': match_features.corsi_diff,
            'fenwick_diff': match_features.fenwick_diff,
            'hits_diff': match_features.hits_diff,
            'blocked_diff': match_features.blocked_diff,
            'special_teams_diff': match_features.special_teams_diff,
            'pp_diff': match_features.pp_diff,
            'pk_diff': match_features.pk_diff,
            'faceoff_diff': match_features.faceoff_diff,
            
            # Luck/regression indicators
            'home_regression_risk': match_features.home_regression_risk,
            'away_regression_risk': match_features.away_regression_risk,
            'regression_diff': match_features.home_regression_risk - match_features.away_regression_risk,
            
            # Time-based features
            'home_win_trend': home_time_features.get('win_rate_trend', 0.0),
            'away_win_trend': away_time_features.get('win_rate_trend', 0.0),
            'home_goals_trend': home_time_features.get('goals_scored_trend', 0.0),
            'away_goals_trend': away_time_features.get('goals_scored_trend', 0.0),
            'home_momentum': home_time_features.get('form_momentum', 0.0),
            'away_momentum': away_time_features.get('form_momentum', 0.0),
            'season_phase': home_time_features.get('season_phase', 0.5),
        }
        
        # Add raw stats if available
        if home_stats:
            features.update({
                'home_corsi_pct': home_stats.corsi_for_pct,
                'home_fenwick_pct': home_stats.fenwick_for_pct,
                'home_pdo': home_stats.pdo,
                'home_goals_for_pg': home_stats.goals_for_per_game,
                'home_goals_against_pg': home_stats.goals_against_per_game,
                'home_shots_for_pg': home_stats.shots_for_per_game,
                'home_takeaway_ratio': home_stats.takeaway_giveaway_ratio,
            })
        else:
            features.update({
                'home_corsi_pct': 50.0,
                'home_fenwick_pct': 50.0,
                'home_pdo': 100.0,
                'home_goals_for_pg': 3.0,
                'home_goals_against_pg': 3.0,
                'home_shots_for_pg': 30.0,
                'home_takeaway_ratio': 1.0,
            })
        
        if away_stats:
            features.update({
                'away_corsi_pct': away_stats.corsi_for_pct,
                'away_fenwick_pct': away_stats.fenwick_for_pct,
                'away_pdo': away_stats.pdo,
                'away_goals_for_pg': away_stats.goals_for_per_game,
                'away_goals_against_pg': away_stats.goals_against_per_game,
                'away_shots_for_pg': away_stats.shots_for_per_game,
                'away_takeaway_ratio': away_stats.takeaway_giveaway_ratio,
            })
        else:
            features.update({
                'away_corsi_pct': 50.0,
                'away_fenwick_pct': 50.0,
                'away_pdo': 100.0,
                'away_goals_for_pg': 3.0,
                'away_goals_against_pg': 3.0,
                'away_shots_for_pg': 30.0,
                'away_takeaway_ratio': 1.0,
            })
        
        return features
    
    def get_feature_names(self) -> List[str]:
        """Get list of all feature names."""
        return [
            'shooting_pct_diff', 'save_pct_diff', 'pdo_diff',
            'corsi_diff', 'fenwick_diff', 'hits_diff', 'blocked_diff',
            'special_teams_diff', 'pp_diff', 'pk_diff', 'faceoff_diff',
            'home_regression_risk', 'away_regression_risk', 'regression_diff',
            'home_win_trend', 'away_win_trend',
            'home_goals_trend', 'away_goals_trend',
            'home_momentum', 'away_momentum', 'season_phase',
            'home_corsi_pct', 'home_fenwick_pct', 'home_pdo',
            'home_goals_for_pg', 'home_goals_against_pg',
            'home_shots_for_pg', 'home_takeaway_ratio',
            'away_corsi_pct', 'away_fenwick_pct', 'away_pdo',
            'away_goals_for_pg', 'away_goals_against_pg',
            'away_shots_for_pg', 'away_takeaway_ratio'
        ]
