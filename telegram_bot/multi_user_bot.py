"""Multi-User Telegram Bot for Eden Analytics Pro."""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from pathlib import Path
import yaml

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler
)

from database.user_manager import UserManager, User, SubscriptionTier
from database.db_manager import DatabaseManager
from utils.logger import get_logger

logger = get_logger(__name__)

# Conversation states
REGISTER_BANKROLL = 1
SETTINGS_MENU = 2


class MultiUserTelegramBot:
    """Multi-user Telegram bot with user management and admin features."""
    
    def __init__(self, token: str, db_manager: DatabaseManager = None,
                 admin_ids: List[int] = None):
        self.token = token
        self.db_manager = db_manager or DatabaseManager()
        self.user_manager = UserManager()
        self.admin_ids = admin_ids or []
        
        self.application: Optional[Application] = None
        self.is_running = False
        
        self._load_config()
    
    def _load_config(self):
        """Load bot configuration."""
        config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                telegram_config = config.get('telegram', {})
                self.enabled = telegram_config.get('enabled', False)
                
                # Add admin IDs from config
                config_admins = telegram_config.get('admin_ids', [])
                self.admin_ids.extend(config_admins)
        except Exception as e:
            logger.warning(f"Could not load config: {e}")
            self.enabled = False
    
    async def start(self):
        """Start the bot."""
        if not self.token or not self.enabled:
            logger.warning("Telegram bot not configured or disabled")
            return
        
        self.application = Application.builder().token(self.token).build()
        
        # Register handlers
        self._register_handlers()
        
        # Start polling
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        self.is_running = True
        logger.info("Multi-user Telegram bot started")
    
    async def stop(self):
        """Stop the bot."""
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
        
        self.is_running = False
        logger.info("Telegram bot stopped")
    
    def _register_handlers(self):
        """Register all command handlers."""
        app = self.application
        
        # User commands
        app.add_handler(CommandHandler("start", self.cmd_start))
        app.add_handler(CommandHandler("help", self.cmd_help))
        app.add_handler(CommandHandler("register", self.cmd_register))
        app.add_handler(CommandHandler("profile", self.cmd_profile))
        app.add_handler(CommandHandler("bankroll", self.cmd_bankroll))
        app.add_handler(CommandHandler("stats", self.cmd_stats))
        app.add_handler(CommandHandler("history", self.cmd_history))
        app.add_handler(CommandHandler("arbitrage", self.cmd_arbitrage))
        app.add_handler(CommandHandler("settings", self.cmd_settings))
        app.add_handler(CommandHandler("subscribe", self.cmd_subscribe))
        
        # Admin commands
        app.add_handler(CommandHandler("admin", self.cmd_admin))
        app.add_handler(CommandHandler("users", self.cmd_users))
        app.add_handler(CommandHandler("broadcast", self.cmd_broadcast))
        app.add_handler(CommandHandler("ban", self.cmd_ban))
        app.add_handler(CommandHandler("unban", self.cmd_unban))
        app.add_handler(CommandHandler("premium", self.cmd_premium))
        
        # Callback query handler for inline buttons
        app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Registration conversation
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("setup", self.cmd_setup)],
            states={
                REGISTER_BANKROLL: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.setup_bankroll)]
            },
            fallbacks=[CommandHandler("cancel", self.cmd_cancel)]
        )
        app.add_handler(conv_handler)
    
    # User Commands
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        telegram_id = update.effective_user.id
        user = self.user_manager.get_user_by_telegram_id(telegram_id)
        
        if user:
            # Welcome back
            await update.message.reply_text(
                f"👋 Welcome back, {user.full_name}!\n\n"
                f"🏒 *Eden Analytics Pro*\n"
                f"Your intelligent hockey betting companion.\n\n"
                f"Use /help to see available commands.",
                parse_mode='Markdown'
            )
        else:
            # New user
            new_user = self.user_manager.register_user(
                telegram_id=telegram_id,
                username=update.effective_user.username,
                first_name=update.effective_user.first_name,
                last_name=update.effective_user.last_name
            )
            
            if new_user:
                await update.message.reply_text(
                    f"🎉 Welcome to *Eden Analytics Pro*!\n\n"
                    f"You've been registered successfully.\n\n"
                    f"🏒 Features:\n"
                    f"• ML-powered overtime predictions\n"
                    f"• Real-time arbitrage detection\n"
                    f"• Personal bankroll tracking\n"
                    f"• Performance analytics\n\n"
                    f"Use /setup to configure your bankroll.\n"
                    f"Use /help to see all commands.",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "❌ Registration failed. Please try again later."
                )
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        user = self._get_user(update)
        
        help_text = """
🏒 *Eden Analytics Pro - Commands*

*Basic Commands:*
/start - Start the bot
/help - Show this help
/profile - View your profile
/stats - View your statistics

*Betting Commands:*
/arbitrage - Find arbitrage opportunities
/history - View your bet history
/bankroll - Manage your bankroll

*Settings:*
/settings - Bot settings
/subscribe - Upgrade to Premium

"""
        if user and user.is_admin:
            help_text += """
*Admin Commands:*
/admin - Admin dashboard
/users - List all users
/broadcast <message> - Send to all users
/ban <user_id> - Ban a user
/unban <user_id> - Unban a user
/premium <user_id> - Grant premium
"""
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def cmd_register(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /register command."""
        # Same as start for new users
        await self.cmd_start(update, context)
    
    async def cmd_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /profile command."""
        user = self._get_user(update)
        if not user:
            await update.message.reply_text("❌ Please /start first to register.")
            return
        
        bankroll = self.user_manager.get_user_bankroll(user.user_id)
        
        tier_emoji = "👑" if user.is_admin else ("⭐" if user.is_premium else "🆓")
        tier_name = user.subscription_tier.value.title()
        
        profile_text = f"""
👤 *Your Profile*

*Name:* {user.full_name}
*Username:* @{user.username or 'N/A'}
*Tier:* {tier_emoji} {tier_name}
*Registered:* {user.registration_date.strftime('%Y-%m-%d')}

💰 *Bankroll:*
• Current: ${bankroll.current_bankroll:,.2f}
• Profit: ${bankroll.total_profit:+,.2f}
• ROI: {bankroll.roi:.1f}%

📊 *Stats:*
• Total Bets: {bankroll.total_bets}
• Win Rate: {bankroll.win_rate*100:.1f}%
• Wins: {bankroll.win_count}
• Losses: {bankroll.loss_count}
• Holes: {bankroll.hole_count}
"""
        
        if user.is_premium and user.subscription_expires:
            expires = user.subscription_expires.strftime('%Y-%m-%d')
            profile_text += f"\n⏰ *Premium expires:* {expires}"
        
        await update.message.reply_text(profile_text, parse_mode='Markdown')
    
    async def cmd_bankroll(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /bankroll command."""
        user = self._get_user(update)
        if not user:
            await update.message.reply_text("❌ Please /start first to register.")
            return
        
        bankroll = self.user_manager.get_user_bankroll(user.user_id)
        
        keyboard = [
            [InlineKeyboardButton("📈 View History", callback_data="bankroll_history")],
            [InlineKeyboardButton("💰 Set Bankroll", callback_data="bankroll_set")],
            [InlineKeyboardButton("🔄 Reset Stats", callback_data="bankroll_reset")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"💰 *Bankroll Management*\n\n"
            f"Current Bankroll: *${bankroll.current_bankroll:,.2f}*\n"
            f"Initial Bankroll: ${bankroll.initial_bankroll:,.2f}\n"
            f"Total Profit: ${bankroll.total_profit:+,.2f}\n"
            f"ROI: {bankroll.roi:.1f}%",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command."""
        user = self._get_user(update)
        if not user:
            await update.message.reply_text("❌ Please /start first to register.")
            return
        
        bankroll = self.user_manager.get_user_bankroll(user.user_id)
        
        # Calculate additional stats
        avg_profit = bankroll.total_profit / bankroll.total_bets if bankroll.total_bets > 0 else 0
        
        await update.message.reply_text(
            f"📊 *Your Statistics*\n\n"
            f"*Performance:*\n"
            f"• Total Bets: {bankroll.total_bets}\n"
            f"• Win Rate: {bankroll.win_rate*100:.1f}%\n"
            f"• ROI: {bankroll.roi:.1f}%\n\n"
            f"*Results:*\n"
            f"• Wins: {bankroll.win_count} ✅\n"
            f"• Losses: {bankroll.loss_count} ❌\n"
            f"• Holes: {bankroll.hole_count} 🕳️\n\n"
            f"*Profit:*\n"
            f"• Total: ${bankroll.total_profit:+,.2f}\n"
            f"• Average: ${avg_profit:+,.2f}/bet",
            parse_mode='Markdown'
        )
    
    async def cmd_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /history command."""
        user = self._get_user(update)
        if not user:
            await update.message.reply_text("❌ Please /start first to register.")
            return
        
        bets = self.user_manager.get_user_bets(user.user_id, limit=10)
        
        if not bets:
            await update.message.reply_text("📜 No betting history yet.")
            return
        
        history_text = "📜 *Recent Bets (Last 10):*\n\n"
        
        for bet in bets:
            result_emoji = {"win": "✅", "loss": "❌", "hole": "🕳️", None: "⏳"}.get(bet.get('result'), "⏳")
            profit = bet.get('profit', 0)
            profit_str = f"${profit:+,.2f}" if profit else "Pending"
            
            history_text += (
                f"{result_emoji} {bet.get('home_team', 'N/A')} vs {bet.get('away_team', 'N/A')}\n"
                f"   Stake: ${bet.get('total_stake', 0):.2f} | {profit_str}\n\n"
            )
        
        await update.message.reply_text(history_text, parse_mode='Markdown')
    
    async def cmd_arbitrage(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /arbitrage command."""
        user = self._get_user(update)
        if not user:
            await update.message.reply_text("❌ Please /start first to register.")
            return
        
        # Check rate limit
        remaining = self.user_manager.check_daily_limit(user.user_id, 'arbitrage_searches')
        
        if remaining <= 0:
            await update.message.reply_text(
                "❌ Daily limit reached!\n\n"
                "Free users: 10 searches/day\n"
                "Use /subscribe to upgrade to Premium for unlimited searches."
            )
            return
        
        # Increment usage
        self.user_manager.increment_daily_usage(user.user_id, 'arbitrage_searches')
        
        await update.message.reply_text("🔍 Searching for arbitrage opportunities...")
        
        # Fetch opportunities (using existing logic)
        try:
            from core.odds_fetcher import OddsFetcher
            from core.arbitrage_finder import ArbitrageFinder
            from analysis.match_analyzer import MatchAnalyzer
            
            # Load config
            config_path = Path(__file__).parent.parent / "config" / "config.yaml"
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            api_config = config.get('api', {}).get('the_odds_api', {})
            
            fetcher = OddsFetcher(
                api_key=api_config.get('key', ''),
                sport='icehockey_nhl'
            )
            finder = ArbitrageFinder()
            analyzer = MatchAnalyzer()
            
            matches = fetcher.fetch_odds(markets="h2h")
            
            if not matches:
                await update.message.reply_text(
                    "📭 No matches found at this time.\n"
                    "Try again later!"
                )
                return
            
            opportunities = finder.find_arbitrage(matches)
            
            if not opportunities:
                await update.message.reply_text(
                    f"📭 No arbitrage opportunities found.\n"
                    f"Analyzed {len(matches)} matches.\n\n"
                    f"💡 Remaining searches today: {remaining - 1}"
                )
                return
            
            # Analyze opportunities
            analyses = []
            for opp in opportunities[:5]:  # Limit to 5
                analysis = analyzer.analyze(opp)
                analyses.append(analysis)
            
            # Format results
            result_text = f"🎯 *Found {len(opportunities)} Opportunities!*\n\n"
            
            for i, analysis in enumerate(analyses, 1):
                rec_emoji = {"bet": "✅", "skip": "❌", "caution": "⚠️"}.get(
                    analysis.recommendation.value, "❓"
                )
                
                result_text += (
                    f"*{i}. {analysis.home_team} vs {analysis.away_team}*\n"
                    f"   ROI: {analysis.roi*100:.2f}% | Hole: {analysis.hole_probability*100:.1f}%\n"
                    f"   {rec_emoji} {analysis.recommendation.value.upper()}\n\n"
                )
            
            result_text += f"💡 Remaining searches: {remaining - 1}"
            
            await update.message.reply_text(result_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Arbitrage search error: {e}")
            await update.message.reply_text(
                f"❌ Error searching for opportunities.\n"
                f"Please try again later."
            )
    
    async def cmd_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /settings command."""
        user = self._get_user(update)
        if not user:
            await update.message.reply_text("❌ Please /start first to register.")
            return
        
        keyboard = [
            [InlineKeyboardButton("🔔 Notifications", callback_data="settings_notifications")],
            [InlineKeyboardButton("⚠️ Confidence Level", callback_data="settings_confidence")],
            [InlineKeyboardButton("💰 Bankroll Settings", callback_data="settings_bankroll")],
            [InlineKeyboardButton("📊 Analytics", callback_data="settings_analytics")],
            [InlineKeyboardButton("🌐 Language", callback_data="settings_language")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "⚙️ *Settings*\n\nChoose a category:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def cmd_subscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /subscribe command."""
        user = self._get_user(update)
        if not user:
            await update.message.reply_text("❌ Please /start first to register.")
            return
        
        if user.is_premium:
            expires = user.subscription_expires.strftime('%Y-%m-%d') if user.subscription_expires else "Never"
            await update.message.reply_text(
                f"⭐ You already have Premium!\n"
                f"Expires: {expires}"
            )
            return
        
        await update.message.reply_text(
            "⭐ *Eden Analytics Pro Premium*\n\n"
            "*Benefits:*\n"
            "• ♾️ Unlimited arbitrage searches\n"
            "• 🔔 Priority notifications\n"
            "• 📊 Advanced analytics\n"
            "• 🤖 Custom ML model access\n"
            "• 💬 Priority support\n\n"
            "*Price:* $9.99/month\n\n"
            "Contact @EdenSupport to subscribe!",
            parse_mode='Markdown'
        )
    
    async def cmd_setup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /setup command - start registration flow."""
        user = self._get_user(update)
        if not user:
            await update.message.reply_text("❌ Please /start first to register.")
            return
        
        await update.message.reply_text(
            "💰 *Initial Setup*\n\n"
            "Please enter your initial bankroll amount (in USD):\n"
            "Example: 1000",
            parse_mode='Markdown'
        )
        
        return REGISTER_BANKROLL
    
    async def setup_bankroll(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle bankroll input during setup."""
        user = self._get_user(update)
        
        try:
            amount = float(update.message.text.replace(',', '').replace('$', ''))
            
            if amount < 10:
                await update.message.reply_text("❌ Minimum bankroll is $10. Please try again.")
                return REGISTER_BANKROLL
            
            if amount > 1000000:
                await update.message.reply_text("❌ Maximum bankroll is $1,000,000. Please try again.")
                return REGISTER_BANKROLL
            
            self.user_manager.set_initial_bankroll(user.user_id, amount)
            
            await update.message.reply_text(
                f"✅ Bankroll set to *${amount:,.2f}*\n\n"
                f"You're all set! Use /arbitrage to start finding opportunities.",
                parse_mode='Markdown'
            )
            
            return ConversationHandler.END
            
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid amount. Please enter a number.\n"
                "Example: 1000"
            )
            return REGISTER_BANKROLL
    
    async def cmd_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /cancel command."""
        await update.message.reply_text("❌ Operation cancelled.")
        return ConversationHandler.END
    
    # Admin Commands
    
    async def cmd_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /admin command - admin dashboard."""
        if not self._is_admin(update):
            await update.message.reply_text("❌ You don't have admin access.")
            return
        
        stats = self.user_manager.get_user_count()
        
        await update.message.reply_text(
            "👑 *Admin Dashboard*\n\n"
            f"📊 *User Statistics:*\n"
            f"• Total Users: {stats['total']}\n"
            f"• Active Users: {stats['active']}\n"
            f"• Premium Users: {stats['premium']}\n"
            f"• Admins: {stats['admins']}\n\n"
            f"*Commands:*\n"
            f"/users - List users\n"
            f"/broadcast <msg> - Send to all\n"
            f"/ban <id> - Ban user\n"
            f"/unban <id> - Unban user\n"
            f"/premium <id> - Grant premium",
            parse_mode='Markdown'
        )
    
    async def cmd_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /users command - list users."""
        if not self._is_admin(update):
            await update.message.reply_text("❌ You don't have admin access.")
            return
        
        users = self.user_manager.get_all_users(active_only=False)[:20]
        
        text = "👥 *Users (Last 20):*\n\n"
        
        for user in users:
            status = "✅" if user.is_active else "❌"
            tier = "👑" if user.is_admin else ("⭐" if user.is_premium else "🆓")
            text += f"{status} {tier} {user.full_name} (ID: {user.user_id})\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /broadcast command - send message to all users."""
        if not self._is_admin(update):
            await update.message.reply_text("❌ You don't have admin access.")
            return
        
        if not context.args:
            await update.message.reply_text("Usage: /broadcast <message>")
            return
        
        message = " ".join(context.args)
        users = self.user_manager.get_all_users()
        
        sent = 0
        failed = 0
        
        await update.message.reply_text(f"📢 Broadcasting to {len(users)} users...")
        
        for user in users:
            try:
                await context.bot.send_message(
                    chat_id=user.telegram_id,
                    text=f"📢 *Announcement*\n\n{message}",
                    parse_mode='Markdown'
                )
                sent += 1
            except Exception as e:
                failed += 1
                logger.warning(f"Failed to send to {user.telegram_id}: {e}")
        
        await update.message.reply_text(
            f"✅ Broadcast complete!\n"
            f"Sent: {sent} | Failed: {failed}"
        )
    
    async def cmd_ban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ban command."""
        if not self._is_admin(update):
            await update.message.reply_text("❌ You don't have admin access.")
            return
        
        if not context.args:
            await update.message.reply_text("Usage: /ban <user_id>")
            return
        
        try:
            user_id = int(context.args[0])
            if self.user_manager.deactivate_user(user_id):
                await update.message.reply_text(f"✅ User {user_id} has been banned.")
            else:
                await update.message.reply_text(f"❌ Failed to ban user {user_id}.")
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID.")
    
    async def cmd_unban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /unban command."""
        if not self._is_admin(update):
            await update.message.reply_text("❌ You don't have admin access.")
            return
        
        if not context.args:
            await update.message.reply_text("Usage: /unban <user_id>")
            return
        
        try:
            user_id = int(context.args[0])
            if self.user_manager.activate_user(user_id):
                await update.message.reply_text(f"✅ User {user_id} has been unbanned.")
            else:
                await update.message.reply_text(f"❌ Failed to unban user {user_id}.")
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID.")
    
    async def cmd_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /premium command - grant premium to user."""
        if not self._is_admin(update):
            await update.message.reply_text("❌ You don't have admin access.")
            return
        
        if not context.args:
            await update.message.reply_text("Usage: /premium <user_id> [months]")
            return
        
        try:
            user_id = int(context.args[0])
            months = int(context.args[1]) if len(context.args) > 1 else 1
            
            if self.user_manager.upgrade_to_premium(user_id, months):
                await update.message.reply_text(
                    f"✅ User {user_id} upgraded to Premium for {months} month(s)!"
                )
            else:
                await update.message.reply_text(f"❌ Failed to upgrade user {user_id}.")
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID or months.")
    
    # Callback Handlers
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("bankroll_"):
            await self._handle_bankroll_callback(update, context, data)
        elif data.startswith("settings_") or data.startswith("conf_"):
            await self._handle_settings_callback(update, context, data)
    
    async def _handle_bankroll_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle bankroll-related callbacks."""
        query = update.callback_query
        user = self._get_user_from_callback(update)
        
        if data == "bankroll_history":
            bets = self.user_manager.get_user_bets(user.user_id, limit=5)
            
            if not bets:
                await query.edit_message_text("📜 No betting history yet.")
                return
            
            text = "📜 *Last 5 Bets:*\n\n"
            for bet in bets:
                profit = bet.get('profit', 0)
                result = bet.get('result', 'pending')
                text += f"• {bet.get('home_team')} vs {bet.get('away_team')}: {result} (${profit:+,.2f})\n"
            
            await query.edit_message_text(text, parse_mode='Markdown')
        
        elif data == "bankroll_set":
            await query.edit_message_text(
                "💰 To set a new bankroll, use:\n/setup"
            )
        
        elif data == "bankroll_reset":
            bankroll = self.user_manager.get_user_bankroll(user.user_id)
            self.user_manager.set_initial_bankroll(user.user_id, bankroll.initial_bankroll)
            await query.edit_message_text("✅ Bankroll stats have been reset!")
    
    async def _handle_settings_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle settings-related callbacks."""
        query = update.callback_query
        user = self._get_user_from_callback(update)
        
        if data == "settings_confidence":
            # Show confidence level options
            keyboard = [
                [InlineKeyboardButton("✅ High Only (BET)", callback_data="conf_high_only")],
                [InlineKeyboardButton("⚠️ High + Caution (Recommended)", callback_data="conf_include_caution")],
                [InlineKeyboardButton("🔙 Back", callback_data="settings_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "⚠️ *Confidence Level Settings*\n\n"
                "Choose which recommendations you want to receive:\n\n"
                "✅ *High Only*: Only BET recommendations\n"
                "⚠️ *High + Caution*: BET and CAUTION recommendations\n\n"
                "_CAUTION bets have slightly higher risk but can still be profitable._",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            return
        
        elif data == "conf_high_only":
            self.user_manager.update_user_setting(user.user_id, 'include_caution', False)
            await query.edit_message_text(
                "✅ *Setting Updated!*\n\n"
                "You will now only receive BET (high confidence) recommendations.\n\n"
                "Use /settings to change this anytime.",
                parse_mode='Markdown'
            )
            return
        
        elif data == "conf_include_caution":
            self.user_manager.update_user_setting(user.user_id, 'include_caution', True)
            await query.edit_message_text(
                "⚠️ *Setting Updated!*\n\n"
                "You will now receive both BET and CAUTION recommendations.\n\n"
                "_CAUTION bets may have slightly higher risk but can offer good opportunities._\n\n"
                "Use /settings to change this anytime.",
                parse_mode='Markdown'
            )
            return
        
        elif data == "settings_back":
            # Go back to main settings
            keyboard = [
                [InlineKeyboardButton("🔔 Notifications", callback_data="settings_notifications")],
                [InlineKeyboardButton("⚠️ Confidence Level", callback_data="settings_confidence")],
                [InlineKeyboardButton("💰 Bankroll Settings", callback_data="settings_bankroll")],
                [InlineKeyboardButton("📊 Analytics", callback_data="settings_analytics")],
                [InlineKeyboardButton("🌐 Language", callback_data="settings_language")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "⚙️ *Settings*\n\nChoose a category:",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            return
        
        settings_texts = {
            "settings_notifications": "🔔 *Notification Settings*\n\nComing soon!",
            "settings_bankroll": "💰 *Bankroll Settings*\n\nUse /setup to configure.",
            "settings_analytics": "📊 *Analytics Settings*\n\nComing soon!",
            "settings_language": "🌐 *Language Settings*\n\nCurrently English only."
        }
        
        text = settings_texts.get(data, "Unknown setting")
        await query.edit_message_text(text, parse_mode='Markdown')
    
    # Helper Methods
    
    def _get_user(self, update: Update) -> Optional[User]:
        """Get user from update."""
        telegram_id = update.effective_user.id
        return self.user_manager.get_user_by_telegram_id(telegram_id)
    
    def _get_user_from_callback(self, update: Update) -> Optional[User]:
        """Get user from callback query."""
        telegram_id = update.callback_query.from_user.id
        return self.user_manager.get_user_by_telegram_id(telegram_id)
    
    def _is_admin(self, update: Update) -> bool:
        """Check if user is admin."""
        telegram_id = update.effective_user.id
        
        # Check admin IDs list
        if telegram_id in self.admin_ids:
            return True
        
        # Check database
        user = self._get_user(update)
        return user and user.is_admin


__all__ = ['MultiUserTelegramBot']
