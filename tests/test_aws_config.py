import os
from mangum.platforms.aws.config import AWSConfig
from mangum.platforms.aws.helpers import get_default_resource_name


def test_get_default_resource_name() -> None:
    resource_name = get_default_resource_name("helloworldproject")
    assert resource_name == "Helloworldproject"
    resource_name_with_underscores = get_default_resource_name("hello_world_project")
    assert resource_name_with_underscores == "HelloWorldProject"


def test_aws_config(mock_data) -> None:
    settings = mock_data.get_aws_config_settings()
    config = AWSConfig(**settings)
    build_context = config.get_build_context()
    assert build_context == {
        "description": "ASGI application",
        "project_name": "TestProject",
        "region_name": "ap-southeast-1",
        "resource_name": "Testproject",
        "runtime_version": "3.7",
        "s3_bucket_name": "testproject-04a427ce-3267-4cbf-91c9-44fb986cddfd",
        "stack_name": "testproject",
        "timeout": 300,
        "url_root": "/",
    }

    SAM_template = config.get_SAM_template().strip()
    assert mock_data.get_mock_SAM_template() == SAM_template.strip()

    config_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    assert config.config_dir == config_dir
    assert config.build_dir == os.path.join(config_dir, "build")
    assert config.project_dir == os.path.join(config_dir, "TestProject")
