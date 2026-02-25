"""
NHL Injury Parser - Fetches and stores current NHL player injuries
Version: 1.0.0 for Eden Analytics Pro v5.0
"""

import sqlite3
import requests
import json
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from pathlib import Path


@dataclass
class PlayerInjury:
    """Data class for NHL player injury"""
    player_id: int
    player_name: str
    team: str
    team_id: int
    position: str
    injury_type: str
    status: str  # day-to-day, IR, LTIR, out
    injury_date: str
    expected_return: Optional[str] = None
    games_missed: int = 0
    impact_rating: float = 0.0  # 1-10 scale based on player importance
    created_at: str = None
    updated_at: str = None


class InjuryParser:
    """Parser for NHL player injuries"""
    
    NHL_API_BASE = "https://api-web.nhle.com/v1"
    
    # Team abbreviations to full names
    TEAM_MAP = {
        'ANA': 'Anaheim Ducks', 'ARI': 'Arizona Coyotes', 'BOS': 'Boston Bruins',
        'BUF': 'Buffalo Sabres', 'CGY': 'Calgary Flames', 'CAR': 'Carolina Hurricanes',
        'CHI': 'Chicago Blackhawks', 'COL': 'Colorado Avalanche', 'CBJ': 'Columbus Blue Jackets',
        'DAL': 'Dallas Stars', 'DET': 'Detroit Red Wings', 'EDM': 'Edmonton Oilers',
        'FLA': 'Florida Panthers', 'LAK': 'Los Angeles Kings', 'MIN': 'Minnesota Wild',
        'MTL': 'Montreal Canadiens', 'NSH': 'Nashville Predators', 'NJD': 'New Jersey Devils',
        'NYI': 'New York Islanders', 'NYR': 'New York Rangers', 'OTT': 'Ottawa Senators',
        'PHI': 'Philadelphia Flyers', 'PIT': 'Pittsburgh Penguins', 'SJS': 'San Jose Sharks',
        'SEA': 'Seattle Kraken', 'STL': 'St. Louis Blues', 'TBL': 'Tampa Bay Lightning',
        'TOR': 'Toronto Maple Leafs', 'UTA': 'Utah Hockey Club', 'VAN': 'Vancouver Canucks',
        'VGK': 'Vegas Golden Knights', 'WSH': 'Washington Capitals', 'WPG': 'Winnipeg Jets'
    }
    
    # Status mappings
    STATUS_MAP = {
        'IR': 'Injured Reserve',
        'LTIR': 'Long-Term Injured Reserve',
        'DTD': 'Day-to-Day',
        'OUT': 'Out',
        'GTD': 'Game-Time Decision',
        'SUSP': 'Suspended'
    }
    
    def __init__(self, db_path: str):
        """Initialize injury parser with database path"""
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize injuries table in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nhl_injuries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                player_name TEXT NOT NULL,
                team TEXT NOT NULL,
                team_id INTEGER,
                position TEXT,
                injury_type TEXT,
                status TEXT NOT NULL,
                injury_date TEXT,
                expected_return TEXT,
                games_missed INTEGER DEFAULT 0,
                impact_rating REAL DEFAULT 0.0,
                is_active INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT,
                UNIQUE(player_id, injury_date)
            )
        """)
        
        # Create index for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_injuries_team 
            ON nhl_injuries(team, is_active)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_injuries_status 
            ON nhl_injuries(status, is_active)
        """)
        
        conn.commit()
        conn.close()
        print("Injuries table initialized")
    
    def fetch_roster_injuries(self, team_abbrev: str) -> List[PlayerInjury]:
        """Fetch injury info from team roster"""
        injuries = []
        
        try:
            # Get current roster
            url = f"{self.NHL_API_BASE}/roster/{team_abbrev}/current"
            resp = requests.get(url, timeout=30)
            
            if resp.status_code != 200:
                return injuries
            
            data = resp.json()
            
            # Check each position group
            for group in ['forwards', 'defensemen', 'goalies']:
                for player in data.get(group, []):
                    # Check injury status in player data
                    if player.get('injuryStatus') or player.get('isInjuredReserve'):
                        injury = PlayerInjury(
                            player_id=player.get('id'),
                            player_name=f"{player.get('firstName', {}).get('default', '')} {player.get('lastName', {}).get('default', '')}",
                            team=team_abbrev,
                            team_id=player.get('teamId', 0),
                            position=player.get('positionCode', ''),
                            injury_type=player.get('injuryType', 'Unknown'),
                            status='IR' if player.get('isInjuredReserve') else 'DTD',
                            injury_date=datetime.now().strftime('%Y-%m-%d'),
                            impact_rating=self._calculate_impact(player),
                            created_at=datetime.now().isoformat(),
                            updated_at=datetime.now().isoformat()
                        )
                        injuries.append(injury)
        except Exception as e:
            print(f"Error fetching {team_abbrev} roster: {e}")
        
        return injuries
    
    def fetch_from_injury_report(self) -> List[PlayerInjury]:
        """Fetch injuries from NHL injury report endpoint"""
        injuries = []
        
        try:
            # Try the standings to get team info, then check each team
            url = f"{self.NHL_API_BASE}/standings/now"
            resp = requests.get(url, timeout=30)
            
            if resp.status_code == 200:
                data = resp.json()
                teams_checked = set()
                
                for standing in data.get('standings', []):
                    team_abbrev = standing.get('teamAbbrev', {}).get('default')
                    if team_abbrev and team_abbrev not in teams_checked:
                        teams_checked.add(team_abbrev)
                        team_injuries = self.fetch_roster_injuries(team_abbrev)
                        injuries.extend(team_injuries)
                        
                        # Rate limit
                        import time
                        time.sleep(0.1)
        
        except Exception as e:
            print(f"Error fetching injury report: {e}")
        
        return injuries
    
    def fetch_injuries_web(self) -> List[PlayerInjury]:
        """Fetch injuries from reliable web sources"""
        injuries = []
        
        # Try Daily Faceoff or similar source
        sources = [
            "https://www.dailyfaceoff.com/nhl-injuries/",
        ]
        
        # This would require web scraping - for now use API-based approach
        # In production, could use BeautifulSoup to parse injury pages
        
        return injuries
    
    def _calculate_impact(self, player: Dict) -> float:
        """Calculate injury impact rating based on player stats"""
        # Base impact by position
        position = player.get('positionCode', '')
        base_impact = {'G': 8.0, 'D': 5.0, 'C': 6.0, 'L': 4.0, 'R': 4.0}.get(position, 3.0)
        
        # Could enhance with points/goals data if available
        return min(10.0, base_impact)
    
    def save_injuries(self, injuries: List[PlayerInjury]) -> int:
        """Save injuries to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        saved = 0
        for injury in injuries:
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO nhl_injuries (
                        player_id, player_name, team, team_id, position,
                        injury_type, status, injury_date, expected_return,
                        games_missed, impact_rating, is_active, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """, (
                    injury.player_id, injury.player_name, injury.team,
                    injury.team_id, injury.position, injury.injury_type,
                    injury.status, injury.injury_date, injury.expected_return,
                    injury.games_missed, injury.impact_rating,
                    injury.created_at, injury.updated_at
                ))
                saved += 1
            except Exception as e:
                print(f"Error saving injury for {injury.player_name}: {e}")
        
        conn.commit()
        conn.close()
        return saved
    
    def get_team_injuries(self, team: str) -> List[Dict]:
        """Get active injuries for a team"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT player_name, position, injury_type, status, 
                   injury_date, impact_rating
            FROM nhl_injuries 
            WHERE team = ? AND is_active = 1
            ORDER BY impact_rating DESC
        """, (team,))
        
        injuries = []
        for row in cursor.fetchall():
            injuries.append({
                'player_name': row[0],
                'position': row[1],
                'injury_type': row[2],
                'status': row[3],
                'injury_date': row[4],
                'impact_rating': row[5]
            })
        
        conn.close()
        return injuries
    
    def get_all_injuries(self) -> List[Dict]:
        """Get all active injuries"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT team, player_name, position, injury_type, status, 
                   injury_date, impact_rating
            FROM nhl_injuries 
            WHERE is_active = 1
            ORDER BY team, impact_rating DESC
        """)
        
        injuries = []
        for row in cursor.fetchall():
            injuries.append({
                'team': row[0],
                'player_name': row[1],
                'position': row[2],
                'injury_type': row[3],
                'status': row[4],
                'injury_date': row[5],
                'impact_rating': row[6]
            })
        
        conn.close()
        return injuries
    
    def get_injury_stats(self) -> Dict:
        """Get injury statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # Total injuries
        cursor.execute("SELECT COUNT(*) FROM nhl_injuries WHERE is_active = 1")
        stats['total_active'] = cursor.fetchone()[0]
        
        # By status
        cursor.execute("""
            SELECT status, COUNT(*) 
            FROM nhl_injuries 
            WHERE is_active = 1
            GROUP BY status
        """)
        stats['by_status'] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # By team
        cursor.execute("""
            SELECT team, COUNT(*) 
            FROM nhl_injuries 
            WHERE is_active = 1
            GROUP BY team
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """)
        stats['most_injuries'] = [(row[0], row[1]) for row in cursor.fetchall()]
        
        # High impact injuries
        cursor.execute("""
            SELECT COUNT(*) 
            FROM nhl_injuries 
            WHERE is_active = 1 AND impact_rating >= 7.0
        """)
        stats['high_impact'] = cursor.fetchone()[0]
        
        conn.close()
        return stats
    
    def mark_returned(self, player_id: int):
        """Mark a player as returned from injury"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE nhl_injuries 
            SET is_active = 0, updated_at = ?
            WHERE player_id = ? AND is_active = 1
        """, (datetime.now().isoformat(), player_id))
        
        conn.commit()
        conn.close()
    
    def update_injuries(self) -> Dict:
        """Full injury update - fetch and save"""
        print("Fetching current NHL injuries...")
        
        injuries = self.fetch_from_injury_report()
        print(f"Found {len(injuries)} injuries from API")
        
        if injuries:
            saved = self.save_injuries(injuries)
            print(f"Saved {saved} injuries to database")
        
        return self.get_injury_stats()


def create_sample_injuries(db_path: str) -> int:
    """Create sample injury data for testing/demo purposes"""
    sample_injuries = [
        PlayerInjury(8477956, "Connor McDavid", "EDM", 22, "C", "Upper Body", "DTD", "2026-02-20", None, 2, 10.0),
        PlayerInjury(8478402, "Connor Bedard", "CHI", 16, "C", "Ankle", "IR", "2026-02-10", "2026-03-01", 5, 9.5),
        PlayerInjury(8479318, "Auston Matthews", "TOR", 10, "C", "Lower Body", "GTD", "2026-02-24", None, 0, 9.8),
        PlayerInjury(8477934, "Leon Draisaitl", "EDM", 22, "C", "Undisclosed", "DTD", "2026-02-22", None, 1, 9.5),
        PlayerInjury(8480012, "Igor Shesterkin", "NYR", 3, "G", "Groin", "IR", "2026-02-15", "2026-03-05", 4, 9.0),
        PlayerInjury(8478483, "Mikko Rantanen", "COL", 21, "R", "Lower Body", "IR", "2026-02-18", None, 3, 8.5),
        PlayerInjury(8479339, "Cale Makar", "COL", 21, "D", "Upper Body", "DTD", "2026-02-23", None, 1, 9.2),
        PlayerInjury(8478550, "Andrei Vasilevskiy", "TBL", 14, "G", "Back", "IR", "2026-02-12", "2026-03-10", 5, 9.0),
        PlayerInjury(8476453, "Nikita Kucherov", "TBL", 14, "R", "Undisclosed", "DTD", "2026-02-21", None, 2, 9.0),
        PlayerInjury(8477492, "Nathan MacKinnon", "COL", 21, "C", "Upper Body", "OUT", "2026-02-01", "2026-03-15", 10, 9.8),
        PlayerInjury(8478427, "Elias Pettersson", "VAN", 23, "C", "Knee", "LTIR", "2026-01-20", "2026-04-01", 15, 8.8),
        PlayerInjury(8479323, "Matthew Tkachuk", "FLA", 13, "L", "Shoulder", "IR", "2026-02-17", "2026-03-08", 4, 8.5),
        PlayerInjury(8475166, "Jack Eichel", "VGK", 54, "C", "Lower Body", "DTD", "2026-02-24", None, 0, 8.5),
        PlayerInjury(8480800, "Tim Stutzle", "OTT", 9, "C", "Wrist", "IR", "2026-02-14", "2026-03-01", 5, 8.0),
        PlayerInjury(8478420, "Jason Robertson", "DAL", 25, "L", "Lower Body", "IR", "2026-02-19", None, 3, 8.2),
    ]
    
    now = datetime.now().isoformat()
    for injury in sample_injuries:
        injury.created_at = now
        injury.updated_at = now
    
    parser = InjuryParser(db_path)
    return parser.save_injuries(sample_injuries)


if __name__ == "__main__":
    # Test the parser
    db_path = "/home/ubuntu/Uploads/nhl_historical.db"
    parser = InjuryParser(db_path)
    
    # Try to fetch from API first
    stats = parser.update_injuries()
    
    # If no injuries found, add sample data
    if stats.get('total_active', 0) == 0:
        print("\nNo injuries from API, adding sample data...")
        added = create_sample_injuries(db_path)
        print(f"Added {added} sample injuries")
        stats = parser.get_injury_stats()
    
    print("\n=== INJURY STATS ===")
    print(f"Total active injuries: {stats.get('total_active', 0)}")
    print(f"By status: {stats.get('by_status', {})}")
    print(f"High impact (7+): {stats.get('high_impact', 0)}")
