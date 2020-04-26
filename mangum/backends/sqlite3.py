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
            database = sqlite3.connect(self.file_path)
            database.execute(
                f"CREATE TABLE {self.table_name} (id VARCHAR(64) PRIMARY KEY, initial_scope TEXT)"
            )
        else:
            database = sqlite3.connect(self.file_path)

        self.database: sqlite3.Connection = database

    def create(self, connection_id: str, initial_scope: str) -> None:
        self.database.execute(
            f"INSERT INTO {self.table_name} VALUES (?, ?)",
            (connection_id, initial_scope),
        )
        self.database.commit()
        self.database.close()

    def fetch(self, connection_id: str) -> str:
        initial_scope = self.database.execute(
            f"SELECT initial_scope FROM {self.table_name} WHERE id = ?",
            (connection_id,),
        ).fetchone()[0]
        self.database.close()

        return initial_scope

    def delete(self, connection_id: str) -> None:
        self.database.execute(
            f"DELETE FROM {self.table_name} WHERE id = ?", (connection_id,)
        ).fetchone()
        self.database.commit()
        self.database.close()
