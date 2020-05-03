import os
import sqlite3

from dataclasses import dataclass

from mangum.backends.base import WebSocketBackend
from mangum.exceptions import ConfigurationError


@dataclass
class SQLiteBackend(WebSocketBackend):
    def __post_init__(self) -> None:
        try:
            file_path = self.params["file_path"]
        except KeyError:
            raise ConfigurationError(f"SQLite3 database 'file_path' missing.")
        self.table_name = self.params.get("table_name", "mangum")
        if not os.path.exists(file_path):
            self.connection = sqlite3.connect(file_path)
            self.cursor = self.connection.cursor()
            self.cursor.execute(
                f"create table {self.table_name} (id varchar(64) primary key, initial_scope text)"
            )
        else:
            self.connection = sqlite3.connect(file_path)
            self.cursor = self.connection.cursor()

    def create(self, connection_id: str, initial_scope: str) -> None:
        self.cursor.execute(
            f"insert into {self.table_name} values (?, ?)",
            (connection_id, initial_scope),
        )
        self.connection.commit()
        self.cursor.close()
        self.connection.close()

    def fetch(self, connection_id: str) -> str:
        initial_scope = self.cursor.execute(
            f"select initial_scope from {self.table_name} where id = ?",
            (connection_id,),
        ).fetchone()[0]
        self.cursor.close()
        self.connection.close()

        return initial_scope

    def delete(self, connection_id: str) -> None:
        self.cursor.execute(
            f"delete from {self.table_name} where id = ?", (connection_id,)
        ).fetchone()
        self.connection.commit()
        self.cursor.close()
        self.connection.close()
