"""Main Telegram Bot Class for Eden MVP.

Provides real-time notifications about arbitrage opportunities.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path
import yaml

try:
    from telegram import Update, Bot
    from telegram.ext import (
        Application, ApplicationBuilder, CommandHandler,
        CallbackQueryHandler, ContextTypes, MessageHandler, filters
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    Update = None
    Bot = None
    Application = None
    ContextTypes = None

from utils.logger import get_logger

logger = get_logger(__name__)


class TelegramBot:
    """Main Telegram Bot for Eden MVP.
    
    Features:
    - Real-time arbitrage notifications
    - User-specific filters
    - Command handling (/start, /stop, /stats, etc.)
    - Thread-safe operation
    - Both polling and webhook modes
    
    Example:
        >>> bot = TelegramBot(token="YOUR_BOT_TOKEN")
        >>> await bot.start()
        >>> await bot.send_arbitrage_notification(opportunity)
    """
    
    # Placeholder tokens that should be treated as missing
    PLACEHOLDER_TOKENS = {
        "YOUR_BOT_TOKEN_HERE",
        "YOUR_BOT_TOKEN",
        "YOUR_TOKEN_HERE",
        "",
    }
    
    def __init__(
        self,
        token: Optional[str] = None,
        config_path: Optional[str] = None,
        db_manager=None
    ):
        """Initialize TelegramBot.
        
        Args:
            token: Bot token from @BotFather
            config_path: Path to telegram_config.yaml
            db_manager: DatabaseManager instance for user preferences
        """
        # Initialize all attributes first to ensure is_running property works
        self.enabled = False
        self._running = False
        self.application: Optional[Application] = None
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self.config: Dict[str, Any] = {}
        self.token = ""
        self.db_manager = db_manager
        
        # Check if telegram library is available
        if not TELEGRAM_AVAILABLE:
            logger.warning("python-telegram-bot not installed. Telegram features disabled.")
            return
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Check if telegram is disabled in main config
        main_config = self._load_main_config()
        telegram_config = main_config.get('telegram', {})
        if not telegram_config.get('enabled', True):
            logger.info("Telegram bot disabled in config.")
            return
        
        # Get token from parameter or config
        self.token = token if token else self.config.get('bot_token', '')
        
        # Check if token is valid (not empty or placeholder)
        if not self.token or self.token in self.PLACEHOLDER_TOKENS:
            logger.warning("No valid Telegram bot token provided. Bot disabled.")
            self.token = ""
            return
        
        # All checks passed, enable the bot
        self.enabled = True
        
        # Import handlers here to avoid circular imports
        from telegram_bot.handlers import BotHandlers
        from telegram_bot.notifications import NotificationSender
        
        self.handlers = BotHandlers(self)
        self.notifier = NotificationSender(self)
        
        logger.info("TelegramBot initialized")
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if config_path:
            path = Path(config_path)
        else:
            path = Path(__file__).parent.parent / "config" / "telegram_config.yaml"
        
        if path.exists():
            try:
                with open(path, 'r') as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                logger.error(f"Failed to load Telegram config: {e}")
        
        return {}
    
    def _load_main_config(self) -> Dict[str, Any]:
        """Load main application config to check if telegram is enabled."""
        path = Path(__file__).parent.parent / "config" / "config.yaml"
        
        if path.exists():
            try:
                with open(path, 'r') as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                logger.error(f"Failed to load main config: {e}")
        
        return {}
    
    async def _build_application(self) -> None:
        """Build the Telegram application with handlers."""
        self.application = (
            ApplicationBuilder()
            .token(self.token)
            .build()
        )
        
        # Register command handlers
        self.application.add_handler(CommandHandler("start", self.handlers.cmd_start))
        self.application.add_handler(CommandHandler("stop", self.handlers.cmd_stop))
        self.application.add_handler(CommandHandler("resume", self.handlers.cmd_resume))
        self.application.add_handler(CommandHandler("stats", self.handlers.cmd_stats))
        self.application.add_handler(CommandHandler("settings", self.handlers.cmd_settings))
        self.application.add_handler(CommandHandler("help", self.handlers.cmd_help))
        self.application.add_handler(CommandHandler("status", self.handlers.cmd_status))
        
        # Callback query handler for inline buttons
        self.application.add_handler(CallbackQueryHandler(self.handlers.handle_callback))
        
        # Error handler
        self.application.add_error_handler(self._error_handler)
        
        logger.info("Telegram bot application built with handlers")
    
    async def _error_handler(self, update, context) -> None:
        """Handle errors."""
        logger.error(f"Telegram error: {context.error}")
    
    async def start_polling(self) -> None:
        """Start the bot in polling mode."""
        if not self.enabled:
            logger.warning("Cannot start disabled bot")
            return
        
        await self._build_application()
        
        logger.info("Starting Telegram bot in polling mode...")
        self._running = True
        
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"]
        )
    
    async def stop(self) -> None:
        """Stop the bot."""
        if self.application and self._running:
            logger.info("Stopping Telegram bot...")
            self._running = False
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
    
    def start_in_thread(self) -> None:
        """Start the bot in a background thread."""
        if not self.enabled:
            return
        
        def run_bot():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            try:
                self._loop.run_until_complete(self.start_polling())
                self._loop.run_forever()
            except Exception as e:
                logger.error(f"Bot thread error: {e}")
            finally:
                self._loop.close()
        
        self._thread = threading.Thread(target=run_bot, daemon=True)
        self._thread.start()
        logger.info("Telegram bot started in background thread")
    
    def stop_thread(self) -> None:
        """Stop the bot running in a background thread."""
        if self._loop and self._running:
            asyncio.run_coroutine_threadsafe(self.stop(), self._loop)
            if self._loop.is_running():
                self._loop.call_soon_threadsafe(self._loop.stop)
    
    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "HTML",
        reply_markup=None
    ) -> bool:
        """Send a message to a specific chat."""
        if not self.enabled or not self.application:
            return False
        
        try:
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {chat_id}: {e}")
            return False
    
    def send_message_sync(self, chat_id: int, text: str, **kwargs) -> bool:
        """Send a message synchronously (for use from non-async code)."""
        if not self.enabled or not self._loop:
            return False
        
        future = asyncio.run_coroutine_threadsafe(
            self.send_message(chat_id, text, **kwargs),
            self._loop
        )
        try:
            return future.result(timeout=10)
        except Exception as e:
            logger.error(f"Sync send_message failed: {e}")
            return False
    
    async def broadcast(
        self,
        text: str,
        filter_func: Optional[Callable] = None
    ) -> int:
        """Broadcast a message to all enabled users.
        
        Args:
            text: Message to send
            filter_func: Optional function to filter users
            
        Returns:
            Number of messages successfully sent
        """
        if not self.db_manager:
            return 0
        
        users = self.db_manager.get_telegram_users(enabled_only=True)
        sent_count = 0
        
        for user in users:
            if filter_func and not filter_func(user):
                continue
            
            if await self.send_message(user['chat_id'], text):
                sent_count += 1
            
            # Rate limiting
            await asyncio.sleep(0.05)  # 20 messages per second max
        
        return sent_count
    
    @property
    def is_running(self) -> bool:
        """Check if bot is running."""
        return self._running and self.enabled
