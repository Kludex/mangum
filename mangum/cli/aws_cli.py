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


def aws_package(settings: dict) -> bool:  # pragma: no cover
    cmd = [
        "aws",
        "cloudformation",
        "package",
        "--template-file",
        f"{settings['project_name']}/template.yaml",
        "--output-template-file",
        f"{settings['project_name']}/packaged.yaml",
        "--s3-bucket",
        f"{settings['s3_bucket_name']}",
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE)
    return res.returncode == 0


def aws_deploy(settings: dict) -> bool:  # pragma: no cover
    cmd = [
        "aws",
        "cloudformation",
        "deploy",
        "--template-file",
        f"{settings['project_name']}/packaged.yaml",
        "--stack-name",
        f"{settings['stack_name']}",
        "--capabilities",
        "CAPABILITY_IAM",
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE)
    return res.returncode == 0
