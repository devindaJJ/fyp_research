"""
Logging configuration for Urban Traffic System
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import colorama

# Initialize colorama for colored output on Windows
colorama.init()

# Custom log colors
LOG_COLORS = {
    'DEBUG': colorama.Fore.CYAN,
    'INFO': colorama.Fore.GREEN,
    'WARNING': colorama.Fore.YELLOW,
    'ERROR': colorama.Fore.RED,
    'CRITICAL': colorama.Fore.RED + colorama.Style.BRIGHT,
}

# Reset color
RESET_COLOR = colorama.Style.RESET_ALL


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors."""
    
    def format(self, record):
        # Add color based on log level
        level_color = LOG_COLORS.get(record.levelname, colorama.Fore.WHITE)
        
        # Create formatted message
        if hasattr(self, '_style'):
            # Python 3.2+
            message = super().format(record)
        else:
            # Older Python
            message = logging.Formatter.format(self, record)
        
        # Add color to level name
        colored_level = f"{level_color}{record.levelname}{RESET_COLOR}"
        message = message.replace(record.levelname, colored_level, 1)
        
        return message


def setup_logger(
    name: str = "UrbanTrafficSystem",
    level: str = "INFO",
    log_file: Optional[str] = None,
    console_output: bool = True
) -> logging.Logger:
    """
    Setup and configure logger.
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        console_output: Enable console output
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Set level
    logger.setLevel(getattr(logging, level.upper()))
    
    # Create formatters
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        # Create directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: str = "UrbanTrafficSystem") -> logging.Logger:
    """
    Get logger instance by name.
    
    Args:
        name: Logger name
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class ProgressLogger:
    """Logger for progress tracking."""
    
    def __init__(self, total_steps: int, description: str = "Processing"):
        self.total_steps = total_steps
        self.current_step = 0
        self.description = description
        self.start_time = datetime.now()
        self.logger = get_logger("Progress")
    
    def update(self, step: int = 1, message: str = ""):
        """Update progress."""
        self.current_step += step
        percentage = (self.current_step / self.total_steps) * 100
        
        elapsed = datetime.now() - self.start_time
        if self.current_step > 0:
            estimated_total = elapsed * (self.total_steps / self.current_step)
            remaining = estimated_total - elapsed
            remaining_str = f"{remaining.seconds // 60}:{remaining.seconds % 60:02d}"
        else:
            remaining_str = "?"
        
        log_msg = f"{self.description}: {percentage:.1f}% ({self.current_step}/{self.total_steps})"
        if message:
            log_msg += f" - {message}"
        log_msg += f" - Remaining: {remaining_str}"
        
        self.logger.info(log_msg)
    
    def complete(self, message: str = "Completed"):
        """Mark progress as complete."""
        elapsed = datetime.now() - self.start_time
        elapsed_str = f"{elapsed.seconds // 60}:{elapsed.seconds % 60:02d}"
        
        self.logger.info(f"{self.description}: {message} in {elapsed_str}")