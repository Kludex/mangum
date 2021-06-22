from typing import Any
from urllib.parse import urlparse

import aiosqlite

from .base import WebSocketBackend
from ..exceptions import WebSocketError


class SQLiteBackend(WebSocketBackend):
    async def __aenter__(self) -> WebSocketBackend:
        parsed_dsn = urlparse(self.dsn)
        self.connection = await aiosqlite.connect(parsed_dsn.path)
        await self.connection.execute(
            "create table if not exists mangum_websockets "
            "(id varchar(64) primary key, initial_scope text)"
        )
        await self.connection.commit()

        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.connection.close()

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
