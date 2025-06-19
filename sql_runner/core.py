import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from jinja2 import Environment, FileSystemLoader
from pathlib import Path


@dataclass
class ConnectionConfig:
    host: str = None
    database: str = None
    user: str = None
    password: str = None
    port: int = None
    catalog: str = None
    schema: str = None
    url: str = None

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        """
        Masks the host, password, and URL, if available.
        """
        return (
            f"{self.__class__.__name__}("
            f"host=***,",
            f"database={self.database!r},",
            f"user={self.user!r},",
            f"password=***,"
            f"port={self.port!r},",
            f"catalog={self.catalog!r},",
            f"schema={self.schema!r},",
            f"url=***",
            f")"
        )


class SQLRunner(ABC):

    def __init__(
            self,
            connection_config: ConnectionConfig,
            logger: logging.Logger=None,
    ):
        self.connection_config = connection_config

        if logger is None:
            logger = logging.getLogger()
        self.logger = logger

    @abstractmethod
    def execute_query(self, query: str):
        raise NotImplementedError

    @abstractmethod
    def execute_queries(self, queries: list[str]):
        raise NotImplementedError

    @abstractmethod
    def execute_transaction(self, queries: list[str]):
        raise NotImplementedError

    @abstractmethod
    def query_to_df(self, query: str):
        raise NotImplementedError

    @staticmethod
    def build_query(
            file_name: str,
            sql_directory: Path | str = "sql/",
            render_params: dict = None
    ):
        if render_params is None:
            render_params = {}

        env = Environment(
            loader=FileSystemLoader(sql_directory),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        template = env.get_template(file_name)
        return template.render(**render_params)
