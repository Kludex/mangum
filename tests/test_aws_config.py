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
        "config_dir": "atest/",
        "description": "ASGI application",
        "package_dir": "atest/test_project",
        "project_name": "TestProject",
        "region_name": "ap-southeast-1",
        "resource_name": "Testproject",
        "runtime_version": "3.7",
        "s3_bucket_name": "testproject-04a427ce-3267-4cbf-91c9-44fb986cddfd",
        "stack_name": "testproject",
        "timeout": 300,
        "url_root": "/",
    }


def test_get_template_map(mock_data) -> None:
    settings = mock_data.get_aws_config_settings()
    config = AWSConfig(**settings)
    template_map = config.get_template_map()
    assert len(template_map["README.md"]["content"]) > 0
    assert len(template_map["template.yaml"]["content"]) > 0
    assert len(template_map["app.py"]["content"]) > 0
