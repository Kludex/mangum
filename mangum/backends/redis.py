from dataclasses import dataclass

import redis

from mangum.backends.base import WebSocketBackend


@dataclass
class RedisBackend(WebSocketBackend):
    def __post_init__(self) -> None:
        self.connection = redis.Redis.from_url(self.dsn)

    def create(self, connection_id: str, initial_scope: str) -> None:
        self.connection.set(connection_id, initial_scope)

    def fetch(self, connection_id: str) -> str:
        initial_scope = self.connection.get(connection_id)

        return initial_scope

    def delete(self, connection_id: str) -> None:
        self.connection.delete(connection_id)

    def add_subscriber(self, connection_id: str, *, channel: str) -> None:
        self.connection.sadd(channel, connection_id)

    def remove_subscriber(self, connection_id: str, *, channel: str) -> None:
        self.connection.srem(channel, connection_id)

    def get_subscribers(self, channel: str) -> None:
        subscribers = self.connection.smembers(channel)

        return subscribers
