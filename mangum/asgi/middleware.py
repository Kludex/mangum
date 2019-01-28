from typing import Any


class ServerlessMiddleware:
    def __init__(self, app, debug: bool = False) -> None:
        """
        Base class for implementing platform-specific ASGI middleware.
        """
        self.app = app
        self.debug = debug

    def __call__(self, *args, **kwargs) -> Any:
        """
        Attempt to run the application request-response cycle for a particular platform
        implementation.

        If an unhandled error is raised within the application, then optionally allow
        returning the error in the response if a debug response method exists.
        """
        try:
            response = self.asgi(*args, **kwargs)
        except Exception as exc:
            if self.debug:
                return self._debug(str(exc))
            raise exc
        else:
            return response

    def asgi(self, *args, **kwargs) -> Any:
        """
        This should be used as the main entrypoint for HTTP request events received
        from a platform.

        It should handle building a connection scope from the request information and
        running the ASGI request-response cycle, finally returning a valid response to
        the platform.
        """
        raise NotImplementedError()

    def _debug(self, content: str, status_code: int = 500) -> Any:
        """
        This should be used to send debug responses to a platform in the event of an
        unhandled server error. The debug behaviour is disabled by default, it should
        NOT be used in production environments.
        """
        raise NotImplementedError()
