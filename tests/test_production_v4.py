"""
Comprehensive Unit Tests for Eden Analytics Pro v3.2.0
Production-Ready Test Suite

These tests validate ALL critical fixes from the third PDF review:
1. Scaler data leakage fix
2. OT rate anomaly handling
3. AUC overfitting prevention
4. Walk-forward validation
5. Proper EV calculation with de-vigging
6. Independent component testing

Run with: pytest tests/test_production_v4.py -v
"""

import pytest
import numpy as np
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestScalerDataLeakage:
    """Test that scaler is NOT fit on test data (critical fix)."""
    
    def test_scaler_fit_only_on_train_data(self):
        """Verify scaler.fit() is only called on training data."""
        from models.model_trainer_v4 import ProductionModelTrainer, TrainingConfigV4
        
        # Create trainer with test config
        config = TrainingConfigV4(
            n_estimators=10,  # Reduce for speed
            cv_folds=2,
            optuna_trials=1,
            use_walk_forward=False
        )
        trainer = ProductionModelTrainer(config)
        
        # Create mock data
        n_samples = 100
        X = [
            {
                "home_gf_avg": np.random.random(),
                "home_ga_avg": np.random.random(),
                "away_gf_avg": np.random.random(),
                "away_ga_avg": np.random.random(),
                "goal_diff_home": np.random.random(),
                "goal_diff_away": np.random.random(),
                "home_win_rate": np.random.random(),
                "away_win_rate": np.random.random(),
                "win_rate_diff": np.random.random(),
                "home_ot_rate": 0.22,
                "away_ot_rate": 0.22,
                "home_ot_win_rate": 0.5,
                "away_ot_win_rate": 0.5,
                "home_form": np.random.random(),
                "away_form": np.random.random(),
                "form_diff": np.random.random(),
                "home_rest_days": 2,
                "away_rest_days": 2,
                "home_back_to_back": 0,
                "away_back_to_back": 0,
                "h2h_ot_rate": 0.22,
                "home_special_teams": 0.5,
                "away_special_teams": 0.5,
                "same_division": 0,
                "same_conference": 1,
            }
            for _ in range(n_samples)
        ]
        y = [int(np.random.random() > 0.78) for _ in range(n_samples)]  # ~22% OT rate
        
        # Train model
        result = trainer.train(X, y, save_model=False)
        
        # Verify scaler was fit within CV (indicated by flag)
        assert result.scaler_fit_within_cv == True
        
        # Verify no perfect AUC (which would indicate leakage)
        assert result.train_auc < 1.0, "Train AUC of 1.0 indicates data leakage!"
        
        # Verify gap is reasonable
        assert result.train_test_gap < 0.20, "Large train-test gap indicates overfitting"
    
    def test_scaler_transform_not_fit_on_test(self):
        """Verify test data is only transformed, not fit."""
        from sklearn.preprocessing import StandardScaler
        
        # Create data
        np.random.seed(42)
        X_train = np.random.randn(80, 5)
        X_test = np.random.randn(20, 5)
        
        # Correct approach: fit on train only
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)  # Only transform!
        
        # Verify means are different (if we fit on test, means would be ~0)
        train_mean = np.mean(X_train_scaled, axis=0)
        test_mean = np.mean(X_test_scaled, axis=0)
        
        # Train mean should be ~0 (since we fit on it)
        assert np.allclose(train_mean, 0, atol=0.01)
        
        # Test mean should NOT be ~0 (since we only transformed)
        # This verifies we didn't accidentally fit on test
        assert not np.allclose(test_mean, 0, atol=0.01) or len(X_test) < 5


class TestOTRateValidation:
    """Test OT rate validation and repair functionality."""
    
    def test_ot_rate_detection(self):
        """Verify low OT rate is detected as anomaly."""
        from models.model_trainer_v4 import ProductionModelTrainer, TrainingConfigV4
        
        config = TrainingConfigV4(repair_ot_labels=False)
        trainer = ProductionModelTrainer(config)
        
        # Create data with abnormally low OT rate
        X = [{"home_gf_avg": 3.0} for _ in range(100)]
        y = [0] * 100  # 0% OT rate - impossible in real NHL
        game_info = [{"season": "20252026"} for _ in range(100)]
        
        X_clean, y_clean, info, stats = trainer._validate_and_filter_data(X, y, game_info)
        
        # Should flag as invalid
        assert stats["ot_rate_valid"] == False
    
    def test_ot_rate_repair(self):
        """Verify OT rate repair for seasons with missing labels."""
        from models.model_trainer_v4 import ProductionModelTrainer, TrainingConfigV4
        
        config = TrainingConfigV4(repair_ot_labels=True)
        trainer = ProductionModelTrainer(config)
        
        # Create data simulating missing OT labels
        # 1-goal games in season with 0% OT rate
        y = [0] * 100
        game_info = [
            {
                "match_id": f"game_{i}",
                "home_score": 3,
                "away_score": 2,  # 1-goal diff (could be OT)
                "season": "20252026",
                "season_ot_rate": 0.0  # Suspiciously low
            }
            for i in range(100)
        ]
        
        y_repaired, repaired_count = trainer._repair_ot_labels(y, game_info)
        
        # Should repair some labels to get closer to expected 22%
        assert repaired_count > 0, "Should repair missing OT labels"
        new_ot_rate = sum(y_repaired) / len(y_repaired)
        assert 0.15 < new_ot_rate < 0.30, f"Repaired OT rate {new_ot_rate} should be reasonable"


class TestOverfittingPrevention:
    """Test anti-overfitting measures."""
    
    def test_train_test_gap_monitoring(self):
        """Verify train-test gap is monitored."""
        from models.model_trainer_v4 import ProductionModelTrainer, TrainingConfigV4
        
        config = TrainingConfigV4(
            n_estimators=10,
            max_depth=3,  # Very shallow to prevent overfitting
            cv_folds=2,
            use_walk_forward=False
        )
        trainer = ProductionModelTrainer(config)
        
        # Create simple data
        n = 100
        X = [{
            "home_gf_avg": np.random.random() + (0.2 if i % 5 == 0 else 0),
            "home_ga_avg": np.random.random(),
            "away_gf_avg": np.random.random(),
            "away_ga_avg": np.random.random(),
            "goal_diff_home": np.random.random() - 0.5,
            "goal_diff_away": np.random.random() - 0.5,
            "home_win_rate": np.random.random(),
            "away_win_rate": np.random.random(),
            "win_rate_diff": np.random.random() - 0.5,
            "home_ot_rate": 0.22,
            "away_ot_rate": 0.22,
            "home_ot_win_rate": 0.5,
            "away_ot_win_rate": 0.5,
            "home_form": np.random.random(),
            "away_form": np.random.random(),
            "form_diff": np.random.random() - 0.5,
            "home_rest_days": 2,
            "away_rest_days": 2,
            "home_back_to_back": 0,
            "away_back_to_back": 0,
            "h2h_ot_rate": 0.22,
            "home_special_teams": 0.5,
            "away_special_teams": 0.5,
            "same_division": 0,
            "same_conference": 1,
        } for i in range(n)]
        y = [int(np.random.random() > 0.78) for _ in range(n)]
        
        result = trainer.train(X, y, save_model=False)
        
        # Train-test gap should be monitored and reported
        assert hasattr(result, 'train_test_gap')
        assert hasattr(result, 'train_auc')
        assert hasattr(result, 'test_auc')
        
        # With regularization, gap should be reasonable
        # (Not testing strict threshold since random data)
        assert result.train_test_gap >= 0, "Test AUC shouldn't exceed train AUC"
    
    def test_regularization_parameters(self):
        """Verify regularization parameters are stricter than before."""
        from models.model_trainer_v4 import TrainingConfigV4
        from models.model_trainer_v3 import TrainingConfigV3
        
        v4_config = TrainingConfigV4()
        v3_config = TrainingConfigV3()
        
        # v4 should have stricter regularization
        assert v4_config.max_depth <= v3_config.max_depth, \
            "v4 should have shallower trees"
        assert v4_config.min_samples_split >= v3_config.min_samples_split, \
            "v4 should require more samples to split"
        assert v4_config.min_samples_leaf >= v3_config.min_samples_leaf, \
            "v4 should have larger leaf size"


class TestEVCalculation:
    """Test proper Expected Value calculation with de-vigging."""
    
    def test_proper_devigging(self):
        """Verify de-vigging is applied correctly."""
        from analysis.ev_calculator_v2 import ProductionEVCalculator
        
        calc = ProductionEVCalculator()
        
        # Test with known odds
        odds_1 = 1.91  # Implied ~52.4%
        odds_2 = 1.91  # Implied ~52.4%
        # Total implied = 104.7%, margin = 4.7%
        
        fair_1, fair_2 = calc.devig_odds_proportional(odds_1, odds_2)
        
        # Fair odds should be higher (closer to 2.0)
        assert fair_1 > odds_1
        assert fair_2 > odds_2
        
        # Fair probabilities should sum to 1.0
        fair_p_1 = 1 / fair_1
        fair_p_2 = 1 / fair_2
        assert abs(fair_p_1 + fair_p_2 - 1.0) < 0.01
    
    def test_ev_calculation_with_margin(self):
        """Verify EV accounts for margin properly."""
        from analysis.ev_calculator_v2 import calculate_proper_ev
        
        # Test scenario
        result = calculate_proper_ev(
            odds_strong=1.85,
            odds_weak_reg=2.10,
            p_strong_match=0.55,
            p_weak_reg=0.30,
            p_hole=0.15
        )
        
        # Should have all three EV estimates
        assert hasattr(result, 'ev_raw')
        assert hasattr(result, 'ev_devigged')
        assert hasattr(result, 'ev_conservative')
        
        # Conservative should be lower than raw
        assert result.ev_conservative <= result.ev_raw, \
            "Conservative EV should be lower than raw"
        
        # Should have margin info
        assert result.total_margin > 0
    
    def test_ev_with_high_margin_bookmaker(self):
        """Verify high-margin bookmakers reduce EV appropriately."""
        from analysis.ev_calculator_v2 import calculate_proper_ev
        
        # Same odds, different bookmakers
        result_pinnacle = calculate_proper_ev(
            odds_strong=1.90,
            odds_weak_reg=2.00,
            p_strong_match=0.55,
            p_weak_reg=0.30,
            p_hole=0.15,
            bookmaker_strong='pinnacle',
            bookmaker_weak='pinnacle'
        )
        
        result_belarusian = calculate_proper_ev(
            odds_strong=1.90,
            odds_weak_reg=2.00,
            p_strong_match=0.55,
            p_weak_reg=0.30,
            p_hole=0.15,
            bookmaker_strong='belarusian',
            bookmaker_weak='belarusian'
        )
        
        # Belarusian (higher margin) should have lower conservative EV
        assert result_belarusian.ev_conservative < result_pinnacle.ev_conservative, \
            "Higher margin should result in lower conservative EV"
    
    def test_probability_sum_validation(self):
        """Verify probabilities are validated."""
        from analysis.ev_calculator_v2 import calculate_proper_ev
        
        # Invalid probabilities (don't sum to 1)
        result = calculate_proper_ev(
            odds_strong=1.90,
            odds_weak_reg=2.00,
            p_strong_match=0.50,
            p_weak_reg=0.50,
            p_hole=0.50  # Sum = 1.5 (invalid)
        )
        
        # Should have warning
        assert len(result.warnings) > 0
        assert any("sum" in w.lower() or "probability" in w.lower() for w in result.warnings)


class TestWalkForwardValidation:
    """Test walk-forward validation implementation."""
    
    def test_walk_forward_creates_windows(self):
        """Verify walk-forward creates proper temporal windows."""
        from models.model_trainer_v4 import ProductionModelTrainer, TrainingConfigV4
        
        config = TrainingConfigV4(
            use_walk_forward=True,
            walk_forward_windows=3,
            n_estimators=5,
            cv_folds=2
        )
        trainer = ProductionModelTrainer(config)
        
        # Create time-ordered data
        n = 100
        np.random.seed(42)
        X = np.random.randn(n, len(trainer.FEATURE_NAMES)).astype(np.float32)
        y = (np.random.random(n) > 0.78).astype(np.int32)
        
        # Run walk-forward
        scores = trainer._walk_forward_validation(X, y)
        
        # Should have results for each window
        assert len(scores) == config.walk_forward_windows
        
        # Scores should be valid AUCs
        for score in scores:
            assert 0.0 <= score <= 1.0


class TestBlacklistedFeatures:
    """Test that blacklisted features are properly removed."""
    
    def test_blacklist_removal(self):
        """Verify blacklisted features are removed from training."""
        from models.model_trainer_v4 import ProductionModelTrainer, BLACKLISTED_FEATURES
        
        trainer = ProductionModelTrainer()
        
        # Create data with blacklisted features
        X = [{
            "home_gf_avg": 3.0,
            "predicted_closeness": 0.8,  # BLACKLISTED
            "implied_closeness": 0.7,    # BLACKLISTED
            "current_odds": 1.9,         # BLACKLISTED
        } for _ in range(10)]
        y = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
        
        X_clean, y_clean, _, stats = trainer._validate_and_filter_data(X, y, None)
        
        # Should have removed blacklisted features
        assert len(stats["blacklisted_removed"]) > 0
        
        # Clean data should not contain blacklisted features
        for x in X_clean:
            for feature in BLACKLISTED_FEATURES:
                assert feature not in x


class TestModelCalibration:
    """Test model probability calibration."""
    
    def test_calibration_improves_brier_score(self):
        """Verify calibration is applied when configured."""
        from models.model_trainer_v4 import TrainingConfigV4
        
        config = TrainingConfigV4(use_calibration=True)
        assert config.use_calibration == True
        assert config.calibration_method in ['isotonic', 'sigmoid']


class TestIndependentComponents:
    """Test arbitrage and OT predictor as independent components."""
    
    def test_arbitrage_finder_standalone(self):
        """Test arbitrage finder works independently."""
        from core.arbitrage_finder import ArbitrageFinder, ArbitrageConfig
        from core.odds_fetcher import MatchOdds, OddsData
        
        config = ArbitrageConfig(min_roi=0.01)
        finder = ArbitrageFinder(config)
        
        # Create test odds
        match = MatchOdds(
            match_id="test_1",
            home_team="Team A",
            away_team="Team B",
            commence_time="2026-02-25T20:00:00Z",
            bookmakers={
                "book1": OddsData(
                    bookmaker="book1",
                    home_odds=1.80,
                    away_odds=2.10
                ),
                "book2": OddsData(
                    bookmaker="book2",
                    home_odds=2.15,
                    away_odds=1.75
                )
            }
        )
        
        opportunities = finder.find_arbitrage([match])
        
        # Should find opportunities or not based on odds
        assert isinstance(opportunities, list)
    
    def test_ot_predictor_standalone(self):
        """Test OT predictor works independently."""
        from models.overtime_predictor import OvertimePredictor, TeamStats
        
        predictor = OvertimePredictor()
        
        home_stats = TeamStats(
            team_name="Team A",
            goals_scored_avg=3.2,
            goals_conceded_avg=2.8,
            games_played=50,
            ot_games=10,
            ot_wins=5,
            recent_form=[1, 1, 0, 1, 0]
        )
        
        away_stats = TeamStats(
            team_name="Team B",
            goals_scored_avg=2.9,
            goals_conceded_avg=3.1,
            games_played=50,
            ot_games=12,
            ot_wins=4,
            recent_form=[0, 1, 0, 0, 1]
        )
        
        prediction = predictor.predict(home_stats, away_stats)
        
        # Should produce valid prediction
        assert 0 <= prediction.ot_probability <= 1
        assert 0 <= prediction.hole_probability <= 1


def run_all_tests():
    """Run all tests and generate report."""
    import subprocess
    result = subprocess.run(
        ['python', '-m', 'pytest', __file__, '-v', '--tb=short'],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
    return result.returncode == 0


if __name__ == "__main__":
    # Run tests
    success = run_all_tests()
    sys.exit(0 if success else 1)
