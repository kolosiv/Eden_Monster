"""Data module for Eden MVP v3.0.1."""
from .historical_data_fetcher import HistoricalDataFetcher
from .injury_parser import InjuryParser, PlayerInjury, create_sample_injuries

# NEW: Real data fetcher for training on verified NHL data
try:
    from .real_data_fetcher import RealNHLDataFetcher, RealHistoricalMatch, DataQualityMetrics
    REAL_DATA_AVAILABLE = True
except ImportError:
    REAL_DATA_AVAILABLE = False
    RealNHLDataFetcher = None
    RealHistoricalMatch = None
    DataQualityMetrics = None

__all__ = [
    'HistoricalDataFetcher',
    'InjuryParser',
    'PlayerInjury',
    'create_sample_injuries',
    # Real data components
    'RealNHLDataFetcher',
    'RealHistoricalMatch', 
    'DataQualityMetrics',
    'REAL_DATA_AVAILABLE'
]
