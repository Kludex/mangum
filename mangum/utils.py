import urllib.parse
from typing import Union


def encode_query_string(query_string_params: dict) -> str:
    return urllib.parse.urlencode(query_string_params).encode()


def maybe_encode(data: Union[str, bytes]) -> bytes:
    if not isinstance(data, bytes):
        return data.encode("utf-8")
    return data
