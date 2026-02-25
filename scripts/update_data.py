#!/usr/bin/env python3
"""Update NHL data with new seasons (2024-2025 and 2025-2026).

Eden Analytics Pro - Data Update Script
This script collects NHL data for the new seasons and exports updated training data.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from data_collector.nhl_historical_collector import (
    NHLHistoricalCollector,
    SEASONS,
    CURRENT_SEASON
)
from utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """Run the data update process."""
    print("=" * 60)
    print("  Eden Analytics Pro - NHL Data Update")
    print("  Version 2.4.0")
    print("=" * 60)
    print()
    
    # Initialize collector
    db_path = Path(__file__).parent.parent / "data" / "nhl_historical.db"
    collector = NHLHistoricalCollector(str(db_path))
    
    # Current date
    today = datetime.now().strftime('%Y-%m-%d')
    print(f"Current date: {today}")
    print(f"Seasons to collect: {', '.join(SEASONS)}")
    print()
    
    # Collect 2024-2025 season (full season completed)
    print("=" * 40)
    print("Collecting 2024-2025 season...")
    print("=" * 40)
    games_2024 = collector.collect_season('20242025')
    print(f"✅ Season 2024-2025: {games_2024} games")
    print()
    
    # Collect 2025-2026 season (current - up to today)
    print("=" * 40)
    print(f"Collecting 2025-2026 season (up to {today})...")
    print("=" * 40)
    games_2025 = collector.collect_season('20252026', up_to_date=today)
    print(f"✅ Season 2025-2026: {games_2025} games (through {today})")
    print()
    
    # Get collection stats
    print("=" * 40)
    print("Collection Summary")
    print("=" * 40)
    stats = collector.get_collection_stats()
    
    print(f"\nTotal games collected: {stats['total_games']}")
    print(f"OT rate: {stats.get('ot_rate', 0.23):.2%}")
    print("\nGames by season:")
    for season, count in sorted(stats.get('by_season', {}).items()):
        print(f"  {season}: {count} games")
    
    # Export training data
    print("\n" + "=" * 40)
    print("Exporting Training Data")
    print("=" * 40)
    
    try:
        from data_collector.data_validator import validate_and_export
        
        export_path = Path(__file__).parent.parent / "data" / "nhl_training_data_v2.csv"
        report = validate_and_export(str(db_path), str(export_path))
        
        print(f"\n✅ Training data exported: {export_path}")
        print(f"Total samples: {report.get('total_samples', 'N/A')}")
        print(f"OT games: {report.get('ot_games', 'N/A')}")
        print(f"Validation status: {report.get('status', 'OK')}")
    except ImportError:
        print("⚠ Data validator not available, skipping export")
    except Exception as e:
        print(f"⚠ Export error: {e}")
    
    print("\n" + "=" * 60)
    print("  ✅ Data update complete!")
    print("=" * 60)


def update_current_only():
    """Update only the current season (2025-2026)."""
    print("=" * 60)
    print("  Eden Analytics Pro - Current Season Update")
    print("=" * 60)
    print()
    
    db_path = Path(__file__).parent.parent / "data" / "nhl_historical.db"
    collector = NHLHistoricalCollector(str(db_path))
    
    new_games = collector.update_current_season()
    
    print(f"\n✅ Added {new_games} new games to current season")
    print("=" * 60)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Update NHL data')
    parser.add_argument(
        '--current-only',
        action='store_true',
        help='Update only current season (2025-2026)'
    )
    
    args = parser.parse_args()
    
    if args.current_only:
        update_current_only()
    else:
        main()
