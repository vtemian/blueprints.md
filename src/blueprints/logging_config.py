"""Logging configuration for blueprints.md."""

import logging
import sys
from typing import Optional


class ColorFormatter(logging.Formatter):
    """Colorized log formatter for better visual output."""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # Add color to level name
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Set up logging configuration.
    
    Args:
        verbose: Enable verbose (DEBUG) logging
        
    Returns:
        Configured logger instance
    """
    # Get root logger
    logger = logging.getLogger('blueprints')
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Set level based on verbosity
    level = logging.DEBUG if verbose else logging.INFO
    logger.setLevel(level)
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    # Create formatter
    if sys.stdout.isatty():  # Color output only for terminals
        formatter = ColorFormatter(
            '%(levelname)s: %(message)s'
        )
    else:
        formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Don't propagate to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance.
    
    Args:
        name: Logger name (defaults to 'blueprints')
        
    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f'blueprints.{name}')
    return logging.getLogger('blueprints')