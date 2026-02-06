"""
Shared helper functions for MCP tools.

This module provides common functionality used across all tools,
particularly the ADT client access and error handling.
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.abap_adt_client.adt_client import AdtClient
from src.utils.context import get_adt_client, set_adt_client
from src.utils.logger import logger
from src.utils.constants import ERROR_NO_CLIENT, ERROR_MISSING_CREDENTIALS

# Re-export for convenience
__all__ = [
    "get_adt_client_safe",
    "AdtClient",
    "logger",
    "ERROR_NO_CLIENT",
    "ERROR_MISSING_CREDENTIALS",
]


def get_adt_client_safe() -> AdtClient:
    """
    Get ADT client from async context (ContextVar).
    Client is created by middleware and stored in context for the request.

    Returns:
        AdtClient instance ready to use

    Raises:
        Exception: If no client is available (missing credentials in headers)
    """
    client = get_adt_client()
    if client is not None:
        return client

    raise Exception(ERROR_NO_CLIENT)
