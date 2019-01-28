class ServerlessMiddleware:
    def __init__(self, app, debug: bool = False) -> None:
        self.app = app
        self.debug = debug

    def __call__(self, *args, **kwargs):
        try:
            response = self.asgi(*args, **kwargs)
        except Exception as exc:
            if self.debug:
                return self._debug(exc)
            raise exc
        else:
            return response

    def asgi(self, *args, **kwargs) -> None:
        """
        This should be used as the main entrypoint for HTTP request events received
        from a platform.

        It should handle building a connection scope from the request information and
        running the ASGI request-response cycle, finally returning a valid response to
        the platform.
        """
        raise NotImplementedError()  # pragma: no cover

    def _debug(self, content: str, status_code: int = 500) -> None:
        """
        This should be used to send debug responses to a platform in the event of an
        unhandled server error. The debug behaviour is disbaled by default, it should
        NOT be used in production environments.
        """
        raise NotImplementedError()  # pragma: no cover
