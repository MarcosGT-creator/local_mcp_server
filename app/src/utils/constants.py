"""
Application-wide constants and configuration values.
"""

# Server Configuration
SERVER_NAME = "SAP-MCP-Server"
SERVER_VERSION = "1.0.0"
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8001
SERVER_PATH = "/mcp/"

# Connection Pool Configuration
DEFAULT_MAX_IDLE_TIME = 1800  # 30 minutes in seconds
DEFAULT_MAX_POOL_SIZE = 50

# SAP Client Configuration
DEFAULT_SAP_CLIENT = "110"
SUPPORTED_SAP_CLIENTS = ["110", "120", "300"]

# HTTP Headers
HEADER_HOSTNAME = "x-hostname"
HEADER_USERNAME = "x-username"
HEADER_PASSWORD = "x-password"
HEADER_CLIENT = "x-client"

# Error Messages
ERROR_NO_CLIENT = f"""No ADT client available. Ensure SAP credentials are provided in headers:
  x-hostname: <sap-system-url>
  x-username: <username>
  x-password: <password>
  x-client: <client-number>

Or use the 'connect_to_sap' tool to establish a connection without headers.
"""

ERROR_MISSING_CREDENTIALS = "Error: username and password are required for SAP connection."
