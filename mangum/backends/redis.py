from dataclasses import dataclass

import redis

from mangum.backends.base import WebSocketBackend


@dataclass
class RedisBackend(WebSocketBackend):
    def __post_init__(self) -> None:
        self.connection = redis.Redis.from_url(self.dsn)

    def create(self, connection_id: str, *, initial_scope_json: str) -> None:
        self.connection.set(connection_id, initial_scope_json)

    def update(self, connection_id: str, *, updated_scope_json: str) -> None:
        self.connection.set(connection_id, updated_scope_json)

    def retrieve(self, connection_id: str) -> str:
        scope_json = self.connection.get(connection_id)

        return scope_json

    def delete(self, connection_id: str) -> None:
        self.connection.delete(connection_id)

    def subscribe(self, channel: str, *, connection_id: str) -> None:
        self.connection.sadd(channel, connection_id)

    def unsubscribe(self, channel: str, *, connection_id: str) -> None:
        self.connection.srem(channel, connection_id)

    def get_subscribers(self, channel: str) -> set:
        subscribers = self.connection.smembers(channel)

        return subscribers
