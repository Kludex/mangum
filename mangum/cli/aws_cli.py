import subprocess  # pragma: no cover
import json  # pragma: no cover
from typing import Tuple  # pragma: no cover


def aws_describe(settings: dict) -> Tuple[str, str]:  # pragma: no cover
    cmd = [
        "aws",
        "cloudformation",
        "describe-stacks",
        "--stack-name",
        settings["stack_name"],
        "--query",
        "Stacks[].Outputs",
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE)
    data = json.loads(res.stdout)
    for i in data:
        for j in i:
            if j["OutputKey"] == f"{settings['resource_name']}Api":
                endpoint = j["OutputValue"]
    return f"{endpoint}Prod", f"{endpoint}Stage"


def aws_deploy(settings: dict) -> bool:  # pragma: no cover
    cmd = [
        "aws",
        "cloudformation",
        "deploy",
        "--template-file",
        f"{settings['project_name']}/packaged.yaml",
        f"--stack-name {settings['stack_name']}" "--capabilities CAPABILITY_IAM",
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE)
    return res.returncode == 0


def aws_package(settings: dict) -> bool:  # pragma: no cover
    cmd = [
        "aws",
        "cloudformation",
        "package",
        "--template-file",
        f"{settings['project_name']}/template.yaml",
        f"--output-template-file {settings['project_name']}/packaged.yaml",
        f"--s3-bucket {settings['s3_bucket_name']}",
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE)
    return res.returncode == 0
