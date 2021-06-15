# import psycopg2
import aiopg

from mangum.backends.base import WebSocketBackend


class PostgreSQLBackend(WebSocketBackend):
    async def connect(self) -> None:
        self.connection = await aiopg.connect(self.dsn)

        self.cursor = await self.connection.cursor()
        await self.cursor.execute(
            "create table if not exists mangum_websockets (id varchar(64) primary key, initial_scope text)"
        )

    async def disconnect(self) -> None:
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
        initial_scope = row[0]
        return initial_scope

    async def delete(self, connection_id: str) -> None:
        await self.cursor.execute(
            "delete from mangum_websockets where id = %s", (connection_id,)
        )
