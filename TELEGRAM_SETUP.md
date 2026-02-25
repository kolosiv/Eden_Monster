# 📡 Telegram Bot Setup Guide

This guide will help you set up the Eden MVP Telegram bot for receiving real-time arbitrage notifications.

## Prerequisites

- Telegram account
- Python 3.8+
- Eden MVP installed

## Step 1: Create a Telegram Bot

1. **Open Telegram** and search for **@BotFather**
2. Start a conversation and send `/newbot`
3. Follow the prompts:
   - Enter a **name** for your bot (e.g., "Eden Arbitrage Bot")
   - Enter a **username** for your bot (must end in 'bot', e.g., "eden_arb_bot")
4. **Copy the token** provided by BotFather. It looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

⚠️ **Keep your token secret!** Anyone with the token can control your bot.

## Step 2: Configure Eden MVP

### Option A: Using the Config File

1. Open `config/telegram_config.yaml`
2. Replace `YOUR_BOT_TOKEN_HERE` with your actual token:

```yaml
bot_token: "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
```

3. Customize other settings as needed

### Option B: Using Environment Variable

```bash
export EDEN_TELEGRAM_TOKEN="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
```

## Step 3: Install Dependencies

```bash
pip install python-telegram-bot>=20.0
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

## Step 4: Start the Bot

The bot starts automatically with the GUI application. You can also start it manually:

```python
from telegram_bot import TelegramBot
from database import DatabaseManager

db = DatabaseManager("eden_mvp.db")
bot = TelegramBot(token="YOUR_TOKEN", db_manager=db)

# Start in background thread
bot.start_in_thread()
```

## Using the Bot

### Available Commands

| Command | Description |
|---------|-------------|
| `/start` | Subscribe to notifications |
| `/stop` | Pause notifications |
| `/resume` | Resume notifications |
| `/stats` | View your betting statistics |
| `/settings` | Customize notification filters |
| `/status` | Check bot status |
| `/help` | List all commands |

### Notification Filters

Customize which opportunities you receive:

1. Send `/settings` to the bot
2. Tap on a setting to change it:
   - **Min ROI**: Only receive alerts above this ROI (e.g., 3%)
   - **Max Hole Risk**: Only receive alerts below this risk (e.g., 8%)
   - **Leagues**: Filter by league (NHL, KHL, etc.)

### Example Notification

```
🏒 ARBITRAGE OPPORTUNITY ✅

Boston Bruins vs Toronto Maple Leafs
📅 Feb 20, 19:00
⏰ Starting in 3.5h

💰 ROI: 3.45%

Odds:
├ Boston Bruins: 1.85 (Pinnacle)
└ Toronto Maple Leafs: 2.15 (Bet365)

Analysis:
├ 🕳️ Hole Risk: 6.2%
├ ⚙️ OT Probability: 23.4%
├ 📊 EV: 2.18%
└ 🟢 Risk Level: LOW

Recommended Stakes:
├ Boston Bruins: $21.50
├ Toronto Maple Leafs: $18.50
└ Potential Profit: $1.38

✅ RECOMMENDATION: PLACE BET
```

## Troubleshooting

### Bot not responding

1. Check if the token is correct
2. Verify internet connection
3. Check logs: `logs/eden.log`

### "Unauthorized" error

- Your token is invalid. Get a new one from @BotFather

### Rate limit errors

- Telegram limits 30 messages/second
- The bot handles this automatically
- If you see errors, reduce `messages_per_second` in config

### Messages not sending

1. Make sure users have started the bot with `/start`
2. Check if notifications are enabled for the user
3. Verify the user's filters aren't too strict

## Security Best Practices

1. **Never share your bot token publicly**
2. Store the token in environment variables for production
3. Regularly check `/stats` for unusual activity
4. Use admin IDs to restrict certain commands

## Advanced Configuration

### Webhook Mode (for Production)

For better performance in production, use webhooks:

```yaml
polling:
  enabled: false

webhook:
  enabled: true
  url: "https://yourdomain.com/webhook/eden"
  port: 8443
  cert_path: "/path/to/cert.pem"
  key_path: "/path/to/key.pem"
```

### Custom Notification Schedule

Edit time ranges in filters to only receive notifications during specific hours.

## Support

If you encounter issues:
1. Check the logs in `logs/eden.log`
2. Review the Telegram Bot API documentation
3. Open an issue on GitHub
