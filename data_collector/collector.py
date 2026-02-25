"""Data Collector - Orchestrates NHL data collection.

Main module for collecting and managing NHL historical data.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
import time

from .nhl_api import NHLAPIClient, NHLGame
from .data_storage import DataStorage
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CollectionProgress:
    """Tracks data collection progress."""
    total_items: int = 0
    completed_items: int = 0
    current_task: str = ""
    errors: List[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    
    @property
    def progress_percent(self) -> float:
        """Get progress percentage."""
        if self.total_items == 0:
            return 0.0
        return (self.completed_items / self.total_items) * 100
    
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        return (datetime.now() - self.started_at).total_seconds()


class DataCollector:
    """Orchestrates NHL data collection.
    
    Manages the entire data collection process including:
    - Fetching historical games
    - Incremental updates
    - Progress tracking
    - Error handling and retry logic
    
    Example:
        >>> collector = DataCollector()
        >>> collector.collect_season("20232024")
        >>> collector.collect_recent_games(days=7)
    """
    
    SEASONS_TO_COLLECT = ["20232024", "20242025"]  # Last 2 seasons
    
    def __init__(
        self,
        api_client: Optional[NHLAPIClient] = None,
        storage: Optional[DataStorage] = None
    ):
        """Initialize data collector.
        
        Args:
            api_client: NHL API client instance
            storage: Data storage instance
        """
        self.api = api_client or NHLAPIClient()
        self.storage = storage or DataStorage()
        self.progress = CollectionProgress()
        self._progress_callback: Optional[Callable] = None
    
    def set_progress_callback(self, callback: Callable[[CollectionProgress], None]) -> None:
        """Set callback for progress updates.
        
        Args:
            callback: Function to call with progress updates
        """
        self._progress_callback = callback
    
    def _update_progress(
        self,
        current_task: str = None,
        completed: int = None,
        error: str = None
    ) -> None:
        """Update and report progress."""
        if current_task:
            self.progress.current_task = current_task
        if completed is not None:
            self.progress.completed_items = completed
        if error:
            self.progress.errors.append(error)
        
        if self._progress_callback:
            self._progress_callback(self.progress)
    
    def collect_season(
        self,
        season: str,
        include_playoffs: bool = False,
        force_refresh: bool = False
    ) -> int:
        """Collect all games for a season.
        
        Args:
            season: Season string (e.g., "20232024")
            include_playoffs: Include playoff games
            force_refresh: Force re-fetch even if data exists
            
        Returns:
            Number of games collected
        """
        logger.info(f"Collecting data for season {season}")
        
        # Check if we already have data
        existing_count = self.storage.get_game_count(season)
        if existing_count > 0 and not force_refresh:
            logger.info(f"Season {season} already has {existing_count} games")
            # Do incremental update instead
            return self.collect_recent_games(days=7)
        
        self.progress = CollectionProgress()
        self._update_progress(f"Fetching games for season {season}")
        
        # Fetch all games
        games = self.api.fetch_games_for_season(season, "2")  # Regular season
        
        if include_playoffs:
            playoff_games = self.api.fetch_games_for_season(season, "3")
            games.extend(playoff_games)
        
        self.progress.total_items = len(games)
        self._update_progress(f"Processing {len(games)} games")
        
        # Store games
        inserted = 0
        for i, game in enumerate(games):
            try:
                game_dict = {
                    'game_id': game.game_id,
                    'date': game.date,
                    'season': game.season or season,
                    'game_type': game.game_type,
                    'home_team': game.home_team,
                    'away_team': game.away_team,
                    'home_team_id': game.home_team_id,
                    'away_team_id': game.away_team_id,
                    'home_score': game.home_score,
                    'away_score': game.away_score,
                    'period': game.period,
                    'home_shots': game.home_shots,
                    'away_shots': game.away_shots
                }
                self.storage.insert_game(game_dict)
                inserted += 1
            except Exception as e:
                self._update_progress(error=f"Game {game.game_id}: {e}")
            
            self._update_progress(completed=i + 1)
        
        logger.info(f"Collected {inserted} games for season {season}")
        return inserted
    
    def collect_all_seasons(self, seasons: List[str] = None) -> int:
        """Collect data for multiple seasons.
        
        Args:
            seasons: List of season strings, defaults to SEASONS_TO_COLLECT
            
        Returns:
            Total games collected
        """
        seasons = seasons or self.SEASONS_TO_COLLECT
        total = 0
        
        for season in seasons:
            count = self.collect_season(season)
            total += count
            time.sleep(1)  # Small delay between seasons
        
        logger.info(f"Total games collected: {total}")
        return total
    
    def collect_recent_games(self, days: int = 7) -> int:
        """Collect games from the last N days (incremental update).
        
        Args:
            days: Number of days to look back
            
        Returns:
            Number of games collected
        """
        logger.info(f"Collecting games from last {days} days")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        self.progress = CollectionProgress()
        self._update_progress(f"Fetching recent games ({days} days)")
        
        games = self.api.fetch_schedule(
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )
        
        self.progress.total_items = len(games)
        
        inserted = 0
        for i, game in enumerate(games):
            if game.game_state in ("FINAL", "OFF"):
                try:
                    game_dict = {
                        'game_id': game.game_id,
                        'date': game.date,
                        'season': game.season,
                        'game_type': game.game_type,
                        'home_team': game.home_team,
                        'away_team': game.away_team,
                        'home_team_id': game.home_team_id,
                        'away_team_id': game.away_team_id,
                        'home_score': game.home_score,
                        'away_score': game.away_score,
                        'period': game.period,
                        'home_shots': game.home_shots,
                        'away_shots': game.away_shots
                    }
                    self.storage.insert_game(game_dict)
                    inserted += 1
                except Exception as e:
                    self._update_progress(error=f"Game {game.game_id}: {e}")
            
            self._update_progress(completed=i + 1)
        
        logger.info(f"Collected {inserted} recent games")
        return inserted
    
    def collect_team_stats(self, season: str = None) -> int:
        """Collect team statistics.
        
        Args:
            season: Season string, defaults to current
            
        Returns:
            Number of teams updated
        """
        if not season:
            # Determine current season
            now = datetime.now()
            if now.month >= 10:
                season = f"{now.year}{now.year + 1}"
            else:
                season = f"{now.year - 1}{now.year}"
        
        logger.info(f"Collecting team stats for season {season}")
        
        self._update_progress(f"Fetching team statistics")
        
        stats_list = self.api.fetch_team_stats(season)
        
        for stats in stats_list:
            try:
                stats_dict = {
                    'team_abbrev': stats.team_id,
                    'team_name': stats.team_name,
                    'season': stats.season or season,
                    'games_played': stats.games_played,
                    'wins': stats.wins,
                    'losses': stats.losses,
                    'ot_losses': stats.ot_losses,
                    'points': stats.points,
                    'goals_for': stats.goals_for,
                    'goals_against': stats.goals_against,
                    'power_play_pct': stats.power_play_pct,
                    'penalty_kill_pct': stats.penalty_kill_pct
                }
                self.storage.insert_team_stats(stats_dict)
            except Exception as e:
                logger.warning(f"Could not store stats for {stats.team_name}: {e}")
        
        logger.info(f"Collected stats for {len(stats_list)} teams")
        return len(stats_list)
    
    def get_training_data(
        self,
        min_games: int = 500,
        seasons: List[str] = None
    ) -> Dict:
        """Get data ready for ML training.
        
        Ensures we have enough data and returns statistics.
        
        Args:
            min_games: Minimum games required
            seasons: Seasons to include
            
        Returns:
            Dict with data statistics
        """
        seasons = seasons or self.SEASONS_TO_COLLECT
        
        total_games = 0
        for season in seasons:
            count = self.storage.get_game_count(season)
            total_games += count
            
            if count == 0:
                logger.info(f"No data for {season}, collecting...")
                self.collect_season(season)
        
        # Recalculate
        total_games = sum(
            self.storage.get_game_count(s) for s in seasons
        )
        
        if total_games < min_games:
            logger.warning(
                f"Only {total_games} games available, "
                f"minimum {min_games} recommended"
            )
        
        # Get OT statistics
        ot_stats = self.storage.get_ot_statistics()
        
        return {
            'total_games': total_games,
            'seasons': seasons,
            'ot_rate': ot_stats['ot_rate'],
            'avg_goals': ot_stats['avg_total_goals'],
            'ready_for_training': total_games >= min_games
        }
    
    def get_team_recent_form(
        self,
        team_abbrev: str,
        last_n_games: int = 10
    ) -> Dict:
        """Calculate recent form for a team.
        
        Args:
            team_abbrev: Team abbreviation
            last_n_games: Number of recent games to consider
            
        Returns:
            Dict with form statistics
        """
        return self.storage.calculate_team_stats_from_games(
            team_abbrev,
            last_n_games=last_n_games
        )
    
    def get_h2h_stats(
        self,
        team1: str,
        team2: str,
        limit: int = 10
    ) -> Dict:
        """Get head-to-head statistics.
        
        Args:
            team1: First team abbreviation
            team2: Second team abbreviation
            limit: Maximum games to consider
            
        Returns:
            Dict with H2H statistics
        """
        games = self.storage.get_h2h_games(team1, team2, limit)
        
        if not games:
            return {
                'games_played': 0,
                'ot_rate': 0.23,  # League average
                'team1_wins': 0,
                'team2_wins': 0
            }
        
        ot_games = sum(1 for g in games if g['went_to_ot'])
        team1_wins = sum(
            1 for g in games 
            if (g['home_team'] == team1 and g['home_score'] > g['away_score']) or
               (g['away_team'] == team1 and g['away_score'] > g['home_score'])
        )
        
        return {
            'games_played': len(games),
            'ot_rate': ot_games / len(games),
            'team1_wins': team1_wins,
            'team2_wins': len(games) - team1_wins
        }
    
    def cleanup_old_data(self, keep_seasons: int = 3) -> int:
        """Remove data older than N seasons.
        
        Args:
            keep_seasons: Number of seasons to keep
            
        Returns:
            Number of records removed
        """
        logger.info(f"Cleaning up data older than {keep_seasons} seasons")
        
        current_year = datetime.now().year
        cutoff_year = current_year - keep_seasons
        cutoff_season = f"{cutoff_year}{cutoff_year + 1}"
        
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM nhl_games WHERE season < ?",
                (cutoff_season,)
            )
            deleted = cursor.rowcount
        
        logger.info(f"Removed {deleted} old game records")
        return deleted
    
    def get_collection_status(self) -> Dict:
        """Get current data collection status.
        
        Returns:
            Dict with status information
        """
        total_games = self.storage.get_game_count()
        latest_date = self.storage.get_latest_game_date()
        ot_stats = self.storage.get_ot_statistics()
        
        return {
            'total_games': total_games,
            'latest_game_date': latest_date,
            'ot_rate': ot_stats['ot_rate'],
            'seasons': self.SEASONS_TO_COLLECT,
            'cache_enabled': self.api.cache_enabled,
            'last_collection': self.progress.started_at.isoformat() if self.progress.started_at else None
        }


def run_data_collection(seasons: List[str] = None, force: bool = False) -> Dict:
    """Convenience function to run data collection.
    
    Args:
        seasons: Seasons to collect
        force: Force refresh all data
        
    Returns:
        Collection results
    """
    collector = DataCollector()
    
    # Initialize storage
    collector.storage.initialize()
    
    # Collect data
    if force:
        total = 0
        for season in (seasons or DataCollector.SEASONS_TO_COLLECT):
            total += collector.collect_season(season, force_refresh=True)
    else:
        total = collector.collect_all_seasons(seasons)
    
    # Collect team stats
    collector.collect_team_stats()
    
    # Get training data info
    training_info = collector.get_training_data()
    
    return {
        'games_collected': total,
        'training_info': training_info,
        'status': collector.get_collection_status()
    }
