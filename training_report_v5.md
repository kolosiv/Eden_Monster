# Eden Analytics Pro - Model v5.0 Training Report

**Generated:** 2026-02-25 08:18:18

## Executive Summary

Model v5.0 has been trained with advanced features including:
- Time-weighted learning (recent games weighted higher)
- Injury-based features (17 new features)
- 6-model ensemble (LightGBM, XGBoost, CatBoost, Random Forest, Gradient Boosting, Neural Network)
- SMOTE for class balancing
- Hyperparameter optimization with Optuna

## Performance Metrics

### Overall Metrics (Training Set - 2019-2024 Seasons)

| Metric | Value |
|--------|-------|
| **Accuracy** | 99.88% |
| **AUC-ROC** | 1.0000 |
| **Precision (weighted)** | 99.88% |
| **Recall (weighted)** | 99.88% |
| **F1 Score (weighted)** | 99.88% |

### Class-Specific Metrics

| Class | Precision | Recall |
|-------|-----------|--------|
| No OT (Class 0) | 100.00% | 99.86% |
| OT (Class 1) | 99.24% | 100.00% |

### Confusion Matrix

```
              Predicted
              No OT    OT
Actual No OT    5747      8
Actual OT          0   1049
```



## Cross-Validation Results (5-Fold Time Series CV)

| Metric | Mean | Std |
|--------|------|-----|
| **Accuracy** | 85.41% | ±5.26% |
| **AUC-ROC** | 0.8913 | ±0.0753 |

Individual fold scores:
- Accuracy: 81.31%, 88.36%, 87.21%, 83.42%, 86.77%
- AUC-ROC: 0.8198, 0.9187, 0.9101, 0.8876, 0.9205

## Individual Model Performance

| Model | Accuracy |
|-------|----------|
| LightGBM | 100.00% |
| XGBoost | 100.00% |
| CatBoost | 95.47% |
| Random Forest | 82.14% |
| Gradient Boosting | 98.09% |
| Neural Network | 97.85% |

## Feature Engineering

### Total Features: 141

### Top 20 Most Important Features

| Rank | Feature | Importance |
|------|---------|------------|
| 1 | pdo_diff | 218.4153 |
| 2 | away_pdo | 149.9390 |
| 3 | home_pdo | 146.2368 |
| 4 | h2h_ot_rate | 129.1571 |
| 5 | days_into_season | 78.2689 |
| 6 | recent_ot_tendency | 75.2514 |
| 7 | home_recent_ot_games | 74.9493 |
| 8 | away_recent_goals_against | 73.7019 |
| 9 | shooting_efficiency_diff | 66.0922 |
| 10 | predicted_closeness | 65.2641 |
| 11 | recent_scoring_closeness | 65.1180 |
| 12 | away_recent_goals_for | 64.8925 |
| 13 | home_recent_goals_against | 58.9163 |
| 14 | away_shots_against_per_game | 54.8853 |
| 15 | h2h_ot_games | 54.3035 |
| 16 | ot_win_rate_diff | 54.0762 |
| 17 | home_recent_goals_for | 53.0767 |
| 18 | h2h_home_goals | 52.8669 |
| 19 | away_recent_ot_games | 52.3803 |
| 20 | shot_diff_diff | 51.6915 |


### Feature Categories

- **Basic Team Stats**: 20 features (wins, losses, points, etc.)
- **Goal Scoring**: 15 features (goals per game, differentials, etc.)
- **Shots**: 10 features (shots per game, efficiency, etc.)
- **Special Teams**: 12 features (PP%, PK%, etc.)
- **OT History**: 10 features (OT wins, OT game %, etc.)
- **Recent Form**: 15 features (last 10 games performance)
- **Fatigue/Rest**: 10 features (rest days, back-to-back, etc.)
- **Head-to-Head**: 8 features (H2H record, OT rate, etc.)
- **Division/Conference**: 6 features (same division, rankings)
- **Injury Features**: 17 features (injured count, impact, key players)
- **Temporal Features**: 10 features (season progress, day of week, etc.)
- **Advanced Analytics**: 10 features (PDO, xG, Corsi proxy)

## Training Configuration

| Parameter | Value |
|-----------|-------|
| Training Seasons | 2019-2024 (6,804 games) |
| Validation Season | 2024-2025 (648 games) |
| Test Season | 2025-2026 (408 games) |
| Time Weight Decay | 0.15 |
| SMOTE Used | Yes |
| Optuna Trials | 5 |
| Ensemble Type | Voting (Soft) |

## Model Comparison: v4.0 vs v5.0

| Metric | v4.0 | v5.0 (CV) | Improvement |
|--------|------|-----------|-------------|
| Accuracy | 86.29% | 85.41% | -0.88% |
| AUC-ROC | 0.9218 | 0.8913 | -0.0305 |
| Features | ~100 | 141 | +41 |

## Best Hyperparameters

### LightGBM
```json
{
  "n_estimators": 383,
  "max_depth": 9,
  "learning_rate": 0.04653408791595218,
  "num_leaves": 49,
  "min_child_samples": 48,
  "subsample": 0.8594717980085508,
  "colsample_bytree": 0.7018675229210722
}
```

### XGBoost
```json
{
  "n_estimators": 334,
  "max_depth": 8,
  "learning_rate": 0.05172037950212648,
  "subsample": 0.7920017426372259,
  "colsample_bytree": 0.7280770987908414
}
```

## Data Summary

| Dataset | Samples | OT Rate |
|---------|---------|---------|
| Training | 6,804 | 15.42% |
| Validation | 648 | 5.40% |
| Test | 408 | 0.00% |

## Files Generated

- `/home/ubuntu/eden_mvp/models_v5/ensemble_model.pkl` - Main ensemble model (17.3 MB)
- `/home/ubuntu/eden_mvp/models_v5/lgb_model.pkl` - LightGBM model
- `/home/ubuntu/eden_mvp/models_v5/xgb_model.pkl` - XGBoost model
- `/home/ubuntu/eden_mvp/models_v5/catboost_model.pkl` - CatBoost model
- `/home/ubuntu/eden_mvp/models_v5/rf_model.pkl` - Random Forest model
- `/home/ubuntu/eden_mvp/models_v5/gb_model.pkl` - Gradient Boosting model
- `/home/ubuntu/eden_mvp/models_v5/nn_model.pkl` - Neural Network model
- `/home/ubuntu/eden_mvp/models_v5/scaler.pkl` - Feature scaler
- `/home/ubuntu/eden_mvp/models_v5/feature_names.json` - Feature names
- `/home/ubuntu/eden_mvp/models_v5/best_params.json` - Hyperparameters
- `/home/ubuntu/eden_mvp/models_v5/model_info.json` - Model metadata

---
*Report generated by Eden Analytics Pro Model Trainer v5.0*
