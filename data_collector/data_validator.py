"""Data Validator for NHL Historical Data.

Validates data quality and exports training datasets.
"""

import sqlite3
import csv
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationReport:
    """Data validation report."""
    total_games: int = 0
    games_by_season: Dict[str, int] = field(default_factory=dict)
    ot_games: int = 0
    so_games: int = 0
    ot_rate: float = 0.0
    
    # Completeness metrics
    completeness: Dict[str, float] = field(default_factory=dict)
    
    # Data quality flags
    has_sufficient_data: bool = False
    has_good_ot_distribution: bool = False
    
    # Warnings
    warnings: List[str] = field(default_factory=list)


class DataValidator:
    """Validates NHL historical data for ML training."""
    
    MIN_GAMES_REQUIRED = 5000
    MIN_OT_RATE = 0.15
    MAX_OT_RATE = 0.30
    
    def __init__(self, db_path: str = "data/nhl_historical.db"):
        """Initialize validator.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")
    
    def validate(self) -> ValidationReport:
        """Run full data validation.
        
        Returns:
            ValidationReport with results
        """
        report = ValidationReport()
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Total games
        cursor.execute("SELECT COUNT(*) FROM nhl_games")
        report.total_games = cursor.fetchone()[0]
        
        # Games by season
        cursor.execute("""
            SELECT season, COUNT(*) 
            FROM nhl_games 
            GROUP BY season 
            ORDER BY season
        """)
        report.games_by_season = {row[0]: row[1] for row in cursor.fetchall()}
        
        # OT statistics
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN went_to_ot = 1 AND went_to_so = 0 THEN 1 ELSE 0 END),
                SUM(CASE WHEN went_to_so = 1 THEN 1 ELSE 0 END)
            FROM nhl_games
        """)
        ot_stats = cursor.fetchone()
        report.ot_games = ot_stats[0] or 0
        report.so_games = ot_stats[1] or 0
        
        total_extra_time = report.ot_games + report.so_games
        report.ot_rate = total_extra_time / max(report.total_games, 1)
        
        # Completeness checks
        completeness_fields = [
            ('home_shots', 'shot_data'),
            ('home_goalie', 'goalie_data'),
            ('home_faceoff_pct', 'faceoff_data'),
            ('home_pp_opportunities', 'pp_data'),
            ('home_hits', 'hits_data'),
        ]
        
        for field, name in completeness_fields:
            if field in ('home_goalie',):
                cursor.execute(f"""
                    SELECT COUNT(*) FROM nhl_games 
                    WHERE {field} IS NOT NULL AND {field} != ''
                """)
            else:
                cursor.execute(f"""
                    SELECT COUNT(*) FROM nhl_games WHERE {field} > 0
                """)
            count = cursor.fetchone()[0]
            report.completeness[name] = count / max(report.total_games, 1)
        
        # Validate thresholds
        report.has_sufficient_data = report.total_games >= self.MIN_GAMES_REQUIRED
        report.has_good_ot_distribution = (
            self.MIN_OT_RATE <= report.ot_rate <= self.MAX_OT_RATE
        )
        
        # Generate warnings
        if not report.has_sufficient_data:
            report.warnings.append(
                f"Insufficient data: {report.total_games} games (need {self.MIN_GAMES_REQUIRED})"
            )
        
        if not report.has_good_ot_distribution:
            report.warnings.append(
                f"OT rate {report.ot_rate:.1%} outside expected range "
                f"({self.MIN_OT_RATE:.0%}-{self.MAX_OT_RATE:.0%})"
            )
        
        for name, pct in report.completeness.items():
            if pct < 0.5:
                report.warnings.append(f"Low completeness for {name}: {pct:.1%}")
        
        conn.close()
        return report
    
    def export_training_data(
        self,
        output_path: str = "data/nhl_training_data.csv"
    ) -> Tuple[int, str]:
        """Export training data to CSV.
        
        Args:
            output_path: Output file path
            
        Returns:
            Tuple of (row count, file path)
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get all games with useful features
        cursor.execute("""
            SELECT 
                game_id,
                date,
                season,
                home_team,
                away_team,
                home_score,
                away_score,
                went_to_ot,
                went_to_so,
                home_shots,
                away_shots,
                home_sv_pct,
                away_sv_pct,
                home_hits,
                away_hits,
                home_blocked,
                away_blocked,
                home_pim,
                away_pim
            FROM nhl_games
            ORDER BY date
        """)
        
        rows = cursor.fetchall()
        
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output, 'w', newline='') as f:
            if rows:
                # Write header
                writer = csv.DictWriter(f, fieldnames=dict(rows[0]).keys())
                writer.writeheader()
                
                # Write rows
                for row in rows:
                    writer.writerow(dict(row))
        
        conn.close()
        logger.info(f"Exported {len(rows)} games to {output_path}")
        
        return len(rows), str(output)
    
    def export_team_stats(
        self,
        output_path: str = "data/nhl_team_stats.csv"
    ) -> Tuple[int, str]:
        """Export team statistics to CSV.
        
        Args:
            output_path: Output file path
            
        Returns:
            Tuple of (row count, file path)
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM nhl_team_stats ORDER BY season, team")
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
        logger.info(f"Exported {len(rows)} team-season records to {output_path}")
        
        return len(rows), str(output)
    
    def generate_summary_report(
        self,
        output_path: str = "data/collection_summary.json"
    ) -> str:
        """Generate JSON summary report.
        
        Args:
            output_path: Output file path
            
        Returns:
            File path
        """
        report = self.validate()
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Get additional statistics
        cursor.execute("SELECT COUNT(DISTINCT home_team) FROM nhl_games")
        team_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM nhl_team_stats")
        team_stat_records = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM nhl_h2h")
        h2h_records = cursor.fetchone()[0]
        
        conn.close()
        
        summary = {
            "collection_date": datetime.now().isoformat(),
            "database_path": str(self.db_path),
            
            "games": {
                "total": report.total_games,
                "by_season": report.games_by_season,
            },
            
            "overtime": {
                "ot_games": report.ot_games,
                "so_games": report.so_games,
                "total": report.ot_games + report.so_games,
                "rate": round(report.ot_rate * 100, 2),
            },
            
            "teams": {
                "count": team_count,
                "stat_records": team_stat_records,
                "h2h_records": h2h_records,
            },
            
            "data_completeness": {
                k: round(v * 100, 1) for k, v in report.completeness.items()
            },
            
            "validation": {
                "has_sufficient_data": report.has_sufficient_data,
                "has_good_ot_distribution": report.has_good_ot_distribution,
                "ready_for_training": (
                    report.has_sufficient_data and report.has_good_ot_distribution
                ),
                "warnings": report.warnings,
            },
            
            "ml_training_info": {
                "target_variable": "went_to_ot OR went_to_so",
                "positive_class_ratio": round(report.ot_rate * 100, 2),
                "recommended_validation_split": 0.2,
                "suggested_cv_folds": 5,
            }
        }
        
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Summary report saved to {output_path}")
        
        return str(output)
    
    def print_report(self) -> None:
        """Print validation report to console."""
        report = self.validate()
        
        print("\n" + "=" * 60)
        print("NHL DATA VALIDATION REPORT")
        print("=" * 60)
        
        print(f"\n📊 Total Games: {report.total_games:,}")
        print(f"   Target: {self.MIN_GAMES_REQUIRED:,} minimum")
        
        print("\n📅 Games by Season:")
        for season, count in report.games_by_season.items():
            print(f"   {season[:4]}-{season[4:]}: {count:,} games")
        
        print(f"\n🏒 Overtime Statistics:")
        print(f"   OT Games: {report.ot_games:,}")
        print(f"   Shootouts: {report.so_games:,}")
        print(f"   Total OT/SO: {report.ot_games + report.so_games:,}")
        print(f"   OT Rate: {report.ot_rate:.1%}")
        
        print("\n📈 Data Completeness:")
        for name, pct in report.completeness.items():
            status = "✅" if pct >= 0.5 else "⚠️"
            print(f"   {status} {name}: {pct:.1%}")
        
        print("\n✅ Validation Status:")
        print(f"   Sufficient Data: {'✅' if report.has_sufficient_data else '❌'}")
        print(f"   Good OT Distribution: {'✅' if report.has_good_ot_distribution else '❌'}")
        
        if report.warnings:
            print("\n⚠️ Warnings:")
            for warning in report.warnings:
                print(f"   - {warning}")
        
        ready = report.has_sufficient_data and report.has_good_ot_distribution
        print(f"\n🎯 Ready for ML Training: {'✅ YES' if ready else '❌ NO'}")
        print("=" * 60)


def validate_and_export() -> Dict:
    """Main function to validate and export data.
    
    Returns:
        Summary dictionary
    """
    validator = DataValidator()
    
    # Print report
    validator.print_report()
    
    # Export data
    games_count, games_path = validator.export_training_data()
    team_count, team_path = validator.export_team_stats()
    summary_path = validator.generate_summary_report()
    
    print(f"\n📁 Files Generated:")
    print(f"   Training data: {games_path} ({games_count:,} records)")
    print(f"   Team stats: {team_path} ({team_count:,} records)")
    print(f"   Summary: {summary_path}")
    
    return {
        "training_data": games_path,
        "team_stats": team_path,
        "summary": summary_path,
        "games_count": games_count,
        "team_count": team_count,
    }


if __name__ == "__main__":
    validate_and_export()
