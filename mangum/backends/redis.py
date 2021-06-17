# TODO handle module missing
import aioredis

from mangum.backends.base import WebSocketBackend
from mangum.exceptions import WebSocketError


class RedisBackend(WebSocketBackend):
    async def connect(self) -> None:
        self.connection = await aioredis.create_redis(self.dsn)

    async def disconnect(self) -> None:
        self.connection.close()

    async def save(self, connection_id: str, *, json_scope: str) -> None:
        await self.connection.set(connection_id, json_scope)

    async def retrieve(self, connection_id: str) -> str:
        scope = await self.connection.get(connection_id)
        if not scope:
            raise WebSocketError(f"Connection not found: {connection_id}")
        return scope

    async def delete(self, connection_id: str) -> None:
        await self.connection.delete(connection_id)
