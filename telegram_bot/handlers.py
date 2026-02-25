"""Telegram Command Handlers for Eden MVP.

Handles all bot commands and user interactions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Dict, Any
from datetime import datetime

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    Update = None
    InlineKeyboardButton = None
    InlineKeyboardMarkup = None
    ContextTypes = None

from utils.logger import get_logger

if TYPE_CHECKING:
    from telegram_bot.bot import TelegramBot

logger = get_logger(__name__)


class BotHandlers:
    """Handles Telegram bot commands and callbacks.
    
    Commands:
    - /start: Welcome message and registration
    - /stop: Disable notifications
    - /resume: Re-enable notifications
    - /stats: Show user statistics
    - /settings: Interactive settings menu
    - /help: List all commands
    - /status: Show bot status
    """
    
    def __init__(self, bot: 'TelegramBot'):
        """Initialize handlers.
        
        Args:
            bot: Parent TelegramBot instance
        """
        self.bot = bot
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command - Welcome and registration."""
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        logger.info(f"New user started bot: {user.username} ({user.id})")
        
        # Register user in database
        if self.bot.db_manager:
            self.bot.db_manager.add_telegram_user(
                user_id=user.id,
                chat_id=chat_id,
                username=user.username or "",
                first_name=user.first_name or ""
            )
        
        welcome_text = f"""
🏒 <b>Welcome to Eden MVP, {user.first_name}!</b>

I'll send you real-time notifications about hockey arbitrage opportunities.

<b>What I can do:</b>
✅ Find arbitrage opportunities in NHL/KHL matches
✅ Calculate optimal stake sizes
✅ Assess risk using ML-based OT prediction
✅ Filter opportunities by your preferences

<b>Quick Commands:</b>
/stats - View your statistics
/settings - Customize notification filters
/stop - Pause notifications
/help - See all commands

🎯 You're now subscribed to notifications!
Default filters: ROI ≥ 2%, Hole Risk ≤ 10%

Use /settings to customize.
        """
        
        await update.message.reply_text(welcome_text, parse_mode="HTML")
    
    async def cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stop command - Disable notifications."""
        user_id = update.effective_user.id
        
        if self.bot.db_manager:
            self.bot.db_manager.update_telegram_user(user_id, enabled=False)
        
        await update.message.reply_text(
            "🔕 <b>Notifications paused.</b>\n\n"
            "You won't receive arbitrage alerts until you use /resume.\n\n"
            "Miss you already! 🏒",
            parse_mode="HTML"
        )
        logger.info(f"User {user_id} disabled notifications")
    
    async def cmd_resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /resume command - Re-enable notifications."""
        user_id = update.effective_user.id
        
        if self.bot.db_manager:
            self.bot.db_manager.update_telegram_user(user_id, enabled=True)
        
        await update.message.reply_text(
            "🔔 <b>Notifications resumed!</b>\n\n"
            "You'll now receive arbitrage alerts based on your filter settings.\n\n"
            "Let's find some opportunities! 🚀",
            parse_mode="HTML"
        )
        logger.info(f"User {user_id} enabled notifications")
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stats command - Show user statistics."""
        user_id = update.effective_user.id
        
        # Get statistics from database
        stats = {}
        if self.bot.db_manager:
            stats = self.bot.db_manager.get_statistics()
        
        stats_text = f"""
📊 <b>Your Arbitrage Statistics</b>

<b>Betting Performance:</b>
├ Total Bets: {stats.get('total_bets', 0)}
├ Won: {stats.get('won', 0)} ✅
├ Lost: {stats.get('lost', 0)} ❌
├ Pending: {stats.get('pending', 0)} ⏳
└ Win Rate: {stats.get('win_rate', 0):.1f}%

<b>Financial:</b>
├ Total P/L: ${stats.get('total_profit_loss', 0):,.2f}
├ ROI: {stats.get('roi', 0):.2f}%
├ Best Bet: ${stats.get('best_result', 0):,.2f}
└ Worst Bet: ${stats.get('worst_result', 0):,.2f}

<b>Risk Analysis:</b>
├ Hole Count: {stats.get('hole_count', 0)} 🕳️
└ Hole Rate: {stats.get('hole_rate', 0):.1f}%

📈 Keep going! Use smart bankroll management.
        """
        
        await update.message.reply_text(stats_text, parse_mode="HTML")
    
    async def cmd_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /settings command - Interactive settings menu."""
        user_id = update.effective_user.id
        
        # Get current user settings
        user_settings = {'min_roi': 2.0, 'max_hole_risk': 10.0, 'leagues': 'NHL,KHL'}
        if self.bot.db_manager:
            user_data = self.bot.db_manager.get_telegram_user(user_id)
            if user_data:
                user_settings = {
                    'min_roi': user_data.get('min_roi', 2.0),
                    'max_hole_risk': user_data.get('max_hole_risk', 10.0),
                    'leagues': user_data.get('leagues', 'NHL,KHL')
                }
        
        keyboard = [
            [InlineKeyboardButton(f"📈 Min ROI: {user_settings['min_roi']:.1f}%", callback_data="set_roi")],
            [InlineKeyboardButton(f"🕳️ Max Hole Risk: {user_settings['max_hole_risk']:.1f}%", callback_data="set_hole_risk")],
            [InlineKeyboardButton(f"🏒 Leagues: {user_settings['leagues']}", callback_data="set_leagues")],
            [InlineKeyboardButton("🔄 Reset to Defaults", callback_data="reset_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "⚙️ <b>Notification Settings</b>\n\n"
            "Tap a setting to change it:",
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command - Show all commands."""
        help_text = """
🆘 <b>Eden MVP Bot Commands</b>

<b>Basic Commands:</b>
/start - Start the bot and subscribe
/stop - Pause all notifications
/resume - Resume notifications
/status - Check bot status

<b>Statistics:</b>
/stats - View your betting statistics

<b>Settings:</b>
/settings - Customize notification filters
  • Min ROI threshold
  • Max hole risk threshold
  • League preferences (NHL, KHL, etc.)

<b>Tips:</b>
💡 Higher Min ROI = fewer but better opportunities
💡 Lower Max Hole Risk = safer but fewer alerts
💡 Use /settings to find your sweet spot

<b>Need Help?</b>
Visit our documentation or contact support.
        """
        
        await update.message.reply_text(help_text, parse_mode="HTML")
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command - Show bot status."""
        user_id = update.effective_user.id
        
        # Get user settings
        enabled = True
        user_settings = {}
        if self.bot.db_manager:
            user_data = self.bot.db_manager.get_telegram_user(user_id)
            if user_data:
                enabled = user_data.get('enabled', True)
                user_settings = user_data
        
        status_emoji = "🟢" if enabled else "🔴"
        status_text = "Active" if enabled else "Paused"
        
        status_msg = f"""
📡 <b>Bot Status</b>

{status_emoji} Notifications: {status_text}
🤖 Bot Version: 1.0.0
⏰ Server Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<b>Your Filters:</b>
├ Min ROI: {user_settings.get('min_roi', 2.0):.1f}%
├ Max Hole Risk: {user_settings.get('max_hole_risk', 10.0):.1f}%
└ Leagues: {user_settings.get('leagues', 'NHL,KHL')}

<b>Bot Health:</b> ✅ All systems operational
        """
        
        await update.message.reply_text(status_msg, parse_mode="HTML")
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries from inline buttons."""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        data = query.data
        
        if data == "set_roi":
            keyboard = [
                [InlineKeyboardButton("1%", callback_data="roi_1"),
                 InlineKeyboardButton("2%", callback_data="roi_2"),
                 InlineKeyboardButton("3%", callback_data="roi_3")],
                [InlineKeyboardButton("4%", callback_data="roi_4"),
                 InlineKeyboardButton("5%", callback_data="roi_5"),
                 InlineKeyboardButton("6%", callback_data="roi_6")],
                [InlineKeyboardButton("⬅️ Back", callback_data="back_settings")]
            ]
            await query.edit_message_text(
                "📈 <b>Select Minimum ROI Threshold</b>\n\n"
                "Only opportunities with ROI above this value will be sent:",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        elif data.startswith("roi_"):
            roi_value = float(data.split("_")[1])
            if self.bot.db_manager:
                self.bot.db_manager.update_telegram_user(user_id, min_roi=roi_value)
            
            await query.edit_message_text(
                f"✅ Min ROI set to {roi_value}%\n\n"
                "Use /settings to see all your settings.",
                parse_mode="HTML"
            )
        
        elif data == "set_hole_risk":
            keyboard = [
                [InlineKeyboardButton("5%", callback_data="hole_5"),
                 InlineKeyboardButton("7.5%", callback_data="hole_7.5"),
                 InlineKeyboardButton("10%", callback_data="hole_10")],
                [InlineKeyboardButton("12.5%", callback_data="hole_12.5"),
                 InlineKeyboardButton("15%", callback_data="hole_15"),
                 InlineKeyboardButton("20%", callback_data="hole_20")],
                [InlineKeyboardButton("⬅️ Back", callback_data="back_settings")]
            ]
            await query.edit_message_text(
                "🕳️ <b>Select Maximum Hole Risk Threshold</b>\n\n"
                "Only opportunities with hole risk below this value will be sent:",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        elif data.startswith("hole_"):
            hole_value = float(data.split("_")[1])
            if self.bot.db_manager:
                self.bot.db_manager.update_telegram_user(user_id, max_hole_risk=hole_value)
            
            await query.edit_message_text(
                f"✅ Max Hole Risk set to {hole_value}%\n\n"
                "Use /settings to see all your settings.",
                parse_mode="HTML"
            )
        
        elif data == "set_leagues":
            keyboard = [
                [InlineKeyboardButton("NHL Only", callback_data="leagues_NHL")],
                [InlineKeyboardButton("KHL Only", callback_data="leagues_KHL")],
                [InlineKeyboardButton("NHL + KHL", callback_data="leagues_NHL,KHL")],
                [InlineKeyboardButton("All Leagues", callback_data="leagues_ALL")],
                [InlineKeyboardButton("⬅️ Back", callback_data="back_settings")]
            ]
            await query.edit_message_text(
                "🏒 <b>Select Leagues to Monitor</b>\n\n"
                "Choose which leagues you want notifications for:",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        elif data.startswith("leagues_"):
            leagues = data.split("_")[1]
            if self.bot.db_manager:
                self.bot.db_manager.update_telegram_user(user_id, leagues=leagues)
            
            await query.edit_message_text(
                f"✅ Leagues set to: {leagues}\n\n"
                "Use /settings to see all your settings.",
                parse_mode="HTML"
            )
        
        elif data == "reset_settings":
            if self.bot.db_manager:
                self.bot.db_manager.update_telegram_user(
                    user_id,
                    min_roi=2.0,
                    max_hole_risk=10.0,
                    leagues="NHL,KHL"
                )
            
            await query.edit_message_text(
                "🔄 <b>Settings Reset to Defaults</b>\n\n"
                "├ Min ROI: 2.0%\n"
                "├ Max Hole Risk: 10.0%\n"
                "└ Leagues: NHL, KHL\n\n"
                "Use /settings to customize again.",
                parse_mode="HTML"
            )
        
        elif data == "back_settings":
            # Return to main settings menu
            await self.cmd_settings(update, context)
