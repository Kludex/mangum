# import os

# import yaml
# from click.testing import CliRunner

# from mangum.cli.commands import init


# def test_cli(tmpdir) -> None:
#     name = "test"
#     bucket_name = "my-bucket-1"
#     region_name = "ap-southeast-1"
#     runner = CliRunner()
#     config_dir = tmpdir.mkdir("tmp")
#     os.chdir(config_dir)
#     requirements_file_path = os.path.join(config_dir, "requirements.txt")
#     config_file_path = os.path.join(config_dir, "mangum.yml")
#     expected_config = {
#         "name": name,
#         "code_dir": "app",
#         "handler": "asgi.handler",
#         "bucket_name": bucket_name,
#         "region_name": region_name,
#         "timeout": 300,
#     }

#     result = runner.invoke(init, [name, bucket_name, region_name])

#     with open(config_file_path, "r") as f:
#         assert f.read() == yaml.dump(
#             expected_config, default_flow_style=False, sort_keys=False
#         )
#     with open(requirements_file_path, "r") as f:
#         assert f.read() == "mangum\n"

#     assert result.exit_code == 0


# def test_cli_no_optional_args(tmpdir) -> None:
#     name = "test"
#     runner = CliRunner()
#     config_dir = tmpdir.mkdir("tmp")
#     os.chdir(config_dir)
#     requirements_file_path = os.path.join(config_dir, "requirements.txt")
#     config_file_path = os.path.join(config_dir, "mangum.yml")
#     expected_config = {
#         "name": name,
#         "code_dir": "app",
#         "handler": "asgi.handler",
#         "bucket_name": None,
#         "region_name": None,
#         "timeout": 300,
#     }

#     result = runner.invoke(init, [name])

#     with open(config_file_path, "r") as f:
#         assert f.read() == yaml.dump(
#             expected_config, default_flow_style=False, sort_keys=False
#         )
#     with open(requirements_file_path, "r") as f:
#         assert f.read() == "mangum\n"

#     assert result.exit_code == 0
