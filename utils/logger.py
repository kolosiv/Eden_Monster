"""Logger Module for Eden MVP.

Configures logging to file and console with structured formatting.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from logging.handlers import RotatingFileHandler


# Global logger instances
_loggers = {}
_initialized = False
_log_dir = Path("logs")


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output."""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        """Format log record with colors."""
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        record.levelname = f"{color}{record.levelname}{reset}"
        return super().format(record)


def setup_logger(
    name: str = "eden",
    level: str = "INFO",
    log_dir: str = "logs",
    max_file_size_mb: int = 10,
    backup_count: int = 5,
    console_output: bool = True
) -> logging.Logger:
    """Setup and configure logger.
    
    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_dir: Directory for log files
        max_file_size_mb: Maximum log file size in MB
        backup_count: Number of backup files to keep
        console_output: Whether to output to console
        
    Returns:
        Configured logger instance
    """
    global _initialized, _log_dir
    
    # Create log directory
    _log_dir = Path(log_dir)
    _log_dir.mkdir(parents=True, exist_ok=True)
    
    # Get or create logger
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Set level
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # Format string
    file_format = "%(asctime)s | %(name)s | %(levelname)s | %(module)s:%(lineno)d | %(message)s"
    console_format = "%(asctime)s | %(levelname)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # File handler with rotation
    log_file = _log_dir / f"{name}.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_file_size_mb * 1024 * 1024,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(file_format, date_format))
    logger.addHandler(file_handler)
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(ColoredFormatter(console_format, date_format))
        logger.addHandler(console_handler)
    
    _initialized = True
    _loggers[name] = logger
    
    return logger


def get_logger(name: str = "eden") -> logging.Logger:
    """Get a logger instance.
    
    If not initialized, creates a basic logger.
    
    Args:
        name: Logger name (use __name__ for module loggers)
        
    Returns:
        Logger instance
    """
    # For module loggers, prefix with eden
    if name.startswith("__"):
        name = "eden"
    elif not name.startswith("eden"):
        name = f"eden.{name}"
    
    if name in _loggers:
        return _loggers[name]
    
    # Create child logger if parent exists
    parent_name = "eden"
    if parent_name in _loggers:
        logger = logging.getLogger(name)
        _loggers[name] = logger
        return logger
    
    # Initialize root logger if needed
    if not _initialized:
        setup_logger()
    
    logger = logging.getLogger(name)
    _loggers[name] = logger
    return logger


def set_log_level(level: str) -> None:
    """Set log level for all loggers.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    for logger in _loggers.values():
        logger.setLevel(log_level)
        for handler in logger.handlers:
            handler.setLevel(log_level)


def get_log_file_path() -> Path:
    """Get path to current log file.
    
    Returns:
        Path to log file
    """
    return _log_dir / "eden.log"


def clear_logs() -> None:
    """Clear all log files."""
    for log_file in _log_dir.glob("*.log*"):
        try:
            log_file.unlink()
        except OSError:
            pass
