import clickhouse_connect

from sql_runner.core import ConnectionConfig, SQLRunner


class ClickHouseRunner(SQLRunner):
    def __init__(
            self,
            connection_config: ConnectionConfig,
            secure: bool = True
    ):
        super().__init__(connection_config=connection_config)

        self.client = clickhouse_connect.create_client(
            host=connection_config.host,
            port=connection_config.port,
            user=connection_config.user,
            password=connection_config.password,
            database=connection_config.database,
            secure=secure
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


    def execute_query(self, query: str):
        try:
            self.logger.info(f"Executing query:\n{query}")
            self.client.command(query)
        except Exception as e:
            self.logger.error(f"Query failed to execute: {query}\n{e}")
            raise e

    def execute_queries(self, queries: list[str], **kwargs):
        for query in queries:
            self.execute_query(query)

    def execute_transaction(self, queries: list[str]):
        self.execute_queries(queries)

    def query_to_df(
            self,
            query: str,
            fetch_size: int = None,
            use_arrow: bool = True,
    ):
        self.logger.info(f"Converting ClickHouse query to dataframe:\n{query}")
        return self.client.query_df(query)
