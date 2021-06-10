import aiosqlite

from mangum.backends.base import WebSocketBackend


class SQLiteBackend(WebSocketBackend):
    async def connect(self) -> None:
        self.connection = await aiosqlite.connect(self.dsn[9:])  # TODO fix
        await self.connection.execute(
            "create table if not exists mangum_websockets (id varchar(64) primary key, initial_scope text)"
        )
        await self.connection.commit()

    async def disconnect(self) -> None:
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
            scope = row[0]

        return scope

    async def delete(self, connection_id: str) -> None:
        await self.connection.execute(
            "delete from mangum_websockets where id = ?", (connection_id,)
        )
        await self.connection.commit()
