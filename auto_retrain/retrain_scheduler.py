"""Retrain Scheduler Module.

Schedules automatic retraining.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
import threading
import time

from .retrain_triggers import RetrainTriggerManager
from .retrain_manager import RetrainManager
from utils.logger import get_logger

logger = get_logger(__name__)

# Try importing APScheduler
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    logger.warning("APScheduler not installed. Run: pip install apscheduler")


@dataclass
class ScheduleConfig:
    """Configuration for retraining schedule."""
    enabled: bool = True
    weekly_enabled: bool = True
    weekly_day: str = "sunday"  # Day of week
    weekly_hour: int = 3  # Hour (24h format)
    monthly_enabled: bool = True
    monthly_day: int = 1  # Day of month
    monthly_hour: int = 4
    check_interval_minutes: int = 60  # How often to check triggers
    timezone: str = "UTC"


class RetrainScheduler:
    """Schedules automatic retraining.
    
    Supports:
    - Weekly scheduled retraining
    - Monthly full retraining
    - Trigger-based retraining (checked periodically)
    - Custom cron schedules
    
    Example:
        >>> scheduler = RetrainScheduler(trigger_manager, retrain_manager)
        >>> scheduler.start()
        >>> # Later...
        >>> scheduler.stop()
    """
    
    def __init__(
        self,
        trigger_manager: RetrainTriggerManager,
        retrain_manager: RetrainManager,
        config: Optional[ScheduleConfig] = None
    ):
        """Initialize scheduler.
        
        Args:
            trigger_manager: Trigger manager instance
            retrain_manager: Retrain manager instance
            config: Schedule configuration
        """
        self.triggers = trigger_manager
        self.retrain = retrain_manager
        self.config = config or ScheduleConfig()
        
        self.scheduler = None
        self.running = False
        self._fallback_thread = None
        self._stop_event = threading.Event()
    
    def start(self) -> bool:
        """Start the scheduler.
        
        Returns:
            True if started successfully
        """
        if self.running:
            logger.warning("Scheduler already running")
            return False
        
        if not self.config.enabled:
            logger.info("Scheduler is disabled")
            return False
        
        if APSCHEDULER_AVAILABLE:
            return self._start_apscheduler()
        else:
            return self._start_fallback_scheduler()
    
    def _start_apscheduler(self) -> bool:
        """Start using APScheduler."""
        try:
            self.scheduler = BackgroundScheduler(timezone=self.config.timezone)
            
            # Weekly retraining
            if self.config.weekly_enabled:
                day_map = {
                    'monday': 0, 'tuesday': 1, 'wednesday': 2,
                    'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6
                }
                day_of_week = day_map.get(self.config.weekly_day.lower(), 6)
                
                self.scheduler.add_job(
                    self._run_weekly_retrain,
                    CronTrigger(
                        day_of_week=day_of_week,
                        hour=self.config.weekly_hour,
                        minute=0
                    ),
                    id='weekly_retrain',
                    name='Weekly Retraining'
                )
                logger.info(
                    f"Scheduled weekly retraining: {self.config.weekly_day} "
                    f"at {self.config.weekly_hour}:00"
                )
            
            # Monthly full retraining
            if self.config.monthly_enabled:
                self.scheduler.add_job(
                    self._run_monthly_retrain,
                    CronTrigger(
                        day=self.config.monthly_day,
                        hour=self.config.monthly_hour,
                        minute=0
                    ),
                    id='monthly_retrain',
                    name='Monthly Full Retraining'
                )
                logger.info(
                    f"Scheduled monthly retraining: day {self.config.monthly_day} "
                    f"at {self.config.monthly_hour}:00"
                )
            
            # Periodic trigger check
            self.scheduler.add_job(
                self._check_triggers,
                IntervalTrigger(minutes=self.config.check_interval_minutes),
                id='trigger_check',
                name='Check Retraining Triggers'
            )
            logger.info(
                f"Scheduled trigger check every {self.config.check_interval_minutes} minutes"
            )
            
            self.scheduler.start()
            self.running = True
            
            logger.info("Retrain scheduler started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start APScheduler: {e}")
            return self._start_fallback_scheduler()
    
    def _start_fallback_scheduler(self) -> bool:
        """Start a simple fallback scheduler using threading."""
        logger.info("Using fallback scheduler")
        
        self._stop_event.clear()
        
        def run_scheduler():
            last_trigger_check = datetime.now()
            last_weekly_check = datetime.now()
            
            while not self._stop_event.is_set():
                now = datetime.now()
                
                # Check triggers periodically
                if (now - last_trigger_check).total_seconds() >= self.config.check_interval_minutes * 60:
                    self._check_triggers()
                    last_trigger_check = now
                
                # Check for weekly retrain
                if self.config.weekly_enabled:
                    day_map = {
                        'monday': 0, 'tuesday': 1, 'wednesday': 2,
                        'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6
                    }
                    target_day = day_map.get(self.config.weekly_day.lower(), 6)
                    
                    if (now.weekday() == target_day and 
                        now.hour == self.config.weekly_hour and
                        (now - last_weekly_check).total_seconds() > 3600):
                        self._run_weekly_retrain()
                        last_weekly_check = now
                
                # Sleep for a minute
                self._stop_event.wait(60)
        
        self._fallback_thread = threading.Thread(target=run_scheduler, daemon=True)
        self._fallback_thread.start()
        self.running = True
        
        return True
    
    def stop(self) -> None:
        """Stop the scheduler."""
        if not self.running:
            return
        
        if self.scheduler:
            self.scheduler.shutdown(wait=False)
            self.scheduler = None
        
        self._stop_event.set()
        if self._fallback_thread:
            self._fallback_thread.join(timeout=5)
            self._fallback_thread = None
        
        self.running = False
        logger.info("Retrain scheduler stopped")
    
    def _check_triggers(self) -> None:
        """Check if any triggers should fire."""
        logger.debug("Checking retraining triggers...")
        
        trigger = self.triggers.get_trigger_priority()
        
        if trigger:
            logger.info(f"Trigger fired: {trigger.trigger_type.value}")
            self.retrain.run_retraining(trigger, incremental=True)
    
    def _run_weekly_retrain(self) -> None:
        """Run weekly scheduled retraining."""
        logger.info("Running weekly scheduled retraining")
        
        from .retrain_triggers import TriggerEvent, TriggerType
        
        trigger = TriggerEvent(
            timestamp=datetime.now(),
            trigger_type=TriggerType.TIME,
            reason="Weekly scheduled retraining",
            current_value=7,
            threshold_value=7
        )
        
        self.retrain.run_retraining(trigger, incremental=True)
    
    def _run_monthly_retrain(self) -> None:
        """Run monthly full retraining."""
        logger.info("Running monthly full retraining")
        
        from .retrain_triggers import TriggerEvent, TriggerType
        
        trigger = TriggerEvent(
            timestamp=datetime.now(),
            trigger_type=TriggerType.TIME,
            reason="Monthly full retraining",
            current_value=30,
            threshold_value=30
        )
        
        self.retrain.run_retraining(trigger, incremental=False)
    
    def get_next_scheduled(self) -> Dict[str, Any]:
        """Get information about next scheduled jobs.
        
        Returns:
            Dict with next job information
        """
        result = {
            'running': self.running,
            'next_trigger_check': None,
            'next_weekly': None,
            'next_monthly': None
        }
        
        if not self.running:
            return result
        
        if APSCHEDULER_AVAILABLE and self.scheduler:
            jobs = self.scheduler.get_jobs()
            
            for job in jobs:
                next_run = job.next_run_time
                if next_run:
                    if job.id == 'trigger_check':
                        result['next_trigger_check'] = next_run.isoformat()
                    elif job.id == 'weekly_retrain':
                        result['next_weekly'] = next_run.isoformat()
                    elif job.id == 'monthly_retrain':
                        result['next_monthly'] = next_run.isoformat()
        else:
            # Estimate for fallback scheduler
            now = datetime.now()
            result['next_trigger_check'] = (
                now + timedelta(minutes=self.config.check_interval_minutes)
            ).isoformat()
        
        return result
    
    def update_config(self, **kwargs) -> None:
        """Update scheduler configuration.
        
        Args:
            **kwargs: Configuration values to update
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        # Restart scheduler to apply changes
        if self.running:
            self.stop()
            self.start()
    
    def trigger_immediate_retrain(self, incremental: bool = True) -> None:
        """Trigger an immediate retraining.
        
        Args:
            incremental: Use incremental training
        """
        logger.info("Triggering immediate retraining")
        
        self.triggers.request_manual_retrain()
        trigger = self.triggers.check_manual_trigger()
        
        if trigger:
            # Run in background thread
            thread = threading.Thread(
                target=self.retrain.run_retraining,
                args=(trigger, incremental),
                daemon=True
            )
            thread.start()
