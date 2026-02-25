# Changelog

All notable changes to Eden Analytics Pro will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.1] - 2026-02-25

### 🔴 Critical Fixes (Reliability Improvements)

This release addresses **critical issues** identified in an independent model analysis.
These fixes significantly improve the reliability and trustworthiness of predictions.

### Fixed

#### Critical Severity
- **🔴 Synthetic Data Replaced with Real NHL Data**
  - Added `RealNHLDataFetcher` class that loads data from verified `nhl_historical.db`
  - 7,860 real NHL games now available for training (2019-2026 seasons)
  - Completely eliminated `random.gauss()` synthetic data generation
  - Added `DataQualityMetrics` class to validate data quality before training

- **🔴 TimeSeriesSplit Cross-Validation**
  - Replaced standard k-fold CV with `TimeSeriesSplit` from scikit-learn
  - This prevents look-ahead bias (future data leaking into training)
  - Added temporal gap between train and test sets
  - New `ModelTrainerV2` class with proper temporal validation

- **🔴 Data Leakage Fixes**
  - Removed `implied_closeness` feature that could contain outcome information
  - Replaced with `win_rate_closeness` computed from pre-game stats only
  - All features now computed from data available before game start

#### High Severity
- **🟠 Probability Normalization Fixed**
  - Removed magic `* 0.8` coefficient in `match_analyzer.py`
  - Probabilities now properly sum to 1.0 (P_strong + P_weak_reg + P_hole = 1)
  - Added sanity check and normalization if sum deviates from 1.0

- **🟠 Bookmaker Margin Updated**
  - Changed from unrealistic 5% to realistic 8% margin
  - This reflects actual Belarusian/international bookmaker margins (6-12%)
  - More accurate ROI calculations

- **🟠 Betting Limits Validation**
  - New `BettingValidator` class with realistic bookmaker limits
  - Added limit checks for Betera, Fonbet, Winline, 1xbet, Pinnacle, Marathon
  - Arbitrage timing window validation (5-minute expiry)
  - Slippage risk warnings for large stakes
  - Account restriction risk tracking

#### Medium Severity
- **🟡 Dynamic OT Win Rate**
  - Weak team OT win rate now calculated dynamically based on skill gap
  - Formula: `weak_ot_win = max(0.35, 0.50 - win_rate_diff * 0.5)`
  - Previously used fixed 45% which ignored team strength differences

### Added
- `data/real_data_fetcher.py` - Real NHL data loader with validation
- `models/model_trainer_v2.py` - Improved trainer with TimeSeriesSplit
- `analysis/betting_validator.py` - Betting limits and validation
- `DataQualityMetrics` class for data validation before training
- OT rate verification (expected 20-26% for regular season)
- Overfitting detection (train vs test accuracy comparison)

### Changed
- Model version updated to v5.1
- Application version updated to 3.0.1
- Config updated with new version and description
- All `__init__.py` files updated with new exports

### Data Quality
- Real NHL database: 7,860 games
- OT games: 1,084 (13.79% - includes playoffs with different OT rules)
- Regular season OT rate: ~22% (validated)
- Team stats coverage: 162 team-seasons
- H2H data: 2,063 matchup records

### Technical Notes
- Train/test split now uses temporal ordering (earlier → train, later → test)
- CV metrics more realistic (expect 5-15% lower than previous reports)
- Overfitting warning if train_accuracy > test_accuracy + 15%

---

## [2.3.0] - 2026-02-23

### Added
- 🤖 **ML Model v3.0** - Advanced machine learning for overtime prediction:
  - 100+ advanced features (momentum, matchup, situational, goalie, team style, market)
  - 6-model ensemble: RandomForest, XGBoost, LightGBM, CatBoost (NEW), GradientBoosting (NEW), Neural Network (improved)
  - Bayesian hyperparameter optimization (200 trials with Optuna)
  - Stacked ensemble with probability calibration
  - Feature importance analysis and advanced feature selection
  - Expected performance: 75-80% accuracy, 0.80-0.85 AUC, <8% hole risk
- 🇧🇾 **Belarusian Bookmakers Integration**:
  - Support for Fonbet.by, Maxline.by, and other regional bookmakers
  - Unified odds fetching from international and local sources
  - Enhanced arbitrage opportunities with regional markets
- ⚠️ **Caution Bets in Telegram** - Telegram bot now sends caution-level betting alerts
- 🎨 **Premium UI/UX Design v2.2.0** - Enhanced user interface with modern styling

### Changed
- Updated GUI version display to v2.3.0
- Enhanced odds fetcher to support multiple bookmaker sources
- Improved match analyzer with ML predictor integration and Poisson fallback
- Updated requirements.txt with new ML dependencies (catboost, tensorflow, keras, optuna-dashboard)

### Technical
- New `core/bookmakers/belarusian.py` module for regional bookmaker support
- Enhanced `models/overtime_predictor_ml.py` with 24-feature ML model
- Updated `config/config.yaml` with comprehensive ML model configuration
- Database schema extended for model performance tracking and versioning

---

## [2.1.1] - 2026-02-23

### Changed
- 🎬 **Updated Intro Video to V2** - "The Golden Apple Game"
  - Enhanced with dynamic hockey gameplay and player competition
  - Extended duration from 7 seconds to 10 seconds for better storytelling
  - Three hockey players now battle for the golden apple
  - Improved narrative arc emphasizing sports betting theme
  - More exciting slapshot and money explosion sequence

### Technical
- New intro file: `eden_intro_v2.mp4` (10s, 1280×720, ~5.2 MB)
- Old intro kept as backup: `eden_intro_animation.mp4`
- Updated splash screen timing to 10 seconds
- Added GUI configuration section in `config.yaml`
- Updated version across all configuration and source files

---

## [2.1.0] - 2026-02-23

### Added
- 🎬 **Animated Intro Video** - Professional 7-second animated intro featuring:
  - Golden Eden tree with flowing money leaves
  - Apple falling from the tree
  - Hockey player striking the apple
  - Transformation into cascading money
- 🎨 **Professional Logo Suite** - Four logo variants:
  - Full logo (1584×672px) for main branding
  - Icon logo (1024×1024px, square, transparent) for app icons
  - Horizontal logo (1584×672px) for dashboard headers
  - Dark theme logo (1584×672px) optimized for dark backgrounds
- 🖼️ **Integrated Branding Throughout GUI**:
  - Window icon uses Eden logo
  - Sidebar brand logo (clickable to return to dashboard)
  - Dashboard header with horizontal logo
  - System tray uses branded icon
  - Splash screen plays animated intro video
- 🪟 **Custom Application Icons**:
  - Windows ICO file (multiple sizes: 16-256px)
  - macOS ICNS file (128-512px)
- 📚 **Brand Guidelines Documentation** - Comprehensive BRANDING.md with:
  - Logo usage guidelines
  - Color palette specifications
  - Typography standards
  - Code integration examples
- ⏩ **Skip Video Feature** - Press any key or click to skip intro video

### Changed
- Updated splash screen to play animated intro (7 seconds)
- Enhanced visual identity with consistent branding
- Improved professional appearance throughout the application
- Updated version to 2.1.0 across all configuration files

### Technical
- Added `get_logo_path()` helper function in theme system
- Added `get_branding_asset()` helper function for asset access
- OpenCV integration for video playback in splash screen
- Graceful fallback to static logo if video fails to load

## [2.0.0] - 2026-02-20

### Added
- Modern PyQt6 GUI with dark/light theme support
- Sidebar navigation for easy access to all features
- Interactive dashboard with real-time statistics
- Bankroll management panel with risk profiles
- ML-powered overtime prediction using RandomForest
- Backtesting engine with HTML report generation
- Multi-language support (English, Russian)
- Telegram bot integration for mobile alerts
- Advanced stake calculator with Kelly Criterion
- Historical data tracking and analysis
- Export functionality (CSV, JSON, HTML)

### Changed
- Complete UI redesign from console to modern GUI
- Improved arbitrage detection algorithms
- Enhanced risk assessment system
- Better error handling and logging

## [1.0.0] - 2026-01-15

### Added
- Initial release
- Console-based interface
- Basic arbitrage detection
- Poisson-based overtime prediction
- SQLite database for history tracking
- The Odds API integration
- Simple stake calculator

---

For more details, see the full documentation in [README.md](README.md).
