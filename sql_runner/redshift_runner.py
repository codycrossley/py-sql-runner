import traceback

import pandas as pd
import redshift_connector
from typing import List

from sql_runner.core import ConnectionConfig, SQLRunner


class RedshiftRunner(SQLRunner):
    def __init__(
        self,
        connection_config: ConnectionConfig,
    ):
        super().__init__(connection_config=connection_config)

        self.conn = redshift_connector.connect(
            host=connection_config.host,
            port=connection_config.port or 5439,
            database=connection_config.database,
            user=connection_config.user,
            password=connection_config.password,
            ssl=True,
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
        cursor = self.conn.cursor()
        try:
            self.logger.info(f"Executing query:\n{query}")
            cursor.execute(query)
            self.conn.commit()
        except Exception:
            self.logger.exception(f"Failed to execute query\n{query}\n{traceback.format_exc()}")
            raise
        finally:
            cursor.close()

    def execute_queries(self, queries: list[str]):
        for query in queries:
            self.execute_query(query)

    def execute_transaction(self, queries: List[str]):
        cursor = self.conn.cursor()
        try:
            for query in queries:
                self.logger.info(f"Executing SQL in transaction:\n{query}")
                cursor.execute(query)
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            self.logger.exception(f"Transaction failed. Attempting to roll back changes\n{traceback.format_exc()}")
            raise
        finally:
            cursor.close()

    def query_to_df(
        self,
        query: str,
        fetch_size: int | None = None,
        use_arrow: bool = True
    ) -> pd.DataFrame:
        cursor = self.conn.cursor()
        try:
            self.logger.info(f"Creating DataFrame from query:\n{query}")
            cursor.execute(query)

            if fetch_size:
                rows = []
                while batch := cursor.fetchmany(fetch_size):
                    rows.extend(batch)
            else:
                rows = cursor.fetchall()

            column_names = [col_desc[0] for col_desc in cursor.description]

            if not rows:
                return pd.DataFrame(data=[], columns=pd.Index(column_names))

            if use_arrow:
                try:
                    import pyarrow as pa
                    arrays = [pa.array(column) for column in zip(*rows)]
                    table = pa.Table.from_arrays(arrays, names=column_names)
                    return table.to_pandas()
                except ImportError:
                    pass

            return pd.DataFrame(rows, columns=tuple(column_names))

        finally:
            cursor.close()
