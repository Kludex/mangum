# TODO handle module missing
import aioredis

from mangum.backends.base import WebSocketBackend


class RedisBackend(WebSocketBackend):
    async def connect(self) -> None:
        self.connection = await aioredis.create_redis(self.dsn)

    async def disconnect(self) -> None:
        await self.connection.close()

    async def save(self, connection_id: str, *, json_scope: str) -> None:
        await self.connection.set(connection_id, json_scope)

    async def retrieve(self, connection_id: str) -> str:
        return await self.connection.get(connection_id)

    async def delete(self, connection_id: str) -> None:
        await self.connection.delete(connection_id)
