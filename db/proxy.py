from .base import SimpleConcurrentRepository
from .exceptions import ProxyNotExists, ProxyFormatError


lock = SimpleConcurrentRepository.locked


class ProxyRepository(SimpleConcurrentRepository):
    _PROXY_BODY = "proxy:body"
    _PROXY_CURRENT_PORT = "proxy:port"

    def __str__(self):
        return f"{self._proxy_body}:{self._proxy_port}"

    @property
    @lock()
    def can_use(self) -> tuple[bool, str | None]:
        body, port = self._proxy_body, self._proxy_port

        if (not body) or (not port or not (0 < port <= 900)):
            return False, f"{body}:{port}"

        return True, None

    @lock()
    def next(self) -> str:
        body, port = self._proxy_body, self._proxy_port

        if not (body and port):
            raise ProxyNotExists()

        self._proxy_port += 1

        return f"{body}:{port}"

    @SimpleConcurrentRepository.locked()
    def add(self, proxy: str):
        proxy_components = proxy.split(":")
        proxy_body, proxy_port = ":".join(proxy_components[2]), int(proxy_components[-1])

        if not (0 < proxy_port <= 1000):
            raise ProxyFormatError()

        self._conn.set(self._PROXY_BODY, proxy_body)
        self._conn.set(self._PROXY_CURRENT_PORT, proxy_port)

        return str(self)

    @property
    def _proxy_port(self):
        port = self._conn.get(self._PROXY_CURRENT_PORT).decode()

        if not port:
            return port

        return int(port)

    @_proxy_port.setter
    def _proxy_port(self, new_port: int):
        if new_port > 1000:
            raise ProxyFormatError("Try update proxy port failed")

        self._conn.set(self._PROXY_CURRENT_PORT, new_port)

    @property
    def _proxy_body(self) -> str | None:
        return self._conn.get(self._PROXY_BODY).decode()
