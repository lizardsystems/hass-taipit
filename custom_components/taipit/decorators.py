"""Taipit integration decorators."""
from functools import wraps
from typing import TypeVar, ParamSpec, Callable, Concatenate, Awaitable, Coroutine, Any

from aiotaipit.exceptions import TaipitError, TaipitAuthError
from async_timeout import timeout
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import DEFAULT_API_TIMEOUT

_TaipitCoordinatorT = TypeVar("_TaipitCoordinatorT", bound="TaipitCoordinator")
_R = TypeVar("_R")
_P = ParamSpec("_P")

_FuncType = Callable[Concatenate[_TaipitCoordinatorT, _P], Awaitable[_R]]
_ReturnFuncType = Callable[
    Concatenate[_TaipitCoordinatorT, _P], Coroutine[Any, Any, _R]
]


def api_request_handler(
    func: _FuncType[_TaipitCoordinatorT, _P, _R]
) -> _ReturnFuncType[_TaipitCoordinatorT, _P, _R]:
    """Decorator to handle API errors."""

    @wraps(func)
    async def wrapper(
        self: _TaipitCoordinatorT, *args: _P.args, **kwargs: _P.kwargs
    ) -> _R:
        """Wrap an API method."""
        try:
            async with timeout(DEFAULT_API_TIMEOUT):
                result = await func(self, *args, **kwargs)
            if not result:
                raise TaipitError("API error while execute function %s", func.__name__)
        except TaipitAuthError as exc:
            raise ConfigEntryAuthFailed("Auth error") from exc
        except TaipitError as error:  # pylint: disable=broad-except
            raise UpdateFailed(f"Invalid response from API: {error}") from error

        return result

    return wrapper
