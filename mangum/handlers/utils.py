import base64
from typing import Dict, List, Tuple, Union
from urllib.parse import unquote

from mangum.types import Headers


DEFAULT_TEXT_MIME_TYPES = [
    "text/",
    "application/json",
    "application/javascript",
    "application/xml",
    "application/vnd.api+json",
]


def maybe_encode_body(body: Union[str, bytes], *, is_base64: bool) -> bytes:
    body = body or b""
    if is_base64:
        body = base64.b64decode(body)
    elif not isinstance(body, bytes):
        body = body.encode()

    return body


def get_server_and_port(headers: dict) -> Tuple[str, int]:
    server_name = headers.get("host", "mangum")
    if ":" not in server_name:
        server_port = headers.get("x-forwarded-port", 80)
    else:
        server_name, server_port = server_name.split(":")  # pragma: no cover
    server = (server_name, int(server_port))

    return server


def strip_api_gateway_path(path: str, *, api_gateway_base_path: str) -> str:
    if not path:
        return "/"

    if api_gateway_base_path and api_gateway_base_path != "/":
        if not api_gateway_base_path.startswith("/"):
            api_gateway_base_path = f"/{api_gateway_base_path}"
        if path.startswith(api_gateway_base_path):
            path = path[len(api_gateway_base_path) :]

    return unquote(path)


def handle_multi_value_headers(
    response_headers: Headers,
) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    headers: Dict[str, str] = {}
    multi_value_headers: Dict[str, List[str]] = {}
    for key, value in response_headers:
        lower_key = key.decode().lower()
        if lower_key in multi_value_headers:
            multi_value_headers[lower_key].append(value.decode())
        elif lower_key in headers:
            # Move existing to multi_value_headers and append current
            multi_value_headers[lower_key] = [
                headers[lower_key],
                value.decode(),
            ]
            del headers[lower_key]
        else:
            headers[lower_key] = value.decode()
    return headers, multi_value_headers


def handle_base64_response_body(
    body: bytes, headers: Dict[str, str]
) -> Tuple[str, bool]:
    is_base64_encoded = False
    output_body = ""
    if body != b"":
        for text_mime_type in DEFAULT_TEXT_MIME_TYPES:
            if text_mime_type in headers.get("content-type", ""):
                try:
                    output_body = body.decode()
                except UnicodeDecodeError:
                    output_body = base64.b64encode(body).decode()
                    is_base64_encoded = True
                break
        else:
            output_body = base64.b64encode(body).decode()
            is_base64_encoded = True

    return output_body, is_base64_encoded
