"""NHL Historical Data Collector for ML Model Training.

Collects comprehensive NHL data for 5 seasons (2019-2024) to train 
advanced ML models for overtime prediction with 80%+ accuracy target.
"""

import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import sqlite3
import requests

from utils.logger import get_logger

logger = get_logger(__name__)

# NHL API URLs
NHL_API_BASE = "https://api-web.nhle.com/v1"

# Seasons to collect (2019-2020 through 2025-2026)
SEASONS = [
    "20192020",  # 2019-2020 (COVID shortened)
    "20202021",  # 2020-2021 (COVID shortened)
    "20212022",  # 2021-2022
    "20222023",  # 2022-2023
    "20232024",  # 2023-2024
    "20242025",  # 2024-2025 (NEW)
    "20252026",  # 2025-2026 (NEW - current season)
]

# Season date ranges
SEASON_DATES = {
    "20192020": ("2019-10-02", "2020-03-11"),  # COVID pause
    "20202021": ("2021-01-13", "2021-05-19"),  # Late start
    "20212022": ("2021-10-12", "2022-04-29"),
    "20222023": ("2022-10-07", "2023-04-14"),
    "20232024": ("2023-10-10", "2024-04-18"),
    "20242025": ("2024-10-04", "2025-04-17"),  # 2024-2025 season
    "20252026": ("2025-10-07", "2026-04-16"),  # 2025-2026 current season
}

# Current season identifier
CURRENT_SEASON = "20252026"

# NHL Teams (including historical)
NHL_TEAMS = {
    "ANA": "Anaheim Ducks", "ARI": "Arizona Coyotes", "BOS": "Boston Bruins",
    "BUF": "Buffalo Sabres", "CGY": "Calgary Flames", "CAR": "Carolina Hurricanes",
    "CHI": "Chicago Blackhawks", "COL": "Colorado Avalanche", "CBJ": "Columbus Blue Jackets",
    "DAL": "Dallas Stars", "DET": "Detroit Red Wings", "EDM": "Edmonton Oilers",
    "FLA": "Florida Panthers", "LAK": "Los Angeles Kings", "MIN": "Minnesota Wild",
    "MTL": "Montreal Canadiens", "NSH": "Nashville Predators", "NJD": "New Jersey Devils",
    "NYI": "New York Islanders", "NYR": "New York Rangers", "OTT": "Ottawa Senators",
    "PHI": "Philadelphia Flyers", "PIT": "Pittsburgh Penguins", "SJS": "San Jose Sharks",
    "SEA": "Seattle Kraken", "STL": "St. Louis Blues", "TBL": "Tampa Bay Lightning",
    "TOR": "Toronto Maple Leafs", "VAN": "Vancouver Canucks", "VGK": "Vegas Golden Knights",
    "WSH": "Washington Capitals", "WPG": "Winnipeg Jets"
}


@dataclass
class CollectionStats:
    """Statistics for data collection progress."""
    total_games: int = 0
    games_collected: int = 0
    ot_games: int = 0
    so_games: int = 0
    errors: List[str] = field(default_factory=list)
    season_counts: Dict[str, int] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.now)
    
    @property
    def elapsed_minutes(self) -> float:
        return (datetime.now() - self.start_time).total_seconds() / 60
    
    @property
    def ot_percentage(self) -> float:
        if self.games_collected == 0:
            return 0.0
        return (self.ot_games + self.so_games) / self.games_collected * 100


class NHLHistoricalCollector:
    """Comprehensive NHL historical data collector.
    
    Collects 5 seasons of NHL data including:
    - Game results and overtime outcomes
    - Team statistics
    - Advanced metrics
    - Head-to-head history
    
    Example:
        >>> collector = NHLHistoricalCollector()
        >>> collector.collect_all_seasons()
        >>> stats = collector.get_collection_stats()
    """
    
    def __init__(self, db_path: str = "data/nhl_historical.db"):
        """Initialize collector.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.stats = CollectionStats()
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize database with comprehensive schema."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Main games table with comprehensive data
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nhl_games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT UNIQUE NOT NULL,
                date TEXT NOT NULL,
                season TEXT NOT NULL,
                game_type TEXT DEFAULT 'regular',
                
                -- Teams
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                home_team_id INTEGER,
                away_team_id INTEGER,
                
                -- Scores
                home_score INTEGER NOT NULL,
                away_score INTEGER NOT NULL,
                
                -- Overtime outcome
                went_to_ot INTEGER DEFAULT 0,
                went_to_so INTEGER DEFAULT 0,
                ot_winner TEXT,
                period_count INTEGER DEFAULT 3,
                
                -- Basic stats
                home_shots INTEGER DEFAULT 0,
                away_shots INTEGER DEFAULT 0,
                home_hits INTEGER DEFAULT 0,
                away_hits INTEGER DEFAULT 0,
                home_blocked INTEGER DEFAULT 0,
                away_blocked INTEGER DEFAULT 0,
                home_giveaways INTEGER DEFAULT 0,
                away_giveaways INTEGER DEFAULT 0,
                home_takeaways INTEGER DEFAULT 0,
                away_takeaways INTEGER DEFAULT 0,
                
                -- Power play
                home_pp_goals INTEGER DEFAULT 0,
                home_pp_opportunities INTEGER DEFAULT 0,
                away_pp_goals INTEGER DEFAULT 0,
                away_pp_opportunities INTEGER DEFAULT 0,
                home_pp_pct REAL DEFAULT 0,
                away_pp_pct REAL DEFAULT 0,
                
                -- Faceoffs
                home_faceoff_wins INTEGER DEFAULT 0,
                away_faceoff_wins INTEGER DEFAULT 0,
                home_faceoff_pct REAL DEFAULT 0,
                away_faceoff_pct REAL DEFAULT 0,
                
                -- PIM
                home_pim INTEGER DEFAULT 0,
                away_pim INTEGER DEFAULT 0,
                
                -- Goalie info
                home_goalie TEXT,
                away_goalie TEXT,
                home_saves INTEGER DEFAULT 0,
                away_saves INTEGER DEFAULT 0,
                home_sv_pct REAL DEFAULT 0,
                away_sv_pct REAL DEFAULT 0,
                
                -- Metadata
                venue TEXT,
                attendance INTEGER DEFAULT 0,
                game_state TEXT,
                
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Team season statistics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nhl_team_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team TEXT NOT NULL,
                season TEXT NOT NULL,
                
                -- Record
                games_played INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                ot_losses INTEGER DEFAULT 0,
                points INTEGER DEFAULT 0,
                points_pct REAL DEFAULT 0,
                
                -- Goals
                goals_for INTEGER DEFAULT 0,
                goals_against INTEGER DEFAULT 0,
                goals_per_game REAL DEFAULT 0,
                goals_against_per_game REAL DEFAULT 0,
                goal_differential INTEGER DEFAULT 0,
                
                -- Shots
                shots_for INTEGER DEFAULT 0,
                shots_against INTEGER DEFAULT 0,
                shots_per_game REAL DEFAULT 0,
                shots_against_per_game REAL DEFAULT 0,
                
                -- Special teams
                pp_goals INTEGER DEFAULT 0,
                pp_opportunities INTEGER DEFAULT 0,
                pp_pct REAL DEFAULT 0,
                pk_goals_against INTEGER DEFAULT 0,
                pk_opportunities INTEGER DEFAULT 0,
                pk_pct REAL DEFAULT 0,
                
                -- Faceoffs
                faceoff_wins INTEGER DEFAULT 0,
                faceoff_total INTEGER DEFAULT 0,
                faceoff_pct REAL DEFAULT 0,
                
                -- Overtime
                ot_wins INTEGER DEFAULT 0,
                so_wins INTEGER DEFAULT 0,
                so_losses INTEGER DEFAULT 0,
                ot_game_pct REAL DEFAULT 0,
                
                -- Home/Away
                home_wins INTEGER DEFAULT 0,
                home_losses INTEGER DEFAULT 0,
                home_ot_losses INTEGER DEFAULT 0,
                away_wins INTEGER DEFAULT 0,
                away_losses INTEGER DEFAULT 0,
                away_ot_losses INTEGER DEFAULT 0,
                
                -- Streaks/Form
                current_streak TEXT,
                last_10_record TEXT,
                
                -- Division/Conference
                division TEXT,
                conference TEXT,
                division_rank INTEGER,
                conference_rank INTEGER,
                league_rank INTEGER,
                
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(team, season)
            )
        """)
        
        # Head-to-head records
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nhl_h2h (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team1 TEXT NOT NULL,
                team2 TEXT NOT NULL,
                season TEXT NOT NULL,
                
                team1_wins INTEGER DEFAULT 0,
                team2_wins INTEGER DEFAULT 0,
                ot_games INTEGER DEFAULT 0,
                so_games INTEGER DEFAULT 0,
                team1_goals INTEGER DEFAULT 0,
                team2_goals INTEGER DEFAULT 0,
                games_played INTEGER DEFAULT 0,
                
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(team1, team2, season)
            )
        """)
        
        # Create indexes for faster queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_season ON nhl_games(season)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_date ON nhl_games(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_teams ON nhl_games(home_team, away_team)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_ot ON nhl_games(went_to_ot)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_team_stats_season ON nhl_team_stats(team, season)")
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")
    
    def _api_request(self, endpoint: str, retries: int = 3) -> Optional[Dict]:
        """Make API request with retry logic.
        
        Args:
            endpoint: API endpoint
            retries: Number of retries on failure
            
        Returns:
            JSON response or None
        """
        url = f"{NHL_API_BASE}{endpoint}"
        
        for attempt in range(retries):
            try:
                time.sleep(0.3)  # Rate limiting
                response = self.session.get(url, timeout=30)
                
                if response.status_code == 429:
                    logger.warning("Rate limited, waiting 30 seconds...")
                    time.sleep(30)
                    continue
                
                if response.status_code == 200:
                    return response.json()
                    
                logger.warning(f"API returned {response.status_code} for {endpoint}")
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt+1}): {e}")
                time.sleep(2 ** attempt)
        
        return None
    
    def collect_all_seasons(self, force: bool = False) -> CollectionStats:
        """Collect data for all 5 seasons.
        
        Args:
            force: Force re-collection even if data exists
            
        Returns:
            Collection statistics
        """
        self.stats = CollectionStats()
        self.stats.start_time = datetime.now()
        
        logger.info("=" * 60)
        logger.info("Starting comprehensive NHL data collection")
        logger.info(f"Seasons: {', '.join(SEASONS)}")
        logger.info("=" * 60)
        
        for season in SEASONS:
            logger.info(f"\n{'='*40}")
            logger.info(f"Collecting season {season}")
            logger.info(f"{'='*40}")
            
            games_collected = self.collect_season(season, force)
            self.stats.season_counts[season] = games_collected
            
            logger.info(f"Season {season}: {games_collected} games collected")
        
        # Collect team stats
        self._collect_team_stats_all_seasons()
        
        # Calculate H2H records
        self._calculate_h2h_records()
        
        # Final summary
        self._print_collection_summary()
        
        return self.stats
    
    def collect_season(self, season: str, force: bool = False, up_to_date: Optional[str] = None) -> int:
        """Collect all games for a season.
        
        Args:
            season: Season string (e.g., "20232024")
            force: Force re-collection
            up_to_date: For current season, collect only up to this date (YYYY-MM-DD)
            
        Returns:
            Number of games collected
        """
        logger.info(f"\n=== Collecting {season} season ===")
        
        # Check existing data
        if not force:
            existing = self._get_game_count(season)
            if existing > 500:  # Already have substantial data
                logger.info(f"Season {season} already has {existing} games, skipping")
                return existing
        
        # Get season date range
        if season in SEASON_DATES:
            start_date, end_date = SEASON_DATES[season]
        else:
            start_year = int(season[:4])
            start_date = f"{start_year}-10-01"
            end_date = f"{start_year+1}-04-30"
        
        # Apply up_to_date filter for current season
        if up_to_date:
            end_date = up_to_date
            logger.info(f"Filtering games up to {up_to_date}")
        
        games_collected = 0
        
        # Iterate through each team to get comprehensive schedule
        for team in NHL_TEAMS.keys():
            team_games = self._collect_team_season(team, season, up_to_date=up_to_date)
            games_collected += team_games
            
        # Remove duplicates (games appear for both teams)
        actual_games = self._get_game_count(season)
        
        logger.info(f"Season {season}: {actual_games} games collected")
        
        return actual_games
    
    def collect_all_seasons_extended(self, include_current: bool = True) -> CollectionStats:
        """Collect data for all 7 seasons (2019-2026).
        
        Args:
            include_current: Whether to include current season (up to today)
            
        Returns:
            Collection statistics
        """
        self.stats = CollectionStats()
        self.stats.start_time = datetime.now()
        
        logger.info("=" * 60)
        logger.info("Starting comprehensive NHL data collection (7 seasons)")
        logger.info(f"Seasons: {', '.join(SEASONS)}")
        logger.info("=" * 60)
        
        for season in SEASONS:
            # For current season (2025-2026), collect only up to today
            if season == CURRENT_SEASON and include_current:
                today = datetime.now().strftime('%Y-%m-%d')
                games_collected = self.collect_season(season, up_to_date=today)
            else:
                games_collected = self.collect_season(season)
            
            self.stats.season_counts[season] = games_collected
            time.sleep(2)  # Rate limiting between seasons
        
        # Collect team stats
        self._collect_team_stats_all_seasons()
        
        # Calculate H2H records
        self._calculate_h2h_records()
        
        # Final summary
        self._print_collection_summary()
        
        return self.stats
    
    def update_current_season(self) -> int:
        """Update current season data (2025-2026) with new games.
        
        Returns:
            Number of new games collected
        """
        today = datetime.now().strftime('%Y-%m-%d')
        logger.info(f"\n=== Updating current season ({CURRENT_SEASON}) up to {today} ===")
        
        # Get existing games
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT game_id FROM nhl_games WHERE season = ?",
            (CURRENT_SEASON,)
        )
        existing_ids = {row[0] for row in cursor.fetchall()}
        conn.close()
        
        logger.info(f"Existing games in current season: {len(existing_ids)}")
        
        # Collect new games
        initial_count = len(existing_ids)
        
        for team in NHL_TEAMS.keys():
            self._collect_team_season(team, CURRENT_SEASON, up_to_date=today)
        
        # Get new count
        new_count = self._get_game_count(CURRENT_SEASON)
        new_games = new_count - initial_count
        
        logger.info(f"✅ Collected {new_games} new games for current season")
        logger.info(f"Total games in {CURRENT_SEASON}: {new_count}")
        
        return new_games
    
    def _collect_team_season(self, team: str, season: str, up_to_date: Optional[str] = None) -> int:
        """Collect all games for a team in a season.
        
        Args:
            team: Team abbreviation
            season: Season string
            up_to_date: Optional date filter (YYYY-MM-DD)
            
        Returns:
            Number of games inserted
        """
        endpoint = f"/club-schedule-season/{team}/{season}"
        data = self._api_request(endpoint)
        
        if not data or 'games' not in data:
            logger.warning(f"No schedule data for {team} season {season}")
            return 0
        
        inserted = 0
        for game_data in data['games']:
            try:
                # Only process completed games
                game_state = game_data.get('gameState', '')
                if game_state not in ('FINAL', 'OFF'):
                    continue
                
                # Apply date filter for current season
                game_date = game_data.get('gameDate', '')
                if up_to_date and game_date > up_to_date:
                    continue
                
                game_id = str(game_data.get('id', ''))
                
                # Check if already exists
                if self._game_exists(game_id):
                    continue
                
                # Parse game data
                game = self._parse_game_data(game_data, season)
                if game:
                    # Get detailed boxscore
                    boxscore = self._api_request(f"/gamecenter/{game_id}/boxscore")
                    if boxscore:
                        game = self._enrich_with_boxscore(game, boxscore)
                    
                    # Insert into database
                    self._insert_game(game)
                    inserted += 1
                    self.stats.games_collected += 1
                    
                    if game.get('went_to_ot') or game.get('went_to_so'):
                        self.stats.ot_games += 1
                    
                    if inserted % 50 == 0:
                        logger.info(f"  {team}: {inserted} games processed...")
                        
            except Exception as e:
                error_msg = f"Error processing game {game_data.get('id')}: {e}"
                logger.warning(error_msg)
                self.stats.errors.append(error_msg)
        
        return inserted
    
    def _parse_game_data(self, game_data: Dict, season: str) -> Optional[Dict]:
        """Parse game data from schedule API.
        
        Args:
            game_data: Raw game data
            season: Season string
            
        Returns:
            Parsed game dict
        """
        try:
            home_team = game_data.get('homeTeam', {})
            away_team = game_data.get('awayTeam', {})
            
            # Determine OT/SO
            period_desc = game_data.get('periodDescriptor', {})
            period_type = period_desc.get('periodType', '')
            period_num = period_desc.get('number', 3)
            
            went_to_ot = period_type == 'OT' or period_num > 3
            went_to_so = period_type == 'SO'
            
            # Determine OT winner
            home_score = home_team.get('score', 0)
            away_score = away_team.get('score', 0)
            ot_winner = None
            if went_to_ot or went_to_so:
                if home_score > away_score:
                    ot_winner = home_team.get('abbrev', '')
                else:
                    ot_winner = away_team.get('abbrev', '')
            
            return {
                'game_id': str(game_data.get('id', '')),
                'date': game_data.get('gameDate', ''),
                'season': season,
                'game_type': 'regular' if str(game_data.get('gameType')) == '2' else 'playoff',
                'home_team': home_team.get('abbrev', ''),
                'away_team': away_team.get('abbrev', ''),
                'home_team_id': home_team.get('id', 0),
                'away_team_id': away_team.get('id', 0),
                'home_score': home_score,
                'away_score': away_score,
                'went_to_ot': 1 if went_to_ot else 0,
                'went_to_so': 1 if went_to_so else 0,
                'ot_winner': ot_winner,
                'period_count': period_num,
                'game_state': game_data.get('gameState', ''),
                'venue': game_data.get('venue', {}).get('default', ''),
            }
        except Exception as e:
            logger.warning(f"Failed to parse game: {e}")
            return None
    
    def _enrich_with_boxscore(self, game: Dict, boxscore: Dict) -> Dict:
        """Enrich game data with boxscore details.
        
        Args:
            game: Basic game data
            boxscore: Detailed boxscore data
            
        Returns:
            Enriched game data
        """
        try:
            # Team stats from boxscore
            home_stats = boxscore.get('homeTeam', {})
            away_stats = boxscore.get('awayTeam', {})
            
            # Get team game stats
            for team_key, prefix in [('homeTeam', 'home_'), ('awayTeam', 'away_')]:
                team_data = boxscore.get(team_key, {})
                
                game[f'{prefix}shots'] = team_data.get('sog', 0)
                
            # Box score summary
            box_summary = boxscore.get('boxscore', {})
            if box_summary:
                team_game_stats = box_summary.get('teamGameStats', [])
                
                for stat_block in team_game_stats:
                    category = stat_block.get('category', '')
                    home_val = stat_block.get('homeValue', 0)
                    away_val = stat_block.get('awayValue', 0)
                    
                    if category == 'sog':  # Shots on goal
                        game['home_shots'] = home_val if isinstance(home_val, int) else 0
                        game['away_shots'] = away_val if isinstance(away_val, int) else 0
                    elif category == 'faceoffWinningPctg':
                        game['home_faceoff_pct'] = float(home_val) if home_val else 0
                        game['away_faceoff_pct'] = float(away_val) if away_val else 0
                    elif category == 'powerPlay':
                        # Format: "1/3" (goals/opportunities)
                        if isinstance(home_val, str) and '/' in home_val:
                            parts = home_val.split('/')
                            game['home_pp_goals'] = int(parts[0])
                            game['home_pp_opportunities'] = int(parts[1])
                        if isinstance(away_val, str) and '/' in away_val:
                            parts = away_val.split('/')
                            game['away_pp_goals'] = int(parts[0])
                            game['away_pp_opportunities'] = int(parts[1])
                    elif category == 'pim':
                        game['home_pim'] = int(home_val) if isinstance(home_val, int) else 0
                        game['away_pim'] = int(away_val) if isinstance(away_val, int) else 0
                    elif category == 'hits':
                        game['home_hits'] = int(home_val) if isinstance(home_val, int) else 0
                        game['away_hits'] = int(away_val) if isinstance(away_val, int) else 0
                    elif category == 'blockedShots':
                        game['home_blocked'] = int(home_val) if isinstance(home_val, int) else 0
                        game['away_blocked'] = int(away_val) if isinstance(away_val, int) else 0
                    elif category == 'giveaways':
                        game['home_giveaways'] = int(home_val) if isinstance(home_val, int) else 0
                        game['away_giveaways'] = int(away_val) if isinstance(away_val, int) else 0
                    elif category == 'takeaways':
                        game['home_takeaways'] = int(home_val) if isinstance(home_val, int) else 0
                        game['away_takeaways'] = int(away_val) if isinstance(away_val, int) else 0
                        
            # Starting goalies
            player_by_game = boxscore.get('playerByGameStats', {})
            
            for team_key, prefix in [('homeTeam', 'home_'), ('awayTeam', 'away_')]:
                team_players = player_by_game.get(team_key, {})
                goalies = team_players.get('goalies', [])
                
                if goalies:
                    # Find starting goalie (usually first or one with most saves)
                    starter = max(goalies, key=lambda g: g.get('savePctg', 0) or 0, default=None)
                    if starter:
                        game[f'{prefix}goalie'] = starter.get('name', {}).get('default', '')
                        game[f'{prefix}saves'] = starter.get('saves', 0)
                        game[f'{prefix}sv_pct'] = starter.get('savePctg', 0) or 0
                        
        except Exception as e:
            logger.debug(f"Boxscore enrichment error: {e}")
        
        return game
    
    def _game_exists(self, game_id: str) -> bool:
        """Check if game already exists in database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM nhl_games WHERE game_id = ?", (game_id,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    
    def _insert_game(self, game: Dict) -> None:
        """Insert game into database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        columns = ', '.join(game.keys())
        placeholders = ', '.join(['?' for _ in game])
        
        try:
            cursor.execute(
                f"INSERT OR IGNORE INTO nhl_games ({columns}) VALUES ({placeholders})",
                list(game.values())
            )
            conn.commit()
        except Exception as e:
            logger.warning(f"Insert failed: {e}")
        finally:
            conn.close()
    
    def _get_game_count(self, season: str = None) -> int:
        """Get count of games in database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        if season:
            cursor.execute("SELECT COUNT(*) FROM nhl_games WHERE season = ?", (season,))
        else:
            cursor.execute("SELECT COUNT(*) FROM nhl_games")
        
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def _collect_team_stats_all_seasons(self) -> None:
        """Collect team statistics for all seasons."""
        logger.info("\nCollecting team statistics...")
        
        for season in SEASONS:
            self._collect_team_stats(season)
    
    def _collect_team_stats(self, season: str) -> None:
        """Collect team statistics from standings API."""
        endpoint = f"/standings/{season}"
        data = self._api_request(endpoint)
        
        if not data or 'standings' not in data:
            logger.warning(f"No standings data for season {season}")
            return
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        for team_data in data['standings']:
            try:
                team_abbrev = team_data.get('teamAbbrev', {}).get('default', '')
                if not team_abbrev:
                    continue
                
                stats = {
                    'team': team_abbrev,
                    'season': season,
                    'games_played': team_data.get('gamesPlayed', 0),
                    'wins': team_data.get('wins', 0),
                    'losses': team_data.get('losses', 0),
                    'ot_losses': team_data.get('otLosses', 0),
                    'points': team_data.get('points', 0),
                    'points_pct': team_data.get('pointPctg', 0),
                    'goals_for': team_data.get('goalFor', 0),
                    'goals_against': team_data.get('goalAgainst', 0),
                    'goals_per_game': team_data.get('goalFor', 0) / max(team_data.get('gamesPlayed', 1), 1),
                    'goals_against_per_game': team_data.get('goalAgainst', 0) / max(team_data.get('gamesPlayed', 1), 1),
                    'goal_differential': team_data.get('goalDifferential', 0),
                    'division': team_data.get('divisionName', ''),
                    'conference': team_data.get('conferenceName', ''),
                    'division_rank': team_data.get('divisionSequence', 0),
                    'conference_rank': team_data.get('conferenceSequence', 0),
                    'league_rank': team_data.get('leagueSequence', 0),
                    'home_wins': team_data.get('homeWins', 0),
                    'home_losses': team_data.get('homeLosses', 0),
                    'home_ot_losses': team_data.get('homeOtLosses', 0),
                    'away_wins': team_data.get('roadWins', 0),
                    'away_losses': team_data.get('roadLosses', 0),
                    'away_ot_losses': team_data.get('roadOtLosses', 0),
                    'current_streak': team_data.get('streakCode', ''),
                    'last_10_record': team_data.get('l10Record', ''),
                }
                
                # Insert or update
                columns = ', '.join(stats.keys())
                placeholders = ', '.join(['?' for _ in stats])
                update_clause = ', '.join([f"{k} = ?" for k in stats.keys()])
                
                cursor.execute(f"""
                    INSERT INTO nhl_team_stats ({columns}) VALUES ({placeholders})
                    ON CONFLICT(team, season) DO UPDATE SET {update_clause}
                """, list(stats.values()) + list(stats.values()))
                
            except Exception as e:
                logger.warning(f"Error processing team stats: {e}")
        
        conn.commit()
        conn.close()
        logger.info(f"  Season {season}: Team stats collected")
    
    def _calculate_h2h_records(self) -> None:
        """Calculate head-to-head records from game data."""
        logger.info("\nCalculating head-to-head records...")
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Get all games grouped by matchup and season
        cursor.execute("""
            SELECT 
                CASE WHEN home_team < away_team THEN home_team ELSE away_team END as team1,
                CASE WHEN home_team < away_team THEN away_team ELSE home_team END as team2,
                season,
                SUM(CASE WHEN (home_team < away_team AND home_score > away_score) OR
                              (home_team > away_team AND away_score > home_score) THEN 1 ELSE 0 END) as team1_wins,
                SUM(CASE WHEN (home_team < away_team AND away_score > home_score) OR
                              (home_team > away_team AND home_score > away_score) THEN 1 ELSE 0 END) as team2_wins,
                SUM(went_to_ot) as ot_games,
                SUM(went_to_so) as so_games,
                SUM(CASE WHEN home_team < away_team THEN home_score ELSE away_score END) as team1_goals,
                SUM(CASE WHEN home_team < away_team THEN away_score ELSE home_score END) as team2_goals,
                COUNT(*) as games_played
            FROM nhl_games
            GROUP BY team1, team2, season
        """)
        
        h2h_records = cursor.fetchall()
        
        for record in h2h_records:
            cursor.execute("""
                INSERT OR REPLACE INTO nhl_h2h 
                (team1, team2, season, team1_wins, team2_wins, ot_games, so_games, 
                 team1_goals, team2_goals, games_played)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, record)
        
        conn.commit()
        conn.close()
        logger.info(f"  H2H records calculated: {len(h2h_records)} matchups")
    
    def _print_collection_summary(self) -> None:
        """Print collection summary."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        print("\n" + "=" * 60)
        print("NHL DATA COLLECTION SUMMARY")
        print("=" * 60)
        
        # Total games
        cursor.execute("SELECT COUNT(*) FROM nhl_games")
        total_games = cursor.fetchone()[0]
        print(f"\nTotal Games Collected: {total_games}")
        
        # By season
        print("\nGames by Season:")
        cursor.execute("""
            SELECT season, COUNT(*) as games,
                   SUM(went_to_ot + went_to_so) as ot_games,
                   ROUND(100.0 * SUM(went_to_ot + went_to_so) / COUNT(*), 1) as ot_pct
            FROM nhl_games
            GROUP BY season
            ORDER BY season
        """)
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]:,} games ({row[2]} OT/SO = {row[3]}%)")
        
        # OT distribution
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN went_to_ot = 1 AND went_to_so = 0 THEN 1 ELSE 0 END) as ot_only,
                SUM(CASE WHEN went_to_so = 1 THEN 1 ELSE 0 END) as shootouts,
                SUM(CASE WHEN went_to_ot = 0 AND went_to_so = 0 THEN 1 ELSE 0 END) as regulation
            FROM nhl_games
        """)
        ot_stats = cursor.fetchone()
        
        print(f"\nOvertime Distribution:")
        print(f"  Regulation: {ot_stats[2]:,} games")
        print(f"  Overtime:   {ot_stats[0]:,} games")
        print(f"  Shootout:   {ot_stats[1]:,} games")
        
        total_ot = (ot_stats[0] or 0) + (ot_stats[1] or 0)
        if total_games > 0:
            print(f"  OT Rate:    {100*total_ot/total_games:.1f}%")
        
        # Team stats
        cursor.execute("SELECT COUNT(DISTINCT team) FROM nhl_team_stats")
        teams = cursor.fetchone()[0]
        print(f"\nTeams with Stats: {teams}")
        
        # H2H records
        cursor.execute("SELECT COUNT(*) FROM nhl_h2h")
        h2h = cursor.fetchone()[0]
        print(f"H2H Matchups: {h2h}")
        
        # Collection time
        print(f"\nCollection Time: {self.stats.elapsed_minutes:.1f} minutes")
        
        if self.stats.errors:
            print(f"Errors: {len(self.stats.errors)}")
        
        print("=" * 60)
        
        conn.close()
    
    def get_training_data(self) -> Tuple[List[Dict], List[int]]:
        """Get training data for ML model.
        
        Returns:
            Tuple of (features list, labels list)
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM nhl_games
            WHERE game_type = 'regular'
            ORDER BY date
        """)
        
        features = []
        labels = []
        
        for row in cursor.fetchall():
            game = dict(row)
            
            # Extract features
            feature_dict = {
                'home_score': game['home_score'],
                'away_score': game['away_score'],
                'score_diff': abs(game['home_score'] - game['away_score']),
                'total_goals': game['home_score'] + game['away_score'],
                'home_shots': game.get('home_shots', 0),
                'away_shots': game.get('away_shots', 0),
                'shot_diff': abs(game.get('home_shots', 0) - game.get('away_shots', 0)),
                'home_pp_pct': game.get('home_pp_pct', 0) or 0,
                'away_pp_pct': game.get('away_pp_pct', 0) or 0,
                'home_faceoff_pct': game.get('home_faceoff_pct', 0) or 0,
                'away_faceoff_pct': game.get('away_faceoff_pct', 0) or 0,
                'home_sv_pct': game.get('home_sv_pct', 0) or 0,
                'away_sv_pct': game.get('away_sv_pct', 0) or 0,
            }
            
            features.append(feature_dict)
            labels.append(1 if game['went_to_ot'] or game['went_to_so'] else 0)
        
        conn.close()
        
        logger.info(f"Prepared {len(features)} samples for training")
        logger.info(f"OT games: {sum(labels)} ({100*sum(labels)/len(labels):.1f}%)")
        
        return features, labels
    
    def export_to_csv(self, output_path: str = "data/nhl_training_data.csv") -> str:
        """Export training data to CSV.
        
        Args:
            output_path: Output file path
            
        Returns:
            Path to exported file
        """
        import csv
        
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM nhl_games ORDER BY date")
        rows = cursor.fetchall()
        
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output, 'w', newline='') as f:
            if rows:
                writer = csv.DictWriter(f, fieldnames=dict(rows[0]).keys())
                writer.writeheader()
                for row in rows:
                    writer.writerow(dict(row))
        
        conn.close()
        logger.info(f"Exported {len(rows)} games to {output_path}")
        
        return str(output)


def collect_nhl_data(force: bool = False) -> CollectionStats:
    """Main function to collect NHL data.
    
    Args:
        force: Force re-collection
        
    Returns:
        Collection statistics
    """
    collector = NHLHistoricalCollector()
    return collector.collect_all_seasons(force=force)


if __name__ == "__main__":
    stats = collect_nhl_data()
    print(f"\nCollection complete: {stats.games_collected} games")
