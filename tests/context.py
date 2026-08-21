from __future__ import annotations

from mangum.types import LambdaCognitoIdentity, LambdaMobileClientContext

__all__ = ["MockLambdaContext"]


class MockLambdaContext:
    function_name: str = "test-function"
    function_version: str = "$LATEST"
    invoked_function_arn: str = "arn:aws:lambda:us-east-1:123456789012:function:test-function"
    memory_limit_in_mb: int = 128
    aws_request_id: str = "00000000-0000-0000-0000-000000000000"
    log_group_name: str = "/aws/lambda/test-function"
    log_stream_name: str = "2026/01/01/[$LATEST]0123456789abcdef"
    identity: LambdaCognitoIdentity | None = None
    client_context: LambdaMobileClientContext | None = None

    def get_remaining_time_in_millis(self) -> int:
        raise NotImplementedError
