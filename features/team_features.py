"""Team-level feature extraction for ML model.

Extracts features related to team performance, form, and statistics.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TeamFeatures:
    """Container for team-level features."""
    team_abbrev: str
    
    # Recent form
    win_rate_last_5: float = 0.5
    win_rate_last_10: float = 0.5
    
    # Goals
    goals_for_avg: float = 2.7
    goals_against_avg: float = 2.7
    goals_for_last_5: float = 2.7
    goals_against_last_5: float = 2.7
    
    # Home/Away performance
    home_win_rate: float = 0.55
    away_win_rate: float = 0.45
    
    # Fatigue
    days_rest: int = 2
    back_to_back: bool = False
    games_last_7_days: int = 2
    
    # Special teams
    power_play_pct: float = 0.20
    penalty_kill_pct: float = 0.80
    
    # Other
    shots_per_game: float = 30.0
    shots_against_per_game: float = 30.0
    faceoff_win_pct: float = 0.50
    
    # OT performance
    ot_win_rate: float = 0.50
    ot_games_played: int = 5
    
    # Streak
    current_streak: int = 0  # Positive = wins, negative = losses
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'team_abbrev': self.team_abbrev,
            'win_rate_last_5': self.win_rate_last_5,
            'win_rate_last_10': self.win_rate_last_10,
            'goals_for_avg': self.goals_for_avg,
            'goals_against_avg': self.goals_against_avg,
            'goals_for_last_5': self.goals_for_last_5,
            'goals_against_last_5': self.goals_against_last_5,
            'home_win_rate': self.home_win_rate,
            'away_win_rate': self.away_win_rate,
            'days_rest': self.days_rest,
            'back_to_back': self.back_to_back,
            'games_last_7_days': self.games_last_7_days,
            'power_play_pct': self.power_play_pct,
            'penalty_kill_pct': self.penalty_kill_pct,
            'shots_per_game': self.shots_per_game,
            'shots_against_per_game': self.shots_against_per_game,
            'faceoff_win_pct': self.faceoff_win_pct,
            'ot_win_rate': self.ot_win_rate,
            'ot_games_played': self.ot_games_played,
            'current_streak': self.current_streak
        }


class TeamFeatureExtractor:
    """Extracts team-level features from game data.
    
    Features extracted:
    - Recent form (win rate last 5/10 games)
    - Goals scored/allowed per game (overall and recent)
    - Home/away performance
    - Fatigue indicators (back-to-back, days of rest)
    - Special teams (PP%, PK%)
    - Shot metrics
    - OT performance
    
    Example:
        >>> extractor = TeamFeatureExtractor(storage)
        >>> features = extractor.extract("TOR", before_date="2024-01-15")
    """
    
    def __init__(self, storage):
        """Initialize extractor.
        
        Args:
            storage: DataStorage instance
        """
        self.storage = storage
    
    def extract(
        self,
        team_abbrev: str,
        before_date: str = None,
        season: str = None
    ) -> TeamFeatures:
        """Extract features for a team.
        
        Args:
            team_abbrev: Team abbreviation
            before_date: Only use games before this date
            season: Season filter
            
        Returns:
            TeamFeatures object
        """
        # Get team's games
        all_games = self.storage.get_games_for_team(team_abbrev, season, limit=50)
        
        # Filter by date if specified
        if before_date:
            all_games = [g for g in all_games if g['date'] < before_date]
        
        if not all_games:
            logger.warning(f"No games found for {team_abbrev}")
            return TeamFeatures(team_abbrev=team_abbrev)
        
        # Sort by date (most recent first)
        all_games.sort(key=lambda x: x['date'], reverse=True)
        
        # Get recent games for form calculation
        last_5 = all_games[:5]
        last_10 = all_games[:10]
        
        # Calculate win rates
        win_rate_5 = self._calculate_win_rate(team_abbrev, last_5)
        win_rate_10 = self._calculate_win_rate(team_abbrev, last_10)
        
        # Calculate goals
        gf_avg, ga_avg = self._calculate_goal_averages(team_abbrev, all_games[:20])
        gf_last_5, ga_last_5 = self._calculate_goal_averages(team_abbrev, last_5)
        
        # Calculate home/away splits
        home_games = [g for g in all_games if g['home_team'] == team_abbrev]
        away_games = [g for g in all_games if g['away_team'] == team_abbrev]
        
        home_win_rate = self._calculate_win_rate(team_abbrev, home_games[:10]) if home_games else 0.55
        away_win_rate = self._calculate_win_rate(team_abbrev, away_games[:10]) if away_games else 0.45
        
        # Calculate fatigue (days since last game)
        days_rest = self._calculate_days_rest(all_games)
        back_to_back = days_rest == 1
        games_last_7 = self._calculate_games_in_period(all_games, 7)
        
        # Calculate OT performance
        ot_games = [g for g in all_games if g['went_to_ot']]
        ot_win_rate = self._calculate_win_rate(team_abbrev, ot_games) if ot_games else 0.5
        
        # Calculate streak
        streak = self._calculate_current_streak(team_abbrev, all_games)
        
        # Calculate shot metrics
        shots_for, shots_against = self._calculate_shot_averages(team_abbrev, all_games[:10])
        
        return TeamFeatures(
            team_abbrev=team_abbrev,
            win_rate_last_5=win_rate_5,
            win_rate_last_10=win_rate_10,
            goals_for_avg=gf_avg,
            goals_against_avg=ga_avg,
            goals_for_last_5=gf_last_5,
            goals_against_last_5=ga_last_5,
            home_win_rate=home_win_rate,
            away_win_rate=away_win_rate,
            days_rest=days_rest,
            back_to_back=back_to_back,
            games_last_7_days=games_last_7,
            ot_win_rate=ot_win_rate,
            ot_games_played=len(ot_games),
            current_streak=streak,
            shots_per_game=shots_for,
            shots_against_per_game=shots_against
        )
    
    def _calculate_win_rate(
        self,
        team_abbrev: str,
        games: List[Dict]
    ) -> float:
        """Calculate win rate for a set of games."""
        if not games:
            return 0.5
        
        wins = 0
        for game in games:
            is_home = game['home_team'] == team_abbrev
            if is_home:
                won = game['home_score'] > game['away_score']
            else:
                won = game['away_score'] > game['home_score']
            if won:
                wins += 1
        
        return wins / len(games)
    
    def _calculate_goal_averages(
        self,
        team_abbrev: str,
        games: List[Dict]
    ) -> tuple:
        """Calculate goals for and against averages."""
        if not games:
            return 2.7, 2.7
        
        goals_for = 0
        goals_against = 0
        
        for game in games:
            is_home = game['home_team'] == team_abbrev
            if is_home:
                goals_for += game['home_score']
                goals_against += game['away_score']
            else:
                goals_for += game['away_score']
                goals_against += game['home_score']
        
        n = len(games)
        return goals_for / n, goals_against / n
    
    def _calculate_shot_averages(
        self,
        team_abbrev: str,
        games: List[Dict]
    ) -> tuple:
        """Calculate shots for and against averages."""
        if not games:
            return 30.0, 30.0
        
        shots_for = 0
        shots_against = 0
        count = 0
        
        for game in games:
            home_shots = game.get('home_shots', 0)
            away_shots = game.get('away_shots', 0)
            
            if home_shots == 0 and away_shots == 0:
                continue
            
            is_home = game['home_team'] == team_abbrev
            if is_home:
                shots_for += home_shots
                shots_against += away_shots
            else:
                shots_for += away_shots
                shots_against += home_shots
            count += 1
        
        if count == 0:
            return 30.0, 30.0
        
        return shots_for / count, shots_against / count
    
    def _calculate_days_rest(self, games: List[Dict]) -> int:
        """Calculate days since last game."""
        if not games or len(games) < 2:
            return 2
        
        from datetime import datetime
        
        try:
            last_game_date = datetime.fromisoformat(games[0]['date'].replace('Z', '+00:00'))
            today = datetime.now(last_game_date.tzinfo) if last_game_date.tzinfo else datetime.now()
            
            days = (today - last_game_date).days
            return max(1, min(7, days))
        except:
            return 2
    
    def _calculate_games_in_period(
        self,
        games: List[Dict],
        days: int
    ) -> int:
        """Calculate number of games in the last N days."""
        from datetime import datetime, timedelta
        
        cutoff = datetime.now() - timedelta(days=days)
        count = 0
        
        for game in games:
            try:
                game_date = datetime.fromisoformat(game['date'].replace('Z', '+00:00'))
                if game_date.replace(tzinfo=None) > cutoff:
                    count += 1
            except:
                pass
        
        return count
    
    def _calculate_current_streak(
        self,
        team_abbrev: str,
        games: List[Dict]
    ) -> int:
        """Calculate current winning/losing streak."""
        if not games:
            return 0
        
        streak = 0
        first_result = None
        
        for game in games:
            is_home = game['home_team'] == team_abbrev
            if is_home:
                won = game['home_score'] > game['away_score']
            else:
                won = game['away_score'] > game['home_score']
            
            if first_result is None:
                first_result = won
                streak = 1 if won else -1
            elif won == first_result:
                streak += 1 if won else -1
            else:
                break
        
        return streak
    
    def extract_for_match(
        self,
        home_team: str,
        away_team: str,
        match_date: str = None,
        season: str = None
    ) -> Dict[str, TeamFeatures]:
        """Extract features for both teams in a match.
        
        Args:
            home_team: Home team abbreviation
            away_team: Away team abbreviation
            match_date: Match date (features calculated before this date)
            season: Season filter
            
        Returns:
            Dict with 'home' and 'away' TeamFeatures
        """
        home_features = self.extract(home_team, before_date=match_date, season=season)
        away_features = self.extract(away_team, before_date=match_date, season=season)
        
        return {
            'home': home_features,
            'away': away_features
        }
