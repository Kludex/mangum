import os
import sys
import json
import shutil
import subprocess
import datetime
from typing import Union
from dataclasses import dataclass
from pathlib import Path

from mangum.utils import get_logger

import boto3


@dataclass
class MangumConfig:

    config_dir: str
    project_dir: str
    project_name: str
    resource_name: str
    handler_name: str
    description: str
    url_root: str
    timeout: int
    region_name: str
    s3_bucket_name: str

    def __post_init__(self) -> None:
        self.logger = get_logger()
        self.init()

    def init(self) -> None:
        config_file_path = os.path.join(self.config_dir, "config.json")
        config_json = json.dumps(
            {
                "config_dir": self.config_dir,
                "project_dir": self.project_dir,
                "project_name": self.project_name,
                "handler_name": self.handler_name,
                "resource_name": self.resource_name,
                "description": self.description,
                "region_name": self.region_name,
                "url_root": self.url_root,
                "s3_bucket_name": self.s3_bucket_name,
                "timeout": self.timeout,
            }
        )
        with open(config_file_path, "w") as f:
            f.write(config_json)

    def build(self) -> None:

        build_dir = os.path.join(self.config_dir, "build")
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)

        if not os.path.isdir(build_dir):
            os.mkdir(build_dir)

        self.logger.info("Installing requirements...")
        install_cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            "requirements.txt",
            "-t",
            build_dir,
        ]
        installed = subprocess.run(install_cmd, stdout=subprocess.PIPE)
        if installed.returncode != 0:
            raise RuntimeError("Build failed, could not install requirements.")

        self.logger.info(f"Requirements installed to {build_dir}")
        exclude = ("config.json", "template.json", "requirements.txt", ".env")

        for root, dirs, files in os.walk(self.project_dir, topdown=True):
            files[:] = [f for f in files if f not in exclude]

            for file_name in files:
                file_path = os.path.join(root, file_name)
                relative_file_path = Path(file_path).relative_to(self.project_dir)
                target_path = Path(os.path.join(build_dir, relative_file_path))
                if not os.path.isdir(target_path.parent):
                    os.makedirs(target_path.parent)
                shutil.copyfile(file_path, target_path)

    def describe(self) -> Union[str, None]:  # pragma: no cover
        cmd = [
            "aws",
            "cloudformation",
            "describe-stacks",
            "--stack-name",
            self.project_name.lower(),
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

    def package(self) -> bool:
        template_json = json.dumps(self.get_template())
        template_file_path = os.path.join(self.config_dir, "template.json")
        with open(template_file_path, "w") as f:
            f.write(template_json)

        cmd = [
            "aws",
            "cloudformation",
            "package",
            "--template-file",
            "template.json",
            "--output-template-file",
            "packaged.yaml",
            "--s3-bucket",
            self.s3_bucket_name,
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE)
        return res.returncode == 0

    def deploy(self) -> bool:
        cmd = [
            "aws",
            "cloudformation",
            "deploy",
            "--template-file",
            "packaged.yaml",
            "--stack-name",
            self.project_name.lower(),
            "--capabilities",
            "CAPABILITY_IAM",
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE)
        return res.returncode == 0

    def validate(self) -> Union[None, str]:
        client = boto3.client("cloudformation")
        template = self.get_template()
        try:
            client.validate_template(TemplateBody=json.dumps(template))
        except Exception as exc:
            return str(exc)
        return None

    def get_env_vars(self) -> dict:
        env_vars = {}
        env_file = Path(os.path.join(self.config_dir, ".env"))
        if env_file.is_file():
            with open(env_file, "r") as env_file:
                for line in env_file:
                    if line[0] != "#":
                        key, value = line.strip().split("=")
                        env_vars[key] = value
        return env_vars

    def get_template(self) -> dict:
        iam_role_name = f"{self.resource_name}FunctionRole"
        lambda_function_name = f"{self.resource_name}Function"
        api_gateway_name = f"{self.resource_name}Api"
        permission_name = f"{self.resource_name}FunctionPermission"

        template_dict = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Transform": "AWS::Serverless-2016-10-31",
            "Description": f"{self.description} {datetime.datetime.now()}",
            "Globals": {"Function": {"Timeout": self.timeout}},
            "Resources": {
                f"{self.resource_name}Function": {
                    "Type": "AWS::Serverless::Function",
                    "Properties": {
                        "CodeUri": os.path.join(self.config_dir, "build"),
                        "Handler": self.handler_name,
                        "Runtime": "python3.7",
                        "Environment": {"Variables": self.get_env_vars()},
                        "Events": {
                            "ProxyApiRoot": {
                                "Type": "Api",
                                "Properties": {"Path": "/", "Method": "ANY"},
                            },
                            "ProxyApiGreedy": {
                                "Type": "Api",
                                "Properties": {"Path": "/{proxy+}", "Method": "ANY"},
                            },
                        },
                    },
                },
                permission_name: {
                    "Type": "AWS::IAM::Policy",
                    "Properties": {
                        "PolicyName": "root",
                        "PolicyDocument": {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Action": ["s3:*"],
                                    "Resource": "arn:aws:s3:::*",
                                }
                            ],
                        },
                        "Roles": [{"Ref": iam_role_name}],
                    },
                },
            },
            "Outputs": {
                api_gateway_name: {
                    "Description": "API Gateway endpoint URL for ASGI function",
                    "Value": {
                        "Fn::Sub": "https://${ServerlessRestApi}.execute-api.${AWS::Region}.amazonaws.com/"
                    },
                },
                lambda_function_name: {
                    "Description": f"{self.resource_name} Lambda Function ARN",
                    "Value": {"Fn::GetAtt": f"{self.resource_name}Function.Arn"},
                },
                iam_role_name: {
                    "Description": f"Implicit IAM Role created for {self.resource_name} function",
                    "Value": {"Fn::GetAtt": f"{self.resource_name}FunctionRole.Arn"},
                },
            },
        }
        return template_dict
