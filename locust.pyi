from collections.abc import Callable
from typing import Any, TypeVar, overload

_F = TypeVar("_F", bound=Callable[..., object])

class Response:
    def raise_for_status(self) -> None: ...
    def json(self) -> dict[str, Any]: ...

class HttpSession:
    def get(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = ...,
        name: str | None = ...,
    ) -> Response: ...
    def post(
        self,
        path: str,
        *,
        json: dict[str, Any] | None = ...,
        headers: dict[str, str] | None = ...,
        files: dict[str, tuple[str, str, str]] | None = ...,
        name: str | None = ...,
    ) -> Response: ...

class HttpUser:
    client: HttpSession
    host: str
    wait_time: Callable[[], float]

    def on_start(self) -> None: ...

def between(min_wait: float, max_wait: float) -> Callable[[], float]: ...
@overload
def task(weight: int) -> Callable[[_F], _F]: ...
@overload
def task(func: _F) -> _F: ...
