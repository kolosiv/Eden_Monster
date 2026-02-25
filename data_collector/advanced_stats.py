"""Advanced Team Statistics Module.

Fetches advanced analytics like Corsi, Fenwick, PDO, etc.
"""

import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
import time

from utils.logger import get_logger

logger = get_logger(__name__)


class AdvancedTeamStats(BaseModel):
    """Advanced team statistics model."""
    team_abbrev: str
    team_name: str
    season: str
    games_played: int = 0
    
    # Shooting/Scoring
    shooting_percentage: float = 0.0
    save_percentage: float = 0.0
    pdo: float = 100.0  # shooting% + save% (luck indicator)
    
    # Possession metrics
    corsi_for_pct: float = 50.0  # Shot attempts for %
    corsi_for: int = 0
    corsi_against: int = 0
    fenwick_for_pct: float = 50.0  # Unblocked shot attempts %
    fenwick_for: int = 0
    fenwick_against: int = 0
    
    # Physical play
    hits_per_game: float = 0.0
    hits_for: int = 0
    hits_against: int = 0
    blocked_shots_per_game: float = 0.0
    
    # Puck control
    takeaways_per_game: float = 0.0
    giveaways_per_game: float = 0.0
    takeaway_giveaway_ratio: float = 1.0
    
    # Face-offs
    faceoff_win_pct: float = 50.0
    faceoffs_won: int = 0
    faceoffs_lost: int = 0
    
    # Special teams
    power_play_pct: float = 0.0
    penalty_kill_pct: float = 0.0
    power_play_opportunities: int = 0
    times_shorthanded: int = 0
    
    # Goals
    goals_for_per_game: float = 0.0
    goals_against_per_game: float = 0.0
    goal_differential: float = 0.0
    
    # Shots
    shots_for_per_game: float = 0.0
    shots_against_per_game: float = 0.0
    shot_differential: float = 0.0


class AdvancedStatsCollector:
    """Collects advanced team statistics from NHL API.
    
    Provides analytics like:
    - Corsi/Fenwick (possession metrics)
    - PDO (luck indicator)
    - Shooting/Save percentages
    - Physical play stats
    
    Example:
        >>> collector = AdvancedStatsCollector()
        >>> stats = collector.fetch_team_advanced_stats("TOR")
    """
    
    BASE_URL = "https://api-web.nhle.com"
    STATS_URL = "https://api.nhle.com/stats/rest/en"
    
    def __init__(self):
        """Initialize advanced stats collector."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json'
        })
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 3600  # 1 hour
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached data if still valid."""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if datetime.now().timestamp() - timestamp < self._cache_ttl:
                return data
        return None
    
    def _set_cache(self, key: str, data: Any) -> None:
        """Cache data with timestamp."""
        self._cache[key] = (data, datetime.now().timestamp())
    
    def _make_request(self, url: str, retries: int = 3) -> Optional[Dict]:
        """Make API request with retry logic."""
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt < retries - 1:
                    time.sleep(1 * (attempt + 1))
        return None
    
    def fetch_team_advanced_stats(
        self,
        team_abbrev: str,
        season: str = None
    ) -> Optional[AdvancedTeamStats]:
        """Fetch advanced statistics for a team.
        
        Args:
            team_abbrev: Team abbreviation
            season: Season string
            
        Returns:
            AdvancedTeamStats or None
        """
        if not season:
            now = datetime.now()
            season = f"{now.year}{now.year + 1}" if now.month >= 10 else f"{now.year - 1}{now.year}"
        
        cache_key = f"advanced_{team_abbrev}_{season}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        # Fetch summary stats
        url = f"{self.STATS_URL}/team/summary?cayenneExp=seasonId={season}%20and%20teamAbbrevs='{team_abbrev}'"
        data = self._make_request(url)
        
        if not data or 'data' not in data or not data['data']:
            logger.warning(f"No advanced stats for {team_abbrev}")
            return None
        
        summary = data['data'][0]
        
        # Fetch shooting/goaltending stats
        misc_url = f"{self.STATS_URL}/team/percentages?cayenneExp=seasonId={season}%20and%20teamAbbrevs='{team_abbrev}'"
        misc_data = self._make_request(misc_url)
        
        # Fetch face-off stats
        fo_url = f"{self.STATS_URL}/team/faceoffpercentages?cayenneExp=seasonId={season}%20and%20teamAbbrevs='{team_abbrev}'"
        fo_data = self._make_request(fo_url)
        
        games_played = summary.get('gamesPlayed', 1) or 1
        
        # Parse misc data
        shooting_pct = 0.0
        save_pct = 0.0
        if misc_data and 'data' in misc_data and misc_data['data']:
            misc = misc_data['data'][0]
            shooting_pct = misc.get('shootingPct', 0.0) or 0.0
            save_pct = misc.get('savePct', 0.0) or 0.0
        
        # Parse face-off data
        fo_win_pct = 50.0
        if fo_data and 'data' in fo_data and fo_data['data']:
            fo = fo_data['data'][0]
            fo_win_pct = fo.get('faceoffWinPct', 50.0) or 50.0
        
        # Calculate derived metrics
        goals_for = summary.get('goalsFor', 0) or 0
        goals_against = summary.get('goalsAgainst', 0) or 0
        
        # Estimate Corsi/Fenwick from available data
        shots_for = summary.get('shotsForPerGame', 30.0) * games_played
        shots_against = summary.get('shotsAgainstPerGame', 30.0) * games_played
        
        # Approximate Corsi using shots + missed + blocked
        corsi_for = int(shots_for * 1.4)  # Rough estimate
        corsi_against = int(shots_against * 1.4)
        
        corsi_for_pct = (corsi_for / (corsi_for + corsi_against) * 100) if (corsi_for + corsi_against) > 0 else 50.0
        
        # Fenwick (unblocked shot attempts)
        fenwick_for = int(shots_for * 1.15)
        fenwick_against = int(shots_against * 1.15)
        fenwick_for_pct = (fenwick_for / (fenwick_for + fenwick_against) * 100) if (fenwick_for + fenwick_against) > 0 else 50.0
        
        # PDO = shooting% + save%
        pdo = (shooting_pct * 100 + save_pct * 100) if shooting_pct < 1 else (shooting_pct + save_pct)
        
        stats = AdvancedTeamStats(
            team_abbrev=team_abbrev,
            team_name=summary.get('teamFullName', team_abbrev),
            season=season,
            games_played=games_played,
            
            shooting_percentage=shooting_pct if shooting_pct > 0 else (goals_for / shots_for * 100 if shots_for > 0 else 0),
            save_percentage=save_pct if save_pct > 0 else 0.91,
            pdo=pdo if pdo > 80 else 100.0,
            
            corsi_for_pct=corsi_for_pct,
            corsi_for=corsi_for,
            corsi_against=corsi_against,
            fenwick_for_pct=fenwick_for_pct,
            fenwick_for=fenwick_for,
            fenwick_against=fenwick_against,
            
            hits_per_game=summary.get('hitsPerGame', 20.0) or 20.0,
            blocked_shots_per_game=summary.get('blockedShotsPerGame', 14.0) or 14.0,
            
            takeaways_per_game=summary.get('takeawaysPerGame', 6.0) or 6.0,
            giveaways_per_game=summary.get('giveawaysPerGame', 8.0) or 8.0,
            takeaway_giveaway_ratio=(
                (summary.get('takeawaysPerGame', 6.0) or 6.0) / 
                (summary.get('giveawaysPerGame', 8.0) or 8.0)
            ),
            
            faceoff_win_pct=fo_win_pct,
            
            power_play_pct=summary.get('powerPlayPct', 20.0) or 20.0,
            penalty_kill_pct=summary.get('penaltyKillPct', 80.0) or 80.0,
            
            goals_for_per_game=goals_for / games_played,
            goals_against_per_game=goals_against / games_played,
            goal_differential=(goals_for - goals_against) / games_played,
            
            shots_for_per_game=summary.get('shotsForPerGame', 30.0) or 30.0,
            shots_against_per_game=summary.get('shotsAgainstPerGame', 30.0) or 30.0,
            shot_differential=(
                (summary.get('shotsForPerGame', 30.0) or 30.0) - 
                (summary.get('shotsAgainstPerGame', 30.0) or 30.0)
            )
        )
        
        self._set_cache(cache_key, stats)
        return stats
    
    def fetch_all_teams_stats(
        self,
        season: str = None
    ) -> Dict[str, AdvancedTeamStats]:
        """Fetch advanced stats for all NHL teams.
        
        Args:
            season: Season string
            
        Returns:
            Dict mapping team abbrev to stats
        """
        if not season:
            now = datetime.now()
            season = f"{now.year}{now.year + 1}" if now.month >= 10 else f"{now.year - 1}{now.year}"
        
        # Get list of all teams from summary endpoint
        url = f"{self.STATS_URL}/team/summary?cayenneExp=seasonId={season}"
        data = self._make_request(url)
        
        if not data or 'data' not in data:
            logger.error("Failed to fetch team list")
            return {}
        
        all_stats = {}
        for team_data in data.get('data', []):
            team_abbrev = team_data.get('teamAbbrev')
            if team_abbrev:
                stats = self.fetch_team_advanced_stats(team_abbrev, season)
                if stats:
                    all_stats[team_abbrev] = stats
                time.sleep(0.1)  # Rate limiting
        
        return all_stats
    
    def calculate_team_metrics_differential(
        self,
        home_team: str,
        away_team: str,
        season: str = None
    ) -> Dict[str, float]:
        """Calculate metric differentials between two teams.
        
        Args:
            home_team: Home team abbreviation
            away_team: Away team abbreviation
            season: Season string
            
        Returns:
            Dict of metric differentials
        """
        home_stats = self.fetch_team_advanced_stats(home_team, season)
        away_stats = self.fetch_team_advanced_stats(away_team, season)
        
        if not home_stats or not away_stats:
            return {}
        
        return {
            'shooting_pct_diff': home_stats.shooting_percentage - away_stats.shooting_percentage,
            'save_pct_diff': home_stats.save_percentage - away_stats.save_percentage,
            'pdo_diff': home_stats.pdo - away_stats.pdo,
            'corsi_diff': home_stats.corsi_for_pct - away_stats.corsi_for_pct,
            'fenwick_diff': home_stats.fenwick_for_pct - away_stats.fenwick_for_pct,
            'hits_diff': home_stats.hits_per_game - away_stats.hits_per_game,
            'blocked_diff': home_stats.blocked_shots_per_game - away_stats.blocked_shots_per_game,
            'faceoff_diff': home_stats.faceoff_win_pct - away_stats.faceoff_win_pct,
            'special_teams_diff': (
                (home_stats.power_play_pct + home_stats.penalty_kill_pct) -
                (away_stats.power_play_pct + away_stats.penalty_kill_pct)
            ),
            'goals_per_game_diff': home_stats.goals_for_per_game - away_stats.goals_for_per_game,
            'shots_diff': home_stats.shots_for_per_game - away_stats.shots_for_per_game
        }
    
    def get_team_possession_rating(
        self,
        team_abbrev: str,
        season: str = None
    ) -> float:
        """Get a composite possession rating for a team.
        
        Args:
            team_abbrev: Team abbreviation
            season: Season string
            
        Returns:
            Possession rating (0-100)
        """
        stats = self.fetch_team_advanced_stats(team_abbrev, season)
        
        if not stats:
            return 50.0
        
        # Weighted combination of possession metrics
        rating = (
            stats.corsi_for_pct * 0.4 +
            stats.fenwick_for_pct * 0.3 +
            stats.faceoff_win_pct * 0.15 +
            (stats.takeaway_giveaway_ratio * 25) * 0.15  # Normalize to ~50
        )
        
        return min(max(rating, 0), 100)
    
    def get_team_luck_indicator(
        self,
        team_abbrev: str,
        season: str = None
    ) -> Dict[str, Any]:
        """Analyze if team is playing above/below expected performance.
        
        PDO ~100 = normal
        PDO > 102 = potentially lucky
        PDO < 98 = potentially unlucky
        
        Args:
            team_abbrev: Team abbreviation
            season: Season string
            
        Returns:
            Dict with luck analysis
        """
        stats = self.fetch_team_advanced_stats(team_abbrev, season)
        
        if not stats:
            return {'pdo': 100.0, 'luck_status': 'unknown', 'regression_risk': 0.0}
        
        pdo = stats.pdo
        
        if pdo > 102:
            luck_status = 'lucky'
            regression_risk = (pdo - 100) / 10  # How much to regress
        elif pdo < 98:
            luck_status = 'unlucky'
            regression_risk = (100 - pdo) / 10  # Upside potential
        else:
            luck_status = 'normal'
            regression_risk = 0.0
        
        return {
            'pdo': pdo,
            'luck_status': luck_status,
            'regression_risk': min(regression_risk, 1.0),
            'shooting_vs_avg': stats.shooting_percentage - 9.5,  # League avg ~9.5%
            'save_vs_avg': stats.save_percentage - 0.91  # League avg ~91%
        }
