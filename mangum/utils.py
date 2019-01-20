import urllib.parse


def encode_query_string(query_string_params: dict) -> str:
    return urllib.parse.urlencode(query_string_params).encode("ascii")
