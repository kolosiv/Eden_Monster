"""User Management System for Eden Analytics Pro Multi-User Support."""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)


class SubscriptionTier(Enum):
    FREE = "free"
    PREMIUM = "premium"
    ADMIN = "admin"


@dataclass
class User:
    """User data model."""
    user_id: int
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    registration_date: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    subscription_expires: Optional[datetime] = None
    settings: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def is_premium(self) -> bool:
        """Check if user has active premium subscription."""
        if self.subscription_tier == SubscriptionTier.ADMIN:
            return True
        if self.subscription_tier == SubscriptionTier.PREMIUM:
            if self.subscription_expires is None:
                return False
            return datetime.now() < self.subscription_expires
        return False
    
    @property
    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.subscription_tier == SubscriptionTier.ADMIN
    
    @property
    def full_name(self) -> str:
        """Get user's full name."""
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.last_name:
            parts.append(self.last_name)
        return " ".join(parts) or self.username or str(self.telegram_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'user_id': self.user_id,
            'telegram_id': self.telegram_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'registration_date': self.registration_date.isoformat(),
            'is_active': self.is_active,
            'subscription_tier': self.subscription_tier.value,
            'subscription_expires': self.subscription_expires.isoformat() if self.subscription_expires else None,
            'settings': self.settings,
            'is_premium': self.is_premium,
            'is_admin': self.is_admin
        }


@dataclass
class UserBankroll:
    """User bankroll data model."""
    id: int
    user_id: int
    initial_bankroll: float = 1000.0
    current_bankroll: float = 1000.0
    total_profit: float = 0.0
    total_bets: int = 0
    win_count: int = 0
    loss_count: int = 0
    hole_count: int = 0
    roi: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)
    
    @property
    def win_rate(self) -> float:
        """Calculate win rate."""
        total = self.win_count + self.loss_count + self.hole_count
        if total == 0:
            return 0.0
        return self.win_count / total


class UserManager:
    """Manages user database operations."""
    
    def __init__(self, db_path: str = "eden_users.db"):
        self.db_path = Path(db_path)
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_database(self):
        """Initialize database tables."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                subscription_tier TEXT DEFAULT 'free',
                subscription_expires TIMESTAMP,
                settings TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # User bankrolls table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_bankrolls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                initial_bankroll REAL DEFAULT 1000.0,
                current_bankroll REAL DEFAULT 1000.0,
                total_profit REAL DEFAULT 0.0,
                total_bets INTEGER DEFAULT 0,
                win_count INTEGER DEFAULT 0,
                loss_count INTEGER DEFAULT 0,
                hole_count INTEGER DEFAULT 0,
                roi REAL DEFAULT 0.0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # User bets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_bets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                match_id TEXT,
                home_team TEXT,
                away_team TEXT,
                bet_type TEXT,
                stake_strong REAL,
                stake_weak REAL,
                total_stake REAL,
                odds_strong REAL,
                odds_weak REAL,
                predicted_hole_prob REAL,
                result TEXT,
                profit REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # User daily usage table (for rate limiting)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_daily_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date DATE NOT NULL,
                arbitrage_searches INTEGER DEFAULT 0,
                notifications_sent INTEGER DEFAULT 0,
                UNIQUE(user_id, date),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_bets_user_id ON user_bets(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_daily_usage ON user_daily_usage(user_id, date)")
        
        conn.commit()
        conn.close()
        
        logger.info("User database initialized")
    
    # User CRUD operations
    
    def register_user(self, telegram_id: int, username: str = None,
                     first_name: str = None, last_name: str = None,
                     initial_bankroll: float = 1000.0) -> Optional[User]:
        """Register a new user."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute("SELECT user_id FROM users WHERE telegram_id = ?", (telegram_id,))
            existing = cursor.fetchone()
            
            if existing:
                logger.warning(f"User {telegram_id} already exists")
                conn.close()
                return self.get_user_by_telegram_id(telegram_id)
            
            # Insert user
            cursor.execute("""
                INSERT INTO users (telegram_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            """, (telegram_id, username, first_name, last_name))
            
            user_id = cursor.lastrowid
            
            # Create bankroll record
            cursor.execute("""
                INSERT INTO user_bankrolls (user_id, initial_bankroll, current_bankroll)
                VALUES (?, ?, ?)
            """, (user_id, initial_bankroll, initial_bankroll))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Registered new user: {telegram_id} (ID: {user_id})")
            return self.get_user_by_id(user_id)
            
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by internal ID."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return self._row_to_user(row)
            return None
            
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return self._row_to_user(row)
            return None
            
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def update_user(self, user_id: int, **kwargs) -> bool:
        """Update user fields."""
        try:
            allowed_fields = {'username', 'first_name', 'last_name', 'is_active',
                            'subscription_tier', 'subscription_expires', 'settings'}
            
            updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
            
            if not updates:
                return False
            
            # Handle special fields
            if 'settings' in updates and isinstance(updates['settings'], dict):
                updates['settings'] = json.dumps(updates['settings'])
            if 'subscription_tier' in updates and isinstance(updates['subscription_tier'], SubscriptionTier):
                updates['subscription_tier'] = updates['subscription_tier'].value
            
            set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
            values = list(updates.values()) + [user_id]
            
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(f"UPDATE users SET {set_clause} WHERE user_id = ?", values)
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return False
    
    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate a user."""
        return self.update_user(user_id, is_active=False)
    
    def activate_user(self, user_id: int) -> bool:
        """Activate a user."""
        return self.update_user(user_id, is_active=True)
    
    def upgrade_to_premium(self, user_id: int, months: int = 1) -> bool:
        """Upgrade user to premium tier."""
        expires = datetime.now() + timedelta(days=30 * months)
        return self.update_user(
            user_id,
            subscription_tier=SubscriptionTier.PREMIUM,
            subscription_expires=expires
        )
    
    def make_admin(self, user_id: int) -> bool:
        """Make user an admin."""
        return self.update_user(user_id, subscription_tier=SubscriptionTier.ADMIN)
    
    def update_user_setting(self, user_id: int, key: str, value: Any) -> bool:
        """Update a specific user setting.
        
        Args:
            user_id: User ID
            key: Setting key (e.g., 'include_caution', 'min_roi')
            value: Setting value
            
        Returns:
            True if successful
        """
        try:
            import json
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get current settings
            cursor.execute("SELECT settings FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return False
            
            # Parse existing settings
            settings_str = row['settings'] or '{}'
            try:
                settings = json.loads(settings_str)
            except json.JSONDecodeError:
                settings = {}
            
            # Update setting
            settings[key] = value
            
            # Save back
            cursor.execute(
                "UPDATE users SET settings = ? WHERE user_id = ?",
                (json.dumps(settings), user_id)
            )
            conn.commit()
            conn.close()
            
            logger.info(f"Updated setting {key}={value} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating user setting: {e}")
            return False
    
    def get_user_setting(self, user_id: int, key: str, default: Any = None) -> Any:
        """Get a specific user setting.
        
        Args:
            user_id: User ID
            key: Setting key
            default: Default value if not found
            
        Returns:
            Setting value or default
        """
        try:
            import json
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT settings FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return default
            
            settings_str = row['settings'] or '{}'
            try:
                settings = json.loads(settings_str)
                return settings.get(key, default)
            except json.JSONDecodeError:
                return default
                
        except Exception as e:
            logger.error(f"Error getting user setting: {e}")
            return default
    
    def get_all_users(self, active_only: bool = True) -> List[User]:
        """Get all users."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            query = "SELECT * FROM users"
            if active_only:
                query += " WHERE is_active = 1"
            query += " ORDER BY registration_date DESC"
            
            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()
            
            return [self._row_to_user(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return []
    
    def get_premium_users(self) -> List[User]:
        """Get all premium users."""
        users = self.get_all_users()
        return [u for u in users if u.is_premium]
    
    def get_user_count(self) -> Dict[str, int]:
        """Get user statistics."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM users")
            total = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
            active = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE subscription_tier = 'premium' AND subscription_expires > datetime('now')")
            premium = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE subscription_tier = 'admin'")
            admins = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total': total,
                'active': active,
                'premium': premium,
                'admins': admins
            }
            
        except Exception as e:
            logger.error(f"Error getting user count: {e}")
            return {'total': 0, 'active': 0, 'premium': 0, 'admins': 0}
    
    # Bankroll operations
    
    def get_user_bankroll(self, user_id: int) -> Optional[UserBankroll]:
        """Get user's bankroll."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM user_bankrolls WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return UserBankroll(
                    id=row['id'],
                    user_id=row['user_id'],
                    initial_bankroll=row['initial_bankroll'],
                    current_bankroll=row['current_bankroll'],
                    total_profit=row['total_profit'],
                    total_bets=row['total_bets'],
                    win_count=row['win_count'],
                    loss_count=row['loss_count'],
                    hole_count=row['hole_count'],
                    roi=row['roi']
                )
            return None
            
        except Exception as e:
            logger.error(f"Error getting bankroll: {e}")
            return None
    
    def update_bankroll(self, user_id: int, profit: float, outcome: str) -> bool:
        """Update user's bankroll after a bet.
        
        outcome: 'win', 'loss', 'hole'
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get current bankroll
            cursor.execute("SELECT * FROM user_bankrolls WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return False
            
            new_bankroll = row['current_bankroll'] + profit
            new_profit = row['total_profit'] + profit
            new_bets = row['total_bets'] + 1
            
            win_count = row['win_count'] + (1 if outcome == 'win' else 0)
            loss_count = row['loss_count'] + (1 if outcome == 'loss' else 0)
            hole_count = row['hole_count'] + (1 if outcome == 'hole' else 0)
            
            roi = (new_profit / row['initial_bankroll']) * 100 if row['initial_bankroll'] > 0 else 0
            
            cursor.execute("""
                UPDATE user_bankrolls
                SET current_bankroll = ?, total_profit = ?, total_bets = ?,
                    win_count = ?, loss_count = ?, hole_count = ?,
                    roi = ?, last_updated = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (new_bankroll, new_profit, new_bets, win_count, loss_count, hole_count, roi, user_id))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating bankroll: {e}")
            return False
    
    def set_initial_bankroll(self, user_id: int, amount: float) -> bool:
        """Set user's initial bankroll."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE user_bankrolls
                SET initial_bankroll = ?, current_bankroll = ?,
                    total_profit = 0, total_bets = 0,
                    win_count = 0, loss_count = 0, hole_count = 0, roi = 0
                WHERE user_id = ?
            """, (amount, amount, user_id))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting bankroll: {e}")
            return False
    
    # Bet tracking
    
    def record_bet(self, user_id: int, bet_data: Dict[str, Any]) -> bool:
        """Record a user bet."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO user_bets
                (user_id, match_id, home_team, away_team, bet_type,
                 stake_strong, stake_weak, total_stake, odds_strong, odds_weak,
                 predicted_hole_prob)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                bet_data.get('match_id'),
                bet_data.get('home_team'),
                bet_data.get('away_team'),
                bet_data.get('bet_type'),
                bet_data.get('stake_strong'),
                bet_data.get('stake_weak'),
                bet_data.get('total_stake'),
                bet_data.get('odds_strong'),
                bet_data.get('odds_weak'),
                bet_data.get('hole_probability')
            ))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error recording bet: {e}")
            return False
    
    def get_user_bets(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Get user's bet history."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM user_bets
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting bets: {e}")
            return []
    
    # Rate limiting
    
    def check_daily_limit(self, user_id: int, limit_type: str = 'arbitrage_searches') -> int:
        """Check user's daily usage. Returns remaining uses."""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return 0
            
            # Premium/Admin have unlimited
            if user.is_premium:
                return 999
            
            # Free tier limits
            limits = {
                'arbitrage_searches': 10,
                'notifications_sent': 5
            }
            max_uses = limits.get(limit_type, 10)
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            today = datetime.now().date().isoformat()
            
            cursor.execute(f"""
                SELECT {limit_type} FROM user_daily_usage
                WHERE user_id = ? AND date = ?
            """, (user_id, today))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                used = row[0]
                return max(0, max_uses - used)
            
            return max_uses
            
        except Exception as e:
            logger.error(f"Error checking daily limit: {e}")
            return 0
    
    def increment_daily_usage(self, user_id: int, limit_type: str = 'arbitrage_searches') -> bool:
        """Increment user's daily usage counter."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            today = datetime.now().date().isoformat()
            
            # Try to insert or update
            cursor.execute(f"""
                INSERT INTO user_daily_usage (user_id, date, {limit_type})
                VALUES (?, ?, 1)
                ON CONFLICT(user_id, date) DO UPDATE SET
                {limit_type} = {limit_type} + 1
            """, (user_id, today))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error incrementing usage: {e}")
            return False
    
    # Helper methods
    
    def _row_to_user(self, row: sqlite3.Row) -> User:
        """Convert database row to User object."""
        settings = {}
        if row['settings']:
            try:
                settings = json.loads(row['settings'])
            except:
                pass
        
        subscription_expires = None
        if row['subscription_expires']:
            try:
                subscription_expires = datetime.fromisoformat(row['subscription_expires'])
            except:
                pass
        
        return User(
            user_id=row['user_id'],
            telegram_id=row['telegram_id'],
            username=row['username'],
            first_name=row['first_name'],
            last_name=row['last_name'],
            registration_date=datetime.fromisoformat(row['registration_date']) if row['registration_date'] else datetime.now(),
            is_active=bool(row['is_active']),
            subscription_tier=SubscriptionTier(row['subscription_tier']) if row['subscription_tier'] else SubscriptionTier.FREE,
            subscription_expires=subscription_expires,
            settings=settings,
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now()
        )


__all__ = ['UserManager', 'User', 'UserBankroll', 'SubscriptionTier']
