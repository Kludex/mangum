from __future__ import annotations

import requests


def test_get_with_query_string(function_url: str) -> None:
    response = requests.get(f"{function_url}test/path", params={"hello": "world"}, timeout=60)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.headers["x-echo"] == "mangum"
    assert response.json() == {
        "method": "GET",
        "path": "/test/path",
        "query": "hello=world",
        "body_length": 0,
    }


def test_post_with_body(function_url: str) -> None:
    response = requests.post(f"{function_url}submit", data=b"say=Hi&to=Mom", timeout=60)

    assert response.status_code == 200
    assert response.json() == {
        "method": "POST",
        "path": "/submit",
        "query": "",
        "body_length": 13,
    }
