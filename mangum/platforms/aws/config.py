import os
import subprocess
import json
import uuid
from typing import Union
from jinja2 import Environment, FileSystemLoader

import boto3

# from pip._internal import main as pipmain  # pragma: no cover


class AWSConfig:
    def __init__(
        self,
        *,
        base_dir: str,
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
        self.base_dir = base_dir
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
            "base_dir": self.base_dir,
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

    def build(self) -> None:
        if self.generate_s3:
            self.s3_bucket_name = f"{self.resource_name.lower()}-{uuid.uuid4()}"
            s3 = boto3.resource("s3")
            s3.create_bucket(
                Bucket=self.s3_bucket_name,
                CreateBucketConfiguration={"LocationConstraint": self.region_name},
            )

        os.mkdir(self.package_dir)
        template_map = {
            "template.yaml.txt": {
                "name": "template.yaml",
                "directory": self.package_dir,
                "context": self.get_build_context(),
            },
            "app.py.txt": {
                "name": "app.py",
                "context": {},
                "directory": self.package_dir,
            },
            "README.md.txt": {
                "name": "README.md",
                "context": {},
                "directory": self.package_dir,
            },
        }
        for src_template, dest_info in template_map.items():
            with open(
                os.path.join(dest_info["directory"], dest_info["name"]), "w"
            ) as f:
                template = self.env.get_template(src_template)
                rendered = template.render(context=dest_info["context"])
                f.write(rendered)

        with open(os.path.join(self.base_dir, "settings.json"), "w") as f:
            f.write(json.dumps(self.get_build_context()))

        # pipmain(["install", "mangum", "-t", package_dir, "--ignore-installed", "-q"])
