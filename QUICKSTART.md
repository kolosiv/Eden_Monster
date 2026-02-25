# Eden MVP - Quick Start Guide 🏒

Get up and running with Eden MVP in under 5 minutes!

---

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Terminal/Command Prompt access

---

## Step 1: Verify Python Installation

### Windows
```cmd
python --version
```
If not installed, download from [python.org](https://www.python.org/downloads/windows/)

> ⚠️ **Important:** During installation, check "Add Python to PATH"

### Mac
```bash
python3 --version
```
If not installed:
```bash
brew install python3
```
Or download from [python.org](https://www.python.org/downloads/macos/)

### Linux (Ubuntu/Debian)
```bash
python3 --version
```
If not installed:
```bash
sudo apt update && sudo apt install python3 python3-pip python3-venv
```

---

## Step 2: Extract and Navigate

### Windows
1. Right-click `eden_mvp_v1.0.zip`
2. Select "Extract All..."
3. Open Command Prompt:
```cmd
cd C:\path\to\eden_mvp
```

### Mac/Linux
```bash
unzip eden_mvp_v1.0.zip
cd eden_mvp
```

---

## Step 3: Create Virtual Environment (Recommended)

### Windows
```cmd
python -m venv venv
venv\Scripts\activate
```

### Mac/Linux
```bash
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` at the start of your command line.

---

## Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

Expected output:
```
Successfully installed requests-2.31.0 pyyaml-6.0.1 ...
```

---

## Step 5: Run in Demo Mode (No API Key Needed!)

```bash
python main.py
```

### What You'll See:
```
╔══════════════════════════════════════════════════════════════════╗
║                    EDEN MVP - Hockey Arbitrage                    ║
║                         Demo Mode Active                          ║
╚══════════════════════════════════════════════════════════════════╝

[INFO] Loading demo data...
[INFO] Found 3 potential arbitrage opportunities!

═══════════════════════════════════════════════════════════════════
                    ARBITRAGE OPPORTUNITY #1
═══════════════════════════════════════════════════════════════════
Match: Boston Bruins vs Toronto Maple Leafs
...
```

🎉 **Congratulations!** Eden MVP is working!

---

## Step 6: Get Your API Key (For Live Data)

1. Visit [The Odds API](https://the-odds-api.com/)
2. Click "Get API Key" (free tier: 500 requests/month)
3. Enter your email and verify
4. Copy your API key

---

## Step 7: Switch to Production Mode

### Option A: Edit config.yaml
Open `config/config.yaml` and change:
```yaml
demo_mode: false

api:
  the_odds_api:
    key: "YOUR_ACTUAL_API_KEY"
```

### Option B: Use Environment Variable
```bash
# Mac/Linux
export ODDS_API_KEY="your_api_key_here"

# Windows
set ODDS_API_KEY=your_api_key_here
```

Then run:
```bash
python main.py
```

---

## Common Commands

| Command | Description |
|---------|-------------|
| `python main.py` | Run with default settings |
| `python main.py --demo` | Force demo mode |
| `python main.py --help` | Show all options |

---

## Troubleshooting

### "Python not found"
- **Windows:** Reinstall Python with "Add to PATH" checked
- **Mac/Linux:** Use `python3` instead of `python`

### "Module not found" errors
```bash
pip install -r requirements.txt --force-reinstall
```

### "Permission denied"
- **Mac/Linux:** Use `sudo pip install ...` or use virtual environment
- **Windows:** Run Command Prompt as Administrator

### "API rate limit exceeded"
- Switch to demo mode: `python main.py --demo`
- Wait for rate limit reset (usually 1 hour)

### Database errors
Delete `eden_mvp.db` and restart - it will be recreated automatically.

### Config file errors
Ensure `config/config.yaml` has valid YAML syntax. Use spaces, not tabs.

---

## Next Steps

1. 📖 Read `README.md` for full feature documentation
2. 📚 Read `INSTALLATION_GUIDE.md` for detailed setup
3. ⚙️ Customize `config/config.yaml` for your preferences
4. 💰 Set your bankroll and risk parameters
5. 🏒 Start finding arbitrage opportunities!

---

## Need Help?

- Check the logs in `logs/` directory
- Review error messages carefully
- Ensure all dependencies are installed
- Verify your API key is valid

---

**Happy Arbitrage Hunting! 🎯**
