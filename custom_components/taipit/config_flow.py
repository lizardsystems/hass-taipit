"""Config flow for taipit integration."""
from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import aiohttp
from aiotaipit import SimpleTaipitAuth, TaipitApi
from aiotaipit.exceptions import TaipitAuthError, TaipitError
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_TOKEN,
    DOMAIN,
)
from .decorators import async_retry

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

PASSWORD_SCHEMA = vol.Schema({vol.Required(CONF_PASSWORD): str})


@async_retry
async def _async_validate_credentials(
    hass: HomeAssistant, username: str, password: str
) -> dict[str, Any]:
    """Validate credentials and return token data."""
    session = async_get_clientsession(hass)
    token_data: dict[str, Any] = {}

    def _on_token_update(token: dict[str, Any]) -> None:
        token_data.update(token)

    auth = SimpleTaipitAuth(
        username=username,
        password=password,
        session=session,
        token_update_callback=_on_token_update,
    )
    api = TaipitApi(auth)
    await api.async_get_meters()
    return token_data


class TaipitConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for taipit."""

    VERSION = 1

    async def _async_try_validate(
        self,
        username: str,
        password: str,
        errors: dict[str, str],
        context: str = "",
    ) -> dict[str, Any] | None:
        """Try to validate credentials and return token data on success."""
        try:
            return await _async_validate_credentials(self.hass, username, password)
        except TaipitAuthError as err:
            _LOGGER.warning(
                "Invalid credentials for %s: %s", username, err, exc_info=True
            )
            errors["base"] = "invalid_auth"
        except (TaipitError, aiohttp.ClientError) as err:
            _LOGGER.warning(
                "Connection error for %s: %s", username, err, exc_info=True
            )
            errors["base"] = "cannot_connect"
        except Exception:
            _LOGGER.exception(
                "Unexpected exception%s", f" during {context}" if context else ""
            )
            errors["base"] = "unknown"
        return None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME].strip().lower()
            password = user_input[CONF_PASSWORD]

            if token_data := await self._async_try_validate(
                username, password, errors
            ):
                await self.async_set_unique_id(username)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=username,
                    data={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_TOKEN: token_data,
                    },
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauthorization request from Taipit."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm re-authentication with Taipit."""
        errors: dict[str, str] = {}

        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            password = user_input[CONF_PASSWORD]
            username = reauth_entry.data[CONF_USERNAME]

            if token_data := await self._async_try_validate(
                username, password, errors, context="reauth"
            ):
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={
                        CONF_PASSWORD: password,
                        CONF_TOKEN: token_data,
                    },
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=PASSWORD_SCHEMA,
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration."""
        errors: dict[str, str] = {}

        reconfigure_entry = self._get_reconfigure_entry()

        if user_input is not None:
            password = user_input[CONF_PASSWORD]
            username = reconfigure_entry.data[CONF_USERNAME]

            if token_data := await self._async_try_validate(
                username, password, errors, context="reconfigure"
            ):
                return self.async_update_reload_and_abort(
                    reconfigure_entry,
                    data_updates={
                        CONF_PASSWORD: password,
                        CONF_TOKEN: token_data,
                    },
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=PASSWORD_SCHEMA,
            description_placeholders={
                CONF_USERNAME: reconfigure_entry.data.get(CONF_USERNAME, ""),
            },
            errors=errors,
        )
