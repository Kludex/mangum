import asyncio
import enum
import logging
import contextvars
import typing
import os
import hashlib
import hmac
import json
import datetime
from dataclasses import dataclass, field, InitVar
from urllib.parse import urlparse

import httpx

from mangum.exceptions import (
    UnexpectedMessage,
    WebSocketClosed,
    WebSocketError,
    ConfigurationError,
)
from mangum.types import ASGIApp, Message, Scope


_scope: Scope = contextvars.ContextVar("scope")


def sign(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def get_sigv4_headers(body, *, region_name):
    now = datetime.datetime.utcnow()
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    request_date = now.strftime("%Y%m%d")
    host = f"apigatewaymanagementapi.{region_name}.amazonaws.com"
    canonical_headers = f"host:{host}\nx-amz-date:{amz_date}\n"
    signed_headers = "host;x-amz-date"
    payload_hash = hashlib.sha256(body).hexdigest()
    canonical_request = (
        f"POST\n/\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
    )
    service = "apigatewaymanagementapi"
    algorithm = "AWS4-HMAC-SHA256"
    credential_scope = f"{request_date}/{region_name}/{service}/aws4_request"
    request_hash = hashlib.sha256(canonical_request.encode()).hexdigest()
    string_to_sign = f"{algorithm}\n{amz_date}\n{credential_scope}\n{request_hash}"
    access_key = os.environ["AWS_ACCESS_KEY_ID"]
    secret_key = os.environ["AWS_SECRET_ACCESS_KEY"]
    key_date = sign(("AWS4" + secret_key).encode(), request_date)
    key_region = sign(key_date, region_name)
    key_service = sign(key_region, service)
    signing_key = sign(key_service, "aws4_request")
    signature = hmac.new(
        signing_key, (string_to_sign).encode(), hashlib.sha256
    ).hexdigest()
    authorization_header = (
        f"{algorithm} Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    headers = {
        "Content-Type": "application/x-amz-json-1.0",
        "X-Amz-Date": amz_date,
        "Authorization": authorization_header,
    }

    return headers


@dataclass
class WebSocket:

    connection_id: str
    dsn: InitVar[str]
    api_gateway_region_name: str
    api_gateway_endpoint_url: str
    api_gateway_client: typing.Optional[typing.Any] = None

    def __post_init__(self, dsn: str) -> None:
        if httpx is None:  # pragma: no cover
            raise WebSocketError("httpx must be installed to use WebSockets.")
        self.logger: logging.Logger = logging.getLogger("mangum.websocket")

        parsed_dsn = urlparse(dsn)
        if not any((parsed_dsn.hostname, parsed_dsn.path)):
            raise ConfigurationError("Invalid value for `dsn` provided.")

        scheme = parsed_dsn.scheme
        self.logger.debug(
            f"Attempting WebSocket backend connection using scheme: {scheme}"
        )

        if scheme == "sqlite":
            self.logger.info(
                "The `SQLiteBackend` should be only be used for local "
                "debugging. It will not work in a deployed environment."
            )
            from mangum.backends.sqlite import SQLiteBackend

            self._backend = SQLiteBackend(dsn)  # type: ignore

        elif scheme == "dynamodb":
            from mangum.backends.dynamodb import DynamoDBBackend

            self._backend = DynamoDBBackend(dsn)  # type: ignore

        elif scheme == "s3":
            from mangum.backends.s3 import S3Backend

            self._backend = S3Backend(dsn)  # type: ignore

        elif scheme in ("postgresql", "postgres"):
            from mangum.backends.postgresql import PostgreSQLBackend

            self._backend = PostgreSQLBackend(dsn)  # type: ignore

        elif scheme == "redis":
            from mangum.backends.redis import RedisBackend

            self._backend = RedisBackend(dsn)  # type: ignore

        else:
            raise ConfigurationError(f"{scheme} does not match a supported backend.")

        self.logger.debug("WebSocket backend connection established.")

    async def load_scope(self, event: dict = None) -> typing.Optional[Scope]:
        json_scope = await self._backend.retrieve(self.connection_id)
        if json_scope:

            scope = json.loads(json_scope)
            if event:
                scope["aws.events"].append(event)
            scope.update(
                {
                    "query_string": scope["query_string"].encode(),
                    "headers": [
                        [k.encode(), v.encode()] for k, v in scope["headers"].items()
                    ],
                }
            )

        else:
            scope = None

        _scope.set(scope)

    async def save_scope(self, decode: bool = True) -> None:
        scope = _scope.get()
        if decode:
            scope.update(
                {
                    "query_string": scope["query_string"].decode(),
                    "headers": {h[0].decode(): h[1].decode() for h in scope["headers"]},
                }
            )
        json_scope = json.dumps(scope)
        await self._backend.save(self.connection_id, json_scope=json_scope)

    async def on_connect(self, scope: dict) -> None:
        self.logger.debug("Creating scope entry for %s", self.connection_id)
        await self._backend.connect()
        _scope.set(scope)
        await self.save_scope(decode=False)

    async def on_message(self, event: dict):
        self.logger.debug("Retrieving scope entry for %s", self.connection_id)
        await self._backend.connect()
        await self.load_scope(event=event)

    async def on_disconnect(self) -> None:
        self.logger.debug("Deleting scope entry for %s", self.connection_id)
        await self._backend.connect()
        await self.load_scope()
        scope = _scope.get()

        if scope:
            subscriptions = scope["websocket.broadcast"]["subscriptions"]
            if subscriptions:
                for channel in subscriptions:
                    await self._backend.unsubscribe(self.connection_id, channel)

        await self._backend.delete(self.connection_id)

    async def publish(self, channel: str, *, body: bytes) -> None:
        subscribers = await self._backend.get_subscribers(channel)
        tasks = []
        async with httpx.AsyncClient() as client:
            for connection_id in subscribers:
                if isinstance(connection_id, bytes):
                    connection_id = connection_id.decode()

                task = asyncio.create_task(
                    self.post_to_connection(
                        connection_id, client=client, body=body, channel=channel
                    )
                )
                tasks.append(task)

            await asyncio.gather(*tasks)

        await self.save_scope()

    async def subscribe(self, channel: str) -> None:
        await self._backend.subscribe(channel, connection_id=self.connection_id)
        scope = _scope.get()
        scope["extensions"]["websocket.broadcast"]["subscriptions"].append(channel)
        await self.save_scope()

    async def unsubscribe(self, channel: str) -> None:
        await self._backend.unsubscribe(channel, connection_id=self.connection_id)
        scope = _scope.get()
        scope["extensions"]["websocket.broadcast"]["subscriptions"].remove(channel)
        await self.save_scope()

    async def send(self, body: bytes) -> None:
        await self.post_to_connection(self.connection_id, body=body)

    async def post_to_connection(
        self,
        connection_id: str,
        *,
        client: httpx.AsyncClient,
        body: bytes,
        channel: typing.Optional[str] = None,
    ) -> None:  # pragma: no cover

        headers = get_sigv4_headers(body, region_name=self.api_gateway_region_name)
        url = f"{self.api_gateway_endpoint_url}/@connections/{connection_id}"
        response = await client.post(url, data=body, headers=headers)
        if response.status_code == 410:
            if channel:
                self.logger.debug(
                    "Deleting scope entry for %s and unsubscribing from %s",
                    connection_id,
                    channel,
                )
                await self._backend.delete(connection_id)
                await self._backend.unsubscribe(channel, connection_id=connection_id)
            else:
                await self.on_disconnect()
        elif response.status_code != 200:
            raise WebSocketError(f"Error: {response.status_code}")


class WebSocketCycleState(enum.Enum):
    """
    The state of the ASGI WebSocket connection.

    * **CONNECTING** - Initial state. The ASGI application instance will be run with the
    connection scope containing the `websocket` type.
    * **HANDSHAKE** - The ASGI `websocket` connection with the application has been
    established, and a `websocket.connect` event has been pushed to the application
    queue. The application will respond by accepting or rejecting the connection.
    If rejected, a 403 response will be returned to the client, and it will be removed
    from API Gateway.
    * **RESPONSE** - Handshake accepted by the application. Data received in the API
    Gateway message event will be sent to the application. A `websocket.receive` event
    will be pushed to the application queue.
    * **DISCONNECTING** - The ASGI connection cycle is complete and should be
    disconnected from the application. A `websocket.disconnect` event will be pushed to
    the queue, and a response will be returned to the client connection.
    * **CLOSED** - The application has sent a `websocket.close` message. This will
    either be in response to a `websocket.disconnect` event or occurs when a connection
    is rejected in response to a `websocket.connect` event.
    """

    CONNECTING = enum.auto()
    HANDSHAKE = enum.auto()
    RESPONSE = enum.auto()
    DISCONNECTING = enum.auto()
    CLOSED = enum.auto()


@dataclass
class WebSocketCycle:
    """
    Manages the application cycle for an ASGI `websocket` connection.

    * **scope** - A dictionary containing the connection scope used to run the ASGI
    application instance.
    * **body** -  A string containing the body content of the request.
    * **websocket** - A `WebSocket` connection handler interface for the selected
    `WebSocketBackend` subclass. Contains the ASGI connection `scope` and client
    connection identifier.
    * **state** - An enumerated `WebSocketCycleState` type that indicates the state of
    the ASGI connection.
    * **app_queue** - An asyncio queue (FIFO) containing messages to be received by the
    application.
    * **response** - A dictionary containing the response data to return in AWS Lambda.
    This will only contain a `statusCode` for WebSocket connections.
    """

    connection_id: str
    dsn: InitVar[str]
    api_gateway_region_name: str
    api_gateway_endpoint_url: str
    state: WebSocketCycleState = WebSocketCycleState.CONNECTING
    response: dict = field(default_factory=dict)

    def __post_init__(self, dsn: str) -> None:
        self.logger: logging.Logger = logging.getLogger("mangum.websockets")
        self.response["statusCode"] = 200
        self.app_queue: asyncio.Queue = asyncio.Queue()
        self.app_queue.put_nowait({"type": "websocket.connect"})
        self.websocket: WebSocket = WebSocket(
            self.connection_id,
            dsn=dsn,
            api_gateway_endpoint_url=self.api_gateway_endpoint_url,
            api_gateway_region_name=self.api_gateway_region_name,
        )

    async def __call__(self, app: ASGIApp, *, event: dict) -> dict:
        self.logger.debug("WebSocket cycle starting.")
        self.body = event.get("body", "")
        await self.websocket.on_message(event)
        await self.run(app)

        return self.response

    async def run(self, app: ASGIApp) -> None:
        """
        Calls the application with the ASGI `websocket` connection scope.
        """
        scope = _scope.get().copy()
        try:
            await app(scope, self.receive, self.send)
        except WebSocketClosed:
            self.response["statusCode"] = 403
        except UnexpectedMessage:
            self.response["statusCode"] = 500
        except BaseException as exc:
            self.logger.error("Exception in ASGI application", exc_info=exc)
            self.response["statusCode"] = 500

    async def receive(self) -> Message:
        """
        Awaited by the application to receive ASGI `websocket` events.
        """
        if self.state is WebSocketCycleState.CONNECTING:

            # Initial ASGI connection established. The next event returned by the queue
            # will be `websocket.connect` to initiate the handshake.
            self.state = WebSocketCycleState.HANDSHAKE

        elif self.state is WebSocketCycleState.HANDSHAKE:

            # ASGI connection handshake accepted. The next event returned by the queue
            # will be `websocket.receive` containing the message data from API Gateway.
            self.state = WebSocketCycleState.RESPONSE

        elif self.state is WebSocketCycleState.RESPONSE:

            # ASGI connection disconnecting. The next event returned by the queue will
            # be `websocket.disconnect` to close the current ASGI connection.
            self.state = WebSocketCycleState.DISCONNECTING

        return await self.app_queue.get()

    async def send(self, message: Message) -> None:
        """
        Awaited by the application to send ASGI `websocket` events.
        """
        message_type = message["type"]
        self.logger.info(
            "%s:  '%s' event received from application.", self.state, message_type
        )

        if self.state is WebSocketCycleState.HANDSHAKE and message_type in (
            "websocket.accept",
            "websocket.close",
        ):

            # API Gateway handles the WebSocket client handshake in the connect event,
            # and it cannot be negotiated by the application directly. The handshake
            # behaviour is simulated to allow the application to accept or reject the
            # the client connection. This process does not support subprotocols.
            if message_type == "websocket.accept":
                await self.app_queue.put(
                    {"type": "websocket.receive", "bytes": None, "text": self.body}
                )
            elif message_type == "websocket.close":
                self.state = WebSocketCycleState.CLOSED
                raise WebSocketClosed
        elif self.state is WebSocketCycleState.RESPONSE and message_type in (
            "websocket.send",
            "websocket.broadcast.subscribe",
            "websocket.broadcast.publish",
        ):
            if message["type"] == "websocket.broadcast.subscribe":
                channel = message["channel"]
                self.logger.debug(
                    f"Subscribing {self.websocket.connection_id} to {channel}"
                )
                await self.websocket.subscribe(channel)

            elif message["type"] == "websocket.broadcast.publish":
                channel = message["channel"]
                body = message["body"].encode()
                self.logger.debug(f"Publishing {body} to {channel}")
                await self.websocket.publish(channel, body=body)

            elif message["type"] == "websocket.send":
                body = message["body"].encode()
                await self.websocket.send_data(body)

            await self.app_queue.put({"type": "websocket.disconnect", "code": "1000"})

        elif (
            self.state is WebSocketCycleState.DISCONNECTING
            and message_type == "websocket.close"
        ):

            # ASGI connection is closing, however the WebSocket client in API Gateway
            # will persist and be used in future application ASGI connections until the
            # client disconnects or the application rejects a handshake.
            self.state = WebSocketCycleState.CLOSED
        else:
            raise UnexpectedMessage(
                f"{self.state}: Unexpected '{message_type}' event received."
            )
