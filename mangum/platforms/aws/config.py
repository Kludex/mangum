import os
import subprocess
import json
import sys
from typing import Union
import boto3
import shutil
from mangum.utils import write_file_content


class AWSConfig:
    def __init__(
        self,
        *,
        project_name: str,
        description: str,
        region_name: str,
        runtime_version: str,
        url_root: str,
        s3_bucket_name: str,
        resource_name: str,
        timeout: int,
        stack_name: str,
    ) -> None:
        self.project_name = project_name
        self.description = description
        self.region_name = region_name
        self.runtime_version = runtime_version
        self.url_root = url_root
        self.s3_bucket_name = s3_bucket_name
        self.resource_name = resource_name
        self.timeout = timeout
        self.stack_name = stack_name

    @property
    def config_dir(self):
        return os.getcwd()

    @property
    def project_dir(self):
        return os.path.join(self.config_dir, self.project_name)

    @property
    def build_dir(self):
        build_path = os.path.join(self.config_dir, "build")
        return build_path

    def init(self) -> None:  # pragma: no cover
        """
        Write the configuration files used by the CLI. These will be used later to
        inform the AWS CLI wrappers.
        """
        config_files = {
            "template.yaml": {
                "directory": self.config_dir,
                "content": self.get_SAM_template(),
            },
            "settings.json": {
                "directory": self.config_dir,
                "content": json.dumps(self.get_build_context()),
                "as_json": True,
            },
            "requirements.txt": {"directory": self.config_dir, "content": "mangum\n"},
        }
        for name, info in config_files.items():
            write_file_content(
                content=info["content"],
                filename=name,
                directory=info["directory"],
                as_json=info.get("as_json", False),
            )

        shutil.copyfile(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "templates", "asgi.py"
            ),
            os.path.join(os.path.join(self.config_dir), "asgi.py"),
        )

    def build(self) -> None:  # pragma: no cover
        """
        Copy all the files in the project directory to the build directory, then install
        the requirements.
        """
        if os.path.exists(self.build_dir):
            shutil.rmtree(self.build_dir)

        shutil.copytree(
            self.project_dir,
            os.path.join(self.build_dir, os.path.basename(self.project_dir)),
        )

        for config_file in ("template.yaml", "asgi.py"):
            shutil.copyfile(
                os.path.join(self.config_dir, config_file),
                os.path.join(self.build_dir, config_file),
            )

        if not os.path.exists(os.path.join(self.config_dir, "requirements.txt")):
            raise IOError(f"File not found: 'requirements.txt' does not exist.")

        install_cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            "requirements.txt",
            "-t",
            os.path.join(".", self.build_dir),
        ]
        installed = subprocess.run(install_cmd, stdout=subprocess.PIPE)
        if installed.returncode != 0:
            raise RuntimeError("Build failed, could not install requirements.")

    def validate(self) -> Union[None, str]:  # pragma: no cover
        with open(os.path.join(self.config_dir, "template.yaml")) as f:
            template_body = f.read()
        client = boto3.client("cloudformation")
        try:
            client.validate_template(TemplateBody=template_body)
        except Exception as exc:
            return str(exc)

    def cli_describe(self) -> Union[str, None]:  # pragma: no cover
        cmd = [
            "aws",
            "cloudformation",
            "describe-stacks",
            "--stack-name",
            self.stack_name,
            "--query",
            "Stacks[].Outputs",
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE)
        if res.returncode != 0:
            return None
        data = json.loads(res.stdout)
        for i in data:
            for j in i:
                if j["OutputKey"] == f"{self.resource_name}Api":
                    endpoint = j["OutputValue"]
        return f"{endpoint}Prod\n\n{endpoint}Stage"

    def cli_package(self) -> bool:  # pragma: no cover

        cmd = [
            "aws",
            "cloudformation",
            "package",
            "--template-file",
            "template.yaml",
            "--output-template-file",
            "packaged.yaml",
            "--s3-bucket",
            f"{self.s3_bucket_name}",
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE)
        return res.returncode == 0

    def cli_deploy(self) -> bool:  # pragma: no cover
        cmd = [
            "aws",
            "cloudformation",
            "deploy",
            "--template-file",
            "packaged.yaml",
            "--stack-name",
            f"{self.stack_name}",
            "--capabilities",
            "CAPABILITY_IAM",
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE)
        return res.returncode == 0

    def get_build_context(self) -> dict:
        return {
            "project_name": self.project_name,
            "description": self.description,
            "region_name": self.region_name,
            "runtime_version": self.runtime_version,
            "resource_name": self.resource_name,
            "url_root": self.url_root,
            "s3_bucket_name": self.s3_bucket_name,
            "timeout": self.timeout,
            "stack_name": self.stack_name,
        }

    def get_SAM_template(self) -> str:
        return f"""AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: >
    {self.project_name}
    {self.description}
Globals:
    Function:
        Timeout: {self.timeout}
Resources:
    {self.resource_name}Function:
        Type: AWS::Serverless::Function
        Properties:
            FunctionName: {self.resource_name}Function
            CodeUri: ./build
            Handler: asgi.lambda_handler
            Runtime: python{self.runtime_version}
            # Environment:
            #     Variables:
            #         PARAM1: VALUE
            Events:
                {self.resource_name}:
                    Type: Api
                    Properties:
                        Path: {self.url_root}
                        Method: get
Outputs:
    {self.resource_name}Api:
      Description: "API Gateway endpoint URL for {self.resource_name} function"
      Value: !Sub "https://${{ServerlessRestApi}}.execute-api.${{AWS::Region}}.amazonaws.com{self.url_root}"
    {self.resource_name}Function:
      Description: "{self.resource_name} Lambda Function ARN"
      Value: !GetAtt {self.resource_name}Function.Arn
    {self.resource_name}FunctionIamRole:
      Description: "Implicit IAM Role created for {self.resource_name} function"
      Value: !GetAtt {self.resource_name}FunctionRole.Arn"""
