from typing import Any

import aiopg

from .base import WebSocketBackend
from ..exceptions import WebSocketError


class PostgreSQLBackend(WebSocketBackend):
    async def __aenter__(self) -> WebSocketBackend:
        self.connection = await aiopg.connect(self.dsn)
        self.cursor = await self.connection.cursor()

        await self.cursor.execute(
            "create table if not exists mangum_websockets "
            "(id varchar(64) primary key, initial_scope text)"
        )

        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        self.cursor.close()
        await self.connection.close()

    async def save(self, connection_id: str, *, json_scope: str) -> None:
        await self.cursor.execute(
            "insert into mangum_websockets values (%s, %s)",
            (connection_id, json_scope),
        )

    async def retrieve(self, connection_id: str) -> str:
        await self.cursor.execute(
            "select initial_scope from mangum_websockets where id = %s",
            (connection_id,),
        )
        row = await self.cursor.fetchone()
        if not row:
            raise WebSocketError(f"Connection not found: {connection_id}")
        initial_scope = row[0]
        return initial_scope

    async def delete(self, connection_id: str) -> None:
        await self.cursor.execute(
            "delete from mangum_websockets where id = %s", (connection_id,)
        )
