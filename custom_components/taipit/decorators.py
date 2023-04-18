"""Taipit integration decorators."""
from __future__ import annotations
from functools import wraps
import asyncio

from collections.abc import Callable, Awaitable, Coroutine
from typing import TypeVar, ParamSpec, Concatenate, Any
from typing import TYPE_CHECKING

from aiotaipit.exceptions import TaipitError, TaipitAuthError
from async_timeout import timeout

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
from random import randrange
from .const import API_TIMEOUT, API_MAX_TRIES, API_RETRY_DELAY


if TYPE_CHECKING:
    from .coordinator import TaipitCoordinator


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
            tries = 0
            api_timeout = API_TIMEOUT
            api_retry_delay = API_RETRY_DELAY
            while True:
                tries += 1
                try:
                    async with timeout(api_timeout):
                        result = await func(self, *args, **kwargs)

                    if result is not None:
                        return result

                    self.logger.error(
                        "API error while execute function %s", func.__name__
                    )
                    raise TaipitError(
                        f"API error while execute function {func.__name__}"
                    )

                except asyncio.TimeoutError:
                    api_timeout = tries * API_TIMEOUT
                    self.logger.debug(
                        "Function %s: Timeout connecting to Taipit", func.__name__
                    )
                if tries >= API_MAX_TRIES:
                    raise TaipitError(
                        f"API error while execute function {func.__name__}"
                    )
                self.logger.warning(
                    "Attempt %d/%d. Wait %d seconds and try again",
                    tries,
                    API_MAX_TRIES,
                    api_retry_delay,
                )
                await asyncio.sleep(api_retry_delay)
                api_retry_delay += API_RETRY_DELAY + randrange(API_RETRY_DELAY)

        except TaipitAuthError as exc:
            raise ConfigEntryAuthFailed("Auth error") from exc
        except TaipitError as exc:
            raise UpdateFailed(f"Invalid response from API: {exc}") from exc

    return wrapper
