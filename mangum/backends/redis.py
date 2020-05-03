import logging
from dataclasses import dataclass

import redis

from mangum.backends.base import WebSocketBackend
from mangum.exceptions import ConfigurationError


@dataclass
class RedisBackend(WebSocketBackend):
    def __post_init__(self) -> None:
        self.logger = logging.getLogger("mangum.websocket.redis")
        self.logger.debug("Connecting to Redis host.")

        if "uri" in self.params:
            self.connection = redis.Redis(self.params["uri"])
        else:
            try:
                host = self.params["host"]
            except KeyError:  # pragma: no cover
                raise ConfigurationError("PostgreSQL connection details missing.")
            password = self.params.get("password")
            port = self.params.get("port", "5432")  # pragma: no cover
            self.connection = redis.Redis(host, port, password=password)
        self.logger.debug("Connection established.")

    def create(self, connection_id: str, initial_scope: str) -> None:
        self.logger.debug("Creating entry for %s", connection_id)
        self.connection.set(connection_id, initial_scope)
        self.logger.debug("Entry created.")

    def fetch(self, connection_id: str) -> str:
        self.logger.debug("Fetching initial scope for %s", connection_id)
        initial_scope = self.connection.get(connection_id)
        self.logger.debug("Initial scope fetched.")

        return initial_scope

    def delete(self, connection_id: str) -> None:
        self.logger.debug("Deleting entry for %s", connection_id)
        self.connection.delete(connection_id)
        self.logger.debug("Entry deleted.")
