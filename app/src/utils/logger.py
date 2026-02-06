"""
MCP-style structured logger - generic and reusable.
Clean and simple - outputs logs in the same format as FastMCP's StructuredLoggingMiddleware.
"""

import logging
import sys
import json
from typing import Dict, Any, Optional


class SafeJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles non-serializable objects gracefully."""
    
    def default(self, obj: Any) -> Any:
        # Handle Pydantic FieldInfo objects
        if hasattr(obj, '__class__') and obj.__class__.__name__ == 'FieldInfo':
            return f"<FieldInfo: {getattr(obj, 'default', '...')}>"
        # Handle other Pydantic objects
        if hasattr(obj, 'model_dump'):
            return obj.model_dump()
        if hasattr(obj, 'dict'):
            return obj.dict()
        # Fallback to string representation
        try:
            return str(obj)
        except Exception:
            return f"<{obj.__class__.__name__}>"


# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for terminal output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    
    # Log level colors (matching Rich/MCP style)
    DEBUG = "\033[36m"      # Cyan
    INFO = "\033[34m"       # Blue
    WARNING = "\033[33m"    # Yellow
    ERROR = "\033[31m"      # Red
    CRITICAL = "\033[35m"   # Magenta
    
    # JSON content colors (matching MCP style)
    KEY = "\033[36m"            # Cyan for JSON keys/labels
    STRING = "\033[32m"         # Green for text strings
    NUMBER = "\033[1;34m"       # Bold blue for numbers
    BOOLEAN = "\033[35m"        # Magenta for true/false
    NULL = "\033[90m"           # Gray for null


class MCPStyleFormatter(logging.Formatter):
    """MCP-style JSON formatter with colors - simple and clean like FastMCP with timestamp prefix."""
    
    # Map log levels to colors
    LEVEL_COLORS = {
        'DEBUG': Colors.DEBUG,
        'INFO': Colors.INFO,
        'WARNING': Colors.WARNING,
        'ERROR': Colors.ERROR,
        'CRITICAL': Colors.CRITICAL,
    }
    
    def __init__(self, use_colors: bool = True):
        super().__init__(datefmt='%m/%d/%y %H:%M:%S')
        self.use_colors = use_colors and sys.stdout.isatty()  # Only use colors if outputting to terminal
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record in MCP style: [MM/DD/YY HH:MM:SS] LEVEL {"key": "value"}"""
        
        # Create timestamp prefix like MCP: [10/29/25 11:33:16]
        timestamp = self.formatTime(record, self.datefmt)
        
        # Build log entry in MCP style
        log_entry = {}
        
        # Add message (or it might be in extra_fields as 'event')
        if 'event' not in log_entry:
            log_entry['message'] = record.getMessage()
                    
        # Check if extra_fields exists (for structured logging)
        if hasattr(record, 'extra_fields') and getattr(record, 'extra_fields'):
            log_entry.update(getattr(record, 'extra_fields'))
        
        # Add error if present
        if record.exc_info:
            log_entry["error"] = str(record.exc_info[1]) if record.exc_info[1] else None
        
        # Get color for this log level (no bold)
        level_name = record.levelname
        if self.use_colors:
            color = self.LEVEL_COLORS.get(level_name, '')
            level_colored = f"{color}{level_name:<8}{Colors.RESET}"
        else:
            level_colored = f"{level_name:<8}"
        
        # Format JSON with colors
        if self.use_colors:
            json_output = self._colorize_json(log_entry)
        else:
            json_output = json.dumps(log_entry, ensure_ascii=False, cls=SafeJSONEncoder)
        
        # Format: [MM/DD/YY HH:MM:SS] LEVEL     {"json": "here"}
        return f"[{timestamp}] {level_colored} {json_output}"
    
    def _colorize_json(self, obj: Any) -> str:
        """Colorize JSON output like MCP: cyan for keys, green for strings, bold blue for numbers."""
        import re
        
        # First, convert to JSON string
        json_str = json.dumps(obj, ensure_ascii=False, cls=SafeJSONEncoder)
        
        # We need to process this carefully to avoid conflicts
        # Strategy: Use markers to protect already-colored parts
        
        # 1. Color booleans first (they don't have quotes)
        json_str = re.sub(
            r':\s*(true|false)\b',
            rf': {Colors.BOOLEAN}\1{Colors.RESET}',
            json_str
        )
        
        # 2. Color null (no quotes)
        json_str = re.sub(
            r':\s*(null)\b',
            rf': {Colors.NULL}\1{Colors.RESET}',
            json_str
        )
        
        # 3. Color numbers (no quotes, not already colored)
        json_str = re.sub(
            r':\s*(-?\d+\.?\d*)\b',
            rf': {Colors.NUMBER}\1{Colors.RESET}',
            json_str
        )
        
        # 4. Color string values (comes after ":")
        json_str = re.sub(
            r':\s*"([^"]*)"',
            rf': {Colors.STRING}"\1"{Colors.RESET}',
            json_str
        )
        
        # 5. Finally, color the keys (comes before ":")
        json_str = re.sub(
            r'"([^"]+)"\s*:',
            rf'{Colors.KEY}"\1"{Colors.RESET}:',
            json_str
        )
        
        return json_str


class StructuredLogger:
    """MCP-style structured logger - generic and reusable."""
    
    def __init__(
        self, 
        name: str = "custom-logger",
        level: str = "INFO",
        enable_json: bool = True
    ):
        self.name = name
        self.enable_json = enable_json
        self.logger = self._setup_logger(level)
    
    def _setup_logger(self, level: str) -> logging.Logger:
        """Setup the logger with appropriate formatting."""
        logger = logging.getLogger(self.name)
        
        # Set log level
        log_level = getattr(logging, level.upper(), logging.INFO)
        logger.setLevel(log_level)
        
        # Clear existing handlers
        if logger.hasHandlers():
            logger.handlers.clear()
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        
        # Use MCP-style formatter by default
        if self.enable_json:
            formatter = MCPStyleFormatter()
        else:
            # Human-readable format for development
            formatter = logging.Formatter(
                fmt='[%(levelname)s] %(asctime)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.propagate = False
        
        return logger
    
    def _log_with_context(
        self, 
        level: str = "INFO", 
        message: Optional[str] = None, 
        extra_fields: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs
    ):
        """Internal method to log with additional context."""
        extra = {}
        
        if extra_fields:
            extra['extra_fields'] = extra_fields
        if correlation_id:
            extra['correlation_id'] = correlation_id
        if request_id:
            extra['request_id'] = request_id
        if user_id:
            extra['user_id'] = user_id
            
        # Add any additional kwargs as extra fields
        if kwargs:
            extra.setdefault('extra_fields', {}).update(kwargs)
        
        getattr(self.logger, level.lower())(message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with context."""
        self._log_with_context("DEBUG", message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message with context."""
        self._log_with_context("INFO", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with context."""
        self._log_with_context("WARNING", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with context."""
        self._log_with_context("ERROR", message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with context."""
        self._log_with_context("CRITICAL", message, **kwargs)


def setup_logger(
    name: str = "custom-logger", 
    level: str = "INFO",
    enable_json: bool = True
) -> StructuredLogger:
    """
    Setup MCP-style structured logger - generic and reusable.
    
    Args:
        name: Logger name (default: "custom-logger")
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_json: Use MCP-style JSON format (default: True)
    
    Returns:
        Configured StructuredLogger instance
    
    Usage:
        # Simple message
        logger.info("Operation completed successfully")
        # Output: [10/29/25 11:38:41] INFO     {"message": "Operation completed successfully"}
        
        # Event with extra fields
        logger.info("Tool executed", extra_fields={
            "event": "tool_execution",
            "tool_name": "search_object",
            "duration_ms": 297.99
        })
        # Output: [10/29/25 11:38:41] INFO     {"event": "tool_execution", "tool_name": "search_object", "duration_ms": 297.99}
    """
    return StructuredLogger(name=name, level=level, enable_json=enable_json)


# Create default logger instance with MCP-style formatting
logger = setup_logger()
