import sqlite3

from dataclasses import dataclass

from mangum.backends.base import WebSocketBackend


@dataclass
class SQLiteBackend(WebSocketBackend):
    def __post_init__(self) -> None:
        dsn = self.dsn.replace("sqlite://", "")
        self.connection = sqlite3.connect(dsn)
        self.cursor = self.connection.cursor()
        self.cursor.execute(
            f"create table if not exists mangum_ws (id varchar(64) primary key, initial_scope text)"
        )

    def create(self, connection_id: str, initial_scope: str) -> None:
        self.cursor.execute(
            f"insert into mangum_ws values (?, ?)", (connection_id, initial_scope)
        )
        self.connection.commit()
        self.cursor.close()
        self.connection.close()

    def fetch(self, connection_id: str) -> str:
        initial_scope = self.cursor.execute(
            f"select initial_scope from mangum_ws where id = ?", (connection_id,)
        ).fetchone()[0]
        self.cursor.close()
        self.connection.close()

        return initial_scope

    def delete(self, connection_id: str) -> None:
        self.cursor.execute(
            f"delete from mangum_ws where id = ?", (connection_id,)
        ).fetchone()
        self.connection.commit()
        self.cursor.close()
        self.connection.close()
