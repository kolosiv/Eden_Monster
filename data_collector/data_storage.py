"""Data Storage Module for NHL historical data.

Stores and manages NHL game data in SQLite database.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from contextlib import contextmanager

from utils.logger import get_logger

logger = get_logger(__name__)


class DataStorage:
    """SQLite storage for NHL historical data.
    
    Tables:
    - nhl_games: Historical game data
    - nhl_team_stats: Team statistics by season
    - nhl_h2h: Head-to-head records
    
    Example:
        >>> storage = DataStorage()
        >>> storage.initialize()
        >>> storage.insert_game(game_data)
        >>> games = storage.get_games_for_team("TOR")
    """
    
    def __init__(self, db_path: str = "data/nhl_historical.db"):
        """Initialize data storage.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialized = False
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def initialize(self) -> None:
        """Initialize database with required tables."""
        if self._initialized:
            return
        
        logger.info(f"Initializing NHL data storage at {self.db_path}")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # NHL Games table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nhl_games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id TEXT UNIQUE NOT NULL,
                    date TEXT NOT NULL,
                    season TEXT,
                    game_type TEXT,
                    home_team TEXT NOT NULL,
                    away_team TEXT NOT NULL,
                    home_team_id INTEGER,
                    away_team_id INTEGER,
                    home_score INTEGER NOT NULL,
                    away_score INTEGER NOT NULL,
                    period TEXT,
                    went_to_ot INTEGER DEFAULT 0,
                    went_to_so INTEGER DEFAULT 0,
                    home_shots INTEGER DEFAULT 0,
                    away_shots INTEGER DEFAULT 0,
                    home_pp_goals INTEGER DEFAULT 0,
                    away_pp_goals INTEGER DEFAULT 0,
                    home_pp_opportunities INTEGER DEFAULT 0,
                    away_pp_opportunities INTEGER DEFAULT 0,
                    home_faceoff_pct REAL DEFAULT 0,
                    away_faceoff_pct REAL DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Team Stats table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nhl_team_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_abbrev TEXT NOT NULL,
                    team_name TEXT,
                    season TEXT NOT NULL,
                    games_played INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    ot_losses INTEGER DEFAULT 0,
                    points INTEGER DEFAULT 0,
                    goals_for INTEGER DEFAULT 0,
                    goals_against INTEGER DEFAULT 0,
                    goals_for_per_game REAL DEFAULT 0,
                    goals_against_per_game REAL DEFAULT 0,
                    power_play_pct REAL DEFAULT 0,
                    penalty_kill_pct REAL DEFAULT 0,
                    shots_per_game REAL DEFAULT 0,
                    shots_against_per_game REAL DEFAULT 0,
                    faceoff_win_pct REAL DEFAULT 0,
                    ot_wins INTEGER DEFAULT 0,
                    ot_losses_total INTEGER DEFAULT 0,
                    so_wins INTEGER DEFAULT 0,
                    so_losses INTEGER DEFAULT 0,
                    home_wins INTEGER DEFAULT 0,
                    away_wins INTEGER DEFAULT 0,
                    last_10_wins INTEGER DEFAULT 0,
                    streak TEXT DEFAULT '',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(team_abbrev, season)
                )
            """)
            
            # Head-to-Head table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nhl_h2h (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team1 TEXT NOT NULL,
                    team2 TEXT NOT NULL,
                    season TEXT NOT NULL,
                    team1_wins INTEGER DEFAULT 0,
                    team2_wins INTEGER DEFAULT 0,
                    ot_games INTEGER DEFAULT 0,
                    team1_goals INTEGER DEFAULT 0,
                    team2_goals INTEGER DEFAULT 0,
                    games_played INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(team1, team2, season)
                )
            """)
            
            # Model predictions table (for A/B testing)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    model_version TEXT,
                    predicted_ot_prob REAL,
                    predicted_hole_prob REAL,
                    confidence REAL,
                    actual_went_to_ot INTEGER,
                    actual_ot_winner TEXT,
                    prediction_time TEXT DEFAULT CURRENT_TIMESTAMP,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Model performance table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT NOT NULL,
                    model_version TEXT,
                    date TEXT NOT NULL,
                    games_predicted INTEGER DEFAULT 0,
                    correct_ot_predictions INTEGER DEFAULT 0,
                    correct_winner_predictions INTEGER DEFAULT 0,
                    avg_confidence REAL DEFAULT 0,
                    brier_score REAL DEFAULT 0,
                    log_loss REAL DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Model versions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    file_path TEXT,
                    accuracy REAL,
                    precision_score REAL,
                    recall REAL,
                    f1_score REAL,
                    auc_roc REAL,
                    training_samples INTEGER,
                    features_used TEXT,
                    hyperparameters TEXT,
                    notes TEXT,
                    is_active INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(model_name, version)
                )
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_games_date ON nhl_games(date)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_games_teams ON nhl_games(home_team, away_team)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_games_season ON nhl_games(season)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_team_stats_season ON nhl_team_stats(season)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_predictions_game ON model_predictions(game_id)
            """)
        
        self._initialized = True
        logger.info("NHL data storage initialized")
    
    # -------------------- GAME OPERATIONS --------------------
    
    def insert_game(self, game: Dict[str, Any]) -> int:
        """Insert or update a game record.
        
        Args:
            game: Game data dictionary
            
        Returns:
            Row ID
        """
        self.initialize()
        
        # Determine if game went to OT
        period = game.get('period', 'REG')
        went_to_ot = 1 if period in ('OT', 'SO') else 0
        went_to_so = 1 if period == 'SO' else 0
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO nhl_games (
                    game_id, date, season, game_type,
                    home_team, away_team, home_team_id, away_team_id,
                    home_score, away_score, period,
                    went_to_ot, went_to_so,
                    home_shots, away_shots,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(game_id) DO UPDATE SET
                    home_score = excluded.home_score,
                    away_score = excluded.away_score,
                    period = excluded.period,
                    went_to_ot = excluded.went_to_ot,
                    went_to_so = excluded.went_to_so,
                    home_shots = excluded.home_shots,
                    away_shots = excluded.away_shots,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                game.get('game_id'),
                game.get('date'),
                game.get('season', ''),
                game.get('game_type', '2'),
                game.get('home_team'),
                game.get('away_team'),
                game.get('home_team_id', 0),
                game.get('away_team_id', 0),
                game.get('home_score', 0),
                game.get('away_score', 0),
                period,
                went_to_ot,
                went_to_so,
                game.get('home_shots', 0),
                game.get('away_shots', 0),
                datetime.now().isoformat()
            ))
            
            return cursor.lastrowid
    
    def insert_games_batch(self, games: List[Dict[str, Any]]) -> int:
        """Insert multiple games efficiently.
        
        Args:
            games: List of game data dictionaries
            
        Returns:
            Number of games inserted
        """
        count = 0
        for game in games:
            try:
                self.insert_game(game)
                count += 1
            except Exception as e:
                logger.warning(f"Could not insert game {game.get('game_id')}: {e}")
        
        logger.info(f"Inserted {count}/{len(games)} games")
        return count
    
    def get_game(self, game_id: str) -> Optional[Dict]:
        """Get a game by ID."""
        self.initialize()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM nhl_games WHERE game_id = ?",
                (game_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_games_for_season(
        self,
        season: str,
        include_playoffs: bool = False
    ) -> List[Dict]:
        """Get all games for a season.
        
        Args:
            season: Season string (e.g., "20232024")
            include_playoffs: Include playoff games
            
        Returns:
            List of game dicts
        """
        self.initialize()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if include_playoffs:
                cursor.execute(
                    "SELECT * FROM nhl_games WHERE season = ? ORDER BY date",
                    (season,)
                )
            else:
                cursor.execute(
                    "SELECT * FROM nhl_games WHERE season = ? AND game_type = '2' ORDER BY date",
                    (season,)
                )
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_games_for_team(
        self,
        team_abbrev: str,
        season: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get games for a specific team.
        
        Args:
            team_abbrev: Team abbreviation
            season: Optional season filter
            limit: Maximum games to return
            
        Returns:
            List of game dicts
        """
        self.initialize()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if season:
                cursor.execute("""
                    SELECT * FROM nhl_games 
                    WHERE (home_team = ? OR away_team = ?) AND season = ?
                    ORDER BY date DESC LIMIT ?
                """, (team_abbrev, team_abbrev, season, limit))
            else:
                cursor.execute("""
                    SELECT * FROM nhl_games 
                    WHERE (home_team = ? OR away_team = ?)
                    ORDER BY date DESC LIMIT ?
                """, (team_abbrev, team_abbrev, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_h2h_games(
        self,
        team1: str,
        team2: str,
        limit: int = 10
    ) -> List[Dict]:
        """Get head-to-head games between two teams.
        
        Args:
            team1: First team abbreviation
            team2: Second team abbreviation
            limit: Maximum games to return
            
        Returns:
            List of game dicts
        """
        self.initialize()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM nhl_games 
                WHERE (home_team = ? AND away_team = ?)
                   OR (home_team = ? AND away_team = ?)
                ORDER BY date DESC LIMIT ?
            """, (team1, team2, team2, team1, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_ot_statistics(self, season: str = None) -> Dict[str, Any]:
        """Get overtime statistics.
        
        Args:
            season: Optional season filter
            
        Returns:
            Dict with OT statistics
        """
        self.initialize()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            season_filter = "AND season = ?" if season else ""
            params = (season,) if season else ()
            
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_games,
                    SUM(went_to_ot) as ot_games,
                    SUM(went_to_so) as so_games,
                    AVG(home_score + away_score) as avg_total_goals
                FROM nhl_games
                WHERE 1=1 {season_filter}
            """, params)
            
            row = cursor.fetchone()
            total = row[0] or 1
            ot_games = row[1] or 0
            so_games = row[2] or 0
            
            return {
                'total_games': total,
                'ot_games': ot_games,
                'so_games': so_games,
                'ot_rate': ot_games / total,
                'avg_total_goals': row[3] or 0
            }
    
    # -------------------- TEAM STATS OPERATIONS --------------------
    
    def insert_team_stats(self, stats: Dict[str, Any]) -> int:
        """Insert or update team statistics.
        
        Args:
            stats: Team stats dictionary
            
        Returns:
            Row ID
        """
        self.initialize()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO nhl_team_stats (
                    team_abbrev, team_name, season,
                    games_played, wins, losses, ot_losses, points,
                    goals_for, goals_against,
                    power_play_pct, penalty_kill_pct,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(team_abbrev, season) DO UPDATE SET
                    games_played = excluded.games_played,
                    wins = excluded.wins,
                    losses = excluded.losses,
                    ot_losses = excluded.ot_losses,
                    points = excluded.points,
                    goals_for = excluded.goals_for,
                    goals_against = excluded.goals_against,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                stats.get('team_abbrev', stats.get('team_id', '')),
                stats.get('team_name', ''),
                stats.get('season', ''),
                stats.get('games_played', 0),
                stats.get('wins', 0),
                stats.get('losses', 0),
                stats.get('ot_losses', 0),
                stats.get('points', 0),
                stats.get('goals_for', 0),
                stats.get('goals_against', 0),
                stats.get('power_play_pct', 0),
                stats.get('penalty_kill_pct', 0),
                datetime.now().isoformat()
            ))
            
            return cursor.lastrowid
    
    def get_team_stats(
        self,
        team_abbrev: str,
        season: str
    ) -> Optional[Dict]:
        """Get team statistics for a season."""
        self.initialize()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM nhl_team_stats WHERE team_abbrev = ? AND season = ?",
                (team_abbrev, season)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def calculate_team_stats_from_games(
        self,
        team_abbrev: str,
        season: str = None,
        last_n_games: int = None
    ) -> Dict[str, Any]:
        """Calculate team statistics from game data.
        
        Args:
            team_abbrev: Team abbreviation
            season: Optional season filter
            last_n_games: Only consider last N games
            
        Returns:
            Calculated statistics
        """
        self.initialize()
        
        games = self.get_games_for_team(
            team_abbrev, 
            season, 
            limit=last_n_games or 100
        )
        
        if not games:
            return {}
        
        wins = 0
        losses = 0
        ot_losses = 0
        goals_for = 0
        goals_against = 0
        ot_wins = 0
        ot_losses_total = 0
        home_wins = 0
        away_wins = 0
        
        for game in games:
            is_home = game['home_team'] == team_abbrev
            
            if is_home:
                gf = game['home_score']
                ga = game['away_score']
            else:
                gf = game['away_score']
                ga = game['home_score']
            
            goals_for += gf
            goals_against += ga
            
            won = gf > ga
            went_to_ot = game['went_to_ot'] == 1
            
            if won:
                wins += 1
                if is_home:
                    home_wins += 1
                else:
                    away_wins += 1
                if went_to_ot:
                    ot_wins += 1
            else:
                if went_to_ot:
                    ot_losses += 1
                    ot_losses_total += 1
                else:
                    losses += 1
        
        n = len(games)
        ot_total = ot_wins + ot_losses_total
        
        return {
            'team_abbrev': team_abbrev,
            'games_played': n,
            'wins': wins,
            'losses': losses,
            'ot_losses': ot_losses,
            'win_rate': wins / n if n > 0 else 0,
            'goals_for_avg': goals_for / n if n > 0 else 0,
            'goals_against_avg': goals_against / n if n > 0 else 0,
            'goal_differential': (goals_for - goals_against) / n if n > 0 else 0,
            'ot_wins': ot_wins,
            'ot_losses_total': ot_losses_total,
            'ot_win_rate': ot_wins / ot_total if ot_total > 0 else 0.5,
            'home_win_rate': home_wins / sum(1 for g in games if g['home_team'] == team_abbrev) if games else 0.5,
            'away_win_rate': away_wins / sum(1 for g in games if g['away_team'] == team_abbrev) if games else 0.5
        }
    
    # -------------------- MODEL OPERATIONS --------------------
    
    def insert_prediction(self, prediction: Dict[str, Any]) -> int:
        """Insert a model prediction for tracking."""
        self.initialize()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO model_predictions (
                    game_id, model_name, model_version,
                    predicted_ot_prob, predicted_hole_prob, confidence,
                    prediction_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                prediction.get('game_id'),
                prediction.get('model_name'),
                prediction.get('model_version'),
                prediction.get('predicted_ot_prob'),
                prediction.get('predicted_hole_prob'),
                prediction.get('confidence'),
                datetime.now().isoformat()
            ))
            
            return cursor.lastrowid
    
    def update_prediction_result(
        self,
        prediction_id: int,
        actual_went_to_ot: bool,
        actual_ot_winner: str = None
    ) -> None:
        """Update prediction with actual result."""
        self.initialize()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE model_predictions SET
                    actual_went_to_ot = ?,
                    actual_ot_winner = ?
                WHERE id = ?
            """, (1 if actual_went_to_ot else 0, actual_ot_winner, prediction_id))
    
    def insert_model_version(self, version_info: Dict[str, Any]) -> int:
        """Insert a model version record."""
        self.initialize()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO model_versions (
                    model_name, version, file_path,
                    accuracy, precision_score, recall, f1_score, auc_roc,
                    training_samples, features_used, hyperparameters, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(model_name, version) DO UPDATE SET
                    accuracy = excluded.accuracy,
                    precision_score = excluded.precision_score,
                    recall = excluded.recall,
                    f1_score = excluded.f1_score,
                    auc_roc = excluded.auc_roc
            """, (
                version_info.get('model_name'),
                version_info.get('version'),
                version_info.get('file_path'),
                version_info.get('accuracy'),
                version_info.get('precision_score'),
                version_info.get('recall'),
                version_info.get('f1_score'),
                version_info.get('auc_roc'),
                version_info.get('training_samples'),
                str(version_info.get('features_used', [])),
                str(version_info.get('hyperparameters', {})),
                version_info.get('notes')
            ))
            
            return cursor.lastrowid
    
    def get_active_model_version(self, model_name: str) -> Optional[Dict]:
        """Get the currently active model version."""
        self.initialize()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM model_versions WHERE model_name = ? AND is_active = 1",
                (model_name,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def set_active_model_version(self, model_name: str, version: str) -> None:
        """Set a model version as active."""
        self.initialize()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Deactivate all versions of this model
            cursor.execute(
                "UPDATE model_versions SET is_active = 0 WHERE model_name = ?",
                (model_name,)
            )
            # Activate the specified version
            cursor.execute(
                "UPDATE model_versions SET is_active = 1 WHERE model_name = ? AND version = ?",
                (model_name, version)
            )
    
    def get_game_count(self, season: str = None) -> int:
        """Get total number of games in database."""
        self.initialize()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if season:
                cursor.execute(
                    "SELECT COUNT(*) FROM nhl_games WHERE season = ?",
                    (season,)
                )
            else:
                cursor.execute("SELECT COUNT(*) FROM nhl_games")
            
            return cursor.fetchone()[0]
    
    def get_latest_game_date(self) -> Optional[str]:
        """Get the date of the most recent game."""
        self.initialize()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(date) FROM nhl_games")
            row = cursor.fetchone()
            return row[0] if row else None
