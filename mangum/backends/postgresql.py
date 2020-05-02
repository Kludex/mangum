import logging
from dataclasses import dataclass

import psycopg2
from psycopg2 import sql

from mangum.backends.base import WebSocketBackend
from mangum.exceptions import ConfigurationError


@dataclass
class PostgreSQLBackend(WebSocketBackend):
    def __post_init__(self) -> None:
        self.logger = logging.getLogger("mangum.websocket.postgres")
        self.logger.debug("Connecting to PostgreSQL database.")
        connect_timeout = self.params.get("connect_timeout", 5)
        if "uri" in self.params:
            self.connection = psycopg2.connect(
                self.params["uri"], connect_timeout=connect_timeout
            )
        else:
            try:
                database = self.params["database"]
                user = self.params["user"]
                password = self.params["password"]
                host = self.params["host"]
            except KeyError:  # pragma: no cover
                raise ConfigurationError("PostgreSQL connection details missing.")
            port = self.params.get("port", "5432")  # pragma: no cover
            self.connection = psycopg2.connect(
                database=database,
                user=user,
                password=password,
                host=host,
                port=port,
                connect_timeout=connect_timeout,
            )
        self.table_name = self.params.get("table_name", "mangum")
        self.cursor = self.connection.cursor()
        self.cursor.execute(
            sql.SQL(
                "create table if not exists {} (id varchar(64) primary key, initial_scope text)"
            ).format(sql.Identifier(self.table_name))
        )
        self.connection.commit()
        self.logger.debug("Connection established.")

    def create(self, connection_id: str, initial_scope: str) -> None:
        self.logger.debug("Creating database entry for %s", connection_id)
        self.cursor.execute(
            sql.SQL("insert into {} values (%s, %s)").format(
                sql.Identifier(self.table_name)
            ),
            (connection_id, initial_scope),
        )

        self.connection.commit()
        self.connection.close()
        self.logger.debug("Database entry created.")

    def fetch(self, connection_id: str) -> str:
        self.logger.debug("Fetching initial scope for %s", connection_id)
        self.cursor.execute(
            sql.SQL("select initial_scope from {} where id = %s").format(
                sql.Identifier(self.table_name)
            ),
            (connection_id,),
        )
        initial_scope = self.cursor.fetchone()[0]
        self.cursor.close()
        self.connection.close()
        self.logger.debug("Initial scope fetched.")

        return initial_scope

    def delete(self, connection_id: str) -> None:
        self.logger.debug("Deleting database entry for %s", connection_id)
        self.cursor.execute(
            sql.SQL("delete from {} where id = %s").format(
                sql.Identifier(self.table_name)
            ),
            (connection_id,),
        )
        self.connection.commit()
        self.cursor.close()
        self.connection.close()
        self.logger.debug("Database entry deleted.")
