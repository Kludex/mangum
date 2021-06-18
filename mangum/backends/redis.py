from typing import AsyncIterator
import aioredis

from mangum.backends.base import WebSocketBackend
from mangum.exceptions import WebSocketError
from .._compat import asynccontextmanager


class RedisBackend(WebSocketBackend):
    @asynccontextmanager  # type: ignore
    async def connect(self) -> AsyncIterator:
        self.connection = await aioredis.create_redis(self.dsn)
        try:
            yield
        finally:
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
