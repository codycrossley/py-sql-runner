from dataclasses import dataclass, asdict
from sqlite3 import connect

from dotenv import load_dotenv, dotenv_values
import os
from pathlib import Path

from sql_runner.core import ConnectionConfig
from sql_runner.trino_runner import TrinoRunner


@dataclass
class EnvMapping:
    host: str = "SQL_RUNNER_HOST"
    database: str = "SQL_RUNNER_DATABASE"
    user: str = "SQL_RUNNER_USER"
    password: str = "SQL_RUNNER_PASSWORD"
    port: str = "SQL_RUNNER_PORT"
    catalog: str = "SQL_RUNNER_CATALOG"
    schema: str = "SQL_RUNNER_SCHEMA"
    url: str = "SQL_RUNNER_URL"


def create_trino_runner_from_env(
        env_path: Path,
        env_mapping: EnvMapping | dict = None,
        client_tags: list[str] = None,
):
    load_dotenv(dotenv_path=env_path)

    if not env_mapping:
        env_mapping = EnvMapping()

    if isinstance(env_mapping, dict):
        env_mapping = EnvMapping(**env_mapping)

    connection_config = ConnectionConfig(
        host=os.getenv(env_mapping.host),
        database=os.getenv(env_mapping.database),
        user=os.getenv(env_mapping.user),
        password=os.getenv(env_mapping.password),
        port=int(os.getenv(env_mapping.port)),
        catalog=os.getenv(env_mapping.catalog),
        schema=os.getenv(env_mapping.schema),
        url=os.getenv(env_mapping.url),
    )

    return TrinoRunner(
        connection_config=connection_config,
        client_tags=client_tags,
    )
