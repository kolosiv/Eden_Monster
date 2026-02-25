"""User Notification Filters for Eden MVP Telegram Bot.

Manages filter rules for customizing which notifications users receive.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set
from datetime import datetime, time

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TimeRange:
    """Represents a time range for filtering."""
    start: time = time(0, 0)  # Start of allowed period
    end: time = time(23, 59)  # End of allowed period
    
    def contains(self, t: time) -> bool:
        """Check if time is within range."""
        if self.start <= self.end:
            return self.start <= t <= self.end
        else:  # Range crosses midnight
            return t >= self.start or t <= self.end


@dataclass
class UserFilters:
    """User-specific notification filters.
    
    Attributes:
        user_id: Telegram user ID
        enabled: Whether notifications are enabled
        min_roi: Minimum ROI threshold (percentage)
        max_hole_risk: Maximum hole probability threshold (percentage)
        leagues: Set of leagues to include (empty = all)
        time_ranges: List of allowed notification time ranges
        max_notifications_per_hour: Rate limit on notifications
        min_stake_threshold: Minimum recommended stake to notify
    """
    user_id: int
    enabled: bool = True
    min_roi: float = 2.0  # 2%
    max_hole_risk: float = 10.0  # 10%
    leagues: Set[str] = field(default_factory=lambda: {"NHL", "KHL"})
    time_ranges: List[TimeRange] = field(default_factory=list)
    max_notifications_per_hour: int = 10
    min_stake_threshold: float = 0.0
    bookmaker_blacklist: Set[str] = field(default_factory=set)
    only_recommended: bool = False  # Only send "BET" recommendations
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'user_id': self.user_id,
            'enabled': self.enabled,
            'min_roi': self.min_roi,
            'max_hole_risk': self.max_hole_risk,
            'leagues': ','.join(sorted(self.leagues)) if self.leagues else 'ALL',
            'max_notifications_per_hour': self.max_notifications_per_hour,
            'min_stake_threshold': self.min_stake_threshold,
            'bookmaker_blacklist': ','.join(sorted(self.bookmaker_blacklist)),
            'only_recommended': self.only_recommended
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserFilters':
        """Create from dictionary."""
        leagues_str = data.get('leagues', 'NHL,KHL')
        if leagues_str == 'ALL' or not leagues_str:
            leagues = set()
        else:
            leagues = set(leagues_str.split(','))
        
        blacklist_str = data.get('bookmaker_blacklist', '')
        blacklist = set(blacklist_str.split(',')) if blacklist_str else set()
        
        return cls(
            user_id=data['user_id'],
            enabled=data.get('enabled', True),
            min_roi=data.get('min_roi', 2.0),
            max_hole_risk=data.get('max_hole_risk', 10.0),
            leagues=leagues,
            max_notifications_per_hour=data.get('max_notifications_per_hour', 10),
            min_stake_threshold=data.get('min_stake_threshold', 0.0),
            bookmaker_blacklist=blacklist,
            only_recommended=data.get('only_recommended', False)
        )
    
    @classmethod
    def default(cls, user_id: int) -> 'UserFilters':
        """Create default filter settings."""
        return cls(user_id=user_id)


class FilterManager:
    """Manages user filters and applies them to opportunities."""
    
    def __init__(self, db_manager=None):
        """Initialize FilterManager.
        
        Args:
            db_manager: DatabaseManager instance for persistence
        """
        self.db_manager = db_manager
        self._cache: Dict[int, UserFilters] = {}
    
    def get_filters(self, user_id: int) -> UserFilters:
        """Get filters for a user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            UserFilters for the user
        """
        if user_id in self._cache:
            return self._cache[user_id]
        
        if self.db_manager:
            user_data = self.db_manager.get_telegram_user(user_id)
            if user_data:
                filters = UserFilters.from_dict(user_data)
                self._cache[user_id] = filters
                return filters
        
        # Return defaults if not found
        return UserFilters.default(user_id)
    
    def update_filters(self, user_id: int, **kwargs) -> UserFilters:
        """Update filters for a user.
        
        Args:
            user_id: Telegram user ID
            **kwargs: Filter attributes to update
            
        Returns:
            Updated UserFilters
        """
        filters = self.get_filters(user_id)
        
        for key, value in kwargs.items():
            if hasattr(filters, key):
                setattr(filters, key, value)
        
        self._cache[user_id] = filters
        
        if self.db_manager:
            self.db_manager.update_telegram_user(user_id, **filters.to_dict())
        
        return filters
    
    def passes_filters(self, user_id: int, analysis) -> bool:
        """Check if an analysis passes user's filters.
        
        Args:
            user_id: Telegram user ID
            analysis: MatchAnalysis object
            
        Returns:
            True if passes all filters
        """
        filters = self.get_filters(user_id)
        
        if not filters.enabled:
            return False
        
        # ROI check
        if analysis.arb_roi * 100 < filters.min_roi:
            return False
        
        # Hole risk check
        if analysis.hole_probability * 100 > filters.max_hole_risk:
            return False
        
        # Recommendation check
        if filters.only_recommended:
            if "BET" not in str(analysis.recommendation).upper():
                return False
        
        # Stake threshold check
        if filters.min_stake_threshold > 0:
            total_stake = getattr(analysis, 'total_stake', 0)
            if total_stake < filters.min_stake_threshold:
                return False
        
        # Bookmaker blacklist check
        if filters.bookmaker_blacklist:
            if analysis.bookmaker_strong in filters.bookmaker_blacklist:
                return False
            if analysis.bookmaker_weak in filters.bookmaker_blacklist:
                return False
        
        # Time range check
        if filters.time_ranges:
            current_time = datetime.now().time()
            in_allowed_time = any(
                tr.contains(current_time) for tr in filters.time_ranges
            )
            if not in_allowed_time:
                return False
        
        return True
    
    def clear_cache(self, user_id: Optional[int] = None) -> None:
        """Clear filter cache.
        
        Args:
            user_id: Specific user to clear, or None for all
        """
        if user_id:
            self._cache.pop(user_id, None)
        else:
            self._cache.clear()
