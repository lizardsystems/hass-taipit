"""Taipit integration decorators."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Coroutine
from functools import wraps
from random import randint
from typing import TYPE_CHECKING, Any, Concatenate, ParamSpec, TypeVar

import aiohttp
from aiotaipit.exceptions import TaipitAuthError, TaipitError

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import API_MAX_TRIES, API_RETRY_DELAY, API_TIMEOUT

if TYPE_CHECKING:
    from .coordinator import TaipitCoordinator

_TaipitCoordinatorT = TypeVar("_TaipitCoordinatorT", bound="TaipitCoordinator")
_R = TypeVar("_R")
_P = ParamSpec("_P")

_LOGGER = logging.getLogger(__name__)


def async_retry(
    func: Callable[_P, Awaitable[_R]],
) -> Callable[_P, Coroutine[Any, Any, _R]]:
    """Retry async function on transient errors (timeout, API, network).

    TaipitAuthError is never retried — it propagates immediately.
    """

    @wraps(func)
    async def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        tries = 0
        api_timeout = API_TIMEOUT
        api_retry_delay = API_RETRY_DELAY
        last_error: Exception | None = None
        while True:
            tries += 1
            try:
                async with asyncio.timeout(api_timeout):
                    return await func(*args, **kwargs)

            except TaipitAuthError:
                raise

            except TimeoutError as exc:
                last_error = exc
                api_timeout = tries * API_TIMEOUT
                _LOGGER.debug(
                    "Function %s: Timeout connecting to Taipit API",
                    func.__name__,
                )

            except (TaipitError, aiohttp.ClientError) as exc:
                last_error = exc
                _LOGGER.debug(
                    "Function %s: API error (%s)",
                    func.__name__,
                    exc,
                )

            if tries >= API_MAX_TRIES:
                raise TaipitError(
                    f"Failed after {API_MAX_TRIES} attempts: {func.__name__}"
                ) from last_error

            _LOGGER.warning(
                "Attempt %d/%d. Wait %d seconds and try again",
                tries,
                API_MAX_TRIES,
                api_retry_delay,
            )
            await asyncio.sleep(api_retry_delay)
            api_retry_delay += API_RETRY_DELAY + randint(0, API_RETRY_DELAY)

    return wrapper


def async_api_request_handler(
    method: Callable[Concatenate[_TaipitCoordinatorT, _P], Awaitable[_R]],
) -> Callable[Concatenate[_TaipitCoordinatorT, _P], Coroutine[Any, Any, _R]]:
    """Handle API errors with retries for coordinator methods.

    Wraps async_retry with coordinator-specific exception mapping:
    - TaipitAuthError → ConfigEntryAuthFailed
    - TaipitError → UpdateFailed
    """
    retried = async_retry(method)

    @wraps(method)
    async def wrapper(
        self: _TaipitCoordinatorT, *args: _P.args, **kwargs: _P.kwargs
    ) -> _R:
        try:
            return await retried(self, *args, **kwargs)
        except TaipitAuthError as exc:
            raise ConfigEntryAuthFailed(
                f"Taipit auth error: {exc}"
            ) from exc
        except TaipitError as exc:
            raise UpdateFailed(
                f"Taipit API error: {exc}"
            ) from exc

    return wrapper
