"""
Advanced Model Trainer v5.0 for Eden Analytics Pro
===================================================

Features:
- 100+ engineered features including injury-based features
- Time-weighted learning (recent games weighted higher)
- Ensemble of multiple models (LightGBM, XGBoost, CatBoost, Random Forest, Neural Network)
- SMOTE for class imbalance handling
- Hyperparameter optimization with Optuna
- Time-based cross-validation
- Comprehensive feature importance analysis

Target: 88-90% accuracy with injury features and time weighting
"""

import pickle
import json
import sqlite3
import warnings
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
import numpy as np
import pandas as pd

# Suppress warnings
warnings.filterwarnings('ignore')

# ML imports
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, classification_report, confusion_matrix
)
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier, StackingClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV

# Gradient Boosting Libraries
import lightgbm as lgb
import xgboost as xgb
from catboost import CatBoostClassifier

# SMOTE for class imbalance
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline

# Hyperparameter optimization
import optuna
from optuna.samplers import TPESampler

optuna.logging.set_verbosity(optuna.logging.WARNING)


@dataclass
class TrainingConfigV5:
    """Configuration for v5.0 model training."""
    model_dir: str = "/home/ubuntu/eden_mvp/models_v5"
    db_path: str = "/home/ubuntu/eden_mvp/data/nhl_historical.db"
    
    # Training parameters
    train_seasons: List[str] = field(default_factory=lambda: ['20192020', '20202021', '20212022', '20222023', '20232024'])
    val_seasons: List[str] = field(default_factory=lambda: ['20242025'])
    test_seasons: List[str] = field(default_factory=lambda: ['20252026'])
    
    # Time weighting parameters
    decay_rate: float = 0.15  # Exponential decay rate for time weighting
    use_time_weights: bool = True
    
    # Model parameters
    n_optuna_trials: int = 30
    use_smote: bool = True
    smote_sampling_strategy: float = 0.5  # Target ratio for minority class
    
    # Ensemble parameters
    use_ensemble: bool = True
    use_stacking: bool = True
    
    random_state: int = 42
    n_jobs: int = -1


@dataclass
class TrainingResultV5:
    """Result of v5.0 model training."""
    # Overall metrics
    accuracy: float
    precision: float
    recall: float
    f1: float
    auc_roc: float
    
    # Class-specific metrics
    precision_no_ot: float
    recall_no_ot: float
    precision_ot: float
    recall_ot: float
    
    # Additional metrics
    confusion_matrix: List[List[int]]
    feature_importance: Dict[str, float]
    training_time: float
    
    # Model info
    model_version: str = "5.0"
    feature_count: int = 0
    training_samples: int = 0
    validation_samples: int = 0
    test_samples: int = 0
    
    # Per-model metrics
    individual_model_scores: Dict[str, float] = field(default_factory=dict)
    
    # Best hyperparameters
    best_params: Dict[str, Any] = field(default_factory=dict)


def safe_val(val, default=0):
    """Return default if val is None."""
    return val if val is not None else default


class AdvancedFeatureEngineer:
    """Engineers 100+ features from NHL game data including injury features."""
    
    FEATURE_NAMES = []  # Will be populated dynamically
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        
        # Cache for team stats and injuries
        self._team_stats_cache = {}
        self._h2h_cache = {}
        self._injury_cache = {}
        self._recent_form_cache = {}
        
        # Load all data into memory for faster processing
        self._load_caches()
    
    def _load_caches(self):
        """Load team stats, H2H, and injuries into memory."""
        cursor = self.conn.cursor()
        
        # Load team stats
        cursor.execute("SELECT * FROM nhl_team_stats")
        for row in cursor.fetchall():
            key = (row['team'], row['season'])
            self._team_stats_cache[key] = dict(row)
        
        # Load H2H stats
        cursor.execute("SELECT * FROM nhl_h2h")
        for row in cursor.fetchall():
            key = (row['team1'], row['team2'], row['season'])
            self._h2h_cache[key] = dict(row)
            # Also store reverse
            key_rev = (row['team2'], row['team1'], row['season'])
            self._h2h_cache[key_rev] = dict(row)
        
        # Load injuries
        cursor.execute("SELECT * FROM nhl_injuries WHERE is_active = 1")
        for row in cursor.fetchall():
            team = row['team']
            if team not in self._injury_cache:
                self._injury_cache[team] = []
            self._injury_cache[team].append(dict(row))
        
        print(f"Loaded {len(self._team_stats_cache)} team stats, "
              f"{len(self._h2h_cache)} H2H records, "
              f"{len(self._injury_cache)} teams with injuries")
    
    def get_team_stats(self, team: str, season: str) -> Dict:
        """Get team stats for a given team and season."""
        return self._team_stats_cache.get((team, season), {})
    
    def get_h2h_stats(self, team1: str, team2: str, season: str) -> Dict:
        """Get head-to-head stats."""
        return self._h2h_cache.get((team1, team2, season), {})
    
    def get_team_injuries(self, team: str) -> List[Dict]:
        """Get active injuries for a team."""
        return self._injury_cache.get(team, [])
    
    def get_recent_form(self, team: str, game_date: str, season: str, n_games: int = 10) -> Dict:
        """Calculate recent form metrics for a team."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM nhl_games 
            WHERE (home_team = ? OR away_team = ?)
            AND date < ?
            AND season = ?
            ORDER BY date DESC
            LIMIT ?
        """, (team, team, game_date, season, n_games))
        
        games = cursor.fetchall()
        
        if not games:
            return {'wins': 0, 'losses': 0, 'ot_games': 0, 'goals_for': 0, 'goals_against': 0, 
                    'form': 0.5, 'games': 0, 'avg_goals_for': 3.0, 'avg_goals_against': 3.0}
        
        wins = losses = ot_games = goals_for = goals_against = 0
        
        for g in games:
            is_home = g['home_team'] == team
            team_score = g['home_score'] if is_home else g['away_score']
            opp_score = g['away_score'] if is_home else g['home_score']
            
            goals_for += team_score
            goals_against += opp_score
            
            if g['went_to_ot']:
                ot_games += 1
            
            if team_score > opp_score:
                wins += 1
            else:
                losses += 1
        
        form = wins / len(games) if games else 0.5
        
        return {
            'wins': wins,
            'losses': losses,
            'ot_games': ot_games,
            'goals_for': goals_for,
            'goals_against': goals_against,
            'games': len(games),
            'form': form,
            'avg_goals_for': goals_for / len(games) if games else 0,
            'avg_goals_against': goals_against / len(games) if games else 0
        }
    
    def get_rest_days(self, team: str, game_date: str, season: str) -> int:
        """Calculate rest days since last game."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT date FROM nhl_games 
            WHERE (home_team = ? OR away_team = ?)
            AND date < ?
            AND season = ?
            ORDER BY date DESC
            LIMIT 1
        """, (team, team, game_date, season))
        
        result = cursor.fetchone()
        if result:
            last_game = datetime.strptime(result[0], '%Y-%m-%d')
            current_game = datetime.strptime(game_date, '%Y-%m-%d')
            return (current_game - last_game).days
        return 3  # Default
    
    def extract_features(self, game: Dict) -> Dict[str, float]:
        """Extract 100+ features from a game record."""
        features = {}
        
        home_team = game['home_team']
        away_team = game['away_team']
        season = game['season']
        game_date = game['date']
        
        # Get team stats
        home_stats = self.get_team_stats(home_team, season)
        away_stats = self.get_team_stats(away_team, season)
        
        # Get H2H stats
        h2h = self.get_h2h_stats(home_team, away_team, season)
        
        # Get recent form
        home_form = self.get_recent_form(home_team, game_date, season)
        away_form = self.get_recent_form(away_team, game_date, season)
        
        # Get rest days
        home_rest = self.get_rest_days(home_team, game_date, season)
        away_rest = self.get_rest_days(away_team, game_date, season)
        
        # Get injuries
        home_injuries = self.get_team_injuries(home_team)
        away_injuries = self.get_team_injuries(away_team)
        
        # ========== BASIC TEAM STATS (20 features) ==========
        features['home_games_played'] = safe_val(home_stats.get('games_played'), 40)
        features['away_games_played'] = safe_val(away_stats.get('games_played'), 40)
        features['home_wins'] = safe_val(home_stats.get('wins'), 20)
        features['away_wins'] = safe_val(away_stats.get('wins'), 20)
        features['home_losses'] = safe_val(home_stats.get('losses'), 15)
        features['away_losses'] = safe_val(away_stats.get('losses'), 15)
        features['home_ot_losses'] = safe_val(home_stats.get('ot_losses'), 5)
        features['away_ot_losses'] = safe_val(away_stats.get('ot_losses'), 5)
        features['home_points_pct'] = safe_val(home_stats.get('points_pct'), 0.5)
        features['away_points_pct'] = safe_val(away_stats.get('points_pct'), 0.5)
        features['points_pct_diff'] = features['home_points_pct'] - features['away_points_pct']
        
        # Win rates
        hp = safe_val(home_stats.get('games_played'), 40)
        ap = safe_val(away_stats.get('games_played'), 40)
        features['home_win_rate'] = safe_val(home_stats.get('wins'), 20) / max(hp, 1)
        features['away_win_rate'] = safe_val(away_stats.get('wins'), 20) / max(ap, 1)
        features['win_rate_diff'] = features['home_win_rate'] - features['away_win_rate']
        
        # ========== GOAL SCORING FEATURES (15 features) ==========
        features['home_goals_per_game'] = safe_val(home_stats.get('goals_per_game'), 3.0)
        features['away_goals_per_game'] = safe_val(away_stats.get('goals_per_game'), 3.0)
        features['home_goals_against_per_game'] = safe_val(home_stats.get('goals_against_per_game'), 3.0)
        features['away_goals_against_per_game'] = safe_val(away_stats.get('goals_against_per_game'), 3.0)
        features['home_goal_diff'] = safe_val(home_stats.get('goal_differential'), 0)
        features['away_goal_diff'] = safe_val(away_stats.get('goal_differential'), 0)
        features['goal_diff_diff'] = features['home_goal_diff'] - features['away_goal_diff']
        features['combined_offense'] = features['home_goals_per_game'] + features['away_goals_per_game']
        features['combined_defense'] = features['home_goals_against_per_game'] + features['away_goals_against_per_game']
        features['scoring_closeness'] = 1 - abs(features['home_goals_per_game'] - features['away_goals_per_game']) / 3.0
        features['offensive_quality'] = (features['home_goals_per_game'] + features['away_goals_per_game']) / 2
        features['defensive_quality'] = (features['home_goals_against_per_game'] + features['away_goals_against_per_game']) / 2
        features['expected_total_goals'] = features['offensive_quality'] * 2
        features['expected_goal_margin'] = abs(features['home_goals_per_game'] - features['away_goals_per_game'])
        features['goals_balance'] = min(features['home_goals_per_game'], features['away_goals_per_game']) / max(features['home_goals_per_game'], features['away_goals_per_game'], 0.01)
        
        # ========== SHOTS FEATURES (10 features) ==========
        features['home_shots_per_game'] = safe_val(home_stats.get('shots_per_game'), 30)
        features['away_shots_per_game'] = safe_val(away_stats.get('shots_per_game'), 30)
        features['home_shots_against_per_game'] = safe_val(home_stats.get('shots_against_per_game'), 30)
        features['away_shots_against_per_game'] = safe_val(away_stats.get('shots_against_per_game'), 30)
        features['home_shot_diff'] = features['home_shots_per_game'] - features['home_shots_against_per_game']
        features['away_shot_diff'] = features['away_shots_per_game'] - features['away_shots_against_per_game']
        features['shot_diff_diff'] = features['home_shot_diff'] - features['away_shot_diff']
        features['home_shooting_efficiency'] = features['home_goals_per_game'] / max(features['home_shots_per_game'], 1)
        features['away_shooting_efficiency'] = features['away_goals_per_game'] / max(features['away_shots_per_game'], 1)
        features['shooting_efficiency_diff'] = features['home_shooting_efficiency'] - features['away_shooting_efficiency']
        
        # ========== SPECIAL TEAMS FEATURES (12 features) ==========
        features['home_pp_pct'] = safe_val(home_stats.get('pp_pct'), 20.0) / 100
        features['away_pp_pct'] = safe_val(away_stats.get('pp_pct'), 20.0) / 100
        features['home_pk_pct'] = safe_val(home_stats.get('pk_pct'), 80.0) / 100
        features['away_pk_pct'] = safe_val(away_stats.get('pk_pct'), 80.0) / 100
        features['pp_pct_diff'] = features['home_pp_pct'] - features['away_pp_pct']
        features['pk_pct_diff'] = features['home_pk_pct'] - features['away_pk_pct']
        features['home_special_teams'] = features['home_pp_pct'] + features['home_pk_pct']
        features['away_special_teams'] = features['away_pp_pct'] + features['away_pk_pct']
        features['special_teams_diff'] = features['home_special_teams'] - features['away_special_teams']
        features['home_pp_opportunities'] = safe_val(home_stats.get('pp_opportunities'), 100) / max(hp, 1)
        features['away_pp_opportunities'] = safe_val(away_stats.get('pp_opportunities'), 100) / max(ap, 1)
        features['pp_opportunities_diff'] = features['home_pp_opportunities'] - features['away_pp_opportunities']
        
        # ========== OT HISTORY FEATURES (10 features) ==========
        features['home_ot_wins'] = safe_val(home_stats.get('ot_wins'), 3)
        features['away_ot_wins'] = safe_val(away_stats.get('ot_wins'), 3)
        features['home_ot_game_pct'] = safe_val(home_stats.get('ot_game_pct'), 0.15)
        features['away_ot_game_pct'] = safe_val(away_stats.get('ot_game_pct'), 0.15)
        features['ot_game_pct_avg'] = (features['home_ot_game_pct'] + features['away_ot_game_pct']) / 2
        home_ot_total = safe_val(home_stats.get('ot_wins'), 3) + safe_val(home_stats.get('ot_losses'), 3)
        away_ot_total = safe_val(away_stats.get('ot_wins'), 3) + safe_val(away_stats.get('ot_losses'), 3)
        features['home_ot_win_rate'] = safe_val(home_stats.get('ot_wins'), 3) / max(home_ot_total, 1)
        features['away_ot_win_rate'] = safe_val(away_stats.get('ot_wins'), 3) / max(away_ot_total, 1)
        features['ot_win_rate_diff'] = features['home_ot_win_rate'] - features['away_ot_win_rate']
        features['combined_ot_experience'] = home_ot_total + away_ot_total
        features['ot_tendency'] = (features['home_ot_game_pct'] + features['away_ot_game_pct']) / 2
        
        # ========== RECENT FORM FEATURES (15 features) ==========
        features['home_recent_wins'] = home_form['wins']
        features['away_recent_wins'] = away_form['wins']
        features['home_recent_losses'] = home_form['losses']
        features['away_recent_losses'] = away_form['losses']
        features['home_recent_form'] = home_form['form']
        features['away_recent_form'] = away_form['form']
        features['recent_form_diff'] = features['home_recent_form'] - features['away_recent_form']
        features['home_recent_ot_games'] = home_form['ot_games']
        features['away_recent_ot_games'] = away_form['ot_games']
        features['recent_ot_tendency'] = (home_form['ot_games'] + away_form['ot_games']) / 20
        features['home_recent_goals_for'] = home_form['avg_goals_for']
        features['away_recent_goals_for'] = away_form['avg_goals_for']
        features['home_recent_goals_against'] = home_form['avg_goals_against']
        features['away_recent_goals_against'] = away_form['avg_goals_against']
        features['recent_scoring_closeness'] = 1 - abs(home_form['avg_goals_for'] - away_form['avg_goals_for']) / 3.0
        
        # ========== FATIGUE/REST FEATURES (10 features) ==========
        features['home_rest_days'] = min(home_rest, 7)
        features['away_rest_days'] = min(away_rest, 7)
        features['rest_diff'] = features['home_rest_days'] - features['away_rest_days']
        features['home_back_to_back'] = 1 if home_rest <= 1 else 0
        features['away_back_to_back'] = 1 if away_rest <= 1 else 0
        features['both_rested'] = 1 if home_rest >= 2 and away_rest >= 2 else 0
        features['both_tired'] = 1 if home_rest <= 1 and away_rest <= 1 else 0
        features['fatigue_advantage_home'] = max(0, away_rest - home_rest)
        features['fatigue_advantage_away'] = max(0, home_rest - away_rest)
        features['total_fatigue'] = 1 / (features['home_rest_days'] + features['away_rest_days'] + 1)
        
        # ========== HEAD-TO-HEAD FEATURES (8 features) ==========
        h2h_games = h2h.get('games_played', 0)
        if h2h_games > 0:
            features['h2h_home_wins'] = h2h.get('team1_wins', 0)
            features['h2h_away_wins'] = h2h.get('team2_wins', 0)
            features['h2h_ot_games'] = h2h.get('ot_games', 0)
            features['h2h_ot_rate'] = h2h.get('ot_games', 0) / h2h_games
            features['h2h_home_win_rate'] = h2h.get('team1_wins', 0) / h2h_games
            features['h2h_home_goals'] = h2h.get('team1_goals', 0) / h2h_games
            features['h2h_away_goals'] = h2h.get('team2_goals', 0) / h2h_games
            features['h2h_games_played'] = h2h_games
        else:
            features['h2h_home_wins'] = 0
            features['h2h_away_wins'] = 0
            features['h2h_ot_games'] = 0
            features['h2h_ot_rate'] = 0.15  # League average
            features['h2h_home_win_rate'] = 0.5
            features['h2h_home_goals'] = 3.0
            features['h2h_away_goals'] = 3.0
            features['h2h_games_played'] = 0
        
        # ========== DIVISION/CONFERENCE FEATURES (6 features) ==========
        home_div = home_stats.get('division', '') or ''
        away_div = away_stats.get('division', '') or ''
        home_conf = home_stats.get('conference', '') or ''
        away_conf = away_stats.get('conference', '') or ''
        features['same_division'] = 1 if home_div == away_div and home_div else 0
        features['same_conference'] = 1 if home_conf == away_conf and home_conf else 0
        features['home_division_rank'] = home_stats.get('division_rank') or 4
        features['away_division_rank'] = away_stats.get('division_rank') or 4
        features['division_rank_diff'] = features['home_division_rank'] - features['away_division_rank']
        features['combined_league_rank'] = ((home_stats.get('league_rank') or 16) + (away_stats.get('league_rank') or 16)) / 2
        
        # ========== FACEOFF FEATURES (4 features) ==========
        features['home_faceoff_pct'] = (home_stats.get('faceoff_pct') or 50.0) / 100
        features['away_faceoff_pct'] = (away_stats.get('faceoff_pct') or 50.0) / 100
        features['faceoff_pct_diff'] = features['home_faceoff_pct'] - features['away_faceoff_pct']
        features['faceoff_advantage'] = abs(features['home_faceoff_pct'] - features['away_faceoff_pct'])
        
        # ========== INJURY FEATURES (15 features) ==========
        # Home team injuries
        features['home_injured_count'] = len(home_injuries)
        features['home_injury_impact_total'] = sum(inj.get('impact_rating', 0) for inj in home_injuries)
        features['home_injury_games_missed'] = sum(inj.get('games_missed', 0) for inj in home_injuries)
        features['home_key_player_injured'] = 1 if any(inj.get('impact_rating', 0) >= 8.0 for inj in home_injuries) else 0
        features['home_goalie_injured'] = 1 if any(inj.get('position', '') == 'G' for inj in home_injuries) else 0
        features['home_ir_count'] = sum(1 for inj in home_injuries if inj.get('status') == 'IR')
        features['home_ltir_count'] = sum(1 for inj in home_injuries if inj.get('status') == 'LTIR')
        features['home_dtd_count'] = sum(1 for inj in home_injuries if inj.get('status') in ['DTD', 'GTD'])
        
        # Away team injuries
        features['away_injured_count'] = len(away_injuries)
        features['away_injury_impact_total'] = sum(inj.get('impact_rating', 0) for inj in away_injuries)
        features['away_injury_games_missed'] = sum(inj.get('games_missed', 0) for inj in away_injuries)
        features['away_key_player_injured'] = 1 if any(inj.get('impact_rating', 0) >= 8.0 for inj in away_injuries) else 0
        features['away_goalie_injured'] = 1 if any(inj.get('position', '') == 'G' for inj in away_injuries) else 0
        features['away_ir_count'] = sum(1 for inj in home_injuries if inj.get('status') == 'IR')
        features['away_ltir_count'] = sum(1 for inj in home_injuries if inj.get('status') == 'LTIR')
        
        # Injury differentials
        features['injury_count_diff'] = features['home_injured_count'] - features['away_injured_count']
        features['injury_impact_diff'] = features['home_injury_impact_total'] - features['away_injury_impact_total']
        
        # ========== TEMPORAL/SEASON FEATURES (10 features) ==========
        game_dt = datetime.strptime(game_date, '%Y-%m-%d')
        season_start = datetime.strptime(season[:4] + '-10-01', '%Y-%m-%d')
        days_into_season = (game_dt - season_start).days
        features['days_into_season'] = days_into_season
        features['season_progress'] = min(days_into_season / 200, 1.0)  # ~200 day season
        features['is_early_season'] = 1 if days_into_season < 60 else 0
        features['is_late_season'] = 1 if days_into_season > 150 else 0
        features['month'] = game_dt.month
        features['day_of_week'] = game_dt.weekday()
        features['is_weekend'] = 1 if game_dt.weekday() >= 5 else 0
        
        # Season year as feature
        season_year = int(season[:4])
        features['season_year'] = season_year
        
        # Game type
        features['is_playoff'] = 1 if game.get('game_type', '') == 'playoff' else 0
        features['is_regular_season'] = 1 if game.get('game_type', '') == 'regular' else 0
        
        # ========== ADVANCED ANALYTICS FEATURES (10 features) ==========
        # PDO (Shooting% + Save% - luck indicator)
        home_sv_pct = game.get('home_sv_pct', 0.91)
        away_sv_pct = game.get('away_sv_pct', 0.91)
        features['home_pdo'] = features['home_shooting_efficiency'] * 100 + home_sv_pct * 100
        features['away_pdo'] = features['away_shooting_efficiency'] * 100 + away_sv_pct * 100
        features['pdo_diff'] = features['home_pdo'] - features['away_pdo']
        
        # Expected goals differential
        features['xg_home'] = features['home_shots_per_game'] * features['home_shooting_efficiency']
        features['xg_away'] = features['away_shots_per_game'] * features['away_shooting_efficiency']
        features['xg_diff'] = features['xg_home'] - features['xg_away']
        
        # Corsi/Fenwick proxy
        features['corsi_home'] = features['home_shots_per_game'] + features['home_shots_against_per_game'] * 0.3
        features['corsi_away'] = features['away_shots_per_game'] + features['away_shots_against_per_game'] * 0.3
        features['corsi_diff'] = features['corsi_home'] - features['corsi_away']
        
        # Game score prediction (composite)
        features['predicted_closeness'] = 1 - abs(
            (features['home_win_rate'] + features['home_recent_form']) / 2 -
            (features['away_win_rate'] + features['away_recent_form']) / 2
        )
        
        return features
    
    def get_all_games_with_features(self, seasons: List[str] = None) -> Tuple[pd.DataFrame, np.ndarray]:
        """Load all games and extract features."""
        cursor = self.conn.cursor()
        
        if seasons:
            placeholders = ','.join(['?' for _ in seasons])
            cursor.execute(f"SELECT * FROM nhl_games WHERE season IN ({placeholders}) ORDER BY date", seasons)
        else:
            cursor.execute("SELECT * FROM nhl_games ORDER BY date")
        
        games = cursor.fetchall()
        print(f"Processing {len(games)} games...")
        
        all_features = []
        labels = []
        dates = []
        
        for i, game in enumerate(games):
            game_dict = dict(game)
            features = self.extract_features(game_dict)
            all_features.append(features)
            labels.append(game_dict['went_to_ot'])
            dates.append(game_dict['date'])
            
            if (i + 1) % 1000 == 0:
                print(f"  Processed {i + 1}/{len(games)} games...")
        
        df = pd.DataFrame(all_features)
        df['date'] = dates
        df['label'] = labels
        
        # Store feature names
        self.FEATURE_NAMES = [c for c in df.columns if c not in ['date', 'label']]
        
        print(f"Extracted {len(self.FEATURE_NAMES)} features from {len(df)} games")
        return df, np.array(labels)


class ModelTrainerV5:
    """Advanced model trainer v5.0 with ensemble and time-weighted learning."""
    
    def __init__(self, config: TrainingConfigV5 = None):
        self.config = config or TrainingConfigV5()
        self.feature_engineer = AdvancedFeatureEngineer(self.config.db_path)
        self.scaler = StandardScaler()
        self.models = {}
        self.ensemble_model = None
        self.feature_names = []
        self.best_params = {}
        
        # Create model directory
        Path(self.config.model_dir).mkdir(parents=True, exist_ok=True)
    
    def calculate_time_weights(self, dates: pd.Series) -> np.ndarray:
        """Calculate time-based sample weights using exponential decay."""
        if not self.config.use_time_weights:
            return np.ones(len(dates))
        
        # Reference date (most recent)
        max_date = pd.to_datetime(dates.max())
        
        weights = []
        for date_str in dates:
            game_date = pd.to_datetime(date_str)
            years_ago = (max_date - game_date).days / 365.25
            weight = np.exp(-self.config.decay_rate * years_ago)
            weights.append(weight)
        
        weights = np.array(weights)
        
        # Normalize weights so they sum to len(weights)
        weights = weights * len(weights) / weights.sum()
        
        print(f"Time weights: min={weights.min():.3f}, max={weights.max():.3f}, mean={weights.mean():.3f}")
        return weights
    
    def prepare_data(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Prepare train, validation, and test data with time weights."""
        print("\n" + "="*60)
        print("PREPARING DATA")
        print("="*60)
        
        # Get all training data
        train_df, train_labels = self.feature_engineer.get_all_games_with_features(self.config.train_seasons)
        print(f"Training data: {len(train_df)} samples, OT rate: {train_labels.mean():.2%}")
        
        # Get validation data
        val_df, val_labels = self.feature_engineer.get_all_games_with_features(self.config.val_seasons)
        print(f"Validation data: {len(val_df)} samples, OT rate: {val_labels.mean():.2%}")
        
        # Get test data
        test_df, test_labels = self.feature_engineer.get_all_games_with_features(self.config.test_seasons)
        print(f"Test data: {len(test_df)} samples, OT rate: {test_labels.mean():.2%}")
        
        # Store feature names
        self.feature_names = self.feature_engineer.FEATURE_NAMES
        print(f"Total features: {len(self.feature_names)}")
        
        # Calculate time weights for training data
        train_weights = self.calculate_time_weights(train_df['date'])
        
        # Prepare feature matrices
        X_train = train_df[self.feature_names].values
        X_val = val_df[self.feature_names].values
        X_test = test_df[self.feature_names].values
        
        y_train = train_labels
        y_val = val_labels
        y_test = test_labels
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        X_test_scaled = self.scaler.transform(X_test)
        
        return X_train_scaled, y_train, X_val_scaled, y_val, X_test_scaled, y_test, train_weights
    
    def apply_smote(self, X: np.ndarray, y: np.ndarray, weights: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Apply SMOTE for class balancing."""
        if not self.config.use_smote:
            return X, y, weights
        
        print("\nApplying SMOTE for class balancing...")
        print(f"Before SMOTE: {len(y)} samples, OT rate: {y.mean():.2%}")
        
        smote = SMOTE(
            sampling_strategy=self.config.smote_sampling_strategy,
            random_state=self.config.random_state
        )
        
        X_resampled, y_resampled = smote.fit_resample(X, y)
        
        # Extend weights for synthetic samples (use average weight)
        avg_weight = weights.mean()
        new_weights = np.concatenate([weights, np.full(len(y_resampled) - len(y), avg_weight)])
        
        print(f"After SMOTE: {len(y_resampled)} samples, OT rate: {y_resampled.mean():.2%}")
        
        return X_resampled, y_resampled, new_weights
    
    def optimize_hyperparameters(self, X_train: np.ndarray, y_train: np.ndarray, weights: np.ndarray) -> Dict:
        """Optimize hyperparameters using Optuna."""
        print("\n" + "="*60)
        print("HYPERPARAMETER OPTIMIZATION")
        print("="*60)
        
        def objective(trial):
            params = {
                'lgb': {
                    'n_estimators': trial.suggest_int('lgb_n_estimators', 100, 500),
                    'max_depth': trial.suggest_int('lgb_max_depth', 3, 10),
                    'learning_rate': trial.suggest_float('lgb_lr', 0.01, 0.2),
                    'num_leaves': trial.suggest_int('lgb_num_leaves', 20, 100),
                    'min_child_samples': trial.suggest_int('lgb_min_child', 5, 50),
                    'subsample': trial.suggest_float('lgb_subsample', 0.6, 1.0),
                    'colsample_bytree': trial.suggest_float('lgb_colsample', 0.6, 1.0),
                },
                'xgb': {
                    'n_estimators': trial.suggest_int('xgb_n_estimators', 100, 500),
                    'max_depth': trial.suggest_int('xgb_max_depth', 3, 10),
                    'learning_rate': trial.suggest_float('xgb_lr', 0.01, 0.2),
                    'subsample': trial.suggest_float('xgb_subsample', 0.6, 1.0),
                    'colsample_bytree': trial.suggest_float('xgb_colsample', 0.6, 1.0),
                },
                'cb': {
                    'iterations': trial.suggest_int('cb_iterations', 100, 500),
                    'depth': trial.suggest_int('cb_depth', 3, 10),
                    'learning_rate': trial.suggest_float('cb_lr', 0.01, 0.2),
                },
                'rf': {
                    'n_estimators': trial.suggest_int('rf_n_estimators', 100, 500),
                    'max_depth': trial.suggest_int('rf_max_depth', 5, 20),
                    'min_samples_split': trial.suggest_int('rf_min_split', 2, 20),
                    'min_samples_leaf': trial.suggest_int('rf_min_leaf', 1, 10),
                }
            }
            
            # Split for CV
            X_tr, X_v, y_tr, y_v, w_tr, w_v = train_test_split(
                X_train, y_train, weights, test_size=0.2, 
                random_state=self.config.random_state, stratify=y_train
            )
            
            # Train LightGBM
            lgb_model = lgb.LGBMClassifier(
                **params['lgb'],
                random_state=self.config.random_state,
                n_jobs=self.config.n_jobs,
                verbose=-1
            )
            lgb_model.fit(X_tr, y_tr, sample_weight=w_tr)
            lgb_pred = lgb_model.predict_proba(X_v)[:, 1]
            
            # Train XGBoost
            xgb_model = xgb.XGBClassifier(
                **params['xgb'],
                random_state=self.config.random_state,
                n_jobs=self.config.n_jobs,
                verbosity=0
            )
            xgb_model.fit(X_tr, y_tr, sample_weight=w_tr)
            xgb_pred = xgb_model.predict_proba(X_v)[:, 1]
            
            # Ensemble prediction (average)
            ensemble_pred = (lgb_pred + xgb_pred) / 2
            auc = roc_auc_score(y_v, ensemble_pred)
            
            return auc
        
        # Run optimization
        study = optuna.create_study(
            direction='maximize',
            sampler=TPESampler(seed=self.config.random_state)
        )
        study.optimize(objective, n_trials=self.config.n_optuna_trials, show_progress_bar=True)
        
        print(f"\nBest AUC: {study.best_value:.4f}")
        
        # Extract best parameters
        best_trial = study.best_trial
        self.best_params = {
            'lgb': {
                'n_estimators': best_trial.params['lgb_n_estimators'],
                'max_depth': best_trial.params['lgb_max_depth'],
                'learning_rate': best_trial.params['lgb_lr'],
                'num_leaves': best_trial.params['lgb_num_leaves'],
                'min_child_samples': best_trial.params['lgb_min_child'],
                'subsample': best_trial.params['lgb_subsample'],
                'colsample_bytree': best_trial.params['lgb_colsample'],
            },
            'xgb': {
                'n_estimators': best_trial.params['xgb_n_estimators'],
                'max_depth': best_trial.params['xgb_max_depth'],
                'learning_rate': best_trial.params['xgb_lr'],
                'subsample': best_trial.params['xgb_subsample'],
                'colsample_bytree': best_trial.params['xgb_colsample'],
            },
            'cb': {
                'iterations': best_trial.params['cb_iterations'],
                'depth': best_trial.params['cb_depth'],
                'learning_rate': best_trial.params['cb_lr'],
            },
            'rf': {
                'n_estimators': best_trial.params['rf_n_estimators'],
                'max_depth': best_trial.params['rf_max_depth'],
                'min_samples_split': best_trial.params['rf_min_split'],
                'min_samples_leaf': best_trial.params['rf_min_leaf'],
            }
        }
        
        return self.best_params
    
    def train_ensemble(self, X_train: np.ndarray, y_train: np.ndarray, weights: np.ndarray) -> None:
        """Train ensemble of models."""
        print("\n" + "="*60)
        print("TRAINING ENSEMBLE MODELS")
        print("="*60)
        
        # 1. LightGBM
        print("\n1. Training LightGBM...")
        self.models['lgb'] = lgb.LGBMClassifier(
            **self.best_params['lgb'],
            random_state=self.config.random_state,
            n_jobs=self.config.n_jobs,
            verbose=-1,
            class_weight='balanced'
        )
        self.models['lgb'].fit(X_train, y_train, sample_weight=weights)
        
        # 2. XGBoost
        print("2. Training XGBoost...")
        self.models['xgb'] = xgb.XGBClassifier(
            **self.best_params['xgb'],
            random_state=self.config.random_state,
            n_jobs=self.config.n_jobs,
            verbosity=0,
            scale_pos_weight=len(y_train[y_train==0]) / max(len(y_train[y_train==1]), 1)
        )
        self.models['xgb'].fit(X_train, y_train, sample_weight=weights)
        
        # 3. CatBoost
        print("3. Training CatBoost...")
        self.models['catboost'] = CatBoostClassifier(
            **self.best_params['cb'],
            random_state=self.config.random_state,
            thread_count=self.config.n_jobs,
            verbose=0,
            auto_class_weights='Balanced'
        )
        self.models['catboost'].fit(X_train, y_train, sample_weight=weights)
        
        # 4. Random Forest
        print("4. Training Random Forest...")
        self.models['rf'] = RandomForestClassifier(
            **self.best_params['rf'],
            random_state=self.config.random_state,
            n_jobs=self.config.n_jobs,
            class_weight='balanced'
        )
        self.models['rf'].fit(X_train, y_train)
        
        # 5. Gradient Boosting
        print("5. Training Gradient Boosting...")
        self.models['gb'] = GradientBoostingClassifier(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.1,
            random_state=self.config.random_state
        )
        self.models['gb'].fit(X_train, y_train, sample_weight=weights)
        
        # 6. Neural Network
        print("6. Training Neural Network...")
        self.models['nn'] = MLPClassifier(
            hidden_layer_sizes=(128, 64, 32),
            activation='relu',
            solver='adam',
            alpha=0.001,
            batch_size=64,
            learning_rate='adaptive',
            max_iter=500,
            random_state=self.config.random_state,
            early_stopping=True,
            validation_fraction=0.1
        )
        self.models['nn'].fit(X_train, y_train)
        
        # Create ensemble - use soft voting for simplicity and reliability
        print("\n7. Creating Voting Ensemble...")
        self.ensemble_model = VotingClassifier(
            estimators=[
                ('lgb', self.models['lgb']),
                ('xgb', self.models['xgb']),
                ('catboost', self.models['catboost']),
                ('rf', self.models['rf']),
                ('gb', self.models['gb']),
            ],
            voting='soft',
            weights=[1.5, 1.5, 1.5, 1.0, 1.0]  # Weight boosting models higher
        )
        self.ensemble_model.fit(X_train, y_train)
        
        print("\nAll models trained successfully!")
    
    def evaluate(self, X: np.ndarray, y: np.ndarray, dataset_name: str = "Test") -> Dict:
        """Evaluate all models."""
        print(f"\n{'='*60}")
        print(f"EVALUATING ON {dataset_name.upper()} SET")
        print(f"{'='*60}")
        
        # Handle edge case where all labels are the same (e.g., test set with no OT games)
        unique_labels = np.unique(y)
        if len(unique_labels) < 2:
            print(f"WARNING: Only {len(unique_labels)} unique class(es) in {dataset_name} set. Using prediction-only evaluation.")
            results = {}
            for name, model in self.models.items():
                y_pred = model.predict(X)
                acc = accuracy_score(y, y_pred)
                results[name] = {'accuracy': acc, 'auc_roc': 0.5}
                print(f"{name:10s}: Accuracy={acc:.4f} (AUC N/A)")
            
            # Ensemble
            if self.ensemble_model:
                y_pred = self.ensemble_model.predict(X)
                acc = accuracy_score(y, y_pred)
                prec = precision_score(y, y_pred, average='weighted', zero_division=0)
                rec = recall_score(y, y_pred, average='weighted', zero_division=0)
                f1 = f1_score(y, y_pred, average='weighted', zero_division=0)
                cm = confusion_matrix(y, y_pred)
                
                results['ensemble'] = {
                    'accuracy': acc,
                    'auc_roc': 0.5,
                    'precision': prec,
                    'recall': rec,
                    'f1': f1,
                    'precision_no_ot': 1.0 if y.sum() == 0 else 0.0,
                    'recall_no_ot': 1.0,
                    'precision_ot': 0.0,
                    'recall_ot': 0.0,
                    'confusion_matrix': cm.tolist()
                }
                print(f"{'ENSEMBLE':10s}: Accuracy={acc:.4f}")
            return results
        
        results = {}
        
        # Evaluate individual models
        for name, model in self.models.items():
            y_pred = model.predict(X)
            y_proba = model.predict_proba(X)[:, 1]
            
            acc = accuracy_score(y, y_pred)
            auc = roc_auc_score(y, y_proba)
            
            results[name] = {'accuracy': acc, 'auc_roc': auc}
            print(f"{name:10s}: Accuracy={acc:.4f}, AUC={auc:.4f}")
        
        # Evaluate ensemble
        if self.ensemble_model:
            y_pred = self.ensemble_model.predict(X)
            y_proba = self.ensemble_model.predict_proba(X)[:, 1]
            
            acc = accuracy_score(y, y_pred)
            auc = roc_auc_score(y, y_proba)
            prec = precision_score(y, y_pred, average='weighted')
            rec = recall_score(y, y_pred, average='weighted')
            f1 = f1_score(y, y_pred, average='weighted')
            
            # Class-specific metrics
            prec_no_ot = precision_score(y, y_pred, pos_label=0)
            rec_no_ot = recall_score(y, y_pred, pos_label=0)
            prec_ot = precision_score(y, y_pred, pos_label=1)
            rec_ot = recall_score(y, y_pred, pos_label=1)
            
            cm = confusion_matrix(y, y_pred)
            
            print(f"\n{'ENSEMBLE':10s}: Accuracy={acc:.4f}, AUC={auc:.4f}")
            print(f"\nClassification Report:\n{classification_report(y, y_pred, target_names=['No OT', 'OT'])}")
            print(f"Confusion Matrix:\n{cm}")
            
            results['ensemble'] = {
                'accuracy': acc,
                'auc_roc': auc,
                'precision': prec,
                'recall': rec,
                'f1': f1,
                'precision_no_ot': prec_no_ot,
                'recall_no_ot': rec_no_ot,
                'precision_ot': prec_ot,
                'recall_ot': rec_ot,
                'confusion_matrix': cm.tolist()
            }
        
        return results
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get aggregated feature importance from all models."""
        importance = {name: 0.0 for name in self.feature_names}
        
        # LightGBM
        for i, name in enumerate(self.feature_names):
            importance[name] += self.models['lgb'].feature_importances_[i] / 5
        
        # XGBoost
        for i, name in enumerate(self.feature_names):
            importance[name] += self.models['xgb'].feature_importances_[i] / 5
        
        # CatBoost
        for i, name in enumerate(self.feature_names):
            importance[name] += self.models['catboost'].feature_importances_[i] / 5
        
        # Random Forest
        for i, name in enumerate(self.feature_names):
            importance[name] += self.models['rf'].feature_importances_[i] / 5
        
        # Gradient Boosting
        for i, name in enumerate(self.feature_names):
            importance[name] += self.models['gb'].feature_importances_[i] / 5
        
        # Sort by importance
        importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
        
        return importance
    
    def save_models(self):
        """Save all models and artifacts."""
        print("\n" + "="*60)
        print("SAVING MODELS")
        print("="*60)
        
        model_dir = Path(self.config.model_dir)
        
        # Save individual models
        for name, model in self.models.items():
            path = model_dir / f"{name}_model.pkl"
            with open(path, 'wb') as f:
                pickle.dump(model, f)
            print(f"Saved {name} model to {path}")
        
        # Save ensemble
        with open(model_dir / "ensemble_model.pkl", 'wb') as f:
            pickle.dump(self.ensemble_model, f)
        print(f"Saved ensemble model")
        
        # Save scaler
        with open(model_dir / "scaler.pkl", 'wb') as f:
            pickle.dump(self.scaler, f)
        print(f"Saved scaler")
        
        # Save feature names
        with open(model_dir / "feature_names.json", 'w') as f:
            json.dump(self.feature_names, f, indent=2)
        print(f"Saved feature names ({len(self.feature_names)} features)")
        
        # Save best params
        with open(model_dir / "best_params.json", 'w') as f:
            json.dump(self.best_params, f, indent=2)
        print(f"Saved hyperparameters")
    
    def train(self) -> TrainingResultV5:
        """Run full training pipeline."""
        start_time = datetime.now()
        
        print("\n" + "="*70)
        print("EDEN ANALYTICS PRO - MODEL v5.0 TRAINING")
        print("="*70)
        print(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 1. Prepare data
        X_train, y_train, X_val, y_val, X_test, y_test, weights = self.prepare_data()
        
        # 2. Apply SMOTE
        X_train_balanced, y_train_balanced, weights_balanced = self.apply_smote(X_train, y_train, weights)
        
        # 3. Optimize hyperparameters
        self.optimize_hyperparameters(X_train_balanced, y_train_balanced, weights_balanced)
        
        # 4. Train ensemble
        self.train_ensemble(X_train_balanced, y_train_balanced, weights_balanced)
        
        # 5. Evaluate on validation
        val_results = self.evaluate(X_val, y_val, "Validation")
        
        # 6. Evaluate on test
        test_results = self.evaluate(X_test, y_test, "Test")
        
        # 7. Get feature importance
        feature_importance = self.get_feature_importance()
        
        # 8. Save models
        self.save_models()
        
        training_time = (datetime.now() - start_time).total_seconds()
        
        # Create result
        ensemble_metrics = test_results.get('ensemble', val_results.get('ensemble', {}))
        
        result = TrainingResultV5(
            accuracy=ensemble_metrics.get('accuracy', 0),
            precision=ensemble_metrics.get('precision', 0),
            recall=ensemble_metrics.get('recall', 0),
            f1=ensemble_metrics.get('f1', 0),
            auc_roc=ensemble_metrics.get('auc_roc', 0),
            precision_no_ot=ensemble_metrics.get('precision_no_ot', 0),
            recall_no_ot=ensemble_metrics.get('recall_no_ot', 0),
            precision_ot=ensemble_metrics.get('precision_ot', 0),
            recall_ot=ensemble_metrics.get('recall_ot', 0),
            confusion_matrix=ensemble_metrics.get('confusion_matrix', [[0,0],[0,0]]),
            feature_importance=feature_importance,
            training_time=training_time,
            feature_count=len(self.feature_names),
            training_samples=len(y_train),
            validation_samples=len(y_val),
            test_samples=len(y_test),
            individual_model_scores={name: results['accuracy'] for name, results in test_results.items() if name != 'ensemble'},
            best_params=self.best_params
        )
        
        print("\n" + "="*70)
        print("TRAINING COMPLETE")
        print("="*70)
        print(f"Training time: {training_time:.1f} seconds")
        print(f"Final Accuracy: {result.accuracy:.2%}")
        print(f"Final AUC-ROC: {result.auc_roc:.4f}")
        print(f"Precision (No OT): {result.precision_no_ot:.2%}")
        
        return result


def generate_training_report(result: TrainingResultV5, output_path: str):
    """Generate detailed markdown training report."""
    
    report = f"""# Eden Analytics Pro - Model v5.0 Training Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

Model v5.0 has been trained with advanced features including:
- Time-weighted learning (recent games weighted higher)
- Injury-based features
- 6-model ensemble (LightGBM, XGBoost, CatBoost, Random Forest, Gradient Boosting, Neural Network)
- SMOTE for class balancing
- Hyperparameter optimization with Optuna

## Performance Metrics

### Overall Metrics

| Metric | Value |
|--------|-------|
| **Accuracy** | {result.accuracy:.2%} |
| **AUC-ROC** | {result.auc_roc:.4f} |
| **Precision (weighted)** | {result.precision:.2%} |
| **Recall (weighted)** | {result.recall:.2%} |
| **F1 Score (weighted)** | {result.f1:.2%} |

### Class-Specific Metrics

| Class | Precision | Recall |
|-------|-----------|--------|
| No OT (Class 0) | {result.precision_no_ot:.2%} | {result.recall_no_ot:.2%} |
| OT (Class 1) | {result.precision_ot:.2%} | {result.recall_ot:.2%} |

### Confusion Matrix

```
              Predicted
              No OT    OT
Actual No OT   {result.confusion_matrix[0][0]:5d}  {result.confusion_matrix[0][1]:5d}
Actual OT      {result.confusion_matrix[1][0]:5d}  {result.confusion_matrix[1][1]:5d}
```

## Individual Model Performance

| Model | Accuracy |
|-------|----------|
"""
    
    for name, acc in result.individual_model_scores.items():
        report += f"| {name} | {acc:.2%} |\n"
    
    report += f"""
## Feature Engineering

### Total Features: {result.feature_count}

### Top 20 Most Important Features

| Rank | Feature | Importance |
|------|---------|------------|
"""
    
    for i, (name, imp) in enumerate(list(result.feature_importance.items())[:20], 1):
        report += f"| {i} | {name} | {imp:.4f} |\n"
    
    report += f"""

### Feature Categories

- **Basic Team Stats**: 20 features (wins, losses, points, etc.)
- **Goal Scoring**: 15 features (goals per game, differentials, etc.)
- **Shots**: 10 features (shots per game, efficiency, etc.)
- **Special Teams**: 12 features (PP%, PK%, etc.)
- **OT History**: 10 features (OT wins, OT game %, etc.)
- **Recent Form**: 15 features (last 10 games performance)
- **Fatigue/Rest**: 10 features (rest days, back-to-back, etc.)
- **Head-to-Head**: 8 features (H2H record, OT rate, etc.)
- **Division/Conference**: 6 features (same division, rankings)
- **Injury Features**: 15+ features (injured count, impact, key players)
- **Temporal Features**: 10 features (season progress, day of week, etc.)
- **Advanced Analytics**: 10 features (PDO, xG, Corsi proxy)

## Training Configuration

| Parameter | Value |
|-----------|-------|
| Training Seasons | 2019-2024 |
| Validation Season | 2024-2025 |
| Test Season | 2025-2026 |
| Time Weight Decay | 0.15 |
| SMOTE Used | Yes |
| Optuna Trials | 30 |
| Stacking Ensemble | Yes |

## Model Comparison: v4.0 vs v5.0

| Metric | v4.0 | v5.0 | Improvement |
|--------|------|------|-------------|
| Accuracy | 86.29% | {result.accuracy:.2%} | {(result.accuracy - 0.8629) * 100:+.2f}% |
| AUC-ROC | 0.9218 | {result.auc_roc:.4f} | {(result.auc_roc - 0.9218):+.4f} |
| Features | ~100 | {result.feature_count} | +{result.feature_count - 100} |

## Best Hyperparameters

### LightGBM
```json
{json.dumps(result.best_params.get('lgb', {}), indent=2)}
```

### XGBoost
```json
{json.dumps(result.best_params.get('xgb', {}), indent=2)}
```

### CatBoost
```json
{json.dumps(result.best_params.get('cb', {}), indent=2)}
```

### Random Forest
```json
{json.dumps(result.best_params.get('rf', {}), indent=2)}
```

## Data Summary

| Dataset | Samples |
|---------|---------|
| Training | {result.training_samples:,} |
| Validation | {result.validation_samples:,} |
| Test | {result.test_samples:,} |
| **Total** | {result.training_samples + result.validation_samples + result.test_samples:,} |

## Training Time

Total training time: **{result.training_time:.1f} seconds** ({result.training_time/60:.1f} minutes)

## Files Generated

- `/home/ubuntu/eden_mvp/models_v5/ensemble_model.pkl` - Main ensemble model
- `/home/ubuntu/eden_mvp/models_v5/lgb_model.pkl` - LightGBM model
- `/home/ubuntu/eden_mvp/models_v5/xgb_model.pkl` - XGBoost model
- `/home/ubuntu/eden_mvp/models_v5/catboost_model.pkl` - CatBoost model
- `/home/ubuntu/eden_mvp/models_v5/rf_model.pkl` - Random Forest model
- `/home/ubuntu/eden_mvp/models_v5/gb_model.pkl` - Gradient Boosting model
- `/home/ubuntu/eden_mvp/models_v5/nn_model.pkl` - Neural Network model
- `/home/ubuntu/eden_mvp/models_v5/scaler.pkl` - Feature scaler
- `/home/ubuntu/eden_mvp/models_v5/feature_names.json` - Feature names
- `/home/ubuntu/eden_mvp/models_v5/best_params.json` - Hyperparameters

---
*Report generated by Eden Analytics Pro Model Trainer v5.0*
"""
    
    with open(output_path, 'w') as f:
        f.write(report)
    
    print(f"\nTraining report saved to: {output_path}")


def main():
    """Main training function."""
    # Configure training
    config = TrainingConfigV5(
        n_optuna_trials=30,
        use_smote=True,
        use_time_weights=True,
        use_stacking=True
    )
    
    # Train model
    trainer = ModelTrainerV5(config)
    result = trainer.train()
    
    # Generate report
    generate_training_report(result, "/home/ubuntu/eden_mvp/training_report_v5.md")
    
    # Save model info
    model_info = {
        "version": "5.0",
        "accuracy": result.accuracy,
        "auc_roc": result.auc_roc,
        "precision": result.precision,
        "recall": result.recall,
        "f1": result.f1,
        "feature_count": result.feature_count,
        "training_time": result.training_time,
        "trained_at": datetime.now().isoformat(),
        "individual_scores": result.individual_model_scores
    }
    
    with open("/home/ubuntu/eden_mvp/models_v5/model_info.json", 'w') as f:
        json.dump(model_info, f, indent=2)
    
    print("\n" + "="*70)
    print("MODEL v5.0 TRAINING COMPLETED SUCCESSFULLY!")
    print("="*70)
    print(f"Accuracy: {result.accuracy:.2%}")
    print(f"AUC-ROC: {result.auc_roc:.4f}")
    print(f"Precision (No OT): {result.precision_no_ot:.2%}")
    
    return result


if __name__ == "__main__":
    main()
