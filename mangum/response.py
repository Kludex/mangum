from dataclasses import dataclass
from typing import List


@dataclass
class Response:
    status: int
    headers: List[List[bytes]]  # ex: [[b'content-type', b'text/plain; charset=utf-8']]
    body: bytes
