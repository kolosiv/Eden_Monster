# 🏒 Eden Analytics Pro v2.4.0

**Professional Hockey Arbitrage Analysis System with Advanced ML**

![Eden Analytics Pro Logo](gui/assets/branding/eden_logo_horizontal.png)

Eden Analytics Pro is an advanced sports analytics platform designed for hockey betting analysis, featuring real-time arbitrage detection, **ML-powered overtime prediction v3.0**, and a world-class premium dashboard interface.

## 🎬 Animated Intro

Eden Analytics Pro features a stunning 10-second animated intro:
- Golden Eden tree above professional hockey rink
- Intense hockey gameplay with competing players (3 players battle!)
- Dramatic slapshot and money explosion
- Professional sports broadcast quality
- Skippable with any key press or click

## 🆕 What's New in v2.4.0

### Advanced ML Model v4.0 - 86.29% Accuracy

**Enhanced Feature Engineering (100+ Features):**
- Rolling team statistics (3, 5, 10, 15, 20 game windows)
- Head-to-head historical features
- Momentum and streak features
- Situational features (rest days, back-to-back)
- Advanced analytics (xG, PDO, goalie quality)
- Time-based features (season progress, day of week)

**6-Model Ensemble:**
- XGBoost (optimized hyperparameters)
- LightGBM (gradient boosting)
- CatBoost (categorical features)
- Random Forest (500 trees)
- Gradient Boosting (300 estimators)
- Neural Network (256-128-64-32 architecture)

**Advanced Techniques:**
- SMOTE for class balancing
- Stacking ensemble with meta-learner
- Probability calibration
- 7-season training data (~6,800 games)

**Performance Metrics:**
- Accuracy: 86.29%
- AUC-ROC: 0.9218
- Precision: 0.88 (weighted)
- F1 Score: 0.87 (weighted)

---

## 📖 Previous Updates

### What Was New in v2.3.0

### 🤖 ML Model v3.0 - Major Improvements
The overtime prediction model has been significantly enhanced:

**100+ Advanced Features:**
- 🔥 **Momentum Features** - Win/loss streaks, recent form (5/10/20 games), goal differential momentum
- 🆚 **Matchup Features** - Head-to-head stats, H2H OT rate, division/conference matchups
- 📊 **Situational Features** - Rest days, back-to-back games, travel fatigue, season progress
- 🥅 **Goalie Features** - Save percentage, GAA, workload, goalie quality scores
- 📈 **Team Style Features** - Offensive/defensive ratings, pace, Corsi/Fenwick, PDO
- 💰 **Market Features** - Odds-implied probabilities, market competitiveness

**6-Model Ensemble:**
- RandomForest (optimized, 500 estimators)
- XGBoost (optimized hyperparameters)
- LightGBM (optimized hyperparameters)
- CatBoost (NEW!)
- GradientBoosting (NEW!)
- Neural Network (improved architecture)

**Advanced Techniques:**
- ✅ Bayesian hyperparameter optimization (200 trials per model)
- ✅ Stacked ensemble with meta-learner
- ✅ Probability calibration (isotonic regression)
- ✅ Feature importance analysis
- ✅ Advanced feature selection

**Expected Performance Improvements:**
- Accuracy: 65-70% → **72-76%** (+7-10%)
- AUC: 0.70-0.75 → **0.78-0.82** (+10-15%)
- Hole Risk: 3.8% → **2.0-2.5%** (-35-45%)
- ROI: 4.2% → **5.5-6.5%** (+30-55%)

### Previous in v2.2.0 - Premium UI/UX Overhaul
- **Premium Gold & Cyan Theme** - World-class dark theme with gold (#FFD700) primary and cyan (#00D9FF) accent colors
- **Glassmorphism Effects** - Modern semi-transparent glass-style components
- **Premium Sidebar Navigation** - Redesigned 280px sidebar with glow effects and gradient backgrounds
- **Premium Stats Cards** - Stunning dashboard cards with radial gradient icons and trend indicators
- **Premium Components Library** - New PremiumButton, PremiumInput, PremiumProgressBar, PremiumTable, SkeletonLoader
- **Toast Notifications** - Beautiful animated notifications with fade-in/out effects
- **Premium Header** - Redesigned gradient header with welcome message and status indicators
- **Enhanced Status Bar** - Premium styled status indicators with color-coded badges

### Visual Improvements
- ✨ **Gradient Backgrounds** - Smooth linear gradients throughout the UI
- ✨ **Hover Effects** - Premium hover states with glow and color transitions
- ✨ **Premium Scrollbars** - Custom styled scrollbars with gradient handles
- ✨ **Enhanced Typography** - Better font weights, letter spacing, and sizing
- ✨ **Improved Spacing** - Consistent padding and margins for visual harmony
- ✨ **Shadow Effects** - Drop shadows for depth and visual hierarchy

### Previous in v2.1.2
- **Belarusian Bookmakers Support** - Integrated support for regional bookmakers
- **Caution Level Telegram Alerts** - Now sends ⚠️ CAUTION bets to Telegram
- **Enhanced Video Playback** - Improved error handling for intro video

### Previous in v2.1.1
- **Enhanced Intro Video (V2)** - Dynamic 10-second intro "The Golden Apple Game"
- **Professional Branding Suite** - Full logo, icon, horizontal, and dark theme variants
- **Custom Application Icons** - ICO (Windows) and ICNS (macOS) formats

## ✨ Features

### Modern Dashboard Interface
- **Dark/Light Theme Support** - Toggle between themes for comfortable viewing
- **Sidebar Navigation** - Easy access to all features
- **Live Statistics Dashboard** - Real-time tracking of performance metrics
- **Interactive Charts** - Bankroll, ROI, and win rate visualizations

### Supported Bookmakers

#### International (via The Odds API)
- 20+ major bookmakers from US and EU regions
- Real-time odds with automatic caching

#### Belarusian Bookmakers
- ✅ **Betera** (betera.by) - Leading Belarusian bookmaker
- ✅ **Fonbet** (fonbet.by) - Russian bookmaker with BY branch
- ✅ **Winline** (winline.by) - Popular CIS bookmaker
- ✅ **MarafonBet** (marathonbet.by) - International with BY presence

All bookmakers are enabled by default and can be configured in `config/config.yaml`.

### Core Features
- **Arbitrage Detection** - Identify profitable betting opportunities across bookmakers
- **ML-Powered Predictions** - Machine learning-based overtime probability predictions
- **Risk Analysis** - Comprehensive risk assessment for each opportunity
- **Stake Calculator** - Optimal stake calculation based on Kelly Criterion
- **History Tracking** - Complete bet history with P/L tracking
- **Backtesting** - Test strategies on historical data

### Additional Features
- **Telegram Bot** - Receive alerts on mobile (includes caution-level bets)
- **Multi-language Support** - English, Russian, and more
- **Auto Model Retraining** - ML model improves over time
- **Export Reports** - CSV, JSON, and HTML report generation

## 🚀 Quick Start

### System Requirements
- Python 3.10 or higher
- 4GB RAM minimum
- Internet connection for odds API

### Installation

1. **Extract the archive:**
   ```bash
   unzip eden_analytics_pro_v2.1.1.zip
   cd eden_analytics_pro_v2.1.1
   ```

2. **Create virtual environment (recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate  # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   
   Or use the automated installer:
   ```bash
   python install.py
   ```

4. **Configure API key:**
   Edit `config/config.yaml` and add your The Odds API key:
   ```yaml
   api:
     key: "YOUR_API_KEY_HERE"
   ```
   Get a free API key at: https://the-odds-api.com/

## 🖥️ Running the Application

### GUI Interface (Recommended)

```bash
python start_gui.py
```

Or directly:
```bash
python main_gui.py
```

### Console Interface

```bash
python main.py
```

### Telegram Bot

1. Configure bot token in `config/telegram_config.yaml`
2. Run the bot:
   ```bash
   python start_bot.py
   ```

## 📁 Project Structure

```
eden_analytics_pro_v2.0.0/
├── main_gui.py          # GUI entry point
├── start_gui.py         # GUI launcher with dependency checks
├── main.py              # Console interface
├── start_bot.py         # Telegram bot launcher
├── install.py           # Automated installer
├── requirements.txt     # Python dependencies
├── config/
│   ├── config.yaml      # Main configuration
│   └── telegram_config.yaml
├── core/                # Core business logic
├── gui/                 # Modern GUI components
│   ├── themes/          # Dark/Light themes
│   ├── components/      # Reusable widgets
│   ├── pages/           # Main application pages
│   ├── dialogs/         # Popup dialogs
│   ├── widgets/         # Feature-specific widgets
│   └── main_window_pro.py
├── models/              # ML prediction models
├── analysis/            # Analysis and stake calculation
├── database/            # SQLite database management
├── backtest/            # Backtesting engine
├── telegram_bot/        # Telegram bot integration
├── bankroll/            # Bankroll management
├── localization/        # Multi-language support
└── utils/               # Utility functions
```

## ⚙️ Configuration

### Main Settings (`config/config.yaml`)

```yaml
api:
  key: "your_api_key"
  base_url: "https://api.the-odds-api.com"

bankroll:
  initial: 1000.0
  
strategy:
  min_roi: 0.5
  max_hole_probability: 0.15
  
ml:
  use_ml_predictor: true
  auto_retrain: true
```

### Telegram Bot (`config/telegram_config.yaml`)

```yaml
bot:
  token: "your_bot_token"
  
alerts:
  enabled: true
  min_roi: 1.0
```

## 🔧 Troubleshooting

### GUI Won't Start

1. Check PyQt6 is installed:
   ```bash
   pip install PyQt6 PyQt6-WebEngine
   ```

2. On Linux, install Qt dependencies:
   ```bash
   sudo apt install libxcb-cursor0
   ```

### ML Model Not Loading

Train a new model:
```bash
python -c "from models.model_trainer import train_initial_model; train_initial_model()"
```

### API Rate Limits

- Free tier: 500 requests/month
- Check remaining quota in the console output
- Upgrade API plan for more requests

## 📊 Understanding the Output

### Key Metrics

- **ROI** - Return on Investment percentage
- **Hole Probability** - Risk of the underdog winning in OT
- **Confidence** - ML model's prediction confidence
- **EV** - Expected Value of the bet

### Recommendations

- ✅ **BET** - Good opportunity, within risk tolerance
- ⚠️ **CAUTION** - Marginal opportunity, review carefully
- ❌ **SKIP** - Too risky or unprofitable

## 📝 License

This software is provided for educational purposes only. Use at your own risk.

## 🤝 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the documentation in `/docs`
3. Run the system check: `python check_system.py`

---

**Version:** 2.1.1  
**Last Updated:** February 2026
