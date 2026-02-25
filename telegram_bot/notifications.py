"""Notification Sender for Eden MVP Telegram Bot.

Formats and sends arbitrage opportunity notifications.
"""

import asyncio
from typing import TYPE_CHECKING, Optional, Dict, Any, List
from datetime import datetime, timedelta
import time

from utils.logger import get_logger

if TYPE_CHECKING:
    from telegram_bot.bot import TelegramBot
    from analysis.match_analyzer import MatchAnalysis

logger = get_logger(__name__)


class NotificationSender:
    """Handles sending formatted notifications about arbitrage opportunities.
    
    Features:
    - Rich message formatting with emojis
    - User filter application
    - Rate limiting to avoid Telegram API limits
    - Batch notifications
    """
    
    def __init__(self, bot: 'TelegramBot'):
        """Initialize NotificationSender.
        
        Args:
            bot: Parent TelegramBot instance
        """
        self.bot = bot
        self._last_sent: Dict[int, datetime] = {}  # user_id -> last sent time
        self._rate_limit_seconds = 1.0  # Minimum seconds between messages per user
        self._batch_queue: List[Dict] = []  # Queue for batch notifications
        self._batch_interval = 5  # Seconds to wait before sending batch
    
    def format_opportunity(self, analysis: 'MatchAnalysis') -> str:
        """Format an arbitrage opportunity as a rich message.
        
        Args:
            analysis: MatchAnalysis object with opportunity details
            
        Returns:
            Formatted HTML message string
        """
        # Determine recommendation emoji
        rec_emoji = {
            "BET": "✅",
            "CAUTION": "⚠️",
            "SKIP": "❌"
        }.get(str(analysis.recommendation).upper().split(".")[-1], "❓")
        
        # Risk level emoji
        risk_emoji = {
            "LOW": "🟢",
            "MEDIUM": "🟡",
            "HIGH": "🟠",
            "EXTREME": "🔴"
        }.get(str(analysis.risk_level).upper().split(".")[-1], "⚪")
        
        # Format commence time
        try:
            commence_dt = datetime.fromisoformat(analysis.commence_time.replace('Z', '+00:00'))
            time_str = commence_dt.strftime('%b %d, %H:%M')
            time_until = commence_dt - datetime.now(commence_dt.tzinfo)
            hours_until = time_until.total_seconds() / 3600
            if hours_until > 0:
                if hours_until < 1:
                    time_until_str = f"⏰ Starting in {int(time_until.total_seconds() / 60)} min"
                else:
                    time_until_str = f"⏰ Starting in {hours_until:.1f}h"
            else:
                time_until_str = "⏰ In progress"
        except:
            time_str = analysis.commence_time
            time_until_str = ""
        
        # Build message
        message = f"""
🏒 <b>ARBITRAGE OPPORTUNITY</b> {rec_emoji}

<b>{analysis.team_strong}</b> vs <b>{analysis.team_weak}</b>
📅 {time_str}
{time_until_str}

💰 <b>ROI: {analysis.arb_roi:.2%}</b>

<b>Odds:</b>
├ {analysis.team_strong}: <code>{analysis.odds_strong:.2f}</code> ({analysis.bookmaker_strong})
└ {analysis.team_weak}: <code>{analysis.odds_weak_reg:.2f}</code> ({analysis.bookmaker_weak})

<b>Analysis:</b>
├ 🕳️ Hole Risk: {analysis.hole_probability:.1%}
├ ⚙️ OT Probability: {analysis.ot_probability:.1%}
├ 📊 EV: {analysis.expected_value:.2%}
├ {risk_emoji} Risk Level: {str(analysis.risk_level).split('.')[-1]}
└ 🎯 Confidence: {analysis.confidence_score:.0%}

<b>Recommended Stakes:</b>
├ {analysis.team_strong}: ${getattr(analysis, 'stake_strong', 0):.2f}
├ {analysis.team_weak}: ${getattr(analysis, 'stake_weak', 0):.2f}
├ Total: ${getattr(analysis, 'total_stake', 0):.2f}
└ Potential Profit: ${getattr(analysis, 'potential_profit', 0):.2f}

{self._format_recommendation(analysis)}
        """
        
        return message.strip()
    
    def _format_recommendation(self, analysis: 'MatchAnalysis') -> str:
        """Format the recommendation section."""
        rec = str(analysis.recommendation).split(".")[-1].upper()
        
        if rec == "BET":
            return "✅ <b>RECOMMENDATION: PLACE BET</b>\n" + \
                   "All criteria met. Good opportunity!"
        elif rec == "CAUTION":
            return "⚠️ <b>RECOMMENDATION: PROCEED WITH CAUTION</b>\n" + \
                   f"Reason: {analysis.reasoning[:100]}" if analysis.reasoning else "Review risk factors."
        else:
            return "❌ <b>RECOMMENDATION: SKIP</b>\n" + \
                   f"Reason: {analysis.reasoning[:100]}" if analysis.reasoning else "Does not meet criteria."
    
    def format_batch_summary(self, analyses: List['MatchAnalysis']) -> str:
        """Format multiple opportunities as a summary.
        
        Args:
            analyses: List of MatchAnalysis objects
            
        Returns:
            Formatted summary message
        """
        if not analyses:
            return "No new opportunities found."
        
        summary = f"""🏒 <b>ARBITRAGE SUMMARY</b>
📊 Found <b>{len(analyses)}</b> opportunities

"""
        
        for i, analysis in enumerate(analyses[:5], 1):  # Limit to 5 in summary
            rec_emoji = "✅" if "BET" in str(analysis.recommendation).upper() else "⚠️"
            summary += f"{i}. {rec_emoji} <b>{analysis.team_strong}</b> vs {analysis.team_weak}\n"
            summary += f"   ROI: {analysis.arb_roi:.2%} | Hole: {analysis.hole_probability:.1%}\n\n"
        
        if len(analyses) > 5:
            summary += f"<i>...and {len(analyses) - 5} more opportunities</i>\n"
        
        summary += "\nUse the GUI app for full details and to place bets."
        
        return summary.strip()
    
    async def send_opportunity(
        self,
        analysis: 'MatchAnalysis',
        user_ids: Optional[List[int]] = None
    ) -> int:
        """Send an opportunity notification to users.
        
        Args:
            analysis: MatchAnalysis to send
            user_ids: Specific user IDs to notify, or None for all enabled users
            
        Returns:
            Number of messages successfully sent
        """
        if not self.bot.enabled or not self.bot.db_manager:
            return 0
        
        message = self.format_opportunity(analysis)
        
        if user_ids:
            users = [{'user_id': uid, 'chat_id': uid} for uid in user_ids]
        else:
            users = self.bot.db_manager.get_telegram_users(enabled_only=True)
        
        sent_count = 0
        
        for user in users:
            # Apply user filters
            if not self._passes_user_filters(user, analysis):
                continue
            
            # Rate limiting
            if not self._check_rate_limit(user['user_id']):
                continue
            
            if await self.bot.send_message(user['chat_id'], message):
                sent_count += 1
                self._last_sent[user['user_id']] = datetime.now()
            
            await asyncio.sleep(0.05)  # Global rate limit
        
        logger.info(f"Sent opportunity notification to {sent_count} users")
        return sent_count
    
    async def send_batch_opportunities(
        self,
        analyses: List['MatchAnalysis']
    ) -> int:
        """Send a batch summary of opportunities.
        
        Args:
            analyses: List of MatchAnalysis objects
            
        Returns:
            Number of messages sent
        """
        if not self.bot.enabled or not analyses:
            return 0
        
        # Sort by ROI
        sorted_analyses = sorted(
            analyses,
            key=lambda a: a.arb_roi,
            reverse=True
        )
        
        message = self.format_batch_summary(sorted_analyses)
        
        # Broadcast to all enabled users
        return await self.bot.broadcast(message)
    
    def _passes_user_filters(
        self,
        user: Dict[str, Any],
        analysis: 'MatchAnalysis'
    ) -> bool:
        """Check if an opportunity passes user's filters.
        
        Args:
            user: User data dict with filter preferences
            analysis: MatchAnalysis to check
            
        Returns:
            True if passes all filters
        """
        # Min ROI filter
        min_roi = user.get('min_roi', 2.0) / 100
        if analysis.arb_roi < min_roi:
            return False
        
        # Max hole risk filter
        max_hole_risk = user.get('max_hole_risk', 10.0) / 100
        if analysis.hole_probability > max_hole_risk:
            return False
        
        # Confidence level filter - NEW: include caution level by default
        # include_caution: True = show BET + CAUTION, False = show only BET
        include_caution = user.get('include_caution', True)  # Default: include caution
        
        rec = str(analysis.recommendation).upper().split(".")[-1]
        
        if rec == "SKIP":
            return False  # Never send SKIP recommendations
        
        if rec == "CAUTION" and not include_caution:
            return False  # Filter out CAUTION if user disabled
        
        # League filter (if applicable)
        leagues = user.get('leagues', 'ALL')
        if leagues != 'ALL':
            # This would need actual league info from the analysis
            # For now, we'll pass all
            pass
        
        return True
    
    def _check_rate_limit(self, user_id: int) -> bool:
        """Check if user is within rate limit.
        
        Args:
            user_id: User ID to check
            
        Returns:
            True if can send (not rate limited)
        """
        if user_id not in self._last_sent:
            return True
        
        elapsed = (datetime.now() - self._last_sent[user_id]).total_seconds()
        return elapsed >= self._rate_limit_seconds
    
    def queue_for_batch(self, analysis: 'MatchAnalysis') -> None:
        """Add an opportunity to the batch queue.
        
        Args:
            analysis: MatchAnalysis to queue
        """
        self._batch_queue.append({
            'analysis': analysis,
            'timestamp': datetime.now()
        })
    
    async def flush_batch_queue(self) -> int:
        """Send all queued opportunities as a batch.
        
        Returns:
            Number of messages sent
        """
        if not self._batch_queue:
            return 0
        
        analyses = [item['analysis'] for item in self._batch_queue]
        self._batch_queue = []
        
        return await self.send_batch_opportunities(analyses)
