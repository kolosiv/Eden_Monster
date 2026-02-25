#!/usr/bin/env python3
"""Eden Analytics Pro - Telegram Bot Launcher.

Simple launcher for the Telegram bot with configuration validation.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Colors for terminal
class Colors:
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    CYAN = '\033[96m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def show_header():
    """Show bot launcher header."""
    header = f"""
{Colors.CYAN}╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║        🤖  Eden Analytics Pro - Telegram Bot  🤖              ║
║                       Version 2.1.1                           ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝{Colors.ENDC}
    """
    print(header)

def check_dependencies():
    """Check if required dependencies are installed."""
    print("📋 Checking dependencies...")
    
    missing = []
    
    try:
        from telegram import Bot
        print(f"  {Colors.GREEN}✓{Colors.ENDC} python-telegram-bot")
    except ImportError:
        missing.append("python-telegram-bot")
        print(f"  {Colors.FAIL}✗{Colors.ENDC} python-telegram-bot")
    
    try:
        import yaml
        print(f"  {Colors.GREEN}✓{Colors.ENDC} pyyaml")
    except ImportError:
        missing.append("pyyaml")
        print(f"  {Colors.FAIL}✗{Colors.ENDC} pyyaml")
    
    return missing

def load_config():
    """Load and validate configuration."""
    print("\n📋 Loading configuration...")
    
    config_path = project_root / "config" / "config.yaml"
    
    if not config_path.exists():
        print(f"  {Colors.FAIL}✗{Colors.ENDC} config/config.yaml not found")
        return None
    
    try:
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        telegram_config = config.get('telegram', {})
        
        if not telegram_config.get('enabled', False):
            print(f"  {Colors.WARNING}⚠{Colors.ENDC} Telegram bot is disabled in config")
            print(f"    Set 'telegram.enabled: true' in config/config.yaml")
            return None
        
        print(f"  {Colors.GREEN}✓{Colors.ENDC} Configuration loaded")
        return telegram_config
        
    except Exception as e:
        print(f"  {Colors.FAIL}✗{Colors.ENDC} Error loading config: {e}")
        return None

def validate_token(token: str):
    """Validate the bot token format."""
    print("\n📋 Validating bot token...")
    
    if not token or token == "YOUR_BOT_TOKEN_HERE":
        print(f"  {Colors.FAIL}✗{Colors.ENDC} Bot token not configured")
        print(f"    Please set your bot token in config/config.yaml")
        return False
    
    # Basic format check: should be like 123456789:ABCdefGhIjKlmNoPqRsTuVwXyZ
    if ':' not in token or len(token) < 30:
        print(f"  {Colors.WARNING}⚠{Colors.ENDC} Token format may be invalid")
        return True  # Continue anyway
    
    print(f"  {Colors.GREEN}✓{Colors.ENDC} Token format valid")
    return True

async def test_connection(token: str):
    """Test connection to Telegram API."""
    print("\n📋 Testing Telegram API connection...")
    
    try:
        from telegram import Bot
        
        bot = Bot(token=token)
        me = await bot.get_me()
        
        print(f"  {Colors.GREEN}✓{Colors.ENDC} Connected successfully")
        print(f"    Bot name: {me.first_name}")
        print(f"    Username: @{me.username}")
        return True
        
    except Exception as e:
        print(f"  {Colors.FAIL}✗{Colors.ENDC} Connection failed: {e}")
        return False

async def run_bot(token: str, admin_ids: list):
    """Run the Telegram bot."""
    print(f"\n{Colors.GREEN}🚀 Starting Telegram bot...{Colors.ENDC}")
    print("   Press Ctrl+C to stop\n")
    
    try:
        from telegram_bot.multi_user_bot import MultiUserTelegramBot
        from database.db_manager import DatabaseManager
        
        db_manager = DatabaseManager()
        bot = MultiUserTelegramBot(
            token=token,
            db_manager=db_manager,
            admin_ids=admin_ids
        )
        
        await bot.start()
        
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}⚠ Bot stopped by user{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.FAIL}❌ Error running bot: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()

def main():
    """Main launcher function."""
    show_header()
    
    # Check dependencies
    missing = check_dependencies()
    if missing:
        print(f"\n{Colors.FAIL}❌ Missing dependencies: {', '.join(missing)}{Colors.ENDC}")
        print("   Please run: pip install -r requirements.txt")
        sys.exit(1)
    
    # Load configuration
    config = load_config()
    if not config:
        sys.exit(1)
    
    # Get token from config or environment
    token = config.get('bot_token') or os.environ.get('EDEN_BOT_TOKEN')
    admin_ids = config.get('admin_ids', [])
    
    # Validate token
    if not validate_token(token):
        sys.exit(1)
    
    # Test connection
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if not loop.run_until_complete(test_connection(token)):
        print(f"\n{Colors.WARNING}⚠ Continuing despite connection test failure...{Colors.ENDC}")
    
    # Run the bot
    try:
        loop.run_until_complete(run_bot(token, admin_ids))
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Bot stopped{Colors.ENDC}")
    finally:
        loop.close()

if __name__ == "__main__":
    main()
