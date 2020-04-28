from dataclasses import dataclass

import psycopg2
from psycopg2 import sql

from mangum.backends.base import WebSocketBackend


@dataclass
class PostgreSQLBackend(WebSocketBackend):

    database: str
    user: str
    password: str
    host: str
    port: str = "5432"
    create_table: bool = False
    table_name: str = "connection"

    def __post_init__(self) -> None:
        self.db = psycopg2.connect(
            database=self.database,
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
        )
        self.cursor = self.db.cursor()
        if self.create_table:
            self.cursor.execute(
                "select exists(select * from information_schema.tables where table_name=%s)",
                (self.table_name,),
            )
            if not self.cursor.fetchone()[0]:
                self.cursor.execute(
                    f"create table {self.table_name} (id varchar(64) primary key, initial_scope text)"
                )
                self.db.commit()

    def create(self, connection_id: str, initial_scope: str) -> None:
        self.cursor.execute(
            sql.SQL("insert into {} values (%s, %s)").format(
                sql.Identifier(self.table_name)
            ),
            (connection_id, initial_scope),
        )

        self.db.commit()
        self.db.close()

    def fetch(self, connection_id: str) -> str:
        self.cursor.execute(
            sql.SQL("select initial_scope from {} where id = %s").format(
                sql.Identifier(self.table_name)
            ),
            (connection_id,),
        )
        initial_scope = self.cursor.fetchone()[0]
        self.db.close()

        return initial_scope

    def delete(self, connection_id: str) -> None:
        self.cursor.execute(
            sql.SQL("delete from {} where id = %s").format(
                sql.Identifier(self.table_name)
            ),
            (connection_id,),
        )
        self.db.commit()
        self.db.close()
