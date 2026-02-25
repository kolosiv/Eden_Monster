# Eden MVP Installation Guide

**Hockey Arbitrage Betting System**

This guide will walk you through installing and configuring Eden MVP on your local computer.

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation Steps](#installation-steps)
3. [Getting The Odds API Key](#getting-the-odds-api-key)
4. [Configuration](#configuration)
5. [Running the Application](#running-the-application)
6. [Demo Mode (Testing Without API Key)](#demo-mode)
7. [Troubleshooting](#troubleshooting)
8. [Understanding the System](#understanding-the-system)

---

## System Requirements

### Python
- **Python 3.8 or higher** is required
- Download from: https://www.python.org/downloads/

#### Check your Python version:
```bash
python --version
# or
python3 --version
```

### Operating System Support
- ✅ Windows 10/11
- ✅ macOS 10.15+
- ✅ Linux (Ubuntu, Debian, Fedora, etc.)

### Disk Space
- ~50 MB for the application and dependencies

---

## Installation Steps

### Step 1: Download the Project

If you have Git installed:
```bash
git clone [your-repository-url]
cd eden_mvp
```

Or download and extract the ZIP file to a folder on your computer.

### Step 2: Create a Virtual Environment (Recommended)

**Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

You should see output confirming installation of:
- `requests` - HTTP library for API calls
- `pydantic` - Data validation
- `pyyaml` - Configuration file handling
- `rich` - Beautiful terminal output
- `python-dateutil` - Date/time utilities

### Step 4: Verify Installation

```bash
python -c "import requests, pydantic, yaml, rich; print('✓ All dependencies installed successfully!')"
```

---

## Getting The Odds API Key

Eden MVP uses **The Odds API** to fetch real-time NHL betting odds from multiple bookmakers.

### Pricing Tiers

| Tier | Price | Requests/Month | Best For |
|------|-------|----------------|----------|
| Free | $0 | 500 | Testing & Learning |
| Basic | $50/month | 10,000 | Casual Use |
| Pro | $150/month | 50,000 | Serious Betting |

### Step-by-Step API Key Setup

1. **Visit The Odds API Website**
   - Go to: https://the-odds-api.com/

2. **Create an Account**
   - Click "Get Started" or "Sign Up"
   - Enter your email and create a password

3. **Verify Your Email**
   - Check your inbox for a verification email
   - Click the verification link

4. **Get Your API Key**
   - Log in to your dashboard: https://the-odds-api.com/account/
   - Your API key will be displayed on the dashboard
   - Copy the key (it looks like: `abc123def456...`)

5. **Choose Your Plan**
   - Free tier is sufficient for testing
   - Upgrade later if needed for more requests

### API Key Security Tips

⚠️ **Important:**
- Never share your API key publicly
- Don't commit config.yaml with your real API key to Git
- Add `config/config.yaml` to your `.gitignore` file

---

## Configuration

### Edit config.yaml

Open `config/config.yaml` in a text editor and update the following:

```yaml
# Demo Mode - Set to false to use real API data
demo_mode: false  # Change to false when using real API key

# API Configuration
api:
  the_odds_api:
    key: "YOUR_API_KEY_HERE"  # ← Replace with your actual API key
```

### Configuration Options

| Setting | Default | Description |
|---------|---------|-------------|
| `demo_mode` | `true` | Use simulated data (no API key needed) |
| `api.the_odds_api.key` | `YOUR_API_KEY_HERE` | Your Odds API key |
| `bankroll.total` | `1000.0` | Your betting bankroll in USD |
| `risk.min_roi` | `0.02` | Minimum ROI threshold (2%) |
| `risk.max_hole_probability` | `0.04` | Max acceptable OT risk (4%) |

### Example Production Configuration

```yaml
demo_mode: false

api:
  the_odds_api:
    key: "your-actual-api-key-here"
    
bankroll:
  total: 5000.0  # Your actual bankroll
  default_stake_percent: 4.0  # 4% of bankroll per bet

risk:
  max_hole_probability: 0.03  # Conservative: 3%
  min_roi: 0.025  # Minimum 2.5% ROI
```

---

## Running the Application

### Start Eden MVP

```bash
python main.py
```

### Main Menu Options

```
╭───┬──────────────────────────────────────────╮
│ 1 │ 🔍 Fetch Current Arbitrage Opportunities │
│ 2 │ 📊 Analyze Specific Match                │
│ 3 │ 📜 View Betting History                  │
│ 4 │ 📈 Show Statistics                       │
│ 5 │ ⚙️  Update Configuration                 │
│ 6 │ 💾 Record Bet Result                     │
│ 0 │ 🚪 Exit                                  │
╰───┴──────────────────────────────────────────╯
```

### Quick Start Workflow

1. **Start the app** → `python main.py`
2. **Fetch opportunities** → Press `1`
3. **Review recommendations** → System shows BET, CAUTION, or SKIP
4. **Check stake calculations** → See exactly how much to bet
5. **Record results** → Press `6` after games complete
6. **Track performance** → Press `4` for statistics

---

## Demo Mode

Demo mode lets you explore all features without an API key.

### Enable Demo Mode

In `config/config.yaml`:
```yaml
demo_mode: true
```

### What Demo Mode Provides

- ✅ Simulated NHL match data
- ✅ Realistic odds from multiple bookmakers
- ✅ Some arbitrage opportunities for testing
- ✅ Full stake calculation
- ✅ Database functionality
- ✅ Statistics tracking

### Limitations

- ❌ Data is not real-time
- ❌ Cannot find actual betting opportunities
- ❌ Bookmaker names are simulated

---

## Troubleshooting

### Common Issues

#### 1. "ModuleNotFoundError: No module named 'rich'"

**Solution:** Install dependencies
```bash
pip install -r requirements.txt
```

#### 2. "API key not configured!"

**Solution:** Add your API key to `config/config.yaml` or enable demo mode:
```yaml
demo_mode: true
```

#### 3. "No matches found. NHL might be in off-season."

**Explanation:** The NHL season runs October-June. During off-season:
- Use demo mode for testing
- Check back when season starts

#### 4. "Invalid API key"

**Solution:**
1. Log in to https://the-odds-api.com/account/
2. Copy your API key exactly (no extra spaces)
3. Paste into config.yaml

#### 5. "Rate limit exceeded"

**Solution:**
- Free tier: 500 requests/month
- Wait until next month or upgrade plan
- Check usage at https://the-odds-api.com/account/

#### 6. Permission errors on Windows

**Solution:** Run Command Prompt as Administrator:
```cmd
pip install --user -r requirements.txt
```

#### 7. Python command not found

**Windows Solution:**
- Use `py` instead of `python`
- Or add Python to PATH during installation

**macOS/Linux Solution:**
- Use `python3` instead of `python`

### Log Files

Check `logs/eden.log` for detailed error information:
```bash
# View recent logs
tail -50 logs/eden.log
```

---

## Understanding the System

### What is Hockey Arbitrage?

Arbitrage betting exploits differences in odds between bookmakers to guarantee profit regardless of outcome.

**Example:**
```
FanDuel: Boston Bruins @ 2.20
DraftKings: Toronto Maple Leafs @ 2.00

If you bet proportionally on both teams, you profit no matter who wins.
```

### The "Hole" Problem

In hockey, overtime creates risk. When betting on regulation-time markets:
- If the favored team wins in OT, you lose the bet on the underdog
- This creates a "hole" where both bets lose

Eden MVP calculates this risk and only recommends bets where the hole probability is acceptable.

### Recommendation System

| Recommendation | Criteria |
|---------------|----------|
| **BET** | ROI ≥ 2%, Hole ≤ 4%, Positive EV |
| **CAUTION** | Good ROI but higher risk |
| **SKIP** | Too risky or low ROI |

### Risk Levels

- **LOW**: Very favorable conditions
- **MEDIUM**: Acceptable risk
- **HIGH**: Elevated OT risk
- **EXTREME**: Do not bet

---

## Next Steps

1. **Learn the basics** → Run in demo mode first
2. **Get API key** → Sign up at The Odds API
3. **Configure conservatively** → Start with small bankroll
4. **Track everything** → Use the statistics feature
5. **Start small** → Paper trade before real money

---

## Support

For issues with:
- **The Odds API** → https://the-odds-api.com/contact/
- **Eden MVP** → Check logs/eden.log for errors

---

**Good luck with your hockey arbitrage betting! 🏒**
