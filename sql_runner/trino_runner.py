import pandas as pd
import trino
from trino.transaction import IsolationLevel
from typing import Any

from sql_runner.core import ConnectionConfig, SQLRunner


class TrinoRunner(SQLRunner):

    def __init__(
            self,
            connection_config: ConnectionConfig,
            isolation_level: IsolationLevel = IsolationLevel.AUTOCOMMIT,
            client_tags: list[str] = None,
    ):
        super().__init__(connection_config=connection_config)

        http_scheme = "https" if self.connection_config.password else "http"
        auth = (
            trino.auth.BasicAuthentication(self.connection_config.user, self.connection_config.password)
            if self.connection_config.password
            else None
        )

        self.conn = trino.dbapi.connect(
            host=self.connection_config.host,
            port=self.connection_config.port,
            user=self.connection_config.user,
            catalog=self.connection_config.catalog or self.connection_config.database,
            schema=self.connection_config.schema,
            http_scheme=http_scheme,
            auth=auth,
            isolation_level=isolation_level,
            client_tags=client_tags,
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, "conn") and self.conn:
            self.conn.close()

    def __del__(self):
        if hasattr(self, "conn") and self.conn:
            self.conn.close()


    def execute_query(self, query: str):
        try:
            self.logger.info(f"Executing query:\n{query}")
            cursor = self.conn.cursor()
            cursor.execute(query)
            self.conn.commit()
            cursor.close()
        except Exception as e:
            self.logger.error(f"Query failed to execute: {query}\n{e}")
            raise e

    def execute_queries(self, queries: list[str], **kwargs):
        for query in queries:
            self.execute_query(query)

    def execute_transaction(self, queries: list[str]):
        raise NotImplementedError("At this time, transactions are not support for most catalogs types in "
                                  "Trino. Consider using the `execute_queries` method instead. Caution: "
                                  "Each query will be automatically committed after execution and cannot "
                                  "be rolled back.")

    def query_to_df(
            self,
            query: str,
            fetch_size: int = None,
            use_arrow: bool = True,
    ):
        cursor = self.conn.cursor()
        try:
            self.logger.info(f"Creating dataframe from query:\n{query}")
            cursor.execute(query)

            rows: list[list[Any]] = []
            if fetch_size:
                while batch := cursor.fetchmany(fetch_size):
                    rows.extend(batch)
            else:
                rows = cursor.fetchall()

            column_names: list[str] = [desc[0] for desc in cursor.description]

            if not rows:
                return pd.DataFrame(data=[], columns=pd.Index(column_names))

            if use_arrow:
                try:
                    import pyarrow as pa
                    arrays = [pa.array(col) for col in zip(*rows)]
                    table = pa.Table.from_arrays(arrays, names=column_names)
                    return table.to_pandas()
                except ImportError:
                    pass

            return pd.DataFrame(rows, columns=tuple(column_names))
        finally:
            cursor.close()
