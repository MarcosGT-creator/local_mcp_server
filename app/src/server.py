import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Awaitable
from starlette.responses import JSONResponse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project root to path for src.* imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp import FastMCP
from fastmcp.server.providers import FileSystemProvider
import mcp.types as mt
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware.timing import DetailedTimingMiddleware

from src.utils.context import get_adt_client, set_adt_client
from src.utils.adt_pool import AdtClientPool
from src.utils.credentials import SAPCredentials
from src.utils.logger import logger
from src.utils.constants import (
    SERVER_NAME,
    SERVER_VERSION,
    DEFAULT_MAX_IDLE_TIME,
    DEFAULT_MAX_POOL_SIZE,
)

# Create GLOBAL connection pool (shared across all requests)
adt_pool = AdtClientPool(
    max_idle_time=DEFAULT_MAX_IDLE_TIME, max_pool_size=DEFAULT_MAX_POOL_SIZE
)

# Use FileSystemProvider to auto-discover @tool and @prompt decorated functions
# from the sap_mcp/tools/ and sap_mcp/prompts/ directories
tools_provider = FileSystemProvider(Path(__file__).parent / "sap_mcp" / "tools")
prompts_provider = FileSystemProvider(Path(__file__).parent / "sap_mcp" / "prompts")

mcp = FastMCP(
    name=SERVER_NAME,
    version=SERVER_VERSION,
    mask_error_details=True,
    providers=[tools_provider, prompts_provider],
    instructions="""
    This server provides ABAP Development Tools for SAP systems.
    It allows AI agents to create, modify, search, and manage SAP objects.
    """,
)


# Middleware to handle SAP credentials from HTTP headers
class SAPMiddleware(Middleware):
    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next: Callable[[MiddlewareContext[Any]], Awaitable[Any]],
    ) -> Any:

        # Extract SAP credentials: headers take priority, env vars as fallback
        headers = get_http_headers()
        credentials = SAPCredentials.from_headers(headers) or SAPCredentials.from_env()

        # If credentials available, get/create connection from pool
        if credentials:
            try:
                client = adt_pool.get_or_create(
                    hostname=credentials.hostname,
                    client=credentials.client,
                    username=credentials.username,
                    password=credentials.password,
                )
                set_adt_client(client)  # Use ContextVar (async-safe)
            except Exception as e:
                logger.error(
                    "Failed to create ADT client",
                    extra_fields={"error": str(e)}
                )
                set_adt_client(None)
        else:
            # No credentials - tools will fail with helpful error message
            set_adt_client(None)

        # Log tool execution
        tool_name = context.message.name
        
        # Always log the user from request headers (who is actually making the call)
        user = credentials.username if credentials else "anonymous"
        client_id = credentials.client if credentials else None
        
        logger.info(
            "Executing tool",
            extra_fields={
                "tool": tool_name,
                "user": user,
                "client": client_id
            }
        )

        return await call_next(context)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint for monitoring."""

    health_data = {"status": "healthy", "version": "1.0.0", "timestamp": time.time()}

    return JSONResponse(health_data)


@mcp.custom_route("/pool-stats", methods=["GET"])
async def pool_stats(request):
    """Connection pool statistics endpoint for monitoring."""

    stats = adt_pool.get_stats()
    return JSONResponse(stats)


def main():
    """Main entry point to start the MCP server."""

    # Adding Middlewares
    mcp.add_middleware(SAPMiddleware())
    mcp.add_middleware(DetailedTimingMiddleware())
    # mcp.add_middleware(StructuredLoggingMiddleware(include_payloads=False))

    try:
        # Start the MCP server
        mcp.run(
            transport="streamable-http",
            host="0.0.0.0",
            port=8001,
            path="/mcp/",
            show_banner=False,  # Explicitly disable banner
        )

    except KeyboardInterrupt:
        logger.info("Received shutdown signal...")

    except Exception as e:
        logger.error(f"Server error: {e}")


if __name__ == "__main__":
    main()
