from dataclasses import dataclass

import psycopg2

from mangum.backends.base import WebSocketBackend


@dataclass
class PostgreSQLBackend(WebSocketBackend):
    def __post_init__(self) -> None:
        self.connection = psycopg2.connect(self.dsn, connect_timeout=5)
        self.cursor = self.connection.cursor()
        self.cursor.execute(
            "create table if not exists mangum_websockets (id varchar(64) primary key, initial_scope text)"
        )
        self.connection.commit()

    def create(self, connection_id: str, initial_scope: str) -> None:
        self.cursor.execute(
            "insert into mangum_websockets values (%s, %s)",
            (connection_id, initial_scope),
        )
        self.connection.commit()
        self.connection.close()

    def fetch(self, connection_id: str) -> str:
        self.cursor.execute(
            "select initial_scope from mangum_websockets where id = %s",
            (connection_id,),
        )
        initial_scope = self.cursor.fetchone()[0]
        self.cursor.close()
        self.connection.close()

        return initial_scope

    def delete(self, connection_id: str) -> None:
        self.cursor.execute(
            "delete from mangum_websockets where id = %s", (connection_id,)
        )
        self.connection.commit()
        self.cursor.close()
        self.connection.close()
