import boto3
from botocore.exceptions import ClientError
from dataclasses import dataclass

from dotenv import load_dotenv
import json
import os
from pathlib import Path

from sql_runner.core import ConnectionConfig
from sql_runner import PostgresRunner, TrinoRunner


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


def get_secret_value(
        secret_name: str,
        region: str = "us-east-1",
        session: boto3.session.Session | None = None
):
    session = session or boto3.session.Session()
    client = session.client("secretsmanager", region_name=region)

    try:
        response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        raise RuntimeError(f"Error getting secret value {secret_name}:\n{e}")

    secret_string: str | None = response.get("SecretString")
    secret_binary: bytes | None = response.get("SecretBinary")

    if secret_string is None and secret_binary is not None:
        secret_string = secret_binary.decode("utf-8")

    if secret_string is None:
        raise ValueError(f"No retrievable value could be found for {secret_name}.")

    try:
        return json.loads(secret_string)
    except json.JSONDecodeError:
        return secret_string


def create_connection_config_from_env(
        env_path: Path | str = None,
        env_mapping: EnvMapping | dict = None,
) -> ConnectionConfig:
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

    return connection_config


def create_connection_config_from_secret(
        secret_name: str,
        region: str = "us-east-1",
        session: boto3.session.Session | None = None,
) -> ConnectionConfig:
    secret_config = get_secret_value(
        secret_name=secret_name,
        region=region,
        session=session,
    )

    if isinstance(secret_config, dict):
        return ConnectionConfig(**secret_config)
    else:
        raise ValueError(f"The value of the provided secret ({secret_name}) is not a JSON dictionary. Perhaps, "
                         f"it is a URL/connection string? URLs cannot currently be parsed, but this functionality "
                         f"is expected soon.")


def create_postgres_runner_from_env(
        env_path: Path | str,
        env_mapping: EnvMapping | dict = None,
):
    connection_config = create_connection_config_from_env(
        env_path=env_path,
        env_mapping=env_mapping,
    )

    return PostgresRunner(connection_config=connection_config)


def create_postgres_runner_from_aws_secret(
        secret_name: str,
        region: str = "us-east-1",
        session: boto3.session.Session | None = None,
):
    connection_config = create_connection_config_from_secret(
        secret_name=secret_name,
        region=region,
        session=session,
    )

    return PostgresRunner(connection_config=connection_config)


def create_trino_runner_from_env(
        env_path: Path | str,
        env_mapping: EnvMapping | dict = None,
        client_tags: list[str] = None,
):
    connection_config = create_connection_config_from_env(
        env_path=env_path,
        env_mapping=env_mapping,
    )

    return TrinoRunner(
        connection_config=connection_config,
        client_tags=client_tags,
    )


def create_trino_runner_from_aws_secret(
        secret_name: str,
        region: str = "us-east-1",
        session: boto3.session.Session | None = None,
        client_tags: list[str] = None,
):
    if client_tags is None:
        client_tags = []

    connection_config = create_connection_config_from_secret(
        secret_name=secret_name,
        region=region,
        session=session,
    )

    return TrinoRunner(
        connection_config=connection_config,
        client_tags=client_tags,
    )
