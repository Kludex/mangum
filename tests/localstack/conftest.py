from __future__ import annotations

import io
import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

import boto3
import pytest

if TYPE_CHECKING:
    from testcontainers.community.localstack import LocalStackContainer

PROJECT_ROOT = Path(__file__).parent.parent.parent
APP_DIR = Path(__file__).parent / "app"


def build_lambda_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for source_dir, prefix in [
            (PROJECT_ROOT / "mangum", "mangum"),
            (APP_DIR, ""),
        ]:
            for path in source_dir.rglob("*.py"):
                archive.write(path, f"{prefix}/{path.relative_to(source_dir)}" if prefix else path.name)
        import typing_extensions

        archive.write(typing_extensions.__file__, "typing_extensions.py")
    return buffer.getvalue()


@pytest.fixture(scope="session")
def localstack() -> Iterator[LocalStackContainer]:
    from testcontainers.community.localstack import LocalStackContainer

    with LocalStackContainer("localstack/localstack:4").with_volume_mapping(
        "/var/run/docker.sock", "/var/run/docker.sock", "rw"
    ) as container:
        yield container


@pytest.fixture(scope="session")
def lambda_client(localstack: LocalStackContainer) -> Any:
    return boto3.client(
        "lambda",
        endpoint_url=localstack.get_url(),
        region_name=localstack.region_name,
        aws_access_key_id="testcontainers-localstack",
        aws_secret_access_key="testcontainers-localstack",
    )


@pytest.fixture(scope="session")
def function_url(localstack: LocalStackContainer, lambda_client: Any) -> str:
    lambda_client.create_function(
        FunctionName="mangum-echo",
        Runtime="python3.12",
        Role="arn:aws:iam::000000000000:role/lambda-role",
        Handler="main.handler",
        Code={"ZipFile": build_lambda_zip()},
        Timeout=30,
    )
    lambda_client.get_waiter("function_active_v2").wait(FunctionName="mangum-echo")
    response = lambda_client.create_function_url_config(FunctionName="mangum-echo", AuthType="NONE")
    url = str(response["FunctionUrl"])
    host_port = localstack.get_exposed_port(localstack.edge_port)
    return url.replace(":4566", f":{host_port}")
