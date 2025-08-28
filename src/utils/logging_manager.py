"""
Unified logging manager for the weather data downloader.

This module provides a centralized logging system that combines:
- Structured logging to files
- Colored console output
- Consistent color conventions
- Log levels and formatting
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme


class LoggingManager:
    """
    Centralized logging manager with colored console output.
    
    Provides consistent color conventions and structured logging
    for both console and file output.
    """
    
    # Color theme for different log levels
    COLORS = {
        'DEBUG': 'dim',      # Gray - for detailed debugging
        'INFO': 'blue',      # Blue - for general information
        'SUCCESS': 'green',  # Green - for successful operations
        'WARNING': 'yellow', # Yellow - for warnings
        'ERROR': 'red',      # Red - for errors
        'CRITICAL': 'red'    # Red - for critical errors
    }
    
    def __init__(self, 
                 log_file: Optional[Path] = None,
                 console_level: str = 'INFO',
                 file_level: str = 'DEBUG',
                 enable_rich: bool = True):
        """
        Initialize logging manager.
        
        Args:
            log_file: Path to log file (optional)
            console_level: Minimum log level for console output
            file_level: Minimum log level for file output
            enable_rich: Whether to use Rich formatting
        """
        self.log_file = log_file
        self.console_level = console_level
        self.file_level = file_level
        self.enable_rich = enable_rich
        
        # Initialize Rich console
        self.console = Console(theme=self._create_theme())
        
        # Setup logging
        self._setup_logging()
    
    def _create_theme(self) -> Theme:
        """Create Rich theme with consistent colors."""
        return Theme({
            "info": "blue",
            "success": "green", 
            "warning": "yellow",
            "error": "red",
            "critical": "red",
            "debug": "dim"
        })
    
    def _setup_logging(self):
        """Setup logging configuration."""
        # Create logger
        self.logger = logging.getLogger('weather_downloader')
        self.logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Console handler with Rich formatting
        if self.enable_rich:
            console_handler = RichHandler(
                console=self.console,
                show_time=True,
                show_path=False,
                markup=True
            )
        else:
            console_handler = logging.StreamHandler(sys.stdout)
        
        console_handler.setLevel(getattr(logging, self.console_level.upper()))
        self.logger.addHandler(console_handler)
        
        # File handler (if log file specified)
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(self.log_file)
            file_handler.setLevel(getattr(logging, self.file_level.upper()))
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
        
        # File handler (if log file specified)
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(self.log_file)
            file_handler.setLevel(getattr(logging, self.file_level.upper()))
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
    
    def _get_color(self, level: str) -> str:
        """Get color for log level."""
        return self.COLORS.get(level.upper(), 'white')
    
    def _log_with_color(self, level: str, message: str, **kwargs):
        """Log message with appropriate color."""
        color = self._get_color(level)
        
        # Log to file/structured logging
        if level.upper() == 'SUCCESS':
            self.logger.info(f"SUCCESS: {message}")
        else:
            getattr(self.logger, level.lower())(message)
        
        # Console output with color
        if level.upper() == 'SUCCESS':
            self.console.print(f"[{color}]{message}[/{color}]")
        else:
            # Rich handler will handle colors automatically
            pass
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(message, **kwargs)
    
    def success(self, message: str, **kwargs):
        """Log success message."""
        self._log_with_color('SUCCESS', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self.logger.error(message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self.logger.critical(message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log exception with traceback."""
        self.logger.exception(message, **kwargs)
    
    def print_table(self, *args, **kwargs):
        """Print Rich table using console."""
        self.console.print(*args, **kwargs)
    
    def print_progress(self, *args, **kwargs):
        """Print Rich progress using console."""
        self.console.print(*args, **kwargs)


# Global logging manager instance
_logging_manager: Optional[LoggingManager] = None


def get_logger() -> LoggingManager:
    """Get global logging manager instance."""
    global _logging_manager
    
    if _logging_manager is None:
        # Default configuration
        log_file = Path("logs/weather_downloader.log")
        _logging_manager = LoggingManager(
            log_file=log_file,
            console_level='INFO',
            file_level='DEBUG',
            enable_rich=True
        )
    
    return _logging_manager


def setup_logging(log_file: Optional[Path] = None, 
                 console_level: str = 'INFO',
                 file_level: str = 'DEBUG') -> LoggingManager:
    """Setup global logging configuration."""
    global _logging_manager
    
    _logging_manager = LoggingManager(
        log_file=log_file,
        console_level=console_level,
        file_level=file_level,
        enable_rich=True
    )
    
    return _logging_manager
