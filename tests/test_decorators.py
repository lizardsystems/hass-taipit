"""Tests for Taipit decorators."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from aiotaipit.exceptions import TaipitAuthError, TaipitError
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.taipit.decorators import async_api_request_handler, async_retry


# ---------------------------------------------------------------------------
# async_retry
# ---------------------------------------------------------------------------


async def test_async_retry_success() -> None:
    """Test function succeeds on first try."""
    mock_fn = AsyncMock(return_value="ok")
    wrapped = async_retry(mock_fn)

    result = await wrapped()

    assert result == "ok"
    mock_fn.assert_awaited_once()


async def test_async_retry_transient_then_success() -> None:
    """Test retry on TaipitError then success."""
    mock_fn = AsyncMock(side_effect=[TaipitError("fail"), "ok"])
    wrapped = async_retry(mock_fn)

    result = await wrapped()

    assert result == "ok"
    assert mock_fn.await_count == 2


async def test_async_retry_exhausted() -> None:
    """Test that 3 failures raises TaipitError."""
    mock_fn = AsyncMock(side_effect=TaipitError("persistent failure"))
    wrapped = async_retry(mock_fn)

    with pytest.raises(TaipitError, match="Failed after 3 attempts"):
        await wrapped()

    assert mock_fn.await_count == 3


async def test_async_retry_auth_error_no_retry() -> None:
    """Test TaipitAuthError propagates immediately without retry."""
    mock_fn = AsyncMock(side_effect=TaipitAuthError("auth failed"))
    wrapped = async_retry(mock_fn)

    with pytest.raises(TaipitAuthError, match="auth failed"):
        await wrapped()

    # Should only be called once - no retry on auth errors
    mock_fn.assert_awaited_once()


async def test_async_retry_timeout_then_success() -> None:
    """Test retry on TimeoutError then success."""
    mock_fn = AsyncMock(side_effect=[TimeoutError("timed out"), "ok"])
    wrapped = async_retry(mock_fn)

    result = await wrapped()

    assert result == "ok"
    assert mock_fn.await_count == 2


async def test_async_retry_client_error_then_success() -> None:
    """Test retry on aiohttp.ClientError then success."""
    mock_fn = AsyncMock(
        side_effect=[aiohttp.ClientError("connection reset"), "ok"]
    )
    wrapped = async_retry(mock_fn)

    result = await wrapped()

    assert result == "ok"
    assert mock_fn.await_count == 2


async def test_async_retry_preserves_function_name() -> None:
    """Test that @wraps preserves function metadata."""
    async def my_function():
        return "ok"

    wrapped = async_retry(my_function)
    assert wrapped.__name__ == "my_function"


# ---------------------------------------------------------------------------
# async_api_request_handler
# ---------------------------------------------------------------------------


async def test_api_request_handler_success() -> None:
    """Test async_api_request_handler returns data on success."""
    mock_self = MagicMock()

    async def method(self):
        return {"result": "data"}

    wrapped = async_api_request_handler(method)

    result = await wrapped(mock_self)
    assert result == {"result": "data"}


async def test_api_request_handler_auth_error() -> None:
    """Test TaipitAuthError maps to ConfigEntryAuthFailed."""
    mock_self = MagicMock()

    async def method(self):
        raise TaipitAuthError("auth expired")

    wrapped = async_api_request_handler(method)

    with pytest.raises(ConfigEntryAuthFailed):
        await wrapped(mock_self)


async def test_api_request_handler_api_error() -> None:
    """Test TaipitError maps to UpdateFailed."""
    mock_self = MagicMock()

    async def method(self):
        raise TaipitError("api error")

    wrapped = async_api_request_handler(method)

    with pytest.raises(UpdateFailed):
        await wrapped(mock_self)
