"""
SAP connection management tool.

Provides an alternative way to connect to SAP when HTTP headers
are not available or when credentials need to be passed explicitly.
"""

from fastmcp.tools import tool as _tool
from typing import Callable, Any
tool: Callable[..., Any] = _tool  # type: ignore[assignment]

from ._helpers import AdtClient, logger, set_adt_client, ERROR_MISSING_CREDENTIALS
from src.utils.context import set_adt_client
from src.utils.constants import DEFAULT_SAP_CLIENT


@tool
def connect_to_sap(
    hostname: str,
    username: str,
    password: str,
    client: str = DEFAULT_SAP_CLIENT,
) -> str:
    """
    Establish a connection to SAP system.

    Use this tool when SAP credentials are not passed via HTTP headers.
    After calling this tool, other SAP tools will use this connection.

    Args:
        hostname: SAP system URL (e.g., https://sap-dev.company.com:8000)
        username: SAP username
        password: SAP password
        client: SAP client number (default: 110)

    Returns:
        Success message with connection details
    """
    if not username or not password:
        return ERROR_MISSING_CREDENTIALS

    try:
        # Create ADT client and login to get CSRF token
        adt_client = AdtClient(
            sap_host=hostname,
            username=username,
            password=password,
            client=client,
        )
        adt_client.login()

        # Store in context for other tools to use
        set_adt_client(adt_client)

        logger.info(
            "SAP connection established via connect_to_sap tool",
            extra_fields={
                "hostname": hostname,
                "client": client,
                "username": username,
            }
        )

        return f"Successfully connected to SAP system at {hostname} (client {client}) as {username}"

    except Exception as e:
        logger.error(
            "Failed to connect to SAP",
            extra_fields={"error": str(e), "hostname": hostname}
        )
        return f"Error connecting to SAP: {str(e)}"
