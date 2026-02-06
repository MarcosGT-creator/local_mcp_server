"""
Async context management for request-scoped data.

Uses ContextVar for async-safe storage of ADT client across middleware and tools.
This module is imported by both server.py and tools.py to ensure they share
the same ContextVar instance.
"""

from contextvars import ContextVar
from typing import Any, Optional

# Request context - stores current request's ADT client using ContextVar
# ContextVar is async-safe (works with FastMCP 3.0's async middleware)
_adt_client_var: ContextVar[Optional[Any]] = ContextVar('adt_client', default=None)


def get_adt_client() -> Optional[Any]:
    """
    Get ADT client from async context.
    
    Returns:
        AdtClient instance or None if not set
    """
    return _adt_client_var.get()


def set_adt_client(client: Any) -> None:
    """
    Set ADT client in async context.
    
    Args:
        client: AdtClient instance to store
    """
    _adt_client_var.set(client)


def clear_adt_client() -> None:
    """Clear ADT client from context."""
    _adt_client_var.set(None)
