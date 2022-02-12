import base64
from abc import ABCMeta, abstractmethod
from typing import Dict, Any, Tuple, List

from mangum.types import Response, Request, LambdaEvent, LambdaContext


class AbstractHandler(metaclass=ABCMeta):
    def __init__(
        self,
        trigger_event: LambdaEvent,
        trigger_context: LambdaContext,
    ):
        self.trigger_event = trigger_event
        self.trigger_context = trigger_context

    @property
    @abstractmethod
    def request(self) -> Request:
        """
        Parse an ASGI scope from the request event
        """

    @property
    @abstractmethod
    def body(self) -> bytes:
        """
        Get the raw body from the request event
        """

    @abstractmethod
    def transform_response(self, response: Response) -> Dict[str, Any]:
        """
        After running our application, transform the response to the correct format for
        this handler
        """

    @staticmethod
    def from_trigger(
        trigger_event: LambdaEvent,
        trigger_context: LambdaContext,
        api_gateway_base_path: str = "/",
    ) -> "AbstractHandler":
        """
        A factory method that determines which handler to use. All this code should
        probably stay in one place to make sure we are able to uniquely find each
        handler correctly.
        """

        # These should be ordered from most specific to least for best accuracy
        if (
            "requestContext" in trigger_event
            and "elb" in trigger_event["requestContext"]
        ):
            from mangum.handlers.aws_alb import AwsAlb

            return AwsAlb(trigger_event, trigger_context)
        if (
            "Records" in trigger_event
            and len(trigger_event["Records"]) > 0
            and "cf" in trigger_event["Records"][0]
        ):
            from mangum.handlers.aws_cf_lambda_at_edge import AwsCfLambdaAtEdge

            return AwsCfLambdaAtEdge(trigger_event, trigger_context)

        if "version" in trigger_event and "requestContext" in trigger_event:
            from mangum.handlers.aws_http_gateway import AwsHttpGateway

            return AwsHttpGateway(
                trigger_event,
                trigger_context,
                api_gateway_base_path,
            )

        if "resource" in trigger_event:
            from mangum.handlers.aws_api_gateway import AwsApiGateway

            return AwsApiGateway(
                trigger_event,
                trigger_context,
                api_gateway_base_path,
            )

        raise TypeError("Unable to determine handler from trigger event")

    @staticmethod
    def _handle_multi_value_headers(
        response_headers: List[List[bytes]],
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

    @staticmethod
    def _handle_base64_response_body(
        body: bytes, headers: Dict[str, str]
    ) -> Tuple[str, bool]:
        """
        To ease debugging for our users, try and return strings where we can,
        otherwise to ensure maximum compatibility with binary data, base64 encode it.
        """
        is_base64_encoded = False
        output_body = ""
        if body != b"":
            from ..adapter import DEFAULT_TEXT_MIME_TYPES

            for text_mime_type in DEFAULT_TEXT_MIME_TYPES:
                if text_mime_type in headers.get("content-type", ""):
                    try:
                        output_body = body.decode()
                    except UnicodeDecodeError:
                        # Can't decode it, base64 it and be done
                        output_body = base64.b64encode(body).decode()
                        is_base64_encoded = True
                    break
            else:
                # Not text, base64 encode
                output_body = base64.b64encode(body).decode()
                is_base64_encoded = True

        return output_body, is_base64_encoded
