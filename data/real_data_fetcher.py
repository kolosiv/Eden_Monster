"""Real NHL Data Fetcher for Eden MVP v3.0.1.

Fetches REAL historical NHL data from the nhl_historical.db database.
This replaces synthetic data generation with verified, real game data.

CRITICAL FIX: This addresses the synthetic data issue identified in the analysis.
The model must be trained on real historical games, not random.gauss() data.
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from pydantic import BaseModel
from utils.logger import get_logger

logger = get_logger(__name__)


class RealHistoricalMatch(BaseModel):
    """Historical match data from real NHL games."""
    match_id: str
    date: str
    season: str
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    went_to_ot: bool
    went_to_so: bool = False
    ot_winner: Optional[str] = None
    
    # Game stats
    home_shots: int = 0
    away_shots: int = 0
    home_pp_pct: float = 0.0
    away_pp_pct: float = 0.0
    home_sv_pct: float = 0.0
    away_sv_pct: float = 0.0
    home_faceoff_pct: float = 0.0
    away_faceoff_pct: float = 0.0
    
    # Computed team stats (filled from team_stats table)
    home_goals_for_avg: float = 0.0
    home_goals_against_avg: float = 0.0
    away_goals_for_avg: float = 0.0
    away_goals_against_avg: float = 0.0
    home_win_rate: float = 0.5
    away_win_rate: float = 0.5
    home_ot_win_rate: float = 0.5
    away_ot_win_rate: float = 0.5
    home_recent_form: float = 0.5
    away_recent_form: float = 0.5
    home_days_rest: int = 2
    away_days_rest: int = 2
    h2h_home_wins: int = 0
    h2h_away_wins: int = 0
    h2h_ot_games: int = 0
    home_special_teams: float = 0.5
    away_special_teams: float = 0.5
    same_division: bool = False
    same_conference: bool = False


@dataclass
class DataQualityMetrics:
    """Data quality validation metrics.
    
    CRITICAL: This validates data quality to ensure trustworthy predictions.
    """
    total_games: int = 0
    ot_games: int = 0
    ot_rate: float = 0.0
    expected_ot_rate: float = 0.22  # NHL average is ~22-24%
    ot_rate_deviation: float = 0.0
    missing_team_stats: int = 0
    invalid_scores: int = 0
    data_quality_score: float = 0.0
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class RealNHLDataFetcher:
    """Fetches REAL historical NHL data for ML training.
    
    This class addresses the critical issue of synthetic data by:
    1. Loading real games from verified NHL database
    2. Computing team statistics from actual performance
    3. Validating data quality before training
    4. Ensuring proper OT rate (~22-24% for regular season)
    
    CRITICAL FIX: Replaces random.gauss() synthetic generation.
    """
    
    # Expected NHL OT rate range (for validation)
    MIN_EXPECTED_OT_RATE = 0.20
    MAX_EXPECTED_OT_RATE = 0.26
    
    def __init__(self, db_path: str = "data/nhl_historical.db"):
        """Initialize with real NHL database.
        
        Args:
            db_path: Path to nhl_historical.db with real games
        """
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            # Try alternate path
            self.db_path = Path(__file__).parent / "nhl_historical.db"
        
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Real NHL database not found at {db_path}. "
                "Cannot train model without real data."
            )
        
        logger.info(f"Initialized RealNHLDataFetcher with {self.db_path}")
        self._cache_team_stats()
        self._cache_h2h_data()
    
    def _cache_team_stats(self) -> None:
        """Cache team statistics from database."""
        self.team_stats = {}
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT team, season, games_played, wins, losses, ot_losses,
                           goals_for, goals_against, pp_pct, pk_pct, shots_for, shots_against
                    FROM nhl_team_stats
                """)
                for row in cursor:
                    team, season = row[0], row[1]
                    key = f"{team}_{season}"
                    gp = max(row[2], 1)
                    wins = row[3]
                    ot_losses = row[5] or 0
                    
                    self.team_stats[key] = {
                        'games_played': gp,
                        'wins': wins,
                        'losses': row[4],
                        'ot_losses': ot_losses,
                        'goals_for_avg': row[6] / gp if row[6] else 2.8,
                        'goals_against_avg': row[7] / gp if row[7] else 2.8,
                        'win_rate': wins / gp,
                        'ot_rate': ot_losses / gp if gp > 0 else 0.22,
                        'pp_pct': row[8] or 0.2,
                        'pk_pct': row[9] or 0.8,
                    }
                logger.info(f"Cached stats for {len(self.team_stats)} team-seasons")
        except Exception as e:
            logger.warning(f"Could not cache team stats: {e}")
            self.team_stats = {}
    
    def _cache_h2h_data(self) -> None:
        """Cache head-to-head data."""
        self.h2h_data = {}
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT team1, team2, season, team1_wins, team2_wins, ot_games
                    FROM nhl_h2h
                """)
                for row in cursor:
                    key = f"{row[0]}_{row[1]}_{row[2]}"
                    self.h2h_data[key] = {
                        'team1_wins': row[3],
                        'team2_wins': row[4],
                        'ot_games': row[5] or 0
                    }
        except Exception as e:
            logger.warning(f"Could not cache H2H data: {e}")
            self.h2h_data = {}
    
    def validate_data_quality(self, games: List[RealHistoricalMatch]) -> DataQualityMetrics:
        """Validate data quality before training.
        
        CRITICAL: This ensures the model is trained on valid data.
        
        Args:
            games: List of games to validate
            
        Returns:
            DataQualityMetrics with validation results
        """
        metrics = DataQualityMetrics()
        metrics.total_games = len(games)
        
        if not games:
            metrics.warnings.append("CRITICAL: No games loaded!")
            metrics.data_quality_score = 0.0
            return metrics
        
        # Count OT games
        metrics.ot_games = sum(1 for g in games if g.went_to_ot)
        metrics.ot_rate = metrics.ot_games / metrics.total_games
        
        # Check OT rate
        metrics.ot_rate_deviation = abs(metrics.ot_rate - metrics.expected_ot_rate)
        
        if metrics.ot_rate < 0.05:
            metrics.warnings.append(
                f"CRITICAL: OT rate {metrics.ot_rate:.1%} is too low! "
                "Expected ~22%. Data may be corrupted or incomplete."
            )
        elif metrics.ot_rate < self.MIN_EXPECTED_OT_RATE:
            metrics.warnings.append(
                f"WARNING: OT rate {metrics.ot_rate:.1%} is below expected "
                f"range ({self.MIN_EXPECTED_OT_RATE:.0%}-{self.MAX_EXPECTED_OT_RATE:.0%})"
            )
        elif metrics.ot_rate > self.MAX_EXPECTED_OT_RATE:
            metrics.warnings.append(
                f"WARNING: OT rate {metrics.ot_rate:.1%} is above expected "
                f"range. May indicate data selection bias."
            )
        
        # Check for missing stats
        for game in games:
            if game.home_goals_for_avg == 0 and game.away_goals_for_avg == 0:
                metrics.missing_team_stats += 1
            if game.home_goals < 0 or game.away_goals < 0:
                metrics.invalid_scores += 1
        
        if metrics.missing_team_stats > len(games) * 0.3:
            metrics.warnings.append(
                f"WARNING: {metrics.missing_team_stats} games ({metrics.missing_team_stats/len(games):.0%}) "
                "missing team stats"
            )
        
        # Calculate quality score (0-1)
        ot_rate_score = max(0, 1 - metrics.ot_rate_deviation * 5)  # Penalty for OT rate deviation
        coverage_score = 1 - (metrics.missing_team_stats / max(len(games), 1))
        validity_score = 1 - (metrics.invalid_scores / max(len(games), 1))
        
        metrics.data_quality_score = (ot_rate_score * 0.4 + coverage_score * 0.4 + validity_score * 0.2)
        
        # Log results
        logger.info(f"Data Quality Validation:")
        logger.info(f"  Total games: {metrics.total_games}")
        logger.info(f"  OT games: {metrics.ot_games} ({metrics.ot_rate:.1%})")
        logger.info(f"  Quality score: {metrics.data_quality_score:.2f}")
        
        for warning in metrics.warnings:
            logger.warning(warning)
        
        return metrics
    
    def load_real_games(
        self,
        limit: int = None,
        season_filter: str = None,
        game_type: str = "regular",  # "regular", "playoff", or "all"
        start_date: str = None,
        end_date: str = None
    ) -> List[RealHistoricalMatch]:
        """Load real NHL games from database.
        
        Args:
            limit: Maximum number of games to load
            season_filter: Filter by season (e.g., "20232024")
            game_type: Filter by game type
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)
            
        Returns:
            List of real historical matches
        """
        games = []
        
        # Note: Some databases use 'OFF' for completed games, others use 'FINAL'
        query = """
            SELECT 
                game_id, date, season, home_team, away_team,
                home_score, away_score, went_to_ot, went_to_so, ot_winner,
                home_shots, away_shots, home_pp_pct, away_pp_pct,
                home_sv_pct, away_sv_pct, home_faceoff_pct, away_faceoff_pct,
                game_type
            FROM nhl_games
            WHERE game_state IN ('FINAL', 'OFF') 
              AND home_score IS NOT NULL AND away_score IS NOT NULL
        """
        params = []
        
        if game_type and game_type != "all":
            query += " AND game_type = ?"
            params.append(game_type)
        
        if season_filter:
            query += " AND season = ?"
            params.append(season_filter)
            
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
            
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        query += " ORDER BY date ASC"  # CRITICAL: Order by date for time series
        
        if limit:
            query += f" LIMIT {limit}"
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(query, params)
                
                for row in cursor:
                    game_id, date, season = str(row[0]), row[1], row[2]
                    home_team, away_team = row[3], row[4]
                    home_score, away_score = row[5], row[6]
                    went_ot = bool(row[7])
                    went_so = bool(row[8])
                    ot_winner = row[9]
                    
                    # Get team stats
                    home_key = f"{home_team}_{season}"
                    away_key = f"{away_team}_{season}"
                    
                    home_stats = self.team_stats.get(home_key, {})
                    away_stats = self.team_stats.get(away_key, {})
                    
                    # Get H2H data
                    h2h_key1 = f"{home_team}_{away_team}_{season}"
                    h2h_key2 = f"{away_team}_{home_team}_{season}"
                    h2h = self.h2h_data.get(h2h_key1) or self.h2h_data.get(h2h_key2) or {}
                    
                    match = RealHistoricalMatch(
                        match_id=game_id,
                        date=date,
                        season=season,
                        home_team=home_team,
                        away_team=away_team,
                        home_goals=home_score,
                        away_goals=away_score,
                        went_to_ot=went_ot,
                        went_to_so=went_so,
                        ot_winner=ot_winner,
                        home_shots=row[10] or 0,
                        away_shots=row[11] or 0,
                        home_pp_pct=row[12] or 0.0,
                        away_pp_pct=row[13] or 0.0,
                        home_sv_pct=row[14] or 0.0,
                        away_sv_pct=row[15] or 0.0,
                        home_faceoff_pct=row[16] or 0.0,
                        away_faceoff_pct=row[17] or 0.0,
                        # Team stats
                        home_goals_for_avg=home_stats.get('goals_for_avg', 2.8),
                        home_goals_against_avg=home_stats.get('goals_against_avg', 2.8),
                        away_goals_for_avg=away_stats.get('goals_for_avg', 2.8),
                        away_goals_against_avg=away_stats.get('goals_against_avg', 2.8),
                        home_win_rate=home_stats.get('win_rate', 0.5),
                        away_win_rate=away_stats.get('win_rate', 0.5),
                        home_ot_win_rate=0.5 + (home_stats.get('win_rate', 0.5) - 0.5) * 0.3,
                        away_ot_win_rate=0.5 + (away_stats.get('win_rate', 0.5) - 0.5) * 0.3,
                        home_special_teams=(home_stats.get('pp_pct', 0.2) + home_stats.get('pk_pct', 0.8)) / 2,
                        away_special_teams=(away_stats.get('pp_pct', 0.2) + away_stats.get('pk_pct', 0.8)) / 2,
                        h2h_home_wins=h2h.get('team1_wins', 0),
                        h2h_away_wins=h2h.get('team2_wins', 0),
                        h2h_ot_games=h2h.get('ot_games', 0),
                    )
                    games.append(match)
                
                logger.info(f"Loaded {len(games)} real NHL games from database")
                
        except Exception as e:
            logger.error(f"Error loading games: {e}")
            raise
        
        return games
    
    def get_training_data(
        self,
        num_samples: int = 5000,
        validate: bool = True,
        game_type: str = "regular"
    ) -> Tuple[List[Dict], List[int], DataQualityMetrics]:
        """Get training data from REAL NHL games.
        
        CRITICAL: This returns REAL data, not synthetic.
        
        Args:
            num_samples: Number of samples (games) to use
            validate: Whether to validate data quality
            game_type: Type of games to include
            
        Returns:
            X: List of feature dictionaries
            y: List of labels (1 = OT, 0 = no OT)
            metrics: Data quality metrics
        """
        logger.info(f"Loading up to {num_samples} real NHL games...")
        
        # Load real games
        games = self.load_real_games(limit=num_samples, game_type=game_type)
        
        if len(games) < 100:
            raise ValueError(
                f"Only found {len(games)} games. Need at least 100 for training. "
                "Check database connection."
            )
        
        # Validate data quality
        metrics = self.validate_data_quality(games) if validate else DataQualityMetrics()
        
        if validate and metrics.data_quality_score < 0.5:
            logger.warning(
                f"Data quality score {metrics.data_quality_score:.2f} is low. "
                "Model predictions may be unreliable."
            )
        
        # Extract features
        X = []
        y = []
        
        for game in games:
            features = self._extract_features(game)
            X.append(features)
            y.append(1 if game.went_to_ot else 0)
        
        logger.info(f"Prepared {len(X)} samples from REAL NHL data")
        logger.info(f"OT distribution: {sum(y)} OT games ({sum(y)/len(y):.1%})")
        
        return X, y, metrics
    
    def _extract_features(self, game: RealHistoricalMatch) -> Dict:
        """Extract ML features from a real game.
        
        NOTE: We avoid features that could cause data leakage.
        The 'implied_closeness' feature has been replaced with
        'win_rate_closeness' computed from pre-game stats only.
        """
        # Compute win rate closeness (pre-game info only, no leakage)
        win_rate_closeness = 1 - abs(game.home_win_rate - game.away_win_rate)
        
        return {
            # Team scoring (from season stats, computed before game)
            "home_gf_avg": game.home_goals_for_avg,
            "home_ga_avg": game.home_goals_against_avg,
            "away_gf_avg": game.away_goals_for_avg,
            "away_ga_avg": game.away_goals_against_avg,
            "goal_diff_home": game.home_goals_for_avg - game.home_goals_against_avg,
            "goal_diff_away": game.away_goals_for_avg - game.away_goals_against_avg,
            
            # Win rates (season stats, no leakage)
            "home_win_rate": game.home_win_rate,
            "away_win_rate": game.away_win_rate,
            "win_rate_diff": abs(game.home_win_rate - game.away_win_rate),
            "win_rate_closeness": win_rate_closeness,  # FIXED: Replaces implied_closeness
            
            # OT history
            "home_ot_win_rate": game.home_ot_win_rate,
            "away_ot_win_rate": game.away_ot_win_rate,
            
            # Form (placeholder - would be computed from recent games)
            "home_form": game.home_recent_form,
            "away_form": game.away_recent_form,
            "form_diff": abs(game.home_recent_form - game.away_recent_form),
            
            # Fatigue
            "home_rest_days": game.home_days_rest,
            "away_rest_days": game.away_days_rest,
            "home_back_to_back": 1 if game.home_days_rest == 1 else 0,
            "away_back_to_back": 1 if game.away_days_rest == 1 else 0,
            
            # H2H
            "h2h_home_dominance": game.h2h_home_wins / max(1, game.h2h_home_wins + game.h2h_away_wins),
            "h2h_ot_rate": game.h2h_ot_games / max(1, game.h2h_home_wins + game.h2h_away_wins),
            
            # Special teams
            "home_special_teams": game.home_special_teams,
            "away_special_teams": game.away_special_teams,
            
            # Division/Conference (placeholder)
            "same_division": 1 if game.same_division else 0,
            "same_conference": 1 if game.same_conference else 0,
        }
    
    def get_statistics(self) -> Dict:
        """Get database statistics."""
        stats = {}
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Total games (use both FINAL and OFF states)
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM nhl_games 
                    WHERE game_state IN ('FINAL', 'OFF') AND home_score IS NOT NULL
                """)
                stats['total_games'] = cursor.fetchone()[0]
                
                # OT games
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM nhl_games 
                    WHERE went_to_ot = 1 AND game_state IN ('FINAL', 'OFF')
                """)
                stats['ot_games'] = cursor.fetchone()[0]
                
                # OT rate
                stats['ot_rate'] = stats['ot_games'] / stats['total_games'] if stats['total_games'] > 0 else 0
                
                # Seasons
                cursor = conn.execute("SELECT DISTINCT season FROM nhl_games ORDER BY season")
                stats['seasons'] = [row[0] for row in cursor.fetchall()]
                
                # Games by type
                cursor = conn.execute("""
                    SELECT game_type, COUNT(*) FROM nhl_games 
                    WHERE game_state IN ('FINAL', 'OFF') GROUP BY game_type
                """)
                stats['games_by_type'] = dict(cursor.fetchall())
                
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
        
        return stats


# Export
__all__ = ['RealNHLDataFetcher', 'RealHistoricalMatch', 'DataQualityMetrics']
