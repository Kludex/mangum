import os
import sys
import json
import shutil
import subprocess
import datetime
import typing
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
    websockets: bool

    def __post_init__(self) -> None:
        self.logger = get_logger()
        self.prefix = self.name.title()
        self.config_dir = os.getcwd()
        self.stack_name = self.name.lower()
        self.build_dir = os.path.join(self.config_dir, "build")
        self.template = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Transform": "AWS::Serverless-2016-10-31",
            "Description": f"ASGI application updated @ {datetime.datetime.now()}",
            "Globals": {"Function": {"Timeout": self.timeout}},
            "Parameters": {},
            "Resources": {},
            "Outputs": {},
        }
        self.generate_template()

    def build(self, *, no_pip: bool) -> None:
        # Remove an existing build directory entirely when building with dependencies.
        if not no_pip:
            if os.path.exists(self.build_dir):
                shutil.rmtree(self.build_dir)

        if not os.path.isdir(self.build_dir):
            os.mkdir(self.build_dir)

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
                self.build_dir,
            ]
            installed = subprocess.run(install_cmd, stdout=subprocess.PIPE)
            if installed.returncode != 0:
                raise RuntimeError("Build failed, could not install requirements.")
            self.logger.info(f"Requirements installed to {self.build_dir}")

        for root, dirs, files in os.walk(self.code_dir, topdown=True):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                relative_file_path = Path(file_path).relative_to(self.code_dir)
                target_path = Path(os.path.join(self.build_dir, relative_file_path))
                if not os.path.isdir(target_path.parent):
                    os.makedirs(target_path.parent)
                shutil.copyfile(file_path, target_path)

    def package(self) -> bool:
        template_yml = yaml.dump(
            self.template, default_flow_style=False, sort_keys=False
        )
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

    def describe(self) -> dict:  # pragma: no cover
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
        output = {}
        for i in data:
            for j in i:
                output_key = j["OutputKey"]
                output_val = j["OutputValue"]

                if output_val.startswith("wss://") or output_val.startswith("https://"):
                    if "Prod" not in output_val:
                        output_val = f"{output_val}Prod"
                    output[output_key] = "\n".join(
                        [output_val, output_val.replace("Prod", "Stage")]
                    )
        return output

    def validate(self) -> typing.Union[None, str]:
        client = boto3.client("cloudformation")
        try:
            client.validate_template(TemplateBody=json.dumps(self.template))
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

    def add_to_template(self, *, section: str, name: str, definition: dict) -> None:
        self.template[section][name] = definition

    def add_resource(self, name: str, definition: dict) -> None:
        self.add_to_template(section="Resources", name=name, definition=definition)

    def add_output(self, name: str, definition: dict) -> None:
        self.add_to_template(section="Outputs", name=name, definition=definition)

    def generate_template(self) -> dict:
        HTTP_FUNCTION = "HTTPFunction"
        HTTP_FUNCTION_API = "HTTPFunctionAPI"
        HTTP_FUNCTION_IAM_ROLE = "HTTPFunctionRole"
        HTTP_FUNCTION_IAM_POLICY = "HTTPFunctionIAMPolicy"

        env_vars = self.get_env_vars()

        if self.websockets:
            # Table name
            WS_TABLE_NAME = "ws-connections"

            # Output name
            WS_URI = "WSURI"

            # Resource names
            WS_API = "WSAPI"
            WS_CONNECTION_TABLE = "WSConnectionTable"

            WS_CONNECT_FUNCTION = "WSConnectFunction"
            WS_CONNECT_PERMISSION = "WSConnectPermission"
            WS_CONNECT_ROUTE = "WSConnectRoute"
            WS_CONNECT_INTEGRATION = "WSConnectIntegration"

            WS_DISCONNECT_FUNCTION = "WSDisconnectFunction"
            WS_DISCONNECT_PERMISSION = "WSDisconnectPermission"
            WS_DISCONNECT_ROUTE = "WSDisconnectRoute"
            WS_DISCONNECT_INTEGRATION = "WSDisconnectIntegration"

            WS_SEND_FUNCTION = "WSSendFunction"
            WS_SEND_PERMISSION = "WSSendPermission"
            WS_SEND_ROUTE = "WSSendRoute"
            WS_SEND_INTEGRATION = "WSSendIntegration"

            self.add_resource(
                WS_API,
                definition={
                    "Type": "AWS::ApiGatewayV2::Api",
                    "Properties": {
                        "Name": WS_API,
                        "ProtocolType": "WEBSOCKET",
                        "RouteSelectionExpression": "$request.body.action",
                    },
                },
            )

            self.add_to_template(
                section="Parameters",
                name="TableName",
                definition={
                    "Type": "String",
                    "Default": WS_TABLE_NAME,
                    "Description": "(Required) The name of the new DynamoDB to store connection identifiers for each connected clients. Minimum 3 characters.",
                    "MinLength": 3,
                    "MaxLength": 50,
                    "AllowedPattern": "^[A-Za-z_\\-]+$",
                },
            )

            self.add_resource(
                WS_CONNECT_FUNCTION,
                definition={
                    "Type": "AWS::Serverless::Function",
                    "Properties": {
                        "CodeUri": self.build_dir,
                        "Handler": self.handler,
                        "MemorySize": 256,
                        "Runtime": "python3.7",
                        "Environment": {
                            "Variables": {"TABLE_NAME": {"Ref": "TableName"}}
                        },
                        "Policies": [
                            {"DynamoDBCrudPolicy": {"TableName": {"Ref": "TableName"}}}
                        ],
                    },
                },
            )
            self.add_resource(
                WS_CONNECT_PERMISSION,
                definition={
                    "Type": "AWS::Lambda::Permission",
                    "DependsOn": [WS_API, WS_CONNECT_FUNCTION],
                    "Properties": {
                        "Action": "lambda:InvokeFunction",
                        "FunctionName": {"Ref": WS_CONNECT_FUNCTION},
                        "Principal": "apigateway.amazonaws.com",
                    },
                },
            )
            self.add_resource(
                WS_CONNECT_ROUTE,
                definition={
                    "Type": "AWS::ApiGatewayV2::Route",
                    "Properties": {
                        "ApiId": {"Ref": WS_API},
                        "RouteKey": "$connect",
                        "AuthorizationType": "NONE",
                        "OperationName": WS_CONNECT_ROUTE,
                        "Target": {
                            "Fn::Join": [
                                "/",
                                ["integrations", {"Ref": WS_CONNECT_INTEGRATION}],
                            ]
                        },
                    },
                },
            )
            self.add_resource(
                WS_CONNECT_INTEGRATION,
                definition={
                    "Type": "AWS::ApiGatewayV2::Integration",
                    "Properties": {
                        "ApiId": {"Ref": WS_API},
                        "Description": "Connect Integration",
                        "IntegrationType": "AWS_PROXY",
                        "IntegrationUri": {
                            "Fn::Sub": "arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${WSConnectFunction.Arn}/invocations"
                        },
                    },
                },
            )
            self.add_resource(
                WS_DISCONNECT_FUNCTION,
                definition={
                    "Type": "AWS::Serverless::Function",
                    "Properties": {
                        "CodeUri": self.build_dir,
                        "Handler": self.handler,
                        "MemorySize": 256,
                        "Runtime": "python3.7",
                        "Environment": {
                            "Variables": {"TABLE_NAME": {"Ref": "TableName"}}
                        },
                        "Policies": [
                            {"DynamoDBCrudPolicy": {"TableName": {"Ref": "TableName"}}}
                        ],
                    },
                },
            )
            self.add_resource(
                WS_DISCONNECT_PERMISSION,
                definition={
                    "Type": "AWS::Lambda::Permission",
                    "DependsOn": [WS_API, WS_DISCONNECT_FUNCTION],
                    "Properties": {
                        "Action": "lambda:InvokeFunction",
                        "FunctionName": {"Ref": WS_DISCONNECT_FUNCTION},
                        "Principal": "apigateway.amazonaws.com",
                    },
                },
            )
            self.add_resource(
                WS_DISCONNECT_ROUTE,
                definition={
                    "Type": "AWS::ApiGatewayV2::Route",
                    "Properties": {
                        "ApiId": {"Ref": WS_API},
                        "RouteKey": "$disconnect",
                        "AuthorizationType": "NONE",
                        "OperationName": WS_DISCONNECT_ROUTE,
                        "Target": {
                            "Fn::Join": [
                                "/",
                                ["integrations", {"Ref": WS_DISCONNECT_INTEGRATION}],
                            ]
                        },
                    },
                },
            )
            self.add_resource(
                WS_DISCONNECT_INTEGRATION,
                definition={
                    "Type": "AWS::ApiGatewayV2::Integration",
                    "Properties": {
                        "ApiId": {"Ref": WS_API},
                        "Description": "Disconnect Integration",
                        "IntegrationType": "AWS_PROXY",
                        "IntegrationUri": {
                            "Fn::Sub": "arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${WSDisconnectFunction.Arn}/invocations"
                        },
                    },
                },
            )

            self.add_resource(
                WS_SEND_FUNCTION,
                definition={
                    "Type": "AWS::Serverless::Function",
                    "Properties": {
                        "CodeUri": self.build_dir,
                        "Handler": self.handler,
                        "MemorySize": 256,
                        "Runtime": "python3.7",
                        "Environment": {
                            "Variables": {"TABLE_NAME": {"Ref": "TableName"}}
                        },
                        "Policies": [
                            {"DynamoDBCrudPolicy": {"TableName": {"Ref": "TableName"}}},
                            {
                                "Statement": [
                                    {
                                        "Effect": "Allow",
                                        "Action": ["execute-api:ManageConnections"],
                                        "Resource": [
                                            "arn:aws:execute-api:*:*:*/@connections/*"
                                        ],
                                    }
                                ]
                            },
                        ],
                    },
                },
            )
            self.add_resource(
                WS_SEND_PERMISSION,
                definition={
                    "Type": "AWS::Lambda::Permission",
                    "DependsOn": [WS_API, WS_SEND_FUNCTION],
                    "Properties": {
                        "Action": "lambda:InvokeFunction",
                        "FunctionName": {"Ref": WS_SEND_FUNCTION},
                        "Principal": "apigateway.amazonaws.com",
                    },
                },
            )
            self.add_resource(
                WS_SEND_ROUTE,
                definition={
                    "Type": "AWS::ApiGatewayV2::Route",
                    "Properties": {
                        "ApiId": {"Ref": WS_API},
                        "RouteKey": "sendmessage",
                        "AuthorizationType": "NONE",
                        "OperationName": WS_SEND_ROUTE,
                        "Target": {
                            "Fn::Join": [
                                "/",
                                ["integrations", {"Ref": WS_SEND_INTEGRATION}],
                            ]
                        },
                    },
                },
            )
            self.add_resource(
                WS_SEND_INTEGRATION,
                definition={
                    "Type": "AWS::ApiGatewayV2::Integration",
                    "Properties": {
                        "ApiId": {"Ref": WS_API},
                        "Description": "Send Integration",
                        "IntegrationType": "AWS_PROXY",
                        "IntegrationUri": {
                            "Fn::Sub": "arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${WSSendFunction.Arn}/invocations"
                        },
                    },
                },
            )

            self.add_resource(
                "Deployment",
                definition={
                    "Type": "AWS::ApiGatewayV2::Deployment",
                    "DependsOn": [WS_CONNECT_ROUTE, WS_SEND_ROUTE, WS_DISCONNECT_ROUTE],
                    "Properties": {"ApiId": {"Ref": WS_API}},
                },
            )

            self.add_resource(
                "Stage",
                definition={
                    "Type": "AWS::ApiGatewayV2::Stage",
                    "Properties": {
                        "StageName": "Prod",
                        "Description": "Prod Stage",
                        "DeploymentId": {"Ref": "Deployment"},
                        "ApiId": {"Ref": WS_API},
                    },
                },
            )
            self.add_resource(
                WS_CONNECTION_TABLE,
                definition={
                    "Type": "AWS::DynamoDB::Table",
                    "Properties": {
                        "AttributeDefinitions": [
                            {"AttributeName": "connectionId", "AttributeType": "S"}
                        ],
                        "KeySchema": [
                            {"AttributeName": "connectionId", "KeyType": "HASH"}
                        ],
                        "ProvisionedThroughput": {
                            "ReadCapacityUnits": 5,
                            "WriteCapacityUnits": 5,
                        },
                        "SSESpecification": {"SSEEnabled": True},
                        "TableName": {"Ref": "TableName"},
                    },
                },
            )

            self.add_output(
                WS_CONNECTION_TABLE,
                definition={
                    "Description": f"{WS_CONNECTION_TABLE} ARN",
                    "Value": {"Fn::GetAtt": [WS_CONNECTION_TABLE, "Arn"]},
                },
            )
            self.add_output(
                WS_CONNECT_FUNCTION,
                definition={
                    "Description": f"{WS_CONNECT_FUNCTION} ARN",
                    "Value": {"Fn::GetAtt": [WS_CONNECT_FUNCTION, "Arn"]},
                },
            )
            self.add_output(
                WS_DISCONNECT_FUNCTION,
                definition={
                    "Description": f"{WS_DISCONNECT_FUNCTION} ARN",
                    "Value": {"Fn::GetAtt": [WS_DISCONNECT_FUNCTION, "Arn"]},
                },
            )
            self.add_output(
                WS_SEND_FUNCTION,
                definition={
                    "Description": f"{WS_SEND_FUNCTION} ARN",
                    "Value": {"Fn::GetAtt": [WS_SEND_FUNCTION, "Arn"]},
                },
            )
            self.add_output(
                WS_URI,
                definition={
                    "Description": "The WSS Protocol URI to connect to",
                    "Value": {
                        "Fn::Join": [
                            "",
                            [
                                "wss://",
                                {"Ref": WS_API},
                                ".execute-api.",
                                {"Ref": "AWS::Region"},
                                ".amazonaws.com/",
                                {"Ref": "Stage"},
                            ],
                        ]
                    },
                },
            )
            env_vars["WS_URI"] = {
                "Fn::Join": [
                    "",
                    [
                        "wss://",
                        {"Ref": WS_API},
                        ".execute-api.",
                        {"Ref": "AWS::Region"},
                        ".amazonaws.com/",
                        {"Ref": "Stage"},
                    ],
                ]
            }

        # HTTP
        self.add_resource(
            HTTP_FUNCTION,
            definition={
                "Type": "AWS::Serverless::Function",
                "Properties": {
                    "CodeUri": self.build_dir,
                    "Handler": self.handler,
                    "Runtime": "python3.7",
                    "Environment": {"Variables": env_vars},
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
        )
        self.add_resource(
            HTTP_FUNCTION_IAM_POLICY,
            definition={
                "Type": "AWS::IAM::Policy",
                "Properties": {
                    "PolicyName": "root",
                    "PolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": ["s3:*"],
                                "Resource": ["arn:aws:s3:::*", "arn:aws:s3:::*/*"],
                            },
                            {
                                "Effect": "Allow",
                                "Action": "dynamodb:*",
                                "Resource": [
                                    "arn:aws:dynamodb:::*",
                                    "arn:aws:dynamodb:::*/*",
                                ],
                            },
                            {
                                "Effect": "Allow",
                                "Action": ["execute-api:ManageConnections"],
                                "Resource": [
                                    "arn:aws:execute-api:::*",
                                    "arn:aws:execute-api:::*/*",
                                ]
                                # "Resource": [
                                #     {
                                #         "Fn::Sub": "arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${ASGIWebSocketApi}/*"
                                #     }
                                # ],
                            },
                        ],
                    },
                    "Roles": [{"Ref": HTTP_FUNCTION_IAM_ROLE}],
                },
            },
        )
        self.add_output(
            HTTP_FUNCTION_API,
            definition={
                "Description": f"API Gateway endpoint URL for {HTTP_FUNCTION}",
                "Value": {
                    "Fn::Sub": "https://${ServerlessRestApi}.execute-api.${AWS::Region}.amazonaws.com/"
                },
            },
        )
        self.add_output(
            HTTP_FUNCTION,
            definition={
                "Description": f"{HTTP_FUNCTION} ARN",
                "Value": {"Fn::GetAtt": f"{HTTP_FUNCTION}.Arn"},
            },
        )
        self.add_output(
            HTTP_FUNCTION_IAM_ROLE,
            definition={
                "Description": f"Implicit IAM Role created for {HTTP_FUNCTION}",
                "Value": {"Fn::GetAtt": f"{HTTP_FUNCTION_IAM_ROLE}.Arn"},
            },
        )
