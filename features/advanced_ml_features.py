"""Advanced ML Features for Overtime Prediction v3.0.

Comprehensive feature engineering with 100+ features for improved OT prediction.
Categories: momentum, matchup, situational, goalie_advanced, team_style, market.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from utils.logger import get_logger

logger = get_logger(__name__)


# NHL Team Data
NHL_TEAMS = {
    'ANA': {'division': 'Pacific', 'conference': 'Western', 'city': 'Anaheim'},
    'ARI': {'division': 'Central', 'conference': 'Western', 'city': 'Phoenix'},
    'BOS': {'division': 'Atlantic', 'conference': 'Eastern', 'city': 'Boston'},
    'BUF': {'division': 'Atlantic', 'conference': 'Eastern', 'city': 'Buffalo'},
    'CGY': {'division': 'Pacific', 'conference': 'Western', 'city': 'Calgary'},
    'CAR': {'division': 'Metropolitan', 'conference': 'Eastern', 'city': 'Raleigh'},
    'CHI': {'division': 'Central', 'conference': 'Western', 'city': 'Chicago'},
    'COL': {'division': 'Central', 'conference': 'Western', 'city': 'Denver'},
    'CBJ': {'division': 'Metropolitan', 'conference': 'Eastern', 'city': 'Columbus'},
    'DAL': {'division': 'Central', 'conference': 'Western', 'city': 'Dallas'},
    'DET': {'division': 'Atlantic', 'conference': 'Eastern', 'city': 'Detroit'},
    'EDM': {'division': 'Pacific', 'conference': 'Western', 'city': 'Edmonton'},
    'FLA': {'division': 'Atlantic', 'conference': 'Eastern', 'city': 'Miami'},
    'LAK': {'division': 'Pacific', 'conference': 'Western', 'city': 'Los Angeles'},
    'MIN': {'division': 'Central', 'conference': 'Western', 'city': 'Minneapolis'},
    'MTL': {'division': 'Atlantic', 'conference': 'Eastern', 'city': 'Montreal'},
    'NSH': {'division': 'Central', 'conference': 'Western', 'city': 'Nashville'},
    'NJD': {'division': 'Metropolitan', 'conference': 'Eastern', 'city': 'Newark'},
    'NYI': {'division': 'Metropolitan', 'conference': 'Eastern', 'city': 'New York'},
    'NYR': {'division': 'Metropolitan', 'conference': 'Eastern', 'city': 'New York'},
    'OTT': {'division': 'Atlantic', 'conference': 'Eastern', 'city': 'Ottawa'},
    'PHI': {'division': 'Metropolitan', 'conference': 'Eastern', 'city': 'Philadelphia'},
    'PIT': {'division': 'Metropolitan', 'conference': 'Eastern', 'city': 'Pittsburgh'},
    'SJS': {'division': 'Pacific', 'conference': 'Western', 'city': 'San Jose'},
    'SEA': {'division': 'Pacific', 'conference': 'Western', 'city': 'Seattle'},
    'STL': {'division': 'Central', 'conference': 'Western', 'city': 'St. Louis'},
    'TBL': {'division': 'Atlantic', 'conference': 'Eastern', 'city': 'Tampa'},
    'TOR': {'division': 'Atlantic', 'conference': 'Eastern', 'city': 'Toronto'},
    'VAN': {'division': 'Pacific', 'conference': 'Western', 'city': 'Vancouver'},
    'VGK': {'division': 'Pacific', 'conference': 'Western', 'city': 'Las Vegas'},
    'WSH': {'division': 'Metropolitan', 'conference': 'Eastern', 'city': 'Washington'},
    'WPG': {'division': 'Central', 'conference': 'Western', 'city': 'Winnipeg'},
    'UTA': {'division': 'Central', 'conference': 'Western', 'city': 'Salt Lake City'},
}


@dataclass
class TeamMLStats:
    """Extended team statistics for ML features."""
    team_id: str
    games_played: int = 0
    
    # Basic stats
    goals_for: float = 0.0
    goals_against: float = 0.0
    wins: int = 0
    losses: int = 0
    ot_wins: int = 0
    ot_losses: int = 0
    
    # Recent form (last 5, 10, 20 games)
    recent_5_wins: int = 0
    recent_5_goals_for: float = 0.0
    recent_5_goals_against: float = 0.0
    recent_10_wins: int = 0
    recent_10_goals_for: float = 0.0
    recent_10_goals_against: float = 0.0
    recent_20_wins: int = 0
    
    # OT specific stats
    ot_games: int = 0
    ot_win_rate: float = 0.5
    so_games: int = 0
    so_win_rate: float = 0.5
    
    # Special teams
    powerplay_pct: float = 0.20
    penalty_kill_pct: float = 0.80
    pp_opportunities_per_game: float = 3.0
    pk_opportunities_per_game: float = 3.0
    
    # Advanced stats
    corsi_for_pct: float = 50.0
    fenwick_for_pct: float = 50.0
    pdo: float = 100.0
    shots_for_per_game: float = 30.0
    shots_against_per_game: float = 30.0
    
    # Goalie stats
    goalie_sv_pct: float = 0.910
    goalie_gaa: float = 2.80
    goalie_games_last_7: int = 0
    backup_sv_pct: float = 0.900
    
    # Streaks
    current_win_streak: int = 0
    current_loss_streak: int = 0
    longest_win_streak: int = 0
    longest_loss_streak: int = 0
    
    # Home/Away splits
    home_wins: int = 0
    home_losses: int = 0
    away_wins: int = 0
    away_losses: int = 0
    home_goals_for_avg: float = 0.0
    away_goals_for_avg: float = 0.0
    
    # Rest and schedule
    rest_days: int = 1
    games_in_last_7_days: int = 0
    games_in_last_14_days: int = 0
    travel_distance_last_week: float = 0.0
    
    @property
    def win_rate(self) -> float:
        if self.games_played == 0:
            return 0.5
        return (self.wins + self.ot_wins) / self.games_played
    
    @property
    def goal_differential(self) -> float:
        return self.goals_for - self.goals_against
    
    @property
    def goals_per_game(self) -> float:
        if self.games_played == 0:
            return 3.0
        return self.goals_for / self.games_played
    
    @property
    def goals_against_per_game(self) -> float:
        if self.games_played == 0:
            return 3.0
        return self.goals_against / self.games_played
    
    @property
    def recent_form_5(self) -> float:
        return self.recent_5_wins / 5 if self.games_played >= 5 else 0.5
    
    @property
    def recent_form_10(self) -> float:
        return self.recent_10_wins / 10 if self.games_played >= 10 else 0.5
    
    @property
    def special_teams_index(self) -> float:
        return (self.powerplay_pct * 100 + self.penalty_kill_pct * 100) / 2


class AdvancedMLFeatures:
    """Advanced feature engineering for overtime prediction v3.0.
    
    Creates 100+ features across categories:
    - Momentum features (streaks, form)
    - Matchup features (H2H, division)
    - Situational features (rest, schedule, travel)
    - Goalie features (advanced goalie stats)
    - Team style features (offense/defense ratings, pace)
    - Market features (betting odds derived)
    """
    
    # Feature category definitions
    MOMENTUM_FEATURES = [
        'current_win_streak_home', 'current_loss_streak_home',
        'current_win_streak_away', 'current_loss_streak_away',
        'home_form_5', 'home_form_10', 'home_form_20',
        'away_form_5', 'away_form_10', 'away_form_20',
        'home_gd_momentum_5', 'home_gd_momentum_10',
        'away_gd_momentum_5', 'away_gd_momentum_10',
        'home_scoring_trend', 'away_scoring_trend',
        'home_defense_trend', 'away_defense_trend',
    ]
    
    MATCHUP_FEATURES = [
        'h2h_games_played', 'h2h_home_wins', 'h2h_away_wins',
        'h2h_ot_rate', 'h2h_avg_total_goals',
        'h2h_last_3_ot_rate', 'h2h_last_5_ot_rate',
        'h2h_home_goal_diff', 'h2h_scoring_avg',
        'is_division_game', 'is_conference_game',
        'division_rivalry_factor', 'strength_differential',
    ]
    
    SITUATIONAL_FEATURES = [
        'home_rest_days', 'away_rest_days', 'rest_advantage',
        'home_back_to_back', 'away_back_to_back',
        'home_games_last_7', 'away_games_last_7',
        'home_games_last_14', 'away_games_last_14',
        'away_travel_distance', 'travel_fatigue_factor',
        'season_progress', 'is_playoff_race', 'is_early_season',
        'is_weekend', 'day_of_week', 'is_prime_time',
        'home_schedule_difficulty', 'away_schedule_difficulty',
    ]
    
    GOALIE_FEATURES = [
        'home_goalie_sv_pct', 'away_goalie_sv_pct',
        'home_goalie_recent_sv_pct', 'away_goalie_recent_sv_pct',
        'home_goalie_gaa', 'away_goalie_gaa',
        'home_goalie_vs_opp', 'away_goalie_vs_opp',
        'home_goalie_workload', 'away_goalie_workload',
        'home_goalie_quality', 'away_goalie_quality',
        'goalie_quality_diff', 'goalie_fatigue_diff',
        'home_backup_risk', 'away_backup_risk',
    ]
    
    TEAM_STYLE_FEATURES = [
        'home_offensive_rating', 'away_offensive_rating',
        'home_defensive_rating', 'away_defensive_rating',
        'home_pace', 'away_pace', 'pace_matchup',
        'home_shot_quality', 'away_shot_quality',
        'home_corsi', 'away_corsi', 'corsi_diff',
        'home_fenwick', 'away_fenwick', 'fenwick_diff',
        'home_pdo', 'away_pdo', 'pdo_diff',
        'home_pp_effectiveness', 'away_pp_effectiveness',
        'home_pk_effectiveness', 'away_pk_effectiveness',
        'special_teams_diff', 'physical_play_diff',
    ]
    
    MARKET_FEATURES = [
        'home_implied_prob', 'away_implied_prob',
        'draw_implied_prob', 'market_competitiveness',
        'ot_implied_prob', 'total_line', 'total_line_vs_avg',
        'spread_line', 'market_efficiency',
        'odds_movement', 'line_value',
    ]
    
    def __init__(self, h2h_data: Dict = None, historical_data: Dict = None):
        """Initialize feature extractor.
        
        Args:
            h2h_data: Head-to-head historical data
            historical_data: General historical match data
        """
        self.h2h_data = h2h_data or {}
        self.historical_data = historical_data or {}
        self.feature_names = []
        self._build_feature_list()
    
    def _build_feature_list(self):
        """Build complete feature name list."""
        self.feature_names = (
            self.MOMENTUM_FEATURES +
            self.MATCHUP_FEATURES +
            self.SITUATIONAL_FEATURES +
            self.GOALIE_FEATURES +
            self.TEAM_STYLE_FEATURES +
            self.MARKET_FEATURES
        )
        logger.info(f"Built feature list with {len(self.feature_names)} features")
    
    def create_momentum_features(
        self,
        home_stats: TeamMLStats,
        away_stats: TeamMLStats
    ) -> Dict[str, float]:
        """Create momentum and streak features.
        
        Args:
            home_stats: Home team statistics
            away_stats: Away team statistics
            
        Returns:
            Dictionary of momentum features
        """
        features = {}
        
        # Win/loss streaks
        features['current_win_streak_home'] = float(home_stats.current_win_streak)
        features['current_loss_streak_home'] = float(home_stats.current_loss_streak)
        features['current_win_streak_away'] = float(away_stats.current_win_streak)
        features['current_loss_streak_away'] = float(away_stats.current_loss_streak)
        
        # Recent form (last 5, 10, 20 games)
        features['home_form_5'] = home_stats.recent_form_5
        features['home_form_10'] = home_stats.recent_form_10
        features['home_form_20'] = home_stats.recent_20_wins / 20 if home_stats.games_played >= 20 else 0.5
        features['away_form_5'] = away_stats.recent_form_5
        features['away_form_10'] = away_stats.recent_form_10
        features['away_form_20'] = away_stats.recent_20_wins / 20 if away_stats.games_played >= 20 else 0.5
        
        # Goal differential momentum
        if home_stats.games_played >= 5:
            home_gd_5 = home_stats.recent_5_goals_for - home_stats.recent_5_goals_against
        else:
            home_gd_5 = 0.0
        if home_stats.games_played >= 10:
            home_gd_10 = home_stats.recent_10_goals_for - home_stats.recent_10_goals_against
        else:
            home_gd_10 = 0.0
            
        features['home_gd_momentum_5'] = home_gd_5 / 5
        features['home_gd_momentum_10'] = home_gd_10 / 10
        
        if away_stats.games_played >= 5:
            away_gd_5 = away_stats.recent_5_goals_for - away_stats.recent_5_goals_against
        else:
            away_gd_5 = 0.0
        if away_stats.games_played >= 10:
            away_gd_10 = away_stats.recent_10_goals_for - away_stats.recent_10_goals_against
        else:
            away_gd_10 = 0.0
            
        features['away_gd_momentum_5'] = away_gd_5 / 5
        features['away_gd_momentum_10'] = away_gd_10 / 10
        
        # Scoring/defense trends
        features['home_scoring_trend'] = features['home_form_5'] - features['home_form_10']
        features['away_scoring_trend'] = features['away_form_5'] - features['away_form_10']
        features['home_defense_trend'] = features['home_gd_momentum_5'] - features['home_gd_momentum_10']
        features['away_defense_trend'] = features['away_gd_momentum_5'] - features['away_gd_momentum_10']
        
        return features
    
    def create_matchup_features(
        self,
        home_team: str,
        away_team: str,
        home_stats: TeamMLStats,
        away_stats: TeamMLStats
    ) -> Dict[str, float]:
        """Create head-to-head matchup features.
        
        Args:
            home_team: Home team ID
            away_team: Away team ID
            home_stats: Home team statistics
            away_stats: Away team statistics
            
        Returns:
            Dictionary of matchup features
        """
        features = {}
        
        # Get H2H data
        h2h_key = f"{home_team}_{away_team}"
        h2h = self.h2h_data.get(h2h_key, {})
        
        # Historical matchup stats
        features['h2h_games_played'] = float(h2h.get('games_played', 0))
        features['h2h_home_wins'] = float(h2h.get('home_wins', 0))
        features['h2h_away_wins'] = float(h2h.get('away_wins', 0))
        features['h2h_ot_rate'] = h2h.get('ot_rate', 0.25)
        features['h2h_avg_total_goals'] = h2h.get('avg_total_goals', 5.5)
        
        # Recent matchup trends
        features['h2h_last_3_ot_rate'] = h2h.get('last_3_ot_rate', 0.25)
        features['h2h_last_5_ot_rate'] = h2h.get('last_5_ot_rate', 0.25)
        
        # Goal differentials in H2H
        features['h2h_home_goal_diff'] = h2h.get('home_goal_diff', 0.0)
        features['h2h_scoring_avg'] = h2h.get('scoring_avg', 5.5)
        
        # Division/Conference matchup
        home_info = NHL_TEAMS.get(home_team, {})
        away_info = NHL_TEAMS.get(away_team, {})
        
        is_division = home_info.get('division') == away_info.get('division')
        is_conference = home_info.get('conference') == away_info.get('conference')
        
        features['is_division_game'] = 1.0 if is_division else 0.0
        features['is_conference_game'] = 1.0 if is_conference else 0.0
        
        # Rivalry factor (division games tend to be closer)
        features['division_rivalry_factor'] = 1.2 if is_division else (1.1 if is_conference else 1.0)
        
        # Strength differential
        features['strength_differential'] = abs(home_stats.win_rate - away_stats.win_rate)
        
        return features
    
    def create_situational_features(
        self,
        home_stats: TeamMLStats,
        away_stats: TeamMLStats,
        game_date: datetime = None,
        season_start: datetime = None
    ) -> Dict[str, float]:
        """Create situational and contextual features.
        
        Args:
            home_stats: Home team statistics
            away_stats: Away team statistics
            game_date: Date of the game
            season_start: Season start date
            
        Returns:
            Dictionary of situational features
        """
        features = {}
        
        if game_date is None:
            game_date = datetime.now()
        if season_start is None:
            season_start = datetime(game_date.year if game_date.month >= 10 else game_date.year - 1, 10, 1)
        
        # Rest days
        features['home_rest_days'] = float(min(home_stats.rest_days, 7))
        features['away_rest_days'] = float(min(away_stats.rest_days, 7))
        features['rest_advantage'] = features['home_rest_days'] - features['away_rest_days']
        
        # Back-to-back games
        features['home_back_to_back'] = 1.0 if home_stats.rest_days == 0 else 0.0
        features['away_back_to_back'] = 1.0 if away_stats.rest_days == 0 else 0.0
        
        # Games in recent period
        features['home_games_last_7'] = float(home_stats.games_in_last_7_days)
        features['away_games_last_7'] = float(away_stats.games_in_last_7_days)
        features['home_games_last_14'] = float(home_stats.games_in_last_14_days)
        features['away_games_last_14'] = float(away_stats.games_in_last_14_days)
        
        # Travel
        features['away_travel_distance'] = away_stats.travel_distance_last_week / 1000  # Normalize to 1000km
        features['travel_fatigue_factor'] = (
            features['away_travel_distance'] * 0.3 +
            features['away_games_last_7'] * 0.2 +
            (1.0 - features['away_rest_days'] / 7) * 0.5
        )
        
        # Season progress
        days_into_season = (game_date - season_start).days
        season_length = 210  # Approximate NHL regular season
        features['season_progress'] = min(days_into_season / season_length, 1.0)
        features['is_playoff_race'] = 1.0 if features['season_progress'] > 0.75 else 0.0
        features['is_early_season'] = 1.0 if features['season_progress'] < 0.15 else 0.0
        
        # Day of week
        features['is_weekend'] = 1.0 if game_date.weekday() >= 5 else 0.0
        features['day_of_week'] = float(game_date.weekday())
        features['is_prime_time'] = 1.0 if game_date.weekday() in [5, 6] else 0.0
        
        # Schedule difficulty (simplified)
        features['home_schedule_difficulty'] = home_stats.games_in_last_14_days / 7.0
        features['away_schedule_difficulty'] = away_stats.games_in_last_14_days / 7.0
        
        return features
    
    def create_goalie_features(
        self,
        home_stats: TeamMLStats,
        away_stats: TeamMLStats,
        home_goalie_vs_opp: float = None,
        away_goalie_vs_opp: float = None
    ) -> Dict[str, float]:
        """Create advanced goalie performance features.
        
        Args:
            home_stats: Home team statistics
            away_stats: Away team statistics
            home_goalie_vs_opp: Home goalie SV% vs opponent
            away_goalie_vs_opp: Away goalie SV% vs opponent
            
        Returns:
            Dictionary of goalie features
        """
        features = {}
        
        # Basic goalie stats
        features['home_goalie_sv_pct'] = home_stats.goalie_sv_pct
        features['away_goalie_sv_pct'] = away_stats.goalie_sv_pct
        
        # Recent performance (last 5 starts)
        # Estimate from overall if not available
        features['home_goalie_recent_sv_pct'] = home_stats.goalie_sv_pct * 0.95 + 0.05 * np.random.uniform(0.88, 0.94)
        features['away_goalie_recent_sv_pct'] = away_stats.goalie_sv_pct * 0.95 + 0.05 * np.random.uniform(0.88, 0.94)
        
        # Goals against average
        features['home_goalie_gaa'] = home_stats.goalie_gaa
        features['away_goalie_gaa'] = away_stats.goalie_gaa
        
        # Goalie vs opponent
        features['home_goalie_vs_opp'] = home_goalie_vs_opp if home_goalie_vs_opp else home_stats.goalie_sv_pct
        features['away_goalie_vs_opp'] = away_goalie_vs_opp if away_goalie_vs_opp else away_stats.goalie_sv_pct
        
        # Goalie workload
        features['home_goalie_workload'] = float(home_stats.goalie_games_last_7)
        features['away_goalie_workload'] = float(away_stats.goalie_games_last_7)
        
        # Goalie quality score (composite)
        home_quality = (
            (home_stats.goalie_sv_pct - 0.88) * 50 +  # SV% contribution
            (3.5 - home_stats.goalie_gaa) * 10         # GAA contribution
        )
        away_quality = (
            (away_stats.goalie_sv_pct - 0.88) * 50 +
            (3.5 - away_stats.goalie_gaa) * 10
        )
        
        features['home_goalie_quality'] = max(0, min(10, home_quality))
        features['away_goalie_quality'] = max(0, min(10, away_quality))
        features['goalie_quality_diff'] = features['home_goalie_quality'] - features['away_goalie_quality']
        
        # Fatigue differential
        features['goalie_fatigue_diff'] = features['home_goalie_workload'] - features['away_goalie_workload']
        
        # Backup risk (high workload = risk of backup starting)
        features['home_backup_risk'] = 1.0 if home_stats.goalie_games_last_7 >= 4 else 0.0
        features['away_backup_risk'] = 1.0 if away_stats.goalie_games_last_7 >= 4 else 0.0
        
        return features
    
    def create_team_style_features(
        self,
        home_stats: TeamMLStats,
        away_stats: TeamMLStats
    ) -> Dict[str, float]:
        """Create team playing style features.
        
        Args:
            home_stats: Home team statistics
            away_stats: Away team statistics
            
        Returns:
            Dictionary of team style features
        """
        features = {}
        
        # Offensive/Defensive ratings
        features['home_offensive_rating'] = home_stats.goals_per_game / 3.0  # Normalized
        features['away_offensive_rating'] = away_stats.goals_per_game / 3.0
        features['home_defensive_rating'] = 1.0 - (home_stats.goals_against_per_game / 4.0)
        features['away_defensive_rating'] = 1.0 - (away_stats.goals_against_per_game / 4.0)
        
        # Pace of play
        home_pace = (home_stats.shots_for_per_game + home_stats.shots_against_per_game) / 60
        away_pace = (away_stats.shots_for_per_game + away_stats.shots_against_per_game) / 60
        features['home_pace'] = home_pace
        features['away_pace'] = away_pace
        features['pace_matchup'] = (home_pace + away_pace) / 2
        
        # Shot quality (simplified)
        features['home_shot_quality'] = home_stats.goals_per_game / max(home_stats.shots_for_per_game, 1) * 100
        features['away_shot_quality'] = away_stats.goals_per_game / max(away_stats.shots_for_per_game, 1) * 100
        
        # Advanced possession metrics
        features['home_corsi'] = home_stats.corsi_for_pct
        features['away_corsi'] = away_stats.corsi_for_pct
        features['corsi_diff'] = home_stats.corsi_for_pct - away_stats.corsi_for_pct
        
        features['home_fenwick'] = home_stats.fenwick_for_pct
        features['away_fenwick'] = away_stats.fenwick_for_pct
        features['fenwick_diff'] = home_stats.fenwick_for_pct - away_stats.fenwick_for_pct
        
        # PDO (luck indicator)
        features['home_pdo'] = home_stats.pdo
        features['away_pdo'] = away_stats.pdo
        features['pdo_diff'] = home_stats.pdo - away_stats.pdo
        
        # Special teams
        features['home_pp_effectiveness'] = home_stats.powerplay_pct
        features['away_pp_effectiveness'] = away_stats.powerplay_pct
        features['home_pk_effectiveness'] = home_stats.penalty_kill_pct
        features['away_pk_effectiveness'] = away_stats.penalty_kill_pct
        
        features['special_teams_diff'] = (
            (home_stats.special_teams_index - away_stats.special_teams_index) / 100
        )
        
        # Physical play differential (simplified)
        features['physical_play_diff'] = 0.0  # Would need hit/block data
        
        return features
    
    def create_market_features(
        self,
        home_odds: float = None,
        away_odds: float = None,
        draw_odds: float = None,
        total_line: float = None,
        spread_line: float = None
    ) -> Dict[str, float]:
        """Create betting market-derived features.
        
        Args:
            home_odds: Home team decimal odds
            away_odds: Away team decimal odds
            draw_odds: Draw decimal odds (for regulation)
            total_line: Over/under total goals line
            spread_line: Spread/handicap line
            
        Returns:
            Dictionary of market features
        """
        features = {}
        
        if home_odds and away_odds:
            # Implied probabilities (removing vig)
            home_implied = 1 / home_odds
            away_implied = 1 / away_odds
            total_implied = home_implied + away_implied
            
            # Normalize to remove vig
            features['home_implied_prob'] = home_implied / total_implied
            features['away_implied_prob'] = away_implied / total_implied
            
            # Draw probability (if available)
            if draw_odds:
                draw_implied = 1 / draw_odds
                total_3way = home_implied + away_implied + draw_implied
                features['draw_implied_prob'] = draw_implied / total_3way
            else:
                features['draw_implied_prob'] = 0.25  # Default for hockey
            
            # Market competitiveness (closer = more likely OT)
            features['market_competitiveness'] = 1.0 - abs(features['home_implied_prob'] - features['away_implied_prob'])
            
            # OT implied probability (from draw or estimated)
            features['ot_implied_prob'] = features['draw_implied_prob'] * 0.8  # Rough estimate
            
        else:
            features['home_implied_prob'] = 0.5
            features['away_implied_prob'] = 0.5
            features['draw_implied_prob'] = 0.25
            features['market_competitiveness'] = 0.5
            features['ot_implied_prob'] = 0.25
        
        # Total line features
        if total_line:
            features['total_line'] = total_line
            features['total_line_vs_avg'] = total_line - 5.5  # NHL average ~5.5
        else:
            features['total_line'] = 5.5
            features['total_line_vs_avg'] = 0.0
        
        # Spread features
        if spread_line:
            features['spread_line'] = spread_line
        else:
            features['spread_line'] = 0.0
        
        # Market efficiency indicator
        features['market_efficiency'] = features['market_competitiveness'] * 0.8
        
        # Odds movement (would need historical - placeholder)
        features['odds_movement'] = 0.0
        
        # Line value
        features['line_value'] = abs(features['total_line_vs_avg']) * 0.1
        
        return features
    
    def create_all_features(
        self,
        home_team: str,
        away_team: str,
        home_stats: TeamMLStats,
        away_stats: TeamMLStats,
        game_date: datetime = None,
        home_odds: float = None,
        away_odds: float = None,
        draw_odds: float = None,
        total_line: float = None,
        spread_line: float = None
    ) -> Dict[str, float]:
        """Create all advanced features for a match.
        
        Args:
            home_team: Home team ID
            away_team: Away team ID
            home_stats: Home team statistics
            away_stats: Away team statistics
            game_date: Date of the game
            home_odds: Home team decimal odds
            away_odds: Away team decimal odds
            draw_odds: Draw decimal odds
            total_line: Over/under total goals line
            spread_line: Spread/handicap line
            
        Returns:
            Dictionary with all features
        """
        all_features = {}
        
        # Create all feature categories
        all_features.update(self.create_momentum_features(home_stats, away_stats))
        all_features.update(self.create_matchup_features(home_team, away_team, home_stats, away_stats))
        all_features.update(self.create_situational_features(home_stats, away_stats, game_date))
        all_features.update(self.create_goalie_features(home_stats, away_stats))
        all_features.update(self.create_team_style_features(home_stats, away_stats))
        all_features.update(self.create_market_features(home_odds, away_odds, draw_odds, total_line, spread_line))
        
        logger.debug(f"Created {len(all_features)} features for {home_team} vs {away_team}")
        
        return all_features
    
    def features_to_array(self, features: Dict[str, float]) -> np.ndarray:
        """Convert feature dictionary to numpy array.
        
        Args:
            features: Feature dictionary
            
        Returns:
            Numpy array of features in consistent order
        """
        return np.array([features.get(name, 0.0) for name in self.feature_names])
    
    def get_feature_importance_names(self) -> List[str]:
        """Get ordered list of feature names."""
        return self.feature_names.copy()
    
    @staticmethod
    def generate_synthetic_stats(
        team_id: str,
        strength: float = 0.5,
        variance: float = 0.1
    ) -> TeamMLStats:
        """Generate synthetic team stats for testing.
        
        Args:
            team_id: Team identifier
            strength: Base strength (0-1)
            variance: Random variance
            
        Returns:
            TeamMLStats with synthetic data
        """
        np.random.seed(hash(team_id) % (2**32))
        
        games = np.random.randint(40, 82)
        win_rate = np.clip(strength + np.random.normal(0, variance), 0.2, 0.8)
        wins = int(games * win_rate)
        
        return TeamMLStats(
            team_id=team_id,
            games_played=games,
            goals_for=games * (2.5 + win_rate * 1.5 + np.random.normal(0, 0.2)),
            goals_against=games * (3.5 - win_rate * 1.5 + np.random.normal(0, 0.2)),
            wins=wins,
            losses=games - wins - np.random.randint(0, 10),
            ot_wins=np.random.randint(2, 12),
            ot_losses=np.random.randint(2, 10),
            recent_5_wins=np.random.randint(1, 5),
            recent_5_goals_for=np.random.uniform(10, 20),
            recent_5_goals_against=np.random.uniform(8, 18),
            recent_10_wins=np.random.randint(3, 8),
            recent_10_goals_for=np.random.uniform(20, 40),
            recent_10_goals_against=np.random.uniform(18, 35),
            recent_20_wins=np.random.randint(8, 15),
            ot_games=np.random.randint(8, 20),
            ot_win_rate=np.random.uniform(0.35, 0.65),
            so_games=np.random.randint(3, 10),
            so_win_rate=np.random.uniform(0.4, 0.6),
            powerplay_pct=np.random.uniform(0.15, 0.28),
            penalty_kill_pct=np.random.uniform(0.75, 0.88),
            corsi_for_pct=np.random.uniform(46, 55),
            fenwick_for_pct=np.random.uniform(46, 55),
            pdo=np.random.uniform(97, 103),
            shots_for_per_game=np.random.uniform(28, 35),
            shots_against_per_game=np.random.uniform(27, 34),
            goalie_sv_pct=np.random.uniform(0.900, 0.925),
            goalie_gaa=np.random.uniform(2.4, 3.2),
            goalie_games_last_7=np.random.randint(1, 5),
            current_win_streak=np.random.choice([0, 0, 0, 1, 2, 3, 4, 5]),
            current_loss_streak=np.random.choice([0, 0, 0, 1, 2, 3]),
            rest_days=np.random.choice([0, 1, 1, 2, 2, 3]),
            games_in_last_7_days=np.random.randint(2, 5),
            games_in_last_14_days=np.random.randint(5, 9),
        )


class FeatureSelector:
    """Advanced feature selection for ML models."""
    
    def __init__(self, X: np.ndarray, y: np.ndarray, feature_names: List[str]):
        """Initialize feature selector.
        
        Args:
            X: Feature matrix
            y: Labels
            feature_names: List of feature names
        """
        self.X = X
        self.y = y
        self.feature_names = feature_names
        self.selected_features = None
        self.feature_scores = None
    
    def select_by_importance(self, threshold: float = 0.01) -> List[str]:
        """Select features by importance threshold.
        
        Args:
            threshold: Minimum importance threshold
            
        Returns:
            List of selected feature names
        """
        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.feature_selection import SelectFromModel
            
            rf = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
            rf.fit(self.X, self.y)
            
            self.feature_scores = dict(zip(self.feature_names, rf.feature_importances_))
            
            selector = SelectFromModel(rf, threshold=threshold, prefit=True)
            selected_mask = selector.get_support()
            
            self.selected_features = [
                name for name, selected in zip(self.feature_names, selected_mask)
                if selected
            ]
            
            logger.info(f"Selected {len(self.selected_features)} features out of {len(self.feature_names)}")
            return self.selected_features
            
        except ImportError:
            logger.warning("sklearn not available for feature selection")
            return self.feature_names
    
    def select_by_rfe(self, n_features: int = 50) -> List[str]:
        """Select features using Recursive Feature Elimination.
        
        Args:
            n_features: Number of features to select
            
        Returns:
            List of selected feature names
        """
        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.feature_selection import RFE
            
            rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
            rfe = RFE(estimator=rf, n_features_to_select=n_features, step=5)
            rfe.fit(self.X, self.y)
            
            selected_mask = rfe.support_
            self.selected_features = [
                name for name, selected in zip(self.feature_names, selected_mask)
                if selected
            ]
            
            logger.info(f"RFE selected {len(self.selected_features)} features")
            return self.selected_features
            
        except ImportError:
            logger.warning("sklearn not available for RFE")
            return self.feature_names[:n_features]
    
    def get_top_features(self, n: int = 20) -> List[Tuple[str, float]]:
        """Get top N features by importance.
        
        Args:
            n: Number of top features
            
        Returns:
            List of (feature_name, importance) tuples
        """
        if self.feature_scores is None:
            self.select_by_importance()
        
        sorted_features = sorted(
            self.feature_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_features[:n]
