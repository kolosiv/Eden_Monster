"""Player Features Module.

Extracts goalie, player, and injury-related features for ML models.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import numpy as np

from data_collector.player_stats import (
    PlayerStatsCollector, GoalieStats, PlayerStats, InjuryInfo
)
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class GoalieFeatures:
    """Features extracted from goalie statistics."""
    starter_sv_pct: float = 0.91
    starter_gaa: float = 2.8
    starter_wins: int = 0
    starter_games: int = 0
    backup_sv_pct: float = 0.88
    backup_gaa: float = 3.2
    goalie_form_last5: float = 0.91  # SV% last 5 games
    goalie_vs_opponent: float = 0.91  # SV% vs this opponent
    days_since_last_game: int = 2
    goalie_quality_score: float = 50.0  # 0-100 rating


@dataclass
class PlayerFeatures:
    """Features extracted from player statistics."""
    top_scorer_available: bool = True
    top_defender_available: bool = True
    top6_total_points: int = 0
    top6_ppg: float = 0.0
    top4_plus_minus: int = 0
    top4_toi_avg: float = 20.0
    offensive_power_score: float = 50.0  # 0-100
    defensive_power_score: float = 50.0  # 0-100


@dataclass
class InjuryFeatures:
    """Features extracted from injury data."""
    num_injuries: int = 0
    key_players_out: int = 0
    total_points_lost: float = 0.0
    injury_severity_score: float = 0.0  # 0-1
    goalie_injured: bool = False
    top_scorer_injured: bool = False


class PlayerFeatureExtractor:
    """Extracts player-related features for ML models.
    
    Features include:
    - Goalie quality and form
    - Top scorer availability
    - Team offensive/defensive power
    - Injury impact
    
    Example:
        >>> extractor = PlayerFeatureExtractor()
        >>> features = extractor.extract_all("TOR", "BOS", "20232024")
    """
    
    def __init__(self, player_collector: Optional[PlayerStatsCollector] = None):
        """Initialize player feature extractor.
        
        Args:
            player_collector: Optional PlayerStatsCollector instance
        """
        self.collector = player_collector or PlayerStatsCollector()
    
    def extract_goalie_features(
        self,
        team_abbrev: str,
        opponent_abbrev: str = None,
        season: str = None
    ) -> GoalieFeatures:
        """Extract goalie-related features.
        
        Args:
            team_abbrev: Team abbreviation
            opponent_abbrev: Opponent for matchup analysis
            season: Season string
            
        Returns:
            GoalieFeatures
        """
        goalies = self.collector.fetch_team_goalies(team_abbrev, season)
        
        if not goalies:
            logger.warning(f"No goalie data for {team_abbrev}")
            return GoalieFeatures()
        
        starter = goalies[0]
        backup = goalies[1] if len(goalies) > 1 else None
        
        # Calculate goalie quality score (0-100)
        quality_score = self._calculate_goalie_quality(starter)
        
        features = GoalieFeatures(
            starter_sv_pct=starter.save_percentage,
            starter_gaa=starter.goals_against_average,
            starter_wins=starter.wins,
            starter_games=starter.games_played,
            backup_sv_pct=backup.save_percentage if backup else 0.88,
            backup_gaa=backup.goals_against_average if backup else 3.2,
            goalie_form_last5=starter.last_5_sv_pct if starter.last_5_sv_pct > 0 else starter.save_percentage,
            goalie_vs_opponent=starter.save_percentage,  # Placeholder for matchup data
            days_since_last_game=starter.days_since_last_game,
            goalie_quality_score=quality_score
        )
        
        return features
    
    def _calculate_goalie_quality(self, goalie: GoalieStats) -> float:
        """Calculate overall goalie quality score (0-100)."""
        if not goalie or goalie.games_played < 5:
            return 50.0
        
        # Normalize save percentage (0.88-0.94 -> 0-100)
        sv_score = (goalie.save_percentage - 0.88) / 0.06 * 100
        sv_score = min(max(sv_score, 0), 100)
        
        # Normalize GAA (4.0-2.0 -> 0-100)
        gaa_score = (4.0 - goalie.goals_against_average) / 2.0 * 100
        gaa_score = min(max(gaa_score, 0), 100)
        
        # Win rate
        total_decisions = goalie.wins + goalie.losses
        win_rate = goalie.wins / total_decisions if total_decisions > 0 else 0.5
        win_score = win_rate * 100
        
        # Weighted average
        quality = sv_score * 0.5 + gaa_score * 0.3 + win_score * 0.2
        
        return min(max(quality, 0), 100)
    
    def extract_player_features(
        self,
        team_abbrev: str,
        season: str = None
    ) -> PlayerFeatures:
        """Extract player-related features.
        
        Args:
            team_abbrev: Team abbreviation
            season: Season string
            
        Returns:
            PlayerFeatures
        """
        offensive_power = self.collector.get_team_offensive_power(team_abbrev, season)
        defensive_power = self.collector.get_team_defensive_power(team_abbrev, season)
        injuries = self.collector.calculate_team_injury_impact(team_abbrev, season)
        
        # Calculate scores
        offensive_score = self._calculate_offensive_score(offensive_power)
        defensive_score = self._calculate_defensive_score(defensive_power)
        
        features = PlayerFeatures(
            top_scorer_available=injuries.get('key_players_out', 0) == 0,
            top_defender_available=True,  # Would need injury data
            top6_total_points=offensive_power.get('top6_points', 0),
            top6_ppg=offensive_power.get('top6_ppg', 0.0),
            top4_plus_minus=defensive_power.get('top4_plus_minus', 0),
            top4_toi_avg=defensive_power.get('top4_toi_avg', 20.0),
            offensive_power_score=offensive_score,
            defensive_power_score=defensive_score
        )
        
        return features
    
    def _calculate_offensive_score(self, power_data: Dict) -> float:
        """Calculate offensive power score (0-100)."""
        ppg = power_data.get('top6_ppg', 0.5)
        shooting = power_data.get('top6_shooting_pct', 10.0)
        
        # PPG score (0.3-1.2 -> 0-100)
        ppg_score = (ppg - 0.3) / 0.9 * 100
        ppg_score = min(max(ppg_score, 0), 100)
        
        # Shooting score (6-16 -> 0-100)
        shoot_score = (shooting - 6) / 10 * 100
        shoot_score = min(max(shoot_score, 0), 100)
        
        return ppg_score * 0.7 + shoot_score * 0.3
    
    def _calculate_defensive_score(self, power_data: Dict) -> float:
        """Calculate defensive power score (0-100)."""
        pm = power_data.get('top4_plus_minus', 0)
        toi = power_data.get('top4_toi_avg', 20.0)
        
        # Plus/minus score (-20 to +20 -> 0-100)
        pm_score = (pm + 20) / 40 * 100
        pm_score = min(max(pm_score, 0), 100)
        
        # TOI score (15-28 -> 0-100)
        toi_score = (toi - 15) / 13 * 100
        toi_score = min(max(toi_score, 0), 100)
        
        return pm_score * 0.6 + toi_score * 0.4
    
    def extract_injury_features(
        self,
        team_abbrev: str,
        season: str = None
    ) -> InjuryFeatures:
        """Extract injury-related features.
        
        Args:
            team_abbrev: Team abbreviation
            season: Season string
            
        Returns:
            InjuryFeatures
        """
        injuries = self.collector.fetch_team_injuries(team_abbrev)
        impact = self.collector.calculate_team_injury_impact(team_abbrev, season)
        
        # Calculate severity (0-1)
        severity = min(impact.get('impact_score', 0), 1.0)
        
        # Check for goalie/star injuries
        goalie_injured = any(
            i.position == 'G' for i in injuries
        ) if injuries else False
        
        top_scorer_injured = any(
            i.impact_score > 0.8 and i.position in ('C', 'LW', 'RW')
            for i in injuries
        ) if injuries else False
        
        return InjuryFeatures(
            num_injuries=impact.get('total_injuries', 0),
            key_players_out=impact.get('key_players_out', 0),
            total_points_lost=impact.get('total_points_lost', 0.0),
            injury_severity_score=severity,
            goalie_injured=goalie_injured,
            top_scorer_injured=top_scorer_injured
        )
    
    def extract_all(
        self,
        home_team: str,
        away_team: str,
        season: str = None
    ) -> Dict[str, float]:
        """Extract all player features for a match.
        
        Args:
            home_team: Home team abbreviation
            away_team: Away team abbreviation
            season: Season string
            
        Returns:
            Dict of feature name to value
        """
        # Home team features
        home_goalie = self.extract_goalie_features(home_team, away_team, season)
        home_player = self.extract_player_features(home_team, season)
        home_injury = self.extract_injury_features(home_team, season)
        
        # Away team features
        away_goalie = self.extract_goalie_features(away_team, home_team, season)
        away_player = self.extract_player_features(away_team, season)
        away_injury = self.extract_injury_features(away_team, season)
        
        features = {
            # Home goalie features
            'home_goalie_sv_pct': home_goalie.starter_sv_pct,
            'home_goalie_gaa': home_goalie.starter_gaa,
            'home_goalie_form': home_goalie.goalie_form_last5,
            'home_goalie_quality': home_goalie.goalie_quality_score,
            'home_backup_sv_pct': home_goalie.backup_sv_pct,
            
            # Away goalie features
            'away_goalie_sv_pct': away_goalie.starter_sv_pct,
            'away_goalie_gaa': away_goalie.starter_gaa,
            'away_goalie_form': away_goalie.goalie_form_last5,
            'away_goalie_quality': away_goalie.goalie_quality_score,
            'away_backup_sv_pct': away_goalie.backup_sv_pct,
            
            # Goalie differentials
            'goalie_sv_pct_diff': home_goalie.starter_sv_pct - away_goalie.starter_sv_pct,
            'goalie_quality_diff': home_goalie.goalie_quality_score - away_goalie.goalie_quality_score,
            
            # Home player features
            'home_offensive_power': home_player.offensive_power_score,
            'home_defensive_power': home_player.defensive_power_score,
            'home_top6_ppg': home_player.top6_ppg,
            'home_top4_pm': home_player.top4_plus_minus,
            
            # Away player features
            'away_offensive_power': away_player.offensive_power_score,
            'away_defensive_power': away_player.defensive_power_score,
            'away_top6_ppg': away_player.top6_ppg,
            'away_top4_pm': away_player.top4_plus_minus,
            
            # Power differentials
            'offensive_power_diff': home_player.offensive_power_score - away_player.offensive_power_score,
            'defensive_power_diff': home_player.defensive_power_score - away_player.defensive_power_score,
            
            # Injury features
            'home_injuries': home_injury.num_injuries,
            'home_injury_severity': home_injury.injury_severity_score,
            'away_injuries': away_injury.num_injuries,
            'away_injury_severity': away_injury.injury_severity_score,
            'injury_advantage': away_injury.injury_severity_score - home_injury.injury_severity_score,
            
            # Key player availability (binary)
            'home_stars_available': 1 if not home_injury.top_scorer_injured else 0,
            'away_stars_available': 1 if not away_injury.top_scorer_injured else 0
        }
        
        return features
    
    def get_feature_names(self) -> List[str]:
        """Get list of all feature names."""
        return [
            'home_goalie_sv_pct', 'home_goalie_gaa', 'home_goalie_form',
            'home_goalie_quality', 'home_backup_sv_pct',
            'away_goalie_sv_pct', 'away_goalie_gaa', 'away_goalie_form',
            'away_goalie_quality', 'away_backup_sv_pct',
            'goalie_sv_pct_diff', 'goalie_quality_diff',
            'home_offensive_power', 'home_defensive_power',
            'home_top6_ppg', 'home_top4_pm',
            'away_offensive_power', 'away_defensive_power',
            'away_top6_ppg', 'away_top4_pm',
            'offensive_power_diff', 'defensive_power_diff',
            'home_injuries', 'home_injury_severity',
            'away_injuries', 'away_injury_severity',
            'injury_advantage', 'home_stars_available', 'away_stars_available'
        ]
