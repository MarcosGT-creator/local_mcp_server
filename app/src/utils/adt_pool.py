"""
Thread-safe connection pool for ADT clients.
"""

import hashlib
import threading
import time
from typing import Dict, Optional

from src.abap_adt_client.adt_client import AdtClient
from .logger import logger


class AdtClientPool:
    """
    Thread-safe connection pool for ADT clients.

    - Uses SHA-256 hash of hostname:client:username as pool key
    - Automatic cleanup of stale connections on each get_or_create call
    - LRU eviction when at max capacity
    """

    def __init__(self, max_idle_time: int = 1800, max_pool_size: int = 50):
        """
        Initialize the connection pool.

        Args:
            max_idle_time: Maximum idle time in seconds before connection is removed (default: 30 min)
            max_pool_size: Maximum number of connections in the pool (default: 50)
        """
        self._pool: Dict[str, tuple[AdtClient, float]] = {}  # key -> (client, last_access_time)
        self._lock = threading.Lock()
        self._max_idle_time = max_idle_time
        self._max_pool_size = max_pool_size

    def _make_key(self, hostname: str, client: str, username: str) -> str:
        """Generate a unique key for the connection pool."""
        raw = f"{hostname}:{client}:{username}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _cleanup_stale(self) -> None:
        """Remove connections that have been idle for too long."""
        now = time.time()
        stale_keys = [
            key for key, (_, last_access) in self._pool.items()
            if now - last_access > self._max_idle_time
        ]
        for key in stale_keys:
            logger.info(f"Removing stale connection from pool", extra_fields={"key": key[:16]})
            del self._pool[key]

    def _evict_lru(self) -> None:
        """Evict the least recently used connection if at capacity."""
        if len(self._pool) >= self._max_pool_size:
            lru_key = min(self._pool.keys(), key=lambda k: self._pool[k][1])
            logger.info(f"Evicting LRU connection from pool", extra_fields={"key": lru_key[:16]})
            del self._pool[lru_key]

    def get_or_create(
        self,
        hostname: str,
        client: str,
        username: str,
        password: str,
    ) -> AdtClient:
        """
        Get an existing connection from the pool or create a new one.

        Args:
            hostname: SAP system URL
            client: SAP client number
            username: SAP username
            password: SAP password

        Returns:
            AdtClient instance ready to use
        """
        key = self._make_key(hostname, client, username)

        with self._lock:
            # Cleanup stale connections
            self._cleanup_stale()

            # Check if connection exists
            if key in self._pool:
                adt_client, _ = self._pool[key]
                self._pool[key] = (adt_client, time.time())  # Update last access time
                logger.debug(f"Reusing connection from pool", extra_fields={"key": key[:16]})
                return adt_client

            # Evict LRU if at capacity
            self._evict_lru()

            # Create new connection and login to get CSRF token
            logger.info(
                "Creating new ADT connection",
                extra_fields={"hostname": hostname, "client": client, "username": username}
            )
            adt_client = AdtClient(
                sap_host=hostname,
                username=username,
                password=password,
                client=client,
            )
            adt_client.login()

            # Store in pool
            self._pool[key] = (adt_client, time.time())

            return adt_client

    def get_stats(self) -> Dict:
        """Get pool statistics for monitoring."""
        with self._lock:
            now = time.time()
            connections = []
            for key, (client, last_access) in self._pool.items():
                connections.append({
                    "key": key[:16] + "...",  # Truncate for security
                    "idle_seconds": int(now - last_access),
                })

            return {
                "active_connections": len(self._pool),
                "max_pool_size": self._max_pool_size,
                "max_idle_time": self._max_idle_time,
                "connections": connections,
            }

    def remove(self, hostname: str, client: str, username: str) -> bool:
        """
        Remove a specific connection from the pool.

        Returns:
            True if connection was found and removed, False otherwise
        """
        key = self._make_key(hostname, client, username)
        with self._lock:
            if key in self._pool:
                del self._pool[key]
                return True
            return False

    def clear(self) -> int:
        """
        Remove all connections from the pool.

        Returns:
            Number of connections that were removed
        """
        with self._lock:
            count = len(self._pool)
            self._pool.clear()
            return count
