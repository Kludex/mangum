from dataclasses import dataclass

import redis

from mangum.backends.base import WebSocketBackend


@dataclass
class RedisBackend(WebSocketBackend):
    def __post_init__(self) -> None:
        self.connection = redis.Redis.from_url(self.dsn)

    def save(self, connection_id: str, *, json_scope: str) -> None:
        self.connection.set(connection_id, json_scope)

    def retrieve(self, connection_id: str) -> str:
        json_scope = self.connection.get(connection_id)

        return json_scope

    def delete(self, connection_id: str) -> None:
        self.connection.delete(connection_id)

    def subscribe(self, channel: str, *, connection_id: str) -> None:
        self.connection.sadd(channel, connection_id)

    def unsubscribe(self, channel: str, *, connection_id: str) -> None:
        self.connection.srem(channel, connection_id)

    def get_subscribers(self, channel: str) -> set:
        subscribers = self.connection.smembers(channel)

        return subscribers
