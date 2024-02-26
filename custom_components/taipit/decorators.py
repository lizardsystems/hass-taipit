"""Taipit integration decorators."""
from __future__ import annotations

import asyncio
from collections.abc import Callable, Awaitable, Coroutine
from functools import wraps
from random import randrange
from typing import TYPE_CHECKING
from typing import TypeVar, ParamSpec, Concatenate, Any

from aiotaipit.exceptions import TaipitError, TaipitAuthError
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import API_TIMEOUT, API_MAX_TRIES, API_RETRY_DELAY

if TYPE_CHECKING:
    pass

_TaipitCoordinatorT = TypeVar("_TaipitCoordinatorT", bound="TaipitCoordinator")
_R = TypeVar("_R")
_P = ParamSpec("_P")


def async_api_request_handler(
        method: Callable[Concatenate[_TaipitCoordinatorT, _P], Awaitable[_R]]
) -> Callable[Concatenate[_TaipitCoordinatorT, _P], Coroutine[Any, Any, _R]]:
    """Decorator to handle API errors."""

    @wraps(method)
    async def wrapper(self: _TaipitCoordinatorT, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        """Wrap an API method."""
        try:
            tries = 0
            api_timeout = API_TIMEOUT
            api_retry_delay = API_RETRY_DELAY
            while True:
                tries += 1
                try:
                    async with asyncio.timeout(api_timeout):
                        result = await method(self, *args, **kwargs)

                    if result is not None:
                        return result

                    self.logger.error(
                        "API error while execute function %s", method.__name__
                    )
                    raise TaipitError(
                        f"API error while execute function {method.__name__}"
                    )

                except asyncio.TimeoutError:
                    api_timeout = tries * API_TIMEOUT
                    self.logger.debug(
                        "Function %s: Timeout connecting to Taipit", method.__name__
                    )
                if tries >= API_MAX_TRIES:
                    raise TaipitError(
                        f"API error while execute function {method.__name__}"
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
