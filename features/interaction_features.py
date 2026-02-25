"""Interaction Features Module.

Creates interaction features, polynomial features, and rolling statistics.
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import numpy as np

from utils.logger import get_logger

logger = get_logger(__name__)


class InteractionFeatureExtractor:
    """Extracts interaction and polynomial features.
    
    Creates features from combinations of base features:
    - Interaction terms (feature A × feature B)
    - Polynomial terms (feature²)
    - Rolling statistics (3/5/10 game averages)
    - Exponentially weighted moving averages
    
    Example:
        >>> extractor = InteractionFeatureExtractor()
        >>> features = extractor.create_all_interactions(base_features)
    """
    
    # Key interactions to create
    INTERACTION_PAIRS = [
        # (feature_a, feature_b, name)
        ('home_advantage', 'home_form', 'home_adv_x_form'),
        ('rest_differential', 'back_to_back', 'rest_x_b2b'),
        ('goalie_quality_diff', 'defensive_power_diff', 'goalie_x_defense'),
        ('offensive_power_diff', 'opponent_goals_against', 'offense_x_opp_defense'),
        ('implied_closeness', 'h2h_ot_rate', 'closeness_x_h2h_ot'),
        ('corsi_diff', 'shooting_pct_diff', 'possession_x_shooting'),
        ('special_teams_diff', 'penalty_minutes', 'st_x_discipline'),
        ('home_momentum', 'win_rate_diff', 'momentum_x_strength'),
    ]
    
    # Features to square (polynomial)
    POLYNOMIAL_FEATURES = [
        'implied_closeness',
        'win_rate_diff',
        'goal_diff_diff',
        'goalie_quality_diff',
        'corsi_diff',
        'offensive_power_diff',
    ]
    
    # Features to cube (highly non-linear)
    CUBIC_FEATURES = [
        'implied_closeness',
        'momentum_diff',
    ]
    
    def __init__(self):
        """Initialize interaction feature extractor."""
        pass
    
    def create_interaction_features(
        self,
        features: Dict[str, float]
    ) -> Dict[str, float]:
        """Create interaction features from base features.
        
        Args:
            features: Base feature dictionary
            
        Returns:
            Dict with interaction features
        """
        interactions = {}
        
        for feat_a, feat_b, name in self.INTERACTION_PAIRS:
            val_a = features.get(feat_a, 0.0)
            val_b = features.get(feat_b, 0.0)
            
            # Normalize to prevent extreme values
            interaction_val = val_a * val_b
            
            # Clip to reasonable range
            interaction_val = np.clip(interaction_val, -100, 100)
            
            interactions[f'int_{name}'] = float(interaction_val)
        
        return interactions
    
    def create_polynomial_features(
        self,
        features: Dict[str, float]
    ) -> Dict[str, float]:
        """Create polynomial features (squared and cubic terms).
        
        Args:
            features: Base feature dictionary
            
        Returns:
            Dict with polynomial features
        """
        polynomial = {}
        
        # Squared terms
        for feat in self.POLYNOMIAL_FEATURES:
            val = features.get(feat, 0.0)
            polynomial[f'{feat}_sq'] = float(val ** 2)
        
        # Cubic terms (for highly non-linear relationships)
        for feat in self.CUBIC_FEATURES:
            val = features.get(feat, 0.0)
            polynomial[f'{feat}_cb'] = float(val ** 3)
        
        return polynomial
    
    def create_ratio_features(
        self,
        features: Dict[str, float]
    ) -> Dict[str, float]:
        """Create ratio features.
        
        Args:
            features: Base feature dictionary
            
        Returns:
            Dict with ratio features
        """
        ratios = {}
        
        # Goalie quality to team defense ratio
        goalie_q = features.get('home_goalie_quality', 50)
        defense = features.get('home_defensive_power', 50)
        ratios['goalie_defense_ratio'] = goalie_q / max(defense, 1)
        
        # Offense to opponent defense ratio
        offense = features.get('home_offensive_power', 50)
        opp_defense = features.get('away_defensive_power', 50)
        ratios['offense_vs_opp_defense'] = offense / max(opp_defense, 1)
        
        # Special teams impact
        pp = features.get('home_power_play_pct', 20)
        pk = features.get('home_penalty_kill_pct', 80)
        ratios['special_teams_strength'] = (pp + pk) / 100
        
        # Possession quality (corsi × shooting %)
        corsi = features.get('home_corsi_pct', 50)
        shooting = features.get('home_shooting_pct', 9.5)
        ratios['possession_quality'] = corsi * shooting / 50
        
        return ratios
    
    def create_rolling_features(
        self,
        game_history: List[Dict[str, float]],
        feature_names: List[str] = None
    ) -> Dict[str, float]:
        """Create rolling statistics from game history.
        
        Args:
            game_history: List of feature dicts from recent games
            feature_names: Features to calculate rolling stats for
            
        Returns:
            Dict with rolling features
        """
        if not game_history:
            return {}
        
        feature_names = feature_names or [
            'goals_scored', 'goals_against', 'shots_for',
            'power_play_pct', 'penalty_kill_pct', 'faceoff_pct'
        ]
        
        rolling = {}
        windows = [3, 5, 10]
        
        for feat in feature_names:
            values = [g.get(feat, 0) for g in game_history]
            
            for window in windows:
                if len(values) >= window:
                    window_values = values[:window]
                    rolling[f'{feat}_ma{window}'] = float(np.mean(window_values))
                    rolling[f'{feat}_std{window}'] = float(np.std(window_values))
        
        return rolling
    
    def create_ewma_features(
        self,
        game_history: List[Dict[str, float]],
        feature_names: List[str] = None,
        alpha: float = 0.3
    ) -> Dict[str, float]:
        """Create exponentially weighted moving average features.
        
        Args:
            game_history: List of feature dicts from recent games
            feature_names: Features to calculate EWMA for
            alpha: Smoothing factor (0-1), higher = more weight on recent
            
        Returns:
            Dict with EWMA features
        """
        if not game_history:
            return {}
        
        feature_names = feature_names or [
            'goals_scored', 'goals_against', 'win'
        ]
        
        ewma_features = {}
        
        for feat in feature_names:
            values = [g.get(feat, 0) for g in game_history]
            
            if not values:
                continue
            
            # Calculate EWMA
            ewma = values[0]
            for val in values[1:]:
                ewma = alpha * val + (1 - alpha) * ewma
            
            ewma_features[f'{feat}_ewma'] = float(ewma)
        
        return ewma_features
    
    def create_momentum_features(
        self,
        game_history: List[Dict[str, float]]
    ) -> Dict[str, float]:
        """Create momentum/trend features.
        
        Args:
            game_history: List of feature dicts from recent games
            
        Returns:
            Dict with momentum features
        """
        if len(game_history) < 3:
            return {
                'win_momentum': 0.0,
                'goals_momentum': 0.0,
                'form_trend': 0.0,
                'improving': 0
            }
        
        # Calculate win momentum (recent wins / total recent games)
        wins = sum(1 for g in game_history[:5] if g.get('win', 0) == 1)
        win_momentum = wins / 5 if len(game_history) >= 5 else wins / len(game_history)
        
        # Goals momentum
        goals = [g.get('goals_scored', 0) for g in game_history[:5]]
        goals_momentum = np.mean(goals) if goals else 0
        
        # Form trend (comparing recent vs older)
        if len(game_history) >= 6:
            recent_wins = sum(1 for g in game_history[:3] if g.get('win', 0) == 1)
            older_wins = sum(1 for g in game_history[3:6] if g.get('win', 0) == 1)
            form_trend = (recent_wins - older_wins) / 3
        else:
            form_trend = 0.0
        
        return {
            'win_momentum': float(win_momentum),
            'goals_momentum': float(goals_momentum),
            'form_trend': float(form_trend),
            'improving': 1 if form_trend > 0 else 0
        }
    
    def create_all_interactions(
        self,
        base_features: Dict[str, float],
        game_history: List[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """Create all interaction, polynomial, and derived features.
        
        Args:
            base_features: Base feature dictionary
            game_history: Optional game history for rolling features
            
        Returns:
            Dict with all derived features
        """
        all_features = {}
        
        # Interaction features
        all_features.update(self.create_interaction_features(base_features))
        
        # Polynomial features
        all_features.update(self.create_polynomial_features(base_features))
        
        # Ratio features
        all_features.update(self.create_ratio_features(base_features))
        
        # Rolling features (if history available)
        if game_history:
            all_features.update(self.create_rolling_features(game_history))
            all_features.update(self.create_ewma_features(game_history))
            all_features.update(self.create_momentum_features(game_history))
        
        return all_features
    
    def get_feature_names(self) -> List[str]:
        """Get list of all interaction/derived feature names."""
        names = []
        
        # Interaction names
        for _, _, name in self.INTERACTION_PAIRS:
            names.append(f'int_{name}')
        
        # Polynomial names
        for feat in self.POLYNOMIAL_FEATURES:
            names.append(f'{feat}_sq')
        for feat in self.CUBIC_FEATURES:
            names.append(f'{feat}_cb')
        
        # Ratio names
        names.extend([
            'goalie_defense_ratio',
            'offense_vs_opp_defense',
            'special_teams_strength',
            'possession_quality'
        ])
        
        # Momentum names
        names.extend([
            'win_momentum', 'goals_momentum', 'form_trend', 'improving'
        ])
        
        return names


def create_full_feature_set(
    base_features: Dict[str, float],
    player_features: Dict[str, float],
    advanced_features: Dict[str, float],
    game_history: List[Dict[str, float]] = None
) -> Dict[str, float]:
    """Combine all features into a single feature set.
    
    Args:
        base_features: Basic team/match features
        player_features: Player-related features
        advanced_features: Advanced analytics features
        game_history: Optional game history
        
    Returns:
        Complete feature dictionary
    """
    # Start with base features
    all_features = {**base_features}
    
    # Add player features
    all_features.update(player_features)
    
    # Add advanced features
    all_features.update(advanced_features)
    
    # Create interaction features
    extractor = InteractionFeatureExtractor()
    interaction_features = extractor.create_all_interactions(all_features, game_history)
    all_features.update(interaction_features)
    
    return all_features
