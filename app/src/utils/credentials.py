"""
SAP credentials dataclass for extracting authentication from HTTP headers
or environment variables.
"""

import os
from dataclasses import dataclass
from typing import Dict, Optional

from .constants import (
    HEADER_HOSTNAME,
    HEADER_USERNAME,
    HEADER_PASSWORD,
    HEADER_CLIENT,
    DEFAULT_SAP_CLIENT,
    ENV_SAP_HOSTNAME,
    ENV_SAP_USERNAME,
    ENV_SAP_PASSWORD,
    ENV_SAP_CLIENT,
)


@dataclass
class SAPCredentials:
    """SAP connection credentials extracted from HTTP headers or env vars."""

    hostname: str
    username: str
    password: str
    client: str = DEFAULT_SAP_CLIENT

    @classmethod
    def from_headers(cls, headers: Dict[str, str]) -> Optional["SAPCredentials"]:
        """
        Extract SAP credentials from HTTP headers.

        Returns:
            SAPCredentials instance if all required headers are present, None otherwise
        """
        if not headers:
            return None

        hostname = headers.get(HEADER_HOSTNAME)
        username = headers.get(HEADER_USERNAME)
        password = headers.get(HEADER_PASSWORD)
        client = headers.get(HEADER_CLIENT, DEFAULT_SAP_CLIENT)

        if not hostname or not username or not password:
            return None

        return cls(
            hostname=hostname,
            username=username,
            password=password,
            client=client,
        )

    @classmethod
    def from_env(cls) -> Optional["SAPCredentials"]:
        """
        Extract SAP credentials from environment variables.

        Returns:
            SAPCredentials instance if all required env vars are set, None otherwise
        """
        hostname = os.environ.get(ENV_SAP_HOSTNAME)
        username = os.environ.get(ENV_SAP_USERNAME)
        password = os.environ.get(ENV_SAP_PASSWORD)
        client = os.environ.get(ENV_SAP_CLIENT, DEFAULT_SAP_CLIENT)

        if not hostname or not username or not password:
            return None

        return cls(
            hostname=hostname,
            username=username,
            password=password,
            client=client,
        )
