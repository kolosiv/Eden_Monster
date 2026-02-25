"""Feature Engineering - Main module for combining all features.

Orchestrates feature extraction and prepares data for ML training.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import numpy as np

from .team_features import TeamFeatureExtractor, TeamFeatures
from .match_features import MatchFeatureExtractor, MatchFeatures
from utils.logger import get_logger

logger = get_logger(__name__)


# Feature names for the ML model (28 features)
FEATURE_NAMES = [
    # Home team features (10)
    "home_win_rate_recent",
    "home_goals_for_avg",
    "home_goals_against_avg",
    "home_home_win_rate",
    "home_days_rest",
    "home_back_to_back",
    "home_ot_win_rate",
    "home_power_play_pct",
    "home_penalty_kill_pct",
    "home_streak",
    
    # Away team features (10)
    "away_win_rate_recent",
    "away_goals_for_avg",
    "away_goals_against_avg",
    "away_away_win_rate",
    "away_days_rest",
    "away_back_to_back",
    "away_ot_win_rate",
    "away_power_play_pct",
    "away_penalty_kill_pct",
    "away_streak",
    
    # Differential features (4)
    "win_rate_diff",
    "goal_diff_diff",
    "rest_differential",
    "ot_win_rate_diff",
    
    # Match features (4)
    "h2h_ot_rate",
    "same_division",
    "same_conference",
    "implied_closeness"
]


@dataclass
class FeatureSet:
    """Container for a complete feature set."""
    features: Dict[str, float]
    feature_array: np.ndarray
    home_team: str
    away_team: str
    match_date: str = ""
    went_to_ot: bool = None  # Label for training
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'features': self.features,
            'home_team': self.home_team,
            'away_team': self.away_team,
            'match_date': self.match_date,
            'went_to_ot': self.went_to_ot
        }


class FeatureEngineer:
    """Main feature engineering class.
    
    Combines team and match features into a complete feature set
    for ML model training and prediction.
    
    Example:
        >>> engineer = FeatureEngineer(storage)
        >>> features = engineer.extract_features("TOR", "BOS", "2024-01-15")
        >>> X = features.feature_array  # Use for prediction
    """
    
    def __init__(self, storage, api_client=None):
        """Initialize feature engineer.
        
        Args:
            storage: DataStorage instance
            api_client: NHLAPIClient instance (optional)
        """
        self.storage = storage
        self.team_extractor = TeamFeatureExtractor(storage)
        self.match_extractor = MatchFeatureExtractor(storage, api_client)
        self.feature_names = FEATURE_NAMES
    
    def extract_features(
        self,
        home_team: str,
        away_team: str,
        match_date: str = None,
        season: str = None,
        odds_home: float = None,
        odds_away: float = None
    ) -> FeatureSet:
        """Extract all features for a match.
        
        Args:
            home_team: Home team abbreviation
            away_team: Away team abbreviation
            match_date: Match date
            season: Season filter
            odds_home: Home team odds
            odds_away: Away team odds
            
        Returns:
            FeatureSet with all features
        """
        # Extract team features
        home_features = self.team_extractor.extract(home_team, match_date, season)
        away_features = self.team_extractor.extract(away_team, match_date, season)
        
        # Extract match features
        match_features = self.match_extractor.extract(
            home_team, away_team, match_date, odds_home, odds_away
        )
        
        # Combine into feature dict
        features = self._combine_features(home_features, away_features, match_features)
        
        # Convert to array
        feature_array = self._to_array(features)
        
        return FeatureSet(
            features=features,
            feature_array=feature_array,
            home_team=home_team,
            away_team=away_team,
            match_date=match_date or ""
        )
    
    def _combine_features(
        self,
        home: TeamFeatures,
        away: TeamFeatures,
        match: MatchFeatures
    ) -> Dict[str, float]:
        """Combine all features into a single dictionary."""
        features = {}
        
        # Home team features
        features["home_win_rate_recent"] = home.win_rate_last_5
        features["home_goals_for_avg"] = home.goals_for_avg
        features["home_goals_against_avg"] = home.goals_against_avg
        features["home_home_win_rate"] = home.home_win_rate
        features["home_days_rest"] = home.days_rest
        features["home_back_to_back"] = 1 if home.back_to_back else 0
        features["home_ot_win_rate"] = home.ot_win_rate
        features["home_power_play_pct"] = home.power_play_pct
        features["home_penalty_kill_pct"] = home.penalty_kill_pct
        features["home_streak"] = home.current_streak
        
        # Away team features
        features["away_win_rate_recent"] = away.win_rate_last_5
        features["away_goals_for_avg"] = away.goals_for_avg
        features["away_goals_against_avg"] = away.goals_against_avg
        features["away_away_win_rate"] = away.away_win_rate
        features["away_days_rest"] = away.days_rest
        features["away_back_to_back"] = 1 if away.back_to_back else 0
        features["away_ot_win_rate"] = away.ot_win_rate
        features["away_power_play_pct"] = away.power_play_pct
        features["away_penalty_kill_pct"] = away.penalty_kill_pct
        features["away_streak"] = away.current_streak
        
        # Differential features
        features["win_rate_diff"] = abs(home.win_rate_last_5 - away.win_rate_last_5)
        home_goal_diff = home.goals_for_avg - home.goals_against_avg
        away_goal_diff = away.goals_for_avg - away.goals_against_avg
        features["goal_diff_diff"] = abs(home_goal_diff - away_goal_diff)
        features["rest_differential"] = home.days_rest - away.days_rest
        features["ot_win_rate_diff"] = home.ot_win_rate - away.ot_win_rate
        
        # Match features
        features["h2h_ot_rate"] = match.h2h_ot_rate
        features["same_division"] = 1 if match.same_division else 0
        features["same_conference"] = 1 if match.same_conference else 0
        features["implied_closeness"] = match.implied_closeness
        
        return features
    
    def _to_array(self, features: Dict[str, float]) -> np.ndarray:
        """Convert feature dict to numpy array."""
        return np.array([features[name] for name in self.feature_names])
    
    def extract_training_data(
        self,
        games: List[Dict],
        season: str = None
    ) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """Extract features for multiple games (training data).
        
        Args:
            games: List of game dictionaries
            season: Season filter
            
        Returns:
            Tuple of (X features, y labels, game_ids)
        """
        X = []
        y = []
        game_ids = []
        
        for game in games:
            try:
                # Extract features using data before the game date
                feature_set = self.extract_features(
                    home_team=game['home_team'],
                    away_team=game['away_team'],
                    match_date=game['date'],
                    season=season
                )
                
                X.append(feature_set.feature_array)
                y.append(1 if game['went_to_ot'] else 0)
                game_ids.append(game['game_id'])
                
            except Exception as e:
                logger.warning(f"Could not extract features for game {game.get('game_id')}: {e}")
        
        return np.array(X), np.array(y), game_ids
    
    def scale_features(
        self,
        X: np.ndarray,
        scaler=None,
        fit: bool = False
    ) -> Tuple[np.ndarray, Any]:
        """Scale features using StandardScaler.
        
        Args:
            X: Feature array
            scaler: Existing scaler (for transform only)
            fit: Whether to fit the scaler
            
        Returns:
            Tuple of (scaled features, scaler)
        """
        try:
            from sklearn.preprocessing import StandardScaler
        except ImportError:
            logger.warning("sklearn not available, returning unscaled features")
            return X, None
        
        if scaler is None:
            scaler = StandardScaler()
        
        if fit:
            X_scaled = scaler.fit_transform(X)
        else:
            X_scaled = scaler.transform(X)
        
        return X_scaled, scaler
    
    def get_feature_importance(
        self,
        model,
        top_n: int = 10
    ) -> List[Tuple[str, float]]:
        """Get feature importance from a trained model.
        
        Args:
            model: Trained model with feature_importances_ attribute
            top_n: Number of top features to return
            
        Returns:
            List of (feature_name, importance) tuples
        """
        if not hasattr(model, 'feature_importances_'):
            return []
        
        importances = model.feature_importances_
        indices = np.argsort(importances)[::-1]
        
        result = []
        for i in indices[:top_n]:
            result.append((self.feature_names[i], importances[i]))
        
        return result
    
    def select_features(
        self,
        X: np.ndarray,
        y: np.ndarray,
        threshold: float = 0.01
    ) -> Tuple[np.ndarray, List[str]]:
        """Select features based on importance.
        
        Args:
            X: Feature array
            y: Labels
            threshold: Minimum importance threshold
            
        Returns:
            Tuple of (selected features, selected feature names)
        """
        try:
            from sklearn.ensemble import RandomForestClassifier
        except ImportError:
            return X, self.feature_names
        
        # Train a quick RF to get importance
        rf = RandomForestClassifier(n_estimators=50, random_state=42)
        rf.fit(X, y)
        
        # Select features above threshold
        importances = rf.feature_importances_
        selected_mask = importances >= threshold
        
        selected_features = [
            name for name, mask in zip(self.feature_names, selected_mask) if mask
        ]
        X_selected = X[:, selected_mask]
        
        logger.info(f"Selected {len(selected_features)}/{len(self.feature_names)} features")
        
        return X_selected, selected_features
    
    def generate_feature_report(
        self,
        model=None,
        X: np.ndarray = None,
        y: np.ndarray = None
    ) -> Dict[str, Any]:
        """Generate a feature importance report.
        
        Args:
            model: Trained model
            X: Feature array
            y: Labels
            
        Returns:
            Report dictionary
        """
        report = {
            'total_features': len(self.feature_names),
            'feature_names': self.feature_names,
            'feature_groups': {
                'home_team': [f for f in self.feature_names if f.startswith('home_')],
                'away_team': [f for f in self.feature_names if f.startswith('away_')],
                'differential': ['win_rate_diff', 'goal_diff_diff', 'rest_differential', 'ot_win_rate_diff'],
                'match': ['h2h_ot_rate', 'same_division', 'same_conference', 'implied_closeness']
            }
        }
        
        if model and hasattr(model, 'feature_importances_'):
            importances = self.get_feature_importance(model, top_n=len(self.feature_names))
            report['feature_importance'] = importances
            report['top_5_features'] = importances[:5]
        
        if X is not None:
            # Calculate feature statistics
            report['feature_stats'] = {
                name: {
                    'mean': float(X[:, i].mean()),
                    'std': float(X[:, i].std()),
                    'min': float(X[:, i].min()),
                    'max': float(X[:, i].max())
                }
                for i, name in enumerate(self.feature_names)
            }
        
        return report


def prepare_training_data(
    storage,
    seasons: List[str] = None,
    min_games: int = 500
) -> Tuple[np.ndarray, np.ndarray]:
    """Convenience function to prepare training data.
    
    Args:
        storage: DataStorage instance
        seasons: Seasons to include
        min_games: Minimum games required
        
    Returns:
        Tuple of (X, y)
    """
    seasons = seasons or ["20232024", "20242025"]
    engineer = FeatureEngineer(storage)
    
    all_games = []
    for season in seasons:
        games = storage.get_games_for_season(season)
        all_games.extend(games)
    
    if len(all_games) < min_games:
        logger.warning(f"Only {len(all_games)} games available")
    
    X, y, _ = engineer.extract_training_data(all_games)
    
    return X, y
