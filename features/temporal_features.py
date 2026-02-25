"""
Temporal Feature Engineering for LSTM and Sequence Models
Eden Analytics Pro v3.0
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class SequenceConfig:
    """Configuration for sequence feature extraction"""
    lookback: int = 10  # Last N games to consider
    features_per_game: int = 8  # Features extracted per game
    include_opponent_features: bool = True
    normalize: bool = True


class TemporalFeatureEngineer:
    """Create temporal sequence features for LSTM and time-series models"""
    
    def __init__(self, config: Optional[SequenceConfig] = None):
        self.config = config or SequenceConfig()
        self.team_game_cache: Dict[str, pd.DataFrame] = {}
        self.feature_stats: Dict[str, Tuple[float, float]] = {}  # For normalization
    
    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare dataframe with necessary columns"""
        df = df.copy()
        
        # Ensure date column is datetime
        if 'date' in df.columns:
            df['game_date'] = pd.to_datetime(df['date'])
        elif 'game_date' not in df.columns:
            df['game_date'] = pd.to_datetime(df.index)
        
        # Sort by date
        df = df.sort_values('game_date').reset_index(drop=True)
        
        return df
    
    def create_team_game_history(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Create game history for each team"""
        df = self.prepare_data(df)
        
        # Get all unique teams
        all_teams = set(df['home_team'].unique()) | set(df['away_team'].unique())
        
        for team in all_teams:
            # Get all games for this team
            team_games = df[
                (df['home_team'] == team) | (df['away_team'] == team)
            ].sort_values('game_date').copy()
            
            # Calculate team-specific stats for each game
            team_stats = []
            for idx, game in team_games.iterrows():
                is_home = game['home_team'] == team
                
                stats = {
                    'game_date': game['game_date'],
                    'is_home': 1 if is_home else 0,
                    'goals_for': game['home_score'] if is_home else game['away_score'],
                    'goals_against': game['away_score'] if is_home else game['home_score'],
                    'shots_for': game.get('home_shots', 30) if is_home else game.get('away_shots', 30),
                    'shots_against': game.get('away_shots', 30) if is_home else game.get('home_shots', 30),
                    'won': 1 if (is_home and game['home_score'] > game['away_score']) or 
                           (not is_home and game['away_score'] > game['home_score']) else 0,
                    'went_to_ot': game.get('went_to_ot', 0),
                    'save_pct': game.get('home_sv_pct', 0.91) if is_home else game.get('away_sv_pct', 0.91),
                }
                team_stats.append(stats)
            
            self.team_game_cache[team] = pd.DataFrame(team_stats)
        
        return self.team_game_cache
    
    def create_team_sequences(self, df: pd.DataFrame, team: str) -> np.ndarray:
        """Create sequence of last N games for a team"""
        if team not in self.team_game_cache:
            self.create_team_game_history(df)
        
        team_games = self.team_game_cache.get(team)
        if team_games is None or len(team_games) < self.config.lookback:
            return np.array([])
        
        sequences = []
        for i in range(self.config.lookback, len(team_games)):
            # Get last N games
            sequence_games = team_games.iloc[i - self.config.lookback:i]
            
            # Extract features
            features = self._extract_sequence_features(sequence_games)
            sequences.append(features)
        
        return np.array(sequences)
    
    def _extract_sequence_features(self, games: pd.DataFrame) -> np.ndarray:
        """Extract features from game sequence"""
        features = []
        
        for _, game in games.iterrows():
            game_features = [
                game['goals_for'],
                game['goals_against'],
                game['shots_for'],
                game['shots_against'],
                game['won'],
                game['went_to_ot'],
                game['is_home'],
                game['save_pct'],
            ]
            features.extend(game_features)
        
        return np.array(features)
    
    def create_rolling_features(self, df: pd.DataFrame, windows: List[int] = [5, 10, 20]) -> pd.DataFrame:
        """Create rolling statistics for all teams"""
        df = self.prepare_data(df)
        
        # Create team game history if not exists
        if not self.team_game_cache:
            self.create_team_game_history(df)
        
        # Initialize new feature columns
        new_features = {}
        
        for idx, row in df.iterrows():
            home_team = row['home_team']
            away_team = row['away_team']
            game_date = row['game_date']
            
            # Get rolling stats for both teams
            for team_type, team in [('home', home_team), ('away', away_team)]:
                if team in self.team_game_cache:
                    team_history = self.team_game_cache[team]
                    # Only use games before current game
                    past_games = team_history[team_history['game_date'] < game_date]
                    
                    for window in windows:
                        recent = past_games.tail(window)
                        if len(recent) > 0:
                            prefix = f'{team_type}_roll{window}'
                            
                            # Calculate rolling stats
                            if f'{prefix}_win_rate' not in new_features:
                                new_features[f'{prefix}_win_rate'] = [None] * len(df)
                            new_features[f'{prefix}_win_rate'][idx] = recent['won'].mean()
                            
                            if f'{prefix}_gf' not in new_features:
                                new_features[f'{prefix}_gf'] = [None] * len(df)
                            new_features[f'{prefix}_gf'][idx] = recent['goals_for'].mean()
                            
                            if f'{prefix}_ga' not in new_features:
                                new_features[f'{prefix}_ga'] = [None] * len(df)
                            new_features[f'{prefix}_ga'][idx] = recent['goals_against'].mean()
                            
                            if f'{prefix}_ot_rate' not in new_features:
                                new_features[f'{prefix}_ot_rate'] = [None] * len(df)
                            new_features[f'{prefix}_ot_rate'][idx] = recent['went_to_ot'].mean()
                            
                            if f'{prefix}_shots' not in new_features:
                                new_features[f'{prefix}_shots'] = [None] * len(df)
                            new_features[f'{prefix}_shots'][idx] = recent['shots_for'].mean()
        
        # Add new features to dataframe
        for col, values in new_features.items():
            df[col] = values
        
        return df
    
    def create_momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create momentum and trend features"""
        df = self.prepare_data(df)
        
        if not self.team_game_cache:
            self.create_team_game_history(df)
        
        momentum_features = {}
        
        for idx, row in df.iterrows():
            game_date = row['game_date']
            
            for team_type, team in [('home', row['home_team']), ('away', row['away_team'])]:
                if team in self.team_game_cache:
                    team_history = self.team_game_cache[team]
                    past_games = team_history[team_history['game_date'] < game_date]
                    
                    # Current streak
                    streak = self._calculate_streak(past_games)
                    col = f'{team_type}_streak'
                    if col not in momentum_features:
                        momentum_features[col] = [0] * len(df)
                    momentum_features[col][idx] = streak
                    
                    # Form trend (comparing last 5 to last 10)
                    last_5 = past_games.tail(5)
                    last_10 = past_games.tail(10)
                    
                    if len(last_5) >= 5 and len(last_10) >= 10:
                        trend = last_5['won'].mean() - last_10.head(5)['won'].mean()
                    else:
                        trend = 0
                    
                    col = f'{team_type}_trend'
                    if col not in momentum_features:
                        momentum_features[col] = [0] * len(df)
                    momentum_features[col][idx] = trend
                    
                    # OT involvement trend
                    if len(last_10) >= 5:
                        ot_trend = last_5['went_to_ot'].mean() if len(last_5) > 0 else 0
                    else:
                        ot_trend = 0
                    
                    col = f'{team_type}_ot_trend'
                    if col not in momentum_features:
                        momentum_features[col] = [0] * len(df)
                    momentum_features[col][idx] = ot_trend
        
        for col, values in momentum_features.items():
            df[col] = values
        
        return df
    
    def _calculate_streak(self, games: pd.DataFrame) -> int:
        """Calculate current win/loss streak"""
        if len(games) == 0:
            return 0
        
        games = games.sort_values('game_date', ascending=False)
        streak = 0
        first_result = games.iloc[0]['won']
        
        for _, game in games.iterrows():
            if game['won'] == first_result:
                streak += 1 if first_result else -1
            else:
                break
        
        return streak
    
    def create_head_to_head_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create head-to-head historical features"""
        df = self.prepare_data(df)
        
        h2h_features = {
            'h2h_games': [],
            'h2h_home_wins': [],
            'h2h_away_wins': [],
            'h2h_ot_rate': [],
            'h2h_avg_total_goals': [],
        }
        
        for idx, row in df.iterrows():
            home_team = row['home_team']
            away_team = row['away_team']
            game_date = row['game_date']
            
            # Find previous H2H matchups
            h2h_games = df[
                (((df['home_team'] == home_team) & (df['away_team'] == away_team)) |
                 ((df['home_team'] == away_team) & (df['away_team'] == home_team))) &
                (df['game_date'] < game_date)
            ]
            
            n_games = len(h2h_games)
            h2h_features['h2h_games'].append(n_games)
            
            if n_games > 0:
                home_wins = len(h2h_games[
                    ((h2h_games['home_team'] == home_team) & (h2h_games['home_score'] > h2h_games['away_score'])) |
                    ((h2h_games['away_team'] == home_team) & (h2h_games['away_score'] > h2h_games['home_score']))
                ])
                h2h_features['h2h_home_wins'].append(home_wins / n_games)
                h2h_features['h2h_away_wins'].append(1 - home_wins / n_games)
                h2h_features['h2h_ot_rate'].append(h2h_games['went_to_ot'].mean())
                h2h_features['h2h_avg_total_goals'].append(
                    (h2h_games['home_score'] + h2h_games['away_score']).mean()
                )
            else:
                h2h_features['h2h_home_wins'].append(0.5)
                h2h_features['h2h_away_wins'].append(0.5)
                h2h_features['h2h_ot_rate'].append(0.23)  # League average
                h2h_features['h2h_avg_total_goals'].append(5.5)
        
        for col, values in h2h_features.items():
            df[col] = values
        
        return df
    
    def create_fatigue_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create fatigue and rest features"""
        df = self.prepare_data(df)
        
        fatigue_features = {
            'home_rest_days': [],
            'away_rest_days': [],
            'home_back_to_back': [],
            'away_back_to_back': [],
            'home_games_last_7d': [],
            'away_games_last_7d': [],
        }
        
        if not self.team_game_cache:
            self.create_team_game_history(df)
        
        for idx, row in df.iterrows():
            game_date = row['game_date']
            
            for team_type, team in [('home', row['home_team']), ('away', row['away_team'])]:
                if team in self.team_game_cache:
                    team_history = self.team_game_cache[team]
                    past_games = team_history[team_history['game_date'] < game_date]
                    
                    if len(past_games) > 0:
                        last_game_date = past_games.iloc[-1]['game_date']
                        rest_days = (game_date - last_game_date).days
                        
                        # Back to back
                        b2b = 1 if rest_days <= 1 else 0
                        
                        # Games in last 7 days
                        week_ago = game_date - pd.Timedelta(days=7)
                        games_7d = len(past_games[past_games['game_date'] >= week_ago])
                    else:
                        rest_days = 3
                        b2b = 0
                        games_7d = 0
                    
                    fatigue_features[f'{team_type}_rest_days'].append(min(rest_days, 10))
                    fatigue_features[f'{team_type}_back_to_back'].append(b2b)
                    fatigue_features[f'{team_type}_games_last_7d'].append(games_7d)
        
        for col, values in fatigue_features.items():
            df[col] = values
        
        return df
    
    def engineer_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply all feature engineering steps"""
        print("Engineering temporal features...")
        
        # Prepare data
        df = self.prepare_data(df)
        
        # Create team history cache
        print("  - Building team game history...")
        self.create_team_game_history(df)
        
        # Apply all feature engineering
        print("  - Creating rolling features...")
        df = self.create_rolling_features(df)
        
        print("  - Creating momentum features...")
        df = self.create_momentum_features(df)
        
        print("  - Creating head-to-head features...")
        df = self.create_head_to_head_features(df)
        
        print("  - Creating fatigue features...")
        df = self.create_fatigue_features(df)
        
        # Fill NaN values
        df = df.fillna(0)
        
        print(f"  ✓ Created {len([c for c in df.columns if 'roll' in c or 'h2h' in c or 'streak' in c or 'rest' in c])} temporal features")
        
        return df
    
    def prepare_lstm_sequences(self, df: pd.DataFrame, target_col: str = 'went_to_ot') -> Tuple[np.ndarray, np.ndarray]:
        """Prepare sequences for LSTM model"""
        df = self.prepare_data(df)
        
        if not self.team_game_cache:
            self.create_team_game_history(df)
        
        sequences = []
        targets = []
        
        for idx, row in df.iterrows():
            home_team = row['home_team']
            away_team = row['away_team']
            game_date = row['game_date']
            
            # Get sequences for both teams
            home_seq = self._get_team_sequence(home_team, game_date)
            away_seq = self._get_team_sequence(away_team, game_date)
            
            if home_seq is not None and away_seq is not None:
                # Combine home and away sequences
                combined = np.concatenate([home_seq, away_seq])
                sequences.append(combined)
                targets.append(row[target_col])
        
        if len(sequences) == 0:
            return np.array([]), np.array([])
        
        X = np.array(sequences)
        y = np.array(targets)
        
        # Reshape for LSTM: (samples, timesteps, features)
        n_samples = X.shape[0]
        n_features = X.shape[1] // (self.config.lookback * 2)  # Both teams
        X = X.reshape(n_samples, self.config.lookback * 2, n_features)
        
        return X, y
    
    def _get_team_sequence(self, team: str, game_date: pd.Timestamp) -> Optional[np.ndarray]:
        """Get sequence of features for a team before a specific date"""
        if team not in self.team_game_cache:
            return None
        
        team_history = self.team_game_cache[team]
        past_games = team_history[team_history['game_date'] < game_date].tail(self.config.lookback)
        
        if len(past_games) < self.config.lookback:
            return None
        
        return self._extract_sequence_features(past_games)
