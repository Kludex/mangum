import os
import sys
import json
import shutil
import subprocess
import datetime
from typing import Union
from dataclasses import dataclass
from pathlib import Path

import yaml
from mangum.utils import get_logger

import boto3


@dataclass
class Config:

    name: str
    code_dir: str
    handler: str
    bucket_name: str
    region_name: str
    timeout: int

    def __post_init__(self) -> None:
        self.logger = get_logger()
        self.resource_name = self.name.title()
        self.config_dir = os.getcwd()
        self.stack_name = self.name.lower()

    def build(self, *, no_pip: bool) -> None:
        build_dir = os.path.join(self.config_dir, "build")

        # Remove an existing build directory entirely when building with dependencies.
        if not no_pip:
            if os.path.exists(build_dir):
                shutil.rmtree(build_dir)

        if not os.path.isdir(build_dir):
            os.mkdir(build_dir)

        if not no_pip:
            self.logger.info("Installing dependencies from 'requirements.txt'...")
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

        for root, dirs, files in os.walk(self.code_dir, topdown=True):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                relative_file_path = Path(file_path).relative_to(self.code_dir)
                target_path = Path(os.path.join(build_dir, relative_file_path))
                if not os.path.isdir(target_path.parent):
                    os.makedirs(target_path.parent)
                shutil.copyfile(file_path, target_path)

    def package(self) -> bool:
        template = self.get_template()
        template_yml = yaml.dump(template, default_flow_style=False, sort_keys=False)
        template_file_path = os.path.join(self.config_dir, "template.yml")
        with open(template_file_path, "w") as f:
            f.write(template_yml)

        cmd = [
            "aws",
            "cloudformation",
            "package",
            "--template-file",
            "template.yml",
            "--output-template-file",
            "packaged.yml",
            "--s3-bucket",
            self.bucket_name,
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE)
        return res.returncode == 0

    def deploy(self) -> bool:
        cmd = [
            "aws",
            "cloudformation",
            "deploy",
            "--template-file",
            "packaged.yml",
            "--stack-name",
            self.stack_name,
            "--capabilities",
            "CAPABILITY_IAM",
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE)
        return res.returncode == 0

    def describe(self) -> Union[str, None]:  # pragma: no cover
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

        template = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Transform": "AWS::Serverless-2016-10-31",
            "Description": f"ASGI application updated @ {datetime.datetime.now()}",
            "Globals": {"Function": {"Timeout": self.timeout}},
            "Resources": {
                f"{self.resource_name}Function": {
                    "Type": "AWS::Serverless::Function",
                    "Properties": {
                        "CodeUri": os.path.join(self.config_dir, "build"),
                        "Handler": self.handler,
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
                                    "Resource": [
                                        f"arn:aws:s3:::{self.bucket_name}",
                                        f"arn:aws:s3:::{self.bucket_name}/*",
                                    ],
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
        return template
