import urllib.parse
import os
import json


def encode_query_string(query_string_params: dict) -> str:
    return urllib.parse.urlencode(query_string_params).encode("ascii")


def get_file_content(*, filename: str, directory: str, as_json: bool = False) -> str:
    if not os.path.isdir(directory):
        raise IOError(f"Directory not found: '{directory}' does not exist.")
    filepath = os.path.join(directory, filename)
    if not os.path.exists(filepath):
        raise IOError(f"File not found: '{filepath}' does not exist.")
    with open(filepath, "r") as f:
        content = f.read()
    if as_json:
        try:
            content = json.loads(json.loads(content))
        except json.decoder.JSONDecodeError:
            raise ValueError(f"Invalid JSON data: '{filepath}' could not be decoded.")
    return content


def write_file_content(
    *, content: str, filename: str, directory: str, as_json: bool = False
) -> None:
    if not os.path.isdir(directory):
        raise IOError(f"Directory not found: '{directory}' does not exist.")
    filepath = os.path.join(directory, filename)
    if as_json:
        content = json.dumps(content)
    with open(filepath, "w") as f:
        f.write(content)
