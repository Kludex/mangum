import os
import subprocess
import json
import sys
import uuid
from typing import Union
from jinja2 import Environment, FileSystemLoader
import boto3


class AWSConfig:
    def __init__(
        self,
        *,
        config_dir: str,
        package_dir: str,
        project_name: str,
        description: str,
        region_name: str,
        runtime_version: str,
        url_root: str,
        s3_bucket_name: str,
        resource_name: str,
        timeout: int,
        stack_name: str,
        generate_s3: bool = False,
    ) -> None:
        self.config_dir = config_dir
        self.package_dir = package_dir
        self.project_name = project_name
        self.description = description
        self.region_name = region_name
        self.runtime_version = runtime_version
        self.url_root = url_root
        self.s3_bucket_name = s3_bucket_name
        self.resource_name = resource_name
        self.timeout = timeout
        self.stack_name = stack_name
        self.generate_s3 = generate_s3
        self.env = Environment(
            loader=FileSystemLoader(
                os.path.join(os.path.dirname(os.path.realpath(__file__)), "files")
            )
        )

    @classmethod
    def get_config_from_file(cls):
        cwd = os.getcwd()
        with open(os.path.join(cwd, "settings.json"), "r") as f:
            json_data = f.read()
            settings = json.loads(json_data)
        config = cls(**settings)
        return config

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
        install_cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            "requirements.txt",
            "--upgrade",
            "-t",
            os.path.join(".", self.package_dir, "dist"),
        ]
        installed = subprocess.run(install_cmd, stdout=subprocess.PIPE)
        if not installed.returncode == 0:
            return False

        cmd = [
            "aws",
            "cloudformation",
            "package",
            "--template-file",
            f"{self.project_name}/template.yaml",
            "--output-template-file",
            f"{self.project_name}/packaged.yaml",
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
            f"{self.project_name}/packaged.yaml",
            "--stack-name",
            f"{self.stack_name}",
            "--capabilities",
            "CAPABILITY_IAM",
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE)
        return res.returncode == 0

    def get_build_context(self) -> dict:
        return {
            "config_dir": self.config_dir,
            "package_dir": self.package_dir,
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

    def get_sam_template(self) -> str:
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
            CodeUri: .
            Handler: app.lambda_handler
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

    def get_template_map(self) -> dict:
        build_context = self.get_build_context()
        template_map = {
            "template.yaml": {
                "directory": self.package_dir,
                "content": self.get_sam_template(),
            },
            "app.py": {
                "directory": self.package_dir,
                "content": self.env.get_template("app.py.txt").render(),
            },
            "README.md": {
                "directory": self.package_dir,
                "content": self.env.get_template("README.md.txt").render(
                    context=build_context
                ),
            },
        }
        return template_map

    def write_files(self) -> None:
        template_map = self.get_template_map()

        for dest_name, dest_info in template_map.items():
            with open(
                os.path.join(dest_info["directory"], dest_name), "w", encoding="utf-8"
            ) as f:
                content = dest_info["content"]
                f.write(content)

        with open(
            os.path.join(self.config_dir, "settings.json"), "w", encoding="utf-8"
        ) as f:
            f.write(json.dumps(self.get_build_context()))

        with open(
            os.path.join(self.config_dir, "requirements.txt"), "w", encoding="utf-8"
        ) as f:
            f.write("mangum\n")

    def build(self) -> None:
        if self.generate_s3:
            self.s3_bucket_name = f"{self.resource_name.lower()}-{uuid.uuid4()}"
            s3 = boto3.resource("s3")
            s3.create_bucket(
                Bucket=self.s3_bucket_name,
                CreateBucketConfiguration={"LocationConstraint": self.region_name},
            )
        os.mkdir(self.package_dir)
        os.mkdir(os.path.join(self.package_dir, "dist"))
        self.write_files()

    def rebuild(self) -> None:
        self.write_files()
