"""Data Collector Module for Eden MVP Phase 2.

Collects NHL game data for ML model training.
Supports 7 seasons: 2019-2020 through 2025-2026.
"""

from .nhl_api import NHLAPIClient
from .data_storage import DataStorage
from .collector import DataCollector
from .nhl_historical_collector import (
    NHLHistoricalCollector, 
    collect_nhl_data, 
    CollectionStats,
    SEASONS,
    SEASON_DATES,
    CURRENT_SEASON,
)
from .data_validator import DataValidator, ValidationReport, validate_and_export

__all__ = [
    'NHLAPIClient', 
    'DataStorage', 
    'DataCollector',
    'NHLHistoricalCollector',
    'collect_nhl_data',
    'CollectionStats',
    'SEASONS',
    'SEASON_DATES',
    'CURRENT_SEASON',
    'DataValidator',
    'ValidationReport',
    'validate_and_export'
]
