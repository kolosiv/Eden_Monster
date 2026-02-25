"""Database Manager Module for Eden MVP.

SQLite database management for storing matches, bets, and results.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from pydantic import BaseModel

from utils.logger import get_logger

logger = get_logger(__name__)


class MatchRecord(BaseModel):
    """Database record for a match."""
    id: Optional[int] = None
    match_id: str
    team_strong: str
    team_weak: str
    commence_time: str
    odds_strong: float
    odds_weak_reg: float
    bookmaker_strong: str
    bookmaker_weak: str
    arb_roi: float
    hole_probability: float
    recommendation: str
    created_at: Optional[str] = None


class BetRecord(BaseModel):
    """Database record for a placed bet."""
    id: Optional[int] = None
    match_id: str
    strategy: str
    stake_strong: float
    stake_weak: float
    total_stake: float
    potential_profit: float
    status: str = "pending"  # pending, won, lost
    created_at: Optional[str] = None


class ResultRecord(BaseModel):
    """Database record for bet results."""
    id: Optional[int] = None
    bet_id: int
    match_id: str
    actual_outcome: str  # strong_win, weak_win_reg, hole
    profit_loss: float
    final_bankroll: float
    created_at: Optional[str] = None


class DatabaseManager:
    """SQLite database manager for Eden MVP.
    
    Manages three tables:
    - matches: Match details, odds, and predictions
    - bets: Placed bets with stakes and strategies
    - results: Actual outcomes and profit/loss
    
    Example:
        >>> db = DatabaseManager("eden_mvp.db")
        >>> db.initialize()
        >>> db.insert_match(match_record)
        >>> history = db.get_betting_history()
    """
    
    def __init__(self, db_path: str = "eden_mvp.db"):
        """Initialize DatabaseManager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._ensure_directory()
        
    def _ensure_directory(self) -> None:
        """Ensure database directory exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections.
        
        Yields:
            sqlite3.Connection object
        """
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
        """Initialize database with required tables.
        
        Creates tables if they don't exist:
        - matches
        - bets
        - results
        """
        logger.info(f"Initializing database at {self.db_path}")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Matches table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id TEXT UNIQUE NOT NULL,
                    team_strong TEXT NOT NULL,
                    team_weak TEXT NOT NULL,
                    commence_time TEXT,
                    odds_strong REAL NOT NULL,
                    odds_weak_reg REAL NOT NULL,
                    bookmaker_strong TEXT,
                    bookmaker_weak TEXT,
                    arb_roi REAL,
                    arb_percentage REAL,
                    ot_probability REAL,
                    hole_probability REAL,
                    expected_value REAL,
                    risk_level TEXT,
                    recommendation TEXT,
                    confidence_score REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Bets table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    stake_strong REAL NOT NULL,
                    stake_weak REAL NOT NULL,
                    total_stake REAL NOT NULL,
                    potential_profit REAL,
                    risk_amount REAL,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (match_id) REFERENCES matches(match_id)
                )
            """)
            
            # Results table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bet_id INTEGER NOT NULL,
                    match_id TEXT NOT NULL,
                    actual_outcome TEXT NOT NULL,
                    profit_loss REAL NOT NULL,
                    final_bankroll REAL,
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (bet_id) REFERENCES bets(id),
                    FOREIGN KEY (match_id) REFERENCES matches(match_id)
                )
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_matches_date 
                ON matches(commence_time)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_bets_status 
                ON bets(status)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_results_outcome 
                ON results(actual_outcome)
            """)
            
        logger.info("Database initialized successfully")
    
    # -------------------- MATCH OPERATIONS --------------------
    
    def insert_match(self, match: Dict[str, Any]) -> int:
        """Insert a match record.
        
        Args:
            match: Match data dictionary
            
        Returns:
            Inserted row ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO matches (
                    match_id, team_strong, team_weak, commence_time,
                    odds_strong, odds_weak_reg, bookmaker_strong, bookmaker_weak,
                    arb_roi, arb_percentage, ot_probability, hole_probability,
                    expected_value, risk_level, recommendation, confidence_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                match.get('match_id'),
                match.get('team_strong'),
                match.get('team_weak'),
                match.get('commence_time'),
                match.get('odds_strong'),
                match.get('odds_weak_reg'),
                match.get('bookmaker_strong'),
                match.get('bookmaker_weak'),
                match.get('arb_roi'),
                match.get('arb_percentage'),
                match.get('ot_probability'),
                match.get('hole_probability'),
                match.get('expected_value'),
                match.get('risk_level'),
                match.get('recommendation'),
                match.get('confidence_score')
            ))
            
            logger.debug(f"Inserted match: {match.get('match_id')}")
            return cursor.lastrowid
    
    def get_match(self, match_id: str) -> Optional[Dict]:
        """Get a match by ID.
        
        Args:
            match_id: Match identifier
            
        Returns:
            Match dict or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM matches WHERE match_id = ?",
                (match_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_recent_matches(self, limit: int = 20) -> List[Dict]:
        """Get recent matches.
        
        Args:
            limit: Maximum number of matches to return
            
        Returns:
            List of match dicts
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM matches ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    # -------------------- BET OPERATIONS --------------------
    
    def insert_bet(self, bet: Dict[str, Any]) -> int:
        """Insert a bet record.
        
        Args:
            bet: Bet data dictionary
            
        Returns:
            Inserted row ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO bets (
                    match_id, strategy, stake_strong, stake_weak,
                    total_stake, potential_profit, risk_amount, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                bet.get('match_id'),
                bet.get('strategy'),
                bet.get('stake_strong'),
                bet.get('stake_weak'),
                bet.get('total_stake'),
                bet.get('potential_profit'),
                bet.get('risk_amount'),
                bet.get('status', 'pending')
            ))
            
            logger.info(f"Inserted bet for match: {bet.get('match_id')}")
            return cursor.lastrowid
    
    def update_bet_status(self, bet_id: int, status: str) -> None:
        """Update bet status.
        
        Args:
            bet_id: Bet ID
            status: New status (pending, won, lost)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE bets SET status = ? WHERE id = ?",
                (status, bet_id)
            )
            logger.debug(f"Updated bet {bet_id} status to {status}")
    
    def get_pending_bets(self) -> List[Dict]:
        """Get all pending bets.
        
        Returns:
            List of pending bet dicts
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM bets WHERE status = 'pending' ORDER BY created_at"
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_bet_by_match(self, match_id: str) -> Optional[Dict]:
        """Get bet by match ID.
        
        Args:
            match_id: Match identifier
            
        Returns:
            Bet dict or None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM bets WHERE match_id = ? ORDER BY created_at DESC LIMIT 1",
                (match_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # -------------------- RESULT OPERATIONS --------------------
    
    def insert_result(self, result: Dict[str, Any]) -> int:
        """Insert a result record.
        
        Args:
            result: Result data dictionary
            
        Returns:
            Inserted row ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO results (
                    bet_id, match_id, actual_outcome,
                    profit_loss, final_bankroll, notes
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                result.get('bet_id'),
                result.get('match_id'),
                result.get('actual_outcome'),
                result.get('profit_loss'),
                result.get('final_bankroll'),
                result.get('notes')
            ))
            
            # Update bet status
            outcome = result.get('actual_outcome')
            status = 'lost' if outcome == 'hole' else 'won'
            self.update_bet_status(result.get('bet_id'), status)
            
            logger.info(f"Inserted result: {outcome}, P/L: {result.get('profit_loss')}")
            return cursor.lastrowid
    
    def get_results_by_date_range(
        self,
        start_date: str,
        end_date: str
    ) -> List[Dict]:
        """Get results within date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of result dicts
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM results 
                WHERE created_at BETWEEN ? AND ?
                ORDER BY created_at
            """, (start_date, end_date))
            return [dict(row) for row in cursor.fetchall()]
    
    # -------------------- STATISTICS --------------------
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive betting statistics.
        
        Returns:
            Dict with statistics
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total bets
            cursor.execute("SELECT COUNT(*) FROM bets")
            total_bets = cursor.fetchone()[0]
            
            # Won/Lost counts
            cursor.execute("SELECT COUNT(*) FROM bets WHERE status = 'won'")
            won = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM bets WHERE status = 'lost'")
            lost = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM bets WHERE status = 'pending'")
            pending = cursor.fetchone()[0]
            
            # Total profit/loss
            cursor.execute("SELECT COALESCE(SUM(profit_loss), 0) FROM results")
            total_pnl = cursor.fetchone()[0]
            
            # Total staked
            cursor.execute(
                "SELECT COALESCE(SUM(total_stake), 0) FROM bets WHERE status != 'pending'"
            )
            total_staked = cursor.fetchone()[0]
            
            # Hole count
            cursor.execute(
                "SELECT COUNT(*) FROM results WHERE actual_outcome = 'hole'"
            )
            hole_count = cursor.fetchone()[0]
            
            # Win rate
            completed = won + lost
            win_rate = (won / completed * 100) if completed > 0 else 0
            
            # ROI
            roi = (total_pnl / total_staked * 100) if total_staked > 0 else 0
            
            # Hole rate
            hole_rate = (hole_count / completed * 100) if completed > 0 else 0
            
            # Average profit per bet
            avg_profit = total_pnl / completed if completed > 0 else 0
            
            # Best and worst results
            cursor.execute(
                "SELECT MAX(profit_loss), MIN(profit_loss) FROM results"
            )
            best_worst = cursor.fetchone()
            
            return {
                "total_bets": total_bets,
                "won": won,
                "lost": lost,
                "pending": pending,
                "win_rate": round(win_rate, 2),
                "total_profit_loss": round(total_pnl, 2),
                "total_staked": round(total_staked, 2),
                "roi": round(roi, 2),
                "hole_count": hole_count,
                "hole_rate": round(hole_rate, 2),
                "avg_profit_per_bet": round(avg_profit, 2),
                "best_result": round(best_worst[0] or 0, 2),
                "worst_result": round(best_worst[1] or 0, 2)
            }
    
    def get_betting_history(self, limit: int = 50) -> List[Dict]:
        """Get betting history with match and result details.
        
        Args:
            limit: Maximum records to return
            
        Returns:
            List of history records
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    b.id as bet_id,
                    b.match_id,
                    m.team_strong,
                    m.team_weak,
                    m.commence_time,
                    b.strategy,
                    b.total_stake,
                    b.potential_profit,
                    b.status,
                    r.actual_outcome,
                    r.profit_loss,
                    b.created_at
                FROM bets b
                LEFT JOIN matches m ON b.match_id = m.match_id
                LEFT JOIN results r ON b.id = r.bet_id
                ORDER BY b.created_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_strategy_performance(self) -> Dict[str, Dict]:
        """Get performance breakdown by strategy.
        
        Returns:
            Dict mapping strategy to performance stats
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    b.strategy,
                    COUNT(*) as total,
                    SUM(CASE WHEN b.status = 'won' THEN 1 ELSE 0 END) as won,
                    SUM(CASE WHEN b.status = 'lost' THEN 1 ELSE 0 END) as lost,
                    COALESCE(SUM(r.profit_loss), 0) as total_pnl
                FROM bets b
                LEFT JOIN results r ON b.id = r.bet_id
                WHERE b.status != 'pending'
                GROUP BY b.strategy
            """)
            
            results = {}
            for row in cursor.fetchall():
                strategy = row[0]
                total = row[1]
                won = row[2]
                lost = row[3]
                pnl = row[4]
                
                results[strategy] = {
                    "total": total,
                    "won": won,
                    "lost": lost,
                    "win_rate": round(won / total * 100, 2) if total > 0 else 0,
                    "total_pnl": round(pnl, 2)
                }
            
            return results
    
    def backup(self, backup_path: Optional[str] = None) -> str:
        """Create database backup.
        
        Args:
            backup_path: Optional backup file path
            
        Returns:
            Path to backup file
        """
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.db_path.stem}_backup_{timestamp}.db"
        
        with self.get_connection() as conn:
            backup_conn = sqlite3.connect(backup_path)
            conn.backup(backup_conn)
            backup_conn.close()
        
        logger.info(f"Database backed up to {backup_path}")
        return backup_path
    
    def clear_all_data(self, confirm: bool = False) -> None:
        """Clear all data from database.
        
        Args:
            confirm: Must be True to proceed
        """
        if not confirm:
            raise ValueError("Must pass confirm=True to clear all data")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM results")
            cursor.execute("DELETE FROM bets")
            cursor.execute("DELETE FROM matches")
        
        logger.warning("All database data cleared")
    
    # -------------------- TELEGRAM USERS --------------------
    
    def _init_telegram_tables(self) -> None:
        """Initialize Telegram-related tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS telegram_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    chat_id INTEGER NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    enabled INTEGER DEFAULT 1,
                    min_roi REAL DEFAULT 2.0,
                    max_hole_risk REAL DEFAULT 10.0,
                    leagues TEXT DEFAULT 'NHL,KHL',
                    max_notifications_per_hour INTEGER DEFAULT 10,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_telegram_users_enabled
                ON telegram_users(enabled)
            """)
    
    def add_telegram_user(
        self,
        user_id: int,
        chat_id: int,
        username: str = "",
        first_name: str = ""
    ) -> int:
        """Add or update a Telegram user.
        
        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            username: Username
            first_name: First name
            
        Returns:
            Row ID
        """
        self._init_telegram_tables()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO telegram_users (user_id, chat_id, username, first_name)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    chat_id = excluded.chat_id,
                    username = excluded.username,
                    first_name = excluded.first_name,
                    updated_at = CURRENT_TIMESTAMP
            """, (user_id, chat_id, username, first_name))
            
            logger.info(f"Added/updated Telegram user: {user_id}")
            return cursor.lastrowid
    
    def get_telegram_user(self, user_id: int) -> Optional[Dict]:
        """Get a Telegram user by ID.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            User dict or None
        """
        self._init_telegram_tables()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM telegram_users WHERE user_id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_telegram_users(self, enabled_only: bool = False) -> List[Dict]:
        """Get all Telegram users.
        
        Args:
            enabled_only: If True, only return enabled users
            
        Returns:
            List of user dicts
        """
        self._init_telegram_tables()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if enabled_only:
                cursor.execute(
                    "SELECT * FROM telegram_users WHERE enabled = 1"
                )
            else:
                cursor.execute("SELECT * FROM telegram_users")
            
            return [dict(row) for row in cursor.fetchall()]
    
    def update_telegram_user(self, user_id: int, **kwargs) -> None:
        """Update a Telegram user's settings.
        
        Args:
            user_id: Telegram user ID
            **kwargs: Fields to update
        """
        self._init_telegram_tables()
        
        allowed_fields = {
            'enabled', 'min_roi', 'max_hole_risk', 'leagues',
            'max_notifications_per_hour', 'username', 'first_name'
        }
        
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return
        
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [user_id]
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE telegram_users SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                values
            )
            logger.debug(f"Updated Telegram user {user_id}: {updates}")
    
    def delete_telegram_user(self, user_id: int) -> None:
        """Delete a Telegram user.
        
        Args:
            user_id: Telegram user ID
        """
        self._init_telegram_tables()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM telegram_users WHERE user_id = ?",
                (user_id,)
            )
            logger.info(f"Deleted Telegram user: {user_id}")
    
    # -------------------- BANKROLL HISTORY --------------------
    
    def _init_bankroll_tables(self) -> None:
        """Initialize bankroll-related tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bankroll_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    bankroll REAL NOT NULL,
                    change REAL DEFAULT 0,
                    drawdown REAL DEFAULT 0,
                    profile TEXT,
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_bankroll_history_timestamp
                ON bankroll_history(timestamp)
            """)
    
    def insert_bankroll_history(self, entry: Dict[str, Any]) -> int:
        """Insert a bankroll history entry.
        
        Args:
            entry: History entry dict
            
        Returns:
            Row ID
        """
        self._init_bankroll_tables()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            timestamp = entry.get('timestamp')
            if hasattr(timestamp, 'isoformat'):
                timestamp = timestamp.isoformat()
            
            cursor.execute("""
                INSERT INTO bankroll_history (
                    timestamp, bankroll, change, drawdown, profile, notes
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                timestamp or datetime.now().isoformat(),
                entry.get('bankroll', 0),
                entry.get('change', 0),
                entry.get('drawdown', 0),
                entry.get('profile', ''),
                entry.get('notes', '')
            ))
            
            logger.debug(f"Inserted bankroll history: ${entry.get('bankroll', 0):.2f}")
            return cursor.lastrowid
    
    def get_bankroll_history(
        self,
        limit: int = 100,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict]:
        """Get bankroll history.
        
        Args:
            limit: Maximum records to return
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            List of history entries
        """
        self._init_bankroll_tables()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM bankroll_history"
            params = []
            
            if start_date and end_date:
                query += " WHERE timestamp BETWEEN ? AND ?"
                params.extend([start_date, end_date])
            elif start_date:
                query += " WHERE timestamp >= ?"
                params.append(start_date)
            elif end_date:
                query += " WHERE timestamp <= ?"
                params.append(end_date)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_bankroll_summary(self) -> Dict[str, Any]:
        """Get bankroll summary statistics.
        
        Returns:
            Dict with bankroll statistics
        """
        self._init_bankroll_tables()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    MIN(bankroll) as min_bankroll,
                    MAX(bankroll) as max_bankroll,
                    AVG(bankroll) as avg_bankroll,
                    MAX(drawdown) as max_drawdown,
                    AVG(drawdown) as avg_drawdown,
                    COUNT(*) as total_entries
                FROM bankroll_history
            """)
            
            row = cursor.fetchone()
            
            if not row or row[5] == 0:
                return {
                    'min_bankroll': 0,
                    'max_bankroll': 0,
                    'avg_bankroll': 0,
                    'max_drawdown': 0,
                    'avg_drawdown': 0,
                    'total_entries': 0
                }
            
            return {
                'min_bankroll': row[0] or 0,
                'max_bankroll': row[1] or 0,
                'avg_bankroll': row[2] or 0,
                'max_drawdown': row[3] or 0,
                'avg_drawdown': row[4] or 0,
                'total_entries': row[5]
            }
    
    def clear_bankroll_history(self, confirm: bool = False) -> None:
        """Clear all bankroll history.
        
        Args:
            confirm: Must be True to proceed
        """
        if not confirm:
            raise ValueError("Must pass confirm=True to clear history")
        
        self._init_bankroll_tables()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM bankroll_history")
        
        logger.warning("Bankroll history cleared")
    
    # -------------------- MODEL PERFORMANCE --------------------
    
    def _init_model_performance_tables(self) -> None:
        """Initialize model performance tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Model performance history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_performance_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    match_id TEXT NOT NULL,
                    predicted_ot_prob REAL,
                    predicted_hole_prob REAL,
                    actual_went_ot INTEGER,
                    actual_hole INTEGER,
                    confidence REAL,
                    model_version TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Model versions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version_id TEXT UNIQUE NOT NULL,
                    version_number INTEGER NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    model_path TEXT,
                    scaler_path TEXT,
                    accuracy REAL,
                    auc_roc REAL,
                    brier_score REAL,
                    hole_rate REAL,
                    feature_count INTEGER,
                    training_samples INTEGER,
                    hyperparameters TEXT,
                    notes TEXT,
                    is_active INTEGER DEFAULT 0,
                    model_type TEXT
                )
            """)
            
            # Retraining history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS retraining_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    trigger_type TEXT,
                    trigger_reason TEXT,
                    old_accuracy REAL,
                    new_accuracy REAL,
                    old_version TEXT,
                    new_version TEXT,
                    training_time REAL,
                    status TEXT,
                    deployed INTEGER DEFAULT 0,
                    error TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # NHL Goalies
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nhl_goalies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_id INTEGER,
                    name TEXT,
                    team_abbrev TEXT,
                    season TEXT,
                    games_played INTEGER,
                    wins INTEGER,
                    losses INTEGER,
                    save_percentage REAL,
                    goals_against_average REAL,
                    shutouts INTEGER,
                    is_starter INTEGER DEFAULT 0,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # NHL Players
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nhl_players (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_id INTEGER,
                    name TEXT,
                    team_abbrev TEXT,
                    position TEXT,
                    season TEXT,
                    games_played INTEGER,
                    goals INTEGER,
                    assists INTEGER,
                    points INTEGER,
                    plus_minus INTEGER,
                    shots INTEGER,
                    shooting_pct REAL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # NHL Injuries
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nhl_injuries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_id INTEGER,
                    name TEXT,
                    team_abbrev TEXT,
                    position TEXT,
                    injury_status TEXT,
                    injury_type TEXT,
                    expected_return TEXT,
                    impact_score REAL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_model_perf_match
                ON model_performance_history(match_id)
            """)
    
    def insert_model_performance(self, data: Dict[str, Any]) -> int:
        """Insert a model performance record.
        
        Args:
            data: Performance data dict
            
        Returns:
            Row ID
        """
        self._init_model_performance_tables()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO model_performance_history (
                    timestamp, match_id, predicted_ot_prob, predicted_hole_prob,
                    confidence, model_version
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                data.get('timestamp'),
                data.get('match_id'),
                data.get('predicted_ot_prob'),
                data.get('predicted_hole_prob'),
                data.get('confidence'),
                data.get('model_version')
            ))
            
            return cursor.lastrowid
    
    def update_model_performance_outcome(
        self,
        match_id: str,
        went_ot: bool,
        was_hole: bool
    ) -> None:
        """Update outcome for a model performance record.
        
        Args:
            match_id: Match ID
            went_ot: Whether match went to OT
            was_hole: Whether it was a hole
        """
        self._init_model_performance_tables()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE model_performance_history
                SET actual_went_ot = ?, actual_hole = ?
                WHERE match_id = ?
            """, (1 if went_ot else 0, 1 if was_hole else 0, match_id))
    
    def get_model_performance_history(
        self,
        limit: int = 200,
        start_date: str = None
    ) -> List[Dict]:
        """Get model performance history.
        
        Args:
            limit: Maximum records
            start_date: Optional start date filter
            
        Returns:
            List of performance records
        """
        self._init_model_performance_tables()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if start_date:
                cursor.execute("""
                    SELECT * FROM model_performance_history
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (start_date, limit))
            else:
                cursor.execute("""
                    SELECT * FROM model_performance_history
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def insert_retraining_history(self, data: Dict[str, Any]) -> int:
        """Insert a retraining history record.
        
        Args:
            data: Retraining data dict
            
        Returns:
            Row ID
        """
        self._init_model_performance_tables()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO retraining_history (
                    timestamp, trigger_type, trigger_reason,
                    old_accuracy, new_accuracy, old_version, new_version,
                    training_time, status, deployed, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('timestamp'),
                data.get('trigger_type'),
                data.get('trigger_reason'),
                data.get('old_accuracy'),
                data.get('new_accuracy'),
                data.get('old_version'),
                data.get('new_version'),
                data.get('training_time'),
                data.get('status'),
                1 if data.get('deployed') else 0,
                data.get('error')
            ))
            
            return cursor.lastrowid
    
    def get_retraining_history(self, limit: int = 20) -> List[Dict]:
        """Get retraining history.
        
        Args:
            limit: Maximum records
            
        Returns:
            List of retraining records
        """
        self._init_model_performance_tables()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM retraining_history
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
