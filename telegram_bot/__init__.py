"""Telegram Bot Module for Eden MVP.

Provides real-time notifications for arbitrage opportunities.
"""

from telegram_bot.bot import TelegramBot
from telegram_bot.handlers import BotHandlers
from telegram_bot.notifications import NotificationSender
from telegram_bot.filters import UserFilters

__all__ = ['TelegramBot', 'BotHandlers', 'NotificationSender', 'UserFilters']
