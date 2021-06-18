from typing import AsyncIterator
from urllib.parse import urlparse
from contextlib import asynccontextmanager

import aiosqlite

from mangum.backends.base import WebSocketBackend
from ..exceptions import WebSocketError


class SQLiteBackend(WebSocketBackend):
    @asynccontextmanager
    async def connect(self) -> AsyncIterator:
        parsed_dsn = urlparse(self.dsn)
        async with aiosqlite.connect(parsed_dsn.path) as self.connection:
            await self.connection.execute(
                "create table if not exists mangum_websockets "
                "(id varchar(64) primary key, initial_scope text)"
            )
            await self.connection.commit()
            yield

    async def save(self, connection_id: str, *, json_scope: str) -> None:
        await self.connection.execute(
            "insert into mangum_websockets values (?, ?)",
            (connection_id, json_scope),
        )
        await self.connection.commit()

    async def retrieve(self, connection_id: str) -> str:
        async with self.connection.execute(
            "select initial_scope from mangum_websockets where id = ?",
            (connection_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise WebSocketError(f"Connection not found: {connection_id}")
            scope = row[0]

        return scope

    async def delete(self, connection_id: str) -> None:
        await self.connection.execute(
            "delete from mangum_websockets where id = ?", (connection_id,)
        )
        await self.connection.commit()
