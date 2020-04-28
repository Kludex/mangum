import os
import sqlite3
from dataclasses import dataclass

from mangum.backends.base import WebSocketBackend


@dataclass
class SQLite3Backend(WebSocketBackend):

    file_path: str
    table_name: str = "connection"

    def __post_init__(self) -> None:
        if not os.path.exists(self.file_path):
            db = sqlite3.connect(self.file_path)
            db.execute(
                f"create table {self.table_name} (id varchar(64) primary key, initial_scope text)"
            )
        else:
            db = sqlite3.connect(self.file_path)

        self.db: sqlite3.Connection = db

    def create(self, connection_id: str, initial_scope: str) -> None:
        self.db.execute(
            f"insert into {self.table_name} values (?, ?)",
            (connection_id, initial_scope),
        )
        self.db.commit()
        self.db.close()

    def fetch(self, connection_id: str) -> str:
        initial_scope = self.db.execute(
            f"select initial_scope from {self.table_name} where id = ?",
            (connection_id,),
        ).fetchone()[0]
        self.db.close()

        return initial_scope

    def delete(self, connection_id: str) -> None:
        self.db.execute(
            f"delete from {self.table_name} where id = ?", (connection_id,)
        ).fetchone()
        self.db.commit()
        self.db.close()
