import pandas as pd
import psycopg
from typing import Any

from sql_runner.core import ConnectionConfig, SQLRunner


class PostgresRunner(SQLRunner):

    def __init__(
            self,
            connection_config: ConnectionConfig,
    ):
        super().__init__(connection_config=connection_config)

        self.conn = psycopg.connect(
            dbname=self.connection_config.database,
            user=self.connection_config.user,
            password=self.connection_config.password,
            host=self.connection_config.host,
            port=self.connection_config.port,
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
        cursor = self.conn.cursor()
        try:
            for query in queries:
                self.logger.info(f"Executing query:\n{query}")
                cursor.execute(query)
            self.conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to execute transaction:\n{e}. Rolling back any changes...")
            self.conn.rollback()
            raise e
        finally:
            cursor.close()

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

            rows: list[tuple[Any]] = []
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
