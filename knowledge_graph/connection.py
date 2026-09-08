"""Neo4j connection management for Knowledge Graph layer.

Provides safe, thread-safe, and context-managed driver sessions, connectivity
checks, and error handling without credential leakage.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional, Sequence
from contextlib import contextmanager

try:
    import neo4j
    from neo4j import GraphDatabase, Driver, Session, Record
    from neo4j.exceptions import (
        AuthError,
        DriverError,
        Neo4jError,
        ServiceUnavailable,
    )
    NEO4J_INSTALLED = True
except ImportError:
    neo4j = None  # type: ignore
    GraphDatabase = None  # type: ignore
    Driver = Any  # type: ignore
    Session = Any  # type: ignore
    Record = Any  # type: ignore
    NEO4J_INSTALLED = False

from knowledge_graph.config import KnowledgeGraphConfig, default_config

logger = logging.getLogger("knowledge_graph.connection")


class KnowledgeGraphConnectionError(Exception):
    """Raised when connecting or communicating with the Knowledge Graph fails."""
    pass


class Neo4jConnection:
    """Manages the Neo4j Python driver and provides safe query execution."""

    def __init__(self, config: Optional[KnowledgeGraphConfig] = None) -> None:
        if not NEO4J_INSTALLED:
            raise KnowledgeGraphConnectionError(
                "The 'neo4j' Python driver is not installed. Run: pip install neo4j"
            )
        self.config = config or default_config
        self._driver: Optional[Driver] = None

    @property
    def driver(self) -> Driver:
        """Lazily initialize and return the Neo4j driver."""
        if self._driver is None:
            auth = None
            if self.config.username:
                auth = (self.config.username, self.config.password)
            try:
                self._driver = GraphDatabase.driver(
                    self.config.uri,
                    auth=auth,
                    max_connection_lifetime=3600,
                )
            except Exception as e:
                # Mask credentials in logs/exceptions
                safe_info = self.config.to_safe_dict()
                raise KnowledgeGraphConnectionError(
                    f"Failed to initialize Neo4j driver for {safe_info['uri']}: {type(e).__name__}: {str(e)}"
                ) from e
        return self._driver

    def ping(self, timeout_seconds: float = 3.0) -> bool:
        """Safely test connection to Neo4j. Returns True if alive, False otherwise."""
        if not NEO4J_INSTALLED:
            return False
        try:
            drv = self.driver
            drv.verify_connectivity()
            return True
        except Exception as e:
            logger.debug("Neo4j ping check failed: %s: %s", type(e).__name__, str(e))
            return False

    @contextmanager
    def session(self, database: Optional[str] = None):
        """Context manager yielding a Neo4j session."""
        db = database or self.config.database
        sess: Optional[Session] = None
        try:
            sess = self.driver.session(database=db)
            yield sess
        except (ServiceUnavailable, AuthError, Neo4jError) as exc:
            raise KnowledgeGraphConnectionError(
                f"Neo4j session error ({type(exc).__name__}): {str(exc)}"
            ) from exc
        finally:
            if sess is not None:
                sess.close()

    def execute_query(
        self,
        query: str,
        parameters: Optional[dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Execute a parameterized Cypher read or write query and return results as dicts."""
        params = parameters or {}
        with self.session(database=database) as sess:
            result = sess.run(query, parameters=params)
            records = [record.data() for record in result]
            return records

    def execute_write(
        self,
        transaction_func: Callable[..., Any],
        *args: Any,
        database: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Execute a function inside a managed write transaction."""
        with self.session(database=database) as sess:
            return sess.execute_write(transaction_func, *args, **kwargs)

    def execute_read(
        self,
        transaction_func: Callable[..., Any],
        *args: Any,
        database: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Execute a function inside a managed read transaction."""
        with self.session(database=database) as sess:
            return sess.execute_read(transaction_func, *args, **kwargs)

    def close(self) -> None:
        """Close driver connections."""
        if self._driver is not None:
            try:
                self._driver.close()
            except Exception:
                pass
            self._driver = None

    def __enter__(self) -> "Neo4jConnection":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

